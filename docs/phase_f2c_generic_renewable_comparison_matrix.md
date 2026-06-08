# Phase F2-C — Generic Renewable Comparison Matrix

> Type: docs-only, design-only
> Branch: `phase-f2c-generic-renewable-comparison-matrix`
> Base SHA: `eb3c20cdfe9c8c66f683cc43fb4bf3ac0fb7ef4d` (post-F2-B)
> Status: DRAFT, do not mark ready, do not merge
> Scope: consolidated comparison matrix + critical-path analysis
> Hard boundary: **Generic Wind, Generic Solar, TUHO, Oborovo all unchanged**.

## 0. Purpose

F2-A covered Generic Wind. F2-B covered Generic Solar. Both
concluded **NOT READY** with a 39/100 combined readiness score
each. F2-C consolidates the two inventories into a single
decision-making document and answers the next question:

> "What is the shortest path from today's Generic templates to future Reference status?"

F2-C is **not** a validation pack design. F2-C is a **comparison
+ critical-path analysis**. The actual Reference work for
Generic Wind and Generic Solar belongs to later F2-D / F2-E /
F2-F phases, each of which will be scoped in its own follow-up
prompt.

F2-C does **not** promote any project, does **not** modify any
code, and does **not** start any implementation work.

## 1. Side-by-Side Matrix: Generic Wind vs Generic Solar

F2-C compares Generic Wind and Generic Solar across the 13
areas listed in the F2-C brief. The status is **READY** /
**PARTIAL** / **MISSING** for each area, with the source of
evidence.

### 1.1 Dependency areas (12)

| # | Area | Generic Wind (F2-A) | Generic Solar (F2-B) | Delta |
|---|---|---|---|---|
| 1 | CAPEX | PARTIAL (4 named items; 13 placeholders; ~30k kEUR indicative) | PARTIAL (5 named items; 12 placeholders; ~30k kEUR indicative) | Solar has 1 extra named item (Inverters); both minimal |
| 2 | Revenue | PARTIAL (PPA 60, balancing 8, market synthetic, CO2 enabled in factory) | PARTIAL (PPA 55, market synthetic, CO2 disabled) | Wind has balancing cost line; Solar does not; Wind has CO2 discrepancy (factory True vs Phase 34 False) |
| 3 | Production | PARTIAL (P50 3000h, P90 2700h, no degradation) | PARTIAL (P50 1500h, P90 1400h, 0.4% degradation) | Solar has PV degradation; Wind does not |
| 4 | OPEX | PARTIAL (4 items; ~550 kEUR Y1) | PARTIAL (4 items; ~380 kEUR Y1) | Wind OPEX ~45% higher; both minimal |
| 5 | Senior Debt | PARTIAL (DSCR_SCULPT, no frozen path) | PARTIAL (DSCR_SCULPT, no frozen path) | Identical |
| 6 | SHL | PARTIAL (6,000 kEUR factory / 5,000 Phase 34 — discrepancy) | PARTIAL (5,000 kEUR consistent) | Wind has data discrepancy; Solar does not |
| 7 | Tax | PARTIAL (25% corporate, 5y carryforward, ATAD) | PARTIAL (25% corporate, 5y carryforward, ATAD) | Identical |
| 8 | Sponsor | MISSING | MISSING | Identical gap |
| 9 | Construction | PARTIAL (18 months, no per-period cost) | PARTIAL (12 months, no per-period cost) | Wind longer construction; both lack per-period cost |
| 10 | Depreciation | MISSING (no Generic-Wind-specific depreciation; D1/D2 redo/D3 redo arc covers TUHO/Oborovo only) | MISSING (no Generic-Solar-specific depreciation; same arc) | Identical gap; both flagged in `app/depreciation_flag_discipline.py:24` as default-False |
| 11 | Exports | PARTIAL (Generic Solar/Wind fallback in `app/excel_export.py:413-417`; shared) | PARTIAL (same fallback) | Identical (shared) |
| 12 | Audit sheets | PARTIAL (UI warning present; pilot_rc_scope_matrix present; no per-project D1/D2 redo/D3 redo row) | PARTIAL (same) | Identical (shared) |
| **Subtotal** | | **0 READY, 10 PARTIAL, 2 MISSING** | **0 READY, 10 PARTIAL, 2 MISSING** | **Identical** |

