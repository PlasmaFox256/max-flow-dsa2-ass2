#!/usr/bin/env python3
"""Structural diagnostics joined to measurements; no additional timed runs."""
import argparse
import csv
import hashlib
from collections import deque
from pathlib import Path

from benchmark import ROOT
from summarize_experiment import write_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?", default=ROOT / "results/comparison")
    args = parser.parse_args()
    paired = {r["instance_sha256"]: r for r in csv.DictReader((args.directory / "paired.csv").open())}
    rows = []
    for record in csv.DictReader((args.directory / "instances.csv").open()):
        content = (ROOT / record["input_file"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != record["instance_sha256"]:
            raise ValueError("regenerated input hash differs")
        lines = content.decode().splitlines()
        n, m, source, sink = map(int, lines[0].split())
        adjacency = [[] for _ in range(n)]
        source_capacity = sink_capacity = 0
        for line in lines[1:]:
            u, v, capacity = map(int, line.split())
            adjacency[u].append(v)
            if u == source:
                source_capacity += capacity
            if v == sink:
                sink_capacity += capacity
        distance = {source: 0}
        queue = deque([source])
        while queue:
            u = queue.popleft()
            for v in adjacency[u]:
                if v not in distance:
                    distance[v] = distance[u] + 1
                    queue.append(v)
        flow = int(paired[record["instance_sha256"]]["flow"])
        rows.append(dict(family=record["family"], vertices=n, seed=record["seed"],
                         instance_sha256=record["instance_sha256"], edges=m,
                         density=m / (n * (n - 1)), initial_shortest_path=distance.get(sink, -1),
                         source_out_capacity=source_capacity, sink_in_capacity=sink_capacity,
                         flow=flow, initial_source_preflow_return=source_capacity - flow,
                         source_capacity_over_flow=source_capacity / flow if flow else ""))
    write_csv(args.directory / "structure.csv", rows)
    print(f"Verified {len(rows)} input hashes and wrote structure.csv")


if __name__ == "__main__":
    main()
