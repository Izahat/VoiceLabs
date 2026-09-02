export const API_BASE = 'http://localhost:8000/api/v1';
export const USER_ID = localStorage.getItem('voicelabs-user-id') || (() => {
  const id = crypto.randomUUID();
  localStorage.setItem('voicelabs-user-id', id);
  return id;
})();

export function getUserHeaders() {
  return { 'X-User-Id': USER_ID };
}

export async function fetchLanguages() {
  try {
    const res = await fetch(`${API_BASE}/dubbing/languages`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    // API returns { "count": N, "languages": ["en", "ru", ...], "common_names": {...} }
    // Map codes to objects with code+name
    if (Array.isArray(data)) {
      return data;
    }
    if (data.languages && data.common_names) {
      return data.languages.map(code => ({
        code,
        name: data.common_names[code] || code,
      }));
    }
    return data.languages || [];
  } catch (err) {
    console.warn('Using fallback languages:', err.message);
    return [
      { code: 'en', name: 'English' },
      { code: 'ru', name: 'Russian' },
      { code: 'az', name: 'Azerbaijani' },
      { code: 'es', name: 'Spanish' },
      { code: 'fr', name: 'French' },
      { code: 'de', name: 'German' },
      { code: 'it', name: 'Italian' },
      { code: 'pt', name: 'Portuguese' },
      { code: 'zh', name: 'Chinese' },
      { code: 'ja', name: 'Japanese' },
      { code: 'ko', name: 'Korean' },
      { code: 'ar', name: 'Arabic' },
      { code: 'hi', name: 'Hindi' },
      { code: 'tr', name: 'Turkish' },
      { code: 'uk', name: 'Ukrainian' },
    ];
  }
}

export async function startCloning({ referenceAudio, sourceLang, targetLang, text, textLanguage }) {
  const form = new FormData();
  form.append('reference_audio', referenceAudio);
  form.append('source_language', sourceLang || 'auto');
  form.append('target_language', targetLang);
  if (text) form.append('text', text);
  if (textLanguage) form.append('text_language', textLanguage);

  const res = await fetch(`${API_BASE}/dubbing/clone`, {
    method: 'POST',
    headers: getUserHeaders(),
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function pollJob(jobId) {
  const res = await fetch(`${API_BASE}/dubbing/status/${jobId}`, { headers: getUserHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function synthesizeVoiceDesign({ text, language, voiceParams }) {
  const body = {
    text,
    language,
  };
  if (voiceParams.gender) body.gender = voiceParams.gender;
  if (voiceParams.age) body.age = voiceParams.age;
  if (voiceParams.pitch) body.pitch = voiceParams.pitch;
  if (voiceParams.style) body.style = voiceParams.style;
  if (voiceParams.accent) body.accent = voiceParams.accent;

  const res = await fetch(`${API_BASE}/dubbing/tts/voice-design`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getUserHeaders() },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
