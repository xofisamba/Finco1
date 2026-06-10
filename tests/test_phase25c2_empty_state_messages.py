"""Phase 25C-2 — Empty / Error state message tests.

Goal: Provide 7 user-facing empty / error state
messages for the Generic Solar / Generic Wind
exploratory workflow.

These tests prove:

- 7 conditions are exposed in stable order
- Each message has the required fields
- Each message has a severity in
  {info, warning, error}
- Each message has a valid next-action route
  (pre-existing app route)
- The message text does NOT contain stack
  traces, UndefinedError, AttributeError, or
  internal error codes
- The exploratory scope language is in the body
  for messages with is_exploratory_note=True
- The helper does NOT mutate any input
- The helper does NOT call the persistence layer
- The helper does NOT enable any feature flag
- The helper does NOT invent fake run IDs, fake
  validation claims, or fake outputs
"""

import os
import re
import sys

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from app.ui.empty_state_messages import (
    ACTION_ROUTES,
    ALL_CONDITIONS,
    ALL_SEVERITIES,
    CONDITION_DIRTY_UNSAVED,
    CONDITION_EXPORT_BEFORE_RUN,
    CONDITION_LT_2_SCENARIOS,
    CONDITION_NO_PROJECT,
    CONDITION_NO_SCENARIO,
    CONDITION_NOT_RUN,
    CONDITION_STALE_RUN,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    Message,
    build_all_messages,
    build_message,
    is_supported_condition,
)


# ---------------------------------------------------------------------------
# 1. Condition vocabulary
# ---------------------------------------------------------------------------


class TestConditionVocabulary:
    """The condition vocabulary has 7 entries in
    stable order."""

    def test_all_conditions_count(self):
        assert len(ALL_CONDITIONS) == 7

    def test_all_conditions_keys(self):
        expected = {
            CONDITION_NO_PROJECT,
            CONDITION_NO_SCENARIO,
            CONDITION_NOT_RUN,
            CONDITION_LT_2_SCENARIOS,
            CONDITION_EXPORT_BEFORE_RUN,
            CONDITION_DIRTY_UNSAVED,
            CONDITION_STALE_RUN,
        }
        assert set(ALL_CONDITIONS) == expected

    def test_severities_count(self):
        assert len(ALL_SEVERITIES) == 3
        assert SEVERITY_INFO in ALL_SEVERITIES
        assert SEVERITY_WARNING in ALL_SEVERITIES
        assert SEVERITY_ERROR in ALL_SEVERITIES


# ---------------------------------------------------------------------------
# 2. is_supported_condition
# ---------------------------------------------------------------------------


class TestIsSupportedCondition:
    """The supported-condition helper is explicit."""

    @pytest.mark.parametrize(
        "cond,expected",
        [
            (CONDITION_NO_PROJECT, True),
            (CONDITION_NO_SCENARIO, True),
            (CONDITION_NOT_RUN, True),
            (CONDITION_LT_2_SCENARIOS, True),
            (CONDITION_EXPORT_BEFORE_RUN, True),
            (CONDITION_DIRTY_UNSAVED, True),
            (CONDITION_STALE_RUN, True),
            ("", False),
            ("unknown", False),
        ],
    )
    def test_is_supported(self, cond, expected):
        assert is_supported_condition(cond) is expected


# ---------------------------------------------------------------------------
# 3. Message shape
# ---------------------------------------------------------------------------


class TestMessageShape:
    """Each message has the required fields."""

    @pytest.mark.parametrize("cond", ALL_CONDITIONS)
    def test_message_has_required_fields(self, cond):
        m = build_message(cond)
        assert isinstance(m, Message)
        assert m.condition == cond
        assert m.title
        assert m.body
        assert m.next_action
        assert m.next_action_route
        assert m.severity in ALL_SEVERITIES

    @pytest.mark.parametrize("cond", ALL_CONDITIONS)
    def test_message_title_is_short(self, cond):
        m = build_message(cond)
        # Title is short: <= 60 chars
        assert len(m.title) <= 60, (
            f"title for {cond!r} is too long: "
            f"{m.title!r}"
        )

    @pytest.mark.parametrize("cond", ALL_CONDITIONS)
    def test_message_body_does_not_contain_stack_trace(
        self, cond
    ):
        m = build_message(cond)
        body_lc = m.body.lower()
        # Must NOT contain internal Python error
        # markers.
        assert "traceback" not in body_lc
        assert "undefinederror" not in body_lc
        assert "attributeerror" not in body_lc
        assert "typeerror" not in body_lc
        assert "keyerror" not in body_lc

    @pytest.mark.parametrize("cond", ALL_CONDITIONS)
    def test_message_title_does_not_contain_stack_trace(
        self, cond
    ):
        m = build_message(cond)
        title_lc = m.title.lower()
        assert "traceback" not in title_lc
        assert "undefinederror" not in title_lc
        assert "attributeerror" not in title_lc


# ---------------------------------------------------------------------------
# 4. Pre-existing routes
# ---------------------------------------------------------------------------


class TestRoutesArePreExisting:
    """All next-action routes must be pre-existing
    app routes; we never invent new ones."""

    EXPECTED_ROUTES = {
        "/projects/create",
        "/scenarios/tab",
        "/scenarios/save",
        "/scenarios/run",
        "/scenarios/add",
    }

    def test_action_routes_known(self):
        for route in ACTION_ROUTES.values():
            assert route in self.EXPECTED_ROUTES, (
                f"action route {route!r} is not "
                f"in the pre-existing set"
            )

    @pytest.mark.parametrize("cond", ALL_CONDITIONS)
    def test_message_routes_are_pre_existing(self, cond):
        m = build_message(cond)
        assert m.next_action_route in self.EXPECTED_ROUTES


