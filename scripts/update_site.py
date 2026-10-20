#!/usr/bin/env python3
"""Refresh public metadata and render static pages; no third-party dependencies."""
import argparse
from datetime import date, datetime, timedelta, timezone
from html import escape
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import time
import unicodedata
from urllib.parse import urlencode, quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = json.loads((ROOT / 'scripts/translations.json').read_text(encoding='utf-8'))
LANGUAGES = {'en': 'English', 'es': 'Español', 'ru': 'Русский', 'de': 'Deutsch'}
DATA = ROOT / 'data'
AUTHOR = 'laface.antonio'
ZB_PROFILE = 'https://zbmath.org/?q=ai%3Alaface.antonio'
ARXIV_PROFILE = 'https://arxiv.org/search/math?searchtype=author&query=Laface%2C+A&order=-announced_date_first&size=200'
NS = {'a': 'http://www.w3.org/2005/Atom', 'r': 'http://arxiv.org/schemas/atom', 'o': 'http://a9.com/-/spec/opensearch/1.1/'}
ARXIV_MAX_STALE = timedelta(days=7)

class ArxivUnavailable(RuntimeError):
    """All official arXiv API requests failed temporarily."""

def temporary_arxiv_error(error):
    if isinstance(error, HTTPError):
        return error.code in (406, 408, 429) or 500 <= error.code < 600
    return isinstance(error, (URLError, TimeoutError, ConnectionError, subprocess.TimeoutExpired))

def error_detail(error):
    if isinstance(error, HTTPError) and error.fp is not None:
        try:
            detail = clean(error.read(400).decode('utf-8', errors='replace'))
        except (OSError, ValueError):
            return str(error)
        return f'{error}: {detail}' if detail else str(error)
    return str(error)

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
            arxiv_retry = urlparse(url).hostname in ('export.arxiv.org', 'arxiv.org') and error.code in (406, 408)
            if error.code < 500 and error.code != 429 and not arxiv_retry:
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

def fetch_arxiv_with_curl(url):
    # Keep HTTP status and response details: CalledProcessError alone hides them.
    result = subprocess.run(['curl', '--silent', '--show-error', '--location',
                             '--max-time', '30', '--write-out', '\n%{http_code}', url],
                            capture_output=True, check=False, timeout=35)
    if result.returncode:
        detail = clean(result.stderr.decode('utf-8', errors='replace'))
        raise URLError(f'curl exit {result.returncode}: {detail}')
    body, separator, status = result.stdout.rpartition(b'\n')
    if not separator or not re.fullmatch(rb'\d{3}', status):
        raise ValueError('curl returned no HTTP status for arXiv')
    if int(status) != 200:
        raise HTTPError(url, int(status), 'arXiv API request failed', {}, BytesIO(body))
    return body

def fetch_arxiv_page(url):
    urls = [url, url.replace('https://export.arxiv.org/', 'https://arxiv.org/')]
    errors = []
    # The two official Atom endpoints sometimes differ in availability or HTTP
    # negotiation. Keep requests sequential and at least three seconds apart.
    for client, getter in (('urllib', fetch), ('curl', fetch_arxiv_with_curl)):
        for endpoint in urls:
            if errors:
                time.sleep(3)
            try:
                return getter(endpoint)
            except Exception as error:
                if not temporary_arxiv_error(error):
                    raise
                errors.append(f'{urlparse(endpoint).hostname} ({client}): {error_detail(error)}')
    raise ArxivUnavailable('; '.join(errors))