### 1.2 Test coverage

| # | Area | Generic Wind (F2-A) | Generic Solar (F2-B) | Delta |
|---|---|---|---|---|
| 13 | Tests | 18 test files reference Generic Wind incidentally; 0 dedicated | 8+ test files reference Generic Solar incidentally; 0 dedicated | Wind has 10+ more test references; both have no dedicated pack |

### 1.3 Governance

| # | Area | Generic Wind (F2-A) | Generic Solar (F2-B) | Delta |
|---|---|---|---|---|
| (13) | Governance | PARTIAL 87/100 (pilot scope exclusion + UI warning + Phase 34 doc + D1/D2 redo discipline) | PARTIAL 87/100 (same) | Identical |

### 1.4 Matrix summary

- **Generic Wind:** 0 READY / 11 PARTIAL / 2 MISSING (12 dependency areas) + 18 incidental test refs + 87/100 governance
- **Generic Solar:** 0 READY / 11 PARTIAL / 2 MISSING (12 dependency areas) + 8+ incidental test refs + 87/100 governance

**Generic Wind and Generic Solar have identical READY / PARTIAL
/ MISSING counts** across the 12 dependency areas and the same
87/100 governance score. The only meaningful delta is **test
coverage** (Wind 18, Solar 8+).

## 2. Gap Comparison

F2-C classifies gaps into three buckets: shared, Wind-only,
Solar-only.

### 2.1 Shared gaps (both projects)

These gaps apply to **both** Generic Wind and Generic Solar:

1. **No Excel reference workbook.** Blocking for parity.
2. **No parity computation.** Depends on (1).
3. **No `KNOWN_LIMITATIONS.md`.** Independent of (1) and (2).
4. **No dedicated test pack.** Independent of (1) and (2).
5. **No per-project D1/D2 redo/D3 redo audit posture.** Doc gap.
6. **Sponsor modeling MISSING.** No sponsor-specific fields in
   either factory. Modeling gap.
7. **Depreciation MISSING.** No Generic-specific depreciation;
   D1-D3 arc covers TUHO/Oborovo only. Doc + modeling gap.
8. **Live sculpting without a frozen-path validation.** Both
   use `DSCR_SCULPT`; neither has a frozen-path reference.
9. **Synthetic market price curve.** Both use linear synthetic
   curves; unbounded revenue-parity delta.
10. **No validation pack directory** at `docs/validation/<project>/`.
11. **No `excel_reference/`, `parity/`, `test_pack/`,
    `golden_dataset/`, `reviewer_signoff/` subdirs** for either
    project.
12. **No Phase 51F parity green** for either project (parity
    workflow only covers TUHO/Oborovo).
13. **Generic wind/solar inherits TUHO/Oborovo parity guardrails
    by accident** risk (CI / governance risk).

**Count: 13 shared gaps.**

### 2.2 Wind-only gaps

These gaps apply **only** to Generic Wind:

1. **Three data discrepancies (factory vs Phase 34 doc):**
   - PPA tariff: factory 60 EUR/MWh vs Phase 34 doc 55 EUR/MWh
   - CO2 enabled: factory `True` vs Phase 34 doc `False`
   - SHL amount: factory 6,000 kEUR vs Phase 34 doc 5,000 kEUR
2. **No Wind CO2 treatment decision.** CO2 status is
   contradictory between factory and doc; no resolution.
3. **Balancing cost line.** Wind factory has a balancing cost
   line (8 EUR/MWh); this is Wind-specific. The Phase 34 doc
   does not validate this value.
4. **OPEX coverage is higher** (~550 kEUR Y1 vs Solar's ~380
   kEUR Y1). Higher is not necessarily worse, but the
   4-item-vs-12-15-item comparison (vs TUHO/Oborovo) is the
   relevant one, and the gap to TUHO is the same for both
   Generics.

**Count: 4 Wind-only gaps.** (Discrepancies + Wind-specific
data points not validated.)

### 2.3 Solar-only gaps

These gaps apply **only** to Generic Solar:

1. **PV degradation handling.** Solar factory has
   `pv_degradation=0.004` (0.4% / year); the legacy depreciation
   module does not handle PV degradation natively; no shadow
   validation exists for Generic Solar.
