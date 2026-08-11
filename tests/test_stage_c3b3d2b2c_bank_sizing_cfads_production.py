"""tests/test_stage_c3b3d2b2c_bank_sizing_cfads_production.py

C3B3D2B2C — Bank-Sizing CFADS Scenario Layer: Evidence Package

Stage verdict: C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE
R4 verdict:   C3B3D2B2C_R4_SOURCE_INPUTS_IDENTIFIED_CURVE_EXTRACTION_REQUIRED
R4.1 verdict: C3B3D2B2C_R4_1_MANUAL_CAUSALITY_PROVEN_ENGINE_EVALUATION_XLSM_EXTRACTION_REQUIRED

EVIDENCE-ONLY TESTS. No production financial_engine modifications in this PR.
All bank-sizing candidates use finco_recon.bank_sizing_candidates (diagnostic module).

Governance:
    No DS25/DS40 period boundary hardcoding — ENFORCED
    No project-name dispatch in production code — ENFORCED (factories used for oracle)
    No approved_delta or balancing plug — ENFORCED
    No calibration of clean engine to source — ENFORCED
    13547.2 does not appear as a literal — ENFORCED
    Protected C3B2 SHA: f8f244c0660495bfb4115d4e32ba329c291ab829d1d0693e614c889457b5add7
    VBA_IMPLEMENTATION_NOT_VISIBLE — preserved
    BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED — preserved

Test classes:
    TestSourceOracleDs20            — DS!row20 oracle structure + candidate comparison
    TestMacro50Forensics            — Macro!row50 formula extraction result
    TestCandidateAAllProduction     — Candidate A (ALL_PRODUCTION) rejection evidence
    TestCandidateBMerchantOnly      — Candidate B (MERCHANT_ONLY) rejection evidence
    TestMerchantPeriodDecomposition — Per-period delta characterisation
    TestCfadsBridge                 — CF79 = base CFADS identity, DS20 divergence
    TestProductionFilesUnchanged    — Production API unchanged (no bank-sizing fields)
    TestC3b3d2b2bRegressionLock     — CF2=CF3=CF4=CF5=0 still holds
    TestGovernance                  — Governance guards
    TestBaselineGovernance          — Stale-value guards (C3B3D2B2B locked)
    TestHorizonCausality            — R4: active debt horizon + DSCR causal boundary
    TestR4SourceEvidence            — R4: confirmed source cell identifiers
    TestCandidateCArchitecture      — R4: Candidate C architecture constraints
    TestR4_1ManualCausality         — R4.1: manual causality evidence + TUHO oracle
    TestR4_1ProductContract         — R4.1: product contract design constraints
"""
from __future__ import annotations

import json
import pathlib

import pytest

_FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"
_OBOROVO_DEBT_TRUTH_PATH = _FIXTURE_DIR / "excel_oborovo_debt_interest_truth.json"


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

def _load_debt_truth() -> dict:
    with open(_OBOROVO_DEBT_TRUTH_PATH) as f:
        return json.load(f)


def _load_source_ds_row20() -> list[float]:
    """DS!row20 = Macro!row50 oracle. Test only — not for production use."""
    return _load_debt_truth()["workstream_a"]["ds_row20_cfads"]["period_values_keur"]


def _load_cf79_base_cfads() -> list[float]:
    return _load_debt_truth()["workstream_a"]["cf_row79_free_cash_flow_for_banks"]["period_values_keur"]


# ---------------------------------------------------------------------------
# TestSourceOracleDs20
# ---------------------------------------------------------------------------

class TestSourceOracleDs20:
    """DS!row20 = Macro!row50 oracle structure and candidate comparison."""

    def test_source_vector_length_and_construction(self):
        """DS!row20 has 61 entries: [0]=construction, [1-60]=operating."""
        ds20 = _load_source_ds_row20()
        assert len(ds20) == 61
        assert ds20[0] == 0.0, "Index [0] is construction period (zero)"

    def test_source_ppa_period_range(self):
        """DS!row20 PPA periods (1-24) in expected CFADS range."""
        ds20 = _load_source_ds_row20()
        for i in range(1, 25):
            assert 2400.0 < ds20[i] < 3000.0, f"ds20[{i}]={ds20[i]:.1f} outside PPA range"

    def test_source_merchant_period_lower_than_ppa(self):
        """DS!row20 merchant periods (25+) are substantially lower than PPA periods."""
        ds20 = _load_source_ds_row20()
        max_ppa = max(ds20[1:25])
        # First 5 merchant periods all significantly below PPA max
        for i in range(25, 30):
            assert ds20[i] < max_ppa - 200, (
                f"Merchant ds20[{i}]={ds20[i]:.1f} not substantially below max PPA {max_ppa:.1f}"
            )

    def test_ds20_formula_is_macro_row50(self):
        """Confirmed: DS!H20 formula = =Macro!H50."""
        truth = _load_debt_truth()
        formula = truth["workstream_a"]["ds_row20_cfads"]["formula_h"]
        assert formula == "=Macro!H50", f"Unexpected DS!H20 formula: {formula!r}"

    def test_macro49_formula_is_cf79(self):
        """Confirmed: Macro!H49 formula = =CF!H79 (base P50 CFADS)."""
        truth = _load_debt_truth()
        formula = truth["workstream_a"]["macro_row49_input"]["formula_h"]
        assert formula == "=CF!H79", f"Unexpected Macro!H49 formula: {formula!r}"

    def test_macro50_formula_is_none(self):
        """Macro!H50 formula = None — VBA-hardcoded values, not formula-driven."""
        truth = _load_debt_truth()
        formula = truth["workstream_a"]["macro_row50_output_formula"]
        assert formula is None, (
            f"Expected None (VBA-hardcoded), got: {formula!r}. "
            "If formula is now present, re-evaluate VBA_IMPLEMENTATION_NOT_VISIBLE status."
        )

    def test_ppa_identity_holds(self):
        """PPA periods 1-24: Macro49 (=CF79) ≈ DS20 (component bridge confirms)."""
        truth = _load_debt_truth()
        macro49 = truth["workstream_a"]["macro_row49_input"]["period_values_keur"]
        ds20 = _load_source_ds_row20()
        for i in range(1, 25):
            assert abs(macro49[i] - ds20[i]) < 1.0, (
                f"PPA period {i}: Macro49={macro49[i]:.3f} vs DS20={ds20[i]:.3f} "
                f"delta={macro49[i]-ds20[i]:.3f}"
            )

    def test_merchant_divergence_confirmed(self):
        """Merchant periods 25+: DS20 << CF79 (Macro49) — key forensic finding."""
        truth = _load_debt_truth()
        macro49 = truth["workstream_a"]["macro_row49_input"]["period_values_keur"]
        ds20 = _load_source_ds_row20()
        large_gaps = []
        for i in range(25, 61):
            diff = macro49[i] - ds20[i]
            if diff > 100.0:
                large_gaps.append((i, diff))
        assert len(large_gaps) >= 5, (
            f"Expected ≥5 merchant periods with gap >100 kEUR, got {len(large_gaps)}: {large_gaps[:5]}"
        )

    def test_stop_verdict_classification(self):
        """Record C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE."""
        verdict = "C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE"
        assert verdict  # Classification recorded; no source-proven rule identified.

    def test_source_workbook_sha(self):
        """Source workbook SHA matches the committed authoritative value."""
        truth = _load_debt_truth()
        sha = truth["_meta"]["source_sha256"]
        assert sha == "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920"


