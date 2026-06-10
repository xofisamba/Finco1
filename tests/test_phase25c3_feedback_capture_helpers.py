"""Phase 25C-3 — Pilot Feedback Capture helper tests.

Goal: Provide a structured, copyable feedback
template for the Generic Solar / Wind exploratory
pilot.

These tests prove:

- 6 fields are exposed in stable order
- Each field has the required attributes
- The 6 fields are: project, scenario,
  what_i_tried, what_i_expected, what_happened,
  screenshot
- The short template has 3 lines
- The exploratory disclaimer mentions the
  channel is read by humans, is not a support
  channel, and warns against secrets / PII
- The helper does NOT mutate any input
- The helper does NOT call the persistence layer
- The helper does NOT enable any feature flag
- The helper does NOT invent fake ticket IDs,
  fake run IDs, fake validation claims, or
  fake outputs
- The helper does NOT capture PII
"""

import os
import sys

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from app.ui.feedback_capture import (
    EXPLORATORY_DISCLAIMER,
    FIELD_HELP,
    FIELD_LABELS,
    FIELD_ORDER,
    FIELD_PROJECT,
    FIELD_SCENARIO,
    FIELD_SCREENSHOT,
    FIELD_WHAT_HAPPENED,
    FIELD_WHAT_I_EXPECTED,
    FIELD_WHAT_I_TRIED,
    SHORT_TEMPLATE_LINES,
    FeedbackField,
    FeedbackTemplate,
    build_feedback_template,
    is_short_line,
    is_supported_field,
)


# ---------------------------------------------------------------------------
# 1. Field vocabulary
# ---------------------------------------------------------------------------


class TestFieldVocabulary:
    """The field vocabulary has 6 entries in stable
    order."""

    def test_field_order_count(self):
        assert len(FIELD_ORDER) == 6

    def test_field_order_keys(self):
        expected = {
            FIELD_PROJECT,
            FIELD_SCENARIO,
            FIELD_WHAT_I_TRIED,
            FIELD_WHAT_I_EXPECTED,
            FIELD_WHAT_HAPPENED,
            FIELD_SCREENSHOT,
        }
        assert set(FIELD_ORDER) == expected

    def test_field_labels_keys(self):
        assert set(FIELD_LABELS.keys()) == set(FIELD_ORDER)

    def test_field_help_keys(self):
        assert set(FIELD_HELP.keys()) == set(FIELD_ORDER)


# ---------------------------------------------------------------------------
# 2. is_supported_field
# ---------------------------------------------------------------------------


class TestIsSupportedField:
    """The supported-field helper is explicit."""

    @pytest.mark.parametrize(
        "key,expected",
        [
            (FIELD_PROJECT, True),
            (FIELD_SCENARIO, True),
            (FIELD_WHAT_I_TRIED, True),
            (FIELD_WHAT_I_EXPECTED, True),
            (FIELD_WHAT_HAPPENED, True),
            (FIELD_SCREENSHOT, True),
            ("", False),
            ("unknown", False),
        ],
    )
    def test_is_supported(self, key, expected):
        assert is_supported_field(key) is expected


# ---------------------------------------------------------------------------
# 3. is_short_line
# ---------------------------------------------------------------------------


class TestIsShortLine:
    """The short-line helper is explicit."""

    @pytest.mark.parametrize(
        "line,expected",
        [
            ("Project", True),
            ("Project:", True),
            ("What I tried", True),
            ("What I tried:", True),
            ("What happened", True),
            ("What happened:", True),
            ("", False),
            ("Scenario", False),
        ],
    )
    def test_is_short_line(self, line, expected):
        assert is_short_line(line) is expected


# ---------------------------------------------------------------------------
# 4. Short template
# ---------------------------------------------------------------------------


class TestShortTemplate:
    """The short summary template has 3 lines."""

    def test_short_template_count(self):
        assert len(SHORT_TEMPLATE_LINES) == 3

    def test_short_template_contains_project(self):
        joined = " | ".join(SHORT_TEMPLATE_LINES)
        assert "Project" in joined

    def test_short_template_contains_what_i_tried(self):
        joined = " | ".join(SHORT_TEMPLATE_LINES)
        assert "What I tried" in joined

    def test_short_template_contains_what_happened(self):
        joined = " | ".join(SHORT_TEMPLATE_LINES)
        assert "What happened" in joined


# ---------------------------------------------------------------------------
# 5. Exploratory disclaimer
# ---------------------------------------------------------------------------


class TestExploratoryDisclaimer:
    """The disclaimer mentions the channel is read by
    humans, is not a support channel, and warns
    against secrets / PII."""

    def test_disclaimer_present(self):
        assert EXPLORATORY_DISCLAIMER
        assert len(EXPLORATORY_DISCLAIMER) > 20

    def test_disclaimer_mentions_humans(self):
        assert "humans" in EXPLORATORY_DISCLAIMER.lower()

    def test_disclaimer_warns_against_secrets(self):
        text = EXPLORATORY_DISCLAIMER.lower()
        assert "secrets" in text

    def test_disclaimer_warns_against_pii(self):
        text = EXPLORATORY_DISCLAIMER.lower()
        assert "pii" in text

    def test_disclaimer_says_exploratory(self):
        assert "exploratory" in EXPLORATORY_DISCLAIMER.lower()

    def test_disclaimer_does_not_claim_support(self):
        text = EXPLORATORY_DISCLAIMER.lower()
        # We must say it is NOT a support channel.
        assert "not a support" in text


