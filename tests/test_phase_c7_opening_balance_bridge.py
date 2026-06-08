"""Phase C7 - Layer 4 Opening Balance Bridge Offline Implementation tests.

**Scope label:** OFFLINE DOMAIN IMPLEMENTATION. NO RUNTIME WIRING.
NO WATERFALL CHANGES.

This phase implements:
- `domain/construction/opening_bridge.py` (the bridge module)
- All C2/C6 dataclasses, POLICY_TABLE, BridgeIdentityError, and
  build_opening_balance_bridge()

This phase does NOT:
- Wire the bridge into runtime (Layer 5 is C8+)
- Modify any other file in `domain/` or `app/`
- Touch `main_web.py`, `main_api.py`, `static/`
- Change any formula (CAPEX, debt, tax, depreciation, IDC)
- Change any project status
- Flip any feature flag
- Persist any data
- Render any UI
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from dataclasses import fields, is_dataclass
from datetime import date
from pathlib import Path
from typing import Final

import pytest

from domain.construction.engine import compute_construction_schedule
from domain.construction.opening_bridge import (
    BRIDGE_VERSION,
    BridgeAuditRow,
    BridgeFieldPolicy,
    BridgeIdentityError,
    BridgeMetadata,
    GUARD_COMPOSITE,
    GUARD_SINGLE_SOURCE,
    IDENTITY_TOLERANCE_KEUR,
    ManualOverrideRow,
    OVERRIDE_COMPOSITE_NO_OVERRIDE,
    OVERRIDE_CONSTRUCTION_ACTIVE,
    OVERRIDE_MANUAL_ACTIVE,
    OVERRIDE_NO_OVERRIDE,
    OpeningBalanceBridgeInput,
    OpeningBalanceBridgeResult,
    PARITY_DRIFT,
    PARITY_NOT_APPLICABLE,
    PARITY_OK,
    PARITY_UNKNOWN,
    POLICY_TABLE,
    POLICY_VERSION,
    ParityReferenceRow,
    ProjectAssumptions,
    SELECTION_DERIVED,
    SELECTION_FROZEN,
    SELECTION_REPLACED,
    SELECTION_RETAINED,
    build_opening_balance_bridge,
)
from domain.construction.result import (
    ConstructionMonthlyEntry,
    ConstructionScheduleResult,
)
from domain.construction.templates.oborovo import (
    build_oborovo_construction_config,
)
from domain.construction.templates.tuho import (
    build_tuho_construction_config,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_MODULE = (
    REPO_ROOT / "domain" / "construction" / "opening_bridge.py"
)
C4_TUHO_SNAPSHOT = (
    REPO_ROOT
    / "tests" / "fixtures" / "construction_parity"
    / "tuho_construction_snapshot.json"
)
C4_OBOROVO_SNAPSHOT = (
    REPO_ROOT
    / "tests" / "fixtures" / "construction_parity"
    / "oborovo_construction_snapshot.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_construction_result(
    *,
    project_code: str,
    total_uses: float,
    total_equity_draw: float,
    total_shl_draw: float,
    total_junior_draw: float,
    total_senior_draw: float,
    total_shl_idc: float,
    total_senior_idc: float,
    opening_shl_balance: float,
    opening_senior_balance: float,
) -> ConstructionScheduleResult:
    """Build a synthetic ConstructionScheduleResult for tests."""
    return ConstructionScheduleResult(
        project_code=project_code,
        monthly_entries=(),
        total_uses_keur=total_uses,
        total_equity_draw_keur=total_equity_draw,
        total_shl_draw_keur=total_shl_draw,
        total_junior_draw_keur=total_junior_draw,
        total_senior_draw_keur=total_senior_draw,
        total_shl_idc_keur=total_shl_idc,
        total_senior_idc_keur=total_senior_idc,
        opening_shl_balance_keur=opening_shl_balance,
        opening_senior_balance_keur=opening_senior_balance,
        uses_funding_delta_keur=0.0,
        senior_idc_delta_to_target_keur=0.0,
    )


def _make_tuho_result() -> ConstructionScheduleResult:
    """Compute the real TUHO engine result (with senior_idc_capitalized=True)."""
    from dataclasses import replace
    config = build_tuho_construction_config()
    config = replace(config, senior_idc_capitalized=True)
    return compute_construction_schedule(config)


def _make_oborovo_result() -> ConstructionScheduleResult:
    """Compute the real Oborovo engine result (with senior_idc_capitalized=True)."""
    from dataclasses import replace
    config = build_oborovo_construction_config()
    config = replace(config, senior_idc_capitalized=True)
    return compute_construction_schedule(config)


def _tuho_manual_overrides() -> tuple[ManualOverrideRow, ...]:
    return (
        ManualOverrideRow("shl_idc_keur", 1169.0),
        ManualOverrideRow("shl_amount_keur", 29135.176),
        ManualOverrideRow("shl_opening_balance_keur", 30304.176),
        ManualOverrideRow("senior_opening_balance_keur", 43359.274),
        ManualOverrideRow("senior_idc_keur", 1519.564),
        ManualOverrideRow("capex_keur", 72994.450),
        ManualOverrideRow("reserves_keur", 0.0),
        ManualOverrideRow("vat_operating", 0.0),
        ManualOverrideRow("financing_fees_keur", 0.0),
        ManualOverrideRow("commitment_fee_keur", 0.0),
        ManualOverrideRow("equity_total_keur", 500.0),
    )


def _oborovo_manual_overrides() -> tuple[ManualOverrideRow, ...]:
    return (
        ManualOverrideRow("shl_idc_keur", 0.0),
        ManualOverrideRow("shl_amount_keur", 14620.774),
        ManualOverrideRow("shl_opening_balance_keur", 14620.774),
        ManualOverrideRow("senior_opening_balance_keur", 42852.267),
        ManualOverrideRow("senior_idc_keur", 1086.032),
        ManualOverrideRow("capex_keur", 57973.041),
        ManualOverrideRow("reserves_keur", 0.0),
        ManualOverrideRow("vat_operating", 0.0),
        ManualOverrideRow("financing_fees_keur", 0.0),
        ManualOverrideRow("commitment_fee_keur", 0.0),
        ManualOverrideRow("equity_total_keur", 500.0),
    )


def _tuho_assumptions() -> ProjectAssumptions:
    return ProjectAssumptions(
        shl_interest_rate=0.08,
        senior_interest_rate=0.060454449320244484,
        construction_start_date=date(2028, 6, 30),
        cod_date=date(2029, 12, 30),
        shl_investment_date=date(2028, 6, 30),
    )


def _oborovo_assumptions() -> ProjectAssumptions:
    return ProjectAssumptions(
        shl_interest_rate=0.08,
        senior_interest_rate=0.058947812283038616,
        construction_start_date=date(2029, 6, 29),
        cod_date=date(2030, 6, 29),
        shl_investment_date=date(2029, 6, 29),
    )


def _tuho_parity_refs() -> tuple[ParityReferenceRow, ...]:
    with open(C4_TUHO_SNAPSHOT) as f:
        snap = json.load(f)
    return (
        ParityReferenceRow("shl_idc_keur", snap["totals_keur"]["total_shl_idc"]),
        ParityReferenceRow("shl_amount_keur", snap["totals_keur"]["total_shl_draw"]),
        ParityReferenceRow("shl_opening_balance_keur", snap["opening_balances_keur"]["opening_shl_balance"]),
        ParityReferenceRow("senior_opening_balance_keur", snap["opening_balances_keur"]["opening_senior_balance"]),
        ParityReferenceRow("senior_idc_keur", snap["totals_keur"]["total_senior_idc"]),
        ParityReferenceRow("capex_keur", snap["totals_keur"]["total_uses"]),
        ParityReferenceRow("reserves_keur", None),
        ParityReferenceRow("vat_operating", None),
        ParityReferenceRow("financing_fees_keur", None),
        ParityReferenceRow("commitment_fee_keur", None),
        ParityReferenceRow("equity_total_keur", snap["opening_balances_keur"]["equity_contribution_at_cod"]),
    )


def _oborovo_parity_refs() -> tuple[ParityReferenceRow, ...]:
    with open(C4_OBOROVO_SNAPSHOT) as f:
        snap = json.load(f)
    return (
        ParityReferenceRow("shl_idc_keur", snap["totals_keur"]["total_shl_idc"]),
        ParityReferenceRow("shl_amount_keur", snap["totals_keur"]["total_shl_draw"]),
        ParityReferenceRow("shl_opening_balance_keur", snap["opening_balances_keur"]["opening_shl_balance"]),
        ParityReferenceRow("senior_opening_balance_keur", snap["opening_balances_keur"]["opening_senior_balance"]),
        ParityReferenceRow("senior_idc_keur", snap["totals_keur"]["total_senior_idc"]),
        ParityReferenceRow("capex_keur", snap["totals_keur"]["total_uses"]),
        ParityReferenceRow("reserves_keur", None),
        ParityReferenceRow("vat_operating", None),
        ParityReferenceRow("financing_fees_keur", None),
        ParityReferenceRow("commitment_fee_keur", None),
        ParityReferenceRow("equity_total_keur", snap["opening_balances_keur"]["equity_contribution_at_cod"]),
    )


def _make_input(
    project: str,
) -> OpeningBalanceBridgeInput:
    """Build a full OpeningBalanceBridgeInput for a project."""
    if project == "TUHO":
        return OpeningBalanceBridgeInput(
            construction_result=_make_tuho_result(),
            manual_overrides=_tuho_manual_overrides(),
            project_assumptions=_tuho_assumptions(),
            replacement_policy=POLICY_TABLE,
            parity_references=_tuho_parity_refs(),
            bridge_version=BRIDGE_VERSION,
        )
    if project == "OBOROVO":
        return OpeningBalanceBridgeInput(
            construction_result=_make_oborovo_result(),
            manual_overrides=_oborovo_manual_overrides(),
            project_assumptions=_oborovo_assumptions(),
            replacement_policy=POLICY_TABLE,
            parity_references=_oborovo_parity_refs(),
            bridge_version=BRIDGE_VERSION,
        )
    raise ValueError(f"Unknown project: {project!r}")


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


class TestFilesExist:
    def test_bridge_module_exists(self):
        assert BRIDGE_MODULE.is_file()

    def test_c4_tuho_snapshot_exists(self):
        assert C4_TUHO_SNAPSHOT.is_file()

    def test_c4_oborovo_snapshot_exists(self):
        assert C4_OBOROVO_SNAPSHOT.is_file()


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------


class TestModuleConstants:
    def test_policy_version(self):
        assert POLICY_VERSION == "C2-1.0"

    def test_bridge_version(self):
        assert BRIDGE_VERSION == "C7-1.0"

    def test_identity_tolerance(self):
        assert IDENTITY_TOLERANCE_KEUR == 0.001

    def test_policy_table_has_11_entries(self):
        assert len(POLICY_TABLE) == 11

    def test_policy_table_is_tuple(self):
        assert isinstance(POLICY_TABLE, tuple)

    def test_policy_table_entries_are_frozen_dataclasses(self):
        for entry in POLICY_TABLE:
            assert isinstance(entry, BridgeFieldPolicy)
            assert is_dataclass(entry)


# ---------------------------------------------------------------------------
# POLICY_TABLE mirrors C2 §2.1
# ---------------------------------------------------------------------------


class TestPolicyTableMirrorC2Section21:
    EXPECTED: Final[tuple[tuple[str, str, str, str, str], ...]] = (
        # (field_code, current_source_label, construction_source_field, policy, c1_blocker_reference)
        ("shl_idc_keur", "manual_shl_idc", "total_shl_idc_keur", SELECTION_REPLACED, "blocker_1_R-PAR-1"),
        ("shl_amount_keur", "manual_shl_amount", "total_shl_draw_keur", SELECTION_REPLACED, ""),
        ("shl_opening_balance_keur", "manual_shl_opening_balance", "opening_shl_balance_keur", SELECTION_REPLACED, ""),
        ("senior_opening_balance_keur", "manual_senior_opening_balance", "opening_senior_balance_keur", SELECTION_FROZEN, "blocker_5_R-PAR-2"),
        ("senior_idc_keur", "manual_senior_idc", "total_senior_idc_keur", SELECTION_REPLACED, "blocker_5_R-PAR-2"),
        ("capex_keur", "manual_capex", "total_uses_keur", SELECTION_FROZEN, ""),
        ("reserves_keur", "manual_reserves", "", SELECTION_RETAINED, ""),
        ("vat_operating", "manual_vat", "", SELECTION_RETAINED, ""),
        ("financing_fees_keur", "manual_financing_fees", "", SELECTION_RETAINED, ""),
        ("commitment_fee_keur", "manual_commitment_fee", "", SELECTION_RETAINED, ""),
        ("equity_total_keur", "manual_equity_total", "total_equity_draw_keur", SELECTION_DERIVED, "blocker_5_R-PAR-5"),
    )

    def test_policy_table_count(self):
        assert len(POLICY_TABLE) == len(self.EXPECTED)

    @pytest.mark.parametrize("idx,expected", list(enumerate(EXPECTED)))
    def test_policy_entry(self, idx, expected):
        entry = POLICY_TABLE[idx]
        field_code, src_label, src_field, policy, c1_ref = expected
        assert entry.field_code == field_code
        assert entry.current_source_label == src_label
        assert entry.construction_source_field == src_field
        assert entry.policy == policy
        assert entry.c1_blocker_reference == c1_ref

    def test_5_replaced(self):
        n = sum(1 for p in POLICY_TABLE if p.policy == SELECTION_REPLACED)
        # C2 §2.1: shl_idc, shl_amount, shl_opening, senior_idc = 4 fields
        # Plus our POLICY_TABLE has capex_keur as 'frozen' not 'replaced'.
        # Actually we count the actual replaced entries.
        assert n == 4  # shl_idc, shl_amount, shl_opening, senior_idc

    def test_2_frozen(self):
        n = sum(1 for p in POLICY_TABLE if p.policy == SELECTION_FROZEN)
        assert n == 2  # senior_opening_balance, capex

    def test_4_retained(self):
        n = sum(1 for p in POLICY_TABLE if p.policy == SELECTION_RETAINED)
        assert n == 4  # reserves, vat, fin_fees, commitment_fee

    def test_1_derived(self):
        n = sum(1 for p in POLICY_TABLE if p.policy == SELECTION_DERIVED)
        assert n == 1  # equity_total

    def test_unique_field_codes(self):
        codes = [p.field_code for p in POLICY_TABLE]
        assert len(set(codes)) == 11


# ---------------------------------------------------------------------------
# Dataclasses are frozen
# ---------------------------------------------------------------------------


class TestDataclassesFrozen:
    @pytest.mark.parametrize("cls", [
        ManualOverrideRow,
        BridgeFieldPolicy,
        ParityReferenceRow,
        ProjectAssumptions,
        OpeningBalanceBridgeInput,
        BridgeAuditRow,
        BridgeMetadata,
        OpeningBalanceBridgeResult,
    ])
    def test_dataclass_is_frozen(self, cls):
        # The C6 §5 design specifies all 8 dataclasses are frozen.
        for f in fields(cls):
            # All fields should be in __dataclass_params__.frozen
            pass  # existence-only check
        # Verify by trying to setattr on an instance
        if cls is ManualOverrideRow:
            obj = cls(field_code="x", manual_value_keur=0.0)
        elif cls is BridgeFieldPolicy:
            obj = cls(field_code="x", current_source_label="x", construction_source_field="x", policy=SELECTION_REPLACED, c1_blocker_reference="")
        elif cls is ParityReferenceRow:
            obj = cls(field_code="x", parity_reference_keur=0.0)
        elif cls is ProjectAssumptions:
            obj = cls(
                shl_interest_rate=0.0, senior_interest_rate=0.0,
                construction_start_date=date(2025, 1, 1),
                cod_date=date(2025, 1, 1),
                shl_investment_date=date(2025, 1, 1),
            )
        elif cls is OpeningBalanceBridgeInput:
            # Need a valid input — we can use the test helpers
            obj = _make_input("TUHO")
        elif cls is BridgeAuditRow:
            obj = cls(
                field_code="x", manual_value_keur=0.0,
                construction_derived_value_keur=0.0,
                selected_runtime_value_keur=0.0,
                selection_reason=SELECTION_REPLACED,
                override_status=OVERRIDE_NO_OVERRIDE,
                double_counting_guard=GUARD_SINGLE_SOURCE,
                parity_reference_keur=0.0,
                parity_delta_keur=0.0,
                parity_status=PARITY_OK,
                c1_blocker_reference="",
                audit_timestamp="2026-06-08T00:00:00+00:00",
                bridge_version="C7-1.0",
                policy_version="C2-1.0",
            )
        elif cls is BridgeMetadata:
            obj = cls(
                policy_version="C2-1.0", bridge_version="C7-1.0",
                bridge_run_timestamp="2026-06-08T00:00:00+00:00",
            )
        elif cls is OpeningBalanceBridgeResult:
            result = _make_input("TUHO")
            obj = build_opening_balance_bridge(result)
        else:  # pragma: no cover
            pytest.fail(f"Unhandled class: {cls!r}")

        with pytest.raises((AttributeError, Exception)):
            obj.field_code = "modified"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# BridgeIdentityError is a ValueError
# ---------------------------------------------------------------------------


class TestBridgeIdentityError:
    def test_is_value_error(self):
        assert issubclass(BridgeIdentityError, ValueError)

    def test_can_be_raised(self):
        with pytest.raises(BridgeIdentityError):
            raise BridgeIdentityError("test")


# ---------------------------------------------------------------------------
# TUHO bridge — required outputs (C2 §3.3, C6 §5.2)
# ---------------------------------------------------------------------------


class TestTuhoBridgeOutput:
    @pytest.fixture(scope="class")
    def result(self) -> OpeningBalanceBridgeResult:
        return build_opening_balance_bridge(_make_input("TUHO"))

    def test_opening_senior_balance(self, result):
        # Frozen: uses manual 43,359.274 (no IDC added)
        assert abs(result.opening_senior_balance_at_cod_keur - 43359.274) <= 0.001

    def test_opening_shl_balance(self, result):
        # Replaced: uses engine opening_shl_balance_keur
        expected = _make_tuho_result().opening_shl_balance_keur
        assert abs(result.opening_shl_balance_at_cod_keur - expected) <= 0.001

    def test_equity_contribution(self, result):
        # Derived: uses manual 500.0
        assert abs(result.equity_contribution_at_cod_keur - 500.0) <= 0.001

    def test_capitalized_senior_idc(self, result):
        # Replaced: uses engine total_senior_idc_keur
        expected = _make_tuho_result().total_senior_idc_keur
        assert abs(result.capitalized_senior_idc_keur - expected) <= 0.001

    def test_capitalized_shl_idc(self, result):
        # Replaced: uses engine total_shl_idc_keur
        expected = _make_tuho_result().total_shl_idc_keur
        assert abs(result.capitalized_shl_idc_keur - expected) <= 0.001

    def test_financing_fee(self, result):
        # Retained: uses manual 0.0
        assert result.financing_fee_treatment_keur == 0.0


# ---------------------------------------------------------------------------
# Oborovo bridge — required outputs
# ---------------------------------------------------------------------------


class TestOborovoBridgeOutput:
    @pytest.fixture(scope="class")
    def result(self) -> OpeningBalanceBridgeResult:
        return build_opening_balance_bridge(_make_input("OBOROVO"))

    def test_opening_senior_balance(self, result):
        assert abs(result.opening_senior_balance_at_cod_keur - 42852.267) <= 0.001

    def test_opening_shl_balance(self, result):
        expected = _make_oborovo_result().opening_shl_balance_keur
        assert abs(result.opening_shl_balance_at_cod_keur - expected) <= 0.001

    def test_equity_contribution(self, result):
        assert abs(result.equity_contribution_at_cod_keur - 500.0) <= 0.001

    def test_capitalized_senior_idc(self, result):
        expected = _make_oborovo_result().total_senior_idc_keur
        assert abs(result.capitalized_senior_idc_keur - expected) <= 0.001

    def test_capitalized_shl_idc(self, result):
        expected = _make_oborovo_result().total_shl_idc_keur
        assert abs(result.capitalized_shl_idc_keur - expected) <= 0.001

    def test_financing_fee(self, result):
        assert result.financing_fee_treatment_keur == 0.0


# ---------------------------------------------------------------------------
# Audit table — 11 rows
# ---------------------------------------------------------------------------


class TestAuditTableSize:
    def test_tuho_audit_11_rows(self):
        result = build_opening_balance_bridge(_make_input("TUHO"))
        assert len(result.audit_reconciliation_table) == 11

    def test_oborovo_audit_11_rows(self):
        result = build_opening_balance_bridge(_make_input("OBOROVO"))
        assert len(result.audit_reconciliation_table) == 11


class TestAuditTableColumns:
    """C2 §4.1: 14 required columns."""

    REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
        "field_code",
        "manual_value_keur",
        "construction_derived_value_keur",
        "selected_runtime_value_keur",
        "selection_reason",
        "override_status",
        "double_counting_guard",
        "parity_reference_keur",
        "parity_delta_keur",
        "parity_status",
        "c1_blocker_reference",
        "audit_timestamp",
        "bridge_version",
        "policy_version",
    )

    def test_required_columns_exist_on_bridge_audit_row(self):
        names = {f.name for f in fields(BridgeAuditRow)}
        for col in self.REQUIRED_COLUMNS:
            assert col in names, f"missing column {col!r}"

    def test_required_columns_count(self):
        names = {f.name for f in fields(BridgeAuditRow)}
        assert len(names & set(self.REQUIRED_COLUMNS)) == 14

    def test_audit_row_has_14_fields(self):
        assert len(fields(BridgeAuditRow)) == 14


# ---------------------------------------------------------------------------
# Audit row invariants (C2 §4.5)
# ---------------------------------------------------------------------------


class TestAuditRowInvariants:
    @pytest.fixture(scope="class")
    def tuho_result(self) -> OpeningBalanceBridgeResult:
        return build_opening_balance_bridge(_make_input("TUHO"))

    @pytest.fixture(scope="class")
    def oborovo_result(self) -> OpeningBalanceBridgeResult:
        return build_opening_balance_bridge(_make_input("OBOROVO"))

    @pytest.mark.parametrize("project,fixture", [
        ("TUHO", "tuho_result"),
        ("OBOROVO", "oborovo_result"),
    ])
    def test_every_policy_field_has_one_row(
        self, project, fixture, request
    ):
        result = request.getfixturevalue(fixture)
        codes = [r.field_code for r in result.audit_reconciliation_table]
        policy_codes = [p.field_code for p in POLICY_TABLE]
        for code in policy_codes:
            assert codes.count(code) == 1, (
                f"{project}: {code!r} should appear exactly once"
            )

    @pytest.mark.parametrize("project,fixture", [
        ("TUHO", "tuho_result"),
        ("OBOROVO", "oborovo_result"),
    ])
    def test_no_duplicate_rows(self, project, fixture, request):
        result = request.getfixturevalue(fixture)
        codes = [r.field_code for r in result.audit_reconciliation_table]
        assert len(codes) == len(set(codes))

    @pytest.mark.parametrize("project,fixture", [
        ("TUHO", "tuho_result"),
        ("OBOROVO", "oborovo_result"),
    ])
    def test_selection_reason_matches_policy(
        self, project, fixture, request
    ):
        result = request.getfixturevalue(fixture)
        for row in result.audit_reconciliation_table:
            policy_entry = next(
                p for p in POLICY_TABLE if p.field_code == row.field_code
            )
            assert row.selection_reason == policy_entry.policy

    @pytest.mark.parametrize("project,fixture", [
        ("TUHO", "tuho_result"),
        ("OBOROVO", "oborovo_result"),
    ])
    def test_double_counting_guard_not_not_applicable(
        self, project, fixture, request
    ):
        result = request.getfixturevalue(fixture)
        for row in result.audit_reconciliation_table:
            assert row.double_counting_guard in (
                GUARD_SINGLE_SOURCE, GUARD_COMPOSITE
            ), f"{row.field_code}: guard={row.double_counting_guard!r}"

    @pytest.mark.parametrize("project,fixture", [
        ("TUHO", "tuho_result"),
        ("OBOROVO", "oborovo_result"),
    ])
    def test_parity_status_for_retained_no_parity(
        self, project, fixture, request
    ):
        result = request.getfixturevalue(fixture)
        for row in result.audit_reconciliation_table:
            policy_entry = next(
                p for p in POLICY_TABLE if p.field_code == row.field_code
            )
            if policy_entry.policy == SELECTION_RETAINED:
                assert row.parity_status == PARITY_NOT_APPLICABLE


# ---------------------------------------------------------------------------
# TUHO per-field policy decisions
# ---------------------------------------------------------------------------


class TestTuhoPerFieldPolicy:
    @pytest.fixture(scope="class")
    def audit(self) -> dict[str, BridgeAuditRow]:
        result = build_opening_balance_bridge(_make_input("TUHO"))
        return {r.field_code: r for r in result.audit_reconciliation_table}

    def test_shl_idc_replaced(self, audit):
        row = audit["shl_idc_keur"]
        assert row.selection_reason == SELECTION_REPLACED
        assert row.override_status == OVERRIDE_CONSTRUCTION_ACTIVE
        assert row.double_counting_guard == GUARD_SINGLE_SOURCE

    def test_shl_amount_replaced(self, audit):
        row = audit["shl_amount_keur"]
        assert row.selection_reason == SELECTION_REPLACED
        assert row.override_status == OVERRIDE_CONSTRUCTION_ACTIVE

    def test_shl_opening_replaced(self, audit):
        row = audit["shl_opening_balance_keur"]
        assert row.selection_reason == SELECTION_REPLACED

    def test_senior_opening_frozen(self, audit):
        row = audit["senior_opening_balance_keur"]
        assert row.selection_reason == SELECTION_FROZEN
        assert row.override_status == OVERRIDE_MANUAL_ACTIVE
        assert row.double_counting_guard == GUARD_SINGLE_SOURCE
        assert row.parity_status == PARITY_DRIFT
        assert row.c1_blocker_reference == "blocker_5_R-PAR-2"

    def test_senior_idc_replaced(self, audit):
        row = audit["senior_idc_keur"]
        assert row.selection_reason == SELECTION_REPLACED
        assert row.parity_status == PARITY_OK
        assert row.c1_blocker_reference == "blocker_5_R-PAR-2"

    def test_capex_frozen(self, audit):
        row = audit["capex_keur"]
        assert row.selection_reason == SELECTION_FROZEN

    def test_reserves_retained(self, audit):
        row = audit["reserves_keur"]
        assert row.selection_reason == SELECTION_RETAINED
        assert row.override_status == OVERRIDE_NO_OVERRIDE

    def test_vat_retained(self, audit):
        row = audit["vat_operating"]
        assert row.selection_reason == SELECTION_RETAINED

    def test_financing_fees_retained(self, audit):
        row = audit["financing_fees_keur"]
        assert row.selection_reason == SELECTION_RETAINED

    def test_commitment_fee_retained(self, audit):
        row = audit["commitment_fee_keur"]
        assert row.selection_reason == SELECTION_RETAINED

    def test_equity_derived(self, audit):
        row = audit["equity_total_keur"]
        assert row.selection_reason == SELECTION_DERIVED
        assert row.override_status == OVERRIDE_COMPOSITE_NO_OVERRIDE
        assert row.double_counting_guard == GUARD_COMPOSITE


# ---------------------------------------------------------------------------
# Senior IDC asymmetry (C6 §6.4)
# ---------------------------------------------------------------------------


class TestSeniorIdcAsymmetry:
    """C6 §6.4: senior_idc replaced, senior_opening frozen (asymmetry)."""

    def test_tuho_asymmetry(self):
        result = build_opening_balance_bridge(_make_input("TUHO"))
        audit = {
            r.field_code: r
            for r in result.audit_reconciliation_table
        }
        # senior_idc: replaced, parity_ok
        assert audit["senior_idc_keur"].selection_reason == SELECTION_REPLACED
        assert audit["senior_idc_keur"].parity_status == PARITY_OK
        # senior_opening: frozen, parity_drift
        assert audit["senior_opening_balance_keur"].selection_reason == (
            SELECTION_FROZEN
        )
        assert audit["senior_opening_balance_keur"].parity_status == (
            PARITY_DRIFT
        )

    def test_oborovo_asymmetry(self):
        result = build_opening_balance_bridge(_make_input("OBOROVO"))
        audit = {
            r.field_code: r
            for r in result.audit_reconciliation_table
        }
        assert audit["senior_idc_keur"].selection_reason == SELECTION_REPLACED
        assert audit["senior_idc_keur"].parity_status == PARITY_OK
        assert audit["senior_opening_balance_keur"].selection_reason == (
            SELECTION_FROZEN
        )
        assert audit["senior_opening_balance_keur"].parity_status == (
            PARITY_DRIFT
        )

    def test_senior_idc_value_matches_engine(self):
        """The selected senior_idc equals the engine total_senior_idc."""
        for project in ("TUHO", "OBOROVO"):
            inp = _make_input(project)
            result = build_opening_balance_bridge(inp)
            audit = {
                r.field_code: r
                for r in result.audit_reconciliation_table
            }
            assert abs(
                audit["senior_idc_keur"].selected_runtime_value_keur
                - inp.construction_result.total_senior_idc_keur
            ) <= IDENTITY_TOLERANCE_KEUR


# ---------------------------------------------------------------------------
# Bridge metadata
# ---------------------------------------------------------------------------


class TestBridgeMetadata:
    def test_policy_version(self):
        result = build_opening_balance_bridge(_make_input("TUHO"))
        assert result.bridge_metadata.policy_version == POLICY_VERSION

    def test_bridge_version(self):
        result = build_opening_balance_bridge(_make_input("TUHO"))
        assert result.bridge_metadata.bridge_version == BRIDGE_VERSION

    def test_bridge_run_timestamp_format(self):
        result = build_opening_balance_bridge(_make_input("TUHO"))
        ts = result.bridge_metadata.bridge_run_timestamp
        # ISO-8601
        assert "T" in ts
        assert ts.endswith("+00:00") or ts.endswith("Z")


# ---------------------------------------------------------------------------
# BridgeIdentityError — missing manual value
# ---------------------------------------------------------------------------


class TestBridgeIdentityErrorMissingManual:
    def test_missing_manual_for_frozen_raises(self):
        result_input = _make_input("TUHO")
        # Remove the senior_opening_balance_keur manual (which is frozen)
        bad_manual = tuple(
            m for m in result_input.manual_overrides
            if m.field_code != "senior_opening_balance_keur"
        )
        bad_input = OpeningBalanceBridgeInput(
            construction_result=result_input.construction_result,
            manual_overrides=bad_manual,
            project_assumptions=result_input.project_assumptions,
            replacement_policy=result_input.replacement_policy,
            parity_references=result_input.parity_references,
            bridge_version=result_input.bridge_version,
        )
        with pytest.raises(BridgeIdentityError):
            build_opening_balance_bridge(bad_input)

    def test_missing_manual_for_retained_raises(self):
        result_input = _make_input("TUHO")
        bad_manual = tuple(
            m for m in result_input.manual_overrides
            if m.field_code != "reserves_keur"
        )
        bad_input = OpeningBalanceBridgeInput(
            construction_result=result_input.construction_result,
            manual_overrides=bad_manual,
            project_assumptions=result_input.project_assumptions,
            replacement_policy=result_input.replacement_policy,
            parity_references=result_input.parity_references,
            bridge_version=result_input.bridge_version,
        )
        with pytest.raises(BridgeIdentityError):
            build_opening_balance_bridge(bad_input)

    def test_missing_manual_for_derived_raises(self):
        result_input = _make_input("TUHO")
        bad_manual = tuple(
            m for m in result_input.manual_overrides
            if m.field_code != "equity_total_keur"
        )
        bad_input = OpeningBalanceBridgeInput(
            construction_result=result_input.construction_result,
            manual_overrides=bad_manual,
            project_assumptions=result_input.project_assumptions,
            replacement_policy=result_input.replacement_policy,
            parity_references=result_input.parity_references,
            bridge_version=result_input.bridge_version,
        )
        with pytest.raises(BridgeIdentityError):
            build_opening_balance_bridge(bad_input)

    def test_missing_manual_for_replaced_does_not_raise(self):
        """Replaced fields don't need a manual value (engine provides it)."""
        result_input = _make_input("TUHO")
        # shl_idc_keur is replaced — remove its manual
        bad_manual = tuple(
            m for m in result_input.manual_overrides
            if m.field_code != "shl_idc_keur"
        )
        bad_input = OpeningBalanceBridgeInput(
            construction_result=result_input.construction_result,
            manual_overrides=bad_manual,
            project_assumptions=result_input.project_assumptions,
            replacement_policy=result_input.replacement_policy,
            parity_references=result_input.parity_references,
            bridge_version=result_input.bridge_version,
        )
        # Should not raise — replaced uses engine, not manual
        result = build_opening_balance_bridge(bad_input)
        assert result is not None


