"""Public mode regression fixtures; these are not real contest questions."""
import contextlib
import io
import json
from html import escape
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from test_archive_client import Clock, Opener, Reply
import archive_client
from archive_client import ClientError, ORIGIN, PublicArchiveClient, PublicHtml
from progress_store import ProgressStore
from test_progress_store import outcome


def listing(slugs=("fixture-a", "fixture-b", "fixture-c"), next_page=False):
    rows = []
    for slug in slugs:
        rows.append(f'''<div class="vh-problem-row">
          <a class="vh-problem-row__main" href="/problems/{slug}">
          <strong><span class="vh-problem-row__number">1.</span> {slug}
          <em class="vh-problem-row__rating">1000</em></strong></a>
          <span class="vh-problem-row__source">TEST FIXTURE CPC</span>
          <div class="vh-problem-row__tags"><em>implementation</em></div>
          </div>''')
    return "".join(rows) + ('<a data-problem-page="2">Next</a>' if next_page else '')


def detail(slug="fixture-a", scope="/ test"):
    return f'''<span class="vh-problems-eyebrow">CPC problem</span>
      <h1>1. {slug}</h1><div class="vh-problem-limits">
      <div><span>Time limit</span><strong>2 sec {scope}</strong></div>
      <div><span>Memory limit</span><strong>256 MB</strong></div>
      <div><span>Source</span><strong>TEST FIXTURE CPC</strong></div></div>
      <article class="vh-problem-statement">
      <section><h2>Statement</h2><div>{escape('Given $n$. <b>Keep markup</b>')}</div></section>
      <section><h2>Input</h2><div>An integer n.</div></section>
      <section><h2>Output</h2><div>Print n.</div></section>
      <section><h2>Constraints</h2><div>1 &lt;= n &lt;= 10</div></section>
      <section><h2>Example 1</h2><pre id="input-1"> 1\n</pre><pre id="output-1">1\n</pre></section>
      </article><script>pretendMaliciousCode()</script>'''


class HtmlOpener(Opener):
    def open(self, req, timeout):
        response = super().open(req, timeout)
        if isinstance(response, str):
            return Reply(None, raw=response.encode(), content_type="text/html", url=req.full_url)
        return response


class PublicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = Clock()

    def tearDown(self):
        self.tmp.cleanup()

    def client(self, responses):
        opener = HtmlOpener(responses)
        client = PublicArchiveClient(Path(self.tmp.name) / ".client", opener=opener,
                                     clock=self.clock.time, sleep=self.clock.sleep)
        return client, opener

    def test_no_key_or_environment_read_and_get_only(self):
        with patch.object(archive_client.os, "environ", None):
            client, opener = self.client([listing()])
            result = client.call("search", {"limit": 2})
        self.assertEqual(len(result["items"]), 2)
        request = opener.calls[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertTrue(request.full_url.startswith(ORIGIN + "/problems?"))
        self.assertIsNone(request.data)
        self.assertFalse(any(k.lower() in {"authorization", "cookie"} for k in request.headers))

    def test_pagination_keeps_remaining_questions_on_same_page(self):
        client, opener = self.client([listing()])
        first = client.call("search", {"limit": 1})
        second = client.call("search", {"limit": 1, "after": first["next_cursor"]})
        third = client.call("search", {"limit": 1, "after": second["next_cursor"]})
        self.assertEqual([r["items"][0]["title"] for r in (first, second, third)],
                         ["fixture-a", "fixture-b", "fixture-c"])
        self.assertIsNone(third["next_cursor"])
        self.assertEqual(len(opener.calls), 1)

    def test_next_public_page_cursor_and_seen_filter(self):
        client, opener = self.client([listing(("fixture-a",), True), listing(("fixture-b",))])
        first = client.call("search", {"limit": 1})
        found = client.candidates({"limit": 1}, seen={first["items"][0]["id"]})
        self.assertEqual(found[0]["title"], "fixture-b")
        self.assertEqual(len(opener.calls), 2)
        self.assertIn("page=2", opener.calls[1].full_url)

    def test_statement_preserves_markup_samples_limits_and_attribution(self):
        client, opener = self.client([listing(), detail(scope="total")])
        selected = client.call("search", {"limit": 1})["items"][0]
        problem = client.call("problem", {"id": selected["id"]})["problem"]
        self.assertEqual(problem["statement"]["body"], 'Given $n$. <b>Keep markup</b>')
        self.assertEqual(problem["statement"]["samples"], [{"input": " 1\n", "output": "1\n"}])
        self.assertEqual(problem["limits"], {"time_ms": 2000, "time_scope": "all_tests", "memory_mb": 256})
        self.assertEqual(problem["contest"]["name"], "TEST FIXTURE CPC")
        self.assertEqual(len(problem["content_sha256"]), 64)
        self.assertNotIn("pretendMalicious", json.dumps(problem))
        self.assertEqual(len(opener.calls), 2)

    def test_selected_statement_is_fresh_not_listing_cache(self):
        client, opener = self.client([listing(), detail(), detail().replace('Print n.', 'Print n twice.')])
        pid = client.call("search", {"limit": 1})["items"][0]["id"]
        a = client.call("problem", {"id": pid})["problem"]
        b = client.call("problem", {"id": pid})["problem"]
        self.assertNotEqual(a["content_sha256"], b["content_sha256"])
        self.assertEqual(len(opener.calls), 3)

    def test_missing_problem_is_not_guessed(self):
        client, opener = self.client([])
        with self.assertRaisesRegex(ClientError, "search first"):
            client.call("problem", {"id": "a" * 32})
        self.assertEqual(opener.calls, [])

    def test_changed_identity_or_attribution_is_rejected(self):
        for html in (detail("different"), detail().replace('TEST FIXTURE CPC', 'different contest')):
            with self.subTest(html=html[-80:]):
                client, _ = self.client([listing(), html])
                pid = client.call("search", {"limit": 1})["items"][0]["id"]
                with self.assertRaises(ClientError):
                    client.call("problem", {"id": pid})

    def test_bad_structure_or_rating_is_not_empty_pool(self):
        for html in ('<html>Login required</html>', listing().replace('1000', 'bad')):
            client, _ = self.client([html])
            with self.assertRaises(ClientError):
                client.call("search", {"limit": 1})

    def test_redirect_non_html_and_oversize_are_rejected(self):
        for reply in (Reply(None, raw=b'x', content_type='text/html', url='https://evil.example/'),
                      Reply(None, raw=b'{}', url=ORIGIN + '/problems?collection=cpc&sort=number&page=1'),
                      'x' * (1024 * 1024 + 1)):
            client, _ = self.client([reply])
            with self.assertRaises(ClientError):
                client.call("search", {"limit": 1})

    def test_unlisted_path_and_cursor_and_deep_markup_rejected(self):
        client, opener = self.client([])
        for path in ('/problems-evil', '/problems/a/editorial', '/problems/../admin', '/problems/a#x'):
            with self.assertRaises(ClientError):
                client.page(path)
        with self.assertRaises(ClientError):
            client.call("search", {"after": 'f' * 32})
        with self.assertRaises(ClientError):
            PublicHtml('<div>' * 128)
        self.assertEqual(opener.calls, [])

    def test_public_error_does_not_modify_progress(self):
        store = ProgressStore(self.tmp.name)
        store.init()
        before = store.path.read_bytes()
        client, _ = self.client([HTTPError(ORIGIN, 403, 'Forbidden', {}, None)])
        with self.assertRaisesRegex(ClientError, '403'):
            client.call('search', {'limit': 1})
        self.assertEqual(store.path.read_bytes(), before)

    def test_public_assignment_outcome_and_resume(self):
        store = ProgressStore(self.tmp.name)
        store.init()
        client, _ = self.client([listing()])
        selected = client.candidates({'limit': 1})[0]
        store.assign({'problem': selected, 'topic': 'implementation', 'stage': 1, 'mode': 'topic'})
        resumed = ProgressStore(self.tmp.name).resume()
        self.assertEqual(resumed['current_problem']['problem']['id'], selected['id'])
        store.record(outcome())
        self.assertEqual(ProgressStore(self.tmp.name).resume()['totals']['independent_solved'], 1)

    def test_default_cli_selects_public_and_never_api(self):
        client, _ = self.client([listing()])
        argv = ['archive_client.py', 'search', '--state-dir', self.tmp.name, '--limit', '1']
        output = io.StringIO()
        with patch('sys.argv', argv), patch.object(archive_client, 'PublicArchiveClient', return_value=client), \
                patch.object(archive_client, 'ArchiveClient', side_effect=AssertionError('API must not run')), \
                contextlib.redirect_stdout(output):
            archive_client.main()
        self.assertEqual(json.loads(output.getvalue())['items'][0]['title'], 'fixture-a')


if __name__ == '__main__':
    unittest.main()
