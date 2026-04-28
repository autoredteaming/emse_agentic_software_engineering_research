# Beyond the Revert — 3-RQ Reproduction Package

Reproducible experiment backing the EMSE paper *Beyond the Revert: An
Empirical Study of Latent Post-Merge Damage in AI Coding Agent Pull
Requests*.  This directory tree corresponds to the 3-RQ structure used
in the paper after the April-2026 restructuring.

## Three research questions (measurement → bias decomposition → predictability)

1. **RQ1 — Layered measurement framework.** No single SZZ-style proxy
   reliably measures latent post-merge damage on agent PRs.  We
   triangulate four mutually independent layers (text, coarse
   structural, fix-task corrected structural, and line-level
   human/LLM-assisted audit) to constrain the true prevalence to
   `[0.62%, 63.79%]` with a fix-task corrected mid-bound of `32.94%`
   and a Layer-4 strict lower bound of `~8.2%`.  Cohen's
   `κ ≈ -0.002` between the textual and structural signals.
2. **RQ2 — Decomposing the per-agent damage gap.**  A naive comparison
   suggests Codex / Devin produce roughly `16×` more follow-up PR
   activity than Claude Code; after adding a single
   `log_file_hotness` covariate, ~88% of that gap is absorbed,
   leaving a residual relative risk of `1.85–2.0×` (NB IRR) and
   `1.47–1.55×` (Cox HR), with 100% direction consistency over 12/12
   agent coefficients across three outcome strata.
3. **RQ3 — Merge-time predictability without maintainer-trust
   proxies.**  A LightGBM model on 11 code-intrinsic features
   (`PURE_CODE`) reaches `Precision@top-20% = 33.6%` against a
   `17.25%` test base rate (`~1.96×` lift); a `2 × 3` factorial
   ablation (training-target × feature-set) jointly rules out
   maintainer-trust proxy leakage and noisy-proxy overfitting,
   yielding strict-outcome AUC `0.639`, lift `2.01×`, and top-15
   feature overlap `12/15`.

The earlier "RQ3 — Mechanism" content (mixed-effects logistic
regressions with 184 agent × moderator interactions, headline claims
about `n_reviews` as the only robust protective factor and the
`Codex × has_tests` interaction) has been demoted to **RQ2's
Exploratory: PR-Level Covariate Associations subsection** in the
paper.  Reason: under the strictest outcome (`struct_fix_majority`)
`n_reviews` has `OR = 0.999, p = 0.91`, and `0/184` interactions
survive global BH-FDR (vs `11/184` per-model).  The corresponding
scripts and `*.csv/.txt` outputs are preserved here in
`RQ2_exploratory/` so the descriptive analysis remains reproducible,
but they should not be cited as confirmatory evidence.

## Directory layout