def get_arxiv():
    items, start = [], 0
    while True:
        url = 'https://export.arxiv.org/api/query?' + urlencode({'search_query': 'au:Laface', 'start': start, 'max_results': 100, 'sortBy': 'submittedDate', 'sortOrder': 'descending'})
        raw = fetch_arxiv_page(url)
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
        detail = error_detail(error)
        print(f'::warning::{name}: {detail}; keeping the last successful snapshot.', file=sys.stderr)
        if not path.exists():
            raise RuntimeError(f'{name}: no saved snapshot available') from error
        snapshot = json.loads(path.read_text())
        # A short arXiv outage must not fail an otherwise healthy publication.
        # Parsing/programming errors and an outage lasting a week still fail CI.
        if name == 'arxiv' and isinstance(error, ArxivUnavailable) and snapshot.get('items'):
            saved_at = datetime.fromisoformat(snapshot['updated'])
            age = datetime.now(timezone.utc) - saved_at
            if timedelta(0) <= age < ARXIV_MAX_STALE:
                print(f'arxiv: using saved data from {snapshot["updated"]}; will retry on the next run.')
                summary = os.environ.get('GITHUB_STEP_SUMMARY')
                if summary:
                    with open(summary, 'a') as output:
                        output.write(f'### arXiv temporarily unavailable\n\nUsing the last successful snapshot from {snapshot["updated"]}. '
                                     'The next scheduled run will retry. An outage lasting seven days fails the workflow.\n\n')
                return snapshot, None
        return snapshot, detail

def local_path(lang, slug=''):
    return f'/{lang}/' + (f'{slug}/' if slug else '')

def language_picker(lang, active):
    flags, options = [], []
    for code, label in LANGUAGES.items():
        flag = f'<img src="/assets/flags/{code}.svg" width="24" height="16" alt="">'
        if code == lang:
            flags.append(f'<span class="language-flag">{flag}</span>')
        current = ' aria-current="true"' if code == lang else ''
        check = '<span class="language-check" aria-hidden="true">✓</span>' if code == lang else ''
        options.append(f'<li><a href="{local_path(code, active)}" lang="{code}" hreflang="{code}"{current}>{flag}<span>{label}</span>{check}</a></li>')
    label = esc(TRANSLATIONS[lang]['language'] + ': ' + LANGUAGES[lang])
    return f'<details class="language-picker"><summary aria-label="{label}"><span class="language-flags" aria-hidden="true">{"".join(flags)}</span><span class="language-chevron" aria-hidden="true">⌄</span></summary><ul class="language-options" aria-label="{esc(TRANSLATIONS[lang]["language"])}">{"".join(options)}</ul></details>'

