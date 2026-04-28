# Beyond the Revert: Latent Post-Merge Damage in AI Coding Agent PRs

Reproduction package for the EMSE paper *Beyond the Revert: An Empirical
Study of Latent Post-Merge Damage in AI Coding Agent Pull Requests*.

This repository contains the data-processing scripts, intermediate
artefacts, and analysis code for all three research questions of the
paper (after the April-2026 restructuring).

## Repository structure

```
.
├── README.md           ← you are here
├── .gitignore          ← excludes raw AIDev dump (925 MB), MSR2026 PDFs,
│                         and the Overleaf-managed `latex/` subtree
└── RQ/                 ← three-RQ reproduction tree (see RQ/README.md)
    ├── shared/         ← cross-cut data prep + cached parquet artefacts
    ├── RQ1_prevalence/      layered measurement framework (4 layers)
    ├── RQ2_heterogeneity/   bias decomposition (selection-bias share + residual)
    │   └── exploratory/     PR-level covariate associations
    │                        (renamed from RQ3_mechanism, demoted to
    │                         non-confirmatory in the April-2026 restructuring)
    └── RQ3_predictability/  merge-time LightGBM with 2x3 factorial robustness
                             (renamed from RQ4_predictability)
```

## Three research questions

1. **RQ1 — Layered measurement framework**.  No single SZZ-style proxy
   reliably measures latent post-merge damage on agent PRs.  Four
   independent layers (text → coarse structural → fix-task corrected
   structural → line-level qualitative audit) bracket the true
   prevalence to `[0.62%, 63.79%]` with a corrected mid-bound of
   `32.94%` and a strict lower bound of `~8.2%`.  Cohen's
   `κ ≈ −0.002` between text and structural signals.
2. **RQ2 — Decomposing the per-agent damage gap into selection bias
   and residual risk**.  Approximately `88%` of the naive `~16×`
   per-agent NB IRR between Codex / Devin and Claude Code is absorbed
   by a single `log_file_hotness` covariate; the residual is
   `1.85–2.0×` (NB IRR) and `1.47–1.55×` (Cox HR), with `100%`
   direction consistency over `12/12` agent coefficients across three
   outcome strata.
3. **RQ3 — Merge-time predictability without maintainer-trust
   proxies**.  A LightGBM model on `11` code-intrinsic features
   reaches `Precision@top-20% = 33.6%` against a `17.25%` test base
   rate (`~1.96×` lift); a `2 × 3` factorial robustness design
   (training-target × feature-set ablation) jointly rules out
   maintainer-trust proxy leakage and noisy-proxy overfitting,
   yielding strict-outcome AUC `0.639`, lift `2.01×`, and top-15
   feature overlap `12/15`.

## Reproducing the experiments

See [`RQ/README.md`](RQ/README.md) for the full directory layout, run
order, sample-scope description, and headline result tables.

## Data dependencies

The raw AIDev parquet corpus (~925 MB) is **not** committed to this
repository.  Fetch it from the upstream Hugging Face dataset and
unpack it as `AIDev_datasets/` at the repository root before running
`shared/code/build_sample.py`; everything downstream is computed and
cached under `RQ/shared/cache/`.

## Notes on the April-2026 restructuring

The original 4-RQ paper organised the empirical funnel as
*prevalence → heterogeneity → mechanism → predictability*.  After a
detailed editorial-style review, the **mechanism RQ** was retired
because its central claim (`n_reviews` as the only protective factor
robust across all four outcome strata) does not survive the strict
outcomes (under `struct_fix_majority`: OR = 0.999, p = 0.91) and
because `0/184` agent × moderator interactions survive global
BH-FDR correction (vs `11/184` per-model).  The corresponding code
and outputs are preserved under `RQ/RQ2_heterogeneity/exploratory/` and the paper
now reports them as a non-confirmatory subsection inside RQ2.

`RQ4_predictability/` was renamed to `RQ3_predictability/` to match
the new paper structure.  File names inside both renamed directories
keep the legacy `rq3_*` and `rq4_*` prefixes so existing scripts and
data references continue to work.
