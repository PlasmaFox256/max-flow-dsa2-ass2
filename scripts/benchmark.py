#!/usr/bin/env python3
"""Standard-library experiment runner; invoke from any working directory."""
import argparse
import csv
import hashlib
import json
import platform
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALGORITHMS = ("edmonds_karp", "push_relabel")


def generate(family, n, seed, capacity_max):
    rng = random.Random(seed)
    edges = {}

    def add(u, v, capacity=None):
        if u != v and (u, v) not in edges:
            edges[u, v] = rng.randint(1, capacity_max) if capacity is None else capacity

    # Deliberately plant a source-to-sink path. These are structured benchmark
    # distributions, not uniform samples of all directed graphs.
    for u in range(n - 1):
        add(u, u + 1)
    if family == "sparse":
        target = min(4 * n, n * (n - 1))
        while len(edges) < target:
            add(rng.randrange(n), rng.randrange(n))
    elif family == "dense":
        for u in range(n):
            for v in range(n):
                if u != v and rng.random() < 0.25:
                    add(u, v)
    elif family == "layered":
        width = max(2, int(n ** 0.5))
        for u in range(n):
            for v in range(u + 1, min(n, u + width + 1)):
                add(u, v)
    elif family == "bottleneck":
        split = n // 2
        edges[split - 1, split] = 1
        for _ in range(5 * n):
            lower, upper = (0, split) if rng.random() < 0.5 else (split, n)
            add(rng.randrange(lower, upper), rng.randrange(lower, upper))
    else:
        raise ValueError(f"unknown family: {family}")
    lines = [f"{n} {len(edges)} 0 {n - 1}"]
    lines.extend(f"{u} {v} {c}" for (u, v), c in edges.items())
    return "\n".join(lines) + "\n", len(edges)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "build/maxflow_run")
    parser.add_argument("--config", type=Path, default=ROOT / "experiments/configs/smoke.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results/smoke.csv")
    args = parser.parse_args()
    binary = args.binary.resolve()
    config = json.loads(args.config.read_text())
    if not binary.is_file():
        parser.error(f"build the executable first: {binary}")
    if (not config["sizes"] or any(n < 2 for n in config["sizes"]) or
            config["capacity_max"] < 1 or config["repetitions"] < 1 or
            config["timeout_seconds"] <= 0):
        parser.error("invalid experiment configuration")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    instances = ROOT / "experiments/instances"
    instances.mkdir(parents=True, exist_ok=True)
    jobs = []
    for family in config["families"]:
        for n in config["sizes"]:
            for seed in config["seeds"]:
                content, m = generate(family, n, seed, config["capacity_max"])
                digest = hashlib.sha256(content.encode()).hexdigest()
                path = instances / f"{family}-{n}-{seed}-{digest[:12]}.txt"
                path.write_text(content)
                for repetition in range(config["repetitions"]):
                    for algorithm in ALGORITHMS:
                        jobs.append((family, n, m, seed, repetition, algorithm, path, digest))
    random.Random(0).shuffle(jobs)
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(), "machine": platform.machine(),
        "python": sys.version, "binary": str(binary),
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "config": config, "command": sys.argv,
    }
    metadata_path = args.output.with_suffix(".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    failed = False
    counts = {}
    with args.output.open("w", newline="") as stream:
        fields = ["family", "vertices", "edges", "seed", "repetition", "algorithm",
                  "instance_sha256", "status", "flow", "seconds", "error"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for family, n, m, seed, repetition, algorithm, path, digest in jobs:
            row = dict(family=family, vertices=n, edges=m, seed=seed,
                       repetition=repetition, algorithm=algorithm, instance_sha256=digest)
            try:
                result = subprocess.run(
                    [str(binary), "--algorithm", algorithm, "--input", str(path)],
                    capture_output=True, text=True, timeout=config["timeout_seconds"])
                if result.returncode in (0, 3):
                    payload = json.loads(result.stdout)
                    expected = "ok" if result.returncode == 0 else "not_implemented"
                    if payload["status"] != expected:
                        raise ValueError("inconsistent executable status")
                    row.update(payload)
                else:
                    row.update(status="error", error=result.stderr.strip())
            except subprocess.TimeoutExpired:
                row.update(status="timeout")
            except (ValueError, KeyError) as error:
                row.update(status="error", error=str(error))
            failed |= row["status"] in ("error", "timeout")
            counts[row["status"]] = counts.get(row["status"], 0) + 1
            writer.writerow(row)
            stream.flush()
    print(f"Saved {len(jobs)} runs to {args.output}: {counts}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
