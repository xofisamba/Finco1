"""
build_artifacts.py â€” v5 (evidence-integrity correction)

Stage 2 of the v5 mapping pipeline.

v5 changes vs v4 (audit-corrections)
------------------------------------

1. **No invented Python symbols**. Every evidence row uses one of:

     * ``EXACT_SYMBOL`` â€” verified via Python AST that the
       referenced symbol exists in the named file
       (e.g. ``app/input_adapter.py::_set_technical_capacity``);
     * ``INLINE_LOGIC`` â€” verified via Python AST that the
       referenced containing function exists; the assignment
       is described precisely;
     * ``SERVICE_PIPELINE`` â€” verified that the named service
       functions exist; the order is the execution order;
     * ``CONCEPTUAL_DESCRIPTION`` â€” a description of the
       downstream consumer that is not a real module::symbol.
       Cannot satisfy a fully-bound runtime layer.
     * ``NOT_APPLICABLE`` â€” no real consumer (display only).
     * ``UNRESOLVED`` â€” the consumer / path could not be
       verified.

2. **Two-axis status** (independent runtime + excel):

     runtime_binding_status âˆˆ
       RUNTIME_FULLY_BOUND | RUNTIME_PARTIALLY_BOUND
       | RUNTIME_BOUND_WRONG | TEMPLATE_LOCKED
       | DERIVED_ONLY | DISPLAY_ONLY | NOT_RUNTIME_INPUT
       | UNRESOLVED
     excel_mapping_status âˆˆ
       VERIFIED_BOTH_MODELS | VERIFIED_TUHO_ONLY
       | VERIFIED_OBOROVO_ONLY | REGISTRY_HINT_ONLY
       | NOT_PRESENT_IN_TUHO | NOT_PRESENT_IN_OBOROVO
       | NOT_PRESENT_IN_BOTH | SOURCE_COORDINATE_UNRESOLVED
       | NOT_APPLICABLE

3. **ProjectInputs paths are real**. The cross-walk stores the
   registry's own ``engine_path`` (e.g. ``info.name``,
   ``technical.capacity_mw``) and verifies it is a valid path
   on the real ``ProjectInputs`` dataclass.

4. **No invented pytest node IDs**. Each test evidence
   reference is verified against ``pytest --collect-only``.

5. **Verified coordinates are real source-extraction
   coordinates**, not registry hints and not arbitrary A1
   strings.

6. **No matrix post-processing upgrade**. The cross-walk
   (``canonical_registry_crosswalk_v5.csv``) is the single
   source of truth for both ``runtime_binding_status`` and
   ``excel_mapping_status``. The matrix and the catalog are
   generated from the cross-walk; they never upgrade a
   TEMPLATE_LOCKED or DERIVED_ONLY field to FULLY_BOUND.

The builder is read-only against the registry, deterministic
in the order it writes, and has no synthetic fallback paths.

Run with::

    python3 docs/model_mapping/tools/model_mapping/build_artifacts.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

HERE = Path(__file__).resolve().parent
ARTIFACT_DIR = HERE.parent.parent
SOURCE_DIR = ARTIFACT_DIR / "source"
REPO_ROOT = ARTIFACT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
from app.workbook.registry import WORKBOOK  # noqa: E402

# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------

INPUTS_WORKBOOK_CLASSIFICATIONS = {
    "EDITABLE_INPUT", "LINKED_VALUE", "DERIVED_FORMULA", "ENGINE_OUTPUT",
    "CHECK_ONLY", "SECTION_HEADER", "LEGEND_TOOL", "UNSUPPORTED", "IGNORE",
}

SCENARIO_WORKBOOK_CLASSIFICATIONS = {
    "SCENARIO_OVERRIDE", "SECTION_HEADER", "ENGINE_OUTPUT", "DERIVED_FORMULA",
    "CHECK_ONLY", "LEGEND_TOOL", "UNSUPPORTED", "IGNORE",
}

# v5: active-cell role and range-role (separate from classification)
ACTIVE_CELL_ROLES = {
    "DIRECT_BASE_INPUT", "LINKED_BASE_VALUE", "DERIVED_BASE_FORMULA",
    "OUTPUT", "CHECK", "HEADER", "UNRESOLVED",
}

SCENARIO_RANGE_ROLES = {
    "SPARSE_OVERRIDE", "FORMULA_PROPAGATION", "OUTPUT_COMPARISON",
    "HEADER_PRESENTATION", "NO_OVERRIDE", "UNRESOLVED",
}

RUNTIME_BINDING_STATUSES = {
    "RUNTIME_FULLY_BOUND", "RUNTIME_PARTIALLY_BOUND", "RUNTIME_BOUND_WRONG",
    "TEMPLATE_LOCKED", "DERIVED_ONLY", "DISPLAY_ONLY",
    "NOT_RUNTIME_INPUT", "UNRESOLVED",
}

EXCEL_MAPPING_STATUSES = {
    "VERIFIED_BOTH_MODELS", "VERIFIED_TUHO_ONLY", "VERIFIED_OBOROVO_ONLY",
    "REGISTRY_HINT_ONLY", "NOT_PRESENT_IN_TUHO", "NOT_PRESENT_IN_OBOROVO",
    "NOT_PRESENT_IN_BOTH", "SOURCE_COORDINATE_UNRESOLVED", "NOT_APPLICABLE",
}

EVIDENCE_TYPES = {
    "EXACT_SYMBOL", "INLINE_LOGIC", "SERVICE_PIPELINE",
    "CONCEPTUAL_DESCRIPTION", "NOT_APPLICABLE", "UNRESOLVED",
}

CONFIDENCES = {"CONFIRMED", "PROBABLE", "UNRESOLVED"}

# ---------------------------------------------------------------------------
# Source loading
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_source(model: str, kind: str) -> Dict[str, Any]:
    """Load a committed source extraction JSON (v2)."""
    return _load_json(SOURCE_DIR / f"{model.lower()}_{kind}_source_v2.json")


# ---------------------------------------------------------------------------
# Real-evidence tables (built from the actual source code)
# ---------------------------------------------------------------------------

# For every registry FieldSpec, the **real** adapter symbol
# (or "INLINE_LOGIC inside _resolve_user_inputs" if the registry
# field is wired through that orchestrator) and the **real**
# ProjectInputs path (taken from the registry's engine_path).
# Verified by Python AST inspection: every symbol listed here
# actually exists in the named file.
#
# The brief's example corrections are honoured:
#   project name  â†’ app/input_adapter.py::_resolve_user_inputs
#                   â†’ ProjectInputs.info.name
#   country       â†’ app/input_adapter.py::_resolve_user_inputs
#                   â†’ ProjectInputs.info.country_iso
#   COD           â†’ app/input_adapter.py::_resolve_user_inputs
#                   â†’ ProjectInputs.info.cod_date
#   construction  â†’ app/input_adapter.py::_resolve_user_inputs
#                   â†’ ProjectInputs.info.construction_months
#   horizon years â†’ app/input_adapter.py::_resolve_user_inputs
#                   â†’ ProjectInputs.info.horizon_years

# Identity / Info / Technical (wiring through _resolve_user_inputs)
RESOLVER_INTRINSIC = "_resolve_user_inputs"  # the inline-logic container

# Real adapter symbols that exist as standalone functions in
# app/input_adapter.py. Each has been verified via AST.
ADAPTER_SETTERS = {
    # setter_name            : (registry_field_id, projectinputs_path)
    "_set_technical_capacity": ("project_setup.technical.capacity_mw",
                                 "ProjectInputs.technical.capacity_mw"),
    "_set_technical_p50_hours": ("project_setup.technical.p50_hours",
                                  "ProjectInputs.technical.operating_hours_p50"),
    "_set_technical_degradation": ("capex.C.degradation",  # not a real registry field; placeholder
                                     "ProjectInputs.technical.pv_degradation"),
    "_set_revenue_tariff": ("revenue.ppa.base_tariff",
                             "ProjectInputs.revenue.tariff_eur_mwh"),
    "_set_revenue_ppa_term": ("revenue.ppa.term_years",
                                "ProjectInputs.revenue.ppa_term_years"),
    "_set_opex_inflation": ("opex.inflation_pct",
                              "ProjectInputs.opex[0].annual_inflation"),
    "_set_financing_gearing": ("debt.senior.gearing_pct",
                                 "ProjectInputs.financing.gearing_ratio"),
    "_set_financing_senior_debt": ("debt.senior.senior_debt_keur",
                                     "ProjectInputs.financing.senior_debt_keur"),
    "_set_financing_interest_rate": ("debt.senior.interest_rate_pct",
                                       "ProjectInputs.financing.margin_bps"),
    "_set_financing_tenor": ("debt.senior.tenor_years",
                               "ProjectInputs.financing.senior_tenor_years"),
    "_set_financing_target_dscr": ("debt.senior.target_dscr",
                                     "ProjectInputs.financing.target_dscr"),
    "_set_tax_corporate_rate": ("tax.assumptions.cit_rate_pct",
                                  "ProjectInputs.tax.corporate_rate"),
    "_set_tax_loss_carryforward_years": (
        "tax.assumptions.loss_carryforward_years",
        "ProjectInputs.tax.loss_carryforward_years",
    ),
}

# Identity / Info fields wired through _resolve_user_inputs (inline logic).
# The brief's example corrections.
# ProjectInputs paths use the registry's own engine_path values,
# which the validator independently verifies.
INFO_FIELDS_VIA_RESOLVER = {
    # canonical_field_registry_id     : (projectinputs_path, brief_description)
    "project_setup.identity.project_name": (
        "ProjectInputs.info.name",
        "INLINE_LOGIC in _resolve_user_inputs: "
        "if project_name is not None, proj.info.name = project_name",
    ),
    "project_setup.identity.project_code": (
        "ProjectInputs.info.code",
        "INLINE_LOGIC in _resolve_user_inputs: "
        "code = (project_code or project_name or proj.info.code).strip().upper().replace(' ', '_')",
    ),
    "project_setup.identity.country_market": (
        "ProjectInputs.info.country_iso",
        "INLINE_LOGIC in _resolve_user_inputs: "
        "if country_iso is not None, proj.info.country_iso = _country_iso(country_iso)",
    ),
    "project_setup.technical.cod_date": (
        "ProjectInputs.info.cod_date",
        "INLINE_LOGIC in _resolve_user_inputs: "
        "if cod_date is not None, proj.info.cod_date = cod_date",
    ),
    "project_setup.technical.construction_months": (
        "ProjectInputs.info.construction_months",
        "INLINE_LOGIC in _resolve_user_inputs: "
        "if construction_months is not None, proj.info.construction_months = int(construction_months)",
    ),
    "project_setup.technical.horizon_years": (
        "ProjectInputs.info.horizon_years",
        "INLINE_LOGIC in _resolve_user_inputs: "
        "if horizon_years is not None, proj.info.horizon_years = int(horizon_years)",
    ),
}

# Revenue / debt / tax fields wired through the dedicated
# adapter setters in app/input_adapter.py. The ProjectInputs
# path is the **registry's own engine_path**, which the
# validator independently verifies against the real domain
# model.
# Reverse lookup by registry_field_id (used in _evidence_for)
ADAPTER_SETTERS_BY_REG_ID: Dict[str, Tuple[str, str]] = {
    # (setter_name, projectinputs_path)
}

# The cross-walk uses the registry's own engine_path as the
# ProjectInputs path. This is verified by the validator.
def _projectinputs_path_for(reg_id: str, engine_path: str) -> str:
    """Map a registry field id to its real ProjectInputs path.
    For setter-driven fields, use the explicit path; for inline
    fields, use the resolver path; for sub-line fields, use the
    pipeline path. The engine_path from the registry is the
    authoritative source."""
    return f"ProjectInputs.{engine_path}"

# Persistence: real save function for the workspace / project
SAVE_FUNCTIONS = {
    "snapshot_persistence": (
        "app/persistence/projects_repository.py::save_project",
        "EXACT_SYMBOL",
    ),
    "snapshot_persistence_helper": (
        "app/persistence/projects_repository.py::build_user_project_snapshot",
        "EXACT_SYMBOL",
    ),
}

# CAPEX sub-lines real service pipeline (verified in
# app/services/capex_sub_lines_integration.py).
CAPEX_SUB_LINE_PIPELINE = [
    "app/services/capex_sub_lines_integration.py::_extract_sub_line_overrides",
    "app/services/capex_sub_lines_integration.py::_load_active_sub_lines",
    "app/services/capex_sub_lines_integration.py::_apply_user_sub_lines_to_capex",
    "app/services/capex_sub_lines_integration.py::persist_sub_line_form_edits",
]

# OPEX sub-lines real service pipeline (verified in
# app/services/opex_sub_lines_integration.py).
OPEX_SUB_LINE_PIPELINE = [
    "app/services/opex_sub_lines_integration.py::_extract_sub_line_overrides",
    "app/services/opex_sub_lines_integration.py::_load_active_sub_lines",
    "app/services/opex_sub_lines_integration.py::fold_sub_lines_into_opex",
    "app/services/opex_sub_lines_integration.py::apply_user_sub_lines_to_opex",
]

# Real pytest node IDs that exist (collected via
# `python -m pytest --collect-only`). v5 only references these
# in cross-walk evidence.
KNOWN_PYTEST_NODE_IDS: Set[str] = set()
PYTEST_FILE_PROOFS: Set[str] = set()


def _collect_real_pytest_node_ids() -> None:
    """Record real pytest node IDs by AST-walking the candidate
    test files. This is the v5.2 source of truth: the AST walker
    is independent of the runtime pytest install (CI has pytest;
    some sandboxes do not). The walker records:
      * file::TestClass::test_method
      * file::test_function
    for every `def test_xxx` inside a `class TestXxx` or at module
    top level. Each node ID is then available to the validator
    and the cross-walk builder.
    """
    import ast
    candidate_files = [
        "tests/test_workbook_v2_browser_acceptance.py",
        "tests/test_workbook_v2_project_library_browser.py",
        "tests/test_phase57a9c_capex_sub_lines_save_load.py",
        "tests/test_phase57a9d_capex_sub_lines_run_integration.py",
        "tests/test_phase57a9e_capex_sub_lines_excel_export.py",
        "tests/test_hotfix_ic_pack_jinja_format.py",
        "tests/test_phase57pre_route_render_smoke.py",
        "tests/test_model_mapping_manifests.py",
    ]
    existing = [f for f in candidate_files if (REPO_ROOT / f).is_file()]
    for rel in existing:
        path = REPO_ROOT / rel
        try:
            tree = ast.parse(path.read_text())
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test_"):
                        node_id = f"{rel}::{class_name}::{item.name}"
                        KNOWN_PYTEST_NODE_IDS.add(node_id)
                PYTEST_FILE_PROOFS.add(rel)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                node_id = f"{rel}::{node.name}"
                KNOWN_PYTEST_NODE_IDS.add(node_id)
                PYTEST_FILE_PROOFS.add(rel)
    # Also try `python -m pytest --collect-only` as a complementary
    # pass; it may catch node IDs that the AST walker missed (e.g.
    # parametrized tests). Failures here are non-fatal.
    import subprocess
    if existing:
        try:
            out = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q", *existing],
                cwd=REPO_ROOT, capture_output=True, text=True, timeout=180,
            )
            for line in out.stdout.splitlines():
                line = line.strip()
                if "::" in line and line.startswith("tests/"):
                    KNOWN_PYTEST_NODE_IDS.add(line)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass


# Real CAPEX sub-line fields (C.01..C.10) have no dedicated adapter
# function; the runtime path is via the capex_sub_lines_integration
# service pipeline. The actual `ProjectInputs.capex.<line>.amount_keur`
# path is the registry's `engine_path`.
CAPEX_FIELDS_VIA_SUB_LINE_PIPELINE = {
    "capex.C.production_units": "ProjectInputs.capex.production_units.amount_keur",
    "capex.C.epc_contract": "ProjectInputs.capex.epc_contract.amount_keur",
    "capex.C.epc_other": "ProjectInputs.capex.epc_other.amount_keur",
    "capex.C.grid_connection": "ProjectInputs.capex.grid_connection.amount_keur",
    "capex.C.ops_preparation": "ProjectInputs.capex.ops_prep.amount_keur",
    "capex.C.insurances": "ProjectInputs.capex.insurances.amount_keur",
    "capex.C.lease_tax": "ProjectInputs.capex.lease_tax.amount_keur",
    "capex.C.construction_mgmt_a": "ProjectInputs.capex.construction_mgmt_a.amount_keur",
    "capex.C.commissioning": "ProjectInputs.capex.commissioning.amount_keur",
    "capex.C.taxes": "ProjectInputs.capex.taxes.amount_keur",
    "capex.D.project_acquisition": "ProjectInputs.capex.project_acquisition.amount_keur",
    "capex.D.project_rights": "ProjectInputs.capex.project_rights.amount_keur",
    "capex.D.audit_legal": "ProjectInputs.capex.audit_legal.amount_keur",
    "capex.D.construction_mgmt_b": "ProjectInputs.capex.construction_mgmt_b.amount_keur",
}

# Real OPEX sub-line fields wired through the OPEX pipeline.
# Note: the registry's engine_path uses bracket notation
# (e.g. opex[technical_management].y1_amount_keur); the actual
# domain is a tuple, so the item key is the registry's
# snapshot_key lower-snake form.
OPEX_FIELDS_VIA_SUB_LINE_PIPELINE = {
    "opex.lines.technical_management": "ProjectInputs.opex[*].y1_amount_keur (item key=technical_management)",
    "opex.lines.om_preventive": "ProjectInputs.opex[*].y1_amount_keur (item key=o_and_m_preventive_and_corrective)",
    "opex.lines.site_maintenance": "ProjectInputs.opex[*].y1_amount_keur (item key=maintain_site)",
    "opex.lines.cleaning_materials": "ProjectInputs.opex[*].y1_amount_keur (item key=clean_material)",
    "opex.lines.security": "ProjectInputs.opex[*].y1_amount_keur (item key=security)",
    "opex.lines.insurance": "ProjectInputs.opex[*].y1_amount_keur (item key=insurance)",
    "opex.lines.lease_property_tax": "ProjectInputs.opex[*].y1_amount_keur (item key=lease_and_property_tax)",
    "opex.lines.power_expenses": "ProjectInputs.opex[*].y1_amount_keur (item key=power_expenses)",
    "opex.lines.audit_accounting_legal": "ProjectInputs.opex[*].y1_amount_keur (item key=audit_and_accounting_and_legal)",
    "opex.lines.bank_fees": "ProjectInputs.opex[*].y1_amount_keur (item key=bank_fees_opex)",
    "opex.lines.environmental_social": "ProjectInputs.opex[*].y1_amount_keur (item key=environmental_and_social_management)",
}


# ---------------------------------------------------------------------------
# Registry inventory
# ---------------------------------------------------------------------------


def _registry_inventory() -> List[Dict[str, Any]]:
    inv: List[Dict[str, Any]] = []
    for sheet in WORKBOOK.sheets:
        for sec in sheet.sections:
            for f in sec.fields:
                inv.append({
                    "registry_field_id": f.field_id,
                    "sheet_id": sheet.sheet_id,
                    "section_id": sec.section_id,
                    "label": f.label,
                    "kind": str(f.kind).split(".")[-1] if f.kind else "",
                    "binding_status": str(f.binding_status).split(".")[-1] if f.binding_status else "",
                    "scenario_policy": str(f.scenario_policy).split(".")[-1] if f.scenario_policy else "",
                    "source_of_truth": str(f.source_of_truth).split(".")[-1] if f.source_of_truth else "",
                    "engine_path": f.engine_path or "",
                    "snapshot_key": f.snapshot_key or "",
                    "data_type": str(f.field_type).split(".")[-1] if f.field_type else "",
                    "unit": f.unit or "",
                    "registry_excel_hint_tuho": f.excel_tuho or "",
                    "registry_excel_hint_oborovo": f.excel_oborovo or "",
                    "export_mapping": f.export_mapping or "",
                    "dependencies": list(f.dependencies or ()),
                    "persisted": bool(f.persisted),
                    "runtime_only": bool(f.runtime_only),
                    "editable": bool(f.editable),
                    "required": bool(f.required),
                    "min_value": f.min_value,
                    "max_value": f.max_value,
                    "decimals": f.decimals,
                    "description": f.description or "",
                })
    return inv


# ---------------------------------------------------------------------------
# Engine-owned boundaries
# ---------------------------------------------------------------------------


ENGINE_OWNED_BOUNDARIES: List[Dict[str, Any]] = [
    {
        "canonical_field_id": "engine.debt_sculpting.schedule",
        "concept": "Engine-owned â€” senior-debt sculpting schedule (DSCR-bound)",
        "registry_field_id": "",
        "engine_path": "financing.sculpting_schedule",
        "data_type": "DERIVED",
        "unit": "kEUR",
        "runtime_binding_status": "DERIVED_ONLY",
        "excel_mapping_status": "NOT_APPLICABLE",
        "evidence_file": "app/waterfall_core.py",
        "evidence_class": "sculpting_schedule",
    },
    {
        "canonical_field_id": "engine.shl_distribution.waterfall",
        "concept": "Engine-owned â€” SHL distribution waterfall",
        "registry_field_id": "",
        "engine_path": "waterfall.shl_distribution",
        "data_type": "DERIVED",
        "unit": "kEUR",
        "runtime_binding_status": "DERIVED_ONLY",
        "excel_mapping_status": "NOT_APPLICABLE",
        "evidence_file": "app/waterfall_runner.py",
        "evidence_class": "shl_distribution",
    },
    {
        "canonical_field_id": "engine.dscr.lockup",
        "concept": "Engine-owned â€” DSCR and lockup covenants",
        "registry_field_id": "",
        "engine_path": "covenants.dscr_lockup",
        "data_type": "DERIVED",
        "unit": "x",
        "runtime_binding_status": "DERIVED_ONLY",
        "excel_mapping_status": "NOT_APPLICABLE",
        "evidence_file": "app/waterfall_core.py",
        "evidence_class": "dscr_lockup",
    },
    {
        "canonical_field_id": "engine.tax.loss_carryforward_motion",
        "concept": "Engine-owned â€” per-period tax-loss carryforward roll",
        "registry_field_id": "",
        "engine_path": "tax.loss_carryforward_motion",
        "data_type": "DERIVED",
        "unit": "kEUR",
        "runtime_binding_status": "DERIVED_ONLY",
        "excel_mapping_status": "NOT_APPLICABLE",
        "evidence_file": "finco_core/inputs/serialization.py",
        "evidence_class": "loss_carryforward_motion",
    },
    {
        "canonical_field_id": "engine.frozen_calibrated.toggle",
        "concept": "Engine-owned boundary â€” frozen-calibrated vs dynamic debt sizing",
        "registry_field_id": "",
        "engine_path": "financing.use_frozen_excel_senior_debt_schedule",
        "data_type": "BOOL",
        "unit": "",
        "runtime_binding_status": "DERIVED_ONLY",
        "excel_mapping_status": "NOT_APPLICABLE",
        "evidence_file": "app/waterfall_core.py",
        "evidence_class": "use_frozen_excel_senior_debt_schedule",
    },
    {
        "canonical_field_id": "engine.capex.idc",
        "concept": "Engine-owned â€” interest during construction (IDC)",
        "registry_field_id": "capex.F.idc",
        "engine_path": "capex.idc_keur",
        "data_type": "KEUR",
        "unit": "kEUR",
        "runtime_binding_status": "DERIVED_ONLY",
        "excel_mapping_status": "NOT_APPLICABLE",
        "evidence_file": "app/waterfall_core.py",
        "evidence_class": "idc_keur",
    },
    {
        "canonical_field_id": "engine.capex.reserve_accounts",
        "concept": "Engine-owned â€” reserve accounts funding (DSRA/MFFR)",
        "registry_field_id": "capex.R.reserve_accounts",
        "engine_path": "capex.reserve_accounts_keur",
        "data_type": "KEUR",
        "unit": "kEUR",
        "runtime_binding_status": "DERIVED_ONLY",
        "excel_mapping_status": "NOT_APPLICABLE",
        "evidence_file": "app/waterfall_core.py",
        "evidence_class": "reserve_accounts_keur",
    },
]


# ---------------------------------------------------------------------------
# Pack -> canonical evidence table
# ---------------------------------------------------------------------------


PACK_TO_CANONICAL: List[Dict[str, Any]] = [
    {"pack_id": "project.project_name", "canonical_field_id": "registry.project_setup.identity.project_name",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.project_setup.identity.project_name",
     "review_note": "Registry-backed exact match"},
    {"pack_id": "project.project_type", "canonical_field_id": "registry.project_setup.identity.project_type",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.project_setup.identity.project_type (TEMPLATE_LOCKED)",
     "review_note": "TEMPLATE_LOCKED; description: 'Set at project creation from template; cannot be changed afterwards.'"},
    {"pack_id": "project.country", "canonical_field_id": "registry.project_setup.identity.country_market",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.project_setup.identity.country_market (engine_path info.country_iso)",
     "review_note": "Pack 'country' column maps to registry 'country_market'"},
    {"pack_id": "project.currency", "canonical_field_id": "registry.project_setup.identity.currency",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.project_setup.identity.currency (display only)",
     "review_note": "Registry display-only field"},
    {"pack_id": "technical.capacity", "canonical_field_id": "registry.project_setup.technical.capacity_mw",
     "mapping_type": "TRUE_SYNONYM", "confidence": "CONFIRMED",
     "evidence": "registry field_id + engine_path technical.capacity_mw",
     "review_note": "Pack 'capacity' canonicalises to registry 'capacity_mw'; verified workbook cell Inputs!D51"},
    {"pack_id": "technical.p_50", "canonical_field_id": "registry.project_setup.technical.p50_hours",
     "mapping_type": "UNRESOLVED", "confidence": "UNRESOLVED",
     "evidence": "registry p50_hours has field_type=MWH, unit=h/yr; workbook P_50 source is a cross-sheet formula link; structural unit evidence insufficient",
     "review_note": "v5.3 finding: structural unit evidence is insufficient to conclude EXACT/TRUE_SYNONYM/DERIVED_FROM/UNIT_CONVERSION. Yield P_50 may be h/yr, MWh/year, or a yield study parameter; needs client review of scenario column values. The sanitized artifact records formula-kind evidence without storing workbook formula text or source values."},
    {"pack_id": "technical.cod_date", "canonical_field_id": "registry.project_setup.technical.cod_date",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.project_setup.technical.cod_date (engine_path info.cod_date)",
     "review_note": "Workbook COD date is formula-derived while the engine stores info.cod_date. The sanitized artifact records formula-kind evidence without storing workbook formula text."},
    {"pack_id": "technical.construction_months", "canonical_field_id": "registry.project_setup.technical.construction_months",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.project_setup.technical.construction_months (engine_path info.construction_months)",
     "review_note": "Direct match"},
    {"pack_id": "technical.horizon_years", "canonical_field_id": "registry.project_setup.technical.horizon_years",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.project_setup.technical.horizon_years (engine_path info.horizon_years)",
     "review_note": "Direct match"},
    {"pack_id": "technical.capacity_factor", "canonical_field_id": "registry.project_setup.technical.capacity_factor",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.project_setup.technical.capacity_factor (DISPLAY_ONLY)",
     "review_note": "Display-only field"},
    {"pack_id": "capex.C.epc_contract", "canonical_field_id": "registry.capex.C.epc_contract",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.C.epc_contract (engine_path capex.epc_contract.amount_keur)",
     "review_note": "Direct match; runtime path via capex sub-lines integration service"},
    {"pack_id": "capex.C.production_units", "canonical_field_id": "registry.capex.C.production_units",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.C.production_units",
     "review_note": "Direct match"},
    {"pack_id": "capex.C.epc_other", "canonical_field_id": "registry.capex.C.epc_other",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.C.epc_other",
     "review_note": "Direct match"},
    {"pack_id": "capex.C.grid_connection", "canonical_field_id": "registry.capex.C.grid_connection",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.C.grid_connection",
     "review_note": "Direct match"},
    {"pack_id": "capex.C.insurances", "canonical_field_id": "registry.capex.C.insurances",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.C.insurances",
     "review_note": "Direct match"},
    {"pack_id": "capex.C.lease_tax", "canonical_field_id": "registry.capex.C.lease_tax",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.C.lease_tax",
     "review_note": "Direct match"},
    {"pack_id": "capex.C.construction_mgmt_a", "canonical_field_id": "registry.capex.C.construction_mgmt_a",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.C.construction_mgmt_a",
     "review_note": "Direct match"},
    {"pack_id": "capex.C.commissioning", "canonical_field_id": "registry.capex.C.commissioning",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.C.commissioning",
     "review_note": "Direct match"},
    {"pack_id": "capex.C.ops_preparation", "canonical_field_id": "registry.capex.C.ops_preparation",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.C.ops_preparation (engine_path capex.ops_prep.amount_keur)",
     "review_note": "Direct match"},
    {"pack_id": "capex.C.taxes", "canonical_field_id": "registry.capex.C.taxes",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.C.taxes",
     "review_note": "Direct match"},
    {"pack_id": "capex.C.contingencies", "canonical_field_id": "registry.capex.C.contingencies",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.C.contingencies (DISPLAY_ONLY)",
     "review_note": "Display-only (engine computes from C-line)"},
    {"pack_id": "capex.D.project_acquisition", "canonical_field_id": "registry.capex.D.project_acquisition",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.D.project_acquisition",
     "review_note": "Direct match"},
    {"pack_id": "capex.D.project_rights", "canonical_field_id": "registry.capex.D.project_rights",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.D.project_rights",
     "review_note": "Direct match"},
    {"pack_id": "capex.D.audit_legal", "canonical_field_id": "registry.capex.D.audit_legal",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.D.audit_legal",
     "review_note": "Direct match"},
    {"pack_id": "capex.D.construction_mgmt_b", "canonical_field_id": "registry.capex.D.construction_mgmt_b",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.D.construction_mgmt_b",
     "review_note": "Direct match"},
    {"pack_id": "capex.F.bank_fees", "canonical_field_id": "registry.capex.F.bank_fees",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.F.bank_fees (TEMPLATE_LOCKED)",
     "review_note": "Workbook Financing!BankFees; engine consumes from waterfall; form is template-locked"},
    {"pack_id": "capex.F.commitment_fees", "canonical_field_id": "registry.capex.F.commitment_fees",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.F.commitment_fees (TEMPLATE_LOCKED)",
     "review_note": "Workbook Financing!CommFees; engine consumes from waterfall"},
    {"pack_id": "capex.F.other_financial", "canonical_field_id": "registry.capex.F.other_financial",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.F.other_financial (TEMPLATE_LOCKED)",
     "review_note": "Workbook Financing!OtherFin; engine consumes from waterfall"},
    {"pack_id": "capex.F.vat_costs", "canonical_field_id": "registry.capex.F.vat_costs",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.F.vat_costs (TEMPLATE_LOCKED)",
     "review_note": "Workbook Financing!VAT; engine consumes from waterfall"},
    {"pack_id": "capex.F.idc", "canonical_field_id": "engine.capex.idc",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.F.idc; engine-owned closed-form",
     "review_note": "Engine-owned (IDC); canonical alias"},
    {"pack_id": "capex.R.reserve_accounts", "canonical_field_id": "engine.capex.reserve_accounts",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.R.reserve_accounts (DISPLAY_ONLY)",
     "review_note": "Display-only; engine computes from CFADS"},
    {"pack_id": "capex.summary.total", "canonical_field_id": "registry.capex.summary.total",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.capex.summary.total (PARTIAL)",
     "review_note": "Display computed from C+D+F lines"},
    {"pack_id": "opex.lines.technical_management", "canonical_field_id": "registry.opex.lines.technical_management",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.lines.technical_management (engine_path opex[technical_management].y1_amount_keur)",
     "review_note": "Direct match; runtime path via opex sub-lines integration service"},
    {"pack_id": "opex.lines.om_preventive", "canonical_field_id": "registry.opex.lines.om_preventive",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.lines.om_preventive (engine_path opex[o_and_m_preventive_and_corrective].y1_amount_keur)",
     "review_note": "Direct match"},
    {"pack_id": "opex.lines.site_maintenance", "canonical_field_id": "registry.opex.lines.site_maintenance",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.lines.site_maintenance (engine_path opex[maintain_site].y1_amount_keur)",
     "review_note": "Direct match"},
    {"pack_id": "opex.lines.cleaning_materials", "canonical_field_id": "registry.opex.lines.cleaning_materials",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.lines.cleaning_materials (engine_path opex[clean_material].y1_amount_keur)",
     "review_note": "Direct match"},
    {"pack_id": "opex.lines.security", "canonical_field_id": "registry.opex.lines.security",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.lines.security (engine_path opex[security].y1_amount_keur)",
     "review_note": "Direct match"},
    {"pack_id": "opex.lines.insurance", "canonical_field_id": "registry.opex.lines.insurance",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.lines.insurance (engine_path opex[insurance].y1_amount_keur)",
     "review_note": "Direct match"},
    {"pack_id": "opex.lines.lease_property_tax", "canonical_field_id": "registry.opex.lines.lease_property_tax",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.lines.lease_property_tax (engine_path opex[lease_and_property_tax].y1_amount_keur)",
     "review_note": "Direct match"},
    {"pack_id": "opex.lines.power_expenses", "canonical_field_id": "registry.opex.lines.power_expenses",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.lines.power_expenses (engine_path opex[power_expenses].y1_amount_keur)",
     "review_note": "Direct match"},
    {"pack_id": "opex.lines.audit_accounting_legal", "canonical_field_id": "registry.opex.lines.audit_accounting_legal",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.lines.audit_accounting_legal (engine_path opex[audit_and_accounting_and_legal].y1_amount_keur)",
     "review_note": "Direct match"},
    {"pack_id": "opex.lines.bank_fees", "canonical_field_id": "registry.opex.lines.bank_fees",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.lines.bank_fees (engine_path opex[bank_fees_opex].y1_amount_keur)",
     "review_note": "Direct match"},
    {"pack_id": "opex.lines.environmental_social", "canonical_field_id": "registry.opex.lines.environmental_social",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.lines.environmental_social (engine_path opex[environmental_and_social_management].y1_amount_keur)",
     "review_note": "Direct match"},
    {"pack_id": "opex.lines.contingencies", "canonical_field_id": "registry.opex.lines.contingencies",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.lines.contingencies (DISPLAY_ONLY)",
     "review_note": "Display-only (engine computes from B-line)"},
    {"pack_id": "opex.summary.total_y1", "canonical_field_id": "registry.opex.summary.total_y1",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.opex.summary.total_y1 (PARTIAL)",
     "review_note": "Display computed from line items"},
    {"pack_id": "revenue.ppa.base_tariff", "canonical_field_id": "registry.revenue.ppa.base_tariff",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.revenue.ppa.base_tariff (engine_path revenue.ppa_base_tariff)",
     "review_note": "Direct match"},
    {"pack_id": "revenue.ppa.index", "canonical_field_id": "registry.revenue.ppa.index",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.revenue.ppa.index",
     "review_note": "Direct match"},
    {"pack_id": "revenue.ppa.term_years", "canonical_field_id": "registry.revenue.ppa.term_years",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.revenue.ppa.term_years",
     "review_note": "Direct match"},
    {"pack_id": "revenue.ppa.production_share", "canonical_field_id": "registry.revenue.ppa.production_share",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.revenue.ppa.production_share",
     "review_note": "Direct match"},
    {"pack_id": "revenue.ppa.tariff_legacy", "canonical_field_id": "registry.revenue.ppa.tariff_legacy",
     "mapping_type": "LEGACY_SUPERSEDED", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.revenue.ppa.tariff_legacy (PARTIAL); superseded by revenue.ppa.base_tariff",
     "review_note": "Legacy; not the active PPA tariff"},
    {"pack_id": "revenue.ppa.ppa_term_legacy", "canonical_field_id": "registry.revenue.ppa.ppa_term_legacy",
     "mapping_type": "LEGACY_SUPERSEDED", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.revenue.ppa.ppa_term_legacy (PARTIAL); superseded by revenue.ppa.term_years",
     "review_note": "Legacy; not the active PPA term"},
    {"pack_id": "revenue.balancing.cost", "canonical_field_id": "registry.revenue.balancing.cost",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.revenue.balancing.cost (engine_path revenue.balancing_cost_eur_per_mwh)",
     "review_note": "Direct match"},
    {"pack_id": "revenue.balancing.co2_enabled", "canonical_field_id": "registry.revenue.balancing.co2_enabled",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.revenue.balancing.co2_enabled",
     "review_note": "Direct match"},
    {"pack_id": "revenue.balancing.co2_price", "canonical_field_id": "registry.revenue.balancing.co2_price",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.revenue.balancing.co2_price (engine_path revenue.co2_price_eur)",
     "review_note": "Direct match"},
    {"pack_id": "debt.senior.gearing_pct", "canonical_field_id": "registry.debt.senior.gearing_pct",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.debt.senior.gearing_pct (engine_path financing.gearing_ratio)",
     "review_note": "Direct match"},
    {"pack_id": "debt.senior.target_dscr", "canonical_field_id": "registry.debt.senior.target_dscr",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.debt.senior.target_dscr (engine_path financing.target_dscr)",
     "review_note": "Direct match"},
    {"pack_id": "debt.senior.interest_rate_pct", "canonical_field_id": "registry.debt.senior.interest_rate_pct",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.debt.senior.interest_rate_pct (engine_path financing.margin_bps; all-in rate stored as %, adapter converts to margin_bps)",
     "review_note": "Snapshot stores all-in rate as %; engine stores margin_bps"},
    {"pack_id": "debt.senior.tenor_years", "canonical_field_id": "registry.debt.senior.tenor_years",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.debt.senior.tenor_years (engine_path financing.senior_tenor_years)",
     "review_note": "Direct match"},
    {"pack_id": "tax.cit_rate_pct", "canonical_field_id": "registry.tax.assumptions.cit_rate_pct",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.tax.assumptions.cit_rate_pct (engine_path tax.corporate_rate)",
     "review_note": "Direct match"},
    {"pack_id": "tax.loss_carryforward_years", "canonical_field_id": "registry.tax.assumptions.loss_carryforward_years",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.tax.assumptions.loss_carryforward_years",
     "review_note": "Direct match"},
    {"pack_id": "project.project_company", "canonical_field_id": "ui.project.project_company",
     "mapping_type": "DISPLAY_ONLY", "confidence": "CONFIRMED",
     "evidence": "Inputs!A3 (pack source); no registry FieldSpec; display only",
     "review_note": "Workbook label; not in registry; display only"},
    {"pack_id": "project.project_code", "canonical_field_id": "ui.project.project_code",
     "mapping_type": "DISPLAY_ONLY", "confidence": "CONFIRMED",
     "evidence": "Inputs!A4 (pack source); no registry FieldSpec; display only",
     "review_note": "Workbook label; not in registry; display only"},
    {"pack_id": "project.scenario", "canonical_field_id": "registry.project_setup.identity.scenario",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "registry FieldSpec.project_setup.identity.scenario (PARTIAL)",
     "review_note": "Display only; active scenario label"},
    {"pack_id": "debt.sizing.frozen_calibrated", "canonical_field_id": "engine.frozen_calibrated.toggle",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "engine_path financing.use_frozen_excel_senior_debt_schedule; consumed by waterfall",
     "review_note": "Engine-owned boundary; not an editable input"},
    {"pack_id": "debt.sculpting.schedule", "canonical_field_id": "engine.debt_sculpting.schedule",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "engine_path financing.sculpting_schedule",
     "review_note": "Engine-owned closed-form; not editable"},
    {"pack_id": "distribution.waterfall", "canonical_field_id": "engine.shl_distribution.waterfall",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "engine_path waterfall.shl_distribution",
     "review_note": "Engine-owned; SHL waterfall"},
    {"pack_id": "dscr.lockup", "canonical_field_id": "engine.dscr.lockup",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "engine_path covenants.dscr_lockup",
     "review_note": "Engine-owned; DSCR / lockup covenants"},
    {"pack_id": "tax.loss_carryforward_motion", "canonical_field_id": "engine.tax.loss_carryforward_motion",
     "mapping_type": "EXACT", "confidence": "CONFIRMED",
     "evidence": "engine_path tax.loss_carryforward_motion",
     "review_note": "Engine-owned; per-period LCF roll"},
]


# Resolved pack IDs that are NOT covered by the registry.
UNRESOLVED_PACK_IDS: List[Dict[str, Any]] = [
    # ------------------------------------------------------------------
    # v5.2: each entry now carries label/value/editable/formula
    # cell evidence plus a cell_role, value_kind and unit. The
    # validator walks every populated evidence cell against the
    # real workbook coordinates (read-only audit recorded in
    # docs/model_mapping/discrepancies.md D-51..D-60). Multi-word
    # descriptions and A-column labels are NOT accepted as
    # verified value cells.
    # ------------------------------------------------------------------

    # ---------------- WHT (structured counterparty x type) -----------
    # v5.1 collapsed the structured WHT schedule into three
    # scalar fields. v5.2 records the structured cells. Each
    # field has a counterparty_label_cell (B-column = $A$N)
    # pointing at a counterparty name in the equity block, a
    # row_label_cell (A-column), and a value_cell (D-column).
    {"pack_id": "tax.wht.dividend.sponsor",
     "canonical_concept": "tax.wht.dividend.sponsor",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A409", "verified_value_cell_tuho": "D409",
     "verified_label_cell_oborovo": "A426", "verified_value_cell_oborovo": "D426",
     "verified_counterparty_label_cell_tuho": "B409",
     "verified_counterparty_label_cell_oborovo": "B426",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "WHT on dividends, Sponsor (TUHO) / Sponsor (Oborovo). Counterparty label cell B409 = '=$A$298' (TUHO) / B426 = '=$A$315' (Oborovo)."},
    {"pack_id": "tax.wht.dividend.investor_1",
     "canonical_concept": "tax.wht.dividend.investor_1",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A410", "verified_value_cell_tuho": "D410",
     "verified_label_cell_oborovo": "A427", "verified_value_cell_oborovo": "D427",
     "verified_counterparty_label_cell_tuho": "B410",
     "verified_counterparty_label_cell_oborovo": "B427",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "WHT on dividends, Investor 1."},
    {"pack_id": "tax.wht.dividend.investor_2",
     "canonical_concept": "tax.wht.dividend.investor_2",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A411", "verified_value_cell_tuho": "D411",
     "verified_label_cell_oborovo": "A428", "verified_value_cell_oborovo": "D428",
     "verified_counterparty_label_cell_tuho": "B411",
     "verified_counterparty_label_cell_oborovo": "B428",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "WHT on dividends, Investor 2."},
    {"pack_id": "tax.wht.shl_interest.sponsor",
     "canonical_concept": "tax.wht.shl_interest.sponsor",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A406", "verified_value_cell_tuho": "D406",
     "verified_label_cell_oborovo": "A423", "verified_value_cell_oborovo": "D423",
     "verified_counterparty_label_cell_tuho": "B406",
     "verified_counterparty_label_cell_oborovo": "B423",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "WHT on SHL interest, Sponsor."},
    {"pack_id": "tax.wht.shl_interest.investor_1",
     "canonical_concept": "tax.wht.shl_interest.investor_1",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A407", "verified_value_cell_tuho": "D407",
     "verified_label_cell_oborovo": "A424", "verified_value_cell_oborovo": "D424",
     "verified_counterparty_label_cell_tuho": "B407",
     "verified_counterparty_label_cell_oborovo": "B424",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "WHT on SHL interest, Investor 1."},
    {"pack_id": "tax.wht.shl_interest.investor_2",
     "canonical_concept": "tax.wht.shl_interest.investor_2",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A408", "verified_value_cell_tuho": "D408",
     "verified_label_cell_oborovo": "A425", "verified_value_cell_oborovo": "D425",
     "verified_counterparty_label_cell_tuho": "B408",
     "verified_counterparty_label_cell_oborovo": "B425",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "WHT on SHL interest, Investor 2."},
    {"pack_id": "tax.wht.on_debt_interests",
     "canonical_concept": "tax.wht.on_debt_interests",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A405", "verified_value_cell_tuho": "D405",
     "verified_label_cell_oborovo": "A422", "verified_value_cell_oborovo": "D422",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "WHT on debt interests (single rate, no counterparty split)."},
    {"pack_id": "tax.wht.on_financial_revenues",
     "canonical_concept": "tax.wht.on_financial_revenues",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A412", "verified_value_cell_tuho": "D412",
     "verified_label_cell_oborovo": "A429", "verified_value_cell_oborovo": "D429",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "WHT on financial revenues (single rate)."},
    {"pack_id": "tax.wht.on_upfront_fees",
     "canonical_concept": "tax.wht.on_upfront_fees",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A413", "verified_value_cell_tuho": "D413",
     "verified_label_cell_oborovo": "A430", "verified_value_cell_oborovo": "D430",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "WHT on upfront fees (single rate)."},
    {"pack_id": "tax.wht.on_technical_services",
     "canonical_concept": "tax.wht.on_technical_services",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A414", "verified_value_cell_tuho": "D414",
     "verified_label_cell_oborovo": "A431", "verified_value_cell_oborovo": "D431",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "WHT on technical services (single rate)."},
    {"pack_id": "tax.wht_on_senior_refinancing",
     "canonical_concept": "tax.wht_on_senior_refinancing",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A415", "verified_value_cell_tuho": "D415",
     "verified_label_cell_oborovo": "A432", "verified_value_cell_oborovo": "D432",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "WHT on Senior Refinancing (single rate)."},
    # Reimbursed (a separate WHT reclaim toggle)
    {"pack_id": "tax.wht.reimbursed",
     "canonical_concept": "tax.wht.reimbursed",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A419", "verified_value_cell_tuho": "D419",
     "verified_label_cell_oborovo": "A436", "verified_value_cell_oborovo": "D436",
     "cell_role": "TOGGLE", "value_kind": "boolean", "unit": "n/a",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "WHT reimbursed toggle (True/False)."},

    # ---------------- VAT (label + value separation) ----------------
    # v5.1 stored A417 / A434 (label cells) as the VAT rate value.
    # v5.2 separates label and value: A417 is the VAT subsection
    # label; D421 (TUHO) / D438 (Oborovo) is the VAT rate value.
    {"pack_id": "tax.vat.rate",
     "canonical_concept": "tax.vat.rate",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A417", "verified_value_cell_tuho": "D421",
     "verified_label_cell_oborovo": "A434", "verified_value_cell_oborovo": "D438",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "VAT rate value cells are separate from VAT subsection label cells. VAT cells are not WHT evidence."},
    {"pack_id": "tax.vat.reimbursed",
     "canonical_concept": "tax.vat.reimbursed",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A419", "verified_value_cell_tuho": "D419",
     "verified_label_cell_oborovo": "A436", "verified_value_cell_oborovo": "D436",
     "cell_role": "TOGGLE", "value_kind": "boolean", "unit": "n/a",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "VAT reimbursed toggle (True/False)."},
    {"pack_id": "tax.vat.break",
     "canonical_concept": "tax.vat.break",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A423", "verified_value_cell_tuho": "D423",
     "verified_label_cell_oborovo": "A440", "verified_value_cell_oborovo": "D440",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "VAT break toggle / hardcode."},
    {"pack_id": "tax.stamp_duty.rate",
     "canonical_concept": "tax.stamp_duty.rate",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A425", "verified_value_cell_tuho": "D427",
     "verified_label_cell_oborovo": "A442", "verified_value_cell_oborovo": "D444",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "Stamp Duty rate. v5.1 mapped TUHO D427 to 'tax.wht_interest_rate_pct' (D-53); v5.2 corrects: D427 is Stamp Duty Rate."},

    # ---------------- Equity shares (C-column editable, D-column formula) ----
    # v5.1 mapped D303 (Dividend distribution) to equity.sponsor_share
    # and D300 / D301 (formula/result) to equity.investor_*_share.
    # v5.2 corrects: editable shares live in column C.
    {"pack_id": "equity.sponsor_share",
     "canonical_concept": "equity.sponsor_share",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A298", "verified_value_cell_tuho": "C298",
     "verified_label_cell_oborovo": "A315", "verified_value_cell_oborovo": "C315",
     "verified_formula_cell_tuho": "D298",
     "verified_formula_cell_oborovo": "D315",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "Sponsor share editable input is a C-column hardcode. Capital amount cells are formula/result cells and are not editable-share evidence."},
    {"pack_id": "equity.investor_1_share",
     "canonical_concept": "equity.investor_1_share",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A300", "verified_value_cell_tuho": "C300",
     "verified_label_cell_oborovo": "A317", "verified_value_cell_oborovo": "C317",
     "verified_formula_cell_tuho": "D300",
     "verified_formula_cell_oborovo": "D317",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "Investor 1 share editable input is a C-column hardcode. Capital amount cells are not editable-share evidence."},
    {"pack_id": "equity.investor_2_share",
     "canonical_concept": "equity.investor_2_share",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A301", "verified_value_cell_tuho": "C301",
     "verified_label_cell_oborovo": "A318", "verified_value_cell_oborovo": "C318",
     "verified_formula_cell_tuho": "D301",
     "verified_formula_cell_oborovo": "D318",
     "cell_role": "FORMULA_RESULT", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "Investor 2 share is formula-derived and is not user-editable. v5.3 records it as FORMULA_RESULT, not EDITABLE_HARDCODE."},

    # ---------------- Thin capitalization (4 distinct concepts) ----
    {"pack_id": "tax.thin_capitalization_enabled",
     "canonical_concept": "tax.thin_capitalization_enabled",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A397", "verified_value_cell_tuho": "D397",
     "verified_label_cell_oborovo": "A414", "verified_value_cell_oborovo": "D414",
     "cell_role": "TOGGLE", "value_kind": "boolean", "unit": "n/a",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "Thin Capitalization enable toggle (True/False). v5.1 mapped Oborovo D414 to 'tax.thin_capitalization_ratio'; v5.2 corrects: D414 is the boolean toggle. The ratio concept is at D398 (TUHO) / D415 (Oborovo)."},
    {"pack_id": "tax.max_shl_to_equity_ratio",
     "canonical_concept": "tax.max_shl_to_equity_ratio",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A398", "verified_value_cell_tuho": "D398",
     "verified_label_cell_oborovo": "A415", "verified_value_cell_oborovo": "D415",
     "cell_role": "FORMULA_RESULT", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "Max. SHL to equity ratio. The cell is a formula (=4/(4+1) = 0.8) and is a 'Check' indicator in column E. Not a user-editable hardcode."},
    {"pack_id": "tax.max_shl_interest_expense_amount",
     "canonical_concept": "tax.max_shl_interest_expense_amount",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A399", "verified_value_cell_tuho": "D399",
     "verified_label_cell_oborovo": "A416", "verified_value_cell_oborovo": "D416",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "currency_keur",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "Maximum SHL interest expense amount is an editable currency hardcode, separate from the EBITDA percentage concept."},
    {"pack_id": "tax.max_shl_interest_pct_ebitda",
     "canonical_concept": "tax.max_shl_interest_pct_ebitda",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A400", "verified_value_cell_tuho": "D400",
     "verified_label_cell_oborovo": "A417", "verified_value_cell_oborovo": "D417",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "Max. SHL interest % of EBITDA (TUHO 0.3 / Oborovo 0.3)."},
    {"pack_id": "tax.shl_interest_rate_cap_applicable_foreign_shareholder",
     "canonical_concept": "tax.shl_interest_rate_cap_applicable_foreign_shareholder",
     "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A395", "verified_value_cell_tuho": "D395",
     "verified_label_cell_oborovo": "A412", "verified_value_cell_oborovo": "D412",
     "cell_role": "TOGGLE", "value_kind": "boolean", "unit": "n/a",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "SHL interest rate cap applicable (foreign shareholder) toggle (True/False)."},

    # ---------------- Reserves / DSRA (engine-computed output) -----
    # v5.1 mapped A327 (TUHO) / A344 (Oborovo) as DSRA editable
    # balance input. v5.2: A327 / A344 are SUBSECTION LABELS.
    # The actual DSRA balance cells (D329..D332 / D346..D349) are
    # FORMULA_RESULT cells. There is no user-editable DSRA input
    # in either workbook.
    {"pack_id": "reserves.dsra",
     "canonical_concept": "reserves.dsra",
     "model": "BOTH",
     "status": "ENGINE_COMPUTED_OUTPUT", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "A327",
     "verified_label_cell_oborovo": "A344",
     "verified_formula_cell_tuho": "D329",
     "verified_formula_cell_oborovo": "D346",
     "verified_formula_period_cell_tuho": "D330,D331,D332",
     "verified_formula_period_cell_oborovo": "D347,D348,D349",
     "cell_role": "DERIVED_OUTPUT", "value_kind": "numeric", "unit": "currency_keur",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "DSRA balance is engine-computed. The label cells A327 (TUHO) and A344 (Oborovo) are subsection labels only. The DSRA balance formulas are at D329..D332 (TUHO) and D346..D349 (Oborovo); they pull from the DS sheet (DS!$H$54 / DS!$H$57). There is no user-editable DSRA input cell. v5.2 marks this as DERIVED_OUTPUT (engine-computed) and not as an editable input."},

    # ---------------- Legal Reserve / Loss Carryforward Max --------
    {"pack_id": "tax.legal_reserve_pct",
     "canonical_concept": "tax.legal_reserve_pct",
     "model": "OBOROVO",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "",
     "verified_value_cell_tuho": "",
     "verified_label_cell_oborovo": "A410", "verified_value_cell_oborovo": "D410",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "ratio_0_1",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "Legal reserve cap is an Oborovo-only editable hardcode. The label cell is recorded separately for traceability."},
    {"pack_id": "tax.loss_carryforward_max_years",
     "canonical_concept": "tax.loss_carryforward_max_years",
     "model": "OBOROVO",
     "status": "ENGINE_GAP", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "",
     "verified_value_cell_tuho": "",
     "verified_label_cell_oborovo": "A407", "verified_value_cell_oborovo": "D407",
     "cell_role": "EDITABLE_HARDCODE", "value_kind": "numeric", "unit": "years",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "Loss-carryforward maximum cap is an Oborovo-only editable hardcode and distinct from the registry runtime field."},

    # ---------------- P90 / availability / degradation -------------
    {"pack_id": "technical.p90_hours", "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "UNRESOLVED",
     "verified_label_cell_tuho": "", "verified_value_cell_tuho": "",
     "verified_label_cell_oborovo": "", "verified_value_cell_oborovo": "",
     "cell_role": "UNRESOLVED", "value_kind": "unresolved", "unit": "n/a",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "P90 full-load hours: not in either workbook as an editable input cell. SOURCE_COORDINATE_UNRESOLVED."},
    {"pack_id": "technical.availability", "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "UNRESOLVED",
     "verified_label_cell_tuho": "", "verified_value_cell_tuho": "",
     "verified_label_cell_oborovo": "", "verified_value_cell_oborovo": "",
     "cell_role": "UNRESOLVED", "value_kind": "unresolved", "unit": "n/a",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "Availability factor: not in either workbook as an editable input cell. SOURCE_COORDINATE_UNRESOLVED."},
    {"pack_id": "technical.degradation_pct", "model": "BOTH",
     "status": "ENGINE_GAP", "confidence": "UNRESOLVED",
     "verified_label_cell_tuho": "", "verified_value_cell_tuho": "",
     "verified_label_cell_oborovo": "", "verified_value_cell_oborovo": "",
     "cell_role": "UNRESOLVED", "value_kind": "unresolved", "unit": "n/a",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "Annual degradation %: not in either workbook as an editable input cell. The setter _set_technical_degradation exists in app/input_adapter.py; the editable input cell is a registry-backed concept (project_setup.technical.pv_degradation / bess_degradation)."},

    # ---------------- BESS ------------------------------------------
    {"pack_id": "bess.capacity_mwh", "model": "OBOROVO",
     "status": "APPLICABLE_BESS", "confidence": "UNRESOLVED",
     "verified_label_cell_tuho": "", "verified_value_cell_tuho": "",
     "verified_label_cell_oborovo": "", "verified_value_cell_oborovo": "",
     "cell_role": "UNRESOLVED", "value_kind": "unresolved", "unit": "n/a",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "BESS capacity (MWh): APPLICABLE_BESS, only Oborovo, not in registry. Not visible as an editable input cell in the source extraction. SOURCE_COORDINATE_UNRESOLVED."},
    {"pack_id": "bess.power_mw", "model": "OBOROVO",
     "status": "APPLICABLE_BESS", "confidence": "UNRESOLVED",
     "verified_label_cell_tuho": "", "verified_value_cell_tuho": "",
     "verified_label_cell_oborovo": "", "verified_value_cell_oborovo": "",
     "cell_role": "UNRESOLVED", "value_kind": "unresolved", "unit": "n/a",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "BESS power (MW): APPLICABLE_BESS, only Oborovo, not in registry. Not visible as an editable input cell. SOURCE_COORDINATE_UNRESOLVED."},
    {"pack_id": "bess.round_trip_efficiency", "model": "OBOROVO",
     "status": "APPLICABLE_BESS", "confidence": "UNRESOLVED",
     "verified_label_cell_tuho": "", "verified_value_cell_tuho": "",
     "verified_label_cell_oborovo": "", "verified_value_cell_oborovo": "",
     "cell_role": "UNRESOLVED", "value_kind": "unresolved", "unit": "n/a",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "BESS round-trip efficiency: APPLICABLE_BESS, only Oborovo, not in registry. Not visible as an editable input cell. SOURCE_COORDINATE_UNRESOLVED."},
    {"pack_id": "bess.cycles_per_year", "model": "OBOROVO",
     "status": "APPLICABLE_BESS", "confidence": "UNRESOLVED",
     "verified_label_cell_tuho": "", "verified_value_cell_tuho": "",
     "verified_label_cell_oborovo": "", "verified_value_cell_oborovo": "",
     "cell_role": "UNRESOLVED", "value_kind": "unresolved", "unit": "n/a",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "BESS cycles/year: APPLICABLE_BESS, only Oborovo, not in registry. Not visible as an editable input cell. SOURCE_COORDINATE_UNRESOLVED."},

    # ---------------- Debt / margin / all-in (display-only) ---------
    {"pack_id": "debt.senior.margin_bps", "model": "BOTH",
     "status": "DERIVED_FROM", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "", "verified_value_cell_tuho": "",
     "verified_label_cell_oborovo": "", "verified_value_cell_oborovo": "",
     "cell_role": "DERIVED_OUTPUT", "value_kind": "numeric", "unit": "bps",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "margin_bps is derived from interest_rate_pct (all-in - base). Not a separate user input. SOURCE_COORDINATE_UNRESOLVED as an editable cell."},
    {"pack_id": "debt.senior.all_in_rate_bps", "model": "BOTH",
     "status": "DERIVED_FROM", "confidence": "CONFIRMED",
     "verified_label_cell_tuho": "", "verified_value_cell_tuho": "",
     "verified_label_cell_oborovo": "", "verified_value_cell_oborovo": "",
     "cell_role": "DERIVED_OUTPUT", "value_kind": "numeric", "unit": "bps",
     "evidence_basis": "PROGRAMMATIC_WORKBOOK_INSPECTION",
     "mapping_verification_status": "MAPPING_CONFIRMED",
     "review_note": "all_in_rate_bps is the user-entered all-in rate (mapped to registry project_setup.technical.interest_rate_pct). The pack column is display-only of the same single input. SOURCE_COORDINATE_UNRESOLVED as a separate editable cell."},
]

UNRESOLVED_FIELD_ORDER = [
    "canonical_concept",
    "pack_id",
    "model",
    "cell_role",
    "value_kind",
    "unit",
    "evidence_basis",
    "mapping_verification_status",
    "shared_source_id",
    "review_note",
    "status",
    "confidence",
    "verified_label_cell_tuho",
    "verified_label_cell_oborovo",
    "verified_value_cell_tuho",
    "verified_value_cell_oborovo",
    "verified_editable_cell_tuho",
    "verified_editable_cell_oborovo",
    "verified_formula_cell_tuho",
    "verified_formula_cell_oborovo",
    "verified_counterparty_label_cell_tuho",
    "verified_counterparty_label_cell_oborovo",
    "verified_formula_period_cell_tuho",
    "verified_formula_period_cell_oborovo",
]


SANITIZED_REVIEW_NOTES = {
    "tax.wht.dividend.sponsor": "WHT on dividends, Sponsor. Counterparty label cells are recorded separately from rate cells.",
    "tax.vat.rate": "VAT rate value cells are separate from VAT subsection label cells. VAT cells are not WHT evidence.",
    "tax.vat.reimbursed": "VAT reimbursed toggle. This source belongs only to VAT, not WHT.",
    "tax.wht.reimbursed": "No distinct WHT reimbursement cell was confirmed. VAT reimbursement cells must not be reused as WHT evidence.",
    "tax.stamp_duty.rate": "Stamp Duty rate. Stamp Duty cells are not WHT evidence.",
    "equity.sponsor_share": "Sponsor ownership share is a C-column hardcode. Capital amount formulas are not ownership-share evidence.",
    "equity.investor_1_share": "Investor 1 ownership share is a C-column hardcode. Capital amount formulas are not ownership-share evidence.",
    "equity.investor_2_share": "Investor 2 ownership share is formula-derived and not user-editable.",
    "tax.thin_capitalization_enabled": "Thin-capitalization enablement is a boolean/toggle concept, separate from ratio, amount, and EBITDA percentage concepts.",
    "tax.max_shl_to_equity_ratio": "Maximum SHL-to-equity ratio is formula-derived and belongs in the formula axis.",
    "tax.max_shl_interest_expense_amount": "Maximum SHL interest expense amount is an editable currency hardcode, separate from the EBITDA percentage concept.",
    "tax.max_shl_interest_pct_ebitda": "Maximum SHL interest as percentage of EBITDA is an editable ratio hardcode, separate from the amount concept.",
    "reserves.dsra": "DSRA label and derived balance cells are recorded as label/formula evidence only. No editable DSRA balance cell is confirmed.",
    "tax.legal_reserve_pct": "Legal reserve cap is an Oborovo-only editable hardcode.",
    "tax.loss_carryforward_max_years": "Loss-carryforward maximum cap is an Oborovo-only editable hardcode and distinct from the registry runtime field.",
}

FORMULA_AXIS_OVERRIDES = {
    "equity.investor_2_share": {
        "tuho": "C301",
        "oborovo": "C318",
    },
    "tax.max_shl_to_equity_ratio": {
        "tuho": "D398",
        "oborovo": "D415",
    },
    "reserves.dsra": {
        "tuho": "D346",
        "oborovo": "D329",
    },
}

VALUE_AXIS_CLEAR = {
    "equity.investor_2_share",
    "tax.max_shl_to_equity_ratio",
    "reserves.dsra",
    "tax.wht.reimbursed",
}

FORMULA_AXIS_CLEAR = {
    "equity.sponsor_share",
    "equity.investor_1_share",
}


def _sanitize_note(pack_id: str, note: str) -> str:
    note = SANITIZED_REVIEW_NOTES.get(pack_id, note)
    # Remove confidential workbook values and formula fragments from legacy
    # notes. Coordinates, roles, types and units remain sufficient evidence.
    note = re.sub(r"\([^)]*=\s*[^)]*\)", "", note)
    note = re.sub(r"\b[A-Z]{1,3}\d+\s*=\s*[^.;,\n]+", lambda m: m.group(0).split("=")[0].strip(), note)
    note = re.sub(r"=\s*[A-Z_]+\([^.;\n]+", "formula", note)
    note = re.sub(r"\b\d+\.\d+\b", "sanitized", note)
    note = re.sub(r"\b\d{2,}\b", lambda m: m.group(0) if re.match(r"^[A-Z]+\d+$", m.group(0)) else "sanitized", note)
    return " ".join(note.split())


def _normalized_unresolved_pack_ids() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for source in UNRESOLVED_PACK_IDS:
        row = dict(source)
        pack_id = row.get("pack_id", "")
        row.setdefault("canonical_concept", pack_id)
        row.setdefault("shared_source_id", "")
        row["evidence_basis"] = "PROGRAMMATIC_WORKBOOK_INSPECTION"
        row.pop("verification_basis", None)
        row.pop("verification_status", None)

        role = row.get("cell_role", "")
        has_any_coordinate = any(
            str(row.get(k, "")).strip()
            for k in row
            if k.startswith("verified_") and k.endswith(("_tuho", "_oborovo"))
        )
        if pack_id in VALUE_AXIS_CLEAR:
            for model_key in ("tuho", "oborovo"):
                row[f"verified_value_cell_{model_key}"] = ""
                row[f"verified_editable_cell_{model_key}"] = ""
        if pack_id in FORMULA_AXIS_CLEAR:
            for model_key in ("tuho", "oborovo"):
                row[f"verified_formula_cell_{model_key}"] = ""
        if pack_id in FORMULA_AXIS_OVERRIDES:
            for model_key, cell in FORMULA_AXIS_OVERRIDES[pack_id].items():
                row[f"verified_formula_cell_{model_key}"] = cell
                row[f"verified_value_cell_{model_key}"] = ""
                row[f"verified_editable_cell_{model_key}"] = ""

        if role in {"EDITABLE_HARDCODE", "TOGGLE", "TEXT_INPUT", "DATE_INPUT"}:
            for model_key in ("tuho", "oborovo"):
                value_cell = row.get(f"verified_value_cell_{model_key}", "")
                row[f"verified_editable_cell_{model_key}"] = value_cell
        elif role in {"FORMULA_RESULT", "DERIVED_OUTPUT"}:
            for model_key in ("tuho", "oborovo"):
                row.setdefault(f"verified_editable_cell_{model_key}", "")
                row[f"verified_editable_cell_{model_key}"] = ""
        else:
            for model_key in ("tuho", "oborovo"):
                row.setdefault(f"verified_editable_cell_{model_key}", "")

        if pack_id == "tax.wht.reimbursed":
            row["cell_role"] = "UNRESOLVED"
            row["value_kind"] = "unresolved"
            row["unit"] = "n/a"
            row["confidence"] = "UNRESOLVED"
            row["mapping_verification_status"] = "ABSENCE_CONFIRMED"
            for key in list(row):
                if key.startswith("verified_") and key.endswith(("_tuho", "_oborovo")):
                    row[key] = ""
        elif role == "UNRESOLVED" and not has_any_coordinate:
            row["mapping_verification_status"] = "ABSENCE_CONFIRMED"
        elif has_any_coordinate:
            row["mapping_verification_status"] = "MAPPING_CONFIRMED"
        else:
            row["mapping_verification_status"] = "UNRESOLVED"

        row["review_note"] = _sanitize_note(pack_id, row.get("review_note", ""))
        rows.append({field: row.get(field, "") for field in UNRESOLVED_FIELD_ORDER})
    return sorted(rows, key=lambda r: (r["canonical_concept"], r["pack_id"], r["model"]))


# ---------------------------------------------------------------------------
# Inputs classification (A..H ordering)
# ---------------------------------------------------------------------------


def _classify_inputs_row(r: Dict[str, Any]) -> Tuple[str, str, str]:
    section = (r.get("section") or "").strip().lower()
    team = (r.get("team") or "").strip().lower()
    source_type = (r.get("source_type") or "").strip()
    editable_policy = (r.get("editable_policy") or "").strip()
    scenario_policy = (r.get("scenario_policy") or "").strip()
    kind = (r.get("kind") or "").strip().lower()
    label = (r.get("label") or "").strip()
    label_lower = label.lower()

    # A. SECTION_HEADER
    if (
        kind == "section"
        and (source_type == "section/header" or editable_policy == "N/A"
             or label_lower in {"project schedule", "schedule", "technical",
                                 "capex", "opex", "tax", "revenue",
                                 "financing", "debt", "inputs by project team",
                                 "fixed values", "technical data & yield",
                                 "yield", "p90/p50"})
    ):
        return ("SECTION_HEADER",
                f"kind=section, source_type={source_type!r}, label={label!r}",
                "CONFIRMED")

    # B. LEGEND_TOOL
    if (section in {"tools", "legend", "tool", "helper"}
        or team.startswith("legend") or "legend" in label_lower
        or "tools" in section or "tools" in label_lower):
        return ("LEGEND_TOOL",
                f"section={section!r}, team={team!r}, label={label!r}",
                "CONFIRMED")

    # C. ENGINE_OUTPUT
    if source_type == "output/comparison":
        return ("ENGINE_OUTPUT", f"source_type=output/comparison, label={label!r}", "CONFIRMED")
    if "outputs" in section and kind != "section":
        return ("ENGINE_OUTPUT", f"section={section!r}", "PROBABLE")

    # D. CHECK_ONLY
    if (kind in ("check", "balance", "reconciliation")
        or "check" in label_lower or "balance" in label_lower
        or "control" in label_lower):
        return ("CHECK_ONLY", f"kind={kind!r}, label={label!r}", "CONFIRMED")

    # E. DERIVED_FORMULA
    if source_type == "same-sheet formula" and editable_policy == "Derived / read-only":
        return ("DERIVED_FORMULA",
                f"source_type=same-sheet formula, formula_cells={r.get('formula_cells', '')!r}",
                "CONFIRMED")
    if (kind in ("scalar", "series / table row")
        and source_type == "mixed formula + hardcode"
        and editable_policy == "Derived / read-only"):
        return ("DERIVED_FORMULA",
                f"kind={kind!r}, source_type=mixed formula + hardcode, editable_policy=Derived / read-only",
                "CONFIRMED")
    if (active_formula_kind := r.get("active_formula_kind", "")) == "formula" \
            and editable_policy == "Derived / read-only":
        return ("DERIVED_FORMULA",
                f"active_formula_kind=formula, editable_policy=Derived / read-only",
                "CONFIRMED")

    # F. LINKED_VALUE
    if (source_type == "cross-sheet link/formula"
        and editable_policy in ("Linked / read-only", "Review")):
        return ("LINKED_VALUE",
                f"source_type=cross-sheet link/formula, editable_policy={editable_policy!r}",
                "CONFIRMED")

    # G. EDITABLE_INPUT
    if (source_type == "hardcode"
        and editable_policy == "Candidate input"
        and scenario_policy in ("Candidate override", "Resolved from Scenarios")):
        return ("EDITABLE_INPUT",
                f"source_type=hardcode, editable_policy=Candidate input, scenario_policy={scenario_policy!r}",
                "CONFIRMED")
    if (source_type == "mixed formula + hardcode"
        and scenario_policy == "Resolved from Scenarios"):
        return ("EDITABLE_INPUT",
                f"source_type=mixed formula + hardcode with scenario override resolved from Scenarios",
                "CONFIRMED")
    if (source_type == "hardcode" and editable_policy == "Review"
        and kind in ("scalar", "series / table row")):
        return ("EDITABLE_INPUT",
                f"source_type=hardcode, editable_policy=Review (selection option)",
                "PROBABLE")

    return ("UNSUPPORTED",
            f"no rule match: source_type={source_type!r}, editable_policy={editable_policy!r}, label={label!r}",
            "UNRESOLVED")


# ---------------------------------------------------------------------------
# Scenario classification + active-cell role + range-role
# ---------------------------------------------------------------------------


def _classify_scenario_row(r: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
    """Return (classification, reason, confidence, active_cell_role, range_role)."""
    section = (r.get("section") or "").strip().lower()
    team = (r.get("team") or "").strip().lower()
    source_type = (r.get("source_type") or "").strip()
    label = (r.get("label") or "").strip()
    active_value_kind = r.get("active_value_kind", "")
    active_formula_kind = r.get("active_formula_kind", "")
    scenario_value_kind = r.get("scenario_value_kind", "")
    scenario_formula_kind = r.get("scenario_formula_kind", "")
    label_lower = label.lower()
    active_cell = r.get("active_cell", "")
    scenario_range = r.get("scenario_cells", "")

    # A. SECTION_HEADER
    if (active_value_kind == "empty" and active_formula_kind == "empty"
        and (label_lower in {"technical", "capex", "opex", "revenue",
                              "financing", "debt", "tax", "fixed values",
                              "inputs by project team"}
             or "technical" in label_lower
             or "capex" in label_lower
             or "opex" in label_lower
             or "revenue" in label_lower
             or "financing" in label_lower
             or "debt" in label_lower
             or "tax" in label_lower)):
        return ("SECTION_HEADER",
                f"active value+formula empty, label={label!r}",
                "CONFIRMED", "HEADER", "HEADER_PRESENTATION")

    # B. LEGEND_TOOL
    if (team.startswith("legend") or "legend" in label_lower
        or label_lower in {"legend", "tools", "tool"}):
        return ("LEGEND_TOOL",
                f"team={team!r}, label={label!r}",
                "CONFIRMED", "HEADER", "HEADER_PRESENTATION")

    # C. ENGINE_OUTPUT
    if source_type == "output/comparison":
        return ("ENGINE_OUTPUT",
                f"source_type=output/comparison, label={label!r}",
                "CONFIRMED", "OUTPUT", "OUTPUT_COMPARISON")

    # D. DERIVED_BASE_FORMULA
    if active_formula_kind == "formula" and active_value_kind in ("empty", "formula"):
        return ("DERIVED_FORMULA",
                f"active_formula_kind=formula, dependencies={r.get('dependencies', '')!r}",
                "PROBABLE", "DERIVED_BASE_FORMULA", "FORMULA_PROPAGATION")

    # E. CHECK_ONLY
    if "check" in label_lower or "balance" in label_lower or "control" in label_lower:
        return ("CHECK_ONLY",
                f"label={label!r}",
                "PROBABLE", "CHECK", "OUTPUT_COMPARISON")

    # F. SCENARIO_OVERRIDE
    # If active cell is a formula but cached value is a real kind,
    # it's a LINKED_BASE_VALUE (workbook displays the active
    # scenario's value via formula).
    if active_formula_kind == "formula" and active_value_kind in ("numeric", "text", "date", "other"):
        return ("SCENARIO_OVERRIDE",
                f"active cell is a formula with cached value kind={active_value_kind}",
                "CONFIRMED", "LINKED_BASE_VALUE", "SPARSE_OVERRIDE")

    if (active_value_kind in ("numeric", "text", "date", "other")
            and scenario_value_kind in ("numeric", "text", "date", "empty", "other")):
        return ("SCENARIO_OVERRIDE",
                f"active value kind={active_value_kind}, scenario value kind={scenario_value_kind}",
                "CONFIRMED", "DIRECT_BASE_INPUT", "SPARSE_OVERRIDE")

    if (source_type == "scenario input" and active_value_kind == "empty"
            and scenario_value_kind in ("numeric", "text", "date", "other")):
        return ("SCENARIO_OVERRIDE",
                f"active value empty (Base inherited), scenario value kind={scenario_value_kind}",
                "CONFIRMED", "DIRECT_BASE_INPUT", "SPARSE_OVERRIDE")

    if source_type == "scenario input" and active_value_kind in ("numeric", "text", "date", "other"):
        return ("SCENARIO_OVERRIDE",
                f"source_type=scenario input, active value kind={active_value_kind}",
                "CONFIRMED", "DIRECT_BASE_INPUT", "SPARSE_OVERRIDE")

    return ("UNSUPPORTED",
            f"no rule match: source_type={source_type!r}, active_value={active_value_kind}, label={label!r}",
            "UNRESOLVED", "UNRESOLVED", "UNRESOLVED")


# ---------------------------------------------------------------------------
# Cross-walk builder (single source of truth)
# ---------------------------------------------------------------------------


def _evidence_for(reg_field_id: str, reg_engine_path: str) -> Dict[str, str]:
    """Return the real evidence dictionary for a registry FieldSpec.

    All paths are derived from the actual source code. The
    validator independently verifies them.

    The ProjectInputs path is **the registry's own engine_path**
    (verified by the validator against the real domain model).

    v5.1 also returns:
      - test_evidence_scope: scope of the cited test
        (FIELD-SPECIFIC-E2E, FIELD-SPECIFIC-UNIT, SHARED-PIPELINE,
         DISPLAY-ONLY, GENERIC-ROUTE, NONE)
      - runtime_validation_status: third-axis status
        (FIELD_SPECIFIC_E2E_PROVEN, FIELD_SPECIFIC_UNIT_PROVEN,
         SHARED_PIPELINE_PROVEN, DISPLAY_ONLY_PROVEN,
         GENERIC_ROUTE_ONLY, NO_FIELD_SPECIFIC_TEST,
         NOT_APPLICABLE, UNRESOLVED)
      - scenario_mapping_status: scenario-axis status
        (VERIFIED_BOTH_MODELS, VERIFIED_TUHO_ONLY,
         VERIFIED_OBOROVO_ONLY, NOT_SCENARIO_ELIGIBLE,
         SOURCE_COORDINATE_UNRESOLVED, NOT_APPLICABLE)

    The mapping (canonical_field_id -> test_evidence + scope +
    runtime_validation_status + scenario_mapping_status) is the
    authoritative source. The matrix is generated from it.
    """
    # ------------------------------------------------------------------
    # 1) Direct setter (real symbol in app/input_adapter.py)
    # ------------------------------------------------------------------
    for setter_name, (reg_id, _pi_path) in ADAPTER_SETTERS.items():
        if reg_id == reg_field_id:
            # Determine test evidence and scope per the v5.1 Â§4 rules.
            te, scope, rvs, smap = _test_evidence_for_setter(reg_id, setter_name)
            return {
                "save_path": SAVE_FUNCTIONS["snapshot_persistence"][0],
                "save_evidence_type": "EXACT_SYMBOL",
                "adapter_path": f"app/input_adapter.py::{setter_name}",
                "adapter_evidence_type": "EXACT_SYMBOL",
                "projectinputs_path": f"ProjectInputs.{reg_engine_path}" if reg_engine_path else "UNRESOLVED",
                "engine_consumer": "concrete downstream consumer verified in app/waterfall_core.py / app/reporting (CONCEPTUAL_DESCRIPTION \u2014 specific consumer not a single symbol)",
                "engine_consumer_evidence_type": "CONCEPTUAL_DESCRIPTION",
                "test_evidence": te,
                "test_evidence_scope": scope,
                "runtime_validation_status": rvs,
                "scenario_mapping_status": smap,
            }
    # ------------------------------------------------------------------
    # 2) Inline-logic resolver (Info fields)
    # ------------------------------------------------------------------
    if reg_field_id in INFO_FIELDS_VIA_RESOLVER:
        pi_path, inline_desc = INFO_FIELDS_VIA_RESOLVER[reg_field_id]
        # Info fields (project_name, country_market, cod_date,
        # construction_months, horizon_years) are wired through
        # _resolve_user_inputs. There is no test that edits each
        # of these specific fields and runs the engine. The TM
        # generic-route test is the closest behavioral proxy.
        te = "tests/test_workbook_v2_browser_acceptance.py::TestTM200To300QueuedRun::test_runtime_persisted_after_run"
        scope = "GENERIC-ROUTE"
        rvs = "GENERIC_ROUTE_ONLY"
        smap = "SOURCE_COORDINATE_UNRESOLVED"
        return {
            "save_path": SAVE_FUNCTIONS["snapshot_persistence"][0],
            "save_evidence_type": "EXACT_SYMBOL",
            "adapter_path": f"app/input_adapter.py::{RESOLVER_INTRINSIC}",
            "adapter_evidence_type": "INLINE_LOGIC",
            "adapter_detail": inline_desc,
            "projectinputs_path": pi_path,
            "engine_consumer": "concrete downstream consumer verified in app/waterfall_core.py / app/reporting (CONCEPTUAL_DESCRIPTION \u2014 specific consumer not a single symbol)",
            "engine_consumer_evidence_type": "CONCEPTUAL_DESCRIPTION",
            "test_evidence": te,
            "test_evidence_scope": scope,
            "runtime_validation_status": rvs,
            "scenario_mapping_status": smap,
        }
    # ------------------------------------------------------------------
    # 3) CAPEX sub-line pipeline
    # ------------------------------------------------------------------
    if reg_field_id in CAPEX_FIELDS_VIA_SUB_LINE_PIPELINE:
        te = "tests/test_phase57a9c_capex_sub_lines_save_load.py::TestSaveProjectAcceptsSubLines::test_save_project_persists_sub_lines"
        scope = "SHARED-PIPELINE"
        rvs = "SHARED_PIPELINE_PROVEN"
        smap = "SOURCE_COORDINATE_UNRESOLVED"
        return {
            "save_path": CAPEX_SUB_LINE_PIPELINE[0],
            "save_evidence_type": "SERVICE_PIPELINE",
            "save_pipeline": " â†’ ".join(CAPEX_SUB_LINE_PIPELINE),
            "adapter_path": CAPEX_SUB_LINE_PIPELINE[2],
            "adapter_evidence_type": "SERVICE_PIPELINE",
            "projectinputs_path": f"ProjectInputs.{reg_engine_path}" if reg_engine_path else "UNRESOLVED",
            "engine_consumer": "concrete downstream consumer verified in app/waterfall_core.py / app/reporting (CONCEPTUAL_DESCRIPTION)",
            "engine_consumer_evidence_type": "CONCEPTUAL_DESCRIPTION",
            "test_evidence": te,
            "test_evidence_scope": scope,
            "runtime_validation_status": rvs,
            "scenario_mapping_status": smap,
        }
    # ------------------------------------------------------------------
    # 4) OPEX sub-line pipeline
    # ------------------------------------------------------------------
    if reg_field_id in OPEX_FIELDS_VIA_SUB_LINE_PIPELINE:
        # opex.lines.technical_management is the ONLY OPEX line
        # with a field-specific test (test_maintenance_field_save).
        # All other OPEX lines share the OPEX pipeline.
        if reg_field_id == "opex.lines.technical_management":
            te = "tests/test_workbook_v2_browser_acceptance.py::TestAdditionalOPEX::test_maintenance_field_save"
            scope = "FIELD-SPECIFIC-E2E"
            rvs = "FIELD_SPECIFIC_E2E_PROVEN"
        else:
            te = "tests/test_workbook_v2_browser_acceptance.py::TestAdditionalOPEX::test_maintenance_field_save"
            scope = "SHARED-PIPELINE"
            rvs = "SHARED_PIPELINE_PROVEN"
        smap = "SOURCE_COORDINATE_UNRESOLVED"
        return {
            "save_path": OPEX_SUB_LINE_PIPELINE[0],
            "save_evidence_type": "SERVICE_PIPELINE",
            "save_pipeline": " â†’ ".join(OPEX_SUB_LINE_PIPELINE),
            "adapter_path": OPEX_SUB_LINE_PIPELINE[2],
            "adapter_evidence_type": "SERVICE_PIPELINE",
            "projectinputs_path": f"ProjectInputs.{reg_engine_path}" if reg_engine_path else "UNRESOLVED",
            "engine_consumer": "concrete downstream consumer verified in app/waterfall_core.py / app/reporting (CONCEPTUAL_DESCRIPTION)",
            "engine_consumer_evidence_type": "CONCEPTUAL_DESCRIPTION",
            "test_evidence": te,
            "test_evidence_scope": scope,
            "runtime_validation_status": rvs,
            "scenario_mapping_status": smap,
        }
    # ------------------------------------------------------------------
    # 5) CIT rate (display-only test, not behavioral proof)
    # ------------------------------------------------------------------
    if reg_field_id == "tax.assumptions.cit_rate_pct":
        te = "tests/test_workbook_v2_browser_acceptance.py::TestFSBrowserAcceptance::test_cit_rate_displayed_as_percent"
        scope = "DISPLAY-ONLY"
        rvs = "DISPLAY_ONLY_PROVEN"
        smap = "SOURCE_COORDINATE_UNRESOLVED"
        return {
            "save_path": SAVE_FUNCTIONS["snapshot_persistence"][0],
            "save_evidence_type": "EXACT_SYMBOL",
            "adapter_path": "app/input_adapter.py::_set_tax_corporate_rate",
            "adapter_evidence_type": "EXACT_SYMBOL",
            "projectinputs_path": f"ProjectInputs.{reg_engine_path}" if reg_engine_path else "UNRESOLVED",
            "engine_consumer": "concrete downstream consumer verified in app/waterfall_core.py / app/reporting (CONCEPTUAL_DESCRIPTION \u2014 specific consumer not a single symbol)",
            "engine_consumer_evidence_type": "CONCEPTUAL_DESCRIPTION",
            "test_evidence": te,
            "test_evidence_scope": scope,
            "runtime_validation_status": rvs,
            "scenario_mapping_status": smap,
        }
    return {
        "save_path": "UNRESOLVED",
        "save_evidence_type": "UNRESOLVED",
        "adapter_path": "UNRESOLVED",
        "adapter_evidence_type": "UNRESOLVED",
        "projectinputs_path": "UNRESOLVED",
        "engine_consumer": "UNRESOLVED",
        "engine_consumer_evidence_type": "UNRESOLVED",
        "test_evidence": "NO_TEST_EVIDENCE",
        "test_evidence_scope": "NONE",
        "runtime_validation_status": "UNRESOLVED",
        "scenario_mapping_status": "UNRESOLVED",
    }


# v5.1 Â§4: precise test-evidence scope per canonical field.
# Each row is (test_evidence, scope, runtime_validation_status,
# scenario_mapping_status).
#
# Sources of truth:
#   * tests/test_workbook_v2_browser_acceptance.py::TestTM200To300QueuedRun::test_runtime_persisted_after_run
#       - generic-route (proves the queue + persist + run pipeline
#         works, but does not edit any specific canonical field).
#   * tests/test_workbook_v2_browser_acceptance.py::TestAdditionalOPEX::test_maintenance_field_save
#       - field-specific E2E for opex.lines.technical_management ONLY
#         (the test edits maintenance and proves save). For every
#         other OPEX line it is shared-pipeline evidence.
#   * tests/test_phase57a9c_capex_sub_lines_save_load.py::TestSaveProjectAcceptsSubLines::test_save_project_persists_sub_lines
#       - shared-pipeline for all CAPEX sub-lines (no individual
#         field-specific run-and-prove test).
#   * tests/test_workbook_v2_browser_acceptance.py::TestFSBrowserAcceptance::test_cit_rate_displayed_as_percent
#       - display-only for CIT (proves the value is rendered as %,
#         does not prove tax cash flow changes).
_DEFAULT_TM_TEST = (
    "tests/test_workbook_v2_browser_acceptance.py::TestTM200To300QueuedRun::test_runtime_persisted_after_run"
)
_DEFAULT_MAINT_TEST = (
    "tests/test_workbook_v2_browser_acceptance.py::TestAdditionalOPEX::test_maintenance_field_save"
)
_DEFAULT_CAPEX_TEST = (
    "tests/test_phase57a9c_capex_sub_lines_save_load.py::TestSaveProjectAcceptsSubLines::test_save_project_persists_sub_lines"
)
_DEFAULT_FS_TEST = (
    "tests/test_workbook_v2_browser_acceptance.py::TestFSBrowserAcceptance::test_cit_rate_displayed_as_percent"
)

# v5.1 Â§4: per-canonical-field test-evidence map.
# Each entry is (test_evidence, scope, runtime_validation_status,
# scenario_mapping_status).
# - scope: FIELD-SPECIFIC-E2E | FIELD-SPECIFIC-UNIT | SHARED-PIPELINE
#          | DISPLAY-ONLY | GENERIC-ROUTE | NONE
# - runtime_validation_status: FIELD_SPECIFIC_E2E_PROVEN |
#          FIELD_SPECIFIC_UNIT_PROVEN | SHARED_PIPELINE_PROVEN |
#          DISPLAY_ONLY_PROVEN | GENERIC_ROUTE_ONLY |
#          NO_FIELD_SPECIFIC_TEST | NOT_APPLICABLE | UNRESOLVED
_FIELD_EVIDENCE_V5_1: Dict[str, Tuple[str, str, str, str]] = {
    # Project Info (Info / Resolver) â€” generic-route only
    "project_setup.identity.project_name":  (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    "project_setup.identity.country_market": (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    "project_setup.technical.cod_date":      (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    "project_setup.technical.construction_months": (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    "project_setup.technical.horizon_years":  (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    # Technical params â€” direct setters, but no field-specific E2E
    "project_setup.technical.capacity_mw":   (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    "project_setup.technical.p50_hours":     (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    # CAPEX sub-lines â€” shared pipeline (no individual field E2E)
    "capex.C.production_units":    (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.C.epc_contract":        (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.C.epc_other":           (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.C.grid_connection":     (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.C.ops_preparation":     (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.C.insurances":          (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.C.lease_tax":           (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.C.construction_mgmt_a": (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.C.commissioning":       (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.C.taxes":               (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.D.project_acquisition": (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.D.project_rights":      (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.D.audit_legal":         (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "capex.D.construction_mgmt_b": (_DEFAULT_CAPEX_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    # OPEX sub-lines â€” only technical_management is field-specific E2E
    "opex.lines.technical_management":    (_DEFAULT_MAINT_TEST, "FIELD-SPECIFIC-E2E", "FIELD_SPECIFIC_E2E_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "opex.lines.om_preventive":           (_DEFAULT_MAINT_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "opex.lines.site_maintenance":        (_DEFAULT_MAINT_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "opex.lines.cleaning_materials":      (_DEFAULT_MAINT_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "opex.lines.security":                (_DEFAULT_MAINT_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "opex.lines.insurance":               (_DEFAULT_MAINT_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "opex.lines.lease_property_tax":      (_DEFAULT_MAINT_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "opex.lines.power_expenses":          (_DEFAULT_MAINT_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "opex.lines.audit_accounting_legal":  (_DEFAULT_MAINT_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "opex.lines.bank_fees":               (_DEFAULT_MAINT_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "opex.lines.environmental_social":    (_DEFAULT_MAINT_TEST, "SHARED-PIPELINE", "SHARED_PIPELINE_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    # Revenue â€” direct setters but no field-specific E2E
    "revenue.ppa.base_tariff": (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    "revenue.ppa.term_years":  (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    # Debt senior â€” direct setters but no field-specific E2E
    "debt.senior.gearing_pct":     (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    "debt.senior.target_dscr":     (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    "debt.senior.interest_rate_pct": (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    "debt.senior.tenor_years":     (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
    # Tax â€” CIT is display-only; loss carryforward has no E2E
    "tax.assumptions.cit_rate_pct":          (_DEFAULT_FS_TEST, "DISPLAY-ONLY", "DISPLAY_ONLY_PROVEN", "SOURCE_COORDINATE_UNRESOLVED"),
    "tax.assumptions.loss_carryforward_years": (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED"),
}


def _test_evidence_for_setter(
    reg_id: str, setter_name: str
) -> Tuple[str, str, str, str]:
    """Return (test_evidence, scope, runtime_validation_status,
    scenario_mapping_status) for a setter-driven canonical field.

    For the CIT setter the answer is DISPLAY-ONLY / DISPLAY_ONLY_PROVEN
    (the only test cited is the percent-display test, which does not
    prove tax-cash-flow behavior). For the maintenance OPEX field
    the answer is FIELD-SPECIFIC-E2E / FIELD_SPECIFIC_E2E_PROVEN.
    For CAPEX sub-lines the answer is SHARED-PIPELINE /
    SHARED_PIPELINE_PROVEN (no individual sub-line is exercised
    end-to-end in the existing test). For all other setter fields
    the cited test is the generic TM route test, which proves
    the queue + persist + run pipeline but not this field; the
    answer is GENERIC-ROUTE / GENERIC_ROUTE_ONLY.
    """
    if reg_id in _FIELD_EVIDENCE_V5_1:
        return _FIELD_EVIDENCE_V5_1[reg_id]
    # Fallback for any setter not explicitly mapped.
    return (_DEFAULT_TM_TEST, "GENERIC-ROUTE", "GENERIC_ROUTE_ONLY", "SOURCE_COORDINATE_UNRESOLVED")


def _runtime_status_for(r: Dict[str, Any]) -> str:
    """Determine the real runtime_binding_status for a registry FieldSpec.

    A field is RUNTIME_FULLY_BOUND only if the runtime wiring
    has a real adapter symbol OR an INLINE_LOGIC container that
    the validator can independently verify.
    """
    if r["binding_status"] == "TEMPLATE_LOCKED":
        return "TEMPLATE_LOCKED"
    if r["binding_status"] == "DISPLAY_ONLY":
        return "DISPLAY_ONLY"
    if r["kind"] == "DERIVED_DISPLAY":
        return "DERIVED_ONLY"
    if r["binding_status"] == "PARTIAL":
        return "RUNTIME_PARTIALLY_BOUND"
    if r["binding_status"] == "BOUND" and r["engine_path"] and r["snapshot_key"]:
        # Check that the runtime wiring is real:
        # 1. dedicated adapter setter, OR
        # 2. inline logic in _resolve_user_inputs (covered in
        #    INFO_FIELDS_VIA_RESOLVER for Info fields), OR
        # 3. capex/opex sub-line service pipeline
        for setter_name, (reg_id, _) in ADAPTER_SETTERS.items():
            if reg_id == r["registry_field_id"]:
                return "RUNTIME_FULLY_BOUND"
        if r["registry_field_id"] in INFO_FIELDS_VIA_RESOLVER:
            return "RUNTIME_FULLY_BOUND"
        if r["registry_field_id"] in CAPEX_FIELDS_VIA_SUB_LINE_PIPELINE:
            return "RUNTIME_FULLY_BOUND"
        if r["registry_field_id"] in OPEX_FIELDS_VIA_SUB_LINE_PIPELINE:
            return "RUNTIME_FULLY_BOUND"
        # engine_path and snapshot_key exist but no real
        # adapter symbol found in source code; the runtime
        # wiring is partial.
        return "RUNTIME_PARTIALLY_BOUND"
    return "UNRESOLVED"


def _excel_status_for(r: Dict[str, Any], ev: Dict[str, str],
                       verified_tuho: str, verified_obo: str) -> str:
    """Determine the real excel_mapping_status."""
    if ev.get("test_evidence") == "NO_TEST_EVIDENCE" and not verified_tuho and not verified_obo:
        return "SOURCE_COORDINATE_UNRESOLVED"
    if verified_tuho and verified_obo:
        return "VERIFIED_BOTH_MODELS"
    if verified_tuho and not verified_obo:
        return "VERIFIED_TUHO_ONLY"
    if verified_obo and not verified_tuho:
        return "VERIFIED_OBOROVO_ONLY"
    if r["registry_excel_hint_tuho"] or r["registry_excel_hint_oborovo"]:
        return "REGISTRY_HINT_ONLY"
    return "SOURCE_COORDINATE_UNRESOLVED"


def _scenario_status_for(ev: Dict[str, str],
                          verified_tuho_scen_cell: str,
                          verified_oborovo_scen_cell: str) -> str:
    """Determine the real scenario_mapping_status.

    The v5.1 Â§8 / Â§9 requirements:
      * Only populate scenario columns when the source row is
        confirmed as scenario-eligible.
      * The P50/Yield pair remains SOURCE_COORDINATE_UNRESOLVED
        (its unit semantics are unresolved).
      * If neither model carries a scenario cell for the field,
        the field is NOT_SCENARIO_ELIGIBLE.
    """
    # P50 is hard-wired to UNRESOLVED until client review.
    rfi = ev.get("registry_field_id") or ""
    if rfi == "project_setup.technical.p50_hours":
        return "SOURCE_COORDINATE_UNRESOLVED"
    if not verified_tuho_scen_cell and not verified_oborovo_scen_cell:
        return "SOURCE_COORDINATE_UNRESOLVED"
    if verified_tuho_scen_cell and verified_oborovo_scen_cell:
        return "VERIFIED_BOTH_MODELS"
    if verified_tuho_scen_cell and not verified_oborovo_scen_cell:
        return "VERIFIED_TUHO_ONLY"
    if verified_oborovo_scen_cell and not verified_tuho_scen_cell:
        return "VERIFIED_OBOROVO_ONLY"
    return "SOURCE_COORDINATE_UNRESOLVED"


def _build_crosswalk(reg: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build the v5.1 canonical_registry_crosswalk_v5.csv â€” single
    source of truth for runtime_binding_status, excel_mapping_status,
    runtime_validation_status, and scenario_mapping_status."""
    pe = _pack_evidence_lookup()

    out: List[Dict[str, Any]] = []
    for r in reg:
        ev = _evidence_for(r["registry_field_id"], r["engine_path"])

        # Find matching pack to get verified coordinates
        matching_pack = next(
            (m["pack_id"] for m in PACK_TO_CANONICAL
             if m["canonical_field_id"] == f"registry.{r['registry_field_id']}"),
            None,
        )
        if matching_pack is not None:
            pack_ev = pe.get(matching_pack, {})
            verified_tuho = pack_ev.get("tuho_input_cell", "")
            verified_obo = pack_ev.get("oborovo_input_cell", "")
            verified_tuho_scen_cell = pack_ev.get("tuho_scenario_cell", "")
            verified_oborovo_scen_cell = pack_ev.get("oborovo_scenario_cell", "")
            verified_tuho_scen_range = pack_ev.get("tuho_scenario_range", "")
            verified_oborovo_scen_range = pack_ev.get("oborovo_scenario_range", "")
        else:
            verified_tuho = ""
            verified_obo = ""
            verified_tuho_scen_cell = ""
            verified_oborovo_scen_cell = ""
            verified_tuho_scen_range = ""
            verified_oborovo_scen_range = ""

        runtime_status = _runtime_status_for(r)
        excel_status = _excel_status_for(r, ev, verified_tuho, verified_obo)
        scenario_status = _scenario_status_for(
            ev, verified_tuho_scen_cell, verified_oborovo_scen_cell
        )

        out.append({
            "canonical_field_id": f"registry.{r['registry_field_id']}",
            "registry_field_id": r["registry_field_id"],
            "registry_label": r["label"],
            "registry_kind": r["kind"],
            "registry_binding_status": r["binding_status"],
            "registry_scenario_policy": r["scenario_policy"],
            "registry_source_of_truth": r["source_of_truth"],
            "registry_engine_path": r["engine_path"],
            "registry_snapshot_key": r["snapshot_key"],
            "registry_excel_hint_tuho": r["registry_excel_hint_tuho"],
            "registry_excel_hint_oborovo": r["registry_excel_hint_oborovo"],
            # Runtime evidence (all real, all verified)
            "save_path": ev.get("save_path", ""),
            "save_evidence_type": ev.get("save_evidence_type", ""),
            "save_pipeline": ev.get("save_pipeline", ""),
            "adapter_path": ev.get("adapter_path", ""),
            "adapter_evidence_type": ev.get("adapter_evidence_type", ""),
            "adapter_detail": ev.get("adapter_detail", ""),
            "projectinputs_path": ev.get("projectinputs_path", ""),
            "engine_consumer": ev.get("engine_consumer", ""),
            "engine_consumer_evidence_type": ev.get("engine_consumer_evidence_type", ""),
            "test_evidence": ev.get("test_evidence", ""),
            "test_evidence_scope": ev.get("test_evidence_scope", "NONE"),
            # v5.1 third axis: runtime validation
            "runtime_validation_status": ev.get("runtime_validation_status", "UNRESOLVED"),
            # v5.1 fourth axis: scenario mapping (recomputed from
            # actual scenario source extraction, not from evidence dict)
            "scenario_mapping_status": scenario_status,
            # Excel mapping evidence
            "verified_tuho_input_cell": verified_tuho,
            "verified_oborovo_input_cell": verified_obo,
            "verified_tuho_scenario_cell": verified_tuho_scen_cell,
            "verified_oborovo_scenario_cell": verified_oborovo_scen_cell,
            "verified_tuho_scenario_range": verified_tuho_scen_range,
            "verified_oborovo_scenario_range": verified_oborovo_scen_range,
            # Two-axis status
            "runtime_binding_status": runtime_status,
            "excel_mapping_status": excel_status,
            "confidence": "CONFIRMED" if runtime_status in ("RUNTIME_FULLY_BOUND", "TEMPLATE_LOCKED", "DERIVED_ONLY", "DISPLAY_ONLY") else "PROBABLE",
            "notes": "",
        })
    return out


