# Theory versus practice: maximum flow

A shared C++17 framework for comparing Edmonds–Karp (primary author: **Sam**)
and FIFO push–relabel (primary author: **Dima**).

**Status:** FIFO push–relabel is implemented, including current-edge pointers
and full excess discharge. Edmonds–Karp remains a placeholder: its benchmark
runs are `not_implemented`, and its CTest suite is skipped.
See [push–relabel implementation notes](docs/PUSH_RELABEL.md).

## Build and check

Requirements: a C++17 compiler, CMake 3.16+, and Python 3. No external libraries.
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
- Each author replaces their placeholder body while preserving the signature.
  Tests and benchmark registration already exist; no shared-file edit is needed.

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

An additional push–relabel suite covers signed 64-bit capacity limits, parallel
and antiparallel edges, unreachable sinks, cyclic bottlenecks, and long dead-end
chains. It also exhaustively checks all 4,096 simple directed unit-capacity
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
Very short solves need future batching before their timings are meaningful.

## Layout

```text
include/maxflow/             Shared graph, solver, I/O, verification contracts
src/algorithms/              Separately owned implementation modules
src/common/                  Shared framework
src/main.cpp                 Timed, verified single-run executable
tests/test_maxflow.cpp       Framework tests and independent solver checks
scripts/benchmark.py         Generation and CSV experiment runner
experiments/configs/         Versioned experiment configurations
experiments/instances/       Generated reproducible inputs (ignored)
results/                    Generated CSV and metadata (ignored)
docs/IMPLEMENTATION_CONTRACT.md  Team agreement
```
