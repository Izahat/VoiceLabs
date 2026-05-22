import { translations } from './i18n.js';
import { getCurrentLang } from './state.js';
import { handleRefAudioFile } from './text-mode.js';

let mediaRecorder = null;
let audioChunks = [];
let audioContext = null;
let analyser = null;
let canvasCtx = null;
let animationId = null;
let isRecording = false;
let isRecordingPreparing = false;
let recordingStream = null;
let recordingStartTimeout = null;
let recordingInitiated = false;
let recordingStartTime = 0;
let recordingTimerInterval = null;

const MIN_RECORDING_MS = 500;
const WAVE_BUFFER_SIZE = 500;
const SCROLL_SPEED = 8;
let waveBuffer = new Float32Array(WAVE_BUFFER_SIZE);

export function setupRecordButton() {
  const recordBtn = document.getElementById('record-audio-btn');
  const canvas = document.getElementById('waveform-canvas');

  if (!recordBtn || recordBtn.dataset.setup) return;
  recordBtn.dataset.setup = 'true';

  // Get context early, but DON'T set dimensions — canvas is hidden (display: none)
  // Dimensions will be set when recording starts and canvas becomes visible
  if (canvas) canvasCtx = canvas.getContext('2d');

  recordBtn.addEventListener('mousedown', startRecording);
  document.addEventListener('mouseup', handleGlobalMouseUp);
  recordBtn.addEventListener('touchstart', (e) => { e.preventDefault(); startRecording(); });
  document.addEventListener('touchend', handleGlobalTouchEnd);
}

function handleGlobalMouseUp() {
  if (!recordingInitiated) return;
  recordingInitiated = false;
  stopRecording();
}

function handleGlobalTouchEnd() {
  if (!recordingInitiated) return;
  recordingInitiated = false;
  stopRecording();
}

async function startRecording() {
  if (isRecording || isRecordingPreparing) return;

  try {
    isRecordingPreparing = true;
    recordingInitiated = true;

    const recordBtn = document.getElementById('record-audio-btn');
    recordBtn.classList.add('recording', 'preparing');
    const lang = getCurrentLang();
    recordBtn.querySelector('.push-to-talk__text').textContent =
      translations[lang]?.voiceCloning?.releaseToStop || 'Release to Stop';

    recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    recordingStartTimeout = setTimeout(async () => {
      if (!isRecordingPreparing) {
        recordingStream.getTracks().forEach(track => track.stop());
        return;
      }

      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioContext.createMediaStreamSource(recordingStream);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 512;
      analyser.smoothingTimeConstant = 0.8;
      source.connect(analyser);

      mediaRecorder = new MediaRecorder(recordingStream);
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const elapsed = Date.now() - recordingStartTime;

        if (recordingStream) {
          recordingStream.getTracks().forEach(track => track.stop());
          recordingStream = null;
        }
        if (audioContext) { audioContext.close(); audioContext = null; }

        if (elapsed < MIN_RECORDING_MS) {
          cleanupRecordingUI();
          return;
        }

        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const fileName = `recording_${Date.now()}.wav`;
        const file = new File([audioBlob], fileName, { type: 'audio/wav' });
        handleRefAudioFile(file);
        cleanupRecordingUI();
      };

      mediaRecorder.start(100);
      recordingStartTime = Date.now();
      isRecording = true;
      isRecordingPreparing = false;
      recordBtn.classList.remove('preparing');
      waveBuffer = new Float32Array(WAVE_BUFFER_SIZE);

      const canvas = document.getElementById('waveform-canvas');
      if (canvas) {
        canvas.classList.add('active');
        // Must set dimensions AFTER canvas is visible (getBoundingClientRect works)
        const rect = canvas.getBoundingClientRect();
        canvas.width = Math.max(rect.width * 2, 100);
        canvas.height = Math.max(rect.height * 2, 100);
        drawWaveform();
      }

      recordingTimerInterval = setInterval(updateRecordingTimer, 100);

    }, 300);

  } catch (err) {
    console.error('Recording error:', err);
    isRecordingPreparing = false;
    recordingInitiated = false;
    cleanupRecordingUI();
    alert('Could not access microphone. Please check permissions.');
  }
}

function stopRecording() {
  if (recordingStartTimeout) {
    clearTimeout(recordingStartTimeout);
    recordingStartTimeout = null;
  }

  if (recordingTimerInterval) {
    clearInterval(recordingTimerInterval);
    recordingTimerInterval = null;
  }

  if (isRecordingPreparing) {
    isRecordingPreparing = false;
    if (recordingStream) {
      recordingStream.getTracks().forEach(track => track.stop());
      recordingStream = null;
    }
    cleanupRecordingUI();
    return;
  }

  if (!isRecording || !mediaRecorder) return;

  mediaRecorder.stop();
  isRecording = false;

  const canvas = document.getElementById('waveform-canvas');
  if (canvas) canvas.classList.remove('active');

  if (animationId) {
    cancelAnimationFrame(animationId);
    animationId = null;
  }
}

