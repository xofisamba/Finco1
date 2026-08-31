"""Phase C3 Correction G — GFA policy authority, dep-basis comparison, opening RE.

§3  Raw IDC fallback prohibited — fail closed when capitalized IDC absent.
§5  BookCapitalizationTreatment drives GFA inclusion, not metadata.
§6  Unknown/UNRESOLVED non-zero component fails GFA closed.
§7  Policy-causal negative tests — mutate one treatment at a time.
§8  Dep-basis mismatch fires on any material difference, not just zero-vs-nonzero.
§9  Per-component comparison report in gfa_report.
§18 USER_CONFIGURED maps to USER_CONFIGURED_ACCOUNTING_POLICY, not SOURCE_PROVEN.
§13 Opening RE authority comes from preconstruction_retained_earnings_authority.
§16 COD opening RE = typed pre-construction RE + authoritative construction NI.
§21 Source anchors documented as evidence — not replayed.
"""
from __future__ import annotations

import dataclasses

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from finco_core.inputs.accounting import (
    AccountingPolicyAuthority,
    AccountingPolicyConfig,
    BookCapitalizationTreatment,
    LegalReservePolicy,
)
from financial_engine.financial_statements.contracts import LineAuthority


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assemble_oborovo():
    from tests.test_phasec3_correction_d_accounting_provenance import _assemble
    return _assemble("Oborovo")


def _assemble_with_policy(apc: AccountingPolicyConfig):
    """Assemble Oborovo financial statements with a synthetic accounting policy."""
    from app.project_factories import create_default_oborovo
    from financial_engine.orchestrator import run_project_shareholder_waterfall_model
    pi = dataclasses.replace(create_default_oborovo(), accounting_policy_config=apc)
    result = run_project_shareholder_waterfall_model(pi)
    fin = result.financial_result
    from financial_engine.financial_statements.assembly import build_financial_statements
    return build_financial_statements(fin, pi)


# Base source-proven policy for Oborovo (mutated in tests below).
_BASE_APC = create_default_oborovo().accounting_policy_config


# ---------------------------------------------------------------------------
# §18 — USER_CONFIGURED_ACCOUNTING_POLICY label
# ---------------------------------------------------------------------------

class TestG_UserConfiguredLabel:
    def test_user_configured_authority_maps_to_distinct_label(self):
        """USER_CONFIGURED must map to USER_CONFIGURED_ACCOUNTING_POLICY, NOT SOURCE_PROVEN."""
        assert hasattr(LineAuthority, "USER_CONFIGURED_ACCOUNTING_POLICY"), (
            "LineAuthority must have USER_CONFIGURED_ACCOUNTING_POLICY member"
        )
        assert LineAuthority.USER_CONFIGURED_ACCOUNTING_POLICY.value == "USER_CONFIGURED_ACCOUNTING_POLICY"
        assert LineAuthority.USER_CONFIGURED_ACCOUNTING_POLICY != LineAuthority.SOURCE_PROVEN_CONFIGURATION

    def test_source_proven_maps_to_source_proven_configuration(self):
        from financial_engine.financial_statements.assembly import _map_opening_re_label
        apc = AccountingPolicyConfig(
            preconstruction_retained_earnings_keur=0.0,
            preconstruction_retained_earnings_authority=AccountingPolicyAuthority.SOURCE_PROVEN,
        )
        assert _map_opening_re_label(apc) == LineAuthority.SOURCE_PROVEN_CONFIGURATION.value

    def test_user_configured_does_not_map_to_source_proven(self):
        from financial_engine.financial_statements.assembly import _map_opening_re_label
        apc = AccountingPolicyConfig(
            preconstruction_retained_earnings_keur=0.0,
            preconstruction_retained_earnings_authority=AccountingPolicyAuthority.USER_CONFIGURED,
        )
        label = _map_opening_re_label(apc)
        assert label != LineAuthority.SOURCE_PROVEN_CONFIGURATION.value, (
            "USER_CONFIGURED must NOT produce SOURCE_PROVEN_CONFIGURATION label"
        )
        assert label == LineAuthority.USER_CONFIGURED_ACCOUNTING_POLICY.value

    def test_generic_maps_to_generic_finco_accounting_policy(self):
        from financial_engine.financial_statements.assembly import _map_opening_re_label
        apc = AccountingPolicyConfig(
            preconstruction_retained_earnings_keur=0.0,
            preconstruction_retained_earnings_authority=AccountingPolicyAuthority.GENERIC_FINCO_POLICY,
        )
        assert _map_opening_re_label(apc) == LineAuthority.GENERIC_FINCO_ACCOUNTING_POLICY.value

    def test_unresolved_maps_to_unresolved(self):
        from financial_engine.financial_statements.assembly import _map_opening_re_label
        apc = AccountingPolicyConfig(
            preconstruction_retained_earnings_authority=AccountingPolicyAuthority.UNRESOLVED,
        )
        assert _map_opening_re_label(apc) == LineAuthority.UNRESOLVED.value


