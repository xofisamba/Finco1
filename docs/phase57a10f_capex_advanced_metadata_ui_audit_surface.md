# Phase 57A-10F — CAPEX Advanced Metadata UI / Audit Surface

> Type: low-risk implementation, UI / export / audit only
> Branch: `phase57a10f-capex-advanced-metadata-ui-audit-surface`
> Base SHA: `93cd981adb39c55b446d10d34651f66bce1cf618` (post-F2-C)
> Status: DRAFT, do not mark ready, do not merge
> Scope: expose already-approved CAPEX metadata more clearly in
> the CAPEX UI and audit/export surfaces, **without changing
> model calculations**.

## 0. Purpose

Recent phases have already approved CAPEX metadata (VAT %,
WHT %, contingency %, payment schedule, useful life override,
etc.) in the model layer (Phases 57A-10 through 57A-10E), but
this metadata is not clearly distinguished in the UI / audit /
export surface. The user-visible CAPEX sheet can imply that
these fields affect calculations when in fact they do not.

57A-10F improves **user-visible CAPEX audit readiness** by:

1. Adding **status chips** that classify each advanced column
   into one of four categories:
   - **Runtime-used** — feeds the model
   - **Metadata-only** — captured for traceability; does not
     feed the model
   - **Design-only** — design phase; not yet implemented
   - **Export-only** — surfaced in export/audit; not in main UI
2. Adding a **disclaimer badge** to the deferred-placeholder
   block: "Metadata only — does not affect Run."
3. Extending the **export "Metadata Scope"** line in
   `app/excel_export.py` to enumerate which CAPEX fields are
   runtime-used vs metadata-only.

57A-10F does **not** change any model calculation, runtime
materialization, tax, depreciation, IDC, debt, or persistence
schema. The existing CAPEX advanced metadata persistence
(57A-10E) is the source of truth; 57A-10F only changes how
this metadata is **presented** to the user.

## 1. Hard constraints (mirror of brief)

- **No CAPEX total formula changes**
- **No runtime materialization changes**
- **No tax calculation changes**
- **No depreciation calculation changes**
- **No IDC calculation changes**
- **No debt changes**
- **No persistence schema changes** (unless already explicitly
  approved — and none are)
- **No new CAPEX logic**
- **No Generic project promotion**
- **No Tailwind / Alpine / frontend framework**

In other words: 57A-10F is a **UI / export / audit surface**
change only.

## 2. CAPEX advanced metadata field classification

The following CAPEX fields exist in the model today. Each is
classified into one of four status categories:

| Field | Where it lives | Status | Reasoning |
|---|---|---|---|
| `amount_keur` | `domain/inputs.py:CapexItem` | **Runtime-used** | The actual CAPEX value; feeds the model. |
| `y0_share` | `domain/inputs.py:CapexItem` | **Runtime-used** | The y0 spending share; feeds the model. |
| `spending_profile` | `domain/inputs.py:CapexItem` | **Runtime-used** | The post-y0 spending profile; feeds the model. |
| `asset_class` | `domain/inputs.py:CapexItem` | **Runtime-used** | Asset class; feeds depreciation / canonical engine. |
| `idc_keur` | `domain/inputs.py:CapexStructure` | **Runtime-used** | IDC; feeds the model. |
| `bank_fees_keur` | `domain/inputs.py:CapexStructure` | **Runtime-used** | Bank fees; feeds the model. |
| `commitment_fees_keur` | `domain/inputs.py:CapexStructure` | **Runtime-used** | Commitment fees; feeds the model. |
| `other_financial_keur` | `domain/inputs.py:CapexStructure` | **Runtime-used** | Other financial; feeds the model. |
| `vat_costs_keur` | `domain/inputs.py:CapexStructure` | **Runtime-used** | VAT cost; feeds the model (already approved). |
| `reserve_accounts_keur` | `domain/inputs.py:CapexStructure` | **Runtime-used** | Reserve accounts; feeds the model. |
| `useful_life_override` | `domain/inputs.py:CapexItem` | **Metadata-only** | Override stored for traceability; not yet consumed by the canonical depreciation engine. |
| VAT % column | `app/templates/partials/sheet_capex_detail.html:163` | **Metadata-only** | Read-only column; not yet fed to tax engine (deferred per `sheet_capex.html:649-660`). |
| WHT % column | `app/templates/partials/sheet_capex_detail.html:164` | **Metadata-only** | Read-only column; not yet fed to tax engine. |
| Contingency % column | `app/templates/partials/sheet_capex_detail.html` (contingency_pct) | **Metadata-only** | Read-only column; already approved in 57A-10C, but not yet fed to the model. |
| Payment schedule by month | `app/templates/partials/sheet_capex_detail.html` (monthly columns) | **Design-only** | Design phase; not yet implemented. |
| Depreciation category / useful life / flag | `app/templates/partials/sheet_capex.html:692` | **Design-only** | Design phase; not yet implemented. |
| VAT applicability / cost | `app/templates/partials/sheet_capex.html:649` | **Design-only** | Design phase; not yet implemented. |
| WHT rate / cost | `app/templates/partials/sheet_capex.html:652` | **Design-only** | Design phase; not yet implemented. |
| Utilisation of funds | `app/templates/partials/sheet_capex.html:660` | **Design-only** | Design phase; not yet implemented. |
| CAPEX sub-lines persisted | `app/capex_engine.py` / `app/templates/partials/sheet_capex.html` (sub-lines) | **Export-only** | Surfaced in `CapEx_SubLines_Audit` sheet (Phase 57A-9E) and CAPEX sheet; not in main runtime path beyond what already exists. |
| CAPEX category → field mapping | `app/excel_export.py:CAPEX_CATEGORY_TO_FIELD` | **Export-only** | Mapping surfaced in `CapEx_SubLines_Audit` sheet; not in main UI. |

