"""R4 / F06 — Typed Country-Tax Edit Contract.

Closes audit finding F06/P1: a Workbook V2 CIT-rate edit on a project with a
selected typed country-tax policy used to mutate the legacy
``TaxParams.corporate_rate``, while the clean country-tax authority expects a
selected policy plus an optional ``corporate_rate_override`` — producing
``COUNTRY_TAX_LEGACY_FIELD_CONFLICT`` on TUHO.

R4 contract (app-layer authority routing only; no engine/tax-formula changes):

- Project WITHOUT ``country_tax_policy_id``: Workbook CIT edit →
  ``TaxParams.corporate_rate`` (legacy/generic authority preserved);
  ``corporate_rate_override`` stays None.
- Project WITH ``country_tax_policy_id``: Workbook CIT edit →
  ``TaxParams.corporate_rate_override`` (ratio = pct / 100).  The selected
  policy remains the jurisdiction/default authority; the explicit edit is the
  project-specific rate over that policy.
- ``COUNTRY_TAX_LEGACY_FIELD_CONFLICT`` is preserved unchanged for genuinely
  contradictory historical states (policy + no override + conflicting legacy
  rate).

Units: the Workbook stores human percentages (18.0 == 18 %); canonical
TaxParams rates are ratios (0.18).  The /100 conversion happens exactly once,
in ``app.input_adapter._set_tax_corporate_rate``.
"""
from __future__ import annotations

import pytest

from app.project_factories import (
    create_default_oborovo,
    create_default_solar_project,
    create_default_tuho_wind1,
    create_default_wind_project,
)

TUHO_POLICY_ID = "HR-approved-source-model-2026-v1"
CIT_FIELD_ID = "tax.assumptions.cit_rate_pct"
CIT_SNAPSHOT_KEY = "tax_corporate_rate_pct"


# ---------------------------------------------------------------------------
# Shared helpers — the REAL Workbook V2 public edit path (no DB):
# validate_field_update → persisted snapshot → ProjectInputSet → to_projectinputs
# ---------------------------------------------------------------------------

def _tuho_working_copy_snapshot(cit_pct: str | None = None) -> dict:
    """A TUHO working-copy draft snapshot (template_source=tuho is what makes
    build_projectinputs_from_snapshot select the TUHO factory base with its
    typed country-tax policy)."""
    snap = {
        "template_source": "tuho",
        "project_type": "Wind",
        "project_name": "TUHO Working Copy",
        "country_market": "HR",
        "capacity_mw": "53",
        "cod_date": "2027-01-01",
        "construction_months": "6",
        "horizon_years": "30",
        "tariff_eur_mwh": "70",
        "ppa_term_years": "20",
        "p50_hours": "2200",
        "opex_y1_keur": "3000",
        "total_capex_keur": "50000",
        "gearing_pct": "",
        "interest_rate_pct": "5",
        "tenor_years": "18",
        "target_dscr": "1.35",
    }
    if cit_pct is not None:
        snap[CIT_SNAPSHOT_KEY] = cit_pct
    return snap


def _materialise(snapshot: dict):
    """Real V2 materialisation boundary: PIS → ProjectInputs."""
    from app.workbook.input_set import ProjectInputSet
    return ProjectInputSet.from_snapshot(snapshot).to_projectinputs()


def _v2_edit(tuho_pi, pct: float):
    """Apply the Workbook CIT edit through the shared app authority setter —
    the exact function the snapshot resolver invokes for a V2 edit."""
    from app.input_adapter import _set_tax_corporate_rate
    return _set_tax_corporate_rate(tuho_pi, pct)


def _resolved_policy_rate(pi):
    """Run the clean country-tax adapter (the canonical typed resolution)."""
    from financial_engine.adapters.tax_inputs import (
        build_tax_contract_from_project_inputs,
    )
    return build_tax_contract_from_project_inputs(pi).policy.corporate_rate


# ---------------------------------------------------------------------------
# §12 — Registry denominator / metadata assertions
# ---------------------------------------------------------------------------

