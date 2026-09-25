import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

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

    def test_arxiv_can_use_curl_when_urllib_negotiation_is_rejected(self):
        error = m.HTTPError('https://export.arxiv.org/api/query', 406, 'Not Acceptable', {}, None)
        item = {'id': '1234.5678', 'published': '2026-01-01'}
        with patch.object(m, 'fetch', side_effect=error), patch.object(m, 'parse_arxiv', return_value=([item], 1, 1)), patch.object(m.time, 'sleep'), patch.object(m.subprocess, 'run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = b'feed\n200'
            self.assertEqual(m.get_arxiv(), [item])
            self.assertEqual(run.call_args.args[0][0], 'curl')
            self.assertIn('--write-out', run.call_args.args[0])

    def test_arxiv_retries_406_before_using_a_fallback(self):
        error = m.HTTPError('https://export.arxiv.org/api/query', 406, 'Not Acceptable', {}, None)
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'feed'
        with patch.object(m, 'urlopen', side_effect=[error, response]) as request, patch.object(m.time, 'sleep') as sleep:
            self.assertEqual(m.fetch('https://export.arxiv.org/api/query'), b'feed')
            self.assertEqual(request.call_count, 2)
            sleep.assert_called_once_with(3)

    def test_arxiv_falls_back_on_server_errors_and_network_timeouts(self):
        for error in (m.HTTPError('url', 503, 'Unavailable', {}, None), m.URLError('connection failed'), TimeoutError('timed out')):
            with self.subTest(error=error), patch.object(m, 'fetch', side_effect=[error, b'feed']), patch.object(m.time, 'sleep'):
                self.assertEqual(m.fetch_arxiv_page('https://export.arxiv.org/api/query'), b'feed')

    def test_arxiv_tries_both_official_hosts_with_curl(self):
        error = m.HTTPError('url', 406, 'Not Acceptable', {}, None)
        with patch.object(m, 'fetch', side_effect=error), patch.object(m, 'fetch_arxiv_with_curl', side_effect=[error, b'feed']) as curl, patch.object(m.time, 'sleep'):
            self.assertEqual(m.fetch_arxiv_page('https://export.arxiv.org/api/query'), b'feed')
            self.assertEqual(curl.call_args.args[0], 'https://arxiv.org/api/query')

    def test_arxiv_outage_preserves_diagnostic_http_status(self):
        error = m.HTTPError('url', 406, 'Not Acceptable', {}, None)
        result = SimpleNamespace(returncode=0, stdout=b'Temporarily unavailable\n503', stderr=b'')
        with patch.object(m, 'fetch', side_effect=error), patch.object(m.subprocess, 'run', return_value=result), patch.object(m.time, 'sleep'):
            with self.assertRaisesRegex(m.ArxivUnavailable, 'HTTP Error 503.*Temporarily unavailable'):
                m.fetch_arxiv_page('https://export.arxiv.org/api/query')

    def test_curl_transport_failure_keeps_stderr(self):
        result = SimpleNamespace(returncode=28, stdout=b'\n000', stderr=b'Operation timed out')
        with patch.object(m.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(m.URLError, 'curl exit 28: Operation timed out'):
                m.fetch_arxiv_with_curl('https://export.arxiv.org/api/query')

    def test_arxiv_does_not_treat_bad_requests_as_temporary(self):
        for status in (400, 401, 403, 404):
            error = m.HTTPError('url', status, 'Invalid request', {}, None)
            with self.subTest(status=status), patch.object(m, 'fetch', side_effect=error), patch.object(m, 'fetch_arxiv_with_curl') as curl:
                with self.assertRaises(m.HTTPError):
                    m.fetch_arxiv_page('https://export.arxiv.org/api/query')
                curl.assert_not_called()

    def test_arxiv_recent_cache_survives_temporary_outage_and_reports_it(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(m, 'DATA', Path(tmp)):
            saved_at = m.datetime.now(m.timezone.utc) - m.timedelta(days=2)
            original = {'items': [{'id': '2609.26521'}], 'updated': saved_at.isoformat()}
            path = Path(tmp) / 'arxiv.json'
            path.write_text(json.dumps(original))
            before = path.read_bytes()
            summary = Path(tmp) / 'summary.md'
            with patch.dict(m.os.environ, {'GITHUB_STEP_SUMMARY': str(summary)}):
                snapshot, error = m.refresh('arxiv', Mock(side_effect=m.ArxivUnavailable('HTTP 406')), 'source')
            self.assertEqual(snapshot, original)
            self.assertIsNone(error)
            self.assertEqual(path.read_bytes(), before)
            self.assertIn(original['updated'], summary.read_text())

    def test_arxiv_stale_empty_or_invalid_data_still_fail(self):
        cases = [
            (7, [{'id': 'saved'}], m.ArxivUnavailable('HTTP 406')),
            (1, [], m.ArxivUnavailable('HTTP 406')),
            (1, [{'id': 'saved'}], ValueError('Invalid arXiv feed')),
            (1, [{'id': 'saved'}], RuntimeError('Programming error')),
        ]
        for days, items, failure in cases:
            with self.subTest(days=days, failure=failure), tempfile.TemporaryDirectory() as tmp, patch.object(m, 'DATA', Path(tmp)):
                saved_at = m.datetime.now(m.timezone.utc) - m.timedelta(days=days)
                path = Path(tmp) / 'arxiv.json'
                path.write_text(json.dumps({'items': items, 'updated': saved_at.isoformat()}))
                before = path.read_bytes()
                snapshot, error = m.refresh('arxiv', Mock(side_effect=failure), 'source')
                self.assertTrue(error)
                self.assertEqual(path.read_bytes(), before)

    def test_arxiv_outage_without_cache_fails(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(m, 'DATA', Path(tmp)):
            with self.assertRaisesRegex(RuntimeError, 'no saved snapshot'):
                m.refresh('arxiv', Mock(side_effect=m.ArxivUnavailable('HTTP 406')), 'source')

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

    def test_preprints_use_a_rolling_five_year_submission_window(self):
        items = [
            {'id': 'old', 'published': '2021-09-18', 'updated': '2026-09-19'},
            {'id': 'boundary', 'published': '2021-09-19'},
            {'id': 'recent', 'published': '2026-09-19'},
            {'id': 'future', 'published': '2026-09-20'},
        ]
        self.assertEqual([p['id'] for p in m.recent_preprints(items, m.date(2026, 9, 19))],
                         ['boundary', 'recent'])

    def test_preprint_window_handles_leap_day(self):
        items = [{'published': '2019-02-27'}, {'published': '2019-02-28'}]
        self.assertEqual(m.recent_preprints(items, m.date(2024, 2, 29)), items[1:])

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
