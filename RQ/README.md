# Reproduction guide

This directory supports *Post-Merge Damage Indicators in AI Coding Agent Pull Requests: An Empirical Study*, by Lili Wang, Meng Hu, and Yubin Qu. The three research questions concern indicator measurement, agent comparisons, and prediction of the selected indicators.

## Sample and observation periods

- 24,014 merged agent PRs: Codex 18,004; Devin 2,595; Copilot 2,139; Cursor 1,005; Claude Code 271.
- 1,765 repositories, with agent PRs merged from 24 December 2024 to 30 July 2025.
- 5,044 merged human PRs provide a metadata comparison; equivalent commit details, timelines, and related-issue records are not available for this group.
- Textual and follow-up-count indicators use up to 180 days after merge, limited by the dataset cutoff. Observation coverage therefore differs across PRs.
- Survival records track the next agent edit of a file and are censored at the latest observed merge. The survival construction does not impose the 180-day cap used for the count indicators.
- The outcome-definition sensitivity models use 23,871 PRs after excluding 143 rows with missing language.

## Data and dependencies

Obtain the raw parquet files described by the [AIDev paper](https://arxiv.org/abs/2507.15003). Set `DATA_DIR` in [shared/code/load_data.py](shared/code/load_data.py) to their absolute directory. The checked-in value points to the original execution environment. Raw data are excluded from Git; derived caches are stored under `shared/cache/`.

The scripts require Python 3 and these packages:

```text
pandas pyarrow numpy scipy scikit-learn statsmodels lifelines lightgbm
```

The repository does not lock the original package versions. The commands below map to the checked-in scripts; this documentation update did not rerun the experiments or validate execution in a newly installed environment.

## Run order

Run from the repository root:

```bash
cd RQ

# Shared data and indicators
python3 shared/code/build_sample.py
python3 shared/code/compute_signals.py
python3 shared/code/compute_structural.py
python3 shared/code/compute_file_churn.py

# RQ1: indicator measurement
python3 RQ1_prevalence/code/rq1_prevalence.py
python3 RQ1_prevalence/code/rq1_ground_truth.py

# RQ2: agent comparisons
python3 RQ2_heterogeneity/code/rq2_heterogeneity.py
python3 RQ2_heterogeneity/code/rq2_hetero_with_churn.py
python3 RQ2_heterogeneity/code/rq2_robust.py

# RQ2: exploratory PR-level associations
python3 RQ2_heterogeneity/exploratory/code/rq3_mechanism.py
python3 RQ2_heterogeneity/exploratory/code/rq3_robust.py

# RQ3: prediction and sensitivity analyses
python3 RQ3_predictability/code/rq4_predictability.py
python3 RQ3_predictability/code/rq4_pure_code.py
python3 RQ3_predictability/code/rq4_robust.py
python3 RQ3_predictability/code/rq4_case_studies.py
```

For the audit, [RQ1_prevalence/qual/sample_pairs.py](RQ1_prevalence/qual/sample_pairs.py) samples source–follow-up pairs using seed 20260413, language and agent strata, and the follow-up with the highest file overlap for each sampled source PR. [extract_evidence.py](RQ1_prevalence/qual/extract_evidence.py) builds diff-evidence packets. The saved LLM labels are separate artifacts; these commands do not regenerate them.

## Result-file mapping

All paths below are relative to this directory.

| Analysis | Main files |
|---|---|
| Shared sample and indicators | `shared/cache/base_sample.parquet`, `signals.parquet`, `survival_events.parquet`, `followup_counts.parquet`, `pr_file_churn.parquet` (all in `shared/cache/`) |
| RQ1 rates and agreement | `RQ1_prevalence/results/rq1_prevalence.csv`, `rq1_confusion.txt`, `rq1_ground_truth.txt`, `rq1_quadrant_decomp.csv` (all in `RQ1_prevalence/results/`) |
| Audit evidence and labels | `RQ1_prevalence/qual/codebook.md`, `sample_pairs.csv`, `evidence_packs.jsonl`, `coded_results.csv`, `coded_rater2.csv`, `kappa_report.txt` (all in `RQ1_prevalence/qual/`) |
| RQ2 count and survival models | `RQ2_heterogeneity/results/rq2_negbin.txt`, `rq2_cox.txt`, `rq2_negbin_with_churn.txt`, `rq2_cox_with_churn.txt`, `rq2_agent_effect_comparison.csv` (all in `RQ2_heterogeneity/results/`) |
| RQ2 outcome sensitivity | `RQ2_heterogeneity/results/rq2_robust_per_agent.csv`, `rq2_robust_negbin.txt`, `rq2_robust_logit.txt`, `rq2_robust_summary.txt` (all in `RQ2_heterogeneity/results/`) |
| RQ2 exploratory associations | `RQ2_heterogeneity/exploratory/results/rq3_main_effects.txt`, `rq3_marginal_effects.csv`, `rq3_robust_compare.csv` (all in `RQ2_heterogeneity/exploratory/results/`) |
| RQ3 composite target | `RQ3_predictability/results/rq4_metrics.txt`, `rq4_feature_set_comparison.csv`, `rq4_feature_importance.csv` (all in `RQ3_predictability/results/`) |
| RQ3 strict target | `RQ3_predictability/results/rq4_robust_metrics.txt`, `rq4_robust_feature_set_comparison.csv`, `rq4_robust_feature_importance.csv` (all in `RQ3_predictability/results/`) |

## RQ1: indicator rates and audit

| Indicator | Flagged PRs | Rate |
|---|---:|---:|
| Strict bug-related textual signal | 148 | 0.62% |
| Composite textual signal | 1,494 | 6.22% |
| Any structural follow-up | 17,854 | 74.35% |
| Follow-up with at least 30% file overlap | 15,319 | 63.79% |
| File-overlap signal with at least one fix or revert follow-up | 7,909 | 32.94% |
| File-overlap signal with at least 50% fix or revert follow-ups | 2,224 | 9.26% |

The strict textual and 30%-overlap indicators jointly flag 80 PRs. Cohen's kappa is approximately -0.002 and Jaccard similarity is 0.0052.

The 60-pair audit labels 14 pairs as damage, 42 as routine development, and four as undetermined. Among the 56 assessable pairs, estimated precision is 14/56 = 25% (Wilson 95% confidence interval 15.5%–37.7%). The damage labels comprise boundary-condition omission (P2: 7), API misuse (P1: 3), over-refactoring (P5: 3), and implicit coupling (P4: 1). The calculation 32.94% × 25% ≈ 8.2% is an illustrative extrapolation that assumes the audit precision applies to the flagged population; it is not a validated prevalence estimate or lower bound.

The audit uses two sessions of the same LLM with different prompts. The second session labels 20 pairs without seeing the first session's labels. Binary agreement is 90% (kappa 0.459); eight-class agreement is 75% (kappa 0.20). Agreement describes consistency between the two LLM sessions, not agreement with independent human coding.

## RQ2: agent comparisons

The following contrasts use Claude Code as the reference. “Before” and “after” refer to adding both `log_file_hotness` and `log_file_hotness_before` to models that already include the other covariates.

| Agent | NB IRR before | NB IRR after | IRR reduction | Cox HR before | Cox HR after |
|---|---:|---:|---:|---:|---:|
| Devin | 17.54 | 2.00 | 88.6% | 2.23 | 1.55 |
| Codex | 15.28 | 1.85 | 87.9% | 2.22 | 1.47 |
| Copilot | 4.13 | 1.80 | 56.3% | 1.13 | 1.27 |
| Cursor | 4.02 | 1.66 | 58.7% | 1.07 | 1.29 |

IRR reduction is calculated as `1 - IRR_after / IRR_before`. It describes attenuation of an observational association, not a causal decomposition of damage or selection bias.

The negative binomial model fixes dispersion at alpha = 1. Its offset is `log1p(loc_added + 1)`, equivalent to `log(loc_added + 2)`, and a log-size covariate is also included. This offset scales by change size rather than observation time. The Cox fit samples 200,000 file-level records with seed 42 and uses penalizer 0.01; it does not include repository-clustered uncertainty or repository frailty.

The separate outcome-definition sensitivity analysis has 12 positive agent coefficients across three outcomes. These models do not include the file-activity adjustment. Across four non-reference agents, the rank correlation is 0.80 (p = 0.20) for the loose and fix-filtered count outcomes, and 0.40 (p = 0.60) for the loose and majority-fix outcomes.

The exploratory logistic analyses use categorical fixed effects. Eleven of 184 interaction terms pass correction within their individual models; none pass global Benjamini–Hochberg false-discovery-rate correction. For the majority-fix outcome, the review-count odds ratio is 0.999 (p = 0.91).

## RQ3: prediction of selected indicators

The split date is 1 July 2025: 14,060 PRs are in the earlier training partition and 9,954 in the later evaluation partition. T1 is the composite score at or above its full-sample 90th percentile; its positive rates are 4.87% in training and 17.25% in evaluation. T2 is `struct_fix_majority`, with positive rates of 10.43% and 7.62%, respectively.

`FULL` has 23 features. `PURE_CODE` has 11 change, agent, language, and task features. `CODE_PLUS_REVIEW` adds four review or discussion features to `PURE_CODE`. `PURE_CODE_NO_AGENT` removes agent identity, leaving ten features.

| Target | Feature set | Features | AUC | Precision at top 20% | Lift | Best iteration |
|---|---|---:|---:|---:|---:|---:|
| T1 | FULL | 23 | 0.6194 | 0.3382 | 1.96 | 3 |
| T1 | PURE_CODE | 11 | 0.5966 | 0.3362 | 1.95 | 4 |
| T1 | CODE_PLUS_REVIEW | 15 | 0.5950 | 0.3342 | 1.94 | 6 |
| T1 | PURE_CODE_NO_AGENT | 10 | 0.5938 | 0.3116 | 1.81 | 1 |
| T2 | FULL | 23 | 0.6394 | 0.1528 | 2.01 | 45 |
| T2 | PURE_CODE | 11 | 0.6361 | 0.1497 | 1.97 | 34 |
| T2 | CODE_PLUS_REVIEW | 15 | 0.6372 | 0.1492 | 1.96 | 5 |
| T2 | PURE_CODE_NO_AGENT | 10 | 0.6322 | 0.1533 | 2.01 | 45 |

The two-feature logistic baseline uses added lines and review count. For T1, its AUC is 0.6378 and precision at the top 20% is 0.2392; for T2, these values are 0.5743 and 0.1151. Thus the T1 AUC and review-cutoff precision favor different models. The two full-model gain rankings share eight of their top ten features. This comparison uses the first ten rows of each saved importance file; the T2 file exports ten features.

The later partition is used for both early stopping and final metric reporting. T1 standardization and its threshold are computed on the full sample. Review and comment counts include recorded activity from all timestamps, and repository popularity comes from the dataset snapshot. These features are not all verified as available at merge time. The comparison therefore evaluates retrospective associations with the selected indicators. The scripts export gain-based feature importance; no SHAP computation is implemented.

## Preserved file names

The `rq3_*` prefix identifies exploratory files now located under RQ2; `rq4_*` identifies prediction files now located under RQ3. The `ground_truth` filename refers to filtering follow-ups by task labels. These names are retained so existing scripts and data references remain valid. Historical wording inside saved analysis outputs is preserved; this guide gives the current interpretation of the results.
