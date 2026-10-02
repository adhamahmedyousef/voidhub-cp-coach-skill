# Beginner-to-intermediate curriculum

The learner can enter at a diagnosed point. Prerequisites describe demonstrated
skills, not a mandatory lecture sequence. Explain and check missing knowledge
before assigning tasks that depend on it. API ratings are archive metadata and
may be defaults; do not interpret them as reviewed educational levels.

## VoidHub learning route

Organize training around five practical capabilities rather than numbered camp
levels. Select the next capability from the learner's goal, prerequisite gaps
and observed attempts. Topics remain standard algorithm names because renaming
them would make practice less precise; their grouping, emphasis and pacing are
specific to this coach. No external roadmap is required to use this curriculum.

| Capability | Learning focus | Tracked topics |
| --- | --- | --- |
| Understand and implement | Extract the task, trace examples, represent data, implement and debug edge cases | implementation, arrays_strings |
| Organize and preprocess data | Count, order, aggregate and answer range questions; justify time/memory | sorting_frequency, math, prefix_sums |
| Choose and justify an approach | Establish monotonicity, pointer invariants and local-choice correctness | two_pointers, binary_search, greedy |
| Explore states and dependencies | Bound enumeration; model grids/graphs; choose traversal or search | backtracking, bfs_dfs |
| Connect and reuse results | Model connectivity, weighted paths and reusable subproblems | dsu, dijkstra, dp |

These capabilities overlap; they are not five certificates or five weeks.
For example, a learner strong in implementation but weak in choosing an approach
can work on reasoning while reviewing only the missing preprocessing skill.
A beginner needs language, loops and indexing first; an experienced learner
should not repeat those lessons merely to follow an ordered list.

### Select the starting point

Ask which topics the learner believes they handle well, which they have only
studied and which feel difficult. Ask for a recent representative problem or
explanation when it materially helps diagnosis; do not require proof for every
self-report before practice can begin. Save the reported topic map in profile.
Three diagnostic problems sample selected gaps; they cannot establish mastery
of every topic. Use later targeted practice to confirm individual strengths.

Use self-reports to choose diagnosis and avoid unnecessary lectures. Preserve
the distinction between a claimed strength, an observed successful application
and mastery supported by independent attempts. A single accepted problem does
not establish strength across a whole algorithm family. Existing topic stages
provide evidence; review explanation, coverage and transfer before advancing.

### Teach the missing skill

Language syntax and STL are supporting lessons taught as needed. Statement
comprehension, tracing, complexity, invariants, proofs and debugging are assessed
throughout the route, rather than postponed to a separate final chapter.
Retain recurring gaps and demonstrated strengths in profile; put the current
subtopic and concrete next exercise in plan. Do not create extra tracked IDs
for each lecture or count a supporting lesson as a solved problem.

Adapt combinations to readiness: frequency with sorting, prefix sums with
range reasoning, answer search with a check function, recursion with bounded
search, graph modelling with traversal, then simple state transitions for DP.
Use small instructional examples before real CPC practice where needed, and
label those examples clearly rather than assigning them invented contest sources.

### Plan a sustainable week

Choose workload from the learner's available time and actual solving pace.
Normally combine explanation when needed, one question, review and a saved next
step. Reserve time for assisted upsolving and mixed practice. Missed sessions
trigger a smaller realistic plan rather than an accumulating backlog.

Advance only after the required independent evidence and lesson coverage.
When time or archive availability is limited, narrow the target skill; do not
assign an unsuitable harder problem simply to fill a weekly slot. If bounded
search finds no suitable problem, explain the gap and save the pending action.

### Current scope

The tracked route covers the thirteen topics below. Monotonic stacks, dedicated
number-theory subtopics, range-query structures, advanced DP, advanced tree
methods and string algorithms need their own curriculum and tracking extension
before they can be advertised as supported mastery paths. Record a learner's
request for such material; do not disguise it under a related basic topic.

## Tracked topics and mastery

Every topic has three stages: (1) direct application and explanation, (2)
combination/adaptation, (3) recognition in mixed practice. Each stage needs three
different independent successes, including at least one unseen transfer task.
The store derives eligibility from actual records. Never pre-fill mastery.

| Internal topic | Prerequisite skills | Stage 1 → 2 → 3 | Candidate tag hints |
| --- | --- | --- | --- |
| implementation | Basic I/O, loops, conditions | Simulation → edge cases/state → selecting a simple model | implementation |
| arrays_strings | Implementation | Traversal/indexing → transformations → choosing a representation | strings, implementation |
| sorting_frequency | Arrays/strings | Sort/count → grouping/order properties → recognition | sortings, sorting |
| math | Implementation | Parity/divisibility/counting → formulas/invariants → recognizing structure | math |
| prefix_sums | Arrays, arithmetic | Static range sums → differences/2D prefix sums → choosing preprocessing | prefix sums |
| two_pointers | Arrays, sorting where needed | Pointer invariants → windows/pair counting → recognizing monotonic movement | two pointers |
| binary_search | Sorted order, proof of monotonicity | Search in an ordered domain → answer search/check function → recognition/proof | binary search |
| greedy | Sorting, invariants/proof | Local choice → exchange argument → testing when greedy fails | greedy |
| backtracking | Recursion, complexity | Enumeration → pruning/state undo → selecting bounded search | brute force, backtracking |
| bfs_dfs | Arrays, recursion/queue, graph representation | Reachability/grid → components, multi-source BFS and DAG ordering → selecting traversal | dfs and similar, graphs |
| dsu | Graph connectivity | Union/find → offline connectivity → choosing DSU over traversal | dsu |
| dijkstra | BFS, weighted graphs, priority queue | Nonnegative shortest path → graph modelling → method selection | shortest paths |
| dp | Recursion/state, complexity | Simple state/transition → knapsack/grid → recognizing subproblems | dp |

Candidate tags are search hints, not a guaranteed vocabulary. An empty exact-tag
query may mean the archive uses a different name. Inspect bounded metadata
without that tag and confirm the intended topic from the full problem. Do not
invent tags, difficulty, statements or suitability from names alone.

Stage 2/3 combinations can require multiple completed foundations. If an archive
question depends on an advanced concept outside this table, postpone it or
explicitly mark it outside v1 rather than disguising it as beginner practice.
Advanced trees/segment trees, flow, geometry and advanced DP are outside v1.

For initial calibration use a small range around reported ability (or easy
implementation for a complete beginner), then adjust using observed performance.
No fixed rating range guarantees topic fit or readiness. Record why a selected
question targets the learner's demonstrated gap.
