"""Build the unified base sample used by all 4 RQs.

Output: shared/cache/base_sample.parquet — one row per merged agent PR, with
PR-level features aggregated from commit_details and review/comment tables.
Human PRs are included for metadata but flagged has_internal_coverage=0.
"""
import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from load_data import AIDev  # noqa: E402

CACHE = os.path.join(os.path.dirname(__file__), "..", "cache")
os.makedirs(CACHE, exist_ok=True)


def build():
    ai = AIDev()

    print("[build_sample] loading PR metadata...")
    agent = ai.load_agent_prs(merged_only=True)
    human = ai.load_human_prs(merged_only=True)

    # Human PRs only have repo_url — map to repo_id
    repos = ai.load_repos()
    url_to_id = dict(zip(repos["url"], repos["repo_id"]))
    human["repo_id"] = human["repo_url"].map(url_to_id)
    before = len(human)
    human = human[human["repo_id"].notna()].copy()
    human["repo_id"] = human["repo_id"].astype("int64")
    print(f"  human PRs w/ repo_id: {len(human)}/{before}")

    repo_meta = repos.rename(columns={"url": "repo_url"})[
        ["repo_id", "full_name", "language", "stars", "forks", "license"]
    ]
    agent = agent.merge(repo_meta, on="repo_id", how="left")
    human = human.merge(repo_meta, on="repo_id", how="left")

    tt = ai.load_task_types()
    agent = agent.merge(tt.rename(columns={"type": "task_type"}), on="id", how="left")
    human = human.merge(tt.rename(columns={"type": "task_type"}), on="id", how="left")

    base = pd.concat([agent, human], ignore_index=True)
    print(f"[build_sample] total rows: {len(base):,} "
          f"(agent {int(base['is_agent'].sum())}, human {int((1-base['is_agent']).sum())})")

    print("[build_sample] aggregating commit-level features...")
    pr_ids = set(base["id"].astype("int64").tolist())
    commits = ai.load_commit_stats(pr_ids=pr_ids)
    for c in ("additions", "deletions", "changes"):
        commits[c] = pd.to_numeric(commits[c], errors="coerce").fillna(0)

    fn_low = commits["filename"].fillna("").str.lower()
    is_test = (
        fn_low.str.contains(r"(?:^|/)tests?/", regex=True)
        | fn_low.str.contains(r"test_[^/]*$", regex=True)
        | fn_low.str.contains(r"[_/.]test\.", regex=True)
        | fn_low.str.contains(r"\.spec\.", regex=True)
        | fn_low.str.contains(r"_spec\.rb$", regex=True)
    )
    commits["is_test_file"] = is_test.astype(int)

    agg = commits.groupby("pr_id").agg(
        loc_added=("additions", "sum"),
        loc_deleted=("deletions", "sum"),
        files_changed=("filename", "nunique"),
        n_commits=("sha", "nunique"),
        has_tests_in_pr=("is_test_file", "max"),
        n_test_files=("is_test_file", "sum"),
    ).reset_index().rename(columns={"pr_id": "id"})
    base = base.merge(agg, on="id", how="left")
    for c in ("loc_added", "loc_deleted", "files_changed", "n_commits",
              "has_tests_in_pr", "n_test_files"):
        base[c] = base[c].fillna(0).astype(int)

    print("[build_sample] review engagement...")
    rv = ai.load_reviews()
    rv_agg = rv.groupby("pr_id").agg(
        n_reviews=("pr_id", "size"),
        n_approvals=("state", lambda s: (s == "APPROVED").sum()),
        n_changes_requested=("state", lambda s: (s == "CHANGES_REQUESTED").sum()),
        reviewer_diversity=("user", "nunique"),
    ).reset_index().rename(columns={"pr_id": "id"})

    cm = ai.load_comments()
    cm_agg = cm.groupby("pr_id").agg(
        n_comments=("pr_id", "size"),
        commenter_diversity=("user", "nunique"),
        n_bot_comments=("user_type", lambda s: (s == "Bot").sum()),
    ).reset_index().rename(columns={"pr_id": "id"})

    base = base.merge(rv_agg, on="id", how="left").merge(cm_agg, on="id", how="left")
    for c in ("n_reviews", "n_approvals", "n_changes_requested", "reviewer_diversity",
              "n_comments", "commenter_diversity", "n_bot_comments"):
        base[c] = base[c].fillna(0).astype(int)

    base["log_loc_added"] = np.log1p(base["loc_added"])
    base["log_files_changed"] = np.log1p(base["files_changed"])
    base["log_stars"] = np.log1p(base["stars"].fillna(0))
    base["merge_duration_hours"] = (
        (base["merged_at"] - base["created_at"]).dt.total_seconds() / 3600.0
    )
    base["merge_month"] = base["merged_at"].dt.to_period("M").astype(str)
    base["has_internal_coverage"] = base["is_agent"].astype(int)

    out = os.path.join(CACHE, "base_sample.parquet")
    base.to_parquet(out, index=False)
    print(f"[build_sample] saved -> {out}  shape={base.shape}")

    print("\n=== summary ===")
    print(base.groupby("is_agent").agg(
        n=("id", "count"),
        loc_mean=("loc_added", "mean"),
        files_mean=("files_changed", "mean"),
        reviews_mean=("n_reviews", "mean"),
        merge_h_med=("merge_duration_hours", "median"),
        tests_rate=("has_tests_in_pr", "mean"),
    ).round(2))


if __name__ == "__main__":
    build()
