import { translations } from './i18n.js';
import { API_BASE, getUserHeaders } from './api.js';
import { getCurrentLang } from './state.js';
import { showError, clearError, showTextProgress, showAudioResult, hideProgress } from './jobs.js';

let _refAudioFile = null;

export function getRefAudioFile() { return _refAudioFile; }

export function setRefAudioFileLocal(file) { _refAudioFile = file; }

export function setupRefAudioDropzone() {
  const dropzone = document.getElementById('ref-audio-dropzone');
  const input = document.getElementById('ref-audio-input');

  if (!dropzone || dropzone.dataset.setup) return;
  dropzone.dataset.setup = 'true';

  dropzone.addEventListener('click', () => input.click());
  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) handleRefAudioFile(file);
  });
  input.addEventListener('change', () => {
    if (input.files[0]) handleRefAudioFile(input.files[0]);
  });

  document.getElementById('ref-audio-remove').addEventListener('click', (e) => {
    e.stopPropagation();
    _refAudioFile = null;
    document.getElementById('ref-audio-file-info').classList.add('hidden');
    document.getElementById('ref-audio-input').value = '';
    checkTextModeReady();
  });
}

export function handleRefAudioFile(file) {
  if (file.size > 500 * 1024 * 1024) {
    alert('File too large. Max 500MB');
    return;
  }
  _refAudioFile = file;
  const sizeStr = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
  document.getElementById('ref-audio-filename').textContent = file.name;
  document.getElementById('ref-audio-filesize').textContent = sizeStr;
  document.getElementById('ref-audio-file-info').classList.remove('hidden');
  checkTextModeReady();
}

export function checkTextModeReady() {
  const text = document.getElementById('synthesize-text')?.value?.trim();
  const lang = document.getElementById('text-language')?.value;
  document.getElementById('clone-voice-btn').disabled = !(_refAudioFile && text && lang);
}

export function setupTextModeListeners() {
  document.getElementById('synthesize-text')?.addEventListener('input', checkTextModeReady);
  document.getElementById('text-language')?.addEventListener('change', checkTextModeReady);
}

export async function cloneVoiceAndSynthesize() {
  const text = document.getElementById('synthesize-text').value.trim();
  const language = document.getElementById('text-language').value;
  if (!_refAudioFile || !text || !language) return;

  const t = translations[getCurrentLang()] || translations.en;
  showTextProgress(t.voiceCloning?.voiceCloned || 'Cloning voice...');
  clearError('clone-voice-error');

  try {
    const result = await cloneVoice(_refAudioFile);
    const audioUrl = await synthesizeWithClone(text, result.voice_id || result.id, language);
    hideProgress();
    showAudioResult(audioUrl);
  } catch (err) {
    hideProgress();
    showError('clone-voice-error', err.message);
  }
}

async function cloneVoice(audioFile) {
  const form = new FormData();
  form.append('reference_audio', audioFile);
  form.append('mode', 'clone');

  const res = await fetch(`${API_BASE}/dubbing/tts/clone`, {
    method: 'POST',
    headers: getUserHeaders(),
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function synthesizeWithClone(text, voiceId, language) {
  const res = await fetch(`${API_BASE}/dubbing/tts/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getUserHeaders() },
    body: JSON.stringify({ text, voice_id: voiceId, language }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  const data = await res.json();
  return data.audio_url || data.url;
}

export function resetTextMode() {
  _refAudioFile = null;
  document.getElementById('ref-audio-file-info').classList.add('hidden');
  document.getElementById('ref-audio-input').value = '';
  document.getElementById('synthesize-text').value = '';
  document.getElementById('audio-result-section').classList.add('hidden');
  document.getElementById('clone-voice-btn').disabled = true;
  clearError('clone-voice-error');
}
