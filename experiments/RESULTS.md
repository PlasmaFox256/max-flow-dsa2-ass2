# Maximum-flow benchmark results

## What was run

The final run on 8 November 2026 completed **2,398 process measurement batches**:
1,800 in the fixed main grid, 490 in the crossover follow-up, and 108 in the
terminal-capacity control. All succeeded. Every measured solve and warm-up passed
the residual capacity, conservation, and minimum-cut certificate verifier; both
algorithms returned the same flow for each input. The three known-optimum main
families and both controlled variants also matched their analytic answers.

The main grid contains 180 family/size/seed cases. Follow-ups add 35 and 18 cases,
respectively; five disjoint-path cases at n=32 repeat a main-grid input and are
separate measurement sessions, not additional independent graphs.

Measured source revision: `fa09cdc27298e4bd1a8bb875d745a99271d4dc54`.
The algorithm modules were unchanged from the starting branch. Final artifact
commits add these data and interpretation without changing the measured code.

Hardware was an Apple M2, 8 logical CPUs, 16 GiB RAM, running macOS 26.7 on AC
power. C++17 was compiled with Apple Clang 21.0.0, `-O3 -DNDEBUG`, without LTO
or added solver heuristics. The runner used Python 3.14.7. Exact build commands,
compiler identity, input/binary/source hashes, configuration and timestamps are
in each `raw.metadata.json`. The main run took approximately 128 seconds wall
time, the crossover session 1.5 seconds, and the capacity control 20 seconds.
These durations include untimed parsing, reset, verification and orchestration;
they are not algorithm runtime measurements.

