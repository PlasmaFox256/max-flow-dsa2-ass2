#!/usr/bin/env python3
"""Plot raw experiment CSVs: median per seed, then median and range across seeds.

Example: python3 scripts/plot_results.py results/comparison/raw.csv
Requires: pandas, matplotlib.
"""
import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="raw.csv or smoke.csv")
    parser.add_argument("--output", type=Path,
                        help="base PNG, SVG, or PDF path; family names are appended")
    args = parser.parse_args()
    data = pd.read_csv(args.csv)
    required = {"family", "vertices", "seed", "algorithm", "status", "seconds"}
    if not required.issubset(data.columns):
        parser.error(f"missing columns: {', '.join(sorted(required - set(data.columns)))}")
    failed = data["status"].ne("ok")
    if failed.any():
        print(f"Excluding {failed.sum()} unsuccessful rows; check experiment completeness.")
    data = data.loc[~failed].copy()
    if data.empty:
        parser.error("no successful measurements to plot")
    for column in ("vertices", "seconds"):
        data[column] = pd.to_numeric(data[column], errors="raise")
        if not data[column].map(lambda value: math.isfinite(value) and value > 0).all():
            parser.error(f"{column} must contain finite positive values")
    if data[list(required)].isna().any().any():
        parser.error("required columns contain missing values")

    # Give each seed equal weight, regardless of the number of process repeats.
    per_seed = data.groupby(["family", "vertices", "algorithm", "seed"])["seconds"].median()
    summary = per_seed.groupby(level=["family", "vertices", "algorithm"]).agg(
        median="median", minimum="min", maximum="max", seeds="count"
    ).reset_index()
    # Pair algorithms on the same family, size and seed before taking ratios.
    paired = per_seed.unstack("algorithm").reindex(columns=["edmonds_karp", "push_relabel"])
    missing = paired.isna().any(axis=1)
    if missing.any():
        print(f"Excluding {missing.sum()} unpaired seed cases from speedup plots.")
    paired = paired.loc[~missing]
    ratios = paired["edmonds_karp"] / paired["push_relabel"]
    speedup = ratios.groupby(level=["family", "vertices"]).agg(
        median="median", minimum="min", maximum="max", seeds="count"
    ).reset_index()
    families = sorted(summary["family"].unique())
    algorithms = sorted(summary["algorithm"].unique())
    colors = dict(zip(algorithms, plt.get_cmap("tab10").colors))
    output = args.output or args.csv.with_name(args.csv.stem + "_plot.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    for family in families:
        fig, ax = plt.subplots(figsize=(8, 5))
        for algorithm in algorithms:
            values = summary[(summary.family == family) & (summary.algorithm == algorithm)]
            if values.empty:
                continue
            values = values.sort_values("vertices")
            x = values["vertices"].to_numpy()
            ax.plot(x, values["median"].to_numpy(), "o-", label=algorithm,
                    color=colors[algorithm])
            ax.fill_between(x, values["minimum"].to_numpy(), values["maximum"].to_numpy(),
                            color=colors[algorithm], alpha=0.18)
        ax.set(title=family.replace("_", " "), xlabel="Vertices", ylabel="Solver time (seconds)")
        ax.set_yscale("log")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend()
        fig.suptitle("Maximum-flow timings: median across seed medians")
        fig.text(0.5, 0.015, "Shading: min–max across seed medians; spread is not a confidence interval.",
                 ha="center", fontsize=9)
        fig.tight_layout(rect=(0, 0.05, 1, 0.94))
        # Treat family labels as filename components, including for custom CSVs.
        family_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in str(family))
        family_output = output.with_name(f"{output.stem}_{family_name}{output.suffix}")
        fig.savefig(family_output, dpi=200)
        plt.close(fig)
        print(f"Saved {family_output}")
        values = speedup[speedup.family == family].sort_values("vertices")
        if values.empty:
            continue
        fig, ax = plt.subplots(figsize=(8, 5))
        x = values["vertices"].to_numpy()
        ax.plot(x, values["median"].to_numpy(), "o-", label="Median paired speedup")
        ax.fill_between(x, values["minimum"].to_numpy(), values["maximum"].to_numpy(),
                        alpha=0.18, label="Min–max across seeds")
        ax.axhline(1, color="black", linestyle="--", linewidth=1, label="Equal time")
        ax.set(title=f"Speedup: {family.replace('_', ' ')}", xlabel="Vertices",
               ylabel="Edmonds–Karp time / push–relabel time")
        ax.set_yscale("log")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend()
        fig.text(0.5, 0.015,
                 "Above 1: push–relabel faster. Below 1: Edmonds–Karp faster.\n"
                 "Ratios use per-seed median times; shading is not a confidence interval.",
                 ha="center", fontsize=9)
        fig.tight_layout(rect=(0, 0.09, 1, 1))
        speedup_output = output.with_name(f"{output.stem}_{family_name}_speedup{output.suffix}")
        fig.savefig(speedup_output, dpi=200)
        plt.close(fig)
        print(f"Saved {speedup_output}")
    summary.to_csv(output.with_suffix(".summary.csv"), index=False)
    speedup.to_csv(output.with_suffix(".speedup.csv"), index=False)
    print(f"Saved {output.with_suffix('.summary.csv')}")


if __name__ == "__main__":
    main()