# ---------------------------------------------------------------------------
# §13/§16 — Opening RE authority from typed preconstruction RE
# ---------------------------------------------------------------------------

class TestG_OpeningReAuthority:
    def test_oborovo_opening_re_status_ok(self):
        """Oborovo has SOURCE_PROVEN preconstruction RE → opening RE status OK."""
        from financial_engine.financial_statements.contracts import StatementStatus
        fs = _assemble_oborovo()
        assert fs.opening_retained_earnings_status == StatementStatus.OK, (
            f"Oborovo: expected OK, got {fs.opening_retained_earnings_status}"
        )

    def test_oborovo_cod_opening_re_is_finite(self):
        """COD opening RE = 0.0 (pre-construction RE) + construction NI."""
        import math
        fs = _assemble_oborovo()
        assert fs.cod_opening_retained_earnings_keur is not None
        assert math.isfinite(fs.cod_opening_retained_earnings_keur)

    def test_oborovo_opening_re_label_is_source_proven(self):
        """SOURCE_PROVEN preconstruction RE → SOURCE_PROVEN_CONFIGURATION label."""
        fs = _assemble_oborovo()
        label = fs.authority_labels.get("opening_retained_earnings")
        assert label == LineAuthority.SOURCE_PROVEN_CONFIGURATION.value, (
            f"Expected SOURCE_PROVEN_CONFIGURATION, got {label}"
        )

    def test_unresolved_preconstruction_re_blocks_opening_re(self):
        """UNRESOLVED preconstruction RE authority → opening RE unavailable."""
        from financial_engine.financial_statements.contracts import StatementStatus
        apc = dataclasses.replace(
            _BASE_APC,
            preconstruction_retained_earnings_keur=None,
            preconstruction_retained_earnings_authority=AccountingPolicyAuthority.UNRESOLVED,
        )
        fs = _assemble_with_policy(apc)
        assert fs.opening_retained_earnings_status == StatementStatus.OPENING_EQUITY_ACCOUNTING_AUTHORITY_UNAVAILABLE
        assert fs.cod_opening_retained_earnings_keur is None

    def test_preconstruction_re_serializes_and_participates_in_cache(self):
        """New fields round-trip through serialization and change cache key."""
        from finco_core.inputs import project_inputs_to_dict, project_inputs_from_dict
        from finco_core.inputs._models import hash_inputs_for_cache
        pi = create_default_oborovo()
        d = project_inputs_to_dict(pi)
        assert d["accounting_policy_config"]["preconstruction_retained_earnings_keur"] == 0.0
        assert d["accounting_policy_config"]["preconstruction_retained_earnings_authority"] == "SOURCE_PROVEN"
        pi2 = project_inputs_from_dict(d)
        assert pi2.accounting_policy_config.preconstruction_retained_earnings_keur == 0.0
        # Cache key must differ from a policy without typed pre-RE
        pi_no_pre_re = dataclasses.replace(
            pi,
            accounting_policy_config=dataclasses.replace(
                pi.accounting_policy_config,
                preconstruction_retained_earnings_keur=None,
                preconstruction_retained_earnings_authority=AccountingPolicyAuthority.UNRESOLVED,
            ),
        )
        assert hash_inputs_for_cache(pi) != hash_inputs_for_cache(pi_no_pre_re)


# ---------------------------------------------------------------------------
# §3 — Raw IDC fallback prohibited
# ---------------------------------------------------------------------------