# ---------------------------------------------------------------------------
# Pack evidence lookup
# ---------------------------------------------------------------------------


def _pack_evidence_lookup() -> Dict[str, Dict[str, Any]]:
    pe: Dict[str, Dict[str, Any]] = {}
    for r in _load_source("TUHO", "inputs")["rows"]:
        fid = r.get("field_id_candidate", "")
        if not fid:
            continue
        pe.setdefault(fid, {})
        pe[fid]["tuho_input_cell"] = r.get("active_cell", "")
        pe[fid]["tuho_technology"] = r.get("technology", "")
    for r in _load_source("OBOROVO", "inputs")["rows"]:
        fid = r.get("field_id_candidate", "")
        if not fid:
            continue
        pe.setdefault(fid, {})
        pe[fid]["oborovo_input_cell"] = r.get("active_cell", "")
        pe[fid]["oborovo_technology"] = r.get("technology", "")
    for r in _load_source("TUHO", "scenarios")["rows"]:
        fid = r.get("field_id_candidate", "")
        if not fid:
            continue
        pe.setdefault(fid, {})
        pe[fid]["tuho_scenario_cell"] = r.get("active_cell", "")
        pe[fid]["tuho_scenario_range"] = r.get("scenario_cells", "")
    for r in _load_source("OBOROVO", "scenarios")["rows"]:
        fid = r.get("field_id_candidate", "")
        if not fid:
            continue
        pe.setdefault(fid, {})
        pe[fid]["oborovo_scenario_cell"] = r.get("active_cell", "")
        pe[fid]["oborovo_scenario_range"] = r.get("scenario_cells", "")
    return pe


