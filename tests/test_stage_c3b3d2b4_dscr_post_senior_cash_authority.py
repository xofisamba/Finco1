"""
C3B3D2B4 — Base vs Bank DSCR + Post-Senior Cash Authority

Proves:
1. bank_sizing_dscr in DebtSizingSchedules = bank CFADS / senior DS  (lender sizing metric)
2. base_dscr in SeniorDebtSchedules = base CFADS / senior DS  (Base actual DSCR)
3. senior_dscr backward-compat property returns base_dscr
4. PostSeniorCashSchedules contract and math
5. post_senior_cash populated in ProjectModelResult
6. SHL seam consumes post_senior_cash when present; never reads bank_cfads_keur
7. Provenance fix: senior_principal_keur sources debt_sizing.bank_cfads_keur
8. DerivationEvidence for post_senior_cash present

Governance assertions:
  BASE_CFADS_IS_POST_SENIOR_CASH_AUTHORITY
  BANK_CFADS_IS_SIZING_ONLY_NEVER_FLOWS_INTO_SHL
  DSRA_NOT_IMPLEMENTED
  SHL_OUTSIDE_FIXED_POINT
"""
from __future__ import annotations

import dataclasses
import inspect
import math

import pytest


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_tuho_base_op():
    from app.project_factories import create_default_tuho_wind1
    from financial_engine.adapters.project_inputs import from_project_inputs
    return from_project_inputs(create_default_tuho_wind1())


def _make_simple_senior_debt_policy(repayment_start=2, maturity=29):
    from financial_engine.senior_debt.policy import SeniorDebtPolicy, SeniorDebtSizingMode, DayCountConvention
    return SeniorDebtPolicy(
        policy_id="c3b3d2b4_test", policy_version="1.0",
        sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
        target_dscr=1.2, maximum_gearing=None, annual_fixed_rate=0.05,
        periods_per_year=2, day_count_convention=DayCountConvention.ACT_365,
        repayment_start_period_index=repayment_start,
        maturity_period_index=maturity,
        convergence_tolerance_keur=1.0,
        convergence_relative_tolerance=0.001,
        maximum_iterations=300, permit_terminal_balloon=True,
    )


def _make_simple_sd_inputs(eligible_keur=100_000.0):
    from financial_engine.senior_debt.inputs import SeniorDebtInputs
    return SeniorDebtInputs(
        eligible_project_cost_keur=eligible_keur,
        initial_debt_guess_keur=eligible_keur * 0.6,
        period_rates=(), explicit_principal_schedule=None,
    )


def _make_tuho_tax_input():
    from financial_engine.inputs import TaxCalculationInput
    from finco_parity.tax_reference_inputs import build_tax_policy, build_opening_loss_vintages
    policy = build_tax_policy("tuho")
    vintages = build_opening_loss_vintages("tuho")
    return TaxCalculationInput(
        policy=policy, opening_loss_vintages=vintages,
        period_interest=(), period_adjustments=(),
    )


@pytest.fixture(scope="module")
def tuho_result():
    from financial_engine.inputs import YieldScenario, DebtSizingCaseInput, SeniorDebtModelInput
    from financial_engine.orchestrator import run_senior_debt_model
    base_op = _make_tuho_base_op()
    tax_input = _make_tuho_tax_input()
    bank_case = DebtSizingCaseInput(
        production_yield_scenario=YieldScenario.P90_10Y,
        source_label="c3b3d2b4_tuho_bank_case",
    )
    model = SeniorDebtModelInput(
        operating=base_op,
        tax=tax_input,
        senior_debt_policy=_make_simple_senior_debt_policy(repayment_start=2, maturity=61),
        senior_debt_inputs=_make_simple_sd_inputs(100_000.0),
        debt_sizing_case=bank_case,
    )
    return run_senior_debt_model(model)


# ---------------------------------------------------------------------------
# Group A — PostSeniorCashSchedules dataclass contract
# ---------------------------------------------------------------------------

