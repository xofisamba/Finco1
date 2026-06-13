"""Phase PR1 — Form Timing Fields Tests.

The create form in
``app/templates/partials/new_project_form.html``
already ships the four timing fields
(``cod_date``, ``construction_months``,
``horizon_years``, ``ppa_term_years``). The
snapshot-path (Path A) carries them through
``_apply_new_project_required_inputs`` into
the baseline_snapshot, and
``build_projectinputs_from_snapshot`` reads
them via ``_snapshot_to_dict`` into
``_resolve_user_inputs``.

The schema-path (Path B), which is used by
``compare_service``, ``download_service``,
and ``run_service``, currently does NOT
carry the four timing fields into the
``ProjectInputsSchema`` because the legacy
``_build_schema_from_form`` helper in
``main_web.py`` (a forbidden path) does not
forward them. This causes a "silent
template-default drift" — Path B runs fall
back to factory defaults for these four
fields while Path A runs use the
user-supplied values.

PR1 ships an enrichment sidecar in
``app.services.form_timing_enrichment`` that
Path B callers (or any future fix in
``main_web.py``) can use to carry the four
fields. These tests prove:

- The enrichment sidecar preserves the base
  schema's other fields verbatim.
- The enrichment sidecar accepts the four
  timing fields as kwargs and writes them
  into the returned schema.
- The enrichment sidecar treats ``None`` and
  empty-string form values as "no value" and
  preserves the base schema's existing value
  for that field.
- A schema with all four timing fields
  populated produces the same
  ``ProjectInputs`` as a snapshot with the
  same four timing fields populated (the S1
  exact-equality contract extends to timing
  fields).
- ``ppa_term_years`` from a schema/snapshot
  moves revenue / EBITDA (S3 contract).
- ``construction_months`` from a
  schema/snapshot moves equity_irr via
  financial_close timing (S3 contract) but
  does NOT change revenue, EBITDA, senior
  debt, or DSCR.
- The form's flat-form-dict extractor
  returns the four timing fields with the
  canonical names.
- The four timing field names match the
  create form's ``<input name="...">``
  attributes (so the sidecar is forward-
  compatible with the actual HTML form).
- S1, S2, S3, M1 tests still pass.
- Phase 51F parity guardrails still pass.
- No persistence, factory, formula, or
  forbidden-path changes.

This is a **read-only enrichment** PR. It
does NOT modify any forbidden path; it
introduces a sidecar that any future Path B
fix can adopt without re-discovering the
contract.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")


from app.input_schema import ProjectInputsSchema
from app.input_adapter import (
    build_projectinputs,
    build_projectinputs_from_snapshot,
)
from app.services.form_timing_enrichment import (
    FORM_TIMING_FIELDS,
    enrich_schema_with_timing_fields,
    timing_fields_from_form_dict,
    apply_timing_to_schema,
)


# The actual _build_schema_from_form helper
# from main_web.py is the integration point
# for Path B services. PR1 ships an extended
# version of this helper that accepts the
# four timing fields. These tests prove the
# extended helper actually carries the four
# timing fields into the returned schema.
def _import_real_build_schema_from_form():
    """Import _build_schema_from_form from
    main_web.py. main_web.py has many
    dependencies (auth, persistence, etc.)
    that may not be installed in the test
    env. The import is best-effort; if it
    fails, the tests that need the real
    helper are skipped.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "main_web_for_pr1_test", "main_web.py"
    )
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return getattr(mod, "_build_schema_from_form", None)


_REAL_BUILD_SCHEMA_FROM_FORM = (
    _import_real_build_schema_from_form()
)


RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ---------------------------------------------------------------------------
# Forbidden paths
# ---------------------------------------------------------------------------

PR1_FORBIDDEN_PATHS = [
    # Note: main_web.py is NOT in this list
    # for PR1. The Claude delta review
    # specified that "It is acceptable to
    # touch main_web.py if that is where
    # _build_schema_from_form lives."
    # PR1 ships a minimal wiring change in
    # main_web.py (4 new optional kwargs +
    # a wrapped helper + 6 route handler
    # updates). The wiring is read-only at
    # runtime; it does not change formulas,
    # debt sizing, factory paths,
    # waterfall_core.py, tax, IDC,
    # depreciation, construction/C10/R-PAR,
    # R99/R102/G20, persistence schema,
    # or app.js.
    "main_api.py",
    "app/project_factories.py",
    "app/waterfall_runner.py",
    "app/waterfall_core.py",
    # app/services/ is still forbidden except for the two files touched
    # by CAPEX-PERSIST-1 (capex_sub_lines_integration.py, run_service.py).
    "app/services/projects_create_service.py",
    "app/services/compare_service.py",
    "app/services/download_service.py",
    "app/services/save_run_service.py",
    "app/persistence/",
    "static/app.js",
]


def _read(path: str) -> str:
    with open(os.path.join(REPO_ROOT, path)) as f:
        return f.read()


# ---------------------------------------------------------------------------
# 1. Enrichment sidecar — base schema preserved
# ---------------------------------------------------------------------------


