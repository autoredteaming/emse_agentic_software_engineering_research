# Damage-Pattern Codebook (RQ1 Qualitative Analysis)

This codebook is used to label the 60 sampled (src_pr, tgt_pr) pairs where
`src_pr` is an agent PR flagged by `struct_fix_flag = 1` and `tgt_pr` is a
later `fix`/`revert` PR that re-touched ≥30% of `src_pr`'s files within
180 days. We classify *what kind of damage*, if any, the `src_pr` introduced
that the `tgt_pr` had to repair.

## Damage categories (apply if evidence is positive)

**P1. API misuse / wrong call shape**
The agent PR called an existing function with the wrong arguments,
return-type assumptions, or used a deprecated/removed entry point. The
fix swaps the call shape, parameter order, or imports without redesigning
behavior.
*Marker:* fix diff modifies the exact call site or import line introduced
by src; commit message names the function/library.

**P2. Boundary / edge-case omission**
The agent PR implemented a feature that handled the happy path but missed
empty/None/zero/overflow/concurrent inputs. The fix adds a guard, branch,
or default case for the missed condition.
*Marker:* fix adds `if`/`try`/null-check around lines src introduced;
title contains "handle X case", "fix when Y empty", "guard against Z".

**P3. Type / contract / interface break**
The agent PR changed a public signature, schema, or data shape such that
downstream callers (or persisted artifacts) could no longer consume it.
The fix restores the contract or migrates callers.
*Marker:* fix touches type defs, interfaces, OpenAPI/proto/JSON schemas,
or migration files corresponding to src changes.

**P4. Hidden coupling / cross-module side-effect**
The agent PR refactored or modified a module without realizing another
module depended on its internal state, exported name, or invariant. The
fix repairs the unexpected breakage somewhere src didn't directly touch
in the *same* file but did touch the underlying contract.
*Marker:* fix touches the same file but a *different* function/region; or
restores a re-export, global, or initialization order.

**P5. Over-refactor / scope creep**
The agent PR rewrote / renamed / moved code beyond the stated task,
introducing churn that later had to be undone or re-styled. The fix
reverts cosmetic or organizational changes rather than fixing logic.
*Marker:* fix is a partial revert, rename rollback, or moves files back;
diff shows large-block deletions that mirror src's additions.

**P6. Test gap → regression escaped**
The agent PR did not add (or removed) tests covering its change, and the
later fix is *itself* a regression patch plus added tests for the case
src missed.
*Marker:* fix adds new test cases referencing the same module; fix commit
message says "regression", "missed test", "add coverage for X".

## Non-damage categories

**N1. Normal iteration (no damage)**
The follow-up fix is in the same area but addresses an issue *unrelated*
to src's change — e.g., src added feature A, fix patches an old bug in
feature B that happens to live in the same file.
*Marker:* fix touches lines src never modified; commit messages reference
different tickets/symbols.

**N2. Insufficient evidence**
Diff context too small, patch missing, or shared file is auto-generated
(lockfile, snapshot, build artifact) so we can't tell whether src caused
the later fix.

## Coding instructions

- Read src.title, src.body, src.files (patches), then tgt.title, tgt.body,
  tgt.files (patches).
- Pick the SINGLE best-fitting label P1–P6 or N1/N2.
- If two damage patterns apply, pick the one with strongest *direct*
  evidence in the fix diff (line-level overlap with src additions).
- Confidence ∈ {high, medium, low}.
- Justification: 1–2 sentences citing specific files / symbols.
