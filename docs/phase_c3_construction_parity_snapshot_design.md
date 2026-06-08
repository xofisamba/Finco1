# Phase C3 - Construction Period Parity Snapshot Design

> Type: DESIGN ONLY, DOCS ONLY, NO IMPLEMENTATION
> Status: DRAFT
> Date: 2026-06-08
> Base SHA: `59f9e3d` (post-Phase C1, post-Phase C2)
> Branch: `phase-c3-construction-parity-snapshot-design`
> Hard constraints: **NO code, NO implementation, NO runtime changes, NO schema/persistence changes, NO feature flags, NO formula changes, NO CAPEX/debt/tax/depreciation/IDC changes, NO project status changes**

---

## 0. Purpose

Phase C1 (`5fccc3a`) concluded with recommendation **B. More
discovery needed** and identified 5 blockers. Phase C2
(`59f9e3d`) addressed **blockers 1 and 2** (SHL IDC convention
decision, Layer 4 Opening Balance Bridge design) and deferred
**blockers 3, 4, 5** to this phase or later.

This C3 phase addresses **blockers 3 and 4**:

- **Blocker 3 (Layer 5 Runtime Integration seam)** — already
  scoped at the **boundary** in C2 §5; C3 sharpens the **parity
  evidence** required before that seam is wired.
- **Blocker 4 (no construction-period parity snapshot)** — the
  central deliverable of this document.

Blocker 5 (senior IDC effective-rate brittleness) is **addressed
at the design level only** in this document — the C3 readiness
checklist from C2 requires the senior IDC caveat to be
documented in the parity snapshot test docstring. The actual
modelling fix for senior IDC remains a separate workstream.

This document does **not** plan implementation. It designs the
parity framework that **must** exist before any future
construction runtime implementation, and it defines the dataset
shape required to evidence parity at the construction period,
the drawdown level, the IDC level, and the COD opening balance
level.

---

## 1. What construction parity means

### 1.1 Operating-period parity (today's baseline)

FincoGPT today maintains parity against Excel for the
**operating period only**:

- TUHO operating-period parity pack
  (`docs/phase9_tuho_full_line_item_parity_pack.md`) — Revenue,
  OPEX, EBITDA, senior debt, SHL, tax, distributions, returns.
- Oborovo operating-period parity snapshots
  (`docs/phase23n_oborovo_post_correction_parity_snapshot.md`,
  `docs/phase23p_oborovo_post_lockup_parity_snapshot.md`) —
  same shape.

The parity convention is: for each material line item, compare
the **Excel reference value** to the **model value** in a single
table with a **status** column (`PASS`, `WARN`, `BLOCKED`,
`MISSING_EVIDENCE`, `ACCEPTED_CONVENTION`).

### 1.2 What construction parity is *not*

Construction parity is **not** the same as operating parity
because:

- The construction period has **no revenue, OPEX, EBITDA,
  CFADS, tax, distributions, or returns** to compare.
- The construction period has **only flows**: monthly uses,
  monthly drawdowns by source, monthly IDC by source, and a
  single **opening balance** at the COD boundary.
- The construction period output is a **bridge**: it
  transforms monthly flows into COD opening balances that the
  operating waterfall then consumes.

So construction parity is **boundary parity**: it must prove
that the **outputs** of the construction engine match the Excel
reference at the **COD opening balance boundary**, and that the
**internal monthly flows** match the Excel reference at the
**construction-period grid**.

### 1.3 Construction parity is three concentric layers

| Layer | What is compared | Tolerance | Status if missing |
|---|---|---|---|
| **Funding parity** (5.1) | Monthly drawdown by source, total uses | exact (0.001 kEUR) per cell | `MISSING_EVIDENCE` |
| **IDC parity** (5.2) | Monthly IDC by source, total IDC | exact per cell | `MISSING_EVIDENCE` |
| **Opening balance parity** (5.3) | Senior opening at COD, SHL opening at COD, equity contribution at COD | exact | `BLOCKED` |

All three layers must pass before construction runtime can be
wired (Layer 5 in C2 terminology). The C3 design locks all three.

### 1.4 Construction parity is *not* a runtime contract

The C3 deliverable is a **parity framework** — a dataset
schema, a comparison table convention, and a CI gate. It is
**not** a runtime contract: nothing in this document says the
runtime waterfall must consume the construction engine. The
opt-in flag `use_construction_schedule_engine` (Phase 7I)
remains default-off after C3.

The parity framework is the **evidence base** that, when
combined with the Layer 4 bridge (C2) and a future Layer 5
seam (C2 §5), justifies flipping the flag.

---

## 2. TUHO construction parity dataset

### 2.1 Reference source

The TUHO construction-period reference values are extracted
from the TUHO Excel workbook:

- `monthly_uses_keur` — `tuho.py:TUHO_MONTHLY_USES_KEUR` (18
  monthly cells, already extracted at discovery time)