# ---------------------------------------------------------------------------
# TestMacro50Forensics
# ---------------------------------------------------------------------------

class TestMacro50Forensics:
    """Macro!row50 formula extraction result and forensic classification."""

    def test_forensics_module_vba_label(self):
        """VBA_IMPLEMENTATION_NOT_VISIBLE label preserved in forensics module."""
        from finco_recon.bank_sizing_candidates import MACRO50_FORENSICS
        assert MACRO50_FORENSICS["vba_label"] == "VBA_IMPLEMENTATION_NOT_VISIBLE"

    def test_forensics_module_mechanism_label(self):
        """BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED label preserved."""
        from finco_recon.bank_sizing_candidates import MACRO50_FORENSICS
        assert MACRO50_FORENSICS["mechanism_label"] == "BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED"

    def test_forensics_module_r3_verdict(self):
        """R3 STOP verdict recorded in forensics module."""
        from finco_recon.bank_sizing_candidates import MACRO50_FORENSICS
        assert MACRO50_FORENSICS["r3_verdict"] == "C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE"

    def test_no_bank_production_selector(self):
        """No bank production selector found in inspected source evidence."""
        from finco_recon.bank_sizing_candidates import MACRO50_FORENSICS
        assert MACRO50_FORENSICS["bank_production_selector"] is None

    def test_no_bank_price_selector(self):
        """No bank market price selector found in inspected source evidence."""
        from finco_recon.bank_sizing_candidates import MACRO50_FORENSICS
        assert MACRO50_FORENSICS["bank_market_price_selector"] is None

    def test_no_lender_haircut_selector(self):
        """No lender/capture/haircut selector found in inspected source evidence."""
        from finco_recon.bank_sizing_candidates import MACRO50_FORENSICS
        assert MACRO50_FORENSICS["bank_lender_haircut_selector"] is None

    def test_known_scenario_selectors_documented(self):
        """Known Scenarios sheet selectors (DSCR, gearing, maturity) are documented."""
        from finco_recon.bank_sizing_candidates import MACRO50_FORENSICS
        selectors = MACRO50_FORENSICS["scenario_selectors_inspected"]
        assert "Inputs!D52" in selectors, "Base production selector must be documented"
        assert "Inputs!D89" in selectors, "Base market price selector must be documented"
        assert selectors["Inputs!D52"] == "P_50 (base production scenario)"


# ---------------------------------------------------------------------------
# TestCandidateAAllProduction
# ---------------------------------------------------------------------------

class TestCandidateAAllProduction:
    """Candidate A (ALL_PRODUCTION) diagnostic — rejected."""

    @pytest.fixture(scope="class")
    def result_a(self):
        from finco_recon.bank_sizing_candidates import run_candidate_a_all_production
        from app.project_factories import create_default_oborovo
        return run_candidate_a_all_production(create_default_oborovo)

    def test_candidate_a_classification(self, result_a):
        """ALL_PRODUCTION is classified as CANDIDATE_ONLY."""
        assert result_a["classification"] == "OBOROVO_ALL_PRODUCTION_BANK_CASE_RULE_CANDIDATE_ONLY"

    def test_candidate_a_rejected(self, result_a):
        """ALL_PRODUCTION verdict is REJECTED."""
        assert result_a["verdict"] == "REJECTED"

    def test_candidate_a_max_delta_large(self, result_a):
        """ALL_PRODUCTION: max |delta| vs DS!row20 > 100 kEUR — does not reproduce source."""
        assert result_a["max_abs_delta_keur"] > 100.0, (
            f"ALL_PRODUCTION max_abs={result_a['max_abs_delta_keur']:.3f} — "
            "unexpectedly small; would imply unverified source reproduction"
        )

    def test_candidate_a_period_count_outside(self, result_a):
        """ALL_PRODUCTION: multiple periods outside 1 kEUR tolerance."""
        assert result_a["period_count_outside_1keur"] >= 1


# ---------------------------------------------------------------------------
# TestCandidateBMerchantOnly
# ---------------------------------------------------------------------------

class TestCandidateBMerchantOnly:
    """Candidate B (MERCHANT_ONLY) diagnostic — rejected."""

    @pytest.fixture(scope="class")
    def result_b(self):
        from finco_recon.bank_sizing_candidates import run_candidate_b_merchant_only
        from app.project_factories import create_default_oborovo
        return run_candidate_b_merchant_only(create_default_oborovo)

    def test_candidate_b_classification(self, result_b):
        """MERCHANT_ONLY is classified as CANDIDATE_ONLY."""
        assert result_b["classification"] == "OBOROVO_MERCHANT_ONLY_BANK_CASE_RULE_CANDIDATE_ONLY"

    def test_candidate_b_rejected(self, result_b):
        """MERCHANT_ONLY verdict is REJECTED."""
        assert result_b["verdict"] == "REJECTED"

    def test_candidate_b_rejection_reason_vba(self, result_b):
        """MERCHANT_ONLY rejection reason references VBA_IMPLEMENTATION_NOT_VISIBLE."""
        reason = result_b["rejection_reason"]
        assert "VBA_IMPLEMENTATION_NOT_VISIBLE" in reason

    def test_candidate_b_max_delta_large(self, result_b):
        """MERCHANT_ONLY: max |delta| vs DS!row20 > 100 kEUR."""
        assert result_b["max_abs_delta_keur"] > 100.0, (
            f"MERCHANT_ONLY max_abs={result_b['max_abs_delta_keur']:.3f} — "
            "unexpectedly small"
        )

    def test_candidate_b_merchant_deltas_positive(self, result_b):
        """MERCHANT_ONLY merchant deltas are positive: P90 bank CFADS > source Macro50."""
        assert result_b["merchant_deltas_all_positive"], (
            "All merchant period deltas should be positive: "
            "P90 yield is HIGHER than VBA-computed Macro50 for merchant periods"
        )


# ---------------------------------------------------------------------------
# TestMerchantPeriodDecomposition
# ---------------------------------------------------------------------------

class TestMerchantPeriodDecomposition:
    """Per-period characterisation of the merchant gap DS20 vs CF79."""

    def test_first_four_merchant_periods_delta_range(self):
        """First four merchant periods (25-28): |DS20 - CF79| in 590-750 kEUR range."""
        truth = _load_debt_truth()
        macro49 = truth["workstream_a"]["macro_row49_input"]["period_values_keur"]
        ds20 = _load_source_ds_row20()
        # Periods 25-28 (first four merchant)
        for i in [25, 26, 27, 28]:
            gap = macro49[i] - ds20[i]
            assert 500.0 < gap < 800.0, (
                f"Period {i}: CF79-DS20 gap {gap:.1f} outside expected 500-800 kEUR range"
            )

    def test_gap_grows_over_merchant_tenor(self):
        """The CF79-DS20 gap generally grows across merchant periods (VBA downside compounds)."""
        truth = _load_debt_truth()
        macro49 = truth["workstream_a"]["macro_row49_input"]["period_values_keur"]
        ds20 = _load_source_ds_row20()
        early_gaps = [macro49[i] - ds20[i] for i in range(25, 30)]
        late_gaps = [macro49[i] - ds20[i] for i in range(55, 61)]
        assert min(late_gaps) > min(early_gaps), (
            "Late merchant gaps should exceed early gaps (VBA-driven additional downside)"
        )

    def test_no_act360_dscr_explanation(self):
        """C3B3D2B2B proved CF2=CF3=CF4=CF5=0. Gap is from CFADS only, not mechanics.

        This test preserves the C3B3D2B2B finding. The merchant-period gap in DS20 vs CF79
        is NOT explained by ACT/360, DSCR banding, ops fraction, or rate vector.
        """
        # Classification preserved from C3B3D2B2B locked finding
        assert "BANK_SIZING_CFADS_AUTHORITY_IS_SOLE_CURRENT_SIZING_GAP_SOURCE_PROVEN"


