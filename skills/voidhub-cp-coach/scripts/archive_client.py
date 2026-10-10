"""Bounded read-only public CPC access, with an optional authenticated API mode."""

import argparse
from contextlib import contextmanager
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import time
from urllib import error, parse, request

from setup_access import read_credential

ORIGIN = "https://voidhub.co"
MAX_BYTES = 256 * 1024
ID = re.compile(r"[a-f0-9]{32}\Z")


class ClientError(Exception):
    pass


@contextmanager
def locked(path, timeout=10):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise ClientError(
                    "State is locked. Check for another running client; do not remove a live lock."
                )
            time.sleep(0.05)
    try:
        os.close(fd)
        yield
    finally:
        path.unlink()


def atomic_json(path, value):
    import tempfile

    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=".coach-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def summary_valid(item):
    allowed = {"id", "title", "contest", "difficulty", "topics", "url"}
    if not isinstance(item, dict) or set(item) != allowed:
        raise ClientError("Unexpected problem summary fields.")
    if not isinstance(item["id"], str) or not ID.fullmatch(item["id"]):
        raise ClientError("Invalid problem ID.")
    if not isinstance(item["title"], str) or not item["title"].strip():
        raise ClientError("Missing problem title.")
    try:
        url = parse.urlsplit(item["url"] if isinstance(item["url"], str) else "")
    except ValueError:
        raise ClientError("Malformed problem URL.") from None
    if (
        url.scheme != "https"
        or url.netloc != "voidhub.co"
        or not url.path.startswith("/problems/")
        or url.query
        or url.fragment
    ):
        raise ClientError("Unexpected problem origin.")
    contest = item["contest"]
    if (
        not isinstance(contest, dict)
        or set(contest) != {"name", "problem_number"}
        or not isinstance(contest["name"], str)
        or not contest["name"].strip()
    ):
        raise ClientError("Missing contest attribution; do not invent it.")
    if (
        contest["problem_number"] is not None
        and type(contest["problem_number"]) is not int
    ):
        raise ClientError("Invalid contest problem number.")
    difficulty = item["difficulty"]
    if (
        not isinstance(difficulty, dict)
        or set(difficulty) != {"value", "source", "kind"}
        or type(difficulty["value"]) is not int
        or difficulty["source"] != "voidhub"
        or difficulty["kind"] != "archive_rating"
    ):
        raise ClientError("Invalid archive difficulty.")
    if not isinstance(item["topics"], list) or not all(
        isinstance(tag, str) for tag in item["topics"]
    ):
        raise ClientError("Invalid archive topics.")
    return item


