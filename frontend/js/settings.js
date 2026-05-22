import { applyTheme } from './theme.js';
import { applyLanguage } from './language.js';
import { getCurrentTheme } from './state.js';

export function setupSettings() {
  const modal = document.getElementById('settings-modal');
  const btn = document.getElementById('btn-settings');
  const closeBtn = document.getElementById('modal-close');

  btn.addEventListener('click', () => modal.classList.add('open'));
  closeBtn.addEventListener('click', () => modal.classList.remove('open'));
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.remove('open');
  });

  document.getElementById('btn-theme').addEventListener('click', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    applyTheme(isDark ? 'light' : 'dark');
  });

  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.addEventListener('click', () => applyTheme(btn.dataset.themeValue));
  });

  document.querySelectorAll('.lang-option').forEach(el => {
    el.addEventListener('click', () => {
      applyLanguage(el.dataset.langValue);
    });
  });

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (getCurrentTheme() === 'system') applyTheme('system');
  });
}
