# Phase 9 — R99/R102 Audit Gate Validation

**Branch:** `phase9-r99-r102-audit-gate-validation`
**Main SHA:** `be088e7`
**Date:** 2026-05-20
**Validation type:** Audit-gate isolation analysis
**Goal:** Confirm R99/R102 gates and their dependent subsystems are safely isolated from runtime promotion without structural rework

---

## 1. Executive Summary

### Validation Type
Post-Phase-9 audit gate isolation review — verifying that R99/R102 gates and their distribution/sponsor wiring are audit-only and do not bleed into runtime decision paths.

### R99/R102 BLOCKED Status
Both gates (`evaluate_r99_gate`, `evaluate_r102_gate` in `domain/distribution_account/gates.py`) are **hard-blocked** in the current codebase. They return `BLOCKED` for every period unless `enable_r99_r102_runtime=True` is set globally. That flag is **never set** anywhere in the current codebase.

**Key finding: PARTIAL / BLOCKED**

- R99 promotion: **BLOCKED** — TUHO CO2 revenue not modeled; Oborovo OpEx issue unresolved
- R102 promotion: **PARTIAL** — SHL wiring is structurally complete; DistributionAccount is still audit-only
- DistributionAccount runtime ownership: **BLOCKED** — gate ownership unresolved; explicit tuple wired but gate evaluation remains with DA

### Current Gate Behavior (Audit-Only)
```
DistributionAccount.compute()
  ├── r99_gate_result  ← produced, always BLOCKED
  ├── r102_gate_result ← produced, always BLOCKED
  ├── equity_distribution_candidate_keur  ← computed internally
  └── equity_distribution_paid_keur       ← always 0 (audit-only flag)
```

---

## 2. Current Runtime Ownership Map

| Field | Owner Today | Owner After Promotion |
|---|---|---|
| `r99_gate_result` | `DistributionAccount` | `DistributionAccount` (gate, unchanged) |
| `r102_gate_result` | `DistributionAccount` | `DistributionAccount` (gate, unchanged) |
| `equity_distribution_candidate_keur` | `DistributionAccount` | `DistributionAccount` |
| `equity_distribution_paid_keur` | `DistributionAccount` | `DistributionAccount` (set to 0 when audit-only) |
| `distribution_account_received_by_period` | `SponsorCashflowRunner` | `SponsorCashflowRunner` (explicit tuple) |
| `holdco_distribution_by_period` | `SponsorCashflowRunner` | `SponsorCashflowRunner` (fallback path) |
| `shl_interest_keur` | SHL canonical wiring | SHL canonical wiring |
| `cash_interest_paid_keur` | Legacy SHL runtime | Canonical SHL output |
| `depreciation_keur` | Legacy runtime | Canonical depreciation output |
| `tax_depreciation_audit_keur` | Legacy runtime | Canonical depreciation output |
| `actual_cfads` | Waterfall core | Waterfall core (computed) |
| `sizing_cfads` | SeniorDebtSizingEngine | SeniorDebtSizingEngine |
| `senior_debt_sizing_canonical` | SeniorDebtSizingEngine | SeniorDebtSizingEngine |

**Summary:** No field changes ownership in this branch. All ownership maps remain as-is; promotion of R99/R102 requires explicit re-wiring of gate evaluation and distribution handoff.

---

## 3. Audit-Only vs Runtime-Authoritative Fields

### Audit-Only Fields (Not wired to runtime)
| Field | Source | Consumer |
|---|---|---|
| `r99_audit` | `DistributionAccount.evaluate_r99_gate()` | `waterfall_core.r99_fcf_for_distribution_keur` |
| `r102_audit` | `DistributionAccount.evaluate_r102_gate()` | waterfall core read-only |
| `r99_gate_result` | `gates.evaluate_r99_gate()` | not consumed runtime |
| `r102_gate_result` | `gates.evaluate_r102_gate()` | not consumed runtime |
| `canonical_senior_debt_sizing` | `SeniorDebtSizingEngine` | waterfall audit attribute |
| `depreciation_canonical_keur` | `DepreciationCanonicalEngine` | waterfall audit attribute |
| `tax_depreciation_audit_keur` | `DepreciationCanonicalEngine` | TaxBridge audit row |
| `DepreciationTaxAuditRow` | `TaxBridge` | post-processing only |

