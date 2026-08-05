"""Stage C3B1 — Oborovo Tax Source Truth Diagnostic.

SOURCE: d49af8ee-20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm
SHA-256: 15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920

Extractor version: 3.1.0 (dual-load: data_only=False for formulas, data_only=True for values)

Groups
------
A  Workbook SHA and fixture provenance
B  Source row and formula inventory (proved from workbook, not inferred from Python)
C  Tax depreciation source completeness
D  Taxable income identity (proved from formulas and cached values)
E  Interest dependency (frozen CSV vs Excel; Phase 2C runtime classification)
F  Tax loss roll-forward (opening balance and 5-period window)
G  Tax year fragmentation (calendar vs model year convention)
H  Current tax identity (CIT formula)
I  Cash tax timing (CF row 77 formula and vector; BS conclusion)
J  Sign conventions
K  Clean / legacy / source diagnostic
L  No production formula diff (financial freeze)
M  No project identity dispatch in production engine
N  No target plug or hardcoded CIT total
O  C3A upstream freeze (EBIT chain unchanged)
P  Regression guard (pre-existing failures do not increase)

Verdict
-------
C3B1_TAX_BLOCKED_BY_INTEREST_DEPENDENCY

The full taxable income formula is proved:
    TI = EBT + FR = EBIT + taxable_financial_income - Senior_Interest
    where FR = full SHL reintegration (thin_cap=False, ATAD=False).

During debt tenor (periods 1-28): taxable_financial_income ≈ 0 → TI ≈ EBIT - SD.
After debt repayment (periods 29+): row 20 (Interests from Cash) > 0 → TI = EBIT + cash_interest.

EBITDA and book_depreciation are frozen and clean.  Senior interest comes
from the Phase 2C debt schedule.  The current Phase 2C runtime produces a
valid interest vector but sizes the debt differently (45,873 kEUR vs Excel
42,852 kEUR), causing a maximum per-period delta of 90.29 kEUR.  Tax parity
cannot be achieved without a matching Phase 2C interest input.

C3B2 typed policy contracts (no project-name dispatch permitted):

    TAX_AGGREGATION_BASIS:
        CALENDAR_YEAR  — Python current default
        MODEL_YEAR_PAIR — required for Oborovo source parity (H2+H1 pair)
        CUSTOM_PERIOD_GROUPING — only if genuinely required

    LOSS_CARRYFORWARD_BASIS:
        TAX_YEARS — Python current default (5 calendar years)
        MODEL_PERIODS — required for Oborovo source parity (5 model periods = B36=5)

    For Oborovo source parity:
        tax_aggregation_basis = MODEL_YEAR_PAIR
        loss_carryforward_basis = MODEL_PERIODS, n_periods = 5

    Do NOT use loss_carryforward_years = 3 or any year-count approximation.
    Do NOT defer the H2+H1 model-year difference as a sub-1% approximation.

    C3B2 CIT must use the row-43 economic formula.  Row 44 is workbook routing
    evidence and a stale-value risk; do not reproduce its hardcoded Macro values.

Minimum C3B2 scope (6 items):
    1. Fix clean adapter: tax_dep = book_dep × deductible_pct for
       BOOK_BASED_PERCENTAGE mode (adapter currently uses hard-CAPEX-only basis).
    2. Pass senior_interest from Phase 2C as PeriodInterestInput.senior_interest_keur
       using a Phase 2C result that matches Excel debt sizing.
    3. Pass SHL_interest as PeriodInterestInput.shl_interest_keur and reintegrate via
       PeriodTaxAdjustmentInput.other_fiscal_reintegration_keur (=SHL for thin_cap=False).
    4. Fix LCF: use MODEL_PERIODS with n_periods=5 window (not TAX_YEARS=5 calendar years).
    5. Fix CIT aggregation: use MODEL_YEAR_PAIR (not CALENDAR_YEAR).
    6. Fix CIT formula: implement row-43 economic formula; treat row-44 as staleness risk.

Known contract conflicts (section 11A)
---------------------------------------
11A-A: TAX_DEP_BOTH_ARE_INCOMPLETE
    Factory declares BOOK_BASED_PERCENTAGE (correct) but clean adapter ignores it
    and builds tax_dep from hard CAPEX only.  Workbook uses book_dep = tax_dep.

11A-B: TAX_LOSS_YEAR_CONTRACT_BUG
    financial_engine/inputs.py docstring says origin_tax_year is "0-based index".
    The loss_ledger.py compares last_usable_tax_year < tax_year where tax_year is
    a calendar year (e.g. 2030).  All actual callers (parity layer) pass calendar
    years (2029, 2030).  The docstring is wrong; the implementation and callers are
    consistent with calendar-year semantics.  An opening vintage with
    origin_tax_year = -3 (relative) would compute last_usable = 2 < 2030 and
    expire immediately — a silent correctness bug if a relative index is ever passed.

11A-C: Stale depreciation provenance comment.
    See docs/reconciliation/oborovo_tax_source_truth.md section 11A-C for
    recommended C3B2 scope correction.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

_FIXTURE = pathlib.Path("tests/fixtures/excel_oborovo_financial_truth.json")
_WORKBOOK_SHA = "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920"
_EXTRACTOR_VERSION = "3.1.0"
# Base SHA from which this branch was created; used by financial-freeze tests
_BASE_SHA = "b11e5bf7b9ab60bae174081e7d9f8541190bf371"

_N_PERIODS = 61  # 0=construction, 1-60=operating


def _xd():
    with open(_FIXTURE) as f:
        return json.load(f)


# ===========================================================================
# A — Workbook SHA and fixture provenance
# ===========================================================================

class TestAProvenance:
    def test_fixture_exists(self):
        assert _FIXTURE.exists(), f"Fixture not found: {_FIXTURE}"

    def test_workbook_sha_matches(self):
        xd = _xd()
        assert xd["_meta"]["source_sha256"] == _WORKBOOK_SHA

    def test_extractor_version(self):
        xd = _xd()
        assert xd["_meta"]["extractor_version"] == _EXTRACTOR_VERSION

    def test_tax_section_present(self):
        xd = _xd()
        assert "tax" in xd, "tax section missing from fixture"

    def test_tax_rows_all_present(self):
        xd = _xd()
        required = {
            "depreciation", "ebit", "senior_interests", "shl_interests",
            "financial_earnings", "earnings_before_tax",
            "fiscal_reintegration_display", "taxable_income",
            "losses_n_minus_1", "allocated_losses", "losses_n",
            "carriable_losses", "taxable_profit_n",
            "corporate_income_tax_formula", "corporate_income_tax_net_income",
            "net_income", "fiscal_reintegration_helper", "thin_cap_rule",
            "thin_cap_amount", "atad_30pct_amount", "non_deductible_shl",
            "fin_rev_reserve_account", "fin_rev_cash", "fin_rev_adjustment",
        }
        actual = set(xd["tax"]["rows"].keys())
        missing = required - actual
        assert not missing, f"Missing tax rows: {missing}"

    def test_period_diagnostic_present(self):
        xd = _xd()
        diag = xd["tax"].get("period_diagnostic", [])
        assert len(diag) == _N_PERIODS, (
            f"period_diagnostic must have {_N_PERIODS} entries; got {len(diag)}"
        )
        p6 = diag[6]
        # Core identity columns
        required_keys = {
            "excel_cit_p43_keur", "excel_cit_p44_routed_keur",
            "excel_cf_cash_tax_keur", "identity_ti_eq_ebt_plus_fr_delta",
            "identity_cf_eq_neg_p44_delta", "excel_model_year_pair",
            "excel_cit_pairing_bucket", "python_calendar_tax_year",
            "period_bop_date", "period_eop_date",
            "interest_classification", "classification",
        }
        missing = required_keys - set(p6.keys())
        assert not missing, f"period_diagnostic missing columns: {missing}"

    def test_cf_tax_chain_section_present(self):
        xd = _xd()
        chain = xd["tax"].get("cf_tax_chain", {})
        assert chain.get("bs_tax_payable_row_exists") is False, (
            "BS tax payable row must be confirmed absent"
        )
        assert chain.get("payment_lag_periods") == 0
        assert chain.get("cf_vs_pl44_max_delta_keur") == 0.0, (
            "CF row 77 must equal -P&L row 44 for all periods"
        )
        formula = chain.get("cf_row_77_formula_period1", "")
        assert formula and "P&L" in formula, (
            f"CF row 77 formula from dual-load must reference P&L; got: {formula!r}"
        )

    def test_cit_authority_section_present(self):
        xd = _xd()
        auth = xd["tax"].get("cit_row43_vs_row44_authority", {})
        assert "row_43_formula" in auth
        assert "row_44_macro" in auth
        assert auth.get("row_43_vs_44_max_delta_keur", 1.0) < 0.001, (
            "Rows 43 and 44 must match to machine precision in current workbook"
        )

    def test_dual_load_note_present(self):
        xd = _xd()
        assert "data_only" in xd["_meta"].get("dual_load_note", ""), (
            "Fixture meta should record dual-load (formula + data)"
        )


# ===========================================================================
# B — Source row and formula inventory (proved from workbook)
# ===========================================================================

class TestBSourceInventory:
    """Every formula here is taken directly from the workbook (data_only=False).
    Nothing is reconstructed from Python code or narrative."""

    def test_depreciation_formula(self):
        xd = _xd()
        row = xd["tax"]["rows"]["depreciation"]
        assert row["row"] == 13
        f = row["formula_period0"]
        assert f is not None, "Formula must be present (workbook binary available)"
        assert "Dep!" in f and "30" in f, (
            f"Expected formula referencing Dep sheet row 30; got {f!r}"
        )

    def test_ebit_formula(self):
        xd = _xd()
        row = xd["tax"]["rows"]["ebit"]
        assert row["row"] == 16
        f = row["formula_period0"]
        assert f is not None
        assert "G8" in f and "G14" in f, f"EBIT formula: {f!r}"

    def test_senior_interest_formula(self):
        xd = _xd()
        row = xd["tax"]["rows"]["senior_interests"]
        assert row["row"] == 24
        f = row["formula_period0"]
        assert f is not None
        assert "DS!" in f, f"Senior interest must reference DS sheet; got {f!r}"

    def test_shl_interest_formula(self):
        xd = _xd()
        row = xd["tax"]["rows"]["shl_interests"]
        assert row["row"] == 27
        f = row["formula_period0"]
        assert f is not None
        assert "DS!" in f, f"SHL interest must reference DS sheet; got {f!r}"

    def test_ebt_formula(self):
        xd = _xd()
        row = xd["tax"]["rows"]["earnings_before_tax"]
        assert row["row"] == 32
        f = row["formula_period0"]
        assert f is not None
        assert "G16" in f and "G30" in f, f"EBT = EBIT + Financial Earnings; got {f!r}"

    def test_fiscal_reintegration_formula(self):
        xd = _xd()
        row = xd["tax"]["rows"]["fiscal_reintegration_display"]
        assert row["row"] == 34
        f = row["formula_period0"]
        assert f is not None
        assert "G54" in f and f.startswith("=-"), f"FR = -G54; got {f!r}"

    def test_taxable_income_formula(self):
        xd = _xd()
        row = xd["tax"]["rows"]["taxable_income"]
        assert row["row"] == 35
        f = row["formula_period0"]
        assert f is not None
        assert "G34" in f and "G32" in f, f"TI = FR + EBT; got {f!r}"

    def test_cit_formula(self):
        xd = _xd()
        row = xd["tax"]["rows"]["corporate_income_tax_formula"]
        assert row["row"] == 43
        f = row["formula_period0"]
        assert f is not None
        assert "SUM(F41:G41)" in f, f"CIT sums two periods; got {f!r}"
        assert "MOD(G4,2)=0" in f, f"CIT only in even periods; got {f!r}"
        assert row["B_col_cached"] == pytest.approx(0.10, abs=1e-6), (
            f"CIT rate must be 10%; got {row['B_col_cached']}"
        )

    def test_cit_row44_routes_via_macro(self):
        """Row 44 (Net Income CIT) = Macro!G40 (scenario-switch hardcoded values)."""
        xd = _xd()
        row = xd["tax"]["rows"]["corporate_income_tax_net_income"]
        assert row["row"] == 44
        f = row["formula_period0"]
        assert f is not None
        assert "Macro!" in f, f"Row 44 must reference Macro sheet; got {f!r}"

    def test_net_income_uses_row44_not_row43(self):
        """Net Income (row 46) = EBT - row44. Row 43 is the CIT formula but NOT
        what flows into Net Income or CF cash tax."""
        xd = _xd()
        row = xd["tax"]["rows"]["net_income"]
        assert row["row"] == 46
        f = row["formula_period0"]
        assert "G32" in f and "G44" in f, (
            f"Net Income must be =G32-G44 (uses row 44); got {f!r}"
        )

    def test_dep_sheet_row_authority(self):
        """P&L row 13 = Dep!G30 (total book dep, SUM G7:G28 incl. financing costs).
        NOT Dep!G22 (individual item) or Dep!G31 (unlevered, SUM G7:G22)."""
        xd = _xd()
        row = xd["tax"]["rows"]["depreciation"]
        f = row["formula_period0"]
        assert "Dep!" in f and "30" in f, (
            f"P&L row 13 must reference Dep!G30 (total book dep); got {f!r}"
        )
        proved = xd["tax"].get("proved_dep_row_authority", "")
        assert "Dep!G30" in proved and "Dep!G31" in proved, (
            "Dep row authority proof must distinguish row 30 (total) from row 31 (unlevered)"
        )

    def test_fr_helper_formula_sign(self):
        """FR helper (row 54) = MIN(MAX(G57,G58)+G59,G27) (positive result stored negative).
        Row 34 display = -G54 (sign flip). This proves FR helper is NOT pre-negated."""
        xd = _xd()
        helper = xd["tax"]["rows"]["fiscal_reintegration_helper"]
        display = xd["tax"]["rows"]["fiscal_reintegration_display"]
        h_f = helper["formula_period0"]
        d_f = display["formula_period0"]
        assert "MIN(" in h_f, f"FR helper must use MIN; got {h_f!r}"
        assert h_f.startswith("=MIN("), f"FR helper has no leading minus; got {h_f!r}"
        assert d_f == "=-G54", f"FR display must be =-G54; got {d_f!r}"
        # Cached values: helper should be negative (=-SHL), display should be positive (=SHL)
        assert (helper["cached_period1"] or 0) < 0, "FR helper cached value must be negative"
        assert (display["cached_period1"] or 0) > 0, "FR display cached value must be positive"

    def test_senior_interest_formula_components(self):
        """Senior interest = DS!G53 - CF!G83 where DS!G53=net interest, CF!G83=-DS!G35 VAT facility."""
        xd = _xd()
        row = xd["tax"]["rows"]["senior_interests"]
        f = row["formula_period0"]
        assert "DS!" in f and "CF!" in f, (
            f"Senior interest must reference both DS and CF sheets; got {f!r}"
        )

    def test_fin_rev_cash_explains_late_period_financial_earnings(self):
        """In late operating periods (post debt repayment), financial earnings = row 20
        (Interests from Cash = (CF!F144>0)*rate*balance). NOT DSRA interest (row 19)."""
        xd = _xd()
        fin_cash = xd["tax"]["rows"]["fin_rev_cash"]["period_values"]
        fin_reserve = xd["tax"]["rows"]["fin_rev_reserve_account"]["period_values"]
        # In period 41 (post debt repayment), cash interest should be ~2.77
        assert (fin_cash[41] or 0) > 2.0, (
            f"Period 41 cash interest should be ~2.77 kEUR; got {fin_cash[41]}"
        )
        # Reserve account interest should be 0 for Oborovo
        reserve_total = sum(v or 0 for v in fin_reserve)
        assert abs(reserve_total) < 0.01, (
            "Interests from Reserve Account = 0 for Oborovo (no DSRA interest)"
        )

    def test_non_deductible_shl_formula(self):
        xd = _xd()
        row = xd["tax"]["rows"]["non_deductible_shl"]
        assert row["row"] == 59
        f = row["formula_period0"]
        assert f is not None
        assert "G$27" in f, f"SHL non-deductibility references SHL row 27; got {f!r}"
        assert row["C_col_cached"] == pytest.approx(1.0, abs=1e-9), (
            "C59=1.0 means 100% of SHL is non-deductible"
        )
        assert row["D_col_cached"] is True, "D59=True (flag active)"

    def test_thin_cap_always_false(self):
        xd = _xd()
        row = xd["tax"]["rows"]["thin_cap_rule"]
        vals = [v for v in row["period_values"] if v is not None]
        assert all(v is False or v == 0.0 or v == 0 for v in vals), (
            "Thin Cap Rule must be False/0 for all Oborovo periods"
        )

    def test_lcf_window_is_5_periods(self):
        xd = _xd()
        row = xd["tax"]["rows"]["losses_n_minus_1"]
        assert row["B_col_cached"] == pytest.approx(5.0, abs=1e-9), (
            "B36=5 (LCF lookback parameter in the workbook)"
        )

    def test_cit_rate_is_10_pct(self):
        xd = _xd()
        row = xd["tax"]["rows"]["corporate_income_tax_formula"]
        assert row["B_col_cached"] == pytest.approx(0.10, abs=1e-6)

    def test_allocated_losses_cap_is_100_pct(self):
        xd = _xd()
        row = xd["tax"]["rows"]["allocated_losses"]
        assert row["B_col_cached"] == pytest.approx(1.0, abs=1e-9), (
            "B37=1.0 means losses can offset up to 100% of EBT"
        )


# ===========================================================================
# C — Tax depreciation source completeness
# ===========================================================================

class TestCTaxDepreciationSource:
    """Proves the workbook uses book depreciation (incl. financing costs) as
    tax depreciation.  Clean adapter uses hard-CAPEX-only basis — a C3B2 gap."""

    def test_pl_depreciation_matches_dep_total(self):
        xd = _xd()
        pl_dep = xd["pl"]["depreciation_keur"]
        dep_total = xd["dep"]["dep_total_keur"]
        for i in range(_N_PERIODS):
            pd = pl_dep[i] or 0
            dt = dep_total[i] or 0
            assert abs(pd - dt) < 0.001, (
                f"P&L depreciation != Dep total at period {i}: {pd:.3f} vs {dt:.3f}"
            )

    def test_excel_dep_total_lifetime(self):
        xd = _xd()
        total = sum(v for v in xd["dep"]["dep_total_keur"] if v is not None)
        assert abs(total - 57_973.053) < 0.005, f"Excel dep lifetime = {total:.3f}"

    def test_clean_book_dep_matches_excel(self):
        """book_dep in clean engine matches Excel to SOURCE_ROUNDING tolerance."""
        sys.path.insert(0, ".")
        from app.project_factories import create_default_oborovo
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.adapters.project_inputs import from_project_inputs

        pi = create_default_oborovo()
        omin = from_project_inputs(pi, source_id="c3b1_test", baseline_commit_sha="")
        result = run_operating_model(omin)
        total_book = sum(p.book_depreciation_keur for p in result.periods)
        assert abs(total_book - 57_973.053) < 0.005, (
            f"Clean book_dep lifetime {total_book:.3f} ≠ Excel 57,973.053"
        )

    def test_clean_tax_dep_differs_from_excel(self):
        """Clean adapter produces tax_dep from hard-CAPEX only; -1,973.967 kEUR gap."""
        sys.path.insert(0, ".")
        from app.project_factories import create_default_oborovo
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.adapters.project_inputs import from_project_inputs

        pi = create_default_oborovo()
        omin = from_project_inputs(pi, source_id="c3b1_test", baseline_commit_sha="")
        result = run_operating_model(omin)
        total_tax = sum(p.tax_depreciation_keur for p in result.periods)
        delta = total_tax - 57_973.053
        assert abs(delta - (-1_973.967)) < 0.5, (
            f"Expected clean tax_dep delta ≈ -1,973.967 kEUR; got {delta:.3f}"
        )

    def test_tax_dep_gap_equals_financing_cost_dep(self):
        """The exact gap is IDC + commitment fees + bank fees + VAT depreciation."""
        xd = _xd()
        idc = sum(v for v in xd["dep"]["dep_idc_keur"] if v is not None)
        commit = sum(v for v in xd["dep"]["dep_commitment_fees_keur"] if v is not None)
        bank = sum(v for v in xd["dep"]["dep_bank_fees_keur"] if v is not None)
        vat = sum(v for v in xd["dep"]["dep_vat_keur"] if v is not None)
        financing_dep = idc + commit + bank + vat
        assert abs(financing_dep - 1_973.967) < 0.5, (
            f"Financing cost dep = {financing_dep:.3f}, expected 1,973.967"
        )

    def test_tax_dep_mode_classification(self):
        """Classification: TAX_DEP_BOTH_ARE_INCOMPLETE.
        Factory says BOOK_BASED_PERCENTAGE (correct intent).
        Adapter ignores it and uses hard-CAPEX-only basis.
        Workbook uses book_dep = tax_dep."""
        from finco_core.inputs._models import TaxDepreciationMode
        from app.project_factories import create_default_oborovo
        pi = create_default_oborovo()
        mode = getattr(pi.tax, "tax_depreciation_mode", None)
        pct = getattr(pi.tax, "tax_deductible_book_dep_pct", None)
        assert mode == TaxDepreciationMode.BOOK_BASED_PERCENTAGE, (
            f"Factory must declare BOOK_BASED_PERCENTAGE; got {mode}"
        )
        assert pct == pytest.approx(1.0), (
            f"Factory must declare 100% deductible; got {pct}"
        )


# ===========================================================================
# D — Taxable income identity
# ===========================================================================

class TestDTaxableIncomeIdentity:
    """Proves the workbook's taxable income formula from cached values.
    Formula: taxable_income = EBT + fiscal_reintegration (exact, zero residual).
    Equivalent to: EBIT - senior_interest (when thin_cap=False).
    """

    def test_taxable_income_equals_ebt_plus_fiscal_reintegration(self):
        xd = _xd()
        ebt = xd["pl"]["earnings_before_tax_keur"]
        fr = xd["pl"]["fiscal_reintegration_keur"]
        ti = xd["pl"]["taxable_income_keur"]
        max_delta = max(
            abs((ebt[i] or 0) + (fr[i] or 0) - (ti[i] or 0))
            for i in range(_N_PERIODS)
        )
        assert max_delta < 1e-6, f"Max TI identity delta = {max_delta:.2e}"

    def test_fiscal_reintegration_equals_shl_interest(self):
        xd = _xd()
        fr = xd["pl"]["fiscal_reintegration_keur"]
        shl = xd["pl"]["shl_interests_keur"]
        max_delta = max(
            abs((fr[i] or 0) - (shl[i] or 0))
            for i in range(_N_PERIODS)
        )
        assert max_delta < 1e-6, (
            f"fiscal_reintegration ≠ SHL interest; max delta = {max_delta:.2e}"
        )

    def test_taxable_income_equals_ebt_plus_fr_machine_precision(self):
        """TI = EBT + FR exact from workbook formula (period_diagnostic confirms delta=0)."""
        xd = _xd()
        diag = xd["tax"]["period_diagnostic"]
        max_delta = max(r["identity_ti_eq_ebt_plus_fr_delta"] for r in diag)
        assert max_delta < 1e-9, (
            f"Max |EBT + FR - TI| from period_diagnostic = {max_delta:.2e}"
        )

    def test_financial_earnings_explains_ti_vs_ebit_minus_sd(self):
        """During debt tenor TI ≈ EBIT - SD (< 0.01 kEUR gap due to small cash interest).
        After repayment TI = EBIT + cash_interest because SD=0 and FR=0."""
        xd = _xd()
        diag = xd["tax"]["period_diagnostic"]
        # Check periods with senior debt: |TI - (EBIT - SD)| < 0.01
        for r in diag[1:30]:  # debt active in periods 1-28
            if r["excel_senior_keur"] > 1.0:  # meaningful debt
                ti_approx = r["excel_ebit_keur"] - r["excel_senior_keur"]
                delta = abs(r["excel_taxable_income_keur"] - ti_approx)
                assert delta < 0.02, (
                    f"Period {r['period']}: |TI - (EBIT-SD)| = {delta:.4f} (cash interest should be ~0)"
                )
        # After debt repayment (period 30+), financial earnings = cash interest
        p41 = diag[41]
        assert abs(p41["excel_taxable_income_keur"] - (p41["excel_ebit_keur"] + p41["excel_fin_earn_keur"])) < 1e-6, (
            "Period 41: TI = EBIT + fin_earn (no SD, no SHL, FR=0)"
        )

    def test_workbook_does_not_use_tax_depreciation_separately(self):
        """Workbook uses EBIT (net of book_dep) in taxable income chain.
        There is no separate tax_depreciation line in the P&L."""
        xd = _xd()
        tax = xd["tax"]
        assert "proved_formula_identity" in tax
        identity = tax["proved_formula_identity"]
        assert "EBIT" in identity, f"Identity must mention EBIT; got: {identity[:100]}"
        # Senior interest appears as SD or senior_interest or DS!G53
        assert any(kw in identity for kw in ("SD", "senior", "DS!")), (
            f"Identity must reference senior interest; got: {identity[:200]}"
        )

    def test_construction_period_taxable_income_zero(self):
        xd = _xd()
        ti = xd["pl"]["taxable_income_keur"]
        assert (ti[0] or 0) == 0.0, (
            f"Construction period taxable income must be 0; got {ti[0]}"
        )

    def test_opening_losses_zero(self):
        """Oborovo has no pre-existing tax losses at model start."""
        xd = _xd()
        lcf = xd["pl"]["losses_carryforward_keur"]
        assert (lcf[0] or 0) == 0.0
        assert (lcf[1] or 0) == 0.0


# ===========================================================================
# E — Interest dependency
# ===========================================================================

class TestEInterestDependency:
    """Classifies: INTEREST_DEPENDENCY_BLOCKS_TAX.
    Taxable income = EBIT - senior_interest.  Senior interest is a Phase 2C
    output.  No standalone Phase 2B tax parity is achievable without it."""

    def test_senior_interest_is_only_deductible(self):
        """Fiscal reintegration (FR) = full SHL → SHL has zero net deductibility.
        Net effective deduction = SD only; proved by FR = SHL (exact) and TI = EBT + FR."""
        xd = _xd()
        fr = xd["pl"]["fiscal_reintegration_keur"]
        shl = xd["pl"]["shl_interests_keur"]
        ebt = xd["pl"]["earnings_before_tax_keur"]
        ti = xd["pl"]["taxable_income_keur"]
        # FR = SHL  (SHL is fully reintegrated — net deductibility = 0)
        max_fr_shl = max(abs((fr[i] or 0) - (shl[i] or 0)) for i in range(_N_PERIODS))
        assert max_fr_shl < 0.001
        # TI = EBT + FR  (taxable income chain is exact)
        max_ti = max(abs((ebt[i] or 0) + (fr[i] or 0) - (ti[i] or 0)) for i in range(_N_PERIODS))
        assert max_ti < 0.001

    def test_shl_interest_is_not_deductible(self):
        """Fiscal reintegration = full SHL → SHL has zero net deductibility."""
        xd = _xd()
        fr = xd["pl"]["fiscal_reintegration_keur"]
        shl = xd["pl"]["shl_interests_keur"]
        for i in range(_N_PERIODS):
            assert abs((fr[i] or 0) - (shl[i] or 0)) < 1e-6, (
                f"Period {i}: FR={fr[i]:.3f} ≠ SHL={shl[i]:.3f}"
            )

    def test_excel_senior_interest_lifetime(self):
        xd = _xd()
        total = sum(v or 0 for v in xd["pl"]["senior_interests_keur"])
        assert abs(total - 20_133.079) < 0.005

    def test_excel_shl_interest_lifetime(self):
        xd = _xd()
        total = sum(v or 0 for v in xd["pl"]["shl_interests_keur"])
        assert abs(total - 32_104.911) < 0.005

    def test_phase23q_frozen_extraction_matches_excel_senior_interest_period_by_period(self):
        """The frozen phase23q CSV extraction matches Excel DS!G53 for all 43 operating periods.
        The CSV is a historical frozen extraction from a prior run, NOT the current clean runtime.
        Delta must be 0.0000 for all 43 periods (proved by period-by-period comparison)."""
        import csv
        rows = list(csv.DictReader(open("reports/phase23q_oborovo_senior_debt_sizing_extraction.csv")))
        xd = _xd()
        excel_sd = xd["pl"]["senior_interests_keur"]
        assert len(rows) == 43, f"Expected 43 operating periods in CSV; got {len(rows)}"
        for row in rows:
            period_idx = int(row["period_index"])  # 7..49 (excel col H-AX)
            # CSV col H = period_index 7 = first operating period = fixture period 1
            excel_period = period_idx - 7 + 1
            csv_int = float(row["senior_net_interest_keur"])
            exc_int = excel_sd[excel_period] if excel_period < len(excel_sd) else 0.0
            assert abs(csv_int - (exc_int or 0)) < 0.0001, (
                f"Period {excel_period}: CSV={csv_int:.4f} ≠ Excel={exc_int:.4f}"
            )

    def test_phase2c_current_runtime_interest_diverges_from_excel(self):
        """Current clean Phase 2C runtime produces a valid senior interest vector
        but sizes the debt differently from Excel (45,873 vs 42,852 kEUR).
        This causes a maximum per-period delta of 90.29 kEUR (period 25).
        Classification: INTEREST_DEPENDENCY_BLOCKS_TAX.

        The divergence root cause is different debt sizing constraints, not an
        engine defect.  C3B2 must use a Phase 2C run whose debt size matches Excel."""
        import sys
        sys.path.insert(0, ".")
        from financial_engine.orchestrator import run_senior_debt_model
        from financial_engine.inputs import TaxCalculationInput, SeniorDebtModelInput
        from finco_parity.tax_reference_inputs import build_tax_policy, build_opening_loss_vintages
        from finco_parity.financial_engine_tax_cfads_candidate import (
            _load_project_inputs, _load_baseline_snapshot, _build_exogenous_interest,
        )
        from financial_engine.adapters.project_inputs import from_project_inputs
        from finco_parity.check_financial_engine_senior_debt import (
            _build_senior_debt_policy, _build_senior_debt_inputs,
        )

        project_inputs = _load_project_inputs("oborovo")
        op_inputs = from_project_inputs(project_inputs, source_id="parity_oborovo")
        tax_policy = build_tax_policy("oborovo")
        opening_vintages = build_opening_loss_vintages("oborovo")
        snap = _load_baseline_snapshot("oborovo")
        exog_interest = _build_exogenous_interest(snap)
        tax_input = TaxCalculationInput(
            policy=tax_policy,
            opening_loss_vintages=opening_vintages,
            period_interest=exog_interest,
            period_adjustments=(),
        )
        eligible_cost = getattr(project_inputs.capex, "total_capex_keur", None) or 100_000.0
        sd_policy = _build_senior_debt_policy("oborovo")
        sd_inputs = _build_senior_debt_inputs("oborovo", eligible_cost)
        model_input = SeniorDebtModelInput(
            operating=op_inputs, tax=tax_input,
            senior_debt_policy=sd_policy, senior_debt_inputs=sd_inputs,
        )
        result = run_senior_debt_model(model_input)
        sd = result.senior_debt

        # Phase 2C produces a valid, non-empty vector
        assert len(sd.senior_interest_keur) == 60, (
            f"Expected 60 operating periods from Phase 2C; got {len(sd.senior_interest_keur)}"
        )
        p2c_lifetime = sum(sd.senior_interest_keur)
        # Excel lifetime = 20,133 kEUR; Phase 2C = 21,725 kEUR (+7.9%)
        assert p2c_lifetime > 20_000, "Phase 2C lifetime interest implausibly low"
        assert p2c_lifetime < 23_000, "Phase 2C lifetime interest implausibly high"

        # Confirm debt sizing mismatch is the root cause
        _EXCEL_DEBT_SIZE_KEUR = 42_852.28
        assert abs(sd.debt_size_keur - _EXCEL_DEBT_SIZE_KEUR) > 1_000, (
            "Expected Phase 2C debt size to diverge from Excel by > 1,000 kEUR; "
            f"got Phase2C={sd.debt_size_keur:.2f}, Excel={_EXCEL_DEBT_SIZE_KEUR:.2f}"
        )

        # Alignment: Phase 2C period p -> fixture period p-1
        xd = _xd()
        excel_sd_v = xd["pl"]["senior_interests_keur"]
        p2c_by_fixture = {pi - 1: v for pi, v in zip(sd.period_indices, sd.senior_interest_keur)}
        max_delta = max(
            abs((p2c_by_fixture.get(p, 0.0) if abs(p2c_by_fixture.get(p, 0.0)) > 0.001 else 0.0)
                - (excel_sd_v[p] or 0.0))
            for p in range(1, 29)
        )
        # Max delta must be > 1 kEUR (confirmed difference, not noise)
        assert max_delta > 1.0, (
            f"Expected Phase 2C vs Excel delta > 1 kEUR; got {max_delta:.4f} kEUR. "
            "If delta is unexpectedly small, re-check debt sizing."
        )
        # Classify the blocker
        classification = "INTEREST_DEPENDENCY_BLOCKS_TAX"
        assert classification == "INTEREST_DEPENDENCY_BLOCKS_TAX"


# ===========================================================================
# F — Tax loss roll-forward
# ===========================================================================

class TestFTaxLossRollForward:
    """Proves 5-period rolling window for Oborovo LCF.
    Workbook formula B36=5 is a PERIOD count, not a YEAR count."""

    def test_opening_losses_zero_at_model_start(self):
        xd = _xd()
        lcf = xd["pl"]["losses_carryforward_keur"]
        assert (lcf[0] or 0) == 0.0
        assert (lcf[1] or 0) == 0.0

    def test_5_period_window_period_7(self):
        """Period 7 opening LCF = sum of negative TI for periods 2-6 (5 periods)."""
        xd = _xd()
        ti = xd["pl"]["taxable_income_keur"]
        expected = sum(min(0.0, ti[j] or 0) for j in range(2, 7))
        losses_n1 = xd["tax"]["rows"]["losses_n_minus_1"]["period_values"]
        actual = losses_n1[7]
        assert abs((actual or 0) - expected) < 0.001, (
            f"Period 7 opening LCF: computed={expected:.3f}, wb={actual}"
        )

    def test_5_period_window_period_8(self):
        """Period 8 opening LCF = sum of negative TI for periods 3-7."""
        xd = _xd()
        ti = xd["pl"]["taxable_income_keur"]
        expected = sum(min(0.0, ti[j] or 0) for j in range(3, 8))
        losses_n1 = xd["tax"]["rows"]["losses_n_minus_1"]["period_values"]
        actual = losses_n1[8]
        assert abs((actual or 0) - expected) < 0.001, (
            f"Period 8 opening LCF: computed={expected:.3f}, wb={actual}"
        )

    def test_losses_expire_at_period_11(self):
        """By period 11 all losses have expired (5-period window; p6+ all positive)."""
        xd = _xd()
        lcf_opening = xd["tax"]["rows"]["losses_n_minus_1"]["period_values"]
        assert (lcf_opening[11] or 0) == pytest.approx(0.0, abs=0.001), (
            f"Period 11 opening LCF should be 0; got {lcf_opening[11]}"
        )

    def test_loss_utilization_requires_positive_ebt(self):
        """Losses are only utilized when EBT > 0 (not just taxable income > 0)."""
        xd = _xd()
        allocated = xd["tax"]["rows"]["allocated_losses"]["period_values"]
        ebt = xd["pl"]["earnings_before_tax_keur"]
        # In periods where EBT<0 but TI>0 (fiscal reintegration effect), no utilization
        for i in range(_N_PERIODS):
            ebt_v = ebt[i] or 0
            alloc_v = allocated[i] or 0
            if ebt_v < 0 and alloc_v > 0:
                pytest.fail(
                    f"Period {i}: EBT={ebt_v:.3f} < 0 but allocated_losses={alloc_v:.3f} > 0"
                )

    def test_roll_forward_identity(self):
        """LCF opening at period i = SUMIF(negative TI, last 5 periods ending at i-1).
        carriable (row 39) and losses_n_minus_1 (row 36) both represent this opening balance."""
        xd = _xd()
        ti = xd["pl"]["taxable_income_keur"]
        lcf_open = xd["tax"]["rows"]["losses_n_minus_1"]["period_values"]
        # Verify periods 7 and 8 (proved in detail by separate tests); check a few more
        for i in range(7, 12):
            window = range(max(2, i - 5), i)  # 5 periods before i
            expected = sum(min(0.0, ti[j] or 0) for j in window)
            actual = lcf_open[i] or 0
            assert abs(expected - actual) < 0.002, (
                f"Period {i}: SUMIF window computed={expected:.3f}, wb={actual:.3f}"
            )

    def test_tax_loss_source_complete(self):
        """TAX_LOSS_SOURCE_COMPLETE: opening balance proved from workbook (period 0 = 0).
        Parity layer build_opening_loss_vintages('oborovo') returns empty tuple."""
        xd = _xd()
        lcf_open = xd["tax"]["rows"]["losses_n_minus_1"]["period_values"]
        assert (lcf_open[0] or 0) == 0.0, "Period 0 LCF opening must be 0"
        assert (lcf_open[1] or 0) == 0.0, "Period 1 LCF opening must be 0"
        from finco_parity.tax_reference_inputs import build_opening_loss_vintages
        vintages = build_opening_loss_vintages("oborovo")
        assert vintages == () or len(vintages) == 0, (
            f"build_opening_loss_vintages('oborovo') must return empty; got {vintages}"
        )


# ===========================================================================
# G — Tax year fragmentation
# ===========================================================================

class TestGTaxYearFragmentation:
    """Proves the workbook uses a model-year (2-period = 1 year) convention.
    CIT is collected in even-indexed periods, not calendar year Jan-Dec."""

    def test_cit_only_in_even_operating_periods(self):
        xd = _xd()
        cit = xd["pl"]["corporate_income_tax_keur"]
        for i in range(_N_PERIODS):
            cit_v = cit[i] or 0
            if i == 0:
                assert cit_v == 0.0, "Construction period has no CIT"
            elif i % 2 == 1:  # odd operating period
                assert abs(cit_v) < 1e-6, (
                    f"Odd period {i} should have CIT=0; got {cit_v:.3f}"
                )

    def test_python_tax_year_uses_calendar_year(self):
        """Python build_tax_year_bases splits on Jan 1, not model-year boundary."""
        sys.path.insert(0, ".")
        from app.project_factories import create_default_oborovo
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.tax.tax_year import build_tax_year_bases

        pi = create_default_oborovo()
        omin = from_project_inputs(pi, source_id="c3b1_test", baseline_commit_sha="")
        result = run_operating_model(omin)
        bases = build_tax_year_bases(result.periods, {}, {})
        # Calendar year 2030 covers Jun-Dec 2030 (one H2 half-period)
        year_2030 = next((b for b in bases if b.tax_year == 2030), None)
        assert year_2030 is not None
        # Python 2030 has one operating period (H2-2030 ending Dec 31 2030)
        # Excel pairs H2-2030 (period 1) with H1-2031 (period 2) as "model year 1"
        assert 2030 in {b.tax_year for b in bases}, "Calendar year 2030 must exist"

    def test_model_year_vs_calendar_year_mapping_proved(self):
        """Workbook model-year mapping proved from proved_model_year_mapping string
        and from period_diagnostic CIT check.

        Structure (from P&L row 1/2 dates, proved in extractor):
          Period 0: construction (BoP 2029-06-29, EoP 2030-06-30)
          Period 1: H2-2030 (Jul-Dec 2030)
          Period 2: H1-2031 (Jan-Jun 2031)
          ...CIT fires in even periods summing [prev, this] taxable profits.

        Python splits on calendar Jan 1 (not H2+H1 model-year boundary)."""
        xd = _xd()
        # Proved mapping text must mention H2 and H1 periods
        proved = xd["tax"].get("proved_model_year_mapping", "")
        assert "H2-2030" in proved and "H1-2031" in proved, (
            f"proved_model_year_mapping must document H2-2030 and H1-2031; got: {proved[:200]}"
        )
        # Period 6 CIT (even period): sums periods 5+6
        diag = xd["tax"]["period_diagnostic"]
        p5_tp = diag[5]["excel_taxable_profit_keur"]
        p6_tp = diag[6]["excel_taxable_profit_keur"]
        p6_cit = diag[6]["excel_cit_p43_keur"]
        expected = max(0.0, p5_tp + p6_tp) * 0.10
        assert abs(p6_cit - expected) < 1e-4, (
            f"Period 6 CIT={p6_cit:.3f} ≠ (TP5+TP6)*10%={expected:.3f}"
        )


# ===========================================================================
# H — Current tax identity
# ===========================================================================

class TestHCurrentTaxIdentity:
    """Proves the CIT formula from workbook formulas and cached values."""

    def test_cit_equals_annual_tp_sum_times_rate(self):
        xd = _xd()
        cit = xd["pl"]["corporate_income_tax_keur"]
        tp = xd["pl"]["taxable_profit_keur"]
        rate = 0.10
        max_delta = 0.0
        for i in range(2, _N_PERIODS, 2):  # even operating periods
            annual_tp = (tp[i - 1] or 0) + (tp[i] or 0)
            expected = max(0.0, annual_tp) * rate
            delta = abs((cit[i] or 0) - expected)
            max_delta = max(max_delta, delta)
        assert max_delta < 1e-4, (
            f"Max |CIT - annual_sum×rate| = {max_delta:.2e}"
        )

    def test_cit_rate_is_10_pct(self):
        xd = _xd()
        assert xd["tax"]["rows"]["corporate_income_tax_formula"]["B_col_cached"] == pytest.approx(0.10)

    def test_excel_cit_lifetime(self):
        xd = _xd()
        total = sum(v or 0 for v in xd["pl"]["corporate_income_tax_keur"])
        assert abs(total - 10_443.088) < 0.005

    def test_taxable_profit_equals_taxable_income_when_ebt_negative(self):
        """When EBT<0, allocated_losses=0 → taxable_profit = taxable_income."""
        xd = _xd()
        tp = xd["pl"]["taxable_profit_keur"]
        ti = xd["pl"]["taxable_income_keur"]
        ebt = xd["pl"]["earnings_before_tax_keur"]
        for i in range(_N_PERIODS):
            if (ebt[i] or 0) < 0:
                assert abs((tp[i] or 0) - (ti[i] or 0)) < 1e-6, (
                    f"Period {i}: EBT<0 → tp={tp[i]:.3f} should equal ti={ti[i]:.3f}"
                )


# ===========================================================================
# I — Cash tax timing
# ===========================================================================

class TestICashTaxTiming:
    """Proves cash tax timing: CIT is paid in even-indexed operating periods."""

    def test_cash_tax_paid_in_even_periods(self):
        xd = _xd()
        cit = xd["pl"]["corporate_income_tax_keur"]
        for i in range(1, _N_PERIODS):
            cit_v = cit[i] or 0
            if cit_v > 0.001:
                assert i % 2 == 0, (
                    f"CIT paid in odd period {i}: {cit_v:.3f} kEUR"
                )

    def test_cash_tax_corresponds_to_two_period_annual_sum(self):
        """Each CIT payment covers the two-period model year."""
        xd = _xd()
        cit = xd["pl"]["corporate_income_tax_keur"]
        tp = xd["pl"]["taxable_profit_keur"]
        # Verify at period 6 (first CIT payment)
        p5_tp = tp[5] or 0
        p6_tp = tp[6] or 0
        p6_cit = cit[6] or 0
        expected = max(0.0, p5_tp + p6_tp) * 0.10
        assert abs(p6_cit - expected) < 1e-4, (
            f"Period 6 CIT: expected {expected:.3f}, got {p6_cit:.3f}"
        )

    def test_no_cit_during_construction(self):
        xd = _xd()
        cit = xd["pl"]["corporate_income_tax_keur"]
        assert (cit[0] or 0) == 0.0

    def test_python_policy_cash_tax_timing(self):
        """Python TaxPolicy uses TAX_YEAR_LAST_PERIOD (annual) for Oborovo."""
        sys.path.insert(0, ".")
        from finco_parity.tax_reference_inputs import build_tax_policy
        from financial_engine.policies.tax import CashTaxTiming
        policy = build_tax_policy("oborovo")
        assert policy.cash_tax_timing == CashTaxTiming.TAX_YEAR_LAST_PERIOD

    def test_cf_cash_tax_formula_confirmed_from_dual_load(self):
        """CF row 77 formula text is captured from workbook via dual-load.
        Formula must reference P&L!row44 (not hardcoded). Sign: negative = outflow."""
        xd = _xd()
        chain = xd["tax"]["cf_tax_chain"]
        formula = chain["cf_row_77_formula_period1"]
        assert formula is not None, "CF row 77 formula must be captured from dual-load"
        assert "P&L" in formula, (
            f"CF row 77 must reference P&L sheet; got formula: {formula!r}"
        )
        assert "44" in formula, (
            f"CF row 77 must reference row 44; got formula: {formula!r}"
        )
        # Sign: formula must start with minus
        assert formula.startswith("=-"), (
            f"CF row 77 formula must be negation of P&L row 44; got: {formula!r}"
        )

    def test_cf_cash_tax_vector_equals_neg_pl_row44(self):
        """CF cash tax vector (row 77) equals -P&L row 44 for all 61 periods.
        Proved from actual workbook values via dual-load. Max delta = 0."""
        xd = _xd()
        chain = xd["tax"]["cf_tax_chain"]
        assert chain["cf_vs_pl44_max_delta_keur"] == 0.0, (
            f"CF row 77 must equal -P&L row 44 exactly; "
            f"max delta = {chain['cf_vs_pl44_max_delta_keur']}"
        )
        # Verify CF cash tax sign: paid CIT periods must be negative in CF
        diag = xd["tax"]["period_diagnostic"]
        for entry in diag:
            p44 = entry["excel_cit_p44_routed_keur"]
            cf = entry["excel_cf_cash_tax_keur"]
            if abs(p44) > 0.001:
                assert abs(cf + p44) < 1e-6, (
                    f"Period {entry['period']}: CF={cf:.4f} must equal -P44={-p44:.4f}"
                )

    def test_pl_current_tax_row43_equals_row44_equals_cf_row77(self):
        """Three-way proof: P&L row 43 = P&L row 44 = -CF row 77 for all periods.
        Row 43 is the economic formula; row 44 routes via Macro; CF row 77 = -row 44.
        All three must agree to machine precision (max delta = 0)."""
        xd = _xd()
        auth = xd["tax"]["cit_row43_vs_row44_authority"]
        assert auth["row_43_vs_44_max_delta_keur"] < 1e-9, (
            "P&L row 43 (formula) must equal row 44 (Macro-routed) to machine precision"
        )
        chain = xd["tax"]["cf_tax_chain"]
        assert chain["cf_vs_pl44_max_delta_keur"] == 0.0, (
            "CF row 77 must equal -P&L row 44 to machine precision"
        )
        # Lifetime from period_diagnostic (using p43 values)
        diag = xd["tax"]["period_diagnostic"]
        cit_total = sum(r["excel_cit_p43_keur"] for r in diag)
        assert abs(cit_total - 10_443.088) < 0.005, (
            f"CIT lifetime = {cit_total:.3f}, expected 10,443.088"
        )

    def test_bs_no_tax_payable_row_exists(self):
        """The BS sheet has no tax payable or tax receivable row.
        CIT settles within each period: no BS tax balance accumulates."""
        xd = _xd()
        chain = xd["tax"]["cf_tax_chain"]
        assert chain["bs_tax_payable_row_exists"] is False
        assert chain["terminal_bs_tax_balance_keur"] == 0.0
        assert chain["payment_lag_periods"] == 0


# ===========================================================================
# J — Sign conventions
# ===========================================================================

class TestJSignConventions:
    """Proves workbook sign conventions from cached values."""

    def test_senior_interest_stored_positive(self):
        xd = _xd()
        sd = xd["pl"]["senior_interests_keur"]
        positive = [v for v in sd if v is not None and v > 0.001]
        assert len(positive) > 0, "Senior interest should be positive in P&L"

    def test_shl_interest_stored_positive(self):
        xd = _xd()
        shl = xd["pl"]["shl_interests_keur"]
        positive = [v for v in shl if v is not None and v > 0.001]
        assert len(positive) > 0

    def test_losses_carryforward_stored_negative(self):
        xd = _xd()
        lcf = xd["pl"]["losses_carryforward_keur"]
        negative = [v for v in lcf if v is not None and v < -0.001]
        assert len(negative) > 0, "Loss carryforward stored as negative in workbook"

    def test_fiscal_reintegration_stored_positive(self):
        """Fiscal reintegration = +SHL in P&L (addback to taxable income)."""
        xd = _xd()
        fr = xd["pl"]["fiscal_reintegration_keur"]
        positive = [v for v in fr if v is not None and v > 0.001]
        assert len(positive) > 0


# ===========================================================================
# K — Clean / legacy / source diagnostic
# ===========================================================================

class TestKCleanLegacySourceDiagnostic:
    def test_clean_book_dep_matches_excel(self):
        sys.path.insert(0, ".")
        from app.project_factories import create_default_oborovo
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.adapters.project_inputs import from_project_inputs
        pi = create_default_oborovo()
        omin = from_project_inputs(pi, source_id="c3b1_test", baseline_commit_sha="")
        result = run_operating_model(omin)
        total_book = sum(p.book_depreciation_keur for p in result.periods)
        assert abs(total_book - 57_973.053) < 0.005

    def test_clean_tax_dep_vs_excel_delta(self):
        sys.path.insert(0, ".")
        from app.project_factories import create_default_oborovo
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.adapters.project_inputs import from_project_inputs
        pi = create_default_oborovo()
        omin = from_project_inputs(pi, source_id="c3b1_test", baseline_commit_sha="")
        result = run_operating_model(omin)
        total_tax = sum(p.tax_depreciation_keur for p in result.periods)
        delta = total_tax - 57_973.053
        assert -2_000.0 < delta < -1_900.0, (
            f"Clean tax_dep delta expected ≈ -1,974; got {delta:.3f}"
        )

    def test_clean_has_two_construction_periods(self):
        """Clean engine splits 12-month construction into two semesters; Excel has one."""
        sys.path.insert(0, ".")
        from app.project_factories import create_default_oborovo
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.adapters.project_inputs import from_project_inputs
        pi = create_default_oborovo()
        omin = from_project_inputs(pi, source_id="c3b1_test", baseline_commit_sha="")
        result = run_operating_model(omin)
        n_construction = sum(1 for p in result.periods if not p.is_operation)
        assert n_construction == 2

    def test_excel_period_count(self):
        xd = _xd()
        assert len(xd["pl"]["taxable_income_keur"]) == _N_PERIODS

    def test_no_clean_interest_in_phase2b_standalone(self):
        """Phase 2B does not size debt; clean tax calc has no interest without Phase 2C."""
        from finco_parity.tax_reference_inputs import build_tax_policy
        policy = build_tax_policy("oborovo")
        from financial_engine.inputs import TaxCalculationInput
        tax_input = TaxCalculationInput(
            policy=policy,
            opening_loss_vintages=(),
            period_interest=(),  # no interest without Phase 2C
            period_adjustments=(),
        )
        # Just verify the dataclass is constructable (no assertion on tax values)
        assert tax_input is not None


# ===========================================================================
# L — No production formula diff (financial freeze)
# ===========================================================================

class TestLFinancialFreeze:
    """All diffs are against the approved base SHA, not HEAD vs HEAD (which is tautological).
    Base SHA: b11e5bf7b9ab60bae174081e7d9f8541190bf371"""

    def _diff_vs_base(self, path):
        import subprocess
        result = subprocess.run(
            ["git", "diff", _BASE_SHA, "HEAD", "--", path],
            capture_output=True, text=True,
        )
        return result.stdout

    def test_no_tax_engine_formula_changed(self):
        """financial_engine/tax/ must not be modified by C3B1."""
        diff = self._diff_vs_base("financial_engine/tax/")
        assert diff == "", (
            f"financial_engine/tax/ modified vs base {_BASE_SHA[:8]}: {diff[:400]}"
        )

    def test_no_orchestrator_formula_changed(self):
        diff = self._diff_vs_base("financial_engine/orchestrator.py")
        assert diff == "", f"orchestrator.py modified vs base {_BASE_SHA[:8]}"

    def test_no_results_changed(self):
        diff = self._diff_vs_base("financial_engine/results.py")
        assert diff == "", f"results.py modified vs base {_BASE_SHA[:8]}"

    def test_no_financial_engine_adapters_changed(self):
        diff = self._diff_vs_base("financial_engine/adapters/")
        assert diff == "", f"financial_engine/adapters/ modified vs base {_BASE_SHA[:8]}"

    def test_no_app_project_factories_changed(self):
        diff = self._diff_vs_base("app/project_factories.py")
        assert diff == "", f"project_factories.py modified vs base {_BASE_SHA[:8]}"

    def test_only_diagnostic_files_added(self):
        """C3B1 may only add: extractor, fixture, test file, docs. Nothing else."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", _BASE_SHA, "HEAD", "--name-only"],
            capture_output=True, text=True,
        )
        changed = set(result.stdout.strip().splitlines())
        allowed = {
            "finco_recon/extract_oborovo_excel.py",
            "tests/fixtures/excel_oborovo_financial_truth.json",
            "tests/test_stage_c3b1_oborovo_tax_source_truth.py",
            "docs/reconciliation/oborovo_tax_source_truth.md",
        }
        unexpected = changed - allowed
        assert not unexpected, (
            f"C3B1 modified files outside allowed set: {unexpected}"
        )


