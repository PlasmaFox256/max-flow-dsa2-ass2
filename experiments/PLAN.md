# Maximum-flow comparison: experiment plan

Written before inspecting the pilot timings. The pilot checks feasibility and
the measurement pipeline; it is excluded from the final CSV and all summaries.

## Questions and predictions

We compare the existing C++17 Edmonds–Karp and FIFO push–relabel implementations,
without adding optimization heuristics to either one. Both must return a feasible
maximum flow, including returning stranded excess to the source in push–relabel.

1. Does increasing density make push–relabel more competitive? Predict yes:
   repeated BFS searches scan more residual edges, whereas current-arc pointers
   can avoid repeating some scans during discharge. This is a hypothesis, not
   a consequence of the worst-case bounds for every generated graph.
2. Do many short independent routes favor push–relabel? Predict yes at larger
   sizes: EK needs one augmentation per unit route; PR distributes flow locally.
3. Do low cuts and dead ends favor EK? Predict yes: EK can stop after very few
   augmentations, whereas PR initially commits flow that may need to return.
4. Is there one crossover size? Predict no: crossover depends on structure,
   not just vertex count. Report observed reversals or their absence honestly.

## Inputs

All graphs are directed, simple (no duplicate ordered pairs), use source 0 and
sink n-1, and have positive integer capacities. Sizes are 32, 64, 128, 256, 512,
1024. Every family/size uses seeds 11, 22, 33, 44, 55. Random capacities are
uniform integers 1..100 unless stated below. Generation uses Python's seeded
`random.Random`; exact file hashes are retained. Increasing sizes are fresh
instances, not induced subgraphs of one graph.

| Family | Generation and reason |
| --- | --- |
| sparse | Plant a forward chain; add unique random directed pairs until m=4n. Probes bounded average degree with cycles and alternate routes. |
| dense | Plant a chain; independently consider each ordered pair with probability .25, adding a random-capacity edge if absent. Probes density at the same n. |
| layered | Plant a chain; add every forward pair at distance at most floor(sqrt(n)), minimum width 2. This is a banded DAG, not random fully connected layers. Probes long routes and local connectivity. |
| bottleneck | Plant a chain, set its middle cross edge to capacity 1; make 5n attempts to add edges within randomly selected halves. This is the only edge crossing from the source half to the sink half: optimum exactly 1. Probes stranded preflow around a restricted cut. |
| disjoint_paths | n-2 independent s-v-t paths, all capacities 1; optimum n-2. Seeds only shuffle insertion order. Isolates augmenting-path count without density. |
| dead_end | s-1-t has capacity 1; s-2 and chain 2-3-...-(n-2) have capacity 100 with no connection to t. Optimum 1. Seeds only shuffle insertion order. Isolates return of stranded excess. |

The first four families reuse the original framework generator unchanged.
Its planted chain is inserted first and is an acknowledged ordering bias;
results describe these distributions rather than arbitrary graphs. For the last
two, seed variation measures insertion-order sensitivity, not different topology.
Capacity magnitude and cut position are fixed, not independent experimental axes.

## Measurement protocol

- Same Release binary, shared residual graph representation, 64-bit capacities,
  compiler and flags for both algorithms. No algorithm implementation changes.
- Run processes sequentially. Randomly shuffle instance/repetition pairs with
  seed 20261108; randomize which algorithm runs first within each pair. Five
  independent process repetitions per instance and algorithm.
- Each process parses one input, performs one untimed verified warm-up, then
  measures repeated solves until accumulated solver time >=10 ms or 1024
  solves, whichever happens first. Each solve starts from `Graph::reset()`.
  Reset and full verification are outside the timed interval. The CSV records
  actual iterations and accumulated solver seconds, not just a final average.
- `std::chrono::steady_clock` measures wall time around each solver call.
  Solver allocations/initialization are included. File I/O, parsing, initial
  graph construction, reset, verification, Python and process startup are not.
  A timer pair remains around each individual solve; batching provides repeated
  sampling but does not eliminate timer overhead on extremely short runs.
- Every warm-up and measured solve passes the shared capacity/conservation/
  residual-cut verifier. Compare returned flows between algorithms on the same
  SHA-256 input, and check the three known-optimum families independently.
  Existing exhaustive tiny-graph tests provide an independent minimum-cut oracle.
- Whole-process timeout 30 s; save explicit failures/timeouts, never treat them
  as measured solver times. Any failure makes the runner exit nonzero.
- Preserve hardware, memory, OS, Python, compiler, build cache, compile commands,
  source hashes, binary hash, timestamps and power snapshot in metadata. A laptop
  is not an isolated benchmark host: scheduling, CPU frequency and thermal state
  remain uncontrolled. Randomized paired order mitigates but cannot remove them.

## Analysis and stopping rules

The fixed main grid contains 180 instances and 1800 measured process batches.
Within each seed and algorithm, take the median of the five batch means. Then
form the paired ratio `EK seconds / PR seconds`; >1 favors PR. Summarize each
family/size with median times across seeds, geometric mean paired ratio, min/max
paired ratio, and number of seed cases favoring each algorithm. Retain per-seed
summaries and within-instance min/max timings so variance is visible. Five
repetitions of one input are not five independent graph samples.

A reversal between tested sizes brackets a possible crossover for this input
distribution. It does not locate an exact universal threshold. Ratios close to
one with seed disagreement are inconclusive. Do not discard slow samples or
select only the winning seeds. Do not manufacture a surprise: compare the
observations with the predictions above and record whether any are contradicted.
If a follow-up is warranted, label its separate configuration and CSV, and
explain the result that motivated it. No further graph families or sizes are
added to the fixed main grid after seeing its results.

## Follow-ups declared after the rehearsal, before final measurement

The first complete pass was classified as rehearsal because harness tests ran
briefly alongside it. It is retained locally under ignored `results/rehearsal/`
and is excluded from final summaries. All final measurement jobs run sequentially
after tests finish; no build, solver tests, or other experiment runs overlap them.

The rehearsal motivated two separately labeled follow-ups:

- `crossover.json`: disjoint paths at n=4,6,8,12,16,24,32, the same five seeds,
  seven repetitions. The main grid starts with PR already ahead on this family;
  smaller sizes may bracket where its overhead first pays off. Submicrosecond
  differences remain sensitive to timer overhead and this machine.
- `cut_control.json`: three seeds, three repetitions at n=64,256,512. Both
  variants have every s-v and v-t edge, plus internal directed pairs independently
  sampled at probability .25 with capacities 1..100. Source-limited sets source
  arcs to 1 and sink arcs to 100; sink-limited swaps those capacities. Both
  have the same topology, internal capacities and insertion order for a seed,
  and both have optimum n-2. Only terminal capacity placement changes. Predict
  PR is slower for the sink-limited case: initial preflow is 100(n-2), so 99(n-2)
  must return to s. EK needs exactly n-2 augmentations of the direct length-two
  paths in both cases. This tests a mechanism suggested by the rehearsal rather
  than claiming a preplanned independent discovery.

`structure.csv` records input density, initial shortest path, source/sink capacity
and `source_out_capacity - max_flow`. That last number is exactly the net capacity
the initial PR preflow must return to the source. It is a structural diagnostic,
not an operation count or profiler measurement. No memory benchmark is conducted.
