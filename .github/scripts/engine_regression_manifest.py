"""
Canonical engine regression manifest for xofisamba/Finco1.

This module defines the single authoritative deduplicated list of test files
that constitute the full frozen financial engine authority regression suite.
It is derived from the union of all 20 historical authority workflow test paths.

Used by:
  - .github/workflows/nightly_full_engine_regression.yml
  - .github/scripts/tests/test_engine_regression_manifest.py (structural tests)

Do NOT add test paths here without also verifying they exist on disk.
Do NOT remove test paths without a documented reason.
"""
from __future__ import annotations

from pathlib import Path

# ── Canonical deduplicated engine regression test suite ───────────────────────
# Ordered roughly by historical pipeline stage (C3B1 → B8 → G0 → G1 → G2 →
# B2 → B4 → C1 → C2 → C3 → PR5-8 → U2/Upstream).
MANIFEST: list[dict] = [
    # ── Stage C3A / C3B1 ─────────────────────────────────────────────────────
    {
        "path": "tests/test_stage_c3a_clean_pnl_through_ebit.py",
        "areas": ["C3B6", "C3B7", "C3B8"],
        "label": "C3A clean PnL through EBIT",
    },
    {
        "path": "tests/test_stage_c3b1_oborovo_tax_source_truth.py",
        "areas": ["C3B1", "C3B6", "C3B7", "C3B8", "B4", "C3"],
        "label": "C3B1 Oborovo tax source truth",
    },
    # ── Stage C3B3 senior debt ───────────────────────────────────────────────
    {
        "path": "tests/test_stage_c3b3a_clean_senior_debt_source_contract.py",
        "areas": ["C3B6", "C3B7", "C3B8", "PR7"],
        "label": "C3B3A clean senior debt source contract",
    },
    {
        "path": "tests/test_stage_c3b3b_clean_tax_cfads_debt_feedback.py",
        "areas": ["G0"],
        "label": "C3B3B clean tax CFADS debt feedback",
    },
    {
        "path": "tests/test_stage_c3b3c_tax_policy_shl_deductibility.py",
        "areas": ["B2"],
        "label": "C3B3C tax policy SHL deductibility",
    },
    {
        "path": "tests/test_stage_c3b3d0_tax_identity_atad_decoupling.py",
        "areas": ["B2"],
        "label": "C3B3D0 tax identity ATAD decoupling",
    },
    {
        "path": "tests/test_stage_c3b3d2b2c_bank_sizing_cfads_production.py",
        "areas": ["C3B7", "C3B8"],
        "label": "C3B3D2B2C bank sizing CFADs production",
    },
    {
        "path": "tests/test_stage_c3b3d2b3_debt_sizing_case_production.py",
        "areas": ["C3B6", "C3B7", "C3B8", "PR7", "PR8"],
        "label": "C3B3D2B3 debt sizing case production",
    },
    {
        "path": "tests/test_stage_c3b3d2b3_hardening_completion.py",
        "areas": ["C3B7", "C3B8"],
        "label": "C3B3D2B3 hardening completion",
    },
    {
        "path": "tests/test_stage_c3b3d2b4_dscr_post_senior_cash_authority.py",
        "areas": ["C3B6", "C3B7", "C3B8"],
        "label": "C3B3D2B4 DSCR post-senior cash authority",
    },
    {
        "path": "tests/test_stage_c3b3d2b5_shl_fixed_point_integration.py",
        "areas": ["C3B6", "C3B7", "C3B8", "PR6", "PR7", "PR8", "B2"],
        "label": "C3B3D2B5 SHL fixed-point integration",
    },
    {
        "path": "tests/test_stage_c3b3d2b6_base_post_senior_cash_parity.py",
        "areas": ["C3B6", "C3B7", "C3B8", "G0", "PR6", "PR7", "PR8", "B4"],
        "label": "C3B3D2B6 base post-senior cash parity",
    },
    {
        "path": "tests/test_stage_c3b3d2b7_bank_case_senior_parity.py",
        "areas": ["C3B7", "C3B8", "PR6", "PR7", "PR8"],
        "label": "C3B3D2B7 bank case senior parity",
    },
    {
        "path": "tests/test_stage_c3b3d2b8_base_senior_shl_parity_closure.py",
        "areas": ["C3B8", "G0"],
        "label": "C3B3D2B8 base senior SHL parity closure",
    },
    # ── Phase 2 legacy ────────────────────────────────────────────────────────
    {
        "path": "tests/test_phase2b_tax_cfads.py",
        "areas": ["G1"],
        "label": "Phase 2B tax CFADs",
    },
    {
        "path": "tests/test_phase2c_senior_debt.py",
        "areas": ["C3B6", "C3B7", "C3B8", "PR7", "PR8"],
        "label": "Phase 2C senior debt",
    },
    # ── Integration fixtures ─────────────────────────────────────────────────
    {
        "path": "tests/integration/test_tuho_wind1_fixture.py",
        "areas": ["C3B6", "C3B7", "C3B8", "G0"],
        "label": "Tuho Wind-1 integration fixture",
    },
    # ── PR3 DSRA ─────────────────────────────────────────────────────────────
    {
        "path": "tests/test_pr3_cash_dsra_module.py",
        "areas": ["PR5", "PR7", "C3"],
        "label": "PR3 cash DSRA module",
    },
    {
        "path": "tests/test_pr3b_dynamic_dsra_target.py",
        "areas": ["PR5", "PR7", "C3"],
        "label": "PR3B dynamic DSRA target",
    },
    # ── Stage B2 construction IDC ────────────────────────────────────────────
    {
        "path": "tests/test_stage_b2_construction_idc_runtime.py",
        "areas": ["B2"],
        "label": "Stage B2 construction IDC runtime",
    },
    {
        "path": "tests/test_pr9_typed_construction_idc_authority.py",
        "areas": ["B2"],
        "label": "PR9 typed construction IDC authority",
    },
    # ── MVP G0-G2C ───────────────────────────────────────────────────────────
    {
        "path": "tests/test_mvp_g0_generic_clean_engine_enablement.py",
        "areas": ["G0", "G2A", "G2B", "G2C", "PR6", "PR7", "PR8", "B2", "C3"],
        "label": "MVP G0 generic clean engine enablement",
    },
    {
        "path": "tests/test_mvp_g1_governance_methodology_lock.py",
        "areas": ["G1", "B2"],
        "label": "MVP G1 governance methodology lock",
    },
    {
        "path": "tests/test_mvp_g1_workflow_authority.py",
        "areas": ["G1", "G2B", "G2C", "PR6", "PR7", "PR8"],
        "label": "MVP G1 workflow authority",
    },
    {
        "path": "tests/test_mvp_g2a_financing_stack.py",
        "areas": ["G2A", "G2B", "PR7", "PR8"],
        "label": "MVP G2A financing stack",
    },
    {
        "path": "tests/test_mvp_g2b_sponsor_returns.py",
        "areas": ["G2B", "G2C", "C1", "C2", "C3"],
        "label": "MVP G2B sponsor returns",
    },
    {
        "path": "tests/test_mvp_g2c_shareholder_waterfall.py",
        "areas": ["G2C", "C1", "C2"],
        "label": "MVP G2C shareholder waterfall",
    },
    {
        "path": "tests/test_mvp_dsrf_reserve_support.py",
        "areas": ["G2C"],
        "label": "MVP DSRF reserve support",
    },
    # ── Phase 51F ─────────────────────────────────────────────────────────────
    {
        "path": "tests/test_phase51f_parallel_work_guardrails.py",
        "areas": ["G1"],
        "label": "Phase 51F parallel work guardrails",
    },
    # ── Prefreeze period axis ────────────────────────────────────────────────
    {
        "path": "tests/test_prefreeze_prf1_canonical_period_axis.py",
        "areas": ["B2", "PRF1"],
        "label": "Prefreeze PRF1 canonical period axis",
    },
    # ── Prefreeze PR5-8 ──────────────────────────────────────────────────────
    {
        "path": "tests/test_prefreeze_pr5_canonical_ebitda_authority.py",
        "areas": ["PR5", "B2", "C3"],
        "label": "Prefreeze PR5 canonical EBITDA authority",
    },
    {
        "path": "tests/test_prefreeze_pr6_typed_shl_repayment_policy.py",
        "areas": ["PR6", "B4", "C1"],
        "label": "Prefreeze PR6 typed SHL repayment policy",
    },
    {
        "path": "tests/test_prefreeze_pr7_typed_base_bank_case_authority.py",
        "areas": ["PR7", "B4", "C1", "C2", "C3"],
        "label": "Prefreeze PR7 base bank case authority",
    },
    {
        "path": "tests/test_prefreeze_pr8_single_production_financial_authority.py",
        "areas": ["PR8", "B4", "C3"],
        "label": "Prefreeze PR8 single production financial authority",
    },
    # ── Phase B1/B2/B4 ───────────────────────────────────────────────────────
    {
        "path": "tests/test_phaseb1_clean_only_production_router.py",
        "areas": ["B2", "B4"],
        "label": "Phase B1 clean-only production router",
    },
    {
        "path": "tests/test_phaseb2_oborovo_clean_production_promotion.py",
        "areas": ["B2"],
        "label": "Phase B2 Oborovo clean production promotion",
    },
    {
        "path": "tests/test_phaseb4_single_production_engine.py",
        "areas": ["B4", "C1", "C2", "C3"],
        "label": "Phase B4 single production engine",
    },
    # ── KUPI ─────────────────────────────────────────────────────────────────
    {
        "path": "tests/test_kupi_k0_k3_causal_grid.py",
        "areas": ["KUPI", "B2", "B4", "C3"],
        "label": "KUPI K0-K3 causal grid",
    },
    # ── Phase C1/C2/C3 ───────────────────────────────────────────────────────
    {
        "path": "tests/test_phasec1_returns_maturity_authority.py",
        "areas": ["C1"],
        "label": "Phase C1 returns maturity authority",
    },
    {
        "path": "tests/test_phasec2_npv_llcr_plcr_authority.py",
        "areas": ["C2"],
        "label": "Phase C2 NPV/LLCR/PLCR authority",
    },
    {
        "path": "tests/test_phasec3_clean_financial_statements_authority.py",
        "areas": ["C3"],
        "label": "Phase C3 clean financial statements authority",
    },
    {
        "path": "tests/test_phasec3_correction_d_accounting_provenance.py",
        "areas": ["C3"],
        "label": "Phase C3 correction D accounting provenance",
    },
    {
        "path": "tests/test_phasec3_correction_f_accounting_persistence.py",
        "areas": ["C3"],
        "label": "Phase C3 correction F accounting persistence",
    },
    {
        "path": "tests/test_phasec3_correction_g_gfa_policy.py",
        "areas": ["C3"],
        "label": "Phase C3 correction G GFA policy",
    },
    {
        "path": "tests/test_phasec3_u1_integration.py",
        "areas": ["C3"],
        "label": "Phase C3 U1 integration",
    },
    {
        "path": "tests/test_phasec3_u2_integration.py",
        "areas": ["C3", "U2"],
        "label": "Phase C3 U2 integration",
    },
    # ── Phase C3 Capex ───────────────────────────────────────────────────────
    {
        "path": "tests/test_phase57a8_capex_add_line_ux_in_memory.py",
        "areas": ["PR5"],
        "label": "Phase 57A8 CAPEX add-line UX in-memory",
    },
    {
        "path": "tests/test_phase57a9d_capex_sub_lines_run_integration.py",
        "areas": ["PR5"],
        "label": "Phase 57A9D CAPEX sub-lines run integration",
    },
    # ── Upstream / U2 ────────────────────────────────────────────────────────
    {
        "path": "tests/test_upstream_book_depreciable_asset_basis.py",
        "areas": ["C3", "U2"],
        "label": "Upstream book depreciable asset basis",
    },
    {
        "path": "tests/test_upstream_cash_reserve_interest_policy.py",
        "areas": ["U2"],
        "label": "Upstream cash reserve interest policy",
    },
    # ── Waterfall / tax integration ──────────────────────────────────────────
    {
        "path": "tests/test_waterfall_tax_integration.py",
        "areas": ["U2"],
        "label": "Waterfall tax integration",
    },
    {
        "path": "tests/test_waterfall_golden_validation.py",
        "areas": ["U2"],
        "label": "Waterfall golden validation",
    },
    {
        "path": "tests/test_c2_tax_canonical_consistency.py",
        "areas": ["C2", "U2"],
        "label": "C2 tax canonical consistency",
    },
]