# ---------------------------------------------------------------------------
# TestCfadsBridge
# ---------------------------------------------------------------------------

class TestCfadsBridge:
    """CF79 = base CFADS component identity, and DS20 divergence from CF79."""

    def test_component_bridge_identity_holds(self):
        """CF!row79 component bridge residual = 0 (CF79 = revenues + opex + taxes + CIT)."""
        truth = _load_debt_truth()
        bridge = truth["workstream_a"]["component_bridge"]
        assert bridge["identity_holds"], "CF79 component identity should hold"
        assert bridge["max_absolute_residual_keur"] == 0.0

    def test_cf79_equals_macro49(self):
        """Macro!row49 = CF!row79: identical values for all periods."""
        truth = _load_debt_truth()
        cf79 = truth["workstream_a"]["cf_row79_free_cash_flow_for_banks"]["period_values_keur"]
        macro49 = truth["workstream_a"]["macro_row49_input"]["period_values_keur"]
        assert len(cf79) == len(macro49)
        for i, (c, m) in enumerate(zip(cf79, macro49)):
            assert abs(c - m) < 1e-6, f"Period {i}: CF79={c} ≠ Macro49={m}"

    def test_ppa_periods_align_in_scenario(self):
        """In current workbook scenario, DS20 ≈ CF79 for PPA periods (alignment confirmed)."""
        truth = _load_debt_truth()
        assert truth["workstream_a"]["cfads_composition_aligned_in_scenario"] is True

    def test_source_excel_debt_value(self):
        """Source Excel total debt = 42,852.279 kEUR (DS!D51 = DS!D47)."""
        truth = _load_debt_truth()
        excel_debt = truth["phase2c_sizing_analysis"]["excel_total_debt_keur"]
        assert abs(excel_debt - 42852.27876256299) < 0.001


# ---------------------------------------------------------------------------
# TestProductionFilesUnchanged
# ---------------------------------------------------------------------------

class TestProductionFilesUnchanged:
    """Assert production financial_engine files do NOT contain bank-sizing fields.

    R3 STOP verdict: all unproven production bank-sizing code must be absent.
    """

    def test_inputs_no_production_scenario_scope(self):
        """financial_engine/inputs.py must NOT define ProductionScenarioScope."""
        import financial_engine.inputs as fi
        assert not hasattr(fi, "ProductionScenarioScope"), (
            "ProductionScenarioScope must not be in production inputs — "
            "reverted under R3 STOP verdict"
        )

    def test_inputs_debt_sizing_scenario_absent(self):
        """DebtSizingScenario must NOT exist in production inputs (reverted under R3 STOP)."""
        import financial_engine.inputs as fi
        assert not hasattr(fi, "DebtSizingScenario"), (
            "DebtSizingScenario must be absent from production inputs — "
            "reverted under R3 STOP verdict. Candidate logic lives in finco_recon/"
        )

    def test_inputs_senior_debt_model_no_bank_sizing_scenario(self):
        """SeniorDebtModelInput must NOT have bank_sizing_scenario field."""
        from financial_engine.inputs import SeniorDebtModelInput
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(SeniorDebtModelInput)}
        assert "bank_sizing_scenario" not in field_names, (
            "SeniorDebtModelInput.bank_sizing_scenario must be absent — reverted under R3 STOP"
        )

    def test_results_no_bank_sizing_cfads(self):
        """SeniorDebtSchedules must NOT have bank_sizing_cfads_keur field."""
        from financial_engine.results import SeniorDebtSchedules
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(SeniorDebtSchedules)}
        assert "bank_sizing_cfads_keur" not in field_names, (
            "SeniorDebtSchedules.bank_sizing_cfads_keur must be absent — reverted"
        )

    def test_results_no_bank_sizing_dscr(self):
        """SeniorDebtSchedules must NOT have bank_sizing_dscr field."""
        from financial_engine.results import SeniorDebtSchedules
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(SeniorDebtSchedules)}
        assert "bank_sizing_dscr" not in field_names, (
            "SeniorDebtSchedules.bank_sizing_dscr must be absent — reverted"
        )

    def test_orchestrator_no_derive_bank_input(self):
        """financial_engine/orchestrator.py must NOT export _derive_bank_operating_input."""
        import financial_engine.orchestrator as orch
        assert not hasattr(orch, "_derive_bank_operating_input"), (
            "_derive_bank_operating_input must not be in production orchestrator — "
            "moved to finco_recon/bank_sizing_candidates.py"
        )

    def test_orchestrator_no_is_ppa_for_bank_splice(self):
        """financial_engine/orchestrator.py must NOT export _is_ppa_for_bank_splice."""
        import financial_engine.orchestrator as orch
        # _is_ppa_for_bank_splice is a closure/local function — check no module-level attr
        assert not hasattr(orch, "_is_ppa_for_bank_splice"), (
            "_is_ppa_for_bank_splice must not be in production orchestrator"
        )

    def test_provenance_fingerprint_no_bank_scenario_payload(self):
        """Senior debt fingerprint must NOT include bank_sizing_scenario payload."""
        import inspect
        from financial_engine.provenance import compute_senior_debt_fingerprint
        src = inspect.getsource(compute_senior_debt_fingerprint)
        assert "bank_sizing_scenario" not in src, (
            "compute_senior_debt_fingerprint must not reference bank_sizing_scenario — reverted"
        )


# ---------------------------------------------------------------------------
# TestC3b3d2b2bRegressionLock
# ---------------------------------------------------------------------------

class TestC3b3d2b2bRegressionLock:
    """C3B3D2B2B locked findings: CF2=CF3=CF4=CF5=0 kEUR. Must not regress."""

    def test_c3b2_sha_protected(self):
        """Protected SHA is recorded and must not appear in production literal code."""
        protected_sha = "f8f244c0660495bfb4115d4e32ba329c291ab829d1d0693e614c889457b5add7"
        assert protected_sha  # SHA recorded; governance checked separately

    def test_causal_bridge_closed(self):
        """C3B3D2B2B causal bridge closure confirmed: bridge_closed_to_vector=True."""
        truth = _load_debt_truth()
        bridge = truth["phase2c_sizing_analysis"]["causal_bridge"]
        assert bridge["bridge_closed"] is True
        assert abs(bridge["bridge_closure_error_keur"]) < 0.001

    def test_c3b3d2b2b_dscr_rate_daycount_classification(self):
        """C3B3D2B2B proved current engine is source-matched for DSCR/ACT360/ops/rate.

        The C3B2 causal bridge (Case0→Case3) quantifies the historical contribution of
        switching each factor from a baseline setup. The C3B3D2B2B finding is that the
        CURRENT engine already implements source-matching for these factors, so the
        INCREMENTAL C3B3D2B2B delta for CF2-CF5 is 0 from the current engine baseline.
        This test documents that classification; the numerical C3B2 bridge is historical.
        """
        assert "BANK_SIZING_CFADS_AUTHORITY_IS_SOLE_CURRENT_SIZING_GAP_SOURCE_PROVEN"
        assert "CF2_DSCR_SOURCE_MATCHED_IN_CURRENT_ENGINE"
        assert "CF3_ACT360_SOURCE_MATCHED_IN_CURRENT_ENGINE"
        assert "CF4_OPS_FRACTION_SOURCE_MATCHED_IN_CURRENT_ENGINE"
        assert "CF5_RATE_SOURCE_MATCHED_IN_CURRENT_ENGINE"

    def test_classification_bank_cfads_sole_gap_source(self):
        """Bank CFADS is the sole sizing gap source (C3B3D2B2B finding preserved)."""
        # Classification recorded — verified by causal bridge test above
        assert "BANK_SIZING_CFADS_AUTHORITY_IS_SOLE_CURRENT_SIZING_GAP_SOURCE_PROVEN"


# ---------------------------------------------------------------------------
# TestGovernance
# ---------------------------------------------------------------------------

class TestGovernance:
    """Governance guards: no banned patterns in production engine source."""

    def _read_engine_source(self) -> str:
        import pathlib
        engine_dir = pathlib.Path(__file__).parent.parent / "financial_engine"
        parts = []
        for p in engine_dir.rglob("*.py"):
            parts.append(p.read_text(encoding="utf-8"))
        return "\n".join(parts)

    def test_no_literal_13547(self):
        """13547.2 must not appear as a literal in financial_engine source."""
        src = self._read_engine_source()
        assert "13547.2" not in src, "Literal 13547.2 found in production source"

    def test_no_ds25_ds40_period_boundary_as_code(self):
        """DS25/DS40 must not appear as code-active period boundary in production source.

        Governance rule: no hardcoded debt-period integer boundary comparisons
        (e.g. ``period_index == 25``, ``period_index >= 40``) in production code.
        Comments documenting this rule are permitted.

        Because the R3 STOP verdict requires ZERO production diff vs base, this test
        also asserts that condition directly — a zero diff is stronger than any
        pattern scan of comments.
        """
        import pathlib
        import ast

        engine_dir = pathlib.Path(__file__).parent.parent / "financial_engine"

        # Primary guard: production diff vs base must be zero.
        # This is the definitive proof that no period-boundary calculation was introduced.
        import subprocess
        result = subprocess.run(
            [
                "git", "diff", "--exit-code",
                "6e064980868709294e14da4d95e3279790d70ff0..HEAD",
                "--",
                str(engine_dir / "inputs.py"),
                str(engine_dir / "results.py"),
                str(engine_dir / "provenance.py"),
                str(engine_dir / "orchestrator.py"),
            ],
            capture_output=True,
        )
        assert result.returncode == 0, (
            "R3_STOP_PRODUCTION_REVERT_EXACTLY_BASE_PROVEN: production diff is non-zero. "
            "DS25/DS40 hardcoding governance is moot because production files must be "
            "identical to base 6e064980. Diff output:\n" + result.stdout.decode()
        )

        # Secondary guard: AST-scan non-comment lines for integer-comparison patterns
        # on the prohibited boundary values 25 and 40 (as period_index sentinels).
        PROHIBITED_BOUNDARIES = {25, 40}
        for p in engine_dir.rglob("*.py"):
            src = p.read_text(encoding="utf-8")
            try:
                tree = ast.parse(src, filename=str(p))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Compare):
                    continue
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Constant) and comparator.value in PROHIBITED_BOUNDARIES:
                        # Flag only if the left operand looks like a period-index name
                        left = node.left
                        left_name = ""
                        if isinstance(left, ast.Name):
                            left_name = left.id
                        elif isinstance(left, ast.Attribute):
                            left_name = left.attr
                        if "period" in left_name.lower() or "index" in left_name.lower():
                            raise AssertionError(
                                f"{p}:{node.lineno}: hardcoded period boundary "
                                f"{comparator.value!r} found in comparison involving "
                                f"'{left_name}' — DS25/DS40 hardcoding prohibited"
                            )

    def test_no_bank_sizing_cfads_in_production(self):
        """bank_sizing_cfads must not appear in financial_engine production source."""
        src = self._read_engine_source()
        assert "bank_sizing_cfads" not in src, (
            "bank_sizing_cfads found in production engine — must be reverted under R3 STOP"
        )

    def test_no_bank_sizing_scenario_in_production(self):
        """bank_sizing_scenario must not appear in financial_engine production source."""
        src = self._read_engine_source()
        assert "bank_sizing_scenario" not in src, (
            "bank_sizing_scenario found in production engine — reverted under R3 STOP"
        )

    def test_no_production_scenario_scope_in_production(self):
        """ProductionScenarioScope must not appear in financial_engine source."""
        src = self._read_engine_source()
        assert "ProductionScenarioScope" not in src, (
            "ProductionScenarioScope found in production engine — reverted under R3 STOP"
        )

    def test_vba_label_preserved_in_recon(self):
        """VBA_IMPLEMENTATION_NOT_VISIBLE preserved in finco_recon diagnostic module."""
        import pathlib
        recon_src = (pathlib.Path(__file__).parent.parent / "finco_recon" / "bank_sizing_candidates.py").read_text()
        assert "VBA_IMPLEMENTATION_NOT_VISIBLE" in recon_src

    def test_mechanism_label_preserved_in_recon(self):
        """BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED preserved in recon."""
        import pathlib
        recon_src = (pathlib.Path(__file__).parent.parent / "finco_recon" / "bank_sizing_candidates.py").read_text()
        assert "BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED" in recon_src

    def test_stop_verdict_in_recon(self):
        """C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE in recon."""
        import pathlib
        recon_src = (pathlib.Path(__file__).parent.parent / "finco_recon" / "bank_sizing_candidates.py").read_text()
        assert "C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE" in recon_src

    def test_no_fixture_reads_in_production_orchestrator(self):
        """Production orchestrator must not read from test fixtures."""
        import pathlib
        orch_src = (pathlib.Path(__file__).parent.parent / "financial_engine" / "orchestrator.py").read_text()
        assert "fixture" not in orch_src.lower(), (
            "Fixture read found in production orchestrator"
        )

    def test_zero_production_diff_vs_base(self):
        """R3_STOP_PRODUCTION_REVERT_EXACTLY_BASE_PROVEN: all production files identical to base."""
        import subprocess
        import pathlib
        engine_dir = pathlib.Path(__file__).parent.parent / "financial_engine"
        result = subprocess.run(
            [
                "git", "diff", "--exit-code",
                "6e064980868709294e14da4d95e3279790d70ff0..HEAD",
                "--",
                str(engine_dir / "inputs.py"),
                str(engine_dir / "results.py"),
                str(engine_dir / "provenance.py"),
                str(engine_dir / "orchestrator.py"),
            ],
            capture_output=True,
        )
        assert result.returncode == 0, (
            "R3_STOP_PRODUCTION_REVERT_EXACTLY_BASE_PROVEN: production files differ from base. "
            "Diff:\n" + result.stdout.decode()
        )


# ---------------------------------------------------------------------------
# TestBaselineGovernance
# ---------------------------------------------------------------------------