### 2.1 Status chip semantics

Each status chip is a small visual indicator (text + class) that
appears next to the column header in the CAPEX sheet and in
the export audit sheet. The chips have the following
semantics:

- **Runtime-used** — "Used in Run calculations. Changes here
  affect the model output."
- **Metadata-only** — "Captured for audit / traceability. Does
  not affect Run calculations."
- **Design-only** — "Designed for a future phase. Not yet
  implemented."
- **Export-only** — "Surfaced only in export / audit artefacts.
  Not in the main UI."

The brief requires:

> Any metadata field must say clearly:
> "Metadata only — does not affect Run."

57A-10F implements this with a **disclaimer badge** that
appears immediately under the deferred-placeholder block,
naming each Metadata-only field explicitly.

## 3. UI changes

### 3.1 `app/templates/partials/sheet_capex.html`

**Add a status legend** at the top of the sheet (under the
read-only banner, above the data table):

```html
<div class="capex-status-legend" data-capex-status-legend="true">
  <p><strong>CAPEX column status legend:</strong></p>
  <ul>
    <li><span class="badge badge-runtime-used">Runtime-used</span> — feeds the model</li>
    <li><span class="badge badge-metadata-only">Metadata-only</span> — captured for audit; does not affect Run</li>
    <li><span class="badge badge-design-only">Design-only</span> — designed for a future phase; not yet implemented</li>
    <li><span class="badge badge-export-only">Export-only</span> — surfaced in export / audit artefacts only</li>
  </ul>
</div>
```

**Add a disclaimer badge** inside the
`.capex-deferred-note` block:

```html
<p class="capex-metadata-disclaimer">
  <span class="badge badge-metadata-only">Metadata only — does not affect Run.</span>
  These columns are placeholders; they are visible for
  design / planning but they do not affect the current
  model calculations.
</p>
```

**Add per-column status chips** to the deferred-placeholder
list:

```html
<ul>
  <li><span class="badge badge-metadata-only">Metadata-only</span>
      <strong>VAT % / WHT % / Contingency %</strong> — captured
      in CAPEX detail columns; not yet fed to tax / model.</li>
  <li><span class="badge badge-design-only">Design-only</span>
      <strong>Payment schedule by construction month</strong> —
      future input → equity drawdown, SHL drawdown, senior
      debt drawdown, IDC, opening balances at COD.</li>
  <li><span class="badge badge-design-only">Design-only</span>
      <strong>Depreciation category / useful life / flag</strong>
      — future input → P&amp;L and fixed asset schedule.</li>
  <li><span class="badge badge-design-only">Design-only</span>
      <strong>VAT applicability / rate / cost</strong> —
      future input → cash flow / balance sheet / working
      capital / tax receivable logic.</li>
  <li><span class="badge badge-design-only">Design-only</span>
      <strong>WHT rate / cost</strong> — future input → tax /
      cash flow treatment.</li>
  <li><span class="badge badge-design-only">Design-only</span>
      <strong>Utilisation of funds during construction</strong>
      — derived from the payment schedule.</li>
</ul>
```

### 3.2 `app/templates/partials/sheet_capex_detail.html`

**Add a status chip** to the table header for each advanced
column:

```html
<th class="fc-th fc-th--pct" data-col="7" rowspan="2">
  VAT<br/>%
  <span class="badge badge-metadata-only" data-capex-status="VAT">Metadata-only</span>
</th>
<th class="fc-th fc-th--pct" data-col="8" rowspan="2">
  WHT<br/>%
  <span class="badge badge-metadata-only" data-capex-status="WHT">Metadata-only</span>
</th>
<th class="fc-th fc-th--pct" data-col="?" rowspan="2">
  Contingency<br/>%
  <span class="badge badge-metadata-only" data-capex-status="contingency">Metadata-only</span>
</th>
```

