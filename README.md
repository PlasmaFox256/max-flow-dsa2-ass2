# Theory versus practice: maximum flow

A shared C++17 framework for comparing Edmonds–Karp (primary author: **Sam**)
and FIFO push–relabel (primary author: **Dima**).

**Status:** Both algorithms are implemented and pass the shared and exhaustive
correctness tests. FIFO push–relabel includes current-edge pointers and full
excess discharge, without global-relabel or gap heuristics.
See [push–relabel implementation notes](docs/PUSH_RELABEL.md).

## Build and check

Requirements: a C++17 compiler, CMake 3.16+, and Python 3. The C++ code and
experiment runners require no external libraries. Plotting requires pandas and
Matplotlib (`python3 -m pip install pandas matplotlib`, preferably in a virtual environment).
Run from the repository root:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

For development, use a separate Debug build:

```sh
cmake -S . -B build-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build-debug --parallel
ctest --test-dir build-debug --output-on-failure
```

## Start independently

Read [the collaboration contract](docs/IMPLEMENTATION_CONTRACT.md) first.

- Sam edits `src/algorithms/edmonds_karp.cpp` and any algorithm-specific helpers.
- Dima edits `src/algorithms/push_relabel.cpp` and any algorithm-specific helpers.
- Shared headers, graph storage, parsing, verifier, and benchmark format are the
  agreed boundary. Discuss changes to these before making them.
- Preserve the solver signatures when changing implementations. Tests and
  benchmark registration already exist.

Suggested branches: `sam/edmonds-karp` and `dima/push-relabel`, both based on the
same framework commit. Merge small changes after the relevant tests pass.
Framework setup should be committed and shared before either branch starts.

## Input format

Plain whitespace-separated integers, with zero-based vertex IDs:

```text
4 5 0 3
0 1 3
0 2 2
1 2 1
1 3 2
2 3 3
```

The header is `vertex_count edge_count source sink`. Each remaining record is
`from to capacity`. The example has maximum flow **5**. There must be exactly
`edge_count` records and no comments or trailing tokens.

Directed graphs have at least two vertices and distinct terminals. Parallel
edges, antiparallel edges, and zero capacities are supported. Self-loops and
negative capacities are rejected. Capacities and their total sum must fit in a
signed 64-bit integer; this conservative limit also protects flow/excess sums.

```sh
./build/maxflow_run --algorithm edmonds_karp --input path/to/instance.txt
./build/maxflow_run --algorithm push_relabel --input path/to/instance.txt
```

The executable emits JSON on stdout. A successful run includes `status`, `flow`,
and `seconds`. Exit codes: 0 verified success, 1 invalid input/solver failure,
3 solver unfinished. Errors go to stderr. Each invocation loads fresh state.

## Tests

The framework suite checks residual pairing, parallel/antiparallel edges,
reverse pushes, reset, parser rejection, overflow rejection, and verification of
both valid and deliberately invalid flows.

Each solver suite checks hand cases, stranded excess, capacities exceeding
32 bits, arbitrary terminals, repeat runs after reset, and 250 seeded tiny
graphs. An independent exhaustive minimum-cut oracle establishes the expected
answer; capacity, conservation, terminal balance, and a cut certificate are also
checked. A placeholder skips its suite; implemented solvers must pass it.

Dedicated Edmonds–Karp and push–relabel suites cover signed 64-bit capacity limits, parallel
and antiparallel edges, unreachable sinks, cyclic bottlenecks, and long dead-end
chains. The Edmonds–Karp suite also checks rerouting through reverse edges.
Each suite exhaustively checks all 4,096 simple directed unit-capacity
graphs on four vertices with all 12 terminal pairs (49,152 cases), solving each
twice with a reset between runs and checking against exhaustive minimum cuts.

```sh
ctest --test-dir build -R edmonds_karp --output-on-failure
ctest --test-dir build -R push_relabel --output-on-failure
```

## Reproduce a pilot experiment

```sh
python3 scripts/benchmark.py
```

This generates and saves identical instances for both algorithms, randomizes
run order with a fixed seed, enforces a timeout per invocation, and writes
`results/smoke.csv` plus `results/smoke.metadata.json`. The smoke configuration
has 96 runs. Generated instances and raw results are ignored by Git.

```sh
python3 scripts/benchmark.py --config experiments/configs/smoke.json --output results/pilot.csv
```

**Timing:** wall time around the solver call only, including its allocation and
initialization. Parsing, process startup, graph construction, and verification
are excluded. Subprocess timeout covers the entire invocation. No timing is
reported for unfinished or failed solvers. The runner returns nonzero if any
run errors or times out; unfinished status remains explicit in the CSV.

The four initial generators are sparse random graphs, graphs with about 25%
directed density, forward layered/banded graphs, and two regions joined by one
unit-capacity bottleneck. Each plants a source-to-sink path; these are deliberately
structured distributions, not unbiased samples. Seeds control generation and
SHA-256 hashes identify exact inputs. Capacity maxima, sizes, seeds, repetitions,
and timeouts are configurable in JSON. The initial configuration is a pipeline
smoke test, not a sufficient final experiment design.

