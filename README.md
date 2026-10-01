# VoidHub CP Coach

Your competitive programming coach, with adaptive practice and progress that carries across sessions.

Powered by [VoidHub](https://voidhub.co/)

VoidHub CP Coach helps you prepare for ECPC, ACPC and ICPC through real CPC
problems from VoidHub. It starts with your goal, experience and available time,
then assesses your level with three problems, one at a time. Training grows from
direct topic practice into combined ideas and mixed problem solving.

The coach keeps replies brief and gives you room to think. Hints come when you
ask, one step at a time. A complete solution requires an explicit request and is
recorded as assistance. Reviews use your reasoning, code and actual outcome to
choose the next step; they do not treat a few passing examples as proof.

Every practice question includes its title, contest, VoidHub difficulty,
statement, samples and link. The trained topic appears in topic practice and
stays hidden during diagnosis and mixed practice. Archive ratings are estimates;
original contest indices are shown only when verified.

## Start training

You need Python 3.10+ and an approved VoidHub Coach API key. The skill's scripts
use the Python standard library and have no runtime package dependencies.

Copy `skills/voidhub-cp-coach` into `.agents/skills/voidhub-cp-coach` in your
training workspace, reload your agent's skill discovery and start:

```text
$voidhub-cp-coach
Help me prepare for ECPC. Assess my level and build a realistic weekly plan.
```

Use the same training workspace when you continue in another chat. You can also
point your agent directly at the bundled `SKILL.md` to review the behavior before
installing it.

## Memory that carries forward

The coach creates `voidhub-coach-data` in your training workspace. `profile.md`
keeps your goals, preferences and lasting learning notes. `plan.md` keeps the
current workload and a short session handoff. `progress.json` keeps attempts,
hints, reviews, mastery evidence and the unfinished question.

A new chat reads a compact summary and continues from the saved next step. It
does not load the entire history into context or replace your plan on each run.
The full history remains on disk, outside the installed skill, so skill updates
preserve your progress. Another device needs access to those same learner files.
Keep learner data and credentials out of Git.

## Archive access

The coach reads published CPC problems through two authenticated operations:
`POST /api/coach/v1/search` and `POST /api/coach/v1/problem`. They return public
metadata, statements and samples. They do not provide solutions, private tests
or submission access. Each approved installation uses its own bearer key.

To provision a trial credential from this repository:

```powershell
python skills/voidhub-cp-coach/scripts/setup_access.py
```

The tool stores the key privately and displays only its path and SHA-256 digest.
The hosting owner adds that digest to `COACH_API_KEY_HASHES`, preserving existing
comma-separated entries, and restarts the service. On Windows, load your local
key into the process environment:

```powershell
$env:VOIDHUB_COACH_API_KEY = (Get-Content -Raw "$env:LOCALAPPDATA\VoidHubCoach\credentials\trial.token").Trim()
python skills/voidhub-cp-coach/scripts/archive_client.py search --state-dir ./voidhub-coach-data --limit 3 --output ./voidhub-coach-data/search.json
```

The client bounds request frequency and response sizes, rejects redirects and
checks returned data. If access is unavailable, the coach saves the pending
step and waits rather than inventing a question. A bearer key can be used by any
caller who possesses it; access is dedicated to the coach without proving the
identity of its client. Railway proxy setup and API contracts live in
[WORKFLOW.md](skills/voidhub-cp-coach/WORKFLOW.md).

## Inside the skill

[SKILL.md](skills/voidhub-cp-coach/SKILL.md) defines the coach's behavior and routes
to guidance as needed. [WORKFLOW.md](skills/voidhub-cp-coach/WORKFLOW.md) describes
sessions and archive access. [COACHING.md](skills/voidhub-cp-coach/COACHING.md)
covers hints and reviews. [CURRICULUM.md](skills/voidhub-cp-coach/CURRICULUM.md)
defines thirteen topics and their stages. [PROBLEMS.md](skills/voidhub-cp-coach/PROBLEMS.md)
governs question selection and presentation. [MEMORY.md](skills/voidhub-cp-coach/MEMORY.md)
defines learner memory and its commands.

Three Python helpers handle archive access, progress and credential setup.
`agents/openai.yaml` supplies display metadata, and `progress.schema.json`
describes the saved state. Behavioral and script tests remain under `tests/`.
The curriculum covers beginner-to-intermediate preparation; advanced topics are
outside this first version.
