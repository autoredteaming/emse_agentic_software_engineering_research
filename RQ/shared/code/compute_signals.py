"""Compute the text-based and bot-comment damage signals per PR.

Outputs: shared/cache/signals.parquet — one row per merged agent PR with:
  - n_post_merge_bug_issues     (from related_issue)
  - n_post_merge_bug_comments   (from pr_timeline commented events w/ bug-keyword text)
  - n_post_merge_refs           (from pr_timeline referenced/mentioned events)
  - n_post_bot_bug_comments     (from pr_comments Bot authors w/ bug-keyword body)
  - text_flag_strict            (bug_issues > 0 OR bug_comments > 0 OR bot_bug_comments > 0)
  - text_flag_composite         (any of the above OR n_post_merge_refs > 0)
"""
import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from load_data import AIDev  # noqa: E402

CACHE = os.path.join(os.path.dirname(__file__), "..", "cache")
os.makedirs(CACHE, exist_ok=True)

BUG_RE = re.compile(
    r"\b(fix(?:es|ed|ing)?|bug|bugs|defect|regress(?:ion)?|hotfix|patch|"
    r"crash|error|broken|broke|revert(?:s|ed)?|incident|fail(?:s|ed|ure)?)\b",
    re.IGNORECASE,
)

WINDOW_DAYS = 180


def _contains_bug(s) -> int:
    if not isinstance(s, str):
        return 0
    return 1 if BUG_RE.search(s) else 0


def compute(base_path: str, out_path: str):
    ai = AIDev()
    base = pd.read_parquet(base_path, columns=["id", "is_agent", "merged_at"])
    base["merged_at"] = pd.to_datetime(base["merged_at"], utc=True)
    agent = base[base["is_agent"] == 1].copy()
    agent_ids = set(agent["id"].astype("int64").tolist())
    m = dict(zip(agent["id"], agent["merged_at"]))
    print(f"[signals] agent PRs: {len(agent):,}")

    # Signal 1: bug-labeled related issues created post-merge
    print("[signals] bug-labeled related issues...")
    ri = ai.load_related_issue()
    issues = ai.load_issues()
    issues["created_at_i"] = pd.to_datetime(issues["created_at"], utc=True, errors="coerce")
    issues["is_bug"] = issues["title"].fillna("").apply(_contains_bug)
    ri = ri.merge(
        issues[["id", "created_at_i", "is_bug"]].rename(columns={"id": "issue_id"}),
        on="issue_id", how="left",
    )
    ri["merged_at"] = ri["pr_id"].map(m)
    ri["delta"] = (ri["created_at_i"] - ri["merged_at"]).dt.total_seconds() / 86400.0
    ri["post_bug"] = ((ri["is_bug"] == 1) & (ri["delta"] > 0) & (ri["delta"] <= WINDOW_DAYS)).astype(int)
    s1 = ri[ri["post_bug"] == 1].groupby("pr_id").size().rename("n_post_merge_bug_issues").reset_index()

    # Signal 2 + 3: pr_timeline post-merge comments/references
    print("[signals] timeline comments/references...")
    tl = ai.load_timeline()
    tl = tl[tl["pr_id"].isin(agent_ids)].copy()
    tl["created_at"] = pd.to_datetime(tl["created_at"], utc=True, errors="coerce")
    tl["merged_at"] = tl["pr_id"].map(m)
    tl["delta"] = (tl["created_at"] - tl["merged_at"]).dt.total_seconds() / 86400.0
    tl = tl[(tl["delta"] > 0) & (tl["delta"] <= WINDOW_DAYS)]

    ref_events = {"referenced", "cross-referenced", "mentioned"}
    s_refs = tl[tl["event"].isin(ref_events)].groupby("pr_id").size().rename("n_post_merge_refs").reset_index()

    com_tl = tl[tl["event"] == "commented"].copy()
    com_tl["is_bug"] = com_tl["message"].apply(_contains_bug)
    s_bugc = com_tl[com_tl["is_bug"] == 1].groupby("pr_id").size().rename("n_post_merge_bug_comments").reset_index()

    # Signal 4: pr_comments (issue-thread comments) from Bot users post-merge
    print("[signals] bot post-merge bug comments...")
    cm = ai.load_comments()
    cm = cm[cm["user_type"] == "Bot"].copy()
    cm = cm[cm["pr_id"].isin(agent_ids)]
    cm["created_at"] = pd.to_datetime(cm["created_at"], utc=True, errors="coerce")
    cm["merged_at"] = cm["pr_id"].map(m)
    cm["delta"] = (cm["created_at"] - cm["merged_at"]).dt.total_seconds() / 86400.0
    cm = cm[(cm["delta"] > 0) & (cm["delta"] <= WINDOW_DAYS)]
    cm["is_bug"] = cm["body"].apply(_contains_bug)
    s_bot = cm[cm["is_bug"] == 1].groupby("pr_id").size().rename("n_post_bot_bug_comments").reset_index()

    # Merge
    out = agent[["id"]].rename(columns={"id": "pr_id"})
    for s in (s1, s_refs, s_bugc, s_bot):
        out = out.merge(s, on="pr_id", how="left")
    for c in ("n_post_merge_bug_issues", "n_post_merge_refs",
              "n_post_merge_bug_comments", "n_post_bot_bug_comments"):
        out[c] = out[c].fillna(0).astype(int)

    out["text_flag_strict"] = (
        (out["n_post_merge_bug_issues"] > 0)
        | (out["n_post_merge_bug_comments"] > 0)
        | (out["n_post_bot_bug_comments"] > 0)
    ).astype(int)
    out["text_flag_composite"] = (
        out["text_flag_strict"]
        | (out["n_post_merge_refs"] > 0)
    ).astype(int)

    out = out.rename(columns={"pr_id": "id"})
    out.to_parquet(out_path, index=False)
    print(f"[signals] saved -> {out_path}  shape={out.shape}")
    print(f"  strict rate:    {out['text_flag_strict'].mean():.4%}")
    print(f"  composite rate: {out['text_flag_composite'].mean():.4%}")


if __name__ == "__main__":
    base_path = os.path.join(CACHE, "base_sample.parquet")
    out_path = os.path.join(CACHE, "signals.parquet")
    compute(base_path, out_path)