- `total_uses_keur` — 72,994.450 kEUR (Excel)
- `equity_draw_total_keur` — 500.000 kEUR (Excel)
- `shl_draw_total_keur` — 29,135.176 kEUR (Excel)
- `junior_draw_total_keur` — 0.000 kEUR (Excel)
- `senior_draw_total_keur` — 43,359.274 kEUR (Excel)
- `senior_idc_target_keur` — 1,519.564 kEUR (Excel
  `IDC!D57`)
- `shl_idc_target_keur` — 3,568.688 kEUR (Excel — full-source
  elapsed compound, per C2 Convention B)
- `opening_senior_balance_keur` — 43,359.274 + 1,519.564 =
  **44,878.838** kEUR (Excel, principal + senior IDC)
- `opening_shl_balance_keur` — 29,135.176 + 3,568.688 =
  **32,703.864** kEUR (Excel, principal + SHL IDC)
- `equity_contribution_at_cod_keur` — 500.000 kEUR (Excel;
  equity is not capitalized)

### 2.2 Calendar reference

- `construction_start_date` — 2028-06-30
- `cod_date` — 2029-12-30
- `construction_months` — 18
- `shl_investment_date` — 2028-06-30 (TUHO)

### 2.3 TUHO dataset scope (C3 deliverable)

The C3 TUHO dataset must include all of the following for the
construction period:

1. The **18 monthly `monthly_uses_keur`** values.
2. The **18 monthly `equity_draw_keur`** values.
3. The **18 monthly `shl_draw_keur`** values.
4. The **18 monthly `senior_draw_keur`** values.
5. The **18 monthly `shl_idc_keur`** values (per-month, not
   cumulative).
6. The **18 monthly `senior_idc_keur`** values.
7. The **18 cumulative `cumulative_uses_keur`** values
   (sanity row).
8. The **18 cumulative `cumulative_equity_keur` /
   `cumulative_shl_keur` / `cumulative_senior_keur` /
   `cumulative_shl_idc_keur` / `cumulative_senior_idc_keur`**
   values.
9. The 5 **totals** from §2.1.
10. The 2 **calendar dates** from §2.2.
11. The 3 **opening balances at COD** from §2.1.

The 18×11 monthly grid + 5 totals + 2 dates + 3 openings = 207
fields per dataset. The dataset is the **golden reference** for
TUHO construction parity.

### 2.4 TUHO tolerance policy

- Per-month monetary values: exact match, tolerance ±0.001
  kEUR. A mismatch is a **blocking failure**.
- Total monetary values: exact match, tolerance ±0.001 kEUR.
- Date values: exact match (no tolerance).
- Cumulative values: derived from monthly; must match to ±0.001
  kEUR (catches integration drift).

### 2.5 TUHO parity gate (when implemented)

A future pytest test (in `tests/test_phase_c4_*.py`, after
implementation) will:

- Build the TUHO construction config
  (`build_tuho_construction_config`).
- Run the construction engine (`engine.run_construction`).
- Compare the 207 golden fields above to the engine output.
- Fail the test if any field is outside tolerance.
- The test docstring must cite C2 §6.1 (C3 readiness) and
  document the senior IDC effective-rate caveat (C1 R-PAR-2,
  C2 §2.1).

---

## 3. Oborovo construction parity dataset

### 3.1 Reference source

The Oborovo construction-period reference values are extracted
from the Oborovo Excel workbook:

- `monthly_uses_keur` — `oborovo.py:OBOROVO_MONTHLY_USES_KEUR`
  (12 monthly cells)
- `total_uses_keur` — 57,973.041 kEUR (Excel)
- `equity_draw_total_keur` — 500.000 kEUR (Excel)
- `shl_draw_total_keur` — 14,620.774 kEUR (Excel)
- `junior_draw_total_keur` — 0.000 kEUR (Excel)
- `senior_draw_total_keur` — 42,852.267 kEUR (Excel)
- `senior_idc_target_keur` — 1,086.032 kEUR (Excel
  `IDC!D57`)
- `shl_idc_target_keur` — 1,169.662 kEUR (Excel — full-source
  elapsed compound, per C2 Convention B)
- `opening_senior_balance_keur` — 42,852.267 + 1,086.032 =
  **43,938.299** kEUR (Excel, principal + senior IDC)
- `opening_shl_balance_keur` — 14,620.774 + 1,169.662 =
  **15,790.436** kEUR (Excel, principal + SHL IDC)
- `equity_contribution_at_cod_keur` — 500.000 kEUR (Excel)

### 3.2 Calendar reference

- `construction_start_date` — 2029-06-29
- `cod_date` — 2030-06-29
- `construction_months` — 12
- `shl_investment_date` — 2029-06-29 (Oborovo)

### 3.3 Oborovo dataset scope (C3 deliverable)

The C3 Oborovo dataset must include:

