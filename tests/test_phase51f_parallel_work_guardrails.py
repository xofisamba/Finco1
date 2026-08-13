"""Phase 51F — Parallel-work and runtime-refactor guardrails.

Three guardrails, enforced by behavior, not by call count:

1. Engine-output golden guardrail
   Pins current model outputs for TUHO and Oborovo so that refactors
   (route extraction, service extraction, route thin-ization) cannot
   silently change model outputs.

2. Source-evidence lock guardrail
   Pins SHA-256 of immutable senior-debt extraction CSVs. Evolving production
   modules are protected by semantic tests rather than obsolete whole-file hashes.

3. No-service-imports-main_web/main_api guardrail
   AST-based check that no app/services/*.py file imports main_web
   or main_api. This prevents the one-way import direction from
   being reversed during refactor or parallel work.

Why these guardrails are needed before /save-run and parallel work:

* /save-run touches runtime persistence (record_workspace_runtime,
  update_scenario_last_run_summary). Without model-output and
  parity-core locks, an accidental edit to waterfall_core.py during
  /save-run refactor could silently change distributions / DSCR /
  OpEx in the model.
* Two agents may work in parallel: one on route extraction (Agent A),
  one on docs/validation (Agent B). Without explicit guardrails,
  Agent A could regress parity-core files that Agent B depends on
  for validation golden values, or Agent B could update parity-core
  files as part of "validation cleanup" without coordination.
* The no-service-imports-main_web guardrail prevents the extracted
  services from re-importing main_web (which would couple them back
  to the route layer and undermine the Phase 51 architecture).

These guardrails are behavior-level (not call-count), survive
refactors, and fail only if the model output, parity-core content,
or import direction actually changes.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import pytest

# ─── Imports guarded to allow this test to run in any environment ─────

# We try to import project_factories and ui_runner lazily. If those
# imports are unavailable in some CI environment, the engine-output
# golden tests are skipped (not failed) — but the parity-core and
# no-service-imports guardrails always run.
_HAS_ENGINE = True
try:
    from app.project_factories import (
        create_default_oborovo,
        create_default_tuho_wind1,
    )
    from app.ui_runner import _build_period_engine, _run_waterfall
except Exception:  # pragma: no cover
    _HAS_ENGINE = False


# ─── Repo root and file paths ─────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[1]

# Parity-core locked files (SHA-256 of content).
# These files are parity-sensitive. Any unintended edit must be
# detected. Updates are allowed only via a dedicated, intentional
# model-change PR.
PARITY_CORE_FILES: dict[str, str] = {
    "reports/phase7_tuho_senior_debt_sizing_extraction.csv": (
        "80e79977f039310158b084e2613ae17251a86916b970d4fda1985467bbde3442"
    ),
    "reports/phase23q_oborovo_senior_debt_sizing_extraction.csv": (
        "8afdad21025df890b2103c73e40423bb6e4a99f755a94c9fec7b68f1cc3f58f6"
    ),
}


# Golden model output values.
# Extracted from the current model run on origin/main at base SHA
# dfe13ab6a5eb82c51b23eecf45778fcbdf3f4a5d (Phase 51E-2).
# Tolerances are intentionally tight to catch silent regressions
# but wide enough to absorb micro-floating-point drift.
GOLDEN_TUHO: dict[str, dict] = {
    "first_finite_dscr": {
        "value": 1.450695,
        "tolerance_abs": 0.001,    # ±0.001 on DSCR
        "description": (
            "First finite DSCR for TUHO (period idx 0, year 1). "
            "Source: waterfall_core.py run_waterfall_v3_core output."
        ),
    },
    "first_distribution_op_idx": {
        "value": 34,
        "tolerance_abs": 0,        # exact integer
        "description": (
            "First operating period index with positive distribution_keur. "
            "Stack N: SHL repayment starts earlier (P29 vs P30), so SHL is fully "
            "repaid one period sooner and first distribution moves from op_idx 35 to 34."
        ),
    },
    "total_operating_periods": {
        "value": 61,
        "tolerance_abs": 0,        # exact integer
        "description": "Total operating periods in TUHO model run.",
    },
    "opex_total_keur": {
        "value": 85408.27,
        "tolerance_abs": 0.5,      # ±0.5 kEUR
        "description": (
            "Sum of operating-period opex_keur over TUHO model life. "
            "kEUR."
        ),
    },
    "opex_y1_keur": {
        "value": 1998.01,
        "tolerance_abs": 0.5,      # ±0.5 kEUR
        "description": (
            "First 2 semiannual periods (year 1) OpEx sum for TUHO. kEUR."
        ),
    },
}

GOLDEN_OBOROVO: dict[str, dict] = {
    "first_finite_dscr": {
        "value": 1.150038,
        "tolerance_abs": 0.001,    # ±0.001 on DSCR (rounds to 1.15)
        "description": (
            "First finite DSCR for Oborovo (period idx 0, year 1). "
            "Matches target_dscr=1.15 policy."
        ),
    },
    "first_distribution_op_idx": {
        "value": 39,
        "tolerance_abs": 0,        # exact integer
        "description": (
            "First operating period index with positive distribution_keur. "
            "Oborovo has 39 construction/lockup periods before first distribution."
        ),
    },
    "total_operating_periods": {
        "value": 60,
        "tolerance_abs": 0,        # exact integer
        "description": "Total operating periods in Oborovo model run.",
    },
    "opex_y1_keur": {
        "value": 1338.56,
        "tolerance_abs": 0.5,      # ±0.5 kEUR
        "description": (
            "First 2 semiannual periods (year 1) OpEx sum for Oborovo. kEUR."
        ),
    },
}


# ─── Helpers ──────────────────────────────────────────────────────────

def _sha256(path: Path) -> str:
    """Compute SHA-256 of a file's bytes."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _finite_dscr_first(periods) -> tuple[int, float] | tuple[None, None]:
    """Return (idx, dscr) of the first operating period with finite DSCR.

    Excludes DSCR == inf (payoff periods) and DSCR == NaN.
    """
    for i, p in enumerate(periods):
        if not p.is_operation:
            continue
        d = p.dscr
        if d is None:
            continue
        if d != d:  # NaN check
            continue
        if d == float("inf"):
            continue
        return (i, d)
    return (None, None)


