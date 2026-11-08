#!/usr/bin/env python3
"""Validate the full experiment and produce plot-ready paired summaries."""
import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from benchmark import ALGORITHMS, ROOT


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(raw):
    metadata = json.loads(raw.with_suffix(".metadata.json").read_text())
    config = metadata["config"]
    rows = list(csv.DictReader(raw.open()))
    expected = {(f, str(n), str(s), str(r), a)
                for f in config["families"] for n in config["sizes"]
                for s in config["seeds"] for r in range(config["repetitions"])
                for a in ALGORITHMS}
    actual, grouped, identities = set(), defaultdict(list), {}
    for row in rows:
        key = tuple(row[k] for k in ("family", "vertices", "seed", "repetition", "algorithm"))
        if key in actual:
            raise ValueError(f"duplicate measurement: {key}")
        actual.add(key)
        if row["status"] != "ok":
            raise ValueError(f"cannot summarize failure as a timing: {key} {row['status']}")
        seconds, iterations, total = float(row["seconds"]), int(row["iterations"]), float(row["solver_seconds_total"])
        if seconds <= 0 or not 1 <= iterations <= 1024 or not math.isclose(seconds * iterations, total, rel_tol=1e-12):
            raise ValueError(f"invalid batch measurement: {key}")
        identity = key[:3]
        value = (row["instance_sha256"], row["flow"], row["edges"])
        if identity in identities and identities[identity] != value:
            raise ValueError(f"input/flow mismatch: {key}")
        identities[identity] = value
        grouped[key[:3] + (row["algorithm"],)].append(seconds)
    if actual != expected:
        raise ValueError(f"incomplete experiment: {len(expected - actual)} missing, {len(actual - expected)} unexpected")
    manifest = list(csv.DictReader(raw.with_name("instances.csv").open()))
    if len(manifest) != len(identities):
        raise ValueError("manifest size mismatch")
    manifest_keys = set()
    for record in manifest:
        key = tuple(record[k] for k in ("family", "vertices", "seed"))
        if key in manifest_keys or identities[key][0] != record["instance_sha256"]:
            raise ValueError("manifest identity mismatch")
        manifest_keys.add(key)
    paired, cells = [], defaultdict(list)
    for family, n, seed in sorted(identities, key=lambda x: (x[0], int(x[1]), int(x[2]))):
        ek = grouped[(family, n, seed, "edmonds_karp")]
        pr = grouped[(family, n, seed, "push_relabel")]
        ek_median, pr_median = statistics.median(ek), statistics.median(pr)
        row = dict(family=family, vertices=int(n), seed=int(seed),
                   edges=int(identities[family, n, seed][2]),
                   flow=int(identities[family, n, seed][1]),
                   instance_sha256=identities[family, n, seed][0],
                   repetitions=len(ek), ek_median_seconds=ek_median,
                   pr_median_seconds=pr_median,
                   ek_min_seconds=min(ek), ek_max_seconds=max(ek),
                   pr_min_seconds=min(pr), pr_max_seconds=max(pr),
                   ek_over_pr=ek_median / pr_median)
        paired.append(row)
        cells[family, int(n)].append(row)
    summary = []
    for (family, n), values in sorted(cells.items()):
        ratios = [r["ek_over_pr"] for r in values]
        summary.append(dict(family=family, vertices=n, seed_cases=len(values),
                            edges_median=statistics.median(r["edges"] for r in values),
                            ek_median_seconds=statistics.median(r["ek_median_seconds"] for r in values),
                            pr_median_seconds=statistics.median(r["pr_median_seconds"] for r in values),
                            ek_over_pr_geomean=math.exp(statistics.mean(math.log(x) for x in ratios)),
                            ratio_min=min(ratios), ratio_max=max(ratios),
                            pr_wins=sum(r > 1 for r in ratios), ek_wins=sum(r < 1 for r in ratios)))
    write_csv(raw.with_name("paired.csv"), paired)
    write_csv(raw.with_name("summary.csv"), summary)
    print(f"Validated {len(rows)} rows, {len(identities)} instances, {len(summary)} family/size cells")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path, nargs="?", default=ROOT / "results/comparison/raw.csv")
    args = parser.parse_args()
    for row in summarize(args.raw):
        print(f"{row['family']:15s} n={row['vertices']:4d} EK/PR={row['ek_over_pr_geomean']:9.4f} "
              f"PR wins {row['pr_wins']}/{row['seed_cases']}")


if __name__ == "__main__":
    main()
