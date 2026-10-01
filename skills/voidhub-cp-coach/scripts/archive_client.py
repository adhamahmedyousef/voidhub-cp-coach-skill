"""Small stdlib-only client for the authenticated, read-only CPC API."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib import error, parse, request

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
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
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
    url = parse.urlsplit(item["url"] if isinstance(item["url"], str) else "")
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
            or limits["time_scope"] not in {"per_test", "all_tests"}
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
        self.token = (
            token if token is not None else os.environ.get("VOIDHUB_COACH_API_KEY", "")
        )
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("search", "problem"))
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
    if args.operation == "search":
        for field in ("topic", "contest", "after"):
            if getattr(args, field) is not None:
                payload[field] = getattr(args, field)
    try:
        data = ArchiveClient(Path(args.state_dir) / ".client").call(
            args.operation, payload
        )
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            atomic_json(output, data)
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
    except ClientError as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