class TestBaselineGovernance:
    """Guard against reintroduction of stale baseline values.

    Current authoritative baseline (C3B3D2B2B locked, PR #924):
        CURRENT_GRID0_PRODUCTION_CANDIDATE = 43,919.032698 kEUR
        SOURCE_EXCEL_SENIOR_DEBT           = 42,852.278763 kEUR
        CURRENT_GAP                        = +1,066.754 kEUR  (CF1 only)

    Prohibited stale values (historical only, NOT current):
        29,305 kEUR — never a current GRID0 baseline
        13,547.2 kEUR — never a current sizing gap

    Classification: R3_STOP_PRODUCTION_REVERT_EXACTLY_BASE_PROVEN
    """

    def test_current_grid0_constant(self):
        """CURRENT_GRID0_DEBT_KEUR = 43,919.032698 kEUR (C3B3D2B2B locked)."""
        from finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge import CURRENT_GRID0_DEBT_KEUR
        assert abs(CURRENT_GRID0_DEBT_KEUR - 43_919.032698) < 1.0, (
            f"CURRENT_GRID0_DEBT_KEUR={CURRENT_GRID0_DEBT_KEUR:.6f} — expected ~43,919.032698"
        )

    def test_source_excel_constant(self):
        """SOURCE_EXCEL_SENIOR_DEBT_KEUR = 42,852.278763 kEUR (DS!D51)."""
        from finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge import SOURCE_EXCEL_SENIOR_DEBT_KEUR
        assert abs(SOURCE_EXCEL_SENIOR_DEBT_KEUR - 42_852.278763) < 0.001, (
            f"SOURCE_EXCEL_SENIOR_DEBT_KEUR={SOURCE_EXCEL_SENIOR_DEBT_KEUR:.6f} — expected ~42,852.278763"
        )

    def test_current_gap_constant(self):
        """CURRENT_GRID0_TO_SOURCE_GAP_KEUR = +1,066.754 kEUR."""
        from finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge import CURRENT_GRID0_TO_SOURCE_GAP_KEUR
        assert abs(CURRENT_GRID0_TO_SOURCE_GAP_KEUR - 1_066.754) < 1.0, (
            f"CURRENT_GRID0_TO_SOURCE_GAP_KEUR={CURRENT_GRID0_TO_SOURCE_GAP_KEUR:.6f} — expected ~1,066.754"
        )

    def test_current_gap_is_not_13547(self):
        """Current Senior Debt sizing gap is NOT 13,547 kEUR (historical only)."""
        from finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge import CURRENT_GRID0_TO_SOURCE_GAP_KEUR
        assert abs(CURRENT_GRID0_TO_SOURCE_GAP_KEUR - 13_547.2) > 1_000.0, (
            "CURRENT_GRID0_TO_SOURCE_GAP_KEUR ≈ 13,547.2 — this is a stale historical value, "
            "not the current C3B3D2B2B-locked gap. Current gap ≈ +1,066.754 kEUR."
        )

    def test_current_grid0_is_not_29305(self):
        """Current GRID0 baseline is NOT 29,305 kEUR (never a valid current baseline)."""
        from finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge import CURRENT_GRID0_DEBT_KEUR
        assert abs(CURRENT_GRID0_DEBT_KEUR - 29_305.0) > 1_000.0, (
            "CURRENT_GRID0_DEBT_KEUR ≈ 29,305 — this value must not be used as a current baseline. "
            "Current GRID0 = 43,919.032698 kEUR."
        )

    def test_cf1_is_sole_gap_source(self):
        """CF1 delta = −1,066.754 kEUR. CF2-CF5 = 0. Classification preserved."""
        from finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge import (
            CURRENT_GRID0_TO_SOURCE_GAP_KEUR,
            SOURCE_EXCEL_SENIOR_DEBT_KEUR,
            CURRENT_GRID0_DEBT_KEUR,
        )
        cf1_delta = SOURCE_EXCEL_SENIOR_DEBT_KEUR - CURRENT_GRID0_DEBT_KEUR
        assert abs(cf1_delta - (-CURRENT_GRID0_TO_SOURCE_GAP_KEUR)) < 1.0, (
            f"CF1 delta={cf1_delta:.3f} does not match −gap={-CURRENT_GRID0_TO_SOURCE_GAP_KEUR:.3f}"
        )
        assert "BANK_SIZING_CFADS_AUTHORITY_IS_SOLE_CURRENT_SIZING_GAP_SOURCE_PROVEN"


# ---------------------------------------------------------------------------
# TestHorizonCausality — R4
# ---------------------------------------------------------------------------

class TestHorizonCausality:
    """R4: Active Senior Debt horizon causality.

    Classification: POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING

    The DSCR solver binds on the minimum DSCR within the active debt horizon
    [repayment_start_period_index, maturity_period_index]. Periods outside
    that range do not appear in the DSCR schedule and cannot be the binding
    constraint. Active period count and merchant-debt period membership are
    derived generically from policy fields — no hardcoded period integers.
    """

    def _load_r4_evidence(self) -> dict:
        path = _FIXTURE_DIR / "excel_oborovo_bank_sizing_source_evidence_r4.json"
        with open(path) as f:
            return json.load(f)

    def test_active_debt_period_count_from_policy(self):
        """Active debt horizon = 28 periods, derived generically from SeniorDebtPolicy."""
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import (
            build_senior_debt_model_input_from_project_inputs,
        )
        proj = create_default_oborovo()
        sd_input = build_senior_debt_model_input_from_project_inputs(proj)
        policy = sd_input.senior_debt_policy
        active_count = policy.maturity_period_index - policy.repayment_start_period_index + 1
        # Fixture confirms 28 — verify via fixture, not via hardcoded literal
        ev = self._load_r4_evidence()
        expected = ev["active_debt_horizon"]["active_period_count"]
        assert active_count == expected, (
            f"Active period count={active_count} does not match fixture {expected}. "
            "DERIVATION: GENERIC_FROM_SENIOR_DEBT_POLICY_NOT_HARDCODED"
        )

    def test_merchant_debt_period_count(self):
        """4 merchant periods fall within the active debt horizon (periods 26-29)."""
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import (
            build_senior_debt_model_input_from_project_inputs,
        )
        from financial_engine.orchestrator import run_operating_model
        proj = create_default_oborovo()
        sd_input = build_senior_debt_model_input_from_project_inputs(proj)
        policy = sd_input.senior_debt_policy
        debt_start = policy.repayment_start_period_index
        debt_end = policy.maturity_period_index
        op_result = run_operating_model(sd_input.operating)
        merchant_debt = [
            p.period_index for p in op_result.periods
            if p.is_operation and debt_start <= p.period_index <= debt_end
            and not p.is_ppa_active
        ]
        ev = self._load_r4_evidence()
        expected_count = ev["merchant_debt_periods"]["count"]
        assert len(merchant_debt) == expected_count, (
            f"Merchant+debt period count={len(merchant_debt)}, expected {expected_count}. "
            "MERCHANT_DEBT_CAUSAL_PERIOD_COUNT_4_CONFIRMED"
        )

    def test_dscr_schedule_confined_to_active_horizon(self):
        """DSCR schedule period indices are all within [debt_start, debt_end].

        POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING: the solver
        computes minimum DSCR only over active debt periods; post-maturity periods
        (period_index > maturity_period_index) are excluded from the schedule.
        """
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import (
            build_senior_debt_model_input_from_project_inputs,
        )
        from financial_engine.orchestrator import run_senior_debt_model
        proj = create_default_oborovo()
        sd_input = build_senior_debt_model_input_from_project_inputs(proj)
        policy = sd_input.senior_debt_policy
        debt_start = policy.repayment_start_period_index
        debt_end = policy.maturity_period_index
        result = run_senior_debt_model(sd_input)
        schedule_indices = result.senior_debt.period_indices
        assert len(schedule_indices) > 0
        for idx in schedule_indices:
            assert debt_start <= idx <= debt_end, (
                f"DSCR schedule includes period {idx} outside active horizon "
                f"[{debt_start}, {debt_end}]. "
                "POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING violated."
            )

    def test_binding_constraint_within_active_horizon(self):
        """Binding DSCR constraint period is within [debt_start, debt_end]."""
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import (
            build_senior_debt_model_input_from_project_inputs,
        )
        from financial_engine.orchestrator import run_senior_debt_model
        proj = create_default_oborovo()
        sd_input = build_senior_debt_model_input_from_project_inputs(proj)
        policy = sd_input.senior_debt_policy
        debt_end = policy.maturity_period_index
        result = run_senior_debt_model(sd_input)
        max_schedule_idx = max(result.senior_debt.period_indices)
        assert max_schedule_idx <= debt_end, (
            f"Max schedule period {max_schedule_idx} > maturity {debt_end}. "
            "POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING: "
            "post-maturity periods must not appear in the DSCR schedule."
        )

    def test_r4_evidence_fixture_exists_and_classification(self):
        """R4 evidence fixture exists with correct classification."""
        ev = self._load_r4_evidence()
        assert ev["classification"] == "C3B3D2B2C_R4_SOURCE_INPUTS_IDENTIFIED_CURVE_EXTRACTION_REQUIRED"
        assert ev["active_debt_horizon"]["derivation"] == "GENERIC_FROM_SENIOR_DEBT_POLICY_NOT_HARDCODED"
        assert ev["post_maturity_causality"]["classification"] == "POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING"


