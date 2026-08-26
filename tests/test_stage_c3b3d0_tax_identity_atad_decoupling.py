"""Stage C3B3D0 — Tax identity (deductible-only) and ATAD/thin-cap decoupling tests.

Covers:
1. TestAtadBindingIdentity      — controlled ATAD-binding example, TI=2500
2. TestAtadNoBindingIdentity    — ATAD doesn't bind, no change
3. TestAtadEnabledField         — atad_enabled independent of thin_cap_enabled
4. TestAtadEnabledSerialization — round-trip with/without field in payload
5. TestNoFinancialDrift         — Oborovo/TUHO outputs match BASE values exactly
6. TestDisallowedInterestAuditOnly — disallowed not added to taxable income
"""
from __future__ import annotations

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 1. ATAD binding identity — correct TI=2500
# ─────────────────────────────────────────────────────────────────────────────
class TestAtadBindingIdentity:
    """Controlled example proving correct deductible-only identity when ATAD binds."""

    def _result(self):
        from finco_core.waterfall.tax_engine import compute_period_tax
        return compute_period_tax(
            ebitda_keur=5000.0,
            depreciation_keur=1000.0,
            senior_interest_keur=2000.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
            atad_applies=True,
            atad_ebitda_limit=0.30,
            atad_min_threshold_keur=1000.0,
        )

    def test_atad_binds(self):
        r = self._result()
        # ebitda_limit = 5000*0.30 = 1500; min_threshold = 1000; cap = 1500
        # 2000 > 1500 → ATAD binds
        assert r.deductible_interest_keur == pytest.approx(1500.0)
        assert r.disallowed_interest_keur == pytest.approx(500.0)

    def test_taxable_income_before_losses_correct(self):
        """TI = 5000 - 1000 - 1500 = 2500, NOT 3000 (old wrong result)."""
        r = self._result()
        assert r.taxable_income_before_losses_keur == pytest.approx(2500.0)

    def test_not_old_wrong_result(self):
        """Old formula would give 3000; correct is 2500."""
        r = self._result()
        assert r.taxable_income_before_losses_keur != pytest.approx(3000.0)

    def test_gross_interest_formulation_equivalent(self):
        """Algebraic check: EBITDA - dep - gross + disallowed = same TI."""
        r = self._result()
        gross_check = 5000.0 - 1000.0 - 2000.0 + 500.0  # = 2500
        assert gross_check == pytest.approx(2500.0)
        assert r.taxable_income_before_losses_keur == pytest.approx(gross_check)

    def test_tax_correct(self):
        r = self._result()
        assert r.tax_keur == pytest.approx(250.0)


# ─────────────────────────────────────────────────────────────────────────────
# 2. ATAD no-binding identity
# ─────────────────────────────────────────────────────────────────────────────
class TestAtadNoBindingIdentity:
    """When ATAD doesn't bind, no change vs old formula (disallowed=0 either way)."""

    def _result(self):
        from finco_core.waterfall.tax_engine import compute_period_tax
        return compute_period_tax(
            ebitda_keur=5000.0,
            depreciation_keur=1000.0,
            senior_interest_keur=500.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
            atad_applies=True,
            atad_ebitda_limit=0.30,
            atad_min_threshold_keur=3000.0,
        )

    def test_atad_does_not_bind(self):
        r = self._result()
        # 500 < max(1500, 3000) = 3000 → no binding
        assert r.deductible_interest_keur == pytest.approx(500.0)
        assert r.disallowed_interest_keur == pytest.approx(0.0)

    def test_taxable_income(self):
        r = self._result()
        # TI = 5000 - 1000 - 500 = 3500
        assert r.taxable_income_before_losses_keur == pytest.approx(3500.0)


# ─────────────────────────────────────────────────────────────────────────────
# 3. atad_enabled field independence
# ─────────────────────────────────────────────────────────────────────────────
class TestAtadEnabledField:
    """atad_enabled and thin_cap_enabled are independent fields in TaxParams."""

    def test_atad_true_thin_cap_false(self):
        from finco_core.inputs._models import TaxParams
        tp = TaxParams(atad_enabled=True, thin_cap_enabled=False)
        assert tp.atad_enabled is True
        assert tp.thin_cap_enabled is False

    def test_atad_false_thin_cap_true(self):
        from finco_core.inputs._models import TaxParams, ShlInterestDeductibilityMode
        tp = TaxParams(atad_enabled=False, thin_cap_enabled=True,
                       shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE)
        assert tp.atad_enabled is False
        assert tp.thin_cap_enabled is True

    def test_both_true(self):
        from finco_core.inputs._models import TaxParams, ShlInterestDeductibilityMode
        tp = TaxParams(
            atad_enabled=True,
            thin_cap_enabled=True,
            shl_interest_deductibility=ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS,
        )
        assert tp.atad_enabled is True
        assert tp.thin_cap_enabled is True

    def test_default_atad_enabled_false(self):
        """Generic TaxParams() must NOT silently activate jurisdiction-specific ATAD."""
        from finco_core.inputs._models import TaxParams
        tp = TaxParams()
        assert tp.atad_enabled is False

    def test_atad_enabled_not_derived_from_thin_cap(self):
        """Changing thin_cap_enabled must not affect atad_enabled."""
        from finco_core.inputs._models import TaxParams
        tp_a = TaxParams(thin_cap_enabled=False)
        tp_b = TaxParams(thin_cap_enabled=True,
                         shl_interest_deductibility=__import__(
                             "finco_core.inputs._models", fromlist=["ShlInterestDeductibilityMode"]
                         ).ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE)
        # atad_enabled should be False in both cases (default)
        assert tp_a.atad_enabled is False
        assert tp_b.atad_enabled is False


# ─────────────────────────────────────────────────────────────────────────────
# 4. Serialization round-trip
# ─────────────────────────────────────────────────────────────────────────────
class TestAtadEnabledSerialization:
    """atad_enabled round-trips through serialization correctly."""

    def _roundtrip(self, project):
        import json
        from finco_core.inputs.serialization import project_inputs_to_dict as serialize_inputs, project_inputs_from_dict as deserialize_inputs
        payload = serialize_inputs(project)
        raw = json.dumps(payload)
        return deserialize_inputs(json.loads(raw))

    def test_atad_enabled_oborovo_roundtrip(self):
        """Oborovo atad_enabled=False (workbook BS!G45=False) survives round-trip."""
        from app.project_factories import create_default_oborovo
        p = create_default_oborovo()
        assert p.tax.atad_enabled is False  # C3B1 source: workbook ATAD=False for Oborovo
        p2 = self._roundtrip(p)
        assert p2.tax.atad_enabled is False

    def test_atad_enabled_true_explicit_roundtrip(self):
        """atad_enabled=True survives round-trip when set explicitly."""
        import dataclasses
        import json
        from app.project_factories import create_default_oborovo
        from finco_core.inputs.serialization import project_inputs_to_dict as serialize_inputs, project_inputs_from_dict as deserialize_inputs
        p = create_default_oborovo()
        p2 = dataclasses.replace(p, tax=dataclasses.replace(p.tax, atad_enabled=True))
        payload = serialize_inputs(p2)
        p3 = deserialize_inputs(json.loads(json.dumps(payload)))
        assert p3.tax.atad_enabled is True

    def test_old_payload_thin_cap_false_gives_atad_false(self):
        """Old payload without atad_enabled + thin_cap=False → atad=False."""
        import json
        from app.project_factories import create_default_oborovo
        from finco_core.inputs.serialization import project_inputs_to_dict as serialize_inputs, project_inputs_from_dict as deserialize_inputs
        p = create_default_oborovo()
        payload = serialize_inputs(p)
        # thin_cap_enabled=False for Oborovo
        if "atad_enabled" in payload.get("tax", {}):
            del payload["tax"]["atad_enabled"]
        assert payload["tax"]["thin_cap_enabled"] is False
        p2 = deserialize_inputs(json.loads(json.dumps(payload)))
        assert p2.tax.atad_enabled is False

    def test_old_payload_thin_cap_true_gives_atad_true(self):
        """Old payload without atad_enabled + thin_cap=True → atad=True."""
        import json
        import dataclasses
        from app.project_factories import create_default_oborovo
        from finco_core.inputs.serialization import project_inputs_to_dict as serialize_inputs, project_inputs_from_dict as deserialize_inputs
        p = create_default_oborovo()
        # Force thin_cap=True, keep FULLY_NON_DEDUCTIBLE (compatible)
        p2 = dataclasses.replace(p, tax=dataclasses.replace(p.tax, thin_cap_enabled=True, atad_enabled=True))
        payload = serialize_inputs(p2)
        del payload["tax"]["atad_enabled"]
        assert payload["tax"]["thin_cap_enabled"] is True
        p3 = deserialize_inputs(json.loads(json.dumps(payload)))
        assert p3.tax.atad_enabled is True


