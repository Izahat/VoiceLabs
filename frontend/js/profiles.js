import { fetchVoiceProfiles, resolveApiUrl } from './api.js';
import { translate } from './language.js';
import { navigateTo } from './tabs.js';
import { useExistingVoiceProfile } from './text-mode.js';
import { byId, escapeHtml, formatBytes, formatDate, formatDuration, iconMarkup, showOnly } from './ui.js';

let profiles = [];

function render() {
  if (!profiles.length) {
    showOnly(['profiles-loading', 'profiles-error', 'profiles-empty', 'profiles-list'], 'profiles-empty');
    return;
  }
  const list = byId('profiles-list');
  list.innerHTML = profiles.map(profile => {
    const asset = profile.reference_asset || {};
    const meta = [asset.original_filename || '—', asset.size_bytes ? formatBytes(asset.size_bytes) : '', asset.duration ? formatDuration(asset.duration) : ''].filter(Boolean).join(' · ');
    const preview = asset.url ? `<audio controls preload="none" src="${escapeHtml(resolveApiUrl(asset.url))}" aria-label="${translate('profiles.previewReference')}"></audio>` : '';
    return `<article class="profile-card"><div class="profile-card__header"><span class="profile-card__icon">${iconMarkup('user-round')}</span><div><h2>${escapeHtml(asset.original_filename || translate('common.profile'))}</h2><p class="profile-card__id">${escapeHtml(profile.id)}</p></div></div><div class="profile-card__meta"><span>${iconMarkup('clock')} ${translate('profiles.created')}: ${escapeHtml(formatDate(profile.created_at))}</span><span>${iconMarkup('file-audio')} ${translate('profiles.reference')}: ${escapeHtml(meta || '—')}</span></div>${preview}<button class="btn btn--secondary btn--full" type="button" data-use-profile="${escapeHtml(profile.id)}">${iconMarkup('audio-waveform')}<span>${translate('profiles.useVoice')}</span></button></article>`;
  }).join('');
  list.classList.remove('hidden'); byId('profiles-loading').classList.add('hidden'); byId('profiles-error').classList.add('hidden'); byId('profiles-empty').classList.add('hidden');
  list.querySelectorAll('[data-use-profile]').forEach(button => button.addEventListener('click', () => {
    const profile = profiles.find(item => item.id === button.dataset.useProfile);
    navigateTo('cloning');
    useExistingVoiceProfile(profile);
  }));
}

export async function loadProfiles() {
  if (!byId('profiles-list')) return;
  byId('profiles-loading').classList.remove('hidden'); byId('profiles-error').classList.add('hidden');
  try { profiles = await fetchVoiceProfiles(); render(); }
  catch (error) { byId('profiles-error').querySelector('[data-notice-message]').textContent = error.message; showOnly(['profiles-loading', 'profiles-error', 'profiles-empty', 'profiles-list'], 'profiles-error'); }
}

export function setupProfiles() {
  byId('profiles-retry')?.addEventListener('click', loadProfiles);
  document.addEventListener('voicelabs:languagechange', () => { if (profiles.length) render(); });
}
