"""Stage C2B2: Revenue input-authority acceptance tests.

Tests A–E verify that canonical rev_* snapshot keys wire through the full
adapter → resolver → ProjectInputs chain and do not disturb factory defaults
when absent.

Financial freeze: default Oborovo outputs must not change from C2B baseline.
"""
from __future__ import annotations

import json
import pytest


# ---------------------------------------------------------------------------
# A: Merchant balancing % wires through snapshot adapter
# ---------------------------------------------------------------------------

class TestAcceptanceAMerchantBalancing:
    """rev_merchant_balancing_pct → revenue.balancing_cost_pv (as fraction)."""

    def test_canonical_key_sets_balancing_cost_pv(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs

        base = create_default_oborovo()
        # Build a minimal valid snapshot that carries the canonical balancing key.
        snap = _oborovo_snapshot_base(base)
        snap["rev_merchant_balancing_pct"] = "3.5"  # 3.5%

        kwargs = _snapshot_to_dict(snap)
        proj = _resolve_user_inputs(base_inputs=base, **kwargs)

        assert abs(proj.revenue.balancing_cost_pv - 0.035) < 1e-9

    def test_absent_canonical_key_preserves_factory_default(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs

        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        # No rev_merchant_balancing_pct → factory default 0.025 preserved.
        kwargs = _snapshot_to_dict(snap)
        proj = _resolve_user_inputs(base_inputs=base, **kwargs)

        assert abs(proj.revenue.balancing_cost_pv - 0.025) < 1e-9


# ---------------------------------------------------------------------------
# B: CO2 price EUR/MWh wires through snapshot adapter
# ---------------------------------------------------------------------------

class TestAcceptanceBCO2Price:
    """rev_co2_price_eur_mwh → revenue.co2_certificate_price_eur_per_mwh."""

    def test_canonical_co2_key_sets_certificate_price(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs

        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        snap["rev_co2_price_eur_mwh"] = "2.0"

        kwargs = _snapshot_to_dict(snap)
        proj = _resolve_user_inputs(base_inputs=base, **kwargs)

        assert abs(proj.revenue.co2_certificate_price_eur_per_mwh - 2.0) < 1e-9

    def test_absent_co2_key_leaves_factory_certificate_price(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs

        base = create_default_oborovo()
        factory_cert_price = base.revenue.co2_certificate_price_eur_per_mwh
        snap = _oborovo_snapshot_base(base)
        kwargs = _snapshot_to_dict(snap)
        proj = _resolve_user_inputs(base_inputs=base, **kwargs)

        assert proj.revenue.co2_certificate_price_eur_per_mwh == factory_cert_price

    def test_co2_enabled_toggle(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs

        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        snap["rev_co2_enabled"] = "false"

        kwargs = _snapshot_to_dict(snap)
        proj = _resolve_user_inputs(base_inputs=base, **kwargs)

        assert proj.revenue.co2_enabled is False


# ---------------------------------------------------------------------------
# C: Merchant price curve JSON wires through snapshot adapter
# ---------------------------------------------------------------------------

class TestAcceptanceCMerchantCurve:
    """rev_merchant_price_curve_json → market_prices_by_calendar_year_eur_mwh."""

    def test_json_curve_sets_calendar_year_schedule(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs

        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        curve = [{"year": 2050, "price_eur_mwh": 88.0}, {"year": 2051, "price_eur_mwh": 90.0}]
        snap["rev_merchant_price_curve_json"] = json.dumps(curve)

        kwargs = _snapshot_to_dict(snap)
        proj = _resolve_user_inputs(base_inputs=base, **kwargs)

        assert proj.revenue.market_price_calendar_start_year == 2050
        assert proj.revenue.market_prices_by_calendar_year_eur_mwh == (88.0, 90.0)

    def test_invalid_json_raises_value_error(self):
        """Invalid JSON must be rejected with ValueError — not silently skipped."""
        import pytest
        from app.input_adapter import validate_merchant_curve_json

        with pytest.raises(ValueError, match="Invalid JSON"):
            validate_merchant_curve_json("NOT_JSON")

    def test_absent_curve_preserves_factory_schedule(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs

        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        kwargs = _snapshot_to_dict(snap)
        proj = _resolve_user_inputs(base_inputs=base, **kwargs)

        assert proj.revenue.market_price_calendar_start_year == base.revenue.market_price_calendar_start_year
        assert proj.revenue.market_prices_by_calendar_year_eur_mwh == base.revenue.market_prices_by_calendar_year_eur_mwh


# ---------------------------------------------------------------------------
# D: PPA fields wire through snapshot adapter
# ---------------------------------------------------------------------------

class TestAcceptanceDPpaFields:
    """Canonical rev_ppa_* keys win over legacy keys."""

    def test_canonical_tariff_wins_over_legacy(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs

        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        snap["tariff_eur_mwh"] = "50.0"      # legacy — should lose
        snap["rev_ppa_base_tariff"] = "60.0"  # canonical — should win

        kwargs = _snapshot_to_dict(snap)
        proj = _resolve_user_inputs(base_inputs=base, **kwargs)

        assert abs(proj.revenue.ppa_base_tariff - 60.0) < 1e-9

    def test_legacy_tariff_used_when_canonical_absent(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs

        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        snap["tariff_eur_mwh"] = "50.0"
        # No rev_ppa_base_tariff

        kwargs = _snapshot_to_dict(snap)
        proj = _resolve_user_inputs(base_inputs=base, **kwargs)

        assert abs(proj.revenue.ppa_base_tariff - 50.0) < 1e-9

    def test_canonical_ppa_index_sets_escalation_rate(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs

        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        snap["rev_ppa_index"] = "2.5"  # UI % → adapter divides by 100 → engine 0.025

        kwargs = _snapshot_to_dict(snap)
        proj = _resolve_user_inputs(base_inputs=base, **kwargs)

        assert abs(proj.revenue.ppa_index - 0.025) < 1e-9

    def test_canonical_indexation_policy_sets_policy_field(self):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs

        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        snap["rev_ppa_indexation_start_policy"] = "CONTRACT_ANNIVERSARY"
        snap["rev_ppa_indexation_start_date"] = "2024-01-01"  # required for CONTRACT_ANNIVERSARY

        kwargs = _snapshot_to_dict(snap)
        proj = _resolve_user_inputs(base_inputs=base, **kwargs)

        assert proj.revenue.ppa_indexation_start_policy == "CONTRACT_ANNIVERSARY"


# ---------------------------------------------------------------------------
# E: Registry semantics are correct (protection / version / field contracts)
# ---------------------------------------------------------------------------

class TestAcceptanceERegistrySemantics:
    """Registry version, field contracts, and balancing semantic separation."""

    def test_workbook_version_is_2_3_0(self):
        from app.workbook.registry import WORKBOOK
        assert WORKBOOK.version == "2.3.0"

    def test_merchant_balancing_pct_field_maps_to_balancing_cost_pv(self):
        from app.workbook.registry import WORKBOOK
        field = WORKBOOK.field("revenue.balancing.merchant_pct")
        assert field.snapshot_key == "rev_merchant_balancing_pct"
        assert field.engine_path == "revenue.balancing_cost_pv"

    def test_balancing_cost_eur_per_mwh_field_maps_separately(self):
        from app.workbook.registry import WORKBOOK
        field = WORKBOOK.field("revenue.balancing.cost_eur_per_mwh")
        assert field.snapshot_key == "rev_balancing_cost_eur_per_mwh"
        assert field.engine_path == "revenue.balancing_cost_eur_per_mwh"

    def test_co2_price_field_uses_eur_per_mwh_not_eur_per_tco2(self):
        from app.workbook.registry import WORKBOOK
        field = WORKBOOK.field("revenue.balancing.co2_price_eur_mwh")
        assert field.snapshot_key == "rev_co2_price_eur_mwh"
        assert field.engine_path == "revenue.co2_certificate_price_eur_per_mwh"
        assert field.unit == "EUR/MWh"

    def test_ppa_base_tariff_is_bound_not_excluded(self):
        from app.workbook.registry import WORKBOOK
        from app.workbook.specs import BindingStatus
        field = WORKBOOK.field("revenue.ppa.base_tariff")
        assert field.binding_status == BindingStatus.BOUND

    def test_merchant_price_curve_field_exists(self):
        from app.workbook.registry import WORKBOOK
        field = WORKBOOK.field("revenue.merchant.price_curve_json")
        assert field.snapshot_key == "rev_merchant_price_curve_json"

    def test_no_project_dispatch_in_resolver(self):
        """Revenue resolution must not branch on project name or code.

        Behavioral proof: clone Oborovo with different name/code and verify
        identical revenue parameters — proving the resolver is project-agnostic.
        """
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs

        base = create_default_oborovo()

        snap_a = _oborovo_snapshot_base(base)
        snap_a["project_name"] = "Oborovo"
        snap_a["project_code"] = "OBR-001"

        snap_b = _oborovo_snapshot_base(base)
        snap_b["project_name"] = "NotOborovo"
        snap_b["project_code"] = "XYZ-999"

        proj_a = _resolve_user_inputs(base_inputs=base, **_snapshot_to_dict(snap_a))
        proj_b = _resolve_user_inputs(base_inputs=base, **_snapshot_to_dict(snap_b))

        rev_a = proj_a.revenue
        rev_b = proj_b.revenue
        assert abs(rev_a.ppa_base_tariff - rev_b.ppa_base_tariff) < 1e-9
        assert abs(rev_a.ppa_index - rev_b.ppa_index) < 1e-9
        assert abs(rev_a.ppa_production_share - rev_b.ppa_production_share) < 1e-9
        assert abs(rev_a.balancing_cost_pv - rev_b.balancing_cost_pv) < 1e-9
        assert rev_a.ppa_indexation_start_policy == rev_b.ppa_indexation_start_policy

        import inspect
        from app import input_adapter
        source = inspect.getsource(input_adapter._resolve_user_inputs)
        assert "if project_code" not in source


# ---------------------------------------------------------------------------
# Helper: minimal valid Oborovo snapshot
# ---------------------------------------------------------------------------

def _oborovo_snapshot_base(factory_proj) -> dict:
    """Build a minimal snapshot that satisfies REQUIRED_USER_PROJECT_SNAPSHOT_FIELDS."""
    from app.input_adapter import REQUIRED_USER_PROJECT_SNAPSHOT_FIELDS
    rev = factory_proj.revenue
    fin = factory_proj.financing
    tech = factory_proj.technical
    info = factory_proj.info
    opex_y1 = sum(getattr(item, "y1_amount_keur", 0.0) for item in factory_proj.opex)
    total_capex = getattr(factory_proj.capex, "total_capex", None)
    if total_capex is None:
        # fall back to a plausible value
        total_capex = 50_000.0

    return {
        "project_name": info.name or "Oborovo Test",
        "project_type": "Solar",
        "country_market": "HR",
        "capacity_mw": str(tech.capacity_mw),
        "cod_date": str(info.cod_date),
        "construction_months": str(info.construction_months),
        "horizon_years": str(info.horizon_years),
        "tariff_eur_mwh": str(rev.ppa_base_tariff),
        "ppa_term_years": str(int(rev.ppa_term_years)),
        "p50_hours": str(tech.operating_hours_p50),
        "opex_y1_keur": str(opex_y1),
        "total_capex_keur": str(float(total_capex)),
        "gearing_pct": str(fin.gearing_ratio * 100),
        "interest_rate_pct": str(fin.base_rate + fin.margin_bps / 10_000),
        "tenor_years": str(fin.senior_tenor_years),
        "target_dscr": str(fin.target_dscr),
        "template_source": "oborovo",
    }


# ---------------------------------------------------------------------------
# C2B3 — Blocker 1: Percentage unit contract boundary tests
# ---------------------------------------------------------------------------

class TestPercentageUnitContract:
    """UI % → engine fraction conversion happens exactly once in adapter."""

    def _resolve(self, snap_overrides):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs
        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        snap.update(snap_overrides)
        return _resolve_user_inputs(base_inputs=base, **_snapshot_to_dict(snap))

    def test_ppa_index_zero_percent(self):
        proj = self._resolve({"rev_ppa_index": "0.0"})
        assert abs(proj.revenue.ppa_index - 0.0) < 1e-12

    def test_ppa_index_two_percent(self):
        proj = self._resolve({"rev_ppa_index": "2.0"})
        assert abs(proj.revenue.ppa_index - 0.02) < 1e-9

    def test_ppa_index_two_point_five_percent(self):
        proj = self._resolve({"rev_ppa_index": "2.5"})
        assert abs(proj.revenue.ppa_index - 0.025) < 1e-9

    def test_ppa_index_100_percent(self):
        proj = self._resolve({"rev_ppa_index": "100.0"})
        assert abs(proj.revenue.ppa_index - 1.0) < 1e-9

    def test_ppa_index_no_double_division(self):
        """2.0 UI % must yield 0.02, not 0.0002 (double-divided)."""
        proj = self._resolve({"rev_ppa_index": "2.0"})
        assert proj.revenue.ppa_index > 0.019
        assert proj.revenue.ppa_index < 0.021

    def test_ppa_production_share_50_percent(self):
        proj = self._resolve({"rev_ppa_production_share": "50.0"})
        assert abs(proj.revenue.ppa_production_share - 0.50) < 1e-9

    def test_ppa_production_share_100_percent(self):
        proj = self._resolve({"rev_ppa_production_share": "100.0"})
        assert abs(proj.revenue.ppa_production_share - 1.0) < 1e-9

    def test_ppa_production_share_zero_percent(self):
        proj = self._resolve({"rev_ppa_production_share": "0.0"})
        assert abs(proj.revenue.ppa_production_share - 0.0) < 1e-12

    def test_merchant_balancing_already_divides_by_100(self):
        """Confirm merchant balancing pct also converts correctly (regression guard)."""
        proj = self._resolve({"rev_merchant_balancing_pct": "2.5"})
        assert abs(proj.revenue.balancing_cost_pv - 0.025) < 1e-9


# ---------------------------------------------------------------------------
# C2B3 — Blocker 2: Indexation start date field
# ---------------------------------------------------------------------------

class TestIndexationStartDate:
    """rev_ppa_indexation_start_date wires through adapter as date object."""

    def _resolve(self, snap_overrides):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs
        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        snap.update(snap_overrides)
        return _resolve_user_inputs(base_inputs=base, **_snapshot_to_dict(snap))

    def test_iso_date_string_parsed(self):
        from datetime import date
        proj = self._resolve({"rev_ppa_indexation_start_date": "2031-01-01"})
        assert proj.revenue.ppa_indexation_start_date == date(2031, 1, 1)

    def test_absent_date_is_none(self):
        proj = self._resolve({})
        # Factory default is None (no indexation start date in factory)
        assert proj.revenue.ppa_indexation_start_date is None

    def test_empty_string_yields_none(self):
        proj = self._resolve({"rev_ppa_indexation_start_date": ""})
        assert proj.revenue.ppa_indexation_start_date is None

    def test_invalid_date_raises(self):
        import pytest
        from app.input_adapter import _set_revenue_ppa_indexation_start_date
        from app.project_factories import create_default_oborovo
        base = create_default_oborovo()
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            _set_revenue_ppa_indexation_start_date(base, "not-a-date")


# ---------------------------------------------------------------------------
# C2B3 — Blocker 3: Merchant curve validation matrix
# ---------------------------------------------------------------------------

class TestMerchantCurveValidation:
    """validate_merchant_curve_json rejects all specified invalid inputs."""

    def _validate(self, json_str):
        from app.input_adapter import validate_merchant_curve_json
        return validate_merchant_curve_json(json_str)

    def test_valid_curve_returns_sorted_list(self):
        import json
        curve = [{"year": 2050, "price_eur_mwh": 88.0}, {"year": 2051, "price_eur_mwh": 90.0}]
        result = self._validate(json.dumps(curve))
        assert result[0]["year"] == 2050
        assert result[1]["year"] == 2051

    def test_malformed_json_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Invalid JSON"):
            self._validate("{not json}")

    def test_empty_array_raises(self):
        import pytest
        with pytest.raises(ValueError, match="empty"):
            self._validate("[]")

    def test_non_array_raises(self):
        import pytest
        with pytest.raises(ValueError, match="array"):
            self._validate('{"year": 2050, "price_eur_mwh": 88.0}')

    def test_duplicate_years_raises(self):
        import json, pytest
        curve = [{"year": 2050, "price_eur_mwh": 88.0}, {"year": 2050, "price_eur_mwh": 90.0}]
        with pytest.raises(ValueError, match="duplicate"):
            self._validate(json.dumps(curve))

    def test_non_integer_year_raises(self):
        import json, pytest
        curve = [{"year": "twenty-fifty", "price_eur_mwh": 88.0}]
        with pytest.raises(ValueError, match="integer"):
            self._validate(json.dumps(curve))

    def test_gap_in_years_raises(self):
        import json, pytest
        curve = [{"year": 2042, "price_eur_mwh": 75.0}, {"year": 2044, "price_eur_mwh": 76.0}]
        with pytest.raises(ValueError, match="contiguous"):
            self._validate(json.dumps(curve))

    def test_negative_price_raises(self):
        import json, pytest
        curve = [{"year": 2050, "price_eur_mwh": -1.0}]
        with pytest.raises(ValueError, match="non-negative"):
            self._validate(json.dumps(curve))

    def test_nan_price_raises(self):
        import json, pytest
        import math
        with pytest.raises((ValueError, Exception)):
            self._validate('[{"year": 2050, "price_eur_mwh": NaN}]')

    def test_missing_year_field_raises(self):
        import json, pytest
        curve = [{"price_eur_mwh": 88.0}]
        with pytest.raises(ValueError, match="year"):
            self._validate(json.dumps(curve))

    def test_missing_price_field_raises(self):
        import json, pytest
        curve = [{"year": 2050}]
        with pytest.raises(ValueError, match="price"):
            self._validate(json.dumps(curve))

    def test_unsorted_input_is_accepted_and_sorted(self):
        import json
        curve = [{"year": 2052, "price_eur_mwh": 90.0}, {"year": 2051, "price_eur_mwh": 88.0}]
        result = self._validate(json.dumps(curve))
        assert result[0]["year"] == 2051
        assert result[1]["year"] == 2052


# ---------------------------------------------------------------------------
# C2B3 — Blocker 1: Percentage unit contract boundary tests
# ---------------------------------------------------------------------------

class TestPercentageUnitContract:
    """UI % → engine fraction conversion happens exactly once in adapter."""

    def _resolve(self, snap_overrides):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs
        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        snap.update(snap_overrides)
        return _resolve_user_inputs(base_inputs=base, **_snapshot_to_dict(snap))

    def test_ppa_index_zero_percent(self):
        proj = self._resolve({"rev_ppa_index": "0.0"})
        assert abs(proj.revenue.ppa_index - 0.0) < 1e-12

    def test_ppa_index_two_percent(self):
        proj = self._resolve({"rev_ppa_index": "2.0"})
        assert abs(proj.revenue.ppa_index - 0.02) < 1e-9

    def test_ppa_index_two_point_five_percent(self):
        proj = self._resolve({"rev_ppa_index": "2.5"})
        assert abs(proj.revenue.ppa_index - 0.025) < 1e-9

    def test_ppa_index_100_percent(self):
        proj = self._resolve({"rev_ppa_index": "100.0"})
        assert abs(proj.revenue.ppa_index - 1.0) < 1e-9

    def test_ppa_index_no_double_division(self):
        """2.0 UI % must yield 0.02, not 0.0002 (double-divided)."""
        proj = self._resolve({"rev_ppa_index": "2.0"})
        assert proj.revenue.ppa_index > 0.019
        assert proj.revenue.ppa_index < 0.021

    def test_ppa_production_share_50_percent(self):
        proj = self._resolve({"rev_ppa_production_share": "50.0"})
        assert abs(proj.revenue.ppa_production_share - 0.50) < 1e-9

    def test_ppa_production_share_100_percent(self):
        proj = self._resolve({"rev_ppa_production_share": "100.0"})
        assert abs(proj.revenue.ppa_production_share - 1.0) < 1e-9

    def test_ppa_production_share_zero_percent(self):
        proj = self._resolve({"rev_ppa_production_share": "0.0"})
        assert abs(proj.revenue.ppa_production_share - 0.0) < 1e-12

    def test_merchant_balancing_already_divides_by_100(self):
        """Confirm merchant balancing pct also converts correctly (regression guard)."""
        proj = self._resolve({"rev_merchant_balancing_pct": "2.5"})
        assert abs(proj.revenue.balancing_cost_pv - 0.025) < 1e-9


# ---------------------------------------------------------------------------
# C2B3 — Blocker 2: Indexation start date field
# ---------------------------------------------------------------------------

class TestIndexationStartDate:
    """rev_ppa_indexation_start_date wires through adapter as date object."""

    def _resolve(self, snap_overrides):
        from app.project_factories import create_default_oborovo
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs
        base = create_default_oborovo()
        snap = _oborovo_snapshot_base(base)
        snap.update(snap_overrides)
        return _resolve_user_inputs(base_inputs=base, **_snapshot_to_dict(snap))

    def test_iso_date_string_parsed(self):
        from datetime import date
        proj = self._resolve({"rev_ppa_indexation_start_date": "2031-01-01"})
        assert proj.revenue.ppa_indexation_start_date == date(2031, 1, 1)

    def test_absent_date_is_none(self):
        proj = self._resolve({})
        assert proj.revenue.ppa_indexation_start_date is None

    def test_empty_string_yields_none(self):
        proj = self._resolve({"rev_ppa_indexation_start_date": ""})
        assert proj.revenue.ppa_indexation_start_date is None

    def test_invalid_date_raises(self):
        import pytest
        from app.input_adapter import _set_revenue_ppa_indexation_start_date
        from app.project_factories import create_default_oborovo
        base = create_default_oborovo()
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            _set_revenue_ppa_indexation_start_date(base, "not-a-date")


# ---------------------------------------------------------------------------
# C2B3 — Blocker 3: Merchant curve validation matrix
# ---------------------------------------------------------------------------

class TestMerchantCurveValidation:
    """validate_merchant_curve_json rejects all specified invalid inputs."""

    def _validate(self, json_str):
        from app.input_adapter import validate_merchant_curve_json
        return validate_merchant_curve_json(json_str)

    def test_valid_curve_returns_sorted_list(self):
        import json
        curve = [{"year": 2050, "price_eur_mwh": 88.0}, {"year": 2051, "price_eur_mwh": 90.0}]
        result = self._validate(json.dumps(curve))
        assert result[0]["year"] == 2050
        assert result[1]["year"] == 2051

    def test_malformed_json_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Invalid JSON"):
            self._validate("{not json}")

    def test_empty_array_raises(self):
        import pytest
        with pytest.raises(ValueError, match="empty"):
            self._validate("[]")

    def test_non_array_raises(self):
        import pytest
        with pytest.raises(ValueError, match="array"):
            self._validate('{"year": 2050, "price_eur_mwh": 88.0}')

    def test_duplicate_years_raises(self):
        import json, pytest
        curve = [{"year": 2050, "price_eur_mwh": 88.0}, {"year": 2050, "price_eur_mwh": 90.0}]
        with pytest.raises(ValueError, match="duplicate"):
            self._validate(json.dumps(curve))

    def test_non_integer_year_raises(self):
        import json, pytest
        curve = [{"year": "twenty-fifty", "price_eur_mwh": 88.0}]
        with pytest.raises(ValueError, match="integer"):
            self._validate(json.dumps(curve))

    def test_gap_in_years_raises(self):
        import json, pytest
        curve = [{"year": 2042, "price_eur_mwh": 75.0}, {"year": 2044, "price_eur_mwh": 76.0}]
        with pytest.raises(ValueError, match="contiguous"):
            self._validate(json.dumps(curve))

    def test_negative_price_raises(self):
        import json, pytest
        curve = [{"year": 2050, "price_eur_mwh": -1.0}]
        with pytest.raises(ValueError, match="non-negative"):
            self._validate(json.dumps(curve))

    def test_nan_price_raises(self):
        import pytest
        with pytest.raises((ValueError, Exception)):
            self._validate('[{"year": 2050, "price_eur_mwh": NaN}]')

    def test_missing_year_field_raises(self):
        import json, pytest
        curve = [{"price_eur_mwh": 88.0}]
        with pytest.raises(ValueError, match="year"):
            self._validate(json.dumps(curve))

    def test_missing_price_field_raises(self):
        import json, pytest
        curve = [{"year": 2050}]
        with pytest.raises(ValueError, match="price"):
            self._validate(json.dumps(curve))

    def test_unsorted_input_is_accepted_and_sorted(self):
        import json
        curve = [{"year": 2052, "price_eur_mwh": 90.0}, {"year": 2051, "price_eur_mwh": 88.0}]
        result = self._validate(json.dumps(curve))
        assert result[0]["year"] == 2051
        assert result[1]["year"] == 2052

    def test_float_year_with_fraction_raises(self):
        """2042.5 must be rejected — fractional years silently truncated to 2042 before."""
        import json, pytest
        curve = [{"year": 2042.5, "price_eur_mwh": 75.0}]
        with pytest.raises(ValueError, match="whole-number"):
            self._validate(json.dumps(curve))

    def test_float_year_whole_number_accepted(self):
        """2042.0 is an acceptable representation of 2042."""
        import json
        curve = [{"year": 2042.0, "price_eur_mwh": 75.0}]
        result = self._validate(json.dumps(curve))
        assert result[0]["year"] == 2042

    def test_boolean_year_raises(self):
        """true/false as year must be rejected (JSON booleans are ints in Python)."""
        import json, pytest
        curve = [{"year": True, "price_eur_mwh": 75.0}]
        with pytest.raises(ValueError):
            self._validate(json.dumps(curve))
