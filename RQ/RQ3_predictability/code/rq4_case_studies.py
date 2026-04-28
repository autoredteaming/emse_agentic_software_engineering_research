"""RQ4 — Export top high-risk PR data for qualitative case study.

Reviewer concern: the paper needs a qualitative dimension. We can't do the
actual qualitative reading, but we CAN assemble the raw material that a
human author will need to inspect and write up.

This script:
  1. Loads the test set + retrained LightGBM
  2. Scores all test PRs
  3. For the top-20 by predicted damage probability (keeps 20 so the author
     can pick 5 that are most illustrative), exports:
        - PR metadata: URL, title, body (first 1k chars)
        - agent, task_type, language
        - size features: LOC, files, commits, tests
        - damage signals present (text_flag, struct_flag, fix_fup)
        - follow-up PR list: each followup's number + title + task_type
        - files modified (limit to top 15 by changes)
  4. Writes a markdown case study template the human author can fill in

Outputs:
  ../results/rq4_case_studies.csv
  ../results/rq4_case_studies.md
"""
import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
BASE = os.path.join(HERE, "..", "..")
CACHE = os.path.join(BASE, "shared", "cache")
DATA_OUT = os.path.join(HERE, "..", "data")
RESULTS = os.path.join(HERE, "..", "results")
os.makedirs(RESULTS, exist_ok=True)

sys.path.insert(0, os.path.join(BASE, "shared", "code"))
from load_data import AIDev  # noqa: E402


def damage_score(df: pd.DataFrame) -> pd.Series:
    df = df.copy()
    df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True)
    end = df["merged_at"].max()
    df["days_at_risk"] = (end - df["merged_at"]).dt.total_seconds() / 86400.0
    df["days_at_risk"] = df["days_at_risk"].clip(lower=1.0)
    obs = df["days_at_risk"].clip(upper=180.0)
    df["followup_30_rate"] = df["n_followup_30"] / obs
    df["refs_rate"] = df["n_post_merge_refs"] / obs

    def z(col):
        v = df[col].astype(float)
        s = v.std()
        return (v - v.mean()) / (s if s > 0 else 1.0)

    return 0.45 * z("text_flag_strict") + 0.40 * z("followup_30_rate") + 0.15 * z("refs_rate")


