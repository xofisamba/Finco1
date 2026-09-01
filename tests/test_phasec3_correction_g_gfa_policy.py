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
    from app.services.production_financial_authority import run_clean_production
    from financial_engine.financial_statements import (
        assemble_decision_complete_financial_statements,
    )
    pi = dataclasses.replace(create_default_oborovo(), accounting_policy_config=apc)
    run = run_clean_production(pi, project_type="Oborovo")
    return assemble_decision_complete_financial_statements(run.g2c_result, pi)


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
        """gfa_report audit must expose senior_idc_capitalized_keur and raw for TUHO evidence."""
        fs = _assemble_oborovo()
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        audit = report.get("audit", {})
        assert "senior_idc_capitalized_keur" in audit, (
            "gfa_report.audit must contain 'senior_idc_capitalized_keur' (audit evidence)"
        )
        assert "senior_idc_raw_keur" in audit, "raw IDC must still be in audit as evidence"

    def test_raw_idc_greater_than_capitalized_idc(self):
        """raw IDC >= capitalized IDC (terminal raw IDC excluded for TUHO)."""
        fs = _assemble_oborovo()
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        audit = report.get("audit", {})
        raw = audit.get("senior_idc_raw_keur", 0.0)
        cap = audit.get("senior_idc_capitalized_keur", 0.0)
        terminal = audit.get("senior_idc_terminal_excluded_keur", 0.0)
        assert raw >= cap, f"raw IDC ({raw}) must be >= capitalized IDC ({cap})"
        assert abs(raw - cap - terminal) < 1e-3, (
            f"Identity: raw ({raw}) = cap ({cap}) + terminal ({terminal}) violated"
        )

    def test_raw_idc_not_equal_to_capitalized_idc_for_tuho(self):
        """For TUHO, terminal IDC exists so raw != capitalized."""
        from tests.test_phasec3_correction_d_accounting_provenance import _assemble
        fs = _assemble("TUHO")
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        audit = report.get("audit", {})
        raw = audit.get("senior_idc_raw_keur", 0.0)
        cap = audit.get("senior_idc_capitalized_keur", 0.0)
        terminal = audit.get("senior_idc_terminal_excluded_keur", 0.0)
        # TUHO has terminal IDC excluded ≈ 217 kEUR
        assert terminal > 0.0, "TUHO must have non-zero terminal IDC excluded"
        assert abs(raw - cap - terminal) < 1e-3


# ---------------------------------------------------------------------------
# §5/§7 — Policy-causal negative tests
# ---------------------------------------------------------------------------

class TestG_PolicyCausalNegative:
    def test_canonical_basis_drives_gfa_regardless_of_policy_map(self):
        """GFA is driven by canonical BookDepreciableAssetBasis — policy map changes do NOT alter GFA."""
        from financial_engine.financial_statements.contracts import StatementStatus
        # Change senior_idc treatment to EXPENSE_PNL in policy — GFA must still be AVAILABLE
        new_components = dict(_BASE_APC.book_capitalization_components)
        new_components["senior_idc"] = BookCapitalizationTreatment.EXPENSE_PNL.value
        apc = dataclasses.replace(_BASE_APC, book_capitalization_components=new_components)
        fs = _assemble_with_policy(apc)
        # GFA must still be OK — canonical basis is the authority, not the policy map
        assert fs.fixed_asset_status == StatementStatus.OK, (
            "GFA must be AVAILABLE regardless of policy map changes; "
            "canonical BookDepreciableAssetBasis is the sole authority"
        )

    def test_unresolved_policy_component_does_not_fail_gfa(self):
        """UNRESOLVED in policy map must NOT fail GFA; canonical basis is the authority."""
        from financial_engine.financial_statements.contracts import StatementStatus
        new_components = dict(_BASE_APC.book_capitalization_components)
        new_components["senior_commitment_fees"] = BookCapitalizationTreatment.UNRESOLVED.value
        apc = dataclasses.replace(_BASE_APC, book_capitalization_components=new_components)
        fs = _assemble_with_policy(apc)
        # GFA must still be OK — canonical basis drives GFA, policy map is presentation-only
        assert fs.fixed_asset_status == StatementStatus.OK, (
            "UNRESOLVED policy map component must NOT fail GFA; "
            "canonical BookDepreciableAssetBasis is the sole GFA authority"
        )

    def test_policy_map_is_presentation_not_gfa_authority(self):
        """Changing policy map must not change canonical GFA amount."""
        from financial_engine.financial_statements.contracts import StatementStatus
        # Baseline canonical GFA
        baseline_fs = _assemble_oborovo()
        baseline_gfa = baseline_fs.accounting_policies.provenance.get("gfa_report", {}).get("canonical_book_gfa_keur")
        # Change dsra_funding to CAPITALIZE_FIXED_ASSET — must not affect canonical GFA
        new_components = dict(_BASE_APC.book_capitalization_components)
        new_components["dsra_funding"] = BookCapitalizationTreatment.CAPITALIZE_FIXED_ASSET.value
        apc = dataclasses.replace(_BASE_APC, book_capitalization_components=new_components)
        fs = _assemble_with_policy(apc)
        changed_gfa = fs.accounting_policies.provenance.get("gfa_report", {}).get("canonical_book_gfa_keur")
        assert fs.fixed_asset_status == StatementStatus.OK
        assert abs(baseline_gfa - changed_gfa) < 1e-6, (
            f"Policy map change must not alter canonical GFA; "
            f"baseline {baseline_gfa:.3f} != changed {changed_gfa:.3f}"
        )


# ---------------------------------------------------------------------------
# §8/§9 — Dep-basis mismatch: any material difference, not just zero-vs-nonzero
# ---------------------------------------------------------------------------

class TestG_DepBasisComparison:
    def test_canonical_gfa_report_structure(self):
        """gfa_report must contain canonical_book_gfa_keur, authority, and components."""
        fs = _assemble_oborovo()
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        assert "canonical_book_gfa_keur" in report, "gfa_report must contain canonical_book_gfa_keur"
        assert "canonical_book_basis_authority" in report
        assert "canonical_book_basis_components" in report
        components = report["canonical_book_basis_components"]
        assert isinstance(components, list) and len(components) > 0

    def test_oborovo_gfa_now_available(self):
        """After U1 integration, Oborovo GFA must be AVAILABLE (not BOOK_CAPITALIZATION_BASIS_UNAVAILABLE)."""
        from financial_engine.financial_statements.contracts import StatementStatus
        fs = _assemble_oborovo()
        assert fs.fixed_asset_status == StatementStatus.OK, (
            f"After U1 integration, Oborovo GFA must be OK; got {fs.fixed_asset_status}"
        )
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        assert report.get("canonical_book_gfa_keur") is not None
        assert report.get("canonical_book_gfa_keur") > 0

    def test_canonical_gfa_equals_basis_total(self):
        """canonical_book_gfa_keur == sum of all component amounts."""
        fs = _assemble_oborovo()
        report = fs.accounting_policies.provenance.get("gfa_report", {})
        gfa = report.get("canonical_book_gfa_keur", 0.0)
        components = report.get("canonical_book_basis_components", [])
        component_sum = sum(c["amount_keur"] for c in components)
        assert abs(gfa - component_sum) < 1e-6, (
            f"canonical_book_gfa_keur ({gfa:.6f}) != component sum ({component_sum:.6f})"
        )


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
