'use strict';
(() => {
  const supported = ['en', 'es', 'ru'];
  const key = 'laface-language';
  const url = new URL(window.location.href);
  const first = url.pathname.split('/')[1];
  if (supported.includes(first)) {
    // An explicit language URL always wins over saved or browser preferences.
    try { localStorage.setItem(key, first); } catch (_) { /* Storage is optional. */ }
    return;
  }
  // Only the five generated pages have translated counterparts.
  if (!/^\/(?:index\.html)?$|^\/(?:papers|arxiv|software|book)\/(?:index\.html)?$/.test(url.pathname)) return;
  let saved;
  try { saved = localStorage.getItem(key); } catch (_) { /* Storage is optional. */ }
  const preferred = (navigator.languages || [navigator.language || 'en'])
    .map(value => value.toLowerCase().split('-')[0])
    .find(value => supported.includes(value));
  const language = supported.includes(saved) ? saved : (preferred || 'en');
  url.pathname = `/${language}${url.pathname.replace(/index\.html$/, '')}`;
  // Keep deep links, query parameters and fragments intact.
  window.location.replace(url.href);
})();