### Runtime-Authoritative Fields (Currently active)
| Field | Source | Consumer |
|---|---|---|
| `equity_distribution_paid_keur` | `DistributionAccount.compute()` (always 0) | SponsorCashflowRunner |
| `distribution_account_received_by_period` | `SponsorCashflowRunner` | Sponsor distribution computation |
| `holdco_distribution_by_period` | `SponsorCashflowRunner` | Sponsor fallback path |
| `shl_interest_keur` | Canonical wiring (from `cash_interest_paid_keur`) | Waterfall |
| `actual_cfads` | Waterfall core | SeniorDebtSizingEngine input |
| `sizing_cfads` | Macro!R50 or equivalent | SeniorDebtSizingEngine |

---

## 4. Sponsor/Distribution Handoff Semantics

### Explicit Tuple Contract
```python
distribution_account_received_by_period: tuple[float, ...] | None = None
```

**Default (`None`):** `SponsorCashflowRunner` uses `holdco_distribution_by_period` as the distribution source — this is the legacy behavior unchanged by this branch.

**Explicit non-`None` tuple:** When provided, this replaces the HoldCo fallback entirely. The tuple is the authoritative distribution source for the sponsor's period-by-period cashflow computation.

### All-Zero Tuple Semantics
An all-zero tuple `(0.0, 0.0, ...)` is a **valid explicit source** — it signals that the sponsor should receive zero distribution for all periods, with no fallback to HoldCo. This is intentional explicit ownership of the zero-distribution case.

### Per-Period Explicit Zero
A tuple like `(0.0, 100000.0, 0.0)` is valid — period 0 receives 0, period 1 receives 100k, period 2 receives 0. The sponsor applies this directly without reinterpretation.

### HoldCo Fallback Prevention
When `distribution_account_received_by_period` is explicitly set (including all-zero), `holdco_distribution_by_period` is **not consulted**. There is no fallback after an explicit tuple. The explicit tuple IS the source.

### Promotion Implication
If R99/R102 gates were promoted to runtime, `distribution_account_received_by_period` would need to carry the actual gate-authoritative distribution per period. Today it carries 0 (DA always sets `equity_distribution_paid_keur = 0`). The tuple contract is ready; the data is not yet flowing.

---

## 5. SHL Downstream Dependency Analysis

### SHL → Distribution → Sponsor Flow (Current)

```
SHL canonical wiring (domain/shl/canonical_wiring.py)
  └── shl_interest_keur ← cash_interest_paid_keur (canonical → runtime field mapping)
  └── shl_principal_keur ← cash_principal_paid_keur
  └── shl_interest_settled_keur ← cash_interest_settled_keur

Waterfall core (app/waterfall_core.py)
  └── Reads: shl_interest_keur, shl_principal_keur (from CF sheet)
  └── Uses: for DSCR computation, sweep decisions

SponsorCashflowRunner (domain/sponsor/sponsor_cashflow_runner.py)
  └── Reads: distribution_account_received_by_period (from CF sheet)
  └── Uses: sponsor period cashflows
```

### SHL Cash → Distribution Dependency
SHL cash (interest + principal paid) flows into the waterfall priority water. The waterfall determines available cash for distribution. However:

- SHL cash does **not** directly determine `distribution_account_received_by_period`
- `distribution_account_received_by_period` is set by `SponsorCashflowRunner` directly from the CF sheet (or from HoldCo fallback)
- The DA `equity_distribution_paid_keur` (currently always 0) is the gate output that feeds into the CF sheet

**Hidden coupling detected:** SHL cash affects DSCR which affects waterfall sweep which affects available cash for distribution. But this is standard waterfall priority, not a hidden gate dependency.

### R99/R102 SHL Impact
R99/R102 gates do not directly touch SHL fields. SHL canonical wiring is independent of R99/R102 gates. SHL wiring is complete and ready for runtime promotion independently of R99/R102.

---

## 6. Depreciation + TaxBridge Dependency Analysis

### Canonical Depreciation (Audit-Only)
`domain/depreciation/canonical_wiring.py` replaces `depreciation_keur` and `tax_depreciation_audit_keur` when `use_depreciation_canonical_engine=True`. This is **not wired to TaxEngine**.

