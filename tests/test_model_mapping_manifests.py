import csv
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = REPO_ROOT / "docs" / "model_mapping"
VALIDATOR = ARTIFACT_DIR / "tools" / "model_mapping" / "validate_manifests.py"
BUILDER = ARTIFACT_DIR / "tools" / "model_mapping" / "build_artifacts.py"


def _load_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _run_validator(cwd: Path = REPO_ROOT):
    return subprocess.run(
        [sys.executable, "docs/model_mapping/tools/model_mapping/validate_manifests.py"],
        cwd=cwd,
        text=True,
        capture_output=True,
    )


def _mutate_unresolved(mutator):
    path = ARTIFACT_DIR / "unresolved_pack_id_evidence.csv"
    report_path = ARTIFACT_DIR / "validation_report_v5.json"
    original_csv = path.read_text(encoding="utf-8", errors="replace")
    original_report = report_path.read_text(encoding="utf-8", errors="replace") if report_path.exists() else None
    try:
        rows = _load_csv(path)
        mutator(rows)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return _run_validator(REPO_ROOT)
    finally:
        path.write_text(original_csv, encoding="utf-8")
        if original_report is not None:
            report_path.write_text(original_report, encoding="utf-8")


def _mutate_json(rel_path: str, mutator):
    path = ARTIFACT_DIR / rel_path
    report_path = ARTIFACT_DIR / "validation_report_v5.json"
    original_json = path.read_text(encoding="utf-8", errors="replace")
    original_report = report_path.read_text(encoding="utf-8", errors="replace") if report_path.exists() else None
    try:
        payload = json.loads(original_json)
        mutator(payload)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return _run_validator(REPO_ROOT)
    finally:
        path.write_text(original_json, encoding="utf-8")
        if original_report is not None:
            report_path.write_text(original_report, encoding="utf-8")


def _row(pack_id: str):
    rows = _load_csv(ARTIFACT_DIR / "unresolved_pack_id_evidence.csv")
    return next(r for r in rows if r["pack_id"] == pack_id)


def test_validator_accepts_committed_artifacts():
    result = _run_validator()
    assert result.returncode == 0, result.stdout + result.stderr


def test_required_artifacts_exist():
    required = [
        "README.md",
        "discrepancies.md",
        "implementation_backlog.md",
        "inputs_scenarios_ui_handoff.md",
        "canonical_field_catalog_v5.csv",
        "canonical_registry_crosswalk_v5.csv",
        "input_coverage_matrix_v5.csv",
        "unresolved_pack_id_evidence.csv",
        "canonical_to_pack_id_evidence.csv",
        "coverage_summary_v5.json",
        "validation_report_v5.json",
        "support_package_metadata_audit_v5_3_1.json",
    ]
    missing = [rel for rel in required if not (ARTIFACT_DIR / rel).is_file()]
    assert missing == []


def test_v53_unresolved_schema_has_explicit_evidence_axes():
    rows = _load_csv(ARTIFACT_DIR / "unresolved_pack_id_evidence.csv")
    cols = set(rows[0])
    assert "evidence_basis" in cols
    assert "mapping_verification_status" in cols
    assert "verified_editable_cell_tuho" in cols
    assert "verified_editable_cell_oborovo" in cols
    assert "verification_basis" not in cols
    assert "verification_status" not in cols


def test_v53_summary_reports_axis_counts():
    summary = _load_json(ARTIFACT_DIR / "coverage_summary_v5.json")
    assert summary["summary_version"] == "v5.3"
    axes = summary["v53_evidence_axes"]
    assert axes["label_cell_count"] > 0
    assert axes["value_cell_count"] > 0
    assert axes["editable_cell_count"] > 0
    assert axes["formula_cell_count"] > 0
    assert "MAPPING_CONFIRMED" in axes["by_mapping_verification_status"]


def test_vat_rate_uses_value_and_editable_axes_not_label_axis():
    row = _row("tax.vat.rate")
    assert row["cell_role"] == "EDITABLE_HARDCODE"
    assert row["verified_label_cell_tuho"].startswith("A")
    assert row["verified_value_cell_tuho"] == row["verified_editable_cell_tuho"]
    assert row["verified_value_cell_tuho"] != row["verified_label_cell_tuho"]


