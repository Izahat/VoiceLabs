import { getCurrentTheme, setCurrentTheme } from './state.js';
import { translate } from './language.js';

const media = window.matchMedia('(prefers-color-scheme: dark)');

function resolvedTheme(preference) {
  return preference === 'system' ? (media.matches ? 'dark' : 'light') : preference;
}

export function updateThemeIcon() {
  const button = document.getElementById('btn-theme');
  const use = button?.querySelector('[data-theme-use]');
  const isDark = document.documentElement.dataset.theme === 'dark';
  use?.setAttribute('href', `assets/lucide-sprite.svg#${isDark ? 'sun' : 'moon'}`);
  if (button) {
    const label = isDark ? translate('settings.light') : translate('settings.dark');
    button.setAttribute('aria-label', label);
    button.removeAttribute('data-tooltip');
  }
}

function updateThemeButtons() {
  const preference = getCurrentTheme();
  document.querySelectorAll('.theme-btn').forEach(button => {
    const active = button.dataset.themeValue === preference;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
}

export function applyTheme(preference) {
  setCurrentTheme(preference);
  document.documentElement.dataset.theme = resolvedTheme(getCurrentTheme());
  document.documentElement.style.colorScheme = document.documentElement.dataset.theme;
  updateThemeButtons();
  updateThemeIcon();
  document.dispatchEvent(new CustomEvent('voicelabs:themechange', {
    detail: { preference: getCurrentTheme(), theme: document.documentElement.dataset.theme },
  }));
}

export function setupSystemThemeListener() {
  media.addEventListener('change', () => {
    if (getCurrentTheme() === 'system') applyTheme('system');
  });
  document.addEventListener('voicelabs:languagechange', updateThemeIcon);
}
