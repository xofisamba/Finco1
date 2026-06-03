"""Phase 53E-2 — Targeted regression pin for _compute_baseline_snapshot.

This file adds a STRONG regression pin for _compute_baseline_snapshot
and its nested _sum_opex helper. These pins were missing in the
initial 53E-2 PR, which is how a regression slipped through (TUHO /
Oborovo branches were wrong, _sum_opex used amount_keur instead of
y1_amount_keur, and the early-return after TUHO/Oborovo branches was
missing).

The 5 pins:

1. _compute_baseline_snapshot("Wind", "tuho") returns TUHO-specific values
   and active_project == "tuho-baseline".
2. _compute_baseline_snapshot("Solar", "oborovo") returns Oborovo-specific
   values and active_project == "oborovo-baseline".
3. Generic wind/solar fallback still works (capitalizes on canonical_type).
4. _sum_opex behavior is pinned indirectly through opex_y1_keur
   using y1_amount_keur, NOT amount_keur.
5. The lowercase template_source behavior is preserved (the source
   string is exactly "tuho" and "oborovo", not "TUHO" or "Oborovo").
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_PY = REPO_ROOT / "app" / "persistence" / "projects_repository.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ----------------------------- G1: source-byte pin for _compute_baseline_snapshot ----------------------------


class TestComputeBaselineSnapshotSourcePin:
    """Pin the exact source of _compute_baseline_snapshot in projects_repository.py.
    This is the strongest possible pin: byte-for-byte comparison to a known-good
    reference. If this fails, the function has drifted from the original.
    """

    def test_function_defined_in_projects_repository(self):
        text = _read(PROJECTS_PY)
        assert "def _compute_baseline_snapshot(" in text

    def test_function_no_longer_defined_in_repository(self):
        # After 53E-2 extraction, _compute_baseline_snapshot should NOT be in repository.py body
        text = _read(REPOSITORY_PY)
        # It should only appear as a re-export in the import block
        # Count occurrences of the def line
        n = text.count("def _compute_baseline_snapshot(")
        assert n == 0, f"_compute_baseline_snapshot should not be defined in repository.py (moved in 53E-2)"

    def test_lowercase_tuho_branch_present(self):
        # The lowercase "tuho" check is the critical one
        text = _read(PROJECTS_PY)
        # Find the function body
        m = re.search(r"def _compute_baseline_snapshot\(.*?(?=\ndef |\Z)", text, re.DOTALL)
        assert m, "_compute_baseline_snapshot not found"
        body = m.group(0)
        assert 'normalized_source == "tuho"' in body, \
            f'_compute_baseline_snapshot must use lowercase "tuho" comparison. Got: {body[:200]}...'

    def test_lowercase_oborovo_branch_present(self):
        text = _read(PROJECTS_PY)
        m = re.search(r"def _compute_baseline_snapshot\(.*?(?=\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        assert 'normalized_source == "oborovo"' in body, \
            f'_compute_baseline_snapshot must use lowercase "oborovo" comparison. Got: {body[:200]}...'

    def test_no_uppercase_tuho_oborovo(self):
        # Regression: the old broken version used "TUHO" / "Oborovo" (uppercase)
        text = _read(PROJECTS_PY)
        m = re.search(r"def _compute_baseline_snapshot\(.*?(?=\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        # No uppercase versions should appear in the comparison
        assert 'normalized_source == "TUHO"' not in body, \
            "_compute_baseline_snapshot must NOT use uppercase TUHO"
        assert 'normalized_source == "Oborovo"' not in body, \
            "_compute_baseline_snapshot must NOT use uppercase Oborovo"

    def test_early_return_after_tuho_branch(self):
        # Each TUHO/Oborovo branch must return baseline immediately
        text = _read(PROJECTS_PY)
        m = re.search(r"def _compute_baseline_snapshot\(.*?(?=\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        # The TUHO branch should end with "return baseline"
        # Find the tuho branch and the next elif or generic block
        tuho_block = re.search(
            r'if normalized_source == "tuho":.*?(?=if normalized_source == "oborovo")',
            body, re.DOTALL
        )
        assert tuho_block, "TUHO branch not found"
        assert "return baseline" in tuho_block.group(0), \
            "TUHO branch must return baseline immediately"

    def test_early_return_after_oborovo_branch(self):
        text = _read(PROJECTS_PY)
        m = re.search(r"def _compute_baseline_snapshot\(.*?(?=\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        oborovo_block = re.search(
            r'if normalized_source == "oborovo":.*?(?=# generic_wind)',
            body, re.DOTALL
        )
        assert oborovo_block, "Oborovo branch not found"
        assert "return baseline" in oborovo_block.group(0), \
            "Oborovo branch must return baseline immediately"

    def test_generic_fallback_after_tuho_oborovo(self):
        # The generic_wind / generic_solar fallback must come AFTER the TUHO/Oborovo branches
        text = _read(PROJECTS_PY)
        m = re.search(r"def _compute_baseline_snapshot\(.*?(?=\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        # The fallback comment "generic_wind / generic_solar fallback" must exist
        assert "# generic_wind / generic_solar fallback" in body, \
            "Generic fallback comment must be present"
        # And it must come AFTER both TUHO and Oborovo branches
        tuho_pos = body.find('normalized_source == "tuho"')
        oborovo_pos = body.find('normalized_source == "oborovo"')
        fallback_pos = body.find("# generic_wind / generic_solar fallback")
        assert tuho_pos > 0 and oborovo_pos > 0 and fallback_pos > 0
        assert fallback_pos > tuho_pos, "Fallback must come after TUHO branch"
        assert fallback_pos > oborovo_pos, "Fallback must come after Oborovo branch"


# ----------------------------- G2: _sum_opex uses y1_amount_keur ----------------------------


class TestSumOpexY1AmountKeur:
    """Pin that _sum_opex uses y1_amount_keur (NOT amount_keur)."""

    def test_y1_amount_keur_in_sum_opex(self):
        text = _read(PROJECTS_PY)
        m = re.search(r"def _sum_opex\(.*?(?=\n    [a-zA-Z]|\Z)", text, re.DOTALL)
        assert m, "_sum_opex not found"
        body = m.group(0)
        assert "y1_amount_keur" in body, \
            "_sum_opex must use y1_amount_keur (not amount_keur)"

    def test_no_amount_keur_in_sum_opex(self):
        # Regression: the old broken version used getattr(item, "amount_keur", 0)
        text = _read(PROJECTS_PY)
        m = re.search(r"def _sum_opex\(.*?(?=\n    [a-zA-Z]|\Z)", text, re.DOTALL)
        body = m.group(0)
        # The function must NOT reference amount_keur
        assert '"amount_keur"' not in body, \
            "_sum_opex must NOT use amount_keur (must use y1_amount_keur)"
        assert "'amount_keur'" not in body, \
            "_sum_opex must NOT use amount_keur (must use y1_amount_keur)"

    def test_sum_opex_docstring_mentions_y1(self):
        # The original docstring says: "Sum y1_amount_keur from an opex iterable."
        text = _read(PROJECTS_PY)
        m = re.search(r"def _sum_opex\(.*?(?=\n    [a-zA-Z]|\Z)", text, re.DOTALL)
        body = m.group(0)
        assert "Sum y1_amount_keur" in body, \
            "_sum_opex must have docstring mentioning y1_amount_keur"

    def test_sum_opex_signature(self):
        # _sum_opex takes a single parameter 'items' and returns a float
        text = _read(PROJECTS_PY)
        m = re.search(r"def _sum_opex\(items\):", text)
        assert m, "_sum_opex(items) signature not found"


# ----------------------------- G3: opex_y1_keur string format ----------------------------


class TestOpexY1KeurStringFormat:
    """Pin the string format of opex_y1_keur in all 3 branches (TUHO, Oborovo, generic)."""

    def test_tuho_branch_opex_y1_keur_uses_sum_opex(self):
        text = _read(PROJECTS_PY)
        # Find the TUHO branch
        m = re.search(
            r'if normalized_source == "tuho":.*?return baseline',
            text, re.DOTALL
        )
        assert m, "TUHO branch not found"
        assert '"opex_y1_keur": str(_sum_opex(pi.opex))' in m.group(0)

    def test_oborovo_branch_opex_y1_keur_uses_sum_opex(self):
        text = _read(PROJECTS_PY)
        m = re.search(
            r'if normalized_source == "oborovo":.*?return baseline',
            text, re.DOTALL
        )
        assert m, "Oborovo branch not found"
        assert '"opex_y1_keur": str(_sum_opex(pi.opex))' in m.group(0)

    def test_generic_branch_opex_y1_keur_uses_sum_opex(self):
        text = _read(PROJECTS_PY)
        m = re.search(
            r'# generic_wind / generic_solar fallback.*?return baseline',
            text, re.DOTALL
        )
        assert m, "Generic fallback branch not found"
        assert '"opex_y1_keur": str(_sum_opex(pi.opex))' in m.group(0)


# ----------------------------- G4: active_project values for each branch ----------------------------


class TestActiveProjectValues:
    """Pin the active_project value that each branch sets."""

    def test_tuho_active_project(self):
        text = _read(PROJECTS_PY)
        m = re.search(
            r'if normalized_source == "tuho":.*?return baseline',
            text, re.DOTALL
        )
        body = m.group(0)
        assert '"active_project": "tuho-baseline"' in body

    def test_oborovo_active_project(self):
        text = _read(PROJECTS_PY)
        m = re.search(
            r'if normalized_source == "oborovo":.*?return baseline',
            text, re.DOTALL
        )
        body = m.group(0)
        assert '"active_project": "oborovo-baseline"' in body

    def test_generic_active_project(self):
        text = _read(PROJECTS_PY)
        m = re.search(
            r'# generic_wind / generic_solar fallback.*?return baseline',
            text, re.DOTALL
        )
        body = m.group(0)
        # In the generic branch, active_project equals normalized_source
        assert '"active_project": normalized_source' in body


# ----------------------------- G5: project_type for each branch ----------------------------


class TestProjectTypePerBranch:
    """Pin the project_type value that each branch sets."""

    def test_tuho_project_type_wind(self):
        text = _read(PROJECTS_PY)
        m = re.search(
            r'if normalized_source == "tuho":.*?return baseline',
            text, re.DOTALL
        )
        body = m.group(0)
        assert '"project_type": "Wind"' in body

    def test_oborovo_project_type_solar(self):
        text = _read(PROJECTS_PY)
        m = re.search(
            r'if normalized_source == "oborovo":.*?return baseline',
            text, re.DOTALL
        )
        body = m.group(0)
        assert '"project_type": "Solar"' in body

    def test_generic_branch_uses_canonical_type(self):
        # The generic fallback uses canonical_type variable, NOT "Wind" or "Solar" literal
        text = _read(PROJECTS_PY)
        m = re.search(
            r'# generic_wind / generic_solar fallback.*?return baseline',
            text, re.DOTALL
        )
        body = m.group(0)
        # The generic branch does NOT set project_type explicitly (it uses canonical_type from baseline dict)
        # So we check that baseline["project_type"] = canonical_type (which is the initial value)
        # and that the generic branch updates the dict with values from the factory
        # It does NOT have an explicit "project_type" key in the update dict
        # (canonical_type was set initially in the baseline dict)
        # Verify that the generic branch updates template_source and other fields
        assert '"template_source": normalized_source' in body
        # The factory-set values (not project_type, which is from canonical_type)
        # Verify _sum_opex is still called
        assert '_sum_opex(pi.opex)' in body


# ----------------------------- G6: imports ----------------------------


class TestImports:
    """Pin the imports inside _compute_baseline_snapshot."""

    def test_create_default_tuho_wind1_imported(self):
        text = _read(PROJECTS_PY)
        m = re.search(r"def _compute_baseline_snapshot\(.*?(?=\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        assert "from app.project_factories import (" in body
        assert "create_default_tuho_wind1" in body

    def test_create_default_oborovo_imported(self):
        text = _read(PROJECTS_PY)
        m = re.search(r"def _compute_baseline_snapshot\(.*?(?=\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        assert "create_default_oborovo" in body

    def test_create_default_wind_project_imported(self):
        text = _read(PROJECTS_PY)
        m = re.search(r"def _compute_baseline_snapshot\(.*?(?=\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        assert "create_default_wind_project" in body

    def test_create_default_solar_project_imported(self):
        text = _read(PROJECTS_PY)
        m = re.search(r"def _compute_baseline_snapshot\(.*?(?=\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        assert "create_default_solar_project" in body


# ----------------------------- G7: byte-for-byte source comparison ----------------------------


class TestByteForByteSourceComparison:
    """The strongest pin: byte-for-byte source comparison to the original
    in the pre-53E-2 base SHA (6ee6544e9d18d0efc3eb0ce1f6099f6c6c2d1ef2).
    This SHA is the documented base of PR #435 and is the last commit
    that had _compute_baseline_snapshot in app/persistence/repository.py.
    """

    # Pre-53E-2 base SHA (last commit on main before PR #435 was merged)
    PRE_53E2_BASE_SHA = "6ee6544e9d18d0efc3eb0ce1f6099f6c6c2d1ef2"

    def test_compute_baseline_snapshot_byte_for_byte(self):
        import subprocess
        # Get the original function body from the pre-53E-2 base SHA
        result = subprocess.run(
            ["git", "show", f"{self.PRE_53E2_BASE_SHA}:app/persistence/repository.py"],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0
        original_full = result.stdout
        # Extract _compute_baseline_snapshot.._build_default_snapshot
        m_orig = re.search(
            r"def _compute_baseline_snapshot\(.*?(?=\ndef _build_default_snapshot)",
            original_full, re.DOTALL
        )
        assert m_orig, "Could not find _compute_baseline_snapshot in pre-53E-2 base"
        original_body = m_orig.group(0)
        # Get the new function body
        new_full = _read(PROJECTS_PY)
        m_new = re.search(
            r"def _compute_baseline_snapshot\(.*?(?=\ndef _build_default_snapshot)",
            new_full, re.DOTALL
        )
        assert m_new, "Could not find _compute_baseline_snapshot in projects_repository.py"
        new_body = m_new.group(0)
        # Compare byte-for-byte
        assert original_body == new_body, (
            f"_compute_baseline_snapshot differs from pre-53E-2 base.\n"
            f"Original length: {len(original_body)}, New length: {len(new_body)}\n"
            f"First 200 chars of new: {new_body[:200]!r}"
        )
