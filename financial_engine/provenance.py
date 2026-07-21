"""
financial_engine.provenance — Deterministic engine run provenance.

EngineProvenance is attached at result construction time and is immutable.
The input fingerprint is a deterministic hash of the clean OperatingModelInput —
same inputs always produce the same fingerprint; one material change produces
a different one. It contains no timestamps, object IDs, paths, or Git SHAs.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from financial_engine.inputs import OperatingModelInput


@dataclass(frozen=True)
class DerivationEvidence:
    """Records which source module/function produced a specific output."""
    output_path: str
    source_module: str
    source_function: str
    input_paths: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class EngineProvenance:
    """Immutable provenance record for one clean engine run."""
    engine_version: str
    run_path_id: str
    input_fingerprint: str
    derivation_evidence: tuple[DerivationEvidence, ...]


def _to_canonical(obj: Any) -> Any:
    """Recursively convert to a JSON-serializable canonical form."""
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, (bool, int, float, str, type(None))):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_canonical(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_canonical(v) for k in sorted(obj) for v in [obj[k]]}
    # dataclass fallback
    try:
        import dataclasses
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return _to_canonical(dataclasses.asdict(obj))
    except Exception:
        pass
    return str(obj)


def compute_input_fingerprint(inputs: "OperatingModelInput") -> str:
    """Compute a deterministic SHA-256 fingerprint of the clean input contract.

    Stable key ordering, no timestamps, no paths, no object IDs.
    Same OperatingModelInput always produces the same hex digest.
    """
    import dataclasses
    raw = _to_canonical(dataclasses.asdict(inputs))
    canonical = json.dumps(raw, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_tax_cfads_fingerprint(inputs: "Any") -> str:
    """Compute a deterministic SHA-256 fingerprint of TaxCfadsModelInput.

    Covers the complete operating + tax input set. Any change to:
    - corporate tax rate, ATAD limit, ATAD threshold, LCF duration,
      cash-tax timing, cash-tax lag, opening vintage origins/amounts,
      any period interest component, any fiscal adjustment
    will produce a different fingerprint.
    """
    import dataclasses

    def _to_canonical_extended(obj: Any) -> Any:
        """Handle TaxPolicy enum fields and property-based fields."""
        from enum import Enum
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, (bool, int, float, str, type(None))):
            return obj
        if isinstance(obj, (list, tuple)):
            return [_to_canonical_extended(v) for v in obj]
        if isinstance(obj, dict):
            return {k: _to_canonical_extended(v) for k in sorted(obj) for v in [obj[k]]}
        try:
            if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
                d = dataclasses.asdict(obj)
                # Add computed properties that affect tax calculations
                if hasattr(obj, 'total_interest_keur'):
                    d['_total_interest_keur'] = obj.total_interest_keur
                return _to_canonical_extended(d)
        except Exception:
            pass
        return str(obj)

    raw = _to_canonical_extended(inputs)
    canonical = json.dumps(raw, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
