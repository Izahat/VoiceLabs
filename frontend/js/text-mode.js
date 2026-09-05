import { createVoiceProfile, synthesizeWithVoiceProfile, resolveApiUrl } from './api.js';
import { getCurrentLang } from './state.js';
import { translate } from './language.js';
import { setupFileDropzone } from './components/dropzone.js';
import { drawFileWaveform, loadAudioPlayer, resetAudioPlayer } from './components/audio-player.js?v=3';
import { announce, byId, clearNotice, formatBytes, formatDuration, getMediaDuration, setButtonBusy, setReadyState, showNotice, showOnly } from './ui.js';

let referenceFile = null;
let referenceDuration = null;
let referencePreviewUrl = null;
let voiceId = null;
let outputUrl = null;
let lastAction = 'profile';

const referenceIds = ['clone-preview-empty', 'clone-preview-reference', 'clone-preview-processing', 'clone-preview-profile', 'clone-preview-error', 'audio-result-section'];

export function getRefAudioFile() { return referenceFile; }
export function getVoiceProfileId() { return voiceId; }

function validMedia(file) {
  const extension = file.name.split('.').pop()?.toLowerCase();
  return file.type.startsWith('audio/') || file.type.startsWith('video/') || ['wav', 'mp3', 'm4a', 'ogg', 'webm', 'mp4', 'mov', 'avi', 'mkv'].includes(extension);
}

function showClonePreview(id) {
  showOnly(referenceIds, id);
}

function updateRecordMetadata() {
  const file = referenceFile;
  if (!file) return;
  const size = formatBytes(file.size);
  const duration = referenceDuration ? ` · ${formatDuration(referenceDuration)}` : '';
  byId('ref-audio-filesize').textContent = size;
  byId('ref-audio-duration').textContent = duration;
  byId('clone-preview-filemeta').textContent = `${size}${duration}`;
}

function resetProfileState({ keepReference = false } = {}) {
  voiceId = null;
  outputUrl = null;
  byId('clone-phase-two')?.classList.add('phase-section--locked');
  byId('clone-synthesis-fields')?.setAttribute('disabled', '');
  byId('clone-phase-lock')?.classList.remove('hidden');
  byId('clone-step-profile')?.classList.add('active');
  byId('clone-step-profile')?.classList.remove('done');
  byId('clone-step-synthesis')?.classList.remove('active', 'done');
  byId('clone-step-synthesis')?.removeAttribute('aria-current');
  byId('clone-profile-id').textContent = '';
  byId('clone-phase-lock').querySelector('span:last-child').textContent = translate('status.locked');
  byId('clone-voice-btn').disabled = true;
  byId('audio-result-section')?.classList.add('hidden');
  resetAudioPlayer('result-audio');
  if (!keepReference) showClonePreview(referenceFile ? 'clone-preview-reference' : 'clone-preview-empty');
}

function checkProfileReady() {
  const ready = Boolean(referenceFile) && !voiceId;
  setReadyState(byId('create-voice-profile-btn'), ready);
  const synthesisReady = Boolean(voiceId && byId('synthesize-text')?.value.trim() && byId('text-language')?.value);
  setReadyState(byId('clone-voice-btn'), synthesisReady);
}

export function handleRefAudioFile(file) {
  if (!file) return;
  if (file.size > 500 * 1024 * 1024) {
    showNotice('recorder-error', `${translate('errors.fileTooLarge')} ${translate('voiceCloning.formats')}`);
    return;
  }
  if (!validMedia(file)) {
    showNotice('recorder-error', translate('errors.invalidMedia'));
    return;
  }
  referenceFile = file;
  referenceDuration = null;
  if (referencePreviewUrl) URL.revokeObjectURL(referencePreviewUrl);
  referencePreviewUrl = URL.createObjectURL(file);
  resetProfileState({ keepReference: true });
  byId('ref-audio-dropzone').classList.add('hidden');
  byId('ref-audio-file-info').classList.remove('hidden');
  byId('ref-audio-filename').textContent = file.name;
  const fileIcon = byId('ref-file-icon-use');
  fileIcon?.setAttribute('href', `assets/lucide-sprite.svg#${file.type.startsWith('video/') ? 'file-video' : 'file-audio'}`);
  byId('clone-preview-filename').textContent = file.name;
  updateRecordMetadata();
  clearNotice('recorder-error');
  clearNotice('clone-profile-error');
  clearNotice('clone-voice-error');
  showClonePreview('clone-preview-reference');
  drawFileWaveform('ref-preview-waveform', file);
  loadAudioPlayer('ref-audio-preview', referencePreviewUrl);
  getMediaDuration(file).then(duration => {
    if (referenceFile !== file) return;
    referenceDuration = duration;
    updateRecordMetadata();
  });
  checkProfileReady();
  announce(translate('status.referenceSelected'));
}

