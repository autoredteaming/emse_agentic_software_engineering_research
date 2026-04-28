"""Helper: derive strict damage outcomes from the fix-task pair table.

Used by RQ2/RQ3/RQ4 robustness reruns. Produces, for each agent PR id:
  - struct_fix_flag      : ≥1 fix-task follow-up at ≥30% overlap
  - n_fix_fup            : number of fix-task follow-ups at ≥30% overlap
  - n_total_fup          : number of any-task follow-ups at ≥30% overlap
  - fix_share            : n_fix_fup / max(n_total_fup, 1)
  - struct_fix_majority  : ≥50% of follow-ups are fix-task AND ≥1 followup

This is the *strict* outcome reviewers want: a damage signal that requires
the later PR to itself be a bug-fix, not just an unrelated touch.
"""
import os
import pandas as pd
import numpy as np

HERE = os.path.dirname(__file__)
RQ1_DATA = os.path.join(HERE, "..", "..", "RQ1_prevalence", "data")

FIX_TASKS = {"fix", "revert"}


def load_strict_outcomes() -> pd.DataFrame:
    """Return DataFrame[id, n_fix_fup, n_total_fup, fix_share,
    struct_fix_flag, struct_fix_majority]."""
    pairs = pd.read_parquet(
        os.path.join(RQ1_DATA, "rq1_followup_tasks.parquet")
    )
    p = pairs[pairs["overlap_frac"] >= 0.30].copy()
    p["is_fix"] = p["tgt_task"].isin(FIX_TASKS).astype(int)
    g = p.groupby("src_pr").agg(
        n_fix_fup=("is_fix", "sum"),
        n_total_fup=("tgt_pr", "nunique"),
    ).reset_index().rename(columns={"src_pr": "id"})
    g["fix_share"] = np.where(
        g["n_total_fup"] > 0,
        g["n_fix_fup"] / g["n_total_fup"].clip(lower=1),
        0.0,
    )
    g["struct_fix_flag"] = (g["n_fix_fup"] > 0).astype(int)
    g["struct_fix_majority"] = ((g["fix_share"] >= 0.5) & (g["n_fix_fup"] > 0)).astype(int)
    return g
