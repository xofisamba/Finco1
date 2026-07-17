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
| Branch | `phase1b-legacy-baseline-materialization` |
| PR | #891 — Draft, do not merge |
| Previous amendment head | `2428e343b6c602a4cff5e54f590a1617226578cc` |
| Python-pin head | `ee1f39c40a128f73078d8c5e70d2c26dc63bcf35` |
| Final head | committed with this amendment |

---

## Failure History

### Stage 1 — Transient `baseline_commit_sha` → PROVENANCE_DRIFT

The original `cmd_check()` auto-detected the current checkout SHA and embedded
it in every fresh snapshot as `baseline_commit_sha`.  After the Phase 1B commit
advanced HEAD, every future `--check` run generated a snapshot with the new
HEAD SHA, causing `PROVENANCE_DRIFT` on `baseline_commit_sha` for all four
baselines.

**Fix:** `cmd_check()` now reads `baseline_commit_sha` from the committed
artifact and passes it explicitly to `capture_snapshot()`.

### Stage 2 — Python 3.11 vs 3.12 → VALUE_DRIFT at 1 ULP

After fixing provenance, CI (Python 3.12) generated LLCR/PLCR ratio values
that differed from the committed artifacts by 1 ULP (~4.4e-16).  This is
caused by different floating-point code-generation between CPython 3.11 and
3.12; the arithmetic is identical but last-bit rounding differs.

**Fix:** Workflow pinned to `python-version: "3.11"` to match the generation
environment.  The `generation_environment` contract in the manifest documents
the required environment and `cmd_check()` enforces it as a fail-fast check
before running the engine.

---

## Stable `baseline_commit_sha` Policy

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

## Generation Environment Contract

```json
{
  "generation_environment": {
    "python_minor": "3.11",
    "constraints_file": "constraints.txt",
    "numpy_version": "1.26.4",
    "pandas_version": "2.2.3"
  }
}
```

`cmd_check()` enforces this contract before running the engine (exit code 5):

```
BASELINE ENVIRONMENT MISMATCH
expected Python 3.11, NumPy 1.26.4, pandas 2.2.3
actual   Python 3.12, NumPy 2.4.6, pandas 3.0.3
```

Version lookup uses `importlib.metadata` (stdlib, no extra dependencies).
Environment mismatch is reported as `BASELINE ENVIRONMENT MISMATCH`, not as
`VALUE_DRIFT`.

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

Generation rules:
- Default (no `--output-dir`): writes to `resolve_snapshot_path(entry)`.
- `--output-dir DIR`: preserves relative subpath beneath `SNAPSHOTS_DIR`;
  e.g. `snapshot_path = ".../snapshots/sub/foo.json"` → `DIR/sub/foo.json`.

Validation rules:
- Relative paths only (absolute paths fail).
- Explicit `..` path component is rejected even if normalization stays inside.
- Resolved path must remain inside `finco_parity/baselines/snapshots/`.
- Paths resolving to a directory are rejected.
- Duplicate normalized paths fail.
- Every declared artifact must exist.
- Every artifact must be referenced exactly once.
- Orphan JSON files fail (recursive via `rglob("*.json")`).

---

## Workflow Trigger Policy

The Phase 1B baseline check runs on **every PR to `main`** — no `paths:`
filter.  This ensures future changes to the legacy engine, its dependencies,
or any file in the repository are caught immediately.

```yaml
on:
  pull_request:
    branches: [main]
```

The workflow pins Python 3.11 and installs from `constraints.txt`
(numpy==1.26.4, pandas==2.2.3) to match the generation environment.

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

Baseline artifact bytes are **unchanged** from the original Phase 1B additions.

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
files for all four baselines (within the same environment).

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
| Orphan artifact (top-level) | `ManifestIntegrityError: Orphan` |
| Orphan artifact (nested subdirectory) | `ManifestIntegrityError: Orphan` |
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
| Path traversal (`../`) | `ManifestIntegrityError: Escapes/traversal` |
| Explicit `..` component | `ManifestIntegrityError: traversal` |
| Absolute snapshot_path | `ManifestIntegrityError: relative/absolute` |
| Directory snapshot_path | `ManifestIntegrityError: directory` |
| generation_environment not a dict | `ManifestIntegrityError: generation_environment` |
| generation_environment missing field | `ManifestIntegrityError: generation_environment` |

---

## Environment Mismatch Matrix

| Mismatch | `cmd_check()` result |
|---|---|
| Matching environment | returns 0 (if no drift) |
| Wrong Python minor | exit 5, `BASELINE ENVIRONMENT MISMATCH` |
| Wrong NumPy version | exit 5, `BASELINE ENVIRONMENT MISMATCH` |
| Wrong pandas version | exit 5, `BASELINE ENVIRONMENT MISMATCH` |
| Engine not called after mismatch | verified (no `capture_snapshot` calls) |

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
Triggers on **all** PRs to `main` — no `paths:` filter (full drift guardrail).
Checks out PR head explicitly: `ref: ${{ github.event.pull_request.head.sha }}`
Python: `3.11` (matches generation environment; numpy==1.26.4, pandas==2.2.3)
Permissions: `contents: read`

Workflow run IDs and conclusions: pending CI execution on corrected head.

---

## Test Results (local)

```
515 passed in 11.43s
```

| File | Tests |
|---|---|
| `test_phase1a_parity_manifest.py` | 39 |
| `test_phase1a_parity_schema_normalization.py` | 135 |
| `test_phase1a_parity_runner.py` | 204 |
| `test_phase1b_baseline_generation.py` | 52 |
| `test_phase1b_baseline_integrity.py` | 38 |
| `test_phase1b_snapshot_comparison.py` | 57 |
| `test_phase1b_production_isolation.py` | 15 |

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
