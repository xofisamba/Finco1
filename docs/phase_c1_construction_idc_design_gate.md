# Phase C1 - Construction Schedule / IDC Design Gate

> Type: DESIGN ONLY, DOCS ONLY
> Status: DRAFT
> Date: 2026-06-08
> Base SHA: `fe741b6` (post-57A-10H, post-Depreciation audit, post-Generic F1-F2-C, post-CAPEX UX arc)
> Branch: `phase-c1-construction-idc-design-gate`
> Hard constraints: **NO code, NO implementation, NO runtime changes, NO schema/persistence changes, NO feature flags, NO formula changes, NO project status changes**

---

## 0. Purpose

A formal **design gate** before any implementation of construction-period
modelling: schedule, drawdown timing, funding allocation, IDC mechanics,
opening balances at COD.

The question this gate answers:

> **What exactly would need to exist before FincoGPT can support
> construction schedule and IDC modelling in a parity-safe way?**

This document does **not** plan implementation. It identifies what is
missing, what is at risk, and what evidence would be required before
implementation, runtime wiring, and promotion.

---

## 1. Current State

The construction-period problem today is split between **runtime
authoritative inputs** and **diagnostic-only offline engines**.

### 1.1 CAPEX

- `Project.spending_profile` and `_CAPEX_ITEM_FIELDS` are the runtime
  authoritative source for operating-period CAPEX totals
  (post-COD). 15 sub-lines mapped in `domain/inputs.py:CapexItem`.
- **No construction-period spend profile** is wired into runtime.
  Operating-period CAPEX assumes the entire construction spend lands
  in a single period (typically period 0 or "pre-COD lump").
- Phase 7F and 7I produced a **diagnostic-only construction engine**
  in `domain/construction/` that produces a `ConstructionIDCResult`
  with monthly rows, but this result is **audit-only** and never
  reaches `Project.spending_profile`.

### 1.2 Debt

- Senior debt: `Project.senior_opening_balance_keur` is the runtime
  authoritative opening at COD. Phase 23A frozen the senior debt
  schedule. Phase 7K documented the sculpting fixture, but senior
  IDC is **not** computed in runtime; the runtime uses the manual
  `senior_opening_balance_keur` field as-is.
- Senior IDC: a 1,519.564 kEUR target exists in the TUHO template
  (Phase 7I), but runtime does not consume it.
- Senior drawdown timing: **not modeled**. Runtime assumes the
  opening balance lands in period 0 in full.

### 1.3 SHL

- `Project.shl_idc_keur` is a **manual hardcoded input** per project
  factory (TUHO: 1,169; Oborovo: 0; the runtime waterfall consumes
  this field as-is). Phase 7F flagged this as a known gap.
- `Project.shl_opening_balance_keur` is the runtime authoritative
  opening at COD. For TUHO this is 32,704; for Oborovo this is
  15,790. These are **hardcoded project factory values**, not
  computed.
- Phase 7I offline engine produces SHL IDC matching the Excel
  golden reference (TUHO 3,568.688, Oborovo 1,169.662), but the
  computed IDC does **not** replace the manual `shl_idc_keur` field.
  Phase 7I's runtime flag is **diagnostic-only** and default-off.

### 1.4 Depreciation

- Phase D1, D2, D3 + Closure (D-arc) closed the depreciation
  audit. The depreciation model consumes **opening balances** at
  COD but does not model construction-period flows. Asset
  retirements and additions during construction are not modeled.
- The `Asset` registry in `domain/inputs.py:Asset` is keyed by
  `asset_class` and is currently populated from project factories
  with no notion of when each asset was put in service (month /
  period of COD).

### 1.5 Construction schedule

- **No runtime construction schedule exists**. The only
  construction schedule artefacts are:
  - `domain/construction/engine.py` (offline, audit-only)
  - `domain/construction/templates/tuho.py` and `oborovo.py`
    (offline, audit-only)
  - The Phase 20L workbook UX (`sheet_construction.html`,
    `sheet_idc.html`) which displays the diagnostic schedule in
    the UI, but the data is sourced from the offline engine, not
    from the runtime.
- The current `use_construction_schedule_engine` flag is **default
  off** and **diagnostic-only** (per Phase 7I). No project code
  currently has this flag enabled.

