#!/usr/bin/env python3
"""Paired, sequential, warm-cache solver experiment; standard library only."""
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

from benchmark import ALGORITHMS, ROOT, generate


def instance(family, n, seed, cap):
    if family not in ("disjoint_paths", "dead_end", "source_limited_dense", "sink_limited_dense"):
        return generate(family, n, seed, cap)
    rng = random.Random(seed)
    edges = []
    if family in ("source_limited_dense", "sink_limited_dense"):
        source_cap, sink_cap = (1, cap) if family == "source_limited_dense" else (cap, 1)
        for v in range(1, n - 1):
            edges.extend([(0, v, source_cap), (v, n - 1, sink_cap)])
        for u in range(1, n - 1):
            for v in range(1, n - 1):
                if u != v and rng.random() < 0.25:
                    edges.append((u, v, rng.randint(1, cap)))
    elif family == "disjoint_paths":
        # n-2 independent length-two paths, unit capacities; max flow n-2.
        for v in range(1, n - 1):
            edges.extend([(0, v, 1), (v, n - 1, 1)])
    else:
        # One useful path plus a high-capacity chain unable to reach the sink.
        # EK ignores the stranded capacity; PR must return its preflow to s.
        edges = [(0, 1, 1), (1, n - 1, 1), (0, 2, cap)]
        edges.extend((v, v + 1, cap) for v in range(2, n - 2))
    # Seeds vary adjacency insertion order for these otherwise fixed topologies.
    rng.shuffle(edges)
    content = f"{n} {len(edges)} 0 {n - 1}\n"
    content += "".join(f"{u} {v} {c}\n" for u, v, c in edges)
    return content, len(edges)


def command_output(command):
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "experiments/configs/comparison.json")
    parser.add_argument("--binary", type=Path, default=ROOT / "build-experiment/maxflow_bench")
    parser.add_argument("--output", type=Path, default=ROOT / "results/comparison/raw.csv")
    parser.add_argument("--hardware-info", type=Path, help="optional externally collected CPU/RAM JSON")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if (min(config["sizes"]) < 4 or config["capacity_max"] < 1 or
            not config["seeds"] or config["repetitions"] < 1 or
            not 0 < config["target_seconds"] <= 1 or config["timeout_seconds"] <= 0):
        parser.error("invalid configuration")
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error("build maxflow_bench first")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        parser.error("output exists; use a new path to preserve previous measurements")
    instance_dir = ROOT / "experiments/instances"
    instance_dir.mkdir(parents=True, exist_ok=True)
    manifest, pairs = [], []
    for family in config["families"]:
        for n in config["sizes"]:
            for seed in config["seeds"]:
                content, m = instance(family, n, seed, config["capacity_max"])
                digest = hashlib.sha256(content.encode()).hexdigest()
                path = instance_dir / f"{family}-{n}-{seed}-{digest[:12]}.txt"
                path.write_text(content)
                record = dict(family=family, vertices=n, edges=m, seed=seed,
                              instance_sha256=digest, input_file=str(path.relative_to(ROOT)))
                manifest.append(record)
                for repetition in range(config["repetitions"]):
                    pairs.append((record, repetition, path))
    rng = random.Random(config["order_seed"])
    rng.shuffle(pairs)
    metadata = dict(started_utc=datetime.now(timezone.utc).isoformat(),
                    platform=platform.platform(), machine=platform.machine(),
                    python=sys.version, config=config, command=sys.argv,
                    binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                    source_revision=command_output(["git", "rev-parse", "HEAD"]),
                    git_status=command_output(["git", "status", "--short"]),
                    compiler=command_output(["c++", "--version"]),
                    cmake=command_output(["cmake", "--version"]))
    if sys.platform == "darwin":
        metadata["hardware"] = command_output(["sysctl", "-n", "machdep.cpu.brand_string", "hw.memsize", "hw.ncpu"])
        metadata["power"] = command_output(["pmset", "-g", "batt"])
    if args.hardware_info:
        metadata["hardware_external"] = json.loads(args.hardware_info.read_text())
    cache = binary.parent / "CMakeCache.txt"
    if cache.exists():
        metadata["cmake_cache"] = cache.read_text()
    # Preserve the actual build commands/flags, not just compiler defaults.
    metadata["compile_commands"] = json.loads((binary.parent / "compile_commands.json").read_text())
    metadata["source_hashes"] = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ("src", "include", "scripts", "experiments/configs")
        for p in sorted((ROOT / folder).rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }
    args.output.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    with args.output.with_name("instances.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest[0]))
        writer.writeheader()
        writer.writerows(manifest)
    fields = ["run_order", "family", "vertices", "edges", "seed", "repetition",
              "algorithm", "instance_sha256", "status", "flow", "iterations",
              "solver_seconds_total", "seconds", "error"]
    failures, flows = 0, {}
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        run_order = 0
        for pair_index, (record, repetition, path) in enumerate(pairs):
            algorithms = list(ALGORITHMS)
            rng.shuffle(algorithms)
            for algorithm in algorithms:
                row = {k: v for k, v in record.items() if k != "input_file"}
                row.update(run_order=run_order, repetition=repetition, algorithm=algorithm)
                run_order += 1
                try:
                    result = subprocess.run([str(binary), algorithm, str(path), str(config["target_seconds"])],
                                            capture_output=True, text=True, timeout=config["timeout_seconds"])
                    if result.returncode:
                        raise ValueError(result.stderr.strip())
                    row.update(json.loads(result.stdout))
                    if row["status"] != "ok" or row["seconds"] <= 0:
                        raise ValueError("invalid timing/status")
                    digest = record["instance_sha256"]
                    if digest in flows and flows[digest] != row["flow"]:
                        raise ValueError("algorithms disagree on flow")
                    flows[digest] = row["flow"]
                    expected = {"disjoint_paths": record["vertices"] - 2,
                                "source_limited_dense": record["vertices"] - 2,
                                "sink_limited_dense": record["vertices"] - 2,
                                "dead_end": 1, "bottleneck": 1}
                    if record["family"] in expected and row["flow"] != expected[record["family"]]:
                        raise ValueError("flow differs from known family optimum")
                except subprocess.TimeoutExpired:
                    row.update(status="timeout", error="whole subprocess exceeded timeout")
                except (ValueError, KeyError) as error:
                    row.update(status="error", error=str(error))
                failures += row["status"] != "ok"
                writer.writerow(row)
                stream.flush()
            if (pair_index + 1) % 25 == 0:
                print(f"{pair_index + 1}/{len(pairs)} pairs; {failures} failures", flush=True)
    metadata.update(finished_utc=datetime.now(timezone.utc).isoformat(), rows=run_order, failures=failures)
    args.output.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Saved {run_order} rows: {args.output}; {failures} failures")
    return int(failures != 0)


if __name__ == "__main__":
    sys.exit(main())
