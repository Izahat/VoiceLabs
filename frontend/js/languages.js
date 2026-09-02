import { translations } from './i18n.js';
import { fetchLanguages } from './api.js';
import { getCurrentLang } from './state.js';

export async function loadLanguages() {
  const langs = await fetchLanguages();
  populateLanguages(langs);
}

function populateLanguages(langs) {
  const sourceSelects = ['source-lang', 'clone-source-lang'];
  const targetSelects = ['target-lang', 'clone-target-lang'];
  const t = translations[getCurrentLang()] || translations.en;

  sourceSelects.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const currentVal = el.value;
    el.innerHTML = '';
    const opt = document.createElement('option');
    opt.value = 'auto';
    opt.textContent = t.autoDetect || 'Auto Detect';
    el.appendChild(opt);
    langs.forEach(l => {
      const opt = document.createElement('option');
      opt.value = l.code;
      opt.textContent = l.name;
      el.appendChild(opt);
    });
    if (currentVal && [...el.options].some(o => o.value === currentVal)) {
      el.value = currentVal;
    }
  });

  targetSelects.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const currentVal = el.value;
    el.innerHTML = '';
    langs.forEach(l => {
      const opt = document.createElement('option');
      opt.value = l.code;
      opt.textContent = l.name;
      el.appendChild(opt);
    });
    if (currentVal && [...el.options].some(o => o.value === currentVal)) {
      el.value = currentVal;
    }
  });

  const textLangIds = ['text-language', 'clone-text-language', 'vd-language', 'transcribe-language'];
  const commonCodes = ['en', 'ru', 'az', 'tr', 'uk', 'de', 'fr', 'es', 'it', 'pt', 'zh', 'ja', 'ko', 'ar', 'hi', 'fa', 'ur', 'bn', 'vi', 'id'];

  textLangIds.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const currentVal = el.value;
    el.innerHTML = '';
    langs.filter(l => commonCodes.includes(l.code)).forEach(l => {
      const opt = document.createElement('option');
      opt.value = l.code;
      opt.textContent = l.name;
      el.appendChild(opt);
    });
    if (currentVal && [...el.options].some(o => o.value === currentVal)) {
      el.value = currentVal;
    }
  });
}
