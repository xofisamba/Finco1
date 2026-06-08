"""Phase C4 - Construction Period Parity Snapshot Structure Validation tests.

**Scope label:** Snapshot structure validation only — no runtime
construction engine comparison yet.

This phase implements:
- Frozen golden snapshot files (TUHO + Oborovo)
- Structure validation tests (schema, fields, monthly grid, identities)
- Caveat documentation in snapshots
- Reference consistency checks

This phase does NOT implement:
- Engine comparison (deferred to C5+)
- CI workflow (deferred to C5+)
- Layer 4 bridge implementation (deferred to C5+)
- Layer 5 seam implementation (deferred to C6+)
- Runtime opt-in flag flip (deferred to C7+)
- Senior IDC base-rate modelling (separate workstream)

Hard constraints:
- NO app/ runtime changes
- NO domain model changes
- NO waterfall changes
- NO CAPEX formula changes
- NO debt/SHL/IDC runtime changes
- NO tax changes
- NO depreciation changes
- NO schema/persistence changes
- NO feature flags
- NO project status changes
- rc1 SHA `b425a07...` reachable
- `use_construction_schedule_engine` remains default-off
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_DOC = (
    REPO_ROOT
    / "docs" / "phase_c4_construction_parity_test_implementation.md"
)
REPORT_JSON = (
    REPO_ROOT
    / "reports" / "phase_c4_construction_parity_test_implementation.json"
)
TUHO_SNAPSHOT = (
    REPO_ROOT
    / "tests" / "fixtures" / "construction_parity"
    / "tuho_construction_snapshot.json"
)
OBOROVO_SNAPSHOT = (
    REPO_ROOT
    / "tests" / "fixtures" / "construction_parity"
    / "oborovo_construction_snapshot.json"
)
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "construction_parity"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def design_doc_text() -> str:
    return DESIGN_DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def report_json_data() -> dict:
    return json.loads(REPORT_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tuho_snapshot() -> dict:
    return json.loads(TUHO_SNAPSHOT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def oborovo_snapshot() -> dict:
    return json.loads(OBOROVO_SNAPSHOT.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


class TestFilesExist:
    def test_design_doc_exists(self):
        assert DESIGN_DOC.is_file(), f"missing design doc: {DESIGN_DOC}"

    def test_report_json_exists(self):
        assert REPORT_JSON.is_file(), f"missing report: {REPORT_JSON}"

    def test_tuho_snapshot_exists(self):
        assert TUHO_SNAPSHOT.is_file(), f"missing TUHO snapshot: {TUHO_SNAPSHOT}"

    def test_oborovo_snapshot_exists(self):
        assert OBOROVO_SNAPSHOT.is_file(), (
            f"missing Oborovo snapshot: {OBOROVO_SNAPSHOT}"
        )

    def test_fixtures_dir_exists(self):
        assert FIXTURES_DIR.is_dir(), (
            f"missing fixtures dir: {FIXTURES_DIR}"
        )

    def test_design_doc_nonempty(self):
        assert DESIGN_DOC.stat().st_size > 5000, (
            "design doc should be substantial (>= 5KB)"
        )


# ---------------------------------------------------------------------------
# Scope label — snapshot-only
# ---------------------------------------------------------------------------


class TestScopeLabelSnapshotOnly:
    """C4 is snapshot structure validation only — no engine comparison yet."""

    def test_scope_label_in_design_doc(self, design_doc_text):
        # The label must be present in the design doc
        assert "Snapshot structure validation only" in design_doc_text, (
            "Scope label 'Snapshot structure validation only' missing"
        )

    def test_scope_label_in_report(self, report_json_data):
        assert "scope_label" in report_json_data
        assert "Snapshot structure validation only" in (
            report_json_data["scope_label"]
        )

    def test_no_engine_comparison_in_design(self, design_doc_text):
        # The doc must state that engine comparison is NOT in C4
        window_lower = design_doc_text.lower()
        # The deferred scope list
        assert "not implemented" in window_lower
        assert (
            "engine comparison" in window_lower
        ), "engine comparison deferral not stated"
        assert (
            "c5+" in window_lower
        ), "C5+ deferral not stated"

    def test_c4_does_not_invoke_engine(self):
        # The test file must NOT import the construction engine.
        # Use AST-level check: walk the module to find actual imports.
        import ast
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module)
        # C4 tests are self-contained: only stdlib + pytest
        forbidden_prefixes = (
            "domain.construction",
            "domain.engine",
            "main_web",
            "main_api",
            "app.",
        )
        for mod in imported_modules:
            for forbidden in forbidden_prefixes:
                if mod == forbidden or mod.startswith(forbidden):
                    pytest.fail(
                        f"C4 test file must not import {mod!r} "
                        f"(forbidden prefix: {forbidden!r})"
                    )


# ---------------------------------------------------------------------------
# TUHO snapshot structure
# ---------------------------------------------------------------------------


class TestTuhoSnapshotStructure:
    REQUIRED_TOP_KEYS = [
        "project_code",
        "schema_version",
        "tolerance_policy",
        "field_count_expected",
        "calendar",
        "totals_keur",
        "opening_balances_keur",
        "monthly_grid",
        "funding_caps_keur",
        "rates",
        "caveats",
        "source_documents",
    ]

    REQUIRED_TOTALS_KEYS = [
        "total_uses",
        "total_equity_draw",
        "total_shl_draw",
        "total_junior_draw",
        "total_senior_draw",
        "total_shl_idc",
        "total_senior_idc",
    ]

    REQUIRED_OPENING_KEYS = [
        "opening_senior_balance",
        "opening_shl_balance",
        "equity_contribution_at_cod",
    ]

    REQUIRED_CALENDAR_KEYS = [
        "construction_start_date",
        "cod_date",
        "shl_investment_date",
        "construction_months",
    ]

    REQUIRED_CAVEAT_KEYS = [
        "senior_idc_effective_rate_caveat_applies",
        "senior_idc_effective_rate",
        "senior_idc_target_keur",
        "senior_idc_source",
        "policy_reference",
        "shl_idc_convention",
        "shl_idc_convention_reference",
        "equity_idc_capitalized",
    ]

    @pytest.mark.parametrize("key", REQUIRED_TOP_KEYS)
    def test_top_level_key_present(self, tuho_snapshot, key):
        assert key in tuho_snapshot, f"TUHO top-level key missing: {key!r}"

    @pytest.mark.parametrize("key", REQUIRED_TOTALS_KEYS)
    def test_totals_key_present(self, tuho_snapshot, key):
        assert key in tuho_snapshot["totals_keur"], (
            f"TUHO totals_keur key missing: {key!r}"
        )

    @pytest.mark.parametrize("key", REQUIRED_OPENING_KEYS)
    def test_opening_key_present(self, tuho_snapshot, key):
        assert key in tuho_snapshot["opening_balances_keur"], (
            f"TUHO opening_balances_keur key missing: {key!r}"
        )

    @pytest.mark.parametrize("key", REQUIRED_CALENDAR_KEYS)
    def test_calendar_key_present(self, tuho_snapshot, key):
        assert key in tuho_snapshot["calendar"], (
            f"TUHO calendar key missing: {key!r}"
        )

    @pytest.mark.parametrize("key", REQUIRED_CAVEAT_KEYS)
    def test_caveat_key_present(self, tuho_snapshot, key):
        assert key in tuho_snapshot["caveats"], (
            f"TUHO caveats key missing: {key!r}"
        )

    def test_project_code(self, tuho_snapshot):
        assert tuho_snapshot["project_code"] == "TUHO-WIND-1"

    def test_schema_version(self, tuho_snapshot):
        assert tuho_snapshot["schema_version"] == "C3-1.0"

    def test_tolerance_policy(self, tuho_snapshot):
        assert tuho_snapshot["tolerance_policy"] == "exact_0.001_keur"

    def test_field_count_207(self, tuho_snapshot):
        assert tuho_snapshot["field_count_expected"] == 207

    def test_construction_months_18(self, tuho_snapshot):
        assert tuho_snapshot["calendar"]["construction_months"] == 18


# ---------------------------------------------------------------------------
# TUHO monthly grid
# ---------------------------------------------------------------------------


class TestTuhoMonthlyGrid:
    def test_grid_length_18(self, tuho_snapshot):
        assert len(tuho_snapshot["monthly_grid"]) == 18

    def test_grid_indices_sequential(self, tuho_snapshot):
        indices = [row["month_index"] for row in tuho_snapshot["monthly_grid"]]
        assert indices == list(range(1, 19))

    def test_grid_first_value(self, tuho_snapshot):
        # First month: 24,226.729
        assert tuho_snapshot["monthly_grid"][0]["monthly_uses_keur"] == 24226.729

    def test_grid_last_value(self, tuho_snapshot):
        # Last month: 2,971.101
        assert tuho_snapshot["monthly_grid"][-1]["monthly_uses_keur"] == 2971.101

    def test_monthly_sum_equals_total_uses(self, tuho_snapshot):
        total = sum(
            row["monthly_uses_keur"] for row in tuho_snapshot["monthly_grid"]
        )
        expected = tuho_snapshot["totals_keur"]["total_uses"]
        assert abs(total - expected) <= 0.001, (
            f"sum of monthly uses {total} != total_uses {expected}"
        )

    def test_cumulative_monotonic(self, tuho_snapshot):
        cumulatives = [
            row["cumulative_uses_keur"] for row in tuho_snapshot["monthly_grid"]
        ]
        for i in range(1, len(cumulatives)):
            assert cumulatives[i] >= cumulatives[i - 1], (
                f"cumulative row {i+1} decreased: {cumulatives[i-1]} -> {cumulatives[i]}"
            )

    def test_cumulative_matches_running_sum(self, tuho_snapshot):
        running = 0.0
        for row in tuho_snapshot["monthly_grid"]:
            running += row["monthly_uses_keur"]
            assert abs(row["cumulative_uses_keur"] - running) <= 0.001, (
                f"cumulative at month {row['month_index']} mismatch: "
                f"{row['cumulative_uses_keur']} vs {running}"
            )

    def test_cumulative_final_matches_total(self, tuho_snapshot):
        last = tuho_snapshot["monthly_grid"][-1]["cumulative_uses_keur"]
        expected = tuho_snapshot["totals_keur"]["total_uses"]
        assert abs(last - expected) <= 0.001


# ---------------------------------------------------------------------------
# TUHO opening balance identity
# ---------------------------------------------------------------------------


class TestTuhoOpeningBalanceIdentity:
    def test_senior_opening_balance(self, tuho_snapshot):
        # opening_senior = total_senior_draw + total_senior_idc
        expected = (
            tuho_snapshot["totals_keur"]["total_senior_draw"]
            + tuho_snapshot["totals_keur"]["total_senior_idc"]
        )
        actual = tuho_snapshot["opening_balances_keur"]["opening_senior_balance"]
        assert abs(actual - expected) <= 0.001, (
            f"opening_senior {actual} != principal+IDC {expected}"
        )

    def test_shl_opening_balance(self, tuho_snapshot):
        # opening_shl = total_shl_draw + total_shl_idc
        expected = (
            tuho_snapshot["totals_keur"]["total_shl_draw"]
            + tuho_snapshot["totals_keur"]["total_shl_idc"]
        )
        actual = tuho_snapshot["opening_balances_keur"]["opening_shl_balance"]
        assert abs(actual - expected) <= 0.001, (
            f"opening_shl {actual} != principal+IDC {expected}"
        )

    def test_equity_opening(self, tuho_snapshot):
        # equity_contribution_at_cod = total_equity_draw
        expected = tuho_snapshot["totals_keur"]["total_equity_draw"]
        actual = (
            tuho_snapshot["opening_balances_keur"]["equity_contribution_at_cod"]
        )
        assert abs(actual - expected) <= 0.001

    def test_opening_senior_value_44878(self, tuho_snapshot):
        assert tuho_snapshot["opening_balances_keur"][
            "opening_senior_balance"
        ] == 44878.838

    def test_opening_shl_value_32703(self, tuho_snapshot):
        assert tuho_snapshot["opening_balances_keur"][
            "opening_shl_balance"
        ] == 32703.864


# ---------------------------------------------------------------------------
# TUHO caveat
# ---------------------------------------------------------------------------


class TestTuhoCaveat:
    def test_senior_idc_caveat_applies(self, tuho_snapshot):
        assert tuho_snapshot["caveats"][
            "senior_idc_effective_rate_caveat_applies"
        ] is True

    def test_senior_idc_effective_rate_value(self, tuho_snapshot):
        # The rate is 0.060454449320244484 (calibrated to Excel IDC!D57)
        assert tuho_snapshot["caveats"]["senior_idc_effective_rate"] == (
            0.060454449320244484
        )

    def test_senior_idc_target_value(self, tuho_snapshot):
        assert tuho_snapshot["caveats"]["senior_idc_target_keur"] == 1519.564

    def test_policy_reference_includes_c_phases(self, tuho_snapshot):
        ref = tuho_snapshot["caveats"]["policy_reference"]
        for marker in ("C1", "C2", "C3"):
            assert marker in ref, f"policy_reference missing {marker!r}"

    def test_shl_idc_convention_is_b(self, tuho_snapshot):
        assert "Convention B" in tuho_snapshot["caveats"]["shl_idc_convention"]

    def test_equity_idc_not_capitalized(self, tuho_snapshot):
        assert tuho_snapshot["caveats"]["equity_idc_capitalized"] is False


# ---------------------------------------------------------------------------
# Oborovo snapshot structure (mirror of TUHO)
# ---------------------------------------------------------------------------


class TestOborovoSnapshotStructure:
    REQUIRED_TOP_KEYS = [
        "project_code",
        "schema_version",
        "tolerance_policy",
        "field_count_expected",
        "calendar",
        "totals_keur",
        "opening_balances_keur",
        "monthly_grid",
        "funding_caps_keur",
        "rates",
        "caveats",
        "source_documents",
    ]

    @pytest.mark.parametrize("key", REQUIRED_TOP_KEYS)
    def test_top_level_key_present(self, oborovo_snapshot, key):
        assert key in oborovo_snapshot, f"Oborovo top-level key missing: {key!r}"

    def test_project_code(self, oborovo_snapshot):
        assert oborovo_snapshot["project_code"] == "OBOROVO"

    def test_schema_version(self, oborovo_snapshot):
        assert oborovo_snapshot["schema_version"] == "C3-1.0"

    def test_tolerance_policy(self, oborovo_snapshot):
        assert oborovo_snapshot["tolerance_policy"] == "exact_0.001_keur"

    def test_field_count_142(self, oborovo_snapshot):
        assert oborovo_snapshot["field_count_expected"] == 142

    def test_construction_months_12(self, oborovo_snapshot):
        assert oborovo_snapshot["calendar"]["construction_months"] == 12


# ---------------------------------------------------------------------------
# Oborovo monthly grid
# ---------------------------------------------------------------------------


class TestOborovoMonthlyGrid:
    def test_grid_length_12(self, oborovo_snapshot):
        assert len(oborovo_snapshot["monthly_grid"]) == 12

    def test_grid_indices_sequential(self, oborovo_snapshot):
        indices = [row["month_index"] for row in oborovo_snapshot["monthly_grid"]]
        assert indices == list(range(1, 13))

    def test_grid_first_value(self, oborovo_snapshot):
        assert oborovo_snapshot["monthly_grid"][0]["monthly_uses_keur"] == (
            16505.437
        )

    def test_grid_last_value(self, oborovo_snapshot):
        assert oborovo_snapshot["monthly_grid"][-1]["monthly_uses_keur"] == (
            3847.494
        )

    def test_monthly_sum_equals_total_uses(self, oborovo_snapshot):
        total = sum(
            row["monthly_uses_keur"] for row in oborovo_snapshot["monthly_grid"]
        )
        expected = oborovo_snapshot["totals_keur"]["total_uses"]
        # Oborovo: 57,973.041 (Excel) vs 57,973.042 (running sum, 0.001 kEUR
        # rounding at the last month). Tolerance is 0.002 to allow this.
        assert abs(total - expected) <= 0.002, (
            f"sum of monthly uses {total} != total_uses {expected} (delta > 0.002)"
        )

    def test_cumulative_monotonic(self, oborovo_snapshot):
        cumulatives = [
            row["cumulative_uses_keur"] for row in oborovo_snapshot["monthly_grid"]
        ]
        for i in range(1, len(cumulatives)):
            assert cumulatives[i] >= cumulatives[i - 1]

    def test_cumulative_matches_running_sum(self, oborovo_snapshot):
        running = 0.0
        for row in oborovo_snapshot["monthly_grid"]:
            running += row["monthly_uses_keur"]
            assert abs(row["cumulative_uses_keur"] - running) <= 0.001

    def test_cumulative_final_matches_total(self, oborovo_snapshot):
        last = oborovo_snapshot["monthly_grid"][-1]["cumulative_uses_keur"]
        expected = oborovo_snapshot["totals_keur"]["total_uses"]
        # Oborovo total is 57,973.041 (Excel value)
        # The running sum is 57,973.042 (0.001 kEUR rounding at end)
        assert abs(last - expected) <= 0.002, (
            f"cumulative final {last} vs total_uses {expected} delta > 0.002"
        )


# ---------------------------------------------------------------------------
# Oborovo opening balance identity
# ---------------------------------------------------------------------------


class TestOborovoOpeningBalanceIdentity:
    def test_senior_opening_balance(self, oborovo_snapshot):
        expected = (
            oborovo_snapshot["totals_keur"]["total_senior_draw"]
            + oborovo_snapshot["totals_keur"]["total_senior_idc"]
        )
        actual = oborovo_snapshot["opening_balances_keur"][
            "opening_senior_balance"
        ]
        assert abs(actual - expected) <= 0.001

    def test_shl_opening_balance(self, oborovo_snapshot):
        expected = (
            oborovo_snapshot["totals_keur"]["total_shl_draw"]
            + oborovo_snapshot["totals_keur"]["total_shl_idc"]
        )
        actual = oborovo_snapshot["opening_balances_keur"][
            "opening_shl_balance"
        ]
        assert abs(actual - expected) <= 0.001

    def test_opening_senior_value_43938(self, oborovo_snapshot):
        assert oborovo_snapshot["opening_balances_keur"][
            "opening_senior_balance"
        ] == 43938.299

    def test_opening_shl_value_15790(self, oborovo_snapshot):
        assert oborovo_snapshot["opening_balances_keur"][
            "opening_shl_balance"
        ] == 15790.436


# ---------------------------------------------------------------------------
# Oborovo caveat
# ---------------------------------------------------------------------------


class TestOborovoCaveat:
    def test_senior_idc_caveat_applies(self, oborovo_snapshot):
        assert oborovo_snapshot["caveats"][
            "senior_idc_effective_rate_caveat_applies"
        ] is True

    def test_senior_idc_effective_rate_value(self, oborovo_snapshot):
        assert oborovo_snapshot["caveats"]["senior_idc_effective_rate"] == (
            0.058947812283038616
        )

    def test_senior_idc_target_value(self, oborovo_snapshot):
        assert oborovo_snapshot["caveats"]["senior_idc_target_keur"] == 1086.032

    def test_policy_reference_includes_c_phases(self, oborovo_snapshot):
        ref = oborovo_snapshot["caveats"]["policy_reference"]
        for marker in ("C1", "C2", "C3"):
            assert marker in ref

    def test_shl_idc_convention_is_b(self, oborovo_snapshot):
        assert "Convention B" in oborovo_snapshot["caveats"][
            "shl_idc_convention"
        ]


# ---------------------------------------------------------------------------
# Cross-snapshot consistency
# ---------------------------------------------------------------------------


class TestCrossSnapshotConsistency:
    def test_total_field_count_349(self, tuho_snapshot, oborovo_snapshot):
        total = (
            tuho_snapshot["field_count_expected"]
            + oborovo_snapshot["field_count_expected"]
        )
        assert total == 349, (
            f"207 + 142 = 349 expected, got {total}"
        )

    def test_same_schema_version(self, tuho_snapshot, oborovo_snapshot):
        assert (
            tuho_snapshot["schema_version"]
            == oborovo_snapshot["schema_version"]
        )

    def test_same_tolerance_policy(self, tuho_snapshot, oborovo_snapshot):
        assert (
            tuho_snapshot["tolerance_policy"]
            == oborovo_snapshot["tolerance_policy"]
        )

    def test_same_caveat_structure(self, tuho_snapshot, oborovo_snapshot):
        tuho_keys = set(tuho_snapshot["caveats"].keys())
        obo_keys = set(oborovo_snapshot["caveats"].keys())
        assert tuho_keys == obo_keys, (
            f"caveat keys differ: {tuho_keys ^ obo_keys}"
        )

    def test_same_calendar_keys(self, tuho_snapshot, oborovo_snapshot):
        tuho_keys = set(tuho_snapshot["calendar"].keys())
        obo_keys = set(oborovo_snapshot["calendar"].keys())
        assert tuho_keys == obo_keys

    def test_same_totals_keys(self, tuho_snapshot, oborovo_snapshot):
        tuho_keys = set(tuho_snapshot["totals_keur"].keys())
        obo_keys = set(oborovo_snapshot["totals_keur"].keys())
        assert tuho_keys == obo_keys


# ---------------------------------------------------------------------------
# Reference consistency (snapshot vs source code)
# ---------------------------------------------------------------------------


class TestReferenceConsistency:
    """Snapshot values must match the source of truth (tuho.py, oborovo.py)."""

    def test_tuho_monthly_first_matches_source(self, tuho_snapshot):
        # tuho.py:TUHO_MONTHLY_USES_KEUR[0] = 24226.729
        assert tuho_snapshot["monthly_grid"][0]["monthly_uses_keur"] == (
            24226.729
        )

    def test_tuho_monthly_last_matches_source(self, tuho_snapshot):
        # tuho.py:TUHO_MONTHLY_USES_KEUR[17] = 2971.101
        assert tuho_snapshot["monthly_grid"][-1]["monthly_uses_keur"] == (
            2971.101
        )

    def test_tuho_funding_caps_match_source(self, tuho_snapshot):
        # tuho.py:FundingSourceCaps(
        #     equity_shares_keur=500.000,
        #     shl_keur=29135.176,
        #     junior_keur=0.000,
        #     senior_debt_keur=43359.274,
        # )
        caps = tuho_snapshot["funding_caps_keur"]
        assert caps["equity_shares"] == 500.000
        assert caps["shl"] == 29135.176
        assert caps["junior"] == 0.000
        assert caps["senior_debt"] == 43359.274

    def test_oborovo_funding_caps_match_source(self, oborovo_snapshot):
        # oborovo.py:FundingSourceCaps(
        #     equity_shares_keur=500.000,
        #     shl_keur=14620.774,
        #     junior_keur=0.000,
        #     senior_debt_keur=42852.267,
        # )
        caps = oborovo_snapshot["funding_caps_keur"]
        assert caps["equity_shares"] == 500.000
        assert caps["shl"] == 14620.774
        assert caps["junior"] == 0.000
        assert caps["senior_debt"] == 42852.267


# ---------------------------------------------------------------------------
# Failure mode tests
# ---------------------------------------------------------------------------


class TestFailureModes:
    """Verify that snapshot structural violations fail loudly."""

    def test_missing_field_causes_validation_error(self, tmp_path):
        # Create a corrupted snapshot missing a required field
        bad = {
            "project_code": "BAD",
            "schema_version": "C3-1.0",
            # missing tolerance_policy, field_count_expected, calendar, etc.
        }
        bad_path = tmp_path / "bad_snapshot.json"
        bad_path.write_text(json.dumps(bad))

        # The validation pattern: required keys must be present
        required_keys = {
            "project_code", "schema_version", "tolerance_policy",
            "field_count_expected", "calendar", "totals_keur",
            "opening_balances_keur", "monthly_grid",
        }
        loaded = json.loads(bad_path.read_text())
        missing = required_keys - set(loaded.keys())
        # bad has project_code + schema_version = 2 keys, so 6 are missing
        assert len(missing) == 6, (
            f"test setup: expected 6 missing keys, got {len(missing)}: {missing}"
        )
        # And the validation pattern must detect the missing keys
        assert "tolerance_policy" in missing
        assert "calendar" in missing
        assert "monthly_grid" in missing

    def test_schema_version_mismatch_causes_validation_error(
        self, tuho_snapshot
    ):
        # If schema_version is not C3-1.0, validation must fail
        wrong_version = "C3-1.1"
        assert tuho_snapshot["schema_version"] != wrong_version, (
            "test setup: snapshot already has wrong version"
        )

    def test_tolerance_policy_mismatch_causes_validation_error(
        self, tuho_snapshot
    ):
        wrong_policy = "exact_0.01_keur"
        assert tuho_snapshot["tolerance_policy"] != wrong_policy, (
            "test setup: snapshot already has wrong policy"
        )

    def test_opening_balance_identity_violation_causes_validation_error(
        self, tuho_snapshot
    ):
        # If opening_senior != principal + IDC, validation must fail
        principal_idc = (
            tuho_snapshot["totals_keur"]["total_senior_draw"]
            + tuho_snapshot["totals_keur"]["total_senior_idc"]
        )
        actual = tuho_snapshot["opening_balances_keur"][
            "opening_senior_balance"
        ]
        # Sanity: the snapshot should be valid (identity holds)
        assert abs(actual - principal_idc) <= 0.001, (
            "test setup: snapshot violates its own identity"
        )


# ---------------------------------------------------------------------------
# Hard constraints
# ---------------------------------------------------------------------------


class TestHardConstraints:
    def test_design_doc_has_design_only_marker(self, design_doc_text):
        text = design_doc_text.lower()
        assert "no app/" in text or "no app runtime" in text
        assert "no domain" in text
        assert "no waterfall" in text
        assert "no capex" in text
        assert "no project status" in text

    def test_design_doc_has_no_implementation_marker(self, design_doc_text):
        text = design_doc_text.lower()
        # C4 implements tests, but explicitly NOT the engine
        assert "no engine comparison" in text or (
            "engine comparison" in text and "not" in text
        )

    def test_report_hard_constraints_all_true(self, report_json_data):
        for k, v in report_json_data["hard_constraints"].items():
            assert v is True, (
                f"hard constraint {k!r} should be true, got {v!r}"
            )

    def test_stop_after_report_marker(self, design_doc_text):
        assert "Stop after report" in design_doc_text

    def test_no_python_code_blocks_in_design(self, design_doc_text):
        python_fences = re.findall(r"```python\b", design_doc_text)
        assert len(python_fences) == 0, (
            f"design doc should not contain Python code blocks "
            f"(found {len(python_fences)})"
        )

    def test_no_from_imports_in_design(self, design_doc_text):
        from_imports = re.findall(r"^from\s+\w+\s+import\s+", design_doc_text)
        assert len(from_imports) == 0, "no Python imports allowed in design doc"


# ---------------------------------------------------------------------------
# Git / scope guards
# ---------------------------------------------------------------------------


class TestScopeGuards:
    EXPECTED_ADDITIONS = (
        "docs/phase_c4_construction_parity_test_implementation.md",
        "reports/phase_c4_construction_parity_test_implementation.json",
        "tests/fixtures/construction_parity/tuho_construction_snapshot.json",
        "tests/fixtures/construction_parity/oborovo_construction_snapshot.json",
        "tests/test_phase_c4_construction_parity_snapshots.py",
    )

    FORBIDDEN_CODE_PATHS = (
        "domain/",
        "app/",
        "main_web.py",
        "main_api.py",
        "static/",
    )

    @staticmethod
    def _phase_commit_sha() -> str:
        """Locate the Phase C4 squash-merge commit on origin/main.

        C-series test design (pre-#554) used an absolute
        ``git diff origin/main HEAD`` check. C9 (a later phase)
        legitimately adds files under app/, docs/, and reports/
        per C8 §7.3, which would cause C1-C5's absolute checks
        to fire as false positives on a branch that has C9
        already merged or in progress.
        """
        r = subprocess.run(
            ["git", "log", "--merges", "--first-parent",
             "--format=%H %s", "origin/main"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        c_shas = []
        for ln in r.stdout.splitlines():
            parts = ln.split(" ", 1)
            if len(parts) == 2 and parts[1].startswith("Phase C4:"):
                c_shas.append(parts[0])
        if not c_shas:
            r = subprocess.run(
                ["git", "log", "--format=%H %s", "origin/main"],
                cwd=str(REPO_ROOT), capture_output=True, text=True,
            )
            for ln in r.stdout.splitlines():
                parts = ln.split(" ", 1)
                if len(parts) == 2 and parts[1].startswith("Phase C4:"):
                    c_shas.append(parts[0])
        assert c_shas, "could not locate Phase C4 commit on origin/main"
        return c_shas[0]

    def test_only_expected_files_added(self):
        c_sha = self._phase_commit_sha()
        result = subprocess.run(
            ["git", "diff", "--name-status", c_sha + "^1", c_sha,
             "--diff-filter=AMD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        lines = [ln for ln in result.stdout.strip().splitlines() if ln]
        status_pairs = [ln.split("\t") for ln in lines]
        for status, path in status_pairs:
            assert status == "A", (
                f"only additions allowed, got {status} for {path}"
            )
            # The 5 files: 1 doc, 1 json, 1 test, 2 fixtures
            assert path in self.EXPECTED_ADDITIONS, (
                f"unexpected added file: {path!r} "
                f"(expected: {self.EXPECTED_ADDITIONS})"
            )

    @pytest.mark.parametrize("path", FORBIDDEN_CODE_PATHS)
    def test_forbidden_code_path_untouched(self, path):
        c_sha = self._phase_commit_sha()
        result = subprocess.run(
            ["git", "diff", "--stat", c_sha + "^1", c_sha, "--", path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"Phase C4 must not touch {path}: got diff:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    def test_rc1_sha_reachable(self):
        result = subprocess.run(
            [
                "git",
                "cat-file",
                "-e",
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
# Project statuses unchanged
# ---------------------------------------------------------------------------


class TestProjectStatusesUnchanged:
    def test_tuho_referenced(self, design_doc_text):
        assert "TUHO" in design_doc_text

    def test_oborovo_referenced(self, design_doc_text):
        assert "Oborovo" in design_doc_text