def test_d_column_hardcode_can_be_editable_when_source_metadata_says_so():
    row = _row("tax.vat.rate")
    assert row["verified_editable_cell_tuho"].startswith("D")
    assert row["evidence_basis"] == "PROGRAMMATIC_WORKBOOK_INSPECTION"


def test_formula_axis_can_be_c_column_when_source_metadata_says_so():
    row = _row("equity.investor_2_share")
    assert row["cell_role"] == "FORMULA_RESULT"
    assert row["verified_formula_cell_tuho"].startswith("C")
    assert row["verified_value_cell_tuho"] == ""
    assert row["verified_editable_cell_tuho"] == ""


def test_wht_reimbursement_is_absence_confirmed_not_vat_alias():
    row = _row("tax.wht.reimbursed")
    assert row["cell_role"] == "UNRESOLVED"
    assert row["mapping_verification_status"] == "ABSENCE_CONFIRMED"
    assert row["verified_value_cell_tuho"] == ""
    assert row["verified_editable_cell_tuho"] == ""


def test_cost_and_formula_content_is_not_committed_in_public_mapping_delivery():
    forbidden = [
        "VISUAL" + "_" + "AUDIT",
        "INDEX" + "/" + "MATCH",
        "=" + "Scenarios",
        "=" + "SUM",
        "D421 " + "= ",
        "C301 " + "=",
        "." + "xlsm",
        "." + "xlsx",
    ]
    files = [
        p for p in ARTIFACT_DIR.rglob("*")
        if p.is_file() and "source" not in p.parts and "__pycache__" not in p.parts
    ] + [Path(__file__)]
    offenders = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in forbidden:
            if token in text:
                offenders.append((path, token))
    assert offenders == []


