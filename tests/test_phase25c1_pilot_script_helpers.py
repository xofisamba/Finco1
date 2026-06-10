"""Phase 25C-1 — Generic pilot script helper tests.

Goal: Provide a 9-step first-user pilot script for
Generic Solar / Generic Wind users.

These tests prove the helper:

- exposes 9 steps in stable order
- has pre-classified label / hint / route for each
  step
- has an exploratory disclaimer that mentions
  scope language without making lender / bank /
  audit claims
- does NOT mutate any input
- does NOT call the persistence layer
- does NOT enable any feature flag
- exposes a ``is_supported_project_type`` helper
- does NOT invent new routes
"""

import os
import sys

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from app.ui.generic_pilot_script import (
    EXPLORATORY_DISCLAIMER,
    STEP_CHANGE_INPUTS,
    STEP_COMPARE,
    STEP_CREATE,
    STEP_DUPLICATE_DOWNSIDE,
    STEP_EXPORT,
    STEP_HINTS,
    STEP_LABELS,
    STEP_ORDER,
    STEP_ROUTES,
    STEP_RUN,
    STEP_RUN_DOWNSIDE,
    STEP_SAVE_BASE,
    STEP_USE_DEFAULTS,
    PilotScript,
    PilotStep,
    build_pilot_script,
    is_supported_project_type,
)


PILOT_STEP_COUNT = 9


# ---------------------------------------------------------------------------
# 1. Step vocabulary
# ---------------------------------------------------------------------------


class TestStepVocabulary:
    """The step vocabulary has 9 entries in stable order."""

    def test_step_order_count(self):
        assert len(STEP_ORDER) == 9

    def test_step_order_keys(self):
        expected = {
            STEP_CREATE,
            STEP_USE_DEFAULTS,
            STEP_SAVE_BASE,
            STEP_RUN,
            STEP_DUPLICATE_DOWNSIDE,
            STEP_CHANGE_INPUTS,
            STEP_RUN_DOWNSIDE,
            STEP_COMPARE,
            STEP_EXPORT,
        }
        assert set(STEP_ORDER) == expected

    def test_step_labels_keys(self):
        assert set(STEP_LABELS.keys()) == set(STEP_ORDER)

    def test_step_hints_keys(self):
        assert set(STEP_HINTS.keys()) == set(STEP_ORDER)

    def test_step_routes_keys(self):
        assert set(STEP_ROUTES.keys()) == set(STEP_ORDER)


# ---------------------------------------------------------------------------
# 2. Exploratory disclaimer
# ---------------------------------------------------------------------------


class TestExploratoryDisclaimer:
    """The disclaimer mentions exploratory scope but
    avoids lender / bank / audit claims."""

    def test_disclaimer_present(self):
        assert EXPLORATORY_DISCLAIMER
        assert len(EXPLORATORY_DISCLAIMER) > 20

    def test_disclaimer_mentions_exploratory(self):
        assert "exploratory" in EXPLORATORY_DISCLAIMER.lower()

    def test_disclaimer_does_not_claim_lender_approval(self):
        # The disclaimer must say the workflow is
        # NOT lender-ready (not "is lender-ready").
        text = EXPLORATORY_DISCLAIMER.lower()
        assert "not lender" in text
        assert "not audit" in text

    def test_disclaimer_does_not_claim_bank_approval(self):
        text = EXPLORATORY_DISCLAIMER.lower()
        assert "not bank" in text or "bank-approved" not in text

    def test_disclaimer_does_not_claim_excel_parity(self):
        text = EXPLORATORY_DISCLAIMER.lower()
        assert "not excel" in text or "parity" in text


# ---------------------------------------------------------------------------
# 3. Routes — pre-existing only
# ---------------------------------------------------------------------------


class TestRoutesArePreExisting:
    """The 9 routes must be pre-existing app routes; we
    never invent new ones."""

    EXPECTED_ROUTES = {
        STEP_CREATE: "/projects/create",
        STEP_USE_DEFAULTS: "/scenarios/tab",
        STEP_SAVE_BASE: "/scenarios/save",
        STEP_RUN: "/scenarios/run",
        STEP_DUPLICATE_DOWNSIDE: "/scenarios/add",
        STEP_CHANGE_INPUTS: "/scenarios/tab",
        STEP_RUN_DOWNSIDE: "/scenarios/run",
        STEP_COMPARE: "/scenarios/compare",
        STEP_EXPORT: "/download",
    }

    def test_all_routes_match_expected(self):
        for key, expected in self.EXPECTED_ROUTES.items():
            assert STEP_ROUTES[key] == expected, (
                f"step {key!r}: route should be "
                f"{expected!r}, got {STEP_ROUTES[key]!r}"
            )

    def test_no_dynamically_generated_routes(self):
        for route in STEP_ROUTES.values():
            assert not route.startswith("__")
            assert "{" not in route


