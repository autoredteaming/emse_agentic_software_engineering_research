"""RQ2 robustness rerun — replace noisy struct_flag outcome with the strict
struct_fix_majority outcome and refit per-agent / per-task heterogeneity.

Goal: confirm the per-agent ranking is stable when we move from the 33%-rate
proxy to the 9%-rate strict proxy. If rankings hold, RQ2's heterogeneity
conclusions are robust to label noise; if they flip, RQ2 needs a caveat.

Outputs:
  ../results/rq2_robust_negbin.txt        — main NB on n_fix_fup
  ../results/rq2_robust_logit.txt         — logistic on struct_fix_majority
  ../results/rq2_robust_per_agent.csv     — side-by-side per-agent IRR/OR
  ../results/rq2_robust_per_lang.csv      — by-language strict rates
  ../results/rq2_robust_summary.txt       — comparison narrative
"""
import os
import sys
import io
import contextlib
import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
BASE = os.path.join(HERE, "..", "..")
CACHE = os.path.join(BASE, "shared", "cache")
RESULTS = os.path.join(HERE, "..", "results")
os.makedirs(RESULTS, exist_ok=True)

sys.path.insert(0, os.path.join(BASE, "shared", "code"))
from strict_outcome import load_strict_outcomes  # noqa: E402