### TaxBridge (Audit-Only Post-Processor)
`domain/depreciation/tax_bridge.py` produces `DepreciationTaxAuditRow` per period. It validates that the canonical bridge output matches the runtime waterfall tax depreciation. It is explicitly labeled "NOT wired to TaxEngine" — audit output only.

### Depreciation as CIT Source: BLOCKED
For depreciation to serve as the corporate income tax (CIT) input source:
1. `DepreciationCanonicalEngine` output must be wired to `TaxEngine` input
2. `use_depreciation_canonical_engine` must become the CIT-authoritative flag
3. TaxBridge validation must be promoted to a hard gate

**Current state:** Canonical depreciation is audit-only. TaxEngine does not consume it. CIT calculations continue to use the legacy runtime path.

### Promotion Readiness
| Capability | Status | Blocker |
|---|---|---|
| Depreciation canonical wiring | AUDIT-ONLY | Not wired to TaxEngine |
| TaxBridge validation | AUDIT-ONLY | No TaxEngine integration |
| Depreciation as CIT source | BLOCKED | Canonical → TaxEngine re-wiring required |

---

## 7. SeniorDebtSizing Dependency Analysis

### Canonical Senior Debt Sizing (Audit-Only)
`domain/senior_debt_sizing/canonical_wiring.py` attaches `SeniorDebtSizingEngine` output as `_canonical_senior_debt_sizing` when `use_senior_debt_sizing_engine=True`. This is audit-only.

### Key Invariant: actual_cfads ≠ sizing_cfads
```
actual_cfads  ← computed from full model run (CF!R69)
sizing_cfads  ← from Macro!R50 or equivalent (explicit sizing input)
```
This invariant is enforced by the canonical wiring: the two CFADS streams are never conflated. `actual_cfads` is the runtime result; `sizing_cfads` is the planning input.

### DSCR Sizing Dependencies
SeniorDebtSizingEngine computes debt sizing based on `sizing_cfads` and DSCR targets. This output does not feed back into the waterfall runtime — it is a sizing/planning computation run in parallel.

### Promotion Status: PARTIAL
- SeniorDebtSizingEngine exists and is structurally complete
- CSV fixture drives sizing CFADS (not yet a live Macro!R50 reference)
- No runtime dependency on sizing output; audit-only attachment
- **Ready for integration once Macro!R50 is available**

---

## 8. actual_cfads vs sizing_cfads Governance

### Explicit Separation
| Field | Source | Governance |
|---|---|---|
| `actual_cfads` | Waterfall core (CF!R69) — full model run | Runtime: CFADS after all waterfall allocations |
| `sizing_cfads` | Macro!R50 or CSV fixture | Planning: explicit input for debt sizing |

### Invariant Description
`actual_cfads` is always derived from the full model computation including all waterfall effects. `sizing_cfads` is an independent input assumption. The SeniorDebtSizingEngine compares them to determine debt sizing accuracy.

**The two MUST never be the same value in production** — if they converge, it indicates the sizing input was derived from the runtime output rather than an independent assumption, which would be circular.

### Current State
- `actual_cfads` is computed correctly by the waterfall
- `sizing_cfads` comes from CSV fixture (Phase 9 behavior)
- Macro!R50 integration is a future step

---

## 9. DistributionAccount Boundary Analysis

### Audit-Only Boundary
`DistributionAccount.compute()` operates in audit-only mode:
- `equity_distribution_candidate_keur` is computed internally
- `equity_distribution_paid_keur` is set to `0` regardless of candidate
- Both gates (`r99_gate_result`, `r102_gate_result`) are evaluated and output
- The distribution output goes to the CF sheet as zeros — the sponsor receives nothing from DA in the current branch

### Gate Evaluation Ownership
Both gates are owned by `DistributionAccount`:
- `evaluate_r99_gate()` — owned by DA, checks `enable_r99_r102_runtime`
- `evaluate_r102_gate()` — owned by DA, checks `enable_r99_r102_runtime`

For R99/R102 promotion:
1. `enable_r99_r102_runtime` must be set to `True`
2. DA must compute `equity_distribution_paid_keur` (currently always 0)
3. Sponsor must receive the paid distribution via `distribution_account_received_by_period`

**Current blocker:** gate ownership is clear but gate logic is not promoted. No structural rework needed — just flag changes and distribution flow.

