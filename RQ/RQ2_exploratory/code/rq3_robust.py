"""RQ3 robustness rerun — refit the main-effects logistic models with the
strict struct_fix_majority outcome added alongside the original two outcomes.

Goal: confirm that the sign/significance of merge-time predictors
(has_tests_in_pr, n_reviews, log_loc_added, agent fixed effects) does not
flip when we move from struct_flag (33% rate) to struct_fix_majority (9% rate).

Outputs:
  ../results/rq3_robust_main.txt          — full GLM summary for strict outcome
  ../results/rq3_robust_compare.csv       — side-by-side coef table (3 outcomes)
  ../results/rq3_robust_summary.txt       — narrative
"""
import os
import sys
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
    signals = pd.read_parquet(os.path.join(CACHE, "signals.parquet"))
    fup = pd.read_parquet(os.path.join(CACHE, "followup_counts.parquet"))
    strict = load_strict_outcomes()

    df = (base
          .merge(signals, on="id", how="left")
          .merge(fup, on="id", how="left")
          .merge(strict, on="id", how="left"))
    for c in ("text_flag_strict", "n_followup_30", "n_fix_fup",
              "struct_fix_flag", "struct_fix_majority"):
        df[c] = df[c].fillna(0).astype(int)
    df["struct_flag"] = (df["n_followup_30"] > 0).astype(int)

    top_langs = df["language"].value_counts().head(5).index.tolist()
    df["lang_c"] = df["language"].where(df["language"].isin(top_langs), "Other")
    df = df.dropna(subset=["task_type", "lang_c"]).copy()

    print(f"[RQ3-robust] n = {len(df):,}")
    for y in ("text_flag_strict", "struct_flag", "struct_fix_flag", "struct_fix_majority"):
        print(f"  {y:25s} rate = {df[y].mean():.4%}  n_pos = {int(df[y].sum())}")

    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    formula_template = (
        "{y} ~ C(agent) + C(task_type) + C(lang_c) "
        "+ log_loc_added + log_stars + has_tests_in_pr + n_reviews"
    )

    outcomes = ["struct_flag", "struct_fix_flag", "struct_fix_majority"]
    fits = {}
    summary_text = []
    for y in outcomes:
        m = smf.glm(formula=formula_template.format(y=y),
                    data=df, family=sm.families.Binomial()).fit()
        fits[y] = m
        summary_text.append(f"=== outcome: {y} ===")
        summary_text.append(f"n={int(m.nobs)}  events={int(df[y].sum())}  "
                            f"LL={m.llf:.1f}  AIC={m.aic:.1f}")
        summary_text.append(m.summary().as_text())
        summary_text.append("")

    with open(os.path.join(RESULTS, "rq3_robust_main.txt"), "w") as fh:
        fh.write("RQ3 robustness — main effects across loose, mid-strict, strict outcomes\n\n")
        fh.write("\n".join(summary_text))

    # Build side-by-side coefficient table
    keys_of_interest = []
    for k in fits["struct_flag"].params.index:
        if (k.startswith("C(agent)[T.") or
            k.startswith("C(task_type)[T.") or
            k in ("has_tests_in_pr", "n_reviews", "log_loc_added", "log_stars")):
            keys_of_interest.append(k)

    rows = []
    for k in keys_of_interest:
        row = {"term": k}
        for y in outcomes:
            m = fits[y]
            if k in m.params.index:
                row[f"OR_{y}"] = float(np.exp(m.params[k]))
                row[f"p_{y}"] = float(m.pvalues[k])
            else:
                row[f"OR_{y}"] = np.nan
                row[f"p_{y}"] = np.nan
        rows.append(row)

    cmp = pd.DataFrame(rows)
    cmp.to_csv(os.path.join(RESULTS, "rq3_robust_compare.csv"), index=False)

    # Sign-stability check: count terms where sign of log(OR) flips
    def sign(x):
        if pd.isna(x):
            return 0
        return 1 if x > 1 else (-1 if x < 1 else 0)

    flips_loose_vs_majority = 0
    direction_concordance = 0
    n_terms_compared = 0
    for r in rows:
        s_loose = sign(r["OR_struct_flag"])
        s_majority = sign(r["OR_struct_fix_majority"])
        if s_loose != 0 and s_majority != 0:
            n_terms_compared += 1
            if s_loose == s_majority:
                direction_concordance += 1
            else:
                flips_loose_vs_majority += 1

    print(f"\n=== sign concordance (loose vs majority) ===")
    print(f"  terms compared:   {n_terms_compared}")
    print(f"  same sign:        {direction_concordance}")
    print(f"  sign flips:       {flips_loose_vs_majority}")
    print(f"  concordance rate: {direction_concordance/max(n_terms_compared,1):.1%}")

    # Spearman rank correlation on coef magnitudes (just agent terms)
    from scipy.stats import spearmanr
    agent_terms = [k for k in keys_of_interest if k.startswith("C(agent)[T.")]
    a_loose = [fits["struct_flag"].params[k] for k in agent_terms]
    a_strict = [fits["struct_fix_flag"].params[k] for k in agent_terms]
    a_majority = [fits["struct_fix_majority"].params[k] for k in agent_terms]
    rho_strict, _ = spearmanr(a_loose, a_strict)
    rho_majority, _ = spearmanr(a_loose, a_majority)
    print(f"\n  Spearman ρ agent coefs (loose vs strict)   = {rho_strict:.3f}")
    print(f"  Spearman ρ agent coefs (loose vs majority) = {rho_majority:.3f}")

    # narrative
    with open(os.path.join(RESULTS, "rq3_robust_summary.txt"), "w") as fh:
        fh.write("RQ3 robustness — main-effects sign concordance across outcomes\n")
        fh.write("=" * 65 + "\n\n")
        fh.write(f"Sample n = {len(df):,}\n")
        for y in outcomes + ["text_flag_strict"]:
            fh.write(f"  {y:25s} events={int(df[y].sum())}  "
                     f"rate={df[y].mean():.4%}\n")
        fh.write("\nSide-by-side OR (3 outcomes):\n")
        fh.write(cmp.round(3).to_string(index=False) + "\n\n")
        fh.write(f"Sign concordance (loose struct_flag vs strict majority):\n")
        fh.write(f"  terms compared:   {n_terms_compared}\n")
        fh.write(f"  same sign:        {direction_concordance}\n")
        fh.write(f"  sign flips:       {flips_loose_vs_majority}\n")
        fh.write(f"  concordance rate: {direction_concordance/max(n_terms_compared,1):.1%}\n\n")
        fh.write(f"Spearman ρ agent coefs (loose vs strict)   = {rho_strict:.3f}\n")
        fh.write(f"Spearman ρ agent coefs (loose vs majority) = {rho_majority:.3f}\n\n")
        if direction_concordance / max(n_terms_compared, 1) >= 0.85:
            fh.write("CONCLUSION: ≥85% sign concordance — RQ3 main-effects directions are robust to outcome strictness.\n")
        elif direction_concordance / max(n_terms_compared, 1) >= 0.7:
            fh.write("CONCLUSION: 70–85% sign concordance — most directions hold but a few terms flip; flag in paper.\n")
        else:
            fh.write("CONCLUSION: <70% sign concordance — RQ3 main effects unstable; explicit caveat needed.\n")

    # Print compact term table
    print("\n=== compact OR comparison ===")
    for r in rows:
        if r["term"].startswith("C(agent)[T.") or r["term"] in (
            "has_tests_in_pr", "n_reviews", "log_loc_added", "log_stars"):
            print(f"  {r['term']:32s}  loose={r['OR_struct_flag']:7.3f}  "
                  f"strict={r['OR_struct_fix_flag']:7.3f}  majority={r['OR_struct_fix_majority']:7.3f}")


if __name__ == "__main__":
    main()
