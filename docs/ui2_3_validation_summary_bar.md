# UI-2.3 — Validation Summary Bar Partial

## Context

UI-2.3 is the third runtime UI implementation, the second in the
runtime stack after UI-2.1 and UI-2.2. It adds a reusable validation
summary bar partial and wires it minimally into the audit/
reconciliation tab.

**This is a DRAFT PR. NO auto-merge. User visual review required.**

## Branch

`phase-ui2-3-validation-summary-bar`
**Base:** `6bd991f87b1aea2007d5c18818ce67b14aa30ba3` (post-UI-2.2 main)

## Files Changed

### New files
- `app/templates/partials/_validation_summary_bar.html` (NEW, 50 lines)
- `tests/test_ui2_3_validation_summary_bar.py` (NEW, 50 tests)
- `docs/ui2_3_validation_summary_bar.md` (this file)
- `reports/ui2_3_validation_summary_bar.json`

### Modified files (additive only)
- `app/templates/partials/audit_reconciliation_tab.html` (added 2-line include at top)
- `static/styles.css` (added 97 lines of `.validation-summary-*` classes)

### NOT changed
- `main_web.py`
- `app/services/`
- `app/persistence/`
- `app/runtime_impact_taxonomy.py`
- `static/app.js`
- All other templates
- All other CSS classes
- `:root` CSS variables

## Bar Spec

### Context handling

| Scenario | Behavior |
|---|---|
| `validation_summary` is supplied | Renders counts/status from it (pass/warn/fail counts + last_validated_at) |
| `validation_summary` is missing | Renders a compact neutral info bar with safe internal-review message |

### 4 supported tones

| Tone | Color | Trigger |
|---|---|---|
| `pass` | green (`#0f7a52`) | 0 fail, 0 warn |
| `warn` | amber (`#b45309`) | ≥ 1 warn, 0 fail |
| `fail` | red (`#b91c1c`) | ≥ 1 fail |
| `info` | blue (`#1a56db`) | validation_summary missing |

### HTML structure

```html
<div class="validation-summary-bar validation-summary-{tone}" role="status" aria-label="{label}">
  <span class="validation-summary-icon" aria-hidden="true">VS</span>
  <div class="validation-summary-body">
    <span class="validation-summary-title">{label}</span>
    <span class="validation-summary-desc">{description}</span>
  </div>
  {if last_validated_at}<span class="validation-summary-meta">Last checked: {timestamp}</span>{endif}
</div>
```

## Behavior

- Renders a compact bar (smaller than the UI-2.1 banner — `0.65rem` padding)
- Always renders (even when `validation_summary` is missing) — falls back to neutral info
- Does NOT compute financial logic in the template
- Does NOT imply external validation
- Optional `last_validated_at` shown on the right side when `validation_summary` is supplied

## Safe Copy Used

- "Validation checks need review" (when fail)
- "Items needing review" (when warn)
- "No blocking checks shown" (when pass)
- "Internal validation checks" (fallback)
- "Review status is shown per item below"
- "No blocking checks message is shown when all rows pass"
- "Last checked: {timestamp}"

## No-Go Copy Check

- ✓ No "bankable", "lender-ready", "certified", "audit-ready", "validated" (alone)
- ✓ No "investor-ready", "SaaS-ready", "production-ready"
- ✓ No "guaranteed returns", "investment advice", "customer reference"
- ✓ No "external validation"
- ✓ Safe terms: "validation checks", "review", "model evidence", "internal review"

## Hard Gates (UI-2.3)

- ✓ Only allowed files modified
- ✓ No backend/service/persistence changes
- ✓ No `runtime_impact_taxonomy.py` changes
- ✓ No `static/app.js` changes
- ✓ No `:root` CSS variable changes
- ✓ No new forbidden UI claims
- ✓ Phase 51F (21/21) + 52F G1-G6 (10/10) + 53I + 54x + UI-2.1 + UI-2.2 tests pass
- ✓ 50 new UI-2.3 tests pass
- ✓ 663 total tests pass
- ✓ rc1 (b425a07) untouched

## Visual Review Checklist

For the user (after PR is opened as DRAFT):

- [ ] Bar appears at top of audit/reconciliation tab (before `audit-disclaimer`)
- [ ] 4 tones render with correct color (green/amber/red/blue)
- [ ] When `validation_summary` is missing (current state), the bar shows neutral info copy
- [ ] Bar is compact and doesn't push other content down
- [ ] No regression in `audit-disclaimer` or other audit sections
- [ ] Accessible (role="status", aria-label, aria-hidden on icon)
- [ ] Icon "VS" visible
- [ ] No forbidden UI claims

## Test results

- `tests/test_ui2_3_*.py`: 50/50 pass
- `tests/test_ui2_1_*.py`: 56/56 pass
- `tests/test_ui2_2_*.py`: 50/50 pass
- `tests/test_phase54*.py`: 412/412 pass
- `tests/test_phase51f_*.py`: 21/21 pass
- `tests/test_phase52f_*.py`: 29/29 pass
- `tests/test_phase53i4_*.py`: 45/45 pass
- **Total: 663/663 pass**