1. The **12 monthly `monthly_uses_keur`** values.
2. The **12 monthly `equity_draw_keur`** values.
3. The **12 monthly `shl_draw_keur`** values.
4. The **12 monthly `senior_draw_keur`** values.
5. The **12 monthly `shl_idc_keur`** values.
6. The **12 monthly `senior_idc_keur`** values.
7. The **12 cumulative `cumulative_uses_keur`** values.
8. The **12 cumulative `cumulative_equity_keur` /
   `cumulative_shl_keur` / `cumulative_senior_keur` /
   `cumulative_shl_idc_keur` / `cumulative_senior_idc_keur`**
   values.
9. The 5 **totals** from §3.1.
10. The 2 **calendar dates** from §3.2.
11. The 3 **opening balances at COD** from §3.1.

The 12×11 monthly grid + 5 totals + 2 dates + 3 openings = 142
fields per dataset.

### 3.4 Oborovo tolerance policy

Same as §2.4: per-month exact ±0.001 kEUR, totals exact ±0.001
kEUR, dates exact.

### 3.5 Oborovo parity gate (when implemented)

A future pytest test (in `tests/test_phase_c4_*.py`, after
implementation) will:

- Build the Oborovo construction config
  (`build_oborovo_construction_config`).
- Run the construction engine.
- Compare the 142 golden fields to the engine output.
- Fail the test on any mismatch.
- The test docstring must document the senior IDC
  effective-rate caveat (C1 R-PAR-2).

### 3.6 Difference vs TUHO

| Aspect | TUHO | Oborovo |
|---|---|---|
| Construction months | 18 | 12 |
| Total uses | 72,994.450 | 57,973.041 |
| SHL principal | 29,135.176 | 14,620.774 |
| Senior principal | 43,359.274 | 42,852.267 |
| SHL IDC (Conv B) | 3,568.688 | 1,169.662 |
| Senior IDC target | 1,519.564 | 1,086.032 |
| Opening senior at COD | 44,878.838 | 43,938.299 |
| Opening SHL at COD | 32,703.864 | 15,790.436 |
| Excel layout | (reference 1) | (reference 2) |
| CO2 / certificates | Yes (Phase 9 calibration) | No (not in scope) |
| Effective senior rate | 0.06045 | 0.05895 |

Both datasets must be exercised by the parity gate. The
difference is a **smoke test** that the construction engine is
not hardcoded to one project.

---

## 4. Required snapshot fields

### 4.1 Why a single canonical field list

The Phase 9 and Phase 23N/23P operating-period parity packs each
list their own line items. That is fine for human review, but a
parity **gate** needs a **machine-readable** field list with
**stable codes**.

C3 introduces the **construction parity field codes**: a
canonical list of fields, each with a unique code, type, unit,
and tolerance, that any parity test must conform to.

### 4.2 Field code convention

A field code is a snake_case identifier:

```
<project>_<category>_<subcategory>_<field>
```

- `project` is `tuho` or `oborovo` (or `generic_wind`,
  `generic_solar` for future projects).
- `category` is one of `mflow` (monthly flow), `cum`
  (cumulative), `tot` (total), `cal` (calendar), `ob` (opening
  balance at COD), `meta` (metadata).
- `subcategory` is one of `use`, `eq`, `shl`, `sen`, `idc`,
  `n_a` (not applicable for meta).
- `field` is the field name from the engine dataclass
  (`monthly_uses_keur`, `equity_draw_keur`, `cod_date`, etc.).

### 4.3 Canonical field list (TUHO + Oborovo)

