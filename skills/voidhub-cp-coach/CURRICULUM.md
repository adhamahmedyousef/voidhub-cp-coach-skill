# Beginner-to-intermediate curriculum

The learner can enter at a diagnosed point. Prerequisites describe demonstrated
skills, not a mandatory lecture sequence. Explain and check missing knowledge
before assigning tasks that depend on it. API ratings are archive metadata and
may be defaults; do not interpret them as reviewed educational levels.

## Intensive Camps learning route

Use the learner's requested camp route when building the weekly plan. This route
is adapted from [Intensive Camps — Wave 2](https://roadmap.sh/r/intensive-camps---wave-2)
by Hamed Mohamed / Intensive Training, inspected on 2026-10-02. The source gives
session groups; this skill adds diagnosis, paced practice and evidence-based
reviews. Camp levels and the three mastery stages below are different axes.
A session is a unit of content, not a promise to finish it in one sitting.

### Level 0: programming foundations

Start here only where diagnosis reveals missing foundations. Follow this order:

| Learning block | Coaching treatment | Persistent topic |
| --- | --- | --- |
| C++ input/output, variables and conditions, then loops | Explain, trace a small example, check understanding, then practice | implementation |
| Arrays, strings and frequency arrays | Indexing, traversal, counting and representation | arrays_strings, sorting_frequency |
| Complexity and tracing | Estimate time/memory and manually trace each learner's approach | Cross-cutting; store observed gaps in profile |
| Basic math and bit operations | Divisibility, parity, gcd/lcm and simple bit operations as needed | math |
| Functions, sorting and custom comparators | Reusable functions, ordering and comparator correctness | sorting_frequency |
| Prefix/suffix sums, partial sums and 2D prefix sums | Range preprocessing before adapting it to another representation | prefix_sums |
| C++ STL foundations | Teach required containers and operations before using them | Supporting lessons; retain coverage in plan |
| Two pointers | Pointer invariants, windows and movement | two_pointers |

Monotonic stacks appear in the source beside two pointers but require a distinct
invariant. They are a gap in the current tracked curriculum: do not silently
count their mastery as two-pointers progress or claim full Level 0 completion.

### Level 1: algorithm foundations

Follow binary search, elementary number theory, recursion, backtracking, bounded
bitmask enumeration, DFS, BFS, elementary counting and introductory DP. Teach
missing prerequisites before assigning dependent practice.

Binary search uses `binary_search`. Elementary number theory and counting use
`math`; scope lessons to the learner's current gap rather than claiming all
number theory is covered. Introduce recursion before `backtracking`, and use
small bitmask searches only where the state count can be justified. Graph
practice uses `bfs_dfs`: begin with reachability, flood fill and components;
then teach bipartiteness, multi-source BFS and topological ordering when the
needed foundations are demonstrated. Introductory dynamic programming uses `dp`.

Record the exact camp lesson and remaining subtopics in `plan.md`. Existing
mastery IDs aggregate broad topics, not individual camp-session certificates.
The script's eligibility is necessary evidence; the coach must also check lesson
coverage and prerequisites before marking a camp block complete. Optional
`greedy`, `dsu` and `dijkstra` are taught when a practice task or later route
requires them, rather than jumping to them because a tag appears.

### Level 2: extension boundary

The source continues into range-query structures, advanced DP, advanced graph
and tree methods, and string algorithms. This version supports basic DSU and
Dijkstra, but has no separate tracking for Fenwick/sparse tables, segment-tree
variants, digit/bitmask DP, rollback DSU/MST, Euler tours, LCA, DSU on tree,
KMP/Z, tries or hashing. Do not advertise Level 2 as implemented or credit it
under a loosely related basic topic. Persist the learner's requested advanced
route in the plan and state which curriculum/tracking extension it needs.

### Pacing and practice

Use the actual weekly time rather than a fixed camp duration. A study block
normally combines a short explanation, a trace or understanding check, one real
CPC problem and a review. Add another independent problem only after the learner
finishes the active one. Reserve some available time for assisted upsolving and
mixed practice instead of filling every hour with new content.

A learner who already knows loops and arrays can start at an evidenced gap;
do not replay Level 0 lectures automatically. If no suitable CPC question exists
within readiness and the bounded search budget, defer that exercise and record
why. Instructional mini-examples must be labeled as examples, never attributed
to a contest. Persist the camp lesson and next action in the session handoff.

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
