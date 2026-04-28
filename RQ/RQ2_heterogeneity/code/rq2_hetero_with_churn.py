"""RQ2 — Heterogeneity analysis **with file-churn baseline covariate**.

Reviewer concern: hot files (README.md, package.json, CI YAML) get modified
frequently regardless of PR quality, confounding the follow-up signal.
We control for this by adding the file's AIDev-observed historical activity
to both the Cox PH and the Negative Binomial models. We then compare agent
coefficients BEFORE and AFTER controlling for churn — if the agent effect
shrinks to ~0, the reviewer is right (we were measuring hotness). If it
persists, the agent effect is independent of file hotness.

Outputs:
  ../results/rq2_cox_with_churn.txt
  ../results/rq2_negbin_with_churn.txt
  ../results/rq2_agent_effect_comparison.csv
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


def main() -> None:
    base = pd.read_parquet(os.path.join(CACHE, "base_sample.parquet"))
    base = base[base["is_agent"] == 1].copy()
    surv = pd.read_parquet(os.path.join(CACHE, "survival_events.parquet"))
    fup = pd.read_parquet(os.path.join(CACHE, "followup_counts.parquet"))
    churn = pd.read_parquet(os.path.join(CACHE, "pr_file_churn.parquet"))
    print(f"[RQ2-churn] surv {len(surv):,}  fup {len(fup):,}  churn {len(churn):,}")

    # ===== Cox PH: file-level, attach per-PR churn to each (pr_id, filename) row =====
    from lifelines import CoxPHFitter

    # We need per-file churn, not per-PR. Re-load the file index join to get
    # each file's total activity (was computed in compute_file_churn.py).
    # Approximation: use the per-PR mean hotness for all the PR's files.
    # This is slightly less precise than a per-file attachment but keeps
    # the pipeline simple.
    surv2 = surv.merge(
        churn[["id", "log_file_hotness", "log_file_hotness_before"]]
        .rename(columns={"id": "pr_id"}),
        on="pr_id", how="left",
    ).dropna(subset=["agent", "language", "log_file_hotness"])

    top_langs = surv2["language"].value_counts().head(5).index.tolist()
    surv2["lang_c"] = surv2["language"].where(surv2["language"].isin(top_langs), "Other")

    X = pd.get_dummies(
        surv2[["time_days", "event", "agent", "lang_c",
               "log_loc_added", "log_stars", "has_tests_in_pr", "n_reviews",
               "log_file_hotness", "log_file_hotness_before"]],
        columns=["agent", "lang_c"], drop_first=True, dtype=float,
    )
    const_cols = [c for c in X.columns if X[c].nunique() < 2]
    X = X.drop(columns=const_cols)
    n_sample = min(200_000, len(X))
    X_s = X.sample(n=n_sample, random_state=42)
    print(f"[RQ2-churn] fitting Cox PH on {len(X_s):,} rows...")
    cph = CoxPHFitter(penalizer=0.01)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cph.fit(X_s, duration_col="time_days", event_col="event")
        cph.print_summary(style="ascii", model="RQ2 Cox PH w/ file churn")
    with open(os.path.join(RESULTS, "rq2_cox_with_churn.txt"), "w") as fh:
        fh.write(f"RQ2 — Cox PH (file-level survival) with file churn baseline\n")
        fh.write(f"n rows: {len(X_s):,}  events: {int(X_s['event'].sum()):,}\n\n")
        fh.write(buf.getvalue())

    summary_df = cph.summary[["coef", "exp(coef)", "exp(coef) lower 95%",
                              "exp(coef) upper 95%", "p"]].round(3)
    print("\n=== Cox PH with churn — key HR ===")
    print(summary_df.to_string())

    # ===== Negative Binomial with churn covariate =====
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    nb = base.merge(fup[["id", "n_followup_30"]], on="id", how="left")
    nb = nb.merge(
        churn[["id", "log_file_hotness", "log_file_hotness_before"]],
        on="id", how="left",
    )
    nb["n_followup_30"] = nb["n_followup_30"].fillna(0).astype(int)
    nb = nb.dropna(subset=["task_type", "language", "log_file_hotness"]).copy()
    top_langs2 = nb["language"].value_counts().head(6).index.tolist()
    nb["lang_c"] = nb["language"].where(nb["language"].isin(top_langs2), "Other")
    nb["_offset"] = np.log1p(nb["loc_added"] + 1)

    # Model A (no churn)
    formula_a = ("n_followup_30 ~ C(agent) + C(task_type) + C(lang_c) "
                 "+ log_loc_added + log_stars + has_tests_in_pr + n_reviews")
    m_a = smf.glm(formula=formula_a, data=nb,
                  family=sm.families.NegativeBinomial(alpha=1.0),
                  offset=nb["_offset"].values).fit()
    # Model B (+ log_file_hotness)
    formula_b = formula_a + " + log_file_hotness + log_file_hotness_before"
    m_b = smf.glm(formula=formula_b, data=nb,
                  family=sm.families.NegativeBinomial(alpha=1.0),
                  offset=nb["_offset"].values).fit()

    print(f"\n[RQ2-churn] NB without churn: LL={m_a.llf:.1f}  AIC={m_a.aic:.1f}")
    print(f"[RQ2-churn] NB with    churn: LL={m_b.llf:.1f}  AIC={m_b.aic:.1f}")

    rows = []
    for k in m_a.params.index:
        if k.startswith("C(agent)[T."):
            agent = k.replace("C(agent)[T.", "").replace("]", "")
            rows.append({
                "agent": agent,
                "coef_no_churn": m_a.params[k],
                "IRR_no_churn": float(np.exp(m_a.params[k])),
                "p_no_churn": float(m_a.pvalues[k]),
                "coef_with_churn": m_b.params[k] if k in m_b.params.index else np.nan,
                "IRR_with_churn": float(np.exp(m_b.params[k])) if k in m_b.params.index else np.nan,
                "p_with_churn": float(m_b.pvalues[k]) if k in m_b.params.index else np.nan,
            })
    cmp_df = pd.DataFrame(rows)
    cmp_df["IRR_shrinkage_pct"] = (
        (cmp_df["IRR_no_churn"] - cmp_df["IRR_with_churn"])
        / cmp_df["IRR_no_churn"] * 100
    ).round(1)
    cmp_df.to_csv(os.path.join(RESULTS, "rq2_agent_effect_comparison.csv"), index=False)
    print("\n=== per-agent IRR: before vs after churn control ===")
    print(cmp_df.round(3).to_string(index=False))

    with open(os.path.join(RESULTS, "rq2_negbin_with_churn.txt"), "w") as fh:
        fh.write("RQ2 — Negative Binomial on n_followup_30 (with file churn)\n\n")
        fh.write(f"Model A (no churn) — LL={m_a.llf:.1f} AIC={m_a.aic:.1f}\n")
        fh.write(m_a.summary().as_text())
        fh.write("\n\n")
        fh.write(f"Model B (with churn) — LL={m_b.llf:.1f} AIC={m_b.aic:.1f}\n")
        fh.write(m_b.summary().as_text())

    # Churn coefficient itself
    print(f"\nlog_file_hotness in model B:")
    print(f"  coef = {m_b.params['log_file_hotness']:+.4f}  "
          f"IRR = {np.exp(m_b.params['log_file_hotness']):.3f}  "
          f"p = {m_b.pvalues['log_file_hotness']:.4g}")
    print(f"log_file_hotness_before in model B:")
    print(f"  coef = {m_b.params['log_file_hotness_before']:+.4f}  "
          f"IRR = {np.exp(m_b.params['log_file_hotness_before']):.3f}  "
          f"p = {m_b.pvalues['log_file_hotness_before']:.4g}")


if __name__ == "__main__":
    main()
