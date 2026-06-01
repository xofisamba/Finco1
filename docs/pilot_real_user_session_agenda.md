# FincoGPT — Real-User Pilot Session Agenda

**Branch:** `phase45-pilot-feedback-capture-first-real-user-session`
**Base SHA:** `0c268c38bc0cc75c3830bd98eca8c491cd31a73b`
**Date:** 2026-06-01

Use this agenda to structure the first real-user pilot session.

---

## Session Purpose

To observe how a genuine pilot user interacts with FincoGPT under normal conditions — without script guidance or internal prompting. Capture authentic friction points, questions, and signals.

**This is not:**
- ❌ A bank/lender/audit/certification review
- ❌ A formal external reviewer sign-off
- ❌ A sales or demo presentation

**This is:**
- ✅ An internal controlled pilot observation session
- ✅ A real user attempting real tasks
- ✅ Feedback capture for pilot improvement

---

## Scope Disclaimer (Read Aloud to User Before Starting)

> "Before we start — FincoGPT is an internal pilot tool. The validated outputs are for TUHO and Oborovo projects only. Generic solar and wind projects are exploratory and not validated against Excel. Do not use generic project outputs for any financial decision. FincoGPT does not provide bank approval, lender approval, external audit, or certification. All outputs reflect the last clean backend run — not unsaved draft edits. Is that clear?"

Wait for user confirmation before proceeding.

---

## Pre-Session User Briefing

1. Explain the pilot scope: TUHO and Oborovo are validated; generic is exploratory
2. Explain draft/saved/runtime distinction: re-run after input changes before exporting
3. Explain exports reflect the last clean backend run
4. Explain Audit/Parity tab is internal review evidence — not certified audit
5. Confirm user has access to `docs/pilot_scope_confirmation_note.md`

---

## Project Selection

1. Ask the user to open FincoGPT
2. Observe: does the user know which project to select?
3. Observe: does the user understand the difference between TUHO, Oborovo, and generic?

---

## TUHO Walkthrough

Observe the user completing the following tasks on TUHO Wind (72 MW):

1. **Select TUHO project** — observe if user navigates correctly
2. **Review inputs** — observe if user checks capacity, tariff, CAPEX, OPEX
3. **Save a baseline scenario** — observe if user creates a named snapshot before changing anything
4. **Make a small input change** — observe what change is made
5. **Run the model** — observe if user clicks Run and waits for backend
6. **Interpret runtime summary** — ask: "What does this panel show you?"
7. **Export results** — observe if user re-runs after input change before exporting
8. **Review Audit/Parity tab** — ask: "What is this tab showing you? Is it an external audit?"

---

## Oborovo Walkthrough

Repeat the same walkthrough for Oborovo Solar (53.63 MW):

1. **Select Oborovo project**
2. **Review inputs**
3. **Save a baseline scenario**
4. **Make a small input change**
5. **Run the model**
6. **Interpret runtime summary**
7. **Export results**
8. **Review Audit/Parity tab**

---

## Save / Run / Export / Audit Workflow

Ask the user to explain in their own words:
- "What is the difference between a saved scenario and the last clean run?"
- "When would you re-run the model before exporting?"
- "What does the Audit/Parity tab tell you? Is it a certified audit?"

---

## Stale Output Explanation

Ask the user:
- "If you changed inputs but didn't re-run, what would the export show?"

Correct any misunderstandings without leading the answer.

---

## Generic Warning Explanation

Show the user a generic solar or wind project (if available) and ask:
- "Can you use outputs from this project for a financial decision?"

Expected answer: No — generic is unvalidated/exploratory.

---

## User Questions

Allow 10–15 minutes for free-form questions. Note:
- Which questions were asked most frequently?
- Which concepts caused the most confusion?
- Did the user ask about bank/lender/audit/certification?

---

## Feedback Capture

During the session, the operator fills `docs/pilot_feedback_form_template.md`.
After the session, the operator fills `docs/pilot_first_real_user_session_notes_template.md`.

**Do not fabricate user responses. Record only what was actually said or observed.**

---

## Issue Intake

If the user encounters an issue:
1. Note the exact behavior observed
2. File via `docs/pilot_issue_intake_template.md`
3. Classify severity using the Phase 43 triage SLA

---

## Closing Summary

At the end of the session:

1. Thank the user for their time
2. Confirm any issues filed
3. Remind the user: "Pilot outputs are internal review evidence only — not bank/lender/audit/certification"
4. Confirm the user knows how to file future issues via `docs/pilot_issue_intake_template.md`
5. Confirm the user received `docs/pilot_scope_confirmation_note.md`

---

## Session Metadata (Filled by Operator After)

| Field | Value |
|-------|-------|
| Session ID | |
| Date/time | |
| Participant role | |
| Operator | |
| Duration | |
| TUHO completed? | |
| Oborovo completed? | |
| Issues filed | |
| Continuation recommendation | |