| Code | Type | Unit | TUHO | Oborovo | Tolerance | Source |
|---|---|---|---|---|---|---|
| `tuho_mflow_use_m1_keur` | float | kEUR | 24,226.729 | — | ±0.001 | `TUHO_MONTHLY_USES_KEUR[0]` |
| `tuho_mflow_use_m2_keur` | float | kEUR | 2,785.808 | — | ±0.001 | `TUHO_MONTHLY_USES_KEUR[1]` |
| ... | ... | ... | ... | ... | ... | (18 rows for TUHO) |
| `tuho_mflow_eq_m1_keur` | float | kEUR | (derived) | — | ±0.001 | engine output |
| `tuho_mflow_shl_m1_keur` | float | kEUR | (derived) | — | ±0.001 | engine output |
| `tuho_mflow_sen_m1_keur` | float | kEUR | (derived) | — | ±0.001 | engine output |
| `tuho_mflow_idc_shl_m1_keur` | float | kEUR | (derived) | — | ±0.001 | engine output |
| `tuho_mflow_idc_sen_m1_keur` | float | kEUR | (derived) | — | ±0.001 | engine output |
| `tuho_cum_use_m1_keur` | float | kEUR | 24,226.729 | — | ±0.001 | engine output |
| `tuho_cum_eq_m1_keur` | float | kEUR | (derived) | — | ±0.001 | engine output |
| `tuho_cum_shl_m1_keur` | float | kEUR | (derived) | — | ±0.001 | engine output |
| `tuho_cum_sen_m1_keur` | float | kEUR | (derived) | — | ±0.001 | engine output |
| `tuho_cum_idc_shl_m1_keur` | float | kEUR | (derived) | — | ±0.001 | engine output |
| `tuho_cum_idc_sen_m1_keur` | float | kEUR | (derived) | — | ±0.001 | engine output |
| `tuho_tot_uses_keur` | float | kEUR | 72,994.450 | — | ±0.001 | Excel |
| `tuho_tot_eq_draw_keur` | float | kEUR | 500.000 | — | ±0.001 | Excel |
| `tuho_tot_shl_draw_keur` | float | kEUR | 29,135.176 | — | ±0.001 | Excel |
| `tuho_tot_sen_draw_keur` | float | kEUR | 43,359.274 | — | ±0.001 | Excel |
| `tuho_tot_shl_idc_keur` | float | kEUR | 3,568.688 | — | ±0.001 | Excel (Conv B) |
| `tuho_tot_sen_idc_keur` | float | kEUR | 1,519.564 | — | ±0.001 | Excel |
| `tuho_cal_start_date` | date | ISO | 2028-06-30 | — | exact | Excel |
| `tuho_cal_cod_date` | date | ISO | 2029-12-30 | — | exact | Excel |
| `tuho_cal_months` | int | months | 18 | — | exact | Excel |
| `tuho_ob_sen_balance_keur` | float | kEUR | 44,878.838 | — | ±0.001 | derived |
| `tuho_ob_shl_balance_keur` | float | kEUR | 32,703.864 | — | ±0.001 | derived |
| `tuho_ob_eq_contribution_keur` | float | kEUR | 500.000 | — | ±0.001 | Excel |
| (analogous 142 rows for Oborovo) | | | | | | |

### 4.4 Field code resolution rules

- Per-month flow codes are repeated for each month index
  (m1..m18 for TUHO, m1..m12 for Oborovo). The full code is
  `tuho_mflow_<sub>_m<n>_keur`.
- Cumulative codes are repeated for each month. The full code
  is `tuho_cum_<sub>_m<n>_keur`.
- Total codes are project-level (no month suffix).
- Calendar codes are project-level.
- Opening balance codes are project-level.

### 4.5 Why "sub" is restricted

The `sub` field is restricted to `eq`, `shl`, `sen`, `idc`
because:

- These are the four **funding source categories** in the
  current engine.
- Adding new categories (e.g. `junior`) requires a code-list
  bump, which is a **breaking change** in the parity schema.
- C3 does not add new categories. If a future project uses a
  junior tranche, that is a new C-phase.

### 4.6 The 4 field types

| Type | Encoding | Tolerance | Where the value comes from |
|---|---|---|---|
| `excel_value` | float | ±0.001 kEUR | Direct Excel reference (manual extraction) |
| `excel_target` | float | ±0.001 kEUR | Excel `IDC!D57` or equivalent target cell |
| `derived` | float | ±0.001 kEUR | Computed from other field codes (e.g. opening = principal + IDC) |
| `engine_output` | float | ±0.001 kEUR | Construction engine dataclass field |
| `date` | ISO 8601 | exact | Excel reference |
| `int` | integer | exact | Excel reference |

The 207 (TUHO) + 142 (Oborovo) = **349 fields** in the canonical
list. This is the **machine-readable** shape of the C3 dataset.

### 4.7 Why field codes are not Python enums

The field codes are documented in this design doc and in the
report JSON. They are **not** introduced as Python enums in
this phase. C3 is a **docs-only** phase. The enums (if needed)
are a C4+ decision. Until then, field codes are **strings** in
the report JSON.

---

## 5. Funding parity

### 5.1 What funding parity proves

Funding parity proves that the construction engine allocates
the **same total monthly spend** to the **same funding source**
at the **same month** as the Excel reference. If funding parity
fails, every downstream calculation is suspect.

### 5.2 Funding parity test (when implemented)

A future pytest test will:

1. Build the project construction config (TUHO or Oborovo).
2. Run the construction engine.
3. For each month `m` in `1..N` (N=18 for TUHO, N=12 for
   Oborovo), assert:
   - `engine_output.monthly_entries[m-1].monthly_uses_keur ==
     excel_value_within_tolerance(0.001)`
   - `engine_output.monthly_entries[m-1].equity_draw_keur ==
     excel_value_within_tolerance(0.001)`
   - `engine_output.monthly_entries[m-1].shl_draw_keur ==
     excel_value_within_tolerance(0.001)`
   - `engine_output.monthly_entries[m-1].senior_draw_keur ==
     excel_value_within_tolerance(0.001)`
4. Assert that monthly uses sum to the Excel
   `total_uses_keur` (catches integration errors).
