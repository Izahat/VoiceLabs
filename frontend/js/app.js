import { checkApiHealth, downloadAsset, resolveApiUrl, synthesizeVoiceDesign } from './api.js';
import { getCurrentLang, getCurrentTheme } from './state.js';
import { applyTheme, setupSystemThemeListener } from './theme.js';
import { applyLanguage, translate } from './language.js';
import { setupTabs } from './tabs.js';
import { setupSettings } from './settings.js';
import { loadLanguages } from './languages.js';
import { setupRecordButton, setupTranscriptionRecorder } from './recorder.js';
import { setupRefAudioDropzone, setupTextModeListeners, resetTextMode } from './text-mode.js';
import { handleTranscriptionFile, setupTranscribeListeners } from './transcribe.js';
import { setupAudioPlayers, loadAudioPlayer, resetAudioPlayer } from './components/audio-player.js?v=3';
import { announce, byId, clearNotice, formatDuration, setButtonBusy, setReadyState, showNotice, showOnly } from './ui.js';
import { loadJobs, setupJobs } from './history.js';
import { loadProfiles, setupProfiles } from './profiles.js';

const designStates = ['vd-preview-empty', 'vd-preview-loading', 'vd-preview-error', 'vd-result-section'];
let designAudioUrl = null;
let designReady = false;

function checkDesignReady() {
  const ready = Boolean(byId('vd-text')?.value.trim() && byId('vd-language')?.value);
  designReady = ready;
  setReadyState(byId('start-dubbing-btn'), ready);
}

function updateCharacterCount() {
  const text = byId('vd-text');
  if (text) byId('vd-text-count').textContent = `${text.value.length} / 500`;
}

function showDesignState(id) {
  showOnly(designStates, id);
}

function resetDesignResult() {
  designAudioUrl = null;
  resetAudioPlayer('vd-result-audio');
  showDesignState('vd-preview-empty');
  byId('vd-result-language').textContent = '—';
  byId('vd-result-duration').textContent = '—:—';
}

async function startVoiceDesign() {
  const text = byId('vd-text').value.trim();
  const language = byId('vd-language').value;
  if (!text || !language) return;
  clearNotice('design-error');
  showDesignState('vd-preview-loading');
  setButtonBusy(byId('start-dubbing-btn'), true, { busyText: translate('voiceDesign.generating') });
  announce(translate('voiceDesign.loadingTitle'));
  try {
    const voiceParams = {
      gender: byId('gender').value, age: byId('age').value, pitch: byId('pitch').value,
      style: byId('style').value, accent: byId('accent').value,
    };
    const result = await synthesizeVoiceDesign({ text, language, voiceParams, customInstruct: byId('custom-instruct')?.value.trim() });
    designAudioUrl = resolveApiUrl(result.audio_url || result.url);
    if (!designAudioUrl) throw new Error('The service did not return an audio file.');
    byId('vd-result-language').textContent = byId('vd-language').selectedOptions[0]?.textContent || language.toUpperCase();
    byId('vd-result-duration').textContent = '—:—';
    const audio = byId('vd-result-audio');
    audio.addEventListener('loadedmetadata', () => {
      byId('vd-result-duration').textContent = formatDuration(audio.duration);
    }, { once: true });
    showDesignState('vd-result-section');
    await loadAudioPlayer('vd-result-audio', designAudioUrl);
    announce(translate('status.voiceGenerated'));
    document.dispatchEvent(new CustomEvent('voicelabs:datachange'));
  } catch (error) {
    byId('vd-preview-error-message').textContent = error.message;
    showNotice('design-error', error.message);
    showDesignState('vd-preview-error');
    announce(error.message);
  } finally {
    setButtonBusy(byId('start-dubbing-btn'), false, { idleText: translate('voiceDesign.generate') });
    checkDesignReady();
  }
}

function setupVoiceDesign() {
  byId('vd-text')?.addEventListener('input', () => { updateCharacterCount(); checkDesignReady(); });
  byId('vd-language')?.addEventListener('change', checkDesignReady);
  byId('start-dubbing-btn')?.addEventListener('click', startVoiceDesign);
  byId('vd-retry-btn')?.addEventListener('click', startVoiceDesign);
  byId('vd-preview-retry-btn')?.addEventListener('click', startVoiceDesign);
  byId('vd-download-btn')?.addEventListener('click', async () => {
    if (!designAudioUrl) return;
    try { await downloadAsset(designAudioUrl, 'voice-design'); } catch (error) { showNotice('design-error', error.message); }
  });
  byId('vd-create-another-btn')?.addEventListener('click', () => {
    resetDesignResult();
    byId('vd-text')?.focus();
  });
  updateCharacterCount();
  checkDesignReady();
}

function setupAppReset() {
  document.getElementById('new-job-btn')?.addEventListener('click', () => {
    resetDesignResult();
    resetTextMode();
    byId('vd-text').value = '';
    updateCharacterCount();
    checkDesignReady();
  });
}

async function updateLocalStatus() {
  const status = byId('local-status');
  if (!status) return;
  try {
    await checkApiHealth();
    status.classList.add('is-online');
    status.classList.remove('is-offline');
    const label = status.querySelector('[data-i18n]');
    if (label) { label.dataset.i18n = 'status.localProcessing'; label.textContent = translate('status.localProcessing'); }
  } catch {
    status.classList.add('is-offline');
    status.classList.remove('is-online');
    const label = status.querySelector('[data-i18n]');
    if (label) { label.dataset.i18n = 'status.apiUnavailable'; label.textContent = translate('status.apiUnavailable'); }
  }
}

async function init() {
  applyTheme(getCurrentTheme());
  setupSystemThemeListener();
  applyLanguage(getCurrentLang());
  setupTabs();
  setupSettings();
  setupVoiceDesign();
  setupRefAudioDropzone();
  setupRecordButton();
  setupTextModeListeners();
  setupTranscribeListeners();
  setupTranscriptionRecorder(handleTranscriptionFile);
  setupAudioPlayers();
  setupJobs();
  setupProfiles();
  loadLanguages().catch(error => console.warn('Language loading failed:', error.message));
  setupAppReset();
  loadJobs();
  loadProfiles();
  document.addEventListener('voicelabs:navigate', event => {
    if (event.detail.page === 'jobs') loadJobs();
    if (event.detail.page === 'profiles') loadProfiles();
  });
  document.addEventListener('voicelabs:datachange', () => {
    if (document.getElementById('tab-jobs')?.classList.contains('active')) loadJobs();
    if (document.getElementById('tab-profiles')?.classList.contains('active')) loadProfiles();
  });
  document.addEventListener('voicelabs:languagechange', () => {
    byId('vd-generate-label').textContent = translate('voiceDesign.generate');
    checkDesignReady();
  });
  updateLocalStatus();
}

document.addEventListener('DOMContentLoaded', init);
