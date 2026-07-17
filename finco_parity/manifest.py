"""
finco_parity.manifest — Manifest loading and integrity validation for Phase 1B.

The manifest is the single source of truth for baseline identity.  Every
artifact must be referenced by exactly one manifest entry; every manifest entry
must point to exactly one committed artifact.

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
It must NOT import from app.*, domain.*, finco_core.*, main_web, main_api.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finco_parity.canonical import sha256_of_file
from finco_parity.schema import SCHEMA_VERSION

# Canonical paths.
BASELINES_DIR: Path = Path(__file__).parent / "baselines"
SNAPSHOTS_DIR: Path = BASELINES_DIR / "snapshots"
MANIFEST_PATH: Path = BASELINES_DIR / "manifest.json"


def load_manifest() -> dict[str, Any]:
    """Load and return the raw manifest dict."""
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def manifest_baseline_ids() -> list[str]:
    """Return ordered list of baseline_ids from the manifest."""
    return [entry["baseline_id"] for entry in load_manifest()["baselines"]]


def snapshot_path_for(baseline_id: str) -> Path:
    """Return the canonical committed artifact path for *baseline_id*."""
    return SNAPSHOTS_DIR / f"{baseline_id}.json"


class ManifestIntegrityError(ValueError):
    """Raised when the manifest or its artifacts fail an integrity check."""


def validate_manifest_integrity() -> None:
    """Validate full manifest ↔ artifact consistency.

    Checks:
      1. No duplicate baseline_ids.
      2. No duplicate artifact paths.
      3. Every manifest entry points to an existing artifact.
      4. No orphan artifacts (unreferenced .json files in SNAPSHOTS_DIR).
      5. Artifact SHA-256 matches the value stored in the manifest (if present).
      6. Snapshot schema_version matches SCHEMA_VERSION.
      7. Snapshot baseline_id matches the manifest entry.
      8. Snapshot engine_designation matches the manifest entry.
      9. Snapshot input_source_id matches the manifest entry.
     10. All artifact paths remain inside SNAPSHOTS_DIR (no path traversal).

    Raises ManifestIntegrityError on first failure found per check (all
    checks run independently so multiple issues are reported together).
    """
    manifest = load_manifest()
    entries: list[dict] = manifest.get("baselines", [])
    errors: list[str] = []

    seen_ids: set[str] = set()
    seen_paths: set[Path] = set()
    referenced_paths: set[Path] = set()

    for entry in entries:
        bid = entry.get("baseline_id", "")

        # 1. Duplicate IDs.
        if bid in seen_ids:
            errors.append(f"Duplicate baseline_id: {bid!r}")
        seen_ids.add(bid)

        # Resolve artifact path.
        artifact_path = snapshot_path_for(bid)

        # 2. Duplicate paths.
        if artifact_path in seen_paths:
            errors.append(f"Duplicate artifact path: {artifact_path}")
        seen_paths.add(artifact_path)
        referenced_paths.add(artifact_path)

        # 10. Path traversal check.
        try:
            artifact_path.resolve().relative_to(SNAPSHOTS_DIR.resolve())
        except ValueError:
            errors.append(
                f"{bid}: artifact path escapes SNAPSHOTS_DIR: {artifact_path}"
            )
            continue

        # 3. Artifact existence.
        if not artifact_path.exists():
            errors.append(f"{bid}: artifact missing: {artifact_path}")
            continue

        # Load snapshot for content checks.
        try:
            snapshot = json.loads(artifact_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{bid}: cannot parse artifact JSON: {exc}")
            continue

        # 5. SHA-256 check (if stored in manifest).
        if "artifact_sha256" in entry:
            actual_sha = sha256_of_file(artifact_path)
            if actual_sha != entry["artifact_sha256"]:
                errors.append(
                    f"{bid}: SHA-256 mismatch "
                    f"(manifest={entry['artifact_sha256'][:16]}… "
                    f"actual={actual_sha[:16]}…)"
                )

        # 6. Schema version.
        snap_schema = snapshot.get("schema_version", "")
        if snap_schema != SCHEMA_VERSION:
            errors.append(
                f"{bid}: snapshot schema_version={snap_schema!r} "
                f"!= expected {SCHEMA_VERSION!r}"
            )

        # 7. Baseline ID provenance.
        if snapshot.get("baseline_id") != bid:
            errors.append(
                f"{bid}: snapshot baseline_id={snapshot.get('baseline_id')!r} "
                f"!= manifest baseline_id={bid!r}"
            )

        # 8. Engine designation provenance.
        manifest_engine = entry.get("engine_designation", "")
        snap_engine = snapshot.get("engine_designation", "")
        if manifest_engine and snap_engine != manifest_engine:
            errors.append(
                f"{bid}: snapshot engine_designation={snap_engine!r} "
                f"!= manifest {manifest_engine!r}"
            )

        # 9. Input source provenance.
        # Manifest uses factory_function; snapshot uses input_source_id (project_factories.*)
        manifest_factory = entry.get("factory_function", "")
        snap_input = snapshot.get("input_source_id", "")
        # Normalize: snapshot strips "app." prefix, manifest includes it.
        # Accept either exact match or manifest endswith snapshot.
        if manifest_factory and snap_input:
            normalized_manifest = manifest_factory.replace("app.", "")
            normalized_snap = snap_input.replace("app.", "")
            if normalized_manifest != normalized_snap:
                errors.append(
                    f"{bid}: snapshot input_source_id={snap_input!r} "
                    f"!= manifest factory_function={manifest_factory!r}"
                )

    # 4. Orphan artifacts.
    if SNAPSHOTS_DIR.exists():
        for p in SNAPSHOTS_DIR.glob("*.json"):
            if p not in referenced_paths:
                errors.append(f"Orphan artifact (unreferenced by manifest): {p.name}")

    if errors:
        raise ManifestIntegrityError(
            f"{len(errors)} manifest integrity error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )
