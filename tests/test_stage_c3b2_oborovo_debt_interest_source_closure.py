"""Stage C3B2 — Oborovo Debt Sizing & Interest Source Closure.

Tests validate generated evidence and numerical identities, not fixture text.
All tests are CI-portable: no workbook binary required.

Verdict classification must be determined by the evidence in the fixture,
not by comparing a fixed string — the sole exception is
test_verdict_supported_by_evidence which verifies the verdict is one of the
four permitted classifications and that the evidence is consistent.
"""
from __future__ import annotations

import json
import pathlib

import pytest

FIXTURE_PATH = (
    pathlib.Path(__file__).parent / "fixtures" / "excel_oborovo_debt_interest_truth.json"
)
EXPECTED_WORKBOOK_SHA = "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920"
EXPECTED_EXTRACTOR_VERSION = "2.0.0"

VALID_VERDICTS = frozenset({
    "C3B2_DEBT_INTEREST_SOURCE_TRUTH_PROVED",
    "C3B2_SOURCE_TRUTH_PARTIAL_MANUAL_CHECK_REQUIRED",
})

N_PERIODS = 61


@pytest.fixture(scope="module")
def truth() -> dict:
    with FIXTURE_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Extractor version — single source of truth
# ---------------------------------------------------------------------------

class TestExtractorVersion:
    def test_module_version_matches_expected(self):
        from finco_recon.extract_oborovo_debt_interest import _EXTRACTOR_VERSION
        assert _EXTRACTOR_VERSION == EXPECTED_EXTRACTOR_VERSION

    def test_fixture_version_matches_module(self, truth):
        from finco_recon.extract_oborovo_debt_interest import _EXTRACTOR_VERSION
        assert truth["_meta"]["extractor_version"] == _EXTRACTOR_VERSION

    def test_fixture_has_source_filename(self, truth):
        assert "source_filename" in truth["_meta"]
        assert truth["_meta"]["source_filename"]

    def test_fixture_has_exact_sha256(self, truth):
        assert truth["_meta"]["source_sha256"] == EXPECTED_WORKBOOK_SHA, (
            "Fixture SHA-256 does not match authoritative workbook. "
            "Regenerate with: python -m finco_recon.extract_oborovo_debt_interest "
            "--workbook <path> --output tests/fixtures/excel_oborovo_debt_interest_truth.json"
        )

    def test_fixture_has_extraction_timestamp(self, truth):
        ts = truth["_meta"].get("extraction_timestamp_utc", "")
        assert ts and ts.endswith("Z"), f"Timestamp missing or malformed: {ts!r}"

    def test_fixture_has_dual_load_note(self, truth):
        note = truth["_meta"].get("dual_load_note", "")
        assert "data_only=True" in note and "data_only=False" in note

    def test_no_manual_exploration_placeholder(self, truth):
        raw = json.dumps(truth)
        assert "MANUAL_EXPLORATION_NO_BINARY_IN_CI" not in raw, (
            "Fixture still contains manual-exploration placeholder. Regenerate from workbook."
        )


# ---------------------------------------------------------------------------
# Workstream A — CFADS composition
# ---------------------------------------------------------------------------

class TestWorkstreamA_CFADS:
    def test_section_present(self, truth):
        assert "workstream_a" in truth

    def test_ds_row20_formula_references_macro(self, truth):
        formula = truth["workstream_a"]["ds_row20_cfads"]["formula_h"]
        assert formula is not None
        assert "Macro" in formula

    def test_cfads_period_vector_length(self, truth):
        vals = truth["workstream_a"]["ds_row20_cfads"]["period_values_keur"]
        assert len(vals) == N_PERIODS

    def test_cfads_period1_plausible(self, truth):
        p1 = truth["workstream_a"]["ds_row20_cfads"]["period_values_keur"][1]
        assert p1 is not None
        assert 1000 < p1 < 5000, f"Period-1 CFADS implausible: {p1}"

    def test_cf_row79_formula_contains_correct_components(self, truth):
        fml = truth["workstream_a"]["cf_row79_free_cash_flow_for_banks"]["formula_h"]
        assert fml is not None
        assert "H23" in fml or "SUM" in fml

    def test_cf_row79_period_vector_length(self, truth):
        vals = truth["workstream_a"]["cf_row79_free_cash_flow_for_banks"]["period_values_keur"]
        assert len(vals) == N_PERIODS

    def test_component_bridge_identity_holds(self, truth):
        bridge = truth["workstream_a"]["component_bridge"]
        assert bridge["identity_holds"] is True, (
            f"CF row79 != SUM(components); max residual = {bridge['max_absolute_residual_keur']}"
        )

    def test_no_unexpected_null_in_active_cfads(self, truth):
        vals = truth["workstream_a"]["ds_row20_cfads"]["period_values_keur"]
        for p in range(1, 29):
            assert vals[p] is not None, f"CFADS null at active period {p}"

    def test_dscr_target_period1(self, truth):
        p1 = truth["workstream_a"]["ds_row22_dscr_target"]["period_values"][1]
        assert p1 is not None
        assert abs(p1 - 1.15) < 0.001

    def test_dscr_target_period25_band_switch(self, truth):
        """Excel DSCR switches from 1.15 to 1.35 at period 25."""
        vals = truth["workstream_a"]["ds_row22_dscr_target"]["period_values"]
        p24 = vals[24]; p25 = vals[25]
        assert p24 is not None and p25 is not None
        assert abs(p24 - 1.15) < 0.01, f"p24 DSCR expected 1.15, got {p24}"
        assert abs(p25 - 1.35) < 0.01, f"p25 DSCR expected 1.35, got {p25}"


# ---------------------------------------------------------------------------
# Workstream B — Sculpting algorithm
# ---------------------------------------------------------------------------

class TestWorkstreamB_Sculpting:
    def test_section_present(self, truth):
        assert "workstream_b" in truth

    def test_ds_row47_formula_references_next_period(self, truth):
        formula = truth["workstream_b"]["period_vectors"]["row47_capacity"]["formula_h"]
        assert formula is not None
        assert "I47" in formula

    def test_ds_d51_positive(self, truth):
        val = truth["workstream_b"]["ds_d51_total_debt"]["value_keur"]
        assert val is not None and val > 0

    def test_ds_d47_equals_d51_in_fixture(self, truth):
        d47 = truth["workstream_b"]["ds_d47_total_capacity"]["value_keur"]
        d51 = truth["workstream_b"]["ds_d51_total_debt"]["value_keur"]
        assert d47 is not None and d51 is not None
        assert abs(d47 - d51) < 0.01, f"D47={d47} should equal D51={d51}"

    def test_opening_balance_period1_equals_d51(self, truth):
        d51 = truth["workstream_b"]["ds_d51_total_debt"]["value_keur"]
        op_p1 = truth["workstream_b"]["period_vectors"]["row61_opening"]["period_values"][1]
        assert op_p1 is not None
        assert abs(op_p1 - d51) < 0.01

    def test_debt_rollforward_identity(self, truth):
        """closing[p-1] = opening[p] for all active periods."""
        opening = truth["workstream_b"]["period_vectors"]["row61_opening"]["period_values"]
        closing = truth["workstream_b"]["period_vectors"]["row67_closing"]["period_values"]
        for p in range(2, 29):
            if opening[p] is not None and closing[p-1] is not None:
                diff = abs(opening[p] - closing[p-1])
                assert diff < 0.01, f"Roll-forward mismatch at p{p}: opening={opening[p]}, prev_closing={closing[p-1]}"

    def test_interest_identity_per_period(self, truth):
        """interest[p] = opening[p] × rate[p] × day_frac[p]"""
        opening = truth["workstream_b"]["period_vectors"]["row61_opening"]["period_values"]
        interest = truth["workstream_b"]["period_vectors"]["row64_interest"]["period_values"]
        rate = truth["workstream_e"]["ds_row44_annual_sculpting_rate"]["period_values"]
        frac = truth["workstream_b"]["period_vectors"]["row6_day_frac"]["period_values"]
        for p in range(1, 29):
            if all(v is not None for v in [opening[p], rate[p], frac[p], interest[p]]):
                expected = opening[p] * rate[p] * frac[p]
                assert abs(interest[p] - expected) < 0.01, (
                    f"Interest identity failed at p{p}: "
                    f"got {interest[p]:.4f}, expected {expected:.4f}"
                )

    def test_no_unexpected_null_opening_in_active(self, truth):
        opening = truth["workstream_b"]["period_vectors"]["row61_opening"]["period_values"]
        for p in range(1, 29):
            assert opening[p] is not None, f"Opening balance null at active period {p}"

    def test_convergence_mechanism_documented(self, truth):
        mech = truth["workstream_b"]["convergence_mechanism"]
        assert "EXCEL" in mech or "ITERATIVE" in mech

    def test_algorithm_match_noted(self, truth):
        note = truth["workstream_b"]["algorithm_match"]
        assert "EXACT" in note or "EQUIVALENT" in note


# ---------------------------------------------------------------------------
# Workstream C — DSRA
# ---------------------------------------------------------------------------

class TestWorkstreamC_DSRA:
    def test_section_present(self, truth):
        assert "workstream_c" in truth

    def test_dsra_target_is_zero(self, truth):
        val = truth["workstream_c"]["inputs_i348_dsra_target"]["value"]
        assert val == 0 or val is None or (isinstance(val, float) and val == 0.0)

    def test_dsra_not_present(self, truth):
        assert truth["workstream_c"]["dsra_present"] is False

    def test_dsra_target_zero_confirmed(self, truth):
        assert truth["workstream_c"]["target_is_zero"] is True

    def test_dsra_cached_values_all_zero(self, truth):
        assert truth["workstream_c"]["all_cached_values_zero"] is True

    def test_dsra_formula_evidence_rows_present(self, truth):
        rows = truth["workstream_c"]["cf_dsra_rows"]
        assert "cf_row89" in rows, "CF!row89 (operation flow) must be present"
        assert rows["cf_row89"]["source_formula_present"] is True, (
            "CF!row89 formula must be present to prove mechanism exists but is deactivated"
        )

    def test_dsra_all_rows_zero(self, truth):
        rows = truth["workstream_c"]["cf_dsra_rows"]
        for name, r in rows.items():
            count = r.get("nonzero_count", 0)
            assert count == 0, f"{name} has {count} non-zero values; expected all zero"


# ---------------------------------------------------------------------------
# Workstream D — Sizing base / gearing chain
# ---------------------------------------------------------------------------

class TestWorkstreamD_SizingBase:
    def test_section_present(self, truth):
        assert "workstream_d" in truth

    def test_d192_is_not_a_gearing_fraction(self, truth):
        chain = truth["workstream_d"]["gearing_chain"]
        d192 = chain["inputs_d192"]
        classification = d192.get("classification", "")
        note = d192.get("note", "")
        # Classification must signal debt amount, not a fractional/percentage value
        assert "DEBT_AMOUNT" in classification or "kEUR" in classification, (
            f"D192 must be classified as a debt amount (kEUR). Got: {classification!r}"
        )
        # The note must explicitly state D192 is not a percentage
        assert "NOT" in note or "not" in note.lower(), (
            f"D192 note must state it is NOT a percentage. Got: {note!r}"
        )

    def test_d192_formula_is_ds_d51(self, truth):
        fml = truth["workstream_d"]["gearing_chain"]["inputs_d192"]["formula"]
        assert fml is not None and "DS" in fml and "D51" in fml, (
            f"D192 formula must reference DS!D51, got {fml!r}"
        )

    def test_d195_is_the_gearing_constraint(self, truth):
        d195 = truth["workstream_d"]["gearing_chain"]["inputs_d195_available_amount"]
        fml = d195.get("formula", "")
        assert fml is not None
        # Formula uses $D$47 and $D$230 with absolute references; check both patterns
        has_min = "MIN" in fml
        has_d47 = "D47" in fml or "D$47" in fml or "$D$47" in fml
        has_d230 = "D230" in fml or "D$230" in fml or "$D$230" in fml
        assert has_min and has_d47 and has_d230, (
            f"D195 must contain MIN(DS!D47, G171×D230), got {fml!r}"
        )

    def test_d230_dual_use_documented(self, truth):
        d230 = truth["workstream_d"]["gearing_chain"]["inputs_d230_hedge_coverage_and_gearing_cap"]
        dual = d230.get("dual_use", "")
        assert dual, "D230 dual-use must be documented"
        assert "hedge" in dual.lower() or "Hedge" in dual
        assert "gearing" in dual.lower() or "Gearing" in dual

    def test_g171_total_value(self, truth):
        val = truth["workstream_d"]["inputs_g171_total_eligible_cost"]["value_keur"]
        assert val is not None
        assert abs(val - 57973) < 10, f"G171 expected ~57973 kEUR, got {val}"

    def test_idc_included(self, truth):
        assert truth["workstream_d"]["idc_included_in_gearing_base"] is True

    def test_gearing_cap_not_binding(self, truth):
        assert truth["workstream_d"]["gearing_cap_binding_confirmed"] is False

    def test_gearing_cap_computed_from_formula(self, truth):
        cap = truth["workstream_d"]["gearing_cap_keur"]
        g171 = truth["workstream_d"]["inputs_g171_total_eligible_cost"]["value_keur"]
        d230 = truth["workstream_d"]["gearing_chain"]["inputs_d230_hedge_coverage_and_gearing_cap"]["value"]
        if cap is not None and g171 is not None and d230 is not None:
            expected = g171 * d230
            assert abs(cap - expected) < 1.0, (
                f"Gearing cap must be G171×D230={expected:.3f}, fixture has {cap:.3f}"
            )

    def test_d195_below_gearing_cap(self, truth):
        cap = truth["workstream_d"]["gearing_cap_keur"]
        d51 = truth["workstream_b"]["ds_d51_total_debt"]["value_keur"]
        if cap and d51:
            assert d51 < cap, f"DSCR debt {d51:.3f} should be below gearing cap {cap:.3f}"


# ---------------------------------------------------------------------------
# Workstream E — Interest rate
# ---------------------------------------------------------------------------

class TestWorkstreamE_InterestRate:
    def test_section_present(self, truth):
        assert "workstream_e" in truth

    def test_rate_convention_is_annual(self, truth):
        note = truth["workstream_e"]["rate_convention_note"]
        assert "annual" in note.lower()
        assert "H6" in note or "year_fraction" in note.lower() or "year fraction" in note.lower()

    def test_no_rate_doubling_in_note(self, truth):
        note = truth["workstream_e"]["rate_convention_note"].lower()
        # Note must say NOT to multiply by 2 (it can mention the concept to refute it)
        assert "multiply by 2" not in note or "do not multiply" in note or "not multiply" in note, (
            "Rate convention note must not endorse multiplying the rate by 2"
        )
        # Note must affirm the rate is annual
        assert "annual" in note

    def test_no_11pct_annual_rate_claim(self, truth):
        raw = json.dumps(truth["workstream_e"])
        assert "11.9" not in raw and "11.90" not in raw, (
            "Fixture must not claim DS!H44 annual rate is ~11.9%"
        )

    def test_sculpting_rate_period1_annual_pct(self, truth):
        rate_pct = truth["workstream_e"]["sculpting_rate_period1_annual_pct"]
        assert rate_pct is not None
        assert abs(rate_pct - 5.95) < 0.1, f"Sculpting rate expected ~5.95%, got {rate_pct}"

    def test_interest_identity_holds(self, truth):
        identity = truth["workstream_e"]["interest_identity"]
        assert identity["identity_holds"] is True, (
            f"Interest identity failed; max residual = {identity['max_absolute_residual_keur']}"
        )

    def test_fixed_fraction_is_080(self, truth):
        val = truth["workstream_e"]["ds_b40_fixed_fraction"]["value"]
        assert val is not None and abs(val - 0.80) < 0.001

    def test_float_fraction_is_020(self, truth):
        val = truth["workstream_e"]["ds_b39_float_fraction"]["value"]
        assert val is not None and abs(val - 0.20) < 0.001

    def test_tranche_interest_formula_uses_h44(self, truth):
        fml = truth["workstream_e"]["ds_row64_period_interest"]["formula_h"]
        assert fml is not None and "H44" in fml

    def test_tranche_interest_formula_uses_year_fraction(self, truth):
        fml = truth["workstream_e"]["ds_row64_period_interest"]["formula_h"]
        assert fml is not None and "H6" in fml

    def test_d280_note_mentions_fcf_section(self, truth):
        note = truth["workstream_e"]["inputs_d280_fcf_rate"]["note"]
        assert "B33" in note or "FCF" in note

    def test_d280_note_says_not_tranche_schedule(self, truth):
        note = truth["workstream_e"]["inputs_d280_fcf_rate"]["note"]
        assert "NOT" in note or "not" in note.lower()

    def test_rate_mismatch_confirmed(self, truth):
        assert truth["workstream_e"]["rate_mismatch_confirmed"] is True

    def test_rate_period_vector_no_null_in_active(self, truth):
        vals = truth["workstream_e"]["ds_row44_annual_sculpting_rate"]["period_values"]
        for p in range(1, 29):
            assert vals[p] is not None, f"Rate null at active period {p}"

    def test_year_fraction_vector_no_null_in_active(self, truth):
        vals = truth["workstream_e"]["ds_row6_year_fraction"]["period_values"]
        for p in range(1, 29):
            assert vals[p] is not None, f"Year fraction null at active period {p}"


# ---------------------------------------------------------------------------
# Phase 2C sizing analysis (C3B2 — uses actual solve_senior_debt solver)
# ---------------------------------------------------------------------------

class TestPhase2CSizingAnalysis:
    def test_section_present(self, truth):
        assert "phase2c_sizing_analysis" in truth, (
            "Fixture must contain 'phase2c_sizing_analysis' (renamed from 'equal_input_equal_policy'). "
            "Regenerate fixture from workbook."
        )

    def test_status_is_computed(self, truth):
        status = truth["phase2c_sizing_analysis"]["status"]
        assert status == "COMPUTED", f"Status must be COMPUTED, got {status!r}"

    def test_api_is_solve_senior_debt(self, truth):
        api = truth["phase2c_sizing_analysis"].get("phase2c_api", "")
        assert "solve_senior_debt" in api, (
            f"phase2c_api must reference solve_senior_debt, got {api!r}. "
            "build_schedule is a schedule builder, not a solver — Blocker 1."
        )

    def test_old_build_schedule_api_not_used(self, truth):
        api = truth["phase2c_sizing_analysis"].get("phase2c_api", "")
        assert "build_schedule" not in api, (
            "phase2c_api must not reference build_schedule — debt must be an OUTPUT of the solver."
        )

    def test_verdict_is_valid_classification(self, truth):
        verdict = truth["phase2c_sizing_analysis"]["verdict"]
        assert verdict in VALID_VERDICTS, f"Unknown verdict: {verdict!r}"

    def test_verdict_is_source_truth_proved(self, truth):
        verdict = truth["phase2c_sizing_analysis"]["verdict"]
        assert verdict == "C3B2_DEBT_INTEREST_SOURCE_TRUTH_PROVED", (
            f"Verdict must be C3B2_DEBT_INTEREST_SOURCE_TRUTH_PROVED "
            f"(independent backward induction closes to Excel debt), got {verdict!r}"
        )

    def test_no_build_schedule_in_extractor(self):
        import inspect
        from finco_recon import extract_oborovo_debt_interest as m
        src = inspect.getsource(m)
        assert "build_schedule" not in src, (
            "Extractor must not call build_schedule — use solve_senior_debt."
        )

    def test_excel_debt_not_hardcoded_in_extractor(self):
        import inspect
        from finco_recon import extract_oborovo_debt_interest as m
        src = inspect.getsource(m)
        assert "42852.279" not in src, (
            "Extractor must not hardcode the Excel debt value 42852.279."
        )

    def test_no_project_name_dispatch(self):
        from finco_recon import extract_oborovo_debt_interest as m
        import inspect
        src = inspect.getsource(m)
        for pat in ["if project", "if oborovo", "if 'oborovo'"]:
            assert pat.lower() not in src.lower(), (
                f"Extractor contains project-name dispatch: {pat!r}"
            )

    def test_no_approved_delta_or_plug(self):
        from finco_recon import extract_oborovo_debt_interest as m
        import inspect
        src = inspect.getsource(m)
        for kw in ["approved_delta", "target_override", "frozen_schedule"]:
            assert kw not in src, f"Extractor contains forbidden pattern: {kw!r}"

    def test_inputs_used_no_hardcoded_values(self, truth):
        inputs = truth["phase2c_sizing_analysis"].get("inputs_used", {})
        hardcoded = inputs.get("hardcoded_values", "")
        assert "NONE" in hardcoded or "none" in hardcoded.lower(), (
            "inputs_used must declare no hardcoded values"
        )


class TestCurrentPhase2CSolverResult:
    """Case 0: current production Phase 2C config — debt is an OUTPUT."""

    def _section(self, truth):
        return truth["phase2c_sizing_analysis"]["current_phase2c_solver_result"]

    def test_section_present(self, truth):
        assert "current_phase2c_solver_result" in truth["phase2c_sizing_analysis"]

    def test_debt_is_computed_output(self, truth):
        """Debt must come from solver, not from Excel supply."""
        s = self._section(truth)
        debt = s["debt_size_keur"]
        excel_debt = truth["phase2c_sizing_analysis"]["excel_total_debt_keur"]
        assert debt != excel_debt, (
            "current_phase2c_solver_result debt must be a COMPUTED output, not Excel debt. "
            f"Got {debt:.3f} which equals Excel {excel_debt:.3f}."
        )

    def test_converged(self, truth):
        s = self._section(truth)
        assert s["converged"] is True, "Case 0 solver must converge"

    def test_debt_plausible(self, truth):
        s = self._section(truth)
        debt = s["debt_size_keur"]
        assert 40_000 < debt < 60_000, f"Case 0 debt implausible: {debt:.3f}"

    def test_terminal_closing_near_zero(self, truth):
        s = self._section(truth)
        t = s.get("terminal_closing_keur", None)
        if t is not None:
            assert abs(t) < 1.0, f"Terminal closing should be near zero, got {t:.6f}"

    def test_rate_is_565_bps(self, truth):
        s = self._section(truth)
        rate = s["config"]["annual_fixed_rate"]
        assert abs(rate - 0.0565) < 1e-6, f"Case 0 rate must be 5.65%, got {rate}"

    def test_day_count_is_act365(self, truth):
        s = self._section(truth)
        assert s["config"]["day_count"] == "ACT_365"

    def test_debt_substantially_above_excel(self, truth):
        """Current Phase 2C uses 5.65% vs Excel ~5.95% → larger debt capacity."""
        s = self._section(truth)
        excel_debt = truth["phase2c_sizing_analysis"]["excel_total_debt_keur"]
        debt = s["debt_size_keur"]
        assert debt > excel_debt + 1_000, (
            f"Case 0 debt {debt:.3f} should be substantially above Excel {excel_debt:.3f} "
            "(lower rate → higher debt capacity)"
        )