class TestRegistryDenominator:
    def test_exactly_one_editable_cit_field(self):
        from app.workbook.registry import WORKBOOK
        cit = [
            f for f in WORKBOOK.all_fields()
            if f.field_type.value == "pct" and "cit" in f.field_id.lower()
        ]
        assert len(cit) == 1
        assert cit[0].field_id == CIT_FIELD_ID

    def test_no_duplicate_editable_corporate_rate_field(self):
        from app.workbook.registry import WORKBOOK
        matches = [
            f for f in WORKBOOK.all_fields()
            if f.editable and "corporate" in (
                (f.description or "") + f.field_id).lower()
        ]
        assert [f.field_id for f in matches] == [CIT_FIELD_ID]

    def test_cit_field_full_contract(self):
        from app.workbook.registry import WORKBOOK
        from app.workbook.specs import (
            BindingStatus,
            FieldType,
            ScenarioPolicy,
            SourceOfTruth,
        )
        f = WORKBOOK.field(CIT_FIELD_ID)
        assert f.snapshot_key == CIT_SNAPSHOT_KEY
        assert f.field_type is FieldType.PCT
        assert f.unit == "%"
        assert f.binding_status is BindingStatus.BOUND
        assert f.scenario_policy is ScenarioPolicy.OVERRIDE
        assert f.source_of_truth is SourceOfTruth.INPUT_SET
        assert f.persisted is True and f.editable is True
        assert (f.min_value, f.max_value) == (0, 100)

    def test_declared_canonical_path_is_conditionally_accurate(self):
        """§12: the registry must not claim a single unconditional engine
        path that is no longer true."""
        from app.workbook.registry import WORKBOOK
        f = WORKBOOK.field(CIT_FIELD_ID)
        assert f.engine_path == "tax.corporate_rate"
        assert f.engine_path_conditional is not None
        assert "tax.corporate_rate_override" in f.engine_path_conditional
        assert "country_tax_policy_id" in f.engine_path_conditional
        assert "country_tax_policy_id is set" in f.engine_path_conditional


# ---------------------------------------------------------------------------
# §3 — Dual-mode authority contract
# ---------------------------------------------------------------------------

class TestDualModeAuthority:
    def test_tuho_edit_maps_to_typed_override(self):
        pi = _v2_edit(create_default_tuho_wind1(), 25.0)
        assert pi.tax.country_tax_policy_id == TUHO_POLICY_ID
        assert pi.tax.corporate_rate_override == pytest.approx(0.25)
        # legacy field keeps the policy default — no second authority created
        assert pi.tax.corporate_rate == pytest.approx(0.18)
        # adapter resolves exactly the edited rate over the selected policy
        assert _resolved_policy_rate(pi) == pytest.approx(0.25)

    def test_generic_solar_edit_keeps_legacy_authority(self):
        pi = _v2_edit(create_default_solar_project(), 30.0)
        assert pi.tax.country_tax_policy_id is None
        assert pi.tax.corporate_rate == pytest.approx(0.30)
        assert pi.tax.corporate_rate_override is None

    def test_generic_wind_edit_keeps_legacy_authority(self):
        pi = _v2_edit(create_default_wind_project(), 22.5)
        assert pi.tax.country_tax_policy_id is None
        assert pi.tax.corporate_rate == pytest.approx(0.225)
        assert pi.tax.corporate_rate_override is None

    def test_oborovo_no_policy_stays_on_legacy_authority(self):
        """§8: Oborovo has no selected typed country policy — it must stay on
        its current (legacy corporate_rate) authority and remain unaffected
        by the typed-override routing."""
        base = create_default_oborovo()
        assert base.tax.country_tax_policy_id is None
        assert base.tax.corporate_rate_override is None
        assert base.tax.corporate_rate == pytest.approx(0.10)
        pi = _v2_edit(base, 12.0)
        assert pi.tax.corporate_rate == pytest.approx(0.12)
        assert pi.tax.corporate_rate_override is None
        # still runs through the adapter without any conflict
        assert _resolved_policy_rate(pi) == pytest.approx(0.12)


# ---------------------------------------------------------------------------
# §5 — Explicit backward-compatibility semantic states
# ---------------------------------------------------------------------------