class TestA_PostSeniorCashSchedulesContract:

    def test_a1_dataclass_exists(self):
        from financial_engine.results import PostSeniorCashSchedules
        assert dataclasses.is_dataclass(PostSeniorCashSchedules)

    def test_a2_frozen(self):
        from financial_engine.results import PostSeniorCashSchedules
        params = dataclasses.fields(PostSeniorCashSchedules)
        assert params  # non-empty
        inst = PostSeniorCashSchedules(
            period_indices=(0, 1),
            base_cfads_keur=(100.0, 200.0),
            senior_debt_service_keur=(80.0, 80.0),
            cash_after_senior_before_reserves_keur=(20.0, 120.0),
            cash_available_for_shl_before_reserves_keur=(20.0, 120.0),
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError, TypeError)):
            inst.period_indices = (99,)  # direct assignment must raise on frozen

    def test_a3_required_fields(self):
        from financial_engine.results import PostSeniorCashSchedules
        field_names = {f.name for f in dataclasses.fields(PostSeniorCashSchedules)}
        required = {
            "period_indices",
            "base_cfads_keur",
            "senior_debt_service_keur",
            "cash_after_senior_before_reserves_keur",
            "cash_available_for_shl_before_reserves_keur",
        }
        assert required <= field_names

    def test_a4_no_bank_cfads_field(self):
        from financial_engine.results import PostSeniorCashSchedules
        field_names = {f.name for f in dataclasses.fields(PostSeniorCashSchedules)}
        # Bank CFADS must never appear in PostSeniorCashSchedules
        assert "bank_cfads_keur" not in field_names
        assert "bank_sizing_dscr" not in field_names


# ---------------------------------------------------------------------------
# Group B — bank_sizing_dscr field on DebtSizingSchedules
# ---------------------------------------------------------------------------

class TestB_BankSizingDscr:

    def test_b1_field_exists(self):
        from financial_engine.results import DebtSizingSchedules
        field_names = {f.name for f in dataclasses.fields(DebtSizingSchedules)}
        assert "bank_sizing_dscr" in field_names

    def test_b2_populated_in_run(self, tuho_result):
        ds = tuho_result.debt_sizing
        assert ds is not None
        assert hasattr(ds, "bank_sizing_dscr")
        assert isinstance(ds.bank_sizing_dscr, tuple)
        assert len(ds.bank_sizing_dscr) == len(ds.period_indices)

    def test_b3_none_where_no_debt_service(self, tuho_result):
        ds = tuho_result.debt_sizing
        sd = tuho_result.senior_debt
        sd_service_by_idx = dict(zip(sd.period_indices, sd.senior_debt_service_keur))
        # Periods not in sd schedule should have None bank_sizing_dscr
        for idx, dscr_val in zip(ds.period_indices, ds.bank_sizing_dscr):
            if idx not in sd_service_by_idx or sd_service_by_idx[idx] == 0.0:
                assert dscr_val is None, (
                    f"period {idx}: expected None bank_sizing_dscr where DS=0, got {dscr_val}"
                )

    def test_b4_finite_where_positive_service(self, tuho_result):
        ds = tuho_result.debt_sizing
        sd = tuho_result.senior_debt
        sd_service_by_idx = dict(zip(sd.period_indices, sd.senior_debt_service_keur))
        bank_cfads_by_idx = dict(zip(ds.period_indices, ds.bank_cfads_keur))
        for idx, dscr_val in zip(ds.period_indices, ds.bank_sizing_dscr):
            svc = sd_service_by_idx.get(idx, 0.0)
            bcfads = bank_cfads_by_idx.get(idx, 0.0)
            if svc > 0.0 and math.isfinite(bcfads):
                assert dscr_val is not None
                assert math.isfinite(dscr_val)

    def test_b5_formula_correct(self, tuho_result):
        """bank_sizing_dscr[p] = bank_cfads[p] / senior_ds[p]."""
        ds = tuho_result.debt_sizing
        sd = tuho_result.senior_debt
        sd_service_by_idx = dict(zip(sd.period_indices, sd.senior_debt_service_keur))
        bank_cfads_by_idx = dict(zip(ds.period_indices, ds.bank_cfads_keur))
        tol = 1e-6
        for idx, dscr_val in zip(ds.period_indices, ds.bank_sizing_dscr):
            svc = sd_service_by_idx.get(idx, 0.0)
            if dscr_val is not None:
                expected = bank_cfads_by_idx[idx] / svc
                assert abs(dscr_val - expected) < tol, (
                    f"period {idx}: bank_sizing_dscr expected {expected:.6f}, got {dscr_val:.6f}"
                )


# ---------------------------------------------------------------------------
# Group C — base_dscr field on SeniorDebtSchedules (result type)
# ---------------------------------------------------------------------------

