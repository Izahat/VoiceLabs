import { transcribeUpload, transcribeUrl } from './api.js';
import { translate } from './language.js';
import { setupFileDropzone } from './components/dropzone.js';
import { loadAudioPlayer, resetAudioPlayer } from './components/audio-player.js?v=3';
import { announce, byId, clearNotice, formatBytes, formatDuration, getMediaDuration, setButtonBusy, setReadyState, showNotice, showOnly, showToast } from './ui.js';

let sourceFile = null;
let sourceDuration = null;
let sourceMode = 'file';
let lastSource = null;
let sourcePreviewUrl = null;

const resultIds = ['transcribe-empty', 'transcribe-progress', 'transcribe-preview-error', 'transcribe-result'];

function validMedia(file) {
  const extension = file.name.split('.').pop()?.toLowerCase();
  return file.type.startsWith('audio/') || file.type.startsWith('video/') || ['wav', 'mp3', 'm4a', 'ogg', 'webm', 'mp4', 'mov', 'avi', 'mkv'].includes(extension);
}

function activeSource() {
  return sourceMode === 'file' ? sourceFile : byId('transcribe-url')?.value.trim();
}

function checkReady() {
  setReadyState(byId('start-transcribe-btn'), Boolean(activeSource()));
}

function showPreview(id) {
  showOnly(resultIds, id);
}

function updateFileMeta() {
  if (!sourceFile) return;
  byId('transcribe-filesize').textContent = formatBytes(sourceFile.size);
  byId('transcribe-fileduration').textContent = sourceDuration ? ` · ${formatDuration(sourceDuration)}` : '';
}

function setMode(mode) {
  sourceMode = mode;
  const fileActive = mode === 'file';
  byId('transcribe-mode-file').classList.toggle('active', fileActive);
  byId('transcribe-mode-url').classList.toggle('active', !fileActive);
  byId('transcribe-mode-file').setAttribute('aria-selected', String(fileActive));
  byId('transcribe-mode-url').setAttribute('aria-selected', String(!fileActive));
  byId('transcribe-file-panel').classList.toggle('hidden', !fileActive);
  byId('transcribe-url-panel').classList.toggle('hidden', fileActive);
  checkReady();
}

function handleFile(file) {
  if (!file) return;
  if (file.size > 500 * 1024 * 1024) {
    showNotice('transcribe-error', translate('errors.fileTooLarge'));
    return;
  }
  if (!validMedia(file)) {
    showNotice('transcribe-error', translate('errors.invalidMedia'));
    return;
  }
  sourceFile = file;
  sourceDuration = null;
  if (sourcePreviewUrl) URL.revokeObjectURL(sourcePreviewUrl);
  sourcePreviewUrl = URL.createObjectURL(file);
  loadAudioPlayer('transcribe-audio-preview', sourcePreviewUrl);
  byId('transcribe-filename').textContent = file.name;
  byId('transcribe-filesize').textContent = formatBytes(file.size);
  byId('transcribe-fileduration').textContent = '';
  byId('transcribe-file-icon-use')?.setAttribute('href', `assets/lucide-sprite.svg#${file.type.startsWith('video/') ? 'file-video' : 'file-audio'}`);
  byId('transcribe-dropzone').classList.add('hidden');
  byId('transcribe-file-info').classList.remove('hidden');
  clearNotice('transcribe-error');
  setMode('file');
  getMediaDuration(file).then(duration => {
    if (sourceFile !== file) return;
    sourceDuration = duration;
    updateFileMeta();
  });
  checkReady();
  announce(translate('status.referenceSelected'));
}

function clearFile() {
  sourceFile = null;
  sourceDuration = null;
  if (sourcePreviewUrl) URL.revokeObjectURL(sourcePreviewUrl);
  sourcePreviewUrl = null;
  byId('transcribe-file-input').value = '';
  byId('transcribe-file-info').classList.add('hidden');
  byId('transcribe-dropzone').classList.remove('hidden');
  resetAudioPlayer('transcribe-audio-preview');
  checkReady();
}

export function handleTranscriptionFile(file) {
  handleFile(file);
}

function validUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch { return false; }
}