# ─────────────────────────────────────────────────────────────────────────────
# 5. No financial drift
# ─────────────────────────────────────────────────────────────────────────────
class TestNoFinancialDrift:
    """Oborovo and TUHO outputs remain locked on the canonical PR-F1 axis."""

    BASE = {
        "oborovo": dict(
            tax=8490.320140,
            dist=64006.489082,
            senior_ds=63191.174225,
            proj_irr=0.07972912,
            eq_irr=0.10348369,
        ),
        "tuho": dict(
            tax=36994.270322,
            dist=165423.195150,
            senior_ds=65826.388280,
            proj_irr=0.09438932,
            eq_irr=0.11319445,
        ),
    }

    def _run(self, factory):
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
        p = factory()
        engine = _build_period_engine(p)
        config = WaterfallRunConfig.from_inputs(p, engine)
        return WaterfallRunner(p, engine).run(config)

    def test_oborovo_no_drift(self):
        from app.project_factories import create_default_oborovo_legacy_calibration
        r = self._run(create_default_oborovo_legacy_calibration)
        b = self.BASE["oborovo"]
        assert r.total_tax_keur == pytest.approx(b["tax"], abs=0.001)
        assert r.total_distribution_keur == pytest.approx(b["dist"], abs=0.001)
        assert r.total_senior_ds_keur == pytest.approx(b["senior_ds"], abs=0.001)
        assert r.project_irr == pytest.approx(b["proj_irr"], abs=1e-6)
        assert r.equity_irr == pytest.approx(b["eq_irr"], abs=1e-6)

    def test_tuho_no_drift(self):
        from app.project_factories import create_default_tuho_wind1
        r = self._run(create_default_tuho_wind1)
        b = self.BASE["tuho"]
        assert r.total_tax_keur == pytest.approx(b["tax"], abs=0.001)
        assert r.total_distribution_keur == pytest.approx(b["dist"], abs=0.001)
        assert r.total_senior_ds_keur == pytest.approx(b["senior_ds"], abs=0.001)
        assert r.project_irr == pytest.approx(b["proj_irr"], abs=1e-6)
        assert r.equity_irr == pytest.approx(b["eq_irr"], abs=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# 6. disallowed_interest is audit only
# ─────────────────────────────────────────────────────────────────────────────
class TestDisallowedInterestAuditOnly:
    """disallowed_interest_keur is present in TaxPeriodResult but NOT added to TI."""

    def test_disallowed_present_in_result(self):
        from finco_core.waterfall.tax_engine import compute_period_tax
        r = compute_period_tax(
            ebitda_keur=5000.0,
            depreciation_keur=1000.0,
            senior_interest_keur=2000.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
            atad_applies=True,
            atad_ebitda_limit=0.30,
            atad_min_threshold_keur=1000.0,
        )
        # disallowed is 500 — present as audit field
        assert r.disallowed_interest_keur == pytest.approx(500.0)

    def test_disallowed_not_added_to_taxable_income(self):
        """If disallowed were added to TI, result would be 3000, not 2500."""
        from finco_core.waterfall.tax_engine import compute_period_tax
        r = compute_period_tax(
            ebitda_keur=5000.0,
            depreciation_keur=1000.0,
            senior_interest_keur=2000.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
            atad_applies=True,
            atad_ebitda_limit=0.30,
            atad_min_threshold_keur=1000.0,
        )
        # Correct deductible-only: TI = 5000 - 1000 - 1500 = 2500
        # Wrong (old) formula: TI = 5000 - 1000 - 1500 + 500 = 3000
        assert r.taxable_income_before_losses_keur == pytest.approx(2500.0)
        assert r.taxable_income_before_losses_keur != pytest.approx(3000.0)

    def test_disallowed_consistent_with_deductible(self):
        from finco_core.waterfall.tax_engine import compute_period_tax
        r = compute_period_tax(
            ebitda_keur=5000.0,
            depreciation_keur=1000.0,
            senior_interest_keur=2000.0,
            shl_interest_keur=0.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
            atad_applies=True,
            atad_ebitda_limit=0.30,
            atad_min_threshold_keur=1000.0,
        )
        # deductible + disallowed = gross_interest
        assert r.deductible_interest_keur + r.disallowed_interest_keur == pytest.approx(2000.0)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Generic Solar/Wind — atad_enabled is False
# ─────────────────────────────────────────────────────────────────────────────
class TestGenericProjectAtad:
    """Generic Solar and Wind projects must not silently activate ATAD."""

    def test_solar_atad_disabled(self):
        from app.project_factories import create_default_solar_project
        p = create_default_solar_project()
        assert p.tax.atad_enabled is False

    def test_wind_atad_disabled(self):
        from app.project_factories import create_default_wind_project
        p = create_default_wind_project()
        assert p.tax.atad_enabled is False


# ─────────────────────────────────────────────────────────────────────────────
# 8. No financial drift — Solar and Wind
# ─────────────────────────────────────────────────────────────────────────────
class TestNoFinancialDriftGeneric:
    """Solar and Wind outputs remain locked on the canonical PR-F1 axis."""

    BASE = {
        "solar": dict(
            tax=9428.571521,
            dist=19841.892207,
            senior_ds=36928.460619,
            proj_irr=0.07187342,
            eq_irr=0.16305334,
        ),
        "wind": dict(
            tax=31090.265455,
            dist=72964.191873,
            senior_ds=49147.882569,
            proj_irr=0.10503091,
            eq_irr=0.26210647,
        ),
    }

    def _run(self, factory):
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
        p = factory()
        engine = _build_period_engine(p)
        config = WaterfallRunConfig.from_inputs(p, engine)
        return WaterfallRunner(p, engine).run(config)

    def test_solar_no_drift(self):
        from app.project_factories import create_default_solar_project
        r = self._run(create_default_solar_project)
        b = self.BASE["solar"]
        assert r.total_tax_keur == pytest.approx(b["tax"], abs=0.001)
        assert r.total_distribution_keur == pytest.approx(b["dist"], abs=0.001)
        assert r.total_senior_ds_keur == pytest.approx(b["senior_ds"], abs=0.001)
        assert r.project_irr == pytest.approx(b["proj_irr"], abs=1e-6)
        assert r.equity_irr == pytest.approx(b["eq_irr"], abs=1e-6)

    def test_wind_no_drift(self):
        from app.project_factories import create_default_wind_project
        r = self._run(create_default_wind_project)
        b = self.BASE["wind"]
        assert r.total_tax_keur == pytest.approx(b["tax"], abs=0.001)
        assert r.total_distribution_keur == pytest.approx(b["dist"], abs=0.001)
        assert r.total_senior_ds_keur == pytest.approx(b["senior_ds"], abs=0.001)
        assert r.project_irr == pytest.approx(b["proj_irr"], abs=1e-6)
        assert r.equity_irr == pytest.approx(b["eq_irr"], abs=1e-6)