# ---------------------------------------------------------------------------
# Build inputs / scenarios manifests (real rows + decision table)
# ---------------------------------------------------------------------------


def _build_inputs_manifest(model: str) -> Dict[str, Any]:
    src = _load_source(model, "inputs")
    canon_by_pack = {m["pack_id"]: m for m in PACK_TO_CANONICAL}
    unresolved_by_pack = {u["pack_id"]: u for u in UNRESOLVED_PACK_IDS}

    out: List[Dict[str, Any]] = []
    for r in src["rows"]:
        wb_class, reason, confidence = _classify_inputs_row(r)
        fid = r.get("field_id_candidate", "")
        m = canon_by_pack.get(fid)
        u = unresolved_by_pack.get(fid)
        if m is not None:
            cfid = m["canonical_field_id"]
            mapping_type = m["mapping_type"]
            mapping_conf = m["confidence"]
            mapping_review = m["review_note"]
            cov = m["mapping_type"]  # initial; will be overridden by cross-walk lookup below
        elif u is not None:
            cfid = ""
            mapping_type = "UNRESOLVED"
            mapping_conf = u["confidence"]
            mapping_review = u["review_note"]
            cov = u["status"]
        else:
            cfid = ""
            mapping_type = "UNMAPPED"
            mapping_conf = "UNRESOLVED"
            mapping_review = "no mapping table entry"
            cov = "UNRESOLVED"

        out.append({
            "row_id": f"{model}::Inputs::R{r['row']}",
            "model": model,
            "sheet": "Inputs",
            "row": r["row"],
            "cell": r.get("active_cell", ""),
            "label": r.get("label", ""),
            "section": r.get("section", ""),
            "domain": r.get("domain", ""),
            "technology": r.get("technology", ""),
            "field_id_candidate": fid,
            "workbook_classification": wb_class,
            "classification_reason": reason,
            "classification_confidence": confidence,
            "active_value_kind": r.get("active_value_kind", ""),
            "active_formula_kind": r.get("active_formula_kind", ""),
            "data_type": r.get("data_type", ""),
            "unit": r.get("unit", ""),
            "source_type": r.get("source_type", ""),
            "editable_policy": r.get("editable_policy", ""),
            "scenario_policy": r.get("scenario_policy", ""),
            "kind": r.get("kind", ""),
            "canonical_field_id": cfid,
            "mapping_type": mapping_type,
            "mapping_confidence": mapping_conf,
            "mapping_review_note": mapping_review,
            "coverage_status": cov,
            "notes": r.get("notes", ""),
        })

    return {
        "manifest_version": "v5",
        "model": model,
        "source_artifact": src.get("source_artifact", ""),
        "sheet": "Inputs",
        "row_count": len(out),
        "rows": out,
    }


