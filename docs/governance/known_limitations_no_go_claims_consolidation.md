# Known Limitations / No-Go Claims Consolidation

This file is the **known limitations / no-go claims
consolidation**. It is the B-track governance wrapper
for the consolidated list of known limitations and
no-go claims after the UI governance arc (B35-B40,
PR #489) and the Generic Modelling Loop arc (B41-B47,
PR #588).

> **This consolidation is the B-track governance
> wrapper. The primary no-go claim artifacts
> remain B1, B11, B19, B22, B38, B44. B51 supplements
> (does not replace) those artifacts.**

---

## 1. Known limitations

The following are known limitations of the Finco1
product at the time of B51 authoring.

### 1.1 Model limitations

* **item_id:** KL-01.
* **statement:** Generic Solar output is not
  Excel-parity validated against a reference solar
  model.
* **rationale:** No reference solar model is
  available.
* **affected_area:** Generic Solar output.
* **permitted_wording:** "Generic Solar is exploratory
  and unvalidated. The exploratory banner is
  required."
* **prohibited_wording:** "Generic Solar is
  validated" / "Generic Solar is Excel-parity
  validated".
* **evidence_source:** B41, B44.
* **next_review_trigger:** After first real Generic
  Solar reference model.

* **item_id:** KL-02.
* **statement:** Generic Wind output is not
  Excel-parity validated against a reference wind
  model.
* **rationale:** No reference wind model is
  available.
* **affected_area:** Generic Wind output.
* **permitted_wording:** "Generic Wind is exploratory
  and unvalidated. The exploratory banner is
  required."
* **prohibited_wording:** "Generic Wind is
  validated" / "Generic Wind is Excel-parity
  validated".
* **evidence_source:** B41, B44.
* **next_review_trigger:** After first real Generic
  Wind reference model.

* **item_id:** KL-03.
* **statement:** Generic Solar / Wind defaults are
  not market-validated assumptions.
* **rationale:** No market validation has been
  performed.
* **affected_area:** Generic Solar / Wind defaults.
* **permitted_wording:** "Generic Solar / Wind
  defaults are illustrative until validated by
  reference models."
* **prohibited_wording:** "Generic Solar / Wind
  defaults are market-validated" / "Generic Solar /
  Wind defaults are industry-standard".
* **evidence_source:** B41, B44.
* **next_review_trigger:** After first real Generic
  Solar / Wind reference model.

### 1.2 Generic Solar / Wind limitations

* **item_id:** KL-04.
* **statement:** Generic Solar / Wind are
  exploratory and unvalidated.
* **rationale:** The Generic Solar / Wind templates
  are not validated against reference models.
* **affected_area:** Generic Solar / Wind
  templates.
* **permitted_wording:** "Generic Solar / Wind are
  exploratory. The exploratory banner is required."
* **prohibited_wording:** "Generic Solar / Wind are
  validated" / "Generic Solar / Wind are Excel-
  parity validated".
* **evidence_source:** B41, B44.
* **next_review_trigger:** Per B47 cadence plan.

### 1.3 Tax limitations

* **item_id:** KL-05.
* **statement:** Tax calculations are not the focus
  of the Generic Modelling / Scenario Loop arc. The
  tax calculations are unchanged by the Generic
  Modelling arc.
* **rationale:** The Generic Modelling arc is a UI +
  minimal metadata-persistence rotation. The tax
  calculations are the Agent A implementation; the
  B-track governance records the tax calculations
  as unchanged.
* **affected_area:** Tax calculations.
* **permitted_wording:** "Tax calculations are
  unchanged by the Generic Modelling arc."
* **prohibited_wording:** "Tax calculations are
  validated by the Generic Modelling arc".
* **evidence_source:** B41, B43.
* **next_review_trigger:** Per tax-related phase.

### 1.4 Debt limitations

* **item_id:** KL-06.
* **statement:** Debt calculations are not the
  focus of the Generic Modelling / Scenario Loop
  arc. The debt calculations are unchanged by the
  Generic Modelling arc. G20 remains BLOCKED.
* **rationale:** The Generic Modelling arc is a UI +
  minimal metadata-persistence rotation. G20 is the
  gate for the senior debt / loan amortization /
  cash sweep; it is unaffected by the Generic
  Modelling arc.
* **affected_area:** Debt calculations.
* **permitted_wording:** "Debt calculations are
  unchanged by the Generic Modelling arc. G20
  remains BLOCKED."
* **prohibited_wording:** "G20 is approved" / "G20
  is promoted".
* **evidence_source:** B41, B43.
* **next_review_trigger:** Per G20 promotion.

### 1.5 CAPEX / LineItemGrid limitations

* **item_id:** KL-07.
* **statement:** The CAPEX summary grid (Phase 57A
  LineItemGrid) is a UI refactor. The underlying
  financial model is unchanged.
* **rationale:** The LineItemGrid is a UI refactor.
  The financial model is unchanged.
* **affected_area:** CAPEX summary grid.
* **permitted_wording:** "The LineItemGrid CAPEX
  summary is a UI refactor. The underlying financial
  model is unchanged."
* **prohibited_wording:** "The LineItemGrid is a
  full spreadsheet engine" / "The LineItemGrid is
  a replacement for the underlying financial
  model".
* **evidence_source:** B35, B36, B40.
* **next_review_trigger:** After first UI-3
  migration PR.

### 1.6 UI limitations

* **item_id:** KL-08.
* **statement:** UI polish does not mean production
  readiness. UI polish does not mean enterprise
  SaaS readiness.
* **rationale:** UI polish is a UI refactor. UI
  polish does not change the financial model, does
  not validate the engine output, does not
  authorize paid pilot.
* **affected_area:** UI.
* **permitted_wording:** "UI polish is a UI
  refactor."
* **prohibited_wording:** "UI polish is production-
  ready" / "UI polish is enterprise SaaS-ready".
* **evidence_source:** B35, B38.
* **next_review_trigger:** Per PR / Phase.

### 1.7 Persistence limitations

* **item_id:** KL-09.
* **statement:** The persistence rotation in
  `update_scenario_last_run_summary` is minimal
  and scoped. No schema migration. No new columns.
  No data backfill.
* **rationale:** The persistence rotation is the
  Agent A implementation; the B-track governance
  records the rotation as a fact.
* **affected_area:** Persistence.
* **permitted_wording:** "The persistence rotation
  is minimal and scoped."
* **prohibited_wording:** "The persistence
  rotation is a schema migration" / "The
  persistence rotation requires data backfill".
* **evidence_source:** B41, B43.
* **next_review_trigger:** Per PR / Phase.

### 1.8 Scenario compare limitations

* **item_id:** KL-10.
* **statement:** The scenario compare is internal
  functionality, not model validation.
* **rationale:** The compare is a side-by-side view
  of existing run summaries. The compare does not
  validate the engine.
* **affected_area:** Scenario compare.
* **permitted_wording:** "The scenario compare is
  internal functionality."
* **prohibited_wording:** "The scenario compare
  validates the model" / "The scenario compare is
  a model validation".
* **evidence_source:** B41, B44.
* **next_review_trigger:** Per B47 cadence plan.

### 1.9 What Changed limitations

* **item_id:** KL-11.
* **statement:** The "What Changed" deltas are
  explanatory, not guaranteed accuracy claims. The
  exploratory banner is required for Generic Solar
  / Wind.
* **rationale:** The deltas are computed via
  subtraction and percentage on the existing run
  summary data. The deltas are explanatory.
* **affected_area:** What Changed panel.
* **permitted_wording:** "The What Changed deltas
  are explanatory."
* **prohibited_wording:** "The What Changed deltas
  are investment advice" / "The What Changed deltas
  are guaranteed returns" / "The What Changed
  deltas are guaranteed accuracy claims".
* **evidence_source:** B41, B43, B44.
* **next_review_trigger:** Per B47 cadence plan.

### 1.10 Export / download limitations

* **item_id:** KL-12.
* **statement:** The export / download pack is
  internal artifact generation, not bankability.
* **rationale:** The export / download pack is the
  internal artifact generation for Generic
  scenarios. The export / download pack does not
  constitute a bankable artifact.
* **affected_area:** Export / download pack.
* **permitted_wording:** "The export / download
  pack is internal artifact generation."
* **prohibited_wording:** "The export / download
  pack is bankable" / "The export / download pack
  is a bankable artifact".
* **evidence_source:** B41, B44.
* **next_review_trigger:** Per B47 cadence plan.

### 1.11 External validation limitations

* **item_id:** KL-13.
* **statement:** No external validation has
  occurred.
* **rationale:** External review is a separate
  workstream. External review has not been
  performed.
* **affected_area:** External validation.
* **permitted_wording:** "External review has not
  occurred."
* **prohibited_wording:** "External validation has
  been completed" / "External review is approved".
* **evidence_source:** B1, B11, B22.
* **next_review_trigger:** After first external
  reviewer feedback.

### 1.12 SaaS / product limitations

* **item_id:** KL-14.
* **statement:** The enterprise SaaS readiness
  dimension is not claimed. The B8 enterprise SaaS
  readiness tracker is the primary record.
* **rationale:** The enterprise SaaS readiness is
  governed by the B8 / B17 / B25 / B33 artifacts.
* **affected_area:** Enterprise SaaS readiness.
* **permitted_wording:** "Enterprise SaaS readiness
  is not claimed."
* **prohibited_wording:** "Enterprise SaaS-ready".
* **evidence_source:** B8, B17, B25, B33.
* **next_review_trigger:** Per enterprise readiness
  development.

### 1.13 Pilot / commercial limitations

* **item_id:** KL-15.
* **statement:** Paid pilot is not authorized.
  Customer reference is not made. Production
  readiness is not claimed. Enterprise SaaS
  readiness is not claimed.
* **rationale:** Paid pilot is governed by the
  B25 / B33 / B35 stop / go checklists and the B45
  controlled pilot runbook. Customer reference is
  not made by the controlled pilot.
* **affected_area:** Paid pilot, customer reference,
  production readiness, enterprise SaaS readiness.
* **permitted_wording:** "Paid pilot is not
  authorized."
* **prohibited_wording:** "Paid pilot is authorized"
  / "Customer reference is available" / "Production-
  ready" / "Enterprise SaaS-ready".
* **evidence_source:** B1, B11, B19, B22, B38, B44.
* **next_review_trigger:** Per B47 cadence plan.

## 2. No-go claim categories

The following are the no-go claim categories. Each
category is preserved from the B1 / B11 / B19 / B22
/ B38 / B44 no-go claim artifacts and is not
relaxed by the Generic Modelling / Scenario Loop arc.

* **item_id:** NG-01.
* **statement:** No bankability claim.
* **rationale:** No reference solar / wind model is
  available. No external validation has occurred.
* **affected_area:** Bankability.
* **permitted_wording:** "The product is not
  bankable."
* **prohibited_wording:** "The product is bankable"
  / "The product is lender-ready".
* **evidence_source:** B1, B11, B19, B22, B38, B44.
* **next_review_trigger:** Per external validation
  completion.

* **item_id:** NG-02.
* **statement:** No lender reliance claim.
* **rationale:** No reference solar / wind model is
  available. No external validation has occurred.
* **affected_area:** Lender reliance.
* **permitted_wording:** "The product is not
  lender-ready."
* **prohibited_wording:** "The product is lender-
  ready" / "Lenders rely on the product".
* **evidence_source:** B1, B11, B19, B22, B38, B44.
* **next_review_trigger:** Per external validation
  completion.

* **item_id:** NG-03.
* **statement:** No audit / certification claim.
* **rationale:** No external validation has
  occurred. No audit has been performed.
* **affected_area:** Audit / certification.
* **permitted_wording:** "The product is not
  audited" / "The product is not certified".
* **prohibited_wording:** "The product is audited"
  / "The product is certified".
* **evidence_source:** B1, B11, B19, B22, B38, B44.
* **next_review_trigger:** Per external validation
  completion.

* **item_id:** NG-04.
* **statement:** No regulatory approval claim.
* **rationale:** No regulatory approval has been
  obtained.
* **affected_area:** Regulatory approval.
* **permitted_wording:** "The product is not
  regulatory-approved."
* **prohibited_wording:** "The product is
  regulatory-approved".
* **evidence_source:** B1, B11, B19, B22, B38, B44.
* **next_review_trigger:** Per regulatory approval
  process.

* **item_id:** NG-05.
* **statement:** No paid pilot authorization.
* **rationale:** Paid pilot is governed by the
  B25 / B33 / B35 stop / go checklists and the B45
  controlled pilot runbook.
* **affected_area:** Paid pilot.
* **permitted_wording:** "Paid pilot is not
  authorized."
* **prohibited_wording:** "Paid pilot is
  authorized" / "Paid pilot is running".
* **evidence_source:** B1, B11, B19, B22, B38, B44.
* **next_review_trigger:** Per paid pilot gate
  review.

* **item_id:** NG-06.
* **statement:** No customer reference.
* **rationale:** The controlled pilot is internal
  governance; it does not create a customer
  reference.
* **affected_area:** Customer reference.
* **permitted_wording:** "The controlled pilot is
  internal, not a customer reference."
* **prohibited_wording:** "Customer reference is
  available" / "Live customer" / "Deployed at
  [customer name]".
* **evidence_source:** B1, B11, B19, B22, B38, B44.
* **next_review_trigger:** Per customer reference
  process.

* **item_id:** NG-07.
* **statement:** No production-ready claim.
* **rationale:** The product is not production-
  ready. The production-readiness dimension is
  governed by the B8 / B17 / B25 / B33 artifacts.
* **affected_area:** Production readiness.
* **permitted_wording:** "The product is not
  production-ready."
* **prohibited_wording:** "The product is
  production-ready".
* **evidence_source:** B1, B11, B19, B22, B38, B44.
* **next_review_trigger:** Per production readiness
  development.

* **item_id:** NG-08.
* **statement:** No enterprise SaaS-ready claim.
* **rationale:** The enterprise SaaS readiness is
  governed by the B8 / B17 / B25 / B33 artifacts.
* **affected_area:** Enterprise SaaS readiness.
* **permitted_wording:** "The product is not
  enterprise SaaS-ready."
* **prohibited_wording:** "The product is
  enterprise SaaS-ready".
* **evidence_source:** B1, B11, B19, B22, B38, B44.
* **next_review_trigger:** Per enterprise readiness
  development.

* **item_id:** NG-09.
* **statement:** No investment advice.
* **rationale:** The product is not investment
  advice. The What Changed deltas are explanatory,
  not guaranteed accuracy claims.
* **affected_area:** Investment advice.
* **permitted_wording:** "The product is not
  investment advice."
* **prohibited_wording:** "The product is
  investment advice" / "Invest in the product" /
  "Guaranteed returns".
* **evidence_source:** B1, B11, B19, B22, B38, B44.
* **next_review_trigger:** Per investment advice
  process.

* **item_id:** NG-10.
* **statement:** No guaranteed returns.
* **rationale:** The product does not guarantee
  returns. The What Changed deltas are explanatory,
  not guaranteed accuracy claims.
* **affected_area:** Guaranteed returns.
* **permitted_wording:** "The product does not
  guarantee returns."
* **prohibited_wording:** "Guaranteed returns" /
  "The product guarantees returns".
* **evidence_source:** B1, B11, B19, B22, B38, B44.
* **next_review_trigger:** Per guaranteed returns
  process.

* **item_id:** NG-11.
* **statement:** G20 remains BLOCKED.
* **rationale:** G20 is the gate for the senior
  debt / loan amortization / cash sweep. G20 is
  not promoted by the Generic Modelling arc.
* **affected_area:** G20.
* **permitted_wording:** "G20 remains BLOCKED."
* **prohibited_wording:** "G20 is approved" / "G20
  is promoted".
* **evidence_source:** B1, B11, B19, B22, B25, B33.
* **next_review_trigger:** Per G20 promotion.

* **item_id:** NG-12.
* **statement:** R99 remains NOT APPROVED.
* **rationale:** R99 (sponsor cashflows double-
  count fix validation) is not approved by the
  Generic Modelling arc.
* **affected_area:** R99.
* **permitted_wording:** "R99 remains NOT
  APPROVED."
* **prohibited_wording:** "R99 is approved" / "R99
  is promoted".
* **evidence_source:** B1, B11, B19, B22, B25, B33.
* **next_review_trigger:** Per R99 promotion.

* **item_id:** NG-13.
* **statement:** R102 remains NOT APPROVED.
* **rationale:** R102 (sponsor distribution handoff
  contract) is not approved by the Generic
  Modelling arc.
* **affected_area:** R102.
* **permitted_wording:** "R102 remains NOT
  APPROVED."
* **prohibited_wording:** "R102 is approved" /
  "R102 is promoted".
* **evidence_source:** B1, B11, B19, B22, B25, B33.
* **next_review_trigger:** Per R102 promotion.

* **item_id:** NG-14.
* **statement:** Generic Solar / Wind remain
  exploratory and unvalidated.
* **rationale:** The Generic Solar / Wind templates
  are not validated against reference models.
* **affected_area:** Generic Solar / Wind.
* **permitted_wording:** "Generic Solar / Wind are
  exploratory and unvalidated."
* **prohibited_wording:** "Generic Solar / Wind are
  validated" / "Generic Solar / Wind are Excel-
  parity validated".
* **evidence_source:** B41, B44.
* **next_review_trigger:** Per B47 cadence plan.

* **item_id:** NG-15.
* **statement:** `partial_pay_sweep` is not
  promoted.
* **rationale:** `partial_pay_sweep` is not
  promoted by the Generic Modelling arc.
* **affected_area:** `partial_pay_sweep`.
* **permitted_wording:** "`partial_pay_sweep` is
  not promoted."
* **prohibited_wording:** "`partial_pay_sweep` is
  promoted".
* **evidence_source:** B1, B11, B19, B22, B25, B33.
* **next_review_trigger:** Per `partial_pay_sweep`
  promotion.

* **item_id:** NG-16.
* **statement:** Flat / min DSCR sculpting is not
  promoted.
* **rationale:** Flat / min DSCR sculpting is not
  promoted by the Generic Modelling arc.
* **affected_area:** Flat / min DSCR sculpting.
* **permitted_wording:** "Flat / min DSCR sculpting
  is not promoted."
* **prohibited_wording:** "Flat / min DSCR
  sculpting is promoted".
* **evidence_source:** B1, B11, B19, B22, B25, B33.
* **next_review_trigger:** Per flat / min DSCR
  sculpting promotion.

## 3. What B51 is not

* B51 is not a code change. Agent B does not
  implement code.
* B51 is not external validation.
* B51 is not a paid pilot authorization.
* B51 is not a customer reference.
* B51 is not a production readiness claim.
* B51 is not an enterprise SaaS readiness claim.
* B51 is not a financial model validation.
* B51 is not a substitute for the B1 / B11 / B19 /
  B22 / B38 / B44 no-go claim artifacts.

## 4. Cross-references

* `reports/governance/known_limitations_no_go_claims_consolidation.json`
  (B51, machine-readable)
* `docs/governance/current_product_scope_snapshot_after_ui_generic_loop.md`
  (B48)
* `docs/pilot/internal_pilot_readiness_matrix.md` (B49)
* `docs/review/external_reviewer_evidence_index_refresh.md`
  (B50)
* `docs/pilot/controlled_pilot_data_room_index.md` (B52)
* `docs/governance/next_validation_roadmap_after_generic_loop.md`
  (B53)
* `docs/external_review/no_go_claims.md` (B1)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/commercial/demo_claims_checklist.json` (B19)
* `docs/commercial/qa_claims_matrix.json` (B22)
* `docs/commercial/ui demo_guardrail_refresh.md` (B38)
* `docs/commercial/generic_solar_wind_demo_guardrail_refresh.md` (B44)
* `docs/governance/phase53_stop_go_checklist.md` (B33)

---

*End of known limitations / no-go claims
consolidation.*