export function setupTranscribeListeners() {
  setupFileDropzone({
    dropzone: byId('transcribe-dropzone'), input: byId('transcribe-file-input'),
    maxSize: 500 * 1024 * 1024, validate: file => validMedia(file) ? '' : translate('errors.invalidMedia'),
    onFile: handleFile, onError: message => showNotice('transcribe-error', message),
  });
  byId('transcribe-mode-file')?.addEventListener('click', () => setMode('file'));
  byId('transcribe-mode-url')?.addEventListener('click', () => setMode('url'));
  byId('transcribe-replace')?.addEventListener('click', () => byId('transcribe-file-input').click());
  byId('transcribe-remove')?.addEventListener('click', clearFile);
  byId('transcribe-url')?.addEventListener('input', () => {
    clearNotice('transcribe-error');
    checkReady();
  });
  byId('start-transcribe-btn')?.addEventListener('click', startTranscription);
  byId('transcribe-retry-btn')?.addEventListener('click', startTranscription);
  byId('transcribe-preview-retry-btn')?.addEventListener('click', startTranscription);
  byId('transcribe-copy-btn')?.addEventListener('click', copyTranscription);
  byId('transcribe-new-btn')?.addEventListener('click', resetTranscription);
  setMode('file');
}

async function startTranscription() {
  const source = activeSource();
  if (!source) return;
  if (sourceMode === 'url' && !validUrl(source)) {
    showNotice('transcribe-error', translate('errors.invalidUrl'));
    return;
  }
  lastSource = source;
  clearNotice('transcribe-error');
  setButtonBusy(byId('start-transcribe-btn'), true, { busyText: translate('transcription.starting') });
  showPreview('transcribe-progress');
  byId('transcribe-status').textContent = sourceMode === 'url' ? translate('transcription.processingUrlDescription') : translate('transcription.processingDescription');
  announce(translate('transcription.processingTitle'));
  try {
    const language = byId('transcribe-language').value || null;
    const result = sourceMode === 'url' ? await transcribeUrl({ url: source, language }) : await transcribeUpload({ file: source, language });
    showResult(result);
    document.dispatchEvent(new CustomEvent('voicelabs:datachange'));
  } catch (error) {
    byId('transcribe-preview-error-message').textContent = error.message;
    showNotice('transcribe-error', error.message);
    showPreview('transcribe-preview-error');
    announce(error.message);
  } finally {
    setButtonBusy(byId('start-transcribe-btn'), false, { idleText: translate('transcription.start') });
    checkReady();
  }
}

function showResult(result) {
  byId('transcribe-language-badge').textContent = (result.language || byId('transcribe-language').value || '—').toUpperCase();
  byId('transcribe-duration').textContent = formatDuration(Number(result.duration));
  byId('transcribe-source-name').textContent = sourceMode === 'file' ? sourceFile?.name || '—' : (() => { try { return new URL(lastSource).hostname; } catch { return lastSource || '—'; } })();
  byId('transcribe-speakers-count').classList.add('hidden');
  byId('transcribe-text').textContent = result.full_text || result.text || '';
  const segments = Array.isArray(result.segments) ? result.segments : [];
  byId('transcribe-segments').replaceChildren(...segments.map(segment => {
    const item = document.createElement('article');
    item.className = 'segment-item';
    const time = document.createElement('time');
    time.className = 'segment-time';
    time.textContent = `${formatTimestamp(segment.start)} – ${formatTimestamp(segment.end)}`;
    const text = document.createElement('p');
    text.className = 'segment-text';
    text.textContent = segment.text || '';
    item.append(time, text);
    return item;
  }));
  clearNotice('transcribe-error');
  byId('transcribe-copy-feedback').classList.add('hidden');
  showPreview('transcribe-result');
  announce(translate('status.transcriptionComplete'));
}

function formatTimestamp(seconds) {
  if (!Number.isFinite(Number(seconds))) return '—:—';
  const total = Math.max(0, Math.floor(Number(seconds)));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}

async function copyTranscription() {
  const text = byId('transcribe-text').textContent.trim();
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const range = document.createRange();
    range.selectNodeContents(byId('transcribe-text'));
    const selection = window.getSelection();
    selection.removeAllRanges(); selection.addRange(range);
    document.execCommand('copy'); selection.removeAllRanges();
  }
  byId('transcribe-copy-feedback').classList.remove('hidden');
  showToast(translate('transcription.copied'));
}

function resetTranscription() {
  clearFile();
  byId('transcribe-url').value = '';
  byId('transcribe-language').value = '';
  clearNotice('transcribe-error');
  showPreview('transcribe-empty');
  setMode('file');
  checkReady();
}