### 1.6 IDC

- **No runtime IDC calculator exists**. The offline engine in
  `domain/construction/idc_calculator.py` is the only implementation
  and is audit-only.
- The runtime waterfall does not capitalise construction-period
  interest; opening senior and SHL balances are entered as if the
  drawdown and IDC had already settled before period 0.

### 1.7 What is "manual" vs "runtime authoritative" vs "audit-only"

| Concept | Manual | Runtime authoritative | Audit-only |
|---|---|---|---|
| Operating CAPEX total | - | `Project.spending_profile` | - |
| Construction spend profile | - | - | `domain/construction/` |
| Senior opening balance | `Project.senior_opening_balance_keur` | `Project.senior_opening_balance_keur` | - |
| Senior IDC | not modeled | not modeled | `domain/construction/` (target 1,519.564 TUHO) |
| SHL opening balance | `Project.shl_opening_balance_keur` | `Project.shl_opening_balance_keur` | - |
| SHL IDC | `Project.shl_idc_keur` (TUHO 1,169 / Oborovo 0) | `Project.shl_idc_keur` | `domain/construction/` (3,568.688 TUHO) |
| Construction schedule | - | - | `domain/construction/engine.py` |
| IDC calculation | - | - | `domain/construction/idc_calculator.py` |
| Funding allocation | - | - | `domain/construction/funding_allocation.py` |
| Asset in-service date | not modeled | not modeled | not modeled |

The pattern is: **all construction-period concepts are audit-only
except for the small set of "opening balance" fields that the
operating-period waterfall reads directly**. The runtime never sees
the construction period.

---

## 2. Excel Gap Analysis

A standard project-finance model separates construction from
operations. The Excel reference implements the following layers:

### 2.1 Construction period (`Phase 0`)

- A schedule of construction months (TUHO: 18, Oborovo: 12)
- A monthly CAPEX spend profile (linear / S-curve / custom)
- A monthly drawdown profile per funding source (equity, SHL,
  junior, senior) — typically a **waterfall** order rather than
  pro-rata
- A monthly interest accrual per debt source, with two method
  variants in practice:
  - **Average balance**: `(opening + 0.5 * drawdown) * rate * period`
  - **Opening balance**: `opening * rate * period`
- The Excel model uses a **full-source elapsed compound** method
  for SHL IDC: `SHL IDC = SHL draw * ((1 + SHL rate) ^ elapsed_years
  - 1)` (Phase 7I). This is a **different convention** from the
  draw-by-draw monthly method, and the project finance market
  standard varies.
- The Excel model uses a **monthly cumulative-balance** method for
  senior IDC: `(senior_rate + base_rate_t) * prior cumulative
  senior draw * period_fraction_t` (Phase 7I).

### 2.2 COD bridge

At COD, the construction engine produces:
- Senior opening balance (= total senior draw + senior IDC)
- SHL opening balance (= total SHL draw + SHL IDC)
- Equity invested (= total equity draw)
- Asset book values (= total CAPEX + total IDC, allocated to
  asset classes)

### 2.3 Operating period (`Phase 1+`)

The operating period reads opening balances and runs the waterfall
(revenue, OPEX, debt service, distributions, R99).

### 2.4 Missing layers in FincoGPT today

| Layer | Excel | FincoGPT | Gap |
|---|---|---|---|
| Construction schedule | explicit | absent (audit-only) | **Missing** |
| Construction CAPEX spend profile | explicit (linear / S-curve / custom) | absent | **Missing** |
| Funding drawdown waterfall | explicit | absent (audit-only) | **Missing** |
| Senior IDC | computed in monthly loop | absent (target 1,519.564 in TUHO template only) | **Missing** |
| SHL IDC | full-source elapsed compound | absent (manual `shl_idc_keur` consumed as-is) | **Missing** |
| Senior opening balance bridge | computed at COD | manual input `senior_opening_balance_keur` | **Stub** |
| SHL opening balance bridge | computed at COD | manual input `shl_opening_balance_keur` | **Stub** |
| Asset in-service date | month of COD | not modeled | **Missing** |
| Depreciation base for IDC | IDC capitalized into asset cost | not modeled (assets keyed by class, not by service date) | **Missing** |
| Construction cash management | separate construction account | not modeled | **Missing** |

