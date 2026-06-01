# FincoGPT — Pilot Issue Triage Board Template

**Branch:** `phase43-pilot-ongoing-operations-issue-triage`
**Base SHA:** `07506503e0602e6a8d4bd940be56001b6201906a`
**Date:** 2026-06-01

Use this board to track all pilot issues from intake to resolution.

---

## Board Columns

| Column | Description |
|--------|-------------|
| **New** | Issues just filed, awaiting initial triage |
| **Needs clarification** | More information needed from reporter |
| **In review** | Triage owner investigating |
| **Accepted / known limitation** | Confirmed issue, deferred to future phase |
| **Fix planned** | Accepted, fix in development |
| **Resolved** | Fix verified and merged |
| **Out of scope** | Generic path, future feature, or not-yet-implemented |

---

## Issue Card Fields

Each issue card must include:

| Field | Description |
|-------|-------------|
| **Issue ID** | Assigned by triage owner (e.g., P43-001) |
| **Severity** | blocker / major / minor / clarification / out-of-scope / user-support |
| **Project** | TUHO / Oborovo / Generic / Other |
| **Scenario/version** | Named scenario or version used |
| **Last run timestamp** | Backend run timestamp from UI |
| **Reporter** | Name and contact |
| **Owner** | Assigned triage owner |
| **Status** | Current board column |
| **Decision** | Brief explanation of triage decision |
| **Next action** | Concrete next step with owner and due date |

---

## Board State

*Initial board state — updated as issues are filed.*

| Issue ID | Severity | Project | Status | Owner | Decision |
|----------|----------|---------|--------|-------|----------|
| P42-CLR-001 | clarification | Oborovo | Accepted / known limitation | Phase 40/42 sign-off team | Label vs stale anchor — runtime correct; documented in Phase 31C |

---

## Severity Reference

| Severity | SLA |
|----------|-----|
| blocker | Immediate (within 1h) |
| major | Within 4h |
| minor | Next business day |
| clarification | 3 business days |
| out-of-scope | Log and defer |
| user-support | Best effort |

---

## Triage Owner Responsibilities

- Monitor board daily for new issues
- Assign severity within 1h of filing
- Route to appropriate column
- Meet SLA or escalate
- Update status at each transition
- Log resolution in `docs/phase42_pilot_issue_log.md` (and subsequent phase logs)

---

## Adding a New Issue

1. Pilot user or operator fills `docs/pilot_issue_intake_template.md`
2. Operator creates card in **New** column with all required fields
3. Triage owner reviews within SLA and moves card to appropriate column
4. Every transition must update: Status, Owner, Next action, Date

---

## Resolved Issue Sign-Off

When an issue moves to **Resolved**, the triage owner must confirm:
- ✅ Fix applied and verified
- ✅ Test added if applicable
- ✅ Documentation updated
- ✅ Pilot continuation criteria still met
- ✅ Decision logged in issue log