# ── Key authority areas that MUST be represented ──────────────────────────────
REQUIRED_AREAS = {"C1", "C2", "C3", "B4", "G0", "G2A", "G2B", "G2C",
                  "U2", "PR6", "PR7", "PR8", "KUPI"}

TEST_PATHS: list[str] = [entry["path"] for entry in MANIFEST]


def validate_manifest(root: Path | None = None) -> list[str]:
    """Return list of error strings; empty list means manifest is valid."""
    errors: list[str] = []
    if root is None:
        root = Path(__file__).resolve().parents[2]

    if not MANIFEST:
        errors.append("MANIFEST is empty")
        return errors

    # Check for duplicate paths
    seen: set[str] = set()
    for entry in MANIFEST:
        p = entry["path"]
        if p in seen:
            errors.append(f"Duplicate path in manifest: {p}")
        seen.add(p)

    # Check all files exist
    for entry in MANIFEST:
        full = root / entry["path"]
        if not full.exists():
            errors.append(f"Missing test file: {entry['path']}")

    # Check required areas are covered
    covered: set[str] = set()
    for entry in MANIFEST:
        covered.update(entry.get("areas", []))
    missing_areas = REQUIRED_AREAS - covered
    if missing_areas:
        errors.append(f"Required authority areas not covered: {sorted(missing_areas)}")

    return errors


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[2]
    errors = validate_manifest(root)
    if errors:
        print("MANIFEST VALIDATION FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print(f"Manifest OK: {len(MANIFEST)} test files, "
          f"areas covered: {sorted(set(a for e in MANIFEST for a in e.get('areas', [])))}")
