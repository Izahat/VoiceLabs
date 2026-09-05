import { fetchLanguages } from './api.js';
import { getCurrentLang } from './state.js';
import { translate } from './language.js';

let cachedLanguages = [];
const commonCodes = new Set(['en', 'ru', 'az', 'tr', 'uk', 'de', 'fr', 'es', 'it', 'pt', 'zh', 'ja', 'ko', 'ar', 'hi', 'fa', 'ur', 'bn', 'vi', 'id']);

function displayName(code, fallback) {
  try {
    return new Intl.DisplayNames([getCurrentLang()], { type: 'language' }).of(code) || fallback;
  } catch {
    return fallback;
  }
}

function populateSelect(id, { autoDetect = false, defaultCode = 'en' } = {}) {
  const select = document.getElementById(id);
  if (!select) return;
  const previous = select.value;
  select.innerHTML = '';

  if (autoDetect) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = translate('common.autoDetect');
    select.appendChild(option);
  }

  cachedLanguages.filter(item => commonCodes.has(item.code)).forEach(item => {
    const option = document.createElement('option');
    option.value = item.code;
    option.textContent = displayName(item.code, item.name);
    select.appendChild(option);
  });

  const validPrevious = [...select.options].some(option => option.value === previous);
  if (validPrevious) select.value = previous;
  else if (autoDetect) select.value = '';
  else if ([...select.options].some(option => option.value === defaultCode)) select.value = defaultCode;
  else if (select.options.length) select.selectedIndex = 0;
  select.dispatchEvent(new Event('change', { bubbles: true }));
}

export function populateLanguages() {
  populateSelect('vd-language');
  populateSelect('text-language');
  populateSelect('transcribe-language', { autoDetect: true });
}

export async function loadLanguages() {
  cachedLanguages = await fetchLanguages();
  populateLanguages();
  return cachedLanguages;
}

document.addEventListener('voicelabs:languagechange', () => {
  if (cachedLanguages.length) populateLanguages();
});
