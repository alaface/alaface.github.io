'use strict';
const search = document.querySelector('[data-filter]');
if (search) {
  const entries = [...document.querySelectorAll('[data-search]')];
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  search.addEventListener('input', () => {
    const terms = normalize(search.value).trim().split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const entry of entries) {
      entry.hidden = !terms.every(term => normalize(entry.dataset.search).includes(term));
      if (!entry.hidden) visible++;
    }
    document.querySelectorAll('.year-group').forEach(group => {
      group.hidden = !group.querySelector('[data-search]:not([hidden])');
    });
    document.querySelectorAll('[data-archive]').forEach(archive => { archive.open = terms.length > 0; });
    const count = document.querySelector('[data-count]');
    count.textContent = `${visible} of ${entries.length} ${count.dataset.itemLabel || 'entries'}`;
    document.querySelector('[data-empty]').hidden = visible > 0;
  });
  document.querySelector('[data-reset-filter]')?.addEventListener('click', () => {
    search.value = '';
    search.dispatchEvent(new Event('input'));
    search.focus();
  });
}
