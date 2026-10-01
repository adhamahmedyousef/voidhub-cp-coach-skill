import copy
from email.message import Message
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.error import HTTPError, URLError

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/voidhub-cp-coach/scripts"
sys.path.insert(0, str(SCRIPTS))
from archive_client import ArchiveClient, ClientError, MAX_BYTES, NoRedirect, validate_response

TOKEN = "fixture_only_not_a_real_key_" + "x" * 32
PID = "1" * 32


def summary(pid=PID):
    return {"id": pid, "title": "TEST FIXTURE — synthetic problem", "contest": {"name": "TEST FIXTURE — not a real CPC", "problem_number": 1},
            "difficulty": {"value": 1000, "source": "voidhub", "kind": "archive_rating"},
            "topics": ["implementation"], "url": "https://voidhub.co/problems/test-fixture-" + pid}


def statement():
    content = {"body": "Given $n \\leq 10$. <img src='/problem-images/fixture'>", "input": "An integer", "output": "An integer",
               "constraints": "$1 \\leq n$", "notes": None, "samples": [{"input": "1\n2\n", "output": "3\n"}]}
    item = {**summary(), "statement": content, "content_format": "stored_markup",
            "limits": {"time_ms": 1000, "time_scope": "per_test", "memory_mb": 256}, "updated_at": None,
            "content_sha256": hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
    return {"api_version": 1, "problem": item}


class Clock:
    def __init__(self): self.now = 1000.0
    def time(self): return self.now
    def sleep(self, seconds): self.now += seconds


class Reply(io.BytesIO):
    def __init__(self, data, operation="search", raw=None, content_type="application/json", url=None):
        super().__init__(raw if raw is not None else json.dumps(data).encode())
        self.status = 200
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.url = url or "https://voidhub.co/api/coach/v1/" + operation
    def geturl(self): return self.url


class Opener:
    def __init__(self, replies): self.replies, self.calls = list(replies), []
    def open(self, req, timeout):
        self.calls.append(req)
        result = self.replies.pop(0)
        if isinstance(result, Exception): raise result
        return result


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = Clock()
    def tearDown(self): self.tmp.cleanup()
    def client(self, replies):
        self.opener = Opener(replies)
        return ArchiveClient(self.tmp.name, TOKEN, self.opener, self.clock.time, self.clock.sleep)
    def error(self, status, retry=None):
        headers = Message()
        if retry: headers["Retry-After"] = retry
        return HTTPError("https://voidhub.co/api/coach/v1/search", status, "fixture", headers, io.BytesIO(b"{}"))

    def test_success_is_post_and_does_not_store_secret(self):
        data = {"api_version": 1, "items": [summary()], "next_cursor": None}
        client = self.client([Reply(data)])
        self.assertEqual(client.call("search", {"limit": 5}), data)
        self.assertEqual(self.opener.calls[0].method, "POST")
        for path in Path(self.tmp.name).glob("*"):
            self.assertNotIn(TOKEN, path.read_text())

    def test_statement_preserves_math_images_and_sample_lines(self):
        data = statement()
        client = self.client([Reply(data, "problem")])
        self.assertEqual(client.call("problem", {"id": PID}), data)
        self.assertIn("\\leq", data["problem"]["statement"]["body"])
        self.assertEqual(data["problem"]["statement"]["samples"][0]["input"], "1\n2\n")

    def test_wrong_identity_checksum_private_fields_or_origin_rejected(self):
        variants = []
        for mutate in (lambda p: p.update(id="2" * 32), lambda p: p.update(content_sha256="0" * 64),
                       lambda p: p.update(solution_code="secret"), lambda p: p.update(url="https://evil.example/problems/x"),
                       lambda p: p.update(limits={"time_ms": True, "time_scope": "per_test", "memory_mb": 256})):
            data = statement(); mutate(data["problem"]); variants.append(data)
        for data in variants:
            with self.subTest(data=data), self.assertRaises(ClientError):
                validate_response(data, "problem", {"id": PID})

    def test_all_tests_time_scope_matches_server(self):
        data = statement(); data["problem"]["limits"]["time_scope"] = "all_tests"
        validate_response(data, "problem", {"id": PID})

    def test_401_and_503_are_not_retried_and_errors_hide_token(self):
        for status in (401, 503):
            client = self.client([self.error(status)])
            with self.assertRaises(ClientError) as caught: client.call("search", {})
            self.assertNotIn(TOKEN, str(caught.exception))
            self.assertEqual(len(self.opener.calls), 1)

    def test_429_retries_are_bounded_and_honor_header(self):
        client = self.client([self.error(429, "2"), self.error(429, "2"), Reply({"api_version": 1, "items": [], "next_cursor": None})])
        start = self.clock.now
        client.call("search", {})
        self.assertEqual(len(self.opener.calls), 3)
        self.assertGreaterEqual(self.clock.now - start, 4)

    def test_long_retry_after_does_not_block_session(self):
        client = self.client([self.error(429, "120")])
        with self.assertRaisesRegex(ClientError, "120"): client.call("search", {})
        self.assertEqual(len(self.opener.calls), 1)

    def test_redirects_never_follow_or_forward_credentials(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.example"))
        client = self.client([self.error(302)])
        with self.assertRaises(ClientError): client.call("search", {})
        self.assertEqual(len(self.opener.calls), 1)

    def test_size_malformed_json_and_wrong_content_type(self):
        for reply in (Reply({}, raw=b"a" * (MAX_BYTES + 1)), Reply({}, raw=b"{"), Reply({}, content_type="text/html"),
                      Reply({}, url="https://evil.example")):
            client = self.client([reply])
            with self.assertRaises(ClientError): client.call("search", {})

    def test_network_failure_stops(self):
        client = self.client([URLError("fixture")])
        with self.assertRaises(ClientError): client.call("search", {})
        self.assertEqual(len(self.opener.calls), 1)

    def test_pacing_shared_across_client_instances_and_twenty_per_minute(self):
        client = self.client([])
        for _ in range(20): client.pace()
        another = ArchiveClient(self.tmp.name, TOKEN, self.opener, self.clock.time, self.clock.sleep)
        with self.assertRaisesRegex(ClientError, "budget"): another.pace()
        self.clock.sleep(61); another.pace()

    def test_candidates_bounded_to_five_pages_and_seen_ids_excluded(self):
        replies = [Reply({"api_version": 1, "items": [summary(str(i) * 32)], "next_cursor": str(i) * 32}) for i in range(1, 6)]
        client = self.client(replies)
        self.assertEqual(client.candidates({"limit": 1}, seen={str(i) * 32 for i in range(1, 6)}), [])
        self.assertEqual(len(self.opener.calls), 5)

    def test_missing_key_fails_before_network(self):
        with self.assertRaises(ClientError): ArchiveClient(self.tmp.name, token="")


if __name__ == "__main__": unittest.main()
