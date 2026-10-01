# VoidHub CP Coach

Your competitive programming coach, with adaptive practice and progress that carries across sessions.

Powered by [VoidHub](https://voidhub.co/)

## What it does

- Diagnoses your starting point with three real CPC problems, one at a time.
- Builds beginner-to-intermediate topic practice with progressive hints.
- Names each problem's contest and links directly to VoidHub.
- Tracks assistance, weaknesses, reviews and progress across chats.

No submission integration. Complete solutions are provided only on explicit
request. Archive ratings are estimates; coaching accuracy is evaluated through
evidence and session review, not guaranteed by the skill format.

## Try it

Requires Python 3.10+ and an approved VoidHub read-API key. The bundled scripts
use only the Python standard library.

Install the folder `skills/voidhub-cp-coach` with your agent's skill installer,
or copy it into `.agents/skills/voidhub-cp-coach` in your chosen training workspace.
Reload your agent's skill discovery, then start:

```text
$voidhub-cp-coach
Help me prepare for ECPC. Assess my level and build a realistic weekly plan.
```

For review before installation, point the agent directly at the bundled
`skills/voidhub-cp-coach/SKILL.md` and ask it to follow that skill.

Learner files default to `voidhub-coach-data` in the training workspace, outside
the installed skill. Never commit that directory or secrets. Installation
updates must not replace your learner data.

## API access

The skill uses a dedicated, authenticated read API for published CPC problems.
It receives statements, samples and metadata, never solutions or private tests.
Keys are per installation; there is no public shared key. Access is initially
provisioned manually for trials.

[Live API setup and test commands](docs/api-trial.md) ·
[Architecture](docs/architecture.md) ·
[Validation report](docs/validation.md)

## Development

```text
python -m unittest discover -s tests -v
```

Tests use temporary learner data and fake transport credentials. They do not
submit code or query production. Python standard library only.

This is a v1 trial covering beginner-to-intermediate topics. Advanced curriculum
and automated key enrollment are future work. No license has been selected yet.