5. Assert that source draws sum to the Excel
   `total_<source>_draw_keur` (catches allocation errors).

### 5.3 Funding parity per-source accounting identity

For each project, the funding identity is:

```
sum(monthly_uses_keur)        = total_uses_keur
sum(equity_draw_keur)         = total_equity_draw_keur
sum(shl_draw_keur)            = total_shl_draw_keur
sum(junior_draw_keur)         = total_junior_draw_keur
sum(senior_draw_keur)         = total_senior_draw_keur
```

This is a **hard identity**. If it fails, the construction
engine is broken. The parity test must include a dedicated
identity-check subtest.

### 5.4 Funding parity for unknown months

The engine currently uses `CapexProfileType.CUSTOM` and consumes
the `monthly_uses_keur` array. The C3 parity test does not need
to test **profile types** other than `CUSTOM` — that is a
**profile-type parity pack** (future C-phase).

### 5.5 Funding parity failure mode

A funding parity failure is a **blocking failure**. The test
must fail the build, the parity report must record
`funding_parity_status: BLOCKED`, and the C3 readiness
checklist (C2 §6.7) is not satisfied.

---

## 6. IDC parity

### 6.1 What IDC parity proves

IDC parity proves that the construction engine produces the
**same per-month interest** at the **same rate basis** as the
Excel reference, summed to the same total. IDC is a **derived**
flow — it depends on the funding draw timing.

### 6.2 Two IDC sources, two conventions

| Source | TUHO | Oborovo | Excel target | Convention |
|---|---|---|---|---|
| SHL | 3,568.688 kEUR | 1,169.662 kEUR | `IDC!D37` | C2 Convention B (Excel full-source elapsed compound) |
| Senior | 1,519.564 kEUR | 1,086.032 kEUR | `IDC!D57` | Effective-rate (C1 R-PAR-2 caveat) |

The SHL IDC target is **modelling-correct** (full-source
elapsed compound matches the Excel formula by construction).
The senior IDC target is **calibrated to an effective rate**
because the per-month senior base-rate rows are not yet
modelled.

### 6.3 The senior IDC effective-rate caveat

The C1 design gate flagged senior IDC as **R-PAR-2 (effective
rate brittleness)**. The C2 design froze the senior opening
balance as `frozen` until the senior IDC is modelling-correct.

The C3 parity test must, in its docstring, document this
caveat:

> The senior IDC parity is achieved via effective rate, not
> modelling correctness. The effective rate is documented in
> `tuho.py:senior_interest_rate` (0.06045...) and
> `oborovo.py:senior_interest_rate` (0.05895...). These rates
> are calibrated to the Excel `IDC!D57` target. The rate is
> NOT modelling-correct (the Excel base-rate row inputs are
> not yet modelled in the engine). When the base-rate rows are
> modelled, the effective rate must be replaced with a
> derived rate that does not depend on the target value.
> Until then, the senior IDC parity is a **calibrated** parity,
> not a **modelled** parity.

This caveat is a **test docstring** requirement, not a
runtime behaviour.

### 6.4 IDC parity test (when implemented)

A future pytest test will:

1. Build the project construction config.
2. Run the construction engine.
3. For each month `m`, assert:
   - `engine_output.monthly_entries[m-1].shl_idc_keur ==
     excel_value_within_tolerance(0.001)` (per-month SHL
     IDC)
   - `engine_output.monthly_entries[m-1].senior_idc_keur ==
     excel_value_within_tolerance(0.001)` (per-month senior
     IDC)
4. Assert that the **total SHL IDC** matches
   `total_shl_idc_keur` (3,568.688 TUHO, 1,169.662 Oborovo)
   to ±0.001.
5. Assert that the **total senior IDC** matches
   `senior_idc_target_keur` (1,519.564 TUHO, 1,086.032 Oborovo)
   to ±0.001.

### 6.5 IDC parity accounting identity

The IDC accounting identity is:

```
sum(shl_idc_keur)   = total_shl_idc_keur
sum(senior_idc_keur) = total_senior_idc_keur
```

A failure here means the per-month rates are wrong.

### 6.6 IDC parity failure mode

An IDC parity failure is a **blocking failure**. The test must
fail the build, the parity report must record
`idc_parity_status: BLOCKED`, and the C3 readiness checklist
(C2 §6.7) is not satisfied.

---

## 7. Opening balance parity

### 7.1 What opening balance parity proves

Opening balance parity proves that the **COD boundary** between
the construction engine and the operating waterfall is
correct. The operating waterfall reads
`senior_opening_balance_keur`, `shl_opening_balance_keur`, and
`equity_total_keur` at the start of period 0. If the
construction engine produces the wrong opening balance, the
operating waterfall's senior debt, SHL, and equity cashflows
are all wrong from period 0 onwards.

### 7.2 The three opening balance fields