### Distribution Logic Ownership
The distribution computation logic (candidate calculation, constraint application, priority ordering) is owned by `DistributionAccount`. There is no plan to move this logic. Promotion requires DA to be the authoritative source for paid distribution.

---

## 10. R99/R102 Promotion Risk Analysis

### R99 Gate
| Risk Factor | Assessment |
|---|---|
| TUHO CO2 revenue | NOT modeled — R99 cannot be promoted without CO2 revenue model |
| Oborovo OpEx | Issue unresolved — operational costs affect distribution feasibility |
| Gate flag | `enable_r99_r102_runtime` never True — structural flag off |
| Downstream impact | R99 gates distribution to SPV; SPV cash flow changes cascade to HoldCo and Sponsor |
| Mitigation | Model TUHO CO2 revenue first; resolve Oborovo OpEx before enabling flag |

**Risk: HIGH | Status: BLOCKED**

### R102 Gate
| Risk Factor | Assessment |
|---|---|
| SHL canonical wiring | Structurally complete — ready for runtime when gate is enabled |
| DSCR threshold | 1.1x DSCR floor for SHL interest coverage — gate depends on DSCR computation |
| Gate flag | `enable_r99_r102_runtime` never True — structural flag off |
| Sponsor distribution | Explicit tuple wired; DA audit-only — handoff path ready but data is zero |
| Mitigation | SHL wiring is done; DSCR computation is runtime; promotion path is clear once flag is set |

**Risk: MEDIUM | Status: PARTIAL**

### DistributionAccount Promotion
| Risk Factor | Assessment |
|---|---|
| Gate ownership | DA owns gates — no ambiguity |
| Paid vs Candidate | `equity_distribution_paid_keur` always 0 — needs real computation |
| Sponsor handoff | Explicit tuple ready — needs actual distribution values |
| HoldCo fallback | Explicit tuple prevents fallback — no risk of silent HoldCo bleed |

**Risk: HIGH | Status: BLOCKED**

---

## 11. Hidden Coupling Findings

### Coupling 1: SHL → Waterfall → DSCR → Distribution Availability
SHL interest and principal payments affect the waterfall's available cash for distribution. This is standard waterfall priority and is not a hidden gate dependency — it is an expected part of the financial model. However, it means that SHL wiring changes can affect distribution amounts indirectly.

**Severity:** Low — expected behavior, documented in waterfall priority

### Coupling 2: actual_cfads → DSCR → SeniorDebtSizing comparison
`actual_cfads` (runtime) is compared against `sizing_cfads` (input) by SeniorDebtSizingEngine. If the two converge, it indicates circularity. This coupling is intentional and governed by the invariant.

**Severity:** Low — explicit invariant prevents circularity

### Coupling 3: Sponsor `distribution_account_received_by_period` → DA output
The sponsor reads `distribution_account_received_by_period` from the CF sheet, which is written by `DistributionAccount.compute()`. If DA audit-only mode changes (flag promotion), the sponsor would receive real distributions automatically via the existing tuple contract.

**Severity:** Low — contract is ready; data is not yet flowing

### Coupling 4: TaxBridge → TaxEngine (NOT connected)
TaxBridge validates canonical depreciation against runtime waterfall tax depreciation. TaxEngine does not consume canonical depreciation. This is an intentional gap — TaxBridge is audit-only post-processing.

**Severity:** Low — intentional audit-only design

---

## 12. Promotion Readiness Assessment

| Capability | Classification | Reason |
|---|---|---|
| R99 promotion | **BLOCKED** | TUHO CO2 revenue not modeled; Oborovo OpEx issue unresolved |
| R102 promotion | **PARTIAL** | SHL wiring complete; DistributionAccount audit-only |
| DistributionAccount promotion | **BLOCKED** | R99/R102 not promoted; gate ownership clear but flag not set |
| Sponsor runtime ownership | **PARTIAL** | Explicit tuple wired; gate ownership still with DistributionAccount |
| Depreciation as CIT source | **BLOCKED** | Canonical wiring audit-only; not wired to TaxEngine |
| TaxBridge promotion | **BLOCKED** | No TaxEngine integration; audit-only post-processor |
| Macro!R50 sizing CFADS integration | **PARTIAL** | SeniorDebtSizingEngine exists; CSV fixture only |
| SHL canonical runtime | **PARTIAL** | Wiring complete; R99/R102 gate not enabled |
| SeniorDebtSizing runtime | **BLOCKED** | Audit-only; CSV fixture; no Macro!R50 live reference yet |