function clearReference() {
  referenceFile = null;
  referenceDuration = null;
  if (referencePreviewUrl) URL.revokeObjectURL(referencePreviewUrl);
  referencePreviewUrl = null;
  byId('ref-audio-input').value = '';
  byId('ref-audio-file-info').classList.add('hidden');
  byId('ref-audio-dropzone').classList.remove('hidden');
  resetAudioPlayer('ref-audio-preview');
  resetProfileState();
  checkProfileReady();
}

export function setupRefAudioDropzone() {
  const dropzone = byId('ref-audio-dropzone');
  const input = byId('ref-audio-input');
  if (!dropzone || dropzone.dataset.setup === 'true') return;
  setupFileDropzone({
    dropzone, input, maxSize: 500 * 1024 * 1024,
    validate: file => validMedia(file) ? '' : translate('errors.invalidMedia'),
    onFile: handleRefAudioFile,
    onError: message => showNotice('recorder-error', message),
  });
  byId('ref-audio-replace')?.addEventListener('click', () => input.click());
  byId('ref-audio-remove')?.addEventListener('click', event => { event.stopPropagation(); clearReference(); });
}

export function setupTextModeListeners() {
  byId('synthesize-text')?.addEventListener('input', () => {
    byId('clone-text-count').textContent = `${byId('synthesize-text').value.length} / 500`;
    checkProfileReady();
  });
  byId('text-language')?.addEventListener('change', checkProfileReady);
  byId('create-voice-profile-btn')?.addEventListener('click', createProfile);
  byId('clone-voice-btn')?.addEventListener('click', synthesizeSpeech);
  byId('clone-profile-retry-btn')?.addEventListener('click', createProfile);
  byId('clone-preview-retry-btn')?.addEventListener('click', () => lastAction === 'synthesis' ? synthesizeSpeech() : createProfile());
  byId('clone-synthesis-retry-btn')?.addEventListener('click', synthesizeSpeech);
  byId('clone-new-voice-btn')?.addEventListener('click', resetTextMode);
  byId('clone-use-again-btn')?.addEventListener('click', () => {
    byId('audio-result-section')?.classList.add('hidden');
    resetAudioPlayer('result-audio');
    byId('synthesize-text')?.focus();
    showClonePreview('clone-preview-profile');
  });
  checkProfileReady();
}

async function createProfile() {
  if (!referenceFile || voiceId) return;
  lastAction = 'profile';
  clearNotice('clone-profile-error');
  clearNotice('recorder-error');
  setButtonBusy(byId('create-voice-profile-btn'), true, { busyText: translate('voiceCloning.creatingProfile') });
  showClonePreview('clone-preview-processing');
  byId('clone-processing-title').textContent = translate('voiceCloning.preparingProfile');
  byId('clone-processing-description').textContent = translate('voiceCloning.preparingDescription');
  announce(translate('voiceCloning.preparingProfile'));
  try {
    const result = await createVoiceProfile(referenceFile);
    voiceId = result.voice_id || result.id;
    if (!voiceId) throw new Error('The service did not return a voice profile ID.');
    byId('clone-profile-id').textContent = translate('voiceCloning.selectedProfile', { id: voiceId });
    byId('clone-phase-two').classList.remove('phase-section--locked');
    byId('clone-synthesis-fields').removeAttribute('disabled');
    byId('clone-phase-lock').classList.add('hidden');
    byId('clone-step-profile').classList.remove('active');
    byId('clone-step-profile').classList.add('done');
    byId('clone-step-synthesis').classList.add('active');
    byId('clone-step-synthesis').setAttribute('aria-current', 'step');
    showClonePreview('clone-preview-profile');
    checkProfileReady();
    announce(translate('voiceCloning.profileReadyTitle'));
    document.dispatchEvent(new CustomEvent('voicelabs:datachange'));
  } catch (error) {
    showNotice('clone-profile-error', error.message);
    byId('clone-preview-error-message').textContent = error.message;
    showClonePreview('clone-preview-error');
    announce(error.message);
  } finally {
    setButtonBusy(byId('create-voice-profile-btn'), false, { idleText: translate('voiceCloning.createProfile') });
    checkProfileReady();
  }
}

