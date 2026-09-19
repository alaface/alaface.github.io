#!/usr/bin/env python3
"""Refresh public metadata and render static pages; no third-party dependencies."""
import argparse
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
from urllib.parse import urlencode, quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
AUTHOR = 'laface.antonio'
ZB_PROFILE = 'https://zbmath.org/?q=ai%3Alaface.antonio'
ARXIV_PROFILE = 'https://arxiv.org/search/math?searchtype=author&query=Laface%2C+A&order=-announced_date_first&size=200'
NS = {'a': 'http://www.w3.org/2005/Atom', 'r': 'http://arxiv.org/schemas/atom', 'o': 'http://a9.com/-/spec/opensearch/1.1/'}

def clean(value):
    return ' '.join(str(value or '').split())

def esc(value):
    return escape(str(value or ''), quote=True)

def safe_url(value):
    value = clean(value)
    return value if urlparse(value).scheme in ('https', 'http') else ''

def normalize(value):
    value = unicodedata.normalize('NFKD', value).lower()
    value = re.sub(r'\\[a-z]+', '', value)
    return re.sub(r'[^a-z0-9]', '', value)

def arxiv_id(value):
    return re.sub(r'v\d+$', '', value.split('/abs/')[-1].replace('arXiv:', ''))

def fetch(url):
    headers = {'User-Agent': 'AntonioLafaceHomepage/1.0 (https://alaface.github.io)', 'Accept': 'application/atom+xml' if urlparse(url).hostname in ('export.arxiv.org', 'arxiv.org') else 'application/json'}
    if urlparse(url).hostname == 'api.github.com' and os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:
                return response.read()
        except HTTPError as error:
            if error.code < 500 and error.code != 429:
                raise
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))

def parse_zbmath(records):
    items = []
    for record in records:
        authors = record.get('contributors', {}).get('authors', [])
        if not any(AUTHOR in a.get('codes', []) for a in authors):
            continue
        if record.get('database') == 'arXiv' or not (record.get('document_type') or {}).get('code'):
            continue
        title = clean((record.get('title') or {}).get('title'))
        if not title:
            raise ValueError('Missing zbMATH title')
        links = record.get('links') or []
        names = []
        for author in authors:
            name = clean(author.get('name'))
            if ', ' in name:
                family, given = name.split(', ', 1)
                name = given + ' ' + family
            names.append(name)
        items.append({'id': str(record['id']), 'title': title, 'authors': names,
                      'year': str(record.get('year') or ''),
                      'citation': clean((record.get('source') or {}).get('source')),
                      'url': safe_url(record.get('zbmath_url')),
                      'doi': next((clean(x['identifier']) for x in links if x.get('type') == 'doi'), ''),
                      'arxiv': [arxiv_id(x['identifier']) for x in links if x.get('type') == 'arxiv'],
                      'license': record.get('license') or []})
    if not items:
        raise ValueError('No verified publications returned by zbMATH')
    return sorted({p['id']: p for p in items}.values(), key=lambda p: (p['year'], p['title']), reverse=True)

def get_publications():
    records, page = [], 0
    while True:
        url = 'https://api.zbmath.org/v1/document/_search?' + urlencode({'search_string': 'ai:' + AUTHOR, 'page': page, 'results_per_page': 100})
        response = json.loads(fetch(url))
        status = response.get('status', {})
        batch = response.get('result')
        if status.get('execution_bool') is not True or not isinstance(batch, list):
            raise ValueError('Invalid zbMATH API response')
        records.extend(batch)
        total = int(status['nr_total_results'])
        if len(records) >= total:
            break
        if not batch:
            raise ValueError('Incomplete zbMATH pagination')
        page += 1
        time.sleep(1)
    return parse_zbmath(records)

