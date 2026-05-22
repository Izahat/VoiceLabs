import { translations } from './i18n.js';
import { getCurrentLang, setCurrentLang } from './state.js';

export function applyLanguage(lang) {
  setCurrentLang(lang);
  document.documentElement.lang = lang;
  const t = translations[lang] || translations.en;

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    const val = key.split('.').reduce((o, k) => o?.[k], t);
    if (val) el.textContent = val;
  });

  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.dataset.i18nPlaceholder;
    const val = key.split('.').reduce((o, k) => o?.[k], t);
    if (val) el.placeholder = val;
  });

  updateLangPickerSelection();
}

function updateLangPickerSelection() {
  document.querySelectorAll('.lang-option').forEach(el => {
    el.classList.toggle('selected', el.dataset.langValue === getCurrentLang());
  });
}
