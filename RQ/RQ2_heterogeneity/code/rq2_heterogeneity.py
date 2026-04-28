"""RQ2 — Heterogeneity of post-merge damage across agents, tasks, languages.

  (a) Kaplan-Meier per agent on file-level re-edit survival
  (b) Cox PH with repo frailty on file-level survival
  (c) Negative Binomial on follow-up PR density, per-agent IRR + per-task IRR
  (d) Cross-tab descriptives by language & stars bucket

Outputs:
  ../data/rq2_km_per_agent.csv
  ../results/rq2_cox.txt
  ../results/rq2_negbin.txt
  ../results/rq2_by_task.csv
  ../results/rq2_by_language.csv
  ../results/rq2_by_stars.csv
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
DATA_OUT = os.path.join(HERE, "..", "data")
RESULTS = os.path.join(HERE, "..", "results")
os.makedirs(DATA_OUT, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)


def main() -> None:
    base = pd.read_parquet(os.path.join(CACHE, "base_sample.parquet"))
    base = base[base["is_agent"] == 1].copy()

    surv = pd.read_parquet(os.path.join(CACHE, "survival_events.parquet"))
    fup = pd.read_parquet(os.path.join(CACHE, "followup_counts.parquet"))
    print(f"[RQ2] base: {len(base):,}  surv rows: {len(surv):,}  fup rows: {len(fup):,}")

    # =========================================================
    # (a) Kaplan-Meier per agent
    # =========================================================
    from lifelines import KaplanMeierFitter
    km_rows = []
    for agent, grp in surv.groupby("agent"):
        kmf = KaplanMeierFitter()
        kmf.fit(grp["time_days"], event_observed=grp["event"], label=agent)
        km_rows.append({
            "agent": agent,
            "n_obs": len(grp),
            "n_events": int(grp["event"].sum()),
            "median_days": kmf.median_survival_time_,
            "alive_30d": float(kmf.predict(30)),
            "alive_90d": float(kmf.predict(90)),
            "alive_180d": float(kmf.predict(180)),
        })
    km = pd.DataFrame(km_rows).sort_values("median_days", na_position="last")
    km.to_csv(os.path.join(DATA_OUT, "rq2_km_per_agent.csv"), index=False)
    print("\n=== Kaplan-Meier per agent ===")
    print(km.round(3).to_string(index=False))

    # =========================================================
    # (b) Cox PH model (downsample for speed; 200K rows)
    # =========================================================
    from lifelines import CoxPHFitter
    df = surv.dropna(subset=["agent", "language"]).copy()
    top_langs = df["language"].value_counts().head(5).index.tolist()
    df["lang_c"] = df["language"].where(df["language"].isin(top_langs), "Other")
    df["agent_c"] = df["agent"].astype("category")
    X = pd.get_dummies(
        df[["time_days", "event", "agent_c", "lang_c",
            "log_loc_added", "log_stars", "has_tests_in_pr", "n_reviews"]],
        columns=["agent_c", "lang_c"], drop_first=True, dtype=float,
    )
    const_cols = [c for c in X.columns if X[c].nunique() < 2]
    X = X.drop(columns=const_cols)
    n_sample = min(200_000, len(X))
    X_s = X.sample(n=n_sample, random_state=42)
    print(f"\n[RQ2] fitting Cox PH on {len(X_s):,} rows...")
    cph = CoxPHFitter(penalizer=0.01)
    cox_out = io.StringIO()
    with contextlib.redirect_stdout(cox_out):
        cph.fit(X_s, duration_col="time_days", event_col="event")
        cph.print_summary(style="ascii", model="RQ2 Cox PH (file-level survival)")
    with open(os.path.join(RESULTS, "rq2_cox.txt"), "w") as fh:
        fh.write(f"RQ2 — Cox proportional hazards (file-level survival)\n")
        fh.write(f"n rows fit: {len(X_s):,}  events: {int(X_s['event'].sum()):,}\n\n")
        fh.write(cox_out.getvalue())
    print("[RQ2] Cox summary saved")
    # Print HR table quickly
    summary_df = cph.summary[["coef", "exp(coef)", "exp(coef) lower 95%",
                              "exp(coef) upper 95%", "p"]].round(3)
    print("\n=== Cox PH HR table ===")
    print(summary_df.to_string())

    # =========================================================
    # (c) Negative Binomial on follow-up PR density
    # =========================================================
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    nb = base.merge(fup[["id", "n_followup_30", "n_followup_any"]], on="id", how="left")
    for c in ("n_followup_30", "n_followup_any"):
        nb[c] = nb[c].fillna(0).astype(int)
    nb = nb.dropna(subset=["task_type", "language"]).copy()
    top_langs2 = nb["language"].value_counts().head(6).index.tolist()
    nb["lang_c"] = nb["language"].where(nb["language"].isin(top_langs2), "Other")
    nb["_offset"] = np.log1p(nb["loc_added"] + 1)

    formula = ("n_followup_30 ~ C(agent) + C(task_type) + C(lang_c) "
               "+ log_loc_added + log_stars + has_tests_in_pr + n_reviews")
    print(f"\n[RQ2] fitting Negative Binomial on {len(nb):,} rows...")
    nb_model = smf.glm(
        formula=formula, data=nb,
        family=sm.families.NegativeBinomial(alpha=1.0),
        offset=nb["_offset"].values,
    ).fit()
    with open(os.path.join(RESULTS, "rq2_negbin.txt"), "w") as fh:
        fh.write(f"RQ2 — Negative Binomial on n_followup_30\n")
        fh.write(f"n: {len(nb)}\n\n")
        fh.write(nb_model.summary().as_text())
    # Extract per-agent IRR
    params = nb_model.params
    agent_rows = []
    for k in params.index:
        if k.startswith("C(agent)[T."):
            name = k.replace("C(agent)[T.", "").replace("]", "")
            agent_rows.append({"agent": name, "coef": params[k],
                               "IRR": float(np.exp(params[k])),
                               "p": float(nb_model.pvalues[k])})
    agent_irr = pd.DataFrame(agent_rows).sort_values("IRR", ascending=False)
    print("\n=== per-agent IRR (reference = Claude_Code) ===")
    print(agent_irr.round(3).to_string(index=False))

    task_rows = []
    for k in params.index:
        if k.startswith("C(task_type)[T."):
            name = k.replace("C(task_type)[T.", "").replace("]", "")
            task_rows.append({"task_type": name, "coef": params[k],
                              "IRR": float(np.exp(params[k])),
                              "p": float(nb_model.pvalues[k])})
    task_irr = pd.DataFrame(task_rows).sort_values("IRR", ascending=False)
    task_irr.to_csv(os.path.join(RESULTS, "rq2_by_task.csv"), index=False)
    print("\n=== per-task IRR ===")
    print(task_irr.round(3).to_string(index=False))

    # =========================================================
    # (d) descriptives by language & stars bucket
    # =========================================================
    signals = pd.read_parquet(os.path.join(CACHE, "signals.parquet"))
    df_lang = base.merge(signals, on="id", how="left").merge(fup, on="id", how="left")
    for c in ("text_flag_strict", "text_flag_composite", "n_followup_30", "n_followup_any"):
        df_lang[c] = df_lang[c].fillna(0)
    df_lang["struct_any"] = (df_lang["n_followup_any"] > 0).astype(int)
    df_lang["struct_30"] = (df_lang["n_followup_30"] > 0).astype(int)
    df_lang["lang_c"] = df_lang["language"].where(
        df_lang["language"].isin(df_lang["language"].value_counts().head(6).index.tolist()),
        "Other")
    by_lang = df_lang.groupby("lang_c").agg(
        n=("id", "count"),
        text_strict=("text_flag_strict", "mean"),
        text_composite=("text_flag_composite", "mean"),
        struct_any=("struct_any", "mean"),
        struct_30=("struct_30", "mean"),
        mean_followup_30=("n_followup_30", "mean"),
    ).round(4).sort_values("mean_followup_30", ascending=False).reset_index()
    by_lang.to_csv(os.path.join(RESULTS, "rq2_by_language.csv"), index=False)
    print("\n=== by language ===")
    print(by_lang.to_string(index=False))

    # Stars buckets
    df_lang["stars_bucket"] = pd.qcut(
        df_lang["stars"].clip(upper=df_lang["stars"].quantile(0.99)),
        q=4, duplicates="drop", labels=["Q1", "Q2", "Q3", "Q4"],
    ).astype(str)
    by_stars = df_lang.groupby("stars_bucket").agg(
        n=("id", "count"),
        text_strict=("text_flag_strict", "mean"),
        struct_any=("struct_any", "mean"),
        mean_followup_30=("n_followup_30", "mean"),
    ).round(4).reset_index()
    by_stars.to_csv(os.path.join(RESULTS, "rq2_by_stars.csv"), index=False)
    print("\n=== by stars bucket ===")
    print(by_stars.to_string(index=False))


if __name__ == "__main__":
    main()
