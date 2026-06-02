# Prohibited Claims Register

This file is the **prohibited claims register** for Finco1
commercial messaging. Each entry is a specific phrase or claim
category that is prohibited in any commercial channel, with a
rationale, a category, and a cross-reference to the B1 no-go claim
list that authorizes the prohibition.

> **The register is internal governance. It is not a marketing or
> sales artifact, not a customer reference, and not external
> validation.** The register exists to prevent claims that the
> project is not in a position to support. See
> `docs/commercial/no_go_claims_commercial_guardrail.md` for the
> full guardrail.

---

## 1. Authority

The register is built on the B1 no-go claim list
(`docs/external_review/no_go_claims.md`, merged in PR #390).
Each entry in the register is a commercial-messaging-specific
instance of a B1 no-go claim. The category is the B1 category.

The register is the source of truth for what must not be said in
commercial messaging. The commercial claims review matrix
(`reports/commercial/commercial_claims_review_matrix.json`) is
the per-channel authority grid.

## 2. Categories

The register uses the B1 categories:

* **lender** — claims about lender / bank / bankability.
* **audit** — claims about audit / certification / regulatory.
* **saas** — claims about SaaS / production / commercial.
* **claim** — claims about model correctness for any specific
  use.
* **approval** — claims about approval of not-approved areas.
* **advice** — claims about investment advice or guaranteed
  returns.

## 3. The register

### 3.1 Lender / bank

| Phrase | Category | Rationale | B1 reference |
|---|---|---|---|
| "bankable" | lender | Implies lender approval or acceptability to any specific lender. | `no_go_claims.md` §1 |
| "lender-approved" | lender | Implies a specific lender has approved the model. No lender has. | `no_go_claims.md` §1 |
| "lender-grade" | lender | Implies the model is suitable for any lender's credit process. | `no_go_claims.md` §1 |
| "ready for credit committee" | lender | Implies the model is ready for any specific lender's ICG / credit committee. | `no_go_claims.md` §1 |
| "ICG-ready" / "credit-policy-aligned" | lender | Implies alignment with any specific lender's credit policy. | `no_go_claims.md` §1 |
| "acceptable to any specific lender or bank" | lender | Implies specific lender acceptance. | `no_go_claims.md` §1 |
| "sufficient for any loan-approval decision" | lender | Implies the model is sufficient for any specific lender's loan-approval process. | `no_go_claims.md` §1 |

### 3.2 Audit / certification / regulatory

| Phrase | Category | Rationale | B1 reference |
|---|---|---|---|
| "audited" | audit | Implies an audit opinion. No audit has been performed. | `no_go_claims.md` §2 |
| "certified" | audit | Implies a certification. No certification has been issued. | `no_go_claims.md` §2 |
| "accredited" | audit | Implies an accreditation. No accreditation has been issued. | `no_go_claims.md` §2 |
| "IFRS-aligned" / "US-GAAP-aligned" (as compliance) | audit | Implies compliance with a specific accounting framework. | `no_go_claims.md` §2 |
| "regulatory-approved" | audit | Implies a specific regulator has approved the model. No regulator has. | `no_go_claims.md` §2 |
| "regulatory-ready" / "filing-ready" | audit | Implies the model is ready for any specific regulator or filing. | `no_go_claims.md` §2 |
| "compliant with any regulatory regime" | audit | Implies compliance with any specific regulatory regime. | `no_go_claims.md` §2 |
| "subject to any external assurance opinion" | audit | Implies an external assurance opinion has been issued. None has. | `no_go_claims.md` §2 |

### 3.3 SaaS / production / commercial

| Phrase | Category | Rationale | B1 reference |
|---|---|---|---|
| "enterprise SaaS-ready" | saas | Implies the model is ready for any specific enterprise customer. | `no_go_claims.md` §3 |
| "production-ready" | saas | Implies the model is ready for any production use. | `no_go_claims.md` §3 |
| "SLA-backed" / "warranty-covered" | saas | Implies a service-level commitment. None exists. | `no_go_claims.md` §3 |
| "ready for any specific customer" | saas | Implies specific customer readiness. | `no_go_claims.md` §3 |
| "scalable" (in the sense of "ready for enterprise scale") | saas | Implies enterprise-scale readiness. | `no_go_claims.md` §3 |
| "multi-tenant-ready" | saas | Implies multi-tenant architecture readiness. | `no_go_claims.md` §3 |
| "commercially-ready" | saas | Implies commercial readiness. | `no_go_claims.md` §3 |
| "customer-ready" | saas | Implies specific customer readiness. | `no_go_claims.md` §3 |

### 3.4 Generic validation

| Phrase | Category | Rationale | B1 reference |
|---|---|---|---|
| "generic solar validated" | claim | Generic solar is exploratory; not validated. | `no_go_claims.md` §3, §3.4 |
| "generic wind validated" | claim | Generic wind is exploratory; not validated. | `no_go_claims.md` §3, §3.4 |
| "solar / wind parity" | claim | Parity is a project-internal concept; not external validation. | `no_go_claims.md` §3, §3.4 |
| "any solar project" (in the sense of "correct for any solar project") | claim | Implies generic correctness. | `no_go_claims.md` §3, §3.4 |
| "any wind project" (in the sense of "correct for any wind project") | claim | Implies generic correctness. | `no_go_claims.md` §3, §3.4 |
| "validation" (used as a noun implying external validation) | claim | Confuses internal validation with external validation. | `no_go_claims.md` (general) |
| "externally validated" | claim | No external validation has been performed. | `no_go_claims.md` (general) |

### 3.5 Approval of not-approved areas

| Phrase | Category | Rationale | B1 reference |
|---|---|---|---|
| "G20 approved" | approval | G20 is BLOCKED. | `no_go_claims.md` §6 |
| "G20 ready" | approval | G20 is BLOCKED. | `no_go_claims.md` §6 |
| "R99 approved" | approval | R99 is NOT APPROVED. | `no_go_claims.md` §6 |
| "R102 approved" | approval | R102 is NOT APPROVED. | `no_go_claims.md` §6 |
| "partial-pay sweep supported" | approval | `partial_pay_sweep` is not promoted. | `no_go_claims.md` (general) |
| "flat DSCR sculpting supported" | approval | Flat / min DSCR sculpting is not promoted. | `no_go_claims.md` (general) |
| "any not-approved feature supported" | approval | Implies approval of a not-approved feature. | `no_go_claims.md` (general) |

### 3.6 Advice / guarantees

| Phrase | Category | Rationale | B1 reference |
|---|---|---|---|
| "investment advice" | advice | The model is a screening tool, not an investment advisor. | `no_go_claims.md` (general) |
| "buy recommendation" | advice | Implies a specific recommendation. | `no_go_claims.md` (general) |
| "guaranteed returns" | advice | Implies a guarantee of any kind. | `no_go_claims.md` (general) |
| "guaranteed IRR" | advice | Implies a guarantee of any kind. | `no_go_claims.md` (general) |
| "any statement that the user should rely on the model's output for a real decision" | advice | Implies reliability for a real decision. | `no_go_claims.md` (general) |

## 4. Adding to the register

Adding a new entry to the register is a normal B-track operation,
not a code change. The procedure:

1. Identify the new prohibited phrase or claim category.
2. Document the rationale and the B1 reference.
3. Add the entry to the register.
4. Update the commercial claims review matrix to reflect the
   new entry.
5. Communicate the change to anyone who uses the register.

A new entry is added to the register, never removed silently. A
phrase that was once in the register is always in the register,
even if the rationale weakens over time. The register is a
historical record.

## 5. Removing from the register

Removing an entry from the register requires:

* a dedicated governance change;
* an explicit relaxation of the corresponding B1 no-go claim;
* a recorded rationale;
* a corresponding update to the commercial claims review matrix.

This is the same procedure as relaxing any B1 no-go claim. It is
not a routine operation.

## 6. What the register is not

* It is not a marketing playbook.
* It is not a sales enablement tool.
* It is not a customer reference.
* It is not external validation.

## 7. Cross-references

* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/commercial/approved_demo_language.md` (B11)
* `reports/commercial/commercial_claims_review_matrix.json` (B11)
* `docs/external_review/no_go_claims.md` (B1, source of truth)

---

*End of prohibited claims register.*