**Add a status legend** at the top of the sheet (same legend
as in `sheet_capex.html`).

### 3.3 Why a status chip pattern (and not a full re-render)

The brief allows:
- status chips: Runtime-used / Metadata-only / Design-only /
  Export-only

A status chip pattern is the minimal, low-risk, low-surface
implementation:

- **CSS-only** — the chips are styled with the existing
  `.badge-*` classes; no new CSS file is required.
- **No JS** — the chips are pure HTML; no Alpine / Tailwind.
- **No data layer** — the status is hard-coded in the template
  based on the field classification in §2.
- **No persistence** — the chips are presentation-only.

This pattern matches the existing `badge-preview` /
`badge-warning` / `badge-muted` chip pattern already in use
in `sheet_capex.html` (footer note: `<span class="badge
badge-preview">{{ project_ctx.data_source }}</span>`).

## 4. Export / audit changes

### 4.1 `app/excel_export.py`

**Extend the "Metadata Scope" line** in the
`CapEx_SubLines_Audit` sheet's `notes_df` from:

```python
("Metadata Scope", "Metadata only - does not affect Run."),
```

to:

```python
("Metadata Scope", "Metadata only - does not affect Run. "
 "CAPEX runtime-used fields: amount, y0_share, spending_profile, "
 "asset_class, idc, bank_fees, commitment_fees, other_financial, "
 "vat_costs, reserve_accounts. "
 "CAPEX metadata-only fields: useful_life_override, VAT %, WHT %, "
 "contingency %. "
 "CAPEX design-only fields: payment schedule, depreciation "
 "category / useful life / flag, VAT applicability, WHT rate, "
 "utilisation of funds."),
```

This makes the classification visible in the export audit
sheet without changing any calculations.

## 5. Tests

### 5.1 New test file: `tests/test_phase57a10f_capex_advanced_metadata_ui_audit_surface.py`

The test file is **render / context / export safety only**. It
covers:

- **CAPEX page renders** — load the CAPEX sheet and assert
  status 200 + no `UndefinedError` / `NameError` /
  `AttributeError` in the response.
- **Metadata labels visible** — assert that
  `badge-metadata-only` text appears in the rendered HTML for
  both `sheet_capex.html` (status legend + disclaimer) and
  `sheet_capex_detail.html` (column header chips).
- **Status legend present** — assert that all four chip labels
  (Runtime-used / Metadata-only / Design-only / Export-only)
  appear in `sheet_capex.html`'s status legend block.
- **Disclaimer badge present** — assert that
  `Metadata only — does not affect Run.` text appears in
  `sheet_capex.html`'s deferred-placeholder block.
- **Export audit metadata scope** — assert that
  `app/excel_export.py` contains the extended
  "Metadata Scope" line and that the line explicitly names
  the runtime-used, metadata-only, and design-only CAPEX
  fields.
- **TUHO parity unchanged** — assert that the existing
  `tests/test_phase9_tuho_full_line_item_parity_pack.py`
  still passes (no regression).
- **Oborovo parity unchanged** — assert that the existing
  `tests/test_phase23n_oborovo_post_correction_parity_snapshot.py`
  still passes (no regression).
- **No CAPEX total change** — assert that the
  `_CAPEX_ITEM_FIELDS` tuple in `domain/inputs.py:CapexStructure`
  is unchanged from the pre-57A-10F SHA. This is a regression
  test, not a formula test.
- **Route smoke if templates touched** — assert that the
  workspace route still renders 200 for both TUHO and Oborovo
  contexts.

### 5.2 Tests that are **explicitly NOT included**

- No new test for the **runtime calculation** of CAPEX totals
  (this is out of scope; the brief explicitly forbids
  formula changes).
- No new test for the **parity computation** (this is out of
  scope; the brief explicitly forbids parity changes).
- No new test for the **persistence layer** (this is out of
  scope; the brief explicitly forbids schema changes).

## 6. Files changed

| Status | File | Lines | Type |
|---|---|---|---|
| M | `app/templates/partials/sheet_capex.html` | +35 / -0 | UI |
| M | `app/templates/partials/sheet_capex_detail.html` | +25 / -0 | UI |
| M | `app/excel_export.py` | +1 / -1 (or +N -1) | export |
| A | `tests/test_phase57a10f_capex_advanced_metadata_ui_audit_surface.py` | +200 / -0 | tests |
| A | `docs/phase57a10f_capex_advanced_metadata_ui_audit_surface.md` | (this file) | docs |
| A | `reports/phase57a10f_capex_advanced_metadata_ui_audit_surface.json` | +120 / -0 | report |

