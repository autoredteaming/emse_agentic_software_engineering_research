"""RQ1 — Prevalence of post-merge latent damage.

Answers:
  1. How prevalent is post-merge damage under TEXT signal?
  2. How prevalent is post-merge damage under STRUCTURAL signal?
  3. Do the two signals agree? (Cohen's κ, Jaccard, 2×2 confusion)
  4. How do rates differ by agent / task_type / language?

Consumes: base_sample.parquet, signals.parquet, followup_counts.parquet
Outputs:
  ../data/rq1_merged_signals.parquet
  ../results/rq1_prevalence.csv
  ../results/rq1_confusion.txt
  ../results/rq1_by_agent.csv
  ../results/rq1_by_task.csv
"""
import os
import sys
import pandas as pd
import numpy as np

HERE = os.path.dirname(__file__)
BASE = os.path.join(HERE, "..", "..")
CACHE = os.path.join(BASE, "shared", "cache")
DATA_OUT = os.path.join(HERE, "..", "data")
RESULTS = os.path.join(HERE, "..", "results")
os.makedirs(DATA_OUT, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)


def load_merged() -> pd.DataFrame:
    base = pd.read_parquet(os.path.join(CACHE, "base_sample.parquet"))
    base = base[base["is_agent"] == 1].copy()
    signals = pd.read_parquet(os.path.join(CACHE, "signals.parquet"))
    fup = pd.read_parquet(os.path.join(CACHE, "followup_counts.parquet"))

    df = base.merge(signals, on="id", how="left").merge(fup, on="id", how="left")
    for c in ("n_post_merge_bug_issues", "n_post_merge_refs",
              "n_post_merge_bug_comments", "n_post_bot_bug_comments",
              "text_flag_strict", "text_flag_composite",
              "n_followup_any", "n_followup_30", "n_followup_50"):
        df[c] = df[c].fillna(0).astype(int)

    # Structural flag: at least one follow-up PR at ≥30% file overlap within 180d
    df["struct_flag"] = (df["n_followup_30"] > 0).astype(int)
    # Relaxed structural flag: any follow-up at all
    df["struct_flag_any"] = (df["n_followup_any"] > 0).astype(int)
    return df