### 2.5 What is at risk if we wire it now

- If the runtime waterfall consumes **both** the manual opening
  balance and the computed construction IDC, we **double-count**
  interest. This is the central risk that Phase 7I's "no
  double-counting" rule was written to prevent.
- The Excel SHL IDC method (full-source elapsed compound) and the
  monthly average-balance method give **different numbers**. For
  TUHO: 3,568.688 (Excel) vs an average-balance method would give
  a smaller figure because the drawdown is front-loaded. The
  current model uses the manual TUHO `shl_idc_keur=1,169` which is
  **a different concept again** (it is not the full source-elapsed
  figure). Until we resolve which convention is authoritative,
  any wiring will produce a different number than Excel.
- Senior IDC parity currently uses **template-level effective
  rates** calibrated to the discovered Excel totals. The base
  rates and day-count conventions are not yet modeled. The
  effective rates work for parity snapshots, but the moment the
  construction period changes (e.g. COD moves), the effective rate
  becomes invalid. This is documented in Phase 7I as a known
  limitation.

---

## 3. Architecture Review

Prior construction work exists in three places:

### 3.1 Phase 7F — Construction CAPEX & IDC Module Design

- A **module design note** written in May 2026. Defined dataclasses
  (`MonthlySpendProfile`, `FundingAllocation`, `MonthlyIDCEntry`,
  `ConstructionIDCResult`, `ConstructionIDCConfig`), 5 profile
  generators (linear, S-curve, front-loaded, back-loaded, custom),
  and 2 interest methods (average balance, opening balance).
- **Status today**: superseded by Phase 7I. Phase 7F was
  conceptual; Phase 7I actually shipped an engine. Phase 7F's
  average-balance method differs from Phase 7I's
  full-source-elapsed-compound method.
- **What remains valid**:
  - The 5-attribute dataclass structure
  - The list of profile types
  - The opt-in design (config is `None` by default → manual
    inputs keep working)
  - The "backward compatibility" principle
- **What should change**:
  - The interest method should be **explicit** and named, not a
    free string. Phase 7F used `"average_balance"` and
    `"opening_balance"`; Phase 7I introduced a third method
    ("full_source_elapsed_compound" for SHL) and a fourth for
    senior (monthly cumulative-balance with base-rate adjustment).
  - The `app/construction/` package location proposed in Phase 7F
    is **not** where the engine shipped — it shipped in
    `domain/construction/`. We should align.
  - The dataclass names should be reviewed for collision with
    Phase 7I's `MonthlyIDCEntry` and `ConstructionIDCResult`.
- **What should be deferred**:
  - VAT bridge (`vat_bridge_pct`) and grants (`grant_pct`)
    placeholders. These are not in the current Excel scope and
    should be deferred to a separate phase.
  - Multi-phase construction (phased COD) — not in v1.

### 3.2 Phase 7I — Construction Schedule Engine

- The **actual shipped engine**. Lives in `domain/construction/`.
  Includes `engine.py`, `idc_calculator.py`, `funding_allocation.py`,
  `capex_schedule.py`, `result.py`, `templates/tuho.py`,
  `templates/oborovo.py`.
- Produces a `ConstructionIDCResult` that **matches the Excel
  golden reference** for both TUHO and Oborovo (parity table in
  Phase 7I docs).
- **What remains valid**:
  - The three-step engine (uses → funding → IDC)
  - The source-waterfall funding logic (equity → SHL → junior →
    senior)
  - The custom profile generator (used for TUHO and Oborovo
    because their monthly cash requirements are explicit in the
    Excel)
  - The parity table (TUHO 18 months, Oborovo 12 months, exact
    target numbers)
- **What should change**:
  - The senior IDC method is **effective-rate based** for parity
    but not modelling-correct. Before any runtime wiring, the
    senior IDC method needs to be derived from the Excel base
    rates and day-count conventions, not from a calibrated
    effective rate.
  - The runtime flag is diagnostic-only. If we want to wire the
    engine into the operating waterfall, the flag semantics need
    a second design pass.
