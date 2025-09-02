// Build papers/index.html from zbMATH Open (author: "Laface, Antonio")
// Run in GitHub Actions (node >=18, uses global fetch)
const fs = require('node:fs/promises');

const AUTHOR = 'Laface, Antonio';
const ROWS = 200;

const ZB_URL = 'https://api.zbmath.org/v1/document?' + new URLSearchParams({
  q: `au:"${AUTHOR}"`,
  size: String(ROWS),
  sort: 'year.desc'
}).toString();

const esc = (s='') => s.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
const yearOf = it => it.year || it?.published?.year || '';
const doiURL = doi => doi ? `https://doi.org/${encodeURIComponent(doi)}` : '';
const mrLookup = doi => doi ? `https://mathscinet.ams.org/mathscinet/relay?mr=Lookup&url=https://mathscinet.ams.org/mathscinet/search/publications.html?pg1=DOI&s1=${encodeURIComponent(doi)}` : '';
const zbDocURL = id => id ? `https://zbmath.org/?q=an:${encodeURIComponent(id)}` : '';

// strict match: keep only items that explicitly list "Laface, Antonio"
function includesExactZbName(list){
  return (list||[]).some(a => {
    const name = typeof a === 'string' ? a : (a.name || [a.first, a.last].filter(Boolean).join(', '));
    const n = (name||'').trim().toLowerCase();
    return n === 'laface, antonio' || n === 'antonio laface';
  });
}

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
  <p>This page is generated automatically from zbMATH Open (author: ${esc(AUTHOR)}).</p>
  <div id="papers" class="card">
`;

const footer = `
  </div>
  <p style="font-size:.95em;color:#57606a;margin-top:1rem">
    Data source: zbMATH Open · Query: au:"${esc(AUTHOR)}"
  </p>
</main>
<footer>© <span id="y"></span> Antonio Laface</footer>
<script>document.getElementById('y').textContent = new Date().getFullYear();</script>
</body></html>`;

(async () => {
  try {
    const r = await fetch(ZB_URL, { headers: { 'User-Agent': 'alaface-pages/1.0 (mailto:alaface@udec.cl)' } });
    if (!r.ok) throw new Error(`zbMATH HTTP ${r.status}`);
    const data = await r.json();
    const raw = data?.data || data?.hits || data?.documents || data?.items || [];
    const items = raw.filter(it => includesExactZbName(it.authors || it.author || it.au));

    const html = items.map(it => {
      const title = it.title || (Array.isArray(it.ti) ? it.ti[0] : '(untitled)');
      const yr = yearOf(it);
      const list = it.authors || it.author || it.au || [];
      const authors = list.map(a => typeof a === 'string' ? a : (a.name || [a.first, a.last].filter(Boolean).join(' '))).join(', ');
      const journal = it.journal?.title || it.journal_title || it.journal || '';
      const vol = it.volume || it.vol || '';
      const issue = it.issue || it.no || '';
      const page = it.pages || it.page || '';
      const citeTail = [vol && ` ${esc(vol)}`, issue && `(${esc(issue)})`, page && `:${esc(page)}`].filter(Boolean).join('');
      const doi = it.doi || (Array.isArray(it.dois) ? it.dois[0] : '');
      const url = doiURL(doi) || it.url || it.link || zbDocURL(it.id || it.an);

      return `
        <div class="card">
          <h3 style="margin-top:0"><a href="${esc(url)}" target="_blank" rel="noopener">${esc(title)}</a></h3>
          <p><strong>Authors:</strong> ${esc(authors)}</p>
          <p><strong>Journal:</strong> ${esc(journal)}${citeTail ? esc(citeTail) : ''}${yr ? ` · <strong>Year:</strong> ${esc(String(yr))}` : ''}</p>
          <p>
            ${doi ? `DOI: <a href="${esc(doiURL(doi))}" target="_blank" rel="noopener">${esc(doi)}</a>` : ''}
            ${doi ? ` · <a href="${esc(mrLookup(doi))}" target="_blank" rel="noopener">MR lookup</a>` : ''}
            ${it.an ? ` · <a href="${esc(zbDocURL(it.an))}" target="_blank" rel="noopener">zbMATH</a>` : ''}
          </p>
        </div>`;
    }).join('') || '<p>No records found via zbMATH.</p>';

    await fs.mkdir('papers', { recursive: true });
    await fs.writeFile('papers/index.html', header + html + footer, 'utf8');
    console.log(`Generated papers/index.html with ${items.length} entries (zbMATH).`);
  } catch (e) {
    console.error('Build failed:', e);
    const fallback = `<p>Failed to fetch zbMATH right now. Please try again later.</p>`;
    await fs.mkdir('papers', { recursive: true });
    await fs.writeFile('papers/index.html', header + fallback + footer, 'utf8');
    process.exitCode = 0;
  }
})();
