/**
 * Transcription Tab — handles file upload, URL input, and transcription display.
 */
import { API_BASE, getUserHeaders } from './api.js';
import { showError, clearError } from './jobs.js';

let transcribeFile = null;
let transcribeBarInterval = null;

// ── Init ──────────────────────────────────────────────────────────────────

export function setupTranscribeListeners() {
  setupDropzone();
  setupURLInput();
  setupButtons();
}

function setupDropzone() {
  const dropzone = document.getElementById('transcribe-dropzone');
  const fileInput = document.getElementById('transcribe-file-input');
  const fileInfo = document.getElementById('transcribe-file-info');
  const filename = document.getElementById('transcribe-filename');
  const filesize = document.getElementById('transcribe-filesize');
  const removeBtn = document.getElementById('transcribe-remove');

  if (!dropzone) return;

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dropzone--drag');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dropzone--drag');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dropzone--drag');
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFileSelect(fileInput.files[0]);
  });

  removeBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    clearTranscribeFile();
  });

  function handleFileSelect(file) {
    // Only audio/video
    if (!file.type.startsWith('audio/') && !file.type.startsWith('video/')) {
      showError('transcribe-error', 'Please select an audio or video file');
      return;
    }

    transcribeFile = file;
    filename.textContent = file.name;
    filesize.textContent = formatFileSize(file.size);
    fileInfo.classList.remove('hidden');
    dropzone.classList.add('hidden');

    checkTranscribeReady();
    clearError('transcribe-error');
  }
}

function setupURLInput() {
  const urlInput = document.getElementById('transcribe-url');
  const fileInput = document.getElementById('transcribe-file-input');

  urlInput?.addEventListener('input', () => {
    // Clear file if URL is typed
    if (urlInput.value.trim()) {
      clearTranscribeFile();
    }
    checkTranscribeReady();
  });
}

function setupButtons() {
  const startBtn = document.getElementById('start-transcribe-btn');
  const copyBtn = document.getElementById('transcribe-copy-btn');
  const newBtn = document.getElementById('transcribe-new-btn');

  startBtn?.addEventListener('click', startTranscription);
  copyBtn?.addEventListener('click', copyTranscription);
  newBtn?.addEventListener('click', resetTranscribe);
}

function checkTranscribeReady() {
  const url = document.getElementById('transcribe-url')?.value?.trim();
  const startBtn = document.getElementById('start-transcribe-btn');
  startBtn.disabled = !transcribeFile && !url;
}

// ── Transcription ─────────────────────────────────────────────────────────

