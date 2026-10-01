# VoidHub CP Coach

Your competitive programming coach, with adaptive practice and progress that carries across sessions.

Powered by [VoidHub](https://voidhub.co/)

## What it does

- Diagnoses your starting point with three real CPC problems, one at a time.
- Builds beginner-to-intermediate practice across thirteen topics.
- Names each problem's contest, preserves its statement and links to VoidHub.
- Tracks assistance, weaknesses, spaced reviews and progress across chats.

Hints follow your requests. Complete solutions require an explicit request and
count as assistance. Each stage needs three distinct independent successes,
including an unseen transfer problem. Archive ratings and educational levels
are separate; the skill does not promise perfect coaching accuracy.

## Structure

```text
skills/voidhub-cp-coach/
├── SKILL.md
├── WORKFLOW.md
├── COACHING.md
├── CURRICULUM.md
├── PROBLEMS.md
├── progress.schema.json
├── agents/openai.yaml
├── scripts/
│   ├── archive_client.py
│   ├── progress_store.py
│   └── setup_access.py
└── tests/
```

[SKILL.md](skills/voidhub-cp-coach/SKILL.md) is the entry point.
[WORKFLOW.md](skills/voidhub-cp-coach/WORKFLOW.md) describes sessions and script contracts;
[COACHING.md](skills/voidhub-cp-coach/COACHING.md) defines assistance, evidence and evaluation;
[CURRICULUM.md](skills/voidhub-cp-coach/CURRICULUM.md) defines prerequisites and stages;
[PROBLEMS.md](skills/voidhub-cp-coach/PROBLEMS.md) governs selection and presentation.
The JSON schema documents learner state. Scripts handle API access, persistence
and private trial credentials; tests verify those behaviors.

## Install and start

Requires Python 3.10+ and an approved VoidHub read-API key. Runtime scripts use
only the Python standard library.

Copy `skills/voidhub-cp-coach` into `.agents/skills/voidhub-cp-coach` in your
training workspace, then reload skill discovery. Start with:

```text
$voidhub-cp-coach
Help me prepare for ECPC. Assess my level and build a realistic weekly plan.
```

For review before installation, ask the agent to follow the bundled `SKILL.md`.
Learner files live outside the installed skill, by default in
`voidhub-coach-data` in the training workspace: `profile.md`, `plan.md` and
`progress.json`. Use the same directory in subsequent chats. Keep it out of Git.

## Trial API access

Access covers published CPC statements, samples and metadata through
`POST /api/coach/v1/search` and `POST /api/coach/v1/problem`. It does not provide
solutions, private tests or submission access. Keys are provisioned per
installation; bearer authentication cannot prove that a caller is the skill.

From this repository, generate a private local credential:

```powershell
python skills/voidhub-cp-coach/scripts/setup_access.py
```

The tool displays its path and SHA-256 digest only. On Windows the token is saved
under `%LOCALAPPDATA%\VoidHubCoach\credentials\trial.token`. Add the digest to
`COACH_API_KEY_HASHES` in the VoidHub hosting environment, preserving existing
comma-separated digests, and restart the service. Never upload the token.
For a Railway-hosted service behind its HTTPS edge, enable
`COACH_API_TRUST_RAILWAY_PROXY=true` after deploying the corresponding server
change. Only enable this when requests reach the app through that trusted edge.

Load the key locally and test without putting it in command arguments:

```powershell
$env:VOIDHUB_COACH_API_KEY = (Get-Content -Raw "$env:LOCALAPPDATA\VoidHubCoach\credentials\trial.token").Trim()
python skills/voidhub-cp-coach/scripts/archive_client.py search --state-dir ./voidhub-coach-data --limit 1
python skills/voidhub-cp-coach/scripts/archive_client.py problem --state-dir ./voidhub-coach-data --id <returned-id>
```

A minimal caller, with the same environment variable:

```python
import os
import requests

req = requests.post(
    "https://voidhub.co/api/coach/v1/search",
    headers={"Authorization": "Bearer " + os.environ["VOIDHUB_COACH_API_KEY"],
             "Accept": "application/json", "User-Agent": "VoidHub-CP-Coach/0.1"},
    json={"topic": "binary search", "limit": 5},
    timeout=(5, 15),
    allow_redirects=False,
)
req.raise_for_status()
data = req.json()
```

Use `/problem` with `json={"id": returned_id}` for a statement. The bundled
client adds response validation, download limits and persistent pacing: at
least 1.1 seconds between calls, at most 20 per minute. It rejects redirects,
bounds 429 retries and does not retry rejected keys or disabled service.
Server limits apply across clients. If access fails, diagnosis waits;
archive questions are never invented.

## Validation

```text
python -m unittest discover -s skills/voidhub-cp-coach/tests -v
```

All 34 local tests pass, and the skill format validator passes.
Tests cover client failures, response validation, concurrent and interrupted
state writes, repeat prevention, assistance tracking and packaging. Fixtures
are synthetic and do not query production or submit code. Behavioral scenarios
and a manual evaluation rubric are included in `COACHING.md`; automated state
checks do not establish the quality of an actual coaching conversation.

Live search and statement retrieval both passed on 2026-10-01 using the bundled
client and the deployed API. Identity, response schema and content checksum
validation passed for one problem. For Nonogram, statement sections matched the public page after whitespace
normalization; sample input/output matched exactly, including blank lines.
Live rejection checks passed for invalid credentials (401), unexpected fields
(400) and an unknown ID (404). Images and original contest-source fidelity
remain unverified. In API v1, `contest.problem_number` is a VoidHub archive
position, not an original contest index; coaching must not confuse them.
Advanced curriculum and automated key enrollment are future work.
No license has been selected yet.
