# Post-Merge Damage Indicators in AI Coding Agent Pull Requests: An Empirical Study

Reproduction package for the manuscript by Lili Wang, Meng Hu, and Yubin Qu, prepared for submission to the *Journal of Systems and Software*.

The study examines 24,014 merged pull requests (PRs) from five AI coding agents across 1,765 repositories in the AIDev dataset. This repository contains the analysis scripts, intermediate data, saved results, and evidence for the LLM-assisted audit.

## Research questions and results

1. **RQ1: How do post-merge indicators differ?** The bug-related textual indicator flags 0.62% of PRs, the indicator based on at least 30% file overlap flags 63.79%, and requiring a fix or revert follow-up reduces the flagged share to 32.94%. Agreement between the textual and file-overlap indicators is near chance (Cohen's kappa approximately -0.002). In an LLM-assisted audit of 60 source–follow-up pairs, 14 of 56 assessable pairs are labeled as damage: estimated precision 25%, with a Wilson 95% confidence interval of 15.5%–37.7%. These indicators measure different recorded activities. Multiplying 32.94% by 25% gives an illustrative extrapolation of approximately 8.2%, conditional on audit representativeness, rather than a validated prevalence bound.
2. **RQ2: How do agent comparisons change after adjustment for file activity?** Adding both `log_file_hotness` and `log_file_hotness_before` reduces the Codex and Devin negative binomial incidence rate ratios relative to Claude Code by approximately 88%, to 1.85 and 2.00. Their adjusted Cox hazard ratios are 1.47 and 1.55. The models describe associations with follow-up activity and subsequent file modification; attenuation of the ratios does not identify a causal share of selection bias. Additional outcome definitions and PR-level associations are examined in sensitivity and exploratory analyses.
3. **RQ3: How well do PR features predict the selected indicators?** The temporal-split analysis compares two targets and four feature sets. The 11-feature `PURE_CODE` configuration achieves 33.62% precision among the highest-scoring 20% of PRs for the composite target, against a 17.25% evaluation-set positive rate (1.95-fold lift). This configuration includes agent, language, and task metadata as well as change features. A two-feature logistic baseline has higher AUC on this target; LightGBM has higher precision at the review cutoff. The strict-target full model has AUC 0.6394 and 2.01-fold lift. Eight of the top ten features overlap between the two full-model gain rankings.

The later temporal partition is used for both early stopping and final metric reporting. The composite target is defined using full-sample standardization and a full-sample threshold. Review counts include recorded activity from all timestamps, and repository popularity is taken from the dataset snapshot. These details define the scope of the retrospective prediction results.

## Repository structure

```text
RQ/
├── shared/                       Data loading, indicator construction, and cached data
├── RQ1_prevalence/               Indicator rates and LLM-assisted audit
├── RQ2_heterogeneity/            Agent comparisons and file-activity adjustment
│   └── exploratory/             PR-level associations and interaction analyses
└── RQ3_predictability/           Two targets, four feature sets, and baselines
```

See [RQ/README.md](RQ/README.md) for the run order, result-file mapping, and numerical tables.

## Data and execution

The raw AIDev parquet corpus is not included. Obtain the data described in the [AIDev paper](https://arxiv.org/abs/2507.15003), then set `DATA_DIR` in [RQ/shared/code/load_data.py](RQ/shared/code/load_data.py) to the absolute path of the extracted parquet directory. The checked-in loader uses the original machine's absolute path, so placing the data at the repository root alone does not configure it.

The scripts use Python 3 with `pandas`, `pyarrow`, `numpy`, `scipy`, `scikit-learn`, `statsmodels`, `lifelines`, and `lightgbm`. The repository does not include a lockfile for the original environment. The commands in [RQ/README.md](RQ/README.md) describe the analysis sequence; they were checked against the source files, without rerunning the experiments during this documentation revision.

The audit directory contains the sampled pairs, evidence packets, codebook, and saved labels. Two sessions of the same LLM used different prompts, with the second session blind to the first session's labels. These are LLM-assisted labels, not an independently human-coded reference set. The sampling and evidence-extraction scripts do not regenerate the saved LLM labels.

## File naming

Legacy `rq3_*` filenames under `RQ2_heterogeneity/exploratory/` and `rq4_*` filenames under `RQ3_predictability/` are retained to preserve script and data references. The `ground_truth` filename refers to filtering follow-ups by task labels. Some saved text outputs retain wording from earlier manuscript drafts; this README describes the current interpretation of those results.
