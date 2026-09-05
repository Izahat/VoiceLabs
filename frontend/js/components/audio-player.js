import { formatDuration } from '../ui.js';
import { translate } from '../language.js';

const players = new Map();

function palette() {
  const styles = getComputedStyle(document.documentElement);
  return {
    accent: styles.getPropertyValue('--color-accent').trim() || '#a994ff',
    muted: styles.getPropertyValue('--color-border-strong').trim() || '#3a4552',
    background: styles.getPropertyValue('--color-bg-subtle').trim() || '#101318',
  };
}

function resizeCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(1, Math.floor(rect.width * ratio));
  // canvas.height is the pixel buffer and changes every time we draw at high
  // DPI. Store a separate immutable logical height to prevent a feedback
  // loop that would make the waveform grow after playback starts.
  const defaultHeight = canvas.classList.contains('waveform--result') ? 220
    : canvas.classList.contains('waveform--reference') ? 150
      : canvas.classList.contains('waveform--empty') ? 96
        : Number(canvas.getAttribute('height')) || 120;
  const storedHeight = Number(canvas.dataset.waveformHeight);
  const logicalHeight = Number.isFinite(storedHeight) && storedHeight > 0
    ? storedHeight
    : defaultHeight;
  canvas.dataset.waveformHeight = String(logicalHeight);
  const height = Math.max(1, Math.floor(logicalHeight * ratio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  return { width, height, ratio };
}

export function drawWaveform(canvas, samples = null, { empty = false, progress = null, isPlaying = false } = {}) {
  if (!canvas) return;
  if (samples) canvas._waveSamples = samples;
  const data = canvas._waveSamples;
  const { width, height, ratio } = resizeCanvas(canvas);
  const ctx = canvas.getContext('2d');
  const colors = palette();
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = colors.background;
  if (!empty) ctx.fillRect(0, 0, width, height);

  const barCount = Math.max(48, Math.floor(width / (6 * ratio)));
  const gap = Math.max(2 * ratio, width / barCount * 0.34);
  const barWidth = Math.max(1 * ratio, width / barCount - gap);
  const center = height / 2;
  const playbackProgress = Number.isFinite(progress) ? Math.min(1, Math.max(0, progress)) : null;
  const now = performance.now() / 1000;

  for (let index = 0; index < barCount; index += 1) {
    const progress = index / Math.max(1, barCount - 1);
    const played = playbackProgress !== null && progress <= playbackProgress;
    let amplitude;
    if (data?.length) {
      const sampleIndex = Math.min(data.length - 1, Math.floor(progress * data.length));
      amplitude = Math.max(0.035, Math.abs(data[sampleIndex]));
    } else {
      amplitude = 0.08 + Math.abs(Math.sin(index * 0.77) * Math.cos(index * 0.21)) * (empty ? 0.18 : 0.55);
    }
    const pulse = isPlaying && played ? 0.82 + Math.sin(now * 9 + index * 0.57) * 0.16 : 1;
    const barHeight = Math.max(2 * ratio, amplitude * height * 0.82 * pulse);
    const x = index * (barWidth + gap);
    ctx.fillStyle = empty ? colors.muted : (played ? colors.accent : colors.muted);
    ctx.globalAlpha = empty ? 0.45 : (played ? 0.98 : 0.52);
    ctx.beginPath();
    ctx.roundRect(x, center - barHeight / 2, barWidth, barHeight, barWidth / 2);
    ctx.fill();
  }

  if (playbackProgress !== null && !empty) {
    const headX = Math.min(width - ratio, Math.max(0, playbackProgress * width));
    ctx.fillStyle = colors.accent;
    ctx.globalAlpha = isPlaying ? 0.95 : 0.7;
    ctx.fillRect(headX, height * 0.18, Math.max(ratio, 1), height * 0.64);
  }
  ctx.globalAlpha = 1;
}

function summarizeBuffer(buffer, count = 240) {
  const channel = buffer.getChannelData(0);
  const block = Math.max(1, Math.floor(channel.length / count));
  const samples = new Float32Array(count);
  for (let index = 0; index < count; index += 1) {
    let sum = 0;
    const start = index * block;
    for (let offset = 0; offset < block && start + offset < channel.length; offset += 1) {
      sum += Math.abs(channel[start + offset]);
    }
    samples[index] = Math.min(1, (sum / block) * 2.4);
  }
  return samples;
}

async function decodeArrayBuffer(buffer) {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) throw new Error('Web Audio is unavailable');
  const context = new AudioContextClass();
  try {
    return await context.decodeAudioData(buffer.slice(0));
  } finally {
    await context.close().catch(() => {});
  }
}

export async function drawFileWaveform(canvasId, file) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  try {
    const buffer = await file.arrayBuffer();
    const decoded = await decodeArrayBuffer(buffer);
    drawWaveform(canvas, summarizeBuffer(decoded));
  } catch {
    drawWaveform(canvas);
  }
}

export function drawPlaceholderWaveforms() {
  document.querySelectorAll('.waveform--empty').forEach(canvas => drawWaveform(canvas, null, { empty: true }));
}

async function drawRemoteWaveform(canvas, url) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Unable to load waveform');
    const decoded = await decodeArrayBuffer(await response.arrayBuffer());
    drawWaveform(canvas, summarizeBuffer(decoded));
  } catch {
    drawWaveform(canvas);
  }
}

