import { setCurrentPage } from './state.js';
import { translate } from './language.js';

const pages = new Set(['design', 'cloning', 'transcribe', 'jobs', 'profiles']);

function closeMobileNavigation() {
  const sidebar = document.getElementById('app-sidebar');
  const menu = document.getElementById('mobile-menu');
  const scrim = document.getElementById('nav-scrim');
  sidebar?.classList.remove('is-open');
  scrim?.classList.remove('open');
  document.body.classList.remove('nav-open');
  menu?.setAttribute('aria-expanded', 'false');
}

function updateBreadcrumb(page) {
  const section = document.getElementById(`tab-${page}`);
  const currentSection = document.getElementById('current-section');
  const currentPage = document.getElementById('current-page');
  if (!section || !currentSection || !currentPage) return;

  const sectionKey = page === 'design' || page === 'cloning' ? 'nav.createVoice' : 'nav.workspace';
  const pageKey = {
    design: 'nav.voiceDesign', cloning: 'nav.voiceCloning', transcribe: 'nav.transcription',
    jobs: 'nav.recentJobs', profiles: 'nav.voiceProfiles',
  }[page];
  currentSection.textContent = translate(sectionKey);
  currentPage.textContent = translate(pageKey);
}

export function navigateTo(page, { updateHash = true, focus = true } = {}) {
  const target = pages.has(page) ? page : 'design';
  document.querySelectorAll('.tab-content').forEach(section => {
    const active = section.id === `tab-${target}`;
    section.classList.toggle('active', active);
    section.hidden = !active;
  });
  document.querySelectorAll('.tab[data-tab]').forEach(button => {
    const active = button.dataset.tab === target;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  setCurrentPage(target);
  updateBreadcrumb(target);
  closeMobileNavigation();
  if (updateHash && window.location.hash !== `#${target}`) history.replaceState(null, '', `#${target}`);
  if (focus) document.getElementById('main-content')?.focus({ preventScroll: true });
  document.dispatchEvent(new CustomEvent('voicelabs:navigate', { detail: { page: target } }));
}

export function setupTabs() {
  document.querySelectorAll('.tab[data-tab], [data-navigate]').forEach(control => {
    control.addEventListener('click', () => navigateTo(control.dataset.tab || control.dataset.navigate));
  });

  const sidebar = document.getElementById('app-sidebar');
  const menu = document.getElementById('mobile-menu');
  const scrim = document.getElementById('nav-scrim');
  const openMobileNavigation = () => {
    sidebar?.classList.add('is-open');
    scrim?.classList.add('open');
    document.body.classList.add('nav-open');
    menu?.setAttribute('aria-expanded', 'true');
    document.getElementById('sidebar-close')?.focus();
  };
  menu?.addEventListener('click', openMobileNavigation);
  document.getElementById('sidebar-close')?.addEventListener('click', () => {
    closeMobileNavigation();
    menu?.focus();
  });
  document.getElementById('nav-scrim')?.addEventListener('click', closeMobileNavigation);
  window.addEventListener('hashchange', () => navigateTo(window.location.hash.slice(1), { updateHash: false }));
  window.addEventListener('keydown', event => {
    if (event.key === 'Escape' && document.body.classList.contains('nav-open')) {
      closeMobileNavigation();
      menu?.focus();
    }
  });
  document.addEventListener('voicelabs:languagechange', () => updateBreadcrumb(window.location.hash.slice(1) || 'design'));

  navigateTo(window.location.hash.slice(1) || 'design', { updateHash: true, focus: false });
}
