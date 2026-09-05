const configuredBase = document.querySelector('meta[name="api-base"]')?.content?.trim();

function inferApiBase() {
  if (window.VOICELABS_API_BASE) return String(window.VOICELABS_API_BASE);
  if (configuredBase) return configuredBase;
  if (window.location.protocol.startsWith('http') && window.location.port === '8000') {
    return `${window.location.origin}/api/v1`;
  }
  return 'http://localhost:8000/api/v1';
}

export const API_BASE = inferApiBase().replace(/\/$/, '');
export const USER_ID = localStorage.getItem('voicelabs-user-id') || (() => {
  const id = crypto.randomUUID();
  localStorage.setItem('voicelabs-user-id', id);
  return id;
})();

export function getUserHeaders() {
  return { 'X-User-Id': USER_ID };
}

export function resolveApiUrl(path) {
  if (!path) return '';
  if (/^https?:\/\//i.test(path) || path.startsWith('blob:')) return path;
  const base = new URL(API_BASE, window.location.origin);
  return new URL(path, `${base.origin}/`).toString();
}

async function parseError(response) {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg || String(item)).join(', ');
  return detail || body?.message || `Request failed (${response.status})`;
}

export async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...getUserHeaders(), ...(options.headers || {}) },
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function checkApiHealth() {
  return requestJson('/dubbing/health');
}

export async function fetchLanguages() {
  try {
    const data = await requestJson('/dubbing/languages');
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.languages)) {
      return data.languages.map(item => {
        if (typeof item === 'string') return { code: item, name: data.common_names?.[item] || item };
        return { code: item.code, name: item.name || item.code };
      });
    }
    return [];
  } catch (error) {
    console.warn('Using fallback languages:', error.message);
    return [
      ['en', 'English'], ['ru', 'Russian'], ['az', 'Azerbaijani'], ['tr', 'Turkish'],
      ['uk', 'Ukrainian'], ['de', 'German'], ['fr', 'French'], ['es', 'Spanish'],
      ['it', 'Italian'], ['pt', 'Portuguese'], ['zh', 'Chinese'], ['ja', 'Japanese'],
      ['ko', 'Korean'], ['ar', 'Arabic'], ['hi', 'Hindi'], ['fa', 'Persian'],
    ].map(([code, name]) => ({ code, name }));
  }
}

export async function synthesizeVoiceDesign({ text, language, voiceParams, customInstruct }) {
  const body = { text, language };
  for (const [key, value] of Object.entries(voiceParams || {})) {
    if (value) body[key] = value;
  }
  if (customInstruct) body.custom_instruct = customInstruct;
  return requestJson('/dubbing/tts/voice-design', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function createVoiceProfile(referenceFile) {
  const form = new FormData();
  form.append('reference_audio', referenceFile);
  form.append('mode', 'clone');
  return requestJson('/dubbing/tts/clone', { method: 'POST', body: form });
}

export async function synthesizeWithVoiceProfile({ text, voiceId, language }) {
  return requestJson('/dubbing/tts/synthesize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice_id: voiceId, language }),
  });
}

export async function transcribeUpload({ file, language }) {
  const form = new FormData();
  form.append('file', file);
  if (language) form.append('language', language);
  form.append('enable_diarization', 'false');
  return requestJson('/transcription/transcribe', { method: 'POST', body: form });
}

export async function transcribeUrl({ url, language }) {
  const form = new FormData();
  form.append('url', url);
  if (language) form.append('language', language);
  form.append('enable_diarization', 'false');
  return requestJson('/transcription/transcribe/url', { method: 'POST', body: form });
}

export async function fetchJobs() {
  const data = await requestJson('/dubbing/jobs');
  return data.jobs || [];
}

export async function fetchVoiceProfiles() {
  const data = await requestJson('/dubbing/voice-profiles');
  return data.profiles || [];
}

function filenameFromDisposition(value) {
  if (!value) return '';
  const encoded = value.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  if (encoded) return decodeURIComponent(encoded.replace(/["']/g, ''));
  return value.match(/filename="?([^";]+)"?/i)?.[1] || '';
}

function extensionForMime(mime) {
  const normalized = String(mime || '').split(';')[0].trim().toLowerCase();
  return {
    'audio/wav': '.wav', 'audio/x-wav': '.wav', 'audio/wave': '.wav',
    'audio/mpeg': '.mp3', 'audio/mp4': '.m4a', 'audio/ogg': '.ogg',
    'audio/webm': '.webm', 'video/mp4': '.mp4', 'video/webm': '.webm',
  }[normalized] || '';
}

export async function downloadAsset(url, fallbackBase = 'voicelabs-audio') {
  const resolved = resolveApiUrl(url);
  try {
    const response = await fetch(resolved, { headers: getUserHeaders() });
    if (!response.ok) throw new Error(await parseError(response));
    const blob = await response.blob();
    const headerName = filenameFromDisposition(response.headers.get('content-disposition'));
    const extension = extensionForMime(blob.type) || '.wav';
    const filename = headerName || `${fallbackBase}${extension}`;
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  } catch (error) {
    const anchor = document.createElement('a');
    anchor.href = resolved;
    anchor.download = `${fallbackBase}.wav`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    console.warn('Direct asset download fallback:', error.message);
  }
}
