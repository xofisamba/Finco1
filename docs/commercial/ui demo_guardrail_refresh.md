# UI No-Go Claim / Demo Guardrail Refresh

This file is the **UI no-go claim / demo guardrail
refresh**. It is the B-track governance wrapper for the
demo / commercial language after the UI improvements
(Phase 54A-56 and the pending Phase 57A LineItemGrid
CAPEX pilot).

> **UI polish does not mean production readiness. UI
> polish does not mean enterprise SaaS readiness.
> LineItemGrid pilot does not mean full spreadsheet
> engine. CAPEX summary pilot does not mean full model
> validation.**
>
> **The B1 no-go claim list, the B11 commercial
> guardrail, and the B22 Q&A matrix are the primary
> no-go claim artifacts. B38 is a UI-focused refresh
> that supplements the B1 / B11 / B22 guardrails with
> UI-specific guardrails.**

---

## 1. Allowed demo statements

The following statements are allowed in demo / commercial
contexts after the UI improvements. Each statement is
paired with a required caveat.

* **Allowed:** "The CAPEX summary grid is now rendered
  via the shared LineItemGrid partial."
  **Required caveat:** "The LineItemGrid is a UI
  refactor; the underlying financial model is
  unchanged."
* **Allowed:** "The runtime summary, validation summary,
  and banner context are now available on the index
  page."
  **Required caveat:** "The context wiring is a UI
  refactor; the underlying state is unchanged."
* **Allowed:** "The Help section has been moved into a
  dedicated section." (Per Phase 56B DRAFT.)
  **Required caveat:** "The Help section is a UI
  refactor; the underlying instructions are
  unchanged."
* **Allowed:** "The New Project form has been
  simplified." (Per Phase 56C DRAFT.)
  **Required caveat:** "The form simplification is a
  UI refactor; the required fields and validation are
  unchanged."
* **Allowed:** "The COD is now derived from
  construction_start_date and
  construction_duration_months." (Per Phase 56D.)
  **Required caveat:** "The COD derivation is a UI-side
  display calculation; the financial model is
  unchanged."
* **Allowed:** "The project switcher has been
  simplified." (Per Phase 56E DRAFT.)
  **Required caveat:** "The project switcher is a UI
  refactor; the project selection logic is unchanged."
* **Allowed:** "The state banner hierarchy has been
  polished." (Per Phase 56F DRAFT.)
  **Required caveat:** "The state banner is a UI
  refactor; the underlying state is unchanged."
* **Allowed:** "The route-render smoke and index
  context-contract tests are now in place." (Per
  Phase 57-pre.)
  **Required caveat:** "The tests are guardrails for
  the UI-3 work; they do not validate the underlying
  state or authorize any external claim."

## 2. Prohibited demo statements

The following statements are prohibited in demo /
commercial contexts. Each prohibition is paired with the
no-go claim category that it would violate.

* **Prohibited:** "Production-ready."
  **No-go claim category:** production-ready claim.
* **Prohibited:** "Enterprise SaaS-ready."
  **No-go claim category:** enterprise SaaS-readiness
  claim.
* **Prohibited:** "Bankable" / "lender-ready" /
  "auditable" / "certified" / "regulatory-approved".
  **No-go claim category:** lender / bank / audit /
  certification / regulatory claim.
* **Prohibited:** "Investment advice" / "guaranteed
  returns" / "investor-grade".
  **No-go claim category:** investment advice /
  guaranteed returns claim.
* **Prohibited:** "Customer reference" / "production
  customer" / "live customer" / "deployed at [customer
  name]".
  **No-go claim category:** customer reference claim.
* **Prohibited:** "The model is validated."
  **No-go claim category:** financial model validation
  claim.
* **Prohibited:** "The LineItemGrid is a full
  spreadsheet engine." / "The CAPEX summary pilot is
  the full model."
  **No-go claim category:** LineItemGrid / CAPEX
  summary pilot overclaim.
* **Prohibited:** "Paid pilot authorized" / "Pilot is
  running" / "Pilot is approved".
  **No-go claim category:** paid pilot authorization.
* **Prohibited:** "External validation completed" /
  "External reviewer approved" / "Audit passed".
  **No-go claim category:** external validation
  claim.
* **Prohibited:** "Generic solar / wind validated."
  **No-go claim category:** generic solar / wind
  validation claim.

## 3. Required caveats

The following caveats are required for any demo /
commercial statement that mentions the UI improvements:

* "The UI improvements do not change the financial
  model."
* "The UI improvements do not validate the engine
  output."
* "The UI improvements do not authorize paid pilot."
* "The UI improvements do not constitute external
  validation."
* "The LineItemGrid is a UI refactor; the underlying
  financial model is unchanged."
* "The CAPEX summary pilot is a single-sheet pilot;
  it is not the full UI-3 rollout."
* "The CAPEX summary pilot does not constitute model
  validation."
* "Generic solar and wind remain exploratory and
  unvalidated."
* "G20 remains BLOCKED."
* "R99 and R102 remain NOT APPROVED."

## 4. Escalation triggers

The following triggers require an immediate escalation
to the user. The B38 guardrail does not authorize Agent B
to act on the escalation; Agent B flags the escalation
to the user.

* Any prohibited demo statement is made in a demo /
  commercial context (e.g., a README, a customer
  presentation, a marketing email, a public website).
* Any required caveat is missing from an allowed
  statement.
* The LineItemGrid pilot is described as a "full
  spreadsheet engine" or the "full model".
* The CAPEX summary pilot is described as "model
  validation" or "external validation".
* The paid pilot is described as "authorized" or
  "running".
* The external review is described as "completed" or
  "approved".
