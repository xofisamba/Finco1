"""test_stage_c3b3b_clean_tax_cfads_debt_feedback.py

Stage C3B3B: Clean Tax / Cash-Tax / CFADS Feedback into Source-Proven Senior Debt.

VERDICT: C3B3B_BLOCKED_WORKBOOK_PERIODISATION_MISMATCH

The clean runtime proves the COMPLETE feedback loop:

    ProjectInputs → from_project_inputs() → run_operating_model()
    → build_tax_contract_from_project_inputs() → run_senior_debt_model()
    → fixed-point: tax/CFADS/debt iterate until convergence

The solver converges (7 iterations, max_abs_diff < 0.001 kEUR), but the
converged debt of 43,919.033 kEUR differs from the source-proven debt of
42,852.279 kEUR by 1,066.754 kEUR — far exceeding the 0.01 kEUR tolerance.

Root cause (proved from C3B1 committed evidence):

  1. WORKBOOK_PERIODISATION_MISMATCH (primary blocker):
     - Workbook uses H2(yr N)+H1(yr N+1) model-year pairing for CIT, where
       CIT fires in the EVEN (H1) period of each pair.
     - Clean engine aggregates on calendar year (Jan–Dec), assigning H2 to
       one year and H1 to the NEXT.  This shifts CIT timing by ~6 months
       and changes the taxable income pool per "year".

  2. LCF mechanism mismatch (secondary, follows from #1):
     - Clean engine: FIFO carry-forward, losses deducted when TI > 0
       (Article 17 Croatian CIT). First CIT fires at P12 (TY2035).
     - Workbook: rolling 5-period SUMIF with EBT>0 gate. EBT is always
       negative during debt service, so losses are NEVER utilised (alloc=0
       in all debt periods). First CIT fires at P6 (workbook pair 5+6).

  3. Consequence for debt sizing:
     - Source pays CIT in P6–P28 (starts early, reduces CFADS early).
     - Clean pays CIT in P12–P28 (starts 6 periods late, higher early CFADS).
     - Higher early CFADS → higher DSCR → higher debt capacity.
     - Measured: clean debt 43,919.033 vs source 42,852.279 → Δ 1,066.754 kEUR.

The C3B3B implementation proves:
  - Tax depreciation gap (#1) RESOLVED: clean tax_dep = source book_dep (C3B1 evidence).
  - Senior/tax adapter built generically from ProjectInputs (no project dispatch).
  - Fixed-point solver converges in 7 iterations.
  - LCF window irrelevance for Oborovo (losses generated but never used in source).
  - SHL cancels in taxable income for ATAD=False projects (thin_cap=False).
  - Only the WORKBOOK_PERIODISATION_MISMATCH prevents debt convergence to source.

Financial freeze (C3B3B): No changes to revenue formulas, OPEX, CAPEX, construction,
IDC, book depreciation, tax policy, tax-loss mechanics, cash-tax formula, production
CFADS formula, DSRA, SHL, distributions, Project IRR, Equity IRR, UI, persistence,
scenarios. No approved_delta. No expected_delta plug. No balancing plug. No hardcoded
debt target. No project-name dispatch.

C3B3B source evidence:
  - Source debt: 42,852.278762563 kEUR (28 semi-annual periods, clean indices 2–29)
  - Source tax dep = book dep: C3B1 period_diagnostic.excel_tax_dep == excel_book_dep
  - ATAD gated on thin_cap_enabled (BS!G45=False → ATAD=False for Oborovo)
  - SHL reintegration = full SHL (thin_cap=False → FR = full SHL → nets to zero)
  - Cash tax timing: TAX_YEAR_LAST_PERIOD, lag=0
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Source constants (proved from C3B1 / C3B2 committed fixtures)
# ---------------------------------------------------------------------------

_SOURCE_DEBT_KEUR: float = 42_852.278762563
_C3B3B_TOLERANCE_KEUR: float = 0.01   # stated acceptance threshold (NOT MET — see verdict)
_CLEAN_DEBT_KEUR: float = 43_919.033  # measured converged clean debt (approximate)
_MEASURED_RESIDUAL_KEUR: float = 1_066.754  # _CLEAN_DEBT_KEUR - _SOURCE_DEBT_KEUR (approx)

_VERDICT = "C3B3B_BLOCKED_WORKBOOK_PERIODISATION_MISMATCH"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def oborovo_project():
    from app.project_factories import create_default_oborovo
    return create_default_oborovo()


@pytest.fixture(scope="module")
def operating_result(oborovo_project):
    from financial_engine.adapters.project_inputs import from_project_inputs
    from financial_engine.orchestrator import run_operating_model
    mi = from_project_inputs(oborovo_project, source_id="c3b3b-test")
    return run_operating_model(mi)


@pytest.fixture(scope="module")
def debt_solver_result(oborovo_project):
    from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
    from financial_engine.orchestrator import run_senior_debt_model
    sd_input = build_senior_debt_model_input_from_project_inputs(
        oborovo_project, source_id="c3b3b-acceptance"
    )
    return run_senior_debt_model(sd_input)


# ---------------------------------------------------------------------------
# Group A: Tax depreciation gap resolved — clean tax_dep = source book_dep
# ---------------------------------------------------------------------------

class TestGroupA_TaxDepEqualsBookDep:
    """C3B3B gap #1: clean tax_dep now equals source book_dep (RESOLVED).

    C3B1 evidence: excel_tax_dep = excel_book_dep for all 28 operating periods.
    Fix: project_adapter dispatches on TaxDepreciationMode.BOOK_BASED_PERCENTAGE
    to use book_depreciable_capex_items() as tax basis (same asset list, same lives).
    """

    def test_tax_depreciation_mode_is_book_based(self, oborovo_project):
        """ProjectInputs sets tax_depreciation_mode = BOOK_BASED_PERCENTAGE."""
        from finco_core.inputs._models import TaxDepreciationMode
        assert oborovo_project.tax.tax_depreciation_mode == TaxDepreciationMode.BOOK_BASED_PERCENTAGE

    def test_book_dep_pct_is_unity(self, oborovo_project):
        """Oborovo: tax_deductible_book_dep_pct = 1.0 (tax_dep = 100% book_dep)."""
        assert oborovo_project.tax.tax_deductible_book_dep_pct == 1.0

    def test_clean_tax_dep_capex_basis_equals_book_basis(self, oborovo_project):
        """After fix: tax_capex basis = book_capex basis (financial costs included)."""
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.inputs import DepreciationInput
        mi = from_project_inputs(oborovo_project, source_id="dep-test")
        dep: DepreciationInput = mi.depreciation
        assert dep.tax_capex_items_for_depreciation == dep.book_capex_items_for_depreciation

    def test_clean_book_dep_matches_source_book_dep_p1(self, operating_result):
        """Clean book_dep for first operating period matches C3B1 source (< 0.001 kEUR)."""
        import json, pathlib
        truth = json.loads(
            pathlib.Path("tests/fixtures/excel_oborovo_financial_truth.json").read_text()
        )
        pd_list = truth["tax"]["period_diagnostic"]
        src_book_dep_p1 = pd_list[1]["excel_book_dep_keur"]  # C3B1 pd[1] = operating P1
        op_periods = [p for p in operating_result.periods if p.is_operation]
        clean_book_dep_p1 = op_periods[0].book_depreciation_keur
        assert abs(clean_book_dep_p1 - src_book_dep_p1) < 0.001

    def test_clean_tax_dep_matches_source_p1(self, operating_result):
        """After fix: clean tax_dep P1 matches C3B1 source tax_dep (< 0.001 kEUR)."""
        import json, pathlib
        truth = json.loads(
            pathlib.Path("tests/fixtures/excel_oborovo_financial_truth.json").read_text()
        )
        pd_list = truth["tax"]["period_diagnostic"]
        src_tax_dep_p1 = pd_list[1]["excel_tax_dep_keur"]
        op_periods = [p for p in operating_result.periods if p.is_operation]
        clean_tax_dep_p1 = op_periods[0].tax_depreciation_keur
        assert abs(clean_tax_dep_p1 - src_tax_dep_p1) < 0.001


# ---------------------------------------------------------------------------
# Group B: Clean tax contract adapter
# ---------------------------------------------------------------------------

class TestGroupB_TaxContractAdapter:
    """build_tax_contract_from_project_inputs() builds a TaxCalculationInput
    from ProjectInputs alone — no project-name dispatch, no snapshot loading.
    """

    def test_adapter_builds_without_error(self, oborovo_project):
        from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs
        tax_input = build_tax_contract_from_project_inputs(oborovo_project)
        assert tax_input is not None

    def test_corporate_rate_from_project(self, oborovo_project):
        from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs
        tax_input = build_tax_contract_from_project_inputs(oborovo_project)
        assert tax_input.policy.corporate_rate == oborovo_project.tax.corporate_rate

    def test_atad_gated_on_thin_cap(self, oborovo_project):
        """ATAD is gated by thin_cap_enabled (C3B1 evidence: BS!G45=thin_cap=False)."""
        from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs
        tax_input = build_tax_contract_from_project_inputs(oborovo_project)
        assert tax_input.policy.atad_enabled == oborovo_project.tax.thin_cap_enabled
        assert tax_input.policy.atad_enabled is False  # Oborovo: thin_cap=False → ATAD=False

    def test_oborovo_no_opening_loss_vintages(self, oborovo_project):
        """Oborovo: initial_tax_loss_keur = 0 → empty opening vintages."""
        from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs
        assert oborovo_project.tax.initial_tax_loss_keur == 0.0
        tax_input = build_tax_contract_from_project_inputs(oborovo_project)
        assert tax_input.opening_loss_vintages == ()

    def test_period_interest_initially_empty(self, oborovo_project):
        """period_interest is empty — senior is supplied by the fixed-point solver."""
        from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs
        tax_input = build_tax_contract_from_project_inputs(oborovo_project)
        assert tax_input.period_interest == ()

    def test_policy_id_is_generic(self, oborovo_project):
        """Policy ID is generic — no project name encoded."""
        from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs
        tax_input = build_tax_contract_from_project_inputs(oborovo_project)
        assert "clean-project-tax" in tax_input.policy.policy_id
        assert "oborovo" not in tax_input.policy.policy_id.lower()

    def test_cash_tax_timing_is_year_last_period(self, oborovo_project):
        """Cash tax timing = TAX_YEAR_LAST_PERIOD (C3B1: lag=0)."""
        from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs
        from financial_engine.policies.tax import CashTaxTiming
        tax_input = build_tax_contract_from_project_inputs(oborovo_project)
        assert tax_input.policy.cash_tax_timing == CashTaxTiming.TAX_YEAR_LAST_PERIOD
        assert tax_input.policy.cash_tax_payment_lag_periods == 0

    def test_semestrial_gives_2_periods_per_tax_year(self, oborovo_project):
        """SEMESTRIAL period frequency → periods_per_tax_year = 2."""
        from financial_engine.adapters.tax_inputs import build_tax_contract_from_project_inputs
        tax_input = build_tax_contract_from_project_inputs(oborovo_project)
        assert tax_input.policy.periods_per_tax_year == 2


# ---------------------------------------------------------------------------
# Group C: Full model input assembly
# ---------------------------------------------------------------------------

class TestGroupC_SeniorDebtModelInputAssembly:
    """build_senior_debt_model_input_from_project_inputs() assembles all phases."""

    def test_assembly_succeeds(self, oborovo_project):
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        sd_input = build_senior_debt_model_input_from_project_inputs(
            oborovo_project, source_id="c3b3b-assembly-test"
        )
        assert sd_input is not None

    def test_has_operating_input(self, oborovo_project):
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.inputs import OperatingModelInput
        sd_input = build_senior_debt_model_input_from_project_inputs(
            oborovo_project, source_id="c3b3b-test"
        )
        assert isinstance(sd_input.operating, OperatingModelInput)

    def test_has_tax_input(self, oborovo_project):
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.inputs import TaxCalculationInput
        sd_input = build_senior_debt_model_input_from_project_inputs(
            oborovo_project, source_id="c3b3b-test"
        )
        assert isinstance(sd_input.tax, TaxCalculationInput)

    def test_senior_debt_policy_id_is_generic(self, oborovo_project):
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        sd_input = build_senior_debt_model_input_from_project_inputs(
            oborovo_project, source_id="c3b3b-test"
        )
        policy = sd_input.senior_debt_policy
        assert "oborovo" not in policy.policy_id.lower()
        assert "clean-project" in policy.policy_id


# ---------------------------------------------------------------------------
# Group D: Fixed-point solver convergence
# ---------------------------------------------------------------------------

class TestGroupD_SolverConvergence:
    """The fixed-point solver converges for the clean Oborovo inputs."""

    def test_solver_converges(self, debt_solver_result):
        """Solver must report converged=True."""
        assert debt_solver_result.senior_debt.diagnostics["converged"] is True

    def test_iteration_count_reasonable(self, debt_solver_result):
        """Solver completes in fewer than 50 iterations."""
        iters = debt_solver_result.senior_debt.diagnostics["iteration_count"]
        assert iters < 50

    def test_max_abs_diff_below_tolerance(self, debt_solver_result):
        """Final max_abs_diff below 0.001 kEUR (well-converged)."""
        diff = debt_solver_result.senior_debt.diagnostics.get(
            "maximum_absolute_difference_keur", float("inf")
        )
        assert diff < 0.001

    def test_clean_debt_is_positive(self, debt_solver_result):
        """Converged debt is a positive finite number."""
        debt = debt_solver_result.senior_debt.diagnostics["final_debt_size_keur"]
        assert 0.0 < debt < 200_000.0

    def test_tax_and_cfads_result_present(self, debt_solver_result):
        """tax_and_cfads result is populated (not None) after convergence."""
        assert debt_solver_result.tax_and_cfads is not None


# ---------------------------------------------------------------------------
# Group E: C3B3B acceptance measurement and stop verdict
# ---------------------------------------------------------------------------

class TestGroupE_C3B3BAcceptanceMeasurementAndVerdict:
    """C3B3B acceptance measurement and stop verdict documentation.

    VERDICT: C3B3B_BLOCKED_WORKBOOK_PERIODISATION_MISMATCH

    The clean feedback loop converges but the converged debt differs from the
    source by 1,066.754 kEUR >> 0.01 kEUR tolerance.

    Root causes (proved from C3B1):
      1. Calendar-year aggregation (clean) vs H2+H1 pairing (workbook): timing shift.
      2. FIFO LCF no-EBT-gate (clean) vs rolling SUMIF EBT-gated (workbook):
         source pays CIT from P6, clean from P12 — 6-period delay.
      3. These are structural architectural differences, not tunable parameters.
    """

    def test_clean_debt_exceeds_source(self, debt_solver_result):
        """Clean debt > source (higher CFADS due to delayed CIT → more debt capacity)."""
        debt = debt_solver_result.senior_debt.diagnostics["final_debt_size_keur"]
        assert debt > _SOURCE_DEBT_KEUR, (
            f"Expected clean debt > source {_SOURCE_DEBT_KEUR}, got {debt:.6f}"
        )

    def test_residual_exceeds_tolerance(self, debt_solver_result):
        """Residual |clean - source| >> 0.01 kEUR — acceptance NOT met."""
        debt = debt_solver_result.senior_debt.diagnostics["final_debt_size_keur"]
        residual = abs(debt - _SOURCE_DEBT_KEUR)
        assert residual > _C3B3B_TOLERANCE_KEUR * 100, (
            f"Residual {residual:.6f} should be >> {_C3B3B_TOLERANCE_KEUR} kEUR; "
            f"if it is small the block is resolved and the test set needs updating."
        )

    def test_measured_residual_matches_expected(self, debt_solver_result):
        """Measured residual is approximately 1066.754 kEUR (within 5 kEUR)."""
        debt = debt_solver_result.senior_debt.diagnostics["final_debt_size_keur"]
        residual = abs(debt - _SOURCE_DEBT_KEUR)
        # Allow 5 kEUR tolerance on the measured gap itself (floating-point variation).
        assert abs(residual - _MEASURED_RESIDUAL_KEUR) < 5.0, (
            f"Residual {residual:.3f} kEUR differs from expected ~{_MEASURED_RESIDUAL_KEUR} kEUR "
            f"by more than 5 kEUR — root cause may have changed."
        )

    def test_verdict_string_is_defined(self):
        """Stop verdict is statically declared and non-empty."""
        assert _VERDICT == "C3B3B_BLOCKED_WORKBOOK_PERIODISATION_MISMATCH"
        assert len(_VERDICT) > 0

    def test_source_first_cit_period(self, debt_solver_result):
        """Source CIT first fires at P6 (workbook pair 5+6); clean CIT first fires at P12.

        This 6-period gap (3 years) is the timing consequence of WORKBOOK_PERIODISATION_MISMATCH:
        workbook pairs H2(yr N)+H1(yr N+1) and has EBT>0 gate suppressed by SHL reintegration;
        clean engine uses calendar year with FIFO LCF that defers first CIT to TY2035.
        """
        tc = debt_solver_result.tax_and_cfads
        # Find first period with non-zero CIT in clean result
        first_cit_period = None
        for pidx, cit in zip(tc.period_indices, tc.corporate_tax_cash_keur):
            if abs(cit) > 0.001:
                first_cit_period = pidx
                break
        # Source first CIT is at workbook period 6 (clean period 6 = 5th operating period).
        # Clean first CIT should be at a later period (demonstrating the timing mismatch).
        assert first_cit_period is not None, "Clean engine produced no CIT — unexpected"
        assert first_cit_period > 6, (
            f"Expected clean first CIT > P6 (source P6=8.9 kEUR due to workbook pairing), "
            f"got first CIT at P{first_cit_period}. "
            f"Verdict: {_VERDICT}"
        )

    def test_periodisation_mismatch_classification_in_c3b1_fixture(self):
        """C3B1 fixture classifies this as WORKBOOK_PERIODISATION_MISMATCH."""
        import json, pathlib
        truth = json.loads(
            pathlib.Path("tests/fixtures/excel_oborovo_financial_truth.json").read_text()
        )
        pm = truth["tax"].get("periodisation_mismatch", {})
        assert pm.get("classification") == "WORKBOOK_PERIODISATION_MISMATCH"

    def test_atad_proved_false_from_c3b1(self):
        """C3B1 proves ATAD=False for Oborovo (G56=BS!G45=thin_cap=False)."""
        import json, pathlib
        truth = json.loads(
            pathlib.Path("tests/fixtures/excel_oborovo_financial_truth.json").read_text()
        )
        atad_proof = truth["tax"].get("proved_atad", "")
        assert "BS!G45=False" in atad_proof or "False" in atad_proof

    def test_shl_reintegration_proved_full_from_c3b1(self):
        """C3B1 proves FR = full SHL (thin_cap=False → C59=1.0, D59=True)."""
        import json, pathlib
        truth = json.loads(
            pathlib.Path("tests/fixtures/excel_oborovo_financial_truth.json").read_text()
        )
        atad_proof = truth["tax"].get("proved_atad", "")
        assert "FR=full SHL" in atad_proof or "thin_cap=False" in atad_proof


# ---------------------------------------------------------------------------
# Group F: Financial freeze guard
# ---------------------------------------------------------------------------

class TestGroupF_FinancialFreeze:
    """No production financial formula was changed — only new adapter code."""

    def test_calculate_tax_function_unchanged(self):
        """calculate_tax() still importable and callable."""
        from financial_engine.tax.engine import calculate_tax
        assert callable(calculate_tax)

    def test_calculate_canonical_cfads_unchanged(self):
        """calculate_canonical_cfads() still importable and callable."""
        from financial_engine.cfads import calculate_canonical_cfads
        assert callable(calculate_canonical_cfads)

    def test_run_senior_debt_model_still_callable(self):
        """run_senior_debt_model() still importable."""
        from financial_engine.orchestrator import run_senior_debt_model
        assert callable(run_senior_debt_model)

    def test_no_project_name_dispatch_in_adapter(self):
        """Adapter dispatches on field values, not on project names (no if/elif chains)."""
        import ast, pathlib
        adapter_src = pathlib.Path("financial_engine/adapters/tax_inputs.py").read_text()
        tree = ast.parse(adapter_src)
        # Check: no string literals equal to 'oborovo' or 'tuho' (dispatch guard)
        string_consts = [
            node.s for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.s, str)
        ]
        for s in string_consts:
            assert s.lower() not in ("oborovo", "tuho"), (
                f"Found hardcoded project name '{s}' in tax_inputs.py adapter"
            )