```
RQ/
├── shared/
│   ├── code/
│   │   ├── load_data.py               memory-efficient AIDev loader
│   │   ├── build_sample.py            base_sample.parquet
│   │   ├── compute_signals.py         signals.parquet (text/bot bug-chatter)
│   │   ├── compute_structural.py      survival_events + followup_counts
│   │   ├── compute_file_churn.py      pr_file_churn.parquet (hotness covariate)
│   │   └── strict_outcome.py          struct_fix_flag / struct_fix_majority loader
│   └── cache/
│       ├── base_sample.parquet        24,014 agent + 5,044 human PRs
│       ├── signals.parquet            per-PR text bug-chatter signals
│       ├── survival_events.parquet    365,045 file-level events for Cox PH
│       ├── followup_counts.parquet    per-PR follow-up PR density (3 thresholds)
│       └── pr_file_churn.parquet      per-PR log_file_hotness covariate
├── RQ1_prevalence/
│   ├── code/
│   │   ├── rq1_prevalence.py          main: rates + κ + confusion matrix
│   │   └── rq1_ground_truth.py        fix-task ground-truth refinement
│   ├── qual/                          Layer-4 line-level auditing
│   │   ├── codebook.md                P1–P6 / N1–N2 codebook
│   │   ├── sample_pairs.py            stratified sampler (60 src/tgt pairs)
│   │   ├── extract_evidence.py        diff-evidence packet builder
│   │   ├── coded_results.csv          rater 1 (LLM, conservative prior)
│   │   ├── coded_rater2.csv           rater 2 (independent, blind)
│   │   ├── kappa_report.txt           inter-rater reliability summary
│   │   ├── evidence_packs.jsonl       per-pair code-diff evidence
│   │   └── sample_pairs.csv
│   ├── data/
│   │   ├── rq1_merged_signals.parquet
│   │   └── rq1_followup_tasks.parquet
│   └── results/
│       ├── rq1_prevalence.csv
│       ├── rq1_confusion.txt
│       ├── rq1_by_agent.csv
│       ├── rq1_by_task.csv
│       ├── rq1_ground_truth.txt
│       └── rq1_quadrant_decomp.csv
├── RQ2_heterogeneity/
│   ├── code/
│   │   ├── rq2_heterogeneity.py       main: KM + Cox + NB
│   │   ├── rq2_hetero_with_churn.py   churn-controlled Cox + NB
│   │   └── rq2_robust.py              3-outcome strictness re-runs
│   ├── data/
│   │   └── rq2_km_per_agent.csv
│   └── results/
│       ├── rq2_cox.txt                            naive
│       ├── rq2_negbin.txt                         naive
│       ├── rq2_cox_with_churn.txt                 churn-controlled (headline)
│       ├── rq2_negbin_with_churn.txt              churn-controlled (headline)
│       ├── rq2_agent_effect_comparison.csv        naive vs churn IRR side-by-side
│       ├── rq2_robust_per_agent.csv               loose / strict / majority
│       ├── rq2_robust_negbin.txt                  outcome = n_fix_fup
│       ├── rq2_robust_logit.txt                   outcome = struct_fix_majority
│       ├── rq2_robust_summary.txt                 Spearman ρ + p-values
│       ├── rq2_robust_per_lang.csv                by-language strict rates
│       ├── rq2_by_task.csv
│       ├── rq2_by_language.csv
│       └── rq2_by_stars.csv
├── RQ2_exploratory/                    (renamed from RQ3_mechanism)
│   │  Demoted to RQ2 Exploratory — see paper §4.2 sub-subsection
│   │  "Exploratory: PR-Level Covariate Associations (Non-Confirmatory)".
│   │  Retained here so the descriptive coefficients and the 11/184
│   │  per-model BH-survivors can be inspected for reproducibility.
│   ├── code/
│   │   ├── rq3_mechanism.py           main effects + 10 interaction models + BH
│   │   └── rq3_robust.py              3-outcome sensitivity for the same model
│   ├── data/
│   │   └── rq3_joined.parquet
│   └── results/
│       ├── rq3_main_effects.txt
│       ├── rq3_interactions.txt
│       ├── rq3_marginal_effects.csv   bh_global vs bh_within_model columns
│       ├── rq3_robust_compare.csv     loose / mid / strict OR side-by-side
│       ├── rq3_robust_main.txt
│       └── rq3_robust_summary.txt     Note: ends with "RQ3 main effects unstable"
└── RQ3_predictability/                 (renamed from RQ4_predictability)
    ├── code/
    │   ├── rq4_predictability.py      main: LightGBM FULL (23 features)
    │   ├── rq4_pure_code.py           FULL / PURE_CODE / CODE+REVIEW ablation
    │   ├── rq4_robust.py              T2 strict-outcome rerun
    │   └── rq4_case_studies.py        top-20 qualitative export
    ├── data/
    │   ├── rq4_train.parquet
    │   ├── rq4_test.parquet
    │   └── rq4_lightgbm.txt           saved LightGBM model
    └── results/
        ├── rq4_metrics.txt                      T1 FULL (best_iter = 3)
        ├── rq4_feature_importance.csv           gain ranking, FULL
        ├── rq4_pure_code_metrics.txt            T1 PURE_CODE (best_iter = 4)
        ├── rq4_feature_set_comparison.csv       FULL / PURE_CODE / CODE+REVIEW
        ├── rq4_robust_metrics.txt               T2 struct_fix_majority (best_iter = 45)
        ├── rq4_robust_feature_importance.csv    gain ranking, T2
        ├── rq4_robust_summary.txt               2x3 factorial summary
        ├── rq4_case_studies.csv
        └── rq4_case_studies.md
```