* Generic solar / wind is described as "validated" or
  "production-ready".
* The UI improvements are described as "production-
  ready" or "enterprise SaaS-ready".
* The customer reference is made.
* The Claude review or post-51T review is referenced as
  external validation or certification.

## 5. Mapping to existing no-go claims

B38 maps to the existing no-go claim artifacts as
follows:

* **B1 no-go claim list** (`docs/external_review/no_go_claims.md`):
  the canonical no-go claim list. B38 supplements
  B1 with UI-specific guardrails.
* **B11 commercial guardrail**
  (`docs/commercial/no_go_claims_commercial_guardrail.md`):
  the commercial / demo guardrail. B38 supplements
  B11 with UI-specific guardrails.
* **B19 demo claims checklist**
  (`docs/commercial/demo_claims_checklist.json`):
  the demo claims checklist. B38 supplements B19 with
  UI-specific guardrails.
* **B22 Q&A matrix** (`docs/commercial/qa_claims_matrix.json`):
  the Q&A matrix. B38 supplements B22 with UI-specific
  guardrails.
* **B1, B11, B19, B22 remain the primary no-go claim
  artifacts.** B38 is a UI-focused refresh, not a
  replacement.

## 6. UI polish does not mean production readiness

UI polish is a UI refactor. UI polish:

* Does not change the financial model.
* Does not validate the engine output.
* Does not authorize paid pilot.
* Does not constitute external validation.
* Does not authorize production rollout.
* Does not authorize enterprise SaaS rollout.
* Does not relax any no-go claim.
* Does not constitute customer reference.
* Does not constitute model validation.

## 7. UI polish does not mean enterprise SaaS readiness

UI polish is a UI refactor. The enterprise SaaS
readiness dimension (B8) is unchanged by the UI polish.
The enterprise SaaS readiness tracker records the
post-UI-2 architecture percentage and the post-UI-2
operational dimensions; the UI polish is a sub-
dimension of the architecture percentage and does not
change the operational or commercial dimensions.

## 8. LineItemGrid pilot does not mean full spreadsheet engine

The LineItemGrid pilot (Phase 57A) is a single-sheet
pilot. It migrates only
`app/templates/partials/sheet_capex.html` to the shared
LineItemGrid partial/macro. The LineItemGrid pilot is
not:

* A full spreadsheet engine.
* A replacement for the underlying financial model.
* A replacement for the underlying engine.
* A replacement for the underlying persistence layer.
* A full UI-3 rollout.

A future UI-3 rollout would migrate the other sheets
(per the B40 UI-3 migration governance plan).

## 9. CAPEX summary pilot does not mean full model validation

The CAPEX summary pilot (Phase 57A) is a UI refactor
that migrates the CAPEX summary grid to the shared
LineItemGrid partial/macro. The CAPEX summary pilot is
not:

* A full model validation.
* An external validation.
* A pin of the underlying model outputs.
* A replacement for the parity-core lock.
* A replacement for the engine-output golden.

The CAPEX summary pilot does not change the financial
model. The parity-core lock is unchanged. The engine-
output golden is unchanged.

## 10. No-go claim categories (preserved from B1)

The following no-go claim categories are preserved from
the B1 no-go claim list and are not relaxed by the UI
polish:

* **Lender reliance:** no.
* **Audit:** no.
* **Certification:** no.
* **Regulatory approval:** no.
* **SaaS claim:** no.
* **Investment advice:** no.
* **Guaranteed returns:** no.
* **Customer reference:** no.
* **Production readiness:** no.
* **Enterprise SaaS readiness:** no.
* **Bankability:** no.

## 11. Generic solar / wind remains exploratory and unvalidated

Generic solar / wind remain exploratory and unvalidated.
The UI polish does not validate generic solar / wind.
The generic solar / wind pilot is not authorized.

## 12. G20 remains BLOCKED

G20 remains BLOCKED. The UI polish does not promote
G20. G20 is the gate for the senior debt / loan
amortization / cash sweep; it is unaffected by the UI
polish.

## 13. R99 / R102 remain NOT APPROVED

R99 (sponsor cashflows double-count fix validation) and
R102 (sponsor distribution handoff contract) remain NOT
APPROVED. The UI polish does not promote R99 or R102.

## 14. What B38 is not

* B38 is not a code change. Agent B does not implement
  UI code.
* B38 is not a replacement for the B1 no-go claim list.
* B38 is not a replacement for the B11 commercial
  guardrail.
* B38 is not a replacement for the B19 demo claims
  checklist.
* B38 is not a replacement for the B22 Q&A matrix.
* B38 is not external validation.
* B38 is not a paid pilot authorization.
* B38 is not a customer reference.
* B38 is not a production readiness claim.
* B38 is not an enterprise SaaS readiness claim.
* B38 is not a financial model validation.
* B38 is not a substitute for the user's demo
  decisions or the user's marketing decisions.

## 15. Cross-references

* `reports/commercial/ui demo_guardrail_refresh.json` (B38,
  machine-readable)
* `docs/governance/post_phase56_ui_governance_refresh.md`
  (B35)
* `docs/ui/phase57a_line_item_grid_visual_review.md` (B36)
* `docs/validation/ui_regression_evidence_matrix.md` (B37)
* `docs/pilot/controlled_pilot_ux_runbook.md` (B39)
* `docs/governance/ui3_line_item_grid_migration_governance_plan.md`
  (B40)
* `docs/external_review/no_go_claims.md` (B1)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/commercial/demo_claims_checklist.json` (B19)
* `docs/commercial/qa_claims_matrix.json` (B22)
* `docs/commercial/approved_demo_language.md` (B11)

---

*End of UI no-go claim / demo guardrail refresh.*
