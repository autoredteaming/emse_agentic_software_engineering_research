"""RQ4 — Predictability of post-merge damage from merge-time features only.

  1. Construct composite damage score (time-at-risk normalized)
  2. Binarize at 90th percentile as y
  3. LightGBM binary classification with temporal holdout (train: ≤ 2025-06-30,
     test: 2025-07)
  4. Baseline: logistic regression on loc_added + n_reviews
  5. Metrics: AUC, AP, Brier, Precision@top-20%
  6. Feature importance (gain) + SHAP top-features summary

Outputs:
  ../data/rq4_features.parquet, rq4_train.parquet, rq4_test.parquet
  ../data/rq4_lightgbm.txt  (saved model)
  ../results/rq4_metrics.txt
  ../results/rq4_feature_importance.csv
"""
import os
import sys
import json
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
    for c in ("text_flag_strict", "text_flag_composite", "n_post_merge_refs",
              "n_followup_any", "n_followup_30", "n_post_merge_bug_issues",
              "n_post_merge_bug_comments", "n_post_bot_bug_comments"):
        df[c] = df[c].fillna(0).astype(int)
    return df


def compute_damage(df: pd.DataFrame) -> pd.Series:
    """Composite damage score with time-at-risk normalization.

    Unified 3-component formula (matches rq4_pure_code.py):
      0.45 * z(text_flag_strict)
    + 0.40 * z(followup_30_rate)   # follow-up PR density per day
    + 0.15 * z(refs_rate)           # post-merge reference events per day

    (The original 4-component formula had fix_fwd_rate = followup_30_rate
    aliased, which was effectively the same information double-counted;
    we consolidated to 3 components in the reviewer-rebuttal pass.)
    """
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


