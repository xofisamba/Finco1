"""G3B KUPI Out-of-Sample Validation — Anti-Overfit Test Suite.

PHASE C — BLIND RUN RULE enforced:
  Assertions are written AFTER the blind run diagnostic was executed and
  results recorded. No KUPI-specific case dispatch is added to the engine.

GOVERNANCE (verbatim from G3B Agent Prompt 20260817):
  - DO NOT open a new PR. Keep #938 DRAFT. Do NOT merge.
  - DO NOT set dcf≈2.08 to match source output.
  - DO NOT add a KUPI special case to the engine.
  - DO NOT silently change all SHL projects to compound interest.
  - NO production formula change authorized merely because KUPI differs from Excel.
  - Do not register KUPI as a user-facing factory/project.

KUPI: 144 MW Wind, Bosnia & Herzegovina.
Source workbook SHA-256: 111178fb21109f55df45c0cc1ea108104ac8b6ed60f010ba75b6c498795f5954

Documented gaps (all pre-authorized before testing):
  KUPI_SHL_CONSTRUCTION_COMPOUNDING_GAP      CURRENT_FINCO_CAPABILITY_GAP
  KUPI_DSCR_REVENUE_MIX_FORMULA_GAP          CURRENT_FINCO_CAPABILITY_GAP
  KUPI_SPONSOR_CONTRIBUTION_TIMING_POLICY_GAP DEFINITION_OR_TIMING_DIFFERENCE
  KUPI_TAX_WORKBOOK_COMPATIBILITY_GAP         CLEAN_POLICY_VS_WORKBOOK_COMPATIBILITY
  KUPI_BANK_CFADS_BALANCING_DEDUCTION_GAP     CLEAN_POLICY_VS_WORKBOOK_COMPATIBILITY
  KUPI_VAT_FACILITY                           UNSUPPORTED_INSTITUTIONAL_FEATURE
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

import pytest

from tests.helpers.g3b_kupi_project import (
    create_kupi_project,
    create_kupi_project_source_effective_co2,
    _KUPI_TOTAL_USES_KEUR,
    _KUPI_SHL_PRINCIPAL_KEUR,
)
from financial_engine.shareholder_waterfall import run_project_shareholder_waterfall_model

# ── shared fixture ─────────────────────────────────────────────────────────────

_result_cache: dict = {}


def _result():
    if "r" not in _result_cache:
        proj = create_kupi_project()
        _result_cache["r"] = run_project_shareholder_waterfall_model(proj)
        _result_cache["proj"] = proj
    return _result_cache["r"]


def _proj():
    _result()
    return _result_cache["proj"]


# ── TestA  Governance ──────────────────────────────────────────────────────────


class TestA_Governance:
    """G3B-A: No forbidden tokens, no factory import, no source output as input."""

    def test_no_kupi_special_case_in_engine(self):
        """Engine must not dispatch on KUPI project name/code."""
        import ast
        import pathlib

        engine_root = pathlib.Path("financial_engine")
        forbidden = {"KUPI", "kupi", "G3B", "g3b"}
        for pyfile in engine_root.rglob("*.py"):
            src = pyfile.read_text(errors="replace")
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    for tok in forbidden:
                        assert tok not in node.value, (
                            f"Engine file {pyfile} contains forbidden token '{tok}' "
                            f"(line {node.lineno}) — KUPI special case not allowed."
                        )

    def test_no_source_output_hardcoded_as_input(self):
        """Source authority senior (147150.442) must not appear in fixture."""
        import pathlib

        fixture = pathlib.Path("tests/helpers/g3b_kupi_project.py").read_text()
        # Source senior commitment may not appear as a literal input
        assert "147150" not in fixture, (
            "Source senior commitment 147150 found in fixture — "
            "source output must not be hardcoded as a model input."
        )

    def test_kupi_not_registered_in_project_factory(self):
        """KUPI must not appear in any user-facing project registry."""
        import ast
        import pathlib

        for pyfile in pathlib.Path("financial_engine").rglob("*.py"):
            src = pyfile.read_text(errors="replace")
            if "KUPI" in src.upper() or "kupi" in src:
                try:
                    tree = ast.parse(src)
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        if "KUPI" in node.value.upper():
                            raise AssertionError(
                                f"KUPI reference in engine file {pyfile}:{node.lineno}"
                            )


# ── TestB  Period Axis ─────────────────────────────────────────────────────────


class TestB_PeriodAxis:
    """G3B-B: Period grid — 2 construction + 60 operating; senior 14yr × 2."""

    def test_shl_period_range(self):
        pmr = _result().financing_result.project_model_result
        pids = list(pmr.shareholder_loan.period_indices)
        assert pids[0] == 0
        assert pids[-1] == 61
        assert len(pids) == 62  # 2 construction + 60 operating

    def test_senior_period_range(self):
        pmr = _result().financing_result.project_model_result
        pids = list(pmr.senior_debt.period_indices)
        assert pids[0] == 2   # first operating period
        assert pids[-1] == 29  # 14yr × 2 = 28 periods → last = 2 + 27 = 29
        assert len(pids) == 28

    def test_first_operating_period_is_2(self):
        """Period 0 and 1 are construction; period 2 is first operating."""
        pmr = _result().financing_result.project_model_result
        shl = pmr.shareholder_loan
        pids = list(shl.period_indices)
        # SHL draws during construction
        drawdowns = list(shl.shl_drawdown_keur)
        assert drawdowns[pids.index(0)] > 0 or drawdowns[pids.index(1)] > 0

    def test_operating_period_count_60(self):
        pmr = _result().financing_result.project_model_result
        ops_pids = list(pmr.operating_schedules.period_indices)
        # periods 2..61 = 60 semi-annual operating periods
        op_count = sum(1 for p in ops_pids if p >= 2)
        assert op_count == 60


# ── TestC  G2A Identity ────────────────────────────────────────────────────────


class TestC_G2AIdentity:
    """G3B-C: Uses = Senior + Share Capital + Derived SHL."""

    def test_total_uses_matches_source(self):
        fr = _result().financing_result
        uses = fr.project_uses.total_project_uses_keur
        assert abs(uses - _KUPI_TOTAL_USES_KEUR) < 1.0, (
            f"Total uses {uses:.4f} kEUR deviates from source "
            f"{_KUPI_TOTAL_USES_KEUR:.4f} kEUR by {uses - _KUPI_TOTAL_USES_KEUR:.4f}"
        )

    def test_g2a_closure_identity(self):
        """Uses - Senior - Capital = Derived SHL to within floating-point."""
        fr = _result().financing_result
        uses = fr.project_uses.total_project_uses_keur
        senior = fr.final_senior_commitment_keur
        capital = _proj().financing.share_capital_keur
        residual = uses - senior - capital
        derived = fr.derived_shl_cash_principal_keur
        assert abs(residual - derived) < 1e-4, (
            f"G2A identity broken: residual={residual:.6f} != derived_shl={derived:.6f}"
        )

    def test_senior_gap_documented_not_zero(self):
        """Senior is below source due to bank CFADS balancing gap — documented."""
        fr = _result().financing_result
        senior = fr.final_senior_commitment_keur
        source_senior = 147_150.442310
        gap = senior - source_senior
        # Gap is negative (Finco lower) due to KUPI_BANK_CFADS_BALANCING_DEDUCTION_GAP
        assert gap < -5_000, (
            f"Senior gap {gap:.2f} kEUR is not in expected negative range. "
            f"If source parity was achieved, update this test with the new classification."
        )
        # Gap must not be catastrophically large either
        assert gap > -20_000, f"Senior gap {gap:.2f} kEUR is unexpectedly large."

    def test_binding_constraint_is_dscr(self):
        pmr = _result().financing_result.project_model_result
        assert pmr.senior_debt.binding_constraint == "DSCR"


# ── TestD  Identity Invariance ─────────────────────────────────────────────────


class TestD_IdentityInvariance:
    """G3B-D: Name/company/code changes must not affect financial outputs."""

    def test_renamed_project_same_senior(self):
        proj_r = create_kupi_project(
            name="XYZ Arbitrary Renamed LLC",
            company="Fictional BA SPV",
            code="FAKE99",
        )
        result_r = run_project_shareholder_waterfall_model(proj_r)
        senior_orig = _result().financing_result.final_senior_commitment_keur
        senior_r = result_r.financing_result.final_senior_commitment_keur
        assert abs(senior_orig - senior_r) < 1e-6, (
            f"Identity invariance FAIL: senior changed from {senior_orig:.6f} "
            f"to {senior_r:.6f} after rename — engine dispatches on project identity."
        )

    def test_renamed_project_same_uses(self):
        proj_r = create_kupi_project(
            name="XYZ Arbitrary Renamed LLC",
            company="Fictional BA SPV",
            code="FAKE99",
        )
        result_r = run_project_shareholder_waterfall_model(proj_r)
        uses_orig = _result().financing_result.project_uses.total_project_uses_keur
        uses_r = result_r.financing_result.project_uses.total_project_uses_keur
        assert abs(uses_orig - uses_r) < 1e-6


# ── TestE  Bank/Base Production Separation ────────────────────────────────────


class TestE_BankBaseSeparation:
    """G3B-E: Bank P90 < Base P50 production; bank CFADS ≤ base CFADS per period."""

    def test_bank_p90_lt_base_p50(self):
        pmr = _result().financing_result.project_model_result
        ds = pmr.debt_sizing
        ops = pmr.operating_schedules
        bank_prod = list(ds.bank_production_mwh)
        base_prod = list(ops.production_mwh)
        ds_pids = list(ds.period_indices)
        ops_pids = list(ops.period_indices)
        pid2_ds = ds_pids.index(2)
        pid2_ops = ops_pids.index(2)
        assert bank_prod[pid2_ds] < base_prod[pid2_ops], "Bank P90 ≥ Base P50 at period 2"

    def test_p90_p50_ratio_consistent(self):
        """P90/P50 ≈ 3058/3535 = 0.865 from TechnicalParams."""
        pmr = _result().financing_result.project_model_result
        ds = pmr.debt_sizing
        ops = pmr.operating_schedules
        bank_prod = list(ds.bank_production_mwh)
        base_prod = list(ops.production_mwh)
        ds_pids = list(ds.period_indices)
        ops_pids = list(ops.period_indices)
        pid2_ds = ds_pids.index(2)
        pid2_ops = ops_pids.index(2)
        ratio = bank_prod[pid2_ds] / base_prod[pid2_ops]
        expected = 3058 / 3535
        assert abs(ratio - expected) < 0.01, f"P90/P50 ratio {ratio:.6f} vs expected {expected:.6f}"

    def test_bank_cfads_lt_base_cfads_operating(self):
        """Bank CFADS must be below base CFADS in operating periods (more conservative)."""
        pmr = _result().financing_result.project_model_result
        ds = pmr.debt_sizing
        psc = pmr.post_senior_cash
        bank_cfads = list(ds.bank_cfads_keur)
        base_cfads = list(psc.base_cfads_keur)
        pids_ds = list(ds.period_indices)
        pids_psc = list(psc.period_indices)

        for pid in range(2, 30):  # senior tenor
            if pid in pids_ds and pid in pids_psc:
                b = bank_cfads[pids_ds.index(pid)]
                base = base_cfads[pids_psc.index(pid)]
                assert b < base, (
                    f"Period {pid}: bank CFADS {b:.4f} >= base CFADS {base:.4f}"
                )

    def test_bank_cfads_balancing_gap_documented(self):
        """Bank CFADS gap at P2 is primarily balancing cost — CLEAN_POLICY_VS_WORKBOOK."""
        pmr = _result().financing_result.project_model_result
        ds = pmr.debt_sizing
        bank_cfads = list(ds.bank_cfads_keur)
        bank_prod = list(ds.bank_production_mwh)
        pids = list(ds.period_indices)
        pid2 = pids.index(2)

        finco_bank_cfads_p2 = bank_cfads[pid2]
        source_bank_cfads_p2 = 11_064.982  # DS!H49 anchor (source)
        gap = finco_bank_cfads_p2 - source_bank_cfads_p2
        # Balancing cost contribution
        bal_cost_keur = bank_prod[pid2] * 5.0 / 1000
        # Gap is roughly equal to balancing cost (within 150 kEUR for period rounding)
        assert abs(gap + bal_cost_keur) < 150, (
            f"Bank CFADS gap {gap:.2f} kEUR at P2 not explained by balancing "
            f"cost {bal_cost_keur:.2f} kEUR. Residual {gap + bal_cost_keur:.2f}. "
            f"Reclassify if a second cause is identified."
        )


# ── TestF  SHL Cash-Sweep Discipline ──────────────────────────────────────────


class TestF_SHLCashSweep:
    """G3B-F: Per-period SHL principal ≤ cash_available_for_shl_before_reserves."""

    def test_principal_never_exceeds_cash_available(self):
        pmr = _result().financing_result.project_model_result
        shl = pmr.shareholder_loan
        for pi, ca, pr in zip(
            shl.period_indices,
            shl.cash_available_for_shl_before_reserves_keur,
            shl.shl_principal_keur,
        ):
            if pr > 0:
                assert pr <= ca + 1e-6, (
                    f"Period {pi}: SHL principal {pr:.4f} > cash_available {ca:.4f} "
                    f"— CASH_SWEEP overpayment."
                )

    def test_shl_closing_zero_at_maturity(self):
        pmr = _result().financing_result.project_model_result
        shl = pmr.shareholder_loan
        pids = list(shl.period_indices)
        closing = list(shl.shl_closing_keur)
        # Closing balance at period 61 (maturity) must be zero or near-zero
        assert abs(closing[pids.index(61)]) < 1.0, (
            f"SHL not fully repaid at period 61: closing={closing[pids.index(61)]:.4f}"
        )

    def test_shl_total_principal_equals_opening(self):
        """Total SHL principal repaid = SHL opening at period 2."""
        pmr = _result().financing_result.project_model_result
        shl = pmr.shareholder_loan
        pids = list(shl.period_indices)
        total_repaid = sum(shl.shl_principal_keur)
        opening_p2 = shl.shl_opening_keur[pids.index(2)]
        assert abs(total_repaid - opening_p2) < 1.0, (
            f"Total SHL repaid {total_repaid:.4f} != SHL opening at P2 {opening_p2:.4f}"
        )


# ── TestG  SHL Construction Compounding Gap ───────────────────────────────────


class TestG_SHLConstructionCompoundingGap:
    """G3B-G: Document KUPI_SHL_CONSTRUCTION_COMPOUNDING_GAP.

    Source uses compound interest: SHL × ((1+8%)^2 − 1) = 11,340.658 kEUR.
    Clean engine uses shl_construction_day_count_fraction=0.0 → PIK = 0.
    Gap = 436.179 kEUR. Classification: CURRENT_FINCO_CAPABILITY_GAP.
    STOP: Do NOT implement compound interest without explicit authorization.
    """

    def test_construction_pik_is_zero(self):
        """Engine produces zero construction PIK (simple interest, dcf=0)."""
        pmr = _result().financing_result.project_model_result
        shl = pmr.shareholder_loan
        total_pik = sum(shl.shl_pik_interest_keur)
        assert total_pik == 0.0, (
            f"Construction PIK = {total_pik:.4f} kEUR; expected 0. "
            f"KUPI_SHL_CONSTRUCTION_COMPOUNDING_GAP: source has 11,340.658 kEUR compound."
        )

    def test_compounding_gap_documented(self):
        """The compound-vs-simple construction interest gap is within the known range."""
        shl_principal = _KUPI_SHL_PRINCIPAL_KEUR
        # Compound: SHL × ((1.08)^2 − 1)
        compound_pik = shl_principal * ((1.08 ** 2) - 1)
        # Simple: SHL × 0.08 × dcf_periods (dcf=2)
        simple_pik = shl_principal * 0.08 * 2
        gap = compound_pik - simple_pik
        # Source compound PIK anchor: 11,340.658 kEUR
        source_compound = 11_340.658
        # Gap = 436.179 kEUR (source − simple counterfactual)
        source_simple_counterfactual = 10_904.479
        assert abs(compound_pik - source_compound) < 1.0, (
            f"Compound PIK formula check: {compound_pik:.4f} vs source {source_compound:.4f}"
        )
        assert abs(gap - (source_compound - source_simple_counterfactual)) < 5.0, (
            f"Gap {gap:.4f} vs expected ~436.179"
        )


# ── TestH  CO2 Bridge / SQ-02 ─────────────────────────────────────────────────


class TestH_CO2Bridge:
    """G3B-H: SQ-02 SOURCE_INPUT_INCONSISTENCY — CO2 toggle=FALSE but source CF includes CO2.

    Run A: co2_enabled=False (literal source toggle).
    Run B: co2_enabled=True + source-effective CO2 parameters.
    Bridge = Rev_B − Rev_A ≈ +62,731 kEUR total.
    """

    def test_co2_bridge_positive(self):
        proj_b = create_kupi_project_source_effective_co2()
        result_b = run_project_shareholder_waterfall_model(proj_b)
        rev_a = sum(_result().financing_result.project_model_result.operating_schedules.revenue_keur)
        rev_b = sum(result_b.financing_result.project_model_result.operating_schedules.revenue_keur)
        bridge = rev_b - rev_a
        assert bridge > 50_000, f"CO2 bridge {bridge:.2f} kEUR unexpectedly small (SQ-02 check)"

    def test_co2_bridge_magnitude(self):
        proj_b = create_kupi_project_source_effective_co2()
        result_b = run_project_shareholder_waterfall_model(proj_b)
        rev_a = sum(_result().financing_result.project_model_result.operating_schedules.revenue_keur)
        rev_b = sum(result_b.financing_result.project_model_result.operating_schedules.revenue_keur)
        bridge = rev_b - rev_a
        # Blind run showed ~62,731 kEUR
        assert abs(bridge - 62_731.795) < 500, (
            f"CO2 bridge {bridge:.4f} kEUR deviates from blind run anchor 62731.795"
        )


# ── TestI  DSCR Revenue-Mix Formula Gap ───────────────────────────────────────


class TestI_DSCRRevenueMixGap:
    """G3B-I: KUPI_DSCR_REVENUE_MIX_FORMULA_GAP — CURRENT_FINCO_CAPABILITY_GAP.

    Source DS!row19 derives DSCR from revenue mix dynamically.
    Engine uses explicit schedule (1.50,)*24 + (1.75,)*4.
    Do NOT implement dynamic derivation without authorization.
    """

    def test_sculpting_config_explicit_schedule(self):
        """Fixture must supply explicit DSCR schedule to SeniorSculptingConfig."""
        proj = _proj()
        sc = proj.financing.senior_sculpting_config
        assert sc.enabled is True
        assert len(sc.target_dscr_schedule) == 28
        # First 24 periods at 1.50, last 4 at 1.75
        assert all(abs(v - 1.50) < 1e-9 for v in sc.target_dscr_schedule[:24])
        assert all(abs(v - 1.75) < 1e-9 for v in sc.target_dscr_schedule[24:])

    def test_bank_dscr_above_one(self):
        """Bank DSCR > 1 throughout senior tenor."""
        pmr = _result().financing_result.project_model_result
        ds = pmr.debt_sizing
        bank_dscr = list(ds.bank_sizing_dscr)
        pids = list(ds.period_indices)
        for pid in range(2, 30):
            if pid in pids:
                dscr = bank_dscr[pids.index(pid)]
                assert dscr > 1.0, f"Bank sizing DSCR at period {pid} = {dscr:.4f} ≤ 1"


# ── TestJ  Sponsor Returns Compass ────────────────────────────────────────────


class TestJ_SponsorReturnsCompass:
    """G3B-J: Sponsor returns are in plausible range given KUPI_SPONSOR_CONTRIBUTION_TIMING_POLICY_GAP.

    Source Equity IRR: 17.136%; Source Gross Sponsor XIRR: 16.987%.
    Finco may differ due to contribution timing policy (DEFINITION_OR_TIMING_DIFFERENCE).
    Do not tune inputs to hit source IRR targets.
    """

    def test_total_sponsor_xirr_in_range(self):
        """Sponsor XIRR in [10%, 30%] — sanity compass, not parity check."""
        r = _result()
        xirr = r.total_sponsor_xirr
        assert 0.10 < xirr < 0.30, f"total_sponsor_xirr={xirr:.4%} outside plausible range"

    def test_pure_equity_xirr_in_range(self):
        # pure_equity_xirr compares equity cashflows only; can be elevated
        # when share capital is small relative to total sponsor contribution.
        # KUPI_SPONSOR_CONTRIBUTION_TIMING_POLICY_GAP: source places full SHL+Capital at FC.
        r = _result()
        xirr = r.pure_equity_xirr
        assert 0.10 < xirr < 0.60, f"pure_equity_xirr={xirr:.4%} outside plausible range"
