import { fetchJobs, downloadAsset, resolveApiUrl } from './api.js';
import { translate } from './language.js';
import { navigateTo } from './tabs.js';
import { byId, escapeHtml, formatDate, formatDuration, iconMarkup, showNotice, showOnly } from './ui.js';

let jobs = [];
let filter = 'all';

const workflow = {
  voice_design: { label: 'jobs.voiceDesign', icon: 'sparkles' },
  voice_profile: { label: 'jobs.voiceProfile', icon: 'user-round' },
  tts_synthesis: { label: 'jobs.clonedSpeech', icon: 'audio-waveform' },
  transcription: { label: 'jobs.transcription', icon: 'file-text' },
  transcription_url: { label: 'jobs.transcription', icon: 'link' },
};

function statusLabel(status) {
  const key = { completed: 'status.completed', failed: 'status.failed', pending: 'status.pending', synthesizing: 'status.synthesizing' }[status] || 'status.processing';
  return translate(key);
}

function render() {
  const list = byId('jobs-list');
  const visible = filter === 'all' ? jobs : jobs.filter(job => {
    if (filter === 'voice_cloning') return ['voice_profile', 'tts_synthesis'].includes(job.kind);
    return job.kind === filter;
  });
  if (!visible.length) {
    showOnly(['jobs-loading', 'jobs-error', 'jobs-empty', 'jobs-list'], 'jobs-empty');
    return;
  }
  list.innerHTML = `<div class="jobs-header"><span>${translate('jobs.workflow')}</span><span>${translate('jobs.status')}</span><span>${translate('jobs.language')}</span><span>${translate('jobs.created')}</span><span>${translate('jobs.actions')}</span></div>${visible.map(jobRow).join('')}`;
  list.classList.remove('hidden');
  byId('jobs-loading').classList.add('hidden'); byId('jobs-error').classList.add('hidden'); byId('jobs-empty').classList.add('hidden');
  list.querySelectorAll('[data-job-download]').forEach(button => button.addEventListener('click', async () => {
    button.disabled = true;
    try { await downloadAsset(button.dataset.jobDownload, button.dataset.filename || 'voicelabs-output'); }
    catch (error) { showNotice('jobs-error', error.message); }
    finally { button.disabled = false; }
  }));
  list.querySelectorAll('[data-job-open]').forEach(button => button.addEventListener('click', () => window.open(resolveApiUrl(button.dataset.jobOpen), '_blank', 'noopener')));
}

function jobRow(job) {
  const meta = workflow[job.kind] || { label: 'jobs.workflow', icon: 'history' };
  const outputUrl = job.output_url || (job.output_asset_id ? `/api/v1/dubbing/assets/${job.output_asset_id}` : '');
  const language = job.target_language || job.source_language || '—';
  const action = outputUrl ? `<button class="icon-button" type="button" data-job-open="${escapeHtml(outputUrl)}" aria-label="${translate('jobs.openAsset')}" data-tooltip="${translate('jobs.openAsset')}">${iconMarkup('external-link')}</button><button class="icon-button" type="button" data-job-download="${escapeHtml(outputUrl)}" data-filename="${escapeHtml(meta.label)}" aria-label="${translate('jobs.downloadAsset')}" data-tooltip="${translate('jobs.downloadAsset')}">${iconMarkup('download')}</button>` : `<span class="job-cell">${translate('jobs.noOutput')}</span>`;
  return `<div class="job-row"><div class="job-primary">${iconMarkup(meta.icon, 'job-icon__svg')}<div><strong>${translate(meta.label)}</strong><span>${escapeHtml(job.job_id || '—')}</span></div></div><span class="status-chip status-chip--${job.status === 'completed' ? 'success' : job.status === 'failed' ? 'danger' : 'neutral'}">${escapeHtml(statusLabel(job.status))}</span><span class="job-cell">${escapeHtml(language)}</span><span class="job-cell">${escapeHtml(formatDate(job.created_at))}</span><div class="job-actions">${action}</div></div>`;
}

export async function loadJobs() {
  if (!byId('jobs-list')) return;
  byId('jobs-loading').classList.remove('hidden');
  byId('jobs-error').classList.add('hidden');
  try {
    jobs = await fetchJobs();
    render();
  } catch (error) {
    byId('jobs-error').querySelector('[data-notice-message]').textContent = error.message;
    showOnly(['jobs-loading', 'jobs-error', 'jobs-empty', 'jobs-list'], 'jobs-error');
  }
}

export function setupJobs() {
  document.querySelectorAll('[data-job-filter]').forEach(button => button.addEventListener('click', () => {
    filter = button.dataset.jobFilter;
    document.querySelectorAll('[data-job-filter]').forEach(item => {
      const active = item === button;
      item.classList.toggle('active', active); item.setAttribute('aria-pressed', String(active));
    });
    render();
  }));
  byId('jobs-retry')?.addEventListener('click', loadJobs);
  document.addEventListener('voicelabs:languagechange', () => { if (jobs.length) render(); });
}