def main() -> None:
    df = load_joined()
    print(f"[RQ4] joined: {len(df):,}")

    df["damage_score"] = compute_damage(df)
    threshold = df["damage_score"].quantile(0.9)
    df["y"] = (df["damage_score"] >= threshold).astype(int)
    print(f"[RQ4] threshold (90th pct): {threshold:.3f}  pos rate: {df['y'].mean():.3%}")

    feat_cols = [
        "agent", "task_type", "language",
        "loc_added", "loc_deleted", "files_changed", "n_commits",
        "has_tests_in_pr", "n_test_files",
        "n_reviews", "n_approvals", "n_changes_requested",
        "reviewer_diversity", "n_comments", "commenter_diversity",
        "n_bot_comments", "log_loc_added", "log_files_changed",
        "log_stars", "merge_duration_hours", "stars", "forks",
        "merge_month",
    ]
    df_small = df[["id", "merged_at", "y", "damage_score"] + feat_cols].copy()
    df_small["merged_at"] = pd.to_datetime(df_small["merged_at"], utc=True)

    # Temporal split at end of June 2025
    split = pd.Timestamp("2025-07-01", tz="UTC")
    train_m = df_small["merged_at"] < split
    test_m = ~train_m
    print(f"[RQ4] train: {train_m.sum():,}  test: {test_m.sum():,}")
    print(f"  train pos rate: {df_small.loc[train_m, 'y'].mean():.3%}")
    print(f"  test pos rate:  {df_small.loc[test_m, 'y'].mean():.3%}")

    cat_cols = ["agent", "task_type", "language", "merge_month"]
    num_cols = [c for c in feat_cols if c not in cat_cols]

    X = df_small[feat_cols].copy()
    for c in cat_cols:
        X[c] = X[c].astype("category")
    for c in num_cols:
        X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0)

    y = df_small["y"].values
    X_train, X_test = X[train_m], X[test_m]
    y_train, y_test = y[train_m], y[test_m]

    df_small[train_m].to_parquet(os.path.join(DATA_OUT, "rq4_train.parquet"), index=False)
    df_small[test_m].to_parquet(os.path.join(DATA_OUT, "rq4_test.parquet"), index=False)

    import lightgbm as lgb
    from sklearn.metrics import (
        roc_auc_score, average_precision_score, brier_score_loss,
    )
    from sklearn.linear_model import LogisticRegression

    dtrain = lgb.Dataset(X_train, label=y_train, categorical_feature=cat_cols)
    dtest = lgb.Dataset(X_test, label=y_test, categorical_feature=cat_cols, reference=dtrain)
    params = dict(
        objective="binary",
        metric=["auc", "average_precision"],
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        feature_fraction=0.85,
        bagging_fraction=0.85,
        bagging_freq=5,
        verbose=-1,
    )
    model = lgb.train(
        params, dtrain,
        num_boost_round=500,
        valid_sets=[dtest],
        callbacks=[lgb.early_stopping(30), lgb.log_evaluation(0)],
    )
    pred = model.predict(X_test, num_iteration=model.best_iteration)
    auc = roc_auc_score(y_test, pred)
    ap = average_precision_score(y_test, pred)
    brier = brier_score_loss(y_test, pred)
    order = np.argsort(-pred)
    top_n = int(0.20 * len(pred))
    p_at_20 = y_test[order[:top_n]].mean()
    print(f"\n=== LightGBM ===")
    print(f"  AUC:              {auc:.4f}")
    print(f"  AP:               {ap:.4f}")
    print(f"  Brier:            {brier:.4f}")
    print(f"  Precision@top20%: {p_at_20:.4f}")

    # Baseline
    base_X_train = df_small[train_m][["loc_added", "n_reviews"]].fillna(0).values
    base_X_test = df_small[test_m][["loc_added", "n_reviews"]].fillna(0).values
    lr = LogisticRegression(max_iter=500).fit(base_X_train, y_train)
    base_pred = lr.predict_proba(base_X_test)[:, 1]
    base_auc = roc_auc_score(y_test, base_pred)
    base_ap = average_precision_score(y_test, base_pred)
    order_b = np.argsort(-base_pred)
    base_p20 = y_test[order_b[:top_n]].mean()
    print(f"\n=== Baseline (logistic on loc + reviews) ===")
    print(f"  AUC:              {base_auc:.4f}")
    print(f"  AP:               {base_ap:.4f}")
    print(f"  Precision@top20%: {base_p20:.4f}")

    # Feature importance
    imp = pd.DataFrame({
        "feature": X_train.columns.tolist(),
        "gain": model.feature_importance(importance_type="gain"),
        "split": model.feature_importance(importance_type="split"),
    }).sort_values("gain", ascending=False)
    imp.to_csv(os.path.join(RESULTS, "rq4_feature_importance.csv"), index=False)
    print(f"\n=== top 15 features by gain ===")
    print(imp.head(15).to_string(index=False))

    # Save metrics
    with open(os.path.join(RESULTS, "rq4_metrics.txt"), "w") as fh:
        fh.write("RQ4 — Predictive damage model metrics\n\n")
        fh.write(f"n_train: {len(X_train)}\n")
        fh.write(f"n_test:  {len(X_test)}\n")
        fh.write(f"threshold (damage_score 90th pct): {threshold:.4f}\n")
        fh.write(f"train pos rate: {y_train.mean():.4f}\n")
        fh.write(f"test pos rate:  {y_test.mean():.4f}\n\n")
        fh.write(f"LightGBM AUC:              {auc:.4f}\n")
        fh.write(f"LightGBM AP:               {ap:.4f}\n")
        fh.write(f"LightGBM Brier:            {brier:.4f}\n")
        fh.write(f"LightGBM Precision@top20%: {p_at_20:.4f}\n\n")
        fh.write(f"Baseline AUC:              {base_auc:.4f}\n")
        fh.write(f"Baseline AP:               {base_ap:.4f}\n")
        fh.write(f"Baseline Precision@top20%: {base_p20:.4f}\n\n")
        fh.write(f"best iteration: {model.best_iteration}\n")

    model.save_model(os.path.join(DATA_OUT, "rq4_lightgbm.txt"))
    print(f"\nsaved model -> {os.path.join(DATA_OUT, 'rq4_lightgbm.txt')}")


if __name__ == "__main__":
    main()
