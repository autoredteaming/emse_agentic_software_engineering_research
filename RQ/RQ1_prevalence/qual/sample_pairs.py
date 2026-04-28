"""Stratified sample of (damaging_src_pr, fixing_tgt_pr) pairs.

Reviewer concern: struct_fix_flag is still signal-on-signal. We sample 60
pairs to qualitatively verify whether the flagged PRs really exhibit
"damage" patterns or are noise.

Selection rules:
  - src must have struct_fix_flag = 1 (i.e., its file changes were later
    touched by a fix/revert PR within 180 days)
  - keep only the highest-overlap (src,tgt) pair per src (best evidence)
  - tgt must have task_type in {fix, revert}
  - stratify the 60 picks by language tier (top-3 lang vs other)
    × agent tier (top-3 agent vs other) so no cell is empty

Outputs:
  qual/sample_pairs.csv  — 60 sampled (src, tgt) rows + metadata
"""
import os
import sys
import pandas as pd
import numpy as np

HERE = os.path.dirname(__file__)
RQ1 = os.path.join(HERE, "..")
SHARED = os.path.join(RQ1, "..", "shared")
CACHE = os.path.join(SHARED, "cache")

sys.path.insert(0, os.path.join(SHARED, "code"))
from load_data import AIDev  # noqa: E402

RNG = np.random.default_rng(20260413)
N_SAMPLE = 60
FIX_TASKS = {"fix", "revert"}


def main() -> None:
    base = pd.read_parquet(os.path.join(CACHE, "base_sample.parquet"))
    base = base[base["is_agent"] == 1].copy()
    base["repo_id"] = base["repo_id"].astype("int64")

    pairs = pd.read_parquet(os.path.join(RQ1, "data", "rq1_followup_tasks.parquet"))
    print(f"[sample] all pairs: {len(pairs):,}")

    # Keep fix/revert tgts at ≥30% overlap (mirrors struct_fix_flag def)
    p = pairs[
        (pairs["overlap_frac"] >= 0.30)
        & (pairs["tgt_task"].isin(FIX_TASKS))
    ].copy()
    print(f"[sample] fix-tgt pairs ≥30% overlap: {len(p):,}")

    # Best evidence = highest overlap_frac per src
    p = p.sort_values(["src_pr", "overlap_frac", "shared_files"],
                      ascending=[True, False, False])
    best = p.drop_duplicates("src_pr", keep="first")
    print(f"[sample] unique src PRs with fix evidence: {len(best):,}")

    # Attach src metadata from base
    meta = base[["id", "agent", "language", "repo_id", "merged_at",
                 "task_type"]].rename(columns={"id": "src_pr"})
    best = best.merge(meta, on="src_pr", how="inner")
    print(f"[sample] after meta join: {len(best):,}")

    # Stratify: language tier × agent tier
    top_langs = best["language"].value_counts().head(3).index.tolist()
    top_agents = best["agent"].value_counts().head(3).index.tolist()
    best["lang_tier"] = np.where(best["language"].isin(top_langs),
                                 best["language"], "_other_lang")
    best["agent_tier"] = np.where(best["agent"].isin(top_agents),
                                  best["agent"], "_other_agent")
    best["stratum"] = best["lang_tier"] + "::" + best["agent_tier"]

    # Proportional allocation, but every nonempty stratum gets ≥1
    counts = best["stratum"].value_counts()
    print(f"[sample] {len(counts)} strata\n{counts.to_string()}")
    quotas = {}
    remaining = N_SAMPLE
    for s, n in counts.items():
        q = max(1, int(round(N_SAMPLE * n / len(best))))
        quotas[s] = min(q, n)
    # Adjust to hit exactly N_SAMPLE
    total = sum(quotas.values())
    while total != N_SAMPLE:
        if total < N_SAMPLE:
            largest = max(quotas, key=lambda s: counts[s] - quotas[s])
            if quotas[largest] >= counts[largest]:
                break
            quotas[largest] += 1
        else:
            largest = max(quotas, key=lambda s: quotas[s])
            quotas[largest] -= 1
        total = sum(quotas.values())

    print(f"[sample] quotas: {quotas} -> {sum(quotas.values())}")

    picks = []
    for s, q in quotas.items():
        pool = best[best["stratum"] == s]
        if q == 0 or len(pool) == 0:
            continue
        idx = RNG.choice(len(pool), size=min(q, len(pool)), replace=False)
        picks.append(pool.iloc[idx])

    sample = pd.concat(picks, ignore_index=True)
    sample = sample[
        ["src_pr", "tgt_pr", "src_task", "tgt_task", "agent", "language",
         "repo_id", "shared_files", "overlap_frac", "merged_at", "stratum"]
    ].sort_values("src_pr").reset_index(drop=True)
    print(f"[sample] final n = {len(sample)}")

    out = os.path.join(HERE, "sample_pairs.csv")
    sample.to_csv(out, index=False)
    print(f"[sample] wrote {out}")
    print(sample[["src_pr", "tgt_pr", "agent", "language", "overlap_frac"]].head(10).to_string())


if __name__ == "__main__":
    main()