async function startTranscription() {
  clearError('transcribe-error');
  showTranscribeProgress();

  const url = document.getElementById('transcribe-url')?.value?.trim();
  const language = document.getElementById('transcribe-language')?.value || null;
  // The API keeps this field for forward compatibility, but diarization is
  // intentionally disabled until a production model is selected.
  const enableDiarization = false;

  try {
    let result;

    if (url) {
      // URL transcription
      const formData = new FormData();
      formData.append('url', url);
      if (language) formData.append('language', language);
      formData.append('enable_diarization', String(enableDiarization));

      const res = await fetch(`${API_BASE}/transcription/transcribe/url`, {
        method: 'POST',
        headers: getUserHeaders(),
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      result = await res.json();
    } else if (transcribeFile) {
      // File transcription
      const formData = new FormData();
      formData.append('file', transcribeFile);
      if (language) formData.append('language', language);
      formData.append('enable_diarization', String(enableDiarization));

      const res = await fetch(`${API_BASE}/transcription/transcribe`, {
        method: 'POST',
        headers: getUserHeaders(),
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      result = await res.json();
    } else {
      throw new Error('Please upload a file or enter a URL');
    }

    hideTranscribeProgress();
    showTranscribeResult(result);

  } catch (err) {
    hideTranscribeProgress();
    showError('transcribe-error', err.message);
  }
}

// ── UI Updates ─────────────────────────────────────────────────────────────

function showTranscribeProgress() {
  document.getElementById('transcribe-progress')?.classList.remove('hidden');
  document.getElementById('transcribe-result')?.classList.add('hidden');
  document.getElementById('start-transcribe-btn').disabled = true;

  // Animate progress bar
  let progress = 0;
  const status = document.getElementById('transcribe-status');
  transcribeBarInterval = setInterval(() => {
    progress += 5;
    if (progress > 90) progress = 90;
    document.getElementById('transcribe-bar').style.width = `${progress}%`;
    if (progress < 30) status.textContent = 'Extracting audio...';
    else if (progress < 60) status.textContent = 'Transcribing...';
    else if (progress < 90) status.textContent = 'Analyzing speakers...';
  }, 500);
}

function hideTranscribeProgress() {
  clearInterval(transcribeBarInterval);
  document.getElementById('transcribe-progress')?.classList.add('hidden');
  document.getElementById('transcribe-bar').style.width = '0%';
  document.getElementById('start-transcribe-btn').disabled = false;
}

function showTranscribeResult(result) {
  const resultSection = document.getElementById('transcribe-result');
  const languageBadge = document.getElementById('transcribe-language-badge');
  const durationEl = document.getElementById('transcribe-duration');
  const speakersCount = document.getElementById('transcribe-speakers-count');
  const fullTextEl = document.getElementById('transcribe-text');
  const segmentsEl = document.getElementById('transcribe-segments');

  // Info
  languageBadge.textContent = (result.language || 'EN').toUpperCase();
  if (result.duration) {
    durationEl.textContent = formatDuration(result.duration);
  }

  // Speakers count
  if (result.speakers && result.speakers.length > 0) {
    const uniqueSpeakers = new Set(result.speakers.map(s => s.speaker));
    speakersCount.textContent = `${uniqueSpeakers.size} speaker(s)`;
    speakersCount.classList.remove('hidden');
  } else {
    speakersCount.classList.add('hidden');
  }

  // Full text
  fullTextEl.textContent = result.full_text || '';

  // Segments with speakers
  segmentsEl.innerHTML = '';
  const segments = result.segments || [];
  const speakerColors = getSpeakerColors();

  for (const seg of segments) {
    const div = document.createElement('div');
    div.className = 'segment-item';

    const speaker = seg.speaker || 'UNKNOWN';
    const colorIndex = parseInt(speaker.replace(/\D/g, '') || '0');

    div.innerHTML = `
      <div class="segment-header">
        <span class="segment-speaker" style="background: ${speakerColors[colorIndex % speakerColors.length]}">
          ${speaker}
        </span>
        <span class="segment-time">${formatTime(seg.start)} - ${formatTime(seg.end)}</span>
      </div>
      <p class="segment-text">${escapeHtml(seg.text)}</p>
    `;
    segmentsEl.appendChild(div);
  }

  resultSection.classList.remove('hidden');

  // Complete progress
  document.getElementById('transcribe-bar').style.width = '100%';
  document.getElementById('transcribe-status').textContent = 'Complete!';
  setTimeout(() => {
    document.getElementById('transcribe-progress')?.classList.add('hidden');
  }, 1000);
}

function copyTranscription() {
  const text = document.getElementById('transcribe-text')?.textContent;
  if (text) {
    navigator.clipboard.writeText(text);
    // Brief visual feedback
    const btn = document.getElementById('transcribe-copy-btn');
    const original = btn.innerHTML;
    btn.innerHTML = '<span>✓</span><span>Copied!</span>';
    setTimeout(() => { btn.innerHTML = original; }, 1500);
  }
}

function resetTranscribe() {
  clearTranscribeFile();
  document.getElementById('transcribe-url').value = '';
  document.getElementById('transcribe-result')?.classList.add('hidden');
  clearError('transcribe-error');
  checkTranscribeReady();
}

function clearTranscribeFile() {
  transcribeFile = null;
  document.getElementById('transcribe-file-input').value = '';
  document.getElementById('transcribe-file-info')?.classList.add('hidden');
  document.getElementById('transcribe-dropzone')?.classList.remove('hidden');
}

// ── Helpers ────────────────────────────────────────────────────────────────

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}m ${secs}s`;
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function getSpeakerColors() {
  return [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
    '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
    '#BB8FCE', '#85C1E9'
  ];
}
