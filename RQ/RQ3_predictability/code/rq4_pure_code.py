"""RQ4 — Feature-set ablation (reviewer rebuttal).

Two construct-validity concerns:
  (i) the FULL model is dominated by `merge_duration_hours`, which may
      encode "maintainer trust level" rather than code quality; and
  (ii) `agent` identity (the categorical "Codex / Devin / Cursor / ...")
      is itself observable at merge time, but it just re-encodes the
      RQ2 per-agent gap and is not a true *code-intrinsic* feature.

We separate the two concerns by training four feature-set variants:
  (A) FULL                  23 features incl. merge_duration, reviews,
                            stars, forks, n_comments, commenter_diversity
  (B) PURE_CODE             11 features: code-intrinsic + agent identity
                            (no review/popularity/merge-duration signals)
  (C) CODE_PLUS_REVIEW      15 features: PURE_CODE + review counts
                            (still excludes merge_duration and popularity)
  (D) PURE_CODE_NO_AGENT    10 features: PURE_CODE minus `agent`; the
                            strictest "code-intrinsic only" set, used to
                            verify that the predictor still works after
                            removing the agent-identity proxy.

Two-axis interpretation:
  FULL → CODE_PLUS_REVIEW → PURE_CODE rebuts "trust-proxy leakage"
  PURE_CODE → PURE_CODE_NO_AGENT rebuts "agent-identity proxy leakage"

Outputs:
  ../results/rq4_pure_code_metrics.txt
  ../results/rq4_feature_set_comparison.csv
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


def load_joined() -> pd.DataFrame:
    base = pd.read_parquet(os.path.join(CACHE, "base_sample.parquet"))
    base = base[base["is_agent"] == 1].copy()
    signals = pd.read_parquet(os.path.join(CACHE, "signals.parquet"))
    fup = pd.read_parquet(os.path.join(CACHE, "followup_counts.parquet"))
    df = base.merge(signals, on="id", how="left").merge(fup, on="id", how="left")
    for c in ("text_flag_strict", "n_post_merge_refs",
              "n_followup_30"):
        df[c] = df[c].fillna(0).astype(int)
    return df


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

    return (
        0.45 * z("text_flag_strict")
        + 0.40 * z("followup_30_rate")
        + 0.15 * z("refs_rate")
    )


FEATURE_SETS = {
    "FULL": [
        "agent", "task_type", "language",
        "loc_added", "loc_deleted", "files_changed", "n_commits",
        "has_tests_in_pr", "n_test_files",
        "n_reviews", "n_approvals", "n_changes_requested",
        "reviewer_diversity", "n_comments", "commenter_diversity",
        "n_bot_comments", "log_loc_added", "log_files_changed",
        "log_stars", "merge_duration_hours", "stars", "forks",
        "merge_month",
    ],
    "PURE_CODE": [
        "agent", "task_type", "language",
        "loc_added", "loc_deleted", "files_changed", "n_commits",
        "has_tests_in_pr", "n_test_files",
        "log_loc_added", "log_files_changed",
    ],
    "CODE_PLUS_REVIEW": [
        "agent", "task_type", "language",
        "loc_added", "loc_deleted", "files_changed", "n_commits",
        "has_tests_in_pr", "n_test_files",
        "log_loc_added", "log_files_changed",
        "n_reviews", "n_approvals", "n_changes_requested",
        "reviewer_diversity",
    ],
    # Strictest code-intrinsic set: PURE_CODE minus `agent` identity.
    # If AUC / lift here are close to PURE_CODE, the predictor is not
    # smuggling in agent-identity-as-shortcut.
    "PURE_CODE_NO_AGENT": [
        "task_type", "language",
        "loc_added", "loc_deleted", "files_changed", "n_commits",
        "has_tests_in_pr", "n_test_files",
        "log_loc_added", "log_files_changed",
    ],
}
CAT_COLS = ["agent", "task_type", "language", "merge_month"]


def train_eval(df_small: pd.DataFrame, feat_cols, train_m, test_m, y):
    import lightgbm as lgb
    from sklearn.metrics import (
        roc_auc_score, average_precision_score, brier_score_loss,
    )

    X = df_small[feat_cols].copy()
    cat_in_set = [c for c in CAT_COLS if c in feat_cols]
    for c in cat_in_set:
        X[c] = X[c].astype("category")
    num_cols = [c for c in feat_cols if c not in cat_in_set]
    for c in num_cols:
        X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0)

    X_tr, X_te = X[train_m], X[test_m]
    y_tr, y_te = y[train_m], y[test_m]

    dtrain = lgb.Dataset(X_tr, label=y_tr, categorical_feature=cat_in_set or "auto")
    dtest = lgb.Dataset(X_te, label=y_te, categorical_feature=cat_in_set or "auto",
                        reference=dtrain)
    params = dict(
        objective="binary", metric=["auc", "average_precision"],
        learning_rate=0.05, num_leaves=31, min_child_samples=20,
        feature_fraction=0.85, bagging_fraction=0.85, bagging_freq=5,
        verbose=-1,
    )
    model = lgb.train(
        params, dtrain, num_boost_round=500, valid_sets=[dtest],
        callbacks=[lgb.early_stopping(30), lgb.log_evaluation(0)],
    )
    pred = model.predict(X_te, num_iteration=model.best_iteration)
    auc = roc_auc_score(y_te, pred)
    ap = average_precision_score(y_te, pred)
    brier = brier_score_loss(y_te, pred)
    order = np.argsort(-pred)
    top_n = int(0.20 * len(pred))
    p20 = y_te[order[:top_n]].mean()

    imp = pd.DataFrame({
        "feature": X_tr.columns.tolist(),
        "gain": model.feature_importance(importance_type="gain"),
    }).sort_values("gain", ascending=False)

    return {
        "n_train": len(X_tr), "n_test": len(X_te),
        "auc": auc, "ap": ap, "brier": brier, "p_at_20": p20,
        "best_iter": model.best_iteration,
        "top_features": imp.head(10),
    }


def main():
    df = load_joined()
    df["damage_score"] = damage_score(df)
    threshold = df["damage_score"].quantile(0.9)
    df["y"] = (df["damage_score"] >= threshold).astype(int)
    df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True)
    print(f"[RQ4 variants] n={len(df):,}  pos rate={df['y'].mean():.3%}")

    split = pd.Timestamp("2025-07-01", tz="UTC")
    train_m = df["merged_at"] < split
    test_m = ~train_m
    y = df["y"].values
    print(f"  train {train_m.sum():,}  test {test_m.sum():,}  "
          f"(pos rates {df.loc[train_m,'y'].mean():.3%} / {df.loc[test_m,'y'].mean():.3%})")

    rows = []
    outputs = {}
    for name, feats in FEATURE_SETS.items():
        print(f"\n=== {name}  ({len(feats)} features) ===")
        res = train_eval(df, feats, train_m, test_m, y)
        print(f"  AUC {res['auc']:.4f}  AP {res['ap']:.4f}  "
              f"Brier {res['brier']:.4f}  P@20% {res['p_at_20']:.4f}  "
              f"iter {res['best_iter']}")
        print(f"  top 5 features:")
        for _, r in res["top_features"].head(5).iterrows():
            print(f"    {r['feature']:24s}  gain={r['gain']:.1f}")
        rows.append({
            "feature_set": name, "n_features": len(feats),
            "auc": res["auc"], "ap": res["ap"], "brier": res["brier"],
            "p_at_20": res["p_at_20"], "best_iter": res["best_iter"],
        })
        outputs[name] = res

    cmp_df = pd.DataFrame(rows)
    cmp_df.to_csv(os.path.join(RESULTS, "rq4_feature_set_comparison.csv"), index=False)
    print("\n=== comparison ===")
    print(cmp_df.round(4).to_string(index=False))

    # Write detailed text
    with open(os.path.join(RESULTS, "rq4_pure_code_metrics.txt"), "w") as fh:
        fh.write("RQ4 — Feature set ablation (reviewer rebuttal on merge_duration leakage)\n\n")
        fh.write(f"train rows: {int(train_m.sum())}\n")
        fh.write(f"test rows:  {int(test_m.sum())}\n\n")
        fh.write(cmp_df.round(4).to_string(index=False) + "\n\n")
        for name, res in outputs.items():
            fh.write(f"\n--- {name} top 10 features (by gain) ---\n")
            fh.write(res["top_features"].to_string(index=False) + "\n")


if __name__ == "__main__":
    main()