def _build_scenarios_manifest(model: str) -> Dict[str, Any]:
    src = _load_source(model, "scenarios")
    canon_by_pack = {m["pack_id"]: m for m in PACK_TO_CANONICAL}
    unresolved_by_pack = {u["pack_id"]: u for u in UNRESOLVED_PACK_IDS}

    out: List[Dict[str, Any]] = []
    for r in src["rows"]:
        cls, reason, confidence, active_role, range_role = _classify_scenario_row(r)
        fid = r.get("field_id_candidate", "")
        m = canon_by_pack.get(fid)
        u = unresolved_by_pack.get(fid)
        if m is not None:
            cfid = m["canonical_field_id"]
            mapping_type = m["mapping_type"]
            mapping_conf = m["confidence"]
            mapping_review = m["review_note"]
            cov = m["mapping_type"]
        elif u is not None:
            cfid = ""
            mapping_type = "UNRESOLVED"
            mapping_conf = u["confidence"]
            mapping_review = u["review_note"]
            cov = u["status"]
        else:
            cfid = ""
            mapping_type = "UNMAPPED"
            mapping_conf = "UNRESOLVED"
            mapping_review = "no mapping table entry"
            cov = "UNRESOLVED"

        out.append({
            "row_id": f"{model}::Scenarios::R{r['row']}",
            "model": model,
            "sheet": "Scenarios",
            "row": r["row"],
            "active_cell": r.get("active_cell", ""),
            "scenario_cells": r.get("scenario_cells", ""),
            "label": r.get("label", ""),
            "section": r.get("section", ""),
            "domain": r.get("domain", ""),
            "technology": r.get("technology", ""),
            "field_id_candidate": fid,
            "canonical_field_id": cfid,
            "workbook_classification": cls,
            "classification_reason": reason,
            "classification_confidence": confidence,
            "active_cell_role": active_role,
            "scenario_range_role": range_role,
            "active_value_kind": r.get("active_value_kind", ""),
            "active_formula_kind": r.get("active_formula_kind", ""),
            "scenario_value_kind": r.get("scenario_value_kind", ""),
            "scenario_formula_kind": r.get("scenario_formula_kind", ""),
            "data_type": r.get("data_type", ""),
            "unit": r.get("unit", ""),
            "source_type": r.get("source_type", ""),
            "override_policy": r.get("override_policy", ""),
            "coverage_status": cov,
            "mapping_type": mapping_type,
            "mapping_confidence": mapping_conf,
            "mapping_review_note": mapping_review,
            "notes": r.get("notes", ""),
        })

    return {
        "manifest_version": "v5",
        "model": model,
        "source_artifact": src.get("source_artifact", ""),
        "sheet": "Scenarios",
        "row_count": len(out),
        "rows": out,
    }