- **What should be deferred**:
  - The linear / S-curve / front-loaded / back-loaded profile
    generators (Phase 7F had them; Phase 7I ships only `linear`
    and `custom`). The Excel reference uses **custom** for both
    current projects. The other profiles are not in scope until
    a project explicitly needs them.

### 3.3 Phase 20L — Construction / IDC Workbook UX

- A **UI / workbook rendering** of the offline engine. Adds
  `sheet_construction.html` and `sheet_idc.html` to the fc-grid
  family.
- **What remains valid**:
  - The display format (financial close, COD, construction period,
    monthly drawdown schedule, IDC summary)
  - The "Audit / Preview" badge semantics (the workbook is
    diagnostic-only)
  - The fc-grid design system alignment
- **What should change**:
  - Once the engine becomes runtime authoritative, the workbook
    should switch from "Audit / Preview" to "Live / Runtime" —
    but that is a future phase and a separate design decision.
- **What should be deferred**:
  - Editing the construction schedule in the UI. The current
    sheets are read-only display surfaces. Editing the schedule
    requires a new form surface, validation, and persistence —
    out of scope here.

### 3.4 Construction Schedule Engine (Phase 7I) — at a glance

The engine architecture is correct in shape:

```
ConstructionIDCConfig
    ↓
engine.build_monthly_uses(config)
    ↓
funding_allocation.allocate(uses, sources)
    ↓
idc_calculator.compute_senior_idc(...) + compute_shl_idc(...)
    ↓
ConstructionIDCResult
```

The shape is fine. The **methods** need work (effective-rate vs
modelling-correct for senior; the SHL convention question needs
answering), and the **wiring** (how the result reaches the
operating waterfall) is the central design problem this gate
addresses.

---

## 4. Proposed Layering

Five clearly separated layers. Each layer has a single
responsibility and a single owner.

### Layer 1: Construction Schedule

**Responsibility:** Produce a monthly schedule of construction cash
requirements (CAPEX + pre-COD opex + pre-COD interest) for the
construction period.

**Inputs:** construction start date, COD date, total CAPEX,
profile type (linear / S-curve / custom).

**Outputs:** `List[MonthlyUseEntry]` — one per construction month,
with `month_index`, `period_start`, `period_end`, `capex_keur`.

**Owner:** `domain/construction/capex_schedule.py` (already
exists; extends Phase 7I with the missing profile generators from
Phase 7F if needed).

**Does NOT:** allocate funding, compute IDC, or bridge to COD.

### Layer 2: Funding Allocation

**Responsibility:** Given a monthly use schedule, allocate each
month's uses to funding sources in waterfall order (equity → SHL
→ junior → senior), respecting per-source caps and tracking
cumulative draws.

**Inputs:** `List[MonthlyUseEntry]`, per-source caps and rates.

**Outputs:** `List[MonthlyDrawEntry]` — one per month per source,
with `month_index`, `source`, `draw_keur`, `cumulative_draw_keur`.

**Owner:** `domain/construction/funding_allocation.py` (already
exists; Phase 7I implementation).

**Does NOT:** compute IDC, choose drawdown timing within a month,
or bridge to COD.

### Layer 3: IDC Calculation

**Responsibility:** Given monthly draws and per-source rates,
compute monthly interest per source, with the convention chosen
**explicitly** per source (no implicit assumptions).

**Inputs:** `List[MonthlyDrawEntry]`, per-source rates, **named
interest method per source** (one of: `full_source_elapsed_compound`
/ `monthly_cumulative_balance` / `monthly_average_balance` /
`monthly_opening_balance`).

**Outputs:** `List[MonthlyIDCEntry]` — one per month per source,
with `month_index`, `source`, `opening_keur`, `draw_keur`,
`idc_keur`, `closing_keur`.

**Owner:** `domain/construction/idc_calculator.py` (already
exists; Phase 7I ships two methods; needs the additional
`monthly_average_balance` and `monthly_opening_balance` from
Phase 7F for completeness).

**Does NOT:** allocate funding, choose the source waterfall order,
or bridge to COD.

### Layer 4: Opening Balance Bridge

**Responsibility:** Given a complete `ConstructionIDCResult`,
produce the opening balances at COD that the operating waterfall
consumes.

**Inputs:** `ConstructionIDCResult`.

