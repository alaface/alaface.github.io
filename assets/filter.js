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
    document.querySelector('[data-count]').textContent = `${visible} of ${entries.length} entries`;
    document.querySelector('[data-empty]').hidden = visible > 0;
  });
}