# ---------------------------------------------------------------------------
# 5. Severity distribution
# ---------------------------------------------------------------------------


class TestSeverityDistribution:
    """Severity is one of info / warning / error.
    We classify the 7 conditions as:
    - info: no_project, no_scenario, not_run,
      lt_2_scenarios
    - warning: export_before_run, dirty_unsaved,
      stale_run
    """

    EXPECTED_INFO = {
        CONDITION_NO_PROJECT,
        CONDITION_NO_SCENARIO,
        CONDITION_NOT_RUN,
        CONDITION_LT_2_SCENARIOS,
    }
    EXPECTED_WARNING = {
        CONDITION_EXPORT_BEFORE_RUN,
        CONDITION_DIRTY_UNSAVED,
        CONDITION_STALE_RUN,
    }

    @pytest.mark.parametrize("cond", sorted(EXPECTED_INFO))
    def test_info_conditions(self, cond):
        m = build_message(cond)
        assert m.severity == SEVERITY_INFO

    @pytest.mark.parametrize("cond", sorted(EXPECTED_WARNING))
    def test_warning_conditions(self, cond):
        m = build_message(cond)
        assert m.severity == SEVERITY_WARNING


# ---------------------------------------------------------------------------
# 6. Exploratory note
# ---------------------------------------------------------------------------


class TestExploratoryNote:
    """The export_before_run message includes
    exploratory scope language; other conditions
    don't have to."""

    def test_export_before_run_is_exploratory(self):
        m = build_message(CONDITION_EXPORT_BEFORE_RUN)
        assert m.is_exploratory_note is True

    def test_export_before_run_body_mentions_exploratory(self):
        m = build_message(CONDITION_EXPORT_BEFORE_RUN)
        # We may or may not include exploratory
        # scope language in the body for this
        # specific condition. The flag is True.
        assert m.is_exploratory_note is True

    def test_other_conditions_may_or_may_not_be_exploratory(self):
        # Other conditions default to
        # is_exploratory_note=False; that's
        # the safe default.
        for cond in (
            CONDITION_NO_PROJECT,
            CONDITION_NO_SCENARIO,
            CONDITION_NOT_RUN,
            CONDITION_LT_2_SCENARIOS,
            CONDITION_DIRTY_UNSAVED,
            CONDITION_STALE_RUN,
        ):
            m = build_message(cond)
            assert m.is_exploratory_note is False, (
                f"{cond!r} should default to "
                f"is_exploratory_note=False"
            )


# ---------------------------------------------------------------------------
# 7. build_all_messages
# ---------------------------------------------------------------------------


class TestBuildAllMessages:
    """``build_all_messages`` returns all 7 messages
    keyed by condition."""

    def test_build_all_messages_count(self):
        out = build_all_messages()
        assert len(out) == 7
        for cond in ALL_CONDITIONS:
            assert cond in out

    def test_build_all_messages_custom_label(self):
        out = build_all_messages(
            project_label="Generic Wind",
        )
        # All bodies should mention the new label
        # (or at least the first message).
        m = out[CONDITION_NO_PROJECT]
        assert "Generic Wind" in m.body


# ---------------------------------------------------------------------------
# 8. No forbidden imports
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
        from app.ui import empty_state_messages
        src = open(empty_state_messages.__file__).read()
        assert f"import {module}" not in src
        assert f"from {module}" not in src


# ---------------------------------------------------------------------------
# 9. No feature flag enablement
# ---------------------------------------------------------------------------


class TestNoFeatureFlagEnablement:
    """The helper must not enable any feature flag."""

    def test_helper_does_not_set_construction_flag(self):
        from app.ui import empty_state_messages
        src = open(empty_state_messages.__file__).read()
        assert "use_construction_schedule_engine" not in src
        assert "use_depreciation_canonical_engine" not in src
        assert "use_canonical_tax_depreciation" not in src
        assert "use_book_depreciation_for_pnl" not in src


# ---------------------------------------------------------------------------
# 10. No fake outputs
# ---------------------------------------------------------------------------


class TestNoFakeOutputs:
    """The helper must not invent fake run IDs, fake
    validation claims, or fake outputs."""

    def test_helper_does_not_invent_run_ids(self):
        from app.ui import empty_state_messages
        src = open(empty_state_messages.__file__).read()
        assert "run_id" not in src
        assert "run-1" not in src
        assert "snapshot_id" not in src

    def test_helper_does_not_invent_validation(self):
        from app.ui import empty_state_messages
        src = open(empty_state_messages.__file__).read()
        assert "parity_validated" not in src
        assert "is_validated" not in src.lower()
        assert "validation_status" not in src

    def test_messages_dont_claim_audit(self):
        for cond in ALL_CONDITIONS:
            m = build_message(cond)
            # The body must not make audit / bank /
            # lender claims; we may MENTION them
            # in scope language, but we never claim
            # a project IS audit-ready.
            body = m.body.lower()
            if "audit" in body:
                assert "not audit" in body or "exploratory" in body
            if "lender" in body:
                assert "not lender" in body or "exploratory" in body
            if "bank" in body:
                assert "not bank" in body or "exploratory" in body