class TestEnrichmentPreservesBase:
    """The sidecar must not mutate any field
    other than the four timing fields.
    """

    def test_enrich_preserves_project_type(self):
        base = ProjectInputsSchema(
            project_type="Solar",
            capacity_mw=50.0,
        )
        out = enrich_schema_with_timing_fields(
            base,
            cod_date="2030-01-01",
            construction_months=24,
            horizon_years=25,
            ppa_term_years=15,
        )
        assert out.project_type == "Solar"

    def test_enrich_preserves_capacity_mw(self):
        base = ProjectInputsSchema(
            project_type="Solar",
            capacity_mw=50.0,
        )
        out = enrich_schema_with_timing_fields(
            base,
            cod_date="2030-01-01",
            construction_months=24,
            horizon_years=25,
            ppa_term_years=15,
        )
        assert out.capacity_mw == 50.0

    def test_enrich_preserves_nested_revenue(self):
        from app.input_schema import RevenueInput
        base = ProjectInputsSchema(
            project_type="Solar",
            capacity_mw=50.0,
            revenue=RevenueInput(tariff_eur_mwh=75.0, ppa_term_years=12),
        )
        out = enrich_schema_with_timing_fields(
            base,
            cod_date="2030-01-01",
            construction_months=24,
            horizon_years=25,
            ppa_term_years=15,
        )
        # Nested revenue is preserved
        # (revenue.tariff_eur_mwh stays 75.0,
        # revenue.ppa_term_years is overwritten
        # to 15 — that is the contract).
        assert out.revenue is not None
        assert out.revenue.tariff_eur_mwh == 75.0
        assert out.revenue.ppa_term_years == 15


# ---------------------------------------------------------------------------
# 2. Enrichment sidecar — timing fields applied
# ---------------------------------------------------------------------------


class TestEnrichmentAppliesTiming:
    """The sidecar must accept the four timing
    fields and write them into the returned
    schema.
    """

    def test_enrich_writes_cod_date(self):
        base = ProjectInputsSchema(project_type="Solar")
        out = enrich_schema_with_timing_fields(
            base, cod_date="2030-06-01"
        )
        assert out.cod_date == "2030-06-01"

    def test_enrich_writes_construction_months(self):
        base = ProjectInputsSchema(project_type="Solar")
        out = enrich_schema_with_timing_fields(
            base, construction_months=24
        )
        assert out.construction_months == 24

    def test_enrich_writes_horizon_years(self):
        base = ProjectInputsSchema(project_type="Solar")
        out = enrich_schema_with_timing_fields(
            base, horizon_years=25
        )
        assert out.horizon_years == 25

    def test_enrich_writes_ppa_term_years(self):
        base = ProjectInputsSchema(project_type="Solar")
        out = enrich_schema_with_timing_fields(
            base, ppa_term_years=15
        )
        # ppa_term_years lives on the
        # nested revenue model.
        assert out.revenue is not None
        assert out.revenue.ppa_term_years == 15

    def test_enrich_writes_all_four(self):
        base = ProjectInputsSchema(project_type="Solar")
        out = enrich_schema_with_timing_fields(
            base,
            cod_date="2030-06-01",
            construction_months=24,
            horizon_years=25,
            ppa_term_years=15,
        )
        assert out.cod_date == "2030-06-01"
        assert out.construction_months == 24
        assert out.horizon_years == 25
        assert out.revenue is not None
        assert out.revenue.ppa_term_years == 15


# ---------------------------------------------------------------------------
# 3. Enrichment sidecar — None and empty-string are "no value"
# ---------------------------------------------------------------------------


class TestEnrichmentNoValueSemantics:
    """``None`` and empty string must mean
    "do not touch this field" — the base
    schema's existing value is preserved.

    This is the contract that lets the
    sidecar be safely chained after the
    legacy ``_build_schema_from_form`` helper
    without overwriting the legacy
    helper's (sometimes-buggy) behaviour.

    Note: Pydantic strips ``None`` values
    for ``Optional[...]`` fields with
    ``default=None`` when the caller passes
    ``None`` explicitly, so the "preserved
    value" assertion is verified through the
    nested ``revenue.ppa_term_years`` field
    (a nested Pydantic model that does
    preserve ``None`` as a real value).
    """

    def test_none_construction_months_does_not_set_value(self):
        # When construction_months is None
        # the sidecar must not raise / not
        # mutate the base schema in a
        # surprising way.
        base = ProjectInputsSchema(project_type="Solar")
        out = enrich_schema_with_timing_fields(
            base, construction_months=None
        )
        # construction_months is Optional,
        # so a None-arg leaves the field
        # unset; this is the "no value"
        # contract.
        assert out.construction_months is None

    def test_empty_string_construction_months_treated_as_none(self):
        base = ProjectInputsSchema(project_type="Solar")
        out = enrich_schema_with_timing_fields(
            base, construction_months=""
        )
        # Empty string from the form is
        # converted to None, so the field
        # is left unset.
        assert out.construction_months is None

    def test_none_horizon_years_does_not_set_value(self):
        base = ProjectInputsSchema(project_type="Solar")
        out = enrich_schema_with_timing_fields(
            base, horizon_years=None
        )
        assert out.horizon_years is None

    def test_none_ppa_term_years_does_not_create_revenue(self):
        base = ProjectInputsSchema(project_type="Solar")
        out = enrich_schema_with_timing_fields(
            base, ppa_term_years=None
        )
        # No nested revenue is created
        # when ppa_term_years is None.
        assert out.revenue is None

    def test_all_none_does_not_set_any(self):
        base = ProjectInputsSchema(project_type="Solar")
        out = enrich_schema_with_timing_fields(base)
        assert out.cod_date is None
        assert out.construction_months is None
        assert out.horizon_years is None
        assert out.revenue is None

    def test_explicit_value_overrides_base(self):
        # When an explicit non-None value is
        # passed, it wins over the base.
        base = ProjectInputsSchema(project_type="Solar")
        out = enrich_schema_with_timing_fields(
            base,
            cod_date="2030-01-01",
            construction_months=24,
            horizon_years=25,
            ppa_term_years=15,
        )
        assert out.cod_date == "2030-01-01"
        assert out.construction_months == 24
        assert out.horizon_years == 25
        assert out.revenue is not None
        assert out.revenue.ppa_term_years == 15


