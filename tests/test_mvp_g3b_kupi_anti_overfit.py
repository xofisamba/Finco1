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

SOURCE WORKBOOK ISSUES:
  KUPI_SOURCE_BANK_REVENUE_BALANCING_OMISSION   SOURCE_WORKBOOK_ASYMMETRY_OR_INCONSISTENCY
  KUPI_CO2_UNUSED_TOGGLE                        SOURCE_INPUT_INCONSISTENCY

TRUE FINCO CAPABILITY GAPS:
  KUPI_SHL_CONSTRUCTION_COMPOUNDING_GAP         CURRENT_FINCO_CAPABILITY_GAP
  GENERIC_DYNAMIC_REVENUE_RATIO_DSCR_FORMULA_NOT_IMPLEMENTED  CURRENT_FINCO_CAPABILITY_GAP
  KUPI_PROJECT_DSCR_SCHEDULE_RESULT_REPRODUCED  (via explicit schedule; no KUPI schedule gap)
  KUPI_VAT_FACILITY                             UNSUPPORTED_INSTITUTIONAL_FEATURE

DEFINITION / COMPATIBILITY DIFFERENCES:
  KUPI_SPONSOR_CONTRIBUTION_TIMING_POLICY_GAP   DEFINITION_OR_TIMING_DIFFERENCE
  KUPI_TAX_WORKBOOK_COMPATIBILITY_GAP           CLEAN_POLICY_VS_WORKBOOK_COMPATIBILITY
  KUPI_SENIOR_GAP_RESIDUAL                      OPEN_SMALL_RESIDUAL (~0.34% of source Senior)

ENGINE_DERIVED_SHL_ADAPTER_HANDSHAKE_DIAGNOSTIC:
  The fixture uses a two-stage handshake to derive clean_shl_principal_keur
  from the engine's G2A fixed-point (not from the source Senior output).
  Source SHL 68,152.996 kEUR exists only as a comparison anchor.
  Engine-derived SHL: ≈79,595.855 kEUR (= Uses − Senior − Capital).

KUPI_SHL_CONSTRUCTION_COMPOUNDING_GAP (CURRENT_FINCO_CAPABILITY_GAP):
  Engine: simple interest, dcf=2.0 → PIK = engine_SHL × 8% × 2.0 ≈ 12,735 kEUR
  Source: compound interest → source_SHL × ((1.08)^2 − 1) = 11,341 kEUR
  (Different SHL principals: engine 79,596 vs source 68,153.)

  CROSS_BASIS_SHL_PIK_DIFFERENCE = 12,735 − 11,341 = +1,394.678 kEUR.
  This is NOT the pure method delta — it combines different SHL principals
  (caused by the Senior sizing gap) with the simple-vs-compound methodology.

  Pure methodology delta on SOURCE principal basis:
    Simple counterfactual:   68,153 × 8% × 2 = 10,904.479 kEUR
    Source compound PIK:     68,153 × ((1.08)^2 − 1) = 11,340.658 kEUR
    Delta (compound−simple): +436.179 kEUR   ← the pure capability gap

  Pure methodology delta on FINCO principal basis:
    Finco simple PIK:        79,596 × 8% × 2 = 12,735.337 kEUR
    Finco compound cf'fact:  79,596 × ((1.08)^2 − 1) ≈ 13,244.750 kEUR
    Delta (compound−simple): ≈+509.413 kEUR

  Do NOT use +1,394.678 as the method delta. Do NOT implement compound interest.

KUPI_SOURCE_BANK_REVENUE_BALANCING_OMISSION (SOURCE_WORKBOOK_ASYMMETRY_OR_INCONSISTENCY):
  GENERIC FINCO PRINCIPLE — balancing cost is a REVENUE-SIDE PROJECT INPUT.
  The same revenue stack (gross energy + CO2 − balancing) applies to both Base and Bank cases.
  The Bank case differs only in SCENARIO INPUTS (P90, price curve, DSCR target).
  Source DS Bank CFADS = P90_revenue − OPEX — balancing NOT deducted.
  No explicit lender evidence (term sheet, note, dedicated Bank balancing input) was found
  to prove this omission is deliberate policy. Classification: source workbook asymmetry.
  Literal Finco Senior: 135,707.583 kEUR | Source Senior: 147,150.442 kEUR
  Literal gap:          −11,442.860 kEUR
  No-bal diagnostic Senior: 147,649.261 kEUR | Bridge: +11,941.678 kEUR
  Residual after bridge:        +498.819 kEUR  →  KUPI_SENIOR_GAP_RESIDUAL  OPEN_SMALL_RESIDUAL
  (~0.34% of source Senior — do not tune away; do not add bank_balancing_cost input).

