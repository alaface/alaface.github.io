// Build papers/index.html from a local BibTeX file exported from zbMATH.
// Run in GitHub Actions (Node >= 18)

const fs = require('node:fs/promises');

const BIB_PATH = 'data/papers.bib';

// --- tiny BibTeX parser (very tolerant, good enough for common @article/@incollection) ---
function parseBibtex(bib) {
  const entries = [];
  const blocks = bib.split('@').slice(1); // skip preamble
  for (const block of blocks) {
    const type = block.slice(0, block.indexOf('{')).trim().toLowerCase();
    const rest = block.slice(block.indexOf('{') + 1);
    const end = rest.lastIndexOf('}');
    const body = rest.slice(0, end);

    // key, fields
    const key = body.slice(0, body.indexOf(',')).trim();
    const fieldsRaw = body.slice(body.indexOf(',') + 1);

    const fields = {};
    // naive field matcher: name = { ... } or " ... "
    const re = /([a-zA-Z\-]+)\s*=\s*(\{([^{}]*|(\{[^{}]*\}))*\}|"[^"]*"|[^,]+)\s*,?/gms;
    let m;
    while ((m = re.exec(fieldsRaw)) !== null) {
      let val = m[2].trim();
      if ((val.startsWith('{') && val.endsWith('}')) || (val.startsWith('"') && val.endsWith('"'))) {
        val = val.slice(1, -1);
      }
      fields[m[1].toLowerCase()] = val.replace(/\s+/g, ' ').trim();
    }
    entries.push({ type, key, ...fields });
  }
  return entries;
}

function esc(s=''){ return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
const doiURL = d => d ? `https://doi.org/${encodeURIComponent(d)}` : '';
const mrLookup = d => d ? `https://mathscinet.ams.org/mathscinet/relay?mr=Lookup&url=https://mathscinet.ams.org/mathscinet/search/publications.html?pg1=DOI&s1=${encodeURIComponent(d)}` : '';
const yearOf = e => e.year || (e.date && e.date.match(/\d{4}/)?.[0]) || '';

const header = `<!doctype html>
<html lang="en"><head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Papers — A. Laface</title>
  <link rel="stylesheet" href="../assets/css/style.css">
</head><body>
<header><nav>
  <a class="brand" href="../">Antonio&nbsp;Laface</a>
  <a href="./">Papers</a>
  <a href="../arxiv/">arXiv</a>
  <a href="../software/">Software</a>
  <a href="../notes/">Lecture notes</a>
  <a href="../book/">Book</a>
</nav></header>
<main>
  <h1>Published papers</h1>
  <p>This page is generated from a BibTeX export of my zbMATH author profile.</p>
  <div id="papers" class="card">`;

const footer = `
  </div>
  <p style="font-size:.95em;color:#57606a;margin-top:1rem">
    Source: zbMATH Open (manual BibTeX export)
  </p>
</main>
<footer>© <span id="y"></span> Antonio Laface</footer>
<script>document.getElementById('y').textContent = new Date().getFullYear();</script>
</body></html>`;

(async () => {
  try {
    const bib = await fs.readFile(BIB_PATH, 'utf8');
    let items = parseBibtex(bib);

    // keep only entries with you as author to be safe
    items = items.filter(e => (e.author || '').toLowerCase().includes('laface'));

    // sort by year desc
    items.sort((a,b) => (parseInt(yearOf(b))||0) - (parseInt(yearOf(a))||0));

    const html = items.map(e => {
      const title = e.title || '(untitled)';
      const authors = e.author || '';
      const journal = e.journal || e.booktitle || '';
      const vol = e.volume ? ` ${e.volume}` : '';
      const no = e.number ? `(${e.number})` : '';
      const pp = e.pages ? `:${e.pages}` : '';
      const yr = yearOf(e);
      const doi = e.doi || '';
      const url = e.url || doiURL(doi);

      return `
        <div class="card">
          <h3 style="margin-top:0">${url ? `<a href="${esc(url)}" target="_blank" rel="noopener">` : ''}${esc(title)}${url ? '</a>' : ''}</h3>
          <p><strong>Authors:</strong> ${esc(authors)}</p>
          <p><strong>Journal:</strong> ${esc(journal)}${esc(vol)}${esc(no)}${esc(pp)}${yr ? ` · <strong>Year:</strong> ${esc(yr)}` : ''}</p>
          <p>
            ${doi ? `DOI: <a href="${esc(doiURL(doi))}" target="_blank" rel="noopener">${esc(doi)}</a>` : ''}
            ${doi ? ` · <a href="${esc(mrLookup(doi))}" target="_blank" rel="noopener">MR lookup</a>` : ''}
          </p>
        </div>`;
    }).join('') || '<p>No records found in papers.bib.</p>';

    await fs.mkdir('papers', { recursive: true });
    await fs.writeFile('papers/index.html', header + html + footer, 'utf8');
    console.log(`Generated papers/index.html with ${items.length} entries from BibTeX.`);
  } catch (e) {
    console.error('Build failed:', e);
    const fallback = `<p>Could not read ${BIB_PATH}. Make sure you uploaded a BibTeX export from zbMATH.</p>`;
    await fs.mkdir('papers', { recursive: true });
    await fs.writeFile('papers/index.html', header + fallback + footer, 'utf8');
    process.exitCode = 0;
  }
})();
