"""
finco_parity.manifest — Manifest loading, path resolution and integrity validation.

The manifest is the single source of truth for baseline identity.  Every
artifact must be referenced by exactly one manifest entry; every manifest
entry must point to exactly one committed artifact.

Artifact path resolution
------------------------
Artifact paths are resolved from the declared `snapshot_path` in each
manifest entry (relative to the repository root), NOT derived from
``SNAPSHOTS_DIR / f"{baseline_id}.json"``.

Required fields
---------------
Every manifest entry must supply these non-empty fields:

    baseline_id, project_type_key, project_code, scenario_identity,
    engine_designation, schema_version, baseline_commit_sha,
    input_source_id, capture_source, run_path, snapshot_path,
    artifact_sha256

``artifact_sha256`` must be exactly 64 lowercase hexadecimal characters.

``capture_source`` must equal the canonical capture function identifier:
    finco_parity.legacy_snapshot.capture_snapshot

``baseline_commit_sha`` semantics
----------------------------------
``baseline_commit_sha`` identifies the source commit represented by the
committed characterization baseline.  It is fixed at the time the baseline
is generated and does NOT change when a later commit runs ``--check``.
It is NOT the transient SHA executing the current CI run.

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
It must NOT import from app.*, domain.*, finco_core.*, main_web, main_api.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from finco_parity.canonical import sha256_of_file
from finco_parity.schema import SCHEMA_VERSION

# Canonical paths.
_REPO_ROOT: Path = Path(__file__).parent.parent
BASELINES_DIR: Path = Path(__file__).parent / "baselines"
SNAPSHOTS_DIR: Path = BASELINES_DIR / "snapshots"
MANIFEST_PATH: Path = BASELINES_DIR / "manifest.json"

# Required manifest entry fields.
_REQUIRED_ENTRY_FIELDS: tuple[str, ...] = (
    "baseline_id",
    "project_type_key",
    "project_code",
    "scenario_identity",
    "engine_designation",
    "schema_version",
    "baseline_commit_sha",
    "input_source_id",
    "capture_source",
    "run_path",
    "snapshot_path",
    "artifact_sha256",
)

# Canonical capture source identifier.
_CANONICAL_CAPTURE_SOURCE = "finco_parity.legacy_snapshot.capture_snapshot"

# artifact_sha256 must be 64 lowercase hex chars.
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Required fields in the generation_environment block.
_REQUIRED_GENERATION_ENV_FIELDS: tuple[str, ...] = (
    "python_minor",
    "constraints_file",
    "numpy_version",
    "pandas_version",
)


def load_manifest() -> dict[str, Any]:
    """Load and return the raw manifest dict."""
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def manifest_baseline_ids() -> list[str]:
    """Return ordered list of baseline_ids from the manifest."""
    return [entry["baseline_id"] for entry in load_manifest()["baselines"]]


def resolve_snapshot_path(entry: dict[str, Any]) -> Path:
    """Return the resolved absolute artifact path for a manifest entry.

    Resolution rules:
      - Uses the declared ``snapshot_path`` field (relative to repo root).
      - Absolute paths are rejected.
      - ``..`` traversal is rejected.
      - Resolved path must remain inside SNAPSHOTS_DIR.
    """
    declared = entry.get("snapshot_path", "")
    if not declared:
        raise ManifestIntegrityError(
            f"{entry.get('baseline_id', '?')}: snapshot_path is empty"
        )
    p = Path(declared)
    if p.is_absolute():
        raise ManifestIntegrityError(
            f"{entry.get('baseline_id', '?')}: snapshot_path must be relative: {declared!r}"
        )
    # Reject explicit '..' components before normalization.
    if any(part == ".." for part in p.parts):
        raise ManifestIntegrityError(
            f"{entry.get('baseline_id', '?')}: snapshot_path contains '..' traversal: {declared!r}"
        )
    resolved = (_REPO_ROOT / p).resolve()
    try:
        resolved.relative_to(SNAPSHOTS_DIR.resolve())
    except ValueError:
        raise ManifestIntegrityError(
            f"{entry.get('baseline_id', '?')}: snapshot_path escapes SNAPSHOTS_DIR: {declared!r}"
        )
    # Reject paths that resolve to an existing directory.
    if resolved.is_dir():
        raise ManifestIntegrityError(
            f"{entry.get('baseline_id', '?')}: snapshot_path resolves to a directory: {declared!r}"
        )
    return resolved


def snapshot_path_for(baseline_id: str) -> Path:
    """Return the resolved artifact path for *baseline_id* from the manifest.

    Raises KeyError if the baseline_id is not found.
    """
    manifest = load_manifest()
    for entry in manifest["baselines"]:
        if entry["baseline_id"] == baseline_id:
            return resolve_snapshot_path(entry)
    raise KeyError(f"baseline_id not found in manifest: {baseline_id!r}")


def get_manifest_entry(baseline_id: str) -> dict[str, Any]:
    """Return the manifest entry for *baseline_id*.  Raises KeyError if absent."""
    manifest = load_manifest()
    for entry in manifest["baselines"]:
        if entry["baseline_id"] == baseline_id:
            return entry
    raise KeyError(f"baseline_id not found in manifest: {baseline_id!r}")


class ManifestIntegrityError(ValueError):
    """Raised when the manifest or its artifacts fail an integrity check."""


def validate_manifest_integrity() -> None:
    """Validate full manifest ↔ artifact consistency.

    Checks (all run, errors accumulated):
      1.  No missing required entry fields.
      2.  No duplicate baseline_ids.
      3.  No duplicate artifact paths (normalized).
      4.  capture_source == canonical capture function.
      5.  artifact_sha256 is exactly 64 lowercase hex chars.
      6.  No absolute snapshot_path.
      7.  No path traversal (resolved path inside SNAPSHOTS_DIR).
      8.  Every artifact exists.
      9.  artifact_sha256 matches artifact bytes.
     10.  Artifact is valid canonical JSON (round-trip byte equality).
     11.  snapshot schema_version matches manifest.schema_version.
     12.  snapshot baseline_id matches manifest.baseline_id.
     13.  snapshot engine_designation matches manifest.engine_designation.
     14.  snapshot baseline_commit_sha matches manifest.baseline_commit_sha.
     15.  snapshot input_source_id matches manifest.input_source_id.
     16.  snapshot run_path_id matches manifest.run_path.
     17.  No orphan artifacts.
     18.  Each committed snapshot passes validate_snapshot().

    Raises ManifestIntegrityError listing all errors found.
    """
    from finco_parity.canonical import canonical_json_bytes
    from finco_parity.schema import validate_snapshot, SnapshotValidationError

    manifest = load_manifest()
    entries: list[dict] = manifest.get("baselines", [])
    errors: list[str] = []

    # 0. Validate generation_environment block if present.
    gen_env = manifest.get("generation_environment")
    if gen_env is not None:
        if not isinstance(gen_env, dict):
            errors.append("generation_environment must be a JSON object")
        else:
            for field in _REQUIRED_GENERATION_ENV_FIELDS:
                val = gen_env.get(field)
                if not val or not isinstance(val, str):
                    errors.append(
                        f"generation_environment.{field} is missing or empty"
                    )

    seen_ids: set[str] = set()
    seen_paths: set[Path] = set()
    referenced_paths: set[Path] = set()

    for entry in entries:
        bid = entry.get("baseline_id", "<missing>")

        # 1. Required fields.
        for field in _REQUIRED_ENTRY_FIELDS:
            val = entry.get(field)
            if not val:
                errors.append(f"{bid}: missing or empty required field: {field!r}")

        # 2. Duplicate baseline_ids.
        if bid in seen_ids:
            errors.append(f"Duplicate baseline_id: {bid!r}")
        seen_ids.add(bid)

        # 4. capture_source.
        cs = entry.get("capture_source", "")
        if cs and cs != _CANONICAL_CAPTURE_SOURCE:
            errors.append(
                f"{bid}: capture_source={cs!r} != {_CANONICAL_CAPTURE_SOURCE!r}"
            )

        # 5. artifact_sha256 format.
        sha_val = entry.get("artifact_sha256", "")
        if sha_val and not _SHA256_RE.match(sha_val):
            errors.append(
                f"{bid}: artifact_sha256 must be 64 lowercase hex chars: {sha_val!r}"
            )

        # Resolve artifact path (catches 6 and 7).
        try:
            artifact_path = resolve_snapshot_path(entry)
        except ManifestIntegrityError as exc:
            errors.append(str(exc))
            continue

        # 3. Duplicate paths.
        if artifact_path in seen_paths:
            errors.append(f"Duplicate artifact path: {artifact_path}")
        seen_paths.add(artifact_path)
        referenced_paths.add(artifact_path)

        # 8. Artifact exists.
        if not artifact_path.exists():
            errors.append(f"{bid}: artifact missing: {artifact_path}")
            continue

        # Load raw bytes and parsed snapshot.
        raw_bytes = artifact_path.read_bytes()
        try:
            snapshot = json.loads(raw_bytes)
        except Exception as exc:
            errors.append(f"{bid}: cannot parse artifact JSON: {exc}")
            continue

        # 9. SHA-256 check.
        if sha_val and _SHA256_RE.match(sha_val):
            import hashlib
            actual_sha = hashlib.sha256(raw_bytes).hexdigest()
            if actual_sha != sha_val:
                errors.append(
                    f"{bid}: SHA-256 mismatch "
                    f"(manifest={sha_val[:16]}… actual={actual_sha[:16]}…)"
                )

        # 10. Canonical byte integrity — artifact must be byte-identical to its
        #     re-serialized form.
        try:
            reserialised = canonical_json_bytes(snapshot)
            if reserialised != raw_bytes:
                errors.append(
                    f"{bid}: artifact is not in canonical form "
                    f"(file bytes != canonical_json_bytes(parsed_artifact)). "
                    f"Re-run generate_baselines to fix."
                )
        except Exception as exc:
            errors.append(f"{bid}: cannot re-serialise artifact: {exc}")

        # 11–16. Provenance binding checks.
        def _chk(field_label: str, snap_val: Any, manifest_val: Any) -> None:
            if manifest_val and snap_val != manifest_val:
                errors.append(
                    f"{bid}: {field_label} mismatch: "
                    f"snapshot={snap_val!r} manifest={manifest_val!r}"
                )

        manifest_schema = entry.get("schema_version", "")
        _chk("schema_version", snapshot.get("schema_version"), manifest_schema or SCHEMA_VERSION)
        _chk("baseline_id", snapshot.get("baseline_id"), bid)
        _chk("engine_designation", snapshot.get("engine_designation"), entry.get("engine_designation"))
        _chk("baseline_commit_sha", snapshot.get("baseline_commit_sha"), entry.get("baseline_commit_sha"))
        _chk("input_source_id", snapshot.get("input_source_id"), entry.get("input_source_id"))
        _chk("run_path_id", snapshot.get("run_path_id"), entry.get("run_path"))

        # 18. validate_snapshot().
        try:
            validate_snapshot(snapshot)
        except SnapshotValidationError as exc:
            errors.append(f"{bid}: snapshot fails schema validation: {exc}")

    # 17. Orphan artifacts — rglob covers nested subdirectories.
    if SNAPSHOTS_DIR.exists():
        for p in sorted(SNAPSHOTS_DIR.rglob("*.json")):
            if p not in referenced_paths:
                rel = p.relative_to(SNAPSHOTS_DIR)
                errors.append(f"Orphan artifact (unreferenced by manifest): {rel}")

    if errors:
        raise ManifestIntegrityError(
            f"{len(errors)} manifest integrity error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


# ---------------------------------------------------------------------------
# Validated manifest context
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidatedManifestContext:
    manifest: dict
    entries: tuple
    baseline_ids: tuple


def load_validated_manifest_context() -> ValidatedManifestContext:
    """Load, parse and validate the manifest in one controlled boundary.

    Normalizes JSON parse errors, structural errors and integrity failures
    to ManifestIntegrityError.

    Returns a ValidatedManifestContext with manifest dict, entries tuple,
    and baseline_ids tuple in manifest order.

    Raises:
        ManifestIntegrityError: on any parse, structure or integrity failure.
    """
    try:
        manifest = load_manifest()
    except (json.JSONDecodeError, OSError) as exc:
        raise ManifestIntegrityError(f"Cannot load manifest: {exc}") from exc

    if not isinstance(manifest, dict):
        raise ManifestIntegrityError(
            f"Manifest root must be a mapping, got {type(manifest).__name__}"
        )

    baselines = manifest.get("baselines")
    if baselines is None:
        raise ManifestIntegrityError("Manifest missing 'baselines' field")
    if not isinstance(baselines, list):
        raise ManifestIntegrityError(
            f"Manifest 'baselines' must be a list, got {type(baselines).__name__}"
        )

    # Full structural + hash integrity check.
    validate_manifest_integrity()

    entries = tuple(baselines)
    ids = tuple(e["baseline_id"] for e in entries if "baseline_id" in e)
    return ValidatedManifestContext(manifest=manifest, entries=entries, baseline_ids=ids)