class TestC_BaseDscrField:

    def test_c1_field_named_base_dscr(self):
        from financial_engine.results import SeniorDebtSchedules
        field_names = {f.name for f in dataclasses.fields(SeniorDebtSchedules)}
        assert "base_dscr" in field_names

    def test_c2_senior_dscr_field_removed(self):
        from financial_engine.results import SeniorDebtSchedules
        field_names = {f.name for f in dataclasses.fields(SeniorDebtSchedules)}
        # senior_dscr is now a property alias, not a dataclass field
        assert "senior_dscr" not in field_names

    def test_c3_base_dscr_populated(self, tuho_result):
        sd = tuho_result.senior_debt
        assert hasattr(sd, "base_dscr")
        assert isinstance(sd.base_dscr, tuple)
        assert len(sd.base_dscr) == len(sd.period_indices)

    def test_c4_none_where_no_service(self, tuho_result):
        sd = tuho_result.senior_debt
        for idx, base_dscr in zip(sd.period_indices, sd.base_dscr):
            svc_idx = list(sd.period_indices).index(idx)
            svc = sd.senior_debt_service_keur[svc_idx]
            if svc == 0.0:
                assert base_dscr is None

    def test_c5_finite_where_positive_service(self, tuho_result):
        sd = tuho_result.senior_debt
        for dscr_val, svc in zip(sd.base_dscr, sd.senior_debt_service_keur):
            if svc > 0.0:
                assert dscr_val is not None
                assert math.isfinite(dscr_val)


# ---------------------------------------------------------------------------
# Group D — senior_dscr backward-compat property
# ---------------------------------------------------------------------------

class TestD_SeniorDscrBackwardCompat:

    def test_d1_property_exists(self):
        from financial_engine.results import SeniorDebtSchedules
        assert isinstance(
            SeniorDebtSchedules.__dict__.get("senior_dscr"),
            property,
        ), "SeniorDebtSchedules.senior_dscr must be a @property"

    def test_d2_returns_base_dscr(self, tuho_result):
        sd = tuho_result.senior_debt
        assert sd.senior_dscr is sd.base_dscr

    def test_d3_identity_not_copy(self, tuho_result):
        sd = tuho_result.senior_debt
        # Same tuple object — not a copy
        assert sd.senior_dscr is sd.base_dscr


# ---------------------------------------------------------------------------
# Group E — Bank DSCR vs Base DSCR are distinct (P50 ≠ P90)
# ---------------------------------------------------------------------------

class TestE_TwoDscrsDiffer:

    def test_e1_bank_sizing_dscr_and_base_dscr_differ(self, tuho_result):
        """P90-10y bank CFADS ≠ P50 base CFADS → two DSCRs differ on debt periods."""
        ds = tuho_result.debt_sizing
        sd = tuho_result.senior_debt
        sd_periods = set(sd.period_indices)
        bank_dscr_by_idx = dict(zip(ds.period_indices, ds.bank_sizing_dscr))
        base_dscr_by_idx = dict(zip(sd.period_indices, sd.base_dscr))

        diffs = []
        for idx in sd_periods:
            bk = bank_dscr_by_idx.get(idx)
            ba = base_dscr_by_idx.get(idx)
            if bk is not None and ba is not None:
                diffs.append(abs(bk - ba))

        assert diffs, "No shared debt periods with non-None DSCRs found"
        # For a P50 vs P90 split, at least some periods should have different DSCRs
        assert any(d > 1e-6 for d in diffs), (
            "bank_sizing_dscr and base_dscr are identical on all debt periods — "
            "expected them to differ for P50 vs P90 yield scenarios"
        )

    def test_e2_bank_sizing_dscr_lower_than_base(self, tuho_result):
        """P90-10y is a conservative scenario → bank CFADS ≤ base CFADS → bank DSCR ≤ base DSCR (typically)."""
        ds = tuho_result.debt_sizing
        sd = tuho_result.senior_debt
        bank_dscr_by_idx = dict(zip(ds.period_indices, ds.bank_sizing_dscr))
        base_dscr_by_idx = dict(zip(sd.period_indices, sd.base_dscr))

        lower_count = 0
        compared = 0
        for idx in sd.period_indices:
            bk = bank_dscr_by_idx.get(idx)
            ba = base_dscr_by_idx.get(idx)
            if bk is not None and ba is not None:
                compared += 1
                if bk <= ba + 1e-6:
                    lower_count += 1

        assert compared > 0
        # Most periods should have bank ≤ base (P90 is conservative)
        assert lower_count / compared >= 0.9, (
            f"Expected bank_sizing_dscr ≤ base_dscr on most periods; "
            f"only {lower_count}/{compared} satisfy this"
        )


# ---------------------------------------------------------------------------
# Group F — PostSeniorCashSchedules populated in result
# ---------------------------------------------------------------------------

