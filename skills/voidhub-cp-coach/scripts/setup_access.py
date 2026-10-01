"""Generate a private trial credential. Print its SHA-256 digest, never the token."""

import argparse
import csv
import hashlib
import os
from pathlib import Path
import secrets
import subprocess
import sys


def credential_directory():
    return (
        Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share")))
        / "VoidHubCoach"
        / "credentials"
    )


def secure_directory(path):
    if path.is_symlink():
        raise RuntimeError("Credential directory cannot be a symlink.")
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        identity = subprocess.check_output(
            ["whoami", "/user", "/fo", "csv", "/nh"], text=True, encoding="utf-8"
        )
        sid = next(csv.reader([identity.strip()]))[1]
        subprocess.run(
            [
                "icacls",
                str(path),
                "/inheritance:r",
                "/grant:r",
                f"*{sid}:(OI)(CI)F",
                "*S-1-5-18:(OI)(CI)F",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        path.chmod(0o700)


def provision(rotate=False):
    directory = credential_directory()
    secure_directory(directory)
    path = directory / "trial.token"
    if path.is_symlink():
        raise RuntimeError("Credential file cannot be a symlink.")
    if path.exists() and not rotate:
        token = path.read_text(encoding="ascii").strip()
    else:
        token = secrets.token_urlsafe(48)
        # Replace through a new restricted file, never a world-readable tempfile.
        temporary = directory / (secrets.token_hex(12) + ".private")
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="ascii") as stream:
                stream.write(token)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
    if not 32 <= len(token) <= 128 or not all(
        c.isascii() and (c.isalnum() or c in "_-") for c in token
    ):
        raise RuntimeError(
            "Existing credential is malformed; review it without displaying it."
        )
    if os.name != "nt":
        path.chmod(0o600)
    return path, hashlib.sha256(token.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rotate",
        action="store_true",
        help="Replace the private key; register its new digest and revoke the old one",
    )
    args = parser.parse_args()
    try:
        path, digest = provision(args.rotate)
        print("Token file: " + str(path))
        print("COACH_API_KEY_HASHES digest: " + digest)
        print(
            "Append this digest in hosting configuration, then restart all web workers. Never display trial.token."
        )
    except (RuntimeError, OSError, subprocess.SubprocessError):
        parser.exit(
            1,
            "Credential setup failed; no credential was printed. Check private directory permissions.\n",
        )


if __name__ == "__main__":
    main()
