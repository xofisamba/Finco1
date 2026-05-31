# Phase 27B — Validation Pack Export / Presentation

## Base SHA
`6b74e1e800716371c0b1fd57cf9a03fe329d099a` (after PR #335 merge)

---

## Why Phase 27B

Phase 27 created the formal validation pack (`phase27_frozen_path_external_validation_pack.md`) and evidence matrix (`phase27_validation_evidence_matrix.md`). Phase 27B packages that evidence into stakeholder-ready documents suitable for external reviewers, advisors, pilot stakeholders, or internal decision-makers.

The goal is to make the validation evidence **easy to navigate, understand, and sign off on** without requiring deep technical knowledge of the model's internal architecture.

---

## Files Created

| File | Purpose |
|------|---------|
| `docs/validation_pack_executive_summary.md` | One-page stakeholder summary — validated scope, key anchors, residuals, non-claims, how to read the pack |
| `docs/validation_pack_index.md` | Navigation index — document map, reading paths, what is not included |
| `docs/external_reviewer_checklist.md` | Section-by-section review checklist with sign-off table |
| `docs/phase27b_validation_pack_export_presentation.md` | This implementation doc |

---

## What Is Included

- **Executive Summary** — entry point for any reviewer; one page covering validated scope, key anchors, residuals, non-claims, how to review
- **Validation Pack Index** — document map with 3 reading paths (quick review, thorough review, technical model review)
- **External Reviewer Checklist** — 10 sections (A–J): model scope, TUHO checks, Oborovo checks, senior debt fixture, DSCR trajectory, SHL/distribution lock-up, residuals, limitations/non-claims, recommended questions, reviewer sign-off

---

## What Is Excluded

- **PDF generation** — markdown is PDF-ready but not auto-generated. Markdown tables, headings, and short paragraphs are PDF-compatible. To generate a PDF: export from a markdown renderer or convert tool.
- **No financial formula changes** — all documents are pure documentation
- **No runtime model changes** — no model files touched
- **No fixture CSV edits**
- **No new dependencies** — only existing documentation infrastructure used

---

## How External Reviewers Should Use This Pack

1. Start with `validation_pack_executive_summary.md` (the one-page overview)
2. Navigate using `validation_pack_index.md` to find relevant supporting documents
3. Work through `external_reviewer_checklist.md` section by section
4. Cross-reference with `phase27_frozen_path_external_validation_pack.md` and `phase27_validation_evidence_matrix.md` for detailed evidence
5. Sign off using Section J of the reviewer checklist

---

## Manifest Decision

No `reports/phase27b_validation_pack_manifest.json` is created in this phase.

**Rationale:** The documentation package (`validation_pack_executive_summary.md`, `validation_pack_index.md`, `external_reviewer_checklist.md`) is self-describing and navigable without a separate manifest JSON. The evidence matrix (`phase27_validation_evidence_matrix.md`) provides the dense cross-reference that a manifest would attempt to replicate. Adding a manifest JSON would be redundant without adding reviewer value.

---

## PDF Decision

No PDF is auto-generated in this phase.

Markdown documents are formatted to be **PDF-ready**:
- Clear section headings (H1, H2, H3)
- Tables throughout
- Short paragraphs
- No broken links
- No unsupported raw HTML

To create a PDF: render the markdown using a tool of choice (e.g., VS Code markdown PDF, Marktext, or any markdown-to-PDF converter).

---

## Tests

### `tests/test_phase27b_validation_pack_export_presentation.py`

13 test cases:
1. `test_phase27b_doc_exists`
2. `test_executive_summary_exists`
3. `test_validation_pack_index_exists`
4. `test_external_reviewer_checklist_exists`
5. `test_executive_summary_contains_validated_scope`
6. `test_executive_summary_contains_key_anchors`
7. `test_index_links_core_pack_documents`
8. `test_reviewer_checklist_contains_review_sections`
9. `test_non_claims_are_explicit`
10. `test_manifest_if_present_is_valid` (manifest skipped — doc explains why)
11. `test_pdf_not_claimed_if_not_generated`
12. `test_no_runtime_model_files_changed_or_claimed`
13. `test_guardrails_unchanged`

---

## Guardrails Preserved

- ✅ No runtime formula changes
- ✅ No financial formula changes
- ✅ No model files changed
- ✅ No fixture CSVs changed
- ✅ No JS financial calculations
- ✅ No factory flag changes
- ✅ No Revenue/OPEX/CAPEX/Tax formula changes
- ✅ No SHL/distribution logic changes
- ✅ No senior debt sizing logic changes
- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ Backend remains source of truth
- ✅ No lender/bank/audit/SaaS/certification claims

---

## Recommended Next Phase

**Phase 28 — Generic Project Path Validation**
- Validate model behavior for new projects without Excel reference

**or**

**Phase 29A — TUHO CO2 Revenue Deep-Dive**
- Verify CO2 price curve, escalation, and certificate handling

Preference: Phase 28 first if the immediate goal is expanding validated coverage beyond TUHO/Oborovo. Phase 29A first if deeper TUHO CO2 revenue reporting is required.
