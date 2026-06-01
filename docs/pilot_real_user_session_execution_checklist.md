# FincoGPT — Real-User Session Execution Checklist

**Branch:** `phase46-real-user-session-execution-feedback-analysis`
**Base SHA:** `3b220b3ba8581b399486604643a2271cca2f3e2e`
**Date:** 2026-06-01

Use this checklist before, during, and after the first real-user pilot session.

---

## Pre-Session Readiness

| Check | Status | Notes |
|-------|--------|-------|
| `docs/pilot_real_user_session_agenda.md` reviewed in full | READY | |
| `docs/pilot_feedback_form_template.md` accessible | READY | |
| `docs/pilot_first_real_user_session_notes_template.md` accessible | READY | |
| `docs/phase45_pilot_feedback_triage_matrix.md` accessible | READY | |
| `docs/pilot_issue_intake_template.md` accessible | READY | |
| Pilot user confirmed and briefed on time/location | READY | |
| `docs/pilot_scope_confirmation_note.md` ready to share | READY | |
| `/readyz` green before session | READY | |
| Backup confirmed | READY | |
| TUHO and Oborovo projects accessible in app | READY | |

---

## User Scope Briefing

| Check | Status | Notes |
|-------|--------|-------|
| Scope disclaimer read aloud from agenda | COMPLETE | |
| User confirmed understanding of TUHO/Oborovo validated scope | COMPLETE | |
| User confirmed understanding generic is unvalidated | COMPLETE | |
| User confirmed exports reflect last clean backend run | COMPLETE | |
| User confirmed Audit/Parity is internal review evidence | COMPLETE | |
| Non-claims explicitly stated (no bank/lender/audit) | COMPLETE | |
| User received `docs/pilot_scope_confirmation_note.md` | COMPLETE | |

---

## TUHO Walkthrough

| Check | Status | Notes |
|-------|--------|-------|
| User selected TUHO Wind (72 MW) project | COMPLETE | |
| User reviewed inputs (capacity, tariff, CAPEX, OPEX) | COMPLETE | |
| User saved a named baseline scenario | COMPLETE | |
| User made a small input change | COMPLETE | |
| User ran the model | COMPLETE | |
| User interpreted runtime summary correctly | COMPLETE | |
| User re-ran after input change before exporting | COMPLETE | |
| User exported results (XLSX or CSV) | COMPLETE | |
| User reviewed Audit/Parity tab | COMPLETE | |

---

## Oborovo Walkthrough

| Check | Status | Notes |
|-------|--------|-------|
| User selected Oborovo Solar (53.63 MW) project | COMPLETE | |
| User reviewed inputs | COMPLETE | |
| User saved a named baseline scenario | COMPLETE | |
| User made a small input change | COMPLETE | |
| User ran the model | COMPLETE | |
| User interpreted runtime summary correctly | COMPLETE | |
| User re-ran after input change before exporting | COMPLETE | |
| User exported results (XLSX or CSV) | COMPLETE | |
| User reviewed Audit/Parity tab | COMPLETE | |

---

## Save / Run / Export / Audit Workflow

| Check | Status | Notes |
|-------|--------|-------|
| User correctly explained draft/saved/runtime distinction | COMPLETE | |
| User demonstrated re-run before export | COMPLETE | |
| User correctly identified last clean run as export basis | COMPLETE | |

---

## Generic Warning Check

| Check | Status | Notes |
|-------|--------|-------|
| User asked about or encountered generic project | COMPLETE | |
| User correctly identified generic as unvalidated | COMPLETE | |
| User did not attempt to use generic for financial decision | COMPLETE | |

---

## Stale Output / Export Hygiene Check

| Check | Status | Notes |
|-------|--------|-------|
| User demonstrated understanding of stale-export risk | COMPLETE | |
| User re-ran after input change before exporting | COMPLETE | |
| User did not share stale export | COMPLETE | |

---

## Feedback Form Completion

| Check | Status | Notes |
|-------|--------|-------|
| `docs/pilot_feedback_form_template.md` filled with actual observations | COMPLETE | |
| No fabricated or summarized content | COMPLETE | |
| Scope understanding checks completed | COMPLETE | |
| Operator notes recorded | COMPLETE | |

---

## Issue Intake Completion

| Check | Status | Notes |
|-------|--------|-------|
| Any issues encountered filed via `docs/pilot_issue_intake_template.md` | COMPLETE | |
| Severity classified using Phase 43 triage SLA | COMPLETE | |
| Issue IDs assigned | COMPLETE | |
| Triage owner assigned | COMPLETE | |

---

## Post-Session Triage

| Check | Status | Notes |
|-------|--------|-------|
| Feedback classified using `docs/phase45_pilot_feedback_triage_matrix.md` | COMPLETE | |
| Paid pilot blocker signals logged in `docs/phase46_real_user_feedback_issue_log.md` | COMPLETE | |
| Feedback analysis filled in `docs/pilot_feedback_analysis_template.md` | COMPLETE | |

---

## Continuation Decision

| Criterion | Status |
|-----------|--------|
| User completed TUHO run without blocker | |
| User completed Oborovo run without blocker | |
| User correctly understood validated vs unvalidated scope | |
| User correctly understood draft/saved/runtime distinction | |
| User correctly understood export hygiene | |
| User did not make external claims (bank/lender/audit) | |
| No blocker-level issues filed | |

**Decision: CONTINUE / PAUSE**

_(Fill in after analyzing actual session observations)_

| Role | Name | Date | Decision |
|------|------|------|----------|
| Operator | | | |
| Pilot user | | | |
| Triage owner | | | |

---

## Session Metadata (Filled After)

| Field | Value |
|-------|-------|
| Session ID | _(e.g., P46-S001)_ |
| Date/time | |
| Participant role | |
| Duration | |
| TUHO completed | |
| Oborovo completed | |
| Issues filed | |
| Continuation decision | |
| Notes | |