**Outputs:**
- `senior_opening_balance_at_cod_keur` (= total senior draw +
  total senior IDC, or as configured)
- `shl_opening_balance_at_cod_keur` (= total SHL draw + total
  SHL IDC, or as configured)
- `equity_invested_keur` (= total equity draw)
- `asset_book_values` (a list of `(asset_class, amount)` pairs
  representing the depreciable base at COD)

**Owner:** `domain/construction/opening_bridge.py` (does **not**
exist yet — Phase 7I stops at the result; this layer is the
missing piece).

**Does NOT:** run the operating waterfall, allocate IDC across
asset classes, or compute depreciation.

### Layer 5: Runtime Integration

**Responsibility:** Given a project factory and a construction
config, decide **which manual fields are replaced** and **which
manual fields are kept**, then feed the construction result into
the operating waterfall through a **single, auditable seam**.

**Inputs:** `Project`, `Optional[ConstructionIDCConfig]`,
explicit `replace_manual_fields: List[str]`.

**Outputs:** a modified `Project` with the chosen manual fields
replaced by construction-engine outputs, and an `AuditTrail`
entry recording the substitution.

**Owner:** a new seam — not in `domain/construction/` and not
in `domain/inputs.py:Project`. The seam should be **explicitly
typed** so the operating waterfall never has to check "did the
construction engine run or not?".

**Does NOT:** decide policy (whether to replace a field); it
enforces the policy that was set.

**Critical design rule:** the seam must refuse to run if
`replace_manual_fields` references a field that is still being
read elsewhere as authoritative. The double-counting guard
sits in this layer, not in Layer 1-4.

### Layer responsibilities summary

| Layer | Owner | Reads from | Writes to | Authority |
|---|---|---|---|---|
| 1. Construction Schedule | `domain/construction/capex_schedule.py` | config | `MonthlyUseEntry[]` | audit-only |
| 2. Funding Allocation | `domain/construction/funding_allocation.py` | `MonthlyUseEntry[]` | `MonthlyDrawEntry[]` | audit-only |
| 3. IDC Calculation | `domain/construction/idc_calculator.py` | `MonthlyDrawEntry[]` | `MonthlyIDCEntry[]` | audit-only |
| 4. Opening Balance Bridge | `domain/construction/opening_bridge.py` (NEW) | `ConstructionIDCResult` | opening balances + asset book values | **candidate runtime input** |
| 5. Runtime Integration | new seam (NEW) | `Project`, `ConstructionIDCConfig` | `Project` (modified) + audit trail | **runtime seam** |

Layers 1-3 exist today (Phase 7I). Layer 4 is missing. Layer 5 is
missing. Layers 1-3 are **audit-only** today and would remain
audit-only until Layers 4 and 5 are designed, reviewed, and
promoted.

---

## 5. Risk Review

### 5.1 Parity risks

| Risk | Severity | Description |
|---|---|---|
| **R-PAR-1: SHL IDC convention mismatch** | **Critical** | Excel uses full-source elapsed compound; Phase 7I matches that. The runtime waterfall consumes `Project.shl_idc_keur` as-is. Wiring the engine into the waterfall will produce a different number (3,568.688 vs the manual 1,169 for TUHO). Which is the **authoritative** number? |
| **R-PAR-2: Senior IDC effective rate brittleness** | **High** | The senior IDC target is calibrated to an effective rate because the Excel base-rate rows are not modeled. Any change to the construction period (e.g. COD shift) invalidates the effective rate. |
| **R-PAR-3: Opening balance double-counting** | **Critical** | If the runtime consumes both the manual `senior_opening_balance_keur` (or `shl_opening_balance_keur`) **and** the construction-engine output, the operating waterfall will pay interest on interest. This is the single most dangerous failure mode. |
| **R-PAR-4: Asset class allocation at COD** | **Medium** | Excel assigns IDC to specific asset classes for depreciation purposes. The FincoGPT depreciation model has no notion of in-service date. The depreciation base at COD is implicitly "CAPEX + IDC lumped into one asset class", which does not match Excel. |
| **R-PAR-5: Equity invested vs CAPEX equity** | **Medium** | Excel may have a different equity line (500 kEUR for TUHO) from the operating CAPEX equity. The runtime waterfall currently treats CAPEX equity as 0 in the operating period. |