class TestF_PostSeniorCashPopulated:

    def test_f1_not_none(self, tuho_result):
        assert tuho_result.post_senior_cash is not None

    def test_f2_period_count_matches_all_periods(self, tuho_result):
        psc = tuho_result.post_senior_cash
        all_periods = tuho_result.periods
        assert len(psc.period_indices) == len(all_periods)

    def test_f3_period_indices_match(self, tuho_result):
        psc = tuho_result.post_senior_cash
        expected = tuple(p.period_index for p in tuho_result.periods)
        assert psc.period_indices == expected

    def test_f4_parallel_vector_lengths_consistent(self, tuho_result):
        psc = tuho_result.post_senior_cash
        n = len(psc.period_indices)
        assert len(psc.base_cfads_keur) == n
        assert len(psc.senior_debt_service_keur) == n
        assert len(psc.cash_after_senior_before_reserves_keur) == n
        assert len(psc.cash_available_for_shl_before_reserves_keur) == n

    def test_f5_base_cfads_matches_tax_and_cfads(self, tuho_result):
        """post_senior_cash.base_cfads_keur = tax_and_cfads.cfads_keur (Base CFADS)."""
        psc = tuho_result.post_senior_cash
        tac = tuho_result.tax_and_cfads
        tac_by_idx = dict(zip(tac.period_indices, tac.cfads_keur))
        for idx, bcfads in zip(psc.period_indices, psc.base_cfads_keur):
            expected = tac_by_idx.get(idx, 0.0)
            assert abs(bcfads - expected) < 1e-6, (
                f"period {idx}: post_senior_cash.base_cfads_keur={bcfads:.4f} "
                f"but tax_and_cfads.cfads_keur={expected:.4f}"
            )


# ---------------------------------------------------------------------------
# Group G — cash_after_senior_before_reserves_keur formula
# ---------------------------------------------------------------------------

class TestG_CashAfterSeniorFormula:

    def test_g1_formula_base_cfads_minus_senior_ds(self, tuho_result):
        """cash_after = base_cfads - senior_ds (signed, per period)."""
        psc = tuho_result.post_senior_cash
        for idx, after, bcfads, sds in zip(
            psc.period_indices,
            psc.cash_after_senior_before_reserves_keur,
            psc.base_cfads_keur,
            psc.senior_debt_service_keur,
        ):
            expected = bcfads - sds
            assert abs(after - expected) < 1e-6, (
                f"period {idx}: cash_after={after:.4f}, expected {expected:.4f}"
            )

    def test_g2_signed_can_be_negative(self, tuho_result):
        """Signed cash can be negative (base CFADS insufficient to cover debt service)."""
        psc = tuho_result.post_senior_cash
        # Not required to find negative — but if any senior DS > base CFADS, should be negative
        for after, bcfads, sds in zip(
            psc.cash_after_senior_before_reserves_keur,
            psc.base_cfads_keur,
            psc.senior_debt_service_keur,
        ):
            if sds > bcfads:
                assert after < 0.0, (
                    f"Expected negative cash_after where sds > base_cfads; got {after}"
                )

    def test_g3_zero_where_no_senior_ds_and_zero_cfads(self, tuho_result):
        psc = tuho_result.post_senior_cash
        for idx, after, bcfads, sds in zip(
            psc.period_indices,
            psc.cash_after_senior_before_reserves_keur,
            psc.base_cfads_keur,
            psc.senior_debt_service_keur,
        ):
            if bcfads == 0.0 and sds == 0.0:
                assert after == 0.0

    def test_g4_post_maturity_equals_base_cfads(self, tuho_result):
        """After senior debt maturity, senior_ds=0 → cash_after = base_cfads."""
        psc = tuho_result.post_senior_cash
        sd = tuho_result.senior_debt
        sd_tenor_max = max(sd.period_indices) if sd.period_indices else -1
        for idx, after, bcfads, sds in zip(
            psc.period_indices,
            psc.cash_after_senior_before_reserves_keur,
            psc.base_cfads_keur,
            psc.senior_debt_service_keur,
        ):
            if idx > sd_tenor_max:
                assert sds == 0.0
                assert abs(after - bcfads) < 1e-6


# ---------------------------------------------------------------------------
# Group H — cash_available_for_shl_before_reserves_keur formula
# ---------------------------------------------------------------------------

