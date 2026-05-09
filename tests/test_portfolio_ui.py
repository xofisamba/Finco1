"""Tests for Phase 1.5 Portfolio UI (app/portfolio_ui.py).

Tests display/build functions for IndependentPortfolioResult.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.portfolio_ui import (
    build_portfolio_summary_table,
    build_portfolio_spv_table,
    build_portfolio_warnings_table,
    render_portfolio_summary,
    _IRR_LABEL,
)


class TestPortfolioSummaryTable:
    """build_portfolio_summary_table produces correct structure."""

    def _mock_result(self, **kwargs):
        defaults = dict(
            portfolio_name="Test Portfolio",
            num_spvs=3,
            total_revenue_keur=150_000.0,
            total_ebitda_keur=120_000.0,
            total_tax_keur=18_000.0,
            total_senior_ds_keur=80_000.0,
            total_distribution_keur=22_000.0,
            min_dscr=1.15,
            avg_dscr=1.35,
            simple_avg_project_irr=0.085,
            simple_avg_equity_irr=0.11,
            dsrf_enabled=False,
            warnings=("warn1", "warn2"),
            spv_outputs=[],
        )
        defaults.update(kwargs)

        result = MagicMock()
        for k, v in defaults.items():
            setattr(result, k, v)
        result.num_spvs = defaults["num_spvs"]
        return result

    def test_columns(self):
        result = self._mock_result()
        df = build_portfolio_summary_table(result)
        assert list(df.columns) == ["Field", "Value"]
        assert len(df) > 5

    def test_portfolio_name(self):
        result = self._mock_result(portfolio_name="My Portfolio")
        df = build_portfolio_summary_table(result)
        assert any(df["Field"] == "Portfolio Name")
        assert any(df["Value"] == "My Portfolio")

    def test_num_spvs(self):
        result = self._mock_result(num_spvs=3)
        df = build_portfolio_summary_table(result)
        assert any(df["Field"] == "Number of SPVs")
        assert any(df["Value"] == 3)

    def test_min_dscr_format(self):
        result = self._mock_result(min_dscr=1.155)
        df = build_portfolio_summary_table(result)
        row = df[df["Field"] == "Min DSCR (conservative)"]
        assert "1.155" in row["Value"].values[0] or "1.155" in str(row["Value"].values[0])

    def test_dsrf_enabled_shown(self):
        result = self._mock_result(dsrf_enabled=False)
        df = build_portfolio_summary_table(result)
        assert any(df["Field"] == "DSRF Enabled")
        assert any(df["Value"] == False)

    def test_warnings_count(self):
        result = self._mock_result(warnings=("warn1", "warn2"))
        df = build_portfolio_summary_table(result)
        row = df[df["Field"] == "Warnings Count"]
        assert row["Value"].values[0] == 2


class TestPortfolioSPVTable:
    """build_portfolio_spv_table produces per-SPV rows."""

    def _mock_result(self, spv_outputs):
        result = MagicMock()
        result.portfolio_name = "Test"
        result.num_spvs = len(spv_outputs)
        result.spv_outputs = spv_outputs
        return result

    def _mock_spv(self, code, rev=1000, ebitda=800, tax=100,
                  senior_ds=500, dist=200, avg_dscr=1.3, min_dscr=1.15,
                  proj_irr=0.09, eq_irr=0.12):
        o = MagicMock()
        o.project_code = code
        o.project_name = f"Project {code}"
        o.total_revenue_keur = rev
        o.total_ebitda_keur = ebitda
        o.total_tax_keur = tax
        o.total_senior_ds_keur = senior_ds
        o.total_distribution_keur = dist
        o.avg_dscr = avg_dscr
        o.min_dscr = min_dscr
        o.project_irr = proj_irr
        o.equity_irr = eq_irr
        return o

    def test_columns(self):
        result = self._mock_result([self._mock_spv("A")])
        df = build_portfolio_spv_table(result)
        expected = ["SPV Code", "SPV Name", "Revenue (kEUR)", "EBITDA (kEUR)",
                   "Senior DS (kEUR)", "Distributions (kEUR)", "Avg DSCR", "Min DSCR",
                   "Project IRR", "Equity IRR"]
        for col in expected:
            assert col in df.columns, f"Missing column: {col}"

    def test_two_spvs(self):
        spv1 = self._mock_spv("A", rev=1000)
        spv2 = self._mock_spv("B", rev=2000)
        result = self._mock_result([spv1, spv2])
        df = build_portfolio_spv_table(result)
        assert len(df) == 2
        codes = set(df["SPV Code"])
        assert codes == {"A", "B"}

    def test_revenue_sum_matches(self):
        spv1 = self._mock_spv("A", rev=1000)
        spv2 = self._mock_spv("B", rev=2000)
        result = self._mock_result([spv1, spv2])
        df = build_portfolio_spv_table(result)
        total = df["Revenue (kEUR)"].apply(
            lambda x: float(str(x).replace(",", ""))
        ).sum()
        assert total == 3000.0


class TestWarningsTable:
    """build_portfolio_warnings_table handles warnings correctly."""

    def _mock_result(self, warnings):
        result = MagicMock()
        result.warnings = warnings
        return result

    def test_empty_warnings(self):
        result = self._mock_result(warnings=())
        df = build_portfolio_warnings_table(result)
        assert list(df.columns) == ["Warning"]
        assert len(df) == 0

    def test_two_warnings(self):
        result = self._mock_result(warnings=("warn1", "warn2"))
        df = build_portfolio_warnings_table(result)
        assert len(df) == 2
        assert list(df["Warning"]) == ["warn1", "warn2"]


class TestRenderPortfolioSummary:
    """render_portfolio_summary produces readable text."""

    def _mock_result(self, **kwargs):
        defaults = dict(
            portfolio_name="Test", num_spvs=2, total_revenue_keur=100_000,
            total_ebitda_keur=80_000, total_distribution_keur=20_000,
            min_dscr=1.2, avg_dscr=1.4, simple_avg_project_irr=0.09,
            simple_avg_equity_irr=0.11, dsrf_enabled=False, warnings=(),
        )
        defaults.update(kwargs)
        result = MagicMock()
        for k, v in defaults.items():
            setattr(result, k, v)
        result.num_spvs = defaults["num_spvs"]
        return result

    def test_basic_output(self):
        result = self._mock_result()
        text = render_portfolio_summary(result)
        assert "Test" in text
        assert "SPVs: 2" in text

    def test_irr_label_included(self):
        result = self._mock_result(simple_avg_project_irr=0.09)
        text = render_portfolio_summary(result)
        assert "NOT Portfolio XIRR" in text

    def test_warnings_section(self):
        result = self._mock_result(warnings=("test warning",))
        text = render_portfolio_summary(result)
        assert "test warning" in text


class TestIRRLabel:
    """IRR label must be explicit about what it is."""

    def test_label_mentions_not_portfolio_xirr(self):
        assert "NOT Portfolio XIRR" in _IRR_LABEL

    def test_label_mentions_simple_average(self):
        assert "Simple Average" in _IRR_LABEL