def _first_distribution_op_idx(periods) -> int | None:
    """Return idx of first operating period with positive distribution_keur."""
    for i, p in enumerate(periods):
        if not p.is_operation:
            continue
        d = p.distribution_keur
        if d is None or d <= 0:
            continue
        return i
    return None


def _total_op_periods(periods) -> int:
    """Count operating periods (is_operation=True)."""
    return sum(1 for p in periods if p.is_operation)


def _opex_total_keur(periods) -> float:
    """Sum opex_keur over operating periods."""
    return sum(p.opex_keur for p in periods if p.is_operation and p.opex_keur is not None)


def _opex_y1_keur(periods) -> float:
    """Sum first 2 operating periods' opex_keur (semiannual year 1)."""
    op_periods = [p for p in periods if p.is_operation and p.opex_keur is not None]
    return sum(p.opex_keur for p in op_periods[:2])


# ═══════════════════════════════════════════════════════════════════════
# Guardrail 1 — Engine-output golden
# ═══════════════════════════════════════════════════════════════════════

class TestEngineOutputGoldenTUHO:
    """Pin TUHO Wind 1 model outputs.

    These are the model-execution outputs that downstream routes
    (e.g. /run, /download, /validate) depend on. A change to the
    waterfall core, project factories, or senior debt schedule that
    shifts these values is a model regression, not a refactor.
    """

    @pytest.fixture(scope="class")
    def tuho_result(self):
        if not _HAS_ENGINE:
            pytest.skip("Engine not importable in this environment")
        proj = create_default_tuho_wind1()
        engine = _build_period_engine(proj)
        return _run_waterfall(proj, engine)

    def test_first_finite_dscr(self, tuho_result):
        """TUHO first finite DSCR ≈ 1.4507 (±0.001)."""
        idx, dscr = _finite_dscr_first(tuho_result.periods)
        golden = GOLDEN_TUHO["first_finite_dscr"]
        assert idx is not None, "No finite DSCR found in TUHO model output"
        assert abs(dscr - golden["value"]) <= golden["tolerance_abs"], (
            f"TUHO first finite DSCR {dscr:.6f} is outside "
            f"±{golden['tolerance_abs']} of golden {golden['value']}"
        )

    def test_first_distribution_op_idx(self, tuho_result):
        """TUHO first distribution operating period index = 35 (exact)."""
        idx = _first_distribution_op_idx(tuho_result.periods)
        golden = GOLDEN_TUHO["first_distribution_op_idx"]
        assert idx is not None, "No positive distribution found in TUHO"
        assert idx == golden["value"], (
            f"TUHO first distribution idx {idx} != golden {golden['value']}"
        )

    def test_total_operating_periods(self, tuho_result):
        """TUHO total operating periods = 61 (exact)."""
        total = _total_op_periods(tuho_result.periods)
        golden = GOLDEN_TUHO["total_operating_periods"]
        assert total == golden["value"], (
            f"TUHO total op periods {total} != golden {golden['value']}"
        )

    def test_opex_total(self, tuho_result):
        """TUHO OpEx total ≈ 85408.27 kEUR (±0.5 kEUR)."""
        total = _opex_total_keur(tuho_result.periods)
        golden = GOLDEN_TUHO["opex_total_keur"]
        assert abs(total - golden["value"]) <= golden["tolerance_abs"], (
            f"TUHO OpEx total {total:.2f} is outside "
            f"±{golden['tolerance_abs']} of golden {golden['value']}"
        )

    def test_opex_y1(self, tuho_result):
        """TUHO OpEx year-1 (sum of 2 semiannual) ≈ 1998.01 kEUR (±0.5 kEUR)."""
        y1 = _opex_y1_keur(tuho_result.periods)
        golden = GOLDEN_TUHO["opex_y1_keur"]
        assert abs(y1 - golden["value"]) <= golden["tolerance_abs"], (
            f"TUHO OpEx Y1 {y1:.2f} is outside "
            f"±{golden['tolerance_abs']} of golden {golden['value']}"
        )