class TestH_CashAvailableFormula:

    def test_h1_equals_max_0_cash_after(self, tuho_result):
        """cash_available = max(0, cash_after)."""
        psc = tuho_result.post_senior_cash
        for idx, avail, after in zip(
            psc.period_indices,
            psc.cash_available_for_shl_before_reserves_keur,
            psc.cash_after_senior_before_reserves_keur,
        ):
            expected = max(0.0, after)
            assert abs(avail - expected) < 1e-6, (
                f"period {idx}: cash_available={avail:.4f}, expected {expected:.4f}"
            )

    def test_h2_non_negative(self, tuho_result):
        psc = tuho_result.post_senior_cash
        for idx, avail in zip(
            psc.period_indices,
            psc.cash_available_for_shl_before_reserves_keur,
        ):
            assert avail >= 0.0, f"period {idx}: cash_available is negative: {avail}"

    def test_h3_zero_construction_periods(self, tuho_result):
        """Construction periods have zero senior DS → cash_available = base_cfads (pre-PIK)."""
        psc = tuho_result.post_senior_cash
        periods_meta = {p.period_index: p for p in tuho_result.periods}
        for idx, avail, sds in zip(
            psc.period_indices,
            psc.cash_available_for_shl_before_reserves_keur,
            psc.senior_debt_service_keur,
        ):
            p = periods_meta.get(idx)
            if p and p.is_construction:
                # Construction: no senior DS (debt not yet drawn)
                assert sds == 0.0


# ---------------------------------------------------------------------------
# Group I — SHL seam consumes post_senior_cash
# ---------------------------------------------------------------------------

class TestI_ShlSeamConsumesPostSeniorCash:

    def test_i1_seam_returns_results(self, tuho_result):
        from financial_engine.adapters.shl_cash_seam import compute_shl_cash_from_phase2c
        results = compute_shl_cash_from_phase2c(tuho_result)
        assert len(results) == len(tuho_result.periods)

    def test_i2_seam_cfads_matches_base_cfads(self, tuho_result):
        """SHL seam reads Base CFADS (post_senior_cash.base_cfads_keur), not bank CFADS."""
        from financial_engine.adapters.shl_cash_seam import compute_shl_cash_from_phase2c
        seam_results = compute_shl_cash_from_phase2c(tuho_result)
        psc = tuho_result.post_senior_cash
        psc_cfads = dict(zip(psc.period_indices, psc.base_cfads_keur))
        for sr in seam_results:
            expected = psc_cfads[sr.period_index]
            assert abs(sr.cfads_keur - expected) < 1e-6, (
                f"period {sr.period_index}: seam cfads={sr.cfads_keur:.4f}, "
                f"post_senior_cash base_cfads={expected:.4f}"
            )

    def test_i3_seam_cash_available_matches_post_senior_cash(self, tuho_result):
        """Seam cash_available_for_shl = post_senior_cash.cash_available (except construction=0)."""
        from financial_engine.adapters.shl_cash_seam import compute_shl_cash_from_phase2c
        seam_results = compute_shl_cash_from_phase2c(tuho_result)
        psc = tuho_result.post_senior_cash
        psc_avail = dict(zip(psc.period_indices, psc.cash_available_for_shl_before_reserves_keur))
        for sr in seam_results:
            if sr.is_construction:
                assert sr.cash_available_for_shl_keur == 0.0
            else:
                expected = psc_avail[sr.period_index]
                assert abs(sr.cash_available_for_shl_keur - expected) < 1e-6, (
                    f"period {sr.period_index}: seam avail={sr.cash_available_for_shl_keur:.4f}, "
                    f"psc avail={expected:.4f}"
                )

    def test_i4_seam_never_reads_bank_cfads(self):
        """SHL seam function code must never ACCESS debt_sizing.bank_cfads_keur.

        Docstrings may mention these paths as governance labels; only code lines matter.
        """
        from financial_engine.adapters import shl_cash_seam
        funcs = [
            shl_cash_seam.compute_shl_cash_from_phase2c,
            shl_cash_seam._compute_shl_cash_from_post_senior_cash,
        ]
        import ast
        for fn in funcs:
            fn_src = inspect.getsource(fn)
            # Strip leading whitespace so ast can parse method source.
            import textwrap
            try:
                tree = ast.parse(textwrap.dedent(fn_src))
            except SyntaxError:
                continue
            # Check attribute accesses in code (not in string literals / docstrings).
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    # Detect .bank_cfads_keur access on any object
                    assert node.attr != "bank_cfads_keur", (
                        f"{fn.__name__}: code accesses .bank_cfads_keur — forbidden"
                    )


# ---------------------------------------------------------------------------
# Group J — Provenance: senior_principal_keur sources bank_cfads_keur
# ---------------------------------------------------------------------------