2. **CAPEX asset class distribution.** Solar factory uses
   `asset_class=SOLAR_PANELS` for Modules + Inverters,
   `asset_class=CIVIL_GRID` for Civil + Grid, and
   `asset_class=SOFT_COSTS` for Soft. A real Excel reference
   may have a different asset-class scheme; this affects
   depreciation mapping.
3. **Zero data discrepancies** (positive finding; Solar is
   internally consistent).
4. **Test coverage is lower** (8+ files vs Wind's 18). This is
   not a "gap" in the sense of missing evidence per se, but it
   is a Solar-only "lower coverage" finding.

**Count: 2 Solar-only real gaps** (PV degradation + asset class).
(The "zero discrepancies" and "lower test coverage" findings are
**not** gaps; they are observations.)

### 2.4 Gap ranking by blocking-ness

| Rank | Gap | Shared / Wind-only / Solar-only | Blocks |
|---|---|---|---|
| 1 | No Excel reference workbook | shared | all parity |
| 2 | No parity computation | shared | Phase 51F integration |
| 3 | Wind data discrepancies (PPA, CO2, SHL) | Wind-only | parity fidelity |
| 4 | No `KNOWN_LIMITATIONS.md` | shared | F1 §3.3 criterion 4 |
| 5 | No dedicated test pack | shared | F1 §3.3 criterion 5 |
| 6 | Per-project D1/D2 redo/D3 redo audit posture | shared | F1 §3.3 criterion 6 |
| 7 | Depreciation MISSING | shared | F1 §3.3 criterion 6 (audit posture) |
| 8 | Sponsor modeling MISSING | shared | modeling completeness |
| 9 | Live sculpting frozen-path validation | shared | parity fidelity |
| 10 | Synthetic market price curve | shared | revenue parity |
| 11 | PV degradation handling | Solar-only | revenue parity for Solar |
| 12 | CAPEX asset class distribution | Solar-only | parity + depreciation mapping for Solar |
| 13 | Wind balancing cost treatment | Wind-only | parity fidelity for Wind |
| 14 | Lower test coverage on Solar | Solar-only | F1 §3.3 criterion 5 (Solar side) |

## 3. Reference Comparison: Generics vs TUHO / Oborovo

F2-C compares both Generic projects against their Reference
counterparts (TUHO Wind, Oborovo Solar) to identify what
already exists in the Reference path that the Generics would
need to mirror.

### 3.1 What Reference projects have that Generics don't

| Capability | TUHO Wind | Oborovo Solar | Generic Wind | Generic Solar |
|---|---|---|---|---|
| **Excel reference workbook** | ✅ Pinned (`tuho_excel_1.xlsm`) | ✅ Pinned (`excel_oborovo.xlsx`) | ❌ MISSING | ❌ MISSING |
| **Parity extraction CSV** | ✅ `phase7_tuho_senior_debt_sizing_extraction.csv` | ✅ `phase23q_oborovo_senior_debt_sizing_extraction.csv` | ❌ MISSING | ❌ MISSING |
| **Golden dataset** | ✅ `tests/golden/fixtures/tuho_golden.py` | ✅ `tests/golden/fixtures/oborovo_golden.py` | ❌ MISSING | ❌ MISSING |
| **Frozen senior debt schedule** | ✅ Frozen-path validated (Phase 23 series) | ✅ Frozen-path validated (Phase 31 series) | ❌ MISSING (DSCR_SCULPT only) | ❌ MISSING (DSCR_SCULPT only) |
| **Phase 51F parity green** | ✅ Green (covered by `.github/workflows/parity_guardrails.yml`) | ✅ Green (same) | ❌ MISSING (not in workflow scope) | ❌ MISSING (not in workflow scope) |
| **D1 audit sheet per-project row** | ✅ Per-project row | ✅ Per-project row | ❌ MISSING (generic-project row only) | ❌ MISSING (generic-project row only) |
| **D2 redo discipline per-project row** | ✅ Per-project row | ✅ Per-project row | ❌ MISSING (module docstring only) | ❌ MISSING (module docstring only) |
| **D3 redo shadow validation** | ✅ Done (Phase D3 redo) | ✅ Done (Phase D3 redo) | ❌ MISSING | ❌ MISSING |
| **OPEX line items** | 12 items (Y1 ~1,998 kEUR) | 15 items (Y1 ~1,338 kEUR) | 4 items (~550 kEUR Y1) | 4 items (~380 kEUR Y1) |
| **CAPEX line items** | turbine + civil + grid + soft + IDC + fees (6 named + construction period) | similar (modules + inverters + civil + grid + soft + IDC + fees + 12 placeholders) | 4 named items (turbines + civil + grid + soft) | 5 named items (modules + inverters + civil + grid + soft) |
| **CO2 treatment** | ✅ Calibrated (Y1 ~611 kEUR, declining ~10%/year) | n/a (Solar) | ⚠️ Enabled in factory, disabled in Phase 34 doc — discrepancy | n/a (CO2 disabled) |
| **Live sculpting vs frozen path** | Frozen-path validated; live sculpting excluded from Pilot RC | Frozen-path validated; live sculpting excluded from Pilot RC | DSCR_SCULPT only; no frozen-path reference | DSCR_SCULPT only; no frozen-path reference |
| **Test file coverage** | 310 files | 243 files | 18 files | 8+ files |
| **PPA tariff** | TUHO-Excel calibrated | Oborovo-Excel calibrated | factory 60, doc 55 (discrepancy) | factory 55 (consistent) |
| **PPA term** | 12 years (TUHO) | 12 years (Oborovo) | 12 years | 10 years |
| **`KNOWN_LIMITATIONS.md`** | implicit in pilot scope matrix; not a separate file | implicit in pilot scope matrix; not a separate file | ❌ MISSING | ❌ MISSING |
| **Dedicated test pack** | ✅ Yes (Phase 23/29 series) | ✅ Yes (Phase 31 series) | ❌ MISSING | ❌ MISSING |
| **Pilot RC scope matrix entry** | ✅ Included / Validated | ✅ Included / Validated | ✅ Excluded / Unvalidated (correct posture) | ✅ Excluded / Unvalidated (correct posture) |

### 3.2 What Generic projects have that Reference projects don't (positive findings)

| Capability | Generic Wind / Solar | TUHO / Oborovo |
|---|---|---|
| **Live sculpting (`DSCR_SCULPT`)** | ✅ Enabled by default | ❌ Excluded from Pilot RC (frozen path only) |
| **User-facing warning label** | "⚠️ Unvalidated · Derived path" | implicit in scope matrix |
| **Pilot RC scope matrix exclusion** | ✅ Explicitly excluded | ✅ Explicitly included |
| **Phase 34 boundary doc** | ✅ Generic path validation boundary | n/a |

### 3.3 Generics-vs-Reference gap delta

| Capability | Wind gap (TUHO − Wind) | Solar gap (Oborovo − Solar) |
|---|---|---|
| Excel reference workbook | 1 (large) | 1 (large) |
| Parity pack (CSV + JSON) | 2 (medium each) | 2 (medium each) |
| Golden dataset | 1 (medium) | 1 (medium) |
| Frozen senior debt schedule | 1 (large) | 1 (large) |
| Phase 51F parity green | 1 (small) | 1 (small) |
| D1/D2 redo/D3 redo per-project | 3 (small each) | 3 (small each) |
| OPEX line items | 8 missing | 11 missing |
| CAPEX line items | ~2-10 missing (depends on counting) | ~2-10 missing (depends on counting) |
| Test file coverage | 292 missing | 235 missing |
| `KNOWN_LIMITATIONS.md` | 1 (small) | 1 (small) |
| Dedicated test pack | 1 (large) | 1 (large) |
| **Total gap magnitude** | **~10 large, ~2 medium, ~300 small** | **~10 large, ~2 medium, ~240 small** |

**Both generics have similar gap magnitudes to their
Reference counterparts.** The dominant gaps are the
**Excel reference**, the **frozen senior debt schedule**, the
**parity pack**, and the **dedicated test pack**. These are
the same four gap categories for both Generics.

## 4. Critical Path Analysis

F2-C ranks blockers by impact. The "impact" is a qualitative
score: **HIGH** (blocks all Reference work), **MEDIUM**
(blocks specific criteria but not all), **LOW** (blocks
documentation only or minor).

| # | Blocker | Impact | Effort | Notes |
|---|---|---|---|---|
| 1 | Excel reference workbook | HIGH | HIGH | Blocks all parity. Requires either an acquired reference workbook or a synthetic one. |
| 2 | Parity computation | HIGH | MEDIUM | Depends on (1). Can be automated once reference is in place. |
| 3 | Frozen senior debt schedule | HIGH | MEDIUM | Required for live-sculpt-vs-frozen validation. Requires either frozen-path re-computation or a separate frozen-path fixture. |
| 4 | Dedicated test pack | HIGH | MEDIUM | Required for Phase 51F parity green. Includes parity tests, parameter-validation tests, audit-surface tests, export-shape tests, frozen-vs-derived tests. |
| 5 | `KNOWN_LIMITATIONS.md` | MEDIUM | LOW | Documentation. Required for F1 §3.3 criterion 4. |
| 6 | Per-project D1 audit sheet row | MEDIUM | LOW | Documentation. Required for F1 §3.3 criterion 6. |
| 7 | Per-project D2 redo discipline row | MEDIUM | LOW | Documentation. Required for F1 §3.3 criterion 6. |
| 8 | Per-project D3 redo shadow validation | MEDIUM | MEDIUM | Modeling + documentation. Optional but recommended. |
| 9 | Wind data discrepancies (3) | MEDIUM | LOW | Resolve by updating the Phase 34 doc to match the factory, or by justifying any deliberate divergence. |
| 10 | Sponsor modeling | MEDIUM | MEDIUM | F2-C does **not** recommend adding sponsor modeling to the Generics; this is a modeling-completeness concern, not a Reference criterion per se. |
| 11 | Depreciation handling for Generics | MEDIUM | MEDIUM | F2-C does **not** recommend extending the D1-D3 arc to Generics; this is a modeling-completeness concern, not a Reference criterion per se. |
| 12 | Phase 51F parity workflow scope | LOW | LOW | Add Generic Wind + Solar to `.github/workflows/parity_guardrails.yml`. Required for criterion 2. |
| 13 | Pilot RC scope matrix CI guard | LOW | LOW | Add a CI guard to prevent Generic Wind/Solar from being added to the Pilot RC scope by accident. |
| 14 | PV degradation handling (Solar) | MEDIUM | MEDIUM | Required only if parity shows a Solar-specific revenue delta due to degradation. |
| 15 | CAPEX asset class distribution (Solar) | LOW | LOW | Likely to be a documentation fix in the parity pack. |

### 4.1 High-impact blockers (must do first)

1. **Excel reference workbook** (item 1)
2. **Parity computation** (item 2)
3. **Frozen senior debt schedule** (item 3)
4. **Dedicated test pack** (item 4)

These four blockers dominate the critical path. Each Reference
migration (one for Wind, one for Solar) must address all four
before the project can be promoted to Level 2.

### 4.2 Medium-impact blockers (must do, but lower priority)

5. `KNOWN_LIMITATIONS.md` (item 5)
6. D1 / D2 redo / D3 redo per-project rows (items 6, 7, 8)
7. Wind data discrepancies (item 9)

### 4.3 Lower-impact blockers (do last, or do in parallel)

8. Sponsor modeling (item 10) — out of scope for Reference
   migration
9. Depreciation handling for Generics (item 11) — out of scope
10. Phase 51F parity workflow scope (item 12)
11. Pilot RC scope matrix CI guard (item 13)
12. PV degradation handling for Solar (item 14) — may be
    subsumed by (2)
13. CAPEX asset class distribution for Solar (item 15) — likely
    a documentation fix

## 5. Fastest Promotion Path

F2-C recommends the shortest path for **Generic Wind** and
the shortest path for **Generic Solar** to reach Level 2
(Reference). F2-C does **not** design the path; F2-C only
names the steps and the order.

### 5.1 Fastest path for Generic Wind (5 steps)

1. **Resolve the 3 data discrepancies** (PPA, CO2, SHL) by
   updating the Phase 34 doc to match the factory.
2. **Acquire/build the Excel reference workbook for Wind** and
   commit it under `docs/validation/generic_wind/excel_reference/`.
3. **Compute parity** between the FincoGPT Wind output and the
   Excel reference; commit `docs/validation/generic_wind/parity/`.
4. **Create the dedicated test pack** at
   `docs/validation/generic_wind/test_pack/`, including a
   frozen-vs-derived test.
5. **Create `KNOWN_LIMITATIONS.md`** and add per-project D1 / D2
   redo / D3 redo rows.

After step 5, run the F1 §10.1 promotion gate. If all criteria
are satisfied, promote to Level 2 (Reference).

**Total steps: 5.** Steps 1-3 are blockers (HIGH impact).
Steps 4-5 are documentation gaps (MEDIUM impact).

### 5.2 Fastest path for Generic Solar (4 steps)

1. **(No data discrepancies to resolve.)** Skip the discrepancy
   resolution step.
2. **Acquire/build the Excel reference workbook for Solar** and
   commit it under `docs/validation/generic_solar/excel_reference/`.
3. **Compute parity** between the FincoGPT Solar output and the
   Excel reference; commit `docs/validation/generic_solar/parity/`.
4. **Create the dedicated test pack** at
   `docs/validation/generic_solar/test_pack/`, including a
   frozen-vs-derived test, and create
   `docs/validation/generic_solar/KNOWN_LIMITATIONS.md` + D1 /
   D2 redo / D3 redo rows.

After step 4, run the F1 §10.1 promotion gate. If all criteria
are satisfied, promote to Level 2 (Reference).

**Total steps: 4.** All four steps are blockers (HIGH impact)
or documentation gaps (MEDIUM impact).

### 5.3 Why Solar is faster

Solar's path has one fewer step (4 vs 5) because the data
discrepancy resolution step is not required. Generic Solar is
**internally consistent** between the factory and the Phase 34
doc, so the first step (which is LOW-MEDIUM effort but
non-trivial) is skipped.

If the Generics are worked on in **parallel** (same Excel
reference acquisition effort, same parity methodology), the
total work is the same as either one in isolation, plus a
small overhead for the per-project pack directories.

### 5.4 Phase names

F2-C recommends the following **phase names** for the next
three to four F-phases. These are **suggestions only**; the
actual phase names will be set in the next F-phase prompt.

- **F2-D** (next for Wind, parallel for Solar): Excel reference
  acquisition + parity computation. For Wind, this includes the
  data discrepancy resolution step. For Solar, this is just the
  Excel reference + parity.
- **F2-E** (next for both): test pack + KNOWN_LIMITATIONS.md +
  D1/D2 redo/D3 redo rows.
- **F2-F** (next for both, after E): Phase 51F parity green
  + Pilot RC scope matrix CI guard.
- **F2-G** (separate, after F): promotion gate evaluation.
  F1 §10.1.

F2-C does **not** start F2-D, F2-E, F2-F, or F2-G.

## 6. Portfolio Recommendation

F2-C recommends one of three portfolio strategies:

- **A. Wind-first.** Migrate Generic Wind first; Solar later.
- **B. Solar-first.** Migrate Generic Solar first; Wind later.
- **C. Parallel.** Migrate both in parallel.

### 6.1 Recommendation: C — Parallel

**Rationale:**

1. **Both generics share 13 of the 15 gap categories.** The
   Excel reference acquisition, the parity computation, the
   test pack, and the `KNOWN_LIMITATIONS.md` are **the same
   effort** for both projects. A Wind-first approach would
   do the Excel reference + parity once for Wind, then do it
   again for Solar. A parallel approach does the Excel
   reference + parity once (with two outputs, one per project)
   and amortizes the methodology work.

2. **The Excel reference work dominates the critical path.**
   It is the HIGH-impact, HIGH-effort blocker (#1 in §4.1).
   Doing it in parallel halves the calendar time.

3. **The "data discrepancies" are Wind-only.** This is the
   one argument for Wind-first: Solar can skip the discrepancy
   step. But the discrepancy step is **LOW effort** (a doc
   update to match the factory), not HIGH. It does not
   justify a Wind-first approach.

4. **The test pack and `KNOWN_LIMITATIONS.md` are per-project.**
   These must be done twice regardless. But these are
   MEDIUM-impact, MEDIUM-effort blockers (§4.1 / §4.2), not
   the dominant cost.

5. **The D1 / D2 redo / D3 redo audit posture is per-project.**
   This must also be done twice. But these are LOW-MEDIUM
   effort.

6. **Governance risk: parallel approach prevents bias.** A
   Wind-first approach risks Solar being perpetually
   deprioritized ("we'll do Solar after Wind's promotion
   lands"). A parallel approach treats both generics with
   equal weight.

7. **Pilot RC scope matrix is symmetric.** Both Generics are
   excluded with the same wording
   (`docs/pilot_rc_scope_matrix.md:27-28`). The exclusion is
   already symmetric; the migration should also be symmetric.

### 6.2 Why not Wind-first (A)

- Wind has 3 data discrepancies to resolve (LOW-MEDIUM
  effort). This is the only "extra" work for Wind.
- Wind has 18 test files; Solar has 8+. So Wind has more
  surface area to migrate, but this is offset by the
  per-project nature of the test pack (must be done for each
  anyway).
- Wind's 3 discrepancies could be argued as a "Wind is closer
  to a real project, so it makes sense to migrate Wind first
  to validate the methodology." But this argument is
  speculative; the discrepancy count does not necessarily
  correlate with methodology validation.

### 6.3 Why not Solar-first (B)

- Solar has 0 data discrepancies to resolve. This is the only
  "fewer steps" argument for Solar.
- Solar has 8+ test files; Wind has 18. So Solar has less
  surface area to migrate, which is consistent with the
  "fewer steps" argument.
- Solar-first is symmetric to Wind-first; both are sequential.
  Neither is recommended over parallel.

### 6.4 Why parallel (C) is the strongest

- The dominant cost (Excel reference + parity) is shared
  between the two generics.
- The per-project costs (test pack, KNOWN_LIMITATIONS, D1/D2
  redo/D3 redo rows) are MEDIUM effort and can be done in
  parallel.
- The governance boundary is symmetric; the migration should
  be symmetric.
- Parallel is the lowest-risk approach: both generics reach
  Reference at the same time, and neither is perpetually
  deprioritized.

**Caveat:** Parallel requires sufficient engineering capacity
to work on both generics simultaneously. If capacity is
constrained, the next-best alternative is **A (Wind-first)**
because Wind's 3 discrepancies are a "real work" argument
that justifies the order, even though Solar is structurally
simpler.

## 7. Readiness Ranking

F2-C ranks the four factory projects for future promotion
work. The ranking is based on the readiness score, the gap
magnitude, and the per-project test coverage.

| Rank | Project | Current Level | Readiness | Why this rank |
|---|---|---|---|---|
| **1st** | **Oborovo Solar** | Level 2 (Reference) | already done | Already at Level 2. No promotion work needed. |
| **2nd** | **TUHO Wind** | Level 2 (Reference) | already done | Already at Level 2. No promotion work needed. |
| **3rd** | **Generic Wind** | Level 1 (Exploratory) | 39/100 | Closer to Reference than Solar in terms of test coverage (18 vs 8+) and factory granularity. 3 data discrepancies to resolve. |
| **4th** | **Generic Solar** | Level 1 (Exploratory) | 39/100 | Same readiness as Wind. Lower test coverage (8+). 0 data discrepancies to resolve. |

**Tie-breaker between Generic Wind (3rd) and Generic Solar
(4th):** F2-C ranks **Generic Wind 3rd and Generic Solar 4th**
based on test coverage. Wind has 18 incidental test references;
Solar has 8+. The 10-file delta suggests Wind has more
**existing test surface** to build a dedicated test pack on,
which is a soft advantage for migration.

This ranking is **for sequencing future work, not for
promotion decisions.** Both generics are at Level 1 and stay
at Level 1 throughout F2-C.

## 8. Strategic Recommendation

F2-C answers the strategic question:

> "Should FincoGPT pursue Generic Wind first, Generic Solar first, or both together?"

**Answer: Both together (parallel).**

**Rationale:**

1. **Shared methodology dominates the critical path.** Excel
   reference acquisition and parity computation are the same
   effort for both generics. Doing them in parallel halves the
   calendar time and reduces methodology risk.
2. **Per-project work is small relative to shared work.** Test
   pack, KNOWN_LIMITATIONS.md, and D1/D2 redo/D3 redo rows
   must be done twice, but each is MEDIUM effort, not HIGH.
3. **Governance is symmetric.** Both generics are excluded
   from Pilot RC with the same wording. The migration should
   be symmetric.
4. **Wind's 3 data discrepancies are LOW effort, not HIGH.**
   They do not justify a Wind-first sequencing.
5. **Solar's 0 data discrepancies are a "free" simplification,
   not a strategic advantage.** They simply skip one LOW
   effort step.
6. **Sequential approaches (Wind-first or Solar-first) risk
   perpetually deprioritizing the second generic.** Parallel
   prevents this.

### 8.1 Suggested roadmap

- **F2-D** (next): Excel reference acquisition + parity
  computation for **both** Generic Wind and Generic Solar
  in parallel. For Wind, this includes the data discrepancy
  resolution step. For Solar, this is just the Excel
  reference + parity.
- **F2-E** (next for both): test pack + KNOWN_LIMITATIONS.md +
  D1/D2 redo/D3 redo rows for **both** generics in parallel.
- **F2-F** (next for both): Phase 51F parity green + Pilot RC
  scope matrix CI guard for **both** generics in parallel.
- **F2-G** (separate, after F): promotion gate evaluation for
  **both** generics, run independently. Generic Wind and
  Generic Solar can be promoted to Level 2 in the same F-phase
  or in separate F-phases, depending on the gate outcome.

F2-C does **not** start F2-D, F2-E, F2-F, or F2-G.

## 9. Hard no-go list (F2-C)

- no code changes
- no runtime changes
- no UI implementation
- no schema changes
- no persistence changes
- no formula changes
- no parity changes
- no feature flags
- no validation status changes
- no project promotions (TUHO/Oborovo/Generic Wind/Generic Solar)
- no implementation plans beyond the F2-C comparison matrix
- no start of F2-D / F2-E / F2-F / F2-G
- no extension of the D1 / D2 redo / D3 redo arc to cover Generics
- no modifications to F1 / F2-A / F2-B outputs

## 10. Forbidden paths (F2-C)

F2-C does **not** modify:

- `app/**`
- `domain/**`
- `static/**`
- `tests/**`
- `main_web.py`
- `main_api.py`

F2-C only adds:

- `docs/phase_f2c_generic_renewable_comparison_matrix.md` (this file)
- `reports/phase_f2c_generic_renewable_comparison_matrix.json`

## 11. Stop-after-report contract

F2-C is:

- A docs-only, design-only comparison matrix.
- A consolidation of F2-A (Generic Wind) and F2-B (Generic Solar)
  inventories, with reference comparison and critical-path
  analysis.
- No implementation, no runtime change, no flag enablement,
  no F2-D / F2-E / F2-F / F2-G start.
- No new tests, no new code, no new persistence, no new
  schema, no new export surface, no new UI.

Branch: `phase-f2c-generic-renewable-comparison-matrix`
PR: DRAFT only, do not mark ready, do not merge.
rc1 SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4` — untouched.
Generic Solar status: **Level 1 (Exploratory / Unvalidated)**
— unchanged.
Generic Wind status: **Level 1 (Exploratory / Unvalidated)**
— unchanged.
TUHO / Oborovo: **Level 2 (Reference)** — unchanged.

## 12. Appendix — Glossary

- **READY:** All evidence is present and pinned.
- **PARTIAL:** Some evidence is present; key gaps remain.
- **MISSING:** No evidence is present.
- **Reference (Level 2):** Excel-pinned, parity-verified, audit-postured.
- **Validated (Level 3):** Reference + external sign-off.
- **Exploratory / Unvalidated (Level 1):** Factory inputs
  populated, no Excel reference, no parity.
- **Concept (Level 0):** Not yet implemented.

## 13. Appendix — F2-C vs F1 / F2-A / F2-B comparison

| Phase | Scope | Output | Status |
|---|---|---|---|
| F1 | Generic Solar/Wind validation methodology (framework + sketch) | `docs/phase_f1_generic_validation_methodology.md` + report | MERGED |
| F2-A | Generic Wind inventory + gap analysis | `docs/phase_f2a_generic_wind_reference_inventory.md` + report | MERGED |
| F2-B | Generic Solar inventory + gap analysis | `docs/phase_f2b_generic_solar_reference_inventory.md` + report | MERGED |
| F2-C | Generic Renewable comparison matrix (this doc) | `docs/phase_f2c_generic_renewable_comparison_matrix.md` + report | DRAFT |
| F2-D | Excel reference + parity (both generics, parallel) | not started | not started |
| F2-E | Test pack + KNOWN_LIMITATIONS + D1/D2 redo/D3 redo (both) | not started | not started |
| F2-F | Phase 51F parity green + CI guard (both) | not started | not started |
| F2-G | Promotion gate evaluation (both) | not started | not started |

F2-C is the **last comparison / analysis** F-phase. F2-D
through F2-G are **execution** F-phases, which F2-C does
**not** start.
