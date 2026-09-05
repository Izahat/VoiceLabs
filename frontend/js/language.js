import { translations } from './i18n.js';
import { getCurrentLang, setCurrentLang } from './state.js';

export function translate(key, params = {}, lang = getCurrentLang()) {
  const resolve = locale => key.split('.').reduce((value, part) => value?.[part], translations[locale]);
  let value = resolve(lang) ?? resolve('en') ?? key;
  if (typeof value !== 'string') return key;
  for (const [name, replacement] of Object.entries(params)) {
    value = value.replaceAll(`{${name}}`, String(replacement));
  }
  return value;
}

export function applyLanguage(lang) {
  const locale = translations[lang] ? lang : 'en';
  setCurrentLang(locale);
  document.documentElement.lang = locale;

  document.querySelectorAll('[data-i18n]').forEach(element => {
    element.textContent = translate(element.dataset.i18n, {}, locale);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
    element.placeholder = translate(element.dataset.i18nPlaceholder, {}, locale);
  });
  document.querySelectorAll('[data-i18n-aria-label]').forEach(element => {
    element.setAttribute('aria-label', translate(element.dataset.i18nAriaLabel, {}, locale));
  });
  document.querySelectorAll('[data-i18n-tooltip]').forEach(element => {
    element.dataset.tooltip = translate(element.dataset.i18nTooltip, {}, locale);
  });

  document.querySelectorAll('.lang-option').forEach(element => {
    const selected = element.dataset.langValue === locale;
    element.classList.toggle('selected', selected);
    element.setAttribute('aria-checked', String(selected));
  });
  document.dispatchEvent(new CustomEvent('voicelabs:languagechange', { detail: { lang: locale } }));
}