def parse_arxiv(raw):
    root = ET.fromstring(raw)
    if root.tag != '{' + NS['a'] + '}feed':
        raise ValueError('Invalid arXiv feed')
    items = []
    for entry in root.findall('a:entry', NS):
        identifier = entry.findtext('a:id', '', NS)
        if '/api/errors' in identifier:
            raise ValueError('arXiv returned an API error')
        authors = [clean(n.text) for n in entry.findall('a:author/a:name', NS)]
        if not any(normalize(name) in ('antoniolaface', 'alaface') for name in authors):
            continue
        title = clean(entry.findtext('a:title', '', NS))
        published = entry.findtext('a:published', '', NS)
        if not title or not re.match(r'^\d{4}-\d{2}-\d{2}T', published) or '/abs/' not in identifier:
            raise ValueError('Incomplete arXiv entry')
        items.append({'id': arxiv_id(identifier), 'title': title, 'authors': authors,
                      'year': published[:4], 'published': published[:10],
                      'updated': entry.findtext('a:updated', '', NS)[:10],
                      'summary': clean(entry.findtext('a:summary', '', NS)),
                      'journal': clean(entry.findtext('r:journal_ref', '', NS)),
                      'doi': clean(entry.findtext('r:doi', '', NS))})
    return items, int(root.findtext('o:totalResults', '', NS)), len(root.findall('a:entry', NS))

def get_arxiv():
    items, start = [], 0
    while True:
        url = 'https://export.arxiv.org/api/query?' + urlencode({'search_query': 'au:Laface', 'start': start, 'max_results': 100, 'sortBy': 'submittedDate', 'sortOrder': 'descending'})
        try:
            raw = fetch(url)
        except HTTPError as error:
            if error.code != 406:
                raise
            # arXiv exposes the same public Atom API on both official hosts.
            # Some export frontends reject otherwise valid content negotiation.
            time.sleep(3)
            raw = fetch(url.replace('https://export.arxiv.org/', 'https://arxiv.org/'))
        batch, total, count = parse_arxiv(raw)
        items.extend(batch)
        start += count
        if start >= total:
            break
        if count == 0:
            raise ValueError('Incomplete arXiv pagination')
        time.sleep(3)
    if not items:
        raise ValueError('No verified arXiv records returned')
    return sorted({p['id']: p for p in items}.values(), key=lambda p: (p['published'], p['id']), reverse=True)

def parse_repositories(records):
    items = [{'name': r['name'], 'url': safe_url(r['html_url']),
              'description': clean(r.get('description')), 'fork': bool(r.get('fork')),
              'archived': bool(r.get('archived'))}
             for r in records if r.get('owner', {}).get('login', '').lower() == 'alaface' and r.get('private') is False]
    if not items:
        raise ValueError('No public repositories returned')
    return sorted({r['name']: r for r in items}.values(), key=lambda r: r['name'].lower())

def get_repositories():
    records, page = [], 1
    while True:
        batch = json.loads(fetch('https://api.github.com/users/alaface/repos?' + urlencode({'type': 'owner', 'per_page': 100, 'page': page})))
        if not isinstance(batch, list):
            raise ValueError('Invalid GitHub response')
        records.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return parse_repositories(records)

def write_cache(name, items, source):
    DATA.mkdir(exist_ok=True)
    path = DATA / (name + '.json')
    payload = {'source': source, 'updated': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'items': items}
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)
    return payload

def refresh(name, getter, source, offline=False):
    path = DATA / (name + '.json')
    if offline:
        return json.loads(path.read_text()), None
    try:
        return write_cache(name, getter(), source), None
    except Exception as error:
        if isinstance(error, HTTPError):
            detail = clean(error.read(400).decode('utf-8', errors='replace'))
            error = RuntimeError(f'{error}: {detail}')
        print(f'::warning::{name}: {error}; keeping the last successful snapshot.', file=sys.stderr)
        if not path.exists():
            raise RuntimeError(f'{name}: no saved snapshot available') from error
        return json.loads(path.read_text()), str(error)