def describe_prevalence(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rows.append({"signal": "text_strict", "n": int(df["text_flag_strict"].sum()),
                 "rate": df["text_flag_strict"].mean()})
    rows.append({"signal": "text_composite", "n": int(df["text_flag_composite"].sum()),
                 "rate": df["text_flag_composite"].mean()})
    rows.append({"signal": "struct_any_followup", "n": int(df["struct_flag_any"].sum()),
                 "rate": df["struct_flag_any"].mean()})
    rows.append({"signal": "struct_30pct_followup", "n": int(df["struct_flag"].sum()),
                 "rate": df["struct_flag"].mean()})
    out = pd.DataFrame(rows)
    out["rate_pct"] = (out["rate"] * 100).round(3)
    return out


def confusion(df: pd.DataFrame, t: str, s: str) -> dict:
    both = int(((df[t] == 1) & (df[s] == 1)).sum())
    only_t = int(((df[t] == 1) & (df[s] == 0)).sum())
    only_s = int(((df[t] == 0) & (df[s] == 1)).sum())
    neither = int(((df[t] == 0) & (df[s] == 0)).sum())
    n = len(df)
    # Cohen's kappa
    po = (both + neither) / n
    pt = ((both + only_t) / n) * ((both + only_s) / n)
    ps = ((only_s + neither) / n) * ((only_t + neither) / n)
    pe = pt + ps
    kappa = (po - pe) / (1 - pe) if (1 - pe) > 0 else float("nan")
    # Jaccard on positive class
    jacc = both / (both + only_t + only_s) if (both + only_t + only_s) > 0 else 0.0
    return {
        "text_label": t, "struct_label": s,
        "both": both, "only_text": only_t, "only_struct": only_s, "neither": neither,
        "total": n,
        "text_rate": (both + only_t) / n,
        "struct_rate": (both + only_s) / n,
        "kappa": kappa, "jaccard": jacc, "agreement": po,
    }


def main() -> None:
    df = load_merged()
    print(f"[RQ1] merged sample: {len(df):,}")

    out_p = os.path.join(DATA_OUT, "rq1_merged_signals.parquet")
    keep = ["id", "agent", "task_type", "language", "repo_id", "merged_at",
            "loc_added", "files_changed", "has_tests_in_pr", "n_reviews",
            "n_post_merge_bug_issues", "n_post_merge_refs",
            "n_post_merge_bug_comments", "n_post_bot_bug_comments",
            "text_flag_strict", "text_flag_composite",
            "n_followup_any", "n_followup_30", "n_followup_50",
            "struct_flag", "struct_flag_any"]
    df[keep].to_parquet(out_p, index=False)
    print(f"saved -> {out_p}")

    # 1) Overall prevalence
    prev = describe_prevalence(df)
    prev.to_csv(os.path.join(RESULTS, "rq1_prevalence.csv"), index=False)
    print("\n=== overall prevalence ===")
    print(prev.to_string(index=False))

    # 2) Confusion matrices & kappa (two flavors)
    conf_strict = confusion(df, "text_flag_strict", "struct_flag")
    conf_composite = confusion(df, "text_flag_composite", "struct_flag_any")
    print("\n=== confusion: text_strict × struct_30pct ===")
    for k, v in conf_strict.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")
    print("\n=== confusion: text_composite × struct_any ===")
    for k, v in conf_composite.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")

    with open(os.path.join(RESULTS, "rq1_confusion.txt"), "w") as fh:
        fh.write("RQ1 — Text vs Structural signal confusion matrix\n\n")
        for label, c in [("STRICT (text_strict × struct_30pct)", conf_strict),
                          ("COMPOSITE (text_composite × struct_any)", conf_composite)]:
            fh.write(f"--- {label} ---\n")
            fh.write(f"n: {c['total']}\n")
            fh.write(f"both:         {c['both']:7d}  ({c['both']/c['total']:.4%})\n")
            fh.write(f"only text:    {c['only_text']:7d}  ({c['only_text']/c['total']:.4%})\n")
            fh.write(f"only struct:  {c['only_struct']:7d}  ({c['only_struct']/c['total']:.4%})\n")
            fh.write(f"neither:      {c['neither']:7d}  ({c['neither']/c['total']:.4%})\n")
            fh.write(f"text rate:    {c['text_rate']:.4%}\n")
            fh.write(f"struct rate:  {c['struct_rate']:.4%}\n")
            fh.write(f"Cohen's κ:    {c['kappa']:.4f}\n")
            fh.write(f"Jaccard:      {c['jaccard']:.4f}\n")
            fh.write(f"Agreement:    {c['agreement']:.4f}\n\n")

    # 3) Per-agent breakdown
    by_agent = df.groupby("agent").agg(
        n=("id", "count"),
        text_strict=("text_flag_strict", "mean"),
        text_composite=("text_flag_composite", "mean"),
        struct_30=("struct_flag", "mean"),
        struct_any=("struct_flag_any", "mean"),
        mean_followup_30=("n_followup_30", "mean"),
    ).round(4).sort_values("struct_any", ascending=False).reset_index()
    by_agent.to_csv(os.path.join(RESULTS, "rq1_by_agent.csv"), index=False)
    print("\n=== by agent ===")
    print(by_agent.to_string(index=False))

    # 4) Per-task breakdown (top 12)
    by_task = df.groupby("task_type").agg(
        n=("id", "count"),
        text_strict=("text_flag_strict", "mean"),
        text_composite=("text_flag_composite", "mean"),
        struct_30=("struct_flag", "mean"),
        struct_any=("struct_flag_any", "mean"),
    ).round(4).sort_values("struct_any", ascending=False).reset_index()
    by_task.to_csv(os.path.join(RESULTS, "rq1_by_task.csv"), index=False)
    print("\n=== by task type ===")
    print(by_task.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