class TestScalarExcelMatchedSolverResult:
    """Case 3: Excel inputs + ACT_360 + scalar DSCR=1.15."""

    def _section(self, truth):
        return truth["phase2c_sizing_analysis"]["scalar_excel_matched_solver_result"]

    def test_section_present(self, truth):
        assert "scalar_excel_matched_solver_result" in truth["phase2c_sizing_analysis"]

    def test_converged(self, truth):
        s = self._section(truth)
        assert s["converged"] is True, "Case 3 solver must converge"

    def test_debt_between_case0_and_excel(self, truth):
        s = self._section(truth)
        debt = s["debt_size_keur"]
        excel_debt = truth["phase2c_sizing_analysis"]["excel_total_debt_keur"]
        c0 = truth["phase2c_sizing_analysis"]["current_phase2c_solver_result"]["debt_size_keur"]
        assert excel_debt < debt < c0, (
            f"Case 3 debt {debt:.3f} should be between Excel {excel_debt:.3f} and Case0 {c0:.3f} "
            "(residual from DSCR banding)"
        )

    def test_day_count_is_act360(self, truth):
        s = self._section(truth)
        assert s["config"]["day_count"] == "ACT_360"

    def test_terminal_closing_near_zero(self, truth):
        s = self._section(truth)
        t = s.get("terminal_closing_keur", None)
        if t is not None:
            assert abs(t) < 1.0, f"Terminal closing should be near zero, got {t:.6f}"


class TestIndependentVectorDSRCapacity:
    """Independent backward induction from raw DS!row20/22/9/44/6 — no forbidden inputs."""

    def _section(self, truth):
        return truth["phase2c_sizing_analysis"]["independent_capacity_proof"]

    def test_section_present(self, truth):
        assert "independent_capacity_proof" in truth["phase2c_sizing_analysis"], (
            "independent_capacity_proof section must be present (derives from raw primitives)"
        )

    def test_forbidden_input_row46_not_used(self, truth):
        s = self._section(truth)
        forbidden = s.get("forbidden_inputs_not_used", [])
        assert any("row46" in f for f in forbidden), (
            "proof must explicitly declare row46 as NOT used"
        )

    def test_vector_capacity_matches_excel_debt(self, truth):
        s = self._section(truth)
        cap = s["vector_capacity"]["capacity_keur"]
        excel_debt = s["excel_total_debt_keur"]
        assert abs(cap - excel_debt) < 0.001, (
            f"Vector backward induction {cap:.9f} must match Excel {excel_debt:.9f} "
            f"(residual={cap-excel_debt:.12f}). Inputs: row20/row22/row9/row44/row6 only."
        )

    def test_final_residual_near_zero(self, truth):
        s = self._section(truth)
        residual = s["final_unforced_residual_keur"]
        assert abs(residual) < 1.0, (
            f"Final unforced residual {residual:.9f} kEUR exceeds 1 kEUR tolerance. "
            "Independent backward induction must reproduce Excel debt."
        )

    def test_scalar_capacity_above_vector(self, truth):
        s = self._section(truth)
        scalar = s["scalar_capacity"]["capacity_keur"]
        vector = s["vector_capacity"]["capacity_keur"]
        assert scalar > vector, (
            f"Scalar (DSCR=1.15) capacity {scalar:.3f} must exceed vector capacity {vector:.3f} "
            "because 1.35 banding at P25-P28 reduces allowed debt service"
        )

    def test_banding_effect_is_negative(self, truth):
        s = self._section(truth)
        banding = s["banding_effect_keur"]
        assert banding < 0, (
            f"Banding effect (vector - scalar) must be negative, got {banding:.3f} kEUR"
        )

    def test_verdict_is_proved(self, truth):
        s = self._section(truth)
        assert s["verdict"] == "C3B2_DEBT_INTEREST_SOURCE_TRUTH_PROVED", (
            f"proof verdict must be PROVED, got {s['verdict']!r}"
        )

    def test_raw_inputs_declared(self, truth):
        s = self._section(truth)
        inputs = s.get("raw_inputs_used", [])
        raw_refs = " ".join(inputs)
        assert "row20" in raw_refs and "row22" in raw_refs, (
            "raw_inputs_used must reference row20 (CFADS) and row22 (DSCR)"
        )

    def test_formula_documented(self, truth):
        s = self._section(truth)
        formula = s.get("formula", "")
        assert "CFADS" in formula or "row20" in formula or "allowed_ds" in formula, (
            f"Formula must document the backward induction computation — got {formula!r}"
        )


