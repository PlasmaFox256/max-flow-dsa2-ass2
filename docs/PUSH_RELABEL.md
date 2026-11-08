# FIFO push–relabel

Primary author: Dima. Implementation: `src/algorithms/push_relabel.cpp`.

## Algorithm

The solver maintains a preflow, per-vertex excess and heights, a FIFO queue of
active internal vertices, and a current-edge cursor for each vertex. All state
is allocated inside the solver call; it uses the existing shared graph API.

1. Give the source height `vertex_count`, leave other heights zero, and saturate
   residual edges leaving the source. Track net outflow as negative source excess.
2. Queue each internal vertex with positive excess, without duplicates.
3. Fully discharge the next vertex. Push along positive-residual edges only when
   its height is exactly one greater than the destination's height. Push the
   smaller of the available excess and residual capacity.
4. When the edge cursor reaches the end, relabel to one plus the minimum height
   of a positive-residual neighbor, then restart the cursor.
5. Finish when no internal excess remains; return the sink's excess.

Previously scanned inadmissible edges need not be rescanned before a relabel:
neighbor heights only increase. A vertex remains marked queued throughout its
discharge, then becomes eligible for future activation after leaving with zero
excess. Source and sink are never discharged.

## Correctness and limits

Pushes update residual edge pairs through `Graph::push`, so capacity constraints
are preserved. Excess is moved between endpoints without loss. Initialization
and relabeling preserve the valid-height condition on every positive-residual
edge. With source height `n` and sink height zero, this rules out a residual
source-to-sink path. At termination internal excess is zero, so the preflow is a
feasible flow; the absence of an augmenting path establishes maximality.

An active vertex always has a residual route back toward the source. Therefore
relabeling has a residual neighbor available, and excess trapped away from the
sink can eventually return to the source. The solver explicitly checks this
neighbor invariant rather than wrapping a height sentinel if it is violated.

On simple graphs the FIFO policy has the standard `O(V^3)` worst-case time bound. Algorithm-local
storage is `O(V)` in addition to the shared `O(V + E)` residual graph. This is the
baseline variant: no global relabeling, gap heuristic, or highest-label policy.
Keep any future heuristic version separately selectable for comparisons.

The shared contract requires a fresh or reset graph and valid, distinct
terminals; invalid terminals are rejected defensively. Capacities and their
total sum must fit in signed 64 bits, as enforced by the graph. The solver
performs no I/O, resets, or timing and preserves the shared interface and topology.

## Reproduce verification

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
python3 scripts/benchmark.py --output results/push-relabel-smoke.csv
```

Repeat the build/tests with `build-debug` and `-DCMAKE_BUILD_TYPE=Debug`.
The existing 250 seeded random cases use exhaustive minimum-cut answers. The
additional exhaustive suite covers every simple directed unit-capacity graph
on four vertices and every distinct terminal pair. Every successful solve also
passes the independent feasible-flow and minimum-cut certificate verifier.
The smoke experiment has 48 verified rows for each implemented algorithm.
These are correctness and pipeline checks, not evidence for performance
conclusions. See the [full experiment results](../experiments/RESULTS.md) for the
paired performance comparison and its limitations.
