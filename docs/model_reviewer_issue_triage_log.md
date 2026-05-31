# Model Reviewer Issue Triage Log

**Base SHA:** `36f278d946a7f51ffd534176e3320efe49c6d2b8`
**Review date:** 2026-06-01
**Reviewer:** Claude (Phase 40 internal AI reviewer)

---

## Severity Guidance

- `blocker` — reviewer cannot complete or sign off on the scoped review without resolution
- `major` — materially affects confidence in an in-scope validated claim
- `minor` — useful correction or clarification, but not a blocker to scoped review
- `clarification` — reviewer needs explanation or reference, not necessarily a defect
- `expected convention difference` — difference is known and expected under frozen-path architecture
- `out-of-scope` — observation is outside validated review scope and should not be escalated as an in-scope defect

---

## Issue Log

| Issue ID | Reviewer | Date | Area | Project | Metric / period | Observation | Severity | Evidence/source | Proposed classification | Owner response | Status |
|----------|----------|------|------|---------|-----------------|-------------|----------|-----------------|-------------------------|----------------|--------|
| REV-001 | Claude | 2026-06-01 | Equity IRR | Oborovo | Equity IRR runtime | Runtime equity IRR ~6.24% differs from stale Phase 29 anchor ~9.88%. Phase 31C investigation confirmed no runtime defect — the anchor was pre-computation. Runtime figure is correct when scenario overrides are applied. | clarification | Phase 31C investigation doc; Phase 23 post-correction snapshot | Known calibration artefact. No runtime defect. Exports should note caveat. | Acknowledged — Phase 31C confirmed no defect. Caveat should be added to export labels. | OPEN — recommend adding caveat to equity IRR export labels |
| REV-002 | Claude | 2026-06-01 | Scope | Generic wind | CO2 | Generic wind CO2 treatment is not validated. No Excel reference model exists. | out-of-scope | Phase 34 generic validation boundary doc; Phase 35 pilot RC scope matrix | Explicitly excluded from pilot RC scope. Not a defect. | N/A — already excluded | CLOSED — out of scope |
| REV-003 | Claude | 2026-06-01 | Scope | Construction | IDC | Construction IDC runtime not wired; M1-M18 IDC not implemented. | out-of-scope | Phase 35 pilot RC scope matrix | Explicitly excluded from pilot RC scope. Not a defect. | N/A — already excluded | CLOSED — out of scope |

---

## Summary

| Severity | Count | Status |
|----------|-------|--------|
| blocker | 0 | No blocker found for controlled trusted pilot within TUHO/Oborovo frozen-template scope. |
| major | 0 | None identified |
| minor | 0 | None identified |
| clarification | 1 | REV-001: Oborovo equity IRR caveat — recommend export label improvement |
| expected convention difference | 0 | None |
| out-of-scope | 2 | REV-002: generic wind CO2; REV-003: construction IDC |

---

## No Blocker Found

**No blocker found for controlled trusted pilot within TUHO/Oborovo frozen-template scope.**

The single clarification item (REV-001) is a known artefact documented in Phase 31C and does not prevent sign-off on the frozen-template scope. The recommendation is to add a caveat to Oborovo equity IRR export labels, but this is a minor labelling improvement, not a blocker.

---

## Paid Pilot Blockers (Informational)

The following would need to be resolved before a **paid pilot**:

| Item | Severity | Notes |
|------|----------|-------|
| Generic solar validation | Blocker | No Excel reference model exists |
| Generic wind validation | Blocker | No Excel reference model exists |
| Generic wind CO2 | Blocker | Not validated |
| Construction IDC | Blocker | Not wired |
| C.16 Project Rights | Blocker | Not wired |
| Bank/lender approval | N/A | Never claimed — out of scope |

None of these block the **controlled trusted pilot** which is scoped to TUHO + Oborovo frozen templates only.