### 5.2 Governance risks

| Risk | Severity | Description |
|---|---|---|
| **R-GOV-1: Project status drift** | **High** | The gate is explicit: no project status changes. Wiring construction into the waterfall risks **silently** moving TUHO and Oborovo from Level 2 (Reference) to Level 3 (Runtime-Authoritative Construction) without an explicit promotion gate. |
| **R-GOV-2: Manual override policy** | **High** | The runtime currently trusts manual project factory inputs. If the construction engine is enabled for one project, the seam must be **explicit** about which fields are replaced and which are not. Ambiguity here is a governance failure. |
| **R-GOV-3: Audit trail completeness** | **Medium** | Phase 7I produced a `construction_schedule_diagnostic` that records the mismatch between manual and computed values. If we wire the engine, the diagnostic must include the **decision** (which field was replaced, which was kept, why) — not just the raw numbers. |

### 5.3 Audit risks

| Risk | Severity | Description |
|---|---|---|
| **R-AUD-1: No replay of the construction decision** | **High** | Today, the construction engine can run offline. If the runtime consumes a construction-engine output, the audit trail must include **enough information to reconstruct the construction result from project factory inputs alone**. |
| **R-AUD-2: Double-counting hidden in waterfall** | **Critical** | The operating waterfall reads `Project.shl_opening_balance_keur` and `Project.shl_idc_keur`. If the construction engine is wired and **also** writes to those fields, the audit trail will not show whether the values came from the construction engine or from the project factory unless we record it explicitly. |
| **R-AUD-3: Asset register changes** | **Medium** | The asset register is rebuilt from project factory inputs at runtime. If Layer 4 produces an asset book values list, the asset register must record "asset book value at COD came from construction engine" — not from the static project factory. |

### 5.4 Validation risks

| Risk | Severity | Description |
|---|---|---|
| **R-VAL-1: No regression test for parity drift** | **High** | The current Phase 9 (TUHO) and Phase 23N (Oborovo) parity snapshots are **operating-period** parity. There is no **construction-period** parity snapshot. Wiring the engine without a construction-period snapshot means there is no test to catch regressions. |
| **R-VAL-2: Test data coverage** | **Medium** | The engine has 2 project templates (TUHO, Oborovo). Wiring the engine without additional test data (e.g. a synthetic short construction period) risks hardcoding assumptions to these two projects. |
| **R-VAL-3: Generic project coverage** | **High** | Generic Wind and Generic Solar are at Level 1 (Exploratory / Unvalidated). They do not currently have construction templates. Wiring the engine to "support Generic" without validation is a risk. |

### 5.5 Severity ranking (top 5)

1. **R-PAR-3: Opening balance double-counting** — Critical
2. **R-PAR-1: SHL IDC convention mismatch** — Critical
3. **R-AUD-2: Double-counting hidden in waterfall** — Critical
4. **R-GOV-2: Manual override policy** — High
5. **R-PAR-2: Senior IDC effective rate brittleness** — High

---

## 6. Promotion Gates

What evidence is required before each step.

### 6.1 Before implementation (any code change beyond docs/reports)

- [ ] This design gate (Phase C1) is reviewed and merged
- [ ] The SHL IDC convention question is answered in writing
      (full-source elapsed compound is the chosen convention; the
      current `shl_idc_keur` manual field semantics are redefined
      accordingly)
- [ ] The senior IDC method is **modelling-correct** (not
      effective-rate based) and the base rates + day-count
      conventions are documented
- [ ] A construction-period parity snapshot test exists for at
      least one project (TUHO is the natural first target)
- [ ] A "double-counting guard" spec exists: which fields are
      allowed to be replaced by the construction engine, and which
      are not
- [ ] A "manual override precedence" spec exists: what happens
      when the project factory's manual values disagree with the
      construction engine's computed values

### 6.2 Before runtime wiring (Layer 5 is enabled for any project)

- [ ] Layer 4 (`opening_bridge.py`) is implemented and unit-tested
- [ ] The audit trail records the construction decision (which
      fields were replaced, which were kept, why) in a queryable
      format
- [ ] The operating waterfall's opening balance reads are routed
      through the **seam**, not through the `Project` field
      directly
