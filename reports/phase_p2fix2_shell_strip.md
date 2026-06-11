# Phase P2-FIX-2 — Test Report

**Branch:** `p2-fix-2-shell-strip`
**Date:** 2026-06-11
**Author:** Mavis
**Status:** DRAFT PR #616 (not yet merged)

---

## 1. Test results

| Suite | Tests | Pass | Skip | Fail |
|---|---|---|---|---|
| `tests/test_phase_p2fix2_shell_strip.py` | 20 | 20 | 0 | 0 |

**20/20 PASS, 0 FAIL.**

Breakdown:

| Test class | Tests | All pass? |
|---|---|---|
| `TestShellStripNormalMode` | 6 | ✅ |
| `TestShellStripAuditSurfacePreserved` | 7 | ✅ |
| `TestShellStripNewProjectMinimal` | 1 | ✅ |
| `TestShellStripInvariants` | 4 | ✅ |
| `TestShellStripFileScope` | 1 | ✅ |
| `TestShellStripHiddenNotDeleted` | 2 | ✅ |

---

## 2. Before/after term exposure (rendered-route basis)

Each row was tested against the rendered HTML of the relevant route,
**not** template source. Forbidden terms are stripped from HTML
attributes (CSS classes, data-*, id, aria-*) — the test checks
user-visible text only.

| Term | Workspace overview (/?project=tuho) | Inputs (/inputs?project=tuho) | Scenarios (/scenarios?project=tuho) | Capex sheet (/sheet/capex?project=tuho) | Project Home (/) | Audit tab |
|---|---|---|---|---|---|---|
| factory | ❌ (relabeled) | ❌ (relabeled) | ❌ (relabeled) | ❌ (relabeled) | ❌ (relabeled) | n/a (relocated) |
| baseline | ❌ (relabeled) | ❌ (relabeled) | ❌ (relabeled) | ❌ (relabeled) | ❌ (relabeled) | n/a |
| parity | ❌ (relabeled) | ❌ (relabeled) | ❌ (relabeled) | ❌ (relabeled) | ❌ (relabeled) | n/a |
| calibration | ❌ (was not used) | ❌ | ❌ | ❌ | ❌ | n/a |
| golden | ❌ (was not used) | ❌ | ❌ | ❌ | ❌ | n/a |
| G20 | ❌ (audit_mode gated) | ❌ (gated) | ❌ | ❌ (gated) | ❌ | ✅ preserved |
| R99 | ❌ (audit_mode gated) | ❌ (gated) | ❌ | ❌ | ❌ | ✅ preserved |
| R102 | ❌ (audit_mode gated) | ❌ (gated) | ❌ | ❌ | ❌ | ✅ preserved |
| exploratory | ❌ (relabeled) | ❌ | ❌ (relabeled) | ❌ | ❌ | n/a |
| Lifecycle Clarity | ❌ (audit_mode gated) | ❌ | n/a | n/a | n/a | ✅ preserved |
| Export Lineage | ❌ (audit_mode gated) | ❌ | n/a | n/a | n/a | ✅ preserved |
| Governance Posture | ❌ (gated / rephrased) | ❌ | n/a | n/a | n/a | ✅ preserved |
| Review boundary | ❌ (audit_mode gated) | n/a | n/a | n/a | n/a | ✅ preserved |
| runtime source | ❌ (relabeled) | ❌ | n/a | n/a | n/a | ✅ preserved (audit) |

**Target: zero on normal-mode user routes, except TUHO/Oborovo as plain
project names. ✅ Achieved.**

---

## 3. Flow-walk evidence

The following routes were tested end-to-end with a logged-in client:

### Project Home (`GET /`)
- Renders consolidated project list
- "Internal-use model — results are indicative." line for generic projects
- No factory / baseline / parity / G20 / R99 / R102 terms

### Project workspace overview (`GET /?project=tuho`)
- Renders sidebar + tabs (Overview / Inputs / Scenarios / Construction /
  Production / Revenue / OPEX / CAPEX / Cash Flow / Balance Sheet /
  Distributions / Sponsor / Equity / Audit / Reference / Downloads /
  Compare / Help)
- Sidebar governance panel hidden in normal mode
- "Protected original — use Save As or create a scenario before editing
  controlled assumptions" lock indicator (relabeled)
- "Reference project" governance banner (relabeled)
- Status strip: Saved / Unsaved / Last run

### Inputs (`GET /inputs?project=tuho`)
- Inputs section renders without G20 / R99/R102 rows in normal mode
- Tax summary shows CIT Rate + Loss Carryforward only
- Section note points to "Audit / Reference tab for the reviewer notes"

### One output sheet — CAPEX (`GET /sheet/capex?project=tuho`)
- CAPEX sub-lines (16 categories) render with C.NN.U### business codes
- Badge "Reference project" (relabeled from data_source)
- No "parity workbooks" / "R99/R102" / "G20" terms

### Audit / Reference tab (`GET /?project=tuho` then tab=audit)
- Relocated content present:
  - Review boundary note
  - Lifecycle Clarity panel (Project state, Runtime state, Export state)
  - Export Lineage panel (Active project, Saved scenario, Last runtime,
    Runtime generated at, **Governance posture G20 BLOCKED / R99/R102 NOT
    APPROVED**)
  - Governance Status card (G20 Gate BLOCKED, R99/R102 Promotion NOT
    APPROVED, Equity IRR residual, Reference Evidence PASS/Senior
    Debt/SHL Opening/Distributions/Tax-CFADS)
- All preserved (no information loss)

---

## 4. Pinned invariants

- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved
- `use_construction_schedule_engine` = False (unchanged)
- 21/21 Phase 51F parity guardrails expected PASS (no schema/formula change)
- `factory_template` / `saved_baseline` literals still in `app/persistence/`
  (hidden != deleted, data model integrity)

---

## 5. Files touched (32 files)

- 1 partial new: `app/templates/partials/_audit_governance_relocated.html`
- 29 templates modified (presentation only)
- 2 UI services modified: `app/ui/dirty_state.py`, `app/ui/project_review.py`
- 1 route context modified: `main_web.py` (added `audit_mode` flag)
- 1 new test file: `tests/test_phase_p2fix2_shell_strip.py` (20 tests)
- 1 new doc: `docs/phase_p2fix2_shell_strip.md`
- 1 new report: `reports/phase_p2fix2_shell_strip.md`

Total diff: ~+850 / -180 lines (rough estimate; final line count in PR).

---

## 6. Stop-after-report

- PR #616 is **DRAFT**
- Do NOT mark ready
- Do NOT merge
- Do NOT start P2-FIX-3 until P2-FIX-2 is approved