The legacy `rq3_*` and `rq4_*` filename prefixes are intentionally
preserved so the file paths printed by the original scripts remain
valid; only the **directory** names changed.  The paper now uses
`RQ2_exploratory/` (formerly `RQ3_mechanism/`) and
`RQ3_predictability/` (formerly `RQ4_predictability/`).

## Run order

```bash
cd RQ

# --- shared layer (run once) ---
python3 shared/code/build_sample.py            # ~30s
python3 shared/code/compute_signals.py         # ~15s
python3 shared/code/compute_structural.py      # ~5min  (survival + followup)
python3 shared/code/compute_file_churn.py      # ~10s

# --- RQ1: layered measurement framework ---
python3 RQ1_prevalence/code/rq1_prevalence.py       # ~10s
python3 RQ1_prevalence/code/rq1_ground_truth.py     # ~5min
# Layer 4 line-level auditing is partly manual; see qual/codebook.md

# --- RQ2: bias decomposition ---
python3 RQ2_heterogeneity/code/rq2_heterogeneity.py     # ~2min  (naive)
python3 RQ2_heterogeneity/code/rq2_hetero_with_churn.py # ~3min  (churn-controlled, headline)
python3 RQ2_heterogeneity/code/rq2_robust.py            # ~2min  (loose/strict/majority)

# --- RQ2 Exploratory (PR-level covariate associations, non-confirmatory) ---
python3 RQ2_exploratory/code/rq3_mechanism.py       # ~1min (11 interaction models)
python3 RQ2_exploratory/code/rq3_robust.py          # ~1min (3-outcome sensitivity)

# --- RQ3: merge-time predictability (2x3 factorial) ---
python3 RQ3_predictability/code/rq4_predictability.py  # ~20s   T1 FULL
python3 RQ3_predictability/code/rq4_pure_code.py       # ~40s   T1 PURE_CODE / CODE+REVIEW
python3 RQ3_predictability/code/rq4_robust.py          # ~30s   T2 struct_fix_majority
python3 RQ3_predictability/code/rq4_case_studies.py    # ~5min  top-20 qualitative export
```

Dependencies: pandas, pyarrow, numpy, scipy, scikit-learn, statsmodels,
lifelines, lightgbm.

## Sample scope

- **Treatment**: 24,014 merged agent PRs (Codex 18,004 / Devin 2,595 /
  Copilot 2,139 / Cursor 1,005 / Claude Code 271)
- **Metadata baseline**: 5,044 merged human PRs (metadata only — AIDev
  does not provide commit_details / timeline / related_issue for these)
- **Repositories**: 1,765 unique agent-merged repos
  (`base_sample[(is_agent==1) & merged_at.notna()]['repo_id'].nunique()`)
- **Merge window**: 2024-12-24 to 2025-07-30
- **Observation window**: 180 days post-merge, right-censored at
  `max(merged_at) = 2025-07-30`
- **Robustness re-run sample**: 23,871 PRs (143 dropped due to missing
  `language` field; the conditional model does not permit imputation
  without altering the design matrix)

## Headline results (matches paper Tables 1–9)

### RQ1 — Layered measurement framework (κ ≈ 0)

| Signal                                  | Rate                 |
|-----------------------------------------|----------------------|
| Text strict (bug comment / issue)       | 0.62 % (148/24,014)  |
| Text composite (any post-merge ref)     | 6.22 % (1,494)       |
| Structural any follow-up                | 74.35 % (17,854)     |
| Structural ≥30 % file overlap           | 63.79 % (15,319)     |
| **Structural + ≥1 fix-task followup**   | **32.94 % (7,909)**  |
| Structural + ≥50 % fix-task followups   | 9.26 % (2,224)       |