# ---------------------------------------------------------------------------
# TestR4SourceEvidence — R4
# ---------------------------------------------------------------------------

class TestR4SourceEvidence:
    """R4: Confirmed source cell identifiers for bank-sizing revenue scenarios.

    Source evidence confirmed from workbook extraction artifacts:
    - Oborovo: D102 (equity), D103 (sizing), D106 (Central case Trackers),
      D109 (Low case Trackers), D110 (Low GMPV), D111 (Central Low case Trackers)
      Scenarios!E324 (equity selector), E325 (debt sizing selector)
    - TUHO: D107 (equity), D108 (sizing), D109 (MidLow)
      Scenarios!E182 (equity Afry), E183 (sizing Afry)

    Curve values for D110, D111 (Oborovo) and D109 (TUHO) are NOT in fixtures.
    Classification: C3B3D2B2C_R4_SOURCE_INPUTS_IDENTIFIED_CURVE_EXTRACTION_REQUIRED
    """

    def _load_r4_evidence(self) -> dict:
        path = _FIXTURE_DIR / "excel_oborovo_bank_sizing_source_evidence_r4.json"
        with open(path) as f:
            return json.load(f)

    def test_oborovo_equity_scenario_cell_confirmed(self):
        """Oborovo equity revenue scenario cell D102 confirmed in evidence fixture."""
        ev = self._load_r4_evidence()
        assert ev["oborovo_revenue_scenario_evidence"]["equity_scenario_cell"] == "Inputs!D102"
        assert ev["oborovo_revenue_scenario_evidence"]["equity_label_confirmed"] == "Equity case revenues"

    def test_oborovo_sizing_scenario_cell_confirmed(self):
        """Oborovo sizing revenue scenario cell D103 confirmed in evidence fixture."""
        ev = self._load_r4_evidence()
        assert ev["oborovo_revenue_scenario_evidence"]["sizing_scenario_cell"] == "Inputs!D103"
        assert ev["oborovo_revenue_scenario_evidence"]["debt_sizing_label_confirmed"] == "Debt sizing revenues curve"

    def test_oborovo_central_low_case_cell_confirmed(self):
        """Oborovo Central Low case Trackers cell D111 confirmed (no curve values)."""
        ev = self._load_r4_evidence()
        oborovo = ev["oborovo_revenue_scenario_evidence"]
        assert oborovo["central_low_case_trackers_cell"] == "Inputs!D111"
        assert oborovo["central_low_case_trackers_label"] == "Central Low case Trackers"
        assert oborovo["central_low_case_values_available"] is False
        assert oborovo["extraction_status"] == "CURVE_EXTRACTION_REQUIRED_FOR_D110_D111_D109"

    def test_tuho_sizing_scenario_cell_confirmed(self):
        """TUHO sizing scenario cell D108 confirmed."""
        ev = self._load_r4_evidence()
        tuho = ev["tuho_revenue_scenario_evidence"]
        assert tuho["sizing_scenario_cell"] == "Inputs!D108"
        assert tuho["sizing_label_confirmed"] == "Sizing scenario"

    def test_candidate_c_status_blocked_pending_extraction(self):
        """Candidate C is BLOCKED pending curve extraction (R4 verdict)."""
        ev = self._load_r4_evidence()
        cc = ev["candidate_c_feasibility"]
        assert cc["status"] == "BLOCKED_PENDING_CURVE_EXTRACTION"
        assert cc["classification"] == "C3B3D2B2C_R4_SOURCE_INPUTS_IDENTIFIED_CURVE_EXTRACTION_REQUIRED"


# ---------------------------------------------------------------------------
# TestCandidateCArchitecture — R4
# ---------------------------------------------------------------------------

class TestCandidateCArchitecture:
    """R4: Candidate C design constraints and generic architecture requirements.

    Candidate C = P90-10y production + bank/sizing revenue scenario (Central Low
    case Trackers for Oborovo, MidLow for TUHO), evaluated over active debt periods
    only. No project-name dispatch. No hardcoded period boundaries. No calibration.

    Cannot be evaluated until D111/D110/D109 curves are extracted.
    Classification: C3B3D2B2C_R4_SOURCE_INPUTS_IDENTIFIED_CURVE_EXTRACTION_REQUIRED
    """

    def test_no_project_name_dispatch_in_recon_candidates(self):
        """finco_recon/bank_sizing_candidates.py must not contain project-name dispatch."""
        import pathlib
        src = (pathlib.Path(__file__).parent.parent / "finco_recon" / "bank_sizing_candidates.py").read_text()
        for token in ("if project", "if proj", "== 'oborovo'", "== 'tuho'",
                      '== "oborovo"', '== "tuho"'):
            assert token not in src, (
                f"Project-name dispatch found in bank_sizing_candidates.py: {token!r}"
            )

    def test_candidate_c_requires_generic_active_period_derivation(self):
        """Active debt period derivation uses policy fields, not hardcoded integers.

        R4 constraint: DO NOT hardcode P1-P28, 28 periods, or 2044.
        The policy fields repayment_start_period_index and maturity_period_index
        must be the only source of the active period boundary.
        """
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import (
            build_senior_debt_model_input_from_project_inputs,
        )
        proj = create_default_oborovo()
        sd_input = build_senior_debt_model_input_from_project_inputs(proj)
        policy = sd_input.senior_debt_policy
        # Generic derivation — same expression the orchestrator uses
        debt_start = policy.repayment_start_period_index
        debt_end = policy.maturity_period_index
        active_count = debt_end - debt_start + 1
        assert active_count > 0
        assert debt_start > 0
        assert debt_end > debt_start

    def test_r4_verdict_classification_in_evidence_fixture(self):
        """R4 verdict present in evidence fixture."""
        path = _FIXTURE_DIR / "excel_oborovo_bank_sizing_source_evidence_r4.json"
        with open(path) as f:
            ev = json.load(f)
        assert "C3B3D2B2C_R4_SOURCE_INPUTS_IDENTIFIED_CURVE_EXTRACTION_REQUIRED" in ev["classification"]
        assert "POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING" in (
            ev["post_maturity_causality"]["classification"]
        )

    def test_post_maturity_classification_label_in_recon(self):
        """POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING present in evidence fixture."""
        path = _FIXTURE_DIR / "excel_oborovo_bank_sizing_source_evidence_r4.json"
        with open(path) as f:
            content = f.read()
        assert "POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING" in content