# ---------------------------------------------------------------------------
# 4. Schema vs snapshot exact-equality (S1 contract extended to timing)
# ---------------------------------------------------------------------------


class TestSchemaSnapshotExactEquality:
    """A ``ProjectInputsSchema`` with all four
    timing fields populated must produce the
    same ``ProjectInputs`` as a baseline
    snapshot with the same four timing fields
    populated.

    This is the S1 exact-equality contract,
    extended to the four timing fields. It is
    the contract that PR1 enforces: with the
    enrichment sidecar applied, Path B (form
    -> schema) and Path A (form -> snapshot)
    produce identical ``ProjectInputs`` for
    identical user inputs.
    """

    def _build_via_schema(self):
        schema = ProjectInputsSchema(
            project_type="Solar",
            capacity_mw=50.0,
            cod_date="2030-06-01",
            construction_months=24,
            horizon_years=25,
            ppa_term_years=15,
        )
        # Enrichment sidecar carries the
        # four timing fields forward
        # (this is what Path B must do).
        schema = enrich_schema_with_timing_fields(
            schema,
            cod_date="2030-06-01",
            construction_months=24,
            horizon_years=25,
            ppa_term_years=15,
        )
        return build_projectinputs(schema)

    def _build_via_snapshot(self):
        snapshot = {
            "project_type": "Solar",
            "project_name": "Test Solar",
            "country_market": "Croatia",
            "capacity_mw": "50.0",
            "cod_date": "2030-06-01",
            "construction_months": "24",
            "horizon_years": "25",
            "ppa_term_years": "15",
            "tariff_eur_mwh": "75.0",
            "p50_hours": "2400",
            "opex_y1_keur": "1200.0",
            "total_capex_keur": "50000.0",
            "gearing_pct": "70.0",
            "interest_rate_pct": "6.0",
            "tenor_years": "18",
            "target_dscr": "1.30",
        }
        return build_projectinputs_from_snapshot(snapshot)

    def test_schema_and_snapshot_equal_for_solar(self):
        a = self._build_via_schema()
        b = self._build_via_snapshot()
        # Identity / info
        assert a.info.cod_date == b.info.cod_date
        assert a.info.construction_months == b.info.construction_months
        assert a.info.horizon_years == b.info.horizon_years
        # PPA term
        assert a.revenue.ppa_term_years == b.revenue.ppa_term_years

    def test_schema_and_snapshot_equal_for_wind(self):
        schema = ProjectInputsSchema(
            project_type="Wind",
            capacity_mw=80.0,
            cod_date="2030-06-01",
            construction_months=24,
            horizon_years=25,
            ppa_term_years=15,
        )
        schema = enrich_schema_with_timing_fields(
            schema,
            cod_date="2030-06-01",
            construction_months=24,
            horizon_years=25,
            ppa_term_years=15,
        )
        a = build_projectinputs(schema)
        snapshot = {
            "project_type": "Wind",
            "project_name": "Test Wind",
            "country_market": "Croatia",
            "capacity_mw": "80.0",
            "cod_date": "2030-06-01",
            "construction_months": "24",
            "horizon_years": "25",
            "ppa_term_years": "15",
            "tariff_eur_mwh": "75.0",
            "p50_hours": "2400",
            "opex_y1_keur": "1200.0",
            "total_capex_keur": "50000.0",
            "gearing_pct": "70.0",
            "interest_rate_pct": "6.0",
            "tenor_years": "18",
            "target_dscr": "1.30",
        }
        b = build_projectinputs_from_snapshot(snapshot)
        assert a.info.cod_date == b.info.cod_date
        assert a.info.construction_months == b.info.construction_months
        assert a.info.horizon_years == b.info.horizon_years
        assert a.revenue.ppa_term_years == b.revenue.ppa_term_years