`Cohen's κ` between text-strict and struct-30% is **−0.002**.
Layer-4 line-level audit on 60 stratified pairs yields true-positive
rate `14/56 = 25%`, tightening the strict lower bound to
`32.94% × 25% ≈ 8.2%`.  Pattern distribution: P2 boundary omission 7,
P1 API misuse 3, P5 over-refactoring 3, P4 implicit coupling 1; N1
normal iteration 42, N2 insufficient evidence 4.

### RQ2 — Bias decomposition (88% shrinkage)

**Negative Binomial IRR** — naive vs churn-controlled (reference: Claude Code):

| Agent   | IRR (naive) | IRR (+ file hotness) | Shrinkage |
|---------|-------------|----------------------|-----------|
| Devin   | **17.54×**  | **2.00×**            | **88.6 %** |
| Codex   | **15.28×**  | **1.85×**            | **87.9 %** |
| Copilot | 4.13×       | 1.80×                | 56.3 %    |
| Cursor  | 4.02×       | 1.66×                | 58.7 %    |

**Cox PH HR** — naive vs churn-controlled:

| Agent   | HR (naive) | HR (+ file hotness) |
|---------|------------|---------------------|
| Devin   | 2.23       | **1.55**            |
| Codex   | 2.22       | **1.47**            |
| Copilot | 1.13       | 1.27                |
| Cursor  | 1.07       | 1.29                |

`log_file_hotness` itself: NB IRR `12.60` (p ≈ 0), Cox HR `3.93`.
NB AIC drops from 138,007 → 98,068 after adding the covariate.

3-outcome robustness: 12/12 agent coefficients positive across
loose / strict / majority outcomes; Spearman `ρ(loose, strict) = 0.80`
(p = 0.20 over n = 4 ranks; treated as descriptive stability rather
than a hypothesis test).

### RQ2 Exploratory (non-confirmatory) — PR-level covariate associations

`n_reviews` OR by outcome strictness:

| Outcome                     | OR    | p       |
|-----------------------------|-------|---------|
| `text_flag_strict`          | 0.92  | 0.047   |
| `struct_flag`               | 0.97  | < 1e-4  |
| `struct_fix_flag`           | 0.985 | 0.065   |
| `struct_fix_majority`       | 0.999 | **0.91**|

Direction-stable but the effect attenuates to `OR ≈ 1` under the
strictest outcome.  **Not advanced as an actionable governance
recommendation.**

Of 184 agent × moderator interaction terms tested:
`bh_within_model = 11`, `bh_global = 0`.  The much-cited
`Codex × has_tests_in_pr → text_flag_strict` (β = −3.52) belongs to
the per-model survivor set, not the global one.

### RQ3 — Merge-time predictability (2 × 3 factorial)

Temporal holdout: train ≤ 2025-06-30 (n = 14,060) /
test = 2025-07 (n = 9,954).

| Training target            | Feature set       | n_feat | AUC    | AP     | P@top20 % | Lift  | best_iter |
|----------------------------|-------------------|-------:|-------:|-------:|----------:|------:|----------:|
| T1 composite top-decile    | FULL              | 23     | 0.6194 | 0.290  | **0.338** | 1.96× | 3         |
| T1 composite top-decile    | **PURE_CODE**     | 11     | **0.597** | **0.289** | **0.336** | 1.95× | 4         |
| T1 composite top-decile    | CODE+REVIEW       | 15     | 0.595  | 0.299  | 0.334     | 1.94× | 6         |
| T2 `struct_fix_majority`   | FULL              | 23     | **0.639** | 0.147  | 0.153     | **2.01×** | **45** |

**Two construct-validity conclusions**:
- Removing all maintainer-trust features (FULL → PURE_CODE) drops AUC
  by only `0.023` → maintainer-trust proxies are not driving the
  predictive signal.
- Switching from the noisy composite proxy to the strict
  `struct_fix_majority` outcome **raises** AUC from 0.619 to 0.639 and
  raises lift from `1.96×` to `2.01×` → the model is not overfitting
  the loose proxy.  `best_iter` rising from `3` to `45` is direct
  evidence that the strict outcome carries a learnable signal that the
  loose proxy buries in noise.

Top-15 feature overlap between T1 FULL and T2 FULL: `12/15`.

## Citation

If you use this code or data, please cite the EMSE paper (forthcoming).
