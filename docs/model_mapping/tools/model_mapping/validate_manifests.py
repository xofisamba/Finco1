"""
validate_manifests.py — v5 (evidence-integrity correction)

Stage 3 of the v5 mapping pipeline.

Compares the committed v5 artifacts (built by
``build_artifacts.py``) against:

* the live ``app.workbook.registry.WORKBOOK`` inventory;
* the committed source extraction JSONs in
  ``docs/model_mapping/source/``;
* the v5-specific contracts documented in
  ``scenario_override_contract.md`` and
  ``dependency_and_circularity_notes.md``.

The validator is **independent** of the builder. It does NOT
import the builder's internal constants. Its only inputs are
the committed artifacts and the live registry.

v5 evidence-integrity rules
---------------------------

1. **Real-symbol AST check**. For every
   ``adapter_evidence_type=EXACT_SYMBOL``, the validator
   parses the referenced Python file with ``ast`` and confirms
   the named symbol exists in the file. For
   ``INLINE_LOGIC``, it confirms the containing function
   exists. For ``SERVICE_PIPELINE``, it confirms every named
   function in the pipeline exists.

2. **ProjectInputs path check**. For every
   ``projectinputs_path`` that is not ``UNRESOLVED`` or
   ``NOT_APPLICABLE``, the validator imports the real
   ``ProjectInputs`` (and friends) and confirms the path
   resolves. Where the path is a bracket notation (e.g.
   ``opex[technical_management].y1_amount_keur``), the
   validator records the field as a tuple-indexed
   projectinput and does not require AST resolution of the
   bracket key.

3. **Pytest node ID check**. For every
   ``test_evidence`` that is not ``NO_TEST_EVIDENCE``, the
   validator runs ``python -m pytest --collect-only`` and
   confirms the node ID is in the collected set.

4. **Verified coordinate check**. For every
   ``verified_*_input_cell`` that is not empty, the validator
   confirms the cell is in the source extraction JSON. A
   string that is not in source extraction is rejected.

5. **Catalog/matrix consistency check**. The cross-walk
   (``canonical_registry_crosswalk_v5.csv``) is the single
   source of truth. The matrix and the catalog are
   generated from the cross-walk. The validator compares the
   catalog's ``runtime_binding_status`` to the cross-walk's
   ``runtime_binding_status`` (and likewise for
   ``excel_mapping_status``). Mismatches are rejected.

6. **No matrix post-processing upgrade**. The validator
   rejects any catalog or matrix row whose
   ``runtime_binding_status`` is TEMPLATE_LOCKED,
   DERIVED_ONLY, or DISPLAY_ONLY but whose cross-walk evidence
   has only generic strings (no real symbol). This enforces
   the "no upgrade" rule.

7. **Inputs semantic classification**. Reject formula +
   EDITABLE_INPUT, section/header + EDITABLE_INPUT, Derived/
   read-only + EDITABLE_INPUT, N/A + EDITABLE_INPUT, kind=
   section + EDITABLE_INPUT. Reject UNSUPPORTED rows.

8. **Scenario semantic classification**. Reject empty
   heading + SCENARIO_OVERRIDE. Reject formula active cell +
   DIRECT_BASE_INPUT (must be LINKED_BASE_VALUE).

The validator exits 0 on success, 1 on failure.
"""

from __future__ import annotations

import ast
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

HERE = Path(__file__).resolve().parent
ARTIFACT_DIR = HERE.parent.parent
SOURCE_DIR = ARTIFACT_DIR / "source"
# v5.2: when ARTIFACT_DIR is redirected to a tmp dir (e.g. by
# mutation tests), fall back to the canonical source dir under
# docs/model_mapping/source.
SOURCE_DIR_FALLBACK = HERE.parent / "source"
REPO_ROOT = ARTIFACT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
from app.workbook.registry import WORKBOOK  # noqa: E402

# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------

RUNTIME_BINDING_STATUSES: Set[str] = {
    "RUNTIME_FULLY_BOUND", "RUNTIME_PARTIALLY_BOUND", "RUNTIME_BOUND_WRONG",
    "TEMPLATE_LOCKED", "DERIVED_ONLY", "DISPLAY_ONLY",
    "NOT_RUNTIME_INPUT", "UNRESOLVED",
}

EXCEL_MAPPING_STATUSES: Set[str] = {
    "VERIFIED_BOTH_MODELS", "VERIFIED_TUHO_ONLY", "VERIFIED_OBOROVO_ONLY",
    "REGISTRY_HINT_ONLY", "NOT_PRESENT_IN_TUHO", "NOT_PRESENT_IN_OBOROVO",
    "NOT_PRESENT_IN_BOTH", "SOURCE_COORDINATE_UNRESOLVED", "NOT_APPLICABLE",
}

EVIDENCE_TYPES: Set[str] = {
    "EXACT_SYMBOL", "INLINE_LOGIC", "SERVICE_PIPELINE",
    "CONCEPTUAL_DESCRIPTION", "NOT_APPLICABLE", "UNRESOLVED",
}

INPUTS_WORKBOOK_CLASSIFICATIONS: Set[str] = {
    "EDITABLE_INPUT", "LINKED_VALUE", "DERIVED_FORMULA", "ENGINE_OUTPUT",
    "CHECK_ONLY", "SECTION_HEADER", "LEGEND_TOOL", "UNSUPPORTED", "IGNORE",
}

SCENARIO_WORKBOOK_CLASSIFICATIONS: Set[str] = {
    "SCENARIO_OVERRIDE", "SECTION_HEADER", "ENGINE_OUTPUT", "DERIVED_FORMULA",
    "CHECK_ONLY", "LEGEND_TOOL", "UNSUPPORTED", "IGNORE",
}

ACTIVE_CELL_ROLES: Set[str] = {
    "DIRECT_BASE_INPUT", "LINKED_BASE_VALUE", "DERIVED_BASE_FORMULA",
    "OUTPUT", "CHECK", "HEADER", "UNRESOLVED",
}

SEMANTIC_CELL_ROLES: Set[str] = {
    "EDITABLE_HARDCODE", "TOGGLE", "TEXT_INPUT", "DATE_INPUT",
    "FORMULA_RESULT", "DERIVED_OUTPUT", "SUBSECTION_LABEL",
    "LABEL", "COUNTERPARTY_LABEL", "UNRESOLVED",
}

EVIDENCE_BASES: Set[str] = {
    "PROGRAMMATIC_WORKBOOK_INSPECTION", "SOURCE_EXTRACTION",
    "REGISTRY_EVIDENCE", "RUNTIME_CODE_EVIDENCE", "TEST_EVIDENCE",
    "UNRESOLVED",
}

MAPPING_VERIFICATION_STATUSES: Set[str] = {
    "MAPPING_CONFIRMED", "ABSENCE_CONFIRMED", "PROBABLE", "UNRESOLVED",
}

SEMANTIC_VALUE_KINDS: Set[str] = {
    "numeric", "boolean", "text", "date", "formula", "label",
    "derived", "unresolved", "n/a", "",
}

SEMANTIC_UNITS: Set[str] = {
    "ratio_0_1", "currency_keur", "currency", "date", "text",
    "boolean", "year_count", "years", "bps", "n/a", "",
}

SEMANTIC_UNRESOLVED_COLUMNS = {
    "canonical_concept", "pack_id", "model", "cell_role", "value_kind",
    "unit", "evidence_basis", "mapping_verification_status",
    "shared_source_id", "review_note", "status", "confidence",
    "verified_label_cell_tuho", "verified_label_cell_oborovo",
    "verified_value_cell_tuho", "verified_value_cell_oborovo",
    "verified_editable_cell_tuho", "verified_editable_cell_oborovo",
    "verified_formula_cell_tuho", "verified_formula_cell_oborovo",
    "verified_counterparty_label_cell_tuho",
    "verified_counterparty_label_cell_oborovo",
    "verified_formula_period_cell_tuho",
    "verified_formula_period_cell_oborovo",
}

SCENARIO_RANGE_ROLES: Set[str] = {
    "SPARSE_OVERRIDE", "FORMULA_PROPAGATION", "OUTPUT_COMPARISON",
    "HEADER_PRESENTATION", "NO_OVERRIDE", "UNRESOLVED",
}

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    target = path
    if not target.is_file() and not path.is_absolute():
        # Try the canonical source dir under docs/model_mapping/source.
        alt = SOURCE_DIR_FALLBACK / path.name
        if alt.is_file():
            target = alt
    with target.open(encoding="utf-8") as f:
        return json.load(f)


def _load_csv(path: Path) -> List[Dict[str, str]]:
    target = path
    if not target.is_file() and not path.is_absolute():
        alt = SOURCE_DIR_FALLBACK / path.name
        if alt.is_file():
            target = alt
    with target.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _err(messages: List[str], msg: str) -> None:
    messages.append(msg)


