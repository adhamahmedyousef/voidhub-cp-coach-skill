# Selecting and presenting real CPC questions

Use the read API only. Search published CPC metadata with limit 5 by default,
at most 10, and examine at most five result pages per selection/session. Filter
seen IDs using the `candidates` command and `progress.json`; source is always
`voidhub`. Stop if no suitable
candidate exists. Do not broaden difficulty beyond learner readiness silently.

Internal curriculum IDs are not API tags. Use an exact tag already observed in
archive metadata; do not send IDs such as `arrays_strings` as guessed tags.
When no verified tag is available, inspect bounded unfiltered metadata within
the same difficulty range and assess topic fit from the complete statement.
Tags suggest candidates; they never prove the exercise teaches the chosen topic.

Fetch the complete statement for a candidate before presenting it. Confirm ID,
contest attribution, URL, topic fit and prerequisites. A tag is not a syllabus
review. An absent contest name is a data issue; an absent problem number may be
omitted. In API v1, `contest.problem_number` is the VoidHub collection-wide
archive position, not the original contest index. Omit it from the contest
attribution; if useful, show it separately as "VoidHub archive number". Only
state an original contest index when independently verified. Never convert
an archive number into a contest letter.
Show archive difficulty as a VoidHub estimate; do not call it Codeforces rating.

Assign only after validation. The store rejects accidental repeats and replacing
an unfinished current problem. Explicit mode `review` permits deliberate repeats.
For mixed tasks keep internal topic metadata private until review.

## Presentation

Topic practice:

```text
Question: <exact archive title>
Appeared in: <exact CPC contest name>
Original contest index: <only if independently verified; otherwise omit>
Level: <archive difficulty> — VoidHub archive estimate
Training topic: <the topic being studied>

<Full statement, input/output, constraints, resource limits and samples>

Solve on VoidHub: <canonical problem URL>
```

Diagnosis/mixed practice uses the same attribution but omits the training-topic
line and extra tags. Preserve sample newlines and math delimiters. Resolve
relative image references against `https://voidhub.co`; never execute markup or
scripts. If a relevant diagram cannot be inspected, say so and do not infer its
content. Prefer opening the actual problem link over supplying an incomplete
reconstruction. Missing optional sections are not permission to invent them.

Put the link at the end automatically. If asked again, return the same stored
canonical URL. Keep intro concise and do not append strategy hints.