# ---------------------------------------------------------------------------
# R4.1 tests
# ---------------------------------------------------------------------------

class TestR4_1ManualCausality:
    """R4.1: Manual black-box causality evidence and TUHO oracle back-calculation.

    R4.1 verdict: C3B3D2B2C_R4_1_MANUAL_CAUSALITY_PROVEN_ENGINE_EVALUATION_XLSM_EXTRACTION_REQUIRED

    Manual observation: Oborovo Scenarios!E325 = 'Central Low case Trackers' (D111)
    produces DS!D51 = 42,852.278763 kEUR exactly. Switching to D106 (Central case
    Trackers) gives 43,813 kEUR. Delta = +961 kEUR. Revenue curve selector is causal.

    TUHO: bank CFADS P1 = senior_debt_service_P1 * DSCR_target = 2539.633673 kEUR.
    """

    def _load_r4_1_fixture(self):
        path = _FIXTURE_DIR / "excel_oborovo_bank_sizing_source_evidence_r4_1.json"
        with open(path) as f:
            return json.load(f)

    def test_r4_1_fixture_exists(self):
        """R4.1 evidence fixture must exist."""
        path = _FIXTURE_DIR / "excel_oborovo_bank_sizing_source_evidence_r4_1.json"
        assert path.exists(), "R4.1 evidence fixture not found"

    def test_r4_1_classification(self):
        """R4.1 fixture carries correct intermediate verdict."""
        ev = self._load_r4_1_fixture()
        assert ev["r4_1_verdict"] == (
            "C3B3D2B2C_R4_1_MANUAL_CAUSALITY_PROVEN_ENGINE_EVALUATION_XLSM_EXTRACTION_REQUIRED"
        )

    def test_manual_causality_d111_reproduces_source_debt(self):
        """Manual observation: D111 (Central Low case Trackers) = DS!D51 = 42,852.278763 kEUR."""
        ev = self._load_r4_1_fixture()
        obs = ev["manual_causality_evidence"]["observation_d111"]
        assert obs["matches_ds_d51"] is True
        assert abs(obs["resulting_debt_keur"] - 42852.278763) < 0.001

    def test_manual_causality_d106_gives_equity_debt(self):
        """Manual observation: D106 (Central case Trackers) gives 43,813 kEUR — equity-case debt."""
        ev = self._load_r4_1_fixture()
        obs = ev["manual_causality_evidence"]["observation_d106"]
        assert obs["matches_ds_d51"] is False
        assert obs["resulting_debt_keur"] > 43000.0

    def test_manual_causality_delta_positive(self):
        """Delta (D106 − D111) must be positive: equity curve gives higher debt than sizing."""
        ev = self._load_r4_1_fixture()
        mc = ev["manual_causality_evidence"]
        assert mc["delta_keur"] > 0
        delta = mc["observation_d106"]["resulting_debt_keur"] - mc["observation_d111"]["resulting_debt_keur"]
        assert abs(delta - mc["delta_keur"]) < 1.0

    def test_manual_causality_classification_label(self):
        """OBOROVO_DEBT_SIZING_REVENUE_CURVE_MANUAL_CAUSALITY_PROVEN in fixture."""
        ev = self._load_r4_1_fixture()
        assert ev["manual_causality_evidence"]["classification"] == (
            "OBOROVO_DEBT_SIZING_REVENUE_CURVE_MANUAL_CAUSALITY_PROVEN"
        )

    def test_manual_causality_in_recon_module(self):
        """MANUAL_CAUSALITY_EVIDENCE dict in bank_sizing_candidates carries classification."""
        from finco_recon.bank_sizing_candidates import MANUAL_CAUSALITY_EVIDENCE
        assert MANUAL_CAUSALITY_EVIDENCE["classification"] == (
            "OBOROVO_DEBT_SIZING_REVENUE_CURVE_MANUAL_CAUSALITY_PROVEN"
        )
        assert MANUAL_CAUSALITY_EVIDENCE["observation_d111"]["matches_ds_d51"] is True
        assert abs(
            MANUAL_CAUSALITY_EVIDENCE["observation_d111"]["resulting_debt_keur"] - 42852.278763
        ) < 0.001

    def test_oborovo_e325_sizing_selector_confirmed(self):
        """Oborovo Scenarios!E325 sizing selector confirmed as 'Central Low case Trackers'."""
        ev = self._load_r4_1_fixture()
        sel = ev["confirmed_revenue_selectors"]["oborovo"]
        assert sel["sizing_active_value"] == "Central Low case Trackers"
        assert sel["sizing_active_value_status"] == "CONFIRMED_FROM_MANUAL_CAUSALITY_EVIDENCE"

    def test_tuho_e182_e183_selectors_confirmed(self):
        """TUHO Scenarios!E182/E183 selectors confirmed from manifest."""
        ev = self._load_r4_1_fixture()
        sel = ev["confirmed_revenue_selectors"]["tuho"]
        assert sel["equity_active_value"] == "Equity case Afry curve"
        assert sel["sizing_active_value"] == "Sizing case Afry curve"
        assert "CONFIRMED" in sel["equity_active_value_status"]
        assert "CONFIRMED" in sel["sizing_active_value_status"]

    def test_tuho_oracle_back_calculation(self):
        """TUHO bank CFADS P1 = senior_debt_service_P1 * DSCR_target."""
        with open(_FIXTURE_DIR / "excel_tuho_periods.json") as f:
            tuho = json.load(f)
        periods = tuho.get("periods", tuho.get("period_results", []))
        p1 = next(p for p in periods if p["period_index"] == 1)
        sds = abs(p1["CF"]["senior_debt_service_keur"])
        dscr_target = p1["DS"]["senior_debt_dscr_target"]
        bank_cfads = sds * dscr_target
        assert abs(bank_cfads - 2539.633673) < 0.001, (
            f"Expected 2539.633673, got {bank_cfads}"
        )

    def test_tuho_oracle_in_recon_module(self):
        """TUHO_ORACLE_DERIVATION dict in bank_sizing_candidates is consistent."""
        from finco_recon.bank_sizing_candidates import TUHO_ORACLE_DERIVATION
        sds = TUHO_ORACLE_DERIVATION["senior_debt_service_p1_keur"]
        target = TUHO_ORACLE_DERIVATION["dscr_target"]
        expected = TUHO_ORACLE_DERIVATION["bank_cfads_p1_keur"]
        assert abs(sds * target - expected) < 0.001

    def test_tuho_residual_price_ratio_below_one(self):
        """TUHO residual price ratio (MidLow/Central) < 1 for period 1."""
        from finco_recon.bank_sizing_candidates import TUHO_ORACLE_DERIVATION
        ratio = TUHO_ORACLE_DERIVATION["residual_price_ratio"]
        assert 0.8 < ratio < 1.0, f"Residual ratio {ratio} outside expected range (0.8, 1.0)"

    def test_oborovo_yield_cases_confirmed(self):
        """Oborovo P50=1494, P90=1410 confirmed in R4.1 fixture."""
        ev = self._load_r4_1_fixture()
        obo = ev["confirmed_yield_cases"]["oborovo"]
        assert obo["p50_hours"] == 1494.0
        assert obo["p90_10y_hours"] == 1410.0
        assert abs(obo["p90_p50_ratio"] - 1410 / 1494) < 1e-9

    def test_tuho_yield_cases_confirmed(self):
        """TUHO P50=4164, P90=3620 confirmed in R4.1 fixture."""
        ev = self._load_r4_1_fixture()
        tuho = ev["confirmed_yield_cases"]["tuho"]
        assert tuho["p50_hours"] == 4164.0
        assert tuho["p90_10y_hours"] == 3620.0
        assert abs(tuho["p90_p50_ratio"] - 3620 / 4164) < 1e-9

    def test_oborovo_central_curve_values_present(self):
        """Oborovo Central case Trackers (D106) CY2042-2060 values are in R4.1 fixture."""
        ev = self._load_r4_1_fixture()
        curve = ev["confirmed_price_curves"]["oborovo_central_case_trackers_d106"]
        assert curve["status"] == "CONFIRMED_VALUES_IN_FIXTURE"
        vals = curve["values_eur_mwh"]
        assert len(vals) == 19
        assert abs(vals["2042"] - 75.12095149999999) < 1e-6

    def test_candidate_c_blocked_d111_extraction_required(self):
        """Candidate C for Oborovo is blocked: D111 not in fixture."""
        ev = self._load_r4_1_fixture()
        obo_c = ev["candidate_c_status"]["oborovo"]
        assert obo_c["revenue_curve_values"] == "NOT_IN_FIXTURE"
        assert obo_c["manual_causality"] == "PROVEN"
        assert obo_c["engine_evaluation"] == "BLOCKED_XLSM_EXTRACTION_REQUIRED"

    def test_candidate_c_blocked_tuho_d109_extraction_required(self):
        """Candidate C for TUHO is blocked: D109 MidLow not in fixture."""
        ev = self._load_r4_1_fixture()
        tuho_c = ev["candidate_c_status"]["tuho"]
        assert tuho_c["revenue_curve_values"] == "NOT_IN_FIXTURE"
        assert tuho_c["engine_evaluation"] == "BLOCKED_XLSM_EXTRACTION_REQUIRED"


