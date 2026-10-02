# Persistent learner memory

The memory belongs to the learner's training workspace, not the skill installation.
Use `voidhub-coach-data` there unless the learner already uses another directory.
A new chat must resolve that same path; it cannot recover another machine's files
or guess where a previous workspace lives. If several profiles exist, ask which
one to resume. Never merge learners or import the author's training records.

## Files and ownership

`profile.md` records the goal, experience, availability, language and lasting
preferences. Its learning notes retain demonstrated recurring difficulties,
with short supporting evidence. Unknown facts remain unknown.

Keep a self-reported topic map: comfortable, studied but not practiced, and
needs work, in the learner's own terms. Ask for missing entries during onboarding;
do not quiz the entire catalog at once. Separately retain observed strengths
and difficulties, each with a problem ID/date and whether help was used. Record
changes after meaningful attempts, not a personality judgment after one mistake.
A reported strength guides selection without granting mastery or skipping a
needed prerequisite. If evidence contradicts a claim, explain the specific gap
and update the observed assessment without rewriting what the learner reported.

`plan.md` records the current focus, weekly workload and a short session handoff:
what was learned, what remains unclear and what to do next. Update the current
plan in place rather than appending transcripts. Keep profile around 300 words
and plan around 200 words unless extra detail materially helps training.

`progress.json` owns all problem identities, attempts, assistance, evidence,
review dates, mastery, coaching decisions, recommended videos and the active
question. Never summarize away or delete
that history to save context. The compact view changes reading, not persistence.
Public statement JSON may also be retained here. Credentials stay in their
separate private credential location; no secret belongs in learner notes.

## Read and save

At the start of a chat, run `resume` and read profile/plan. The summary contains
three recent attempts, up to ten scheduled reviews, mastery counts, the latest
coaching decision, two recent resources, the active
question and next step. A count exposes omitted reviews; for a weekly review or
a question about older evidence, inspect only the relevant part of the full
history. `show` is available when a complete export is explicitly useful.
Do not reload unchanged notes or the full JSON after every message.

Save requested assistance before giving it and outcomes as soon as they are
supplied. Save a short handoff before ending; leave unfinished work active.
Only update profile when facts or preferences change, and plan when workload,
focus or handoff changes. A new chat resumes from these files rather than
starting another diagnosis automatically.

## Store commands

```text
python scripts/progress_store.py init --data-dir <learner-dir>
python scripts/progress_store.py resume --data-dir <learner-dir>
python scripts/progress_store.py show --data-dir <learner-dir>
python scripts/progress_store.py assign --data-dir <learner-dir> --input <assignment.json>
python scripts/progress_store.py hint --data-dir <learner-dir> --level observation
python scripts/progress_store.py record --data-dir <learner-dir> --input <attempt.json>
python scripts/progress_store.py next --data-dir <learner-dir> --text "Concrete next step"
python scripts/progress_store.py profile --data-dir <learner-dir> --input <profile.md>
python scripts/progress_store.py plan --data-dir <learner-dir> --input <plan.md>
python scripts/progress_store.py resource --data-dir <learner-dir> --input <resource.json>
python scripts/progress_store.py decision --data-dir <learner-dir> --input <decision.json>
python scripts/progress_store.py upgrade --data-dir <learner-dir>
```

Assignment JSON has exactly `problem` (the six-field API summary), `topic`
(internal curriculum ID), `stage` (1–3), `mode` (`topic`, `diagnostic`, `mixed`,
`review`). The store owns key, first-exposure flag and initial assistance.

Attempt JSON has exactly `session_id`, `result`, `assistance`, `failure`,
`transfer` (boolean), `evidence` (nonempty observed basis), `revisit_on` (ISO date
or null). Use a stable session ID per conversation/training session. Results:
accepted_reported, verified_correct, solution_viewed, wrong, timeout, unsolved, abandoned.
After delivering a full solution use solution_viewed with full_solution assistance,
transfer false and a review date. Do not turn viewing or copied-code acceptance
into a solve. Later independent work belongs to a separate review attempt.
Assistance: none, clarification, observation, algorithm, full_solution.
Failure: null or statement, recognition, proof, knowledge, complexity,
implementation, debugging, time_management. Assisted attempts require a date.

The store timestamps attempts, preserves the highest assistance and derives
mastery from distinct independent task IDs. Repeated tasks cannot count as
unseen transfer. Corrupt/unknown-version data remains untouched. A crashed
writer can leave `.progress.lock`; do not delete it unless the owning process
has stopped and the learner has reviewed the lock. There is no automatic reset.

JSON is authoritative for current identity, attempts, mastery and next step.
Profile notes describe goals/preferences; plan notes describe workload and
reasoning. If a stale note conflicts with JSON, reconcile the note rather than
changing recorded evidence. State writes and Markdown updates are individually
atomic, not a transaction across all three files; read JSON first after a crash.

## Decisions and compatibility

Decision input has exactly topic, stage, action, target_topic, target_stage,
checks and reason. Action is continue/advance/review_prerequisite. Checks has
four explicit booleans: understanding, complexity, coverage, prerequisites.
Explain the observed basis in reason; do not mark all checks true automatically.
The store adds timestamps and independent/transfer evidence IDs. A failed
advance leaves progress unchanged and reports what needs review.

Resource inputs are defined in [RESOURCES.md](RESOURCES.md). A viewing report
updates a resource; it never awards mastery. The latest decision updates the
saved next step. Profile/plan retain the learner's response and current gap.

New state uses schema v2. Valid v1 history remains readable and upgrades on the
first progress write, or explicitly through upgrade. Before replacement, the
store saves progress.v1.backup.json. Original IDs, attempts, assistance and
timestamps are preserved; new topics begin without invented mastery. A backup
conflict, unsupported version or invalid evidence stops the write. Keep backup
and learner history outside Git. The bundled schema describes v2 state.

Writes return a short receipt by default. Add `--full` only when the full
resulting state is needed. `resume` is read-only and does not change history.
