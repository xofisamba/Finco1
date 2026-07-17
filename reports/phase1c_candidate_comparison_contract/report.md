# Phase 1C — Candidate Comparison Contract

## Overview

Phase 1C defines the candidate comparison contract for Finco1 parity testing.
It specifies the protocol for supplying a new-engine candidate snapshot, the
security rules for file-based candidate providers, the validation chain that
every candidate must pass before comparison, and the orchestration layer that
coordinates environment checks, manifest integrity, candidate acquisition,
validation, payload projection, and structural comparison.

The deliverables are:
- `finco_parity/candidate.py` — `CandidateSnapshotProvider` protocol, `FileCandidateSnapshotProvider`, `validate_candidate_snapshot`, `BaselineReference`
- `finco_parity/dual_run.py` — `run_candidate_provider`, `compare_candidate_snapshot`, `compare_candidate_directory`, result dataclasses and status enum
- `finco_parity/compare_candidate.py` — CLI entry point with structured exit codes

---

## Provenance

| Field | Value |
|---|---|
| Branch | `phase1c-candidate-comparison-contract` |
| Base SHA | `459c2055` |
| Phase 1B report | `reports/phase1b_legacy_baseline_materialization/report.md` |

---

## `CandidateSnapshotProvider` Protocol

`CandidateSnapshotProvider` is a `runtime_checkable` `Protocol` with a single method:

```python
def capture_snapshot(
    self, baseline_id: str, reference: BaselineReference
) -> Mapping[str, Any]: ...
```

Any object implementing this interface can supply a candidate snapshot for
comparison. The protocol does not prescribe how the snapshot is obtained — it
may be loaded from disk, generated live, fetched from a remote service, or
constructed inline.

`BaselineReference` is a frozen dataclass that carries the committed baseline's
identity fields (`baseline_id`, `schema_version`, `input_source_id`, etc.) and
the absolute path to the committed artifact. It is constructed from the manifest
via `baseline_reference_from_manifest(baseline_id)`.

---

## `FileCandidateSnapshotProvider` — Path Resolution and Security Rules

`FileCandidateSnapshotProvider` reads candidate snapshots from a local directory
on disk. It derives the candidate file path by replicating the relative path of
the committed artifact (relative to `SNAPSHOTS_DIR`) under the configured
`candidate_dir`.

**Five security rules, evaluated in order:**

1. **No absolute relative paths** — if the derived relative path is absolute,
   `CandidatePathError` is raised.
2. **No `..` components** — any `..` part in the relative path is rejected with
   `CandidatePathError`.
3. **Must remain inside `candidate_dir`** — the resolved candidate path must be
   a descendant of the resolved `candidate_dir`; otherwise `CandidatePathError`
   is raised (symlink-escape guard).
4. **No directories** — if the resolved path is a directory, `CandidatePathError`
   is raised.
5. **Must exist** — if the file does not exist, `CandidateFileNotFoundError`
   is raised.

After the file is read and parsed as JSON, the provider performs a canonical
byte-equality check: `raw_bytes == canonical_json_bytes(parsed)`. A mismatch
raises `CandidateValidationError`.

---

## `validate_candidate_snapshot` — Check Order

Validation is performed in four steps:

1. **Identity fields** — `schema_version`, `baseline_id`, and `input_source_id`
   must match the corresponding fields in `BaselineReference` exactly.
   `engine_designation` and `run_path_id` are intentionally excluded (they are
   expected provenance differences between legacy and candidate).
2. **Structural schema validation** — delegates to `validate_snapshot()` from
   `finco_parity.schema`; a `SnapshotValidationError` is re-raised as
   `CandidateValidationError`.
3. **No NaN or infinity** — all numeric values in the snapshot are recursively
   checked; any non-finite float raises `CandidateValidationError`.
4. **Raw bytes check (optional)** — if `raw_bytes` is supplied, the candidate
   must satisfy `raw_bytes == canonical_json_bytes(parsed)`.

---

## `BaselineRunStatus` Enum — Values and Meanings