def validate_response(data, operation, payload):
    if (
        not isinstance(data, dict)
        or type(data.get("api_version")) is not int
        or data["api_version"] != 1
    ):
        raise ClientError("Unsupported API response.")
    if operation == "search":
        if (
            set(data) != {"api_version", "items", "next_cursor"}
            or not isinstance(data["items"], list)
            or len(data["items"]) > payload.get("limit", 5)
        ):
            raise ClientError("Invalid search response.")
        for item in data["items"]:
            summary_valid(item)
        ids = [item["id"] for item in data["items"]]
        if len(ids) != len(set(ids)):
            raise ClientError("Duplicate search IDs.")
        cursor = data["next_cursor"]
        if cursor is not None and (
            not ids or cursor != ids[-1] or not ID.fullmatch(cursor)
        ):
            raise ClientError("Invalid pagination cursor.")
    else:
        if set(data) != {"api_version", "problem"} or not isinstance(
            data["problem"], dict
        ):
            raise ClientError("Invalid statement response.")
        item = data["problem"]
        extras = {
            "statement",
            "content_format",
            "limits",
            "updated_at",
            "content_sha256",
        }
        if (
            set(item)
            != {"id", "title", "contest", "difficulty", "topics", "url"} | extras
        ):
            raise ClientError("Unexpected statement fields.")
        summary_valid({key: val for key, val in item.items() if key not in extras})
        if item["id"] != payload["id"] or item["content_format"] != "stored_markup":
            raise ClientError("Statement identity/format mismatch.")
        content = item["statement"]
        if not isinstance(content, dict) or set(content) != {
            "body",
            "input",
            "output",
            "constraints",
            "notes",
            "samples",
        }:
            raise ClientError("Invalid statement sections.")
        if not isinstance(content["body"], str) or not content["body"].strip():
            raise ClientError("Empty statement.")
        for section in ("input", "output", "constraints", "notes"):
            if content[section] is not None and not isinstance(content[section], str):
                raise ClientError("Invalid statement text.")
        if not isinstance(content["samples"], list) or any(
            not isinstance(s, dict)
            or set(s) != {"input", "output"}
            or not all(isinstance(v, str) for v in s.values())
            for s in content["samples"]
        ):
            raise ClientError("Invalid samples.")
        limits = item["limits"]
        if (
            not isinstance(limits, dict)
            or set(limits) != {"time_ms", "time_scope", "memory_mb"}
            or any(
                type(limits[k]) is not int or limits[k] <= 0
                for k in ("time_ms", "memory_mb")
            )
            or limits["time_scope"] not in ("per_test", "all_tests")
        ):
            raise ClientError("Invalid resource limits.")
        digest = hashlib.sha256(
            json.dumps(
                content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
        if item["content_sha256"] != digest:
            raise ClientError("Content checksum mismatch.")
        if item["updated_at"] is not None and not isinstance(item["updated_at"], str):
            raise ClientError("Invalid update timestamp.")
    return data


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ArchiveClient:
    def __init__(
        self, state_dir, token=None, opener=None, clock=time.time, sleep=time.sleep
    ):
        if token is None:
            token = os.environ.get("VOIDHUB_COACH_API_KEY")
            if token is None:
                try:
                    token = read_credential()
                except (RuntimeError, OSError, UnicodeError):
                    raise ClientError(
                        "No usable local credential. Run setup_access.py and ask the hosting owner "
                        "to register its digest, or set VOIDHUB_COACH_API_KEY privately."
                    ) from None
        self.token = token
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", self.token):
            raise ClientError(
                "Set VOIDHUB_COACH_API_KEY using the private local credential; never paste it in chat."
            )
        self.directory = Path(state_dir).resolve()
        skill_dir = Path(__file__).resolve().parents[1]
        if (
            skill_dir == self.directory
            or skill_dir in self.directory.parents
            or Path(state_dir).is_symlink()
        ):
            raise ClientError(
                "Client state must be outside the installed skill, in a local learner directory."
            )
        self.directory.mkdir(parents=True, exist_ok=True)
        self.opener = opener or request.build_opener(NoRedirect())
        self.clock, self.sleep = clock, sleep
        self.bucket = hashlib.sha256(self.token.encode()).hexdigest()[:24]

    def pace(self):
        path = self.directory / ("requests-" + self.bucket + ".json")
        with locked(path.with_suffix(".lock"), timeout=12):
            try:
                if path.is_symlink() or path.exists() and path.stat().st_size > 4096:
                    raise ClientError(
                        "Invalid client pacing file; preserved for review."
                    )
                values = json.loads(path.read_text()) if path.exists() else []
            except (ValueError, OSError):
                raise ClientError(
                    "Client pacing state is damaged; preserved for review."
                )
            if not isinstance(values, list) or any(
                type(t) not in (int, float) or not 0 <= t <= self.clock() + 5
                for t in values
            ):
                raise ClientError(
                    "Invalid client pacing state or clock moved backwards."
                )
            values = [t for t in values if self.clock() - t < 60]
            wait = max(0, values[-1] + 1.1 - self.clock()) if values else 0
            if len(values) >= 20:
                wait = max(wait, values[-20] + 60.1 - self.clock())
            if wait > 5:
                raise ClientError(
                    f"Local request budget reached. Retry in {int(wait) + 1} seconds."
                )
            if wait:
                self.sleep(wait)
            values = [t for t in values if self.clock() - t < 60]
            values.append(self.clock())
            atomic_json(path, values)

    def call(self, operation, payload):
        if operation not in {"search", "problem"}:
            raise ClientError("Only search and problem reads are supported.")
        encoded = json.dumps(payload, allow_nan=False).encode()
        if len(encoded) > 4096:
            raise ClientError("Request too large.")
        for attempt in range(3):
            self.pace()
            req = request.Request(
                ORIGIN + "/api/coach/v1/" + operation,
                data=encoded,
                method="POST",
                headers={
                    "Authorization": "Bearer " + self.token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "VoidHub-CP-Coach/0.1",
                },
            )
            try:
                with self.opener.open(req, timeout=20) as stream:
                    if (
                        stream.status != 200
                        or stream.geturl() != req.full_url
                        or stream.headers.get_content_type() != "application/json"
                    ):
                        raise ClientError("Unexpected HTTP response or redirect.")
                    raw = stream.read(MAX_BYTES + 1)
                    if len(raw) > MAX_BYTES:
                        raise ClientError("Response exceeds 256 KiB.")
                    try:
                        data = json.loads(raw)
                    except (ValueError, UnicodeError):
                        raise ClientError("Server did not return valid JSON.")
                return validate_response(data, operation, payload)
            except error.HTTPError as exc:
                if exc.code == 429 and attempt < 2:
                    retry = exc.headers.get("Retry-After", "")
                    if retry.isdigit() and 1 <= int(retry) <= 15:
                        exc.close()
                        self.sleep(int(retry) + 0.1)
                        continue
                code = exc.code
                retry = exc.headers.get("Retry-After", "")
                reason = ""
                try:
                    body = json.loads(exc.read(1024))
                    known = {
                        "api_disabled",
                        "https_required",
                        "unauthorized",
                        "rate_limit_unavailable",
                        "rate_limited",
                        "not_found",
                        "content_needs_review",
                        "response_too_large",
                    }
                    if (
                        isinstance(body, dict)
                        and isinstance(body.get("error"), str)
                        and body["error"] in known
                    ):
                        reason = " (" + body["error"] + ")"
                except (ValueError, UnicodeError, OSError):
                    pass
                exc.close()
                raise ClientError(
                    f"VoidHub returned HTTP {code}{reason}."
                    + (f" Retry after {retry}s." if retry.isdigit() else "")
                    + " No problem was invented."
                ) from None
            except (error.URLError, TimeoutError, OSError):
                raise ClientError(
                    "VoidHub connection failed. Resume later; do not invent archive content."
                ) from None

    def candidates(self, parameters, seen=()):
        parameters = dict(parameters)
        found, cursors = [], set()
        for _ in range(5):
            data = self.call("search", parameters)
            found.extend(item for item in data["items"] if item["id"] not in seen)
            if found or data["next_cursor"] is None:
                return found
            if data["next_cursor"] in cursors:
                raise ClientError("Repeated archive cursor.")
            cursors.add(data["next_cursor"])
            parameters["after"] = data["next_cursor"]
        return []


class HtmlNode:
    def __init__(self, tag="", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()

    def text(self):
        return "".join(child if isinstance(child, str) else child.text() for child in self.children)

    def nodes(self, predicate):
        for child in self.children:
            if isinstance(child, HtmlNode):
                if predicate(child):
                    yield child
                yield from child.nodes(predicate)

    def one(self, predicate):
        matches = list(self.nodes(predicate))
        if len(matches) != 1:
            raise ClientError("Public page structure changed; open the problem link rather than guessing missing data.")
        return matches[0]


class PublicHtml(HTMLParser):
    """Parse inert HTML; never run page scripts, follow images, or inspect editorials."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root, self.stack, self.skipping = HtmlNode(), [], 0
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skipping += 1
            return
        if self.skipping:
            return
        node = HtmlNode(tag, attrs)
        self.stack[-1].children.append(node)
        if tag == "br":
            node.children.append("\n")
        if tag not in self.VOID:
            if len(self.stack) >= 128:
                raise ClientError("Public page nesting exceeds the parsing limit.")
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skipping = max(0, self.skipping - 1)
            return
        if self.skipping:
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, text):
        if not self.skipping:
            self.stack[-1].children.append(text)


class PublicArchiveClient(ArchiveClient):
    """No credential, environment access, cookies, login, or developer activation."""
    def __init__(self, state_dir, opener=None, clock=time.time, sleep=time.sleep):
        self.directory = Path(state_dir).resolve()
        skill_dir = Path(__file__).resolve().parents[1]
        if skill_dir == self.directory or skill_dir in self.directory.parents or Path(state_dir).is_symlink():
            raise ClientError("Client state must be outside the installed skill.")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.opener = opener or request.build_opener(NoRedirect())
        self.clock, self.sleep, self.bucket = clock, sleep, "public-read"
        self.pages = {}

    def page(self, path):
        if not re.fullmatch(r"/problems(?:\?[^#\\\r\n]*|/[A-Za-z0-9_-]+)", path):
            raise ClientError("Only public VoidHub problem pages are allowed.")
        if path.startswith("/problems?") and path in self.pages:
            return self.pages[path]
        self.pace()
        req = request.Request(ORIGIN + path, method="GET", headers={
            "Accept": "text/html", "User-Agent": "VoidHub-CP-Coach/0.2 (public read-only archive)"})
        try:
            with self.opener.open(req, timeout=20) as stream:
                if stream.status != 200 or stream.geturl() != req.full_url or stream.headers.get_content_type() != "text/html":
                    raise ClientError("Unexpected public page response or redirect.")
                raw = stream.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    raise ClientError("Public page exceeds 1 MiB.")
                try:
                    root = PublicHtml(raw.decode("utf-8")).root
                    if path.startswith("/problems?"):
                        self.pages[path] = root
                    return root
                except UnicodeError:
                    raise ClientError("Public page is not valid UTF-8.") from None
        except error.HTTPError as exc:
            code = exc.code
            retry = exc.headers.get("Retry-After", "")
            exc.close()
            raise ClientError(f"Public archive returned HTTP {code}." +
                (f" Retry after {retry}s." if retry.isdigit() else "") + " No access restriction was bypassed.") from None
        except (error.URLError, TimeoutError, OSError):
            raise ClientError("Public archive connection failed; resume later without inventing a problem.") from None

    def index(self):
        path = self.directory / "public-index.json"
        if not path.exists():
            return {}
        if path.is_symlink() or path.stat().st_size > 512 * 1024:
            raise ClientError("Invalid local public index; preserved for review.")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError()
            for key, item in data.items():
                summary_valid(item)
                if key != item["id"] or key != hashlib.sha256(item["url"].encode()).hexdigest()[:32]:
                    raise ValueError()
            return data
        except (ValueError, OSError):
            raise ClientError("Invalid local public index; preserved for review.") from None

    def call(self, operation, payload):
        if operation == "search":
            limit = payload.get("limit", 5)
            low, high = payload.get("difficulty_min", 0), payload.get("difficulty_max", 4000)
            if type(limit) is not int or not 1 <= limit <= 10 or type(low) is not int or type(high) is not int or not 0 <= low <= high <= 4000:
                raise ClientError("Invalid public search bounds.")
            cursor = payload.get("after")
            if cursor is not None and (not isinstance(cursor, str) or not ID.fullmatch(cursor) or not 1 <= int(cursor, 16) <= 320000):
                raise ClientError("Invalid public pagination cursor.")
            position = int(cursor, 16) - 1 if cursor else 0
            page_number, offset = position // 32 + 1, position % 32
            params = {"collection": "cpc", "sort": "number", "page": page_number}
            if low >= 100:
                params["difficulty_min"] = min(low, 3500)
            if high <= 3500:
                params["difficulty_max"] = max(high, 100)
            for key, field, maximum in (("topic", "tag", 40), ("contest", "contest", 180)):
                if key in payload:
                    value = payload[key]
                    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
                        raise ClientError("Invalid public search text.")
                    params[field] = value.strip()
            page = self.page("/problems?" + parse.urlencode(params))
            rows = list(page.nodes(lambda n: n.has_class("vh-problem-row")))
            if not rows and not list(page.nodes(lambda n: n.has_class("vh-problems-empty__panel"))):
                raise ClientError("Public archive structure changed; no empty-pool claim was made.")
            items = []
            for row in rows:
                link = row.one(lambda n: n.tag == "a" and n.has_class("vh-problem-row__main"))
                path = link.attrs.get("href", "")
                if not re.fullmatch(r"/problems/[A-Za-z0-9_-]+", path):
                    raise ClientError("Unexpected public problem URL.")
                strong = link.one(lambda n: n.tag == "strong")
                title = "".join(c if isinstance(c, str) else "" if c.has_class("vh-problem-row__number") or c.has_class("vh-problem-row__rating") else c.text() for c in strong.children).strip()
                rating_text = row.one(lambda n: n.has_class("vh-problem-row__rating")).text().strip()
                if not rating_text.isascii() or not rating_text.isdigit():
                    raise ClientError("Could not verify the public difficulty rating.")
                rating = int(rating_text)
                if not low <= rating <= high:
                    continue
                tags = row.one(lambda n: n.has_class("vh-problem-row__tags"))
                url = ORIGIN + path
                item = {"id": hashlib.sha256(url.encode()).hexdigest()[:32], "title": title,
                    "contest": {"name": row.one(lambda n: n.has_class("vh-problem-row__source")).text().strip(), "problem_number": None},
                    "difficulty": {"value": rating, "source": "voidhub", "kind": "archive_rating"},
                    "topics": [n.text().strip() for n in tags.nodes(lambda n: n.tag == "em")], "url": url}
                items.append(summary_valid(item))
            index = self.index()
            index.update({item["id"]: item for item in items})
            if len(json.dumps(index).encode()) > 512 * 1024:
                raise ClientError("Public index limit reached; preserve learner state and review it.")
            atomic_json(self.directory / "public-index.json", index)
            next_page = any(n.text().strip() == "Next" for n in page.nodes(lambda n: n.tag == "a" and "data-problem-page" in n.attrs))
            next_position = position + limit + 1 if offset + limit < len(items) else page_number * 32 + 1 if next_page else None
            return {"api_version": 1, "items": items[offset:offset + limit],
                "next_cursor": format(next_position, "032x") if next_position else None}
        if operation != "problem" or not isinstance(payload.get("id"), str) or not ID.fullmatch(payload["id"]):
            raise ClientError("Only public search and selected problem reads are supported.")
        item = self.index().get(payload["id"])
        if item is None:
            raise ClientError("Run public search first; problem IDs are local URL fingerprints, not API IDs.")
        page = self.page(parse.urlsplit(item["url"]).path)
        if page.one(lambda n: n.has_class("vh-problems-eyebrow") and n.text().strip() == "CPC problem").text().strip() != "CPC problem":
            raise ClientError("This is not a published CPC problem.")
        heading = page.one(lambda n: n.tag == "h1").text().strip()
        if re.sub(r"^\d+\.\s*", "", heading) != item["title"]:
            raise ClientError("Public problem identity changed; search again.")
        article = page.one(lambda n: n.has_class("vh-problem-statement"))
        content = {"body": None, "input": None, "output": None, "constraints": None, "notes": None, "samples": []}
        labels = {"Statement": "body", "Input": "input", "Output": "output", "Constraints": "constraints", "Notes": "notes"}
        for section in article.nodes(lambda n: n.tag == "section"):
            label = section.one(lambda n: n.tag == "h2").text().strip()
            if label in labels:
                divs = [n for n in section.children if isinstance(n, HtmlNode) and n.tag == "div"]
                if len(divs) != 1 or content[labels[label]] is not None:
                    raise ClientError("Ambiguous statement sections.")
                content[labels[label]] = divs[0].text()
            elif label.startswith("Example "):
                sample = {}
                for kind in ("input", "output"):
                    sample[kind] = section.one(lambda n: n.tag == "pre" and n.attrs.get("id", "").startswith(kind + "-")).text()
                content["samples"].append(sample)
        limits = page.one(lambda n: n.has_class("vh-problem-limits"))
        values = {}
        for node in (n for n in limits.children if isinstance(n, HtmlNode) and n.tag == "div"):
            values[node.one(lambda n: n.tag == "span").text().strip()] = node.one(lambda n: n.tag == "strong").text().strip()
        if values.get("Source") != item["contest"]["name"]:
            raise ClientError("Contest attribution changed; search again.")
        time_match = re.fullmatch(r"(\d+(?:\.\d+)?) sec\s*(/ test|total)", values.get("Time limit", ""))
        memory_match = re.fullmatch(r"(\d+) MB", values.get("Memory limit", ""))
        if not time_match or not memory_match:
            raise ClientError("Could not verify the public problem limits.")
        result = {**item, "statement": content, "content_format": "stored_markup", "updated_at": None,
            "limits": {"time_ms": round(float(time_match[1]) * 1000), "time_scope": "per_test" if time_match[2] == "/ test" else "all_tests", "memory_mb": int(memory_match[1])},
            "content_sha256": hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
        return validate_response({"api_version": 1, "problem": result}, "problem", payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("search", "candidates", "problem"))
    parser.add_argument("--access", choices=("public", "api"), default="public",
        help="Public pages need no account or key; API is an optional integration")
    parser.add_argument(
        "--state-dir",
        required=True,
        help="Learner directory outside the installed skill",
    )
    parser.add_argument("--id")
    parser.add_argument("--topic")
    parser.add_argument("--contest")
    parser.add_argument("--difficulty-min", type=int, default=0)
    parser.add_argument("--difficulty-max", type=int, default=4000)
    parser.add_argument("--limit", type=int, choices=range(1, 11), default=5)
    parser.add_argument("--after")
    parser.add_argument(
        "--output", help="Save public JSON to this file instead of stdout"
    )
    args = parser.parse_args()
    payload = (
        {"id": args.id}
        if args.operation == "problem"
        else {
            "difficulty_min": args.difficulty_min,
            "difficulty_max": args.difficulty_max,
            "limit": args.limit,
        }
    )
    if args.operation == "problem" and (not args.id or not ID.fullmatch(args.id)):
        parser.error("--id must be a returned 32-character ID")
    if args.operation != "problem":
        if not 0 <= args.difficulty_min <= args.difficulty_max <= 4000:
            parser.error("Difficulty range must satisfy 0 <= min <= max <= 4000")
        if args.after is not None and not ID.fullmatch(args.after):
            parser.error("--after must be a returned 32-character cursor")
        for field in ("topic", "contest", "after"):
            if getattr(args, field) is not None:
                payload[field] = getattr(args, field)
    try:
        learner_dir = Path(args.state_dir)
        if args.operation == "candidates":
            # Import lazily: progress_store also uses this client's state helpers.
            from progress_store import ProgressStore, StoreError

            try:
                state = ProgressStore(learner_dir).read()
            except StoreError as exc:
                raise ClientError(str(exc)) from None
            if state["current_problem"] is not None:
                raise ClientError(
                    "Resume or record the active problem before selecting another."
                )
            seen = {p["metadata"]["id"] for p in state["problems"].values()}
            client = PublicArchiveClient if args.access == "public" else ArchiveClient
            items = client(learner_dir / ".client").candidates(payload, seen)
            data = {"api_version": 1, "items": items, "next_cursor": None}
            if not items:
                raise ClientError(
                    "No unseen candidate within five pages. Keep the selected difficulty; "
                    "review the filters or defer practice."
                )
        else:
            client = PublicArchiveClient if args.access == "public" else ArchiveClient
            data = client(learner_dir / ".client").call(args.operation, payload)
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            atomic_json(output, data)
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
    except ClientError as exc:
        parser.exit(1, str(exc) + "\n")
    except OSError:
        parser.exit(
            1,
            "Client state or output could not be saved. Check the local path and permissions.\n",
        )


if __name__ == "__main__":
    main()
