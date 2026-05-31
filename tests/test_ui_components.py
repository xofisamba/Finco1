"""Tests for app/ui/components.py helpers (non-Streamlit)."""
import pytest
from app.ui.components import format_metric_value, status_badge, STATUS_LABELS

def test_format_metric_value_currency():
    result = format_metric_value(1_500_000, "currency")
    assert "1.5M" in result or "1500" in result
    result2 = format_metric_value(500_000, "currency")
    assert "k" in result2 or "K" in result2 or "500" in result2

def test_format_metric_value_percent():
    assert "10.00%" in format_metric_value(0.10, "percent")
    assert "n/a" in format_metric_value(None, "percent")

def test_format_metric_value_ratio():
    assert format_metric_value(1.45, "ratio") == "1.450"

def test_format_metric_value_none():
    assert format_metric_value(None) == "n/a"

def test_format_metric_value_auto_detects_percent():
    assert "%" in format_metric_value(0.05)

def test_format_metric_value_auto_detects_currency():
    result = format_metric_value(2_000_000)
    assert "M" in result or "k" in result

def test_status_labels_has_required_keys():
    assert "ok" in STATUS_LABELS
    assert "partial" in STATUS_LABELS
    assert "experimental" in STATUS_LABELS


def test_status_labels_include_full_partial_experimental():
    from app.ui.components import STATUS_LABELS
    assert STATUS_LABELS["full"] == "✅ Full model"
    assert STATUS_LABELS["partial"] == "⚠️ Partial integration"
    assert STATUS_LABELS["experimental"] == "🧪 Experimental"


def test_status_labels_restore_warning_and_error_emojis():
    from app.ui.components import STATUS_LABELS
    assert STATUS_LABELS["warning"] == "⚠️ Warning"
    assert STATUS_LABELS["error"] == "❌ Error"


def test_format_metric_value_handles_none():
    from app.ui.components import format_metric_value
    assert format_metric_value(None) == "n/a"
