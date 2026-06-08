"""Phase R-PAR-2 Decision Discovery tests (test-only).

These tests verify that:
- The R-PAR-2 caveat is referenced in the C1 design doc.
- The R-PAR-2 caveat is referenced in the C9 guard module.
- The C9 guard's senior_idc_keur block behaviour is fail-closed.
- The C9 guard's rpar2_resolved=False default is enforced.
- The C9 guard's parity_ok=False default is enforced.
- The decision options A, B, C are documented in this PR's
  discovery doc.
- The C10 readiness design (PR #557) explicitly excludes
  senior_idc_keur from the allowed fields.

These tests are **fully test-only**. They do not touch the
production code, the model, the formulas, the runtime, the
waterfall, the persistence, the UI, or the feature flags.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]

C1_DESIGN_DOC = (
    REPO_ROOT / "docs" / "phase_c1_construction_idc_design_gate.md"
)

C9_SEAM_MODULE = (
    REPO_ROOT / "app" / "services" / "construction_runtime_seam.py"
)

RPAR2_DISCOVERY_DOC = (
    REPO_ROOT / "docs" / "phase_rpar2_decision_discovery.md"
)

RPAR2_REPORT_JSON = (
    REPO_ROOT / "reports" / "phase_rpar2_decision_discovery.json"
)


# ---------------------------------------------------------------------------
# Discovery doc existence
# ---------------------------------------------------------------------------


class TestRpar2DiscoveryDocExists:
    def test_discovery_doc_exists(self):
        assert RPAR2_DISCOVERY_DOC.exists(), (
            f"R-PAR-2 discovery doc must exist at "
            f"{RPAR2_DISCOVERY_DOC.relative_to(REPO_ROOT)}"
        )

    def test_report_json_exists(self):
        assert RPAR2_REPORT_JSON.exists(), (
            f"R-PAR-2 report JSON must exist at "
            f"{RPAR2_REPORT_JSON.relative_to(REPO_ROOT)}"
        )

    def test_discovery_doc_has_decision_options(self):
        text = RPAR2_DISCOVERY_DOC.read_text(encoding="utf-8")
        for opt in ("Option A", "Option B", "Option C"):
            assert opt in text, (
                f"R-PAR-2 discovery doc must reference {opt!r}"
            )

    def test_discovery_doc_references_c9_guard(self):
        text = RPAR2_DISCOVERY_DOC.read_text(encoding="utf-8")
        assert "assert_no_construction_runtime_promotion" in text, (
            "R-PAR-2 discovery doc must reference the C9 guard function"
        )

    def test_discovery_doc_references_pr_557(self):
        text = RPAR2_DISCOVERY_DOC.read_text(encoding="utf-8")
        assert "PR #557" in text or "#557" in text, (
            "R-PAR-2 discovery doc must reference PR #557 (C10 readiness)"
        )

    def test_discovery_doc_references_c10_excludes_senior_idc(self):
        text = RPAR2_DISCOVERY_DOC.read_text(encoding="utf-8")
        assert "senior_idc_keur" in text, (
            "R-PAR-2 discovery doc must reference senior_idc_keur"
        )
        # Must mention that C10 EXCLUDES senior_idc_keur.
        assert re.search(
            r"senior_idc_keur.{0,200}exclud",
            text,
            re.IGNORECASE | re.DOTALL,
        ), (
            "R-PAR-2 discovery doc must state that C10 EXCLUDES "
            "senior_idc_keur from the allowed fields"
        )


# ---------------------------------------------------------------------------
# C1 design doc references R-PAR-2
# ---------------------------------------------------------------------------


class TestC1DesignDocReferencesRpar2:
    def test_c1_design_doc_exists(self):
        assert C1_DESIGN_DOC.exists(), (
            f"C1 design doc must exist at "
            f"{C1_DESIGN_DOC.relative_to(REPO_ROOT)}"
        )

    def test_c1_design_doc_references_rpar2(self):
        """The C1 design doc must reference the R-PAR-2 caveat
        (or its full name \"senior IDC effective-rate caveat\")."""
        text = C1_DESIGN_DOC.read_text(encoding="utf-8")
        # We accept either \"R-PAR-2\" or the full caveat name.
        has_rpar2 = "R-PAR-2" in text or "R-PAR2" in text
        has_full = (
            "senior IDC" in text
            and ("effective rate" in text.lower() or "effective-rate" in text.lower())
        )
        assert has_rpar2 or has_full, (
            "C1 design doc must reference R-PAR-2 or the "
            "senior IDC effective-rate caveat"
        )


# ---------------------------------------------------------------------------
# C9 seam module — fail-closed defaults
# ---------------------------------------------------------------------------


class TestC9GuardFailClosedDefaults:
    def test_c9_seam_module_exists(self):
        assert C9_SEAM_MODULE.exists(), (
            f"C9 seam module must exist at "
            f"{C9_SEAM_MODULE.relative_to(REPO_ROOT)}"
        )

    def test_c9_seam_module_has_guard(self):
        text = C9_SEAM_MODULE.read_text(encoding="utf-8")
        assert "def assert_no_construction_runtime_promotion" in text, (
            "C9 seam module must define "
            "assert_no_construction_runtime_promotion"
        )

    def test_c9_guard_rpar2_resolved_default_false(self):
        """The C9 guard's rpar2_resolved parameter must default to
        False (fail-closed). This is verified by AST inspection."""
        tree = ast.parse(C9_SEAM_MODULE.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name != "assert_no_construction_runtime_promotion":
                continue
            for arg in node.args.kw_defaults:
                if arg is None:
                    continue
                # Find kwonly args and their defaults
                pass
            # Check that rpar2_resolved has a default of False
            kwonly_args = node.args.kwonlyargs
            kw_defaults = node.args.kw_defaults
            for i, arg in enumerate(kwonly_args):
                if arg.arg == "rpar2_resolved":
                    default = kw_defaults[i]
                    assert default is not None, (
                        "rpar2_resolved must have a default (fail-closed)"
                    )
                    assert isinstance(default, ast.Constant), (
                        f"rpar2_resolved default must be a constant, "
                        f"got {type(default).__name__}"
                    )
                    assert default.value is False, (
                        f"rpar2_resolved default must be False (fail-closed), "
                        f"got {default.value!r}"
                    )
                    return
            pytest.fail(
                "assert_no_construction_runtime_promotion must have a "
                "rpar2_resolved keyword-only argument"
            )
        pytest.fail(
            "Could not locate assert_no_construction_runtime_promotion "
            "in C9 seam module"
        )

    def test_c9_guard_parity_ok_default_false(self):
        """The C9 guard's parity_ok parameter must default to
        False (fail-closed)."""
        tree = ast.parse(C9_SEAM_MODULE.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name != "assert_no_construction_runtime_promotion":
                continue
            kwonly_args = node.args.kwonlyargs
            kw_defaults = node.args.kw_defaults
            for i, arg in enumerate(kwonly_args):
                if arg.arg == "parity_ok":
                    default = kw_defaults[i]
                    assert default is not None, (
                        "parity_ok must have a default (fail-closed)"
                    )
                    assert isinstance(default, ast.Constant), (
                        f"parity_ok default must be a constant, "
                        f"got {type(default).__name__}"
                    )
                    assert default.value is False, (
                        f"parity_ok default must be False (fail-closed), "
                        f"got {default.value!r}"
                    )
                    return
            pytest.fail(
                "assert_no_construction_runtime_promotion must have a "
                "parity_ok keyword-only argument"
            )
        pytest.fail(
            "Could not locate assert_no_construction_runtime_promotion "
            "in C9 seam module"
        )

    def test_c9_guard_blocks_senior_idc_with_default_args(self):
        """A direct call to the guard with default args
        (rpar2_resolved=False, parity_ok=False) must RAISE for
        senior_idc_keur, because R-PAR-2 is open.

        We invoke the guard via a subprocess that runs a small
        script in-process. We cannot import the seam module
        directly here because its ``from __future__ import
        annotations`` interacts with the dataclass decorator in
        ways that fail when loaded via importlib.util under
        pytest's import mode. Using subprocess sidesteps this.
        """
        import subprocess
        import textwrap
        repo_root_str = str(REPO_ROOT)
        script = (
            "import sys\n"
            "sys.path.insert(0, " + repr(repo_root_str) + ")\n"
            "from app.services.construction_runtime_seam import (\n"
            "    assert_no_construction_runtime_promotion,\n"
            "    PromotionBlockedError,\n"
            ")\n"
            "try:\n"
            "    assert_no_construction_runtime_promotion(\n"
            "        field_code='senior_idc_keur',\n"
            "        policy='replaced',\n"
            "        promotion_requested=True,\n"
            "    )\n"
            "except PromotionBlockedError:\n"
            "    print('BLOCKED_OK')\n"
            "    sys.exit(0)\n"
            "except ValueError as e:\n"
            "    print('INPUT_VALIDATION_ERROR: ' + str(e))\n"
            "    sys.exit(2)\n"
            "except Exception as e:\n"
            "    print('OTHER_EXCEPTION: ' + type(e).__name__ + ': ' + str(e))\n"
            "    sys.exit(3)\n"
            "print('NO_BLOCK')\n"
            "sys.exit(1)\n"
        )
        result = subprocess.run(
            ["python3", "-c", script],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert "BLOCKED_OK" in result.stdout, (
            f"senior_idc_keur promotion with defaults must be a "
            f"PromotionBlockedError block. Got stdout: {result.stdout!r}, "
            f"stderr: {result.stderr!r}, returncode: {result.returncode}"
        )


# ---------------------------------------------------------------------------
# rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    def test_rc1_sha_reachable(self):
        import subprocess
        result = subprocess.run(
            [
                "git", "cat-file", "-e",
                "b425a0708719eaa5e1d922b1008e5609758e0ad4",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            "rc1 SHA not reachable on origin/main"
        )


# ---------------------------------------------------------------------------
# Feature flag default-off
# ---------------------------------------------------------------------------


class TestFeatureFlagDefaultOff:
    def test_use_construction_schedule_engine_default_false(self):
        domain_inputs = REPO_ROOT / "domain" / "inputs.py"
        text = domain_inputs.read_text(encoding="utf-8")
        # Find the declaration and verify default is False.
        match = re.search(
            r"use_construction_schedule_engine\s*:\s*bool\s*=\s*(\w+)",
            text,
        )
        assert match, (
            "domain/inputs.py must declare "
            "use_construction_schedule_engine: bool"
        )
        assert match.group(1) == "False", (
            f"use_construction_schedule_engine default must be False, "
            f"got {match.group(1)!r}"
        )
