# Phase 1C — Candidate Snapshot Contract and Dual-Run Comparison Readiness

## Overview

Phase 1C defines the stable candidate snapshot provider contract, enabling
comparison of new engine outputs against committed Phase 1B legacy baselines.
It separates expected provenance differences (`engine_designation`,
`run_path_id`) from blocking financial payload drift, provides an
aggregate severity policy, and supplies a deterministic CLI.

---

## Provenance

| Field | Value |
|---|---|
| Base SHA | `459c20550c6f86e0a869bffc424e91e4a972b6a0` |
| Branch | `phase1c-candidate-comparison-contract` |
| PR | #892 — Draft, do not merge |
| Previous amendment head | `460f1a68f8bb1894c08552ebc0d8466ae8e8f051` |
| Final head | committed with this amendment |

---

## Typed Exception Hierarchy

```
CandidateError(ValueError)
  ├── CandidateFileNotFoundError   — candidate file missing
  ├── CandidatePathError           — unsafe path or baseline_id/reference mismatch
  └── CandidateValidationError     — base validation failure
        ├── CandidateIdentityMismatch  — baseline_id / input_source_id / baseline_commit_sha mismatch
        ├── CandidateSchemaMismatch    — schema_version mismatch or structural schema failure
        └── CandidateContentInvalid   — NaN/inf or non-canonical bytes
```

---

## `CandidateSnapshotProvider` Protocol

```python
@runtime_checkable
class CandidateSnapshotProvider(Protocol):
    def capture_snapshot(
        self, baseline_id: str, reference: BaselineReference
    ) -> Mapping[str, Any]: ...
```

`BaselineReference` carries all committed-baseline identity: `baseline_id`,
`project_type_key`, `project_code`, `scenario_identity`, `input_source_id`,
`schema_version`, `baseline_commit_sha`, `committed_snapshot_path`.

---

## `FileCandidateSnapshotProvider` Security Rules

Six rules enforced in `capture_snapshot()` before path resolution and file read:

| Rule | Error |
|---|---|
| 1. `baseline_id` must equal `reference.baseline_id` | `CandidatePathError` |
| 2. Relative path derived from committed path must not be absolute | `CandidatePathError` |
| 3. No `..` component in derived relative path | `CandidatePathError` |
| 4. Resolved candidate path must remain inside `candidate_dir` (symlink escape) | `CandidatePathError` |
| 5. Path must not resolve to a directory | `CandidatePathError` |
| 6. File must exist | `CandidateFileNotFoundError` |

After file read: parsed JSON must be a `dict` and bytes must equal
`canonical_json_bytes(parsed)` (raises `CandidateContentInvalid` on mismatch).

**Safe relative-path reporting**: error messages use `rel` (the relative path
beneath `SNAPSHOTS_DIR`) or `baseline_id`, never absolute `/home/…` or `/tmp/…`
paths. `BaselineRunResult.error_message` is safe to serialize to JSON reports.

---

## `validate_candidate_snapshot()` Check Order

1. **`schema_version`** must match `reference.schema_version` → `CandidateSchemaMismatch`
2. **`baseline_id`**, **`input_source_id`**, **`baseline_commit_sha`** must match reference → `CandidateIdentityMismatch`
3. **Structural schema** via `validate_snapshot()` → `CandidateSchemaMismatch`
4. **NaN / infinity** scan (recursive) → `CandidateContentInvalid`
5. **Raw bytes** canonical check (optional, when `raw_bytes` provided) → `CandidateContentInvalid`

`engine_designation` and `run_path_id` are intentionally **not checked** — they
are expected provenance differences between engines.

---

## `baseline_commit_sha` Candidate Binding

`candidate.baseline_commit_sha` must equal `reference.baseline_commit_sha` (the
fixed SHA from the committed artifact). A mismatch raises `CandidateIdentityMismatch`
before payload projection, blocking comparison entirely.

This prevents a candidate produced from a different source commit from silently
comparing financial data that is not expected to match.

---

## Schema-Version vs Identity Routing

