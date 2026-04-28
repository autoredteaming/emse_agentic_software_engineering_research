"""RQ4 robustness rerun — predict the strict struct_fix_majority outcome
directly (binary y) instead of the composite damage_score top-decile.

Goal: confirm that merge-time features still discriminate damage when the
target is purified, and that the leading features (LOC, agent, tests,
file-hotness) survive the noise stripping.

Outputs:
  ../results/rq4_robust_metrics.txt
  ../results/rq4_robust_feature_importance.csv
  ../results/rq4_robust_summary.txt
"""
import os
import sys
import json
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
    df["struct_fix_majority"] = df["struct_fix_majority"].fillna(0).astype(int)
    print(f"[RQ4-robust] n = {len(df):,}  pos = {int(df['struct_fix_majority'].sum())}  rate = {df['struct_fix_majority'].mean():.4%}")

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
    df_small = df[["id", "merged_at"] + feat_cols].copy()
    df_small["y"] = df["struct_fix_majority"].astype(int).values
    df_small["merged_at"] = pd.to_datetime(df_small["merged_at"], utc=True)

    # Same temporal split as RQ4 main analysis
    split = pd.Timestamp("2025-07-01", tz="UTC")
    train_m = df_small["merged_at"] < split
    test_m = ~train_m
    print(f"  train = {train_m.sum():,}  test = {test_m.sum():,}")
    print(f"  train pos rate = {df_small.loc[train_m,'y'].mean():.3%}  test pos rate = {df_small.loc[test_m,'y'].mean():.3%}")

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
    base_rate = y_test.mean()
    lift = p_at_20 / base_rate if base_rate > 0 else float("nan")

    print(f"\n=== LightGBM strict (struct_fix_majority) ===")
    print(f"  AUC:                {auc:.4f}")
    print(f"  AP:                 {ap:.4f}")
    print(f"  Brier:              {brier:.4f}")
    print(f"  Precision@top20%:   {p_at_20:.4f}  (lift = {lift:.2f}×)")
    print(f"  Test base rate:     {base_rate:.4f}")

    # Baseline
    base_X_train = df_small[train_m][["loc_added", "n_reviews"]].fillna(0).values
    base_X_test = df_small[test_m][["loc_added", "n_reviews"]].fillna(0).values
    lr = LogisticRegression(max_iter=500).fit(base_X_train, y_train)
    base_pred = lr.predict_proba(base_X_test)[:, 1]
    base_auc = roc_auc_score(y_test, base_pred)
    base_ap = average_precision_score(y_test, base_pred)
    order_b = np.argsort(-base_pred)
    base_p20 = y_test[order_b[:top_n]].mean()
    base_lift = base_p20 / base_rate if base_rate > 0 else float("nan")
    print(f"\n=== Baseline (logistic loc + reviews) ===")
    print(f"  AUC:              {base_auc:.4f}")
    print(f"  AP:               {base_ap:.4f}")
    print(f"  Precision@top20%: {base_p20:.4f}  (lift = {base_lift:.2f}×)")

    imp = pd.DataFrame({
        "feature": X_train.columns.tolist(),
        "gain": model.feature_importance(importance_type="gain"),
        "split": model.feature_importance(importance_type="split"),
    }).sort_values("gain", ascending=False)
    imp.to_csv(os.path.join(RESULTS, "rq4_robust_feature_importance.csv"), index=False)
    print(f"\n=== top 15 features by gain (strict outcome) ===")
    print(imp.head(15).to_string(index=False))

    # Compare to original importance order
    orig_imp_path = os.path.join(RESULTS, "rq4_feature_importance.csv")
    if os.path.exists(orig_imp_path):
        orig = pd.read_csv(orig_imp_path)
        orig_top = orig.head(15)["feature"].tolist()
        new_top = imp.head(15)["feature"].tolist()
        common = set(orig_top) & set(new_top)
        print(f"\n  top-15 overlap with original RQ4: {len(common)}/15")

    with open(os.path.join(RESULTS, "rq4_robust_metrics.txt"), "w") as fh:
        fh.write("RQ4 robustness — predicting struct_fix_majority directly (binary)\n\n")
        fh.write(f"n_train: {int(train_m.sum())}  n_test: {int(test_m.sum())}\n")
        fh.write(f"train pos rate: {y_train.mean():.4f}\n")
        fh.write(f"test pos rate:  {y_test.mean():.4f}\n\n")
        fh.write(f"LightGBM AUC:              {auc:.4f}\n")
        fh.write(f"LightGBM AP:               {ap:.4f}\n")
        fh.write(f"LightGBM Brier:            {brier:.4f}\n")
        fh.write(f"LightGBM Precision@top20%: {p_at_20:.4f}\n")
        fh.write(f"LightGBM lift@top20%:      {lift:.2f}x\n\n")
        fh.write(f"Baseline AUC:              {base_auc:.4f}\n")
        fh.write(f"Baseline AP:               {base_ap:.4f}\n")
        fh.write(f"Baseline Precision@top20%: {base_p20:.4f}\n")
        fh.write(f"Baseline lift@top20%:      {base_lift:.2f}x\n\n")
        fh.write(f"best iteration: {model.best_iteration}\n")

    # Summary
    with open(os.path.join(RESULTS, "rq4_robust_summary.txt"), "w") as fh:
        fh.write("RQ4 robustness — strict outcome (struct_fix_majority) summary\n")
        fh.write("=" * 62 + "\n\n")
        fh.write(f"Outcome: struct_fix_majority (≥50% of overlap follow-ups are fix-task)\n")
        fh.write(f"Sample n = {len(df_small):,}  positives = {int(df_small['y'].sum())}  "
                 f"({df_small['y'].mean():.2%})\n\n")
        fh.write(f"Test-set metrics:\n")
        fh.write(f"  LightGBM   AUC={auc:.3f}  AP={ap:.3f}  P@20%={p_at_20:.3f}  lift={lift:.2f}x\n")
        fh.write(f"  Baseline   AUC={base_auc:.3f}  AP={base_ap:.3f}  P@20%={base_p20:.3f}  lift={base_lift:.2f}x\n\n")
        if auc >= 0.70:
            fh.write("CONCLUSION: AUC ≥ 0.70 — merge-time features remain predictive of strict damage; RQ4 robust.\n")
        elif auc >= 0.60:
            fh.write("CONCLUSION: AUC 0.60–0.70 — predictability holds at attenuated strength; RQ4 robust with caveat.\n")
        else:
            fh.write("CONCLUSION: AUC < 0.60 — predictability degrades sharply on strict outcome; RQ4 needs reframing.\n")


if __name__ == "__main__":
    main()
