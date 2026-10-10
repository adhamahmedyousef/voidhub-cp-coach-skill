# Security and delivery notes (0.2.0)

## Works without external activation

The default client uses published VoidHub CPC HTML pages. No account, API key,
developer contact, payment or manual provisioning is needed. The client was
tested against the live public archive without credentials. Optional existing
API integrations are explicitly selected with `--access api`; they do not
unlock or restrict any part of the default coaching workflow.

## Expected patterns reported by automated scans

- `os.fdopen(fd, "w")` writes JSON to a temporary local file, flushes it and
  atomically replaces the target. It protects learner history from partial
  writes. It does not execute a shell command or download/run code.
- `os.environ` is used only by the explicitly selected optional API integration
  to read `VOIDHUB_COACH_API_KEY`. The public client does not read this variable
  or a credential file. Other environment accesses in optional credential setup
  locate the local user configuration directory.
- `https://voidhub.co` is a public service origin, not a secret. The YouTube
  regex validates a public watch URL in local learner records; it is not a key,
  password or automatic outbound request.
- JSON Schema URLs identify a schema and constrain permitted problem links.
  Python JSON parsing never fetches these URLs.

These patterns remain readable; they have not been encoded or hidden to evade
review. No keys, private learner files, generated credentials or executables
are bundled.

## Network and local state

The default client makes GET requests only to the declared public problem
listing and selected statement paths on VoidHub. It executes no page scripts,
loads no image assets and retrieves no editorials or private tests. TLS
verification, redirect rejection, response-size limits and pacing are enabled.
Filters and the chosen problem URL are sent, never learner records or code.
Service errors are reported rather than bypassed. Reading a problem page can
increment its ordinary public view count.

Public metadata/index, response JSON, progress, notes, lock files and pacing
records are local, outside the installed skill. The optional API mode sends
its existing credential only to the two declared read API endpoints. Its
optional Windows setup helper uses fixed `whoami`/`icacls` argument lists,
without `shell=True`, solely to restrict its own credential directory. The
normal coaching workflow does not run that helper.

Browser/search tools can verify requested YouTube explanations. The Python
helpers do not contact YouTube. Full permissions and endpoints are listed in
SKILL.md. Public page structure can change; unverified data is rejected, and
saved coaching progress stays available.
