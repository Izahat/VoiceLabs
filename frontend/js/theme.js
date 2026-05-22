import { getCurrentTheme, setCurrentTheme } from './state.js';

export function updateThemeIcon() {
  const btn = document.getElementById('btn-theme');
  if (!btn) return;
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  btn.textContent = isDark ? '☀' : '🌙';
  btn.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');
}

export function applyTheme(theme) {
  setCurrentTheme(theme);

  if (theme === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
  } else {
    document.documentElement.setAttribute('data-theme', theme);
  }

  updateThemeButtons();
  updateThemeIcon();
}

function updateThemeButtons() {
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.themeValue === getCurrentTheme());
  });
}