function setupPlayer(root) {
  const audioId = root.dataset.audioPlayer;
  const audio = document.getElementById(audioId);
  if (!audio || players.has(audioId)) return;
  const canvas = document.getElementById(root.dataset.waveform);
  const play = root.querySelector('[data-player-action="play"]');
  const seek = root.querySelector('[data-player-action="seek"]');
  const volume = root.querySelector('[data-player-action="volume"]');
  const mute = root.querySelector('[data-player-action="mute"]');
  const elapsed = root.querySelector('[data-player-elapsed]');
  const duration = root.querySelector('[data-player-duration]');
  const playIcon = root.querySelector('[data-player-icon]');
  const volumeIcon = root.querySelector('[data-volume-icon]');

  const updateMuteLabel = () => {
    mute?.setAttribute('aria-label', translate(audio.muted ? 'a11y.unmuteAudio' : 'a11y.muteAudio'));
  };

  updateMuteLabel();

  const player = { root, audio, canvas, update: null, animationFrame: null };

  const renderWaveform = () => {
    if (!canvas) return;
    const total = Number.isFinite(audio.duration) ? audio.duration : 0;
    const progress = total ? audio.currentTime / total : 0;
    drawWaveform(canvas, canvas._waveSamples, { progress, isPlaying: !audio.paused });
  };

  const stopWaveformAnimation = () => {
    if (player.animationFrame) cancelAnimationFrame(player.animationFrame);
    player.animationFrame = null;
  };

  const animateWaveform = () => {
    renderWaveform();
    if (!audio.paused && !audio.ended) {
      player.animationFrame = requestAnimationFrame(animateWaveform);
    } else {
      player.animationFrame = null;
    }
  };

  const startWaveformAnimation = () => {
    stopWaveformAnimation();
    animateWaveform();
  };

  const update = () => {
    const total = Number.isFinite(audio.duration) ? audio.duration : 0;
    elapsed.textContent = formatDuration(audio.currentTime, '0:00');
    duration.textContent = total ? formatDuration(total) : '—:—';
    seek.value = total ? String((audio.currentTime / total) * 100) : '0';
  };
  player.update = update;

  play.addEventListener('click', async () => {
    if (!audio.src) return;
    if (audio.paused) await audio.play(); else audio.pause();
  });
  seek.addEventListener('input', () => {
    if (Number.isFinite(audio.duration)) audio.currentTime = (Number(seek.value) / 100) * audio.duration;
  });
  volume.addEventListener('input', () => {
    audio.volume = Number(volume.value);
    audio.muted = audio.volume === 0;
    volumeIcon.setAttribute('href', `assets/lucide-sprite.svg#${audio.muted ? 'volume-x' : 'volume-2'}`);
    updateMuteLabel();
  });
  mute.addEventListener('click', () => {
    audio.muted = !audio.muted;
    volumeIcon.setAttribute('href', `assets/lucide-sprite.svg#${audio.muted ? 'volume-x' : 'volume-2'}`);
    updateMuteLabel();
  });
  canvas?.addEventListener('click', event => {
    if (!Number.isFinite(audio.duration)) return;
    const rect = canvas.getBoundingClientRect();
    audio.currentTime = ((event.clientX - rect.left) / rect.width) * audio.duration;
  });
  audio.addEventListener('play', () => {
    playIcon.setAttribute('href', 'assets/lucide-sprite.svg#pause');
    play.setAttribute('aria-label', translate('a11y.pauseAudio'));
    startWaveformAnimation();
  });
  audio.addEventListener('pause', () => {
    playIcon.setAttribute('href', 'assets/lucide-sprite.svg#play');
    play.setAttribute('aria-label', translate('a11y.playAudio'));
    stopWaveformAnimation();
    renderWaveform();
  });
  audio.addEventListener('timeupdate', () => {
    update();
    if (audio.paused) renderWaveform();
  });
  audio.addEventListener('loadedmetadata', () => {
    update();
    renderWaveform();
  });
  audio.addEventListener('ended', () => {
    update();
    renderWaveform();
  });
  players.set(audioId, player);
}

export function setupAudioPlayers() {
  document.querySelectorAll('[data-audio-player]').forEach(setupPlayer);
  drawPlaceholderWaveforms();
  window.addEventListener('resize', () => {
    document.querySelectorAll('canvas.waveform').forEach(canvas => drawWaveform(canvas, canvas._waveSamples, { empty: canvas.classList.contains('waveform--empty') }));
  }, { passive: true });
  document.addEventListener('voicelabs:themechange', () => {
    document.querySelectorAll('canvas.waveform').forEach(canvas => drawWaveform(canvas, canvas._waveSamples, { empty: canvas.classList.contains('waveform--empty') }));
  });
  document.addEventListener('voicelabs:languagechange', () => {
    players.forEach(({ root, audio }) => {
      root.querySelector('[data-player-action="play"]')?.setAttribute('aria-label', translate(audio.paused ? 'a11y.playAudio' : 'a11y.pauseAudio'));
      root.querySelector('[data-player-action="mute"]')?.setAttribute('aria-label', translate(audio.muted ? 'a11y.unmuteAudio' : 'a11y.muteAudio'));
    });
  });
}

export async function loadAudioPlayer(audioId, url) {
  const player = players.get(audioId);
  const audio = player?.audio || document.getElementById(audioId);
  if (!audio) return;
  audio.pause();
  audio.src = url;
  audio.load();
  player?.update();
  if (player?.canvas) await drawRemoteWaveform(player.canvas, url);
}

export function resetAudioPlayer(audioId) {
  const player = players.get(audioId);
  const audio = player?.audio || document.getElementById(audioId);
  if (!audio) return;
  audio.pause();
  audio.removeAttribute('src');
  audio.load();
  if (player?.canvas) {
    delete player.canvas._waveSamples;
    drawWaveform(player.canvas);
  }
  player?.update();
}