def page(title, active, body, math=False):
    nav = [('papers', 'Publications'), ('arxiv', 'Preprints'), ('software', 'Software'), ('book', 'Book')]
    links = ''.join(f'<a href="/{slug}/"' + (' aria-current="page"' if slug == active else '') + f'>{label}</a>' for slug, label in nav)
    math_scripts = '<script src="/assets/math.js"></script><script defer src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-chtml.js"></script>' if math else ''
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — Antonio Laface</title><meta name="description" content="Antonio Laface, Full Professor of Mathematics at Universidad de Concepción. Publications, preprints and mathematical software.">
<link rel="stylesheet" href="/assets/css/style.css">{math_scripts}<script defer src="/assets/filter.js"></script></head>
<body><a class="skip-link" href="#main">Skip to content</a><header><nav aria-label="Main navigation"><a class="brand" href="/">Antonio Laface</a>{links}</nav></header>
<main id="main">{body}</main><footer><span>Antonio Laface · Universidad de Concepción</span><a href="mailto:antonio.laface@gmail.com">antonio.laface@gmail.com</a></footer></body></html>\n'''.replace('><', '>\n<')

def updated(data):
    date = datetime.fromisoformat(data['updated']).strftime('%d %B %Y, %H:%M UTC')
    return f'<p class="meta">Updated daily · Last synchronized <time datetime="{esc(data["updated"])}">{date}</time></p>'

def search_box(count, label):
    return f'<label class="filter"><span>{label}</span><input type="search" data-filter placeholder="Type to filter…"></label><p class="count" data-count aria-live="polite">{count} entries</p><p data-empty hidden>No matching entries.</p>'

def link(url, label):
    url = safe_url(url)
    return f'<a href="{esc(url)}">{esc(label)}</a>' if url else ''

def publication_entry(p):
    doi = 'https://doi.org/' + quote(p['doi'], safe='/') if p['doi'] else ''
    links = [link(p['url'], 'zbMATH'), link(doi, 'DOI')]
    if p['doi']:
        links.append(link('https://mathscinet.ams.org/mathscinet/search/publications.html?' + urlencode({'pg1': 'DOI', 's1': p['doi']}), 'MathSciNet'))
    links.extend(link('https://arxiv.org/abs/' + aid, 'arXiv') for aid in p['arxiv'])
    searchable = ' '.join([p['title'], *p['authors'], p['year'], p['citation']])
    return f'<li class="entry" data-search="{esc(searchable)}"><h3>{link(doi or p["url"], p["title"])}</h3><p>{esc(", ".join(p["authors"]))}</p><p>{esc(p["citation"])}</p><div class="entry-links">{"".join(links)}</div></li>'

def arxiv_entry(p):
    url = 'https://arxiv.org/abs/' + p['id']
    searchable = ' '.join([p['title'], *p['authors'], p['year'], p['id']])
    journal = f'<p>{esc(p["journal"])}</p>' if p['journal'] else ''
    return f'<li class="entry" data-search="{esc(searchable)}"><h3>{link(url, p["title"])}</h3><p>{esc(", ".join(p["authors"]))}</p><p>arXiv:{esc(p["id"])} · Submitted {esc(p["published"])} · Revised {esc(p["updated"])}</p>{journal}<div class="entry-links">{link(url, "arXiv")}{link("https://arxiv.org/pdf/" + p["id"], "PDF")}</div><details><summary>Abstract</summary><p>{esc(p["summary"])}</p></details></li>'

def groups(items, renderer):
    years = sorted({p['year'] for p in items}, reverse=True)
    return ''.join(f'<section class="year-group"><h2>{esc(year)}</h2><ul class="entries">' + ''.join(renderer(p) for p in items if p['year'] == year) + '</ul></section>' for year in years)

def partition_arxiv(items, publications):
    ids = {aid for p in publications for aid in p['arxiv']}
    titles = {normalize(p['title']) for p in publications}
    dois = {p['doi'].lower() for p in publications if p['doi']}
    preprints, published = [], []
    for p in items:
        known = p['id'] in ids or normalize(p['title']) in titles or bool(p['doi'] and p['doi'].lower() in dois) or bool(p['journal'])
        (published if known else preprints).append(p)
    return preprints, published

def render(publications, arxiv, repositories):
    home = '''<section class="hero"><div><p class="eyebrow">Mathematics · Universidad de Concepción</p><h1>Antonio Laface</h1><p class="position">Full Professor</p><p class="affiliation">Departamento de Matemática<br>Facultad de Ciencias Físicas y Matemáticas<br>Universidad de Concepción, Chile</p><p class="contact"><a href="mailto:antonio.laface@gmail.com">antonio.laface@gmail.com</a><br><a href="tel:+56412203173">+56 41 220 3173</a><br>Casilla 160-C, Concepción, Chile</p></div><figure><img src="/assets/home.jpg" width="600" height="449" alt="Stingrays swimming in clear turquoise water" fetchpriority="high"></figure></section>