def page(title, active, body, math=False, lang='en'):
    t = TRANSLATIONS[lang]
    links = ''.join(f'<a href="{local_path(lang, slug)}"' + (' aria-current="page"' if slug == active else '') + f'>{t[slug]}</a>' for slug in ('papers', 'arxiv', 'software', 'book'))
    switcher = language_picker(lang, active)
    alternates = ''.join(f'<link rel="alternate" hreflang="{code}" href="https://alaface.github.io{local_path(code, active)}">' for code in LANGUAGES)
    default_path = f'/{active}/' if active else '/'
    math_scripts = '<script src="/assets/math.js"></script><script defer src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-chtml.js"></script>' if math else ''
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — Antonio Laface</title><meta name="description" content="{esc(t['description'])}">
<link rel="canonical" href="https://alaface.github.io{local_path(lang, active)}">{alternates}<link rel="alternate" hreflang="x-default" href="https://alaface.github.io{default_path}">
<script src="/assets/language.js"></script><link rel="stylesheet" href="/assets/css/style.css">{math_scripts}<script defer src="/assets/filter.js"></script></head>
<body><a class="skip-link" href="#main">{t['skip']}</a><header><nav aria-label="{t['navigation']}"><a class="brand" href="{local_path(lang)}">Antonio Laface</a>{links}{switcher}</nav></header>
<main id="main">{body}</main><footer><span>Antonio Laface · Universidad de Concepción</span><a href="mailto:antonio.laface@gmail.com">antonio.laface@gmail.com</a></footer></body></html>\n'''.replace('><', '>\n<')

def updated(data, lang='en'):
    stamp = datetime.fromisoformat(data['updated']).astimezone(timezone.utc)
    # Numeric dates avoid relying on the runner's installed system locales.
    date = stamp.strftime('%Y-%m-%d, %H:%M UTC' if lang == 'en' else '%d/%m/%Y, %H:%M UTC' if lang == 'es' else '%d.%m.%Y, %H:%M UTC')
    return f'<p class="meta">{TRANSLATIONS[lang]["updated"]} <time datetime="{esc(data["updated"])}">{date}</time></p>'

def search_box(count, label, lang='en', repositories=False):
    t = TRANSLATIONS[lang]
    field = f'<label class="filter"><span>{label}</span><input type="search" data-filter placeholder="{t["filter"]}"></label>'
    if repositories:
        field = f'<div class="repository-tools">{field}<button class="filter-reset" type="button" data-reset-filter>{t["reset"]}</button></div>'
    count_key, empty_key = ('repositories_count', 'repositories_empty') if repositories else ('count', 'empty')
    return field + f'<p class="count" data-count data-count-template="{esc(t["filtered"])}" aria-live="polite">{t[count_key].format(count=count)}</p><p data-empty hidden>{t[empty_key]}</p>'

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

def arxiv_entry(p, lang='en'):
    t = TRANSLATIONS[lang]
    url = 'https://arxiv.org/abs/' + p['id']
    searchable = ' '.join([p['title'], *p['authors'], p['year'], p['id']])
    journal = f'<p>{esc(p["journal"])}</p>' if p['journal'] else ''
    return f'<li class="entry" data-search="{esc(searchable)}"><h3>{link(url, p["title"])}</h3><p>{esc(", ".join(p["authors"]))}</p><p>arXiv:{esc(p["id"])} · {t["submitted"]} {esc(p["published"])} · {t["revised"]} {esc(p["updated"])}</p>{journal}<div class="entry-links">{link(url, "arXiv")}{link("https://arxiv.org/pdf/" + p["id"], "PDF")}</div><details><summary>{t["abstract"]}</summary><p>{esc(p["summary"])}</p></details></li>'

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

def recent_preprints(items, today=None):
    today = today or datetime.now(timezone.utc).date()
    try:
        cutoff = today.replace(year=today.year - 5)
    except ValueError:  # February 29 has no counterpart five years earlier.
        cutoff = today.replace(year=today.year - 5, day=28)
    return [p for p in items if cutoff <= date.fromisoformat(p['published']) <= today]

def write_page(lang, slug, title, body, math=False):
    html = page(title, slug, body, math, lang)
    target = ROOT / lang / slug / 'index.html'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding='utf-8')
    # Preserve old URLs and readable English content when JavaScript is disabled.
    if lang == 'en':
        legacy = ROOT / slug / 'index.html'
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(html, encoding='utf-8')

def render(publications, arxiv, repositories):
    pubs, repos = publications['items'], repositories['items']
    preprints, published = partition_arxiv(arxiv['items'], pubs)
    preprints = recent_preprints(preprints)
    for lang in LANGUAGES:
        t = TRANSLATIONS[lang]
        home = f'''<section class="hero"><div><p class="eyebrow">{t['mathematics']} · Universidad de Concepción</p><h1>Antonio Laface</h1><p class="position">{t['position']}</p><p class="affiliation"><a href="https://dmat-udec.cl/">{t['department']}</a><br><a href="https://cfm.udec.cl/">{t['faculty']}</a><br><a href="https://www.udec.cl/">Universidad de Concepción</a>, Chile</p><p class="contact"><a href="mailto:antonio.laface@gmail.com">antonio.laface@gmail.com</a><br><a href="tel:+56412203173">+56 41 220 3173</a><br>Casilla 160-C, Concepción, Chile</p><p><a href="https://scholar.google.com/citations?user=ejWJMPkAAAAJ&amp;hl={lang}">Google Scholar ↗</a></p></div><figure><img src="/assets/home.jpg" width="600" height="449" alt="{t['photo']}" fetchpriority="high"></figure></section>