| Field | Construction engine | Excel | C2 policy |
|---|---|---|---|
| `opening_senior_balance_keur` | `total_senior_draw + total_senior_idc` | 44,878.838 TUHO / 43,938.299 Oborovo | **replaced-when-modelling-correct, frozen-otherwise** (C2 §2.1) |
| `opening_shl_balance_keur` | `total_shl_draw + total_shl_idc` | 32,703.864 TUHO / 15,790.436 Oborovo | **replaced** (C2 §2.1) |
| `equity_contribution_at_cod_keur` | `total_equity_draw` (no IDC) | 500.000 TUHO / 500.000 Oborovo | **derived** (C2 §2.1) |

### 7.3 The senior opening balance caveat

The senior opening balance **includes senior IDC**. The senior
IDC is calibrated to an effective rate (§6.3). Therefore the
senior opening balance parity is also calibrated, not modelled.

The C2 policy correctly freezes the senior opening balance
until the senior IDC is modelling-correct. The C3 parity test
**still** asserts the senior opening balance matches the
Excel-derived value, but the test docstring must cite the
C2 §2.1 freeze policy and the C1 R-PAR-2 caveat.

### 7.4 The SHL opening balance identity

The SHL opening balance identity is the most important
opening balance check, because the SHL IDC is modelling-correct
(per C2 Convention B):

```
opening_shl_balance_keur == total_shl_draw_keur + total_shl_idc_keur
```

This identity is **not calibrated**. It is derived from
first-principles SHL mechanics. If the SHL opening balance
fails parity, the SHL mechanics are broken.

### 7.5 Opening balance parity test (when implemented)

A future pytest test will:

1. Build the project construction config.
2. Run the construction engine.
3. Assert:
   - `engine_output.opening_senior_balance_keur ==
     excel_opening_senior_within_tolerance(0.001)` (with
     caveat)
   - `engine_output.opening_shl_balance_keur ==
     excel_opening_shl_within_tolerance(0.001)` (identity
     check)
   - `engine_output.total_equity_draw_keur ==
     excel_equity_within_tolerance(0.001)` (derived)
4. Assert the SHL identity (7.4) explicitly.
5. Document the senior opening balance caveat in the test
   docstring.

### 7.6 Opening balance parity failure mode

An opening balance parity failure is a **blocking failure**.
The test must fail the build, the parity report must record
`opening_balance_parity_status: BLOCKED`, and the C3
readiness checklist (C2 §6.7) is not satisfied.

---

## 8. Golden dataset structure

### 8.1 Why a golden dataset

The C3 deliverable is a **golden dataset** for TUHO and a
**golden dataset** for Oborovo. The golden dataset is the
**single source of truth** for the parity test. If a field is
in the dataset, the test must check it. If a field is not in
the dataset, the test must skip it.

### 8.2 Dataset file format

A C3 golden dataset is a JSON file in `reports/`:

```json
{
  "project_code": "TUHO-WIND-1",
  "schema_version": "C3-1.0",
  "field_count": 207,
  "tolerance_policy": "exact_0.001_keur",
  "calendar": {
    "construction_start_date": "2028-06-30",
    "cod_date": "2029-12-30",
    "construction_months": 18
  },
  "totals": {
    "total_uses_keur": 72994.450,
    "total_equity_draw_keur": 500.000,
    "total_shl_draw_keur": 29135.176,
    "total_junior_draw_keur": 0.000,
    "total_senior_draw_keur": 43359.274,
    "total_shl_idc_keur": 3568.688,
    "total_senior_idc_keur": 1519.564
  },
  "opening_balances": {
    "opening_senior_balance_keur": 44878.838,
    "opening_shl_balance_keur": 32703.864,
    "equity_contribution_at_cod_keur": 500.000
  },
  "monthly_grid": [
    {
      "month_index": 1,
      "monthly_uses_keur": 24226.729,
      "equity_draw_keur": 500.000,
      "shl_draw_keur": 0.000,
      "junior_draw_keur": 0.000,
      "senior_draw_keur": 23726.729,
      "shl_idc_keur": 0.000,
      "senior_idc_keur": 119.628,
      "cumulative_uses_keur": 24226.729,
      "cumulative_equity_keur": 500.000,
      "cumulative_shl_keur": 0.000,
      "cumulative_junior_keur": 0.000,
      "cumulative_senior_keur": 23726.729,
      "cumulative_shl_idc_keur": 0.000,
      "cumulative_senior_idc_keur": 119.628
    },
    ... (18 rows for TUHO, 12 for Oborovo)
  ],
  "caveats": {
    "senior_idc_effective_rate_caveat": {
      "applies": true,
      "rate": 0.060454449320244484,
      "target_keur": 1519.564,
      "source": "tuho.py:senior_interest_rate",
      "policy_reference": "C1 R-PAR-2, C2 §2.1 freeze"
    },
    "shl_idc_convention": {
      "applies": true,
      "convention": "Excel full-source elapsed compound",
      "policy_reference": "C2 §1.2 Convention B"
    }
  }
}
```