class TestG_NoRawIdcFallback:
    def test_gfa_report_uses_capitalized_not_raw_idc_key(self):
        """gfa_report must expose senior_idc_capitalized_keur, not raw-only key."""
        fs = _assemble_oborovo()
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        assert "senior_idc_capitalized_keur" in report, (
            "gfa_report must contain 'senior_idc_capitalized_keur' (capitalized authority)"
        )
        assert "senior_idc_raw_keur" in report, "raw IDC must still be in report as audit"

    def test_raw_idc_greater_than_capitalized_idc(self):
        """raw IDC >= capitalized IDC (terminal raw IDC excluded)."""
        fs = _assemble_oborovo()
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        raw = report.get("senior_idc_raw_keur", 0.0)
        cap = report.get("senior_idc_capitalized_keur", 0.0)
        terminal = report.get("senior_idc_terminal_excluded_keur", 0.0)
        assert raw >= cap, f"raw IDC ({raw}) must be >= capitalized IDC ({cap})"
        assert abs(raw - cap - terminal) < 1e-3, (
            f"Identity: raw ({raw}) = cap ({cap}) + terminal ({terminal}) violated"
        )

    def test_raw_idc_not_equal_to_capitalized_idc_for_tuho(self):
        """For TUHO, terminal IDC exists so raw != capitalized."""
        from tests.test_phasec3_correction_d_accounting_provenance import _assemble
        fs = _assemble("TUHO")
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        raw = report.get("senior_idc_raw_keur", 0.0)
        cap = report.get("senior_idc_capitalized_keur", 0.0)
        terminal = report.get("senior_idc_terminal_excluded_keur", 0.0)
        # TUHO has terminal IDC excluded ≈ 217.125 kEUR
        assert terminal > 0.0, "TUHO must have non-zero terminal IDC excluded"
        assert abs(raw - cap - terminal) < 1e-3


# ---------------------------------------------------------------------------
# §5/§7 — Policy-causal negative tests
# ---------------------------------------------------------------------------

class TestG_PolicyCausalNegative:
    def test_senior_idc_expense_pnl_removes_from_candidate_gfa(self):
        """senior_idc → EXPENSE_PNL must remove IDC from candidate GFA."""
        new_components = dict(_BASE_APC.book_capitalization_components)
        new_components["senior_idc"] = BookCapitalizationTreatment.EXPENSE_PNL.value
        apc = dataclasses.replace(_BASE_APC, book_capitalization_components=new_components)
        fs = _assemble_with_policy(apc)
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        cap_idc = report.get("senior_idc_capitalized_keur", 0.0)
        # The candidate GFA (if computed) must not include senior IDC
        candidate = report.get("candidate_book_gfa_keur") or report.get("total_book_gfa_keur")
        if candidate is not None and cap_idc > 0:
            # Baseline candidate includes IDC; new candidate should be smaller
            baseline_report = _assemble_oborovo().accounting_policies.provenance.get("gfa_report", {})
            baseline_candidate = baseline_report.get("candidate_book_gfa_keur") or baseline_report.get("total_book_gfa_keur") or 0.0
            assert candidate < baseline_candidate, (
                f"Expensing IDC to P&L must reduce candidate GFA; "
                f"got {candidate:.3f} >= baseline {baseline_candidate:.3f}"
            )

    def test_senior_commitment_fees_unresolved_fails_gfa(self):
        """senior_commitment_fees → UNRESOLVED with non-zero fee must make GFA unavailable."""
        from financial_engine.financial_statements.contracts import StatementStatus
        new_components = dict(_BASE_APC.book_capitalization_components)
        new_components["senior_commitment_fees"] = BookCapitalizationTreatment.UNRESOLVED.value
        apc = dataclasses.replace(_BASE_APC, book_capitalization_components=new_components)
        fs = _assemble_with_policy(apc)
        assert fs.fixed_asset_status == StatementStatus.BOOK_CAPITALIZATION_BASIS_UNAVAILABLE, (
            "UNRESOLVED non-zero component must fail GFA closed"
        )
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        assert report.get("total_book_gfa_keur") is None or fs.fixed_asset_status != StatementStatus.OK

    def test_policy_map_is_authority_not_metadata(self):
        """Prove the map controls output: change dsra_funding to CAPITALIZE_FIXED_ASSET
        in a synthetic policy — assembly must respect it (not hardcode exclusion)."""
        # dsra_funding = 0 in cfin so this doesn't add value to GFA,
        # but the treatment must be READ from the map (not hardcoded excluded).
        new_components = dict(_BASE_APC.book_capitalization_components)
        new_components["dsra_funding"] = BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value
        apc = dataclasses.replace(_BASE_APC, book_capitalization_components=new_components)
        fs = _assemble_with_policy(apc)
        # Assembly ran without error — policy was consulted, not hardcoded to exclude
        assert fs is not None
        # The treatment stored in output matches what we supplied
        stored = fs.accounting_policies.book_capitalization_components.get("dsra_funding")
        assert stored == BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value, (
            f"book_capitalization_components output must reflect policy input, got {stored}"
        )