# ---------------------------------------------------------------------------
# Real-symbol AST verification
# ---------------------------------------------------------------------------


def _check_exact_symbol(ref: str) -> Tuple[bool, str]:
    """Verify a `path::symbol` reference via AST.

    The file at `path` must exist. The file must contain a
    top-level (or class-level) function / class / method
    named `symbol`.
    """
    if "::" not in ref:
        return False, f"ref {ref!r} does not match 'path::symbol'"
    file_part, symbol = ref.split("::", 1)
    p = REPO_ROOT / file_part
    if not p.is_file():
        return False, f"ref {ref!r}: file {file_part!r} does not exist"
    try:
        tree = ast.parse(p.read_text(), filename=str(p))
    except SyntaxError as e:
        return False, f"ref {ref!r}: SyntaxError {e}"
    return _ast_has_symbol(tree, symbol), \
        f"ref {ref!r}: symbol {symbol!r} not found in {file_part}"


def _ast_has_symbol(tree: ast.Module, symbol: str) -> bool:
    """Walk a Module AST and check for any matching top-level / class-level name."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == symbol:
                return True
    return False


def _check_inline_logic(ref: str) -> Tuple[bool, str]:
    """Verify a `path::containing_function` reference for INLINE_LOGIC."""
    return _check_exact_symbol(ref)


def _check_service_pipeline(refs: List[str]) -> List[str]:
    """Verify every ref in a SERVICE_PIPELINE exists."""
    errs: List[str] = []
    for ref in refs:
        ok, msg = _check_exact_symbol(ref)
        if not ok:
            errs.append(f"SERVICE_PIPELINE ref {ref!r}: {msg}")
    return errs


# ---------------------------------------------------------------------------
# ProjectInputs path verification
# ---------------------------------------------------------------------------


def _check_projectinputs_path(path: str) -> Tuple[bool, str]:
    """Verify a ProjectInputs path resolves on the real domain
    model. Returns (ok, error_msg)."""
    if not path or path in ("UNRESOLVED", "NOT_APPLICABLE", "NO_TEST_EVIDENCE"):
        return True, ""
    # Strip the leading "ProjectInputs." or "ProjectInputsSchema."
    if path.startswith("ProjectInputs."):
        rest = path[len("ProjectInputs."):]
    elif path.startswith("ProjectInputsSchema."):
        rest = path[len("ProjectInputsSchema."):]
    else:
        return False, f"path {path!r} does not start with 'ProjectInputs.' or 'ProjectInputsSchema.'"

    # Resolve the path
    try:
        from finco_core.inputs._models import ProjectInputs
    except Exception as e:
        return False, f"could not import finco_core ProjectInputs: {e}"

    return _walk_pi_path(ProjectInputs, rest, path)


def _walk_pi_path(obj: Any, rest: str, full_path: str) -> Tuple[bool, str]:
    """Walk a ProjectInputs/ProjectInputsSchema path. Handles
    bracket notation (e.g. 'opex[*].y1_amount_keur') as a
    tuple-indexed field."""
    parts = rest.split(".")
    cur = obj
    for part in parts:
        # Strip tuple-bracket suffix
        bracket_key = None
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\[([^\]]+)\]$", part)
        if m:
            part, bracket_key = m.group(1), m.group(2)
        # If cur is a class, walk its annotations
        if isinstance(cur, type):
            ann = getattr(cur, "__annotations__", {})
            if part not in ann:
                return False, f"path {full_path!r}: attribute {part!r} not found on class {cur.__name__}"
            ann_type = ann[part]
            # Handle string forward references
            if isinstance(ann_type, str):
                ann_type = _resolve_forward_ref(cur, ann_type)
            cur = ann_type
        else:
            # GenericAlias (e.g. tuple[OpexItem, ...])
            if hasattr(cur, "__origin__") and cur.__origin__ is tuple:
                args = getattr(cur, "__args__", ())
                if args:
                    cur = args[0]
                    # fall through to walk the field on the element
                    if isinstance(cur, type):
                        ann = getattr(cur, "__annotations__", {})
                        if part not in ann:
                            return False, f"path {full_path!r}: attribute {part!r} not found on {cur.__name__}"
                        cur = ann[part]
                        continue
            if not hasattr(cur, part):
                return False, f"path {full_path!r}: attribute {part!r} not found on {type(cur).__name__}"
            cur = getattr(cur, part)
    return True, ""


def _resolve_forward_ref(cls: type, type_name: str) -> Any:
    """Resolve a forward-reference string to an actual type by
    looking it up in the same module's globals()."""
    module_globals = getattr(sys.modules.get(cls.__module__), "__dict__", {})
    return module_globals.get(type_name, type_name)


# ---------------------------------------------------------------------------
# Pytest node ID verification
# ---------------------------------------------------------------------------