### 8.3 Dataset location

| Project | Path |
|---|---|
| TUHO | `reports/phase_c3_tuho_construction_parity_golden.json` |
| Oborovo | `reports/phase_c3_oborovo_construction_parity_golden.json` |

These files are **C3 deliverables** in the C3 PR. The
**design doc** for the dataset is this file
(`docs/phase_c3_construction_parity_snapshot_design.md`).

### 8.4 Dataset versioning

The dataset has a `schema_version` field. C3 introduces
`C3-1.0`. Any future change to the field list, tolerance
policy, or caveat policy requires a schema version bump
(e.g. `C3-1.1`, `C3-2.0`).

### 8.5 Dataset vs parity test

The C3 deliverable is the **dataset** (this design + the
golden JSONs). The C4+ deliverable is the **parity test** that
consumes the dataset. C3 does not include the parity test —
that is the next phase.

### 8.6 The dataset is the contract

Once the C3 dataset is in place, it is the **contract**
between the construction engine and the operating waterfall.
If a future change to the engine breaks a field, the C3
parity test (C4+) will fail. The C3 dataset is the **frozen
reference** against which all future engine changes are
tested.

---

## 9. CI / governance requirements

### 9.1 The C3 gate

The C3 design introduces a **CI gate** at the dataset
boundary, not the test boundary:

- The golden datasets are **checked into the repo** (not
  generated at test time).
- A future CI workflow (C4+) will:
  1. Load the golden dataset.
  2. Run the construction engine.
  3. Compare engine output to the dataset.
  4. Fail the build on any mismatch.

C3 itself does not include the CI workflow — that is C4+.

### 9.2 What the C3 PR does enforce

The C3 PR enforces, via the design test file:

- The 10 required sections are present.
- The TUHO and Oborovo datasets are documented with the
  correct field counts (207 + 142 = 349 fields).
- The field code convention is consistent.
- The C2 hard constraints (no code, no runtime, etc.) are
  preserved.
- rc1 SHA is reachable.

The C3 design test does **not** enforce the actual parity
match — that is the C4+ parity test.

### 9.3 Why no runtime / no engine changes in C3

C3 is **docs only**. It introduces the **dataset** and the
**gate design**, but does not implement either. The reasoning:

- The construction engine is still **diagnostic-only** (Phase
  7I default-off flag).
- The Layer 4 bridge (C2) is **designed** but not implemented.
- The Layer 5 seam (C2) is **bounded** but not wired.
- The C3 gate is a **future** CI workflow.

Any change to the engine or runtime is **out of scope** for
C3. C3 is the **parity framework**, not the parity test.

### 9.4 Schema governance

The C3 dataset schema (`schema_version: C3-1.0`) is governed
by the same rule as the operating parity pack:

- **Schema change** requires a C-phase.
- **Tolerance change** requires a C-phase.
- **Field addition** requires a C-phase.
- **Field removal** requires a C-phase (with migration plan).

This is the **schema freeze** rule. C3 freezes the
construction parity schema for the first time.

### 9.5 Dataset authority

The golden datasets are **authoritative** in the sense that:

- The parity test must match the dataset.
- A change to the engine that produces a value different from
  the dataset is a **regression**.
