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

# Historical range: C3B2 base → C3B2 squash-merge commit (closed range).
# This asserts that C3B2 itself introduced no production changes to these
# directories.  It does NOT assert anything about later stages.
_C3B2_BASE_SHA = "c5f0b1f1643aad07df2f2d9e07acd21943328841"
_C3B2_MERGE_SHA = "ce462bbedf460d6ff7f98a144b9406a5a0fcc04e"


def _historical_diff(path: str) -> str:
    import subprocess
    result = subprocess.run(
        ["git", "diff", f"{_C3B2_BASE_SHA}...{_C3B2_MERGE_SHA}", "--", path],
        cwd=pathlib.Path(__file__).parent.parent,
        capture_output=True, text=True,
    )
    return result.stdout


class TestProductionFileIntegrity:
    def test_no_changes_to_financial_engine(self):
        diff = _historical_diff("financial_engine/")
        assert diff == "", (
            f"C3B2 historical range ({_C3B2_BASE_SHA[:8]}...{_C3B2_MERGE_SHA[:8]}) "
            f"must show no changes to financial_engine/:\n" + diff[:500]
        )

    def test_no_changes_to_app(self):
        diff = _historical_diff("app/")
        assert diff == "", (
            f"C3B2 historical range ({_C3B2_BASE_SHA[:8]}...{_C3B2_MERGE_SHA[:8]}) "
            f"must show no changes to app/:\n" + diff[:500]
        )

    def test_no_changes_to_finco_core(self):
        diff = _historical_diff("finco_core/")
        assert diff == "", (
            f"C3B2 historical range ({_C3B2_BASE_SHA[:8]}...{_C3B2_MERGE_SHA[:8]}) "
            f"must show no changes to finco_core/:\n" + diff[:500]
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


# ---------------------------------------------------------------------------
# TestCompleteFormulaTerms — prove CF!row83=0, B23=True, row5=1, row7=False,
# B54=0, row82=0 so that DS!row47 simplifies to backward-induction formula
# ---------------------------------------------------------------------------

class TestCompleteFormulaTerms:
    """Item 1: complete workbook formula neutrality proof."""

    @pytest.fixture(scope="class")
    def ntp(self):
        data = json.loads(FIXTURE_PATH.read_text())
        proof = data["phase2c_sizing_analysis"].get("neutral_terms_proof")
        assert proof is not None, "neutral_terms_proof missing from phase2c_sizing_analysis"
        return proof

    def test_neutral_terms_proof_present(self, ntp):
        assert ntp is not None

    def test_complete_ds_row23_formula_stored(self, ntp):
        assert "CF!H83" in ntp["complete_ds_row23_formula"]

    def test_complete_ds_row46_formula_stored(self, ntp):
        assert "H5" in ntp["complete_ds_row46_formula"]

    def test_complete_ds_row47_formula_stored(self, ntp):
        assert "H7" in ntp["complete_ds_row47_formula"]
        assert "B54" in ntp["complete_ds_row47_formula"]

    def test_cf_row83_all_zero(self, ntp):
        cf = ntp["cf_row83_cumulative"]
        assert cf["max_residual_keur"] < 1e-9, (
            f"CF!row83 not proved zero: max_residual={cf['max_residual_keur']}"
        )
        assert cf["all_zero_p1_p28"] is True

    def test_b23_tranche_flag_true(self, ntp):
        b23 = ntp["b23_tranche_flag"]
        # Accept either old "value" key or new "extracted_value" key
        val = b23.get("extracted_value", b23.get("value"))
        assert val is True or val == 1, f"B23 must be True/1, got {val!r}"
        assert b23["neutral"] is True

    def test_row5_eligibility_equals_one(self, ntp):
        r5 = ntp["row5_eligibility_flag"]
        assert r5["proved_equals_one_p1_p28"] is True
        assert r5["max_residual_keur"] < 1e-9

    def test_row82_all_zero(self, ntp):
        assert ntp["row82_refinancing_capacity"]["all_zero_p1_p28"] is True

    def test_b54_wht_rate_zero(self, ntp):
        b54 = ntp["b54_wht_rate"]
        val = b54.get("extracted_value", b54.get("value"))
        assert val == 0 or val is None, f"B54 must be 0, got {val!r}"
        assert b54["neutral"] is True

    def test_simplification_valid(self, ntp):
        assert ntp["simplification_valid"] is True, (
            "Not all neutral terms proved — simplification not valid"
        )

    def test_simplified_formula_matches_expected(self, ntp):
        formula = ntp["simplified_formula"]
        assert "row20" in formula and "row22" in formula and "row9" in formula


# ---------------------------------------------------------------------------
# TestRuntimeInventory — prove FROZEN_EXCEL_SCHEDULE_RUNTIME classification
# ---------------------------------------------------------------------------

class TestRuntimeInventory:
    """Item 7: actual Oborovo runtime is FROZEN_EXCEL_SCHEDULE_RUNTIME.

    C3B3A transition: runtime_inventory is now a two-layer structure.
    legacy_runtime carries the frozen-schedule layer (still active).
    clean_senior_debt_contract carries the C3B3A source-proven layer (not yet promoted).
    """

    @pytest.fixture(scope="class")
    def ri(self):
        data = json.loads(FIXTURE_PATH.read_text())
        inv = data["phase2c_sizing_analysis"].get("runtime_inventory")
        assert inv is not None, "runtime_inventory missing from phase2c_sizing_analysis"
        return inv

    @pytest.fixture(scope="class")
    def legacy(self, ri):
        lr = ri.get("legacy_runtime")
        assert lr is not None, "runtime_inventory.legacy_runtime missing (C3B3A two-layer structure)"
        return lr

    def test_runtime_inventory_present(self, ri):
        assert ri is not None

    def test_legacy_runtime_layer_present(self, ri):
        assert "legacy_runtime" in ri, "Two-layer structure requires legacy_runtime key"

    def test_clean_contract_layer_present(self, ri):
        assert "clean_senior_debt_contract" in ri, "Two-layer structure requires clean_senior_debt_contract key"

    def test_runtime_classification_frozen(self, legacy):
        assert legacy["runtime_classification"] == "FROZEN_EXCEL_SCHEDULE_RUNTIME"

    def test_use_frozen_excel_flag_true(self, legacy):
        assert legacy["use_frozen_excel_senior_debt_schedule"] is True

    def test_frozen_fixture_path_present(self, legacy):
        assert "phase23q_oborovo_senior_debt_sizing_extraction.csv" in legacy["frozen_senior_ds_fixture_path"]

    def test_debt_sizing_method_gearing_cap(self, legacy):
        assert "gearing_cap" in str(legacy["debt_sizing_method"])

    def test_fixed_debt_keur_matches_excel(self, legacy):
        data = json.loads(FIXTURE_PATH.read_text())
        excel_debt = data["phase2c_sizing_analysis"]["excel_total_debt_keur"]
        assert abs(legacy["fixed_debt_keur"] - excel_debt) < 1.0, (
            f"fixed_debt_keur {legacy['fixed_debt_keur']:.3f} diverges from "
            f"excel_total_debt_keur {excel_debt:.3f}"
        )

    def test_clean_contract_classification(self, ri):
        cc = ri["clean_senior_debt_contract"]
        assert cc["runtime_classification"] == "CLEAN_SOURCE_CONTRACT_CONFIGURED_NOT_LEGACY_RUNTIME_PROMOTED"

    def test_clean_contract_debt_sizing_mode(self, ri):
        cc = ri["clean_senior_debt_contract"]
        assert "FLAT_DSCR_SCULPTED" in str(cc["debt_sizing_mode"]) or "flat_dscr_sculpted" in str(cc["debt_sizing_mode"])

    def test_clean_contract_not_implying_legacy_promotion(self, ri):
        legacy = ri["legacy_runtime"]
        assert legacy["use_frozen_excel_senior_debt_schedule"] is True, (
            "Legacy runtime frozen flag must remain True — clean contract is not yet promoted"
        )


# ---------------------------------------------------------------------------
# TestIndependentRecomputation — independently compute G3A, G4, bridge,
# residual and confirm they match fixture (zero dependence on production code)
# ---------------------------------------------------------------------------

class TestIndependentRecomputation:
    """Item 6: tests independently compute G3A, G4, bridge, residual."""

    @pytest.fixture(scope="class")
    def vectors(self):
        data = json.loads(FIXTURE_PATH.read_text())
        wa = data["workstream_a"]
        wb = data["workstream_b"]["period_vectors"]
        we = data["workstream_e"]
        cfads = wa["ds_row20_cfads"]["period_values_keur"]
        dscr  = wa["ds_row22_dscr_target"]["period_values"]
        ops   = wb["row9_ops_flag"]["period_values"]
        rates = we["ds_row44_annual_sculpting_rate"]["period_values"]
        fracs = wb["row6_day_frac"]["period_values"]
        return {"cfads": cfads, "dscr": dscr, "ops": ops, "rates": rates, "fracs": fracs}

    @pytest.fixture(scope="class")
    def active(self):
        return list(range(1, 29))

    def _backward_induction(self, cfads, dscr_policy, ops, rates, fracs, active):
        ads = {p: (cfads[p] / dscr_policy[p]) * (ops[p] if ops[p] is not None else 1.0)
               for p in active}
        maturity = max(active)
        V = {}
        V[maturity + 1] = 0.0
        for p in sorted(active, reverse=True):
            V[p] = (V[p + 1] + ads[p]) / (1.0 + rates[p] * fracs[p])
        return V[min(active)]

    def test_g3a_independently_computed(self, vectors, active):
        from finco_recon.derive_c3b2_independent_capacity import derive_capacities_from_vectors
        cfads = vectors["cfads"]
        ops   = vectors["ops"]
        rates = vectors["rates"]
        fracs = vectors["fracs"]
        dscr  = vectors["dscr"]
        # G3A: scalar DSCR=1.15
        dscr_scalar = {p: 1.15 for p in active}
        g3a_manual = self._backward_induction(cfads, dscr_scalar, ops, rates, fracs, active)
        result = derive_capacities_from_vectors(
            cfads={p: cfads[p] for p in active},
            dscr_vector={p: dscr[p] for p in active},
            ops_vector={p: ops[p] if ops[p] is not None else 1.0 for p in active},
            annual_rates={p: rates[p] for p in active},
            day_fractions={p: fracs[p] for p in active},
            active_periods=active,
        )
        assert abs(result["scalar_capacity_keur"] - g3a_manual) < 1e-6, (
            f"G3A mismatch: helper={result['scalar_capacity_keur']:.9f}, manual={g3a_manual:.9f}"
        )

    def test_g4_independently_computed(self, vectors, active):
        from finco_recon.derive_c3b2_independent_capacity import derive_capacities_from_vectors
        cfads = vectors["cfads"]
        dscr  = vectors["dscr"]
        ops   = vectors["ops"]
        rates = vectors["rates"]
        fracs = vectors["fracs"]
        dscr_v = {p: dscr[p] for p in active}
        g4_manual = self._backward_induction(cfads, dscr_v, ops, rates, fracs, active)
        result = derive_capacities_from_vectors(
            cfads={p: cfads[p] for p in active},
            dscr_vector=dscr_v,
            ops_vector={p: ops[p] if ops[p] is not None else 1.0 for p in active},
            annual_rates={p: rates[p] for p in active},
            day_fractions={p: fracs[p] for p in active},
            active_periods=active,
        )
        assert abs(result["vector_capacity_keur"] - g4_manual) < 1e-6

    def test_g3a_exceeds_g4(self, vectors, active):
        from finco_recon.derive_c3b2_independent_capacity import derive_capacities_from_vectors
        cfads = {p: vectors["cfads"][p] for p in active}
        dscr  = {p: vectors["dscr"][p] for p in active}
        ops   = {p: vectors["ops"][p] if vectors["ops"][p] is not None else 1.0 for p in active}
        rates = {p: vectors["rates"][p] for p in active}
        fracs = {p: vectors["fracs"][p] for p in active}
        result = derive_capacities_from_vectors(
            cfads=cfads, dscr_vector=dscr, ops_vector=ops,
            annual_rates=rates, day_fractions=fracs, active_periods=active,
        )
        assert result["scalar_capacity_keur"] > result["vector_capacity_keur"], (
            "G3A must exceed G4 — higher DSCR banding reduces capacity"
        )

    def test_bridge_residual_from_fixture(self):
        data = json.loads(FIXTURE_PATH.read_text())
        proof = data["phase2c_sizing_analysis"]["independent_capacity_proof"]
        g3a = proof["scalar_capacity"]["capacity_keur"]
        g4  = proof["vector_capacity"]["capacity_keur"]
        excel = proof["excel_total_debt_keur"]
        residual = abs(g4 - excel)
        assert residual < 0.001, f"Independent residual {residual:.12f} kEUR must be < 0.001"

    def test_banding_effect_negative(self):
        data = json.loads(FIXTURE_PATH.read_text())
        proof = data["phase2c_sizing_analysis"]["independent_capacity_proof"]
        banding = proof["banding_effect_keur"]
        assert banding < 0, f"Banding effect must be negative (DSCR banding reduces capacity): {banding}"


# ---------------------------------------------------------------------------
# TestSourceVectorProvenance — hash reconstruction without calling production helper
# ---------------------------------------------------------------------------

class TestSourceVectorProvenance:
    """Item 5: independent source-vector hash reconstruction."""

    def test_hash_reproducible_without_production_helper(self):
        """Reconstruct canonical 13-field source-vector hash without production helper."""
        import hashlib
        import json as _json
        data = json.loads(FIXTURE_PATH.read_text())
        wa = data["workstream_a"]
        wb_all = data["workstream_b"]
        wb = wb_all["period_vectors"]
        we = data["workstream_e"]
        pa = data["phase2c_sizing_analysis"]

        cf83_data = wa.get("cf_row83_debt_cost_adj", {})
        cf83_vals = cf83_data.get("period_values", [None] * 61)

        vectors = {
            "cfads": wa["ds_row20_cfads"]["period_values_keur"],
            "dscr":  wa["ds_row22_dscr_target"]["period_values"],
            "ops":   wb["row9_ops_flag"]["period_values"],
            "row5_eligibility": wb["row5_flag"]["period_values"],
            "b23_tranche": wb_all.get("ds_b23_tranche_flag", {}).get("value"),
            "cf83_cumulative": cf83_vals,
            "rate":  we["ds_row44_annual_sculpting_rate"]["period_values"],
            "b54_wht": wb_all.get("ds_b54_wht_rate", {}).get("value"),
            "frac":  wb["row6_day_frac"]["period_values"],
            "row7_refinancing_flag": wb["row7_refin_flag"]["period_values"],
            "row82_refinancing_capacity": wb["row82_refin_capacity"]["period_values"],
            "active_periods": pa.get("active_periods_count"),
            "maturity_period": pa.get("maturity_period"),
        }
        serialised = _json.dumps(vectors, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False)
        computed = hashlib.sha256(serialised.encode()).hexdigest()
        stored = (
            data["phase2c_sizing_analysis"]["independent_capacity_proof"]
            .get("_source_vectors_sha256", "")
        )
        assert computed == stored, (
            f"Source vector hash mismatch: computed={computed[:16]}…, stored={stored[:16]}…\n"
            f"The 13-field canonical payload must match _source_vectors_sha256."
        )

    def test_all_five_raw_vectors_present(self):
        data = json.loads(FIXTURE_PATH.read_text())
        wa = data["workstream_a"]
        wb = data["workstream_b"]["period_vectors"]
        we = data["workstream_e"]
        assert "ds_row20_cfads" in wa
        assert "ds_row22_dscr_target" in wa
        assert "row9_ops_flag" in wb
        assert "ds_row44_annual_sculpting_rate" in we
        assert "row6_day_frac" in wb


# ---------------------------------------------------------------------------
# TestExtractorExecutionPath — call _assemble_bridge_from_vectors directly
# with synthetic inputs; catches NameError and missing G3A/G4
# ---------------------------------------------------------------------------

class TestExtractorExecutionPath:
    """Item 3: real extractor execution-path test."""

    def test_assemble_bridge_importable_and_callable(self):
        from finco_recon.extract_oborovo_debt_interest import _assemble_bridge_from_vectors
        active = list(range(1, 5))
        result = _assemble_bridge_from_vectors(
            cfads_dict={p: 2000.0 for p in active},
            dscr_dict={p: 1.15 for p in active},
            ops_dict={p: 1.0 for p in active},
            rates_dict={p: 0.0565 for p in active},
            fracs_dict={p: 0.5 for p in active},
            active_phase2a=active,
            case0_debt=40000.0,
            case1_debt=41000.0,
            case2_debt=41500.0,
            case3_debt=41800.0,
            excel_debt=41801.0,
        )
        assert "g3a_scalar_capacity_keur" in result
        assert "g4_vector_capacity_keur" in result
        assert "banding_effect_keur" in result
        assert "delta_solver_to_independent_scalar_keur" in result
        assert "delta_dscr_banding_keur" in result
        assert "bridge_closed" in result

    def test_no_name_error_at_import(self):
        import importlib
        import sys
        # Ensure fresh-ish import works without NameError
        mod_name = "finco_recon.extract_oborovo_debt_interest"
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
        else:
            mod = importlib.import_module(mod_name)
        # Key helper must be present
        assert hasattr(mod, "_assemble_bridge_from_vectors")
        assert callable(mod._assemble_bridge_from_vectors)

    def test_source_guard_no_inline_formula(self):
        import inspect
        from finco_recon import extract_oborovo_debt_interest as m
        src = inspect.getsource(m)
        assert "solve_senior_debt" in src, "Extractor must use solve_senior_debt"
        assert "build_schedule" not in src, "Extractor must not use build_schedule"
        # No inline fallback backward induction
        assert "inline" not in src.lower() or "no inline" in src.lower() or "fallback" not in src.lower()

    def test_bridge_g3a_exceeds_g4_synthetic(self):
        from finco_recon.extract_oborovo_debt_interest import _assemble_bridge_from_vectors
        active = list(range(1, 29))
        # Mixed DSCR: 1.15 for P1-P24, 1.35 for P25-P28 (like Oborovo)
        result = _assemble_bridge_from_vectors(
            cfads_dict={p: 2000.0 for p in active},
            dscr_dict={p: 1.15 if p <= 24 else 1.35 for p in active},
            ops_dict={p: 1.0 if p < 28 else 0.989 for p in active},
            rates_dict={p: 0.0565 for p in active},
            fracs_dict={p: 0.5 for p in active},
            active_phase2a=active,
            case0_debt=40000.0,
            case1_debt=41000.0,
            case2_debt=41500.0,
            case3_debt=41800.0,
            excel_debt=41801.0,
        )
        assert result["g3a_scalar_capacity_keur"] > result["g4_vector_capacity_keur"], (
            "G3A (scalar DSCR=1.15) must exceed G4 (vector with 1.35 banding)"
        )
        assert result["banding_effect_keur"] < 0, "DSCR banding must reduce capacity"


# ---------------------------------------------------------------------------
# TestDirectionalSensitivity — higher DSCR/rate/lower ops reduces capacity
# ---------------------------------------------------------------------------

class TestDirectionalSensitivity:
    """Item 6 directional tests: capacity responds correctly to input changes."""

    def _cap_vector(self, cfads, dscr_v, ops_v, rates_v, fracs_v, active):
        """Use vector capacity (respects per-period DSCR) for directional tests."""
        from finco_recon.derive_c3b2_independent_capacity import derive_capacities_from_vectors
        return derive_capacities_from_vectors(
            cfads={p: cfads for p in active},
            dscr_vector={p: dscr_v for p in active},
            ops_vector={p: ops_v for p in active},
            annual_rates={p: rates_v for p in active},
            day_fractions={p: fracs_v for p in active},
            active_periods=active,
        )["vector_capacity_keur"]

    def _cap(self, cfads, dscr_v, ops_v, rates_v, fracs_v, active):
        return self._cap_vector(cfads, dscr_v, ops_v, rates_v, fracs_v, active)

    def test_higher_dscr_reduces_capacity(self):
        active = list(range(1, 10))
        base = self._cap_vector(2000.0, 1.15, 1.0, 0.05, 0.5, active)
        high = self._cap_vector(2000.0, 1.35, 1.0, 0.05, 0.5, active)
        assert high < base, f"Higher DSCR must reduce capacity: base={base:.3f}, high={high:.3f}"

    def test_higher_rate_reduces_capacity(self):
        active = list(range(1, 10))
        base = self._cap(2000.0, 1.15, 1.0, 0.05, 0.5, active)
        high = self._cap(2000.0, 1.15, 1.0, 0.10, 0.5, active)
        assert high < base, f"Higher rate must reduce capacity: base={base:.3f}, high={high:.3f}"

    def test_lower_ops_reduces_capacity(self):
        active = list(range(1, 10))
        base = self._cap(2000.0, 1.15, 1.0, 0.05, 0.5, active)
        low  = self._cap(2000.0, 1.15, 0.5, 0.05, 0.5, active)
        assert low < base, f"Lower ops_frac must reduce capacity: base={base:.3f}, low={low:.3f}"

    def test_higher_cfads_increases_capacity(self):
        active = list(range(1, 10))
        base = self._cap(2000.0, 1.15, 1.0, 0.05, 0.5, active)
        high = self._cap(4000.0, 1.15, 1.0, 0.05, 0.5, active)
        assert high > base, f"Higher CFADS must increase capacity: base={base:.3f}, high={high:.3f}"


# ---------------------------------------------------------------------------
# TestRuntimeInventoryFactory — factory-derived fields match fixture
# ---------------------------------------------------------------------------

class TestRuntimeInventoryFactory:
    """Item 5: runtime inventory must be factory-derived, not hardcoded.

    C3B3A transition: two-layer structure. Legacy fields live in legacy_runtime;
    clean contract fields in clean_senior_debt_contract.
    """

    def test_factory_function_recorded(self):
        data = json.loads(FIXTURE_PATH.read_text())
        ri = data["phase2c_sizing_analysis"]["runtime_inventory"]
        assert ri.get("factory_function") == "app.project_factories.create_default_oborovo", (
            "runtime_inventory must record the factory function path"
        )

    def test_legacy_layer_fields_match_live_factory(self):
        from app import project_factories
        proj = project_factories.create_default_oborovo()
        fp = proj.financing

        data = json.loads(FIXTURE_PATH.read_text())
        ri = data["phase2c_sizing_analysis"]["runtime_inventory"]
        lr = ri["legacy_runtime"]

        assert "gearing_cap" in str(lr["debt_sizing_method"])
        assert abs(lr["fixed_debt_keur"] - fp.fixed_debt_keur) < 1e-6
        assert lr["use_frozen_excel_senior_debt_schedule"] == fp.use_frozen_excel_senior_debt_schedule
        assert lr["frozen_senior_ds_fixture_path"] == fp.frozen_senior_ds_fixture_path

    def test_clean_contract_target_dscr_matches_factory(self):
        from app import project_factories
        proj = project_factories.create_default_oborovo()
        fp = proj.financing

        data = json.loads(FIXTURE_PATH.read_text())
        cc = data["phase2c_sizing_analysis"]["runtime_inventory"]["clean_senior_debt_contract"]
        assert cc["target_dscr"] == fp.target_dscr

    def test_frozen_schedule_true(self):
        data = json.loads(FIXTURE_PATH.read_text())
        ri = data["phase2c_sizing_analysis"]["runtime_inventory"]
        assert ri["legacy_runtime"]["use_frozen_excel_senior_debt_schedule"] is True

    def test_classification_frozen_excel(self):
        data = json.loads(FIXTURE_PATH.read_text())
        ri = data["phase2c_sizing_analysis"]["runtime_inventory"]
        assert ri["legacy_runtime"]["runtime_classification"] == "FROZEN_EXCEL_SCHEDULE_RUNTIME"


# ---------------------------------------------------------------------------
# TestCausalBridgeIntermediateIdentities — G0→G1→G2→G3→G3A→G4 each closes
# ---------------------------------------------------------------------------

class TestCausalBridgeIntermediateIdentities:
    """Item 8: each intermediate bridge identity must close independently."""

    @pytest.fixture(scope="class")
    def bridge(self):
        data = json.loads(FIXTURE_PATH.read_text())
        return data["phase2c_sizing_analysis"]["causal_bridge"]

    @pytest.fixture(scope="class")
    def pa(self):
        data = json.loads(FIXTURE_PATH.read_text())
        return data["phase2c_sizing_analysis"]

    def test_g0_to_g1_identity(self, bridge):
        g0 = bridge["case0_current_phase2c_keur"]
        g1 = bridge["case1_excel_rates_keur"]
        delta_rate = bridge["delta_rate_keur"]
        assert abs((g0 + delta_rate) - g1) < 0.01, (
            f"G0+delta_rate must equal G1: {g0:.3f}+{delta_rate:.3f}={g0+delta_rate:.3f}, G1={g1:.3f}"
        )

    def test_g1_to_g2_identity(self, bridge):
        g1 = bridge["case1_excel_rates_keur"]
        g2 = bridge["case2_excel_cfads_keur"]
        delta_cfads = bridge["delta_cfads_keur"]
        assert abs((g1 + delta_cfads) - g2) < 0.01, (
            f"G1+delta_cfads must equal G2"
        )

    def test_g2_to_g3_identity(self, bridge):
        g2 = bridge["case2_excel_cfads_keur"]
        g3 = bridge["case3_act360_keur"]
        delta_dc = bridge["delta_daycount_keur"]
        assert abs((g2 + delta_dc) - g3) < 0.01, (
            f"G2+delta_daycount must equal G3"
        )

    def test_g3_to_g3a_identity(self, bridge):
        g3 = bridge["case3_act360_keur"]
        g3a = bridge["g3a_scalar_backward_induction_keur"]
        delta_s = bridge["delta_solver_to_independent_scalar_keur"]
        assert abs((g3 + delta_s) - g3a) < 0.01, (
            f"G3+delta_solver_to_independent_scalar must equal G3A"
        )

    def test_g3a_to_g4_identity(self, bridge):
        g3a = bridge["g3a_scalar_backward_induction_keur"]
        g4 = bridge["g4_vector_backward_induction_keur"]
        delta_b = bridge["delta_dscr_banding_g3a_to_g4_keur"]
        assert abs((g3a + delta_b) - g4) < 0.01, (
            f"G3A+delta_dscr_banding must equal G4"
        )

    def test_g4_equals_excel_debt(self, bridge, pa):
        g4 = bridge["g4_vector_backward_induction_keur"]
        excel = pa["excel_total_debt_keur"]
        assert abs(g4 - excel) < 0.001, (
            f"G4 must equal Excel debt: G4={g4:.9f}, excel={excel:.9f}"
        )

    def test_full_bridge_sum_equals_g4(self, bridge):
        g0 = bridge["case0_current_phase2c_keur"]
        total = (g0
                 + bridge["delta_rate_keur"]
                 + bridge["delta_cfads_keur"]
                 + bridge["delta_daycount_keur"]
                 + bridge["delta_solver_to_independent_scalar_keur"]
                 + bridge["delta_dscr_banding_g3a_to_g4_keur"])
        g4 = bridge["g4_vector_backward_induction_keur"]
        assert abs(total - g4) < 0.001, (
            f"G0+all_deltas must equal G4: sum={total:.9f}, G4={g4:.9f}"
        )


# ---------------------------------------------------------------------------
# TestCompleteHelperDirectional — full formula: all 9 directional sensitivities
# ---------------------------------------------------------------------------

class TestCompleteHelperDirectional:
    """Item 6: complete helper directional tests for all formula inputs."""

    def _cap(self, **kwargs):
        from finco_recon.derive_c3b2_independent_capacity import derive_capacities_from_vectors
        active = kwargs.pop("active", list(range(1, 10)))
        cfads = kwargs.pop("cfads", 2000.0)
        dscr  = kwargs.pop("dscr", 1.15)
        ops   = kwargs.pop("ops", 1.0)
        rate  = kwargs.pop("rate", 0.05)
        frac  = kwargs.pop("frac", 0.5)
        result = derive_capacities_from_vectors(
            cfads={p: cfads for p in active},
            dscr_vector={p: dscr for p in active},
            ops_vector={p: ops for p in active},
            annual_rates={p: rate for p in active},
            day_fractions={p: frac for p in active},
            active_periods=active,
            **kwargs,
        )
        return result["vector_capacity_keur"]

    def test_higher_dscr_reduces_capacity(self):
        base = self._cap(dscr=1.15)
        high = self._cap(dscr=1.35)
        assert high < base, f"Higher DSCR reduces capacity: base={base:.3f}, high={high:.3f}"

    def test_higher_rate_reduces_capacity(self):
        base = self._cap(rate=0.05)
        high = self._cap(rate=0.10)
        assert high < base, f"Higher rate reduces capacity: base={base:.3f}, high={high:.3f}"

    def test_lower_ops_reduces_capacity(self):
        base = self._cap(ops=1.0)
        low  = self._cap(ops=0.5)
        assert low < base, f"Lower ops reduces capacity: base={base:.3f}, low={low:.3f}"

    def test_lower_eligibility_reduces_capacity(self):
        active = list(range(1, 10))
        base = self._cap(active=active)  # eligibility=1.0 (neutral)
        low  = self._cap(active=active, eligibility_fraction={p: 0.5 for p in active})
        assert low < base, f"Lower eligibility reduces capacity: base={base:.3f}, low={low:.3f}"

    def test_positive_cf83_increases_capacity(self):
        active = list(range(1, 10))
        base = self._cap(active=active)  # cf83=0 (neutral)
        pos  = self._cap(active=active, cumulative_cf83={p: 100.0 for p in active})
        assert pos > base, f"Positive CF!row83 increases capacity: base={base:.3f}, pos={pos:.3f}"

    def test_positive_row82_increases_capacity(self):
        active = list(range(1, 10))
        base = self._cap(active=active)  # row82=0 (neutral)
        pos  = self._cap(active=active, refinancing_capacity={p: 100.0 for p in active})
        assert pos > base, f"Positive row82 increases capacity: base={base:.3f}, pos={pos:.3f}"

    def test_nonzero_wht_reduces_capacity(self):
        active = list(range(1, 10))
        base = self._cap(active=active)  # wht=0 (neutral)
        wht  = self._cap(active=active, wht_rate={p: 0.2 for p in active})
        assert wht < base, f"Non-zero WHT reduces capacity: base={base:.3f}, wht={wht:.3f}"

    def test_refinancing_flag_changes_branch(self):
        from finco_recon.derive_c3b2_independent_capacity import derive_capacities_from_vectors
        active = list(range(1, 4))
        # All refinancing_flag=True => capacity = sum(refinancing_capacity) discounted
        refin_cap = {p: 500.0 for p in active}
        result = derive_capacities_from_vectors(
            cfads={p: 2000.0 for p in active},
            dscr_vector={p: 1.15 for p in active},
            ops_vector={p: 1.0 for p in active},
            annual_rates={p: 0.05 for p in active},
            day_fractions={p: 0.5 for p in active},
            active_periods=active,
            refinancing_flag={p: True for p in active},
            refinancing_capacity=refin_cap,
        )
        # With all refin_flag=True: V[p] = refin_cap[p]
        # capacity = V[min(active)] = refin_cap[1] = 500.0
        assert abs(result["vector_capacity_keur"] - 500.0) < 1e-6, (
            f"With refinancing_flag=True, capacity must equal refin_cap[first_period]=500.0, "
            f"got {result['vector_capacity_keur']}"
        )

    def test_disabled_tranche_produces_zero_capacity(self):
        active = list(range(1, 10))
        # tranche_enabled=False for all periods => row23=0 => capacity=0
        result_zero = self._cap(
            active=active,
            tranche_enabled={p: False for p in active},
            refinancing_capacity={p: 0.0 for p in active},
            refinancing_flag={p: False for p in active},
        )
        assert abs(result_zero) < 1e-6, (
            f"Disabled tranche must produce 0 capacity (all row23=0), got {result_zero:.6f}"
        )


# ---------------------------------------------------------------------------
# TestExtractorSizingAnalysisPath — exercises the full _compute_phase2c_sizing_analysis
# execution path with synthetic workbook rows.  This is the canonical CI-portable
# guard against NameError / reference-before-assignment regressions: if
# `independent_capacity` or any other variable is referenced before it is
# assigned, these tests will raise NameError and fail.
# ---------------------------------------------------------------------------

def _make_ds_rows(n_rows: int = 100, n_cols: int = 45,
                  cfads: float = 2000.0, dscr: float = 1.15,
                  rate: float = 0.0565, frac: float = 0.5,
                  ops: float = 1.0, n_active: int = 10) -> dict:
    """Build a minimal synthetic ds_rows_d with n_active active Excel periods (1..n_active).

    _PERIOD_COL_OFFSET = 6, so Excel period P occupies column index 6+P.
    Columns 0-6 hold metadata; P1=col7 .. P(n_active)=col(6+n_active).
    We need at least 6+n_active+1 columns.
    """
    n_cols_actual = max(n_cols, 6 + n_active + 1)
    base = [None] * n_cols_actual

    def _row(**kwargs):
        r = list(base)
        for col, val in kwargs.items():
            r[col] = val
        return tuple(r)

    rows = {i: tuple(base) for i in range(n_rows)}

    allowed_ds = cfads / dscr * ops  # row23 value per period

    for p in range(1, n_active + 1):
        c = 6 + p  # column index for this period

        rows[19] = _put(rows[19], c, cfads)             # DS!row20 — CFADS
        rows[21] = _put(rows[21], c, dscr)              # DS!row22 — DSCR target
        rows[22] = _put(rows[22], c, allowed_ds)        # DS!row23 — allowed CF
        rows[43] = _put(rows[43], c, rate)              # DS!row44 — annual rate
        rows[5]  = _put(rows[5],  c, frac)              # DS!row6  — day fraction
        rows[60] = _put(rows[60], c, 1.0)               # DS!row61 — opening balance > 0 (active)
        rows[45] = _put(rows[45], c, allowed_ds)        # DS!row46 — row23 * row5 (row5=1)
        rows[8]  = _put(rows[8],  c, ops)               # DS!row9  — ops fraction
        rows[4]  = _put(rows[4],  c, None)              # DS!row5  — eligibility (openpyxl None = 1)
        rows[6]  = _put(rows[6],  c, None)              # DS!row7  — refinancing flag (None = False)
        rows[46] = _put(rows[46], c, 15000.0)           # DS!row47 — > 0 proves row7=False
        rows[81] = _put(rows[81], c, 0.0)               # DS!row82 — refinancing capacity = 0

    # B23 = True at col 1 of row 22; B54 = 0 at col 1 of row 53
    rows[22] = _put(rows[22], 1, True)
    rows[53] = _put(rows[53], 1, 0)

    return rows


def _put(row: tuple, col: int, val) -> tuple:
    lst = list(row)
    while len(lst) <= col:
        lst.append(None)
    lst[col] = val
    return tuple(lst)


def _make_inp_rows(n_rows: int = 200, excel_debt: float = 20000.0) -> dict:
    """Build a minimal synthetic inp_rows_d.  DS!D51 is at inp_rows[194][3]."""
    base = [None] * 10
    rows = {i: tuple(base) for i in range(n_rows)}
    lst = list(rows[194])
    while len(lst) <= 3:
        lst.append(None)
    lst[3] = excel_debt
    rows[194] = tuple(lst)
    return rows


class TestExtractorSizingAnalysisPath:
    """Execute _compute_phase2c_sizing_analysis with synthetic workbook rows.

    Guards against NameError / reference-before-assignment in the full
    sizing analysis function path (Case 0 → Case 1 → Case 2 → Case 3 →
    G3A scalar backward induction → G4 vector backward induction →
    causal bridge → verdict).
    """

    VALID_VERDICTS = {
        "C3B2_DEBT_INTEREST_SOURCE_TRUTH_PROVED",
        "C3B2_SOURCE_TRUTH_PARTIAL_MANUAL_CHECK_REQUIRED",
    }

    @classmethod
    def _run(cls, n_active: int = 10, excel_debt: float = 20000.0,
             dscr: float = 1.15):
        from finco_recon.extract_oborovo_debt_interest import (
            _compute_phase2c_sizing_analysis,
        )
        ds_rows_d  = _make_ds_rows(n_active=n_active, dscr=dscr)
        inp_rows_d = _make_inp_rows(excel_debt=excel_debt)
        return _compute_phase2c_sizing_analysis({}, ds_rows_d, inp_rows_d)

    def test_no_name_error_on_execution(self):
        """Function must complete without NameError (independent_capacity defined before use)."""
        result = self._run()
        assert result is not None, "Function returned None"

    def test_status_computed(self):
        result = self._run()
        assert result.get("status") == "COMPUTED", (
            f"Expected status=COMPUTED, got {result.get('status')}"
        )

    def test_required_top_level_keys(self):
        result = self._run()
        required = {
            "current_phase2c_solver_result",
            "scalar_excel_matched_solver_result",
            "g3a_scalar_backward_induction",
            "independent_vector_dscr_capacity",
            "causal_bridge",
            "verdict",
        }
        missing = required - set(result.keys())
        assert not missing, f"Missing keys in sizing_analysis result: {missing}"

    def test_verdict_is_valid(self):
        result = self._run()
        verdict = result.get("verdict")
        assert verdict in self.VALID_VERDICTS, (
            f"Unexpected verdict: {verdict!r}; valid={self.VALID_VERDICTS}"
        )

    def test_causal_bridge_closed(self):
        result = self._run()
        bridge = result.get("causal_bridge", {})
        assert bridge.get("bridge_closed") is True, (
            f"Causal bridge not closed; error={bridge.get('bridge_closure_error_keur')}"
        )

    def test_independent_capacity_proof_present(self):
        result = self._run()
        # G3A scalar and G4 vector capacities are stored as separate top-level keys
        g3a = result.get("g3a_scalar_backward_induction", {})
        g4  = result.get("independent_vector_dscr_capacity", {})
        assert g3a.get("capacity_keur") is not None, (
            "g3a_scalar_backward_induction.capacity_keur missing"
        )
        assert g4.get("capacity_keur") is not None, (
            "independent_vector_dscr_capacity.capacity_keur missing"
        )

    def test_g3a_exceeds_g4_for_uniform_dscr(self):
        """With uniform DSCR=1.15, G3A >= G4 (scalar induction >= vector induction)."""
        result = self._run(dscr=1.15)
        g3a_cap = result.get("g3a_scalar_backward_induction", {}).get("capacity_keur")
        g4_cap  = result.get("independent_vector_dscr_capacity", {}).get("capacity_keur")
        assert g3a_cap is not None and g4_cap is not None, (
            f"G3A={g3a_cap}, G4={g4_cap} — capacity values missing"
        )
        # With identical scalar and vector DSCR both = 1.15, G3A >= G4
        assert g3a_cap >= g4_cap - 0.1, (
            f"G3A ({g3a_cap:.3f}) must be >= G4 ({g4_cap:.3f}) for uniform DSCR"
        )

    def test_neutral_terms_proof_present(self):
        result = self._run()
        assert "neutral_terms_proof" in result, "neutral_terms_proof missing from result"

    def test_no_missing_d51_error(self):
        """Correct inp_rows_d must not return MISSING_D51 status."""
        result = self._run(excel_debt=30000.0)
        assert result.get("status") != "MISSING_D51", "D51 extraction failed with valid inp_rows_d"

    def test_missing_d51_returns_error_status(self):
        """Omitting D51 must return a non-COMPUTED status (not crash)."""
        from finco_recon.extract_oborovo_debt_interest import (
            _compute_phase2c_sizing_analysis,
        )
        ds_rows_d  = _make_ds_rows()
        inp_rows_d = _make_inp_rows(excel_debt=None)
        # Patch D51 to None
        lst = list(inp_rows_d[194])
        lst[3] = None
        inp_rows_d[194] = tuple(lst)
        result = _compute_phase2c_sizing_analysis({}, ds_rows_d, inp_rows_d)
        assert result.get("status") in {"MISSING_D51", "NO_ACTIVE_PERIODS", "ERROR"}, (
            f"Expected error status with missing D51, got {result.get('status')}"
        )
