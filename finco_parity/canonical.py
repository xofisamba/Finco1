"""
finco_parity.canonical — Canonical JSON serialization for legacy-engine snapshots.

All snapshot files MUST be written through write_canonical_json() to guarantee
byte-identical output on every regeneration from the same source content.

Serialization rules (non-negotiable):
  - encoding:      UTF-8
  - indent:        2
  - sort_keys:     True
  - ensure_ascii:  False
  - allow_nan:     False
  - newline at EOF (single trailing LF)

Prohibited content (enforced at serialization time via allow_nan=False):
  - NaN or ±infinity
  - Python repr() output
  - Memory addresses

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
It must NOT import from app.*, domain.*, finco_core.*, main_web, main_api.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json_bytes(obj: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes (with trailing newline) for *obj*.

    Raises ValueError (via json.dumps allow_nan=False) if obj contains NaN or
    infinity.  Raises TypeError if obj contains a non-serializable type.
    """
    text = json.dumps(
        obj,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    )
    # Guarantee exactly one trailing newline.
    return (text + "\n").encode("utf-8")


def write_canonical_json(obj: Any, path: Path) -> bytes:
    """Serialize *obj* canonically and write to *path*.

    Creates parent directories as needed.
    Returns the raw bytes written (including trailing newline).
    """
    data = canonical_json_bytes(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def sha256_of_bytes(data: bytes) -> str:
    """Return lowercase hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def sha256_of_file(path: Path) -> str:
    """Return lowercase hex SHA-256 digest of file at *path*."""
    return sha256_of_bytes(path.read_bytes())
