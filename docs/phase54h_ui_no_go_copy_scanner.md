# Phase 54H — UI No-Go Copy Scanner Specification

## Context

Phase 54H specifies a UI no-go copy scanner. The scanner is meant
to catch overclaiming UI language (e.g., "bankable", "lender-ready")
in templates, docs, and reports. **Optional test-only guardrail
allowed if robust. No runtime code changes.**

## Current Main SHA

`46adff407e2ee33aab2f0134e82b18bcc2bb46bd` (post-54G merge)

## Current state of forbidden terms in templates

Inspected forbidden terms in `app/templates/`:

| Term | Count in templates | Status |
|---|---:|---|
| bankable | 0 | clean |
| bank-grade | 0 | clean |
| lender-ready | 0 | clean |
| audit-ready | 0 | clean |
| investor-ready | 0 | clean |
| SaaS-ready | 1 | "Not SaaS-ready" — safe negation in `pilot_help_onboarding.html` |
| production-ready | 0 | clean |
| certified | 3 | all 3 are in negation/safety context |
| validated | 7 | **all in safe context** (see below) |

### Existing safe uses of "validated"

The 7 occurrences of "validated" in templates are all in safe
contexts:

1. `audit_reconciliation_tab.html:14` — "Generic projects remain
   exploratory and **unvalidated** unless separately reviewed."
   (negation)
2. `audit_reconciliation_tab.html:20` — "Validated pilot evidence"
   (section label — refers to the trusted-pilot evidence surface
   for TUHO/Oborovo)
3. `audit_reconciliation_tab.html:24` — "trusted pilot evidence
   surface for the **validated**" (qualified reference)
4. `audit_reconciliation_tab.html:153` — "Pending / **unvalidated** /
   future scope" (qualified — banner says unvalidated)
5. `audit_reconciliation_tab.html:157` — "intentionally separated
   from the **validated** pilot evidence above" (qualified)
6. `audit_reconciliation_tab.html:158` — "they are not **validated**
   frozen-template parity" (negation)
7. `audit_reconciliation_tab.html:165` — "UNVALIDATED" badge (label)
8. `audit_reconciliation_tab.html:174` — "Excluded from trusted
   pilot conclusions unless separately **validated**" (qualified)
9. `audit_reconciliation_tab.html:221` — "Validated parity applies
   to TUHO and Oborovo frozen-template paths only" (qualified)
10. `audit_reconciliation_tab.html:222` — "Generic wind and solar
    projects are **unvalidated** and exploratory" (negation)
11. `debt_dscr_shl_panel.html:30` — "remain exploratory and
    **unvalidated**" (negation)
12. `empty_states_notice.html:62` — "Generic project —
    **unvalidated** path" (qualified)
13. `empty_states_notice.html:63` — "not yet **validated** against
    Excel" (qualified)
14. `pilot_help_onboarding.html:25` — "Validated templates"
    (section label, refers to factory templates)
15. `pilot_help_onboarding.html:27` — "Validated templates"
    (section label)

**Conclusion:** The word "validated" appears extensively in **safe
context** in templates. It is the **Audit Reconciliation tab's
section label** and is used as a project-status descriptor (e.g.,
"validated frozen-template parity"). A naive scanner that flags
"validated" alone would produce **massive false positives**.

## Forbidden terms (canonical list, from 54C)

The 13 forbidden UI claims:

1. `bankable`
2. `bank-grade`
3. `lender-ready`
4. `lender-grade`
5. `certified` (allowed only in negation: "not certified", "is not a certified audit")
6. `audit-ready`
7. `audit-grade`
8. `validated` (allowed only in qualified or negated context; see allowed contexts)
9. `investor-ready`
10. `SaaS-ready`
11. `production-ready`
12. `external validation`
13. `customer reference`
14. `investment advice`
15. `guaranteed returns`

## Allowed contexts (false-positive policy)

The scanner must allow these patterns:

### For "validated"

**Allowed (no flag):**
- "validated frozen-template parity" (qualified)
- "validated pilot evidence" (qualified section label, used as project status)
- "Validated templates" (section label, refers to factory templates)
- "Validated parity" (section title)
- "UNVALIDATED" (badge label, negation)
- "unvalidated" (negation)
- "not validated against Excel" (negation)
- "validated against" (with object — describes the re-anchor action)
- "separately validated" (qualified)
- "validated by" (with agent — qualified)
- Any text where "validated" is preceded by "not", "un", or "separately"
- Any text where "validated" is followed by "frozen-template", "pilot", "parity", "templates", "Excel", "TUHO", "Oborovo"

**Flagged (positive claim):**
- "validated model" (alone, no qualifier)
- "validated calculation" (alone)
- "validated projection" (alone)
- "validated output" (alone)
- "validated by our team" (without "Excel", "TUHO", "Oborovo", "fixture", "frozen")
- "is validated" without a qualifier
- "we validate" or "validates that" without a specific Excel/anchor

### For "certified"

**Allowed (no flag):**
- "not certified audit"
- "not a certified external audit"
- "no certified"
- "[Not included] External audit / certification" (header)
- "certification" (only in negation)

**Flagged (positive claim):**
- "certified audit"
- "certified model"
- "certified output"
- "is certified"
- "we are certified"

### For other forbidden terms

**Allowed (no flag):**
- All terms in negation: "not bankable", "not lender-ready", "no SaaS-ready", etc.
- All terms in `[Not included]` sections
- All terms as the word "is" with "not" before
- All terms followed by "framework only" or "framework"