- [ ] The double-counting guard has a test for **every** opening
      balance the waterfall reads
- [ ] A construction-period parity snapshot test exists for **each
      promoted project** (TUHO, Oborovo, and any new project that
      adopts construction)
- [ ] The project status is **explicitly** updated to indicate
      "construction runtime authoritative" — this is a separate
      promotion decision

### 6.3 Before promotion (project moves to "construction runtime
authoritative")

- [ ] All parity snapshots pass within tolerance for **the
      construction period** (not just the operating period)
- [ ] The audit trail is queryable end-to-end (from project
      factory inputs to operating waterfall output)
- [ ] The project has been reviewed by a second pair of eyes
      (governance review, not just parity)
- [ ] The change is documented in a project-specific changelog
      (e.g. `docs/project_tuho_construction_promotion.md`)

### 6.4 Evidence types

| Evidence | Format | Owner |
|---|---|---|
| Construction parity snapshot | pytest test + golden file | parity test layer |
| Double-counting guard test | pytest test | runtime test layer |
| Audit trail query | SQL / API endpoint | persistence layer |
| Governance review | markdown doc | reviewer |
| Project changelog | markdown doc | project owner |

---

## 7. Recommendation

### Choice: **B. More discovery needed**

Rationale:

1. **The shape is right but the seam is missing.** Phase 7I
   delivered Layers 1-3 (uses, funding, IDC) with strong parity
   to the Excel reference. Layers 4 and 5 are missing. The
   biggest unaddressed design problem is the **runtime seam**
   that decides which manual fields are replaced — without that
   seam, any wiring is a double-counting accident waiting to
   happen.

2. **The SHL IDC convention question is unresolved.** The Excel
   uses full-source elapsed compound. The runtime waterfall
   consumes `Project.shl_idc_keur` as a manual input. These are
   two different conventions with two different numbers
   (TUHO: 3,568.688 vs 1,169). Wiring the engine before
   answering "which is authoritative" will produce a different
   answer than the current operating waterfall — and the
   difference will be hidden inside the waterfall.

3. **There is no construction-period parity snapshot.** The
   current Phase 9 (TUHO) and Phase 23N (Oborovo) parity tests
   are **operating-period** parity. They would not catch a
   regression in the construction period. Wiring the engine
   without a construction-period snapshot is wiring blind.

4. **The senior IDC method is not modelling-correct.** The
   effective-rate approach used in Phase 7I is a parity
   workaround. It will silently break if the construction
   period changes. This needs a design decision before wiring.

5. **Two project templates is not enough coverage.** The
   engine has 2 templates (TUHO, Oborovo). Generic Wind and
   Generic Solar do not have construction templates. Wiring
   the engine risks overfitting to the two existing templates.

What would unblock "A. Ready for implementation planning":

- The SHL IDC convention is decided in writing
- A construction-period parity snapshot test exists for TUHO
  (the natural first target)
- The double-counting guard is specified (which fields can be
  replaced, which cannot)
- A "Layer 4 (opening balance bridge)" design note exists with
  explicit responsibilities

What would unblock "C. Defer":

- Generic program priorities change such that construction is
  no longer on the critical path
- Excel reference becomes unavailable or is replaced by a
  different source of truth
- A new project type that does not need construction (e.g. a
  battery storage with no CAPEX) becomes the pilot instead

None of these defer signals are present today. Construction
remains the largest remaining Excel-parity gap (per the
milestone review). **More discovery is the right call.**

### Suggested next discovery phases (NOT in scope for C1)

These are the discovery questions that would feed into a
follow-up design gate (C2 or equivalent). They are **not** part
of Phase C1 and are listed here only as a roadmap hint:

- **D-Q1:** Which SHL IDC convention is authoritative for the
  operating waterfall: full-source elapsed compound
  (Excel), the manual `shl_idc_keur` field, or something
  else?
- **D-Q2:** How should the asset register at COD be
  constructed? Per-class allocation, single "Construction in
  Progress" line, or some other model?
- **D-Q3:** What is the canonical answer to "what is the
  construction period for a given project?" — explicit
  start/COD dates, a single number of months, or
  project-factory-asserted dates?
- **D-Q4:** How does the equity invested line at COD interact
  with the operating CAPEX equity line? Are they the same
  thing or different?