async function synthesizeSpeech() {
  const text = byId('synthesize-text')?.value.trim();
  const language = byId('text-language')?.value;
  if (!voiceId || !text || !language) return;
  lastAction = 'synthesis';
  clearNotice('clone-voice-error');
  setButtonBusy(byId('clone-voice-btn'), true, { busyText: translate('voiceCloning.synthesizing') });
  showClonePreview('clone-preview-processing');
  byId('clone-processing-title').textContent = translate('voiceCloning.synthesizing');
  byId('clone-processing-description').textContent = translate('common.mayTakeMoment');
  announce(translate('voiceCloning.synthesizing'));
  try {
    const result = await synthesizeWithVoiceProfile({ text, voiceId, language });
    outputUrl = resolveApiUrl(result.audio_url || result.url);
    if (!outputUrl) throw new Error('The service did not return an audio file.');
    byId('clone-result-language').textContent = byId('text-language').selectedOptions[0]?.textContent || language.toUpperCase();
    byId('clone-result-duration').textContent = '—:—';
    showClonePreview('audio-result-section');
    byId('result-audio').addEventListener('loadedmetadata', () => {
      byId('clone-result-duration').textContent = formatDuration(byId('result-audio').duration);
    }, { once: true });
    await loadAudioPlayer('result-audio', outputUrl);
    announce(translate('status.audioReady'));
    document.dispatchEvent(new CustomEvent('voicelabs:datachange'));
  } catch (error) {
    showNotice('clone-voice-error', error.message);
    byId('clone-preview-error-title').textContent = translate('voiceCloning.synthesisErrorTitle');
    byId('clone-preview-error-message').textContent = error.message;
    showClonePreview('clone-preview-error');
    announce(error.message);
  } finally {
    setButtonBusy(byId('clone-voice-btn'), false, { idleText: translate('voiceCloning.synthesizeSpeech') });
    checkProfileReady();
  }
}

export async function downloadClonedAudio(downloadAsset) {
  if (!outputUrl) return;
  await downloadAsset(outputUrl, translate('voiceCloning.downloadName'));
}

export function useExistingVoiceProfile(profile) {
  if (!profile?.id) return;
  voiceId = profile.id;
  byId('clone-profile-id').textContent = translate('voiceCloning.selectedProfile', { id: voiceId });
  byId('clone-phase-two').classList.remove('phase-section--locked');
  byId('clone-synthesis-fields').removeAttribute('disabled');
  byId('clone-phase-lock').classList.add('hidden');
  byId('clone-step-profile').classList.remove('active');
  byId('clone-step-profile').classList.add('done');
  byId('clone-step-synthesis').classList.add('active');
  byId('clone-step-synthesis').setAttribute('aria-current', 'step');
  showClonePreview('clone-preview-profile');
  checkProfileReady();
}

export function resetTextMode() {
  referenceFile = null;
  referenceDuration = null;
  if (referencePreviewUrl) URL.revokeObjectURL(referencePreviewUrl);
  referencePreviewUrl = null;
  voiceId = null;
  outputUrl = null;
  byId('ref-audio-input').value = '';
  byId('ref-audio-file-info').classList.add('hidden');
  byId('ref-audio-dropzone').classList.remove('hidden');
  byId('synthesize-text').value = '';
  byId('clone-text-count').textContent = '0 / 500';
  clearNotice('recorder-error');
  clearNotice('clone-profile-error');
  clearNotice('clone-voice-error');
  resetAudioPlayer('ref-audio-preview');
  resetAudioPlayer('result-audio');
  resetProfileState();
  checkProfileReady();
}