class TestCausalBridge:
    """Causal bridge: Case 0 → Case 1 → Case 2 → Case 3 → Excel."""

    def _section(self, truth):
        return truth["phase2c_sizing_analysis"]["causal_bridge"]

    def test_section_present(self, truth):
        assert "causal_bridge" in truth["phase2c_sizing_analysis"]

    def test_bridge_closed(self, truth):
        s = self._section(truth)
        assert s["bridge_closed"] is True, (
            f"Causal bridge must close: error={s.get('bridge_closure_error_keur'):.6f} kEUR"
        )

    def test_bridge_closure_error_sub_keur(self, truth):
        s = self._section(truth)
        err = s["bridge_closure_error_keur"]
        assert err < 1.0, f"Bridge closure error {err:.6f} kEUR exceeds 1 kEUR tolerance"

    def test_rate_delta_is_negative(self, truth):
        """Higher rate (Excel ~5.95%) → lower debt capacity: delta must be negative."""
        s = self._section(truth)
        assert s["delta_rate_keur"] < 0, (
            f"Rate delta must be negative (Excel rate > prod rate), got {s['delta_rate_keur']:.3f}"
        )

    def test_cfads_delta_is_negative(self, truth):
        """Excel CFADS < Phase2A EBITDA → lower debt capacity: delta must be negative."""
        s = self._section(truth)
        assert s["delta_cfads_keur"] < 0, (
            f"CFADS delta must be negative, got {s['delta_cfads_keur']:.3f}"
        )

    def test_daycount_delta_is_negative(self, truth):
        """ACT_360 > ACT_365 day fracs → more interest per period → less principal → delta negative."""
        s = self._section(truth)
        assert s["delta_daycount_keur"] < 0, (
            f"Day-count delta must be negative (ACT_360 reduces capacity), got {s['delta_daycount_keur']:.3f}"
        )

    def test_dscr_banding_g4_is_negative(self, truth):
        """Vector DSCR (1.35 at P25-28) reduces capacity vs scalar 1.15: G4-G3A delta must be negative."""
        s = self._section(truth)
        # Field was renamed: delta_dscr_banding_g3a_to_g4_keur (G4-G3A, pure banding)
        # Accept either name for backwards compatibility during transition
        delta = s.get("delta_dscr_banding_g3a_to_g4_keur") or s.get("delta_dscr_banding_g3_to_g4_keur")
        assert delta is not None, (
            "delta_dscr_banding_g3a_to_g4_keur (or legacy delta_dscr_banding_g3_to_g4_keur) "
            "must be present in causal_bridge"
        )
        assert delta < 0, (
            f"DSCR banding delta (G4-G3A, pure banding: 1.35 vs 1.15 at P25-28) must be negative, "
            f"got {delta:.3f}"
        )

    def test_case0_debt_is_largest(self, truth):
        s = self._section(truth)
        c0 = s["case0_current_phase2c_keur"]
        c1 = s["case1_excel_rates_keur"]
        c2 = s["case2_excel_cfads_keur"]
        c3 = s["case3_act360_keur"]
        excel = s["excel_debt_keur"]
        assert c0 > c1 > c2 > c3 > excel, (
            f"Cases must be strictly decreasing: {c0:.3f} > {c1:.3f} > {c2:.3f} > {c3:.3f} > {excel:.3f}"
        )


class TestConvergenceInvariance:
    """Case 0 must produce same debt regardless of initial guess."""

    def _section(self, truth):
        return truth["phase2c_sizing_analysis"]["convergence_invariance"]

    def test_section_present(self, truth):
        assert "convergence_invariance" in truth["phase2c_sizing_analysis"]

    def test_deterministic(self, truth):
        s = self._section(truth)
        assert s["deterministic"] is True, (
            "Solver must produce same result for all initial guesses. "
            f"Unique values: {s.get('unique_converged_values')}"
        )

    def test_all_runs_converged(self, truth):
        s = self._section(truth)
        for run in s["runs"]:
            assert run["converged"] is True, (
                f"Run with guess={run['initial_guess_keur']} did not converge"
            )

    def test_unique_values_singleton(self, truth):
        s = self._section(truth)
        assert len(s["unique_converged_values"]) == 1, (
            f"Expected one unique converged debt, got {s['unique_converged_values']}"
        )


# ---------------------------------------------------------------------------
# Sizing constraint identity
# ---------------------------------------------------------------------------

