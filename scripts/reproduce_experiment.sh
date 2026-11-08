#!/usr/bin/env bash
# Run from any directory. Use a NEW destination; existing raw CSVs are protected.
set -euo pipefail
cd "$(dirname "$0")/.."
destination="${1:-results/reproduced}"
hardware_args=()
if [[ -n "${MAXFLOW_HARDWARE_INFO:-}" ]]; then
    hardware_args=(--hardware-info "$MAXFLOW_HARDWARE_INFO")
fi
cmake -S . -B build-experiment -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build-experiment --parallel
ctest --test-dir build-experiment --output-on-failure
python3 scripts/test_experiment.py
python3 scripts/run_experiment.py --output "$destination/comparison/raw.csv" "${hardware_args[@]}"
python3 scripts/run_experiment.py --config experiments/configs/crossover.json --output "$destination/crossover/raw.csv" "${hardware_args[@]}"
python3 scripts/run_experiment.py --config experiments/configs/cut_control.json --output "$destination/cut-control/raw.csv" "${hardware_args[@]}"
for experiment in comparison crossover cut-control; do
    python3 scripts/summarize_experiment.py "$destination/$experiment/raw.csv"
    python3 scripts/describe_instances.py "$destination/$experiment"
done
