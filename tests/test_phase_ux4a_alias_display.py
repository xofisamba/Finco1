"""UX-4A: Scenario tab alias display tests.

Problem: scenario_tab.html effectiveValue macro looked up canonical field names
(tariff_eur_mwh) in overrides dict, but SCENARIO-2 stores overrides under matrix
alias keys (ppa_tariff_eur_mwh). Result: override value 65 showed as 75 (base),
no override badge appeared.

Fix: _SC_CANONICAL_TO_ALIAS map + updated effectiveValue / cellClass / badge logic.

Tests:
  A1. effectiveValue shows alias-keyed override value, not base value.
  A2. effectiveValue shows canonical-keyed override value (no regression).
  A3. effectiveValue returns base value when no override exists.
  A4. effectiveValue base case reads from base_input_set, not overrides.
  B1. cellClass returns --override when alias key is in overrides.
  B2. cellClass returns --inherited when neither alias nor canonical is overridden.
  B3. cellClass returns --base for base case always.
  C1. Badge condition triggers for alias-keyed override.
  C2. Badge condition does not trigger for non-overridden field.
  D1. All four alias pairs are present in template source.
  E1. Engine MD5 unchanged.
  E2. TUHO P1 DSCR unchanged.
  E3. Oborovo P1 DSCR unchanged.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
TUHO_P1_DSCR = 1.4507
OBOROVO_P1_DSCR = 1.15

_TEMPLATE_PATH = Path(REPO_ROOT) / "app/templates/partials/scenario_tab.html"


# ---------------------------------------------------------------------------
# Helpers — lightweight ScenarioRecord-like objects
# ---------------------------------------------------------------------------

class _FakeRecord:
    def __init__(self, *, is_base_case, base_input_set=None, snapshot=None, overrides=None):
        self.is_base_case = is_base_case
        self.base_input_set = base_input_set or {}
        self.snapshot = snapshot or {}
        self.overrides = overrides or {}


def _render_tab(base_record, non_base_records):
    """Render scenario_tab.html in isolation using Jinja2."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(
        loader=FileSystemLoader(str(Path(REPO_ROOT) / "app/templates")),
    )
    tpl = env.get_template("partials/scenario_tab.html")

    # Minimal context
    class _FakeProject:
        project_code = "test-proj"
    class _FakeWS:
        active_scenario_id = ""

    ctx = {
        "project_record": _FakeProject(),
        "base_case_record": base_record,
        "non_base_scenarios": non_base_records,
        "workspace_state": _FakeWS(),
        "is_user_project": True,
        "scenario_editable_fields": [
            ("Revenue / PPA", [("tariff_eur_mwh", "Tariff (EUR/MWh)")]),
            ("Technical", [("p50_hours", "P50 Hours")]),
            ("OPEX Summary", [("opex_y1_keur", "Y1 OPEX (kEUR)")]),
            ("Financing", [("tenor_years", "Tenor (years)")]),
        ],
    }
    return tpl.render(**ctx)


# ---------------------------------------------------------------------------
# A. effectiveValue macro
# ---------------------------------------------------------------------------

class TestEffectiveValue:
    def test_alias_keyed_override_shows_override_value(self):
        """Tariff override stored as ppa_tariff_eur_mwh must render as 65, not 75."""
        base = _FakeRecord(
            is_base_case=True,
            base_input_set={"tariff_eur_mwh": 75},
            snapshot={"tariff_eur_mwh": 75},
        )
        downside = _FakeRecord(
            is_base_case=False,
            snapshot={"tariff_eur_mwh": 75},
            overrides={"ppa_tariff_eur_mwh": 65},
        )
        html = _render_tab(base, [downside])
        # The Downside tariff cell must show 65
        assert "65" in html, "Override value 65 must appear in rendered HTML"
        # And 75 should appear in the Base cell but the Downside cell should show 65
        # Crude check: count occurrences; 65 must appear at least once for override cell
        assert html.count("65") >= 1

    def test_canonical_keyed_override_still_works(self):
        """Override stored under canonical key tariff_eur_mwh still renders correctly."""
        base = _FakeRecord(
            is_base_case=True,
            base_input_set={"tariff_eur_mwh": 75},
            snapshot={"tariff_eur_mwh": 75},
        )
        downside = _FakeRecord(
            is_base_case=False,
            snapshot={"tariff_eur_mwh": 75},
            overrides={"tariff_eur_mwh": 60},
        )
        html = _render_tab(base, [downside])
        assert "60" in html

    def test_no_override_shows_base_value(self):
        """Non-overridden Downside inherits base value."""
        base = _FakeRecord(
            is_base_case=True,
            base_input_set={"tariff_eur_mwh": 75},
            snapshot={"tariff_eur_mwh": 75},
        )
        downside = _FakeRecord(
            is_base_case=False,
            snapshot={"tariff_eur_mwh": 75},
            overrides={},
        )
        html = _render_tab(base, [downside])
        assert "75" in html

    def test_base_case_reads_base_input_set(self):
        """Base case always reads from base_input_set, not overrides."""
        base = _FakeRecord(
            is_base_case=True,
            base_input_set={"tariff_eur_mwh": 80},
            snapshot={},
            overrides={"ppa_tariff_eur_mwh": 50},  # overrides must be ignored for base
        )
        html = _render_tab(base, [])
        assert "80" in html


