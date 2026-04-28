"""RQ1 — Ground-truth validation of the structural signal.

Reviewer concern (Construct Validity): κ ≈ 0 between text signal and
structural signal could mean the structural signal is just capturing
"active files" rather than "damaged code". We rebut this by refining
the structural signal: a follow-up PR only counts as evidence of damage
when IT ITSELF has task_type ∈ {fix, revert, hotfix} — i.e. when a later
PR explicitly went back to FIX something the source PR changed.

This automated ground-truth approximation gives us:
  1. struct_fix_flag — refined structural signal requiring fix-task followup
  2. Re-computed Cohen's κ vs text_flag_strict
  3. Decomposition of the "only struct" quadrant: what fraction of those
     PRs actually have fix-task followups vs just normal-iteration followups?
  4. A per-quadrant task-type profile of the followups

Outputs:
  ../data/rq1_followup_tasks.parquet
  ../results/rq1_ground_truth.txt
  ../results/rq1_quadrant_decomp.csv
"""
import os
import sys
import pandas as pd
import numpy as np

HERE = os.path.dirname(__file__)
BASE = os.path.join(HERE, "..", "..")
CACHE = os.path.join(BASE, "shared", "cache")
DATA_OUT = os.path.join(HERE, "..", "data")
RESULTS = os.path.join(HERE, "..", "results")
os.makedirs(DATA_OUT, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)

sys.path.insert(0, os.path.join(BASE, "shared", "code"))
from load_data import AIDev  # noqa: E402

WINDOW_DAYS = 180
FIX_TASKS = {"fix", "revert"}  # strong "something went wrong" signal


def build_source_tgt_pairs(base: pd.DataFrame, fi: pd.DataFrame) -> pd.DataFrame:
    """Return (src_pr, tgt_pr, tgt_task, overlap_frac) rows for all
    within-180d, same-repo pairs."""
    meta = base[["id", "repo_id", "merged_at", "task_type"]].rename(
        columns={"id": "pr_id"}
    )
    fi = fi.merge(meta, on="pr_id", how="inner")
    print(f"[gt] file index joined: {len(fi):,}")

    repos = fi.groupby("repo_id").size().sort_values(ascending=False).index.tolist()
    print(f"[gt] {len(repos):,} repos")

    parts = []
    processed = 0
    for repo_id in repos:
        rf = fi[fi["repo_id"] == repo_id][["pr_id", "filename", "merged_at", "task_type"]]
        if len(rf) < 2:
            processed += 1
            continue
        src = rf.rename(columns={"pr_id": "src_pr", "merged_at": "src_merged",
                                 "task_type": "src_task"})
        tgt = rf.rename(columns={"pr_id": "tgt_pr", "merged_at": "tgt_merged",
                                 "task_type": "tgt_task"})
        j = src.merge(tgt, on="filename")
        j = j[j["src_pr"] != j["tgt_pr"]]
        delta = (j["tgt_merged"] - j["src_merged"]).dt.total_seconds() / 86400.0
        j = j[(delta > 0) & (delta <= WINDOW_DAYS)]
        if len(j) == 0:
            processed += 1
            continue
        # Count shared files per (src_pr, tgt_pr)
        shared = j.groupby(["src_pr", "tgt_pr", "src_task", "tgt_task"]).size().rename(
            "shared_files"
        ).reset_index()
        # Source PR's total touched files
        s_fc = src.groupby("src_pr").size().rename("src_files").reset_index()
        shared = shared.merge(s_fc, on="src_pr", how="left")
        shared["overlap_frac"] = shared["shared_files"] / shared["src_files"].clip(lower=1)
        parts.append(shared)
        processed += 1
        if processed % 500 == 0:
            print(f"    {processed}/{len(repos)}")
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["src_pr", "tgt_pr", "src_task", "tgt_task",
                 "shared_files", "src_files", "overlap_frac"]
    )


