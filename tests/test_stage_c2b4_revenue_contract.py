"""Stage C2B4: Revenue input contract closeout tests.

Covers:
- CONTRACT_ANNIVERSARY cross-field validation (policy + date)
- AFTER_FIRST_FULL_OPERATING_YEAR in registry options
- materialize_revenue_snapshot_defaults helper
- Strict scalar validation (bad canonical values must not silently fall back)
- Working-copy materialization (new, old, partial, user-override)
"""
from __future__ import annotations
import json
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _oborovo_base():
    from app.project_factories import create_default_oborovo
    return create_default_oborovo()


def _resolve(snap_overrides, base=None):
    from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs
    if base is None:
        base = _oborovo_base()
    snap = _minimal_snap(base)
    snap.update(snap_overrides)
    return _resolve_user_inputs(base_inputs=base, **_snapshot_to_dict(snap))


def _minimal_snap(proj) -> dict:
    rev = proj.revenue
    fin = proj.financing
    tech = proj.technical
    info = proj.info
    opex_y1 = sum(getattr(item, "y1_amount_keur", 0.0) for item in proj.opex)
    total_capex = getattr(proj.capex, "total_capex", None) or 50_000.0
    return {
        "project_name": info.name or "Test",
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
# 1. CONTRACT_ANNIVERSARY cross-field validation
# ---------------------------------------------------------------------------

class TestContractAnniversaryValidation:
    """CONTRACT_ANNIVERSARY requires ppa_indexation_start_date."""

    def test_contract_anniversary_without_date_raises(self):
        from app.revenue_input_validation import RevenueInputError
        with pytest.raises(RevenueInputError, match="CONTRACT_ANNIVERSARY"):
            _resolve({"rev_ppa_indexation_start_policy": "CONTRACT_ANNIVERSARY"})

    def test_contract_anniversary_with_date_succeeds(self):
        proj = _resolve({
            "rev_ppa_indexation_start_policy": "CONTRACT_ANNIVERSARY",
            "rev_ppa_indexation_start_date": "2031-01-01",
        })
        assert proj.revenue.ppa_indexation_start_policy == "CONTRACT_ANNIVERSARY"

    def test_first_full_cy_without_date_succeeds(self):
        """FIRST_FULL_CALENDAR_YEAR_AS_BASE never requires a date."""
        proj = _resolve({"rev_ppa_indexation_start_policy": "FIRST_FULL_CALENDAR_YEAR_AS_BASE"})
        assert proj.revenue.ppa_indexation_start_policy == "FIRST_FULL_CALENDAR_YEAR_AS_BASE"

    def test_after_first_full_without_date_succeeds(self):
        """AFTER_FIRST_FULL_OPERATING_YEAR does not require an explicit date."""
        proj = _resolve({"rev_ppa_indexation_start_policy": "AFTER_FIRST_FULL_OPERATING_YEAR"})
        assert proj.revenue.ppa_indexation_start_policy == "AFTER_FIRST_FULL_OPERATING_YEAR"

    def test_validate_revenue_ppa_cross_field_function(self):
        from app.revenue_input_validation import (
            validate_revenue_ppa_cross_field, RevenueInputError
        )
        # Passes when date provided
        validate_revenue_ppa_cross_field(
            ppa_indexation_start_policy="CONTRACT_ANNIVERSARY",
            ppa_indexation_start_date="2031-01-01",
        )
        # Raises when date missing
        with pytest.raises(RevenueInputError, match="CONTRACT_ANNIVERSARY"):
            validate_revenue_ppa_cross_field(
                ppa_indexation_start_policy="CONTRACT_ANNIVERSARY",
                ppa_indexation_start_date=None,
            )
        # No error for other policies without date
        validate_revenue_ppa_cross_field(
            ppa_indexation_start_policy="FIRST_FULL_CALENDAR_YEAR_AS_BASE",
            ppa_indexation_start_date=None,
        )


# ---------------------------------------------------------------------------
# 2. AFTER_FIRST_FULL_OPERATING_YEAR in registry
# ---------------------------------------------------------------------------

class TestRegistryIndexationPolicyOptions:
    def test_after_first_full_in_registry_options(self):
        from app.workbook.registry import WORKBOOK
        field = WORKBOOK.field("revenue.ppa.indexation_policy")
        assert "AFTER_FIRST_FULL_OPERATING_YEAR" in field.options

    def test_all_three_policies_in_registry(self):
        from app.workbook.registry import WORKBOOK
        field = WORKBOOK.field("revenue.ppa.indexation_policy")
        assert "FIRST_FULL_CALENDAR_YEAR_AS_BASE" in field.options
        assert "CONTRACT_ANNIVERSARY" in field.options
        assert "AFTER_FIRST_FULL_OPERATING_YEAR" in field.options


# ---------------------------------------------------------------------------
# 3. materialize_revenue_snapshot_defaults helper
# ---------------------------------------------------------------------------

class TestMaterializeRevenueSnapshotDefaults:

    def test_ppa_index_in_ui_percent(self):
        from app.revenue_snapshot_utils import materialize_revenue_snapshot_defaults
        base = _oborovo_base()
        result = materialize_revenue_snapshot_defaults(base.revenue)
        # Engine has 0.02; snapshot must have "2.0" (UI %)
        idx_str = result["rev_ppa_index"]
        assert abs(float(idx_str) - 2.0) < 0.001

    def test_production_share_in_ui_percent(self):
        from app.revenue_snapshot_utils import materialize_revenue_snapshot_defaults
        base = _oborovo_base()
        result = materialize_revenue_snapshot_defaults(base.revenue)
        share_str = result["rev_ppa_production_share"]
        assert abs(float(share_str) - 100.0) < 0.001

    def test_balancing_pct_in_ui_percent(self):
        from app.revenue_snapshot_utils import materialize_revenue_snapshot_defaults
        base = _oborovo_base()
        result = materialize_revenue_snapshot_defaults(base.revenue)
        pct_str = result["rev_merchant_balancing_pct"]
        assert abs(float(pct_str) - 2.5) < 0.001

    def test_merchant_curve_is_valid_json(self):
        from app.revenue_snapshot_utils import materialize_revenue_snapshot_defaults
        from app.input_adapter import validate_merchant_curve_json
        base = _oborovo_base()
        result = materialize_revenue_snapshot_defaults(base.revenue)
        curve_json = result["rev_merchant_price_curve_json"]
        items = validate_merchant_curve_json(curve_json)
        assert len(items) == 19  # CY2042–CY2060
        assert items[0]["year"] == 2042

    def test_no_hardcoded_prices_in_save_as(self):
        """project_save_as_service must not contain hardcoded merchant curve prices."""
        import inspect
        from app.services import project_save_as_service
        source = inspect.getsource(project_save_as_service)
        assert "75.12095149999999" not in source, (
            "Hardcoded merchant curve price found in project_save_as_service. "
            "Use materialize_revenue_snapshot_defaults instead."
        )

    def test_round_trip_no_double_division(self):
        """materialize -> snapshot -> resolve must not double-divide ppa_index."""
        from app.revenue_snapshot_utils import materialize_revenue_snapshot_defaults
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs
        base = _oborovo_base()
        snap = _minimal_snap(base)
        snap.update(materialize_revenue_snapshot_defaults(base.revenue))
        proj = _resolve_user_inputs(base_inputs=base, **_snapshot_to_dict(snap))
        # Factory has ppa_index=0.02; after round-trip must still be 0.02
        assert abs(proj.revenue.ppa_index - 0.02) < 1e-9


# ---------------------------------------------------------------------------
# 4. Strict scalar validation
# ---------------------------------------------------------------------------

class TestStrictCanonicalScalarValidation:
    """Non-empty invalid canonical values must not silently fall back to None."""

    def _snapshot_to_dict(self, snap):
        from app.input_adapter import _snapshot_to_dict
        return _snapshot_to_dict(snap)

    def _base_snap(self):
        return _minimal_snap(_oborovo_base())

    def test_invalid_rev_ppa_index_raises(self):
        from app.input_adapter import _snapshot_to_dict
        from app.input_adapter import SnapshotInputError
        snap = self._base_snap()
        snap["rev_ppa_index"] = "not-a-number"
        with pytest.raises(SnapshotInputError):
            _snapshot_to_dict(snap)

    def test_negative_rev_ppa_index_raises(self):
        from app.input_adapter import _snapshot_to_dict, SnapshotInputError
        snap = self._base_snap()
        snap["rev_ppa_index"] = "-5.0"
        with pytest.raises(SnapshotInputError):
            _snapshot_to_dict(snap)

    def test_over_100_rev_ppa_index_raises(self):
        from app.input_adapter import _snapshot_to_dict, SnapshotInputError
        snap = self._base_snap()
        snap["rev_ppa_index"] = "101.0"
        with pytest.raises(SnapshotInputError):
            _snapshot_to_dict(snap)

    def test_invalid_rev_co2_enabled_raises(self):
        from app.input_adapter import _snapshot_to_dict, SnapshotInputError
        snap = self._base_snap()
        snap["rev_co2_enabled"] = "maybe"
        with pytest.raises(SnapshotInputError):
            _snapshot_to_dict(snap)

    def test_invalid_rev_merchant_balancing_pct_raises(self):
        from app.input_adapter import _snapshot_to_dict, SnapshotInputError
        snap = self._base_snap()
        snap["rev_merchant_balancing_pct"] = "abc"
        with pytest.raises(SnapshotInputError):
            _snapshot_to_dict(snap)

    def test_absent_rev_ppa_index_returns_none(self):
        """Absent key must still return None (inherit factory)."""
        from app.input_adapter import _snapshot_to_dict
        snap = self._base_snap()
        # Ensure key is absent
        snap.pop("rev_ppa_index", None)
        result = _snapshot_to_dict(snap)
        assert result["rev_ppa_index"] is None

    def test_empty_rev_ppa_index_returns_none(self):
        """Empty string must return None (inherit factory), not raise."""
        from app.input_adapter import _snapshot_to_dict
        snap = self._base_snap()
        snap["rev_ppa_index"] = ""
        result = _snapshot_to_dict(snap)
        assert result["rev_ppa_index"] is None


# ---------------------------------------------------------------------------
# 5. Working-copy materialization
# ---------------------------------------------------------------------------

class TestWorkingCopyMaterialization:
    """New, old, partially migrated, user-override scenarios."""

    def test_new_working_copy_all_rev_keys_present(self):
        """save_as seeds all canonical rev_* keys for fresh Oborovo copy."""
        from app.project_factories import create_default_oborovo
        from app.revenue_snapshot_utils import materialize_revenue_snapshot_defaults
        base = create_default_oborovo()
        defaults = materialize_revenue_snapshot_defaults(base.revenue)
        required_keys = [
            "rev_ppa_base_tariff", "rev_ppa_index", "rev_ppa_term_years",
            "rev_ppa_production_share", "rev_ppa_indexation_start_policy",
            "rev_merchant_balancing_pct", "rev_balancing_cost_eur_per_mwh",
            "rev_co2_enabled", "rev_co2_price_eur_mwh", "rev_merchant_price_curve_json",
        ]
        for k in required_keys:
            assert k in defaults, f"Missing key: {k}"

    def test_old_working_copy_without_canonical_keys_gets_defaults(self):
        """Old snapshot without any rev_* keys: simulate and verify defaults materialize."""
        from app.project_factories import create_default_oborovo
        from app.revenue_snapshot_utils import materialize_revenue_snapshot_defaults
        base = create_default_oborovo()
        # Old snapshot - no rev_* keys
        old_snap = {
            "active_project": "obrwc-001",
            "project_origin": "user_created",
            "project_name": "Old Oborovo WC",
            "tariff_eur_mwh": "57.0",
            "ppa_term_years": "12",
        }
        defaults = materialize_revenue_snapshot_defaults(base.revenue)
        for key, val in defaults.items():
            if not old_snap.get(key):
                old_snap[key] = val
        assert "rev_ppa_index" in old_snap
        assert "rev_merchant_price_curve_json" in old_snap

    def test_partial_migration_preserves_existing_user_values(self):
        """A snapshot with some canonical keys already set - only missing ones filled."""
        from app.project_factories import create_default_oborovo
        from app.revenue_snapshot_utils import materialize_revenue_snapshot_defaults
        base = create_default_oborovo()
        partial_snap = {
            "rev_ppa_base_tariff": "60.0",  # user already customized this
        }
        defaults = materialize_revenue_snapshot_defaults(base.revenue)
        for key, val in defaults.items():
            if not partial_snap.get(key):
                partial_snap[key] = val
        # User-entered value preserved
        assert partial_snap["rev_ppa_base_tariff"] == "60.0"
        # Missing keys filled in
        assert "rev_ppa_index" in partial_snap

    def test_user_override_not_overwritten(self):
        """User-entered rev_ppa_index must not be overwritten by save_as defaults."""
        from app.project_factories import create_default_oborovo
        from app.revenue_snapshot_utils import materialize_revenue_snapshot_defaults
        base = create_default_oborovo()
        snap = {"rev_ppa_index": "3.0"}  # user set 3%
        defaults = materialize_revenue_snapshot_defaults(base.revenue)
        for key, val in defaults.items():
            if not snap.get(key):
                snap[key] = val
        assert snap["rev_ppa_index"] == "3.0"

    def test_no_hardcoded_merchant_prices_in_save_as_module(self):
        """Regression: save_as must use helper not hardcoded list."""
        import inspect
        from app.services import project_save_as_service
        source = inspect.getsource(project_save_as_service)
        # The specific hardcoded price from C2B3 that was replaced
        assert "75.12095149999999" not in source


# ---------------------------------------------------------------------------
# 6. Merchant curve year validation
# ---------------------------------------------------------------------------

class TestMerchantCurveYearValidation:
    """validate_merchant_curve_json must reject non-integer years strictly."""

    def _v(self, curve_json: str):
        from app.input_adapter import validate_merchant_curve_json
        return validate_merchant_curve_json(curve_json)

    def test_rejects_float_fractional_year(self):
        """2042.5 must be rejected — not silently truncated to 2042."""
        import json, pytest
        curve = json.dumps([{"year": 2042.5, "price_eur_mwh": 75.0}])
        with pytest.raises(ValueError, match="whole-number"):
            self._v(curve)

    def test_accepts_float_whole_year(self):
        """2042.0 (float) is a whole number and must be accepted."""
        import json
        curve = json.dumps([{"year": 2042.0, "price_eur_mwh": 75.0}])
        result = self._v(curve)
        assert result[0]["year"] == 2042

    def test_rejects_bool_year(self):
        """True/False must never be accepted as years."""
        import json, pytest
        for bad in [True, False]:
            curve = json.dumps([{"year": bad, "price_eur_mwh": 75.0}])
            with pytest.raises(ValueError):
                self._v(curve)

    def test_rejects_string_float_year(self):
        """'2042.5' must be rejected."""
        import json, pytest
        curve = json.dumps([{"year": "2042.5", "price_eur_mwh": 75.0}])
        with pytest.raises(ValueError, match="whole-number"):
            self._v(curve)

    def test_accepts_string_integer_year(self):
        """'2042' as string must be accepted."""
        import json
        curve = json.dumps([{"year": "2042", "price_eur_mwh": 75.0}])
        result = self._v(curve)
        assert result[0]["year"] == 2042

    def test_rejects_empty_string_year(self):
        """Empty string year must raise."""
        import json, pytest
        curve = json.dumps([{"year": "", "price_eur_mwh": 75.0}])
        with pytest.raises(ValueError):
            self._v(curve)

    def test_rejects_negative_price(self):
        import json, pytest
        curve = json.dumps([{"year": 2042, "price_eur_mwh": -1.0}])
        with pytest.raises(ValueError, match="non-negative"):
            self._v(curve)

    def test_rejects_duplicate_years(self):
        import json, pytest
        curve = json.dumps([
            {"year": 2042, "price_eur_mwh": 75.0},
            {"year": 2042, "price_eur_mwh": 80.0},
        ])
        with pytest.raises(ValueError, match="duplicate"):
            self._v(curve)

    def test_rejects_gap_in_years(self):
        import json, pytest
        curve = json.dumps([
            {"year": 2042, "price_eur_mwh": 75.0},
            {"year": 2044, "price_eur_mwh": 80.0},
        ])
        with pytest.raises(ValueError, match="gap"):
            self._v(curve)

    def test_accepts_valid_contiguous_curve(self):
        import json
        curve = json.dumps([
            {"year": 2042, "price_eur_mwh": 75.0},
            {"year": 2043, "price_eur_mwh": 76.0},
            {"year": 2044, "price_eur_mwh": 77.0},
        ])
        result = self._v(curve)
        assert len(result) == 3
        assert result[-1]["year"] == 2044


# ---------------------------------------------------------------------------
# 7. Strict validation for rev_ppa_base_tariff and rev_ppa_term_years
# ---------------------------------------------------------------------------

class TestStrictTariffAndTermValidation:
    """rev_ppa_base_tariff and rev_ppa_term_years must use strict validation."""

    def _base_snap(self):
        return _minimal_snap(_oborovo_base())

    def test_invalid_rev_ppa_base_tariff_raises(self):
        from app.input_adapter import _snapshot_to_dict, SnapshotInputError
        snap = self._base_snap()
        snap["rev_ppa_base_tariff"] = "not-a-number"
        with pytest.raises(SnapshotInputError, match="rev_ppa_base_tariff"):
            _snapshot_to_dict(snap)

    def test_negative_rev_ppa_base_tariff_raises(self):
        from app.input_adapter import _snapshot_to_dict, SnapshotInputError
        snap = self._base_snap()
        snap["rev_ppa_base_tariff"] = "-10.0"
        with pytest.raises(SnapshotInputError):
            _snapshot_to_dict(snap)

    def test_absent_rev_ppa_base_tariff_uses_legacy(self):
        """Absent canonical key falls back to legacy tariff_eur_mwh."""
        from app.input_adapter import _snapshot_to_dict
        snap = self._base_snap()
        snap.pop("rev_ppa_base_tariff", None)
        snap["tariff_eur_mwh"] = "60.0"
        result = _snapshot_to_dict(snap)
        # tariff_eur_mwh is the legacy key; result["tariff_eur_mwh"] should be 60.0
        assert result["tariff_eur_mwh"] == 60.0

    def test_invalid_rev_ppa_term_years_raises(self):
        from app.input_adapter import _snapshot_to_dict, SnapshotInputError
        snap = self._base_snap()
        snap["rev_ppa_term_years"] = "abc"
        with pytest.raises(SnapshotInputError, match="rev_ppa_term_years"):
            _snapshot_to_dict(snap)

    def test_zero_rev_ppa_term_years_raises(self):
        """PPA term must be ≥ 1 year."""
        from app.input_adapter import _snapshot_to_dict, SnapshotInputError
        snap = self._base_snap()
        snap["rev_ppa_term_years"] = "0"
        with pytest.raises(SnapshotInputError):
            _snapshot_to_dict(snap)

    def test_over_50_rev_ppa_term_years_raises(self):
        """PPA term must be ≤ 50 years."""
        from app.input_adapter import _snapshot_to_dict, SnapshotInputError
        snap = self._base_snap()
        snap["rev_ppa_term_years"] = "51"
        with pytest.raises(SnapshotInputError):
            _snapshot_to_dict(snap)

    def test_absent_rev_ppa_term_years_uses_legacy(self):
        from app.input_adapter import _snapshot_to_dict
        snap = self._base_snap()
        snap.pop("rev_ppa_term_years", None)
        snap["ppa_term_years"] = "15"
        result = _snapshot_to_dict(snap)
        assert result["ppa_term_years"] == 15


# ---------------------------------------------------------------------------
# 8. PPA escalation 0% / 2% / 100% roundtrip + over-max rejection
# ---------------------------------------------------------------------------

class TestEscalationBoundsAndRoundtrip:
    """0%, 2%, 100% must save/map correctly; >100% must be rejected."""

    def _roundtrip(self, pct_str: str):
        """Return engine fraction after materialising pct_str as rev_ppa_index."""
        from app.input_adapter import _snapshot_to_dict, _resolve_user_inputs
        base = _oborovo_base()
        snap = _minimal_snap(base)
        snap["rev_ppa_index"] = pct_str
        d = _snapshot_to_dict(snap)
        proj = _resolve_user_inputs(base_inputs=base, **d)
        return proj.revenue.ppa_index

    def test_0_percent_maps_to_0(self):
        assert self._roundtrip("0") == 0.0

    def test_2_percent_maps_to_0_02(self):
        assert abs(self._roundtrip("2.0") - 0.02) < 1e-9

    def test_100_percent_maps_to_1(self):
        assert abs(self._roundtrip("100.0") - 1.0) < 1e-9

    def test_over_100_percent_raises_snapshot_error(self):
        from app.input_adapter import _snapshot_to_dict, SnapshotInputError
        base = _oborovo_base()
        snap = _minimal_snap(base)
        snap["rev_ppa_index"] = "101.0"
        with pytest.raises(SnapshotInputError):
            _snapshot_to_dict(snap)

    def test_registry_has_explicit_bounds_on_ppa_index(self):
        from app.workbook.registry import WORKBOOK
        field = WORKBOOK.field("revenue.ppa.index")
        assert field.min_value == 0, f"Expected min_value=0, got {field.min_value}"
        assert field.max_value == 100, f"Expected max_value=100, got {field.max_value}"


# ---------------------------------------------------------------------------
# 9. Old working copy migration (persist_revenue_backfill)
# ---------------------------------------------------------------------------

class TestOldWorkingCopyPersistence:
    """persist_revenue_backfill must write canonical keys to the draft snapshot."""

    @pytest.fixture
    def old_ws(self, tmp_path):
        """Isolated DB with an old Oborovo working copy using direct sqlite3."""
        import json, sqlite3
        from app.project_factories import create_default_oborovo
        from app.persistence.db import _init_schema

        db_path = str(tmp_path / "test_backfill.db")
        user_id = "test-user"
        project_id = "test-old-oborovo-001"

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        _init_schema(conn)

        base = create_default_oborovo()
        rev = base.revenue
        fin = base.financing
        tech = base.technical
        info = base.info
        opex_y1 = sum(getattr(item, "y1_amount_keur", 0.0) for item in base.opex)
        total_capex = getattr(base.capex, "total_capex", None) or 50_000.0

        old_snap = {
            "project_name": "Old Oborovo WC",
            "project_type": "Wind",
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
        }

        now = "2025-01-01T00:00:00+00:00"
        conn.execute(
            "INSERT OR REPLACE INTO projects "
            "(project_id, user_id, project_code, project_name, project_type, "
            " project_origin, template_source, source_project_template, "
            " governance_state_json, last_run_summary_json, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (project_id, user_id, "old-oborovo-wc", "Old Oborovo WC", "Wind",
             "user_created", "oborovo", "oborovo", "{}", "{}", now, now),
        )
        conn.execute(
            "INSERT OR REPLACE INTO workspace_states "
            "(user_id, project_id, project_code, draft_snapshot_json, saved_snapshot_json, "
            " last_runtime_snapshot_json, last_runtime_summary_json, "
            " governance_state_json, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (user_id, project_id, "old-oborovo-wc",
             json.dumps(old_snap), json.dumps(old_snap),
             "{}", "{}", "{}", now, now),
        )
        conn.commit()
        yield {"conn": conn, "user_id": user_id, "project_id": project_id}
        conn.close()

    def _get_project_record(self, project_id: str):
        class _PR:
            def __init__(self, pid):
                self.project_id = pid
                self.project_origin = "user_created"
                self.template_source = "oborovo"
        return _PR(project_id)

    def test_old_copy_needs_backfill(self, old_ws):
        import json
        from app.services.revenue_backfill import needs_revenue_backfill
        conn = old_ws["conn"]
        project_id = old_ws["project_id"]
        user_id = old_ws["user_id"]
        pr = self._get_project_record(project_id)
        row = conn.execute(
            "SELECT draft_snapshot_json FROM workspace_states WHERE user_id=? AND project_id=?",
            (user_id, project_id),
        ).fetchone()
        snap = json.loads(row["draft_snapshot_json"])
        assert needs_revenue_backfill(pr, snap)

    def test_persist_backfill_writes_canonical_keys(self, old_ws):
        import json
        from app.services.revenue_backfill import (
            persist_revenue_backfill, OBOROVO_CANONICAL_REVENUE_KEYS
        )
        conn = old_ws["conn"]
        project_id = old_ws["project_id"]
        user_id = old_ws["user_id"]
        pr = self._get_project_record(project_id)

        updated = persist_revenue_backfill(project_id, user_id, pr, conn=conn)
        assert updated is True, "Expected backfill to write canonical keys"

        row = conn.execute(
            "SELECT draft_snapshot_json FROM workspace_states WHERE user_id=? AND project_id=?",
            (user_id, project_id),
        ).fetchone()
        snap = json.loads(row["draft_snapshot_json"])
        for key in OBOROVO_CANONICAL_REVENUE_KEYS:
            assert snap.get(key), f"Expected {key} to be present after backfill"

    def test_persist_backfill_idempotent(self, old_ws):
        from app.services.revenue_backfill import persist_revenue_backfill
        conn = old_ws["conn"]
        project_id = old_ws["project_id"]
        user_id = old_ws["user_id"]
        pr = self._get_project_record(project_id)
        persist_revenue_backfill(project_id, user_id, pr, conn=conn)
        result = persist_revenue_backfill(project_id, user_id, pr, conn=conn)
        assert result is False

    def test_persist_backfill_preserves_user_value(self, old_ws):
        import json
        from app.services.revenue_backfill import persist_revenue_backfill
        conn = old_ws["conn"]
        project_id = old_ws["project_id"]
        user_id = old_ws["user_id"]
        pr = self._get_project_record(project_id)
        row = conn.execute(
            "SELECT draft_snapshot_json FROM workspace_states WHERE user_id=? AND project_id=?",
            (user_id, project_id),
        ).fetchone()
        snap = json.loads(row["draft_snapshot_json"])
        snap["rev_ppa_base_tariff"] = "99.0"
        conn.execute(
            "UPDATE workspace_states SET draft_snapshot_json=? WHERE user_id=? AND project_id=?",
            (json.dumps(snap), user_id, project_id),
        )
        conn.commit()
        persist_revenue_backfill(project_id, user_id, pr, conn=conn)
        row = conn.execute(
            "SELECT draft_snapshot_json FROM workspace_states WHERE user_id=? AND project_id=?",
            (user_id, project_id),
        ).fetchone()
        snap = json.loads(row["draft_snapshot_json"])
        assert snap["rev_ppa_base_tariff"] == "99.0"

    def test_factory_template_not_backfilled(self):
        """Protected reference (factory_template) must never be backfilled."""
        from app.services.revenue_backfill import needs_revenue_backfill
        class _FactoryPR:
            project_id = "oborovo-ref"
            project_origin = "factory_template"
            template_source = "oborovo"
        # Even with no canonical keys, factory_template must return False
        assert needs_revenue_backfill(_FactoryPR(), {}) is False
