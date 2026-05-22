import { translations } from './i18n.js';
import { getCurrentLang, setPollInterval } from './state.js';

export function showProgress(type) {
  const section = document.getElementById('progress-section');
  const title = document.getElementById('progress-title');
  const t = translations[getCurrentLang()] || translations.en;
  title.textContent = type === 'clone' ? (t.processingCloning || t.processing) : t.processing;
  section.classList.remove('hidden');
  document.getElementById('progress-bar').style.width = '0%';
  document.getElementById('progress-text').textContent = 'Starting...';
  document.querySelectorAll('.step').forEach(s => s.classList.remove('active', 'done'));
}

export function hideProgress() {
  document.getElementById('progress-section').classList.add('hidden');
}

export function updateProgress(step, pct, text) {
  document.getElementById('progress-bar').style.width = pct + '%';
  document.getElementById('progress-text').textContent = text;
  const steps = ['extract', 'transcribe', 'translate', 'synthesize', 'merge'];
  const idx = steps.indexOf(step);
  steps.forEach((s, i) => {
    const el = document.querySelector(`.step[data-step="${s}"]`);
    el.classList.remove('active', 'done');
    if (i < idx) el.classList.add('done');
    if (i === idx) el.classList.add('active');
  });
}

export function showResult(videoUrl) {
  hideProgress();
  const section = document.getElementById('result-section');
  section.classList.remove('hidden');
  const video = document.getElementById('result-video');
  video.src = videoUrl;
  video.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

export function showError(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.classList.remove('hidden');
}

export function clearError(id) {
  document.getElementById(id).classList.add('hidden');
}

export function startPolling(id, type) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/v1/dubbing/status/${id}`);
      const data = await res.json();
      const step = data.step || data.status;
      const pctMap = { extract: 20, transcribe: 40, translate: 60, synthesize: 80, merge: 95 };
      updateProgress(step, pctMap[step] || 0, `Step: ${step}...`);

      if (data.status === 'completed' || data.state === 'completed') {
        clearInterval(interval);
        setPollInterval(null);
        updateProgress('merge', 100, 'Done!');
        setTimeout(() => showResult(data.video_url || data.output_url || `/api/v1/dubbing/output/${id}`), 500);
      } else if (data.status === 'failed' || data.state === 'failed') {
        clearInterval(interval);
        setPollInterval(null);
        hideProgress();
        showError(type === 'clone' ? 'clone-error' : 'design-error', data.error || 'Job failed');
      }
    } catch (err) {
      console.error('Poll error:', err);
    }
  }, 3000);
  setPollInterval(interval);
}

export function showTextProgress(text) {
  const section = document.getElementById('progress-section');
  document.getElementById('progress-title').textContent = text;
  section.classList.remove('hidden');
  document.getElementById('progress-bar').style.width = '30%';
  document.getElementById('progress-text').textContent = text;
}

export function showAudioResult(audioUrl) {
  hideProgress();
  const section = document.getElementById('audio-result-section');
  section.classList.remove('hidden');
  const audio = document.getElementById('result-audio');
  audio.src = audioUrl + '?t=' + Date.now();
  audio.load();
  audio.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

export function downloadResult() {
  const src = document.getElementById('result-video').src;
  if (!src) return;
  const a = document.createElement('a');
  a.href = src;
  a.download = 'dubbed-video.mp4';
  a.click();
}

export function downloadAudioResult() {
  const src = document.getElementById('result-audio').src;
  if (!src) return;
  const a = document.createElement('a');
  a.href = src;
  a.download = 'cloned-voice-audio.mp3';
  a.click();
}
