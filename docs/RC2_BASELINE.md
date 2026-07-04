# Finco1 RC2 — Frozen Legacy Engine Baseline

**Branch**: `Finco1-RC2`  
**SHA**: `b52d39c79683a1ff6965ef197422056a541a81ab`  
**Date frozen**: 2026-07-04  
**Status**: Permanently frozen. No feature work. No extraction work. No PRs.

---

## Purpose

`Finco1-RC2` is the permanent frozen baseline for the Finco One financial engine.

It marks the completion of the structured engineering programme that produced two production-calibrated financial models (TUHO Wind 1, Oborovo Solar) and the Phase 0 pre-extraction stabilisation. It is the ground truth from which all future extraction work is validated.

The branch exists so that at any point in the extraction programme — regardless of what changes are made to `main` — a clean, known-good reference for every financial formula, parity result, and architecture decision is recoverable without archaeology.

---

## Baseline State

### Current main HEAD

| Field | Value |
|-------|-------|
| SHA | `b52d39c79683a1ff6965ef197422056a541a81ab` |
| Commit | docs: Finco One v2 Controlled Extraction Blueprint |
| Parent | `4787207f8de356369dfc4f1592b92af1a0403912` (Phase 0 merge) |
| Date | 2026-07-04 |

### Engine Status

| Subsystem | Status |
|-----------|--------|
| Financial engine (domain/) | Frozen — all formulas validated |
| Waterfall engine | Green — parity confirmed |
| Tax bridge | Corrected (Phase 0 Z1) — Croatian CIT §16 basis |
| SHL engine | Stable — canonical wiring |
| Depreciation engine | Stable — tax and book schedules separate |
| Identity dispatch | Eliminated (Stack AC + Phase 0 Y3) |
| Post-engine mutation | Eliminated (Phase 0 Z2) |

### Parity Status

| Test Suite | Status |
|-----------|--------|
| Parity guardrails (Phase 51F) | GREEN — 21/21 |
| Engine invariants (Stack X) | GREEN — 58/58 |
| Canonical formula tests (Stack W) | GREEN — 18/18 |
| Tax bridge runtime tests | GREEN |
| Phase 0 hotfix tests | GREEN — 17/17 |

### Parity Baselines (Phase 0 / Z1 corrected)

| Project | KPI | Value | Tolerance |
|---------|-----|-------|-----------|
| TUHO Wind 1 | equity_irr | 11.32% | ±0.05% |
| TUHO Wind 1 | actual_avg_dscr | 1.3786 | ±0.001 |
| TUHO Wind 1 | total_tax_keur | 35,414 kEUR | ±500 kEUR |
| TUHO Wind 1 | total_distributions | 165,471 kEUR | ±200 kEUR |
| Oborovo Solar | equity_irr | 10.54% | ±0.05% |
| Oborovo Solar | actual_avg_dscr | 1.179 | ±0.005 |
| Oborovo Solar | total_tax_keur | 8,874 kEUR | ±100 kEUR |

### Architecture Status

| Principle | Status |
|-----------|--------|
| Configuration Over Identity | Enforced — Stack AC + Phase 0 Y3 |
| No post-engine result mutation | Enforced — Phase 0 Z2 |
| Capability flags as sole dispatch | Enforced — `ProjectInfo` / `FinancingParams` |
| Frozen DS fixture path | Config-driven — `frozen_senior_ds_fixture_path` |

---

## Engineering History Reference

The RC2 baseline is the product of a structured multi-stack engineering programme:

| Phase / Stack | Contribution |
|--------------|-------------|
| Stack W | Canonical formula registry (18 tests, all frozen) |
| Stack X | Engine invariant suite (58 tests) |
| Phase 51F | Golden parity guardrails (21 guardrails, SHA-pinned) |
| Stack AB | Engine architecture cleanup |
| Stack AC | Runtime identity elimination — Phase 1 |
| Phase 0 Y3 | All remaining identity guards removed |
| Phase 0 Z1 | Tax bridge formula corrected to Croatian CIT §16 basis |
| Phase 0 Z2 | Bridge cash tax moved to reconciliation-only field |
| Extraction Plan | v2 Controlled Extraction Blueprint committed |

---

## Why This Branch is Frozen

The value of `Finco1-RC2` is that it is immutable.

Any change to the baseline — including "small" fixes — creates ambiguity about what was validated and what was changed post-freeze. The extraction programme depends on having a single, unambiguous reference point. The moment this branch accepts commits, it loses its value as an anchor.

**Engineering policy:**

- No feature branches are created from `Finco1-RC2`
- No PRs target `Finco1-RC2`
- No hotfixes are applied to `Finco1-RC2` without explicit written justification and unanimous engineering review
- Emergency fixes, if ever required, are applied to `main` only and the RC branch is updated to a new named tag

---

## Relationship to Controlled Extraction

The v2 extraction programme proceeds on `main` (and purpose-scoped feature branches). It does not touch `Finco1-RC2`.

At each extraction milestone, the parity harness is run against the extracted engine and compared to the RC2 baselines above. A milestone is not complete until parity is green against this baseline.

After extraction is complete and parity is proven, the extracted architecture will be copied into a new repository: **Finco2**. At that point `Finco1` enters full archive state and `Finco1-RC2` becomes its permanent recorded baseline.

See `docs/FINCO_V2_CONTROLLED_EXTRACTION_PLAN.md` and `docs/EXTRACTION_STRATEGY_UPDATE.md` for the full extraction timeline.

---

## Relationship to Finco2

`Finco2` is not created at RC2 freeze time.

`Finco2` will be created only after:

1. Engine extraction is complete (within Finco1)
2. Parity is reproduced against RC2 baselines
3. Architecture is stabilised
4. Migration is validated

Only then will the extracted code be copied into a clean repository. The `Finco2` repository will not inherit the Finco1 shell, legacy phase tests, generated reports, or identity-dispatch patterns.

When `Finco2` is created, `Finco1` is archived. `Finco1-RC2` remains permanently accessible as the frozen audit reference.

---

*Do not modify this document or the `Finco1-RC2` branch without engineering review.*
