"""Tests for C3B3D2A: Oborovo SHL source-truth fixture provenance and coherence.

Tests read directly from committed source fixtures. No SHL vector values are
hardcoded independently inside this file — all expected values derive from
the authoritative committed source fixtures at test time.

Source hierarchy:
  1. tests/fixtures/excel_oborovo_financial_truth.json  (primary DS vectors)
  2. tests/fixtures/interest_limitation/oborovo_interest_limitation_fixture.json
       (period dates, gross-interest cross-check)
  3. tests/fixtures/excel_oborovo_shl_operating_truth.json  (D2A derived fixture)

No Python model/factory/waterfall output is used.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

_REPO = pathlib.Path(__file__).resolve().parent.parent
_D2A_FIXTURE = _REPO / "tests/fixtures/excel_oborovo_shl_operating_truth.json"
_SOURCE_TRUTH = _REPO / "tests/fixtures/excel_oborovo_financial_truth.json"
_IL_FIXTURE = (
    _REPO / "tests/fixtures/interest_limitation/oborovo_interest_limitation_fixture.json"
)
_DERIVE_SCRIPT = _REPO / "finco_recon/derive_c3b3d2a_oborovo_shl_truth.py"

_RATE = 0.08
_TOL = 1e-6  # kEUR tolerance
_WORKBOOK_SHA = "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920"
_SHL_DRAW = 14620.773894815633   # Excel Inputs!D325
_SHL_RATE_VAL = 0.08             # Excel Inputs!F328
_OP_OPENING = 15790.435806400885  # DS[0].end = DS[1].beg


@pytest.fixture(scope="module")
def source_truth():
    with open(_SOURCE_TRUTH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def il_data():
    with open(_IL_FIXTURE) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def d2a(source_truth, il_data):  # noqa: ARG001
    with open(_D2A_FIXTURE) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def source_ds(source_truth):
    return source_truth["ds"]


@pytest.fixture(scope="module")
def d2a_periods(d2a):
    return d2a["periods"]


class TestA_SourceFixtureLoads:
    """A: authoritative source fixture loads and has expected structure."""

    def test_source_truth_loads(self, source_truth):
        assert source_truth is not None
        assert "ds" in source_truth
        assert "_meta" in source_truth

    def test_source_ds_has_41_shl_periods(self, source_ds):
        assert len(source_ds["shl_beginning_keur"]) >= 41
        assert len(source_ds["shl_net_interest_keur"]) >= 41


class TestB_D2AFixtureLoads:
    """B: D2A fixture loads and has expected structure."""

    def test_d2a_fixture_loads(self, d2a):
        assert d2a is not None
        assert "periods" in d2a
        assert len(d2a["periods"]) == 41

    def test_d2a_has_workbook_inputs(self, d2a):
        assert "workbook_inputs" in d2a
        assert "shl_draw_keur" in d2a["workbook_inputs"]
        assert "shl_annual_rate" in d2a["workbook_inputs"]


class TestC_SourceWorkbookSHA:
    """C: source workbook SHA-256 is preserved in the D2A fixture."""

    def test_source_workbook_sha_in_d2a_meta(self, d2a):
        sha = d2a["_meta"]["source_workbook_sha256"]
        assert sha == _WORKBOOK_SHA

    def test_source_workbook_sha_in_source_truth(self, source_truth):
        sha = source_truth["_meta"]["source_sha256"]
        assert sha == _WORKBOOK_SHA


class TestD_SourceD325Amount:
    """D: Excel Inputs!D325 SHL draw amount is exact."""

    def test_d325_in_source_truth(self, source_truth):
        val = source_truth["inputs"]["shl_amount_keur"]["value"]
        assert val == pytest.approx(_SHL_DRAW, abs=1e-9)

    def test_d325_in_d2a_fixture(self, d2a):
        val = d2a["workbook_inputs"]["shl_draw_keur"]["value"]
        assert val == pytest.approx(_SHL_DRAW, abs=1e-9)

    def test_d325_cell_reference(self, d2a):
        assert d2a["workbook_inputs"]["shl_draw_keur"]["cell"] == "Inputs!D325"


class TestE_SourceF328Rate:
    """E: Excel Inputs!F328 annual rate is exact."""

    def test_f328_in_source_truth(self, source_truth):
        val = source_truth["inputs"]["shl_interest_rate"]["value"]
        assert val == pytest.approx(_SHL_RATE_VAL, abs=1e-9)

    def test_f328_in_d2a_fixture(self, d2a):
        val = d2a["workbook_inputs"]["shl_annual_rate"]["value"]
        assert val == pytest.approx(_SHL_RATE_VAL, abs=1e-9)


class TestF_ShlBeginningMatchesSource:
    """F: all D2A opening_balance_keur values match source shl_beginning_keur."""

    def test_all_opening_balances_match_source(self, source_ds, d2a_periods):
        src = source_ds["shl_beginning_keur"]
        for p in d2a_periods:
            i = p["ds_index"]
            assert p["opening_balance_keur"] == pytest.approx(src[i], abs=_TOL), (
                f"opening_balance mismatch at DS[{i}]"
            )


class TestG_ShlFundingMatchesSource:
    """G: all D2A drawdown_keur values match source shl_funding_keur."""

    def test_all_drawdowns_match_source(self, source_ds, d2a_periods):
        src = source_ds["shl_funding_keur"]
        for p in d2a_periods:
            i = p["ds_index"]
            assert p["drawdown_keur"] == pytest.approx(src[i], abs=_TOL), (
                f"drawdown mismatch at DS[{i}]"
            )


class TestH_GrossInterestMatchesSource:
    """H: all D2A gross_accrued_interest_keur values match source shl_net_interest_keur."""

    def test_all_gross_interest_match_source(self, source_ds, d2a_periods):
        src = source_ds["shl_net_interest_keur"]
        for p in d2a_periods:
            i = p["ds_index"]
            assert p["gross_accrued_interest_keur"] == pytest.approx(src[i], abs=_TOL), (
                f"gross_interest mismatch at DS[{i}]"
            )


class TestI_CapitalisedInterestMatchesSource:
    """I: all D2A pik_interest_keur values match source shl_interest_capitalised_keur."""

    def test_all_pik_match_source(self, source_ds, d2a_periods):
        src = source_ds["shl_interest_capitalised_keur"]
        for p in d2a_periods:
            i = p["ds_index"]
            assert p["pik_interest_keur"] == pytest.approx(src[i], abs=_TOL), (
                f"pik_interest mismatch at DS[{i}]"
            )


class TestJ_EndingBalancesMatchSource:
    """J: all D2A closing_balance_keur values match source shl_ending_keur."""

    def test_all_closing_balances_match_source(self, source_ds, d2a_periods):
        src = source_ds["shl_ending_keur"]
        for p in d2a_periods:
            i = p["ds_index"]
            assert p["closing_balance_keur"] == pytest.approx(src[i], abs=_TOL), (
                f"closing_balance mismatch at DS[{i}]"
            )


class TestK_ServiceMatchesSource:
    """K: all D2A shl_service_keur values match source shl_service_keur."""

    def test_all_service_match_source(self, source_ds, d2a_periods):
        src = source_ds["shl_service_keur"]
        for p in d2a_periods:
            i = p["ds_index"]
            assert p["shl_service_keur"] == pytest.approx(src[i], abs=_TOL), (
                f"shl_service mismatch at DS[{i}]"
            )


class TestL_DerivedCashInterestIdentity:
    """L: cash_interest_keur = gross - cap for all periods (NOT service - cap)."""

    def test_cash_interest_derivation(self, d2a_periods):
        for p in d2a_periods:
            expected = p["gross_accrued_interest_keur"] - p["pik_interest_keur"]
            assert p["cash_interest_keur"] == pytest.approx(expected, abs=_TOL), (
                f"cash_interest derivation failed at DS[{p['ds_index']}]"
            )


class TestM_DerivedPrincipalIdentity:
    """M: principal_repaid = shl_service - cash_interest for all periods."""

    def test_principal_derivation(self, d2a_periods):
        for p in d2a_periods:
            expected = p["shl_service_keur"] - p["cash_interest_keur"]
            assert p["principal_repaid_keur"] == pytest.approx(expected, abs=_TOL), (
                f"principal_repaid derivation failed at DS[{p['ds_index']}]"
            )


class TestN_RollForwardIdentity:
    """N: closing = opening + drawdown + pik - principal for all periods."""

    def test_roll_forward_all_periods(self, d2a_periods):
        for p in d2a_periods:
            expected = (
                p["opening_balance_keur"]
                + p["drawdown_keur"]
                + p["pik_interest_keur"]
                - p["principal_repaid_keur"]
            )
            assert p["closing_balance_keur"] == pytest.approx(expected, abs=_TOL), (
                f"roll-forward failed at DS[{p['ds_index']}]"
            )


class TestO_SequentialContinuity:
    """O: closing[i] == opening[i+1] for all adjacent pairs."""

    def test_sequential_continuity(self, d2a_periods):
        for i in range(len(d2a_periods) - 1):
            assert d2a_periods[i]["closing_balance_keur"] == pytest.approx(
                d2a_periods[i + 1]["opening_balance_keur"], abs=_TOL
            ), f"Gap between DS[{i}] and DS[{i + 1}]"


class TestP_ConstructionCloseEqualsOperatingOpen:
    """P: DS[0].close == DS[1].open == stated operating_opening_balance_keur."""

    def test_construction_close_equals_operating_open(self, d2a, d2a_periods):
        stated = d2a["operating_opening_balance_keur"]
        construction_close = d2a_periods[0]["closing_balance_keur"]
        operating_open = d2a_periods[1]["opening_balance_keur"]
        assert stated == pytest.approx(_OP_OPENING, abs=_TOL)
        assert stated == pytest.approx(construction_close, abs=_TOL)
        assert stated == pytest.approx(operating_open, abs=_TOL)


class TestQ_ConstructionPikProof:
    """Q: DS[0] is 100% PIK: pik == gross, cash_interest == 0, principal == 0."""

    def test_construction_pik(self, d2a_periods):
        p = d2a_periods[0]
        assert p["ds_index"] == 0
        assert p["payment_mode"] == "PIK"
        assert p["pik_interest_keur"] == pytest.approx(
            p["gross_accrued_interest_keur"], abs=_TOL
        )
        assert p["cash_interest_keur"] == pytest.approx(0.0, abs=_TOL)
        assert p["principal_repaid_keur"] == pytest.approx(0.0, abs=_TOL)

    def test_construction_idc_formula(self, source_truth, d2a_periods):
        """Construction IDC = draw * rate * 1.0 (rate from Inputs!F328, DCF=1.0 implied)."""
        p = d2a_periods[0]
        rate = source_truth["inputs"]["shl_interest_rate"]["value"]
        expected_idc = p["drawdown_keur"] * rate * 1.0
        assert p["gross_accrued_interest_keur"] == pytest.approx(expected_idc, abs=_TOL)


class TestR_DS1PartialCashPikProof:
    """R: DS[1] numerical proof — cash_interest = gross - cap, NOT service - cap."""

    def test_ds1_gross_from_source(self, source_ds, d2a_periods):
        src_gross = source_ds["shl_net_interest_keur"][1]
        assert d2a_periods[1]["gross_accrued_interest_keur"] == pytest.approx(
            src_gross, abs=_TOL
        )

    def test_ds1_pik_from_source(self, source_ds, d2a_periods):
        src_cap = source_ds["shl_interest_capitalised_keur"][1]
        assert d2a_periods[1]["pik_interest_keur"] == pytest.approx(src_cap, abs=_TOL)

    def test_ds1_cash_interest_is_gross_minus_cap(self, d2a_periods):
        p = d2a_periods[1]
        assert p["cash_interest_keur"] == pytest.approx(
            p["gross_accrued_interest_keur"] - p["pik_interest_keur"], abs=_TOL
        )

    def test_ds1_cash_interest_approx_value(self, source_ds, d2a_periods):
        """DS1 cash_interest = gross(636.808808) - cap(300.938796) ≈ 335.870012."""
        p = d2a_periods[1]
        gross = source_ds["shl_net_interest_keur"][1]
        cap = source_ds["shl_interest_capitalised_keur"][1]
        expected_cash = gross - cap
        assert p["cash_interest_keur"] == pytest.approx(expected_cash, abs=_TOL)

    def test_ds1_principal_is_zero(self, d2a_periods):
        assert d2a_periods[1]["principal_repaid_keur"] == pytest.approx(0.0, abs=_TOL)

    def test_ds1_payment_mode(self, d2a_periods):
        assert d2a_periods[1]["payment_mode"] == "PARTIAL_CASH_PARTIAL_PIK"


class TestS_PaymentModeBoundaryDiscovery:
    """S: payment-mode boundary is discovered from source values, not hardcoded index.

    DS25 is the RESULT of classifying cap vs gross; the test discovers it,
    not presupposes it.
    """

    def test_all_pik_nonzero_before_cash_paid_boundary(self, source_ds, d2a_periods):
        """All periods with pik>0 come before all periods with cap=0."""
        pik_indices = [p["ds_index"] for p in d2a_periods if p["pik_interest_keur"] > _TOL]
        cash_indices = [p["ds_index"] for p in d2a_periods if p["pik_interest_keur"] <= _TOL]
        # All pik periods should precede all zero-cap periods (exclusive of DS[0])
        if pik_indices and cash_indices:
            assert max(pik_indices) < min(cash_indices), (
                "Non-contiguous payment mode boundary detected"
            )

    def test_first_cash_paid_discovered_as_ds25(self, d2a_periods):
        """First period with cap=0 is DS[25] — discovered from data, not assumed."""
        first_cash = next(
            (p["ds_index"] for p in d2a_periods if p["pik_interest_keur"] <= _TOL),
            None,
        )
        assert first_cash == 25, (
            f"Expected first CASH_PAID at DS[25]; discovered DS[{first_cash}]"
        )

    def test_first_cash_paid_recorded_in_fixture(self, d2a):
        """Fixture records the discovered first_cash_paid_ds_index."""
        pc = d2a["payment_mode_classification"]
        assert pc["first_cash_paid_ds_index_discovered"] == 25

    def test_ds0_payment_mode_pik(self, d2a_periods):
        assert d2a_periods[0]["payment_mode"] == "PIK"

    def test_ds1_to_ds24_payment_mode_partial(self, d2a_periods):
        for p in d2a_periods[1:25]:
            assert p["payment_mode"] == "PARTIAL_CASH_PARTIAL_PIK", (
                f"Expected PARTIAL at DS[{p['ds_index']}]"
            )

    def test_ds25_to_ds40_payment_mode_cash_paid(self, d2a_periods):
        for p in d2a_periods[25:]:
            assert p["payment_mode"] == "CASH_PAID", (
                f"Expected CASH_PAID at DS[{p['ds_index']}]"
            )


class TestT_PrincipalRepaymentBeforeMaturity:
    """T: principal_repaid > 0 in at least one period before DS[40]."""

    def test_ds0_to_ds24_zero_principal(self, d2a_periods):
        """SWEEP begins at DS[25]; DS[0..24] have zero principal."""
        for p in d2a_periods[:25]:
            assert p["principal_repaid_keur"] == pytest.approx(0.0, abs=_TOL), (
                f"Unexpected principal at DS[{p['ds_index']}]"
            )

    def test_first_nonzero_principal_discovered_at_ds25(self, d2a_periods):
        """First period with principal_repaid > 0 is DS[25] — discovered from data."""
        first_principal = next(
            (p["ds_index"] for p in d2a_periods if p["principal_repaid_keur"] > _TOL),
            None,
        )
        assert first_principal == 25, (
            f"Expected first principal at DS[25]; discovered DS[{first_principal}]"
        )

    def test_nonzero_principal_before_ds40(self, d2a_periods):
        """Guard: source is a sweep, not a bullet — principal appears before DS[40]."""
        early = [p for p in d2a_periods[:40] if p["principal_repaid_keur"] > _TOL]
        assert len(early) > 0


class TestU_DS40ClosesExactlyZero:
    """U: DS[40] closing balance is exactly 0.0."""

    def test_ds40_closing_zero(self, d2a_periods):
        last = d2a_periods[40]
        assert last["ds_index"] == 40
        assert last["closing_balance_keur"] == pytest.approx(0.0, abs=_TOL)


class TestV_NoNegativeBalances:
    """V: no negative opening or closing balances."""

    def test_no_negative_opening(self, d2a_periods):
        for p in d2a_periods:
            assert p["opening_balance_keur"] >= -_TOL, (
                f"Negative opening at DS[{p['ds_index']}]"
            )

    def test_no_negative_closing(self, d2a_periods):
        for p in d2a_periods:
            assert p["closing_balance_keur"] >= -_TOL, (
                f"Negative closing at DS[{p['ds_index']}]"
            )


class TestW_SourceVectorContentHash:
    """W: D2A fixture is non-empty and valid JSON matching loaded structure."""

    def test_d2a_fixture_not_empty(self):
        with open(_D2A_FIXTURE, "rb") as f:
            content = f.read()
        assert len(content) > 1000

    def test_d2a_fixture_parseable_and_stage_correct(self, d2a):
        assert d2a["_meta"]["stage"] == "C3B3D2A"
        assert len(d2a["periods"]) == 41


class TestX_DerivationIdempotency:
    """X: running the derivation script reproduces the committed fixture exactly."""

    def test_derive_script_exists(self):
        assert _DERIVE_SCRIPT.exists(), f"Derivation script not found: {_DERIVE_SCRIPT}"

    def test_derivation_idempotent(self):
        """--check mode exits 0 iff derived content == committed fixture."""
        result = subprocess.run(
            [sys.executable, str(_DERIVE_SCRIPT), "--check"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Derivation idempotency check failed:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "IDEMPOTENCY OK" in result.stdout


class TestILCrossCheck:
    """Cross-check: D2A gross interest matches interest_limitation fixture r27 values."""

    def test_gross_interest_matches_il_fixture(self, d2a_periods, il_data):
        """IL fixture periods[i] = DS[i+1]; r27 = gross SHL interest."""
        il_periods = il_data["periods"]
        for i, il_p in enumerate(il_periods[:40]):
            ds_idx = i + 1
            d2a_gross = d2a_periods[ds_idx]["gross_accrued_interest_keur"]
            il_gross = il_p["gross_shl_interest_r27"]
            assert d2a_gross == pytest.approx(il_gross, abs=_TOL), (
                f"Cross-check mismatch at DS[{ds_idx}]: D2A={d2a_gross} IL={il_gross}"
            )


class TestGovernanceSourceConflict:
    """Governance: factory vs Excel source conflict is KNOWN and labeled (not a parity target).

    KNOWN_SOURCE_CONFLICT: factory shl_amount_keur=13547.2 vs Excel 14620.77.
    This is intentional at D2A scope (parity-baseline calibration reversion).
    These tests assert the conflict EXISTS and is documented — NOT that factory == Excel.
    """

    _FACTORY_SHL = 13547.2
    _EXCEL_SHL = 14620.773894815633

    def test_factory_value_differs_from_excel_source(self):
        """Factory 13547.2 != Excel 14620.77 — intentional KNOWN_SOURCE_CONFLICT."""
        assert abs(self._FACTORY_SHL - self._EXCEL_SHL) > 1000, (
            "Factory and Excel values unexpectedly converged — conflict must be explicit"
        )

    def test_excel_source_value_from_fixture(self, source_truth):
        """Excel Inputs!D325 fixture value is authoritative = 14620.773894815633."""
        val = source_truth["inputs"]["shl_amount_keur"]["value"]
        assert val == pytest.approx(self._EXCEL_SHL, abs=1e-9)

    def test_d2a_fixture_documents_conflict_status(self, d2a):
        """D2A fixture must document the known conflict with a provenance label."""
        note = d2a["python_factory_note"]
        assert note["status"] == "C3B3D2A_FACTORY_CALIBRATION_REVERSION_PROVEN"
        assert note["conflict_status"] == "C3B3D2A_FACTORY_VALUE_CONFLICTS_WITH_AUTHORITATIVE_SOURCE"

    def test_d2a_fixture_documents_pr_chronology(self, d2a):
        """Provenance chronology must reference both PR #309 and PR #752."""
        chron = d2a["python_factory_note"]["provenance_chronology"]
        assert "PR #309" in chron
        assert "PR #752" in chron
        assert "34ed6d0b" in chron
        assert "099e4a14" in chron

    def test_rate_sourced_from_fixture_not_hardcoded(self, source_truth, d2a):
        """Rate used in derivation must match Inputs!F328 from source fixture."""
        fixture_rate = source_truth["inputs"]["shl_interest_rate"]["value"]
        d2a_rate = d2a["workbook_inputs"]["shl_annual_rate"]["value"]
        assert fixture_rate == pytest.approx(d2a_rate, abs=1e-9)


