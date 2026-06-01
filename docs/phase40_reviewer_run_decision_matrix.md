# Phase 40 — Reviewer Run Decision Matrix

**Base SHA:** `36f278d946a7f51ffd534176e3320efe49c6d2b8`
**Date:** 2026-06-01

---

## Decision Matrix

| Area | Finding | Severity | Evidence | Decision | Required before trusted pilot? | Required before paid pilot? | Next action |
|------|---------|----------|----------|----------|-------------------------------|-----------------------------|-------------|
| TUHO senior debt | 43,359 kEUR — matches Excel fixture, within ±1% tolerance | Info | Phase 23f fixture; Phase 35 calibration | APPROVED — frozen path confirmed | No | No | None |
| TUHO CO2 | Y1=611 kEUR, co2_enabled=True, co2_price=4.191 EUR/MWh — part of validated frozen scope | Info | Phase 29A deep dive; Phase 35 validation | APPROVED — CO2 revenue correctly wired | No | No | None |
| TUHO DSCR trajectory | Avg DSCR=1.682 — within ±0.05 of Excel 1.451 (advisory tolerance) | Info | Phase 35 calibration; test_tuho_shl_calibration | APPROVED — frozen path confirmed | No | No | None |
| Oborovo senior debt | 42,852 kEUR — matches Excel fixture, within ±1% tolerance | Info | Phase 23q fixture; Phase 35 calibration | APPROVED — frozen path confirmed | No | No | None |
| Oborovo SHL opening | ~15,790 kEUR (SHL amount 14,621 kEUR + IDC 1,169 kEUR) — confirmed | Info | Phase 23k/23l; Phase 31C | APPROVED — SHL opening correctly set | No | No | None |
| Oborovo OpEx | Y1=1,338 kEUR — exact match with Excel; double-count resolved | Info | Phase 31 deep dive; Phase 35 calibration | APPROVED — OpEx correctly computed | No | No | None |
| Oborovo first distribution / lock-up | op_idx 39 / 2050-06-30 — first valid distribution confirmed | Info | Phase 23h/o; Phase 31C | APPROVED — distribution lock-up policy correct | No | No | None |
| Generic solar/wind exclusion | Both excluded from Pilot RC validated scope; no Excel reference exists | Info | Phase 34 boundary doc; Phase 35 scope matrix | CONFIRMED — generic remains exploratory | N/A (explicitly excluded) | Yes — blockers exist | Phase 34A/34B future work |
| Audit/export trust surface | Validated evidence clearly separated from pending/unvalidated scope | Info | Phase 38 polish doc; Phase 39 package | APPROVED — trust surface correctly structured | No | No | None |
| Last clean backend run boundary | Backend is source of truth; exports tied to last clean run | Info | Phase 38; Phase 39 manifest | APPROVED — backend boundary confirmed | No | No | None |
| Non-claims | No bank/lender/audit/certification/SaaS/enterprise claims made | Info | Phase 39 non-claims list; all docs | CONFIRMED — non-claims language strong | No | No | None |
| G20/R99/R102 gates | G20 BLOCKED; R99/R102 NOT APPROVED — unchanged | Info | Phase 35; Phase 36 | CONFIRMED — guardrails intact | No | No | None |
| Backup/restore expectations | SQLite backup/restore validated (Phase 24F); auto-backup (Phase 24F1) | Info | Phase 24F/F1 docs | APPROVED — backup infrastructure confirmed | No | No | None |
| SaaS/enterprise readiness | Explicitly not claimed; strong non-claims language throughout | Info | Phase 39 non-claims; all review docs | CONFIRMED — no such claims made | No | No | None |
| Oborovo equity IRR runtime | Runtime (~6.24%) vs stale anchor (~9.88%) — known Phase 31C artefact, no defect | clarification | Phase 31C investigation; Phase 23n post-correction snapshot | ACTION — add caveat to equity IRR export labels | No (labelling improvement only) | Recommended before paid pilot | Add runtime-vs-anchor caveat to Oborovo equity IRR label in exports |

---

## Summary

| Category | Count |
|----------|-------|
| APPROVED | 13 |
| CONFIRMED (guardrails/non-claims) | 4 |
| ACTION (labelling improvement) | 1 |
| BLOCKED (paid pilot only) | 5 (generic + IDC + C.16) |

---

## Trusted Pilot Go/No-Go

**GO ✅ — No blocker found for controlled trusted pilot within TUHO/Oborovo frozen-template scope.**

The single action item (Oborovo equity IRR export label caveat) is a labelling improvement, not a blocker. All TUHO and Oborovo frozen-template metrics are approved. All guardrails and non-claims are confirmed intact.

---

## Paid Pilot Blockers

| Item | Blocking Paid Pilot? | Path to Resolution |
|------|---------------------|-------------------|
| Generic solar Excel reference | Yes | Phase 34A — requires Excel reference model acquisition |
| Generic wind Excel reference | Yes | Phase 34B — requires Excel reference model acquisition |
| Generic wind CO2 validation | Yes | Phase 34B — requires generic wind reference model |
| Construction IDC | Yes | Out of scope for pilot — requires dedicated phase |
| C.16 Project Rights | Yes | Out of scope for pilot — requires dedicated phase |