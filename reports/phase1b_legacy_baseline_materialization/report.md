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
| Previous head (ba3c5c71) | corrected in this amendment |
| Branch | `phase1b-legacy-baseline-materialization` |
| PR | #891 — Draft, do not merge |

---

## Root cause of original red baseline workflow

The original `cmd_check()` auto-detected the current checkout SHA and embedded
it in every fresh snapshot as `baseline_commit_sha`.  The committed artifacts
contain the Phase 1A merge SHA (`8b13a538…`).  After the Phase 1B commit
advanced HEAD, every future `--check` run generated a snapshot with the new
HEAD SHA, causing `PROVENANCE_DRIFT` on `baseline_commit_sha` for all four
baselines.  This made the baseline workflow permanently red.

## Stable `baseline_commit_sha` policy

`baseline_commit_sha` identifies the **source commit represented by the
committed characterization baseline**.  It is fixed at generation time and
does **not** change when a later commit runs `--check`.  It is **not** the
transient SHA executing the current CI run.

In `cmd_check()`:
1. Load the committed artifact.
2. Read `baseline_commit_sha` from the committed artifact (fixed reference).
3. Pass that value explicitly to `capture_snapshot()`.
4. Compare only engine outputs — repository advancement is invisible.

---

## Required Manifest Entry Fields

Every manifest entry must supply these non-empty fields:

| Field | Description |
|---|---|
| `baseline_id` | Canonical identifier |
| `project_type_key` | Engine project type key |
| `project_code` | Project code |
| `scenario_identity` | Scenario (`Base` for all current entries) |
| `engine_designation` | Engine identifier |
| `schema_version` | Snapshot schema version |
| `baseline_commit_sha` | Source commit the baseline represents |
| `input_source_id` | Factory function (without `app.` prefix) |
| `capture_source` | Must equal `finco_parity.legacy_snapshot.capture_snapshot` |
| `run_path` | Run path (without `app.` prefix; matches `snapshot.run_path_id`) |
| `snapshot_path` | Declared artifact path (repo-relative) |
| `artifact_sha256` | 64 lowercase hex chars; must match artifact bytes |

---

## `snapshot_path` is Authoritative

Artifact paths are resolved from the **declared `snapshot_path`** in each
manifest entry (relative to the repository root).  They are **not** derived
from `SNAPSHOTS_DIR / f"{baseline_id}.json"`.

Validation rules:
- Relative paths only (absolute paths fail).
- `..` traversal is rejected.
- Resolved path must remain inside `finco_parity/baselines/snapshots/`.
- Duplicate normalized paths fail.
- Every declared artifact must exist.
- Every artifact must be referenced exactly once.
- Orphan JSON files fail.

---

## Baseline IDs

| baseline_id | Display name | Periods | Technology | baseline_commit_sha |
|---|---|---|---|---|
| `tuho` | TUHO Wind 1 | 61 | wind | `8b13a538…` |
| `oborovo` | Oborovo Solar PV | 60 | solar | `8b13a538…` |
| `generic_solar` | Generic Solar (Test 1) | 41 | solar | `8b13a538…` |
| `generic_wind` | Generic Wind (Test 2) | 51 | wind | `8b13a538…` |

---

## Artifact Paths and Hashes

| baseline_id | Path | SHA-256 |
|---|---|---|
| `tuho` | `finco_parity/baselines/snapshots/tuho.json` | `9d5cb01a5f84aae61ca6b0dfbc4365ff249645a96d7a93616b6039088dee83e7` |
| `oborovo` | `finco_parity/baselines/snapshots/oborovo.json` | `81f9942775b370e0ba973fac69091b19a093460794ee51848840f3c1d25370dd` |
| `generic_solar` | `finco_parity/baselines/snapshots/generic_solar.json` | `8eb03a9b5ec2f75976c461f828837c31f96c9611a367a468f2f6a051683fa3c4` |
| `generic_wind` | `finco_parity/baselines/snapshots/generic_wind.json` | `fc0c1c8b3ba9814313cecdbc856c7860ea8336c0549d1faf880c4ec36564beb9` |

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

Prohibited: timestamps, machine paths, hostnames, random UUIDs, NaN/infinity.

Byte-determinism verified: two independent generations produce bit-identical
files for all four baselines.

Canonical integrity check: committed artifact bytes must equal
`canonical_json_bytes(parsed_artifact)`.  A manually reformatted artifact
fails even if its parsed JSON values are equal.

---

## Comparison Classifications

| Classification | Trigger |
|---|---|
| `IDENTICAL` | No differences |
| `SCHEMA_DRIFT` | `schema_version` changed |
| `PROVENANCE_DRIFT` | `baseline_id`, `engine_designation`, `baseline_commit_sha`, `run_path_id`, or `input_source_id` changed |
| `STRUCTURAL_DRIFT` | Missing/extra key; list length changed; **type changed** (incl. bool vs int vs float) |
| `AVAILABILITY_DRIFT` | Populated ↔ None transition; `unavailable_fields` or `unavailable_sections` changed |
| `VALUE_DRIFT` | Numeric, string, or bool value changed |