| Mismatch | Exception | Status |
|---|---|---|
| `schema_version` mismatch | `CandidateSchemaMismatch` | `SCHEMA_MISMATCH` |
| `baseline_id` mismatch | `CandidateIdentityMismatch` | `IDENTITY_MISMATCH` |
| `input_source_id` mismatch | `CandidateIdentityMismatch` | `IDENTITY_MISMATCH` |
| `baseline_commit_sha` mismatch | `CandidateIdentityMismatch` | `IDENTITY_MISMATCH` |
| Structural schema failure | `CandidateSchemaMismatch` | `SCHEMA_MISMATCH` |
| NaN / infinity | `CandidateContentInvalid` | `CANDIDATE_INVALID` |
| Non-canonical bytes | `CandidateContentInvalid` | `CANDIDATE_INVALID` |

Routing is by exception **type**, not by inspecting exception message text.

---

## `BaselineRunStatus` Values (11)

| Status | Meaning |
|---|---|
| `PASS` | Candidate matches baseline on all blocking sections |
| `PAYLOAD_DRIFT` | Financial payload differs |
| `CANDIDATE_MISSING` | Candidate file not found |
| `CANDIDATE_INVALID` | NaN/inf or non-canonical bytes |
| `IDENTITY_MISMATCH` | `baseline_id`, `input_source_id`, or `baseline_commit_sha` mismatch |
| `SCHEMA_MISMATCH` | `schema_version` mismatch or structural schema failure |
| `LEGACY_DRIFT` | Fresh legacy snapshot differs from committed artifact |
| `ENVIRONMENT_MISMATCH` | Runtime does not match `generation_environment` contract |
| `EXECUTION_ERROR` | Unexpected error during orchestration |
| `MANIFEST_INTEGRITY_FAILURE` | `validate_manifest_integrity()` or artifact integrity failure |
| `UNKNOWN_BASELINE` | `baseline_id` not found in manifest |

---

## `run_candidate_provider()` Orchestration (9 steps)

```
Step 0: Validate baseline_id in manifest → UNKNOWN_BASELINE if missing
Step 1: Environment check               → ENVIRONMENT_MISMATCH
Step 2: Manifest integrity              → MANIFEST_INTEGRITY_FAILURE
Step 3: Load committed artifact         → MANIFEST_INTEGRITY_FAILURE on failure
Step 4: Build BaselineReference
Step 5: Optional legacy re-run          → LEGACY_DRIFT if unstable
Step 6: Acquire candidate snapshot      → CANDIDATE_MISSING / CANDIDATE_INVALID
Step 7: Validate candidate              → IDENTITY_MISMATCH / SCHEMA_MISMATCH / CANDIDATE_INVALID
Step 8: Project to _PARITY_SECTIONS
Step 9: Compare → PASS or PAYLOAD_DRIFT
```

Unknown baseline exits at Step 0 — provider and legacy engine are never called.

---

## Blocking Parity Sections

```python
_PARITY_SECTIONS = frozenset({
    "period_grid",
    "operating_schedules",
    "tax_and_cfads",
    "financing",
    "financial_statements",
    "returns",
    "unavailable_sections",
    "unavailable_fields",
})
```

---

## Aggregate Severity Policy

`compare_candidate_directory()` selects `overall_status` via:

```python
overall = max(
    (r.status for r in results if r.status != BaselineRunStatus.PASS),
    key=lambda s: _AGGREGATE_SEVERITY[s],
)
```

| Status | Severity |
|---|---|
| `MANIFEST_INTEGRITY_FAILURE` | 9 |
| `ENVIRONMENT_MISMATCH` | 8 |
| `LEGACY_DRIFT` | 7 |
| `EXECUTION_ERROR` | 6 |
| `SCHEMA_MISMATCH` | 5 |
| `IDENTITY_MISMATCH` | 4 |
| `CANDIDATE_INVALID` | 3 |
| `CANDIDATE_MISSING` | 2 |
| `UNKNOWN_BASELINE` | 2 |
| `PAYLOAD_DRIFT` | 1 |
| `PASS` | 0 |

Deterministic and independent of baseline ordering.

---

## CLI Exit Code Table