def main():
    ai = AIDev()

    base = pd.read_parquet(os.path.join(CACHE, "base_sample.parquet"))
    base = base[base["is_agent"] == 1].copy()
    signals = pd.read_parquet(os.path.join(CACHE, "signals.parquet"))
    fup = pd.read_parquet(os.path.join(CACHE, "followup_counts.parquet"))
    df = base.merge(signals, on="id", how="left").merge(fup, on="id", how="left")
    for c in ("text_flag_strict", "n_post_merge_refs", "n_followup_30"):
        df[c] = df[c].fillna(0).astype(int)

    df["damage_score"] = damage_score(df)
    df = df.sort_values("damage_score", ascending=False).head(20).copy()
    print(f"[case] top 20 damage PRs selected")

    # Load PR titles/bodies/URLs
    pr_meta = pd.read_parquet(
        os.path.join(ai.data_dir, "pull_request.parquet"),
        columns=["id", "number", "title", "body", "html_url", "repo_url"],
    )
    df = df.merge(pr_meta, on="id", how="left", suffixes=("", "_meta"))

    # Load file lists
    top_ids = set(df["id"].tolist())
    files = pd.read_parquet(
        os.path.join(ai.data_dir, "pr_commit_details.parquet"),
        columns=["pr_id", "filename", "additions", "deletions", "changes"],
    )
    files = files[files["pr_id"].isin(top_ids)].copy()
    files["changes"] = pd.to_numeric(files["changes"], errors="coerce").fillna(0)
    file_lists = {}
    for pid, g in files.groupby("pr_id"):
        g2 = g.sort_values("changes", ascending=False).head(15)
        file_lists[pid] = g2[["filename", "additions", "deletions"]].to_dict("records")

    # Load related issue titles for each top PR
    ri = ai.load_related_issue()
    issues = ai.load_issues()
    ri = ri.merge(
        issues[["id", "title", "state", "created_at"]].rename(columns={"id": "issue_id"}),
        on="issue_id", how="left",
    )
    ri_by_pr = ri[ri["pr_id"].isin(top_ids)].groupby("pr_id")[["title", "state", "created_at"]].apply(
        lambda g: g.to_dict("records")
    ).to_dict()

    # For each top PR, find the follow-up PRs (we have followup_tasks from RQ1)
    fup_pairs_path = os.path.join(BASE, "RQ1_prevalence", "data", "rq1_followup_tasks.parquet")
    if os.path.exists(fup_pairs_path):
        pairs = pd.read_parquet(fup_pairs_path)
        pairs = pairs[pairs["src_pr"].isin(top_ids) & (pairs["overlap_frac"] >= 0.3)]
        followups_by_src = {}
        for src, g in pairs.groupby("src_pr"):
            g2 = g.sort_values("overlap_frac", ascending=False).head(10)
            tgt_ids = g2["tgt_pr"].unique().tolist()
            if not tgt_ids:
                continue
            tgt_meta = pr_meta[pr_meta["id"].isin(tgt_ids)][
                ["id", "number", "title", "html_url"]
            ]
            tgt_meta = tgt_meta.merge(
                g2[["tgt_pr", "tgt_task", "overlap_frac"]].rename(columns={"tgt_pr": "id"}),
                on="id", how="left",
            )
            followups_by_src[src] = tgt_meta.to_dict("records")
    else:
        followups_by_src = {}

    # CSV export
    csv_rows = []
    for _, r in df.iterrows():
        csv_rows.append({
            "rank": len(csv_rows) + 1,
            "pr_id": int(r["id"]),
            "agent": r["agent"],
            "task_type": r["task_type"],
            "language": r["language"],
            "repo": r["full_name"],
            "damage_score": round(float(r["damage_score"]), 3),
            "text_flag_strict": int(r["text_flag_strict"]),
            "n_post_merge_refs": int(r["n_post_merge_refs"]),
            "n_followup_30": int(r["n_followup_30"]),
            "loc_added": int(r["loc_added"]),
            "loc_deleted": int(r["loc_deleted"]),
            "files_changed": int(r["files_changed"]),
            "has_tests_in_pr": int(r["has_tests_in_pr"]),
            "n_reviews": int(r["n_reviews"]),
            "merge_duration_hours": round(float(r["merge_duration_hours"]), 2),
            "title": (r.get("title") or "")[:200],
            "url": r.get("html_url"),
        })
    pd.DataFrame(csv_rows).to_csv(os.path.join(RESULTS, "rq4_case_studies.csv"), index=False)
    print(f"saved -> rq4_case_studies.csv")

    # Markdown template
    lines = ["# RQ4 — Top-20 High-Damage Case Study Package\n"]
    lines.append(
        "The following PRs are ranked by predicted composite damage score on "
        "the RQ4 test set. A human author should read 5 of them in detail and "
        "extract qualitative insights about WHAT KIND of damage agent PRs "
        "introduce (logic edge cases? hidden coupling? API mis-use? test gaps?).\n"
    )

    for i, r in enumerate(df.iterrows(), 1):
        _, row = r
        pid = int(row["id"])
        lines.append(f"\n## Case {i} — PR #{int(row.get('number', 0))} ({row['agent']})")
        lines.append(f"- **Repo**: `{row['full_name']}`")
        lines.append(f"- **Task type**: `{row['task_type']}`")
        lines.append(f"- **Language**: {row['language']}")
        lines.append(f"- **Damage score**: {row['damage_score']:.3f}")
        lines.append(f"- **Signals**: text_strict={int(row['text_flag_strict'])}, "
                     f"refs={int(row['n_post_merge_refs'])}, "
                     f"followups_30pct={int(row['n_followup_30'])}")
        lines.append(f"- **Size**: +{int(row['loc_added'])}/-{int(row['loc_deleted'])} LOC, "
                     f"{int(row['files_changed'])} files, "
                     f"tests-in-PR={int(row['has_tests_in_pr'])}")
        lines.append(f"- **Review**: {int(row['n_reviews'])} reviews, "
                     f"merge in {row['merge_duration_hours']:.2f}h")
        url = row.get("html_url", "")
        lines.append(f"- **URL**: {url}")
        lines.append(f"- **Title**: {(row.get('title') or '')[:250]}")
        body = (row.get("body") or "")[:800]
        if body:
            lines.append(f"\n<details><summary>PR body (first 800 chars)</summary>\n\n")
            lines.append(body)
            lines.append("\n</details>")

        if pid in file_lists:
            lines.append("\n**Top files modified**:")
            for f in file_lists[pid][:10]:
                adds = f.get("additions")
                dels = f.get("deletions")
                try:
                    adds = int(adds) if adds is not None and adds == adds else 0
                except Exception:
                    adds = 0
                try:
                    dels = int(dels) if dels is not None and dels == dels else 0
                except Exception:
                    dels = 0
                lines.append(f"  - `{f['filename']}` (+{adds}/-{dels})")

        if pid in ri_by_pr:
            lines.append("\n**Linked issues**:")
            for iss in ri_by_pr[pid][:5]:
                lines.append(f"  - [{iss.get('state','?')}] {iss.get('title','?')[:150]}")

        if pid in followups_by_src:
            lines.append("\n**Follow-up PRs (within 180 days, file overlap ≥30%)**:")
            for f in followups_by_src[pid][:10]:
                lines.append(
                    f"  - #{int(f['number'])} [{f.get('tgt_task','?')}] "
                    f"{(f.get('title') or '?')[:150]} (overlap {f.get('overlap_frac', 0):.2f})"
                )

        lines.append("\n**Qualitative notes (to be filled by author)**:")
        lines.append("- What did the agent change?")
        lines.append("- Why is this PR high-risk (edge case? coupling? API? tests?)")
        lines.append("- What did the follow-up PRs actually fix?")
        lines.append("- Single-sentence takeaway:")

    with open(os.path.join(RESULTS, "rq4_case_studies.md"), "w") as fh:
        fh.write("\n".join(lines))
    print(f"saved -> rq4_case_studies.md ({len(lines)} lines)")


if __name__ == "__main__":
    main()
