#!/usr/bin/env python3
"""Check new graph families and measurement harness against known optima."""
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmark import ALGORITHMS, ROOT
from run_experiment import instance


def main():
    binary = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build-experiment/maxflow_bench"
    checks = 0
    with TemporaryDirectory() as folder:
        path = Path(folder) / "graph.txt"
        for n in (4, 7, 32):
            for seed in (11, 22):
                for family, expected in (("disjoint_paths", n - 2), ("dead_end", 1), ("bottleneck", 1),
                                         ("source_limited_dense", n - 2), ("sink_limited_dense", n - 2)):
                    content, m = instance(family, n, seed, 100)
                    assert content == instance(family, n, seed, 100)[0]
                    records = [tuple(map(int, line.split())) for line in content.splitlines()[1:]]
                    assert len(records) == m and len({(u, v) for u, v, _ in records}) == m
                    assert all(0 <= u < n and 0 <= v < n and u != v and c > 0 for u, v, c in records)
                    path.write_text(content)
                    for algorithm in ALGORITHMS:
                        result = subprocess.run([str(binary), algorithm, str(path), "0.0001"],
                                                capture_output=True, text=True, check=True)
                        payload = json.loads(result.stdout)
                        assert payload["status"] == "ok" and payload["flow"] == expected
                        assert payload["iterations"] >= 1 and payload["seconds"] > 0
                        checks += 1
                first = instance("source_limited_dense", n, seed, 100)[0].splitlines()[1:]
                second = instance("sink_limited_dense", n, seed, 100)[0].splitlines()[1:]
                # Controlled cases have identical edge ordering and internal capacities.
                assert [line.split()[:2] for line in first] == [line.split()[:2] for line in second]
                assert [line for line in first if line.split()[0] != "0" and line.split()[1] != str(n - 1)] == [
                    line for line in second if line.split()[0] != "0" and line.split()[1] != str(n - 1)]
    print(f"Passed {checks} known-optimum batched solver checks")


if __name__ == "__main__":
    main()