def test_builder_is_deterministic():
    comparable = [
        "canonical_field_catalog_v5.csv",
        "canonical_registry_crosswalk_v5.csv",
        "input_coverage_matrix_v5.csv",
        "unresolved_pack_id_evidence.csv",
    ]
    before = {rel: (ARTIFACT_DIR / rel).read_text(encoding="utf-8", errors="replace") for rel in comparable}
    before_summary = _load_json(ARTIFACT_DIR / "coverage_summary_v5.json")
    before_summary.pop("real_pytest_node_ids_collected", None)
    result = subprocess.run([sys.executable, str(BUILDER)], cwd=REPO_ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    after = {rel: (ARTIFACT_DIR / rel).read_text(encoding="utf-8", errors="replace") for rel in before}
    assert after == before
    after_summary = _load_json(ARTIFACT_DIR / "coverage_summary_v5.json")
    after_summary.pop("real_pytest_node_ids_collected", None)
    assert after_summary == before_summary


def test_mutation_rejects_legacy_verification_columns():
    result = _mutate_unresolved(
        lambda rows: rows[0].update({"verification_basis": "legacy"}),
    )
    assert result.returncode != 0
    assert "legacy columns" in result.stdout


def test_mutation_rejects_bad_cell_role():
    result = _mutate_unresolved(
        lambda rows: rows[0].update({"cell_role": "BAD_ROLE"}),
    )
    assert result.returncode != 0
    assert "invalid cell_role" in result.stdout


def test_mutation_rejects_bad_evidence_basis():
    result = _mutate_unresolved(
        lambda rows: rows[0].update({"evidence_basis": "MANUAL_SCREENSHOT"}),
    )
    assert result.returncode != 0
    assert "invalid evidence_basis" in result.stdout


def test_mutation_rejects_bad_mapping_status():
    result = _mutate_unresolved(
        lambda rows: rows[0].update({"mapping_verification_status": "CONFIRMED"}),
    )
    assert result.returncode != 0
    assert "invalid mapping_verification_status" in result.stdout


def test_mutation_rejects_mapping_confirmed_without_coordinates():
    def mutate(rows):
        row = rows[0]
        for key in list(row):
            if key.startswith("verified_"):
                row[key] = ""
        row["mapping_verification_status"] = "MAPPING_CONFIRMED"

    result = _mutate_unresolved(mutate)
    assert result.returncode != 0
    assert "without coordinates" in result.stdout


def test_mutation_rejects_absence_confirmed_with_coordinates():
    def mutate(rows):
        row = next(r for r in rows if r["pack_id"] == "tax.wht.reimbursed")
        row["mapping_verification_status"] = "ABSENCE_CONFIRMED"
        row["verified_value_cell_tuho"] = "D419"

    result = _mutate_unresolved(mutate)
    assert result.returncode != 0
    assert "ABSENCE_CONFIRMED with coordinates" in result.stdout


def test_mutation_rejects_formula_role_with_editable_axis():
    def mutate(rows):
        row = next(r for r in rows if r["pack_id"] == "equity.investor_2_share")
        row["verified_editable_cell_tuho"] = row["verified_formula_cell_tuho"]

    result = _mutate_unresolved(mutate)
    assert result.returncode != 0
    assert "formula role must not carry editable axis" in result.stdout


def test_mutation_rejects_editable_role_with_formula_axis():
    def mutate(rows):
        row = next(r for r in rows if r["pack_id"] == "tax.vat.rate")
        row["verified_formula_cell_tuho"] = row["verified_value_cell_tuho"]

    result = _mutate_unresolved(mutate)
    assert result.returncode != 0
    assert "editable role must not carry formula axis" in result.stdout


def test_mutation_rejects_value_cell_that_is_not_hardcode_source():
    def mutate(rows):
        row = next(r for r in rows if r["pack_id"] == "equity.investor_2_share")
        row["cell_role"] = "EDITABLE_HARDCODE"
        row["verified_value_cell_tuho"] = row["verified_formula_cell_tuho"]
        row["verified_editable_cell_tuho"] = row["verified_formula_cell_tuho"]
        row["verified_formula_cell_tuho"] = ""

    result = _mutate_unresolved(mutate)
    assert result.returncode != 0
    assert "not source hardcode evidence" in result.stdout


def test_mutation_rejects_formula_cell_that_is_not_formula_source():
    def mutate(rows):
        row = next(r for r in rows if r["pack_id"] == "tax.vat.rate")
        row["cell_role"] = "FORMULA_RESULT"
        for model in ("tuho", "oborovo"):
            row[f"verified_formula_cell_{model}"] = "Z999"
            row[f"verified_value_cell_{model}"] = ""
            row[f"verified_editable_cell_{model}"] = ""

    result = _mutate_unresolved(mutate)
    assert result.returncode != 0
    assert "not source formula evidence" in result.stdout


def test_mutation_rejects_unshared_coordinate_reuse():
    def mutate(rows):
        vat = next(r for r in rows if r["pack_id"] == "tax.vat.rate")
        stamp = next(r for r in rows if r["pack_id"] == "tax.stamp_duty.rate")
        stamp["verified_value_cell_tuho"] = vat["verified_value_cell_tuho"]
        stamp["verified_editable_cell_tuho"] = vat["verified_editable_cell_tuho"]

    result = _mutate_unresolved(mutate)
    assert result.returncode != 0
    assert "reused without shared_source_id" in result.stdout


def test_mutation_rejects_vat_wht_reimbursement_alias():
    def mutate(rows):
        vat = next(r for r in rows if r["pack_id"] == "tax.vat.reimbursed")
        wht = next(r for r in rows if r["pack_id"] == "tax.wht.reimbursed")
        wht["cell_role"] = "TOGGLE"
        wht["mapping_verification_status"] = "MAPPING_CONFIRMED"
        wht["verified_value_cell_tuho"] = vat["verified_value_cell_tuho"]
        wht["verified_editable_cell_tuho"] = vat["verified_editable_cell_tuho"]

    result = _mutate_unresolved(mutate)
    assert result.returncode != 0
    assert "tax.wht.reimbursed must remain absence-confirmed" in result.stdout


def test_mutation_rejects_missing_vat_editable_axis():
    def mutate(rows):
        row = next(r for r in rows if r["pack_id"] == "tax.vat.reimbursed")
        row["verified_editable_cell_tuho"] = ""

    result = _mutate_unresolved(mutate)
    assert result.returncode != 0
    assert "tax.vat.reimbursed tuho must keep" in result.stdout


def test_mutation_rejects_missing_investor2_formula_axis():
    def mutate(rows):
        row = next(r for r in rows if r["pack_id"] == "equity.investor_2_share")
        row["verified_formula_cell_tuho"] = ""

    result = _mutate_unresolved(mutate)
    assert result.returncode != 0
    assert "equity.investor_2_share tuho must be formula-axis" in result.stdout


def test_mutation_rejects_missing_thin_cap_ratio_formula_axis():
    def mutate(rows):
        row = next(r for r in rows if r["pack_id"] == "tax.max_shl_to_equity_ratio")
        row["verified_formula_cell_tuho"] = ""

    result = _mutate_unresolved(mutate)
    assert result.returncode != 0
    assert "tax.max_shl_to_equity_ratio tuho must be formula-axis" in result.stdout


def test_validation_report_is_current_and_green():
    report = _load_json(ARTIFACT_DIR / "validation_report_v5.json")
    assert report["status"] == "PASS"
    assert report["error_count"] == 0


def test_v531_support_audit_reconciles_row_counts_and_package_noise():
    audit = _load_json(ARTIFACT_DIR / "support_package_metadata_audit_v5_3_1.json")
    assert audit["version"] == "v5.3.1"
    assert audit["inputs"]["package_rows"] == 706
    assert audit["inputs"]["manifest_rows"] == 706
    assert audit["inputs"]["missing_rows"] == 0
    assert audit["inputs"]["extra_rows"] == 0
    assert audit["scenarios"]["package_rows"] == 550
    assert audit["scenarios"]["manifest_rows"] == 550
    assert audit["scenarios"]["missing_rows"] == 0
    assert audit["scenarios"]["extra_rows"] == 0
    assert audit["inputs"]["package_hardcodes_reclassified_as_formula"] == 330
    assert audit["inputs"]["candidate_input_formula_conflicts"] == 14
    assert audit["scenarios"]["active_formula_claim_mismatches"] == 478


def test_v531_verified_storage_sets_are_disjoint():
    audit = _load_json(ARTIFACT_DIR / "support_package_metadata_audit_v5_3_1.json")
    storage = audit["verified_storage"]
    assert storage["hardcode_formula_overlap_count"] == 0
    assert storage["hardcode_empty_overlap_count"] == 0
    assert storage["formula_empty_overlap_count"] == 0
    assert storage["hardcode_cell_count"] > 0
    assert storage["formula_cell_count"] > 0
    assert storage["empty_cell_count"] > 0


def test_v531_curated_evidence_zero_issue_storage_audit():
    audit = _load_json(ARTIFACT_DIR / "support_package_metadata_audit_v5_3_1.json")
    curated = audit["curated_evidence"]
    assert curated["value_editable_formula_coordinates_checked"] == 94
    assert curated["total_coordinates_checked"] == 112
    assert curated["hardcode_evidence_valid"] == 88
    assert curated["formula_evidence_valid"] == 6
    assert curated["period_evidence_valid"] == 6
    assert curated["counterparty_label_evidence_valid"] == 12
    assert curated["issues"] == 0


def test_v531_source_rows_have_verified_storage_basis():
    for rel in [
        "source/tuho_inputs_source_v2.json",
        "source/oborovo_inputs_source_v2.json",
        "source/tuho_scenarios_source_v2.json",
        "source/oborovo_scenarios_source_v2.json",
    ]:
        payload = _load_json(ARTIFACT_DIR / rel)
        assert payload["storage_verification_basis"] == "PROGRAMMATIC_WORKBOOK_INSPECTION"
        assert all(r["storage_verification_basis"] == "PROGRAMMATIC_WORKBOOK_INSPECTION" for r in payload["rows"])


def test_v531_depreciation_formula_conflicts_not_verified_hardcode():
    audit = _load_json(ARTIFACT_DIR / "support_package_metadata_audit_v5_3_1.json")
    affected = {(r["model"], r["row"]) for r in audit["inputs"]["candidate_input_formula_conflict_rows"]}
    assert affected == {
        ("TUHO", 375),
        ("TUHO", 376),
        ("TUHO", 378),
        ("OBOROVO", 392),
        ("OBOROVO", 393),
        ("OBOROVO", 395),
    }


def test_v531_blank_scenario_override_semantics_preserved():
    for rel in ["tuho_scenario_manifest_v5.json", "oborovo_scenario_manifest_v5.json"]:
        rows = _load_json(ARTIFACT_DIR / rel)["rows"]
        assert all("zero" not in r.get("classification_reason", "").lower() for r in rows)


def test_v531_mutation_rejects_formula_moved_into_verified_hardcodes():
    def mutate(payload):
        row = next(r for r in payload["rows"] if r.get("verified_formula_cells"))
        formula_cell = row["verified_formula_cells"].split(",")[0].strip()
        row["verified_hardcode_cells"] = (row.get("verified_hardcode_cells", "") + ", " + formula_cell).strip(", ")

    result = _mutate_json("source/tuho_inputs_source_v2.json", mutate)
    assert result.returncode != 0
    assert "coordinate in hardcode and formula sets" in result.stdout


def test_v531_mutation_rejects_formula_only_editable_input():
    def mutate(payload):
        row = payload["rows"][0]
        row["workbook_classification"] = "EDITABLE_INPUT"
        row["verified_hardcode_cells"] = ""
        row["verified_formula_cells"] = "D2"

    result = _mutate_json("source/tuho_inputs_source_v2.json", mutate)
    assert result.returncode != 0
    assert "EDITABLE_INPUT has only formula-backed value cells" in result.stdout


def test_v531_mutation_rejects_scenario_active_formula_mismatch():
    def mutate(payload):
        row = next(r for r in payload["rows"] if r.get("verified_active_cell_storage_kind") == "HARDCODE")
        row["verified_active_cell_storage_kind"] = "FORMULA"

    result = _mutate_json("source/tuho_scenarios_source_v2.json", mutate)
    assert result.returncode != 0
    assert "active marked FORMULA but not verified formula" in result.stdout


def test_v531_mutation_rejects_curated_editable_to_formula_storage():
    def mutate(payload):
        row = next(r for r in payload["rows"] if r.get("row") == 421)
        editable_cell = row["verified_hardcode_cells"].split(",")[0].strip()
        row["verified_hardcode_cells"] = ""
        row["verified_formula_cells"] = editable_cell

    result = _mutate_json("source/tuho_inputs_source_v2.json", mutate)
    assert result.returncode != 0
    assert "curated: tax.vat.rate tuho value cell" in result.stdout


def test_v531_mutation_rejects_curated_formula_to_hardcode_storage():
    def mutate(payload):
        row = next(r for r in payload["rows"] if r.get("row") == 301)
        formula_cell = row["verified_formula_cells"].split(",")[0].strip()
        row["verified_formula_cells"] = ""
        row["verified_hardcode_cells"] = formula_cell

    result = _mutate_json("source/tuho_inputs_source_v2.json", mutate)
    assert result.returncode != 0
    assert "curated: equity.investor_2_share tuho formula cell" in result.stdout


def test_v531_mutation_rejects_formula_period_without_formula_storage():
    def mutate(payload):
        row = next(r for r in payload["rows"] if r.get("field_id_candidate") == "reserves.dsra")
        row["verified_formula_cells"] = row["verified_formula_cells"].replace("D330", "")

    result = _mutate_json("source/tuho_inputs_source_v2.json", mutate)
    assert result.returncode != 0
    assert "formula-period cell D330 is not verified formula" in result.stdout


def test_v531_mutation_rejects_package_claim_promotion():
    def mutate(payload):
        row = payload["rows"][0]
        row["workbook_classification"] = "EDITABLE_INPUT"
        row["package_claim_hardcode_cells"] = "D2"
        row["verified_hardcode_cells"] = ""
        row["verified_formula_cells"] = ""

    result = _mutate_json("source/tuho_inputs_source_v2.json", mutate)
    assert result.returncode != 0
    assert "package_claim_hardcode_cells cannot establish EDITABLE_INPUT" in result.stdout


def test_v531_mutation_rejects_blank_scenario_zero_semantics():
    def mutate(payload):
        row = payload["rows"][0]
        row["scenario_value_kind"] = "empty"
        row["workbook_classification"] = "SCENARIO_OVERRIDE"
        row["classification_reason"] = "blank treated as zero"

    result = _mutate_json("tuho_scenario_manifest_v5.json", mutate)
    assert result.returncode != 0
    assert "blank scenario override must remain inherit" in result.stdout


def test_v531_mutation_rejects_audit_count_drift():
    def mutate(payload):
        payload["inputs"]["package_rows"] = 705
        payload["inputs"]["manifest_rows"] = 705

    result = _mutate_json("support_package_metadata_audit_v5_3_1.json", mutate)
    assert result.returncode != 0
    assert "input manifest row count does not reconcile" in result.stdout


def test_v531_mutation_rejects_dropped_input_row():
    def mutate(payload):
        payload["rows"] = payload["rows"][:-1]

    result = _mutate_json("source/tuho_inputs_source_v2.json", mutate)
    assert result.returncode != 0
    assert "input manifest row count does not reconcile" in result.stdout