class TestJ_Provenance:

    def test_j1_senior_principal_evidence_references_bank_cfads(self, tuho_result):
        """DerivationEvidence for senior_principal_keur must cite debt_sizing.bank_cfads_keur."""
        evidence = tuho_result.provenance.derivation_evidence
        senior_principal_ev = [
            e for e in evidence
            if e.output_path == "senior_debt.senior_principal_keur"
        ]
        assert senior_principal_ev, "No DerivationEvidence for senior_debt.senior_principal_keur"
        ev = senior_principal_ev[0]
        assert "debt_sizing.bank_cfads_keur" in ev.input_paths, (
            f"senior_principal_keur evidence input_paths must include debt_sizing.bank_cfads_keur; "
            f"got {ev.input_paths}"
        )

    def test_j2_stale_reference_removed(self, tuho_result):
        """tax_and_cfads.cfads_keur must NOT appear as input for senior_principal_keur."""
        evidence = tuho_result.provenance.derivation_evidence
        senior_principal_ev = [
            e for e in evidence
            if e.output_path == "senior_debt.senior_principal_keur"
        ]
        assert senior_principal_ev
        ev = senior_principal_ev[0]
        assert "tax_and_cfads.cfads_keur" not in ev.input_paths, (
            "Stale reference tax_and_cfads.cfads_keur still in senior_principal_keur provenance"
        )

    def test_j3_post_senior_cash_evidence_present(self, tuho_result):
        """DerivationEvidence for post_senior_cash must be in provenance."""
        evidence = tuho_result.provenance.derivation_evidence
        psc_ev = [e for e in evidence if e.output_path == "post_senior_cash"]
        assert psc_ev, "No DerivationEvidence for post_senior_cash"

    def test_j4_post_senior_cash_evidence_cites_base_cfads(self, tuho_result):
        evidence = tuho_result.provenance.derivation_evidence
        psc_ev = [e for e in evidence if e.output_path == "post_senior_cash"][0]
        assert "tax_and_cfads.cfads_keur" in psc_ev.input_paths, (
            f"post_senior_cash evidence must cite tax_and_cfads.cfads_keur; got {psc_ev.input_paths}"
        )

    def test_j5_post_senior_cash_evidence_cites_senior_ds(self, tuho_result):
        evidence = tuho_result.provenance.derivation_evidence
        psc_ev = [e for e in evidence if e.output_path == "post_senior_cash"][0]
        assert "senior_debt.senior_debt_service_keur" in psc_ev.input_paths, (
            f"post_senior_cash evidence must cite senior_debt.senior_debt_service_keur"
        )

    def test_j6_post_senior_cash_notes_dsra_not_implemented(self, tuho_result):
        evidence = tuho_result.provenance.derivation_evidence
        psc_ev = [e for e in evidence if e.output_path == "post_senior_cash"][0]
        notes_text = " ".join(psc_ev.notes)
        assert "DSRA_NOT_IMPLEMENTED" in notes_text, (
            "post_senior_cash provenance must document DSRA_NOT_IMPLEMENTED"
        )


# ---------------------------------------------------------------------------
# Group K — Bank CFADS is sizing-only: never reaches SHL or distributions
# ---------------------------------------------------------------------------

class TestK_BankCfadsIsSizingOnly:

    def test_k1_bank_cfads_not_in_tax_and_cfads(self, tuho_result):
        """tax_and_cfads.cfads_keur is Base CFADS, not bank CFADS."""
        tac = tuho_result.tax_and_cfads
        ds = tuho_result.debt_sizing
        assert tac is not None and ds is not None
        # They should differ (P50 ≠ P90 CFADS)
        tac_total = sum(tac.cfads_keur)
        bank_total = sum(ds.bank_cfads_keur)
        # For a P50 vs P90 split, total CFADS should differ
        assert abs(tac_total - bank_total) > 1.0, (
            "tax_and_cfads.cfads_keur and debt_sizing.bank_cfads_keur are identical — "
            "expected them to differ for P50 vs P90 yield"
        )

    def test_k2_post_senior_cash_uses_base_not_bank(self, tuho_result):
        """post_senior_cash.base_cfads_keur = Base CFADS; not bank CFADS."""
        psc = tuho_result.post_senior_cash
        ds = tuho_result.debt_sizing
        tac = tuho_result.tax_and_cfads
        tac_by_idx = dict(zip(tac.period_indices, tac.cfads_keur))
        bank_by_idx = dict(zip(ds.period_indices, ds.bank_cfads_keur))
        for idx, psc_cfads in zip(psc.period_indices, psc.base_cfads_keur):
            base_cfads = tac_by_idx.get(idx, 0.0)
            bank_cfads = bank_by_idx.get(idx)
            assert abs(psc_cfads - base_cfads) < 1e-6, (
                f"period {idx}: psc.base_cfads_keur={psc_cfads:.4f} ≠ base {base_cfads:.4f}"
            )
            if bank_cfads is not None and abs(base_cfads - bank_cfads) > 1e-3:
                # psc must equal base, not bank
                assert abs(psc_cfads - bank_cfads) > 1e-3

    def test_k3_shl_seam_ignores_bank_cfads(self, tuho_result):
        """SHL seam result never equals bank CFADS where it differs from base."""
        from financial_engine.adapters.shl_cash_seam import compute_shl_cash_from_phase2c
        seam = compute_shl_cash_from_phase2c(tuho_result)
        ds = tuho_result.debt_sizing
        bank_by_idx = dict(zip(ds.period_indices, ds.bank_cfads_keur))
        tac = tuho_result.tax_and_cfads
        base_by_idx = dict(zip(tac.period_indices, tac.cfads_keur))
        for sr in seam:
            idx = sr.period_index
            base = base_by_idx.get(idx, 0.0)
            bank = bank_by_idx.get(idx)
            # Seam cfads must equal base, not bank (where they differ)
            assert abs(sr.cfads_keur - base) < 1e-6