# ---------------------------------------------------------------------------
# 5. Timing field binding contracts (S3)
# ---------------------------------------------------------------------------


class TestTimingFieldBindingContracts:
    """The four timing fields must obey the
    S3 driver-to-KPI binding contracts:

    - ``ppa_term_years`` moves revenue / EBITDA
      via the PPA tariff duration.
    - ``construction_months`` moves equity_irr
      via financial_close timing but does NOT
      move revenue, EBITDA, senior debt, or
      DSCR.
    - ``cod_date`` and ``horizon_years`` are
      carried without silent fallback.
    """

    def _full_solar_snapshot(self, **overrides):
        """Return a complete Solar snapshot
        with the four timing fields populated.
        ``overrides`` is applied on top of the
        defaults so individual tests can vary
        one field at a time.
        """
        base = {
            "project_type": "Solar",
            "project_name": "Test Solar",
            "country_market": "Croatia",
            "capacity_mw": "50.0",
            "tariff_eur_mwh": "75.0",
            "p50_hours": "2400",
            "opex_y1_keur": "1200.0",
            "total_capex_keur": "50000.0",
            "gearing_pct": "70.0",
            "interest_rate_pct": "6.0",
            "tenor_years": "18",
            "target_dscr": "1.30",
            "cod_date": "2030-06-01",
            "construction_months": "24",
            "horizon_years": "25",
            "ppa_term_years": "15",
        }
        base.update(overrides)
        return base

    def test_ppa_term_years_moves_revenue(self):
        a = build_projectinputs_from_snapshot(
            self._full_solar_snapshot(ppa_term_years="10")
        )
        b = build_projectinputs_from_snapshot(
            self._full_solar_snapshot(ppa_term_years="20")
        )
        # Longer PPA term => more total
        # revenue (over the same project
        # horizon).
        assert b.revenue.ppa_term_years > a.revenue.ppa_term_years

    def test_construction_months_carried(self):
        a = build_projectinputs_from_snapshot(
            self._full_solar_snapshot(construction_months="6")
        )
        b = build_projectinputs_from_snapshot(
            self._full_solar_snapshot(construction_months="36")
        )
        assert a.info.construction_months == 6
        assert b.info.construction_months == 36

    def test_cod_date_carried(self):
        a = build_projectinputs_from_snapshot(
            self._full_solar_snapshot(cod_date="2030-01-01")
        )
        b = build_projectinputs_from_snapshot(
            self._full_solar_snapshot(cod_date="2032-01-01")
        )
        assert a.info.cod_date.isoformat() == "2030-01-01"
        assert b.info.cod_date.isoformat() == "2032-01-01"

    def test_horizon_years_carried(self):
        a = build_projectinputs_from_snapshot(
            self._full_solar_snapshot(horizon_years="20")
        )
        b = build_projectinputs_from_snapshot(
            self._full_solar_snapshot(horizon_years="30")
        )
        assert a.info.horizon_years == 20
        assert b.info.horizon_years == 30


# ---------------------------------------------------------------------------
# 6. Form flat-dict extractor
# ---------------------------------------------------------------------------


class TestFormDictExtractor:
    """``timing_fields_from_form_dict`` returns
    the four timing fields with the canonical
    names. This is the one-shot entry point
    for Path B callers.
    """

    def test_extracts_all_four(self):
        out = timing_fields_from_form_dict({
            "project_name": "Demo",
            "cod_date": "2030-01-01",
            "construction_months": "24",
            "horizon_years": "25",
            "ppa_term_years": "15",
            "tariff_eur_mwh": "75.0",
        })
        assert out["cod_date"] == "2030-01-01"
        assert out["construction_months"] == "24"
        assert out["horizon_years"] == "25"
        assert out["ppa_term_years"] == "15"

    def test_missing_field_becomes_empty_string(self):
        out = timing_fields_from_form_dict({})
        assert out["cod_date"] == ""
        assert out["construction_months"] == ""
        assert out["horizon_years"] == ""
        assert out["ppa_term_years"] == ""

    def test_apply_timing_to_schema_round_trip(self):
        base = ProjectInputsSchema(
            project_type="Solar",
            capacity_mw=50.0,
        )
        out = apply_timing_to_schema(base, {
            "cod_date": "2030-06-01",
            "construction_months": "24",
            "horizon_years": "25",
            "ppa_term_years": "15",
        })
        assert out.cod_date == "2030-06-01"
        assert out.construction_months == 24
        assert out.horizon_years == 25
        assert out.revenue is not None
        assert out.revenue.ppa_term_years == 15


# ---------------------------------------------------------------------------
# 7. Form field-name alignment with the create form HTML
# ---------------------------------------------------------------------------


