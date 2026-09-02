// Main app orchestrator — thin entry point
import { synthesizeVoiceDesign } from './api.js';
import { API_BASE } from './api.js';
import {
  getCurrentTheme, getCurrentLang,
  setPollInterval, getPollInterval
} from './state.js';
import { applyTheme, updateThemeIcon } from './theme.js';
import { applyLanguage } from './language.js';
import { setupTabs } from './tabs.js';
import { setupSettings } from './settings.js';
import { loadLanguages } from './languages.js';
import { setupRecordButton } from './recorder.js';
import {
  setupRefAudioDropzone,
  setupTextModeListeners, cloneVoiceAndSynthesize, resetTextMode
} from './text-mode.js';
import {
  showError, clearError,
} from './jobs.js';
import { setupTranscribeListeners } from './transcribe.js';

// ── Init ─────────────────────────────────────────────────────
async function init() {
  applyTheme(getCurrentTheme());
  applyLanguage(getCurrentLang());
  await loadLanguages();
  setupTabs();
  setupButtons();
  setupSettings();
  setupNewJob();
  setupVoiceDesignListeners();
  setupRefAudioDropzone();
  setupRecordButton();
  setupTextModeListeners();
  setupTranscribeListeners();
  updateThemeIcon();
}

// ── Voice Design ─────────────────────────────────────────────
function checkDesignReady() {
  const text = document.getElementById('vd-text')?.value?.trim();
  const lang = document.getElementById('vd-language')?.value;
  document.getElementById('start-dubbing-btn').disabled = !(text && lang);
}

function setupVoiceDesignListeners() {
  document.getElementById('vd-text')?.addEventListener('input', checkDesignReady);
  document.getElementById('vd-language')?.addEventListener('change', checkDesignReady);

  document.getElementById('vd-download-btn')?.addEventListener('click', () => {
    const audio = document.getElementById('vd-result-audio');
    if (audio?.src) {
      const a = document.createElement('a');
      a.href = audio.src;
      a.download = 'voice_design_audio.mp3';
      a.click();
    }
  });
}

async function startVoiceDesignJob() {
  const text = document.getElementById('vd-text').value.trim();
  const language = document.getElementById('vd-language').value;
  if (!text || !language) return;

  const voiceParams = {
    gender: document.getElementById('gender').value,
    age: document.getElementById('age').value,
    pitch: document.getElementById('pitch').value,
    style: document.getElementById('style').value,
    accent: document.getElementById('accent').value,
  };

  const btn = document.getElementById('start-dubbing-btn');
  btn.disabled = true;
  btn.querySelector('span:first-child').textContent = '⏳';
  clearError('design-error');

  try {
    const result = await synthesizeVoiceDesign({ text, language, voiceParams });
    const audioUrl = `${API_BASE.replace('/api/v1', '')}${result.audio_url}`;
    const audio = document.getElementById('vd-result-audio');
    audio.src = audioUrl;
    document.getElementById('vd-result-section').classList.remove('hidden');
  } catch (err) {
    showError('design-error', err.message);
  } finally {
    btn.disabled = false;
    btn.querySelector('span:first-child').textContent = '▶';
  }
}

// ── Buttons ─────────────────────────────────────────────────
function setupButtons() {
  document.getElementById('start-dubbing-btn').addEventListener('click', startVoiceDesignJob);
  document.getElementById('clone-voice-btn').addEventListener('click', cloneVoiceAndSynthesize);
  document.getElementById('download-audio-btn').addEventListener('click', () => {
    const audio = document.getElementById('result-audio');
    if (audio?.src) {
      const a = document.createElement('a');
      a.href = audio.src;
      a.download = 'cloned_audio.mp3';
      a.click();
    }
  });
  document.getElementById('clone-new-voice-btn').addEventListener('click', resetTextMode);
}

// ── New Job ─────────────────────────────────────────────────
function setupNewJob() {
  document.getElementById('new-job-btn').addEventListener('click', () => {
    const pi = getPollInterval();
    if (pi) clearInterval(pi);
    setPollInterval(null);
    document.getElementById('result-section')?.classList.add('hidden');
    document.getElementById('vd-result-section')?.classList.add('hidden');
    document.getElementById('ref-audio-file-info')?.classList.add('hidden');
    document.getElementById('ref-audio-input').value = '';
    document.getElementById('vd-text').value = '';
    document.getElementById('synthesize-text').value = '';
    document.getElementById('start-dubbing-btn').disabled = true;
    document.getElementById('clone-voice-btn').disabled = true;
    clearError('design-error');
    clearError('clone-voice-error');
  });
}

document.addEventListener('DOMContentLoaded', init);