- **D-Q5:** How should the runtime seam handle a partial
  configuration (e.g. construction engine enabled but one
  source rate is missing)? Skip, error, or fall back to
  manual?

---

## 8. Roadmap Position

Where Construction / IDC should sit relative to the other open
arcs.

### 8.1 Depreciation enablement

Status: **D-arc closed** (Phase 535, `647818f`). Depreciation
audit is complete.

Construction-period IDC is **capitalized into the asset base**,
so the depreciation arc is a **prerequisite** for construction
runtime. Construction engine outputs (asset book values at COD)
feed the depreciation model's in-service date / class
allocation. **D-arc done is a prerequisite, not a blocker.**

### 8.2 Generic program

Status: **F1-F2-C complete** (Phase 539, `93cd981`). Generic
Wind and Solar are at Level 1 (Exploratory / Unvalidated).

Construction templates do not yet exist for Generic Wind or
Solar. Wiring the engine to "support Generic" is a **separate
phase** and would be done **after** the engine is runtime
authoritative for the existing two reference projects. **Generic
program comes after, not before, Construction runtime.**

### 8.3 OPEX 2.0

Status: **discovered but not on the critical path** (Phase 20N
parity discovery, `docs/phase20n_revenue_opex_parity_discovery.md`).

OPEX 2.0 is operating-period. Construction is pre-operating.
The two arcs are **independent** and can be pursued in parallel.
**OPEX 2.0 is not blocked by Construction and does not block
Construction.**

### 8.4 Formula transparency

Status: **established convention** (Phase 50C, 50D). All
runtime calculations are auditable.

Construction engine outputs must be auditable end-to-end. The
runtime seam (Layer 5) is the natural place to extend the
formula transparency convention into the construction period.
**Formula transparency is a precondition, not a separate
phase.**

### 8.5 CAPEX evolution

Status: **57A-10F/G/H complete** (Phase 542, `fe741b6`). CAPEX
UX is in a stable state.

CAPEX evolution is **operating-period CAPEX**. Construction
CAPEX is a **separate concept** (the construction spend
profile, not the operating CAPEX total). Wiring the
construction engine would **not** modify the operating CAPEX
UX. **CAPEX evolution and Construction are independent.**

### 8.6 Position summary

| Arc | Status | Construction dependency |
|---|---|---|
| Depreciation enablement | closed | prerequisite (IDC capitalized into asset base) |
| Generic program | F1-F2-C done, Level 1 | comes **after** Construction runtime |
| OPEX 2.0 | discovered | independent, parallel |
| Formula transparency | established | precondition (seam is auditable) |
| CAPEX evolution | 57A-10F/G/H done | independent, parallel |

### 8.7 Recommended sequence

1. **Phase C1 (this document)** — design gate, no code
2. **Phase C2 (discovery)** — answer D-Q1 through D-Q5
3. **Phase C3 (Layer 4 design)** — `opening_bridge.py`
   responsibilities and dataclasses
4. **Phase C4 (Layer 5 design)** — runtime seam spec
5. **Phase C5 (construction-period parity snapshot)** — TUHO
   first, Oborovo second, Generic last
6. **Phase C6 (Layer 4 implementation)** — `opening_bridge.py`
   with unit tests, audit-only
7. **Phase C7 (Layer 5 implementation)** — runtime seam, opt-in
   per project, default off
8. **Phase C8 (runtime wiring for TUHO)** — first promoted
   project
9. **Phase C9 (runtime wiring for Oborovo)** — second promoted
   project
10. **Phase C10 (Generic templates)** — Generic Wind and
    Generic Solar construction templates
11. **Phase C11 (promotion)** — explicit project status change
    from "Reference (operating)" to "Reference (construction
    runtime authoritative)"

Phases C2-C11 are **not** planned in this document. They are
listed as a roadmap hint, subject to revision once the
discovery answers are in.

---

## 9. Stop after report

This is a **design gate only**. No code, no runtime changes, no
schema changes, no persistence changes, no feature flags, no
CAPEX formula changes, no debt changes, no tax changes, no
depreciation changes, no IDC implementation, no project status
changes.

Deliverables: this document + `reports/phase_c1_construction_idc_design_gate.json`.