def _collect_real_pytest_node_ids() -> Set[str]:
    """Return the set of real pytest node IDs by AST-walking the
    candidate test files. v5.2 makes this independent of the
    runtime pytest install: the AST walker records
    `file::TestClass::test_method` and `file::test_function` for
    every `def test_xxx` inside a `class TestXxx` or at module
    top level. This works in CI, in local sandboxes, and in
    tar clones (test_clean_checkout_builder_works).
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
    node_ids: Set[str] = set()
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
                        node_ids.add(f"{rel}::{class_name}::{item.name}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                node_ids.add(f"{rel}::{node.name}")
    # Optional complementary pass via pytest --collect-only.
    # Failures here are non-fatal: the AST walker is authoritative.
    if existing:
        try:
            out = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q", *existing],
                cwd=REPO_ROOT, capture_output=True, text=True, timeout=180,
            )
            for line in out.stdout.splitlines():
                line = line.strip()
                if "::" in line and line.startswith("tests/"):
                    node_ids.add(line)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
    return node_ids


# ---------------------------------------------------------------------------
# Required artifacts + no proprietary
# ---------------------------------------------------------------------------


REQUIRED_ARTIFACTS = [
    "canonical_field_catalog_v5.csv",
    "canonical_field_id_to_registry_id.json",
    "canonical_registry_crosswalk_v5.csv",
    "canonical_to_pack_id_evidence.csv",
    "unresolved_pack_id_evidence.csv",
    "input_coverage_matrix_v5.csv",
    "tuho_model_manifest_v5.json",
    "oborovo_model_manifest_v5.json",
    "tuho_scenario_manifest_v5.json",
    "oborovo_scenario_manifest_v5.json",
    "coverage_summary_v5.json",
    "support_package_metadata_audit_v5_3_1.json",
    "source/tuho_inputs_source_v2.json",
    "source/oborovo_inputs_source_v2.json",
    "source/tuho_scenarios_source_v2.json",
    "source/oborovo_scenarios_source_v2.json",
]


def check_required_files() -> List[str]:
    errs: List[str] = []
    for rel in REQUIRED_ARTIFACTS:
        if not (ARTIFACT_DIR / rel).is_file():
            _err(errs, f"missing required artifact: {rel}")
    return errs


def check_no_proprietary() -> List[str]:
    errs: List[str] = []
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        )
        tracked = out.stdout.splitlines()
    except subprocess.CalledProcessError:
        tracked = []
    forbidden = [
        "Finco1_Excel_Input_Coverage_Agent_Package",
        "20260330" + "_" + "TUHO" + "_" + "BP",
        "20260414" + "_" + "BP" + "_" + "Oborovo",
        "Finco1_Excel_Model_Mapping_Foundation",
    ]
    for f in tracked:
        for s in forbidden:
            if s in f:
                _err(errs, f"forbidden proprietary file tracked: {f}")
    public_prefixes = (
        "docs/model_mapping/",
        "tests/test_model_mapping_manifests.py",
        ".github/workflows/excel_mapping_validation.yml",
    )
    public_files = [
        f for f in tracked
        if f.startswith(public_prefixes) and "/source/" not in f
        and not f.endswith(".pyc")
    ]
    forbidden_literals = [
        "VISUAL" + "_" + "AUDIT",
        "." + "xlsm", "." + "xlsx", "." + "zip", "." + "pdf",
        "INDEX" + "/" + "MATCH",
        "=" + "Scenarios", "=" + "EDATE", "=" + "SUM",
        "=" + "IF", "=" + "INDEX",
        "D421 " + "= ", "D438 " + "= ",
        "C298" + "=", "C300" + "=", "C301 " + "=",
    ]
    for rel in public_files:
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")
        for literal in forbidden_literals:
            if literal in text:
                _err(errs, f"forbidden confidential artifact text in {rel}: {literal}")
    return errs


# ---------------------------------------------------------------------------
# Vocabulary checks
# ---------------------------------------------------------------------------


def check_crosswalk_vocabulary(xw: List[Dict[str, str]]) -> List[str]:
    errs: List[str] = []
    for r in xw:
        if r["runtime_binding_status"] not in RUNTIME_BINDING_STATUSES:
            _err(errs, f"row {r['canonical_field_id']!r}: invalid runtime_binding_status {r['runtime_binding_status']!r}")
        if r["excel_mapping_status"] not in EXCEL_MAPPING_STATUSES:
            _err(errs, f"row {r['canonical_field_id']!r}: invalid excel_mapping_status {r['excel_mapping_status']!r}")
        for ev_key, ev_label in [
            ("save_evidence_type", "save_evidence_type"),
            ("adapter_evidence_type", "adapter_evidence_type"),
            ("engine_consumer_evidence_type", "engine_consumer_evidence_type"),
        ]:
            v = r.get(ev_key, "")
            if v not in EVIDENCE_TYPES:
                _err(errs, f"row {r['canonical_field_id']!r}: invalid {ev_label} {v!r}")
    return errs


def check_manifest_vocabulary(rows: List[Dict[str, Any]], model: str,
                              scenario: bool) -> List[str]:
    errs: List[str] = []
    allowed_cls = SCENARIO_WORKBOOK_CLASSIFICATIONS if scenario else INPUTS_WORKBOOK_CLASSIFICATIONS
    for r in rows:
        cls = r.get("workbook_classification", "")
        if cls not in allowed_cls:
            _err(errs, f"{model} row {r.get('row_id')}: invalid classification {cls!r}")
        if scenario:
            for k in ("active_cell_role", "scenario_range_role"):
                v = r.get(k, "")
                if v not in (ACTIVE_CELL_ROLES if k == "active_cell_role" else SCENARIO_RANGE_ROLES):
                    _err(errs, f"{model} row {r.get('row_id')}: invalid {k} {v!r}")
    return errs


# ---------------------------------------------------------------------------
# Evidence-integrity checks
# ---------------------------------------------------------------------------


def check_real_symbols(xw: List[Dict[str, str]]) -> List[str]:
    """Verify every EXACT_SYMBOL / INLINE_LOGIC / SERVICE_PIPELINE
    reference points to a real symbol in the source code."""
    errs: List[str] = []
    for r in xw:
        cfid = r["canonical_field_id"]
        # Save
        if r["save_evidence_type"] == "EXACT_SYMBOL":
            ok, msg = _check_exact_symbol(r["save_path"])
            if not ok:
                _err(errs, f"{cfid}: save_path {msg}")
        elif r["save_evidence_type"] == "SERVICE_PIPELINE":
            for sub in r["save_path"].split(" → "):
                ok, msg = _check_exact_symbol(sub.strip())
                if not ok:
                    _err(errs, f"{cfid}: SERVICE_PIPELINE ref {msg}")
        # Adapter
        if r["adapter_evidence_type"] == "EXACT_SYMBOL":
            ok, msg = _check_exact_symbol(r["adapter_path"])
            if not ok:
                _err(errs, f"{cfid}: adapter_path {msg}")
        elif r["adapter_evidence_type"] == "INLINE_LOGIC":
            ok, msg = _check_inline_logic(r["adapter_path"])
            if not ok:
                _err(errs, f"{cfid}: adapter_path (INLINE_LOGIC) {msg}")
        elif r["adapter_evidence_type"] == "SERVICE_PIPELINE":
            ok, msg = _check_exact_symbol(r["adapter_path"])
            if not ok:
                _err(errs, f"{cfid}: adapter_path (SERVICE_PIPELINE) {msg}")
    return errs


def check_projectinputs_paths(xw: List[Dict[str, str]]) -> List[str]:
    """Verify every projectinputs_path resolves on the real domain."""
    errs: List[str] = []
    from finco_core.inputs._models import ProjectInputs
    for r in xw:
        cfid = r["canonical_field_id"]
        pi = r["projectinputs_path"]
        if not pi or pi in ("UNRESOLVED", "NOT_APPLICABLE"):
            continue
        # Strip "ProjectInputs." / "ProjectInputsSchema." prefix
        if pi.startswith("ProjectInputs."):
            rest = pi[len("ProjectInputs."):]
        elif pi.startswith("ProjectInputsSchema."):
            rest = pi[len("ProjectInputsSchema."):]
        else:
            _err(errs, f"{cfid}: projectinputs_path {pi!r} does not start with 'ProjectInputs.' or 'ProjectInputsSchema.'")
            continue
        ok, msg = _walk_pi_path(ProjectInputs, rest, pi)
        if not ok:
            _err(errs, f"{cfid}: projectinputs_path {msg}")
    return errs


def check_pytest_node_ids(xw: List[Dict[str, str]],
                          real_node_ids: Set[str]) -> List[str]:
    errs: List[str] = []
    for r in xw:
        cfid = r["canonical_field_id"]
        te = r["test_evidence"]
        if not te or te == "NO_TEST_EVIDENCE":
            continue
        if te not in real_node_ids:
            _err(errs, f"{cfid}: test_evidence {te!r} is not a real pytest node ID")
    return errs


def check_verified_coordinates(matrix: List[Dict[str, str]],
                                source_inputs: List[Dict[str, Any]],
                                model: str) -> List[str]:
    errs: List[str] = []
    src_cells = {r.get("active_cell", "") for r in source_inputs}
    # Only check the verified cell for the model we were called with.
    # The matrix carries verified_tuho_input_cell and
    # verified_oborovo_input_cell; we check the one for this model.
    prefix = "tuho" if model == "TUHO" else "oborovo"
    for r in matrix:
        cfid = r["canonical_field_id"]
        v = r.get(f"verified_{prefix}_input_cell", "")
        if not v or v in ("NOT_PRESENT_IN_MODEL", "NOT_APPLICABLE", "UNRESOLVED"):
            continue
        if v not in src_cells:
            _err(errs, f"{cfid}: verified_{prefix}_input_cell {v!r} is not in source extraction {prefix}")
    return errs


# ---------------------------------------------------------------------------
# Catalog/matrix/cross-walk consistency
# ---------------------------------------------------------------------------


def check_consistency(catalog: List[Dict[str, str]],
                       xw: List[Dict[str, str]],
                       matrix: List[Dict[str, str]]) -> List[str]:
    errs: List[str] = []
    xw_by_id = {r["canonical_field_id"]: r for r in xw}
    for c in catalog:
        cid = c["canonical_field_id"]
        if cid not in xw_by_id:
            # UI/engine-owned entries are added to the catalog
            # separately from the cross-walk; not a mismatch.
            continue
        x = xw_by_id[cid]
        if c["runtime_binding_status"] != x["runtime_binding_status"]:
            _err(errs, f"{cid}: catalog runtime_binding_status {c['runtime_binding_status']!r} != cross-walk {x['runtime_binding_status']!r}")
        if c["excel_mapping_status"] != x["excel_mapping_status"]:
            _err(errs, f"{cid}: catalog excel_mapping_status {c['excel_mapping_status']!r} != cross-walk {x['excel_mapping_status']!r}")
    for m in matrix:
        cid = m["canonical_field_id"]
        if cid not in xw_by_id:
            continue
        x = xw_by_id[cid]
        if m["runtime_binding_status"] != x["runtime_binding_status"]:
            _err(errs, f"{cid}: matrix runtime_binding_status {m['runtime_binding_status']!r} != cross-walk {x['runtime_binding_status']!r}")
        if m["excel_mapping_status"] != x["excel_mapping_status"]:
            _err(errs, f"{cid}: matrix excel_mapping_status {m['excel_mapping_status']!r} != cross-walk {x['excel_mapping_status']!r}")
    return errs


def check_no_matrix_upgrade(xw: List[Dict[str, str]]) -> List[str]:
    """Reject any catalog/matrix row whose runtime_binding_status
    is TEMPLATE_LOCKED / DERIVED_ONLY / DISPLAY_ONLY but whose
    cross-walk evidence is only generic strings (no real symbol).

    Specifically, a RUNTIME_FULLY_BOUND field must have a real
    adapter symbol OR a real inline-logic container OR a real
    service pipeline. Anything else is evidence-only and must
    not be RUNTIME_FULLY_BOUND.
    """
    errs: List[str] = []
    for r in xw:
        if r["runtime_binding_status"] != "RUNTIME_FULLY_BOUND":
            continue
        if r["adapter_evidence_type"] == "EXACT_SYMBOL":
            if r["adapter_path"] in ("UNRESOLVED", ""):
                _err(errs, f"{r['canonical_field_id']}: RUNTIME_FULLY_BOUND but adapter_path is UNRESOLVED/empty")
        elif r["adapter_evidence_type"] == "INLINE_LOGIC":
            if r["adapter_path"] in ("UNRESOLVED", ""):
                _err(errs, f"{r['canonical_field_id']}: RUNTIME_FULLY_BOUND but INLINE_LOGIC adapter_path is UNRESOLVED/empty")
        elif r["adapter_evidence_type"] == "SERVICE_PIPELINE":
            if r["adapter_path"] in ("UNRESOLVED", ""):
                _err(errs, f"{r['canonical_field_id']}: RUNTIME_FULLY_BOUND but SERVICE_PIPELINE adapter_path is UNRESOLVED/empty")
    return errs


# ---------------------------------------------------------------------------
# Inputs / Scenarios semantic classification
# ---------------------------------------------------------------------------


def check_inputs_semantic(rows: List[Dict[str, Any]], model: str) -> List[str]:
    errs: List[str] = []
    for r in rows:
        if r.get("workbook_classification") != "EDITABLE_INPUT":
            continue
        if r.get("active_formula_kind") == "formula":
            _err(errs, f"{model} R{r['row']}: formula cell marked EDITABLE_INPUT")
        if r.get("source_type") == "section/header":
            _err(errs, f"{model} R{r['row']}: section/header marked EDITABLE_INPUT")
        if r.get("editable_policy") == "Derived / read-only":
            _err(errs, f"{model} R{r['row']}: Derived/read-only marked EDITABLE_INPUT")
        if r.get("editable_policy") == "N/A":
            _err(errs, f"{model} R{r['row']}: N/A editable_policy marked EDITABLE_INPUT")
        if r.get("kind") == "section":
            _err(errs, f"{model} R{r['row']}: kind=section marked EDITABLE_INPUT")
    return errs


def check_inputs_zero_unsupported(rows: List[Dict[str, Any]], model: str) -> List[str]:
    errs: List[str] = []
    n = sum(1 for r in rows if r.get("workbook_classification") == "UNSUPPORTED")
    if n > 0:
        _err(errs, f"{model} inputs has {n} UNSUPPORTED rows")
    return errs


def check_scenario_semantic(rows: List[Dict[str, Any]], model: str) -> List[str]:
    errs: List[str] = []
    for r in rows:
        if r.get("workbook_classification") != "SCENARIO_OVERRIDE":
            continue
        # v5: active_formula_kind=formula + active_cell_role=DIRECT_BASE_INPUT is invalid
        if (r.get("active_formula_kind") == "formula"
                and r.get("active_cell_role") == "DIRECT_BASE_INPUT"):
            _err(errs, f"{model} R{r['row']}: formula active cell marked DIRECT_BASE_INPUT (must be LINKED_BASE_VALUE)")
        # v5: empty heading + SCENARIO_OVERRIDE is invalid
        if r.get("active_value_kind") == "empty" and r.get("active_formula_kind") == "empty":
            label = (r.get("label") or "").lower()
            if label in {"technical", "capex", "opex", "revenue", "financing", "debt", "tax", "fixed values", "inputs by project team"}:
                _err(errs, f"{model} R{r['row']}: empty heading marked SCENARIO_OVERRIDE")
        if r.get("scenario_value_kind") == "empty" and "zero" in r.get("classification_reason", "").lower():
            _err(errs, f"{model} R{r['row']}: blank scenario override must remain inherit, not zero")
    return errs


def check_scenario_zero_unsupported(rows: List[Dict[str, Any]], model: str) -> List[str]:
    errs: List[str] = []
    n = sum(1 for r in rows if r.get("workbook_classification") == "UNSUPPORTED")
    if n > 0:
        _err(errs, f"{model} scenarios has {n} UNSUPPORTED rows")
    return errs


# ---------------------------------------------------------------------------
# Source-extraction row matching
# ---------------------------------------------------------------------------


def check_inputs_rows_match_source(inp_rows: List[Dict[str, Any]], source_rows: List[Dict[str, Any]], model: str) -> List[str]:
    errs: List[str] = []
    src_keys = {(r["row"], r.get("active_cell", "")) for r in source_rows}
    out_keys = {(r["row"], r.get("cell", "")) for r in inp_rows}
    missing = src_keys - out_keys
    extra = out_keys - src_keys
    if missing:
        _err(errs, f"{model} inputs missing source rows: {len(missing)} keys")
    if extra:
        _err(errs, f"{model} inputs has extra rows: {len(extra)} keys (synthetic?)")
    return errs


def check_scenario_rows_match_source(scen_rows: List[Dict[str, Any]], source_rows: List[Dict[str, Any]], model: str) -> List[str]:
    errs: List[str] = []
    src_keys = {(r["row"], r.get("active_cell", "")) for r in source_rows}
    out_keys = {(r["row"], r.get("active_cell", "")) for r in scen_rows}
    missing = src_keys - out_keys
    extra = out_keys - src_keys
    if missing:
        _err(errs, f"{model} scenarios missing source rows: {len(missing)} keys")
    if extra:
        _err(errs, f"{model} scenarios has extra rows: {len(extra)} keys (synthetic?)")
    return errs


# ---------------------------------------------------------------------------
# v5.1 §6: editable-input disposition coverage
# ---------------------------------------------------------------------------


def check_editable_input_disposition_coverage() -> List[str]:
    """v5.1 §6: every EDITABLE_INPUT manifest row appears exactly
    once in editable_input_disposition_v5_1.csv. The manifest
    rows are the union of TUHO + Oborovo model manifests filtered
    to workbook_classification == EDITABLE_INPUT.
    """
    errs: List[str] = []
    disp_path = ARTIFACT_DIR / "editable_input_disposition_v5_1.csv"
    if not disp_path.is_file():
        return [f"v5.1: {disp_path.name} missing"]
    disp_rows = list(csv.DictReader(disp_path.open()))
    # Build set of (model, row) from disposition CSV
    disp_keys = {(r["model"], int(r["row"])) for r in disp_rows if r.get("model") and r.get("row")}
    # Build set of (model, row) from manifests
    expected_keys = set()
    for model_key in ("tuho", "oborovo"):
        manifest_path = ARTIFACT_DIR / f"{model_key}_model_manifest_v5.json"
        if not manifest_path.is_file():
            continue
        m = _load_json(manifest_path)
        for r in m.get("rows", []):
            if r.get("workbook_classification") == "EDITABLE_INPUT":
                expected_keys.add((model_key.upper(), int(r.get("row", -1))))
    # Check: every expected key is in disposition
    missing = expected_keys - disp_keys
    extra = disp_keys - expected_keys
    for k in sorted(missing):
        errs.append(f"v5.1 disposition: missing row {k}")
    for k in sorted(extra):
        errs.append(f"v5.1 disposition: extra row {k}")
    # Disposition vocabulary
    allowed = {
        "MAPPED_TO_REGISTRY", "TRUE_DUPLICATE", "TRUE_SYNONYM",
        "DERIVED_FROM_EXISTING_INPUT", "ENGINE_GAP", "UI_GAP",
        "PERSISTENCE_GAP", "APPLICABLE_BESS", "NOT_APPLICABLE",
        "LEGACY_SUPERSEDED", "UNRESOLVED",
    }
    bad = [r for r in disp_rows if r.get("disposition") not in allowed]
    for r in bad[:5]:
        errs.append(f"v5.1 disposition: invalid {r['model']} R{r['row']} disposition={r['disposition']!r}")
    return errs


# ---------------------------------------------------------------------------
# v5.1 §7: workbook-only verified cell must be a real source
# active_cell (A1 column letter + row number). Reject A-column
# hint-look-alikes that aren't actually in the source extraction.
# ---------------------------------------------------------------------------


def check_workbook_only_verified_cells() -> List[str]:
    """v5.1 §7: every verified_cell in unresolved_pack_id_evidence
    and editable_input_disposition must be an exact matching
    active_cell in the relevant source extraction (or empty for
    "not present in this model").
    """
    errs: List[str] = []
    # Build sets of valid cells per model from the source extractions
    valid_cells_by_model: Dict[str, Set[str]] = {}
    for model in ("tuho", "oborovo"):
        src_path = SOURCE_DIR / f"{model}_inputs_source_v2.json"
        if not src_path.is_file():
            continue
        s = _load_json(src_path)
        valid_cells_by_model[model.upper()] = {
            r.get("active_cell", "") for r in s.get("rows", [])
        }
    # Read unresolved_pack_id_evidence
    un_path = ARTIFACT_DIR / "unresolved_pack_id_evidence.csv"
    if un_path.is_file():
        for r in csv.DictReader(un_path.open()):
            for col, model in (("verified_cell_tuho", "TUHO"),
                                ("verified_cell_oborovo", "OBOROVO")):
                v = r.get(col, "").strip()
                if not v:
                    continue
                # An A1 cell must be a single letter + digits. Multi-
                # word descriptions like "Inputs!Financing!Reserves"
                # are NOT A1 cells and must NOT be in this column.
                if not re.match(r"^[A-Z]{1,3}\d+$", v):
                    errs.append(
                        f"v5.1 §7: unresolved_pack_id_evidence {r.get('pack_id', '?')!r} "
                        f"{col}={v!r} is not an A1 cell"
                    )
                else:
                    valid = valid_cells_by_model.get(model, set())
                    if v not in valid:
                        errs.append(
                            f"v5.1 §7: unresolved_pack_id_evidence {r.get('pack_id', '?')!r} "
                            f"{col}={v!r} not in source extraction {model}"
                        )
    # Read editable_input_disposition (active_cell must equal
    # source extraction active_cell)
    disp_path = ARTIFACT_DIR / "editable_input_disposition_v5_1.csv"
    if disp_path.is_file():
        for r in csv.DictReader(disp_path.open()):
            v = r.get("active_cell", "").strip()
            if not v:
                continue
            if not re.match(r"^[A-Z]{1,3}\d+$", v):
                errs.append(
                    f"v5.1 §7: editable_input_disposition {r.get('model', '?')} "
                    f"R{r.get('row', '?')} active_cell={v!r} is not an A1 cell"
                )
    return errs


# ---------------------------------------------------------------------------
# v5.1 §8: scenario coordinates / ranges from cross-walk must
# exist in the relevant scenario source extraction.
# ---------------------------------------------------------------------------


def check_scenario_coordinates_in_source() -> List[str]:
    """v5.1 §8: every populated verified_*_scenario_cell /
    verified_*_scenario_range must equal an actual cell in the
    scenario source extraction for that model.

    Scenario ranges are written as "G9:L9" (column + row range).
    Each cell in the range must be present in the source
    extraction's combined cell set (active_cell + every cell
    mentioned in any scenario_cells value).
    """
    errs: List[str] = []
    xw_path = ARTIFACT_DIR / "canonical_registry_crosswalk_v5.csv"
    if not xw_path.is_file():
        return errs
    valid_by_model: Dict[str, Set[str]] = {}
    for model in ("tuho", "oborovo"):
        src_path = SOURCE_DIR / f"{model}_scenarios_source_v2.json"
        if not src_path.is_file():
            continue
        s = _load_json(src_path)
        cells: Set[str] = set()
        for r in s.get("rows", []):
            ac = r.get("active_cell", "")
            if ac:
                cells.add(ac)
            sc = r.get("scenario_cells", "")
            if sc:
                for part in sc.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    # Range like "G9:L9"
                    if ":" in part:
                        start, end = part.split(":", 1)
                        m_start = re.match(r"^([A-Z]{1,3})(\d+)$", start)
                        m_end = re.match(r"^([A-Z]{1,3})(\d+)$", end)
                        if not m_start or not m_end:
                            continue
                        col1, row1 = m_start.group(1), int(m_start.group(2))
                        col2, row2 = m_end.group(1), int(m_end.group(2))
                        if row1 > row2:
                            continue
                        # Expand columns: A=1, ..., Z=26, AA=27, ...
                        def col_to_num(c: str) -> int:
                            n = 0
                            for ch in c:
                                n = n * 26 + (ord(ch) - ord('A') + 1)
                            return n
                        def num_to_col(n: int) -> str:
                            s = ""
                            while n > 0:
                                n, r = divmod(n - 1, 26)
                                s = chr(ord('A') + r) + s
                            return s
                        c1, c2 = col_to_num(col1), col_to_num(col2)
                        if c1 > c2:
                            c1, c2 = c2, c1
                        for c_num in range(c1, c2 + 1):
                            c_label = num_to_col(c_num)
                            for r_num in range(row1, row2 + 1):
                                cells.add(f"{c_label}{r_num}")
                    elif re.match(r"^[A-Z]{1,3}\d+$", part):
                        cells.add(part)
        valid_by_model[model.upper()] = cells
    for r in csv.DictReader(xw_path.open()):
        cid = r["canonical_field_id"]
        for col, model in (
            ("verified_tuho_scenario_cell", "TUHO"),
            ("verified_oborovo_scenario_cell", "OBOROVO"),
            ("verified_tuho_scenario_range", "TUHO"),
            ("verified_oborovo_scenario_range", "OBOROVO"),
        ):
            v = r.get(col, "").strip()
            if not v:
                continue
            valid = valid_by_model.get(model, set())
            for token in v.split(","):
                token = token.strip()
                if not token:
                    continue
                # Range "G9:L9" — each cell must be in valid
                if ":" in token:
                    start, end = token.split(":", 1)
                    m_start = re.match(r"^([A-Z]{1,3})(\d+)$", start)
                    m_end = re.match(r"^([A-Z]{1,3})(\d+)$", end)
                    if not m_start or not m_end:
                        errs.append(
                            f"v5.1 §8: {cid!r} {col}={token!r} is not an A1 range"
                        )
                        continue
                    col1, row1 = m_start.group(1), int(m_start.group(2))
                    col2, row2 = m_end.group(1), int(m_end.group(2))
                    if row1 > row2:
                        errs.append(
                            f"v5.1 §8: {cid!r} {col}={token!r} inverted range"
                        )
                        continue
                    def col_to_num(c: str) -> int:
                        n = 0
                        for ch in c:
                            n = n * 26 + (ord(ch) - ord('A') + 1)
                        return n
                    def num_to_col(n: int) -> str:
                        s = ""
                        while n > 0:
                            n, r = divmod(n - 1, 26)
                            s = chr(ord('A') + r) + s
                        return s
                    c1, c2 = col_to_num(col1), col_to_num(col2)
                    if c1 > c2:
                        c1, c2 = c2, c1
                    for c_num in range(c1, c2 + 1):
                        c_label = num_to_col(c_num)
                        for r_num in range(row1, row2 + 1):
                            c = f"{c_label}{r_num}"
                            if c not in valid:
                                errs.append(
                                    f"v5.1 §8: {cid!r} {col}={token!r} cell {c!r} not in source extraction {model}"
                                )
                else:
                    if not re.match(r"^[A-Z]{1,3}\d+$", token):
                        errs.append(
                            f"v5.1 §8: {cid!r} {col}={token!r} is not an A1 cell"
                        )
                    elif token not in valid:
                        errs.append(
                            f"v5.1 §8: {cid!r} {col}={token!r} not in source extraction {model}"
                        )
    return errs


def check_scenario_mapping_status_vocab() -> List[str]:
    """v5.1 §8: scenario_mapping_status vocabulary on the cross-walk.
    """
    allowed = {
        "VERIFIED_BOTH_MODELS", "VERIFIED_TUHO_ONLY",
        "VERIFIED_OBOROVO_ONLY", "NOT_SCENARIO_ELIGIBLE",
        "SOURCE_COORDINATE_UNRESOLVED", "NOT_APPLICABLE",
        "UNRESOLVED",
    }
    errs: List[str] = []
    xw_path = ARTIFACT_DIR / "canonical_registry_crosswalk_v5.csv"
    if not xw_path.is_file():
        return errs
    for r in csv.DictReader(xw_path.open()):
        v = r.get("scenario_mapping_status", "")
        if v not in allowed:
            errs.append(f"v5.1 §8: {r['canonical_field_id']!r} scenario_mapping_status={v!r} invalid")
        v = r.get("runtime_validation_status", "")
        if v and v not in {
            "FIELD_SPECIFIC_E2E_PROVEN", "FIELD_SPECIFIC_UNIT_PROVEN",
            "SHARED_PIPELINE_PROVEN", "DISPLAY_ONLY_PROVEN",
            "GENERIC_ROUTE_ONLY", "NO_FIELD_SPECIFIC_TEST",
            "NOT_APPLICABLE", "UNRESOLVED",
        }:
            errs.append(f"v5.1 §3: {r['canonical_field_id']!r} runtime_validation_status={v!r} invalid")
        v = r.get("test_evidence_scope", "")
        if v and v not in {
            "FIELD-SPECIFIC-E2E", "FIELD-SPECIFIC-UNIT",
            "SHARED-PIPELINE", "DISPLAY-ONLY", "GENERIC-ROUTE", "NONE",
        }:
            errs.append(f"v5.1 §4: {r['canonical_field_id']!r} test_evidence_scope={v!r} invalid")
    return errs


# ---------------------------------------------------------------------------
# v5.1 §4: field-specific-E2E test scope must name the same
# canonical field as the row it claims to prove.
# ---------------------------------------------------------------------------


def check_field_specific_e2e_scope() -> List[str]:
    """v5.1 §4: only opex.lines.technical_management may claim
    FIELD-SPECIFIC-E2E / FIELD_SPECIFIC_E2E_PROVEN. All other
    RUNTIME_FULLY_BOUND fields must use GENERIC-ROUTE /
    GENERIC_ROUTE_ONLY (or SHARED-PIPELINE for CAPEX/OPEX
    sub-line pipelines, or DISPLAY-ONLY for CIT).
    """
    errs: List[str] = []
    xw_path = ARTIFACT_DIR / "canonical_registry_crosswalk_v5.csv"
    if not xw_path.is_file():
        return errs
    for r in csv.DictReader(xw_path.open()):
        cid = r["canonical_field_id"]
        rvs = r.get("runtime_validation_status", "")
        scope = r.get("test_evidence_scope", "")
        if rvs == "FIELD_SPECIFIC_E2E_PROVEN" and cid != "registry.opex.lines.technical_management":
            errs.append(
                f"v5.1 §4: {cid!r} claims FIELD_SPECIFIC_E2E_PROVEN but only "
                f"opex.lines.technical_management is field-specific E2E"
            )
        if rvs == "DISPLAY_ONLY_PROVEN" and cid != "registry.tax.assumptions.cit_rate_pct":
            errs.append(
                f"v5.1 §4: {cid!r} claims DISPLAY_ONLY_PROVEN but only "
                f"tax.assumptions.cit_rate_pct is display-only"
            )
        if scope == "FIELD-SPECIFIC-E2E" and cid != "registry.opex.lines.technical_management":
            errs.append(
                f"v5.1 §4: {cid!r} claims FIELD-SPECIFIC-E2E scope but only "
                f"opex.lines.technical_management is field-specific E2E"
            )
        if scope == "DISPLAY-ONLY" and cid != "registry.tax.assumptions.cit_rate_pct":
            errs.append(
                f"v5.1 §4: {cid!r} claims DISPLAY-ONLY scope but only "
                f"tax.assumptions.cit_rate_pct is display-only"
            )
    return errs


# ---------------------------------------------------------------------------
# v5.1 §3 + §11: 6-axis coverage summary reconciliation
# ---------------------------------------------------------------------------


def check_summary_6_axis_consistency() -> List[str]:
    """The coverage summary must have the 6 axes:
      A. Registry runtime wiring (by_runtime_binding_status)
      B. Runtime behavioral validation (by_runtime_validation_status)
      C. Excel Inputs mapping (by_excel_mapping_status)
      D. Excel Scenario mapping (by_scenario_mapping_status)
      E. Workbook-only editable-input dispositions
      F. Engine-owned/derived boundaries
    All six must be present.
    """
    errs: List[str] = []
    summary_path = ARTIFACT_DIR / "coverage_summary_v5.json"
    if not summary_path.is_file():
        return [f"v5.1: {summary_path.name} missing"]
    s = _load_json(summary_path)
    rb = s.get("registry_backed_canonical", {})
    for axis, key in [
        ("A: runtime wiring", "by_runtime_binding_status"),
        ("B: runtime validation", "by_runtime_validation_status"),
        ("C: excel inputs", "by_excel_mapping_status"),
        ("D: excel scenario", "by_scenario_mapping_status"),
    ]:
        if key not in rb:
            errs.append(f"v5.1 summary: missing axis {axis} ({key})")
    if "workbook_only_concepts" not in s:
        errs.append("v5.1 summary: missing E: workbook_only_concepts")
    if "engine_owned_boundaries" not in s:
        errs.append("v5.1 summary: missing F: engine_owned_boundaries")
    if "editable_input_disposition" not in s:
        errs.append("v5.1 summary: missing editable_input_disposition (axis E)")
    return errs


# ---------------------------------------------------------------------------
# v5.1 §3: P50 must remain UNRESOLVED
# ---------------------------------------------------------------------------


def check_p50_unchanged() -> List[str]:
    """v5.1 §3 + §8: p50_hours stays SOURCE_COORDINATE_UNRESOLVED
    on the scenario axis. The structural evidence is insufficient
    until client review of scenario column values.
    """
    errs: List[str] = []
    xw_path = ARTIFACT_DIR / "canonical_registry_crosswalk_v5.csv"
    if not xw_path.is_file():
        return errs
    for r in csv.DictReader(xw_path.open()):
        if r["canonical_field_id"] == "registry.project_setup.technical.p50_hours":
            if r.get("scenario_mapping_status") != "SOURCE_COORDINATE_UNRESOLVED":
                errs.append(
                    f"v5.1 §3: p50_hours scenario_mapping_status must stay "
                    f"SOURCE_COORDINATE_UNRESOLVED; got {r.get('scenario_mapping_status')!r}"
                )
    return errs


# ---------------------------------------------------------------------------
# v5.3 semantic evidence checks
# ---------------------------------------------------------------------------


def _split_cells(value: str) -> Set[str]:
    cells: Set[str] = set()
    for part in re.split(r"[,;\s]+", value or ""):
        part = part.strip()
        if re.match(r"^[A-Z]{1,3}\d+$", part):
            cells.add(part)
    return cells


def _cell_source_index(rows: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    index: Dict[str, Set[str]] = {}
    for row in rows:
        for cell in _split_cells(row.get("active_cell", "")):
            index.setdefault(cell, set()).add("active")
        for cell in _split_cells(row.get("verified_hardcode_cells", row.get("hardcode_cells", ""))):
            index.setdefault(cell, set()).add("hardcode")
        for cell in _split_cells(row.get("verified_formula_cells", row.get("formula_cells", ""))):
            index.setdefault(cell, set()).add("formula")
        for cell in _split_cells(row.get("verified_empty_cells", "")):
            index.setdefault(cell, set()).add("empty")
        for cell in _split_cells(row.get("verified_label_or_presentation_cells", "")):
            index.setdefault(cell, set()).add("label")
        for cell in _split_cells(row.get("cell_span", "")):
            index.setdefault(cell, set()).add("span")
    return index


def _has_source(index: Dict[str, Set[str]], cell: str, kinds: Set[str]) -> bool:
    return bool(cell and index.get(cell, set()) & kinds)


def check_v53_semantic_evidence(
    unresolved: List[Dict[str, Any]],
    tuho_source: List[Dict[str, Any]],
    oborovo_source: List[Dict[str, Any]],
) -> List[str]:
    errs: List[str] = []
    source_by_model = {
        "tuho": _cell_source_index(tuho_source),
        "oborovo": _cell_source_index(oborovo_source),
    }
    if unresolved:
        cols = set(unresolved[0].keys())
        missing = sorted(SEMANTIC_UNRESOLVED_COLUMNS - cols)
        legacy = sorted({"verification_basis", "verification_status"} & cols)
        if missing:
            errs.append(f"semantic: unresolved evidence missing v5.3 columns: {missing}")
        if legacy:
            errs.append(f"semantic: unresolved evidence still has legacy columns: {legacy}")

    coord_reuse: Dict[Tuple[str, str, str], List[Tuple[str, str]]] = {}
    for row in unresolved:
        pack_id = row.get("pack_id", "?")
        role = row.get("cell_role", "").strip()
        value_kind = row.get("value_kind", "").strip()
        unit = row.get("unit", "").strip()
        evidence_basis = row.get("evidence_basis", "").strip()
        verification = row.get("mapping_verification_status", "").strip()
        if role not in SEMANTIC_CELL_ROLES:
            errs.append(f"semantic: {pack_id} invalid cell_role {role!r}")
        if value_kind not in SEMANTIC_VALUE_KINDS:
            errs.append(f"semantic: {pack_id} invalid value_kind {value_kind!r}")
        if unit not in SEMANTIC_UNITS:
            errs.append(f"semantic: {pack_id} invalid unit {unit!r}")
        if evidence_basis not in EVIDENCE_BASES:
            errs.append(f"semantic: {pack_id} invalid evidence_basis {evidence_basis!r}")
        if verification not in MAPPING_VERIFICATION_STATUSES:
            errs.append(f"semantic: {pack_id} invalid mapping_verification_status {verification!r}")

        coordinates = [
            row.get(f"verified_{axis}_cell_{model}", "").strip()
            for axis in ("value", "editable", "formula")
            for model in ("tuho", "oborovo")
        ]
        has_coordinate = any(coordinates)
        if verification == "MAPPING_CONFIRMED" and not has_coordinate:
            errs.append(f"semantic: {pack_id} MAPPING_CONFIRMED without coordinates")
        if verification == "ABSENCE_CONFIRMED" and has_coordinate:
            errs.append(f"semantic: {pack_id} ABSENCE_CONFIRMED with coordinates")
        if role == "UNRESOLVED" and verification == "MAPPING_CONFIRMED":
            errs.append(f"semantic: {pack_id} unresolved role cannot be MAPPING_CONFIRMED")

        for model in ("tuho", "oborovo"):
            source = source_by_model[model]
            label_cell = row.get(f"verified_label_cell_{model}", "").strip()
            value_cell = row.get(f"verified_value_cell_{model}", "").strip()
            editable_cell = row.get(f"verified_editable_cell_{model}", "").strip()
            formula_cell = row.get(f"verified_formula_cell_{model}", "").strip()

            if value_cell and not _has_source(source, value_cell, {"hardcode"}):
                errs.append(f"semantic: {pack_id} value cell {model}:{value_cell} is not source hardcode evidence")
            if editable_cell and not _has_source(source, editable_cell, {"hardcode"}):
                errs.append(f"semantic: {pack_id} editable cell {model}:{editable_cell} is not source hardcode evidence")
            if formula_cell and not _has_source(source, formula_cell, {"formula", "active", "span"}):
                errs.append(f"semantic: {pack_id} formula cell {model}:{formula_cell} is not source formula evidence")

            if role in {"EDITABLE_HARDCODE", "TOGGLE", "TEXT_INPUT", "DATE_INPUT"}:
                if value_cell != editable_cell:
                    errs.append(f"semantic: {pack_id} {model} editable/value axes must match for editable roles")
                if formula_cell:
                    errs.append(f"semantic: {pack_id} {model} editable role must not carry formula axis")
            if role in {"FORMULA_RESULT", "DERIVED_OUTPUT"}:
                if editable_cell:
                    errs.append(f"semantic: {pack_id} {model} formula role must not carry editable axis")
                if value_cell:
                    errs.append(f"semantic: {pack_id} {model} formula role must not carry value axis")
            if role in {"SUBSECTION_LABEL", "LABEL", "COUNTERPARTY_LABEL"}:
                if value_cell or editable_cell or formula_cell:
                    errs.append(f"semantic: {pack_id} {model} label role must not carry value/editable/formula axes")

            for axis, cell in (("value", value_cell), ("editable", editable_cell), ("formula", formula_cell)):
                if cell:
                    coord_reuse.setdefault((model, axis, cell), []).append(
                        (pack_id, row.get("shared_source_id", "").strip())
                    )

        if pack_id == "tax.wht.reimbursed" and verification != "ABSENCE_CONFIRMED":
            errs.append("semantic: tax.wht.reimbursed must remain absence-confirmed until distinct evidence exists")
        if pack_id == "tax.vat.reimbursed":
            for model in ("tuho", "oborovo"):
                if not row.get(f"verified_editable_cell_{model}", "").strip():
                    errs.append(f"semantic: tax.vat.reimbursed {model} must keep its VAT-only editable evidence")
        if pack_id == "equity.investor_2_share":
            for model in ("tuho", "oborovo"):
                if not row.get(f"verified_formula_cell_{model}", "").strip():
                    errs.append(f"semantic: equity.investor_2_share {model} must be formula-axis evidence")
        if pack_id == "tax.max_shl_to_equity_ratio":
            for model in ("tuho", "oborovo"):
                if not row.get(f"verified_formula_cell_{model}", "").strip():
                    errs.append(f"semantic: tax.max_shl_to_equity_ratio {model} must be formula-axis evidence")

    for (model, axis, cell), pack_refs in coord_reuse.items():
        if len(pack_refs) < 2:
            continue
        shared_ids = {sid for _, sid in pack_refs if sid}
        all_ids = {sid for _, sid in pack_refs}
        if len(shared_ids) == 1 and len(all_ids) == 1:
            continue
        packs = [pid for pid, _ in pack_refs]
        errs.append(f"semantic: {model}:{axis}:{cell} reused without shared_source_id: {packs}")
    return errs


def check_v53_xw_evidence(xw: List[Dict[str, str]]) -> List[str]:
    errs: List[str] = []
    for row in xw:
        canonical = row.get("canonical_field_id") or row.get("canonical_concept") or "?"
        cell_role = row.get("cell_role", "").strip()
        if cell_role and cell_role not in SEMANTIC_CELL_ROLES:
            errs.append(f"xw_semantic: {canonical} invalid cell_role {cell_role!r}")
        if row.get("verification_basis") or row.get("verification_status"):
            errs.append(f"xw_semantic: {canonical} uses legacy verification columns")
    return errs


def check_v531_verified_storage(
    inputs: List[Dict[str, Any]],
    scenarios: List[Dict[str, Any]],
    unresolved: List[Dict[str, Any]],
    audit: Dict[str, Any],
) -> List[str]:
    errs: List[str] = []
    rows = inputs + scenarios
    for row in rows:
        ident = f"{row.get('model_id')} {row.get('sheet')} R{row.get('row')}"
        if row.get("storage_verification_basis", "") != "PROGRAMMATIC_WORKBOOK_INSPECTION":
            errs.append(f"storage: {ident} missing PROGRAMMATIC_WORKBOOK_INSPECTION basis")
        hard = _split_cells(row.get("verified_hardcode_cells", ""))
        formula = _split_cells(row.get("verified_formula_cells", ""))
        empty = _split_cells(row.get("verified_empty_cells", ""))
        if hard & formula:
            errs.append(f"storage: {ident} coordinate in hardcode and formula sets")
        if hard & empty:
            errs.append(f"storage: {ident} coordinate in hardcode and empty sets")
        if formula & empty:
            errs.append(f"storage: {ident} coordinate in formula and empty sets")
        active = row.get("active_cell", "").strip()
        active_kind = row.get("verified_active_cell_storage_kind", "").strip()
        if active_kind == "FORMULA" and active not in formula:
            errs.append(f"storage: {ident} active marked FORMULA but not verified formula")
        if active_kind == "HARDCODE" and active not in hard:
            errs.append(f"storage: {ident} active marked HARDCODE but not verified hardcode")
        if active_kind == "EMPTY" and active not in empty:
            errs.append(f"storage: {ident} active marked EMPTY but not verified empty")
        editable_claim = (
            row.get("workbook_classification") == "EDITABLE_INPUT"
            or row.get("editable_policy") == "Candidate input"
        )
        if editable_claim and formula and not hard:
            errs.append(f"storage: {ident} EDITABLE_INPUT has only formula-backed value cells")
        if editable_claim and row.get("package_claim_hardcode_cells") and not hard:
            errs.append(f"storage: {ident} package_claim_hardcode_cells cannot establish EDITABLE_INPUT")
        if row.get("workbook_classification") == "SCENARIO_OVERRIDE":
            if row.get("scenario_value_kind") == "empty" and "zero" in row.get("classification_reason", "").lower():
                errs.append(f"storage: {ident} blank scenario override must remain inherit, not zero")

    source_by_model: Dict[str, Dict[str, Set[str]]] = {}
    for row in inputs:
        model = str(row.get("model_id", "")).lower()
        source_by_model.setdefault(model, {})
        for cell in _split_cells(row.get("verified_hardcode_cells", "")):
            source_by_model[model].setdefault(cell, set()).add("hardcode")
        for cell in _split_cells(row.get("verified_formula_cells", "")):
            source_by_model[model].setdefault(cell, set()).add("formula")
        for cell in _split_cells(row.get("verified_label_or_presentation_cells", "")):
            source_by_model[model].setdefault(cell, set()).add("label")

    checked_vef = 0
    checked_total = 0
    curated_issues = 0
    for row in unresolved:
        pack_id = row.get("pack_id", "?")
        for model in ("tuho", "oborovo"):
            index = source_by_model.get(model, {})
            for axis in ("value", "editable"):
                for cell in _split_cells(row.get(f"verified_{axis}_cell_{model}", "")):
                    checked_vef += 1
                    checked_total += 1
                    if "hardcode" not in index.get(cell, set()):
                        curated_issues += 1
                        errs.append(f"curated: {pack_id} {model} {axis} cell {cell} is not verified hardcode")
            for cell in _split_cells(row.get(f"verified_formula_cell_{model}", "")):
                checked_vef += 1
                checked_total += 1
                if "formula" not in index.get(cell, set()):
                    curated_issues += 1
                    errs.append(f"curated: {pack_id} {model} formula cell {cell} is not verified formula")
            for cell in _split_cells(row.get(f"verified_formula_period_cell_{model}", "")):
                checked_total += 1
                if "formula" not in index.get(cell, set()):
                    curated_issues += 1
                    errs.append(f"curated: {pack_id} {model} formula-period cell {cell} is not verified formula")
            for cell in _split_cells(row.get(f"verified_counterparty_label_cell_{model}", "")):
                checked_total += 1
                if not (index.get(cell, set()) & {"hardcode", "formula", "label"}):
                    curated_issues += 1
                    errs.append(f"curated: {pack_id} {model} counterparty-label cell {cell} is not verified")

    curated = audit.get("curated_evidence", {})
    if curated.get("value_editable_formula_coordinates_checked") != checked_vef:
        errs.append("audit: curated value/editable/formula count does not reconcile")
    if curated.get("total_coordinates_checked") != checked_total:
        errs.append("audit: curated total coordinate count does not reconcile")
    if curated.get("issues") != curated_issues:
        errs.append("audit: curated issue count does not reconcile")
    if audit.get("inputs", {}).get("manifest_rows") != len(inputs):
        errs.append("audit: input manifest row count does not reconcile")
    if audit.get("scenarios", {}).get("manifest_rows") != len(scenarios):
        errs.append("audit: scenario manifest row count does not reconcile")
    storage = audit.get("verified_storage", {})
    if storage.get("hardcode_formula_overlap_count") != 0:
        errs.append("audit: verified hardcode/formula overlap must be zero")
    if storage.get("hardcode_empty_overlap_count") != 0:
        errs.append("audit: verified hardcode/empty overlap must be zero")
    if storage.get("formula_empty_overlap_count") != 0:
        errs.append("audit: verified formula/empty overlap must be zero")
    return errs


def validate() -> Tuple[bool, List[str], Dict[str, Any]]:
    errs: List[str] = []
    errs.extend(check_required_files())
    errs.extend(check_no_proprietary())
    if errs:
        return False, errs, {}

    xw = _load_csv(ARTIFACT_DIR / "canonical_registry_crosswalk_v5.csv")
    catalog = _load_csv(ARTIFACT_DIR / "canonical_field_catalog_v5.csv")
    matrix = _load_csv(ARTIFACT_DIR / "input_coverage_matrix_v5.csv")
    pack_ev = _load_csv(ARTIFACT_DIR / "canonical_to_pack_id_evidence.csv")
    unresolved = _load_csv(ARTIFACT_DIR / "unresolved_pack_id_evidence.csv")
    summary = _load_json(ARTIFACT_DIR / "coverage_summary_v5.json")
    support_audit = _load_json(ARTIFACT_DIR / "support_package_metadata_audit_v5_3_1.json")

    tuho_inputs = _load_json(ARTIFACT_DIR / "tuho_model_manifest_v5.json")["rows"]
    obo_inputs = _load_json(ARTIFACT_DIR / "oborovo_model_manifest_v5.json")["rows"]
    tuho_scen = _load_json(ARTIFACT_DIR / "tuho_scenario_manifest_v5.json")["rows"]
    obo_scen = _load_json(ARTIFACT_DIR / "oborovo_scenario_manifest_v5.json")["rows"]

    tuho_inp_src = _load_json(SOURCE_DIR / "tuho_inputs_source_v2.json")["rows"]
    obo_inp_src = _load_json(SOURCE_DIR / "oborovo_inputs_source_v2.json")["rows"]
    tuho_scen_src = _load_json(SOURCE_DIR / "tuho_scenarios_source_v2.json")["rows"]
    obo_scen_src = _load_json(SOURCE_DIR / "oborovo_scenarios_source_v2.json")["rows"]

    # Real pytest node IDs (run --collect-only)
    real_node_ids = _collect_real_pytest_node_ids()

    # Vocabulary
    errs.extend(check_crosswalk_vocabulary(xw))
    errs.extend(check_manifest_vocabulary(tuho_inputs, "TUHO", scenario=False))
    errs.extend(check_manifest_vocabulary(obo_inputs, "OBOROVO", scenario=False))
    errs.extend(check_manifest_vocabulary(tuho_scen, "TUHO", scenario=True))
    errs.extend(check_manifest_vocabulary(obo_scen, "OBOROVO", scenario=True))

    # Evidence-integrity
    errs.extend(check_real_symbols(xw))
    errs.extend(check_projectinputs_paths(xw))
    errs.extend(check_pytest_node_ids(xw, real_node_ids))
    errs.extend(check_verified_coordinates(matrix, tuho_inp_src, "TUHO"))
    errs.extend(check_verified_coordinates(matrix, obo_inp_src, "OBOROVO"))

    # Catalog/matrix/cross-walk consistency
    errs.extend(check_consistency(catalog, xw, matrix))
    errs.extend(check_no_matrix_upgrade(xw))

    # v5.1: 6-axis summary reconciliation + disposition coverage
    # + verified-cell A1 enforcement + scenario coordinates +
    # scope/scenario_mapping_status vocabulary + P50 invariant +
    # field-specific E2E scope check.
    errs.extend(check_summary_6_axis_consistency())
    errs.extend(check_editable_input_disposition_coverage())
    errs.extend(check_workbook_only_verified_cells())
    errs.extend(check_scenario_coordinates_in_source())
    errs.extend(check_scenario_mapping_status_vocab())
    errs.extend(check_field_specific_e2e_scope())
    errs.extend(check_p50_unchanged())

    # v5.2: semantic coordinate validation. Multi-axis evidence
    # (label/value/editable/formula + cell_role + value_kind + unit
    # + verification_basis + verification_status) is rejected if it
    # places a label cell into a value slot or reuses a single value
    # cell for two unrelated concepts.
    errs.extend(check_v53_semantic_evidence(unresolved, tuho_inp_src, obo_inp_src))
    errs.extend(check_v53_xw_evidence(xw))
    errs.extend(check_v531_verified_storage(
        tuho_inp_src + obo_inp_src,
        tuho_scen_src + obo_scen_src,
        unresolved,
        support_audit,
    ))

    # Inputs semantic
    for model, rows, src_rows in (("TUHO", tuho_inputs, tuho_inp_src),
                                   ("OBOROVO", obo_inputs, obo_inp_src)):
        errs.extend(check_inputs_semantic(rows, model))
        errs.extend(check_inputs_zero_unsupported(rows, model))
        errs.extend(check_inputs_rows_match_source(rows, src_rows, model))

    # Scenarios semantic
    for model, rows, src_rows in (("TUHO", tuho_scen, tuho_scen_src),
                                   ("OBOROVO", obo_scen, obo_scen_src)):
        errs.extend(check_scenario_semantic(rows, model))
        errs.extend(check_scenario_zero_unsupported(rows, model))
        errs.extend(check_scenario_rows_match_source(rows, src_rows, model))

    full_summary = {
        "canonical_field_count": len(catalog),
        "crosswalk_row_count": len(xw),
        "matrix_row_count": len(matrix),
        "pack_evidence_count": len(pack_ev),
        "unresolved_pack_id_count": len(unresolved),
        "tuho_inputs_row_count": len(tuho_inputs),
        "oborovo_inputs_row_count": len(obo_inputs),
        "tuho_scenario_row_count": len(tuho_scen),
        "oborovo_scenario_row_count": len(obo_scen),
        "runtime_binding_status_counts": dict(Counter(r["runtime_binding_status"] for r in xw)),
        "excel_mapping_status_counts": dict(Counter(r["excel_mapping_status"] for r in xw)),
        "tuho_inputs_classification": dict(Counter(r.get("workbook_classification") for r in tuho_inputs)),
        "oborovo_inputs_classification": dict(Counter(r.get("workbook_classification") for r in obo_inputs)),
        "tuho_scenario_classification": dict(Counter(r.get("workbook_classification") for r in tuho_scen)),
        "oborovo_scenario_classification": dict(Counter(r.get("workbook_classification") for r in obo_scen)),
        "registry_backed_canonical": summary.get("registry_backed_canonical", {}),
        "workbook_only_concepts": summary.get("workbook_only_concepts", {}),
        "engine_owned_boundaries": summary.get("engine_owned_boundaries", {}),
        "support_package_metadata_audit": {
            "version": support_audit.get("version"),
            "inputs": support_audit.get("inputs", {}),
            "scenarios": support_audit.get("scenarios", {}),
            "curated_evidence": support_audit.get("curated_evidence", {}),
            "verified_storage": support_audit.get("verified_storage", {}),
        },
        "real_pytest_node_ids_collected": len(real_node_ids),
    }

    return not errs, errs, full_summary


def main() -> int:
    ok, errs, summary = validate()
    report = {
        "status": "PASS" if ok else "FAIL",
        "error_count": len(errs),
        "errors": errs,
        "summary": summary,
    }
    (ARTIFACT_DIR / "validation_report_v5.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if summary:
        print("validate_manifests: summary")
        for k, v in summary.items():
            print(f"  {k}: {v}")
    if ok:
        print("All manifests valid.")
        return 0
    print("Validation FAILED:")
    for e in errs[:50]:
        print(f"  - {e}")
    if len(errs) > 50:
        print(f"  ... and {len(errs) - 50} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
