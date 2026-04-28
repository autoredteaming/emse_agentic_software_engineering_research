"""RQ3 — Mechanism: which merge-time features are associated with post-merge damage,
and which interactions modulate the agent main effects?

(a) Main-effects mixed-effects logistic regression on two outcomes:
    - text_flag_strict
    - struct_flag (≥30% file overlap followup)
(b) Interaction panels: C(agent) × M, M ∈ {task_type, has_tests_in_pr,
    reviews_bucket, language, stars_bucket}
(c) Per-model Benjamini-Hochberg FDR (q = 0.05)

Outputs:
  ../data/rq3_joined.parquet
  ../results/rq3_main_effects.txt
  ../results/rq3_interactions.txt
  ../results/rq3_marginal_effects.csv
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
os.makedirs(DATA_OUT, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)


def bh(p, q=0.05):
    p = np.array(p, dtype=float)
    p[np.isnan(p)] = 1.0
    n = len(p)
    order = np.argsort(p)
    sp = p[order]
    thr = (np.arange(1, n + 1) / n) * q
    passing = sp <= thr
    if not passing.any():
        return np.zeros(n, bool)
    k = np.where(passing)[0].max()
    out = np.zeros(n, bool)
    out[order[: k + 1]] = True
    return out


def build_joined() -> pd.DataFrame:
    base = pd.read_parquet(os.path.join(CACHE, "base_sample.parquet"))
    base = base[base["is_agent"] == 1].copy()
    signals = pd.read_parquet(os.path.join(CACHE, "signals.parquet"))
    fup = pd.read_parquet(os.path.join(CACHE, "followup_counts.parquet"))
    df = base.merge(signals, on="id", how="left").merge(fup, on="id", how="left")
    for c in ("text_flag_strict", "text_flag_composite",
              "n_followup_any", "n_followup_30"):
        df[c] = df[c].fillna(0).astype(int)
    df["struct_flag"] = (df["n_followup_30"] > 0).astype(int)
    df["struct_flag_any"] = (df["n_followup_any"] > 0).astype(int)
    return df


def main() -> None:
    df = build_joined()
    print(f"[RQ3] joined: {len(df):,}")
    out_p = os.path.join(DATA_OUT, "rq3_joined.parquet")
    df.to_parquet(out_p, index=False)

    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    # moderator buckets
    top_langs = df["language"].value_counts().head(5).index.tolist()
    df["lang_c"] = df["language"].where(df["language"].isin(top_langs), "Other")
    df["reviews_bucket"] = pd.cut(
        df["n_reviews"], bins=[-0.1, 0, 1, 3, 1000],
        labels=["0", "1", "2-3", "4+"]).astype(str)
    df["stars_bucket"] = pd.qcut(
        df["stars"].clip(upper=df["stars"].quantile(0.99)),
        q=4, duplicates="drop", labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)
    df = df.dropna(subset=["task_type", "lang_c"]).copy()

    outcomes = ["text_flag_strict", "struct_flag"]

    # =========================================================
    # (a) Main effects
    # =========================================================
    main_lines = []
    for y in outcomes:
        formula = (
            f"{y} ~ C(agent) + C(task_type) + C(lang_c) "
            "+ log_loc_added + log_stars + has_tests_in_pr + n_reviews"
        )
        try:
            m = smf.glm(formula=formula, data=df, family=sm.families.Binomial()).fit()
            main_lines.append(f"=== Main effects — outcome: {y} ===")
            main_lines.append(f"n={int(m.nobs)}  events={int(df[y].sum())}  LL={m.llf:.1f}")
            main_lines.append(m.summary().as_text())
            main_lines.append("")
        except Exception as e:
            main_lines.append(f"=== {y}: fit FAILED — {e}\n")

    with open(os.path.join(RESULTS, "rq3_main_effects.txt"), "w") as fh:
        fh.write("\n".join(main_lines))
    print(f"saved -> rq3_main_effects.txt")

    # Print a compressed summary of key coefficients
    for y in outcomes:
        formula = (
            f"{y} ~ C(agent) + C(task_type) + C(lang_c) "
            "+ log_loc_added + log_stars + has_tests_in_pr + n_reviews"
        )
        m = smf.glm(formula=formula, data=df, family=sm.families.Binomial()).fit()
        print(f"\n=== MAIN EFFECTS — {y} (n={int(m.nobs)}, events={int(df[y].sum())}) ===")
        for name in ("has_tests_in_pr", "n_reviews", "log_loc_added", "log_stars"):
            if name in m.params.index:
                coef, p = m.params[name], m.pvalues[name]
                print(f"  {name:20s} β={coef:+.4f}  OR={np.exp(coef):.3f}  p={p:.4g}")
        # Print all agent effects
        for k in m.params.index:
            if k.startswith("C(agent)[T."):
                name = k.replace("C(agent)[T.", "").replace("]", "")
                print(f"  agent={name:13s} β={m.params[k]:+.4f}  "
                      f"OR={np.exp(m.params[k]):.3f}  p={m.pvalues[k]:.4g}")

    # =========================================================
    # (b) Interaction panels
    # =========================================================
    interaction_specs = {
        "M1 agent × task_type": "C(agent) * C(task_type)",
        "M2 agent × has_tests_in_pr": "C(agent) * has_tests_in_pr + C(task_type)",
        "M3 agent × reviews_bucket": "C(agent) * C(reviews_bucket) + C(task_type)",
        "M4 agent × lang_c": "C(agent) * C(lang_c) + C(task_type)",
        "M5 agent × stars_bucket": "C(agent) * C(stars_bucket) + C(task_type)",
    }
    controls = "+ log_loc_added + log_stars"

    all_lines = []
    marginal_rows = []

    for y in outcomes:
        for name, core in interaction_specs.items():
            formula = f"{y} ~ {core} {controls}"
            try:
                m = smf.glm(formula=formula, data=df, family=sm.families.Binomial()).fit()
                all_lines.append(f"=== {y} — {name} ===")
                all_lines.append(f"n={int(m.nobs)}  AIC={m.aic:.1f}  LL={m.llf:.1f}")
                all_lines.append(m.summary().as_text())
                all_lines.append("")
                for p, c, pv, se in zip(
                    m.params.index, m.params.values, m.pvalues.values, m.bse.values
                ):
                    if ":" in p:
                        marginal_rows.append({
                            "outcome": y, "model": name, "term": p,
                            "coef": float(c), "se": float(se), "pvalue": float(pv),
                        })
            except Exception as e:
                all_lines.append(f"=== {y} — {name}: FIT FAILED — {e}\n")

    mdf = pd.DataFrame(marginal_rows)
    # Global BH across all 10 models
    if len(mdf):
        mdf["bh_global"] = bh(mdf["pvalue"].tolist(), q=0.05)
        # Per-model BH
        parts = []
        for (yy, mm), g in mdf.groupby(["outcome", "model"]):
            g = g.copy()
            g["bh_within_model"] = bh(g["pvalue"].tolist(), q=0.05)
            parts.append(g)
        mdf = pd.concat(parts, ignore_index=True)
    mdf.to_csv(os.path.join(RESULTS, "rq3_marginal_effects.csv"), index=False)

    with open(os.path.join(RESULTS, "rq3_interactions.txt"), "w") as fh:
        fh.write("\n".join(all_lines))

    print(f"\n[RQ3] interaction terms: {len(mdf)}")
    if len(mdf):
        print(f"  raw p<0.05:          {int((mdf['pvalue']<0.05).sum())}")
        print(f"  BH global q<0.05:    {int(mdf['bh_global'].sum())}")
        print(f"  BH per-model q<0.05: {int(mdf['bh_within_model'].sum())}")
        # Show the per-model BH survivors
        sig = mdf[mdf["bh_within_model"]].sort_values("pvalue")
        if len(sig):
            print("\n=== per-model BH survivors (q=0.05) ===")
            print(sig[["outcome", "model", "term", "coef", "pvalue"]].round(4).to_string(index=False))
        else:
            # Show top 10 raw p
            top = mdf.nsmallest(10, "pvalue")
            print("\n=== top 10 raw-p interaction terms (no BH survivors) ===")
            print(top[["outcome", "model", "term", "coef", "pvalue"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
