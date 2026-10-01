# Beginner-to-intermediate curriculum

The learner can enter at a diagnosed point. Prerequisites describe demonstrated
skills, not a mandatory lecture sequence. Explain and check missing knowledge
before assigning tasks that depend on it. API ratings are archive metadata and
may be defaults; do not interpret them as reviewed educational levels.

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
| prefix_sums | Arrays, arithmetic | Static range sums → differences/transformed arrays → choosing preprocessing | prefix sums |
| two_pointers | Arrays, sorting where needed | Pointer invariants → windows/pair counting → recognizing monotonic movement | two pointers |
| binary_search | Sorted order, proof of monotonicity | Search in an ordered domain → answer search/check function → recognition/proof | binary search |
| greedy | Sorting, invariants/proof | Local choice → exchange argument → testing when greedy fails | greedy |
| backtracking | Recursion, complexity | Enumeration → pruning/state undo → selecting bounded search | brute force, backtracking |
| bfs_dfs | Arrays, recursion/queue, graph representation | Reachability/grid → components/implicit graphs → selecting traversal | dfs and similar, graphs |
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