class TestGovernanceConstructionDCF:
    """Governance: construction DCF=1.0 is implied by arithmetic (SOURCE_IMPLIED),
    not claimed from a specific 365-calendar-day date range.
    """

    def test_construction_dcf_implied_by_arithmetic(self, source_truth, d2a_periods):
        """gross / (draw * rate) == 1.0 for DS[0] — this is the DCF proof."""
        draw = source_truth["ds"]["shl_funding_keur"][0]
        gross = source_truth["ds"]["shl_net_interest_keur"][0]
        rate = source_truth["inputs"]["shl_interest_rate"]["value"]
        dcf_implied = gross / (draw * rate)
        assert dcf_implied == pytest.approx(1.0, abs=1e-9)

    def test_construction_dcf_label_in_fixture(self, d2a):
        """Fixture must use CONSTRUCTION_SHL_DCF_SOURCE_IMPLIED_1_0 label."""
        cp = d2a["construction_period"]
        assert "CONSTRUCTION_SHL_DCF_SOURCE_IMPLIED_1_0" in cp["dcf_note"]

    def test_no_false_365_calendar_day_claim(self, d2a):
        """Fixture must NOT claim '365 calendar days / 365 = 1.0' as the proof."""
        dcf_note = d2a["construction_period"]["dcf_note"]
        # Must not assert a specific calendar-day count as the causal proof
        assert "365/365" not in dcf_note, (
            "Remove false '365/365' calendar-day claim — use arithmetic implication"
        )
