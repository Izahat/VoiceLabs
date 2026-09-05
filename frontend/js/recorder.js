import { translate } from './language.js';
import { handleRefAudioFile } from './text-mode.js';
import { announce, byId, clearNotice, showNotice } from './ui.js';

function supportedMime() {
  return ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg'].find(type => window.MediaRecorder?.isTypeSupported?.(type)) || '';
}

function setupRecorder({
  buttonId,
  stopButtonId,
  timerId,
  waveformId,
  errorId,
  statusId,
  onRecorded,
  keys,
}) {
  const button = byId(buttonId);
  if (!button || button.dataset.recorderSetup === 'true') return;
  button.dataset.recorderSetup = 'true';

  const stopButton = byId(stopButtonId);
  const timerElement = byId(timerId);
  const statusElement = byId(statusId);
  let mediaRecorder = null;
  let stream = null;
  let chunks = [];
  let startedAt = 0;
  let timer = null;
  let preparing = false;
  let recording = false;
  let pointerHold = false;
  let audioContext = null;
  let analyser = null;
  let animationFrame = null;

  const setLabel = key => {
    const label = button.querySelector('.push-to-talk__text');
    if (label) label.textContent = translate(key);
  };

  const setStatus = key => {
    if (statusElement) statusElement.textContent = translate(key);
  };

  const setRecorderUi = state => {
    button.classList.toggle('recording', state === 'recording' || state === 'preparing');
    button.classList.toggle('preparing', state === 'preparing');
    button.setAttribute('aria-pressed', String(state === 'recording'));
    if (state === 'recording') {
      setLabel(keys.recording);
      stopButton?.classList.remove('hidden');
      timerElement?.classList.remove('hidden');
      setStatus(keys.recording);
    } else if (state === 'preparing') {
      setLabel(keys.preparing);
      stopButton?.classList.add('hidden');
      timerElement?.classList.add('hidden');
      setStatus(keys.preparing);
    } else {
      setLabel(keys.idle);
      stopButton?.classList.add('hidden');
      timerElement?.classList.add('hidden');
      if (timerElement) timerElement.textContent = '0:00';
    }
  };

  const updateTimer = () => {
    const elapsed = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
    if (timerElement) timerElement.textContent = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, '0')}`;
  };

  const stopWaveform = () => {
    if (animationFrame) cancelAnimationFrame(animationFrame);
    animationFrame = null;
    analyser = null;
    audioContext?.close().catch(() => {});
    audioContext = null;
    byId(waveformId)?.classList.remove('active');
  };

  const drawWaveform = () => {
    const canvas = byId(waveformId);
    if (!canvas || !analyser) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    const ctx = canvas.getContext('2d');
    const data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);
    const styles = getComputedStyle(document.documentElement);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = styles.getPropertyValue('--color-accent').trim() || '#a994ff';
    ctx.globalAlpha = 0.9;
    ctx.lineWidth = Math.max(1, ratio * 1.6);
    ctx.lineCap = 'round';
    ctx.beginPath();
    data.forEach((value, index) => {
      const x = (index / (data.length - 1)) * canvas.width;
      const y = canvas.height / 2 + ((value - 128) / 128) * canvas.height * 0.35;
      if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.globalAlpha = 1;
    animationFrame = requestAnimationFrame(drawWaveform);
  };

  const startWaveform = mediaStream => {
    const canvas = byId(waveformId);
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!canvas || !AudioContextClass) return;
    audioContext = new AudioContextClass();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.78;
    audioContext.createMediaStreamSource(mediaStream).connect(analyser);
    canvas.classList.add('active');
    drawWaveform();
  };

  const finishRecording = () => {
    const type = mediaRecorder?.mimeType || 'audio/webm';
    const blob = new Blob(chunks, { type });
    stream?.getTracks().forEach(track => track.stop());
    stream = null;
    mediaRecorder = null;
    stopWaveform();
    if (blob.size) {
      const extension = type.includes('ogg') ? 'ogg' : 'webm';
      const file = new File([blob], `recording_${Date.now()}.${extension}`, { type });
      onRecorded?.(file);
      setStatus(keys.recorded);
      announce(translate(keys.recorded));
    }
  };

  const startRecording = async () => {
    if (recording || preparing || !navigator.mediaDevices?.getUserMedia) return;
    preparing = true;
    setRecorderUi('preparing');
    clearNotice(errorId);
    announce(translate(keys.preparing));
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = supportedMime();
      mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      chunks = [];
      mediaRecorder.addEventListener('dataavailable', event => { if (event.data.size) chunks.push(event.data); });
      mediaRecorder.addEventListener('stop', finishRecording, { once: true });
      mediaRecorder.start(100);
      startWaveform(stream);
      preparing = false;
      recording = true;
      startedAt = Date.now();
      timer = window.setInterval(updateTimer, 250);
      setRecorderUi('recording');
      announce(translate(keys.recording));
    } catch (error) {
      preparing = false;
      recording = false;
      stream?.getTracks().forEach(track => track.stop());
      stream = null;
      setRecorderUi('idle');
      showNotice(errorId, translate(keys.denied));
      announce(error.message || translate(keys.denied));
    }
  };

  const stopRecording = () => {
    if (preparing) {
      preparing = false;
      stream?.getTracks().forEach(track => track.stop());
      stream = null;
      setRecorderUi('idle');
      return;
    }
    if (!recording || !mediaRecorder) return;
    recording = false;
    mediaRecorder.stop();
    if (timer) window.clearInterval(timer);
    timer = null;
    setRecorderUi('idle');
    stopWaveform();
  };

  setRecorderUi('idle');
  button.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    event.preventDefault();
    pointerHold = true;
    button.setPointerCapture?.(event.pointerId);
    startRecording();
  });
  button.addEventListener('pointerup', () => { if (pointerHold) { pointerHold = false; stopRecording(); } });
  button.addEventListener('pointercancel', () => { pointerHold = false; stopRecording(); });
  button.addEventListener('keydown', event => {
    if ((event.key === 'Enter' || event.key === ' ') && !event.repeat) {
      event.preventDefault();
      if (recording) stopRecording(); else startRecording();
    }
  });
  stopButton?.addEventListener('click', stopRecording);
  document.addEventListener('pointerup', () => { if (pointerHold) { pointerHold = false; stopRecording(); } });
  document.addEventListener('voicelabs:languagechange', () => { if (!recording && !preparing) setRecorderUi('idle'); });
}

export function setupRecordButton() {
  setupRecorder({
    buttonId: 'record-audio-btn', stopButtonId: 'stop-recording-btn', timerId: 'recording-timer',
    waveformId: 'waveform-canvas', errorId: 'recorder-error', statusId: 'recorder-status',
    onRecorded: handleRefAudioFile,
    keys: {
      idle: 'voiceCloning.holdToRecord', preparing: 'voiceCloning.preparingMicrophone',
      recording: 'voiceCloning.recording', recorded: 'voiceCloning.recorded', denied: 'voiceCloning.microphoneDenied',
    },
  });
}

export function setupTranscriptionRecorder(onRecorded) {
  setupRecorder({
    buttonId: 'transcribe-record-audio-btn', stopButtonId: 'transcribe-stop-recording-btn', timerId: 'transcribe-recording-timer',
    waveformId: 'transcribe-waveform-canvas', errorId: 'transcribe-recorder-error', statusId: 'transcribe-recorder-status',
    onRecorded,
    keys: {
      idle: 'transcription.holdToRecord', preparing: 'transcription.preparingMicrophone',
      recording: 'transcription.recording', recorded: 'transcription.recorded', denied: 'transcription.microphoneDenied',
    },
  });
}