---

## Exact Type Comparison Policy

| Comparison | Result |
|---|---|
| `True` vs `1` | `STRUCTURAL_DRIFT` |
| `False` vs `0` | `STRUCTURAL_DRIFT` |
| `1` vs `1.0` | `STRUCTURAL_DRIFT` |
| `1.0` vs `1.0` | `IDENTICAL` |
| `1` vs `1` | `IDENTICAL` |
| `"1"` vs `1` | `STRUCTURAL_DRIFT` |

`bool` is checked before `int` because `bool` is a Python subclass of `int`.
Diagnostic `Tolerance` may only be applied after both values pass the type
policy; it never suppresses type mismatches.

---

## Exact Comparison Policy

- Default tolerance: zero (`Tolerance(absolute=0.0, relative=0.0)`)
- CI guardrail always uses zero tolerance
- No tolerance stored in production code
- No difference approved via allowlist in this PR

---

## Manifest Negative-Test Matrix

| Test | Expected error |
|---|---|
| Missing any required field | `ManifestIntegrityError` mentioning field name |
| Missing artifact file | `ManifestIntegrityError: missing` |
| Orphan artifact | `ManifestIntegrityError: Orphan` |
| Duplicate baseline_id | `ManifestIntegrityError: Duplicate` |
| Duplicate snapshot_path | `ManifestIntegrityError: Duplicate` |
| Wrong artifact_sha256 | `ManifestIntegrityError: mismatch` |
| sha256 wrong format | `ManifestIntegrityError: sha256/hex` |
| schema_version mismatch | `ManifestIntegrityError: schema_version` |
| baseline_id mismatch | `ManifestIntegrityError: baseline_id` |
| engine_designation mismatch | `ManifestIntegrityError: engine_designation` |
| baseline_commit_sha mismatch | `ManifestIntegrityError: baseline_commit_sha` |
| input_source_id mismatch | `ManifestIntegrityError: input_source_id` |
| run_path mismatch | `ManifestIntegrityError: run_path` |
| capture_source mismatch | `ManifestIntegrityError: capture_source` |
| Non-canonical artifact bytes | `ManifestIntegrityError: canonical` |
| Path traversal | `ManifestIntegrityError: Escapes/traversal` |
| Absolute snapshot_path | `ManifestIntegrityError: relative/absolute` |

---

## Drift Formatter Example

```
Baseline: tuho
Status:   VALUE_DRIFT
Differences: 1

1. returns.project_irr
   kind:     VALUE_DRIFT
   baseline: 0.089...
   current:  0.9999
   absolute delta: 0.910...
   relative delta: 1019.XXX%
```

---

## `--check` Result (committed state)

```
python -m finco_parity.generate_baselines --check --quiet
exit: 0
```

All 4 baselines match committed artifacts.

---

## Production Isolation Proof

AST scan of `app/`, `domain/`, `finco_core/`, `main_web.py`, `main_api.py`:
- No production file imports any `finco_parity.*` module.
- No production file references `baselines/snapshots`, `generate_baselines`, etc.
- Importing `finco_parity.*` does not execute any engine code.
- `--check` mode does not write to committed artifact paths.

---

## CI Command

```bash
python -m finco_parity.generate_baselines --check
```

Workflow: `.github/workflows/phase1b_baseline_check.yml`
Triggers on PRs to `main` with changes in `finco_parity/**`, baseline files, tests.
Checks out PR head explicitly: `ref: ${{ github.event.pull_request.head.sha }}`
Permissions: `contents: read`

Workflow run IDs: pending CI execution on corrected head.

---

## Test Results (local)

```
498 passed in 11.21s
```

| File | Tests |
|---|---|
| `test_phase1a_parity_manifest.py` | 39 |
| `test_phase1a_parity_schema_normalization.py` | 135 |
| `test_phase1a_parity_runner.py` | 204 |
| `test_phase1b_baseline_generation.py` | 43 |
| `test_phase1b_baseline_integrity.py` | 29 |
| `test_phase1b_snapshot_comparison.py` | 50 |
| `test_phase1b_production_isolation.py` | 14 (was 14) |

---

## Limitations

These artifacts characterize the current legacy implementation.
They are compatibility references, not evidence that the underlying
financial methodology is correct, complete or bankable.

The legacy engine remains an oracle for compatibility characterization only.
No financial correctness claim is made.

---

## Phase 1C Remaining Decisions

1. Drift threshold policy for Phase 2 extraction comparison.
2. Whether to add construction-period baselines.
3. Whether to archive intermediate drift reports as CI artifacts.
4. Whether to add `--verbose-diff` to `generate_baselines --check`.
