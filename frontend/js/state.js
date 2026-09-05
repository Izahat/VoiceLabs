const supportedLanguages = new Set(['en', 'ru', 'az']);
const supportedThemes = new Set(['light', 'dark', 'system']);

let currentLang = localStorage.getItem('ui-lang') || 'en';
let currentTheme = localStorage.getItem('ui-theme') || 'system';
let currentPage = window.location.hash.replace('#', '') || 'design';

if (!supportedLanguages.has(currentLang)) currentLang = 'en';
if (!supportedThemes.has(currentTheme)) currentTheme = 'system';

export const getCurrentLang = () => currentLang;
export const getCurrentTheme = () => currentTheme;
export const getCurrentPage = () => currentPage;

export function setCurrentLang(value) {
  if (!supportedLanguages.has(value)) return;
  currentLang = value;
  localStorage.setItem('ui-lang', value);
}

export function setCurrentTheme(value) {
  if (!supportedThemes.has(value)) return;
  currentTheme = value;
  localStorage.setItem('ui-theme', value);
}

export function setCurrentPage(value) {
  currentPage = value;
}