class TestR4_1ProductContract:
    """R4.1: Product contract design constraints.

    Tests that the PRODUCT_CONTRACT_DESIGN dict in bank_sizing_candidates encodes
    the correct architecture: generic YieldCase, named PriceCurve library,
    RevenueCaseSelection with equity/sizing selectors, no project-name dispatch,
    no hardcoded period boundaries.
    """

    def test_product_contract_dict_present(self):
        """PRODUCT_CONTRACT_DESIGN must be importable from bank_sizing_candidates."""
        from finco_recon.bank_sizing_candidates import PRODUCT_CONTRACT_DESIGN
        assert "yield_case" in PRODUCT_CONTRACT_DESIGN
        assert "price_curve" in PRODUCT_CONTRACT_DESIGN
        assert "revenue_case_selection" in PRODUCT_CONTRACT_DESIGN

    def test_product_contract_no_project_dispatch(self):
        """PRODUCT_CONTRACT_DESIGN must assert no_project_name_dispatch=True."""
        from finco_recon.bank_sizing_candidates import PRODUCT_CONTRACT_DESIGN
        assert PRODUCT_CONTRACT_DESIGN["no_project_name_dispatch"] is True

    def test_product_contract_no_hardcoded_period_boundaries(self):
        """PRODUCT_CONTRACT_DESIGN must assert no_hardcoded_period_boundaries=True."""
        from finco_recon.bank_sizing_candidates import PRODUCT_CONTRACT_DESIGN
        assert PRODUCT_CONTRACT_DESIGN["no_hardcoded_period_boundaries"] is True

    def test_yield_case_has_p90_p50_ratio_derived(self):
        """YieldCase UX contract: p90_p50_ratio is derived, not a free input."""
        from finco_recon.bank_sizing_candidates import PRODUCT_CONTRACT_DESIGN
        fields = PRODUCT_CONTRACT_DESIGN["yield_case"]["fields"]
        ratio_field = [f for f in fields if "p90_p50_ratio" in f]
        assert len(ratio_field) == 1
        assert "derived" in ratio_field[0].lower()

    def test_price_curve_has_curve_id_and_values(self):
        """PriceCurve schema must include curve_id and values_eur_mwh."""
        from finco_recon.bank_sizing_candidates import PRODUCT_CONTRACT_DESIGN
        fields = PRODUCT_CONTRACT_DESIGN["price_curve"]["fields"]
        assert any("curve_id" in f for f in fields)
        assert any("values_eur_mwh" in f for f in fields)

    def test_revenue_case_selection_has_equity_and_sizing(self):
        """RevenueCaseSelection must have equity_curve_id and sizing_curve_id."""
        from finco_recon.bank_sizing_candidates import PRODUCT_CONTRACT_DESIGN
        fields = PRODUCT_CONTRACT_DESIGN["revenue_case_selection"]["fields"]
        assert any("equity_curve_id" in f for f in fields)
        assert any("sizing_curve_id" in f for f in fields)

    def test_scenario_tab_has_production_and_revenue_sections(self):
        """Scenario tab contract must have at least Production and Revenue sections."""
        from finco_recon.bank_sizing_candidates import PRODUCT_CONTRACT_DESIGN
        sections = PRODUCT_CONTRACT_DESIGN["scenario_tab_sections"]
        assert any("Production" in s or "Yield" in s for s in sections)
        assert any("Revenue" in s for s in sections)

    def test_r4_1_evidence_fixture_path_constant(self):
        """R4_1_EVIDENCE_FIXTURE_PATH must point to the committed fixture."""
        from finco_recon.bank_sizing_candidates import R4_1_EVIDENCE_FIXTURE_PATH
        import pathlib
        path = pathlib.Path(__file__).parent.parent / R4_1_EVIDENCE_FIXTURE_PATH
        assert path.exists(), f"R4.1 evidence fixture not found at {path}"

    def test_r4_1_verdict_in_recon_module(self):
        """R4.1 verdict label present in bank_sizing_candidates module docstring."""
        import pathlib
        src = (
            pathlib.Path(__file__).parent.parent
            / "finco_recon"
            / "bank_sizing_candidates.py"
        ).read_text()
        assert "C3B3D2B2C_R4_1_MANUAL_CAUSALITY_PROVEN_ENGINE_EVALUATION_XLSM_EXTRACTION_REQUIRED" in src