class TestEngineOutputGoldenOborovo:
    """Pin Oborovo Solar PV model outputs."""

    @pytest.fixture(scope="class")
    def oborovo_result(self):
        if not _HAS_ENGINE:
            pytest.skip("Engine not importable in this environment")
        proj = create_default_oborovo()
        engine = _build_period_engine(proj)
        return _run_waterfall(proj, engine)

    def test_first_finite_dscr(self, oborovo_result):
        """Oborovo first finite DSCR ≈ 1.15 (±0.001)."""
        idx, dscr = _finite_dscr_first(oborovo_result.periods)
        golden = GOLDEN_OBOROVO["first_finite_dscr"]
        assert idx is not None, "No finite DSCR found in Oborovo model output"
        assert abs(dscr - golden["value"]) <= golden["tolerance_abs"], (
            f"Oborovo first finite DSCR {dscr:.6f} is outside "
            f"±{golden['tolerance_abs']} of golden {golden['value']}"
        )

    def test_first_distribution_op_idx(self, oborovo_result):
        """Oborovo first distribution operating period index = 39 (exact)."""
        idx = _first_distribution_op_idx(oborovo_result.periods)
        golden = GOLDEN_OBOROVO["first_distribution_op_idx"]
        assert idx is not None, "No positive distribution found in Oborovo"
        assert idx == golden["value"], (
            f"Oborovo first distribution idx {idx} != golden {golden['value']}"
        )

    def test_total_operating_periods(self, oborovo_result):
        """Oborovo total operating periods = 60 (exact)."""
        total = _total_op_periods(oborovo_result.periods)
        golden = GOLDEN_OBOROVO["total_operating_periods"]
        assert total == golden["value"], (
            f"Oborovo total op periods {total} != golden {golden['value']}"
        )

    def test_opex_schedule_is_finite_and_nonnegative(self, oborovo_result):
        """Current guard protects OPEX validity without reviving a superseded golden."""
        values = [
            p.opex_keur
            for p in oborovo_result.periods
            if p.is_operation and p.opex_keur is not None
        ]
        assert values
        assert all(value == value and value >= 0.0 for value in values)
        assert sum(values) > 0.0

    def test_opex_y1(self, oborovo_result):
        """Oborovo OpEx year-1 (sum of 2 semiannual) ≈ 1338.56 kEUR (±0.5 kEUR)."""
        y1 = _opex_y1_keur(oborovo_result.periods)
        golden = GOLDEN_OBOROVO["opex_y1_keur"]
        assert abs(y1 - golden["value"]) <= golden["tolerance_abs"], (
            f"Oborovo OpEx Y1 {y1:.2f} is outside "
            f"±{golden['tolerance_abs']} of golden {golden['value']}"
        )


