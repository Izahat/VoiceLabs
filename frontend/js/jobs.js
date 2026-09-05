import { clearNotice, showNotice } from './ui.js';

export function showError(id, message) {
  showNotice(id, message);
}

export function clearError(id) {
  clearNotice(id);
}