class TestSemanticStates:
    def _policy_pi(self, *, override=None, legacy=0.18):
        import dataclasses
        pi = create_default_tuho_wind1()
        return dataclasses.replace(
            pi.tax, corporate_rate_override=override,
            corporate_rate=legacy) if False else dataclasses.replace(
            pi, tax=dataclasses.replace(
                pi.tax, corporate_rate_override=override,
                corporate_rate=legacy))

    def test_no_policy_plus_legacy_rate_ok(self):
        from financial_engine.adapters.tax_inputs import (
            build_tax_contract_from_project_inputs,
        )
        pi = _v2_edit(create_default_solar_project(), 28.0)
        assert build_tax_contract_from_project_inputs(
            pi).policy.corporate_rate == pytest.approx(0.28)

    def test_policy_no_override_legacy_equals_default_ok(self):
        assert _resolved_policy_rate(self._policy_pi()) == pytest.approx(0.18)

    def test_policy_with_explicit_override_ok(self):
        assert _resolved_policy_rate(
            self._policy_pi(override=0.22)) == pytest.approx(0.22)

    def test_policy_legacy_default_plus_override_ok(self):
        assert _resolved_policy_rate(
            self._policy_pi(override=0.22, legacy=0.18)) == pytest.approx(0.22)

    def test_policy_conflicting_legacy_no_override_fails_closed(self):
        """§4: the fail-closed guard is NOT weakened — a genuinely
        contradictory historical/manual state still raises."""
        from financial_engine.adapters.tax_inputs import (
            build_tax_contract_from_project_inputs,
        )
        with pytest.raises(ValueError, match="COUNTRY_TAX_LEGACY_FIELD_CONFLICT"):
            build_tax_contract_from_project_inputs(
                self._policy_pi(legacy=0.30))

    def test_explicit_zero_is_not_missing(self):
        pi = _v2_edit(create_default_tuho_wind1(), 0.0)
        assert pi.tax.corporate_rate_override == 0.0
        assert _resolved_policy_rate(pi) == 0.0


# ---------------------------------------------------------------------------
# §6 — TUHO full causal coverage through the REAL V2 edit path
# ---------------------------------------------------------------------------

class TestTuhoWorkbookJourney:
    @staticmethod
    def _edit_snapshot(cit_pct: str):
        """Public V2 edit: validate → apply to snapshot (as the CAS persist
        does) → materialise → typed resolution."""
        from app.workbook.update_service import WorkbookUpdateService
        v = WorkbookUpdateService.validate_field_update(CIT_FIELD_ID, cit_pct)
        assert v.is_valid, v.error
        snap = _tuho_working_copy_snapshot()
        snap[CIT_SNAPSHOT_KEY] = str(v.typed_value)
        return _materialise(snap), v.typed_value

    def test_a_factory_no_edit_baseline(self):
        pi = _materialise(_tuho_working_copy_snapshot())
        assert pi.tax.country_tax_policy_id == TUHO_POLICY_ID
        assert pi.tax.corporate_rate_override is None
        assert pi.tax.corporate_rate == pytest.approx(0.18)
        assert _resolved_policy_rate(pi) == pytest.approx(0.18)

    def test_b_save_and_reload_without_economic_cit_change(self):
        # a draft saved and reloaded without a CIT edit has no CIT key at all
        pis_snap = _tuho_working_copy_snapshot()
        pi = _materialise(pis_snap)
        assert pi.tax.corporate_rate_override is None
        assert pi.tax.corporate_rate == pytest.approx(0.18)
        assert _resolved_policy_rate(pi) == pytest.approx(0.18)

    def test_c_equal_value_edit_preserves_economics(self):
        pi, typed = self._edit_snapshot("18.0")
        assert typed == 18.0
        assert pi.tax.corporate_rate_override == pytest.approx(0.18)
        assert pi.tax.corporate_rate == pytest.approx(0.18)
        assert _resolved_policy_rate(pi) == pytest.approx(0.18)

    def test_d_higher_edit_becomes_typed_override(self):
        pi, _ = self._edit_snapshot("20.0")
        assert pi.tax.corporate_rate_override == pytest.approx(0.20)
        assert pi.tax.corporate_rate == pytest.approx(0.18)
        assert _resolved_policy_rate(pi) == pytest.approx(0.20)

    def test_e_lower_edit_becomes_typed_override(self):
        pi, _ = self._edit_snapshot("15.0")
        assert pi.tax.corporate_rate_override == pytest.approx(0.15)
        assert _resolved_policy_rate(pi) == pytest.approx(0.15)

    def test_f_explicit_zero_rate(self):
        pi, typed = self._edit_snapshot("0")
        assert typed == 0.0
        assert pi.tax.corporate_rate_override == 0.0
        assert _resolved_policy_rate(pi) == 0.0

    def test_snapshot_persistence_round_trip_is_idempotent(self):
        """Persisted value → PIS → canonical TaxParams twice (save/reload)
        yields the identical typed authority — no drift, no stacking."""
        snap = _tuho_working_copy_snapshot("15.0")
        pi1 = _materialise(snap)
        # simulate a save/reload: re-serialise the value verbatim
        snap2 = dict(snap)
        snap2[CIT_SNAPSHOT_KEY] = str(float(snap[CIT_SNAPSHOT_KEY]))
        pi2 = _materialise(snap2)
        assert pi1.tax.corporate_rate_override == pi2.tax.corporate_rate_override
        assert _resolved_policy_rate(pi1) == _resolved_policy_rate(pi2)