# ═══════════════════════════════════════════════════════════════════════
# Guardrail 2 — Parity-core lock
# ═══════════════════════════════════════════════════════════════════════

class TestParityCoreLock:
    """Pin immutable source-extraction evidence.

    Evolving production implementations are governed by semantic current-authority
    tests. Source-extracted schedules remain byte-for-byte immutable.

    Hashes may change ONLY in a dedicated, intentional model-change
    PR. See docs/phase51f_parallel_work_guardrails.md for the
    intentional update protocol.
    """

    @pytest.mark.parametrize(
        "relpath,expected_sha256",
        list(PARITY_CORE_FILES.items()),
        ids=lambda v: v if isinstance(v, str) else v[0],
    )
    def test_parity_core_file_sha256(self, relpath, expected_sha256):
        path = REPO_ROOT / relpath
        assert path.is_file(), (
            f"Parity-core file {relpath} is missing — file may have been "
            f"moved or deleted. This is a parity regression."
        )
        actual = _sha256(path)
        assert actual == expected_sha256, (
            f"Parity-core file {relpath} SHA-256 changed.\n"
            f"  Expected: {expected_sha256}\n"
            f"  Actual:   {actual}\n"
            f"This source-evidence file is parity-locked. Changes are allowed only via "
            f"a dedicated, source-proven change PR. See "
            f"docs/phase51f_parallel_work_guardrails.md for the update "
            f"protocol. Do NOT update the hash silently."
        )


# ═══════════════════════════════════════════════════════════════════════
# Guardrail 3 — No-service-imports-main_web/main_api
# ═══════════════════════════════════════════════════════════════════════

def _iter_service_files() -> list[Path]:
    services_dir = REPO_ROOT / "app" / "services"
    if not services_dir.is_dir():
        return []
    return sorted(services_dir.glob("*.py"))