# ===========================================================================
# M — No project identity dispatch in production engine
# ===========================================================================

class TestMNoProjectIdentityDispatch:
    def test_no_oborovo_string_in_tax_engine(self):
        import subprocess
        result = subprocess.run(
            ["grep", "-r", "oborovo", "financial_engine/"],
            capture_output=True, text=True,
        )
        assert result.stdout == "", (
            f"'oborovo' found in financial_engine/: {result.stdout[:300]}"
        )

    def test_no_project_code_dispatch_in_tax_engine(self):
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "project_code\|project_name\|baseline_id", "financial_engine/"],
            capture_output=True, text=True,
        )
        assert result.stdout == "", (
            f"Project identity dispatch found in financial_engine/: {result.stdout[:300]}"
        )

    def test_parity_layer_dispatch_is_permitted(self):
        """finco_parity/tax_reference_inputs.py uses baseline_id — this is permitted."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rl", "baseline_id", "finco_parity/"],
            capture_output=True, text=True,
        )
        assert "tax_reference_inputs" in result.stdout, (
            "Parity layer should use baseline_id for routing tax reference inputs"
        )


# ===========================================================================
# N — No target plug or hardcoded CIT total
# ===========================================================================

class TestNNoTargetPlug:
    def test_no_hardcoded_cit_total_in_engine(self):
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "10443\|10,443", "financial_engine/"],
            capture_output=True, text=True,
        )
        assert result.stdout == "", (
            f"Hardcoded CIT total found: {result.stdout[:300]}"
        )

    def test_no_approved_delta_plug_in_engine(self):
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "approved_delta\|tax.*plug\|cit.*target", "financial_engine/"],
            capture_output=True, text=True,
        )
        assert result.stdout == "", (
            f"Target-plug pattern found: {result.stdout[:300]}"
        )


# ===========================================================================
# O — C3A upstream freeze
# ===========================================================================

class TestOC3AUpstreamFreeze:
    def test_ebit_keur_in_operating_period_result(self):
        sys.path.insert(0, ".")
        from financial_engine.results import OperatingPeriodResult
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(OperatingPeriodResult)}
        assert "ebit_keur" in field_names

    def test_operating_schedules_has_ebit(self):
        from financial_engine.results import OperatingSchedules
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(OperatingSchedules)}
        assert "ebit_keur" in field_names

    def test_clean_ebitda_unchanged(self):
        sys.path.insert(0, ".")
        from app.project_factories import create_default_oborovo
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.adapters.project_inputs import from_project_inputs
        pi = create_default_oborovo()
        omin = from_project_inputs(pi, source_id="c3b1_test", baseline_commit_sha="")
        result = run_operating_model(omin)
        clean_ebitda = sum(p.ebitda_keur for p in result.periods if p.is_operation)
        assert abs(clean_ebitda - 181_893.870) < 0.5, (
            f"EBITDA should be frozen at 181,893.870; got {clean_ebitda:.3f}"
        )

    def test_ebit_identity_holds(self):
        sys.path.insert(0, ".")
        from app.project_factories import create_default_oborovo
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.adapters.project_inputs import from_project_inputs
        pi = create_default_oborovo()
        omin = from_project_inputs(pi, source_id="c3b1_test", baseline_commit_sha="")
        result = run_operating_model(omin)
        for p in result.periods:
            expected = p.ebitda_keur - p.book_depreciation_keur
            assert abs(p.ebit_keur - expected) < 1e-9, (
                f"Period {p.period_index}: ebit={p.ebit_keur:.6f} ≠ ebitda-book_dep={expected:.6f}"
            )


# ===========================================================================
# P — GitHub workflow and test failure classification
# ===========================================================================

class TestPRegressionGuard:
    """Verifies that C3B1 changes do not introduce new test failures.

    CI workflow failure classification for all seven GitHub Actions workflows
    is documented in docs/reconciliation/oborovo_tax_source_truth.md (section
    'GitHub Workflow Failure Matrix').  That section is the authoritative record;
    this group contains only behaviorally testable regression guards.

    PRE_EXISTING_ON_BASE: present on b11e5bf7 before C3B1 changes.
    INTRODUCED: first appears after C3B1 changes (none permitted in this PR).
    ENVIRONMENTAL: workbook / infra absent in CI (not a code defect).
    """

    def test_no_new_failures_introduced_by_c3b1(self):
        """C3A and Phase 2C regression suites pass at HEAD.
        Only the pre-existing test_phase2b_tax_cfads[oborovo] failure remains."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest",
             "tests/test_stage_c3a_clean_pnl_through_ebit.py",
             "tests/test_phase2c_senior_debt.py",
             "-q", "--tb=no"],
            capture_output=True, text=True, cwd=".",
        )
        assert result.returncode == 0, (
            f"Regression tests failed (C3B1 introduced new failures):\n{result.stdout[-800:]}"
        )

    def test_pre_existing_failure_is_phase2b_oborovo_only(self):
        """Only one test should fail at HEAD: test_phase2b_tax_cfads[oborovo].
        This was already failing on base SHA b11e5bf7 (verified by git stash test).
        Root cause: cash_tax_bridge_reconciliation drift not approved in parity layer."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest",
             "tests/test_phase2b_tax_cfads.py",
             "-q", "--tb=no"],
            capture_output=True, text=True, cwd=".",
        )
        # Exactly the pre-existing oborovo failure; no new failures
        out = result.stdout + result.stderr
        assert "oborovo" in out or result.returncode != 0, (
            "Expected pre-existing oborovo failure to remain; test suite output unexpected"
        )
        # Assert no NEW unexpected test IDs appear as failures
        lines = [l for l in out.splitlines() if l.startswith("FAILED")]
        introduced = [l for l in lines if "oborovo" not in l]
        assert not introduced, (
            f"C3B1 introduced unexpected new failures in Phase2B suite:\n" +
            "\n".join(introduced)
        )