# ---------------------------------------------------------------------------
# §7 — Downstream financial causality with an actual canonical Run
# ---------------------------------------------------------------------------

class TestRunTaxFingerprint:
    @staticmethod
    def _reference_snapshot(cit_pct=None):
        """The REAL TUHO reference baseline snapshot (same builder the
        library clone path uses), optionally with a persisted CIT edit."""
        from app.persistence.projects_repository import _compute_baseline_snapshot
        snap = dict(_compute_baseline_snapshot("Wind", "tuho"))
        snap["project_origin"] = "user_created"  # working copy, editable
        if cit_pct is not None:
            snap[CIT_SNAPSHOT_KEY] = cit_pct
        return snap

    @pytest.fixture(scope="class")
    def runs(self):
        from app.api.project_runner import run_project
        base_pi = _materialise(self._reference_snapshot())
        edited_pi = _materialise(self._reference_snapshot("15.0"))
        base = run_project("TUHO", "Base", project_inputs_override=base_pi)
        edited = run_project("TUHO", "Base", project_inputs_override=edited_pi)
        return base_pi, edited_pi, base, edited

    def test_material_edit_changes_total_tax_and_xirr(self, runs):
        _, _, base, edited = runs
        assert edited["kpis"]["total_tax_keur"] < base["kpis"]["total_tax_keur"]
        assert edited["kpis"]["project_irr"] > base["kpis"]["project_irr"]

    def test_positive_taxable_period_shows_causal_rate_effect(self, runs):
        """Find periods with positive taxable income in BOTH runs and prove
        the edited run's cash tax in those periods is strictly lower
        (0.15/0.18 ratio), while non-monotonic/zero periods are tolerated."""
        _, _, base, edited = runs

        def _period_tax(result):
            ts = result.get("tax_schedule")
            rows = ts["periods"] if isinstance(ts, dict) else ts.period_results
            out = {}
            for pr in rows:
                idx = pr["period"] if isinstance(pr, dict) else pr.period_index
                taxable = (
                    pr.get("taxable_profit_keur")
                    if isinstance(pr, dict)
                    else getattr(pr, "taxable_profit_after_losses_keur", None)
                )
                cash = (
                    pr.get("corporate_tax_cash_keur")
                    if isinstance(pr, dict)
                    else getattr(pr, "cash_tax_current_period_keur", None)
                )
                out[idx] = (taxable, cash)
            return out

        b, e = _period_tax(base), _period_tax(edited)
        # Only periods that actually PAY cash tax in the base run are
        # causally comparable; periods with zero base cash tax (tax-year
        # payment lag / loss carryforward) are tolerated as non-monotonic.
        comparable = [
            idx for idx in b
            if (b[idx][0] or 0) > 0 and (b[idx][1] or 0) > 0
            and e[idx][1] is not None
        ]
        assert comparable, "expected at least one positively-taxed period"
        for idx in comparable:
            assert e[idx][1] < b[idx][1], idx

    def test_edit_does_not_touch_unrelated_assumptions(self, runs):
        base_pi, edited_pi, _, _ = runs
        assert edited_pi.capex == base_pi.capex
        assert edited_pi.opex == base_pi.opex
        assert edited_pi.revenue == base_pi.revenue
        assert edited_pi.financing == base_pi.financing
        assert edited_pi.technical == base_pi.technical
        t0, t1 = base_pi.tax, edited_pi.tax
        assert t1.country_tax_policy_id == t0.country_tax_policy_id
        assert t1.loss_carryforward_years == t0.loss_carryforward_years
        assert t1.opening_tax_loss_vintages == t0.opening_tax_loss_vintages
        assert t1.atad_enabled == t0.atad_enabled
        assert t1.thin_cap_enabled == t0.thin_cap_enabled
        assert t1.interest_limitation_policy == t0.interest_limitation_policy


