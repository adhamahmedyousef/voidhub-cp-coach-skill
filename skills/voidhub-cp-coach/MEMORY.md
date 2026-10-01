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

`plan.md` records the current focus, weekly workload and a short session handoff:
what was learned, what remains unclear and what to do next. Update the current
plan in place rather than appending transcripts. Keep profile around 300 words
and plan around 200 words unless extra detail materially helps training.

`progress.json` owns all problem identities, attempts, assistance, evidence,
review dates, mastery and the active question. Never summarize away or delete
that history to save context. The compact view changes reading, not persistence.
Public statement JSON may also be retained here. Credentials stay in their
separate private credential location; no secret belongs in learner notes.

## Read and save

At the start of a chat, run `resume` and read profile/plan. The summary contains
three recent attempts, up to ten scheduled reviews, mastery counts, the active
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
```

Assignment JSON has exactly `problem` (the six-field API summary), `topic`
(internal curriculum ID), `stage` (1–3), `mode` (`topic`, `diagnostic`, `mixed`,
`review`). The store owns key, first-exposure flag and initial assistance.

Attempt JSON has exactly `session_id`, `result`, `assistance`, `failure`,
`transfer` (boolean), `evidence` (nonempty observed basis), `revisit_on` (ISO date
or null). Use a stable session ID per conversation/training session. Results:
accepted_reported, verified_correct, wrong, timeout, unsolved, abandoned.
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

Writes return a short receipt by default. Add `--full` only when the full
resulting state is needed. `resume` is read-only and does not change history.