# ---------------------------------------------------------------------------
# B. cellClass macro
# ---------------------------------------------------------------------------

class TestCellClass:
    def test_alias_override_gives_override_class(self):
        """Cell with alias-keyed override gets sc-matrix-cell--override class."""
        base = _FakeRecord(
            is_base_case=True,
            base_input_set={"tariff_eur_mwh": 75},
            snapshot={"tariff_eur_mwh": 75},
        )
        downside = _FakeRecord(
            is_base_case=False,
            snapshot={"tariff_eur_mwh": 75},
            overrides={"ppa_tariff_eur_mwh": 65},
        )
        html = _render_tab(base, [downside])
        assert "sc-matrix-cell--override" in html

    def test_no_override_gives_inherited_class(self):
        """Cell with no override gets sc-matrix-cell--inherited class."""
        base = _FakeRecord(
            is_base_case=True,
            base_input_set={"tariff_eur_mwh": 75},
            snapshot={"tariff_eur_mwh": 75},
        )
        downside = _FakeRecord(
            is_base_case=False,
            snapshot={"tariff_eur_mwh": 75},
            overrides={},
        )
        html = _render_tab(base, [downside])
        assert "sc-matrix-cell--inherited" in html
        # Must NOT get --override class for tariff
        # (p50, opex, tenor cells also have no override)
        assert "sc-matrix-cell--override" not in html

    def test_base_case_always_gets_base_class(self):
        """Base case cell always gets sc-matrix-cell--base."""
        base = _FakeRecord(
            is_base_case=True,
            base_input_set={"tariff_eur_mwh": 75},
            snapshot={},
        )
        html = _render_tab(base, [])
        assert "sc-matrix-cell--base" in html
        assert "sc-matrix-cell--override" not in html
        assert "sc-matrix-cell--inherited" not in html


# ---------------------------------------------------------------------------
# C. Override badge
# ---------------------------------------------------------------------------

class TestOverrideBadge:
    def test_badge_appears_for_alias_override(self):
        """✎ badge appears when override is stored under alias key."""
        base = _FakeRecord(
            is_base_case=True,
            base_input_set={"tariff_eur_mwh": 75},
            snapshot={"tariff_eur_mwh": 75},
        )
        downside = _FakeRecord(
            is_base_case=False,
            snapshot={"tariff_eur_mwh": 75},
            overrides={"ppa_tariff_eur_mwh": 65},
        )
        html = _render_tab(base, [downside])
        assert "sc-override-badge" in html
        assert "✎" in html

    def test_badge_absent_for_non_overridden_field(self):
        """✎ badge absent when no override for field."""
        base = _FakeRecord(
            is_base_case=True,
            base_input_set={"tariff_eur_mwh": 75},
            snapshot={"tariff_eur_mwh": 75},
        )
        downside = _FakeRecord(
            is_base_case=False,
            snapshot={"tariff_eur_mwh": 75},
            overrides={},
        )
        html = _render_tab(base, [downside])
        assert "sc-override-badge" not in html


# ---------------------------------------------------------------------------
# D. Source completeness — all alias pairs present
# ---------------------------------------------------------------------------

class TestAliasSourceCompleteness:
    def test_all_alias_pairs_in_template(self):
        src = _TEMPLATE_PATH.read_text()
        pairs = [
            ("ppa_tariff_eur_mwh", "tariff_eur_mwh"),
            ("operating_hours_p50", "p50_hours"),
            ("opex_y1_total_keur", "opex_y1_keur"),
            ("senior_tenor_years", "tenor_years"),
        ]
        for alias, canonical in pairs:
            assert alias in src, f"Alias {alias} missing from template"
            assert canonical in src, f"Canonical {canonical} missing from template"


# ---------------------------------------------------------------------------
# E. Parity
# ---------------------------------------------------------------------------

class TestUX4AParity:
    def test_engine_md5_unchanged(self):
        digest = hashlib.md5(
            (Path(REPO_ROOT) / "app/waterfall_core.py").read_bytes()
        ).hexdigest()
        assert digest == ENGINE_MD5, f"waterfall_core.py changed: {digest}"

    def test_tuho_p1_dscr_unchanged(self):
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_tuho_wind1()
        result = _run_waterfall(proj, _build_period_engine(proj))
        for p in result.periods:
            d = getattr(p, "dscr", None)
            if d is not None and abs(d) < 1e10:
                assert abs(d - TUHO_P1_DSCR) < 0.001, f"TUHO P1 DSCR={d}"
                return
        pytest.fail("No finite DSCR found")

    def test_oborovo_p1_dscr_unchanged(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_oborovo()
        result = _run_waterfall(proj, _build_period_engine(proj))
        for p in result.periods:
            d = getattr(p, "dscr", None)
            if d is not None and abs(d) < 1e10:
                assert abs(d - OBOROVO_P1_DSCR) < 0.01, f"Oborovo P1 DSCR={d}"
                return
        pytest.fail("No finite DSCR found")