<section class="section-links" aria-label="{t['explore']}"><a href="{local_path(lang, 'papers')}"><strong>{t['papers']} ↗</strong><span>{t['publications_teaser']}</span></a><a href="{local_path(lang, 'arxiv')}"><strong>{t['arxiv']} ↗</strong><span>{t['preprints_teaser']}</span></a><a href="{local_path(lang, 'software')}"><strong>{t['software']} ↗</strong><span>{t['software_teaser']}</span></a><a href="{local_path(lang, 'book')}"><strong>Cox Rings ↗</strong><span>Cambridge Studies in Advanced Mathematics</span></a></section>
<p class="meta"><a href="/halphen-surfaces/">{t['catalogue_teaser']}</a></p>'''
        write_page(lang, '', t['home'], home)
        body = f'<div class="page-heading"><p class="eyebrow">{t["research"]}</p><h1>{t["papers"]}</h1><p class="lead">{t["publications_intro"]}</p>' + updated(publications, lang) + f'<div class="source-links">{link(ZB_PROFILE, t["profile"])}</div></div>'
        body += search_box(len(pubs), t['search_publications'], lang) + groups(pubs, publication_entry)
        body += f'<p class="source-note">{t["bibliography"]} ' + link(ZB_PROFILE, 'zbMATH Open') + f' / FIZ Karlsruhe, {t["license"]} ' + link('https://creativecommons.org/licenses/by-sa/4.0/', 'CC BY-SA 4.0') + f'. {t["metadata_note"]}</p>'
        write_page(lang, 'papers', t['papers'], body, True)
        body = f'<div class="page-heading"><p class="eyebrow">{t["research"]}</p><h1>{t["arxiv"]}</h1><p class="lead">{t["preprints_intro"]}</p>' + updated(arxiv, lang) + f'<div class="source-links">{link(ARXIV_PROFILE, t["all_arxiv"])}<a href="{local_path(lang, "papers")}">{t["papers"]}</a></div><p class="meta">{t["original_language"]}</p></div>'
        body += search_box(len(preprints) + len(published), t['search_preprints'], lang)
        body += f'<h2>{t["arxiv"]} <span class="count">({len(preprints)})</span></h2>' + groups(preprints, lambda p: arxiv_entry(p, lang))
        body += f'<details data-archive><summary>{t["archive"]} ({len(published)})</summary>' + groups(published, lambda p: arxiv_entry(p, lang)) + '</details>'
        body += f'<p class="source-note">{t["arxiv_note"]}</p>'
        write_page(lang, 'arxiv', t['arxiv'], body, True)
        intro = t['repositories_intro'].format(count=len(repos), github=link('https://github.com/alaface?tab=repositories', 'GitHub'))
        body = f'<div class="page-heading"><p class="eyebrow">{t["resources"]}</p><h1>{t["software"]}</h1><p class="lead">{intro}</p></div>'
        body += search_box(len(repos), t['search_repositories'], lang, repositories=True) + '<div class="repository-list">'
        for r in repos:
            badges = (' · ' + t['fork'] if r['fork'] else '') + (' · ' + t['archived'] if r['archived'] else '')
            description = f'<p>{esc(r["description"])}</p>' if r['description'] else ''
            body += f'<article class="repository" data-search="{esc(r["name"] + " " + r["description"])}"><h3>{link(r["url"], r["name"])} ↗</h3>{description}<p class="meta">GitHub{badges}</p></article>'
        body += '</div>' + updated(repositories, lang)
        body += f'<h2>{t["support"]}</h2><section class="feature"><div><h3>{t["halphen"]}</h3><p>{t["halphen_intro"]}</p><a href="/halphen-surfaces/">{t["open_catalogue"]}</a></div><div><h3>{t["jacobian"]}</h3><p>{t["jacobian_intro"]}</p><a href="https://github.com/alaface/jacobian-semiampleness">{t["project"]}</a></div></section>'
        write_page(lang, 'software', t['software'], body)
        body = f'<p class="eyebrow">Cambridge Studies in Advanced Mathematics · 144</p><h1><em>Cox Rings</em></h1><p class="lead">{t["book_authors"]}</p><div class="card"><h2>Cambridge University Press, 2015</h2><p>{t["book_intro"]}</p><div class="source-links">{link("https://doi.org/10.1017/CBO9781139175852", t["publisher"])}{link("https://arxiv.org/abs/1003.4229", "arXiv")}</div></div>'
        write_page(lang, 'book', 'Cox Rings', body)
    print(f'Rendered {len(pubs)} publications, {len(preprints)} preprints, {len(published)} archived arXiv papers and {len(repos)} public repositories in {len(LANGUAGES)} languages.')


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
