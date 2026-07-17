"""
finco_parity — Finco One parity harness and legacy-engine characterization.

Phase 1B (current): Legacy Baseline Materialization and Drift Comparison
Phase 1A: Legacy Characterization Snapshot Foundation
---------------------------------------------------------------
Captures deterministic, normalized, offline snapshots of the current legacy
waterfall engine for four baseline projects.  The snapshots are the reference
baseline against which the extracted engine (Phase 2+) will be compared.

Modules added in Phase 1B:
    canonical        — Canonical UTF-8 JSON serialization (sort_keys, indent=2, trailing LF)
    comparison       — Structural/numeric snapshot comparison (IDENTICAL/STRUCTURAL_DRIFT/…)
    generate_baselines — Baseline generation CLI (python -m finco_parity.generate_baselines)
    manifest         — Manifest loading and artifact integrity validation

Subpackages added in Phase 1B:
    baselines/snapshots/  — Committed canonical JSON baseline artifacts

Modules added in Phase 1A:
    schema          — Versioned snapshot schema, UNAVAILABLE sentinel, validate_snapshot()
    normalization   — Deterministic normalization (None ≠ 0.0, no timestamps)
    legacy_snapshot — Offline CLI runner (python -m finco_parity.legacy_snapshot)

Subpackages added in Phase 1A:
    baselines/      — Machine-readable baseline manifest (manifest.json)

Pre-existing subpackages (populated during V2-4+):
    fixtures    — TUHO Wind 1 and Oborovo Solar input fixtures
    golden      — Expected output baselines (from Finco1-RC2 reference run)
    regression  — Parametrised regression tests comparing extracted engine
                  output against golden baselines

Import boundary
---------------
This package must NOT be imported by production code (app.*, domain.*, main_*).
It imports from finco_core and (at runtime in legacy_snapshot) from app.* for
engine execution.  All imports of app.* are deferred to function scope.

Parity gate: every V2-3+ milestone PR must pass all tests in this package
before merge is permitted.
"""