| Value | Meaning |
|---|---|
| `PASS` | Candidate matches committed baseline on all blocking sections. |
| `CANDIDATE_MISSING` | Candidate file was not found. |
| `CANDIDATE_INVALID` | Candidate file exists but is malformed or fails validation. |
| `IDENTITY_MISMATCH` | Identity fields (`schema_version`, `baseline_id`, `input_source_id`) differ. |
| `SCHEMA_MISMATCH` | Candidate fails structural schema validation. |
| `PAYLOAD_DRIFT` | Candidate diverges from baseline in one or more blocking sections. |
| `LEGACY_DRIFT` | Live legacy re-run differs from committed artifact (baseline is stale). |
| `ENVIRONMENT_MISMATCH` | Runtime environment does not match the generation contract. |
| `EXECUTION_ERROR` | Unexpected error during orchestration (manifest, artifact load, etc.). |

---

## `BaselineRunResult` and `AggregateRunResult` Structure

### `BaselineRunResult`

Frozen dataclass. Key fields: `baseline_id`, `status`, `legacy_engine_designation`,
`candidate_engine_designation`, `legacy_run_path`, `candidate_run_path`,
`comparison_status`, `difference_count`, `differences`, `legacy_warnings`,
`candidate_warnings`, `error_message`.

### `AggregateRunResult`

Frozen dataclass. Fields: `selected_baselines`, `passed_baselines`,
`failed_baselines`, `overall_status` (`PASS` iff all baselines passed),
`baseline_results` (in manifest order).

---

## `_PARITY_SECTIONS` — Blocking Sections

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

Differences in any other field (e.g. `engine_designation`, `run_path_id`,
`warnings`) do not affect the pass/fail outcome.

---

## `compare_candidate` CLI — Exit Code Table

| Code | Meaning |
|---|---|
| 0 | All baselines pass. |
| 1 | Execution error (engine failure, manifest error, unexpected exception). |
| 2 | Unknown baseline ID or invalid CLI arguments. |
| 3 | Candidate payload drift. |
| 4 | Manifest / baseline integrity failure. |
| 5 | Environment mismatch. |
| 6 | Candidate missing or invalid. |
| 7 | Identity or schema mismatch. |
| 8 | Live legacy drift (committed artifact stale). |

---

## CLI Options Table

| Option | Description |
|---|---|
| `--candidate-dir DIR` | (Required) Directory containing candidate snapshot files. |
| `--baseline-id ID` | Compare a single baseline by ID (mutually exclusive with `--all`). |
| `--all` | Compare all baselines declared in the manifest. |
| `--check` | Zero-tolerance mode: forces `verify_legacy=True`. |
| `--verify-legacy` | Capture and verify a fresh legacy snapshot (default). |
| `--no-verify-legacy` | Skip fresh legacy snapshot verification. |
| `--json-report PATH` | Write a canonical JSON report to PATH. |
| `--text-report PATH` | Write a human-readable text report to PATH. |
| `--max-diffs N` | Cap on differences reported per baseline. |
| `--quiet` | Suppress progress output. |

---

## Production Isolation Proof

Phase 1C modules (`finco_parity.candidate`, `finco_parity.dual_run`,
`finco_parity.compare_candidate`) are not imported by any production code in
`app/`, `domain/`, `finco_core/`, `main_web.py`, or `main_api.py`.

Verified by AST-based import scan, string scan for candidate comparison symbol
names, and module-level import safety test in
`tests/test_phase1c_production_isolation.py`.

---

## Limitations

- Phase 1C does not implement a live candidate engine runner; the
  `CandidateSnapshotProvider` protocol targets file-based or pre-computed
  snapshots in this phase.
- `verify_legacy=True` requires the legacy engine and its environment to be
  available. Use `--no-verify-legacy` to skip this step in environments without
  the legacy engine.
- `_PARITY_SECTIONS` is hard-coded; additions require updating `dual_run.py`
  and re-generating committed baselines.
- Numeric comparison tolerances are inherited from Phase 1B's
  `compare_snapshots()` implementation and are not configurable via the CLI.
