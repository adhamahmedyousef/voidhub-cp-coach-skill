# VoidHub training curriculum

This route spans programming foundations through advanced competitive programming.
It follows the requested camp's subject coverage with different grouping and
prerequisite-based pacing. A tracked topic does not guarantee a suitable CPC
exercise or a reviewed teaching resource is available in the archive.

## Route and starting point

Ask goal, time and reported strong/weak topics; use the saved programming
language, defaulting to C++. Record claims separately
from demonstrated ability. Diagnose with three real questions, one at a time,
then assess further gaps through targeted practice. Three questions cannot test
all 38 topics. Start at an evidenced gap rather than repeating known lessons.

C++ syntax, loops, functions, STL containers and comparators are supporting
lessons. Comprehension, tracing, proof, complexity and debugging recur throughout.
`curriculum.json` is the canonical catalog of coverage and prerequisites; load
only the entries needed for the current topic and its next candidate.

## Training tracks

The sequence is a planning guide; actual dependencies determine the order.
Math, graphs and DP can be interleaved as the learner's gaps require.

### Foundations

| Topic ID | Scope | Prerequisites |
| --- | --- | --- |
| `implementation` | Tracing, conditions, loops and simulation | Language basics |
| `arrays_strings` | Indexing, representation and traversal | implementation |
| `sorting_frequency` | Frequency arrays, ordering, custom comparators | arrays_strings |
| `math` | Parity, divisibility and invariants | implementation |

### Data techniques

| Topic ID | Scope | Prerequisites |
| --- | --- | --- |
| `prefix_sums` | Prefix/suffix, difference arrays and 2D sums | arrays_strings |
| `two_pointers` | Pointer invariants, fixed/variable windows | arrays_strings, sorting_frequency |
| `monotonic_stack` | Nearest greater/smaller, amortized analysis and sliding extrema | arrays_strings |

### Reasoning

| Topic ID | Scope | Prerequisites |
| --- | --- | --- |
| `binary_search` | Ordered search, monotone predicates, answer search | sorting_frequency |
| `greedy` | Exchange arguments and counterexamples | sorting_frequency |
| `number_theory` | GCD/LCM, primes, sieve, factorization, modular arithmetic and inverses | math |
| `counting` | Sum/product rules, combinations, permutations and modular counting | number_theory |
| `bitwise` | Binary representation, shifts, set tests and subset enumeration | math |

### Search

| Topic ID | Scope | Prerequisites |
| --- | --- | --- |
| `backtracking` | Enumeration, pruning and undoing state | recursion |
| `recursion` | Call stack, base cases, recurrence and divide-and-conquer | implementation |

### Graphs

| Topic ID | Scope | Prerequisites |
| --- | --- | --- |
| `bfs_dfs` | Flood fill, components, bipartiteness, unweighted and multisource BFS | arrays_strings, recursion |
| `dsu` | Connectivity, path compression and union by size | bfs_dfs |
| `dijkstra` | Nonnegative weighted paths, priority queues and modelling | bfs_dfs |
| `topological_sort` | Dependencies, Kahn/DFS ordering and cycle detection | bfs_dfs |

### Dynamic programming

| Topic ID | Scope | Prerequisites |
| --- | --- | --- |
| `dp` | States, transitions, base cases, simple grid and knapsack | recursion |
| `dp_ranges` | Range transitions; use proven structure rather than assumed optimization | dp, segment_tree |
| `digit_dp` | Position, tightness, leading zero and range subtraction | dp, number_theory |
| `bitmask_dp` | Subset states, transitions and exponential bounds | dp, bitwise |

### Range queries

| Topic ID | Scope | Prerequisites |
| --- | --- | --- |
| `fenwick` | Point updates, prefix/range queries and indexing invariants | prefix_sums, bitwise |
| `sparse_table` | Static idempotent queries and overlapping blocks | prefix_sums, bitwise |
| `segment_tree` | Merge identity, build, point update and interval query | recursion, prefix_sums |
| `merge_sort_tree` | Sorted node vectors and static range counting | segment_tree, binary_search |
| `lazy_segment_tree` | Range operations, tag composition and push/pull invariants | segment_tree |

### Advanced connectivity

| Topic ID | Scope | Prerequisites |
| --- | --- | --- |
| `rollback_dsu` | Change stack, snapshots and offline dynamic connectivity; no unsafe path compression | dsu |
| `mst` | Kruskal/Prim, cut property and disconnected graphs | dsu, greedy |

### Trees

| Topic ID | Scope | Prerequisites |
| --- | --- | --- |
| `euler_tour` | Entry/exit intervals, subtree ranges and DFS representation | bfs_dfs, prefix_sums |
| `lca` | Ancestor jumps, depth alignment and path queries | euler_tour, bitwise |
| `dsu_on_tree` | Merge-size argument, sack retention and clearing | euler_tour, sorting_frequency |

### Strings

| Topic ID | Scope | Prerequisites |
| --- | --- | --- |
| `kmp` | Prefix function, fallback links, matching and automaton DP | arrays_strings, dp |
| `z_algorithm` | Z-box invariant, matching and borders | arrays_strings |
| `trie` | Prefix representation, insert/query and memory bounds | arrays_strings |
| `binary_trie` | Bitwise traversal and XOR queries | trie, bitwise |
| `hashing` | Substring normalization and probabilistic collision limits | arrays_strings, number_theory |
| `dynamic_hashing` | Maintain hash merges under updates; preserve collision caveats | hashing, segment_tree |

## Stages and the coach's decision

Every topic has direct application, adaptation and mixed recognition stages.
Each stage needs three distinct independent successes, including an unseen
transfer task. Earlier stages cannot be skipped. The store derives eligibility;
the coach checks understanding, complexity, coverage and prerequisites.

After a reviewed outcome, the coach records continue, advance or review_prerequisite.
If the learner cannot explain correctness, misjudges cost or needs algorithmic
help, stay on the stage and target that gap. Watching a video, reporting confidence
or repeating a question does not count as unseen transfer or independent mastery.

Advance one stage at a time only with the required evidence and all four explicit
checks. Move to another topic after the source's third stage, with direct-application
evidence for target prerequisites. An unfinished question blocks advancement.
Save the decision and reason before announcing it; give one concrete next task.

A diagnosed starting point is not an earned advancement. Respect a learner's
request to explore elsewhere, record reassessment and keep prior mastery unchanged.
Review contradictory new failures instead of deleting earlier evidence.

## Sustainable practice

Use the actual weekly time and solving pace. A block normally contains an
explanation if needed, one understanding check, one real question and review.
Reserve time for assisted upsolving and mixed practice. Missed sessions call
for a smaller realistic workload rather than a growing backlog.

Choose a suitable video through [RESOURCES.md](RESOURCES.md) when it addresses
the current gap. Follow viewing with a trace/explanation and independent practice.
If bounded archive search finds no suitable problem, record the gap and defer
assignment rather than inventing a contest question or misusing a low rating.

Flow, computational geometry and subjects outside the catalog remain outside
this route until their curriculum and tracking are added. Educational judgment,
source quality and semantic transfer still require actual session review.