# ---------------------------------------------------------------------------
# Group L — ProjectModelResult contract
# ---------------------------------------------------------------------------

class TestL_ProjectModelResultContract:

    def test_l1_post_senior_cash_field_in_result(self):
        from financial_engine.results import ProjectModelResult
        field_names = {f.name for f in dataclasses.fields(ProjectModelResult)}
        assert "post_senior_cash" in field_names

    def test_l2_post_senior_cash_optional_default_none(self):
        from financial_engine.results import ProjectModelResult
        field_map = {f.name: f for f in dataclasses.fields(ProjectModelResult)}
        f = field_map["post_senior_cash"]
        assert f.default is None

    def test_l3_phase2a_result_has_none(self):
        from financial_engine.orchestrator import run_operating_model
        from app.project_factories import create_default_tuho_wind1
        from financial_engine.adapters.project_inputs import from_project_inputs
        op = from_project_inputs(create_default_tuho_wind1())
        result = run_operating_model(op)
        assert result.post_senior_cash is None

    def test_l4_phase2c_result_has_post_senior_cash(self, tuho_result):
        assert tuho_result.post_senior_cash is not None


# ---------------------------------------------------------------------------
# Group M — Governance: identity-free production scanning
# ---------------------------------------------------------------------------

class TestM_GovernanceIdentityFree:

    def _read(self, rel: str) -> str:
        import pathlib
        return (pathlib.Path(__file__).parent.parent / rel).read_text()

    def test_m1_results_py_no_project_identity(self):
        src = self._read("financial_engine/results.py").lower()
        for tok in ("oborovo", "tuho", "project.name", "project.code"):
            assert tok not in src, f"results.py: forbidden token {tok!r}"

    def test_m2_orchestrator_no_project_identity_in_post_senior_cash(self):
        from financial_engine.orchestrator import run_senior_debt_model
        src = inspect.getsource(run_senior_debt_model)
        for tok in ("oborovo", "tuho"):
            assert tok not in src.lower(), (
                f"run_senior_debt_model: forbidden token {tok!r}"
            )

    def test_m3_shl_seam_no_project_dispatch_in_calculation(self):
        """SHL seam must not dispatch on project identity in calculation code.

        Historical reconciliation labels (e.g. SOURCE_VECTOR_IDENTITY_FOR_OBOROVO)
        are allowed in docstrings; project-name tokens in calculation code are not.
        """
        from financial_engine.adapters import shl_cash_seam
        # Check only function/method code, not module-level docstring.
        funcs = [
            shl_cash_seam.compute_shl_cash_from_phase2c,
            shl_cash_seam._compute_shl_cash_from_post_senior_cash,
        ]
        for fn in funcs:
            fn_src = inspect.getsource(fn).lower()
            for tok in ("tuho", "project.name", "project.code"):
                assert tok not in fn_src, (
                    f"{fn.__name__}: forbidden token {tok!r} in calculation code"
                )

    def test_m4_no_forbidden_abstractions_in_results(self):
        src = self._read("financial_engine/results.py")
        for pat in ("DebtSizingScenario", "ProductionScenarioScope",
                    "bank_sizing_scenario", "bank_sizing_cfads_keur"):
            assert pat not in src, f"results.py: forbidden abstraction {pat!r}"


# ---------------------------------------------------------------------------
# Group N — Seam legacy path still functional (post_senior_cash=None)
# ---------------------------------------------------------------------------