**Flagged (positive claim):**
- Any standalone positive use

## Scanning approach

### Target files

**Primary scope:** `app/templates/**/*.html`

**Optional scope (defer if too noisy):**
- `docs/**/*.md`
- `reports/**/*.json`
- `app/services/**/*.py` (only return values, not internal logic)
- `static/app.js` (only user-facing strings)

### Implementation

**Phase 1 (this PR): Spec only. No scanner yet.**

The scanner spec is documented. Implementation is deferred to a
follow-up phase (54H-2) to avoid blocking the UI-1/UI-2 work on
no-go scanner false-positive tuning.

**Rationale for deferral:**
- The 54C forbidden terms list is a **policy document**; the
  scanner is enforcement
- Current templates are already **clean** (no positive claims
  found; all uses are in qualified/negated context)
- A scanner with too many false positives would be a maintenance
  burden
- A scanner with too few rules would provide false security

### Recommended scanner architecture (for future 54H-2)

1. **Tokenize** template text into words
2. **Check for forbidden terms** as standalone tokens
3. **Check context** within ±20 words for negation/qualification
4. **Flag** only if no negation/qualification context found
5. **Allow** negation patterns: "not", "un", "no", "is not a", "not a", "[Not included]"
6. **Allow** qualification patterns: "frozen-template", "pilot evidence", "parity", "templates", "against Excel", "by TUHO", "by Oborovo", "by fixture", "by frozen"

### False positive strategy

**Primary strategy: Negation allow-list.**

If a forbidden term appears within ±20 words of any of these
patterns, it is allowed:

- `not`, `no`, `un-`, `framework only`, `[Not included]`, `is not`, `isn't`
- "validated" — additionally allowed near: "frozen-template", "pilot", "parity", "templates", "Excel", "TUHO", "Oborovo", "fixture", "separately"
- "certified" — additionally allowed near: "not", "no", "external audit", "certification"

**Secondary strategy: Whitelist phrases.**

The scanner maintains a list of explicitly allowed phrases that
contain forbidden terms but are known safe:

- "validated frozen-template parity"
- "Validated pilot evidence"
- "Validated templates"
- "Validated parity"
- "Not SaaS-ready"
- "not a certified audit"
- "Not certified"
- "UNVALIDATED"

These phrases are added to the whitelist when first encountered and
reviewed.

## Examples of allowed vs blocked copy

### Allowed

- "Validated pilot evidence" (section label, qualified)
- "Generic projects remain exploratory and unvalidated" (negation)
- "Not SaaS-ready" (negation)
- "Not a certified audit" (negation)
- "Validated against Excel" (qualified re-anchor)
- "Validated frozen-template parity" (qualified)
- "Validated by frozen schedule" (qualified by source)
- "UNVALIDATED" (badge label, negation)

### Blocked (would be flagged)

- "Bankable model" (positive claim, no qualifier)
- "Lender-ready" (positive claim)
- "Certified audit" (positive claim)
- "Validated model" (positive claim, no qualifier)
- "Production-ready" (positive claim)
- "Investor-ready" (positive claim)
- "Guaranteed returns" (positive claim)
- "Investment advice" (positive claim)

## Recommendation: implement now or defer?

**DEFER to 54H-2 (next phase) or UI-3.** Rationale:

1. **Current templates are clean** — no positive forbidden claims
   found in any template
2. **Scanner false-positive tuning is high effort** — requires
   carefully reviewing every "validated" usage in context
3. **UI-2 priority is implementation, not enforcement** — the
   54G boundaries already specify no-go checks per item
4. **No regression risk** — the 54F/54G work confirms no
   forbidden claims are in any of the planned new partials

**When to implement:**

- If UI-2 introduces a forbidden claim (caught by review)
- If a 54x PR adds a forbidden claim
- If a future phase requires automated enforcement

**Until then:** Manual no-go review per UI-2 PR is sufficient.

## How UI-2 PRs must use the scanner

**When implemented (in 54H-2 or later):**

1. Before opening a UI-2.x PR, run the scanner:
   ```
   python -m tests.test_phase54h_ui_no_go_copy_scanner
   ```
2. If any forbidden term is flagged, fix the copy or add to the
   whitelist with justification
3. CI must pass with the scanner integrated

**Until implemented (now):**

1. Use the manual no-go checklist in 54E § no-go copy checklist
2. Reference the 13 forbidden terms list from 54C
3. Each UI-2.x PR requires user review (per 54G) — this is the
   primary enforcement

## Hard Gates (54H)

- ✓ Only docs/report/test files added
- ✓ No templates/CSS/JS/services/persistence changes
- ✓ Branch based on post-54G main `46adff407e2ee33aab2f0134e82b18bcc2bb46bd`
- ✓ Current state of forbidden terms in templates documented
- ✓ Allowed contexts (false-positive policy) defined
- ✓ Scanning approach specified
- ✓ Recommendation to defer scanner implementation
- ✓ How UI-2 PRs use the scanner (current + future)
- ✓ rc1 (b425a07) untouched

## Files Created in 54H

- `docs/phase54h_ui_no_go_copy_scanner.md` (this file)
- `reports/phase54h_ui_no_go_copy_scanner.json`
- `tests/test_phase54h_ui_no_go_copy_scanner.py` (guardrail)