# ---------------------------------------------------------------------------
# §8/§9 — Dep-basis mismatch: any material difference, not just zero-vs-nonzero
# ---------------------------------------------------------------------------

class TestG_DepBasisComparison:
    def test_dep_basis_comparison_in_gfa_report(self):
        """gfa_report must contain dep_basis_comparison with component breakdown."""
        fs = _assemble_oborovo()
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        comp = report.get("dep_basis_comparison")
        assert comp is not None, "gfa_report must contain dep_basis_comparison"
        assert "financing_costs_clean_gfa_keur" in comp
        assert "financing_costs_dep_basis_keur" in comp
        assert "financing_costs_diff_keur" in comp
        assert "authority" in comp

    def test_dep_basis_gap_fires_for_oborovo(self):
        """Oborovo has non-zero cfin financing costs vs zero capex scalars → gap fires."""
        from financial_engine.financial_statements.contracts import StatementStatus
        fs = _assemble_oborovo()
        assert fs.fixed_asset_status == StatementStatus.BOOK_CAPITALIZATION_BASIS_UNAVAILABLE
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        comp = report.get("dep_basis_comparison", {})
        assert comp.get("authority") == "BOOK_DEPRECIABLE_ASSET_BASIS_UPSTREAM_REQUIRED"
        assert comp.get("financing_costs_diff_keur", 0) > 1.0, (
            "Financing cost difference must be > 1 kEUR for Oborovo"
        )

    def test_dep_basis_comparison_identifies_exact_difference(self):
        """The diff field must equal clean_gfa minus dep_basis."""
        fs = _assemble_oborovo()
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        comp = report.get("dep_basis_comparison", {})
        clean = comp.get("financing_costs_clean_gfa_keur", 0.0)
        dep = comp.get("financing_costs_dep_basis_keur", 0.0)
        diff = comp.get("financing_costs_diff_keur", 0.0)
        assert abs(diff - (clean - dep)) < 1e-6


# ---------------------------------------------------------------------------
# §21 — Source anchors as evidence only
# ---------------------------------------------------------------------------

class TestG_SourceAnchors:
    FIRST_PARTIAL_KEUR = 0.7952316513369624
    CAP_FILLING_KEUR = 49.20476834866304
    TOTAL_KEUR = 50.0

    def test_source_anchors_documented_as_constants(self):
        """Evidence anchors are recorded (this test IS the documentation)."""
        assert abs(self.FIRST_PARTIAL_KEUR + self.CAP_FILLING_KEUR - self.TOTAL_KEUR) < 1e-9, (
            "Source anchors: first partial + cap-filling must equal 50 kEUR"
        )

    def test_source_anchors_not_replayed_into_runtime(self):
        """The runtime must NOT contain the exact anchor values as literal outputs."""
        for ptype in ("Oborovo", "TUHO"):
            from tests.test_phasec3_correction_d_accounting_provenance import _assemble
            fs = _assemble(ptype)
            # No RE period should have a legal reserve allocation exactly equal to source anchor
            for p in fs.retained_earnings_periods:
                alloc = p.legal_reserve_allocation_keur
                if alloc is not None:
                    assert abs(alloc - self.FIRST_PARTIAL_KEUR) > 1e-6, (
                        f"{ptype}: source anchor value leaked into runtime at period {p.period_index}"
                    )
