"""Compute the two structural damage signals:

  1. File-level survival events (per-(pr_id, filename))
       -> shared/cache/survival_events.parquet
  2. Follow-up PR counts per source agent PR (three overlap thresholds)
       -> shared/cache/followup_counts.parquet

Both are produced from the same repo-partitioned self-join over
pr_commit_details to avoid doing the expensive join twice.
"""
import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from load_data import AIDev  # noqa: E402

CACHE = os.path.join(os.path.dirname(__file__), "..", "cache")
os.makedirs(CACHE, exist_ok=True)

WINDOW_DAYS = 180


def compute(base_path: str):
    ai = AIDev()
    base = pd.read_parquet(base_path, columns=["id", "is_agent", "repo_id",
                                               "merged_at", "agent", "task_type",
                                               "language", "log_loc_added",
                                               "log_stars", "has_tests_in_pr",
                                               "n_reviews", "loc_added"])
    base["merged_at"] = pd.to_datetime(base["merged_at"], utc=True)
    agent = base[base["is_agent"] == 1].copy()
    agent["repo_id"] = agent["repo_id"].astype("int64")
    print(f"[structural] agent PRs: {len(agent):,}")

    print("[structural] loading file index...")
    fi = ai.load_file_index()
    print(f"[structural] file index rows: {len(fi):,}")

    # Attach merged_at and repo_id to file rows
    meta = agent[["id", "repo_id", "merged_at"]].rename(columns={"id": "pr_id"})
    fi = fi.merge(meta, on="pr_id", how="inner")
    print(f"[structural] joined rows: {len(fi):,}")

    global_max = agent["merged_at"].max()
    print(f"[structural] global censor t_max = {global_max}")

    # We'll build two outputs via a repo-partitioned loop:
    #   - survival rows: (pr_id, filename, merged_at, next_merged_at, event, time_days)
    #   - followup counts: per src_pr, counts at overlap thresholds
    survival_parts = []
    followup_parts = []

    repos = fi.groupby("repo_id").size().sort_values(ascending=False).index.tolist()
    print(f"[structural] processing {len(repos):,} repos...")

    processed = 0
    for repo_id in repos:
        rf = fi[fi["repo_id"] == repo_id][["pr_id", "filename", "merged_at"]]
        if len(rf) == 0:
            processed += 1
            continue

        # --- Survival: per (pr_id, filename), find next (same filename in repo)
        rf_sorted = rf.sort_values(["filename", "merged_at"])
        rf_sorted["next_merged_at"] = rf_sorted.groupby("filename")["merged_at"].shift(-1)
        rf_sorted = rf_sorted.copy()
        rf_sorted["event"] = rf_sorted["next_merged_at"].notna().astype(int)
        rf_sorted["time_days"] = np.where(
            rf_sorted["event"] == 1,
            (rf_sorted["next_merged_at"] - rf_sorted["merged_at"]).dt.total_seconds() / 86400.0,
            (global_max - rf_sorted["merged_at"]).dt.total_seconds() / 86400.0,
        )
        rf_sorted = rf_sorted[rf_sorted["time_days"] > 0]
        if len(rf_sorted):
            rf_sorted = rf_sorted.assign(repo_id=repo_id)
            survival_parts.append(
                rf_sorted[["pr_id", "filename", "repo_id", "merged_at",
                           "next_merged_at", "time_days", "event"]].copy()
            )

        # --- Follow-up: self-join on filename, tgt > src within 180d
        src = rf.rename(columns={"pr_id": "src_pr", "merged_at": "src_merged"})
        tgt = rf.rename(columns={"pr_id": "tgt_pr", "merged_at": "tgt_merged"})
        j = src.merge(tgt, on="filename")
        j = j[j["src_pr"] != j["tgt_pr"]]
        delta = (j["tgt_merged"] - j["src_merged"]).dt.total_seconds() / 86400.0
        j = j[(delta > 0) & (delta <= WINDOW_DAYS)]
        if len(j) == 0:
            processed += 1
            continue
        f_any = j.groupby("src_pr")["tgt_pr"].nunique().rename("n_followup_any")
        shared = j.groupby(["src_pr", "tgt_pr"]).size().rename("shared_files").reset_index()
        s_fc = src.groupby("src_pr").size().rename("src_files")
        shared = shared.merge(s_fc, on="src_pr", how="left")
        shared["overlap_frac"] = shared["shared_files"] / shared["src_files"].clip(lower=1)
        f_30 = shared[shared["overlap_frac"] >= 0.3].groupby("src_pr").size().rename("n_followup_30")
        f_50 = shared[shared["overlap_frac"] >= 0.5].groupby("src_pr").size().rename("n_followup_50")
        r = pd.concat([f_any, f_30, f_50], axis=1).fillna(0).astype(int).reset_index()
        followup_parts.append(r)

        processed += 1
        if processed % 500 == 0:
            print(f"    {processed}/{len(repos)}")

    # Survival output
    surv = pd.concat(survival_parts, ignore_index=True) if survival_parts else pd.DataFrame()
    # Attach agent/task/language/feature covariates
    surv = surv.merge(
        agent[["id", "agent", "task_type", "language",
               "log_loc_added", "log_stars", "has_tests_in_pr", "n_reviews"]]
        .rename(columns={"id": "pr_id"}),
        on="pr_id", how="left",
    )
    surv_path = os.path.join(CACHE, "survival_events.parquet")
    surv.to_parquet(surv_path, index=False)
    print(f"[structural] survival events: {len(surv):,}  events={int(surv['event'].sum()):,}"
          f" ({surv['event'].mean():.1%})")
    print(f"[structural] saved -> {surv_path}")

    # Follow-up counts output (one row per src_pr even when zero)
    fp = pd.concat(followup_parts, ignore_index=True) if followup_parts else \
        pd.DataFrame(columns=["src_pr", "n_followup_any", "n_followup_30", "n_followup_50"])
    all_src = agent[["id"]].rename(columns={"id": "src_pr"})
    fp = all_src.merge(fp, on="src_pr", how="left").fillna(0)
    for c in ("n_followup_any", "n_followup_30", "n_followup_50"):
        fp[c] = fp[c].astype(int)
    fp = fp.rename(columns={"src_pr": "id"})
    fp_path = os.path.join(CACHE, "followup_counts.parquet")
    fp.to_parquet(fp_path, index=False)
    print(f"[structural] follow-up counts: {len(fp):,}")
    print(f"[structural] saved -> {fp_path}")


if __name__ == "__main__":
    compute(os.path.join(CACHE, "base_sample.parquet"))
