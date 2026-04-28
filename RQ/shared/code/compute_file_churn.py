"""Compute per-file AIDev-observed historical churn baseline.

For every (pr_id, filename) in the agent sample, we attach two churn
features:
  - file_aidev_activity_total: total # of distinct PRs touching that file
    across the full AIDev window (irrespective of direction)
  - file_aidev_activity_before: # of PRs in the same repo that touched the
    file BEFORE the source PR's merge (a proxy for pre-merge "hotness")

These features are then aggregated to the PR level:
  - file_hotness_mean: mean total activity across the PR's files
  - file_hotness_max: max total activity across the PR's files
  - file_hotness_before_mean: mean pre-merge activity
  - file_hotness_norm: log1p(mean total activity)

Output: shared/cache/pr_file_churn.parquet (one row per agent PR)
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from load_data import AIDev  # noqa: E402

CACHE = os.path.join(os.path.dirname(__file__), "..", "cache")


def main():
    ai = AIDev()
    base = pd.read_parquet(os.path.join(CACHE, "base_sample.parquet"),
                           columns=["id", "is_agent", "repo_id", "merged_at"])
    base = base[base["is_agent"] == 1].copy()
    base["merged_at"] = pd.to_datetime(base["merged_at"], utc=True)
    base["repo_id"] = base["repo_id"].astype("int64")

    print("[churn] loading file index...")
    fi = ai.load_file_index()
    meta = base[["id", "repo_id", "merged_at"]].rename(columns={"id": "pr_id"})
    fi = fi.merge(meta, on="pr_id", how="inner")
    print(f"[churn] joined rows: {len(fi):,}")

    # Per (repo_id, filename): total # of distinct PRs
    file_total = fi.groupby(["repo_id", "filename"])["pr_id"].nunique().rename(
        "file_total_activity"
    ).reset_index()
    fi = fi.merge(file_total, on=["repo_id", "filename"], how="left")

    # For "before" activity: within each (repo_id, filename), count how many
    # earlier merges exist. Sort by merged_at and cumcount minus self.
    fi = fi.sort_values(["repo_id", "filename", "merged_at"])
    fi["rank"] = fi.groupby(["repo_id", "filename"]).cumcount()
    fi["file_before_activity"] = fi["rank"]  # 0 for the first, increments for later

    # Aggregate to PR level
    agg = fi.groupby("pr_id").agg(
        file_hotness_mean=("file_total_activity", "mean"),
        file_hotness_max=("file_total_activity", "max"),
        file_hotness_p75=("file_total_activity", lambda s: s.quantile(0.75)),
        file_hotness_before_mean=("file_before_activity", "mean"),
        file_hotness_before_max=("file_before_activity", "max"),
        n_files_touched=("filename", "nunique"),
    ).reset_index().rename(columns={"pr_id": "id"})

    agg["log_file_hotness"] = np.log1p(agg["file_hotness_mean"])
    agg["log_file_hotness_before"] = np.log1p(agg["file_hotness_before_mean"])

    out = os.path.join(CACHE, "pr_file_churn.parquet")
    agg.to_parquet(out, index=False)
    print(f"[churn] saved -> {out}  shape={agg.shape}")
    print("\nstats:")
    print(agg[["file_hotness_mean", "file_hotness_max",
               "file_hotness_before_mean", "n_files_touched"]].describe().round(2))


if __name__ == "__main__":
    main()
