# Phase B4 — Single Production Engine / Legacy Excision

## Before B4

Clean-only normal routing existed (B1–B3: Generic Solar/Wind, Oborovo and
TUHO all promoted to the clean G2C authority), but explicit legacy financial
execution seams still lived inside production/app namespaces:

- `app.api.project_runner.run_project_legacy()` (`force_legacy=True` branch,
  legacy demo funnel + legacy sponsor engine + legacy FS assembly);
- `app.services.production_waterfall_seam.execute_calibration_waterfall()`
  (WaterfallRunner execution inside a production service module);
- `app.ui_runner.run_demo_project()` — legacy waterfall funnel with
  `legacy_calibration=True` default factory selection — importable from
  production entry points (vestigial imports in main_web / CLI / Streamlit
  / download deps);
- `main_web` FS-compare route executed WaterfallRunner directly for
  non-promoted user snapshots; three dead WaterfallRunner imports;
- production error messages advertised legacy/calibration entry points;
- `_run_sponsor_engine` (hardcoded TUHO/Oborovo capital structures) lived in
  the production run module.

## After B4 — one production financial engine

`typed ProjectInputs → clean production authority → one clean G2C calculation → presentation/output adapters`

is the only supported production calculation path.

- **Production entry point:** `app.api.project_runner.run_project()` (and the
  shared seam `app.services.production_waterfall_seam.execute_production_waterfall /
  execute_production_demo` consuming the one classifier
  `classify_production_authority` and the one clean runner
  `run_clean_production` →
  `financial_engine.shareholder_waterfall.run_project_shareholder_waterfall_model`,
  exactly once per run).
- **Clean run path ID / provenance:** every production payload carries
  `runtime_authority` = `clean_g2c` with `classification`, `reason_code`,
  `calculation_count`, `clean_entry_point`, engine fingerprint metadata and
  the explicit `unavailable_fields` manifest (Project IRR / NPV / LLCR /
  PLCR / FS assembly remain truthful NOT_AVAILABLE — never fabricated).
- **Blocked behavior:** blocked / unregistered / Portfolio inputs raise the
  typed `CleanNotReadyError` (machine-readable reason,
  `calculation_count = 0`). There is NO fallback engine — no flag, no env
  var, no query/API parameter, no exception path can reach a legacy engine.
- **Unsupported project policy:** KUPI remains evidence/out-of-sample scope;
  Portfolio remains an offline experimental composition, not a production
  financial authority.

## OFFLINE_VALIDATION_ONLY

Historical legacy/calibration code retained for parity tests,
source-workbook validation, offline diagnostics and characterization
evidence — all unreachable from production entry points:

- `app/ui_runner.py` (legacy demo funnel; banner-marked; no production
  importer remains — `DemoResult` moved to `app/demo_result.py`);
- `app/waterfall_runner.py`, `app/waterfall_core.py` (legacy engine — only
  offline modules and tests import them);
- `app/validation_framework.py`, `app/sponsor_project_adapter.py`,
  `app/portfolio_runner.py`, `app/cache.py` (dormant/offline);
- `app/project_factories.py`: `create_default_oborovo_legacy_calibration()`
  and `create_default_tuho_wind1_legacy_calibration()` — classified
  OFFLINE-only factory data (no production router selects them; user-created
  projects cannot inherit them);
- `tests/helpers/offline_calibration.py` — the relocated pre-B4
  `run_project_legacy()` and `execute_calibration_waterfall()` seams;
- `tests/helpers/offline_sponsor_engine.py` — the relocated legacy sponsor
  engine bridge.

## Proof

- Static: `tests/test_phaseb4_single_production_engine.py` B4-D gate —
  module-level production import graph contains no legacy execution seam
  (`app.ui_runner`, `app.waterfall_runner`, `app.waterfall_core`,
  `app.validation_framework`, `app.sponsor_project_adapter`,
  `app.portfolio_runner`, `app.cache`, tests helpers are unreachable from
  all 18 production entry modules); AST call-scan proves no production
  service constructs WaterfallRunner or calls the legacy funnel/sponsor
  engine; token scan proves `run_project_legacy` / `force_legacy` /
  `execute_calibration_waterfall` do not appear in production code.
- Runtime: engine counters prove ONE clean calculation and ZERO legacy
  execution for all four supported projects across run/save/scenario/
  reporting/download/CLI seams; fail-closed inputs execute ZERO engines.
- Financial: B4-A..E KPI fingerprints bit-identical to B3 main
  (`bf71b21d`) for Solar / Wind / Oborovo / TUHO; no recalibration.


## Correction A — production authority metadata closure

- `_RUNTIME_AUTHORITY_BY_CLASSIFICATION`: every non-promoted classification
  now maps to `clean_not_ready` (NOT-EXECUTED). A production
  `AuthorityDecision` NEVER claims `legacy_waterfall_calibration` —
  classification and runtime execution are separate concepts; a non-promoted
  classification means "not registered for production execution; zero
  calculations", not "a legacy engine will serve this project".
- Stale routing language ("routed to the explicitly-classified legacy
  calibration runtime", "the legacy calibration runtime serves this
  project until then") replaced with truthful fail-closed wording.
- Runtime authority vocabulary: `clean_g2c` (supported production) ·
  `clean_not_ready` (non-promoted / blocked / unregistered — zero
  calculations) · `legacy_waterfall_offline_calibration` (offline
  historical evidence helper only — never a production runtime).

## Correction A — expanded financial non-regression evidence

`tests/fixtures/b4a_b3main_baseline.py` — DESCRIPTIVE_REGRESSION_EVIDENCE
snapshot generated from independently verified B3-main (`bf71b21d`) runtime
outputs via the clean G2C entry point. For Solar / Wind / Oborovo / TUHO it
freezes: revenue, OPEX, EBITDA, cash tax, Base CFADS, Bank CFADS, Senior
debt size / interest / principal / DS / terminal, SHL first-opening /
interest / principal / terminal, distributions, sponsor receipts — plus
full period-vector digests for Senior interest/principal/DS/closing and
SHL interest/principal/closing (Oborovo + TUHO). B4-I tests prove scalar
and period-vector identity. Regression evidence ONLY — never read by
runtime or financial code; no engine value was fitted to match it.


## Correction B — final semantic cleanup + complete financial freeze

- Remaining split-literal false claims removed from runtime details:
  BLOCKED_BY_TYPED_INPUT_GAP ("The legacy calibration runtime serves this
  project until...") → "not registered for production execution until the
  required typed financing fields are configured and reviewed; production
  returns zero calculations; historical calibration evidence offline only".
  LEGACY_CALIBRATION_ONLY ("the project's accepted runtime contract is the
  frozen-schedule Excel calibration stack") → "snapshot contains historical
  frozen-calibration markers and is not registered for production
  execution; clean_not_ready; offline evidence only".
- H5 strengthened to an AST-based scan over EVALUATED string constants
  (adjacent literals concatenate — catches split-string claims a raw
  substring scan misses). New H6 instantiates all three non-promoted
  classifications and asserts every runtime detail is fail-closed
  consistent (not-registered / zero-calculations / offline-only).
- Baseline expanded to the complete freeze matrix (29 scalar metrics per
  project): operating, tax/CFADS, Senior, min/avg DSCR, binding constraint,
  DSCR/gearing capacity, total project uses, typed construction/VAT
  financing inputs (authoritative values incl. zeros), SHL, distributions,
  sponsor receipts + period-vector digests. Regenerated at B3 main
  bf71b21d in a clean git worktree; provenance documented in the fixture.