<section class="section-links" aria-label="Explore"><a href="/papers/"><strong>Publications ↗</strong><span>Articles, chapters and books</span></a><a href="/arxiv/"><strong>Preprints ↗</strong><span>Recent manuscripts on arXiv</span></a><a href="/software/"><strong>Software ↗</strong><span>Code and computational resources</span></a><a href="/book/"><strong>Cox Rings ↗</strong><span>Cambridge Studies in Advanced Mathematics</span></a></section>
<p class="meta"><a href="/halphen-surfaces/">Explore the catalogue of extremal Halphen surfaces →</a></p>'''
    (ROOT / 'index.html').write_text(page('Home', '', home))
    pubs = publications['items']
    body = '<div class="page-heading"><p class="eyebrow">Research</p><h1>Publications</h1><p class="lead">Articles, book chapters and books, from most recent to earliest.</p>' + updated(publications) + f'<div class="source-links">{link(ZB_PROFILE, "Author profile on zbMATH Open")}</div></div>'
    body += search_box(len(pubs), 'Search publications by title, author or year') + groups(pubs, publication_entry)
    body += '<p class="source-note">Bibliographic metadata: ' + link(ZB_PROFILE, 'zbMATH Open') + ' / FIZ Karlsruhe, under ' + link('https://creativecommons.org/licenses/by-sa/4.0/', 'CC BY-SA 4.0') + '. Metadata selected and reformatted; no reviews are reproduced.</p>'
    (ROOT / 'papers/index.html').write_text(page('Publications', 'papers', body, True))
    preprints, published = partition_arxiv(arxiv['items'], pubs)
    body = '<div class="page-heading"><p class="eyebrow">Research</p><h1>Preprints</h1><p class="lead">Recent manuscripts and the arXiv archive.</p>' + updated(arxiv) + f'<div class="source-links">{link(ARXIV_PROFILE, "All submissions on arXiv")}{link("https://alaface.github.io/papers/", "Publications")}</div></div>'
    body += search_box(len(arxiv['items']), 'Search manuscripts by title, author, year or arXiv ID')
    body += f'<h2>Preprints <span class="count">({len(preprints)})</span></h2>' + groups(preprints, arxiv_entry)
    body += f'<details data-archive><summary>Published work on arXiv ({len(published)})</summary>' + groups(published, arxiv_entry) + '</details>'
    body += '<p class="source-note">Source: arXiv. Publication status follows the available bibliographic records.</p>'
    (ROOT / 'arxiv/index.html').write_text(page('Preprints', 'arxiv', body, True))
    repos = repositories['items']
    body = '<div class="page-heading"><p class="eyebrow">Computational resources</p><h1>Software</h1><p class="lead">Research code, mathematical software and interactive catalogues.</p></div><section class="feature"><div><h2>Extremal Halphen surfaces</h2><p>A catalogue of 26 explicit plane models, with marked points, component classes and verification notes.</p><a href="/halphen-surfaces/">Open the catalogue →</a></div><div><h2>Jacobian elliptic surfaces</h2><p>Exact computations and verification material for semiampleness on Jacobian elliptic surfaces.</p><a href="https://github.com/alaface/jacobian-semiampleness">View the project →</a></div></section><h2>GitHub repositories</h2><p>All public repositories on <a href="https://github.com/alaface?tab=repositories">github.com/alaface</a>.</p>' + updated(repositories)
    body += search_box(len(repos), 'Search repositories') + '<div class="repository-list">'
    for r in repos:
        badges = (' · Fork' if r['fork'] else '') + (' · Archived' if r['archived'] else '')
        description = f'<p>{esc(r["description"])}</p>' if r['description'] else ''
        body += f'<article class="repository" data-search="{esc(r["name"] + " " + r["description"])}"><h3>{link(r["url"], r["name"])} ↗</h3>{description}<p class="meta">GitHub{badges}</p></article>'
    body += '</div>'
    (ROOT / 'software/index.html').write_text(page('Software', 'software', body))
    print(f'Rendered {len(pubs)} publications, {len(preprints)} preprints, {len(published)} archived arXiv papers and {len(repos)} public repositories.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='Render saved snapshots without network access')
    args = parser.parse_args()
    sources = [('publications', get_publications, ZB_PROFILE), ('arxiv', get_arxiv, ARXIV_PROFILE), ('repositories', get_repositories, 'https://github.com/alaface?tab=repositories')]
    data, errors = [], []
    for name, getter, source in sources:
        snapshot, error = refresh(name, getter, source, args.offline)
        data.append(snapshot)
        if error:
            errors.append(name)
    render(*data)
    return 1 if errors else 0

if __name__ == '__main__':
    sys.exit(main())