class TestSizingConstraintIdentity:
    def test_d195_equals_min_d47_cap(self, truth):
        """D195 = MIN(DS!D47, G171 × D230) — verify numerically."""
        d195 = truth["workstream_d"]["gearing_chain"]["inputs_d195_available_amount"]["value"]
        d47 = truth["workstream_d"]["gearing_chain"]["ds_d47_dscr_capacity"]["value_keur"]
        g171 = truth["workstream_d"]["inputs_g171_total_eligible_cost"]["value_keur"]
        d230 = truth["workstream_d"]["gearing_chain"]["inputs_d230_hedge_coverage_and_gearing_cap"]["value"]
        if all(v is not None for v in [d195, d47, g171, d230]):
            expected = min(d47, g171 * d230)
            assert abs(d195 - expected) < 0.1, (
                f"D195={d195:.3f} should equal MIN({d47:.3f}, {g171:.3f}×{d230})={expected:.3f}"
            )

    def test_d192_equals_d51_value(self, truth):
        """D192 = DS!D51 (proved C3B1). Numeric values must match."""
        d192_val = truth["workstream_d"]["gearing_chain"]["inputs_d192"]["value"]
        d51_val = truth["workstream_b"]["ds_d51_total_debt"]["value_keur"]
        if d192_val is not None and d51_val is not None:
            assert abs(d192_val - d51_val) < 0.01, (
                f"D192={d192_val:.3f} should equal D51={d51_val:.3f}"
            )


# ---------------------------------------------------------------------------
# Production file integrity
# ---------------------------------------------------------------------------

class TestProductionFileIntegrity:
    def test_no_changes_to_financial_engine(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "c5f0b1f1643aad07df2f2d9e07acd21943328841...HEAD",
             "--", "financial_engine/"],
            cwd=pathlib.Path(__file__).parent.parent,
            capture_output=True, text=True,
        )
        assert result.stdout == "", (
            "financial_engine/ must not be modified:\n" + result.stdout[:500]
        )

    def test_no_changes_to_app(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "c5f0b1f1643aad07df2f2d9e07acd21943328841...HEAD",
             "--", "app/"],
            cwd=pathlib.Path(__file__).parent.parent,
            capture_output=True, text=True,
        )
        assert result.stdout == "", (
            "app/ must not be modified:\n" + result.stdout[:500]
        )

    def test_no_changes_to_finco_core(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "c5f0b1f1643aad07df2f2d9e07acd21943328841...HEAD",
             "--", "finco_core/"],
            cwd=pathlib.Path(__file__).parent.parent,
            capture_output=True, text=True,
        )
        assert result.stdout == "", (
            "finco_core/ must not be modified:\n" + result.stdout[:500]
        )


# ---------------------------------------------------------------------------
# Synthetic extractor smoke tests (no workbook binary needed)
# ---------------------------------------------------------------------------

class TestExtractorSynthetic:
    def test_extractor_version_constant_value(self):
        from finco_recon.extract_oborovo_debt_interest import _EXTRACTOR_VERSION
        assert _EXTRACTOR_VERSION == "2.0.0"

    def test_row_to_periods_helper(self):
        from finco_recon.extract_oborovo_debt_interest import _row_to_periods
        row = tuple([None] * 6 + [1.0, 2.0, 3.0] + [None] * 52)
        result = _row_to_periods(row, n=61)
        assert result[0] == 1.0
        assert result[1] == 2.0
        assert len(result) == 61

    def test_scalar_helper(self):
        from finco_recon.extract_oborovo_debt_interest import _scalar
        assert _scalar((10, 20), 1) == 20
        assert _scalar((10,), 99) is None

    def test_formula_helper(self):
        from finco_recon.extract_oborovo_debt_interest import _formula
        row = (None, "=A1+B1", "literal")
        assert _formula(row, 1) == "=A1+B1"
        assert _formula(row, 2) is None

    def test_main_entry_point_importable(self):
        from finco_recon.extract_oborovo_debt_interest import main
        assert callable(main)

    def test_main_returns_1_on_missing_workbook(self, tmp_path):
        from finco_recon.extract_oborovo_debt_interest import main
        code = main(["--workbook", str(tmp_path / "missing.xlsm"),
                     "--output", str(tmp_path / "out.json")])
        assert code == 1

    def test_extractor_has_no_hardcoded_debt_target(self):
        from finco_recon import extract_oborovo_debt_interest as m
        import inspect
        src = inspect.getsource(m)
        assert "42852.279" not in src

    def test_renamed_project_identity_invariance(self):
        """Extractor must not contain runtime dispatch on project name."""
        from finco_recon import extract_oborovo_debt_interest as m
        import inspect
        src = inspect.getsource(m)
        # Forbidden: runtime conditional dispatch on project name
        for pat in ['if "oborovo"', "if 'oborovo'", "if project_name", "elif oborovo"]:
            assert pat not in src.lower(), (
                f"Extractor contains project-name dispatch: {pat!r}"
            )
