"""Stack V — Excel Audit Completeness tests.

Verifies:
1. Main CSV export contains all new tax audit columns.
2. export_tax_audit_csv produces correct columns.
3. export_formula_sources_csv produces two-column CSV.
4. No KPI movement (TUHO equity_irr ~0.1132, Oborovo ~0.1054).
5. Audit CSV rows equal number of operating periods.
6. tax_accrued and cash_paid columns are non-negative.
"""
from __future__ import annotations
import csv
import os
import sys
import tempfile

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ui_runner import run_demo_project
from utils.export import (
    export_waterfall_csv,
    export_tax_audit_csv,
    export_formula_sources_csv,
    _FORMULA_SOURCES,
    _TAX_AUDIT_COLUMNS,
)

_TAX_AUDIT_FIELDS = [
    "corporate_tax_cash_keur",
    "cit_accrual_audit_keur",
    "taxable_profit_keur",
    "taxable_income_before_losses_audit_keur",
    "taxable_profit_after_losses_audit_keur",
    "tax_loss_opening_audit_keur",
    "tax_loss_used_audit_keur",
    "tax_loss_closing_audit_keur",
    "fiscal_reintegration_audit_keur",
    "tax_depreciation_audit_keur",
    "cash_tax_current_period_audit_keur",
    "cash_tax_excel_style_h2_diagnostic_keur",
    "r67_excel_style_cash_tax_diagnostic_keur",
]


@pytest.fixture(scope="module")
def tuho():
    return run_demo_project("TUHO").result


@pytest.fixture(scope="module")
def oborovo():
    return run_demo_project("Oborovo").result


# ── 1. Main CSV contains all audit columns ────────────────────────────────────

class TestV1MainCSVAuditColumns:
    def test_all_audit_columns_present(self, tuho):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            path = f.name
        try:
            export_waterfall_csv(tuho, path)
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
            for col in _TAX_AUDIT_FIELDS:
                assert col in headers, f"Missing audit column: {col}"
        finally:
            os.unlink(path)

    def test_tax_keur_still_present(self, tuho):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            path = f.name
        try:
            export_waterfall_csv(tuho, path)
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
            assert "tax_keur" in headers
        finally:
            os.unlink(path)


# ── 2. export_tax_audit_csv correct columns ───────────────────────────────────

class TestV3TaxAuditCSV:
    def test_correct_columns(self, tuho):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            path = f.name
        try:
            export_tax_audit_csv(tuho, path)
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
            for col in _TAX_AUDIT_COLUMNS:
                assert col in headers, f"Missing tax audit column: {col}"
        finally:
            os.unlink(path)

    # ── 5. Rows equal number of operating periods ─────────────────────────────

    def test_rows_equal_operating_periods(self, tuho):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            path = f.name
        try:
            export_tax_audit_csv(tuho, path)
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            expected = sum(1 for p in tuho.periods if p.is_operation)
            assert len(rows) == expected
        finally:
            os.unlink(path)

    # ── 6. tax_accrued and cash_paid non-negative ─────────────────────────────

    def test_tax_accrued_non_negative(self, tuho):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            path = f.name
        try:
            export_tax_audit_csv(tuho, path)
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            for row in rows:
                assert float(row["tax_accrued_keur"]) >= -0.01, (
                    f"Negative tax_accrued in period {row['period']}: {row['tax_accrued_keur']}"
                )
        finally:
            os.unlink(path)

    def test_cash_paid_non_negative(self, tuho):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            path = f.name
        try:
            export_tax_audit_csv(tuho, path)
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            for row in rows:
                assert float(row["corporate_tax_cash_keur"]) >= -0.01, (
                    f"Negative cash_paid in period {row['period']}: {row['corporate_tax_cash_keur']}"
                )
        finally:
            os.unlink(path)


# ── 3. export_formula_sources_csv two-column CSV ─────────────────────────────

class TestV2FormulaSourcesCSV:
    def test_two_columns(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            path = f.name
        try:
            export_formula_sources_csv(path)
            with open(path, newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
            assert rows[0] == ["column_name", "source"]
            for row in rows[1:]:
                assert len(row) == 2
        finally:
            os.unlink(path)

    def test_all_audit_fields_documented(self):
        for col in _TAX_AUDIT_FIELDS:
            assert col in _FORMULA_SOURCES, f"Missing formula source for: {col}"

    def test_row_count_matches_formula_sources(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            path = f.name
        try:
            export_formula_sources_csv(path)
            with open(path, newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
            # header + one row per entry
            assert len(rows) == len(_FORMULA_SOURCES) + 1
        finally:
            os.unlink(path)


# ── 4. No KPI movement ────────────────────────────────────────────────────────

class TestNoKPIMovement:
    def test_tuho_equity_irr(self, tuho):
        assert abs(tuho.equity_irr - 0.1132) < 0.0003, (
            f"TUHO equity_irr moved: {tuho.equity_irr:.4f}"
        )

    def test_oborovo_equity_irr(self, oborovo):
        assert abs(oborovo.equity_irr - 0.1054) < 0.0003, (
            f"Oborovo equity_irr moved: {oborovo.equity_irr:.4f}"
        )