GENERIC_DYNAMIC_REVENUE_RATIO_DSCR_FORMULA_NOT_IMPLEMENTED (CURRENT_FINCO_CAPABILITY_GAP):
  Source DS!row13 = merchant_revenue / total_revenue (merchant_revenue_ratio).
  This ratio can EXCEED 100%: AF13 ≈ 1.030598, AH13 ≈ 1.031398.
  Do NOT call it "merchant_share" — it is not normalised.
  KUPI DSCR result reproduced via explicit schedule. Generic configurability gap only.
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

import pytest

from tests.helpers.g3b_kupi_project import (
    create_kupi_project,
    create_kupi_project_source_effective_co2,
    _KUPI_TOTAL_USES_KEUR,
    _KUPI_SOURCE_SHL_PRINCIPAL_KEUR,
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
    """G3B-A: No forbidden tokens, no factory import; semantic SHL input check."""

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

    def test_source_shl_not_used_as_blind_input(self):
        """Source SHL principal 68,152.996 must NOT drive engine SHL sizing.

        The engine's G2A fixed-point derives SHL from (Uses - Senior - Capital).
        The fixture's clean_shl_principal_keur must equal the engine-derived value,
        not the source Senior output residual (68,152.996 kEUR).
        """
        fr = _result().financing_result
        engine_derived_shl = fr.derived_shl_cash_principal_keur
        source_derived_shl = _KUPI_SOURCE_SHL_PRINCIPAL_KEUR  # 68,152.996

        # Engine-derived SHL ≠ source-derived SHL (Finco senior ≠ source senior)
        assert abs(engine_derived_shl - source_derived_shl) > 5_000, (
            f"Engine SHL {engine_derived_shl:.4f} ≈ source SHL {source_derived_shl:.4f}. "
            f"If Finco senior now matches source exactly, the fixture may be target-fitting "
            f"the Senior. Investigate before reducing this threshold."
        )

        # The fixture's configured SHL must match the engine-derived value (handshake proof)
        configured_shl = _proj().financing.clean_shl_principal_keur
        assert abs(configured_shl - engine_derived_shl) < 1.0, (
            f"ENGINE_DERIVED_SHL_ADAPTER_HANDSHAKE_DIAGNOSTIC FAIL: "
            f"configured SHL {configured_shl:.4f} != engine-derived {engine_derived_shl:.4f}. "
            f"The fixture must use the two-stage handshake, not a hardcoded source output."
        )

    def test_source_senior_not_hardcoded_as_input_in_capex_or_financing(self):
        """Source Senior 147,150 kEUR and source SHL 68,152 kEUR must not drive model inputs."""
        import ast, pathlib

        fixture = pathlib.Path("tests/helpers/g3b_kupi_project.py").read_text()
        tree = ast.parse(fixture)

        # Collect line numbers that are the direct RHS of a "_SOURCE_"-named assignment.
        # Those are legitimate comparison-anchor definitions, not model inputs.
        source_anchor_lines: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and "SOURCE" in tgt.id.upper():
                        for child in ast.walk(node.value):
                            if isinstance(child, ast.Constant) and isinstance(child.value, (int, float)):
                                source_anchor_lines.add(child.lineno)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and "SOURCE" in node.target.id.upper():
                    if node.value is not None:
                        for child in ast.walk(node.value):
                            if isinstance(child, ast.Constant) and isinstance(child.value, (int, float)):
                                source_anchor_lines.add(child.lineno)

        # Source output values must not appear as numeric constants outside their anchor definitions.
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                if node.lineno in source_anchor_lines:
                    continue  # This IS the anchor definition — allowed.
                val = float(node.value)
                # 147,150.xx is the source Senior commitment
                if abs(val - 147_150.442310) < 1.0:
                    raise AssertionError(
                        f"Source Senior 147150 appears as a NUMERIC constant at line "
                        f"{node.lineno} — it must not be used as a model input."
                    )
                # 68,152.xx is source SHL (= Uses - source_Senior - Capital)
                if abs(val - _KUPI_SOURCE_SHL_PRINCIPAL_KEUR) < 0.1:
                    raise AssertionError(
                        f"Source-derived SHL {val:.3f} appears as numeric constant at line "
                        f"{node.lineno} — must not drive engine SHL sizing."
                    )

    def test_kupi_not_registered_in_project_factory(self):
        """KUPI must not appear in any user-facing engine registry."""
        import ast, pathlib

        for pyfile in pathlib.Path("financial_engine").rglob("*.py"):
            src = pyfile.read_text(errors="replace")
            if "KUPI" not in src.upper():
                continue
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

    def test_shl_handshake_stage2_senior_unchanged(self):
        """ENGINE_DERIVED_SHL_ADAPTER_HANDSHAKE_DIAGNOSTIC proof.

        Stage 1 and Stage 2 must produce identical Senior, because the engine's
        fixed-point overrides clean_shl_principal_keur regardless of the input value.
        """
        from dataclasses import replace
        from financial_engine.financing import run_project_financing_model
        from financial_engine.shareholder_waterfall import run_project_shareholder_waterfall_model

        # Stage 1 result (already cached)
        senior_stage2 = _result().financing_result.final_senior_commitment_keur

        # Stage 1 with source-derived SHL as input (should give same senior)
        proj_source_shl = replace(
            _proj(),
            financing=replace(
                _proj().financing,
                clean_shl_principal_keur=_KUPI_SOURCE_SHL_PRINCIPAL_KEUR,
                shl_amount_keur=_KUPI_SOURCE_SHL_PRINCIPAL_KEUR,
            ),
        )
        result_source_shl = run_project_shareholder_waterfall_model(proj_source_shl)
        senior_source_shl = result_source_shl.financing_result.final_senior_commitment_keur

        assert abs(senior_stage2 - senior_source_shl) < 1e-4, (
            f"Handshake proof FAIL: Senior changed from {senior_source_shl:.6f} "
            f"to {senior_stage2:.6f} when switching from source-SHL input to engine-derived SHL. "
            f"This means the engine IS reading clean_shl_principal_keur as an input — "
            f"investigate the fixed-point implementation."
        )


# ── TestB  Period Axis ─────────────────────────────────────────────────────────


class TestB_PeriodAxis:
    """G3B-B: Period grid — 2 construction + 60 operating; senior 14yr × 2."""

    def test_shl_period_range(self):
        pmr = _result().financing_result.project_model_result
        pids = list(pmr.shareholder_loan.period_indices)
        assert pids[0] == 0
        assert pids[-1] == 61
        assert len(pids) == 62

    def test_senior_period_range(self):
        pmr = _result().financing_result.project_model_result
        pids = list(pmr.senior_debt.period_indices)
        assert pids[0] == 2
        assert pids[-1] == 29
        assert len(pids) == 28

    def test_operating_period_count_60(self):
        pmr = _result().financing_result.project_model_result
        ops_pids = list(pmr.operating_schedules.period_indices)
        op_count = sum(1 for p in ops_pids if p >= 2)
        assert op_count == 60


# ── TestC  G2A Identity ────────────────────────────────────────────────────────


class TestC_G2AIdentity:
    """G3B-C: Uses = Senior + Share Capital + Derived SHL."""

    def test_total_uses_matches_source(self):
        fr = _result().financing_result
        uses = fr.project_uses.total_project_uses_keur
        assert abs(uses - _KUPI_TOTAL_USES_KEUR) < 1.0, (
            f"Total uses {uses:.4f} kEUR deviates from source {_KUPI_TOTAL_USES_KEUR:.4f}"
        )

    def test_g2a_closure_identity(self):
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
        """Senior is below source — documented CLEAN_POLICY_VS_WORKBOOK_COMPATIBILITY gap."""
        fr = _result().financing_result
        senior = fr.final_senior_commitment_keur
        source_senior = 147_150.442310
        gap = senior - source_senior
        assert gap < -5_000, (
            f"Senior gap {gap:.2f} kEUR is not in expected negative range. "
            f"If source parity was achieved, update classification."
        )
        assert gap > -20_000, f"Senior gap {gap:.2f} kEUR is unexpectedly large."

    def test_binding_constraint_is_dscr(self):
        pmr = _result().financing_result.project_model_result
        assert pmr.senior_debt.binding_constraint == "DSCR"

    def test_engine_derived_shl_used_downstream(self):
        """Downstream SHL opening must equal engine-derived SHL + construction PIK."""
        fr = _result().financing_result
        shl = fr.project_model_result.shareholder_loan
        pids = list(shl.period_indices)
        shl_opening_p2 = shl.shl_opening_keur[pids.index(2)]
        derived_shl = fr.derived_shl_cash_principal_keur
        pik = fr.shl_construction_pik_keur
        expected_opening = derived_shl + pik
        assert abs(shl_opening_p2 - expected_opening) < 1.0, (
            f"SHL opening P2 {shl_opening_p2:.4f} != derived_SHL + PIK {expected_opening:.4f}"
        )


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
        assert abs(senior_orig - senior_r) < 1e-4, (
            f"Identity invariance FAIL: senior changed from {senior_orig:.6f} "
            f"to {senior_r:.6f} after rename."
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
    """G3B-E: Bank P90 < Base P50; bank CFADS ≤ base CFADS."""

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
        assert bank_prod[pid2_ds] < base_prod[pid2_ops]

    def test_p90_p50_ratio_consistent(self):
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
        assert abs(ratio - expected) < 0.01

    def test_bank_cfads_lt_base_cfads_operating(self):
        pmr = _result().financing_result.project_model_result
        ds = pmr.debt_sizing
        psc = pmr.post_senior_cash
        bank_cfads = list(ds.bank_cfads_keur)
        base_cfads = list(psc.base_cfads_keur)
        pids_ds = list(ds.period_indices)
        pids_psc = list(psc.period_indices)

        for pid in range(2, 30):
            if pid in pids_ds and pid in pids_psc:
                b = bank_cfads[pids_ds.index(pid)]
                base = base_cfads[pids_psc.index(pid)]
                assert b < base, (
                    f"Period {pid}: bank CFADS {b:.4f} >= base CFADS {base:.4f}"
                )

    def test_bank_cfads_balancing_gap_documented(self):
        """Bank CFADS gap at P2: source omits balancing cost that is part of project revenue.

        KUPI_SOURCE_BANK_REVENUE_BALANCING_OMISSION — SOURCE_WORKBOOK_ASYMMETRY_OR_INCONSISTENCY.
        Finco applies the same revenue stack (gross energy − balancing) in both Base and Bank cases.
        Source DS Bank CFADS omits the balancing deduction — no explicit lender policy evidence found.
        Source bank CFADS P2 anchor: 11,064.982 kEUR (from DS!H49 area).
        """
        pmr = _result().financing_result.project_model_result
        ds = pmr.debt_sizing
        bank_cfads = list(ds.bank_cfads_keur)
        bank_prod = list(ds.bank_production_mwh)
        pids = list(ds.period_indices)
        pid2 = pids.index(2)

        finco_bank_cfads_p2 = bank_cfads[pid2]
        source_bank_cfads_p2 = 11_064.982
        gap = finco_bank_cfads_p2 - source_bank_cfads_p2
        bal_cost_keur = bank_prod[pid2] * 5.0 / 1000

        # Residual after removing balancing should be small (< 250 kEUR)
        assert abs(gap + bal_cost_keur) < 250, (
            f"Bank CFADS gap {gap:.2f} not explained by balancing {bal_cost_keur:.2f}. "
            f"Residual {gap + bal_cost_keur:.2f}. Reclassify if a second cause found."
        )

    def test_balancing_bridge_closes_senior_gap(self):
        """Diagnostic: removing balancing from Bank CFADS explains the majority of the Senior gap.

        KUPI_SOURCE_BANK_REVENUE_BALANCING_OMISSION — SOURCE_WORKBOOK_ASYMMETRY_OR_INCONSISTENCY.
        The no-balancing variant is a DIAGNOSTIC ONLY — not a production methodology candidate.
        Finco keeps economically consistent revenue stacks across Base and Bank cases.
        No bank_balancing_cost_wind_eur_mwh input exists or should be added.

        Literal Senior (bal=5):  135,707.583 kEUR
        No-bal diagnostic (bal=0): 147,649.261 kEUR
        Source Senior:             147,150.442 kEUR
        Bridge:                   +11,941.678 kEUR  (source omits balancing in Bank CFADS)
        Residual: KUPI_SENIOR_GAP_RESIDUAL  +498.819 kEUR  (~0.34%)  OPEN_SMALL_RESIDUAL
        """
        from dataclasses import replace

        proj = _proj()
        proj_no_bal = replace(proj, revenue=replace(proj.revenue, balancing_cost_wind_eur_mwh=0.0))
        result_no_bal = run_project_shareholder_waterfall_model(proj_no_bal)
        senior_literal = _result().financing_result.final_senior_commitment_keur
        senior_no_bal = result_no_bal.financing_result.final_senior_commitment_keur
        source_senior = 147_150.442310

        bridge = senior_no_bal - senior_literal
        residual = senior_no_bal - source_senior

        # Bridge must be large (balancing is the primary gap cause)
        assert bridge > 5_000, f"Balancing bridge {bridge:.2f} kEUR unexpectedly small."
        # No-bal senior must be within 3,000 kEUR of source (residual only from minor causes)
        assert abs(residual) < 3_000, (
            f"Residual after balancing bridge: {residual:.2f} kEUR. "
            f"A second material gap cause may remain — investigate."
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
                    f"Period {pi}: SHL principal {pr:.4f} > cash_available {ca:.4f}"
                )

    def test_shl_closing_zero_at_maturity(self):
        pmr = _result().financing_result.project_model_result
        shl = pmr.shareholder_loan
        pids = list(shl.period_indices)
        closing = list(shl.shl_closing_keur)
        assert abs(closing[pids.index(61)]) < 1.0, (
            f"SHL not fully repaid at P61: closing={closing[pids.index(61)]:.4f}"
        )

    def test_shl_total_principal_equals_opening_less_pik_adjustments(self):
        """Total SHL principal repaid is consistent with SHL opening balance."""
        pmr = _result().financing_result.project_model_result
        shl = pmr.shareholder_loan
        pids = list(shl.period_indices)
        total_repaid = sum(shl.shl_principal_keur)
        opening_p2 = shl.shl_opening_keur[pids.index(2)]
        # Total repaid ≈ opening (SHL closes fully by maturity; PIK reduces gross interest)
        assert abs(total_repaid - opening_p2) < 10.0, (
            f"Total SHL repaid {total_repaid:.4f} far from opening {opening_p2:.4f}"
        )


# ── TestG  SHL Construction Compounding Gap ───────────────────────────────────


class TestG_SHLConstructionCompoundingGap:
    """G3B-G: Document KUPI_SHL_CONSTRUCTION_COMPOUNDING_GAP — CURRENT_FINCO_CAPABILITY_GAP.

    Source: compound interest on source SHL → 68,153 × ((1.08)^2 − 1) = 11,340.658 kEUR.
    Finco:  simple interest, dcf=2.0     → 79,596 × 8% × 2             = 12,735.337 kEUR.

    CROSS_BASIS_SHL_PIK_DIFFERENCE = +1,394.678 kEUR.
    This is NOT the pure compounding capability gap — the two PIK amounts use different
    SHL principal bases (79,596 engine vs 68,153 source), caused by the Senior sizing gap.

    Pure methodology delta on SOURCE principal basis (same-principal comparison):
      Source simple counterfactual:   68,153 × 8% × 2 = 10,904.479 kEUR
      Source compound PIK:            68,153 × ((1.08)^2 − 1) = 11,340.658 kEUR
      Delta (compound − simple):      +436.179 kEUR   ← pure capability gap, source basis

    Pure methodology delta on FINCO principal basis:
      Finco simple PIK:               79,596 × 8% × 2 = 12,735.337 kEUR
      Finco compound counterfactual:  79,596 × ((1.08)^2 − 1) ≈ 13,244.750 kEUR
      Delta (compound − simple):      ≈+509.413 kEUR  ← pure capability gap, Finco basis

    Do NOT implement compound interest in the engine without explicit authorization.
    """

    def test_construction_pik_is_simple_at_dcf_2(self):
        """Engine produces simple interest PIK = engine_SHL × 8% × 2.0."""
        fr = _result().financing_result
        pik = fr.shl_construction_pik_keur
        derived_shl = fr.derived_shl_cash_principal_keur
        expected_simple = derived_shl * 0.08 * 2.0
        assert abs(pik - expected_simple) < 1.0, (
            f"PIK {pik:.4f} != simple(dcf=2) {expected_simple:.4f}. "
            f"shl_construction_day_count_fraction must be 2.0."
        )

    def test_source_compound_pik_documented(self):
        """Source compound PIK (source SHL basis) = 11,340.658 kEUR."""
        source_shl = _KUPI_SOURCE_SHL_PRINCIPAL_KEUR
        compound_pik = source_shl * ((1.08 ** 2) - 1)
        simple_pik = source_shl * 0.08 * 2
        delta = compound_pik - simple_pik
        assert abs(compound_pik - 11_340.658) < 1.0, (
            f"Source compound PIK formula: {compound_pik:.4f} != 11,340.658"
        )
        assert abs(delta - 436.179) < 2.0, (
            f"Source simple-vs-compound delta: {delta:.4f} != 436.179"
        )

    def test_finco_compound_counterfactual_documented(self):
        """Finco compound counterfactual (engine SHL basis) for reference."""
        fr = _result().financing_result
        engine_shl = fr.derived_shl_cash_principal_keur
        simple_pik = fr.shl_construction_pik_keur
        compound_pik = engine_shl * ((1.08 ** 2) - 1)
        # Simple PIK must be less than compound (simple interest < compound for same rate)
        assert simple_pik < compound_pik, (
            f"Simple PIK {simple_pik:.4f} >= compound PIK {compound_pik:.4f} — impossible."
        )
        # Engine PIK is in the expected range (8,000–16,000 kEUR for this SHL size)
        assert 8_000 < simple_pik < 16_000, f"Simple PIK {simple_pik:.4f} out of range."

    def test_dcf_parameter_is_2_not_zero(self):
        """shl_construction_day_count_fraction must be 2.0 (24 months / 12)."""
        proj = _proj()
        dcf = proj.financing.shl_construction_day_count_fraction
        assert abs(dcf - 2.0) < 1e-9, (
            f"shl_construction_day_count_fraction={dcf} != 2.0. "
            f"Source construction period = 24 months → dcf = 24/12 = 2.0."
        )


# ── TestH  CO2 Bridge / SQ-02 ─────────────────────────────────────────────────


class TestH_CO2Bridge:
    """G3B-H: SQ-02 SOURCE_EFFECTIVE_UNUSED_TOGGLE_DIAGNOSTIC.

    Run A: co2_enabled=False (literal source toggle = FALSE).
    Run B: exact 30-year CO2 price schedule from Inputs!E123:AH123.
    Source total CO2 revenue (CF!row35): 25,002.043309 kEUR.
    Bridge ≈ 24,506 kEUR (residual ~496 kEUR from production/calendar differences).
    """

    def test_co2_bridge_positive(self):
        proj_b = create_kupi_project_source_effective_co2()
        result_b = run_project_shareholder_waterfall_model(proj_b)
        rev_a = sum(_result().financing_result.project_model_result.operating_schedules.revenue_keur)
        rev_b = sum(result_b.financing_result.project_model_result.operating_schedules.revenue_keur)
        bridge = rev_b - rev_a
        assert bridge > 15_000, f"CO2 bridge {bridge:.2f} kEUR unexpectedly small."

    def test_co2_bridge_near_source_total(self):
        """Bridge should be close to source total CO2 revenue (25,002 kEUR) ± 3,000."""
        proj_b = create_kupi_project_source_effective_co2()
        result_b = run_project_shareholder_waterfall_model(proj_b)
        rev_a = sum(_result().financing_result.project_model_result.operating_schedules.revenue_keur)
        rev_b = sum(result_b.financing_result.project_model_result.operating_schedules.revenue_keur)
        bridge = rev_b - rev_a
        source_co2_total = 25_002.043309
        assert abs(bridge - source_co2_total) < 3_000, (
            f"CO2 bridge {bridge:.4f} kEUR deviates more than 3,000 kEUR from "
            f"source CO2 total {source_co2_total:.4f}. Check CO2 price schedule."
        )


# ── TestI  DSCR Revenue-Mix Formula Gap ───────────────────────────────────────


class TestI_DSCRRevenueMixGap:
    """G3B-I: DSCR revenue-mix formula — KUPI result reproduced via explicit schedule.

    KUPI_PROJECT_DSCR_SCHEDULE_RESULT_REPRODUCED: the explicit _KUPI_DSCR_SCHEDULE
    reproduces DS!row19 exactly. There is no KUPI-specific numeric schedule gap.

    GENERIC_DYNAMIC_REVENUE_RATIO_DSCR_FORMULA_NOT_IMPLEMENTED (CURRENT_FINCO_CAPABILITY_GAP):
    Source DS!row13 = merchant_revenue / total_revenue (can exceed 100%:
    AF13 ≈ 1.030598, AH13 ≈ 1.031398). Source DSCR formula:
      target_DSCR = PPA_DSCR + (Merchant_DSCR − PPA_DSCR) × merchant_revenue_ratio
    yields AF19 ≈ 1.757649, AG19 ≈ 1.757649, AH19 ≈ 1.757849, AI19 ≈ 1.757849.
    This is a generic configurability limitation — not a KUPI schedule parity gap.
    Do NOT label DS!row13 as a normalised "merchant_share" — the ratio exceeds 100%.
    """

    def test_sculpting_config_matches_source_row19(self):
        """Explicit DSCR schedule must match source DS!row19 exactly."""
        proj = _proj()
        sc = proj.financing.senior_sculpting_config
        assert sc.enabled is True
        assert len(sc.target_dscr_schedule) == 28

        # First 24 periods: 1.50 (PPA)
        for i, v in enumerate(sc.target_dscr_schedule[:24]):
            assert abs(v - 1.50) < 1e-9, f"Period {i}: DSCR {v} != 1.50"

        # Last 4 periods: source DS!row19 merchant formula result (≈1.7576)
        merchant_dscr = sc.target_dscr_schedule[24:]
        for v in merchant_dscr:
            assert 1.75 <= v <= 1.76, f"Merchant DSCR {v} outside [1.75, 1.76]"

    def test_bank_dscr_above_one(self):
        pmr = _result().financing_result.project_model_result
        ds = pmr.debt_sizing
        bank_dscr = list(ds.bank_sizing_dscr)
        pids = list(ds.period_indices)
        for pid in range(2, 30):
            if pid in pids:
                dscr = bank_dscr[pids.index(pid)]
                assert dscr > 1.0, f"Bank DSCR at period {pid} = {dscr:.4f} ≤ 1"


# ── TestJ  Sponsor Returns Compass ────────────────────────────────────────────


class TestJ_SponsorReturnsCompass:
    """G3B-J: Sponsor returns in plausible range — compass only.

    KUPI_SPONSOR_CONTRIBUTION_TIMING_POLICY_GAP: source places full SHL+Capital at FC;
    engine distributes through construction. Do not tune to match source IRR targets.
    """

    def test_total_sponsor_xirr_in_range(self):
        r = _result()
        xirr = r.total_sponsor_xirr
        assert 0.10 < xirr < 0.30, f"total_sponsor_xirr={xirr:.4%} outside plausible range"

    def test_pure_equity_xirr_in_range(self):
        r = _result()
        xirr = r.pure_equity_xirr
        # Pure equity XIRR can be elevated when share capital is small relative to SHL.
        assert 0.10 < xirr < 0.60, f"pure_equity_xirr={xirr:.4%} outside plausible range"
