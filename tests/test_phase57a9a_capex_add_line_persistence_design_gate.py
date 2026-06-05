"""Phase 57A-9A: CAPEX Add-Line Persistence Design Gate tests.

These tests pin the design contract from
``docs/phase57a9a_capex_add_line_persistence_design_gate.md``.
They do NOT make any runtime / template / persistence
changes.

The contract is:

1. The ownership model is Hybrid (Q4): existence in
   dedicated ``capex_sub_lines`` table, per-scenario
   amount in override blob.
2. The persistence approach is Option 4 (Hybrid).
3. Options 1, 2, 3 (as base), and 5 are explicitly
   rejected.
4. The per-category mapping table covers C.01..C.16
   (C.17 / C.18 are read-only).
5. The business code format is ``C.NN.U###`` with a
   3-digit counter per ``(project_id, parent_category_code)``.
6. A stable UUID ``sub_line_id`` is the durable identifier.
7. The scenario override blob uses reserved keys
   ``_capex_sub_line_overrides`` and
   ``_capex_sub_line_overrides_metadata``.
8. The ``update_scenario_overrides`` change is additive
   (a second allowlist consulted BEFORE the silent-drop
   check; Phase 20B invariant preserved for all other keys).
9. The Run integration helper
   ``_apply_user_sub_lines_to_capex`` returns the input
   ``capex`` unchanged when the user_sub_lines tuple is
   empty (factory project safety).
10. The aggregation rule is base + sum of effective user
    sub-line amounts; soft-deleted + hard-deleted rows
    are excluded.
11. The Excel export integration uses the existing
    ``advanced_capex_line_items`` parameter; no change to
    ``build_capex_summary_table`` /
    ``build_capex_items_table``.
12. The save / load round-trip invariant is documented.
13. The hard no-go list is documented and includes:
    no formula change, no IDC change, no construction
    funding change, no tax engine change, no G20 / R99 /
    R102 promotion, no Tailwind / Alpine, no backend keys
    visible, no factory project mutation, rc1 frozen,
    no 57A-8 in-memory preview regression.
14. The out-of-scope list is documented.
15. The phase plan has 7 rows (57A-9A through 57A-10).
16. No runtime implementation lands in 57A-9A.
17. rc1 (``b425a0708719eaa5e1d922b1008e5609758e0ad4``)
    is frozen.

Type: docs / report / test-only. NOT auto-merge eligible.
Stop after report. Wait for review.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = (
    REPO_ROOT
    / "docs"
    / "phase57a9a_capex_add_line_persistence_design_gate.md"
)
REPORT_PATH = (
    REPO_ROOT
    / "reports"
    / "phase57a9a_capex_add_line_persistence_design_gate.json"
)


RC1_FROZEN_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def doc_text() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Files exist
# ---------------------------------------------------------------------------


class TestFilesExist:
    def test_design_doc_exists(self):
        assert DOC_PATH.is_file()

    def test_report_json_exists(self):
        assert REPORT_PATH.is_file()


# ---------------------------------------------------------------------------
# 2. Top-level shape of the report
# ---------------------------------------------------------------------------


class TestReportTopLevel:
    REQUIRED_TOP_KEYS = {
        "phase",
        "title",
        "type",
        "branch",
        "base_sha",
        "ownership_model",
        "persistence_approach",
        "schema_sketch",
        "phase_plan",
        "hard_no_go",
        "rc1_frozen_sha",
    }

    def test_required_top_keys(self, report):
        missing = self.REQUIRED_TOP_KEYS - set(report.keys())
        assert not missing, f"missing top-level keys: {sorted(missing)}"

    def test_phase_value(self, report):
        assert report["phase"] == "57A-9A"

    def test_type_value(self, report):
        assert report["type"] == "docs/report/test-only"

    def test_branch_value(self, report):
        assert report["branch"] == (
            "phase57a9a-capex-add-line-persistence-design-gate"
        )

    def test_base_sha_is_post_57a8(self, report):
        assert report["base_sha"] == (
            "976f5a449e195ecd5fa6ae4fbfe1b734b5ea5446"
        )

    def test_rc1_frozen_sha(self, report):
        assert report["rc1_frozen_sha"] == RC1_FROZEN_SHA


# ---------------------------------------------------------------------------
# 3. Ownership model — Hybrid (Q4)
# ---------------------------------------------------------------------------


class TestOwnershipModel:
    def test_selected_is_hybrid_q4(self, report):
        assert report["ownership_model"]["selected"] == "hybrid_q4"

    def test_existence_layer_is_table(self, report):
        om = report["ownership_model"]
        assert "capex_sub_lines table" in om["existence_layer"].lower()
        assert "source of truth" in om["existence_layer"].lower()

    def test_amount_layer_is_scenario_override_blob(self, report):
        om = report["ownership_model"]
        assert "_capex_sub_line_overrides" in om["amount_layer"]
        assert "overrides_json" in om["amount_layer"]

    def test_q1_rejected_in_design(self, doc_text):
        # Q1 (project only) is rejected because it kills
        # per-scenario amount variation.
        assert "Q1" in doc_text
        assert "rejected" in doc_text.lower()

    def test_q4_selected_in_design(self, doc_text):
        # Q4 (Hybrid) is the selected quadrant.
        assert "Q4" in doc_text
        assert "Hybrid" in doc_text or "hybrid" in doc_text


# ---------------------------------------------------------------------------
# 4. Persistence approach — Option 4 (Hybrid)
# ---------------------------------------------------------------------------


class TestPersistenceApproach:
    def test_selected_is_option_4(self, report):
        assert report["persistence_approach"]["selected"] == (
            "option_4_hybrid"
        )

    @pytest.mark.parametrize(
        "option_name",
        [
            "option_1_pure_scenario_override_blob",
            "option_2_pure_project_snapshot_blob",
            "option_3_dedicated_table_only_base",
            "option_5_pure_project_template_copy",
        ],
    )
    def test_rejected_options_are_marked(self, report, option_name):
        for opt in report["persistence_approach"]["options"]:
            if opt["name"] == option_name:
                assert opt.get("rejected") is True or (
                    opt.get("rejected_as_base") is True
                )
                return
        pytest.fail(f"option {option_name!r} not in persistence_approach.options")

    def test_option_4_has_no_rejected_flag(self, report):
        for opt in report["persistence_approach"]["options"]:
            if opt["name"] == "option_4_hybrid":
                assert opt.get("selected") is True
                assert "rejected" not in opt
                return
        pytest.fail("option_4_hybrid not in persistence_approach.options")

    def test_design_doc_lists_all_five_options(self, doc_text):
        for marker in [
            "Option 1: Pure scenario override blob",
            "Option 2: Pure project-snapshot blob",
            "Option 3: Dedicated table only",
            "Option 4: Hybrid",
            "Option 5: Pure project-template copy",
        ]:
            assert marker in doc_text, f"missing option marker: {marker!r}"


# ---------------------------------------------------------------------------
# 5. Per-category mapping table
# ---------------------------------------------------------------------------


class TestPerCategoryMapping:
    EXPECTED_CATEGORIES = [
        "C.01", "C.02", "C.03", "C.04", "C.05", "C.06", "C.07",
        "C.08", "C.09", "C.10", "C.11", "C.12", "C.13", "C.14",
        "C.15", "C.16", "C.17", "C.18",
    ]

    def test_all_18_categories_present(self, report):
        mapping = report["per_category_mapping"]["mapping"]
        for cat in self.EXPECTED_CATEGORIES:
            assert cat in mapping, f"category {cat!r} missing from mapping"

    def test_c01_to_c16_have_capex_field(self, report):
        mapping = report["per_category_mapping"]["mapping"]
        for i in range(1, 17):
            cat = f"C.{i:02d}"
            assert mapping[cat]["capex_field"] is not None, (
                f"{cat} should map to a CapexStructure field"
            )

    def test_c17_and_c18_have_no_capex_field(self, report):
        mapping = report["per_category_mapping"]["mapping"]
        assert mapping["C.17"]["capex_field"] is None
        assert mapping["C.18"]["capex_field"] is None

    def test_c02_maps_to_epc_contract(self, report):
        mapping = report["per_category_mapping"]["mapping"]
        assert mapping["C.02"]["capex_field"] == "epc_contract"

    def test_c07_maps_to_lease_tax(self, report):
        # C.07 is the user-facing "Land Securing Costs" which
        # maps to the backend key lease_tax. The display name
        # is what the user sees (Phase 57A-3 backend-key
        # hiding invariant).
        mapping = report["per_category_mapping"]["mapping"]
        assert mapping["C.07"]["capex_field"] == "lease_tax"
        assert "Land Securing" in mapping["C.07"]["name"]

    def test_c16_maps_to_project_rights(self, report):
        mapping = report["per_category_mapping"]["mapping"]
        assert mapping["C.16"]["capex_field"] == "project_rights"

    def test_design_doc_has_per_category_mapping_section(self, doc_text):
        assert "per-category mapping" in doc_text.lower() or (
            "per_category_mapping" in doc_text
        )


# ---------------------------------------------------------------------------
# 6. Business code format
# ---------------------------------------------------------------------------


class TestBusinessCodeFormat:
    def test_pattern_in_report(self, report):
        assert report["business_code_format"]["pattern"] == "C.NN.U###"

    def test_u_prefix_explanation_in_report(self, report):
        bcf = report["business_code_format"]
        assert bcf["components"]["U"] == (
            "literal 'U' prefix marking 'user-added' "
            "(vs. template C.NN.NN codes)"
        )

    def test_counter_is_3_digit_zero_padded(self, report):
        bcf = report["business_code_format"]
        assert "3-digit zero-padded" in bcf["components"]["###"]

    def test_categories_excluded_are_c17_c18(self, report):
        assert report["business_code_format"]["categories_excluded"] == [
            "C.17",
            "C.18",
        ]

    def test_design_doc_has_business_code_format_section(self, doc_text):
        assert "Business code format" in doc_text or (
            "business_code" in doc_text
        )

    def test_design_doc_explains_u_prefix(self, doc_text):
        # The design must explain why the U prefix is needed
        # (namespace disjoint from template C.NN.NN codes).
        assert "namespace" in doc_text.lower()
        assert "C.NN.NN" in doc_text or "C\\.NN\\.NN" in doc_text


# ---------------------------------------------------------------------------
# 7. Stable UUID invariant
# ---------------------------------------------------------------------------


class TestStableUuidInvariant:
    def test_primary_key_is_sub_line_id(self, report):
        assert report["stable_uuid_invariant"]["primary_key"] == (
            "sub_line_id (UUID)"
        )

    def test_scenario_override_keyed_by_sub_line_id(self, report):
        assert report["stable_uuid_invariant"]["scenario_override_key"] == (
            "sub_line_id (UUID), NOT business_code"
        )

    def test_rationale_explains_soft_delete_rebind(self, report):
        rationale = report["stable_uuid_invariant"]["rationale"]
        assert "soft-delete" in rationale.lower()
        assert "UUID" in rationale

    def test_design_doc_has_uuid_section(self, doc_text):
        assert "sub_line_id" in doc_text
        assert "UUID" in doc_text


# ---------------------------------------------------------------------------
# 8. Scenario override blob shape
# ---------------------------------------------------------------------------


class TestScenarioOverrideBlob:
    EXPECTED_RESERVED_KEYS = [
        "_capex_sub_line_overrides",
        "_capex_sub_line_overrides_metadata",
    ]

    def test_reserved_keys(self, report):
        keys = report["scenario_override_blob_shape"]["reserved_keys"]
        for k in self.EXPECTED_RESERVED_KEYS:
            assert k in keys, f"missing reserved key: {k!r}"

    def test_overrides_shape_is_dict_of_sub_line_id_to_float(self, report):
        schema = (
            report["scenario_override_blob_shape"]["schema"][
                "_capex_sub_line_overrides"
            ]
        )
        assert schema["type"] == "object"
        assert "<sub_line_id" in schema["shape"]
        assert "<amount" in schema["shape"]
        assert "float" in schema["shape"]

    def test_update_scenario_overrides_change_is_additive(self, report):
        change = report["scenario_override_blob_shape"][
            "update_scenario_overrides_change"
        ]
        assert change["behavior"].startswith("ADDITIVE")
        # The existing 22-key flat-path must remain.
        assert "22-key flat-path unchanged" in change["behavior"]
        # The Phase 20B silent-drop must be preserved.
        assert "Phase 20B invariant" in change["behavior"]


# ---------------------------------------------------------------------------
# 9. Run integration helper
# ---------------------------------------------------------------------------


class TestRunIntegration:
    def test_helper_name(self, report):
        assert "_apply_user_sub_lines_to_capex" in (
            report["run_integration"]["helper"]
        )

    def test_factory_safety_documented(self, report):
        ri = report["run_integration"]
        # factory_safety is either a bool True or a string
        # that documents the no-op behavior.
        assert ri["factory_safety"] is True or (
            "no-op" in str(ri["factory_safety"])
            or "returned unchanged" in str(ri["factory_safety"])
        )
        # The full run_integration dict must document the no-op
        # behavior in plain English.
        ri_text = " ".join(str(v) for v in ri.values())
        assert (
            "no-op" in ri_text or "returned unchanged" in ri_text
        ), f"factory no-op behavior not documented in run_integration: {ri!r}"

    def test_model_impact_is_zero_new_code(self, report):
        ri = report["run_integration"]
        assert ri["model_impact"].startswith("ZERO new model code")

    def test_design_doc_has_run_integration_section(self, doc_text):
        assert "_apply_user_sub_lines_to_capex" in doc_text
        assert "factory" in doc_text.lower()
        assert "TUHO" in doc_text


# ---------------------------------------------------------------------------
# 10. Aggregation rule
# ---------------------------------------------------------------------------


class TestAggregationRule:
    def test_formula_includes_base_plus_user_sum(self, report):
        formula = report["aggregation_rule"]["formula"]
        assert "base_amount_keur" in formula
        assert "user_sub_lines" in formula
        assert "scenario_overrides" in formula

    def test_soft_deleted_excluded(self, report):
        assert report["aggregation_rule"]["soft_deleted_excluded"] is True

    def test_hard_deleted_excluded(self, report):
        assert report["aggregation_rule"]["hard_deleted_excluded"] is True

    def test_factory_projects_no_op(self, report):
        assert report["aggregation_rule"]["factory_projects_no_op"] is True

    def test_model_derives_automatically(self, report):
        assert report["aggregation_rule"]["model_derives_automatically"] is True


# ---------------------------------------------------------------------------
# 11. Excel export integration
# ---------------------------------------------------------------------------


class TestExcelExportIntegration:
    def test_uses_advanced_capex_line_items_parameter(self, report):
        ee = report["excel_export_integration"]
        # The parameter_used field must reference the
        # advanced_capex_line_items parameter.
        assert "advanced_capex_line_items" in str(ee["parameter_used"])
        ee_text = " ".join(str(v) for v in ee.values())
        # The materialization note must mention the parameter is
        # currently unused (or reserved for future use).
        assert "currently unused" in ee_text.lower() or (
            "reserved" in ee_text.lower()
        )

    def test_summary_sheet_unchanged(self, report):
        ee = report["excel_export_integration"]
        assert "NONE" in ee["summary_sheet_impact"].upper()

    def test_items_sheet_unchanged(self, report):
        ee = report["excel_export_integration"]
        assert (
            "build_capex_items_table" in ee["items_sheet_impact"]
        )
        assert "continue" in ee["items_sheet_impact"].lower() or (
            "automatically" in ee["items_sheet_impact"].lower()
        )

    def test_design_doc_has_excel_export_section(self, doc_text):
        assert (
            "advanced_capex_line_items" in doc_text
        ), "design doc must reference the existing advanced_capex_line_items parameter"
        assert "build_capex_summary_table" in doc_text
        assert "build_capex_items_table" in doc_text


# ---------------------------------------------------------------------------
# 12. Save / load flow
# ---------------------------------------------------------------------------


class TestSaveLoadFlow:
    def test_save_pattern_is_soft_delete_reinsert(self, report):
        sl = report["save_load_flow"]
        assert "Soft-delete" in sl["save_pattern"]
        assert "re-insert" in sl["save_pattern"].lower()

    def test_audit_preservation_documented(self, report):
        sl = report["save_load_flow"]
        assert "NOT garbage-collected" in sl["audit_preservation"]
        assert "replay" in sl["audit_preservation"].lower()

    def test_round_trip_invariant_documented(self, report):
        sl = report["save_load_flow"]
        rt = sl["round_trip_invariant"]
        assert "bit-identical" in rt or "bit identical" in rt.lower()
        assert "in-memory" in rt.lower()

    def test_validator_helper_named(self, report):
        sl = report["save_load_flow"]
        assert "validate_sub_line_override_blob" in sl["validator_helper"]


# ---------------------------------------------------------------------------
# 13. Hard no-go list
# ---------------------------------------------------------------------------


class TestHardNoGo:
    REQUIRED_NO_GO = [
        "no_financial_formula_changes",
        "no_idc_calculation_changes",
        "no_construction_funding_changes",
        "no_tax_engine_changes",
        "no_g20_r99_r102_promotion",
        "no_tailwind_alpine_react_vue_svelte",
        "no_backend_keys_visible_in_ui",
        "no_factory_project_mutation",
        "rc1_frozen",
    ]

    def test_required_no_go_items_present(self, report):
        no_go = report["hard_no_go"]
        for needle in self.REQUIRED_NO_GO:
            assert any(needle in item for item in no_go), (
                f"missing hard no-go item: {needle!r}"
            )

    def test_no_57a8_in_memory_preview_regression(self, report):
        no_go = report["hard_no_go"]
        assert any(
            "57a8" in item.lower() and "regression" in item.lower()
            for item in no_go
        )

    def test_no_overrides_json_schema_change_invariant(self, report):
        # The override-blob allowlist extension is ADDITIVE;
        # the existing 22-key silent-drop must be preserved.
        no_go = report["hard_no_go"]
        assert any(
            "overrides_json" in item.lower() and "additive" in item.lower()
            for item in no_go
        )

    def test_design_doc_hard_no_go_section(self, doc_text):
        assert "Hard no-go" in doc_text or "hard no-go" in doc_text
        # The rc1 SHA must be visible in the no-go section.
        assert RC1_FROZEN_SHA in doc_text


# ---------------------------------------------------------------------------
# 14. Out-of-scope list
# ---------------------------------------------------------------------------


class TestOutOfScope:
    EXPECTED_OUT_OF_SCOPE = [
        "opex_sub_line_persistence",
        "revenue_sub_line_persistence",
        "construction_schedule_per_sub_line_override",
        "tax_depreciation_per_line_override",
        "sub_line_cloning_semantics_on_scenario_create",
        "sub_line_excel_import",
        "multi_user_sub_line_collaboration",
    ]

    def test_required_out_of_scope_present(self, report):
        oos = report["out_of_scope"]
        for needle in self.EXPECTED_OUT_OF_SCOPE:
            assert any(needle in item for item in oos), (
                f"missing out-of-scope item: {needle!r}"
            )


# ---------------------------------------------------------------------------
# 15. Phase plan
# ---------------------------------------------------------------------------


class TestPhasePlan:
    EXPECTED_PHASES = [
        "57A-9A",
        "57A-9B",
        "57A-9C",
        "57A-9D",
        "57A-9E",
        "57A-9F",
        "57A-10",
    ]

    def test_seven_phases(self, report):
        assert len(report["phase_plan"]) == 7

    def test_all_expected_phases_present(self, report):
        phases = [p["phase"] for p in report["phase_plan"]]
        for expected in self.EXPECTED_PHASES:
            assert expected in phases, f"missing phase: {expected!r}"

    def test_57a_9a_is_not_auto_merge_eligible(self, report):
        for p in report["phase_plan"]:
            if p["phase"] == "57A-9A":
                assert p["auto_merge_eligible"] is False
                assert p["type"] == "docs/report/test"
                return
        pytest.fail("57A-9A not in phase_plan")

    def test_57a_9b_through_57a_9e_are_runtime(self, report):
        for p in report["phase_plan"]:
            if p["phase"] in ["57A-9B", "57A-9C", "57A-9D", "57A-9E"]:
                assert "runtime" in p["type"]
                return
        pytest.fail("57A-9B..57A-9E not in phase_plan")

    def test_57a_9f_and_57a_10_are_auto_merge_eligible(self, report):
        for p in report["phase_plan"]:
            if p["phase"] in ["57A-9F", "57A-10"]:
                assert p["auto_merge_eligible"] is True
        # Both must be present
        phases = {p["phase"] for p in report["phase_plan"]}
        assert "57A-9F" in phases
        assert "57A-10" in phases

    def test_phase_plan_pre_req_chain_is_valid(self, report):
        # 57A-9A pre-req is 57A-8 (recap), and the chain
        # 57A-9B -> 57A-9C -> 57A-9D -> 57A-9E -> 57A-9F -> 57A-10
        # must hold.
        phases_by_name = {p["phase"]: p for p in report["phase_plan"]}
        chain = [
            "57A-9B", "57A-9C", "57A-9D", "57A-9E", "57A-9F", "57A-10"
        ]
        prev = "57A-9A"
        for cur in chain:
            assert cur in phases_by_name, f"missing phase {cur}"
            assert phases_by_name[cur]["pre_req"] == prev, (
                f"{cur} pre-req should be {prev}, got "
                f"{phases_by_name[cur]['pre_req']}"
            )
            prev = cur

    def test_design_doc_has_phase_plan_table(self, doc_text):
        assert "Phase plan" in doc_text or "phase plan" in doc_text
        for phase_id in self.EXPECTED_PHASES:
            assert phase_id in doc_text, f"phase {phase_id} not in design doc"


# ---------------------------------------------------------------------------
# 16. Stop-after-report contract
# ---------------------------------------------------------------------------


class TestStopAfterReport:
    def test_stop_after_report_flag_in_report(self, report):
        assert "stop_after_report" in report
        sar = report["stop_after_report"]
        # Must say "Do not auto-merge" and "Do not start 57A-9B".
        assert "Do not auto-merge" in sar
        assert "57A-9B" in sar
        assert "57A-9C" in sar
        assert "57A-9D" in sar
        assert "57A-9E" in sar

    def test_design_doc_has_stop_and_document_section(self, doc_text):
        assert "Stop and document" in doc_text or (
            "Stop-after-report" in doc_text
        )
        # The design must explicitly say "Do not start 57A-9B"
        # and "Do not auto-merge 57A-9A".
        assert "Do not auto-merge" in doc_text
        assert (
            "57A-9B" in doc_text
        ), "design doc must reference 57A-9B as a future phase"
        assert "57A-9C" in doc_text
        assert "57A-9D" in doc_text
        assert "57A-9E" in doc_text


# ---------------------------------------------------------------------------
# 17. Files-not-changed list (design gate purity)
# ---------------------------------------------------------------------------


class TestFilesNotChanged:
    PROTECTED_PATHS = [
        "app/persistence/records.py",
        "app/persistence/_helpers.py",
        "app/persistence/projects_repository.py",
        "app/persistence/scenarios_repository.py",
        "app/persistence/db.py",
        "app/ui/project_context.py",
        "app/input_helpers.py",
        "app/excel_export.py",
        "domain/inputs.py",
        "app/templates/partials/sheet_capex.html",
        "static/app.js",
        "static/styles.css",
        "main_web.py",
        "main_api.py",
    ]

    def test_protected_paths_listed_in_report(self, report):
        not_changed = report["files_not_changed"]
        for path in self.PROTECTED_PATHS:
            assert path in not_changed, f"missing protected path: {path!r}"


# ---------------------------------------------------------------------------
# 18. 57A-8 invariant is preserved (the design must NOT regress the
#     in-memory preview).
# ---------------------------------------------------------------------------


class Test57A8InvariantPreserved:
    REQUIRED_57A8_KEYWORDS = [
        "data-capex-tmp",
        "C.0X.TMP-N",
        "Unsaved",
        "Preview only",
        "Run/Save warning",
        "in-memory only",
        "no name attribute",
    ]

    def test_57a8_keywords_in_design_doc(self, doc_text):
        # Each 57A-8 keyword must appear in the design doc.
        # We allow a couple of normalizations:
        #  - strip spaces, "/", ":", ",", ".", "`"
        #  - lowercase for case-insensitive matching
        import re
        def _norm(s: str) -> str:
            return re.sub(r"[\s/:,.`]", "", s).lower()
        doc_normalized = _norm(doc_text)
        for kw in self.REQUIRED_57A8_KEYWORDS:
            assert _norm(kw) in doc_normalized, (
                f"57A-8 keyword {kw!r} (normalized: {_norm(kw)!r}) "
                f"missing from design doc"
            )

    def test_57a8_invariants_in_recap(self, report):
        recap = report["recap_57a8"]
        assert recap["amount_input_has_name_attribute"] is False
        # api_calls is a string that starts with "none" (may be
        # followed by explanatory text).
        assert str(recap["api_calls"]).lower().startswith("none")
        assert recap["authoritative_totals_modified"] is False
        assert recap["preview_only_block_present"] is True
        assert recap["run_save_warning_block_present"] is True
        assert recap["rc1_frozen"] is True
        # toolbar_categories must mention C.01..C.16 (NOT C.17 / C.18).
        tcat = str(recap["toolbar_categories"])
        assert "C.01..C.16" in tcat
        assert "C.17" in tcat or "C.18" in tcat
        assert (
            "NOT" in tcat or "not" in tcat
        ), f"toolbar_categories must explicitly exclude C.17/C.18: {tcat!r}"


# ---------------------------------------------------------------------------
# 19. Cross-arc consistency — the design must NOT introduce new no-go
#     copy, must NOT promote G20 / R99 / R102, must NOT add Tailwind /
#     Alpine, must keep the persistence pattern consistent.
# ---------------------------------------------------------------------------


class TestCrossArcConsistency:
    FORBIDDEN_PHRASES_IN_DESIGN = [
        "G20 enabled",
        "G20 approved",
        "R99 approved",
        "R102 approved",
        "Tailwind",
        "Alpine.js",
        "React",
        "Vue",
        "Svelte",
    ]

    def test_no_forbidden_promotion_in_design(self, doc_text):
        # The design must mention these by name as forbidden,
        # but the canonical forbidden phrase is "no G20 / R99 /
        # R102 promotion". We allow "Tailwind" / "Alpine" only
        # inside the explicit "no Tailwind / Alpine" line.
        # We forbid standalone promotional statements.
        for phrase in self.FORBIDDEN_PHRASES_IN_DESIGN:
            # Count standalone occurrences outside the
            # explicit no-go list. Simple heuristic: split
            # into lines, check that any line containing
            # the phrase also contains "no " or "forbidden".
            for line in doc_text.splitlines():
                if phrase in line and (
                    "no " in line.lower() or "forbidden" in line.lower()
                ):
                    continue
                if phrase in line:
                    # Allow "Tailwind / Alpine" as a compound
                    # mention in the no-go list.
                    if phrase == "Tailwind" and "Alpine" in line:
                        continue
                    if phrase == "Alpine" and "Tailwind" in line:
                        continue
                    pytest.fail(
                        f"forbidden phrase {phrase!r} appears "
                        f"prominently in design doc line: {line!r}"
                    )

    def test_frontend_stack_unchanged(self, report):
        # The frontend stack is preserved: server-rendered
        # Jinja + HTMX + custom CSS + vanilla JS, no
        # bundler / npm / package.json.
        no_go = report["hard_no_go"]
        assert any(
            "no_tailwind_alpine_react_vue_svelte" in item
            for item in no_go
        )

    def test_no_new_app_domain_module(self, report):
        no_go = report["hard_no_go"]
        assert any(
            "no_new_app_domain_modules" in item
            for item in no_go
        )


# ---------------------------------------------------------------------------
# 20. Architecture / model integration pinning
# ---------------------------------------------------------------------------


class TestArchitecturePinning:
    EXPECTED_FIELD_NAMES = [
        "epc_contract",
        "production_units",
        "epc_other",
        "grid_connection",
        "ops_prep",
        "insurances",
        "lease_tax",
        "construction_mgmt_a",
        "commissioning",
        "audit_legal",
        "construction_mgmt_b",
        "contingencies",
        "taxes",
        "project_acquisition",
        "project_rights",
    ]

    def test_all_15_capex_fields_referenced(self, doc_text):
        for field in self.EXPECTED_FIELD_NAMES:
            assert field in doc_text, (
                f"CapexStructure field {field!r} not referenced "
                f"in design doc"
            )

    def test_scenario_input_fields_count_22(self, doc_text):
        # The design must document the 22-key SCENARIO_INPUT_FIELDS
        # set and the silent-drop behavior.
        assert "22" in doc_text
        assert "SCENARIO_INPUT_FIELDS" in doc_text
        assert "silently drop" in doc_text or "silently dropped" in doc_text

    def test_capex_structure_total_capex_property_referenced(self, doc_text):
        # The design must reference the CapexStructure
        # properties that will pick up the user sub-lines
        # automatically.
        for prop in ["hard_capex_keur", "sculpt_capex_keur", "total_capex"]:
            assert prop in doc_text, (
                f"CapexStructure property {prop!r} not referenced "
                f"in design doc"
            )

    def test_project_origin_values_documented(self, doc_text):
        for origin in [
            "factory_template",
            "saved_baseline",
            "user_project",
        ]:
            assert origin in doc_text, (
                f"project_origin value {origin!r} not in design doc"
            )

    def test_capex_sub_lines_table_proposed_lives_in_persistence(
        self, doc_text
    ):
        # The new helper module lives under
        # app/persistence/capex_sub_lines.py, NOT under
        # app/domain/...
        assert "app/persistence/capex_sub_lines.py" in doc_text
        # The hard no-go must mention "no_new_app_domain_modules".
        assert "no_new_app_domain_modules" in doc_text or (
            "app/domain" in doc_text
        )


# ---------------------------------------------------------------------------
# 21. Schema-level invariants
# ---------------------------------------------------------------------------


class TestSchemaInvariants:
    def test_table_name_is_capex_sub_lines(self, report):
        assert report["schema_sketch"]["table_name"] == "capex_sub_lines"

    def test_sub_line_id_is_unique(self, report):
        ddl = " ".join(report["schema_sketch"]["ddl_outline"])
        assert "sub_line_id" in ddl
        assert "UNIQUE" in ddl

    def test_project_id_is_fk(self, report):
        ddl = " ".join(report["schema_sketch"]["ddl_outline"])
        assert "project_id" in ddl
        assert "FK" in ddl or "REFERENCES" in ddl

    def test_unique_constraint_on_project_business_code(self, report):
        ddl = " ".join(report["schema_sketch"]["ddl_outline"])
        assert "UNIQUE(project_id, business_code)" in ddl

    def test_soft_delete_column_present(self, report):
        ddl = " ".join(report["schema_sketch"]["ddl_outline"])
        assert "is_active" in ddl
        assert "0" in ddl  # soft-delete default

    def test_replay_metadata_column_present(self, report):
        ddl = " ".join(report["schema_sketch"]["ddl_outline"])
        assert "replay_metadata_json" in ddl

    def test_index_present(self, report):
        ddl = " ".join(report["schema_sketch"]["ddl_outline"])
        assert "INDEX" in ddl
        assert "idx_capex_sub_lines_project" in ddl
