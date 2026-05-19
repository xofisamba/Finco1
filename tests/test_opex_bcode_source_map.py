"""Phase 7 — OPEX B-Code Source Map tests.

Validates the OPEX B-code source mapping CSV exists and contains all
required B-groups, sub-items, and classifications. This is a source-map
test, NOT a calculation parity test. No OPEX engine changes.
"""
import csv
import os
import pytest

REPORT_PATH = "reports/phase7_opex_bcode_source_map.csv"


class TestSourceMapExists:
    """CSV must exist."""

    def test_csv_exists(self):
        assert os.path.exists(REPORT_PATH), f"{REPORT_PATH} not found"


class TestBCodeCompleteness:
    """All 13 B-groups B.01-B.13 must be present."""

    @pytest.fixture
    def rows(self):
        with open(REPORT_PATH, newline="") as f:
            return list(csv.DictReader(f))

    def test_all_13_groups_present(self, rows):
        groups = sorted(set(r["category"] for r in rows))
        expected = [f"B.{i:02d}" for i in range(1, 14)]
        assert groups == expected, f"Expected {expected}, got {groups}"

    def test_b02_1_present(self, rows):
        bcodes = [r["bcode"] for r in rows]
        assert "B.02.1" in bcodes, "B.02.1 (explicit schedule) not found"

    def test_b11_1_present(self, rows):
        bcodes = [r["bcode"] for r in rows]
        assert "B.11.1" in bcodes, "B.11.1 (Agency Fee) not found"

    def test_b13_present(self, rows):
        bcodes = [r["bcode"] for r in rows]
        assert "B.13" in bcodes, "B.13 (Contingencies) not found"


class TestConfidenceClassification:
    """No non-zero base item may have confidence == unmapped."""

    @pytest.fixture
    def rows(self):
        with open(REPORT_PATH, newline="") as f:
            return list(csv.DictReader(f))

    def test_no_nonzero_unmapped(self, rows):
        """Any row with base_keur > 0 must not be UNMAPPED."""
        errors = []
        for r in rows:
            base_str = r["excel_base_keur_per_year"]
            # Handle "explicit" and "6%" as non-numeric but valid
            try:
                base = float(base_str)
            except ValueError:
                base = 0.0  # explicit/6% are not numeric base amounts but valid
            if base > 0 and r["confidence"] == "UNMAPPED":
                errors.append(f"{r['bcode']} has base={base} but confidence=UNMAPPED")
        assert not errors, "\n".join(errors)

    def test_b13_delta_class_contingency_pct(self, rows):
        b13_rows = [r for r in rows if r["bcode"] == "B.13"]
        assert len(b13_rows) == 1, f"Expected 1 B.13 row, got {len(b13_rows)}"
        assert b13_rows[0]["delta_class"] == "CONTINGENCY_PCT", (
            f"B.13 delta_class should be CONTINGENCY_PCT, "
            f"got {b13_rows[0]['delta_class']}"
        )

    def test_b02_1_delta_class_explicit_schedule(self, rows):
        b02_1_rows = [r for r in rows if r["bcode"] == "B.02.1"]
        assert len(b02_1_rows) == 1
        assert b02_1_rows[0]["delta_class"] == "EXPLICIT_SCHEDULE", (
            f"B.02.1 delta_class should be EXPLICIT_SCHEDULE, "
            f"got {b02_1_rows[0]['delta_class']}"
        )

    def test_b11_1_delta_class_active_flag(self, rows):
        b11_1_rows = [r for r in rows if r["bcode"] == "B.11.1"]
        assert len(b11_1_rows) == 1
        assert b11_1_rows[0]["delta_class"] == "ACTIVE_FLAG", (
            f"B.11.1 delta_class should be ACTIVE_FLAG, "
            f"got {b11_1_rows[0]['delta_class']}"
        )


class TestHorizonTotal:
    """Documented horizon total including contingencies is ~84,675 kEUR."""

    @pytest.fixture
    def rows(self):
        with open(REPORT_PATH, newline="") as f:
            return list(csv.DictReader(f))

    def test_contingency_base_is_6_pct(self, rows):
        b13_rows = [r for r in rows if r["bcode"] == "B.13"]
        assert len(b13_rows) == 1
        assert "6%" in b13_rows[0]["excel_base_keur_per_year"], (
            f"B.13 base should be '6%', got {b13_rows[0]['excel_base_keur_per_year']}"
        )

    def test_b09_is_zero_line(self, rows):
        b09_rows = [r for r in rows if r["bcode"] == "B.09"]
        assert len(b09_rows) == 1
        assert b09_rows[0]["delta_class"] == "ZERO_LINE", (
            f"B.09 should be ZERO_LINE, got {b09_rows[0]['delta_class']}"
        )
        assert b09_rows[0]["excel_base_keur_per_year"] == "0.0"