# ---------------------------------------------------------------------------
# §9 — Scenario semantics
# ---------------------------------------------------------------------------

class TestScenarioSemantics:
    def test_scenario_cit_override_routes_by_typed_state(self):
        from app.workbook.update_service import WorkbookUpdateService
        v = WorkbookUpdateService.validate_field_update(CIT_FIELD_ID, "22.0")
        assert v.is_valid
        # scenario snapshot on a TUHO working copy → typed override
        tuho_scen = _tuho_working_copy_snapshot(str(v.typed_value))
        pi_tuho = _materialise(tuho_scen)
        assert pi_tuho.tax.corporate_rate_override == pytest.approx(0.22)
        assert _resolved_policy_rate(pi_tuho) == pytest.approx(0.22)
        # the same scenario override on a generic (no-policy) snapshot →
        # legacy corporate_rate authority
        generic_scen = {
            "template_source": "", "project_type": "Solar",
            "project_name": "Generic", "country_market": "DE",
            "capacity_mw": "10", "cod_date": "2027-01-01",
            "construction_months": "6", "horizon_years": "25",
            "tariff_eur_mwh": "70", "ppa_term_years": "20",
            "p50_hours": "2000", "opex_y1_keur": "400",
            "total_capex_keur": "10000", "gearing_pct": "",
            "interest_rate_pct": "5", "tenor_years": "15",
            "target_dscr": "1.35", CIT_SNAPSHOT_KEY: str(v.typed_value),
        }
        pi_gen = _materialise(generic_scen)
        assert pi_gen.tax.corporate_rate == pytest.approx(0.22)
        assert pi_gen.tax.corporate_rate_override is None

    def test_base_scenario_base_round_trip_has_no_stale_override(self):
        """Switch Base → scenario → Base: the restored Base draft carries no
        CIT value, so the re-materialised inputs have NO stale typed
        override and identical economics to the original Base."""
        base_snap = _tuho_working_copy_snapshot()
        pi_base = _materialise(base_snap)
        scen_snap = _tuho_working_copy_snapshot("22.0")
        pi_scen = _materialise(scen_snap)
        assert pi_scen.tax.corporate_rate_override == pytest.approx(0.22)
        # switching back to Base restores the Base draft verbatim
        pi_restored = _materialise(dict(base_snap))
        assert pi_restored.tax.corporate_rate_override is None
        assert _resolved_policy_rate(pi_restored) == pytest.approx(0.18)
        assert _resolved_policy_rate(pi_restored) == _resolved_policy_rate(pi_base)


# ---------------------------------------------------------------------------
# §10 — R3 numeric safety preserved on the CIT field
# ---------------------------------------------------------------------------

class TestR3NumericSafetyPreserved:
    @pytest.mark.parametrize("raw", ["nan", "NaN", "inf", "-inf", "Infinity",
                                     "-Infinity", "1e400", "-1e400", "abc"])
    def test_non_finite_and_non_numeric_rejected(self, raw):
        from app.workbook.update_service import WorkbookUpdateService
        v = WorkbookUpdateService.validate_field_update(CIT_FIELD_ID, raw)
        assert not v.is_valid, raw

    @pytest.mark.parametrize("raw,expected", [
        ("18.0", 18.0),   # exact float that is an integer value stays float
        ("18", 18.0),     # integer string accepted as the percentage 18 %
        ("0", 0.0),       # explicit zero accepted
        ("100", 100.0),   # upper registry bound accepted
    ])
    def test_valid_numeric_semantics_preserved(self, raw, expected):
        from app.workbook.update_service import WorkbookUpdateService
        v = WorkbookUpdateService.validate_field_update(CIT_FIELD_ID, raw)
        assert v.is_valid, raw
        assert v.typed_value == pytest.approx(expected)

    def test_out_of_bounds_rejected(self):
        from app.workbook.update_service import WorkbookUpdateService
        assert not WorkbookUpdateService.validate_field_update(
            CIT_FIELD_ID, "100.01").is_valid
        assert not WorkbookUpdateService.validate_field_update(
            CIT_FIELD_ID, "-0.5").is_valid
