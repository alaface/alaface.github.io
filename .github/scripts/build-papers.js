// Build papers/index.html from Crossref using your ORCID
// Run in GitHub Actions (node >=18)
import fs from 'node:fs/promises';

const ORCID = '0000-0001-6926-8249';
const ROWS = 200;
const CROSSREF_URL = `https://api.crossref.org/works?query.author=Antonio%20Laface&rows=${ROWS}&sort=issued&order=desc&select=title,author,DOI,URL,issued,container-title,volume,issue,page`;

function esc(s=''){ return s.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m])); }
function yearOf(it){ return it?.issued?.['date-parts']?.[0]?.[0] || ''; }
function doiURL(doi){ return doi ? `https://doi.org/${encodeURIComponent(doi)}` : ''; }
function mrLookup(doi){ return doi ? `https://mathscinet.ams.org/mathscinet/relay?mr=Lookup&url=https://mathscinet.ams.org/mathscinet/search/publications.html?pg1=DOI&s1=${encodeURIComponent(doi)}` : ''; }

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
  <p>This page is generated automatically from Crossref (filtered by my ORCID).</p>
  <div id="papers" class="card">
`;

const footer = `
  </div>
  <p style="font-size:.95em;color:#57606a;margin-top:1rem">Data source: Crossref · ORCID ${ORCID}</p>
</main>
<footer>© <span id="y"></span> Antonio Laface</footer>
<script>document.getElementById('y').textContent = new Date().getFullYear();</script>
</body></html>`;

try {
  const r = await fetch(CROSSREF_URL, { headers: { 'User-Agent': 'alaface-pages/1.0 (mailto:alaface@udec.cl)' }});
  if (!r.ok) throw new Error(`Crossref HTTP ${r.status}`);
  const j = await r.json();
  let items = j?.message?.items || [];

  // filtro di sicurezza: tieni solo record dove l’autore include “Antonio Laface” o il tuo ORCID
  items = items.filter(it => {
    const list = it.author || [];
    return list.some(a =>
      (a.ORCID && a.ORCID.replace(/^https?:\/\/orcid\.org\//,'') === ORCID) ||
      ((a.given||'').trim().toLowerCase()==='antonio' && (a.family||'').trim().toLowerCase()==='laface')
    );
  });

  const html = items.map(it => {
    const title = it.title?.[0] || '(untitled)';
    const yr = yearOf(it);
    const authors = (it.author||[]).map(a => esc([a.given, a.family].filter(Boolean).join(' '))).join(', ');
    const journal = it['container-title']?.[0] || '';
    const vol = it.volume || '';
    const no = it.issue || '';
    const pp = it.page || '';
    const citeTail = [vol && ` ${esc(vol)}`, no && `(${esc(no)})`, pp && `:${esc(pp)}`].filter(Boolean).join('');
    const doi = it.DOI || '';
    const url = it.URL || doiURL(doi);

    return `
      <div class="card">
        <h3 style="margin-top:0"><a href="${esc(url)}" target="_blank" rel="noopener">${esc(title)}</a></h3>
        <p><strong>Authors:</strong> ${authors}</p>
        <p><strong>Journal:</strong> ${esc(journal)}${citeTail ? esc(citeTail) : ''}${yr ? ` · <strong>Year:</strong> ${esc(String(yr))}` : ''}</p>
        <p>
          ${doi ? `DOI: <a href="${esc(doiURL(doi))}" target="_blank" rel="noopener">${esc(doi)}</a>` : ''}
          ${doi ? ` · <a href="${esc(mrLookup(doi))}" target="_blank" rel="noopener">MR lookup</a>` : ''}
        </p>
      </div>`;
  }).join('') || '<p>No records found via Crossref.</p>';

  await fs.mkdir('papers', { recursive: true });
  await fs.writeFile('papers/index.html', header + html + footer, 'utf8');

  console.log(`Generated papers/index.html with ${items.length} entries.`);
} catch (e) {
  console.error('Build failed:', e);
  // fallback minimale, pagina informativa
  const fallback = `<p>Failed to fetch Crossref right now. Please try again later.</p>`;
  await fs.mkdir('papers', { recursive: true });
  await fs.writeFile('papers/index.html', header + fallback + footer, 'utf8');
  process.exitCode = 0; // non fallire il job: pubblichiamo comunque il fallback
}