class TestN_SeamLegacyPath:

    def test_n1_seam_works_without_post_senior_cash(self):
        """Legacy path: when post_senior_cash is None, seam derives from tac+sd."""
        from financial_engine.results import (
            ProjectModelResult, OperatingPeriodResult, OperatingSchedules,
            TaxAndCfadsSchedules, SeniorDebtSchedules, PostSeniorCashSchedules,
        )
        from financial_engine.adapters.shl_cash_seam import compute_shl_cash_from_phase2c
        from financial_engine.provenance import EngineProvenance, DerivationEvidence
        from datetime import date

        # Build a minimal result with post_senior_cash=None
        period = OperatingPeriodResult(
            period_index=0, period_start=date(2025, 1, 1), period_end=date(2025, 6, 30),
            year_index=0.0, period_in_year=0.5, is_construction=False, is_operation=True,
            is_ppa_active=True, days_in_period=181, day_fraction=0.496,
            production_mwh=1000.0, revenue_keur=50.0, opex_keur=10.0, ebitda_keur=40.0,
            book_depreciation_keur=5.0, tax_depreciation_keur=5.0, ebit_keur=35.0,
        )
        provenance = EngineProvenance(
            engine_version="test", run_path_id="test",
            input_fingerprint="abc", derivation_evidence=(),
        )
        op_sched = OperatingSchedules(
            period_indices=(0,), production_mwh=(1000.0,), revenue_keur=(50.0,),
            opex_keur=(10.0,), ebitda_keur=(40.0,), book_depreciation_keur=(5.0,),
            tax_depreciation_keur=(5.0,), ebit_keur=(35.0,),
        )
        tac = TaxAndCfadsSchedules(
            period_indices=(0,),
            taxable_profit_keur=(30.0,), taxable_income_before_losses_audit_keur=(30.0,),
            taxable_profit_after_losses_audit_keur=(30.0,),
            tax_keur=(6.0,), corporate_tax_cash_keur=(6.0,),
            cit_accrual_audit_keur=(6.0,), cash_tax_bridge_reconciliation_keur=(34.0,),
            cash_tax_current_period_audit_keur=(6.0,),
            tax_loss_opening_audit_keur=(0.0,), tax_loss_closing_audit_keur=(0.0,),
            tax_loss_used_audit_keur=(0.0,), fiscal_reintegration_audit_keur=(0.0,),
            tax_depreciation_audit_keur=(5.0,),
            cf_after_tax_keur=(34.0,), cfads_keur=(34.0,),
            terminal_unpaid_tax_keur=0.0,
        )
        sd = SeniorDebtSchedules(
            period_indices=(0,),
            senior_debt_opening_keur=(10000.0,), senior_interest_keur=(250.0,),
            senior_principal_keur=(300.0,), senior_debt_service_keur=(550.0,),
            senior_debt_closing_keur=(9700.0,),
            base_dscr=(34.0 / 550.0,),
            debt_size_keur=10000.0, binding_constraint="DSCR", diagnostics={},
        )
        result = ProjectModelResult(
            provenance=provenance, periods=(period,), operating_schedules=op_sched,
            unavailable_sections=(), validation_issues=(), warnings=(),
            tax_and_cfads=tac, senior_debt=sd, debt_sizing=None,
            post_senior_cash=None,  # explicit legacy path
        )
        seam = compute_shl_cash_from_phase2c(result)
        assert len(seam) == 1
        assert abs(seam[0].cfads_keur - 34.0) < 1e-6
        assert abs(seam[0].senior_debt_service_keur - 550.0) < 1e-6
        # max(0, 34 - 550) = 0
        assert seam[0].cash_available_for_shl_keur == 0.0


# ---------------------------------------------------------------------------
# Verdict functions
# ---------------------------------------------------------------------------

def test_c3b3d2b4_verdict():
    """C3B3D2B4 production verdict: DSCR split and PostSeniorCashSchedules proven."""
    from financial_engine.results import (
        PostSeniorCashSchedules, DebtSizingSchedules, SeniorDebtSchedules,
        ProjectModelResult,
    )
    psc_fields = {f.name for f in dataclasses.fields(PostSeniorCashSchedules)}
    assert "base_cfads_keur" in psc_fields
    assert "cash_after_senior_before_reserves_keur" in psc_fields
    assert "cash_available_for_shl_before_reserves_keur" in psc_fields
    ds_fields = {f.name for f in dataclasses.fields(DebtSizingSchedules)}
    assert "bank_sizing_dscr" in ds_fields
    sd_fields = {f.name for f in dataclasses.fields(SeniorDebtSchedules)}
    assert "base_dscr" in sd_fields
    assert "senior_dscr" not in sd_fields  # property, not field
    assert isinstance(SeniorDebtSchedules.__dict__.get("senior_dscr"), property)
    result_fields = {f.name for f in dataclasses.fields(ProjectModelResult)}
    assert "post_senior_cash" in result_fields