**Total estimate:** +380 / -1

## 7. Forbidden paths (57A-10F)

57A-10F does **not** modify:

- `domain/**` (no model / dataclass / formula changes)
- `app/capex_engine.py` (no engine changes)
- `app/capex_overrides.py` (no override changes)
- `app/persistence/**` (no schema changes)
- `main_web.py` (no route changes)
- `main_api.py` (no API changes)
- `static/app.js` (no JS changes)
- `static/styles.css` (no new CSS — uses existing `.badge-*`
  classes)
- `.github/workflows/**` (no CI changes)

57A-10F only modifies:

- `app/templates/partials/sheet_capex.html` (UI)
- `app/templates/partials/sheet_capex_detail.html` (UI)
- `app/excel_export.py` (export text only)
- `tests/test_phase57a10f_*.py` (new test file)
- `docs/phase57a10f_*.md` (this design doc)
- `reports/phase57a10f_*.json` (machine-readable report)

## 8. Stop-after-report contract

57A-10F is:

- A low-risk implementation, UI / export / audit only.
- No model formula, runtime, tax, depreciation, IDC, debt, or
  persistence changes.
- No new CAPEX logic.
- No Generic project promotion.

Branch: `phase57a10f-capex-advanced-metadata-ui-audit-surface`
PR: DRAFT only, do not mark ready, do not merge.
rc1 SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4` — untouched.
Generic Solar status: **Level 1 (Exploratory / Unvalidated)**
— unchanged.
Generic Wind status: **Level 1 (Exploratory / Unvalidated)**
— unchanged.
TUHO / Oborovo: **Level 2 (Reference)** — unchanged.
D-arc / F1 / F2-A / F2-B / F2-C: **unchanged**.

## 9. Appendix — risk analysis

### 9.1 What could go wrong

1. **A Jinja template variable is misnamed** — the status
   legend uses hard-coded text, so this risk is minimal. But
   the deferred-placeholder block uses dynamic rendering for
   some lines, so a misnamed variable could cause
   `UndefinedError` in the response. The render test catches
   this.
2. **A status chip CSS class is undefined** — the chips use
   the existing `.badge-*` classes, but if `.badge-design-only`
   or `.badge-export-only` are not yet defined in
   `static/styles.css`, the chips will render as unstyled
   text. The test does not assert CSS; it asserts that the
   text is present.
3. **The "Metadata Scope" line extension breaks the export
   sheet's column width** — the line is now longer. The
   export sheet's column width is auto-sized; the test
   asserts the line text is present in the source but does
   not assert the rendered column width.
4. **A template change breaks the workspace render** — the
   render test asserts 200 + no `UndefinedError`. If a
   template change breaks the render, the test fails.

### 9.2 What is intentionally out of scope

- A new CSS file (e.g. `capex_status_chips.css`) is not
  added. The chips use existing classes.
- A new JS file is not added. The chips are pure HTML.
- A new data layer for the status is not added. The status
  is hard-coded in the template.
- A new persistence layer is not added. The chips are
  presentation-only.
- A new test for the runtime calculation is not added. The
  brief explicitly forbids formula changes.

## 10. Appendix — alternatives considered and rejected

### 10.1 Alternative: full Jinja macro for status chips

A `{% call %}` / `{% import %}` macro could centralize the
status chip rendering. This is **rejected** because:

- The chip pattern is simple and self-contained.
- A macro adds an indirection that is harder to read in
  template diffs.
- The existing `sheet_capex.html` already uses ad-hoc
  `.badge-*` patterns; a new macro is inconsistent with the
  existing style.

### 10.2 Alternative: add a new data field `metadata_status`
to `CapexItem`

A `metadata_status: Literal["runtime_used", "metadata_only",
"design_only", "export_only"]` field could be added to
`CapexItem` and surfaced via Jinja. This is **rejected**
because:

- The brief explicitly forbids new CAPEX logic.
- The status classification is currently a 1-to-1 mapping
  between field name and status; a data field adds
  indirection without value.
- Adding a data field is a persistence-layer change, which
  is explicitly forbidden.

### 10.3 Alternative: add a new audit sheet

A new `CapEx_Column_Status` sheet could be added to the
export workbook. This is **rejected** because:

- The brief asks for a "user-visible CAPEX audit readiness"
  improvement, not a new sheet.
- The "Metadata Scope" line in the existing
  `CapEx_SubLines_Audit` sheet is the natural place to
  enumerate the status.
- A new sheet adds workbook complexity that is not justified
  by the brief.