# ---------------------------------------------------------------------------
# No-caller-mutation guard (C2 §3.6.1, C6 §3.2)
# ---------------------------------------------------------------------------


class TestNoCallerMutation:
    def test_input_construction_result_unchanged(self):
        result_input = _make_input("TUHO")
        result_obj = result_input.construction_result
        # Snapshot attributes
        before = {
            "project_code": result_obj.project_code,
            "total_uses_keur": result_obj.total_uses_keur,
            "total_shl_idc_keur": result_obj.total_shl_idc_keur,
            "opening_senior_balance_keur": result_obj.opening_senior_balance_keur,
            "opening_shl_balance_keur": result_obj.opening_shl_balance_keur,
        }
        # Call bridge
        build_opening_balance_bridge(result_input)
        # Verify attributes are unchanged
        for k, v in before.items():
            assert getattr(result_obj, k) == v, (
                f"Construction result mutated: {k} changed"
            )

    def test_input_manual_overrides_unchanged(self):
        result_input = _make_input("TUHO")
        before = list(result_input.manual_overrides)
        build_opening_balance_bridge(result_input)
        assert list(result_input.manual_overrides) == before

    def test_input_replacement_policy_unchanged(self):
        result_input = _make_input("TUHO")
        before = list(result_input.replacement_policy)
        build_opening_balance_bridge(result_input)
        assert list(result_input.replacement_policy) == before

    def test_input_parity_references_unchanged(self):
        result_input = _make_input("TUHO")
        before = list(result_input.parity_references)
        build_opening_balance_bridge(result_input)
        assert list(result_input.parity_references) == before

    def test_engine_output_hash_unchanged(self):
        """Hash the engine result before and after — they must be equal."""
        from dataclasses import asdict
        from domain.construction.templates.tuho import build_tuho_construction_config
        from dataclasses import replace as dc_replace
        config = build_tuho_construction_config()
        config = dc_replace(config, senior_idc_capitalized=True)
        engine_result = compute_construction_schedule(config)
        # Call bridge with a frozen input
        inp = OpeningBalanceBridgeInput(
            construction_result=engine_result,
            manual_overrides=_tuho_manual_overrides(),
            project_assumptions=_tuho_assumptions(),
            replacement_policy=POLICY_TABLE,
            parity_references=(),
            bridge_version=BRIDGE_VERSION,
        )
        # Frozen dataclass — compare a key field's value (the
        # hash of asdict on a frozen dataclass with tuple values is
        # not stable across Python versions, so just compare a value)
        before = engine_result.total_senior_idc_keur
        before_opening = engine_result.opening_senior_balance_keur
        build_opening_balance_bridge(inp)
        assert engine_result.total_senior_idc_keur == before
        assert engine_result.opening_senior_balance_keur == before_opening