| Exit | Derived from `overall_status` |
|---|---|
| 0 | `PASS` |
| 1 | `EXECUTION_ERROR` (or unexpected error) |
| 2 | `UNKNOWN_BASELINE` (library) / unknown `--baseline-id` (argparse) |
| 3 | `PAYLOAD_DRIFT` |
| 4 | `MANIFEST_INTEGRITY_FAILURE` |
| 5 | `ENVIRONMENT_MISMATCH` |
| 6 | `CANDIDATE_MISSING` or `CANDIDATE_INVALID` |
| 7 | `IDENTITY_MISMATCH` or `SCHEMA_MISMATCH` |
| 8 | `LEGACY_DRIFT` |

Exit code is derived by `return _STATUS_EXIT_CODE.get(result.overall_status, 1)` — one lookup, no secondary scan of individual results.

---

## CLI Options

| Option | Description |
|---|---|
| `--candidate-dir DIR` | Directory containing candidate snapshot files (required) |
| `--baseline-id ID` | Compare a single baseline (mutually exclusive with `--all`) |
| `--all` | Compare all baselines in manifest (mutually exclusive with `--baseline-id`) |
| `--check` | Zero-tolerance mode: forces `verify_legacy=True` |
| `--verify-legacy` | Capture and verify a fresh legacy snapshot (default) |
| `--no-verify-legacy` | Skip fresh legacy snapshot verification |
| `--json-report PATH` | Write canonical JSON report (parent dirs created automatically) |
| `--text-report PATH` | Write text report ending with exactly one newline |
| `--max-diffs N` | Cap reported differences per baseline (N ≥ 0; preserves `difference_count`) |
| `--quiet` | Suppress progress output |

**`--max-diffs` validation**: negative values rejected at argparse level (exit 2)
and at library level (`ValueError`). `max_diffs=0` returns empty `differences`
tuple but preserves the full `difference_count`.

---

## Robust Report Writes

`_write_report()` in `compare_candidate.py`:
- Creates parent directories with `mkdir(parents=True, exist_ok=True)`
- Normalizes text content to exactly one trailing newline: `content.rstrip("\n") + "\n"`
- Catches `OSError` → prints error to stderr → returns exit code 1
- JSON reports remain canonical via `canonical_json_bytes()`

---

## Manifest Failure Handling

Manifest and integrity validation occurs at one boundary before any
baseline comparison:

1. `validate_manifest_integrity()` failure → `MANIFEST_INTEGRITY_FAILURE` → exit 4
2. Committed-artifact parse failure → `MANIFEST_INTEGRITY_FAILURE` → exit 4
3. Committed-artifact canonical integrity failure → `MANIFEST_INTEGRITY_FAILURE` → exit 4
4. `--all` with malformed manifest → exit 4
5. Single-baseline with malformed manifest → exit 4

These are never mapped to generic exit 1 (`EXECUTION_ERROR`).

---

## Production Isolation Proof

AST scan of `app/`, `domain/`, `finco_core/`, `main_web.py`, `main_api.py`:
- No production file imports `finco_parity.candidate`, `finco_parity.dual_run`,
  or `finco_parity.compare_candidate`.
- Importing `finco_parity.*` does not execute any engine code.
- Candidate harness modules do not appear in any production import graph.

---

## Test Results

| File | Tests collected |
|---|---|
| `test_phase1c_candidate_provider.py` | (see --collect-only) |
| `test_phase1c_dual_run.py` | (see --collect-only) |
| `test_phase1c_compare_candidate_cli.py` | (see --collect-only) |
| `test_phase1c_production_isolation.py` | 3 |
| **Phase 1C total** | **86** |

Full focused suite (Phase 1A + 1B + 1C): **601 passed**

---

## Limitations

These artifacts characterize the current legacy implementation.
They are compatibility references, not evidence that the underlying
financial methodology is correct, complete or bankable.

The legacy engine remains an oracle for compatibility characterization only.
No financial correctness claim is made.

---

## Phase 1C Remaining Decisions

1. Whether to add `baseline_commit_sha` to the blocking comparison sections or keep it as identity-gate only.
2. Drift threshold policy for Phase 2 extraction comparison.
3. Whether to archive intermediate drift reports as CI artifacts.
4. Whether to add `--verbose-diff` to `compare_candidate`.