See [PLAN.md](PLAN.md) for full graph definitions, predictions and protocol, and
the [repository README](../README.md#full-comparison-experiment) for reproduction.
The exploratory pilot and first full rehearsal are excluded. The final sessions
ran sequentially after all build and solver tests finished.

## How to read the data

- `raw.csv`: every process batch, in execution order. `seconds` is the mean of
  its timed solver calls; `iterations` and `solver_seconds_total` retain the
  denominator and total. These are warm-cache, solver-only wall times.
- `paired.csv`: median batch time across repetitions for each algorithm on each
  seed/input. Min/max batch means expose within-input measurement variation.
- `summary.csv`: median of those seed medians for each algorithm, plus geometric
  mean of the paired **EK/PR** ratios, ratio range, and seed win counts.
- `instances.csv`: input manifest and hashes. `structure.csv`: density, initial
  shortest path, terminal capacity sums, optimum and initial PR preflow return.

**EK/PR > 1 favors push–relabel; < 1 favors Edmonds–Karp.** Geometric mean paired
ratios need not equal the ratio of the two aggregate median times. Seeds for
disjoint paths and dead ends vary insertion order only, not topology. No confidence
interval or claim of statistical significance is inferred from five seeds.

## Main grid: structure changes the winner

At n=1,024, the results were:

| Family | EK median (ms) | PR median (ms) | Paired EK/PR geometric mean | PR seed wins |
| --- | ---: | ---: | ---: | ---: |
| Sparse random | 0.1262 | 0.2762 | 0.3051 | 1/5 |
| Dense random | 82.43 | 2,062 | 0.4197 | 2/5 |
| Banded DAG (`layered`) | 34.35 | 341.6 | 1.0749 | 2/5 |
| Middle unit bottleneck | 0.02598 | 53.40 | 0.0005 | 0/5 |
| Independent length-two paths | 1.022 | 0.02457 | 41.6271 | 5/5 |
| Dead-end chain | 0.006664 | 17.85 | 0.0004 | 0/5 |

These are distribution summaries, not interchangeable examples of a typical
graph. In particular, the banded-DAG geometric mean near 1 conceals a ratio range
of **0.0937–87.48**. Dense ratios range **0.0339–17.23**. Seed-level points are
essential in plots; a single averaged line would hide the principal finding.

The independent-path family strongly favors PR as size increases. EK must
perform n-2 augmentations, clearing its n-element predecessor array for each
search. That alone creates quadratic work on this family. PR can discharge each
intermediate vertex with a bounded number of local operations, giving linear
work for these particular graphs. At n=32 its paired advantage is about 1.76x;
by n=1,024 it is about 41.6x. This explains a trend using actual algorithm
structure rather than generic worst-case bounds.

The bottleneck and dead-end families strongly favor EK at every tested size.
Their optimum is 1, so EK needs one successful augmentation and one final failed
search. PR saturates source edges before knowing which excess can reach the
sink, then must return stranded excess. The dead-end chain deliberately exposes
this cost: positive excess can move back and forth while valid heights increase
enough to send it back to a source initially at height n. Returning a feasible
maximum flow is part of the shared contract, so this work is included fairly.

Sparse random inputs favor EK in 27 of the 30 seed/size cases. Neither the dense
nor banded family has a clean, monotonic, seed-independent size crossover. The
dense geometric ratio barely exceeds 1 at n=512 and falls below it at n=1,024;
this does not establish a general density threshold or an exact crossover.

## A bracketed crossover on independent short paths

The follow-up tests smaller versions of the same family, with seven repetitions
per seed. It was motivated by PR already winning at the smallest main-grid size.

| Vertices | Paired EK/PR geometric mean | PR seed wins |
| ---: | ---: | ---: |
| 4 | 0.5421 | 0/5 |
| 6 | 0.6159 | 0/5 |
| 8 | 0.7692 | 0/5 |
| 12 | 0.9111 | 0/5 |
| 16 | 1.1896 | 5/5 |
| 24 | 1.2818 | 5/5 |
| 32 | 1.6453 | 5/5 |

The observed crossover is **between n=12 and n=16** on this machine and protocol.
All five orderings favor EK at n=12 and PR at n=16. This is a bracket, not a
measurement at every intervening integer. At n=12 median times are about
0.315 microseconds for EK and 0.336 microseconds for PR; at n=16 they are about
0.477 and 0.394 microseconds. Such short calls are sensitive to clock and allocator
overhead. The large-n separation is more convincing than an exact small-n
threshold, and this threshold must not be generalized to other graph families.

## The surprise: a little stranded preflow can matter greatly

The initial prediction was that density would make PR reliably more competitive
because EK repeatedly scans edges during BFS. The result was much more conditional.
At n=1,024, dense PR times split into two distinct groups:

| Seed | Source outgoing capacity | Maximum flow | Initial preflow returned | PR median (ms) |
| ---: | ---: | ---: | ---: | ---: |
| 11 | 13,155 | 12,022 | 1,133 | 2,726 |
| 22 | 12,955 | 12,897 | 58 | 2,062 |
| 33 | 12,798 | 12,798 | 0 | 3.815 |
| 44 | 11,931 | 11,931 | 0 | 3.774 |
| 55 | 12,456 | 12,055 | 401 | 2,454 |

Seed 22 returns only 58 units, less than 0.5% of its initial source preflow, yet
is hundreds of times slower than the zero-return cases. The amount of excess
alone does not predict the work needed to return it. The banded family shows
the same association at n=1,024: all three cases requiring return have PR times
around 0.34 seconds; the two zero-return cases take about 0.00037 and 0.00234
seconds. This is an association across generated inputs, not itself a causal test.

The follow-up therefore holds dense topology, internal capacities and edge order
fixed for each seed, swapping only the terminal capacity placement. Both variants
have optimum n-2 and EK performs n-2 augmentations. At n=512:

| Capacity placement | Initial preflow returned | EK median (ms) | PR median (ms) |
| --- | ---: | ---: | ---: |
| Source arcs 1, sink arcs 100 | 0 | 0.6413 | 1.605 |
| Source arcs 100, sink arcs 1 | 50,490 | 150.4 | 755.4 |

PR is approximately **471x slower** in the sink-limited variant. This supports
the importance of stranded-preflow handling, but EK also becomes approximately
234x slower. Equal augmentation counts do not mean equal BFS work: when source
arcs retain residual capacity, searches can repeatedly reach already used
intermediate vertices and scan their outgoing edges. EK still wins all seeds
in both controlled variants; the control does not create a PR-winning regime.

Our interpretation is that FIFO PR without global relabeling or the gap heuristic
can spend substantial work updating local heights after the useful sink capacity
is exhausted. Excess cannot return directly to a source of height n until suitable
height differences develop. The controlled result and the source-return diagnostic
support this mechanism. We did not collect operation counters or a profiler trace,
so the precise split between scanning, pushing and relabeling remains unmeasured.

## Limits and conclusions

These results compare Sam's EK and Dima's baseline FIFO PR, not all implementations
of either algorithm. Global relabeling and gap heuristics are absent. We measured
runtime, not peak memory. Graph density, size and topology are varied; general
capacity distributions, cut positions, parallel edges and real application data
are not comprehensively explored. The planted-chain ordering in the original
four generators is another explicit distribution choice.

The repeated-solve policy has a 1,024-iteration cap. Consequently 625/1,800 main
batches, all 490 crossover batches, and 18/108 control batches accumulate less
than the nominal 10 ms target. None are silently discarded. Each individual
solve retains a timer pair, and warm-up/reset/verification keep graph data warm;
this is not a cold-cache or end-to-end application benchmark. Final comparisons
use five independent process repetitions for the main grid, seven for the
crossover, and three for the control. Repeated calls within one batch are not
independent graph samples. No artificial overhead subtraction is applied.

The laptop was connected to AC power, but CPU affinity, thermal state, frequency
and other system activity were not controlled. Randomized paired order and
medians reduce sensitivity to these effects; they do not remove it. Near-unity
ratios should be interpreted cautiously and seed ranges should accompany plots.

The defensible conclusion is input-sensitive: PR wins decisively on many short
independent routes, EK wins decisively when very little useful flow coexists with
stranded preflow, and random dense/banded cases can change winner with terminal
capacity structure. The short-path family gives a concrete observed crossover;
the dense cases explain why worst-case asymptotics alone do not predict it.
