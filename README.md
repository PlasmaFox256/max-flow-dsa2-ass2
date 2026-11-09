# Theory versus practice: maximum flow

A C++17 comparison of **Edmonds–Karp** (primary author: Sam) and **FIFO
push–relabel** (primary author: Dmytro). Both solve maximum flow on directed,
capacitated graphs using the same residual graph representation and verifier.
Push–relabel uses current-edge pointers and fully discharges excess; it does
not include global-relabel or gap heuristics.

## Build and test

Requires a C++17 compiler, CMake 3.16+, and Python 3. The full reproduction script
also requires Bash. Solvers and experiment runners have no external dependencies;
plotting additionally requires pandas and Matplotlib.

Run from the repository root:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

`CMAKE_EXPORT_COMPILE_COMMANDS=ON` is required by the full experiment runner to
record build provenance; use a Makefile or Ninja CMake generator.

Tests cover parsing, residual edges, overflow, flow feasibility, and both solvers.
Each algorithm is checked against exhaustive minimum cuts on all 4,096 simple
unit-capacity directed graphs with four vertices and all 12 terminal pairs,
including repeat solves after reset. To check the repeated-timing harness too:

```sh
python3 scripts/test_experiment.py build/maxflow_bench
```

## Solve a graph

Create an example input with maximum flow **5**:

```sh
cat > /tmp/maxflow-example.txt <<'EOF'
4 5 0 3
0 1 3
0 2 2
1 2 1
1 3 2
2 3 3
EOF
./build/maxflow_run --algorithm edmonds_karp --input /tmp/maxflow-example.txt
./build/maxflow_run --algorithm push_relabel --input /tmp/maxflow-example.txt
```

The header is `vertices edges source sink`; each following line is
`from to capacity`. Vertex IDs are zero-based. Exactly the declared number of
edges must follow, without comments or trailing tokens. Parallel and antiparallel
edges and zero capacities are supported. Self-loops, negative capacities, and
identical terminals are rejected. Capacities and their sum must fit signed
64-bit integers.

Each command verifies the solution and prints JSON containing `status`, `flow`,
and `seconds`. Successful runs exit with code 0; invalid input or solver errors
exit with code 1 and a message on stderr.

For repeated timing of a single input:

```sh
./build/maxflow_bench edmonds_karp /tmp/maxflow-example.txt 0.01
./build/maxflow_bench push_relabel /tmp/maxflow-example.txt 0.01
```

The last argument is the target accumulated solver time in seconds, greater than
zero and at most one. Each process performs one verified untimed warm-up, then
measures up to 1,024 solves. JSON includes the flow, iteration count, accumulated
solver time, and mean seconds per solve.

## Run experiments

For a quick pipeline check after building:

```sh
python3 scripts/benchmark.py
```

This generates 24 inputs from four graph families and records **96 single-solve
runs** in `results/smoke.csv`, with metadata alongside it.

To reproduce the complete experiment suite:

```sh
bash scripts/reproduce_experiment.sh results/reproduced
```

The script builds a Release executable in `build-experiment`, runs correctness
checks, generates inputs, measures both algorithms sequentially, and produces
summaries and structural diagnostics. Use a new output directory for each run;
existing raw CSVs are protected against overwriting. Avoid other intensive work
during measurement.

| Experiment | Inputs | Measurement batches | Output subdirectory |
| --- | ---: | ---: | --- |
| Main: six families, sizes 32–1,024 | 180 | 1,800 | `comparison/` |
| Independent-path crossover, sizes 4–32 | 35 | 490 | `crossover/` |
| Source-limited versus sink-limited dense graphs | 18 | 108 | `cut-control/` |

To run only the main experiment using the `build` directory above:

```sh
python3 scripts/run_experiment.py --binary build/maxflow_bench --config experiments/configs/comparison.json --output results/main-run/raw.csv
python3 scripts/summarize_experiment.py results/main-run/raw.csv
python3 scripts/describe_instances.py results/main-run
```

All timings include solver allocation and initialization, but exclude parsing,
graph construction, reset, and verification. Repeated experiments use randomized
paired order and identical hashed inputs for both algorithms. Every solve is
verified, and returned flows are compared across algorithms. Short batches may
reach the iteration cap before the target duration.

Each full-experiment output directory contains:

| File | Contents |
| --- | --- |
| `raw.csv` | Every measurement batch, timing, flow, iteration count, and status |
| `raw.metadata.json` | Configuration, source and binary hashes, compiler, build flags, and environment |
| `instances.csv` | Input paths, parameters, and SHA-256 hashes |
| `paired.csv` | Per-input median timings across process repetitions and paired EK/PR ratios |
| `summary.csv` | Per-family/size summaries, geometric mean paired ratios, ranges, and win counts |
| `structure.csv` | Density, initial shortest path, terminal capacities, and stranded preflow |

Graph inputs are generated in `experiments/instances/`. Generated measurements
and inputs are not bundled with the current checkout. The
[experiment plan](experiments/PLAN.md) defines the generators and methodology;
the [historical results discussion](experiments/RESULTS.md) describes the earlier
Apple M2 measurements. New runs must be interpreted using their own metadata.

## Plot results

Install the optional plotting dependencies in a virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install pandas matplotlib
python3 scripts/plot_results.py results/reproduced/comparison/raw.csv
```

The plotter accepts raw experiment CSVs, including `results/smoke.csv`. It saves
a timing plot and an EK/PR speedup plot for each graph family, plus aggregation
CSVs beside the input. For example, `raw_plot_sparse.png` and
`raw_plot_sparse_speedup.png` are generated for the sparse family. To choose an
output location and PNG, SVG, or PDF format:

```sh
python3 scripts/plot_results.py results/reproduced/comparison/raw.csv --output results/figures/timing.svg
```

Timing plots use the median across repetitions for each seed, then the median
and min–max range across seeds. Speedup plots use the median of paired **EK/PR**
ratios: **above 1 favors push–relabel; below 1 favors Edmonds–Karp**. Shading shows
observed spread, not confidence intervals. The summarizer's geometric mean ratio
and the plotter's median ratio are different statistics.

## Repository structure

```text
include/maxflow/             Shared graph, solver, input and verification APIs
src/algorithms/              Edmonds–Karp and FIFO push–relabel implementations
src/common/                  Residual graph, parser and solution verifier
src/main.cpp                 Single-solve command-line executable
src/benchmark.cpp            Repeated solver timing executable
tests/                      Framework and algorithm correctness tests
scripts/                    Experiment runners, validation, summaries and plotting
experiments/configs/         Smoke, main, crossover and capacity-control settings
experiments/PLAN.md          Input definitions and experimental methodology
experiments/RESULTS.md       Historical findings and limitations
experiments/instances/       Generated graph inputs
results/                    Generated CSVs, metadata and figures
docs/PUSH_RELABEL.md         Push–relabel design and correctness notes
```