Metadata records the executable hash, platform, configuration, and command.
For final experiments, also preserve compiler/version, CMake settings, CPU model,
and revision manually. Use the same Release binary and machine for comparisons.
For repeated measurements, use `maxflow_bench` and the full experiment runner below.

## Full comparison experiment

The final design compares six graph families at six sizes, with five seeds and
five process repetitions per algorithm: **180 inputs and 1,800 measurement
batches**. Separate follow-ups examine the short-path crossover and a controlled
change from source-limited to sink-limited capacity. Read the
[experiment plan](experiments/PLAN.md) for hypotheses, graph definitions,
warm-up, timing boundaries, variation, and limitations.

Reproduce all experiments in a **new** output directory:

```sh
bash scripts/reproduce_experiment.sh results/reproduced
```

The experiment runner needs only the Python standard library. Do not run other benchmarks or compilation while
measurement is running. The script builds with Release optimizations, runs the
correctness tests, then executes all measurement processes sequentially. It
refuses to overwrite an existing raw CSV. Timing results vary with hardware and
system load. Set `MAXFLOW_HARDWARE_INFO` to your own CPU/RAM JSON file if sandbox
restrictions prevent automatic hardware collection; the submitted run uses
`experiments/hardware/apple-m2.json`.

Generated results and graph inputs are not bundled with this checkout. Regenerate
measurements on the machine whose environment you report. The historical
[results discussion](experiments/RESULTS.md) describes the earlier Apple M2 run;
its timing claims do not describe a newly generated run.

To run only the main comparison using your existing Release build:

```sh
python3 scripts/run_experiment.py --binary build/maxflow_bench \
  --config experiments/configs/comparison.json --output results/comparison/raw.csv
python3 scripts/summarize_experiment.py results/comparison/raw.csv
python3 scripts/describe_instances.py results/comparison
python3 scripts/plot_results.py results/comparison/raw.csv
```

The runner generates graph inputs automatically. It writes raw measurements,
`instances.csv` with input hashes, and `raw.metadata.json` with build, hardware,
source and run information. Summarization produces `paired.csv` and `summary.csv`;
instance description produces `structure.csv`. Use a new destination for later
runs because existing raw CSVs are protected against overwriting.

For a single graph file, benchmark either algorithm directly:

```sh
./build/maxflow_bench edmonds_karp path/to/instance.txt 0.01
./build/maxflow_bench push_relabel path/to/instance.txt 0.01
```

The final argument is the target accumulated solver time in seconds (greater
than zero and at most one). Each process performs a verified untimed warm-up,
then measures solves until that target or 1,024 iterations. Reset and
verification are outside each timed interval. JSON output includes flow,
iterations, total solver seconds and mean seconds per solve.

### Plots and aggregation

```sh
python3 scripts/plot_results.py results/comparison/raw.csv
# Optional output base and image format:
python3 scripts/plot_results.py results/comparison/raw.csv --output results/comparison/timing.svg
```

The plotting script also accepts `results/smoke.csv`. It saves separate timing
and speedup images for each graph family, plus `.summary.csv` and `.speedup.csv`
files. For example, the default main-comparison output includes
`raw_plot_sparse.png` and `raw_plot_sparse_speedup.png`.

`seconds` in a raw CSV is the arithmetic mean within one process. Timing plots
use the median across process repetitions for each seed, then the median across
seeds, with a min–max band across seed medians. Speedup plots first divide
Edmonds–Karp time by push–relabel time for each matched seed, then plot the median
ratio and min–max range. Above one favors push–relabel; below one favors
Edmonds–Karp. Shading shows observed spread, not a confidence interval.
The summarizer separately reports a geometric mean of paired ratios; it need
not equal the plotted median speedup.

Generated graph inputs are ignored by Git. Most results directories are ignored,
but `results/comparison`, `results/crossover`, and `results/cut-control` are allowed
so selected raw CSVs, metadata and figures can be committed with a report.

## Layout

```text
include/maxflow/             Shared graph, solver, I/O, verification contracts
src/algorithms/              Separately owned implementation modules
src/common/                  Shared framework
src/main.cpp                 Timed, verified single-run executable
src/benchmark.cpp            Repeated, verified solver timing
tests/test_maxflow.cpp       Framework tests and independent solver checks
scripts/benchmark.py         Quick smoke experiment runner
scripts/run_experiment.py    Repeated full experiment runner
scripts/plot_results.py      Per-family timing and speedup figures
experiments/configs/         Versioned experiment configurations
experiments/instances/       Generated reproducible inputs (ignored)
results/                    Generated measurements, metadata and plots
docs/IMPLEMENTATION_CONTRACT.md  Team agreement
```
