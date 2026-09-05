import { translate } from './language.js';

export function byId(id) { return document.getElementById(id); }

export function showOnly(ids, activeId) {
  ids.forEach(id => byId(id)?.classList.toggle('hidden', id !== activeId));
}

export function announce(message) {
  const region = byId('live-region');
  if (!region) return;
  region.textContent = '';
  requestAnimationFrame(() => { region.textContent = message; });
}

export function showToast(message, timeout = 2400) {
  const toast = byId('toast');
  if (!toast) return;
  toast.querySelector('[data-toast-message]').textContent = message;
  toast.classList.remove('hidden');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => toast.classList.add('hidden'), timeout);
  announce(message);
}

export function showNotice(id, message) {
  const notice = byId(id);
  if (!notice) return;
  const target = notice.querySelector('[data-notice-message]') || notice;
  target.textContent = message;
  notice.classList.remove('hidden');
}

export function clearNotice(id) {
  const notice = byId(id);
  if (!notice) return;
  notice.classList.add('hidden');
  const target = notice.querySelector('[data-notice-message]');
  if (target) target.textContent = '';
}

export function setButtonBusy(button, busy, { busyText, idleText } = {}) {
  if (!button) return;
  button.disabled = busy || button.dataset.ready === 'false';
  button.setAttribute('aria-busy', String(busy));
  button.classList.toggle('is-busy', busy);
  const label = button.querySelector('span:last-child');
  if (label) {
    if (!label.dataset.idleText) label.dataset.idleText = idleText || label.textContent;
    label.textContent = busy ? (busyText || translate('common.processing')) : (idleText || label.dataset.idleText);
  }
  const use = button.querySelector('use');
  if (use) use.setAttribute('href', `assets/lucide-sprite.svg#${busy ? 'loader-circle' : (button.dataset.icon || 'audio-waveform')}`);
  button.querySelector('svg')?.classList.toggle('icon--spin', busy);
}

export function setReadyState(button, ready) {
  if (!button) return;
  button.dataset.ready = String(Boolean(ready));
  if (button.getAttribute('aria-busy') !== 'true') button.disabled = !ready;
}

export function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

export function formatDuration(seconds, fallback = '—:—') {
  if (!Number.isFinite(seconds) || seconds < 0) return fallback;
  const total = Math.floor(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours) return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  return `${minutes}:${String(secs).padStart(2, '0')}`;
}

export function formatDate(value) {
  if (!value) return translate('common.unknownDate');
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return translate('common.unknownDate');
  return new Intl.DateTimeFormat(document.documentElement.lang || 'en', {
    dateStyle: 'medium', timeStyle: 'short',
  }).format(date);
}

export function getMediaDuration(file) {
  return new Promise(resolve => {
    if (!file) return resolve(null);
    const media = document.createElement(file.type.startsWith('video/') ? 'video' : 'audio');
    const objectUrl = URL.createObjectURL(file);
    media.preload = 'metadata';
    const cleanup = value => {
      URL.revokeObjectURL(objectUrl);
      media.removeAttribute('src');
      resolve(Number.isFinite(value) ? value : null);
    };
    media.onloadedmetadata = () => cleanup(media.duration);
    media.onerror = () => cleanup(null);
    media.src = objectUrl;
  });
}

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[char]));
}

export function iconMarkup(name, extraClass = '') {
  const className = ['icon', extraClass].filter(Boolean).join(' ');
  return `<svg class="${className}" aria-hidden="true"><use href="assets/lucide-sprite.svg#${name}"></use></svg>`;
}