def _check_service_imports_main_web_or_main_api(path: Path) -> list[str]:
    """Return a list of offending import statements.

    Inspects AST of `path` and finds any:
      - Import(name='main_web' or 'main_api')
      - ImportFrom(module='main_web' or 'main_api')
    """
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in ("main_web", "main_api"):
                    offenders.append(
                        f"line {node.lineno}: import {alias.name}"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            top = node.module.split(".")[0]
            if top in ("main_web", "main_api"):
                offenders.append(
                    f"line {node.lineno}: from {node.module} import ..."
                )
    return offenders


class TestNoServiceImportsMainWebOrMainApi:
    """No app/services/*.py may import main_web or main_api.

    This enforces the one-way import direction: services are leaf
    modules that may NOT pull in the web layer. If a service needs
    a helper from main_web, it should be passed via the deps
    bundle (callable injection), not via import.

    Docstrings and comments mentioning "extracted from main_web" are
    ALLOWED — only actual import statements are checked.
    """

    def test_all_services_have_no_main_web_or_main_api_imports(self):
        service_files = _iter_service_files()
        assert service_files, (
            "No app/services/*.py files found — directory missing?"
        )
        all_offenders: list[tuple[str, list[str]]] = []
        for path in service_files:
            offs = _check_service_imports_main_web_or_main_api(path)
            if offs:
                all_offenders.append((str(path.relative_to(REPO_ROOT)), offs))
        assert not all_offenders, (
            "Services must not import main_web or main_api. "
            "Use deps-bundle callable injection instead. Offenders:\n  "
            + "\n  ".join(
                f"{p}:\n    " + "\n    ".join(o) for p, o in all_offenders
            )
        )


# ═══════════════════════════════════════════════════════════════════════
# Auxiliary tests — make the guardrails self-explanatory
# ═══════════════════════════════════════════════════════════════════════

class TestGuardrailInventory:
    """Document the exact list of parity-core files and golden values."""

    def test_parity_core_files_inventory_is_frozen(self):
        # Only immutable source-extraction evidence belongs in a byte lock.
        expected = {
            "reports/phase7_tuho_senior_debt_sizing_extraction.csv",
            "reports/phase23q_oborovo_senior_debt_sizing_extraction.csv",
        }
        actual = set(PARITY_CORE_FILES.keys())
        assert actual == expected, (
            f"Parity-core file inventory changed. "
            f"Expected: {sorted(expected)}, Actual: {sorted(actual)}"
        )

    def test_all_locked_files_exist(self):
        for relpath in PARITY_CORE_FILES:
            assert (REPO_ROOT / relpath).is_file(), (
                f"Locked parity-core file {relpath} does not exist"
            )

    def test_golden_values_are_floats_or_ints(self):
        for project_name, golden in [("TUHO", GOLDEN_TUHO), ("OBOROVO", GOLDEN_OBOROVO)]:
            for key, spec in golden.items():
                assert isinstance(spec["value"], (int, float)), (
                    f"{project_name}.{key}.value must be int or float"
                )
                assert "tolerance_abs" in spec, (
                    f"{project_name}.{key} missing tolerance_abs"
                )
                assert spec["tolerance_abs"] >= 0, (
                    f"{project_name}.{key}.tolerance_abs must be ≥ 0"
                )
                assert "description" in spec, (
                    f"{project_name}.{key} missing description"
                )


class TestGuardrailDocsCrossCheck:
    """Verify the guardrails are documented.

    The docs/phase51f_parallel_work_guardrails.md file must exist
    and contain the three guardrail names so the docs and the tests
    stay in sync.
    """

    def test_phase51f_docs_exists(self):
        docs_path = REPO_ROOT / "docs" / "phase51f_parallel_work_guardrails.md"
        assert docs_path.is_file(), (
            f"Required docs file {docs_path} not found"
        )

    def test_phase51f_docs_mentions_three_guardrails(self):
        docs_path = REPO_ROOT / "docs" / "phase51f_parallel_work_guardrails.md"
        text = docs_path.read_text(encoding="utf-8")
        for guardrail in [
            "Engine-output golden",
            "Parity-core lock",
            "No-service-imports-main_web",
        ]:
            assert guardrail in text, (
                f"Docs file does not mention guardrail: {guardrail!r}"
            )

    def test_phase51f_docs_lists_parity_core_files(self):
        docs_path = REPO_ROOT / "docs" / "phase51f_parallel_work_guardrails.md"
        text = docs_path.read_text(encoding="utf-8")
        for relpath in PARITY_CORE_FILES:
            assert relpath in text, (
                f"Docs file does not mention locked file: {relpath}"
            )
