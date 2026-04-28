"""RQ4 robustness rerun — predict the strict struct_fix_majority outcome
directly (binary y) instead of the composite damage_score top-decile, and
run the full 2 x 4 factorial (this script x rq4_pure_code.py = 8 cells:
{T1, T2} x {FULL, PURE_CODE, CODE_PLUS_REVIEW, PURE_CODE_NO_AGENT}).

Goal: confirm that merge-time features still discriminate damage when (a)
the target is purified (T1 -> T2) and (b) the agent-identity proxy is
removed (PURE_CODE -> PURE_CODE_NO_AGENT).

Outputs:
  ../results/rq4_robust_metrics.txt          (T2 FULL, kept for back-compat)
  ../results/rq4_robust_feature_importance.csv (T2 FULL gain ranking)
  ../results/rq4_robust_summary.txt          (free-form prose summary)
  ../results/rq4_robust_feature_set_comparison.csv  (T2 x all 4 sets)
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

# Reuse the canonical FEATURE_SETS and helper from rq4_pure_code.
sys.path.insert(0, HERE)
from rq4_pure_code import FEATURE_SETS, train_eval  # noqa: E402


def main() -> None:
    base = pd.read_parquet(os.path.join(CACHE, "base_sample.parquet"))
    base = base[base["is_agent"] == 1].copy()
    strict = load_strict_outcomes()
    df = base.merge(strict, on="id", how="left")
    df["struct_fix_majority"] = df["struct_fix_majority"].fillna(0).astype(int)
    print(f"[RQ4-robust] n = {len(df):,}  pos = {int(df['struct_fix_majority'].sum())}  "
          f"rate = {df['struct_fix_majority'].mean():.4%}")

    df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True)
    split = pd.Timestamp("2025-07-01", tz="UTC")
    train_m = df["merged_at"] < split
    test_m = ~train_m
    y = df["struct_fix_majority"].values
    print(f"  train = {train_m.sum():,}  test = {test_m.sum():,}  "
          f"(pos rates {y[train_m].mean():.3%} / {y[test_m].mean():.3%})")

    # 2 x 4 grid: this script handles T2 x {FULL, PURE_CODE,
    # CODE_PLUS_REVIEW, PURE_CODE_NO_AGENT}.
    rows = []
    full_imp = None
    for name, feats in FEATURE_SETS.items():
        print(f"\n=== T2 / {name} ({len(feats)} features) ===")
        res = train_eval(df, feats, train_m, test_m, y)
        base_rate = y[test_m].mean()
        lift = res["p_at_20"] / base_rate if base_rate > 0 else float("nan")
        print(f"  AUC {res['auc']:.4f}  AP {res['ap']:.4f}  "
              f"Brier {res['brier']:.4f}  P@20% {res['p_at_20']:.4f}  "
              f"lift {lift:.2f}x  iter {res['best_iter']}")
        rows.append({
            "training_target": "T2_struct_fix_majority",
            "feature_set": name,
            "n_features": len(feats),
            "auc": res["auc"], "ap": res["ap"], "brier": res["brier"],
            "p_at_20": res["p_at_20"], "lift_at_20": lift,
            "best_iter": res["best_iter"],
        })
        if name == "FULL":
            full_imp = res["top_features"]

    cmp_df = pd.DataFrame(rows)
    cmp_path = os.path.join(RESULTS, "rq4_robust_feature_set_comparison.csv")
    cmp_df.to_csv(cmp_path, index=False)
    print(f"\nWrote {cmp_path}")
    print(cmp_df.round(4).to_string(index=False))

    # Baseline (logistic regression on loc_added + n_reviews) for headline cell
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score, average_precision_score
    base_X_train = df[train_m][["loc_added", "n_reviews"]].fillna(0).values
    base_X_test = df[test_m][["loc_added", "n_reviews"]].fillna(0).values
    lr = LogisticRegression(max_iter=500).fit(base_X_train, y[train_m])
    base_pred = lr.predict_proba(base_X_test)[:, 1]
    base_auc = roc_auc_score(y[test_m], base_pred)
    base_ap = average_precision_score(y[test_m], base_pred)
    order_b = np.argsort(-base_pred)
    top_n = int(0.20 * len(base_pred))
    base_p20 = y[test_m][order_b[:top_n]].mean()
    base_rate = y[test_m].mean()
    base_lift = base_p20 / base_rate if base_rate > 0 else float("nan")
    print(f"\n=== Baseline (logistic loc + reviews) ===")
    print(f"  AUC {base_auc:.4f}  AP {base_ap:.4f}  P@20% {base_p20:.4f}  lift {base_lift:.2f}x")

    # Headline rq4_robust_metrics.txt = T2 FULL (kept for back-compat)
    full_row = next(r for r in rows if r["feature_set"] == "FULL")
    with open(os.path.join(RESULTS, "rq4_robust_metrics.txt"), "w") as fh:
        fh.write("RQ4 robustness — predicting struct_fix_majority directly (binary)\n\n")
        fh.write(f"n_train: {int(train_m.sum())}  n_test: {int(test_m.sum())}\n")
        fh.write(f"train pos rate: {y[train_m].mean():.4f}\n")
        fh.write(f"test pos rate:  {y[test_m].mean():.4f}\n\n")
        fh.write(f"LightGBM AUC:              {full_row['auc']:.4f}\n")
        fh.write(f"LightGBM AP:               {full_row['ap']:.4f}\n")
        fh.write(f"LightGBM Brier:            {full_row['brier']:.4f}\n")
        fh.write(f"LightGBM Precision@top20%: {full_row['p_at_20']:.4f}\n")
        fh.write(f"LightGBM lift@top20%:      {full_row['lift_at_20']:.2f}x\n\n")
        fh.write(f"Baseline AUC:              {base_auc:.4f}\n")
        fh.write(f"Baseline AP:               {base_ap:.4f}\n")
        fh.write(f"Baseline Precision@top20%: {base_p20:.4f}\n")
        fh.write(f"Baseline lift@top20%:      {base_lift:.2f}x\n\n")
        fh.write(f"best iteration: {full_row['best_iter']}\n")

    # T2 FULL feature importance for back-compat overlap check
    if full_imp is not None:
        full_imp_path = os.path.join(RESULTS, "rq4_robust_feature_importance.csv")
        full_imp.to_csv(full_imp_path, index=False)
        orig_imp_path = os.path.join(RESULTS, "rq4_feature_importance.csv")
        if os.path.exists(orig_imp_path):
            orig = pd.read_csv(orig_imp_path)
            common = set(orig.head(15)["feature"]) & set(full_imp.head(15)["feature"])
            print(f"\n  top-15 overlap with original RQ4 (T1 FULL): {len(common)}/15")

    with open(os.path.join(RESULTS, "rq4_robust_summary.txt"), "w") as fh:
        fh.write("RQ4 robustness — strict outcome (struct_fix_majority) summary\n")
        fh.write("=" * 62 + "\n\n")
        fh.write(f"Outcome: struct_fix_majority (>=50% of overlap follow-ups are fix-task)\n")
        fh.write(f"Sample n = {len(df):,}  positives = {int(y.sum())}  "
                 f"({y.mean():.2%})\n\n")
        fh.write(f"Test-set metrics (T2 grid):\n")
        for r in rows:
            fh.write(f"  {r['feature_set']:24s}  n_feat={r['n_features']:2d}  "
                     f"AUC={r['auc']:.3f}  P@20%={r['p_at_20']:.3f}  "
                     f"lift={r['lift_at_20']:.2f}x  iter={r['best_iter']}\n")
        fh.write(f"  {'BASELINE_loc_reviews':24s}  n_feat= 2  "
                 f"AUC={base_auc:.3f}  P@20%={base_p20:.3f}  lift={base_lift:.2f}x\n\n")
        full_full = next(r for r in rows if r["feature_set"] == "FULL")
        if full_full["auc"] >= 0.70:
            fh.write("CONCLUSION: AUC >= 0.70 — merge-time features remain predictive of strict damage; RQ3 robust.\n")
        elif full_full["auc"] >= 0.60:
            fh.write("CONCLUSION: AUC 0.60-0.70 — predictability holds at attenuated strength; RQ3 robust with caveat.\n")
        else:
            fh.write("CONCLUSION: AUC < 0.60 — predictability degrades sharply on strict outcome; RQ3 needs reframing.\n")


if __name__ == "__main__":
    main()
