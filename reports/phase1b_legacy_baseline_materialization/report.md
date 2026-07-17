# Phase 1B — Legacy Baseline Materialization and Drift Comparison

## Overview

Phase 1B turns the Phase 1A characterization snapshot framework into a
deterministic, committed legacy-oracle baseline package.  It generates
canonical JSON artifacts for every Phase 1A manifest entry, binds each
artifact to its manifest identity, and provides deterministic regeneration
and drift detection.

---

## Provenance

| Field | Value |
|---|---|
| Base SHA | `8b13a53805ea2e1e84144ccad1f2484e16fa8592` |
| Head SHA | (set at merge) |
| Base branch | `main` |
| Feature branch | `phase1b-legacy-baseline-materialization` |
| PR | Draft — do not merge until CI is green |

---

## Baseline IDs

| baseline_id | Display name | Periods | Technology |
|---|---|---|---|
| `tuho` | TUHO Wind 1 | 61 | wind |
| `oborovo` | Oborovo Solar PV | 60 | solar |
| `generic_solar` | Generic Solar (Test 1) | 41 | solar |
| `generic_wind` | Generic Wind (Test 2) | 51 | wind |

---

## Artifact Paths and Hashes

| baseline_id | Path | SHA-256 |
|---|---|---|
| `tuho` | `finco_parity/baselines/snapshots/tuho.json` | `9d5cb01a5f84aae61ca6b0dfbc4365ff249645a96d7a93616b6039088dee83e7` |
| `oborovo` | `finco_parity/baselines/snapshots/oborovo.json` | `81f9942775b370e0ba973fac69091b19a093460794ee51848840f3c1d25370dd` |
| `generic_solar` | `finco_parity/baselines/snapshots/generic_solar.json` | `8eb03a9b5ec2f75976c461f828837c31f96c9611a367a468f2f6a051683fa3c4` |
| `generic_wind` | `finco_parity/baselines/snapshots/generic_wind.json` | `fc0c1c8b3ba9814313cecdbc856c7860ea8336c0549d1faf880c4ec36564beb9` |

---

## Capture Path

```
python -m finco_parity.generate_baselines
```

Internally: `finco_parity.legacy_snapshot.capture_snapshot(baseline_id)` →
`app.ui_runner.run_demo_project(project_type)` →
WaterfallRunner → `run_waterfall_v3_core` →
`finco_parity.normalization.normalize_snapshot()` →
`finco_parity.schema.validate_snapshot()` →
`finco_parity.canonical.write_canonical_json()`

No production startup path, route, or persistence layer is involved.

---

## Canonical Serialization Rules

| Rule | Value |
|---|---|
| Encoding | UTF-8 |
| Indent | 2 spaces |
| sort_keys | True |
| ensure_ascii | False |
| allow_nan | False |
| EOF | Single trailing LF (`\n`) |

Prohibited content: timestamps generated at capture time, machine-specific
paths, hostnames, usernames, random UUIDs, memory addresses, unordered
mappings, Python repr output, NaN or infinity, environment-dependent values.

Two clean generations from the same commit produce byte-identical files
(verified: SHA-256 match across two independent generations for all four
baselines).

---

## Comparison Classifications

| Classification | Trigger |
|---|---|
| `IDENTICAL` | No differences |
| `SCHEMA_DRIFT` | `schema_version` changed |
| `PROVENANCE_DRIFT` | `baseline_id`, `engine_designation`, `baseline_commit_sha`, `run_path_id`, or `input_source_id` changed |
| `STRUCTURAL_DRIFT` | Missing/extra key; list length changed; type changed |
| `AVAILABILITY_DRIFT` | Populated ↔ None transition; `unavailable_fields` or `unavailable_sections` changed |
| `VALUE_DRIFT` | Numeric, string, or bool value changed |

Severity (most to least): SCHEMA_DRIFT > PROVENANCE_DRIFT > STRUCTURAL_DRIFT > AVAILABILITY_DRIFT > VALUE_DRIFT.

All differences are accumulated; the first does not suppress the rest.
Differences are sorted deterministically by JSON path.

---

## Exact Comparison Policy

- Strings: exact
- Booleans: exact
- Integers: exact
- None: exact
- List lengths and ordering: exact
- Floats: exact serialized value comparison (IEEE-754 `==`)

Default tolerance is zero (`Tolerance(absolute=0.0, relative=0.0)`).

A `Tolerance` object may be supplied explicitly for diagnostic use only.
The CI guardrail (`--check`) always uses zero tolerance.
No tolerance configuration is stored in production code.
No current difference is approved through a tolerance allowlist in this PR.

---

## Production Isolation Proof

AST scan of `app/`, `domain/`, `finco_core/`, `main_web.py`, `main_api.py`
confirms:

- No production file imports `finco_parity` or any of its submodules.
- No production file contains references to `baselines/snapshots`, `generate_baselines`, `finco_parity.comparison`, `finco_parity.canonical`, or `finco_parity.manifest`.
- Importing `finco_parity.*` at module level does not execute any engine code.
- `--check` mode does not write to committed artifact paths.

Test: `tests/test_phase1b_production_isolation.py`

---

## CI Command

```bash
python -m finco_parity.generate_baselines --check
```

Exit codes:
- `0` — all baselines match committed artifacts
- `1` — generation/normalization/validation failure
- `3` — drift detected
- `4` — manifest integrity failure

Workflow: `.github/workflows/phase1b_baseline_check.yml`
Triggers on: pull requests to `main` with changes in `finco_parity/**`, baseline files, Phase 1A/1B tests.
Permissions: `contents: read` (read-only).

---

## Test Results

```
455 passed in 10.45s
```

| File | Tests |
|---|---|
| `test_phase1a_parity_manifest.py` | 39 |
| `test_phase1a_parity_schema_normalization.py` | 135 |
| `test_phase1a_parity_runner.py` | 204 |
| `test_phase1b_baseline_generation.py` | 27 |
| `test_phase1b_baseline_integrity.py` | 9 |
| `test_phase1b_snapshot_comparison.py` | 27 |
| `test_phase1b_production_isolation.py` | 14 |

---

## Limitations

These artifacts characterize the current legacy implementation.
They are compatibility references, not evidence that the underlying
financial methodology is correct, complete or bankable.

The legacy engine remains an oracle for compatibility characterization only.
No financial correctness claim is made.  No audit, approval, or bankability
certification is implied.

---

## Phase 1C Remaining Decisions

1. Drift threshold policy for Phase 2 extraction comparison (tolerance object
   parameters, if any, and which baselines require exact vs. near-exact match).
2. Whether to add construction-period baselines if the engine is extended to
   produce them.
3. Whether to archive intermediate drift reports as CI artifacts (currently
   only console output).
4. Whether to add a `--verbose-diff` mode to `generate_baselines --check` that
   emits the full human-readable comparison report for each drifted baseline.
