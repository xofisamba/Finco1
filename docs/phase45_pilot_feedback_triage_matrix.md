# Phase 45 — Pilot Feedback Triage Matrix

**Branch:** `phase45-pilot-feedback-capture-first-real-user-session`
**Base SHA:** `0c268c38bc0cc75c3830bd98eca8c491cd31a73b`
**Date:** 2026-06-01

---

## Feedback Triage Matrix

| Feedback Area | Signal to Capture | Severity Mapping | Action if Observed | Blocks Controlled Pilot? | Blocks Paid Pilot? | Follow-up Phase |
|---------------|-------------------|------------------|--------------------|-----------------------|-------------------|----------------|
| **Validated scope understanding** | User can correctly identify TUHO/Oborovo as validated and generic as unvalidated | Major if misunderstood; Minor if partially clear | Re-brief user on validated vs exploratory scope; update user guide if pattern emerges | No — if re-brief resolves | Yes — generic misunderstanding is paid pilot blocker | Phase 46 |
| **Generic boundary understanding** | User does not attempt to use generic outputs for financial decisions | Blocker if misused; Minor if confused | Immediate correction; document; re-brief user on non-claims | No — correction possible within session | Yes — generic misuse blocks paid pilot | Phase 46 |
| **Draft/saved/runtime confusion** | User correctly distinguishes draft edits, saved scenario, and last clean run | Major if confused; Minor if partially clear | Re-explain boundary; point to runtime summary notice; confirm re-run behavior | No — within-session correction possible | Yes — stale exports are paid pilot risk | Phase 46 |
| **Export hygiene** | User re-runs after input changes before exporting; understands last clean run boundary | Major if stale export used for decision; Minor if hesitation observed | Re-run demonstration; confirm export hygiene rules; document if pattern | No — correction possible | Yes — stale exports are paid pilot risk | Phase 46 |
| **Audit/reconciliation interpretation** | User understands Audit/Parity tab is internal review evidence, not certified audit | Major if misinterpreted as certified; Minor if unclear | Re-brief on internal review nature; point to audit disclaimer; confirm no external claims | No — correction possible | Yes — overclaiming is paid pilot risk | Phase 46 |
| **TUHO run confidence** | User completes TUHO run without error or external assistance | Blocker if cannot complete; Major if requires significant assistance | Operator assistance log; issue filing if blocking | Yes — if user cannot complete TUHO run | Yes — TUHO is core validated path | Phase 46 |
| **Oborovo run confidence** | User completes Oborovo run without error or external assistance | Blocker if cannot complete; Major if requires significant assistance | Operator assistance log; issue filing if blocking | Yes — if user cannot complete Oborovo run | Yes — Oborovo is core validated path | Phase 46 |
| **Scenario versioning** | User saves named scenario before changing inputs | Minor if skipped; Major if causes confusion | Remind user of scenario save step; confirm baseline before run | No — within-session correction possible | No | Phase 46 |
| **Backup/restore expectation** | User understands backup is available and restore is possible | Minor if unaware; Major if causes data loss fear | Brief on auto-backup and restore endpoint; confirm backup before first run | No | No | Phase 46 |
| **Issue intake flow** | User knows how to file issues via `docs/pilot_issue_intake_template.md` | Minor if unclear; Major if issues go unreported | Walk through issue intake template; confirm user has access | No | No | Phase 46 |
| **External claims / overclaiming risk** | User does not claim bank/lender/audit/certification based on pilot outputs | Blocker if external claims made; Major if near-claim observed | Immediate correction; log incident; re-brief non-claims; escalate to sign-off team | No — correction possible but must be logged | Yes — any external claim blocks paid pilot | Phase 43 escalation |
| **Paid pilot blocker feedback** | User identifies or encounters a paid pilot blocker (generic validation, IDC, C.16, M1-M18, etc.) | Major if encountered; Clarification if question only | Log as paid pilot blocker; route to Phase 40/42 issue log; do not resolve in controlled pilot | No | Yes — paid pilot blockers documented but not resolved | Phase 34 scope |

---

## Severity Reference

| Severity | Definition | Response SLA |
|----------|------------|--------------|
| **blocker** | User cannot complete core task OR external claim made | Immediate — within session |
| **major** | Significant misunderstanding or repeated errors | Within 4h — address before next session |
| **minor** | Minor friction or single hesitation | Next sprint |
| **clarification** | Question or confusion, not a blocking issue | Next sprint |
| **out-of-scope** | Generic path, future feature, paid pilot blocker | Log and defer |
| **user-support** | How-to, config, environment | Best effort |

---

## Pilot Continuation Decision

| Signal | Continuation | Notes |
|--------|-------------|-------|
| User completes TUHO/Oborovo runs without blocker | ✅ CONTINUE | Core paths functional |
| User correctly understands validated vs unvalidated scope | ✅ CONTINUE | Evidence threshold met |
| User does not make external claims | ✅ CONTINUE | Non-claims preserved |
| User cannot complete TUHO/Oborovo run | 🔴 PAUSE | Core path blocked |
| User misuses generic outputs for financial decisions | 🔴 PAUSE | Pause policy triggered |
| User makes external claims (bank/lender/audit) | 🔴 PAUSE | Non-claims breached |
| Multiple major misunderstandings despite re-brief | 🔴 PAUSE | User comprehension gap |

---

## Paid Pilot Blocker Tracking

| Blocker | Feedback Signal | Status |
|---------|-----------------|--------|
| Generic solar validation | User expects generic to work like TUHO/Oborovo | Not resolved |
| Generic wind validation | User attempts generic run without warning | Not resolved |
| Generic wind CO2 | User asks about CO2 for generic | Not wired |
| Construction IDC | User asks about construction-phase debt | Not wired |
| C.16 Project Rights | User asks about project rights treatment | Not wired |
| M1-M18 IDC | User asks about IDC during construction | Not wired |

---

**Status:** Framework — matrix is ready for use when first real-user session occurs.