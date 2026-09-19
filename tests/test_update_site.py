import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('site_update', ROOT / 'scripts/update_site.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class MetadataTests(unittest.TestCase):
    def test_author_disambiguation_and_old_arxiv_ids(self):
        raw = '''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:o="http://a9.com/-/spec/opensearch/1.1/"><o:totalResults>2</o:totalResults><entry><id>http://arxiv.org/abs/math/0205271v3</id><title>A &amp; B</title><published>2002-05-25T00:00:00Z</published><author><name>Antonio Laface</name></author></entry><entry><id>http://arxiv.org/abs/1234.5678</id><title>Unrelated</title><published>2020-01-01T00:00:00Z</published><author><name>Enrico Laface</name></author></entry></feed>'''
        items, total, count = m.parse_arxiv(raw)
        self.assertEqual((len(items), total, count), (1, 2, 2))
        self.assertEqual(items[0]['id'], 'math/0205271')
        self.assertEqual(items[0]['title'], 'A & B')

    def test_arxiv_requests_atom_instead_of_json(self):
        with patch.object(m, 'urlopen') as request:
            request.return_value.__enter__.return_value.read.return_value = b'feed'
            self.assertEqual(m.fetch('https://export.arxiv.org/api/query?search_query=au%3ALaface'), b'feed')
            self.assertEqual(request.call_args.args[0].get_header('Accept'), 'application/atom+xml')

    def test_arxiv_uses_the_official_alternate_atom_host_on_406(self):
        error = m.HTTPError('https://export.arxiv.org/api/query', 406, 'Not Acceptable', {}, None)
        item = {'id': '1234.5678', 'published': '2026-01-01'}
        with patch.object(m, 'fetch', side_effect=[error, b'feed']) as request, patch.object(m, 'parse_arxiv', return_value=([item], 1, 1)), patch.object(m.time, 'sleep'):
            self.assertEqual(m.get_arxiv(), [item])
            self.assertTrue(request.call_args_list[1].args[0].startswith('https://arxiv.org/api/query?'))

    def test_invalid_feed_is_not_an_empty_success(self):
        with self.assertRaises((ValueError, m.ET.ParseError)):
            m.parse_arxiv('<html>Upstream unavailable</html>')
        raw = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors#incorrect_id_format</id></entry></feed>'
        with self.assertRaises(ValueError):
            m.parse_arxiv(raw)

    def test_zbmath_excludes_preprints_and_unrelated_authors(self):
        base = {'id': 42, 'contributors': {'authors': [{'codes': [m.AUTHOR], 'name': 'Laface, Antonio'}]}, 'database': 'Zbl', 'document_type': {'code': 'j'}, 'title': {'title': 'Paper'}, 'year': '2026'}
        items = m.parse_zbmath([base, dict(base, id=43, database='arXiv'), dict(base, id=44, contributors={'authors': []})])
        self.assertEqual([p['id'] for p in items], ['42'])
        self.assertEqual(items[0]['authors'], ['Antonio Laface'])

    def test_zbmath_pagination(self):
        responses = [json.dumps({'result': [{'id': 1}], 'status': {'execution_bool': True, 'nr_total_results': 2}}).encode(), json.dumps({'result': [{'id': 2}], 'status': {'execution_bool': True, 'nr_total_results': 2}}).encode()]
        with patch.object(m, 'fetch', side_effect=responses) as fetch, patch.object(m, 'parse_zbmath', side_effect=lambda r: r), patch.object(m.time, 'sleep'):
            self.assertEqual(m.get_publications(), [{'id': 1}, {'id': 2}])
            self.assertIn('page=1', fetch.call_args_list[1].args[0])

    def test_repositories_paginate_and_only_publish_public(self):
        def repo(n, private=False):
            return {'name': str(n), 'html_url': f'https://github.com/alaface/{n}', 'owner': {'login': 'alaface'}, 'private': private}
        with patch.object(m, 'fetch', side_effect=[json.dumps([repo(n) for n in range(100)]).encode(), json.dumps([repo(100), repo('secret', True)]).encode()]) as fetch:
            items = m.get_repositories()
            self.assertEqual(len(items), 101)
            self.assertNotIn('secret', [r['name'] for r in items])
            self.assertIn('page=2', fetch.call_args_list[1].args[0])

    def test_failure_preserves_cache_and_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(m, 'DATA', Path(tmp)):
            original = {'items': [{'title': 'Saved paper'}], 'updated': '2020-01-01T00:00:00+00:00'}
            path = Path(tmp) / 'publications.json'
            path.write_text(json.dumps(original))
            before = path.read_bytes()
            snapshot, error = m.refresh('publications', lambda: (_ for _ in ()).throw(ValueError('API unavailable')), 'source')
            self.assertEqual(snapshot, original)
            self.assertTrue(error)
            self.assertEqual(path.read_bytes(), before)

    def test_publication_matching_by_id_doi_title_and_journal(self):
        pubs = [{'arxiv': ['math/1234'], 'title': 'Cox rings', 'doi': '10.1/example'}]
        def paper(id, **kw):
            return dict({'id': id, 'title': 'Different', 'doi': '', 'journal': ''}, **kw)
        items = [paper('math/1234'), paper('2', doi='10.1/example'), paper('3', title='Cox Rings'), paper('4', journal='Journal 1 (2026)'), paper('5')]
        preprints, published = m.partition_arxiv(items, pubs)
        self.assertEqual([p['id'] for p in preprints], ['5'])
        self.assertEqual(len(published), 4)

    def test_untrusted_metadata_is_escaped(self):
        self.assertEqual(m.link('javascript:alert(1)', 'bad'), '')
        self.assertIn('&lt;script&gt;', m.link('https://example.org/', '<script>'))
        self.assertNotIn('<script>', m.link('https://example.org/', '<script>'))

    def test_real_snapshots_are_complete_and_consistent(self):
        pubs = json.loads((ROOT / 'data/publications.json').read_text())['items']
        arxiv = json.loads((ROOT / 'data/arxiv.json').read_text())['items']
        repos = json.loads((ROOT / 'data/repositories.json').read_text())['items']
        self.assertGreater(len(pubs), 0)
        self.assertGreater(len(arxiv), 0)
        self.assertGreater(len(repos), 0)
        self.assertEqual(len({p['id'] for p in arxiv}), len(arxiv))
        self.assertTrue(all(m.safe_url(r['url']) for r in repos))

if __name__ == '__main__':
    unittest.main()