def main() -> None:
    ai = AIDev()
    base = pd.read_parquet(os.path.join(CACHE, "base_sample.parquet"))
    base = base[base["is_agent"] == 1].copy()
    base["merged_at"] = pd.to_datetime(base["merged_at"], utc=True)
    base["repo_id"] = base["repo_id"].astype("int64")

    signals = pd.read_parquet(os.path.join(CACHE, "signals.parquet"))
    fup = pd.read_parquet(os.path.join(CACHE, "followup_counts.parquet"))

    print("[gt] loading file index...")
    fi = ai.load_file_index()

    print("[gt] building source→target pair table (by fix-task)...")
    pairs = build_source_tgt_pairs(base, fi)
    out = os.path.join(DATA_OUT, "rq1_followup_tasks.parquet")
    pairs.to_parquet(out, index=False)
    print(f"[gt] pairs: {len(pairs):,}  saved -> {out}")

    # Per source PR: count follow-ups at overlap ≥30% by target task class
    p30 = pairs[pairs["overlap_frac"] >= 0.3].copy()
    p30["is_fix"] = p30["tgt_task"].isin(FIX_TASKS).astype(int)
    fix_counts = p30.groupby("src_pr").agg(
        n_fix_fup=("is_fix", "sum"),
        n_total_fup=("tgt_pr", "nunique"),
    ).reset_index()

    df = (
        base[["id", "agent", "task_type", "language", "merged_at"]]
        .merge(signals[["id", "text_flag_strict"]], on="id", how="left")
        .merge(fup[["id", "n_followup_30"]], on="id", how="left")
        .merge(fix_counts.rename(columns={"src_pr": "id"}), on="id", how="left")
    )
    for c in ("text_flag_strict", "n_followup_30", "n_fix_fup", "n_total_fup"):
        df[c] = df[c].fillna(0).astype(int)

    df["struct_flag"] = (df["n_followup_30"] > 0).astype(int)
    df["struct_fix_flag"] = (df["n_fix_fup"] > 0).astype(int)
    # Refined flag: struct signal exists AND ≥50% of followups are fix-task
    df["fix_share"] = np.where(
        df["n_total_fup"] > 0,
        df["n_fix_fup"] / df["n_total_fup"].clip(lower=1),
        0.0,
    )
    df["struct_fix_majority"] = (df["fix_share"] >= 0.5).astype(int) * df["struct_flag"]

    # Cohen's κ between text vs refined structural signals
    def kappa(a, b):
        n = len(df)
        both = int(((df[a] == 1) & (df[b] == 1)).sum())
        only_a = int(((df[a] == 1) & (df[b] == 0)).sum())
        only_b = int(((df[a] == 0) & (df[b] == 1)).sum())
        neither = int(((df[a] == 0) & (df[b] == 0)).sum())
        po = (both + neither) / n
        pa1 = (both + only_a) / n
        pb1 = (both + only_b) / n
        pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
        return (po - pe) / (1 - pe) if (1 - pe) > 0 else float("nan"), {
            "both": both, "only_a": only_a, "only_b": only_b, "neither": neither
        }

    k_original, c_original = kappa("text_flag_strict", "struct_flag")
    k_fix, c_fix = kappa("text_flag_strict", "struct_fix_flag")
    k_majority, c_majority = kappa("text_flag_strict", "struct_fix_majority")

    lines = []
    lines.append("RQ1 — Ground-truth validation of structural signal\n")
    lines.append(f"n = {len(df):,}")
    lines.append("")
    lines.append("--- Signal rates ---")
    lines.append(f"text_flag_strict            : {df['text_flag_strict'].mean():.4%}  ({int(df['text_flag_strict'].sum()):,})")
    lines.append(f"struct_flag (any fup≥30%)   : {df['struct_flag'].mean():.4%}  ({int(df['struct_flag'].sum()):,})")
    lines.append(f"struct_fix_flag (fix fup)   : {df['struct_fix_flag'].mean():.4%}  ({int(df['struct_fix_flag'].sum()):,})")
    lines.append(f"struct_fix_majority (≥50%)  : {df['struct_fix_majority'].mean():.4%}  ({int(df['struct_fix_majority'].sum()):,})")
    lines.append("")
    lines.append("--- Cohen's κ with text_flag_strict ---")
    lines.append(f"vs struct_flag           κ = {k_original:.4f}")
    lines.append(f"vs struct_fix_flag       κ = {k_fix:.4f}")
    lines.append(f"vs struct_fix_majority   κ = {k_majority:.4f}")
    lines.append("")
    lines.append("--- Confusion: text_strict × struct_fix_flag ---")
    for k, v in c_fix.items():
        lines.append(f"  {k:10s}: {v:7d}  ({v/len(df):.4%})")
    lines.append("")
    lines.append("--- Interpretation ---")
    refine_ratio = df["struct_fix_flag"].mean() / max(df["struct_flag"].mean(), 1e-9)
    lines.append(f"struct_fix_flag retains {refine_ratio:.1%} of the original struct_flag")
    lines.append(f"(i.e., {1-refine_ratio:.1%} of 'only struct' PRs were 'normal iteration', not damage)")

    with open(os.path.join(RESULTS, "rq1_ground_truth.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")

    for l in lines:
        print(l)

    # Quadrant decomposition
    df["quadrant"] = np.where(
        (df["text_flag_strict"] == 1) & (df["struct_flag"] == 1), "both",
        np.where(
            (df["text_flag_strict"] == 1) & (df["struct_flag"] == 0), "only_text",
            np.where(
                (df["text_flag_strict"] == 0) & (df["struct_flag"] == 1), "only_struct",
                "neither",
            ),
        ),
    )
    decomp = df.groupby("quadrant").agg(
        n=("id", "count"),
        has_fix_fup_rate=("struct_fix_flag", "mean"),
        mean_fix_share=("fix_share", "mean"),
        mean_total_fup=("n_total_fup", "mean"),
    ).round(4).reset_index()
    decomp.to_csv(os.path.join(RESULTS, "rq1_quadrant_decomp.csv"), index=False)
    print("\n=== quadrant decomposition ===")
    print(decomp.to_string(index=False))


if __name__ == "__main__":
    main()