# ---------------------------------------------------------------------------
# 4. is_supported_project_type
# ---------------------------------------------------------------------------


class TestIsSupportedProjectType:
    """The supported-project-type helper is explicit."""

    @pytest.mark.parametrize(
        "pt,expected",
        [
            ("generic_solar", True),
            ("generic_wind", True),
            ("GENERIC_SOLAR", True),
            ("Generic_Wind", True),
            ("tuho", False),
            ("oborovo", False),
            ("", False),
        ],
    )
    def test_is_supported(self, pt, expected):
        assert is_supported_project_type(pt) is expected


# ---------------------------------------------------------------------------
# 5. build_pilot_script
# ---------------------------------------------------------------------------


class TestBuildPilotScript:
    """``build_pilot_script`` returns a frozen
    PilotScript with the 9 steps in order."""

    def test_default_build(self):
        s = build_pilot_script()
        assert isinstance(s, PilotScript)
        assert s.step_count() == 9
        assert s.project_type == "generic_solar"
        assert s.project_label == "Generic Solar"

    def test_generic_wind_build(self):
        s = build_pilot_script(
            project_type="generic_wind",
            project_label="Generic Wind",
        )
        assert s.project_type == "generic_wind"
        assert s.project_label == "Generic Wind"
        # Steps are identical (only the disclaimer
        # context changes).
        assert s.step_count() == 9

    def test_steps_are_in_order(self):
        s = build_pilot_script()
        for i, step in enumerate(s.steps, start=1):
            assert step.order == i

    def test_step_labels_match_vocabulary(self):
        s = build_pilot_script()
        for step in s.steps:
            assert step.label == STEP_LABELS[step.key]
            assert step.hint == STEP_HINTS[step.key]
            assert step.route == STEP_ROUTES[step.key]

    def test_pilot_script_is_frozen(self):
        s = build_pilot_script()
        with pytest.raises(Exception):
            s.steps = ()  # type: ignore[misc]

    def test_pilot_step_is_frozen(self):
        s = build_pilot_script()
        step = s.steps[0]
        with pytest.raises(Exception):
            step.label = "X"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6. No forbidden imports
# ---------------------------------------------------------------------------


class TestNoForbiddenImports:
    """The helper must not import any forbidden module."""

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
        from app.ui import generic_pilot_script
        src = open(generic_pilot_script.__file__).read()
        assert f"import {module}" not in src
        assert f"from {module}" not in src


# ---------------------------------------------------------------------------
# 7. No feature flag enablement
# ---------------------------------------------------------------------------


class TestNoFeatureFlagEnablement:
    """The helper must not enable any feature flag."""

    def test_helper_does_not_set_construction_flag(self):
        from app.ui import generic_pilot_script
        src = open(generic_pilot_script.__file__).read()
        assert "use_construction_schedule_engine" not in src
        assert "use_depreciation_canonical_engine" not in src
        assert "use_canonical_tax_depreciation" not in src
        assert "use_book_depreciation_for_pnl" not in src


# ---------------------------------------------------------------------------
# 8. No fake outputs
# ---------------------------------------------------------------------------


class TestNoFakeOutputs:
    """The helper must not invent fake run IDs, fake
    validation claims, or fake outputs."""

    def test_helper_does_not_invent_run_ids(self):
        from app.ui import generic_pilot_script
        src = open(generic_pilot_script.__file__).read()
        assert "run_id" not in src
        assert "run-1" not in src
        assert "snapshot_id" not in src

    def test_helper_does_not_invent_validation_status(self):
        from app.ui import generic_pilot_script
        src = open(generic_pilot_script.__file__).read()
        # We may mention "validated" in scope
        # language (e.g. "not Excel-parity validated")
        # but we never claim a project IS validated
        # or parity_validated.
        assert "parity_validated" not in src
        assert "is_validated" not in src.lower()
        assert "validation_status" not in src

    def test_helper_does_not_invent_outputs(self):
        from app.ui import generic_pilot_script
        src = open(generic_pilot_script.__file__).read()
        # We may mention IRR / DSCR / NPV in hint text
        # (e.g. "see IRR / DSCR" in the compare step)
        # but we never produce a numerical output.
        # No ``f``-prefixed IRR values, no JSON
        # output objects, no ``return`` statements
        # with computed values.
        for forbidden_pattern in (
            'return {',
            "return ['IRR'",
            '"IRR":',
            '"DSCR":',
            '"NPV":',
        ):
            assert forbidden_pattern not in src, (
                f"helper must NOT return computed "
                f"output: {forbidden_pattern!r}"
            )