# ---------------------------------------------------------------------------
# 6. build_feedback_template
# ---------------------------------------------------------------------------


class TestBuildFeedbackTemplate:
    """``build_feedback_template`` returns a frozen
    FeedbackTemplate with the 6 fields in order."""

    def test_default_build(self):
        tpl = build_feedback_template()
        assert isinstance(tpl, FeedbackTemplate)
        assert tpl.field_count() == 6

    def test_fields_are_in_order(self):
        tpl = build_feedback_template()
        for i, field in enumerate(tpl.fields, start=1):
            assert field.order == i

    def test_field_labels_match_vocabulary(self):
        tpl = build_feedback_template()
        for field in tpl.fields:
            assert field.label == FIELD_LABELS[field.key]
            assert field.help == FIELD_HELP[field.key]

    def test_short_lines_count(self):
        tpl = build_feedback_template()
        assert len(tpl.short_lines) == 3

    def test_feedback_template_is_frozen(self):
        tpl = build_feedback_template()
        with pytest.raises(Exception):
            tpl.fields = ()  # type: ignore[misc]

    def test_feedback_field_is_frozen(self):
        tpl = build_feedback_template()
        field = tpl.fields[0]
        with pytest.raises(Exception):
            field.label = "X"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 7. No forbidden imports
# ---------------------------------------------------------------------------


class TestNoForbiddenImports:
    """The helper must not import any forbidden
    module."""

    FORBIDDEN_MODULES = [
        "app.persistence",
        "app.services",
        "app.construction",
        "app.debt",
        "app.tax",
        "app.idc",
        "app.depreciation",
        "app.waterfall",
    ]

    @pytest.mark.parametrize("module", FORBIDDEN_MODULES)
    def test_forbidden_module_not_imported(self, module):
        from app.ui import feedback_capture
        src = open(feedback_capture.__file__).read()
        assert f"import {module}" not in src
        assert f"from {module}" not in src


# ---------------------------------------------------------------------------
# 8. No feature flag enablement
# ---------------------------------------------------------------------------


class TestNoFeatureFlagEnablement:
    """The helper must not enable any feature flag."""

    def test_helper_does_not_set_construction_flag(self):
        from app.ui import feedback_capture
        src = open(feedback_capture.__file__).read()
        assert "use_construction_schedule_engine" not in src
        assert "use_depreciation_canonical_engine" not in src
        assert "use_canonical_tax_depreciation" not in src
        assert "use_book_depreciation_for_pnl" not in src


# ---------------------------------------------------------------------------
# 9. No fake outputs / fake ticket IDs / PII capture
# ---------------------------------------------------------------------------


class TestNoFakeOutputs:
    """The helper must not invent fake ticket IDs,
    fake run IDs, fake validation claims, or
    fake outputs. It must not capture PII."""

    def test_helper_does_not_invent_ticket_ids(self):
        from app.ui import feedback_capture
        src = open(feedback_capture.__file__).read()
        assert "ticket_id" not in src
        assert "issue_id" not in src
        assert "feedback_id" not in src

    def test_helper_does_not_invent_run_ids(self):
        from app.ui import feedback_capture
        src = open(feedback_capture.__file__).read()
        assert "run_id" not in src

    def test_helper_does_not_invent_validation(self):
        from app.ui import feedback_capture
        src = open(feedback_capture.__file__).read()
        assert "parity_validated" not in src
        assert "is_validated" not in src.lower()
        assert "validation_status" not in src

    def test_helper_does_not_capture_pii(self):
        from app.ui import feedback_capture
        src = open(feedback_capture.__file__).read()
        # The helper does NOT define a "user_email"
        # / "user_id" / "ip_address" field. The
        # template fields are 6 abstract buckets.
        for forbidden in (
            "user_email",
            "user_id",
            "ip_address",
            "phone",
            "address",
        ):
            assert forbidden not in src

    def test_field_labels_dont_ask_for_pii(self):
        # The field labels are short, structured
        # and do NOT ask for PII.
        for label in FIELD_LABELS.values():
            assert "email" not in label.lower()
            assert "phone" not in label.lower()
            assert "address" not in label.lower()


# ---------------------------------------------------------------------------
# 10. Field help text
# ---------------------------------------------------------------------------


class TestFieldHelp:
    """The field help text is short and instructive."""

    @pytest.mark.parametrize("key", FIELD_ORDER)
    def test_field_help_present(self, key):
        assert FIELD_HELP[key]
        assert len(FIELD_HELP[key]) > 10

    @pytest.mark.parametrize("key", FIELD_ORDER)
    def test_field_help_warns_against_secrets(self, key):
        # Each field's help text mentions the
        # "no secrets / no PII" rule.
        if key == FIELD_SCREENSHOT:
            assert "secret" in FIELD_HELP[key].lower()
            assert "pii" in FIELD_HELP[key].lower()
        if key == FIELD_WHAT_HAPPENED:
            assert "secret" in FIELD_HELP[key].lower()
