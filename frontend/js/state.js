// Shared application state with getters/setters
let _videoFile = null;
let _referenceAudioFile = null;
let _cloneVideoFile = null;
let _refAudioFile = null;
let _jobId = null;
let _pollInterval = null;
let _currentLang = localStorage.getItem('ui-lang') || 'en';
let _currentTheme = localStorage.getItem('ui-theme') || 'system';
let _currentCloneMode = 'video';

export const getVideoFile = () => _videoFile;
export const getReferenceAudioFile = () => _referenceAudioFile;
export const getCloneVideoFile = () => _cloneVideoFile;
export const getRefAudioFile = () => _refAudioFile;
export const getJobId = () => _jobId;
export const getPollInterval = () => _pollInterval;
export const getCurrentLang = () => _currentLang;
export const getCurrentTheme = () => _currentTheme;
export const getCurrentCloneMode = () => _currentCloneMode;

export function setVideoFile(v) { _videoFile = v; }
export function setReferenceAudioFile(v) { _referenceAudioFile = v; }
export function setCloneVideoFile(v) { _cloneVideoFile = v; }
export function setRefAudioFile(v) { _refAudioFile = v; }
export function setJobId(v) { _jobId = v; }
export function setPollInterval(v) { _pollInterval = v; }
export function setCurrentLang(v) { _currentLang = v; localStorage.setItem('ui-lang', v); }
export function setCurrentTheme(v) { _currentTheme = v; localStorage.setItem('ui-theme', v); }
export function setCurrentCloneMode(v) { _currentCloneMode = v; }