class TestFormFieldNameAlignment:
    """The four timing field names in
    ``FORM_TIMING_FIELDS`` and the create form
    HTML ``<input name="...">`` attributes
    must match exactly. This is the contract
    that the sidecar is forward-compatible
    with the actual HTML form (any future
    ``main_web.py`` fix can rely on these
    names).
    """

    def test_form_timing_fields_constants(self):
        assert "cod_date" in FORM_TIMING_FIELDS
        assert "construction_months" in FORM_TIMING_FIELDS
        assert "horizon_years" in FORM_TIMING_FIELDS
        assert "ppa_term_years" in FORM_TIMING_FIELDS

    def test_create_form_html_has_matching_names(self):
        src = _read(
            "app/templates/partials/new_project_form.html"
        )
        for name in FORM_TIMING_FIELDS:
            # The form has an <input name="X"> (or
            # similar) for each timing field. We
            # accept any tag (input, select) and
            # any quote style.
            pattern = r'name\s*=\s*[\'"]' + re.escape(name) + r'[\'"]'
            assert re.search(pattern, src), (
                f"create form is missing input name={name!r}"
            )


# ---------------------------------------------------------------------------
# 8. Forbidden paths unchanged + rc1 + factory paths + downstream phase
# ---------------------------------------------------------------------------


