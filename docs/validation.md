# Validation report — 2026-10-01

## Passed locally

- 34 standard-library unittest cases: client response validation, POST-only read
  operations, origin/redirect rejection, byte limits, malformed JSON, 401/503,
  bounded 429 handling, shared pacing, five-page candidate limit and missing key.
- Progress: resume identity/assistance, accidental repeat rejection, deliberate
  reviews, assistance downgrade prevention, review-date enforcement, derived
  mastery, corruption/version preservation, atomic-write failure and concurrent
  writes without lost revisions.
- Six executable session-state rehearsals cover beginner diagnosis, intermediate
  mixed practice, wrong attempts after hints, explicit full solutions, access
  failure and the client-to-store path. Their problems are synthetic fixtures,
  explicitly labeled as such, not claimed CPC archive questions.
- Credential provisioning tests verify no raw-key stdout, reuse and rotation.
  The actual trial file's Windows ACL was inspected: current user and SYSTEM only.
- The official skill-creator quick validator passed; all routed references exist.
- Draft 2020-12 JSON Schema was checked with an independent validator, and initial
  and populated training states were checked against it. PyYAML/jsonschema were
  installed only in an existing isolated test environment; runtime remains stdlib.
- README was synchronized with GitHub before extending it; its title, opening
  description and clickable Powered by VoidHub link were preserved.

## Live result

The bundled client performed a real HTTPS POST search using the private trial
credential, without printing it. The site returned **503 / api_disabled**.
No statement was retrieved, invented or substituted. A stable identifiable
User-Agent is used for the client; it is observability, not authentication.

The hosting owner must append the trial digest to COACH_API_KEY_HASHES and
restart workers. Successful authenticated search, full-statement identity,
formula/image/sample parity and deployment proxy/Redis behavior remain pending.
The private token stays outside the repository; its path and loading commands
are in api-trial.md. No production settings were changed by this implementation.

## What these tests do not establish

Passing script tests does not prove that an LLM gives appropriate hints,
classifies every problem correctly or never makes mathematical errors. The
behavioral rubric is in tests/coaching-scenarios.md. Fresh-agent evaluation with
actual learner requests and real archive questions is still required before
claiming teaching quality has been validated. No independent model evaluation
or public release is claimed here, and no license was selected.

## Reproduce

From the repository:

```text
python -m unittest discover -s tests -v
```

For the official skill format check, run skill-creator's quick_validate.py against
skills/voidhub-cp-coach in an environment with PyYAML. It verifies packaging,
not educational effectiveness. Use docs/api-trial.md for the live test.