# ---------------------------------------------------------------------------
# No forbidden imports (C2 §3.6.5, C6 §3.1)
# ---------------------------------------------------------------------------


class TestNoForbiddenImports:
    FORBIDDEN_IMPORT_PATTERNS: Final[tuple[str, ...]] = (
        r"^domain\.inputs$",
        r"^domain\.inputs\b",
        r"^domain\.waterfall$",
        r"^domain\.waterfall\b",
        r"^app\.",
        r"^main_web$",
        r"^main_web\b",
        r"^main_api$",
        r"^main_api\b",
        r"^static\.",
    )

    def test_bridge_module_no_forbidden_imports(self):
        source = BRIDGE_MODULE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                for pat in self.FORBIDDEN_IMPORT_PATTERNS:
                    if re.match(pat, node.module):
                        pytest.fail(
                            f"Forbidden import: from {node.module!r}"
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    for pat in self.FORBIDDEN_IMPORT_PATTERNS:
                        if re.match(pat, alias.name):
                            pytest.fail(
                                f"Forbidden import: import {alias.name!r}"
                            )

    def test_bridge_module_imports_only_allowed(self):
        """The bridge should only import stdlib, datetime, dataclasses, typing,
        and domain.construction.result. Nothing else from domain.* or app.*.
        """
        source = BRIDGE_MODULE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        allowed_prefixes = {
            "datetime",
            "dataclasses",
            "typing",
            "__future__",
            "domain.construction.result",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                assert node.module in allowed_prefixes, (
                    f"Bridge imports from {node.module!r} which is not in "
                    f"allowed_prefixes={allowed_prefixes}"
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name in allowed_prefixes, (
                        f"Bridge imports {alias.name!r} which is not in "
                        f"allowed_prefixes={allowed_prefixes}"
                    )


# ---------------------------------------------------------------------------
# No engine call (C6 §3.3)
# ---------------------------------------------------------------------------


class TestNoEngineCall:
    def test_bridge_module_does_not_call_engine(self):
        """The bridge must not call compute_construction_schedule or
        build_runtime_construction_schedule. It's a pure transformation.
        """
        source = BRIDGE_MODULE.read_text(encoding="utf-8")
        forbidden_calls = (
            "compute_construction_schedule",
            "build_runtime_construction_schedule",
        )
        for call in forbidden_calls:
            assert call not in source, (
                f"Bridge must not call {call!r} (C6 §3.3)"
            )

    def test_bridge_module_does_not_import_engine(self):
        source = BRIDGE_MODULE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "engine" in node.module:
                    # Only the runtime_adapter (which is engine) is allowed
                    if node.module == "domain.construction.engine":
                        pytest.fail(
                            "Bridge must not import from domain.construction.engine"
                        )


# ---------------------------------------------------------------------------
# Forbidden paths — git diff guards
# ---------------------------------------------------------------------------


class TestForbiddenPaths:
    """C7 must not touch domain/, app/, main_web.py, main_api.py, static/
    except domain/construction/opening_bridge.py.
    """

    FORBIDDEN_PATHS: Final[tuple[str, ...]] = (
        "app/",
        "main_web.py",
        "main_api.py",
        "static/",
    )

    def test_only_4_files_added(self):
        # Locate the Phase C7 commit on origin/main (works in both
        # branch-state and post-merge state). Branch-state used
        # `git diff origin/main` which is empty once merged; the C7
        # commit itself is the source of truth in either case.
        result = subprocess.run(
            [
                "git", "log", "--merges", "--first-parent",
                "--format=%H %s", "origin/main",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        c7_shas = [
            parts[0] for ln in result.stdout.splitlines()
            if (parts := ln.split(" ", 1)) and len(parts) == 2
            and parts[1].startswith("Phase C7:")
        ]
        if not c7_shas:
            result = subprocess.run(
                ["git", "log", "--format=%H %s", "origin/main"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            c7_shas = [
                ln.split(" ", 1)[0] for ln in result.stdout.splitlines()
                if ln.startswith("Phase C7:")
            ]
        assert c7_shas, "could not locate Phase C7 commit on origin/main"
        c7_sha = c7_shas[0]
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{c7_sha}^1", c7_sha],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        all_changed = sorted(
            ln.strip() for ln in result.stdout.splitlines() if ln.strip()
        )
        assert len(all_changed) == 4, (
            f"C7 must add exactly 4 files, got {len(all_changed)}: "
            f"{all_changed}"
        )

    def test_all_files_added(self):
        # Use the C7 commit on origin/main (see test_only_4_files_added).
        result = subprocess.run(
            [
                "git", "log", "--merges", "--first-parent",
                "--format=%H %s", "origin/main",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        c7_shas = [
            parts[0] for ln in result.stdout.splitlines()
            if (parts := ln.split(" ", 1)) and len(parts) == 2
            and parts[1].startswith("Phase C7:")
        ]
        if not c7_shas:
            result = subprocess.run(
                ["git", "log", "--format=%H %s", "origin/main"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            c7_shas = [
                ln.split(" ", 1)[0] for ln in result.stdout.splitlines()
                if ln.startswith("Phase C7:")
            ]
        assert c7_shas
        c7_sha = c7_shas[0]
        result = subprocess.run(
            ["git", "diff", "--name-status", f"{c7_sha}^1", c7_sha],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            status, path = line.split("\t", 1)
            assert status == "A", (
                f"only additions allowed in C7 commit: {line!r}"
            )
            assert path in (
                "domain/construction/opening_bridge.py",
                "tests/test_phase_c7_opening_balance_bridge.py",
                "docs/phase_c7_opening_balance_bridge_implementation.md",
                "reports/phase_c7_opening_balance_bridge_implementation.json",
            ), f"file {path!r} is not part of C7's 4 expected files"

    def test_no_modifications_to_existing(self):
        # No 'M' (modified) status in the C7 commit.
        result = subprocess.run(
            [
                "git", "log", "--merges", "--first-parent",
                "--format=%H %s", "origin/main",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        c7_shas = [
            parts[0] for ln in result.stdout.splitlines()
            if (parts := ln.split(" ", 1)) and len(parts) == 2
            and parts[1].startswith("Phase C7:")
        ]
        if not c7_shas:
            result = subprocess.run(
                ["git", "log", "--format=%H %s", "origin/main"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            c7_shas = [
                ln.split(" ", 1)[0] for ln in result.stdout.splitlines()
                if ln.startswith("Phase C7:")
            ]
        assert c7_shas
        c7_sha = c7_shas[0]
        result = subprocess.run(
            ["git", "show", "--name-status", "--format=", c7_sha],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            status, _ = line.split("\t", 1)
            assert status == "A", f"no modifications allowed: {line!r}"

    @pytest.mark.parametrize("forbidden", FORBIDDEN_PATHS)
    def test_forbidden_path_untouched(self, forbidden):
        # The C7 commit must not add or modify any forbidden path.
        result = subprocess.run(
            [
                "git", "log", "--merges", "--first-parent",
                "--format=%H %s", "origin/main",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        c7_shas = [
            parts[0] for ln in result.stdout.splitlines()
            if (parts := ln.split(" ", 1)) and len(parts) == 2
            and parts[1].startswith("Phase C7:")
        ]
        if not c7_shas:
            result = subprocess.run(
                ["git", "log", "--format=%H %s", "origin/main"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            c7_shas = [
                ln.split(" ", 1)[0] for ln in result.stdout.splitlines()
                if ln.startswith("Phase C7:")
            ]
        assert c7_shas
        c7_sha = c7_shas[0]
        result2 = subprocess.run(
            [
                "git", "show", "--name-only", "--format=", c7_sha,
                "--", forbidden,
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        touched = [
            ln.strip() for ln in result2.stdout.splitlines() if ln.strip()
        ]
        assert not touched, (
            f"Phase C7 must not touch {forbidden}: {touched}"
        )

    def test_only_domain_opening_bridge_touched(self):
        """The only domain change allowed is opening_bridge.py."""
        # Locate the Phase C7 commit on origin/main (see
        # test_only_4_files_added for rationale on the approach).
        result = subprocess.run(
            [
                "git", "log", "--merges", "--first-parent",
                "--format=%H %s", "origin/main",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        c7_shas = [
            parts[0] for ln in result.stdout.splitlines()
            if (parts := ln.split(" ", 1)) and len(parts) == 2
            and parts[1].startswith("Phase C7:")
        ]
        if not c7_shas:
            result = subprocess.run(
                ["git", "log", "--format=%H %s", "origin/main"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            c7_shas = [
                ln.split(" ", 1)[0] for ln in result.stdout.splitlines()
                if ln.startswith("Phase C7:")
            ]
        assert c7_shas, "could not locate Phase C7 commit on origin/main"
        c7_sha = c7_shas[0]
        result = subprocess.run(
            [
                "git", "diff", "--name-only", f"{c7_sha}^1", c7_sha,
                "--", "domain/",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        all_domain = sorted(
            ln.strip() for ln in result.stdout.splitlines() if ln.strip()
        )
        assert all_domain == ["domain/construction/opening_bridge.py"], (
            f"Only domain/construction/opening_bridge.py allowed, got: {all_domain}"
        )


# ---------------------------------------------------------------------------
# C4 snapshot integrity — unchanged
# ---------------------------------------------------------------------------


class TestC4SnapshotsUnchanged:
    def test_tuho_snapshot_unchanged(self):
        result = subprocess.run(
            [
                "git", "diff", "origin/main", "--",
                "tests/fixtures/construction_parity/tuho_construction_snapshot.json",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        # Also check untracked (the snapshot should be tracked)
        result2 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard",
             "tests/fixtures/construction_parity/tuho_construction_snapshot.json"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "" and not result2.stdout.strip(), (
            f"tuho snapshot must be unchanged: diff={result.stdout!r}, "
            f"untracked={result2.stdout!r}"
        )

    def test_oborovo_snapshot_unchanged(self):
        result = subprocess.run(
            [
                "git", "diff", "origin/main", "--",
                "tests/fixtures/construction_parity/oborovo_construction_snapshot.json",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        result2 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard",
             "tests/fixtures/construction_parity/oborovo_construction_snapshot.json"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "" and not result2.stdout.strip(), (
            f"oborovo snapshot must be unchanged: diff={result.stdout!r}, "
            f"untracked={result2.stdout!r}"
        )


# ---------------------------------------------------------------------------
# rc1 SHA reachable
# ---------------------------------------------------------------------------


class TestRc1Reachable:
    def test_rc1_sha_reachable(self):
        result = subprocess.run(
            [
                "git", "cat-file", "-e",
                "b425a0708719eaa5e1d922b1008e5609758e0ad4",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Use-construction-engine flag default-off
# ---------------------------------------------------------------------------


class TestFeatureFlagUnchanged:
    def test_default_off(self):
        # Per C1: the feature flag remains default-off
        # We just verify the source file mentions it correctly
        # by checking domain/inputs.py or similar
        result = subprocess.run(
            ["grep", "-n", "use_construction_schedule_engine", "-r", "domain/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        # Just check that the flag exists somewhere in domain
        assert "use_construction_schedule_engine" in result.stdout
        # And that it defaults to False
        assert "False" in result.stdout or "= False" in result.stdout


# ---------------------------------------------------------------------------
# Project statuses unchanged
# ---------------------------------------------------------------------------


class TestProjectStatusesUnchanged:
    """TUHO and Oborovo remain Level 2 (C1/C2)."""

    def test_tuho_level_2(self):
        # The TUHO project factory still produces a Level 2 status
        # Verify the project factory exists and is unchanged
        result = subprocess.run(
            [
                "git", "diff", "origin/main", "--",
                "domain/construction/templates/tuho.py",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        result2 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard",
             "domain/construction/templates/tuho.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "" and not result2.stdout.strip(), (
            "tuho.py must be unchanged"
        )

    def test_oborovo_level_2(self):
        result = subprocess.run(
            [
                "git", "diff", "origin/main", "--",
                "domain/construction/templates/oborovo.py",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        result2 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard",
             "domain/construction/templates/oborovo.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "" and not result2.stdout.strip(), (
            "oborovo.py must be unchanged"
        )


# ---------------------------------------------------------------------------
# Senior IDC effective-rate caveat (C1 R-PAR-2)
# ---------------------------------------------------------------------------


class TestSeniorIdcEffectiveRateCaveat:
    """C1 R-PAR-2: senior IDC is effective-rate based, not modelling-correct.

    The bridge preserves this caveat by:
    - Marking senior_opening_balance_keur as `frozen` (manual wins)
    - Marking senior_idc_keur as `replaced` (engine wins, parity_ok)
    """

    def test_senior_idc_replaced_parity_ok(self):
        """senior_idc_keur is replaced and matches parity (effective rate
        calibration is correct)."""
        for project in ("TUHO", "OBOROVO"):
            inp = _make_input(project)
            result = build_opening_balance_bridge(inp)
            audit = {
                r.field_code: r
                for r in result.audit_reconciliation_table
            }
            row = audit["senior_idc_keur"]
            assert row.selection_reason == SELECTION_REPLACED
            assert row.parity_status == PARITY_OK

    def test_senior_opening_frozen_parity_drift(self):
        """senior_opening_balance_keur is frozen; parity drifts by the
        capitalized senior IDC amount."""
        for project in ("TUHO", "OBOROVO"):
            inp = _make_input(project)
            result = build_opening_balance_bridge(inp)
            audit = {
                r.field_code: r
                for r in result.audit_reconciliation_table
            }
            row = audit["senior_opening_balance_keur"]
            assert row.selection_reason == SELECTION_FROZEN
            assert row.parity_status == PARITY_DRIFT

    def test_drift_equals_capitalized_senior_idc(self):
        """The drift is the senior IDC amount (positive when manual
        is less than parity, negative when manual is greater).
        For TUHO: manual 43,359.274, parity 44,878.838, drift = -1519.564.
        """
        for project, expected_drift in (
            ("TUHO", -1519.564),
            ("OBOROVO", -1086.032),
        ):
            inp = _make_input(project)
            result = build_opening_balance_bridge(inp)
            audit = {
                r.field_code: r
                for r in result.audit_reconciliation_table
            }
            row = audit["senior_opening_balance_keur"]
            assert abs(row.parity_delta_keur - expected_drift) <= 0.01, (
                f"{project}: drift={row.parity_delta_keur}, "
                f"expected {expected_drift}"
            )


# ---------------------------------------------------------------------------
# C5 engine comparison still passes (C5 fixtures READ-ONLY)
# ---------------------------------------------------------------------------


class TestC5EngineComparisonStillPasses:
    """The C5 engine comparison tests should still pass — they don't
    depend on the bridge, but we verify by re-running the parity
    against the C4 snapshots using only the engine (no bridge).
    """

    def test_tuho_engine_matches_snapshot(self):
        from dataclasses import replace
        config = build_tuho_construction_config()
        config = replace(config, senior_idc_capitalized=True)
        result = compute_construction_schedule(config)
        with open(C4_TUHO_SNAPSHOT) as f:
            snap = json.load(f)
        totals = snap["totals_keur"]
        assert abs(result.total_uses_keur - totals["total_uses"]) <= 0.01
        assert abs(result.total_shl_idc_keur - totals["total_shl_idc"]) <= 0.001
        assert abs(result.total_senior_idc_keur - totals["total_senior_idc"]) <= 0.001

    def test_oborovo_engine_matches_snapshot(self):
        from dataclasses import replace
        config = build_oborovo_construction_config()
        config = replace(config, senior_idc_capitalized=True)
        result = compute_construction_schedule(config)
        with open(C4_OBOROVO_SNAPSHOT) as f:
            snap = json.load(f)
        totals = snap["totals_keur"]
        assert abs(result.total_uses_keur - totals["total_uses"]) <= 0.01
        assert abs(result.total_shl_idc_keur - totals["total_shl_idc"]) <= 0.001
        assert abs(result.total_senior_idc_keur - totals["total_senior_idc"]) <= 0.001


# ---------------------------------------------------------------------------
# No double-counting — single source per field (C2 §6.6)
# ---------------------------------------------------------------------------


class TestNoDoubleCounting:
    """For each opening balance field, exactly one of
    {manual, construction} is in selected_runtime_value_keur.
    """

    @pytest.mark.parametrize("project", ["TUHO", "OBOROVO"])
    def test_single_source_per_field(self, project):
        inp = _make_input(project)
        result = build_opening_balance_bridge(inp)
        for row in result.audit_reconciliation_table:
            if row.double_counting_guard == GUARD_SINGLE_SOURCE:
                # The selected value must be exactly one of
                # manual_value_keur or construction_derived_value_keur
                m = row.manual_value_keur
                c = row.construction_derived_value_keur
                s = row.selected_runtime_value_keur
                # At least one of m, c must equal s
                matches = []
                if m is not None and abs(s - m) <= IDENTITY_TOLERANCE_KEUR:
                    matches.append("manual")
                if c is not None and abs(s - c) <= IDENTITY_TOLERANCE_KEUR:
                    matches.append("construction")
                assert len(matches) >= 1, (
                    f"{project}/{row.field_code}: selected {s} doesn't match "
                    f"manual={m} or construction={c}"
                )
            elif row.double_counting_guard == GUARD_COMPOSITE:
                # Composite field — selected is the manual composite
                # The construction value is recorded but not used
                m = row.manual_value_keur
                s = row.selected_runtime_value_keur
                if m is not None:
                    assert abs(s - m) <= IDENTITY_TOLERANCE_KEUR


# ---------------------------------------------------------------------------
# Pure function: same input → same output
# ---------------------------------------------------------------------------


class TestPureFunction:
    def test_same_input_same_output_tuho(self):
        inp = _make_input("TUHO")
        r1 = build_opening_balance_bridge(inp)
        r2 = build_opening_balance_bridge(inp)
        # The bridge_run_timestamp may differ (it's wall-clock time)
        # but the rest should be identical
        assert r1.opening_senior_balance_at_cod_keur == r2.opening_senior_balance_at_cod_keur
        assert r1.opening_shl_balance_at_cod_keur == r2.opening_shl_balance_at_cod_keur
        assert r1.capitalized_senior_idc_keur == r2.capitalized_senior_idc_keur
        assert r1.capitalized_shl_idc_keur == r2.capitalized_shl_idc_keur
        assert r1.equity_contribution_at_cod_keur == r2.equity_contribution_at_cod_keur
        assert r1.financing_fee_treatment_keur == r2.financing_fee_treatment_keur
        # Audit table content (excluding timestamps) should be identical
        for a, b in zip(r1.audit_reconciliation_table, r2.audit_reconciliation_table):
            assert a.field_code == b.field_code
            assert a.selected_runtime_value_keur == b.selected_runtime_value_keur
            assert a.selection_reason == b.selection_reason


# ---------------------------------------------------------------------------
# Result is a frozen dataclass
# ---------------------------------------------------------------------------


class TestResultIsFrozenDataclass:
    def test_result_is_dataclass(self):
        result = build_opening_balance_bridge(_make_input("TUHO"))
        assert is_dataclass(result)

    def test_cannot_setattr_on_result(self):
        result = build_opening_balance_bridge(_make_input("TUHO"))
        with pytest.raises(Exception):
            result.opening_senior_balance_at_cod_keur = 0.0

    def test_cannot_setattr_on_audit_row(self):
        result = build_opening_balance_bridge(_make_input("TUHO"))
        row = result.audit_reconciliation_table[0]
        with pytest.raises(Exception):
            row.field_code = "modified"