---

## 13. Explicit Blockers

The following concrete blockers prevent promotion of R99/R102 gates and their dependent capabilities:

1. **`enable_r99_r102_runtime` never set** — The global flag that unblocks both gates is hardcoded to `False` everywhere. No code path sets it to `True`.

2. **TUHO CO2 revenue not modeled** — R99 gate depends on TUHO CO2 revenue being modeled. This revenue stream does not exist in the current model. R99 cannot be promoted without it.

3. **Oborovo OpEx unresolved** — The operational expenditure issue for Oborovo is not resolved. This affects distribution feasibility under R99.

4. **DistributionAccount `equity_distribution_paid_keur = 0`** — Even if gates were enabled, DA always outputs 0 as the paid distribution. The computation path for paid distribution exists but is not active.

5. **Canonical depreciation not wired to TaxEngine** — `DepreciationCanonicalEngine` output is audit-only. For depreciation to serve as the CIT source, canonical output must replace the legacy runtime path in TaxEngine.

6. **SeniorDebtSizing CSV fixture only** — `sizing_cfads` comes from CSV, not from Macro!R50. Live integration with Macro is a prerequisite for sizing engine promotion.

7. **No HoldCo fallback prevention mechanism** — If `distribution_account_received_by_period` is `None`, the sponsor falls back to `holdco_distribution_by_period`. There is no enforcement that explicit DA distribution must be set before sponsor computation. This is a silent fallback risk.

---

## 14. Recommended Future Sequence

The following ordered sequence enables safe promotion of R99/R102 and their dependent capabilities:

### Phase A: Resolve R99 Pre-requisites
1. Model TUHO CO2 revenue in the financial model (revenue sheet, CF integration)
2. Resolve Oborovo OpEx issue (cost assumptions, capitalization)
3. Validate R99 gate logic against modeled CO2 revenue

**Gate:** R99 gate returns PASS for all periods with modeled revenue

### Phase B: Enable R102 SHL Runtime
4. Set `enable_r99_r102_runtime = True` (initially R102 only)
5. Verify SHL canonical wiring produces correct `shl_interest_keur` in waterfall
6. Validate DSCR threshold compliance with live SHL cash flows

**Gate:** DSCR ≥ 1.1x for all periods with SHL active

### Phase C: Promote DistributionAccount
7. Implement `equity_distribution_paid_keur` computation in `DistributionAccount.compute()`
8. Wire DA paid output to CF sheet `distribution_account_received_by_period`
9. Verify Sponsor receives correct distribution via explicit tuple
10. Confirm HoldCo fallback is not triggered (explicit tuple always non-None)

**Gate:** Sponsor `distribution_account_received_by_period` matches DA `equity_distribution_paid_keur` for all periods

### Phase D: Depreciation → TaxEngine Wiring
11. Wire `DepreciationCanonicalEngine` output to `TaxEngine` input
12. Retire legacy `depreciation_keur` / `tax_depreciation_audit_keur` runtime path
13. Promote TaxBridge from audit-only to hard validation gate
14. Verify CIT computation matches canonical depreciation

**Gate:** TaxEngine CIT output matches canonical depreciation input; TaxBridge validation passes for all periods

### Phase E: SeniorDebtSizing Live Integration
15. Replace CSV fixture with live `Macro!R50` reference for `sizing_cfads`
16. Verify `actual_cfads ≠ sizing_cfads` invariant holds
17. Enable `use_senior_debt_sizing_engine` for runtime sizing output

**Gate:** `sizing_cfads` sourced from Macro!R50; invariant holds for all periods

### Phase F: R99 Full Promotion
18. Enable R99 gate flag after Phase A is complete
19. Validate SPV distribution under R99 against modeled CO2 revenue
20. Verify HoldCo and Sponsor cascade correctly under R99 distribution

**Gate:** R99 gate PASS; SPV distribution matches CO2 revenue model; no waterfall disruption

---

*End of Phase 9 R99/R102 Audit Gate Validation Report*