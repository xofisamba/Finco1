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
    "C3B2_EQUAL_INPUT_EQUAL_POLICY_MATCH",
    "C3B2_INPUT_OR_POLICY_MISMATCH_FULLY_EXPLAINED",
    "C3B2_EQUAL_INPUT_EQUAL_POLICY_DIVERGENCE_PROVED",
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
# Equal-input / equal-policy comparison
# ---------------------------------------------------------------------------

class TestEqualInputEqualPolicy:
    def test_section_present(self, truth):
        assert "equal_input_equal_policy" in truth

    def test_status_is_computed(self, truth):
        status = truth["equal_input_equal_policy"]["status"]
        assert status == "COMPUTED", (
            f"Equal-input comparison must be COMPUTED, got {status!r}"
        )

    def test_phase2c_api_documented(self, truth):
        api = truth["equal_input_equal_policy"].get("phase2c_api", "")
        assert "build_schedule" in api or "sculpting" in api

    def test_verdict_is_valid_classification(self, truth):
        verdict = truth["equal_input_equal_policy"]["verdict"]
        assert verdict in VALID_VERDICTS, f"Unknown verdict: {verdict!r}"

    def test_verdict_supported_by_evidence(self, truth):
        """Evidence must determine the verdict, not an assertion about a fixed string."""
        eq = truth["equal_input_equal_policy"]
        verdict = eq["verdict"]
        periods_outside = eq.get("periods_outside_1keur_tolerance", [])
        max_delta = eq.get("maximum_absolute_period_delta_closing", 0.0)

        if verdict == "C3B2_EQUAL_INPUT_EQUAL_POLICY_MATCH":
            assert max_delta < 1.0, (
                f"Verdict is MATCH but max delta = {max_delta:.3f} kEUR (≥ 1 kEUR). "
                "Evidence contradicts verdict."
            )
        elif verdict == "C3B2_INPUT_OR_POLICY_MISMATCH_FULLY_EXPLAINED":
            assert len(periods_outside) > 0 or max_delta > 0.1, (
                "Verdict is MISMATCH_FULLY_EXPLAINED but no periods outside tolerance found. "
                "Evidence does not support verdict."
            )
            # Causal attribution must be present
            causes = eq.get("causal_attribution", [])
            assert len(causes) > 0, "Verdict MISMATCH_EXPLAINED requires causal_attribution"
        elif verdict == "C3B2_SOURCE_TRUTH_PARTIAL_MANUAL_CHECK_REQUIRED":
            pass  # Always acceptable; no numeric constraint to verify
        elif verdict == "C3B2_EQUAL_INPUT_EQUAL_POLICY_DIVERGENCE_PROVED":
            assert max_delta > 0.1, "DIVERGENCE_PROVED requires measurable delta"

    def test_excel_debt_not_hardcoded_in_extractor(self):
        """Verify extractor does not hardcode the Excel debt amount."""
        import inspect
        from finco_recon import extract_oborovo_debt_interest as m
        src = inspect.getsource(m)
        assert "42852.279" not in src, (
            "Extractor must not hardcode the Excel debt value 42852.279. "
            "Read it from the fixture or workbook."
        )

    def test_all_required_metrics_present(self, truth):
        eq = truth["equal_input_equal_policy"]
        required = [
            "excel_total_debt_keur",
            "phase2c_total_debt_keur",
            "total_debt_delta_keur",
            "maximum_absolute_period_delta_closing",
            "maximum_absolute_period_delta_interest",
            "maximum_absolute_period_delta_principal",
            "signed_cumulative_delta_keur",
            "first_differing_period",
            "maximum_delta_period",
            "periods_outside_1keur_tolerance",
            "active_periods_count",
            "period_comparison",
        ]
        for key in required:
            assert key in eq, f"Required metric missing: {key}"

    def test_period_comparison_covers_all_active(self, truth):
        eq = truth["equal_input_equal_policy"]
        n_active = eq["active_periods_count"]
        n_comparison = len(eq["period_comparison"])
        assert n_comparison == n_active, (
            f"period_comparison has {n_comparison} entries; expected {n_active}"
        )

    def test_first_differing_period_is_period25(self, truth):
        """DSCR band switches at period 25; divergence must start there."""
        fd = truth["equal_input_equal_policy"]["first_differing_period"]
        if fd is not None:
            assert fd == 25, f"First differing period expected 25, got {fd}"

    def test_per_period_dscr_validation_exact_match(self, truth):
        """When per-period DSCR is matched, the schedule must be exact."""
        pp = truth["equal_input_equal_policy"].get("per_period_dscr_validation", {})
        assert pp.get("exact_match") is True, (
            "Per-period DSCR forward pass must match Excel exactly. "
            f"max_delta={pp.get('max_absolute_delta_keur')}"
        )

    def test_causal_attribution_mentions_dscr_banding(self, truth):
        causes = truth["equal_input_equal_policy"].get("causal_attribution", [])
        cause_ids = [c.get("cause", "") for c in causes]
        assert any("DSCR" in c for c in cause_ids), (
            "Causal attribution must mention DSCR banding"
        )

    def test_inputs_used_no_hardcoded_debt(self, truth):
        inputs = truth["equal_input_equal_policy"].get("inputs_used", {})
        hardcoded = inputs.get("hardcoded_values", "")
        assert "NONE" in hardcoded or "none" in hardcoded.lower(), (
            "inputs_used must declare no hardcoded values"
        )

    def test_rate_convention_no_doubling(self, truth):
        inputs = truth["equal_input_equal_policy"].get("inputs_used", {})
        rate_note = inputs.get("rate_source", "") + inputs.get("rate_convention", "")
        assert "factor-of-2" not in rate_note.lower().replace("no factor-of-2", "") \
            or "no factor" in rate_note.lower(), (
            f"Rate convention must not imply doubling: {rate_note!r}"
        )

    def test_no_project_name_dispatch(self):
        """Extractor must not contain project-name dispatch logic."""
        from finco_recon import extract_oborovo_debt_interest as m
        import inspect
        src = inspect.getsource(m)
        forbidden = ["if project", "if oborovo", "if 'oborovo'"]
        for kw in forbidden:
            assert kw.lower() not in src.lower(), (
                f"Extractor contains project-name dispatch: {kw!r}"
            )

    def test_no_approved_delta_or_plug(self):
        """Extractor must not contain approved_delta, plug, or target override logic."""
        from finco_recon import extract_oborovo_debt_interest as m
        import inspect
        src = inspect.getsource(m)
        for kw in ["approved_delta", "target_override", "frozen_schedule"]:
            assert kw not in src, f"Extractor contains forbidden pattern: {kw!r}"


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
            ["git", "diff", "1fb4943a4319eff8f4ac7a22add6f65f14bd8cec...HEAD",
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
            ["git", "diff", "1fb4943a4319eff8f4ac7a22add6f65f14bd8cec...HEAD",
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
            ["git", "diff", "1fb4943a4319eff8f4ac7a22add6f65f14bd8cec...HEAD",
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
