"""PR-B focused unit tests — data authority and output surface contracts.

Sections
--------
A. Revenue derivation key contract — verifies exact persisted keys and types
B. Revenue zero-vs-missing semantics
C. Balance-check server-side classification
D. Revenue authority independence from Debt schedule
E. annotate_balance_check_row unit tests
"""
from __future__ import annotations

from unittest.mock import MagicMock
import pytest


# ── A. Revenue derivation key contract ─────────────────────────────────────── #

class TestRevenueDerivatonKeyContract:
    """Exact persisted revenue_derivation keys produced by _format_revenue_derivation."""

    EXPECTED_KEYS = {
        "display_value_keur",
        "summary_method",
        "period_formula",
        "period_count",
        "sample_period_label",
        "sample_generation_mwh",
        "sample_revenue_keur",
        "audit_source",
    }

    def _make_raw(self, **overrides):
        base = {
            "display_value_keur": 5000.0,
            "summary_method": "ppa_tariff",
            "period_formula": "annual",
            "period_count": 25,
            "sample_period_label": "2029-01",
            "sample_generation_mwh": 1000.0,
            "sample_revenue_keur": 55.0,
            "audit_source": "engine v1",
        }
        base.update(overrides)
        return base

    def test_all_expected_keys_present(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation(self._make_raw())
        assert set(result.keys()) == self.EXPECTED_KEYS

    def test_display_value_keur_is_string(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation(self._make_raw())
        assert isinstance(result["display_value_keur"], str)

    def test_sample_revenue_keur_is_string(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation(self._make_raw())
        assert isinstance(result["sample_revenue_keur"], str)

    def test_sample_generation_mwh_is_string(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation(self._make_raw())
        assert isinstance(result["sample_generation_mwh"], str)

    def test_display_value_keur_format(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation(self._make_raw(display_value_keur=5000.0))
        assert result["display_value_keur"] == "5,000 kEUR"

    def test_sample_generation_mwh_format(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation(self._make_raw(sample_generation_mwh=1000.0))
        assert "1,000 MWh" in result["sample_generation_mwh"]

    def test_empty_raw_returns_empty_dict(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        assert _format_revenue_derivation({}) == {}

    def test_none_raw_returns_empty_dict(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        assert _format_revenue_derivation(None) == {}


# ── B. Revenue zero-vs-missing semantics ───────────────────────────────────── #

class TestRevenueDerivatonZeroVsMissing:
    """0 → pre-formatted "0 kEUR"; None → "NOT_AVAILABLE"; missing → "NOT_AVAILABLE"."""

    def test_zero_display_value_renders_not_as_not_available(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation({"display_value_keur": 0})
        assert result["display_value_keur"] == "0 kEUR"
        assert result["display_value_keur"] != "NOT_AVAILABLE"

    def test_none_display_value_renders_as_not_available(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation({"display_value_keur": None})
        assert result["display_value_keur"] == "NOT_AVAILABLE"

    def test_missing_display_value_renders_as_not_available(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation({"summary_method": "x"})
        assert result["display_value_keur"] == "NOT_AVAILABLE"

    def test_zero_sample_revenue_renders_not_as_not_available(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation({"sample_revenue_keur": 0})
        assert result["sample_revenue_keur"] == "0 kEUR"
        assert result["sample_revenue_keur"] != "NOT_AVAILABLE"

    def test_none_sample_revenue_renders_as_not_available(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation({"sample_revenue_keur": None})
        assert result["sample_revenue_keur"] == "NOT_AVAILABLE"

    def test_zero_generation_renders_not_as_not_available(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation({"sample_generation_mwh": 0})
        assert "0 MWh" in result["sample_generation_mwh"]
        assert result["sample_generation_mwh"] != "NOT_AVAILABLE"

    def test_none_generation_renders_as_not_available(self):
        from app.ui.runtime_summary import _format_revenue_derivation
        result = _format_revenue_derivation({"sample_generation_mwh": None})
        assert result["sample_generation_mwh"] == "NOT_AVAILABLE"


# ── C. Balance-check server-side classification ────────────────────────────── #

class TestAnnotateBalanceCheckRow:
    """annotate_balance_check_row classifies server-side; no Jinja threshold needed."""

    def test_none_input_returns_none(self):
        from app.workbook.runtime_projection import annotate_balance_check_row
        assert annotate_balance_check_row(None) is None

    def test_non_balance_rows_unchanged(self):
        from app.workbook.runtime_projection import annotate_balance_check_row
        rows = [{"key": "revenues_keur", "label": "Revenues", "values": [100, 200]}]
        result = annotate_balance_check_row(rows)
        assert result == rows

    def test_balanced_within_threshold_is_ok(self):
        from app.workbook.runtime_projection import annotate_balance_check_row
        rows = [{"key": "balance_check_keur", "label": "Balance Check", "values": [0.0, 0.5, -0.3]}]
        result = annotate_balance_check_row(rows)
        bc = result[0]
        assert bc["balance_check_ok"] is True
        assert bc["css_class"] == "v2-bs-balance-check-ok"
        assert "Balanced" in bc["status_title"]

    def test_exceeds_threshold_is_warn(self):
        from app.workbook.runtime_projection import annotate_balance_check_row
        rows = [{"key": "balance_check_keur", "label": "Balance Check", "values": [0.0, 5.0]}]
        result = annotate_balance_check_row(rows)
        bc = result[0]
        assert bc["balance_check_ok"] is False
        assert bc["css_class"] == "v2-bs-balance-check-warn"
        assert "does not balance" in bc["status_title"]

    def test_exactly_at_boundary_is_ok(self):
        from app.workbook.runtime_projection import annotate_balance_check_row
        rows = [{"key": "balance_check_keur", "label": "Balance Check", "values": [1.0, -1.0]}]
        result = annotate_balance_check_row(rows)
        assert result[0]["balance_check_ok"] is True

    def test_none_values_treated_as_zero(self):
        from app.workbook.runtime_projection import annotate_balance_check_row
        rows = [{"key": "balance_check_keur", "label": "Balance Check", "values": [None, None]}]
        result = annotate_balance_check_row(rows)
        assert result[0]["balance_check_ok"] is True

    def test_empty_rows_returns_empty_list(self):
        from app.workbook.runtime_projection import annotate_balance_check_row
        assert annotate_balance_check_row([]) == []

    def test_original_fields_preserved(self):
        from app.workbook.runtime_projection import annotate_balance_check_row
        rows = [{"key": "balance_check_keur", "label": "Balance Check",
                 "values": [0.1], "is_total": False, "is_stock": True}]
        result = annotate_balance_check_row(rows)
        bc = result[0]
        assert bc["label"] == "Balance Check"
        assert bc["values"] == [0.1]
        assert bc["is_stock"] is True


# ── D. Revenue authority independence from Debt schedule ───────────────────── #

class TestRevenueIndependentOfDebt:
    """Revenue state is CLEAN/STALE even when the Debt schedule is UNAVAILABLE."""

    def _make_rr(self, has_revenue_derivation: bool):
        """Create a minimal RuntimeResult mock."""
        rr = MagicMock()
        rs = {
            "revenue_derivation": {
                "display_value_keur": 5000.0,
                "summary_method": "ppa_tariff",
                "period_formula": "annual",
                "period_count": 25,
                "sample_period_label": "2029-01",
                "sample_generation_mwh": 1000.0,
                "sample_revenue_keur": 55.0,
                "audit_source": "engine v1",
            } if has_revenue_derivation else {},
        }
        rr.runtime_summary = rs
        # Debt schedule absent (UNAVAILABLE for debt)
        rr.debt_schedule = None
        rr.tax_schedule = None
        rr.financial_statements = {"pnl": {"periods": []}, "balance_sheet": {"periods": []}, "pf_cash_waterfall": {"periods": []}}
        return rr

    def test_revenue_clean_when_debt_unavailable(self):
        """Revenue is CLEAN even if debt_schedule is None (UNAVAILABLE for debt)."""
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        rr = self._make_rr(has_revenue_derivation=True)
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)

        # Debt must be UNAVAILABLE
        assert bundle.debt.meta.state.value == "UNAVAILABLE"

        # FS meta: has_runtime=True, has_payload=True (fs payload present)
        assert bundle.fs.meta.has_runtime is True
        assert bundle.fs.meta.is_dirty is False

        # Revenue classification uses fs.meta + revenue_derivation
        from app.workbook.runtime_projection import classify_runtime_state, thaw_runtime_payload
        rs = bundle.fs.runtime_summary
        assert rs is not None
        revenue_derivation = rs.get("revenue_derivation")
        assert revenue_derivation  # non-empty
        meta = bundle.fs.meta
        sentinel = object() if meta.has_runtime else None
        state = classify_runtime_state(sentinel, revenue_derivation, meta.is_dirty)
        assert state.value == "CLEAN"

    def test_revenue_stale_when_debt_unavailable_and_dirty(self):
        """Revenue is STALE (dirty) even if debt_schedule is None."""
        from app.workbook.runtime_projection import build_runtime_projection_bundle, classify_runtime_state
        rr = self._make_rr(has_revenue_derivation=True)
        bundle = build_runtime_projection_bundle(rr, is_dirty=True)

        assert bundle.debt.meta.state.value == "UNAVAILABLE"
        rs = bundle.fs.runtime_summary
        revenue_derivation = rs.get("revenue_derivation")
        meta = bundle.fs.meta
        sentinel = object() if meta.has_runtime else None
        state = classify_runtime_state(sentinel, revenue_derivation, meta.is_dirty)
        assert state.value == "STALE"

    def test_revenue_unavailable_when_derivation_absent(self):
        """Revenue is UNAVAILABLE when revenue_derivation is empty dict."""
        from app.workbook.runtime_projection import build_runtime_projection_bundle, classify_runtime_state
        rr = self._make_rr(has_revenue_derivation=False)
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)

        rs = bundle.fs.runtime_summary
        revenue_derivation = rs.get("revenue_derivation")
        meta = bundle.fs.meta
        sentinel = object() if meta.has_runtime else None
        state = classify_runtime_state(sentinel, revenue_derivation, meta.is_dirty)
        # Empty dict is falsy → UNAVAILABLE
        assert state.value == "UNAVAILABLE"

    def test_revenue_fs_and_debt_share_same_runtime_summary(self):
        """projection.fs.runtime_summary is the same object as projection.debt.runtime_summary."""
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        rr = self._make_rr(has_revenue_derivation=True)
        bundle = build_runtime_projection_bundle(rr, is_dirty=False)
        # Same object: both projections reference the single thawed dict
        assert bundle.fs.runtime_summary is bundle.debt.runtime_summary


# ── E. Jinja template does not perform financial calculations ──────────────── #

class TestJinjaNoFinancialCalculation:
    """Templates must not sum, compare, threshold, or annualise financial values."""

    TEMPLATES_UNDER_TEST = [
        "app/templates/v2/partials/sheet_revenue.html",
        "app/templates/v2/partials/sheet_financial_statements.html",
        "app/templates/v2/partials/sheet_senior_debt.html",
        "app/templates/v2/partials/sheet_tax.html",
    ]

    FORBIDDEN_PATTERNS = [
        # Numeric comparison on financial values
        "> 1.0",
        "< -1.0",
        "| sum",
        "| float",
        # Template-side annualisation
        "/ 12",
        "* 12",
        "/ periods",
    ]

    def _read_template(self, path: str) -> str:
        from pathlib import Path
        repo_root = Path(__file__).resolve().parent.parent
        return (repo_root / path).read_text()

    @pytest.mark.parametrize("template_path", TEMPLATES_UNDER_TEST)
    def test_no_financial_threshold_comparison(self, template_path):
        content = self._read_template(template_path)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in content, (
                f"{template_path} contains forbidden pattern {pattern!r} "
                "(financial calculation in Jinja is not permitted)"
            )