def main() -> None:
    base = pd.read_parquet(os.path.join(CACHE, "base_sample.parquet"))
    base = base[base["is_agent"] == 1].copy()
    strict = load_strict_outcomes()
    df = base.merge(strict, on="id", how="left")
    for c in ("n_fix_fup", "n_total_fup", "struct_fix_flag", "struct_fix_majority"):
        df[c] = df[c].fillna(0)
    df["fix_share"] = df["fix_share"].fillna(0.0)

    df = df.dropna(subset=["task_type", "language"]).copy()
    top_langs = df["language"].value_counts().head(6).index.tolist()
    df["lang_c"] = df["language"].where(df["language"].isin(top_langs), "Other")

    print(f"[RQ2-robust] n = {len(df):,}")
    print(f"  struct_fix_flag rate     = {df['struct_fix_flag'].mean():.4%}")
    print(f"  struct_fix_majority rate = {df['struct_fix_majority'].mean():.4%}")

    # =========================================================
    # (a) Negative binomial on n_fix_fup (count of fix follow-ups)
    # =========================================================
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    df["_offset"] = np.log1p(df["loc_added"] + 1)
    formula = ("n_fix_fup ~ C(agent) + C(task_type) + C(lang_c) "
               "+ log_loc_added + log_stars + has_tests_in_pr + n_reviews")
    print(f"\n[RQ2-robust] fitting NB on n_fix_fup, n = {len(df):,} ...")
    nb = smf.glm(
        formula=formula, data=df,
        family=sm.families.NegativeBinomial(alpha=1.0),
        offset=df["_offset"].values,
    ).fit()
    with open(os.path.join(RESULTS, "rq2_robust_negbin.txt"), "w") as fh:
        fh.write("RQ2 robustness — Negative Binomial on n_fix_fup (strict count)\n")
        fh.write(f"n = {len(df)}\n\n")
        fh.write(nb.summary().as_text())

    nb_agent_rows = []
    for k in nb.params.index:
        if k.startswith("C(agent)[T."):
            name = k.replace("C(agent)[T.", "").replace("]", "")
            nb_agent_rows.append({
                "agent": name,
                "IRR_strict": float(np.exp(nb.params[k])),
                "p_strict": float(nb.pvalues[k]),
            })

    # =========================================================
    # (b) Logistic on struct_fix_majority
    # =========================================================
    formula_b = ("struct_fix_majority ~ C(agent) + C(task_type) + C(lang_c) "
                 "+ log_loc_added + log_stars + has_tests_in_pr + n_reviews")
    print(f"\n[RQ2-robust] fitting logistic on struct_fix_majority ...")
    lg = smf.glm(formula=formula_b, data=df, family=sm.families.Binomial()).fit()
    with open(os.path.join(RESULTS, "rq2_robust_logit.txt"), "w") as fh:
        fh.write("RQ2 robustness — Logistic on struct_fix_majority (strictest binary)\n")
        fh.write(f"n = {len(df)}  events = {int(df['struct_fix_majority'].sum())}\n\n")
        fh.write(lg.summary().as_text())

    lg_agent_rows = []
    for k in lg.params.index:
        if k.startswith("C(agent)[T."):
            name = k.replace("C(agent)[T.", "").replace("]", "")
            lg_agent_rows.append({
                "agent": name,
                "OR_majority": float(np.exp(lg.params[k])),
                "p_majority": float(lg.pvalues[k]),
            })

    # =========================================================
    # (c) Original per-agent IRR (load from existing rq2_negbin.txt)
    # We re-fit the original negbin on n_followup_30 here for
    # an apples-to-apples coefficient comparison.
    # =========================================================
    fup = pd.read_parquet(os.path.join(CACHE, "followup_counts.parquet"))
    df2 = base.merge(fup[["id", "n_followup_30"]], on="id", how="left")
    df2["n_followup_30"] = df2["n_followup_30"].fillna(0).astype(int)
    df2 = df2.dropna(subset=["task_type", "language"]).copy()
    df2["lang_c"] = df2["language"].where(df2["language"].isin(top_langs), "Other")
    df2["_offset"] = np.log1p(df2["loc_added"] + 1)
    nb_orig = smf.glm(
        formula="n_followup_30 ~ C(agent) + C(task_type) + C(lang_c) "
                "+ log_loc_added + log_stars + has_tests_in_pr + n_reviews",
        data=df2,
        family=sm.families.NegativeBinomial(alpha=1.0),
        offset=df2["_offset"].values,
    ).fit()
    orig_agent_rows = []
    for k in nb_orig.params.index:
        if k.startswith("C(agent)[T."):
            name = k.replace("C(agent)[T.", "").replace("]", "")
            orig_agent_rows.append({
                "agent": name,
                "IRR_loose": float(np.exp(nb_orig.params[k])),
                "p_loose": float(nb_orig.pvalues[k]),
            })

    # Side-by-side
    a_orig = pd.DataFrame(orig_agent_rows)
    a_nb = pd.DataFrame(nb_agent_rows)
    a_lg = pd.DataFrame(lg_agent_rows)
    cmp = a_orig.merge(a_nb, on="agent", how="outer").merge(a_lg, on="agent", how="outer")
    # rank each column
    for col in ("IRR_loose", "IRR_strict", "OR_majority"):
        cmp[col + "_rank"] = cmp[col].rank(ascending=False, method="min")
    cmp = cmp.sort_values("IRR_loose", ascending=False)
    cmp.to_csv(os.path.join(RESULTS, "rq2_robust_per_agent.csv"), index=False)
    print("\n=== per-agent comparison (loose vs strict) ===")
    print(cmp.round(3).to_string(index=False))

    # Spearman rank correlation between loose / strict
    from scipy.stats import spearmanr
    rho1, p1 = spearmanr(cmp["IRR_loose"], cmp["IRR_strict"])
    rho2, p2 = spearmanr(cmp["IRR_loose"], cmp["OR_majority"])
    print(f"\nSpearman ρ (IRR_loose vs IRR_strict)   = {rho1:.3f}  p={p1:.3g}")
    print(f"Spearman ρ (IRR_loose vs OR_majority) = {rho2:.3f}  p={p2:.3g}")

    # =========================================================
    # (d) by-language strict rates
    # =========================================================
    by_lang = df.groupby("lang_c").agg(
        n=("id", "count"),
        struct_fix_flag_rate=("struct_fix_flag", "mean"),
        struct_fix_majority_rate=("struct_fix_majority", "mean"),
        mean_n_fix_fup=("n_fix_fup", "mean"),
    ).round(4).sort_values("struct_fix_majority_rate", ascending=False).reset_index()
    by_lang.to_csv(os.path.join(RESULTS, "rq2_robust_per_lang.csv"), index=False)
    print("\n=== by language (strict outcomes) ===")
    print(by_lang.to_string(index=False))

    # =========================================================
    # (e) summary text
    # =========================================================
    with open(os.path.join(RESULTS, "rq2_robust_summary.txt"), "w") as fh:
        fh.write("RQ2 robustness rerun — loose (n_followup_30) vs strict (n_fix_fup, struct_fix_majority)\n")
        fh.write("=" * 70 + "\n\n")
        fh.write(f"Sample n = {len(df):,}\n")
        fh.write(f"  loose outcome rate (any followup_30 > 0) = {(df2['n_followup_30']>0).mean():.4%}\n")
        fh.write(f"  strict struct_fix_flag rate              = {df['struct_fix_flag'].mean():.4%}\n")
        fh.write(f"  strict struct_fix_majority rate          = {df['struct_fix_majority'].mean():.4%}\n\n")
        fh.write("Per-agent IRR/OR (reference = Claude_Code unless absent):\n")
        fh.write(cmp.round(3).to_string(index=False) + "\n\n")
        fh.write(f"Spearman ρ (loose IRR vs strict IRR)        = {rho1:.3f}  p={p1:.3g}\n")
        fh.write(f"Spearman ρ (loose IRR vs majority OR)       = {rho2:.3f}  p={p2:.3g}\n\n")
        if rho1 >= 0.7:
            fh.write("CONCLUSION: per-agent ranking is highly stable (ρ ≥ 0.7) — RQ2 conclusions robust to outcome strictness.\n")
        elif rho1 >= 0.4:
            fh.write("CONCLUSION: per-agent ranking is moderately stable (0.4 ≤ ρ < 0.7) — direction holds, magnitudes differ.\n")
        else:
            fh.write("CONCLUSION: per-agent ranking is unstable (ρ < 0.4) — RQ2 conclusions need explicit caveat.\n")


if __name__ == "__main__":
    main()