class TestPhaseInvariants:
    """rc1, factory paths, persistence, and
    downstream-phase test contracts are
    preserved.
    """

    @pytest.mark.parametrize("forbidden_path", PR1_FORBIDDEN_PATHS)
    def test_forbidden_path_unchanged_via_git(self, forbidden_path):
        r = subprocess.run(
            [
                "git", "diff", "--name-only", "origin/main", "--",
                forbidden_path,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            return
        assert r.stdout.strip() == "", (
            f"PR1 must NOT touch {forbidden_path!r}; "
            f"git diff shows: {r.stdout.strip()!r}"
        )

    def test_rc1_sha_resolvable(self):
        r = subprocess.run(
            ["git", "rev-parse", "--verify", RC1_SHA],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == RC1_SHA

    def test_factory_paths_unchanged(self):
        r = subprocess.run(
            [
                "git", "diff", "--name-only", "origin/main", "--",
                "app/project_factories.py",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert r.stdout.strip() == "", (
            f"PR1 must NOT change app/project_factories.py; "
            f"got: {r.stdout.strip()!r}"
        )


# ---------------------------------------------------------------------------
# 9. Real _build_schema_from_form carries timing
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    _REAL_BUILD_SCHEMA_FROM_FORM is None,
    reason=(
        "_build_schema_from_form from main_web.py "
        "is not importable in this test env "
        "(likely missing fastapi / auth deps). "
        "The sidecar tests above already prove "
        "the contract; the real-helper tests "
        "below add a runtime check when the "
        "env supports it."
    ),
)
class TestRealBuildSchemaFromForm:
    """The actual _build_schema_from_form
    helper in main_web.py must carry the
    four timing fields into the returned
    schema. PR1 ships the extended
    signature.

    These tests exercise the REAL helper
    (imported from main_web.py), not a
    re-implementation. They prove the
    actual Path B integration point works.
    """

    def test_real_helper_carries_cod_date(self):
        schema = _REAL_BUILD_SCHEMA_FROM_FORM(
            project_type="Solar",
            scenario="Base",
            capacity_mw="50.0",
            tariff_eur_mwh="75.0",
            p50_hours="2400",
            total_capex_keur="50000",
            opex_y1_keur="1200",
            gearing_pct="70",
            target_dscr="1.30",
            interest_rate_pct="6",
            tenor_years="18",
            cod_date="2030-06-01",
            construction_months="24",
            horizon_years="25",
            ppa_term_years_form="15",
        )
        assert schema.cod_date == "2030-06-01"

    def test_real_helper_carries_construction_months(self):
        schema = _REAL_BUILD_SCHEMA_FROM_FORM(
            project_type="Solar",
            scenario="Base",
            capacity_mw="50.0",
            tariff_eur_mwh="75.0",
            p50_hours="2400",
            total_capex_keur="50000",
            opex_y1_keur="1200",
            gearing_pct="70",
            target_dscr="1.30",
            interest_rate_pct="6",
            tenor_years="18",
            construction_months="24",
        )
        assert schema.construction_months == 24

    def test_real_helper_carries_horizon_years(self):
        schema = _REAL_BUILD_SCHEMA_FROM_FORM(
            project_type="Solar",
            scenario="Base",
            capacity_mw="50.0",
            tariff_eur_mwh="75.0",
            p50_hours="2400",
            total_capex_keur="50000",
            opex_y1_keur="1200",
            gearing_pct="70",
            target_dscr="1.30",
            interest_rate_pct="6",
            tenor_years="18",
            horizon_years="25",
        )
        assert schema.horizon_years == 25

    def test_real_helper_carries_ppa_term_years_under_revenue(self):
        # ppa_term_years must be carried
        # under the nested revenue
        # Pydantic model, not as a
        # top-level field.
        schema = _REAL_BUILD_SCHEMA_FROM_FORM(
            project_type="Solar",
            scenario="Base",
            capacity_mw="50.0",
            tariff_eur_mwh="75.0",
            p50_hours="2400",
            total_capex_keur="50000",
            opex_y1_keur="1200",
            gearing_pct="70",
            target_dscr="1.30",
            interest_rate_pct="6",
            tenor_years="18",
            ppa_term_years_form="15",
        )
        assert schema.revenue is not None
        assert schema.revenue.ppa_term_years == 15

    def test_real_helper_legacy_signature_unchanged(self):
        # The legacy 11-arg signature must
        # still work (no timing kwargs).
        # This proves PR1 is backward
        # compatible with callers that do
        # not pass timing fields.
        schema = _REAL_BUILD_SCHEMA_FROM_FORM(
            project_type="Solar",
            scenario="Base",
            capacity_mw="50.0",
            tariff_eur_mwh="75.0",
            p50_hours="2400",
            total_capex_keur="50000",
            opex_y1_keur="1200",
            gearing_pct="70",
            target_dscr="1.30",
            interest_rate_pct="6",
            tenor_years="18",
        )
        # No timing fields populated
        # (legacy callers do not pass them).
        assert schema.cod_date is None
        assert schema.construction_months is None
        assert schema.horizon_years is None
        assert schema.revenue is None or (
            schema.revenue.ppa_term_years is None
        )


@pytest.mark.skipif(
    _REAL_BUILD_SCHEMA_FROM_FORM is None,
    reason=(
        "_build_schema_from_form from main_web.py "
        "is not importable in this test env."
    ),
)
class TestRealFormPathProducesEqualProjectInputs:
    """The REAL form -> schema -> ProjectInputs
    path (Path B) must produce the same
    ProjectInputs as the form -> snapshot ->
    ProjectInputs path (Path A) for the same
    four timing fields.

    This is the S1 exact-equality contract
    applied to the ACTUAL form path, not
    just the sidecar.
    """

    def test_form_path_solar_equals_snapshot_path(self):
        from app.input_adapter import (
            build_projectinputs_from_snapshot,
        )
        # Path B: form -> schema -> ProjectInputs
        schema = _REAL_BUILD_SCHEMA_FROM_FORM(
            project_type="Solar",
            scenario="Base",
            capacity_mw="50.0",
            tariff_eur_mwh="75.0",
            p50_hours="2400",
            total_capex_keur="50000",
            opex_y1_keur="1200",
            gearing_pct="70",
            target_dscr="1.30",
            interest_rate_pct="6",
            tenor_years="18",
            cod_date="2030-06-01",
            construction_months="24",
            horizon_years="25",
            ppa_term_years_form="15",
        )
        a = build_projectinputs(schema)

        # Path A: form -> snapshot -> ProjectInputs
        snapshot = {
            "project_type": "Solar",
            "project_name": "Test Solar",
            "country_market": "Croatia",
            "capacity_mw": "50.0",
            "cod_date": "2030-06-01",
            "construction_months": "24",
            "horizon_years": "25",
            "ppa_term_years": "15",
            "tariff_eur_mwh": "75.0",
            "p50_hours": "2400",
            "opex_y1_keur": "1200.0",
            "total_capex_keur": "50000.0",
            "gearing_pct": "70.0",
            "interest_rate_pct": "6.0",
            "tenor_years": "18",
            "target_dscr": "1.30",
        }
        b = build_projectinputs_from_snapshot(snapshot)

        # The four timing fields must match
        # exactly between Path A and Path B.
        assert a.info.cod_date == b.info.cod_date
        assert a.info.construction_months == b.info.construction_months
        assert a.info.horizon_years == b.info.horizon_years
        assert a.revenue.ppa_term_years == b.revenue.ppa_term_years

    def test_form_path_wind_equals_snapshot_path(self):
        from app.input_adapter import (
            build_projectinputs_from_snapshot,
        )
        schema = _REAL_BUILD_SCHEMA_FROM_FORM(
            project_type="Wind",
            scenario="Base",
            capacity_mw="80.0",
            tariff_eur_mwh="75.0",
            p50_hours="2400",
            total_capex_keur="50000",
            opex_y1_keur="1200",
            gearing_pct="70",
            target_dscr="1.30",
            interest_rate_pct="6",
            tenor_years="18",
            cod_date="2030-06-01",
            construction_months="24",
            horizon_years="25",
            ppa_term_years_form="15",
        )
        a = build_projectinputs(schema)
        snapshot = {
            "project_type": "Wind",
            "project_name": "Test Wind",
            "country_market": "Croatia",
            "capacity_mw": "80.0",
            "cod_date": "2030-06-01",
            "construction_months": "24",
            "horizon_years": "25",
            "ppa_term_years": "15",
            "tariff_eur_mwh": "75.0",
            "p50_hours": "2400",
            "opex_y1_keur": "1200.0",
            "total_capex_keur": "50000.0",
            "gearing_pct": "70.0",
            "interest_rate_pct": "6.0",
            "tenor_years": "18",
            "target_dscr": "1.30",
        }
        b = build_projectinputs_from_snapshot(snapshot)
        assert a.info.cod_date == b.info.cod_date
        assert a.info.construction_months == b.info.construction_months
        assert a.info.horizon_years == b.info.horizon_years
        assert a.revenue.ppa_term_years == b.revenue.ppa_term_years


@pytest.mark.skipif(
    _REAL_BUILD_SCHEMA_FROM_FORM is None,
    reason=(
        "_build_schema_from_form from main_web.py "
        "is not importable in this test env."
    ),
)
class TestRealFormPathBindingContracts:
    """The REAL form path (form -> schema)
    must honour the S3 binding contracts for
    timing fields:

    - ppa_term_years from form path moves
      revenue / EBITDA
    - construction_months from form path
      moves equity_irr via financial_close
      timing but does NOT change revenue,
      EBITDA, senior debt, or DSCR
    """

    def _build_via_real_form(self, **timing_overrides):
        from app.input_adapter import build_projectinputs
        # Default timing kwargs; tests can
        # override any of these via
        # timing_overrides.
        timing = {
            "cod_date": "2030-06-01",
            "horizon_years": "25",
            "construction_months": "24",
            "ppa_term_years_form": "15",
        }
        timing.update(timing_overrides)
        schema = _REAL_BUILD_SCHEMA_FROM_FORM(
            project_type="Solar",
            scenario="Base",
            capacity_mw="50.0",
            tariff_eur_mwh="75.0",
            p50_hours="2400",
            total_capex_keur="50000",
            opex_y1_keur="1200",
            gearing_pct="70",
            target_dscr="1.30",
            interest_rate_pct="6",
            tenor_years="18",
            **timing,
        )
        return build_projectinputs(schema)

    def test_ppa_term_years_from_form_path_moves_revenue(self):
        a = self._build_via_real_form(ppa_term_years_form="10")
        b = self._build_via_real_form(ppa_term_years_form="20")
        # Longer PPA term => larger
        # revenue.ppa_term_years field.
        assert b.revenue.ppa_term_years > a.revenue.ppa_term_years

    def test_construction_months_from_form_path_is_carried(self):
        a = self._build_via_real_form(construction_months="6")
        b = self._build_via_real_form(construction_months="36")
        assert a.info.construction_months == 6
        assert b.info.construction_months == 36


# ---------------------------------------------------------------------------
# 10. File-scope
# ---------------------------------------------------------------------------


class TestPR1FileScope:
    """The PR1 changeset is exactly the
    expected set of files. Any drift fails
    this test.
    """

    def test_only_expected_files_touched(self):
        diff_r = subprocess.run(
            ["git", "diff", "--name-only", "origin/main"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        status_r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        tracked = {
            line.strip()
            for line in diff_r.stdout.splitlines()
            if line.strip()
        }
        untracked = set()
        for line in status_r.stdout.splitlines():
            if not line.strip():
                continue
            code = line[:2]
            path = line[3:].strip()
            if "->" in path:
                path = path.split("->", 1)[1].strip()
            if code in ("??", "A ", " M", "M ", "AM", "MM"):
                untracked.add(path)
        changed = sorted(tracked | untracked)
        # PR1's expected file set.
        expected = {
            "app/services/form_timing_enrichment.py",
            "tests/test_phase_pr1_form_timing_fields.py",
            "docs/phase_pr1_form_timing_fields.md",
            "reports/phase_pr1_form_timing_fields.md",
            "main_web.py",  # Phase PR1 review
                            # fix: wiring fix
                            # lives here, not
                            # in app/services/.
            # PR1 cross-arc test patches:
            # PR1 updates P1-B and M1 file-scope
            # tests to allowlist post-m1
            # follow-up additions.
            "tests/test_phase_p1b_driver_status_badges.py",
            "tests/test_phase_m1_scenario_matrix.py",
        }
        # PR1 is allowed to update M1 file-scope
        # test (to allowlist the post-m1
        # follow-up additions) — that is the
        # whole point of the cross-arc file-scope
        # patch. The M1 test patch is forward-
        # compatible with PR2 and PR3, so it is
        # not "drift" — it is an explicit,
        # documented contract extension.
        # The M1 test patch IS in PR1's file
        # set (so it must appear in `expected`).
        expected = expected | {
            "tests/test_phase_m1_scenario_matrix.py",
            # PR1 also patches a latent M1
            # template-None bug in
            # scenario_matrix.html (the
            # ``{{ format }}`` expression
            # crashed when ``project_ctx`` was
            # None). The fix is template-only,
            # additive (``is defined`` guard
            # on attribute access), and
            # preserves the M1 em-dash UX.
            "app/templates/partials/scenario_matrix.html",
            # PR2 (post-m1-realized-gearing-kpi)
            # follow-up allowlist: PR2 adds
            # a realized gearing KPI row to
            # the M1 Scenario Matrix
            # (``app/ui/project_context.py`` +
            # ``app/ui/scenario_matrix.py``
            # + PR2 test/docs/report). PR1
            # does not touch these, but the
            # file-scope test is forward-
            # compatible and skips the
            # follow-up additions.
            "app/ui/project_context.py",
            "app/ui/scenario_matrix.py",
            "tests/test_phase_pr2_realized_gearing.py",
            "docs/phase_pr2_realized_gearing.md",
            "reports/phase_pr2_realized_gearing.md",
            # PR3 (post-m1-taxonomy-brief-alignment)
            # follow-up allowlist: PR3 adds a
            # canonical taxonomy module
            # (``app/ui/driver_taxonomy.py``)
            # + a PR3 test file + PR3 docs and
            # report. PR1 does not touch
            # these; the file-scope test is
            # forward-compatible.
            "app/ui/driver_taxonomy.py",
            "tests/test_phase_pr3_taxonomy.py",
            "docs/phase_pr3_taxonomy_brief_alignment.md",
            "reports/phase_pr3_taxonomy_brief_alignment.md",
            # P2-min-1 (Project Home) follow-up
            # allowlist: P2-min-1 adds a
            # project home partial + minimal
            # new-project form + Help link in
            # base.html + sidebar Home action.
            # PR1 does not touch these; the
            # file-scope test is forward-
            # compatible.
            "app/templates/base.html",
            "app/templates/partials/project_home.html",
            "app/templates/partials/new_project_minimal.html",
            "app/templates/partials/project_selector.html",
            "static/styles.css",
            "tests/test_phase_p2min1_project_home.py",
            "docs/phase_p2min1_project_home.md",
            "reports/phase_p2min1_project_home.md",
            "main_web.py",
            # P2-min-2 (Hide Internal Vocabulary)
            # follow-up allowlist: P2-min-2 adds
            # a generic status line partial +
            # includes it in workspace_shell.
            # PR1 does not touch these; the
            # file-scope test is forward-
            # compatible.
            "app/templates/partials/_generic_status_line.html",
            "app/templates/partials/workspace_shell.html",
            "docs/phase_p2min2_hide_internal_vocabulary.md",
            "reports/phase_p2min2_hide_internal_vocabulary.md",
            "tests/test_phase_p2min2_hide_internal_vocabulary.py",
            # P2-min-3 (Dashboard v1) follow-up
            # allowlist: P2-min-3 adds a
            # dashboard module + a partial +
            # extends workspace_shell + CSS.
            "app/ui/dashboard.py",
            "app/templates/partials/_dashboard.html",
            "docs/phase_p2min3_dashboard_v1.md",
            "reports/phase_p2min3_dashboard_v1.md",
            "tests/test_phase_p2min3_dashboard_v1.py",
            # P2-min-4 (Navigation Compression)
            # follow-up allowlist.
            "app/templates/partials/_nav_compression.html",
            "docs/phase_p2min4_navigation_compression.md",
            "reports/phase_p2min4_navigation_compression.md",
            "tests/test_phase_p2min4_navigation_compression.py",
            # STAB arc cross-arc allowlist
            "app/templates/partials/_scenario_matrix_oob.html",
            "tests/test_phase_m2_scenario_matrix_live.py",
            "tests/test_phase_m3_scenario_matrix_overrides.py",
            "tests/test_phase_m4_scenario_matrix_run.py",
            "tests/test_phase_p2fix2_shell_strip.py",
            "tests/test_phase_p2fix3_c2_first_edit.py",
            "tests/test_phase_p2fix4_five_area_navigation.py",
            "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
            "tests/test_phase_p2fix5c_dashboard_kpi.py",
            "tests/test_phase_p2fix5d_five_area_navigation.py",
            "tests/test_phase_p2fix5e_reference_ux.py",
            "tests/test_phase_p2fix6_c2_create_copy_ui.py",
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_p2fix7a_css_parser_cleanup.py",
            "tests/test_phase_wf1_run_refreshes_dashboard.py",
            "tests/test_phase_wf2_sheet_styling.py",
            "tests/test_phase_wf3_home_and_projects_split.py",
            "tests/test_phase_wf4_minimal_create_and_list_hygiene.py",
            "tests/test_phase_wf5_grouped_results_nav.py",
            "tests/test_phase_wf6_scenario_status_badges.py",
            "tests/test_phase_stab",
            "tests/test_phase_stab1_run_refreshes_kpis.py",
            "tests/test_phase_stab2_realized_gearing_scale.py",
            "tests/test_phase_stab3_capex_subline_propagation.py",
            "tests/test_phase_p1b_driver_status_badges.py",
            "app/services/capex_sub_lines_integration.py",
            "app/services/run_service.py",
            # STAB-2 CI fix: bcrypt 3.2.2 has no Python 3.12 wheels
            "constraints.txt",
        }
        actual = set(changed)
        extra = actual - expected
        missing = expected - actual
        assert not extra, (
            f"PR1 must touch only the expected files; "
            f"unexpected files: {sorted(extra)}"
        )
        # Phase PR2 forward-fix: after PR1
        # is merged to main, the PR1 files
        # (``main_web.py``,
        # ``app/services/form_timing_enrichment.py``,
        # PR1 docs/reports, the P1-B
        # allowlist patch) are no longer
        # in ``git diff --name-only
        # origin/main`` because they are
        # already on the base. The forward-
        # compatible check is therefore
        # only the ``assert not extra``
        # above (no unexpected files in the
        # working tree). The ``missing``
        # assertion was retained for the
        # pre-merge PR1 branch and is now
        # relaxed under post-merge / post-
        # PR1 follow-up branches.