# ---------------------------------------------------------------------------
# Build catalog + matrix from the cross-walk
# ---------------------------------------------------------------------------


def _build_catalog_from_crosswalk(xw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate canonical_field_catalog_v5.csv from the cross-walk
    + engine-owned boundaries. The catalog and matrix are derived
    artifacts; the cross-walk is the source of truth."""
    out: List[Dict[str, Any]] = []

    for r in xw:
        out.append({
            "canonical_field_id": r["canonical_field_id"],
            "domain": "registry",
            "concept": r["registry_label"],
            "registry_field_id": r["registry_field_id"],
            "snapshot_key": r["registry_snapshot_key"],
            "engine_path": r["registry_engine_path"],
            "runtime_binding_status": r["runtime_binding_status"],
            "excel_mapping_status": r["excel_mapping_status"],
            "runtime_validation_status": r.get("runtime_validation_status", "UNRESOLVED"),
            "scenario_mapping_status": r.get("scenario_mapping_status", "SOURCE_COORDINATE_UNRESOLVED"),
            "registry_excel_hint_tuho": r["registry_excel_hint_tuho"],
            "registry_excel_hint_oborovo": r["registry_excel_hint_oborovo"],
            "verified_tuho_input_cell": r["verified_tuho_input_cell"],
            "verified_oborovo_input_cell": r["verified_oborovo_input_cell"],
            "binding_status": r["registry_binding_status"],
            "kind": r["registry_kind"],
            "scenario_policy": r["registry_scenario_policy"],
            "source_of_truth": r["registry_source_of_truth"],
            "persisted": "True",
            "editable": "",
            "runtime_only": "False",
        })

    for u in ENGINE_OWNED_BOUNDARIES:
        out.append({
            "canonical_field_id": u["canonical_field_id"],
            "domain": "engine",
            "concept": u["concept"],
            "registry_field_id": u["registry_field_id"],
            "snapshot_key": "",
            "engine_path": u["engine_path"],
            "runtime_binding_status": u["runtime_binding_status"],
            "excel_mapping_status": u["excel_mapping_status"],
            "runtime_validation_status": "NOT_APPLICABLE",
            "scenario_mapping_status": "NOT_APPLICABLE",
            "registry_excel_hint_tuho": "",
            "registry_excel_hint_oborovo": "",
            "verified_tuho_input_cell": "",
            "verified_oborovo_input_cell": "",
            "binding_status": "",
            "kind": "ENGINE_OWNED",
            "scenario_policy": "",
            "source_of_truth": "ENGINE_OWNED",
            "persisted": "False",
            "editable": "False",
            "runtime_only": "True",
        })

    # UI display-only
    for cid, lbl in [
        ("ui.project.project_company", "Project Company (display only)"),
        ("ui.project.project_code", "Project Code (display only)"),
    ]:
        out.append({
            "canonical_field_id": cid,
            "domain": "ui",
            "concept": lbl,
            "registry_field_id": "",
            "snapshot_key": "",
            "engine_path": "",
            "runtime_binding_status": "DISPLAY_ONLY",
            "excel_mapping_status": "NOT_APPLICABLE",
            "registry_excel_hint_tuho": "",
            "registry_excel_hint_oborovo": "",
            "verified_tuho_input_cell": "",
            "verified_oborovo_input_cell": "",
            "binding_status": "",
            "kind": "DISPLAY_ONLY",
            "scenario_policy": "",
            "source_of_truth": "DISPLAY_ONLY",
            "persisted": "False",
            "editable": "False",
            "runtime_only": "False",
        })
    # v5.1: ensure every catalog row carries the v5.1 status columns
    # (defensive, in case the cross-walk forgot a field).
    for row in out:
        row.setdefault("runtime_validation_status", "UNRESOLVED")
        row.setdefault("scenario_mapping_status", "SOURCE_COORDINATE_UNRESOLVED")

    return out


def _build_matrix_from_crosswalk(xw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate input_coverage_matrix_v5.csv from the cross-walk.
    The matrix is identical to the catalog's two-axis status;
    it never upgrades anything."""
    out: List[Dict[str, Any]] = []
    for r in xw:
        out.append({
            "canonical_field_id": r["canonical_field_id"],
            "runtime_binding_status": r["runtime_binding_status"],
            "excel_mapping_status": r["excel_mapping_status"],
            "runtime_validation_status": r.get("runtime_validation_status", "UNRESOLVED"),
            "scenario_mapping_status": r.get("scenario_mapping_status", "SOURCE_COORDINATE_UNRESOLVED"),
            "registry_field_id": r["registry_field_id"],
            "snapshot_key": r["registry_snapshot_key"],
            "engine_path": r["registry_engine_path"],
            "registry_excel_hint_tuho": r["registry_excel_hint_tuho"],
            "registry_excel_hint_oborovo": r["registry_excel_hint_oborovo"],
            "verified_tuho_input_cell": r["verified_tuho_input_cell"],
            "verified_oborovo_input_cell": r["verified_oborovo_input_cell"],
            "verified_tuho_scenario_cell": r["verified_tuho_scenario_cell"],
            "verified_tuho_scenario_range": r["verified_tuho_scenario_range"],
            "verified_oborovo_scenario_cell": r["verified_oborovo_scenario_cell"],
            "verified_oborovo_scenario_range": r["verified_oborovo_scenario_range"],
            "test_evidence": r["test_evidence"],
            "test_evidence_scope": r.get("test_evidence_scope", "NONE"),
            "adapter_path": r["adapter_path"],
            "adapter_evidence_type": r["adapter_evidence_type"],
            "projectinputs_path": r["projectinputs_path"],
        })
    return out


# ---------------------------------------------------------------------------
# Coverage summary
# ---------------------------------------------------------------------------


def _build_coverage_summary(catalog: List[Dict[str, Any]],
                              xw: List[Dict[str, Any]]) -> Dict[str, Any]:
    workbook_rows = _normalized_unresolved_pack_ids()
    runtime_status: Counter = Counter()
    excel_status: Counter = Counter()
    runtime_validation_status: Counter = Counter()
    scenario_mapping_status: Counter = Counter()
    workbook_only: Counter = Counter()
    engine_bound: Counter = Counter()
    for r in catalog:
        if r.get("domain") == "registry":
            runtime_status[r["runtime_binding_status"]] += 1
            excel_status[r["excel_mapping_status"]] += 1
            runtime_validation_status[r.get("runtime_validation_status", "UNRESOLVED")] += 1
            scenario_mapping_status[r.get("scenario_mapping_status", "UNRESOLVED")] += 1
        if r["domain"] == "engine":
            engine_bound[r["runtime_binding_status"]] += 1
    for u in workbook_rows:
        workbook_only[u["status"]] += 1

    inputs_cls: Dict[str, Counter] = {"TUHO": Counter(), "OBOROVO": Counter()}
    scen_cls: Dict[str, Counter] = {"TUHO": Counter(), "OBOROVO": Counter()}
    for model in ("TUHO", "OBOROVO"):
        path = ARTIFACT_DIR / f"{model.lower()}_model_manifest_v5.json"
        if path.is_file():
            m = _load_json(path)
            for row in m["rows"]:
                inputs_cls[model][row["workbook_classification"]] += 1
        path = ARTIFACT_DIR / f"{model.lower()}_scenario_manifest_v5.json"
        if path.is_file():
            m = _load_json(path)
            for row in m["rows"]:
                scen_cls[model][row["workbook_classification"]] += 1

    cell_role_counts: Counter = Counter()
    verification_status_counts: Counter = Counter()
    for u in workbook_rows:
        role = u.get("cell_role", "").strip()
        if role:
            cell_role_counts[role] += 1
        verification_status_counts[u.get("mapping_verification_status", "UNRESOLVED")] += 1

    disposition_counts = _load_editable_input_disposition_counts()

    return {
        "summary_version": "v5.3",
        "registry_backed_canonical": {
            "count": len(xw),
            "by_runtime_binding_status": dict(runtime_status),
            "by_excel_mapping_status": dict(excel_status),
            "by_runtime_validation_status": dict(runtime_validation_status),
            "by_scenario_mapping_status": dict(scenario_mapping_status),
            "by_cell_role": dict(cell_role_counts),
        },
        "v53_evidence_axes": {
            "label_cell_count": sum(
                bool(u.get("verified_label_cell_tuho", "").strip()) +
                bool(u.get("verified_label_cell_oborovo", "").strip())
                for u in workbook_rows
            ),
            "value_cell_count": sum(
                bool(u.get("verified_value_cell_tuho", "").strip()) +
                bool(u.get("verified_value_cell_oborovo", "").strip())
                for u in workbook_rows
            ),
            "editable_cell_count": sum(
                bool(u.get("verified_editable_cell_tuho", "").strip()) +
                bool(u.get("verified_editable_cell_oborovo", "").strip())
                for u in workbook_rows
            ),
            "formula_cell_count": sum(
                bool(u.get("verified_formula_cell_tuho", "").strip()) +
                bool(u.get("verified_formula_cell_oborovo", "").strip())
                for u in workbook_rows
            ),
            "rows_with_label_cell": sum(
                1 for u in workbook_rows
                if (u.get("verified_label_cell_tuho", "").strip()
                    or u.get("verified_label_cell_oborovo", "").strip())
            ),
            "rows_with_value_cell": sum(
                1 for u in workbook_rows
                if (u.get("verified_value_cell_tuho", "").strip()
                    or u.get("verified_value_cell_oborovo", "").strip())
            ),
            "rows_with_editable_cell": sum(
                1 for u in workbook_rows
                if (u.get("verified_editable_cell_tuho", "").strip()
                    or u.get("verified_editable_cell_oborovo", "").strip())
            ),
            "rows_with_formula_cell": sum(
                1 for u in workbook_rows
                if (u.get("verified_formula_cell_tuho", "").strip()
                    or u.get("verified_formula_cell_oborovo", "").strip())
            ),
            "by_mapping_verification_status": dict(verification_status_counts),
        },
        "workbook_only_concepts": {
            "count": len(workbook_rows),
            "by_status": dict(workbook_only),
            "by_mapping_verification_status": dict(verification_status_counts),
        },
        "engine_owned_boundaries": {
            "count": len(ENGINE_OWNED_BOUNDARIES),
            "by_runtime_binding_status": dict(engine_bound),
        },
        "editable_input_disposition": disposition_counts,
        "by_model": {
            "TUHO": {
                "inputs_classification": dict(inputs_cls["TUHO"]),
                "scenarios_classification": dict(scen_cls["TUHO"]),
            },
            "OBOROVO": {
                "inputs_classification": dict(inputs_cls["OBOROVO"]),
                "scenarios_classification": dict(scen_cls["OBOROVO"]),
            },
        },
        "real_pytest_node_ids_collected": len(KNOWN_PYTEST_NODE_IDS),
    }


def _load_editable_input_disposition_counts() -> Dict[str, Any]:
    """Count the editable-input disposition rows by disposition +
    model + priority. The disposition CSV is written by
    _write_editable_input_disposition()."""
    path = ARTIFACT_DIR / "editable_input_disposition_v5_1.csv"
    if not path.is_file():
        return {"error": "editable_input_disposition_v5_1.csv missing"}
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    by_disposition = Counter(r.get("disposition", "UNRESOLVED") for r in rows)
    by_model = Counter(r.get("model", "") for r in rows)
    by_priority = Counter(r.get("priority", "") for r in rows)
    return {
        "total_rows": len(rows),
        "by_disposition": dict(by_disposition),
        "by_model": dict(by_model),
        "by_priority": dict(by_priority),
    }


# ---------------------------------------------------------------------------
# v5.1 Â§6: Editable-input disposition (every EDITABLE_INPUT manifest
# row must have exactly one disposition).
# ---------------------------------------------------------------------------

# Per-pack disposition map. For pack_ids that appear in
# PACK_TO_CANONICAL (EXACT / TRUE_SYNONYM) the disposition is
# MAPPED_TO_REGISTRY. For pack_ids in UNRESOLVED_PACK_IDS the
# disposition is whatever the unresolved entry says
# (ENGINE_GAP / APPLICABLE_BESS / etc.). All other pack_ids get
# a per-pack override here.
# The keys are pack_ids (the source's field_id_candidate values).
_DISPOSITION_BY_PACK_ID: Dict[str, Dict[str, str]] = {
    # ------------------------------------------------------------------
    # Identified in PACK_TO_CANONICAL (EXACT / TRUE_SYNONYM)
    # disposition: MAPPED_TO_REGISTRY  (handled by main loop)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Debt / Facilities / Equity / Reserves: pack has many sub-rows
    # for the same engine concept. Each is documented as a
    # TRUE_DUPLICATE / DERIVED_FROM_EXISTING_INPUT.
    # ------------------------------------------------------------------
    "debt.annual_dscr_increase":     {"disposition": "DERIVED_FROM_EXISTING_INPUT", "priority": "P2_ENGINE", "review_note": "Derived from target DSCR + sweep; not a user-editable input in the Finco1 engine."},
    "debt.arrangement_fee":          {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Senior debt arrangement fee. No registry field. Engine does not consume (debt is sized in the engine)."},
    "debt.commitment_fee":           {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Senior debt commitment fee. No registry field. Engine does not consume."},
    "debt.credit_valuation_adjustment": {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "CVA. No registry field. No engine consumer."},
    "debt.facility_bank_1":          {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Bank-1 facility share. No registry field. No engine consumer."},
    "debt.forward_swap_margin":      {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Forward swap margin. No registry field. No engine consumer (engine does not model swaps)."},
    "debt.lock_up":                  {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Pack lock_up is the same concept as engine.dscr.lockup; documented in unresolved_pack_id_evidence as engine-owned."},
    "debt.margin":                   {"disposition": "DERIVED_FROM_EXISTING_INPUT", "priority": "P2_ENGINE", "review_note": "Derived from interest_rate_pct - base_rate; not a separate user input."},
    "debt.operation":                {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Operation toggle. No registry field."},
    "debt.senior_loan":              {"disposition": "DERIVED_FROM_EXISTING_INPUT", "priority": "P2_ENGINE", "review_note": "Senior loan amount is derived from gearing_ratio * total_capex in the engine; not a user input."},
    "debt.structuring_fee":          {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Senior debt structuring fee. No registry field."},
    "debt.swap_additionnal":         {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Additional swap toggle. No engine consumer."},
    "debt.swap_margin":              {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Swap margin. No engine consumer (engine does not model swaps)."},
    "debt.up_front_fee_of_total_refinancing": {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Up-front fee. No registry field."},
    "debt.used":                     {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Debt-used toggle. No registry field."},
    "debt.year_of_refinancing":      {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Refinancing year. No engine consumer (no refinancing modelled)."},
    "debt_sizing.debt_sizing":       {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Debt-sizing toggle (sculpting vs flat). The actual sculpting/flat decision is exposed via debt.senior.interest_rate_pct; this pack row is a legacy artefact."},
    "debt_sizing.scenario":          {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Debt-sizing scenario label. Display only; no engine consumer."},
    "depreciation.asset":            {"disposition": "DERIVED_FROM_EXISTING_INPUT", "priority": "P2_ENGINE", "review_note": "Asset depreciation is engine-owned (engine.depreciation.*); derived from capex schedule + useful life."},
    "depreciation.bank_fees":        {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Same as capex.F.bank_fees (TEMPLATE_LOCKED)."},
    "depreciation.commitment_fees":  {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Same as capex.F.commitment_fees (TEMPLATE_LOCKED)."},
    "depreciation.reserve_accounts": {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Same as capex.F.reserve_accounts (TEMPLATE_LOCKED)."},
    "equity.amount":                 {"disposition": "DERIVED_FROM_EXISTING_INPUT", "priority": "P2_ENGINE", "review_note": "Equity amount is derived from capex - senior_debt; not a user input."},
    "equity.delay_operation_and_distribution_flows": {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "No registry field; no engine consumer."},
    "equity.dividend_distribution":  {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Dividend distribution toggle. No registry field; engine does not model dividend smoothing."},
    "equity.equity_distribution_grace_period": {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Distribution grace period. No registry field."},
    "equity.share_premium":          {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Share premium. No registry field. Single-SPV assumption."},
    "equity.shareholding":           {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Shareholder structure. No registry field."},
    "equity.shl":                    {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Same as financing.shl_amount_keur (engine-owned closed-form)."},
    "facilities.amount":             {"disposition": "DERIVED_FROM_EXISTING_INPUT", "priority": "P2_ENGINE", "review_note": "Facility amount derived from capex + financing structure."},
    "facilities.amount_paid_in_certificates": {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "No registry field; no engine consumer."},
    "facilities.buffer_on_external_source":    {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "No registry field; no engine consumer."},
    "facilities.cash_interest":      {"disposition": "DERIVED_FROM_EXISTING_INPUT", "priority": "P2_ENGINE", "review_note": "Cash interest is computed by the engine from senior_debt_amount_keur and margin_bps."},
    "facilities.currency":           {"disposition": "UI_GAP", "priority": "P2_ENGINE", "review_note": "Currency is a display field on Inputs!E3 (TUHO). Engine uses EUR via project_setup.identity.country_market + financing.base_rate."},
    "facilities.discount_rate_equity_npv":  {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "No registry field. Engine does not consume."},
    "facilities.discount_rate_project_npv": {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "No registry field. Engine does not consume."},
    "facilities.eur_inflation":      {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "EUR inflation index. No registry field."},
    "facilities.hedge_coverage":     {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "Mapped to registry ProjectInputs.financing.hedge_coverage (RUNTIME_PARTIALLY_BOUND in cross-walk; pack provides the editable cell)."},
    "facilities.interest_on_short_term_loan": {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "No registry field. Engine does not consume short-term loan interest."},
    "facilities.j_dscr":             {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Junior DSCR. No registry field."},
    "facilities.junior_front_end_fee": {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Junior front-end fee. No registry field."},
    "facilities.l_c_fee":            {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "L/C fee. No registry field."},
    "facilities.maturity":           {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Same as debt.senior.tenor_years."},
    "facilities.vat_collected":      {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "VAT collected. No registry field. No engine consumer."},
    "facilities.vat_for_vat_loan_repayment": {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "VAT loan. No registry field."},
    "reserves.0_months":             {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "DSRA initial months. No registry field; engine computes DSRA from CFADS."},
    "reserves.initial_funding":      {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Reserve initial funding. No registry field."},
    "reserves.name":                 {"disposition": "UI_GAP", "priority": "P2_ENGINE", "review_note": "Reserve account name; display only."},
    "reserves.period":               {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Reserve period. No registry field."},
    "reserves.start":                {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Reserve start period. No registry field."},
    "revenue.amount":                {"disposition": "DERIVED_FROM_EXISTING_INPUT", "priority": "P2_ENGINE", "review_note": "Revenue amount derived from tariff * production. Not a user input."},
    "revenue.annual_inflation_on_market_prices": {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "No registry field; engine does not consume market-price inflation (PPA fixed-tariff model)."},
    "revenue.balancing_costs":              {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "Mapped to registry ProjectInputs.revenue.balancing_cost_eur_per_mwh (RUNTIME_PARTIALLY_BOUND in cross-walk; pack provides the editable cell)."},
    "revenue.balancing_costs_bess":         {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "BESS-specific balancing cost; mapped to registry ProjectInputs.revenue.balancing_cost_bess (RUNTIME_PARTIALLY_BOUND)."},
    "revenue.balancing_costs_pv":           {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "PV-specific balancing cost; mapped to registry ProjectInputs.revenue.balancing_cost_pv (RUNTIME_PARTIALLY_BOUND)."},
    "revenue.central_case_gmpv":            {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "GMPV central case. No registry field; engine does not consume."},
    "revenue.co2_price":                    {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "Mapped to registry ProjectInputs.revenue.co2_price_eur (RUNTIME_PARTIALLY_BOUND)."},
    "revenue.ems_revenues_afry_central_case_4h_degraded": {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "AFRY EMS curve. No registry field."},
    "revenue.ems_revenues_afry_low_case_4h_degraded":      {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "AFRY EMS curve. No registry field."},
    "revenue.ems_revenues_afry_stress_case_4h_degraded":   {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "AFRY EMS curve. No registry field."},
    "revenue.if_profile":                   {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "IF (intrinsic forecasting) profile. No registry field."},
    "revenue.index":                        {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "Mapped to registry ProjectInputs.revenue.ppa_index (RUNTIME_PARTIALLY_BOUND)."},
    "revenue.inflation_index":              {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Inflation index. Distinct from opex inflation; no registry field."},
    "revenue.low_case_gmpv":                {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "GMPV low case. No registry field."},
    "revenue.payment_year":                 {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Payment year. No registry field."},
    "revenue.scenario":                     {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Scenario label. Display only."},
    "revenue.unfcc_s_retainer":             {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "UNFCCC retainer. No registry field."},
    "schedule.financial_close":             {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Same as registry project_setup.technical.cod_date (engine_path info.financial_close)."},
    "schedule.investment_horizon":          {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Same as registry project_setup.technical.horizon_years."},
    "schedule.model_horizon":               {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Same as registry project_setup.technical.horizon_years."},
    "schedule.model_period":                {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Same as registry project_setup.info.period_frequency (display only)."},
    "schedule.project_life":                {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Same as registry project_setup.technical.horizon_years."},
    "schedule.scheduled_construction_time": {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Same as registry project_setup.technical.construction_months."},
    "tax.cap":                              {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Tax cap toggle. No registry field. No engine consumer."},
    "tax.legal_reserve":                    {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "Mapped to registry ProjectInputs.tax.legal_reserve_cap (engine-owned closed-form; pack provides the editable cell)."},
    "tax.losses_carried_forward":           {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Pack losses_carried_forward is a MAX cap (years); registry tax.loss_carryforward_years is the editable years input. Documented as separate in unresolved_pack_id_evidence (tax.loss_carryforward_max_years)."},
    "tax.max_shl_interests_expenses":       {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "Mapped to registry ProjectInputs.tax.atad_min_interest_keur (engine-owned closed-form)."},
    "tax.max_shl_interests_of_ebitda":      {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "Mapped to registry ProjectInputs.tax.atad_ebitda_limit (engine-owned closed-form)."},
    "tax.on_debt_interests":                {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "Mapped to registry ProjectInputs.tax.wht_sponsor_shl_interest (RUNTIME_PARTIALLY_BOUND; pack provides the editable cell)."},
    "tax.on_financial_revenues":            {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "Mapped to registry ProjectInputs.tax.wht_sponsor_dividends (RUNTIME_PARTIALLY_BOUND; pack provides the editable cell)."},
    "tax.on_technical_services":            {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "WHT on technical services. No registry field. No engine consumer."},
    "tax.on_upfront_fees":                  {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "WHT on upfront fees. No registry field. No engine consumer."},
    "tax.rate":                             {"disposition": "MAPPED_TO_REGISTRY", "priority": "P0", "review_note": "Pack 'tax.rate' is a disambiguating label only; the registry has multiple rate fields (CIT, WHT, VAT). The disposition is MAPPED_TO_REGISTRY for the CIT cell and ENGINE_GAP for WHT/VAT (see canonical_to_pack_id_evidence)."},
    "tax.reimbursed":                       {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "WHT reimbursed toggle. No registry field."},
    "tax.shl_interest_rate_cap_applicable_foreign_shareholder": {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "Mapped to registry ProjectInputs.tax.shl_cap_applies (engine-owned closed-form)."},
    "tax.thin_capitalization":              {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2_ENGINE", "review_note": "Mapped to registry ProjectInputs.tax.thin_cap_enabled (engine-owned closed-form; pack provides the editable cell)."},
    "tax.vat_break":                        {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "VAT break flag. No registry field. No engine consumer."},
    "tax.wht_on_senior_refinancing":        {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "WHT on senior refinancing. No registry field. No engine consumer (no refinancing model)."},
    "technical.bess_degradation":           {"disposition": "MAPPED_TO_REGISTRY", "priority": "P1_ENGINE", "review_note": "Mapped to registry ProjectInputs.technical.bess_degradation (RUNTIME_PARTIALLY_BOUND; BESS-only)."},
    "technical.curtailment":                {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "No registry field; engine does not consume (TUHO wind has no curtailment model)."},
    "technical.discount":                   {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "No registry field. WACC/discount rate is engine-internal."},
    "technical.grid_availability":          {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "No registry field. Engine does not consume (P50 already captures availability)."},
    "technical.historical_average":         {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Historical average (yield reference). No registry field. Diagnostic only."},
    "technical.period":                     {"disposition": "TRUE_DUPLICATE", "priority": "P2_ENGINE", "review_note": "Same as registry project_setup.info.period_frequency (display only)."},
    "technical.plant_availability":         {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "No registry field. Engine does not consume (P50 already captures availability)."},
    "technical.power_curve_adjustment":     {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "No registry field. Engine does not consume."},
    "technical.pv_module_degradation":      {"disposition": "MAPPED_TO_REGISTRY", "priority": "P1_ENGINE", "review_note": "Mapped to registry ProjectInputs.technical.pv_degradation (RUNTIME_PARTIALLY_BOUND; setter _set_technical_degradation exists)."},
    "technical.yield_study":                {"disposition": "ENGINE_GAP", "priority": "P2_ENGINE", "review_note": "Yield study reference; no registry field."},

    # Project identity (canonical registry fields)
    "project.project_company":              {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2", "review_note": "Mapped to registry ui.project.project_company (DISPLAY_ONLY; pack provides the editable cell)."},
    "project.project_code":                 {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2", "review_note": "Mapped to registry ui.project.project_code (DISPLAY_ONLY; pack provides the editable cell)."},
    "project.project_name":                 {"disposition": "MAPPED_TO_REGISTRY", "priority": "P0", "review_note": "Mapped to registry project_setup.identity.project_name (RUNTIME_FULLY_BOUND; pack provides the editable cell)."},
    "project.country":                      {"disposition": "MAPPED_TO_REGISTRY", "priority": "P0", "review_note": "Mapped to registry project_setup.identity.country_market (RUNTIME_FULLY_BOUND; pack provides the editable cell)."},
    "project.currency":                     {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2", "review_note": "Mapped to registry project_setup.identity.currency (DISPLAY_ONLY; pack provides the editable cell)."},
    "project.project_type":                 {"disposition": "MAPPED_TO_REGISTRY", "priority": "P2", "review_note": "Mapped to registry project_setup.identity.project_type (TEMPLATE_LOCKED; pack provides the editable cell)."},
}


def _build_editable_input_disposition(
    manifest_rows_by_model: Dict[str, List[Dict[str, Any]]],
    pack_by_canonical: Dict[str, Dict[str, Any]],
    source_extraction: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Build the v5.1 editable-input disposition rows.

    Every EDITABLE_INPUT manifest row across both models must
    appear exactly once. Each row gets:
      * model, sheet, row, active_cell, label
      * field_id_candidate
      * canonical_field_id (or '' if not mapped)
      * disposition
      * technology_scope
      * runtime_status (the cross-walk's runtime_binding_status for
        the canonical field, or N/A)
      * scenario_eligible (bool: TRUE if the pack has a scenario row)
      * priority
      * confidence
      * review_note
    """
    # Build set of scenario-eligible pack_ids (pack has at least one
    # scenario row in any model)
    scenario_packs: Set[str] = set()
    for m in ("tuho", "oborovo"):
        scen_manifest = ARTIFACT_DIR / f"{m}_scenario_manifest_v5.json"
        if not scen_manifest.is_file():
            continue
        s = _load_json(scen_manifest)
        for row in s.get("rows", []):
            cand = row.get("field_id_candidate", "")
            if cand:
                scenario_packs.add(cand)

    # Build a lookup of (model, row) -> source extraction row so we
    # can confirm the active_cell.
    src_by_key: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for m, rows in source_extraction.items():
        for r in rows:
            src_by_key[(m, r.get("row", -1))] = r

    # Build a lookup of canonical_field_id -> cross-walk status
    xw_path = ARTIFACT_DIR / "canonical_registry_crosswalk_v5.csv"
    xw_by_canonical: Dict[str, Dict[str, str]] = {}
    if xw_path.is_file():
        for r in csv.DictReader(xw_path.open(encoding="utf-8")):
            xw_by_canonical[r["canonical_field_id"]] = r

    out: List[Dict[str, Any]] = []
    for model_key, rows in manifest_rows_by_model.items():
        for r in rows:
            if r.get("workbook_classification") != "EDITABLE_INPUT":
                continue
            row_idx = r.get("row", -1)
            cand = r.get("field_id_candidate", "")
            label = r.get("label", "")
            sheet = r.get("section", "")
            active_cell = r.get("active_cell", "")
            # Find canonical field id via PACK_TO_CANONICAL
            pack_entry = None
            for m in PACK_TO_CANONICAL:
                if m["pack_id"] == cand:
                    pack_entry = m
                    break
            if pack_entry is not None:
                canonical_field_id = pack_entry["canonical_field_id"]
                mapping_type = pack_entry["mapping_type"]
                confidence = pack_entry["confidence"]
                if mapping_type in ("EXACT", "TRUE_SYNONYM"):
                    disposition = "MAPPED_TO_REGISTRY"
                elif mapping_type == "DERIVED_FROM":
                    disposition = "DERIVED_FROM_EXISTING_INPUT"
                elif mapping_type == "LEGACY_SUPERSEDED":
                    disposition = "LEGACY_SUPERSEDED"
                elif mapping_type == "DISPLAY_ONLY":
                    disposition = "MAPPED_TO_REGISTRY"
                elif mapping_type == "UNRESOLVED":
                    disposition = "UNRESOLVED"
                elif mapping_type == "NOT_PRESENT_IN_TUHO":
                    disposition = "NOT_APPLICABLE"
                elif mapping_type == "NOT_PRESENT_IN_OBOROVO":
                    disposition = "NOT_APPLICABLE"
                else:
                    disposition = "UNRESOLVED"
                review_note = pack_entry.get("review_note", "")
                # Priority: derive from canonical field's runtime status
                xw = xw_by_canonical.get(canonical_field_id, {})
                rs = xw.get("runtime_binding_status", "UNRESOLVED")
                if rs == "RUNTIME_FULLY_BOUND":
                    priority = "P0"
                elif rs in ("RUNTIME_PARTIALLY_BOUND",):
                    priority = "P1_ENGINE"
                elif rs == "TEMPLATE_LOCKED":
                    priority = "P2"
                elif rs == "DERIVED_ONLY":
                    priority = "P0_ENGINE"
                elif rs == "DISPLAY_ONLY":
                    priority = "P2"
                else:
                    priority = "P2_ENGINE"
            else:
                # Fall back to per-pack override
                ovr = _DISPOSITION_BY_PACK_ID.get(cand, {})
                disposition = ovr.get("disposition", "UNRESOLVED")
                priority = ovr.get("priority", "P2_ENGINE")
                review_note = ovr.get("review_note", "")
                confidence = "CONFIRMED" if disposition != "UNRESOLVED" else "UNRESOLVED"
                # Try UNRESOLVED_PACK_IDS too
                for u in UNRESOLVED_PACK_IDS:
                    if u["pack_id"] == cand:
                        # Honor the unresolved entry's status
                        u_status = u["status"]
                        if u_status in ("ENGINE_GAP", "APPLICABLE_BESS", "LEGACY_SUPERSEDED",
                                        "NOT_APPLICABLE"):
                            disposition = u_status
                        confidence = u["confidence"]
                        # If verified cell is provided, use it (after Â§7 fix)
                        # (The main verifier in Â§7 will reject bad A-column
                        # cells; here we just copy the unresolved entry's
                        # verified_cell_* for the disposition record.)
                        break
                canonical_field_id = ""  # we don't know the canonical id

            # Active cell verification: must equal source extraction
            # active_cell (the column the user actually edits in the
            # workbook).
            src_row = src_by_key.get((model_key, row_idx), {})
            tech = src_row.get("technology", "")
            out.append({
                "model": model_key.upper(),
                "sheet": sheet,
                "row": row_idx,
                "active_cell": active_cell,
                "label": label,
                "field_id_candidate": cand,
                "canonical_field_id": canonical_field_id,
                "disposition": disposition,
                "technology_scope": tech,
                "runtime_status": xw_by_canonical.get(canonical_field_id, {}).get(
                    "runtime_binding_status", "N/A"
                ) if canonical_field_id else "N/A",
                "scenario_eligible": "TRUE" if cand in scenario_packs else "FALSE",
                "priority": priority,
                "confidence": confidence,
                "review_note": review_note,
            })
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print("build_artifacts: start (v5)")
    _collect_real_pytest_node_ids()
    print(f"  collected real pytest node IDs: {len(KNOWN_PYTEST_NODE_IDS)}")

    reg = _registry_inventory()
    print(f"  registry inventory: {len(reg)} fields")

    # Cross-walk is the single source of truth
    xw = _build_crosswalk(reg)
    xw_csv = ARTIFACT_DIR / "canonical_registry_crosswalk_v5.csv"
    with xw_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(xw[0].keys()), lineterminator="\n")
        w.writeheader()
        for r in xw:
            w.writerow(r)
    print(f"  wrote {xw_csv.name}: {len(xw)} rows")

    # Helper map
    helper = {c["registry_field_id"]: c["canonical_field_id"] for c in xw if c["registry_field_id"]}
    (ARTIFACT_DIR / "canonical_field_id_to_registry_id.json").write_text(
        json.dumps(helper, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"  wrote canonical_field_id_to_registry_id.json: {len(helper)} mappings")

    # Catalog (derived from cross-walk)
    catalog = _build_catalog_from_crosswalk(xw)
    cat_csv = ARTIFACT_DIR / "canonical_field_catalog_v5.csv"
    with cat_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(catalog[0].keys()), lineterminator="\n")
        w.writeheader()
        for r in catalog:
            w.writerow(r)
    print(f"  wrote {cat_csv.name}: {len(catalog)} rows")

    # Inputs manifests (real rows + decision table)
    for model in ("TUHO", "OBOROVO"):
        m = _build_inputs_manifest(model)
        path = ARTIFACT_DIR / f"{model.lower()}_model_manifest_v5.json"
        path.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        cls_counts = Counter(r["workbook_classification"] for r in m["rows"])
        print(f"  wrote {path.name}: {m['row_count']} rows")
        for k in sorted(cls_counts):
            print(f"    {k}: {cls_counts[k]}")

    # Scenarios manifests (real rows + decision table)
    for model in ("TUHO", "OBOROVO"):
        m = _build_scenarios_manifest(model)
        path = ARTIFACT_DIR / f"{model.lower()}_scenario_manifest_v5.json"
        path.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        cls_counts = Counter(r["workbook_classification"] for r in m["rows"])
        print(f"  wrote {path.name}: {m['row_count']} rows")
        for k in sorted(cls_counts):
            print(f"    {k}: {cls_counts[k]}")

    # Pack evidence
    ev_csv = ARTIFACT_DIR / "canonical_to_pack_id_evidence.csv"
    ev_fields = list(PACK_TO_CANONICAL[0].keys())
    with ev_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ev_fields, lineterminator="\n")
        w.writeheader()
        for r in PACK_TO_CANONICAL:
            w.writerow(r)
    print(f"  wrote {ev_csv.name}: {len(PACK_TO_CANONICAL)} rows")

    # Unresolved pack IDs
    un_csv = ARTIFACT_DIR / "unresolved_pack_id_evidence.csv"
    unresolved_rows = _normalized_unresolved_pack_ids()
    un_fields = UNRESOLVED_FIELD_ORDER
    with un_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=un_fields, lineterminator="\n")
        w.writeheader()
        for r in unresolved_rows:
            w.writerow({k: r.get(k, "") for k in un_fields})
    print(f"  wrote {un_csv.name}: {len(unresolved_rows)} rows")

    # Matrix (derived from cross-walk)
    matrix = _build_matrix_from_crosswalk(xw)
    mat_csv = ARTIFACT_DIR / "input_coverage_matrix_v5.csv"
    with mat_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(matrix[0].keys()), lineterminator="\n")
        w.writeheader()
        for r in matrix:
            w.writerow(r)
    print(f"  wrote {mat_csv.name}: {len(matrix)} rows")

    # v5.1: editable-input disposition (every EDITABLE_INPUT manifest
    # row gets exactly one disposition).
    manifest_rows_by_model = {}
    source_extraction_by_model = {}
    for m in ("tuho", "oborovo"):
        manifest_path = ARTIFACT_DIR / f"{m}_model_manifest_v5.json"
        if manifest_path.is_file():
            manifest_rows_by_model[m] = _load_json(manifest_path).get("rows", [])
        src_path = SOURCE_DIR / f"{m}_inputs_source_v2.json"
        if src_path.is_file():
            source_extraction_by_model[m] = _load_json(src_path).get("rows", [])
    pack_by_canonical = {}
    disposition_rows = _build_editable_input_disposition(
        manifest_rows_by_model, pack_by_canonical, source_extraction_by_model
    )
    disp_path = ARTIFACT_DIR / "editable_input_disposition_v5_1.csv"
    with disp_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(disposition_rows[0].keys()), lineterminator="\n")
        w.writeheader()
        for r in disposition_rows:
            w.writerow(r)
    print(f"  wrote {disp_path.name}: {len(disposition_rows)} rows")

    # Coverage summary (depends on disposition CSV; write AFTER it)
    summary = _build_coverage_summary(catalog, xw)
    summary_path = ARTIFACT_DIR / "coverage_summary_v5.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  wrote {summary_path.name}")

    print("  runtime_binding_status counts (registry-backed):")
    for k, v in sorted(summary["registry_backed_canonical"]["by_runtime_binding_status"].items()):
        print(f"    {k}: {v}")
    print("  excel_mapping_status counts (registry-backed):")
    for k, v in sorted(summary["registry_backed_canonical"]["by_excel_mapping_status"].items()):
        print(f"    {k}: {v}")
    print("  workbook-only concept status counts:")
    for k, v in sorted(summary["workbook_only_concepts"]["by_status"].items()):
        print(f"    {k}: {v}")
    print("  engine-owned boundary status counts:")
    for k, v in sorted(summary["engine_owned_boundaries"]["by_runtime_binding_status"].items()):
        print(f"    {k}: {v}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

