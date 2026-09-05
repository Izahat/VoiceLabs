import { applyTheme } from './theme.js';
import { applyLanguage } from './language.js';

let returnFocus = null;

function focusableElements(dialog) {
  return [...dialog.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])')];
}

export function openSettings(trigger = document.activeElement) {
  const overlay = document.getElementById('settings-modal');
  const dialog = overlay?.querySelector('[role="dialog"]');
  if (!overlay || !dialog) return;
  returnFocus = trigger instanceof HTMLElement ? trigger : null;
  overlay.classList.add('open');
  overlay.setAttribute('aria-hidden', 'false');
  document.body.classList.add('modal-open');
  dialog.focus();
  requestAnimationFrame(() => dialog.focus());
}

export function closeSettings() {
  const overlay = document.getElementById('settings-modal');
  if (!overlay?.classList.contains('open')) return;
  overlay.classList.remove('open');
  overlay.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('modal-open');
  returnFocus?.focus();
  returnFocus = null;
}

export function setupSettings() {
  const overlay = document.getElementById('settings-modal');
  const dialog = overlay?.querySelector('[role="dialog"]');
  document.getElementById('btn-settings')?.addEventListener('click', event => openSettings(event.currentTarget));
  document.getElementById('sidebar-settings')?.addEventListener('click', event => openSettings(event.currentTarget));
  document.getElementById('modal-close')?.addEventListener('click', closeSettings);
  overlay?.addEventListener('pointerdown', event => {
    if (event.target === overlay) closeSettings();
  });

  document.getElementById('btn-theme')?.addEventListener('click', () => {
    applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  });
  document.querySelectorAll('.theme-btn').forEach(button => {
    button.addEventListener('click', () => applyTheme(button.dataset.themeValue));
  });
  document.querySelectorAll('.lang-option').forEach(button => {
    button.addEventListener('click', () => applyLanguage(button.dataset.langValue));
  });

  window.addEventListener('keydown', event => {
    if (!overlay?.classList.contains('open')) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      closeSettings();
      return;
    }
    if (event.key !== 'Tab' || !dialog) return;
    const controls = focusableElements(dialog);
    if (!controls.length) return;
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (!dialog.contains(document.activeElement)) {
      event.preventDefault();
      (event.shiftKey ? last : first).focus();
      return;
    }
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }, true);
}