- A change to the dataset itself requires a C-phase and a
  rationale (e.g. "we discovered the Excel value was wrong by
  0.5 kEUR").

The dataset is **not** authoritative over the operating
waterfall. If the construction engine produces an opening
balance that matches the dataset but the operating waterfall
reads a different value, the **waterfall** is wrong (not the
dataset). The construction engine + dataset is the upstream
contract; the waterfall is the downstream consumer.

### 9.6 The C3 audit trail

Every C3 decision is recorded:

- The 10 sections document the design.
- The 349 field codes document the schema.
- The two golden datasets document the reference values.
- The two design tests (TUHO + Oborovo) document the C3
  test scaffolding.
- The C3 PR (when opened) is the audit log entry.

---

## 10. Recommendation

### Choice: **B. More discovery needed**

Rationale:

1. **C2 blockers 3 and 4 are now addressed by the parity
   framework design.** The C3 document defines what
   construction parity means (§1), the two project datasets
   (§2, §3), the field code schema (§4), the three parity
   layers (§5, §6, §7), the golden dataset structure (§8),
   and the CI / governance rules (§9). The C3 PR is
   **docs-only** and does not implement the parity test —
   that is the next phase.

2. **The C3 readiness checklist from C2 §6.7 is partially
   satisfied by this document.** Items 1 and 2 (TUHO and
   Oborovo construction-period parity snapshots **exist**)
   are addressed at the **design** level — the datasets are
   specified. Items 3-6 (manual-vs-derived, COD opening
   balance, IDC by source, no-double-counting) are addressed
   at the **structure** level — the parity test shape is
   specified but not implemented. Items 7-8 (senior IDC
   caveat docstring, second pair of eyes) are explicitly
   deferred to C4+.

3. **The senior IDC effective-rate caveat is preserved.**
   The C3 design documents the caveat (§6.3, §7.3) in two
   places. The senior opening balance remains **frozen**
   per C2 §2.1. C3 does not unlock the senior IDC fix.

4. **The C3 design does not address C1 blocker 5 in any
   new way.** The senior IDC is still calibrated to an
   effective rate. C3 documents the caveat but does not
   propose a fix. The fix is a **separate workstream**
   (modelling the Excel base-rate rows), which is out of
   scope for the C-series.

5. **C3 is a framework, not a test.** The actual parity
   test (C4+) must:
   - Implement the test scaffolding.
   - Run the construction engine.
   - Compare to the golden datasets.
   - Fail the build on any mismatch.
   - Document the senior IDC caveat in the test docstring.

   Until the test exists, the C3 design is **untested**.
   C3 cannot prove parity; it can only design the
   framework that will prove parity.

### What would unblock "A. Ready for C4+"

- A C4 design note that implements the parity test
  scaffolding (one test for TUHO, one for Oborovo, plus a
  combined regression test).
- A C4 implementation PR that:
  - Adds the C4 parity tests.
  - Adds the CI workflow that runs the parity tests.
  - Verifies the senior IDC caveat is in the test docstring.
  - Verifies the SHL opening balance identity (§7.4) is
    asserted as a hard test.
- A C4 design note for the senior IDC base-rate modelling
  fix (out of C-series scope; this is mentioned here only
  for context).

### What remains open after C3

- The parity test (C4+).
- The Layer 4 bridge implementation (C2 design → C4+ code).
- The Layer 5 seam implementation (C2 design → C5+ code).
- The senior IDC base-rate modelling (separate workstream).
- The runtime opt-in flag flip (C6+, after all of the above).

### Multi-phase path

C3 is the **third** phase in the C-series identified by C1
(commit `5fccc3a`). The path forward:

| Phase | Scope | Status |
|---|---|---|
| C1 | Design gate | ✅ Merged `5fccc3a` |
| C2 | SHL IDC convention + Layer 4 bridge design | ✅ Merged `59f9e3d` |
| **C3** | **Construction parity framework design** | **This PR (DRAFT)** |
| C4 | Parity test implementation + CI gate | Future |
| C5 | Layer 4 bridge implementation | Future |
| C6 | Layer 5 seam implementation + opt-in flag flip | Future |
| C7 | Promotion of TUHO/Oborovo to construction-runtime-authoritative | Future |
| C8-C11 | Other C1-listed work (e.g. junior tranche, multi-construction, etc.) | Future |

---

## C3 readiness checklist status

Mapping to C2 §6.7:

- [x] **TUHO construction-period parity snapshot exists and
      passes** — *designed* in §2 and §8; **not** implemented
      as a passing test (C4+).
- [x] **Oborovo construction-period parity snapshot exists
      and passes** — *designed* in §3 and §8; **not**
      implemented as a passing test (C4+).
- [x] **Manual-vs-derived reconciliation test exists and
      passes** — *designed* in §5.3 and §7.4; **not**
      implemented (C4+).
- [x] **COD opening balance reconciliation test exists and
      passes** — *designed* in §7; **not** implemented (C4+).
- [x] **IDC by source reconciliation test exists and
      passes** — *designed* in §6.5; **not** implemented
      (C4+).
- [x] **No double-counting test plan is implemented as an
      executable test and passes** — *designed* in C2 §2 and
      §4 audit table; **not** implemented (C4+).
- [x] **The senior IDC effective-rate caveat is documented
      in the parity snapshot test docstring** — *designed* in
      §6.3 and §7.3; **not** in a test docstring yet (C4+).
- [ ] **The bridge (Layer 4) and the audit table schema are
      reviewed by a second pair of eyes** — *deferred* to C4+
      (the audit table schema is in C2 §4; C3 does not
      change it).

**8 of 9 C3 readiness items are designed; 0 of 9 are
implemented as code. C3 is a design phase, not an
implementation phase.**

---

## 11. Hard constraints (re-asserted)

C3 introduces **no code, no runtime changes, no schema
changes, no persistence changes, no feature flags, no
formula changes, no CAPEX changes, no debt changes, no tax
changes, no depreciation changes, no IDC implementation, and
no project status changes**. The C3 deliverable is a
**design doc + 1 report JSON** (the design test file is a
test for this design, not a parity test). Construction
runtime remains diagnostic-only. The opt-in flag
`use_construction_schedule_engine` remains default-off.

---

## 12. Stop after report

This document is the C3 deliverable. The C3 PR is opened
as DRAFT. Do not mark ready. Do not merge. Stop after
report.

---

Deliverables: this document +
`reports/phase_c3_construction_parity_snapshot_design.json`.