function cleanupRecordingUI() {
  const recordBtn = document.getElementById('record-audio-btn');
  if (recordBtn) {
    recordBtn.classList.remove('recording', 'preparing');
    const lang = getCurrentLang();
    recordBtn.querySelector('.push-to-talk__text').textContent =
      translations[lang]?.voiceCloning?.holdToRecord || 'Hold to Record';
  }
  const canvas = document.getElementById('waveform-canvas');
  if (canvas) canvas.classList.remove('active');
  if (animationId) {
    cancelAnimationFrame(animationId);
    animationId = null;
  }
}

function updateRecordingTimer() {
  if (!isRecording) return;
  const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  const recordBtn = document.getElementById('record-audio-btn');
  if (recordBtn) {
    const textEl = recordBtn.querySelector('.push-to-talk__text');
    if (textEl) {
      textEl.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
    }
  }
}

function drawWaveform() {
  if (!analyser || !canvasCtx || !isRecording) return;

  const canvas = document.getElementById('waveform-canvas');
  const width = canvas.width;
  const height = canvas.height;
  const centerY = height / 2;

  const frequencyBinCount = analyser.frequencyBinCount;
  const frequencyData = new Uint8Array(frequencyBinCount);
  analyser.getByteFrequencyData(frequencyData);

  const td = new Uint8Array(analyser.fftSize);
  analyser.getByteTimeDomainData(td);

  // Scroll buffer left, fill right with new audio data
  waveBuffer.copyWithin(0, SCROLL_SPEED);
  for (let i = 0; i < SCROLL_SPEED; i++) {
    const idx = Math.floor(i * td.length / SCROLL_SPEED);
    waveBuffer[WAVE_BUFFER_SIZE - SCROLL_SPEED + i] = (td[idx] - 128) / 128.0;
  }

  // Clear
  canvasCtx.clearRect(0, 0, width, height);

  // ── Background ──
  const bg = canvasCtx.createLinearGradient(0, 0, 0, height);
  bg.addColorStop(0, '#08041a');
  bg.addColorStop(0.5, '#0d0825');
  bg.addColorStop(1, '#08041a');
  canvasCtx.fillStyle = bg;
  canvasCtx.fillRect(0, 0, width, height);

  // ── Subtle frequency bars (background texture) ──
  const barCount = 48;
  const totalW = width * 0.96;
  const barW = totalW / barCount;
  const barGap = 2;
  const barBw = barW - barGap;
  const barSx = (width - totalW) / 2;

  for (let i = 0; i < barCount; i++) {
    const fidx = Math.floor((i / barCount) * frequencyBinCount * 0.6);
    const fval = frequencyData[fidx] / 255;
    const barH = Math.max(3, fval * height * 0.35);
    const bx = barSx + i * barW;

    canvasCtx.fillStyle = `hsla(270, 60%, 40%, ${0.06 + fval * 0.08})`;
    canvasCtx.fillRect(bx, centerY - barH / 2, barBw, barH);
  }

  // ── Build smooth waveform points ──
  const points = [];
  for (let i = 0; i < WAVE_BUFFER_SIZE; i++) {
    const px = (i / WAVE_BUFFER_SIZE) * width;
    const py = centerY + waveBuffer[i] * height * 0.42;
    points.push({ x: px, y: py });
  }

  // ── Glow layers (outer to inner) ──
  const glowLayers = [
    { lineW: 16, r: 139, g: 92, b: 246, a: 0.06 },
    { lineW: 10, r: 168, g: 85, b: 247, a: 0.12 },
    { lineW: 6,  r: 192, g: 132, b: 252, a: 0.22 },
    { lineW: 3.5, r: 216, g: 180, b: 254, a: 0.35 },
  ];

  for (const gl of glowLayers) {
    canvasCtx.beginPath();
    canvasCtx.strokeStyle = `rgba(${gl.r}, ${gl.g}, ${gl.b}, ${gl.a})`;
    canvasCtx.lineWidth = gl.lineW;
    canvasCtx.lineCap = 'round';
    canvasCtx.lineJoin = 'round';
    drawSmoothCurve(points);
    canvasCtx.stroke();
  }

  // ── Main waveform line (gradient) ──
  canvasCtx.beginPath();
  const lineGrad = canvasCtx.createLinearGradient(0, 0, width, 0);
  lineGrad.addColorStop(0, '#7c3aed');
  lineGrad.addColorStop(0.25, '#a855f7');
  lineGrad.addColorStop(0.5, '#e879f9');
  lineGrad.addColorStop(0.75, '#a855f7');
  lineGrad.addColorStop(1, '#7c3aed');
  canvasCtx.strokeStyle = lineGrad;
  canvasCtx.lineWidth = 2.5;
  canvasCtx.lineCap = 'round';
  canvasCtx.lineJoin = 'round';
  drawSmoothCurve(points);
  canvasCtx.stroke();

  // ── Gradient fill above center ──
  canvasCtx.beginPath();
  drawSmoothCurve(points);
  canvasCtx.lineTo(width, centerY);
  canvasCtx.lineTo(0, centerY);
  canvasCtx.closePath();
  const fillUp = canvasCtx.createLinearGradient(0, centerY - height * 0.42, 0, centerY);
  fillUp.addColorStop(0, 'rgba(168, 85, 247, 0.18)');
  fillUp.addColorStop(1, 'rgba(168, 85, 247, 0)');
  canvasCtx.fillStyle = fillUp;
  canvasCtx.fill();

  // ── Gradient fill below center ──
  canvasCtx.beginPath();
  drawSmoothCurve(points);
  canvasCtx.lineTo(width, centerY);
  canvasCtx.lineTo(0, centerY);
  canvasCtx.closePath();
  const fillDown = canvasCtx.createLinearGradient(0, centerY, 0, centerY + height * 0.42);
  fillDown.addColorStop(0, 'rgba(168, 85, 247, 0)');
  fillDown.addColorStop(1, 'rgba(168, 85, 247, 0.18)');
  canvasCtx.fillStyle = fillDown;
  canvasCtx.fill();

  // ── Peak dots ──
  for (let i = 2; i < points.length - 2; i += 3) {
    const val = Math.abs(waveBuffer[i]);
    if (val > 0.25) {
      const brightness = Math.min(1, val * 2.5);
      const dotSize = 2 + val * 3;
      canvasCtx.beginPath();
      canvasCtx.arc(points[i].x, points[i].y, dotSize, 0, Math.PI * 2);
      canvasCtx.fillStyle = `rgba(232, 121, 249, ${brightness * 0.7})`;
      canvasCtx.fill();
    }
  }

  // ── Center reference line ──
  canvasCtx.strokeStyle = 'rgba(168, 85, 247, 0.15)';
  canvasCtx.lineWidth = 1;
  canvasCtx.setLineDash([4, 6]);
  canvasCtx.beginPath();
  canvasCtx.moveTo(0, centerY);
  canvasCtx.lineTo(width, centerY);
  canvasCtx.stroke();
  canvasCtx.setLineDash([]);

  // ── Edge vignette ──
  const vig = canvasCtx.createRadialGradient(
    width / 2, centerY, width * 0.28,
    width / 2, centerY, width * 0.55
  );
  vig.addColorStop(0, 'rgba(8, 4, 26, 0)');
  vig.addColorStop(1, 'rgba(8, 4, 26, 0.7)');
  canvasCtx.fillStyle = vig;
  canvasCtx.fillRect(0, 0, width, height);

  // ── Side fade ──
  const fadeLeft = canvasCtx.createLinearGradient(0, 0, width * 0.08, 0);
  fadeLeft.addColorStop(0, 'rgba(8, 4, 26, 0.9)');
  fadeLeft.addColorStop(1, 'rgba(8, 4, 26, 0)');
  canvasCtx.fillStyle = fadeLeft;
  canvasCtx.fillRect(0, 0, width * 0.08, height);

  const fadeRight = canvasCtx.createLinearGradient(width * 0.92, 0, width, 0);
  fadeRight.addColorStop(0, 'rgba(8, 4, 26, 0)');
  fadeRight.addColorStop(1, 'rgba(8, 4, 26, 0.9)');
  canvasCtx.fillStyle = fadeRight;
  canvasCtx.fillRect(width * 0.92, 0, width * 0.08, height);

  animationId = requestAnimationFrame(drawWaveform);
}

function drawSmoothCurve(points) {
  if (points.length < 2) return;
  canvasCtx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length - 1; i++) {
    const cpx = (points[i].x + points[i + 1].x) / 2;
    const cpy = (points[i].y + points[i + 1].y) / 2;
    canvasCtx.quadraticCurveTo(points[i].x, points[i].y, cpx, cpy);
  }
  const last = points[points.length - 1];
  canvasCtx.lineTo(last.x, last.y);
}
