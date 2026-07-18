"""finco_parity.correction_matcher — Exact correction-record matching contract.

The approved ledger (tax_cfads_v1_exact.json) contains one record per
(baseline_id, field_path) difference.  Every financially relevant field is
compared exactly — no tolerance, no rounding, no string conversion.

JSON type semantics are preserved:
  1 != 1.0   |   true != 1   |   null != 0

Bidirectional completeness
--------------------------
* Every observed Difference must have one exact approved record.
  A path, changed value, changed type, changed drift kind or changed delta
  that does not match an approved record → UNEXPLAINED_DRIFT.

* Every approved record must be observed.
  An approved record with no matching observed Difference → STALE_CORRECTION_RECORD.
  Stale records fail --check.

Ledger validation failures
--------------------------
* Missing approved ledger
* Duplicate correction_id
* Duplicate (baseline_id, field_path)
* Missing required metadata fields
* status other than APPROVED_FINANCIAL_CORRECTION
* Incorrect delta (computed from stored baseline/candidate values)
* Empty financial_reason or manual_test_reference
* Unknown policy_id
* Absolute filesystem paths in governance metadata

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.comparison (for Difference, DriftKind)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from finco_parity.comparison import Difference, DriftKind

_REQUIRED_RECORD_FIELDS = frozenset({
    "correction_id",
    "baseline_id",
    "field_path",
    "baseline_value",
    "candidate_value",
    "delta",
    "correction_category",
    "financial_reason",
    "manual_test_reference",
    "policy_id",
    "policy_version",
    "approval_basis",
    "status",
})

_KNOWN_POLICY_IDS = frozenset({
    "hr_standard_factory_v1",
    "hr_reduced_factory_v1",
    "de_demo_factory_v1",
})

_ABSOLUTE_PATH_MARKERS = ("/home/", "/root/", "/Users/", "/tmp/", "C:\\", "C:/")


@dataclass(frozen=True)
class CorrectionRecord:
    """One approved correction record (immutable)."""
    correction_id: str
    baseline_id: str
    field_path: str
    baseline_value: Any
    candidate_value: Any
    delta: Any           # float | None — stored as-is from JSON
    correction_category: str
    financial_reason: str
    manual_test_reference: str
    policy_id: str
    policy_version: str
    approval_basis: str
    status: str          # must be APPROVED_FINANCIAL_CORRECTION

    def matches(self, diff: Difference) -> bool:
        """Return True iff diff exactly matches this correction record.

        Exact matching rules:
        - field_path == diff.path
        - baseline_value: exact JSON type equality (1 != 1.0, None != 0)
        - candidate_value == diff.current_value (same semantics)
        - delta: if not None, must equal diff.absolute_delta (if delta is stored)
        - drift kind: the correction implicitly approves VALUE_DRIFT only unless
          another kind is stored; checked via _drift_kind_matches
        """
        if self.field_path != diff.path:
            return False
        if not _json_equal(self.baseline_value, diff.baseline_value):
            return False
        if not _json_equal(self.candidate_value, diff.current_value):
            return False
        # Check delta if stored and diff has one.
        # Both are signed (candidate − baseline); Difference.absolute_delta is misnamed —
        # it is actually the signed delta (current − baseline), matching stored convention.
        if self.delta is not None and diff.absolute_delta is not None:
            if not _float_exactly_equal(self.delta, diff.absolute_delta):
                return False
        # Drift kind: records are implicitly VALUE_DRIFT unless the stored
        # baseline/candidate values indicate structural or availability drift.
        expected_kind = _infer_drift_kind(self.baseline_value, self.candidate_value)
        if diff.kind != expected_kind:
            return False
        return True


def _json_equal(a: Any, b: Any) -> bool:
    """Exact JSON type equality. 1 != 1.0, True != 1, None != 0."""
    if type(a) is not type(b):
        return False
    if isinstance(a, float):
        # Both are float; compare bitwise-exact (nan == nan for identity)
        if math.isnan(a) and math.isnan(b):
            return True
        return a == b
    return a == b


def _float_exactly_equal(a: float, b: float) -> bool:
    """Exact float equality for delta comparison."""
    if math.isnan(a) and math.isnan(b):
        return True
    return a == b


def _infer_drift_kind(baseline_value: Any, candidate_value: Any) -> DriftKind:
    """Infer the expected DriftKind from the stored baseline/candidate values.

    Rules (in priority order):
    1. Either value is the UNAVAILABLE sentinel (string) → AVAILABILITY_DRIFT.
    2. Both values are present but of different Python types → STRUCTURAL_DRIFT.
       (e.g. float 0.0 vs int 0: comparison engine emits STRUCTURAL_DRIFT)
    3. Otherwise → VALUE_DRIFT.
    """
    _UNAVAILABLE = "UNAVAILABLE"
    if baseline_value == _UNAVAILABLE or candidate_value == _UNAVAILABLE:
        return DriftKind.AVAILABILITY_DRIFT
    if type(baseline_value) is not type(candidate_value):
        return DriftKind.STRUCTURAL_DRIFT
    return DriftKind.VALUE_DRIFT


@dataclass
class LedgerValidationError(Exception):
    """Raised when the approved ledger fails schema or uniqueness validation."""
    errors: list[str]

    def __str__(self) -> str:
        return f"Ledger validation failed ({len(self.errors)} error(s)):\n" + "\n".join(
            f"  - {e}" for e in self.errors
        )


@dataclass
class MatchResult:
    """Result of matching one baseline's observed differences against the ledger."""
    baseline_id: str
    # Classified differences
    approved: list[Difference] = field(default_factory=list)
    unexplained: list[Difference] = field(default_factory=list)
    stale_records: list[CorrectionRecord] = field(default_factory=list)

    @property
    def status(self) -> str:
        if not self.approved and not self.unexplained:
            return "IDENTICAL"
        if self.unexplained or self.stale_records:
            return "UNEXPLAINED_DRIFT"
        return "APPROVED_FINANCIAL_CORRECTION"

    @property
    def has_failures(self) -> bool:
        return bool(self.unexplained or self.stale_records)


def load_and_validate_ledger(path: Path) -> dict[str, list[CorrectionRecord]]:
    """Load, validate and return {baseline_id: [CorrectionRecord]} from the approved ledger.

    Raises
    ------
    FileNotFoundError
        When the ledger file is absent (missing ledger is a hard failure).
    LedgerValidationError
        On any schema, uniqueness or governance violation.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Approved corrections ledger not found: {path}\n"
            "The ledger is required — run the correction generator and promote records."
        )

    with open(path) as f:
        raw = json.load(f)

    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_paths: set[tuple[str, str]] = set()  # (baseline_id, field_path)
    records_by_baseline: dict[str, list[CorrectionRecord]] = {}

    for i, rec in enumerate(raw.get("corrections", [])):
        loc = f"record[{i}]"

        # Required fields
        missing = _REQUIRED_RECORD_FIELDS - set(rec)
        if missing:
            errors.append(f"{loc}: missing required fields: {sorted(missing)}")
            continue

        # Status
        if rec["status"] != "APPROVED_FINANCIAL_CORRECTION":
            errors.append(
                f"{loc} ({rec.get('field_path', '?')}): "
                f"status must be APPROVED_FINANCIAL_CORRECTION, got {rec['status']!r}"
            )

        # Duplicate correction_id
        cid = rec["correction_id"]
        if cid in seen_ids:
            errors.append(f"{loc}: duplicate correction_id {cid!r}")
        else:
            seen_ids.add(cid)

        # Duplicate (baseline_id, field_path)
        path_key = (rec["baseline_id"], rec["field_path"])
        if path_key in seen_paths:
            errors.append(
                f"{loc}: duplicate (baseline_id, field_path) = "
                f"({rec['baseline_id']!r}, {rec['field_path']!r})"
            )
        else:
            seen_paths.add(path_key)

        # Empty required text fields
        for txt_field in ("financial_reason", "manual_test_reference", "approval_basis"):
            if not str(rec.get(txt_field, "")).strip():
                errors.append(f"{loc}: empty {txt_field!r}")

        # Known policy_id
        if rec.get("policy_id") not in _KNOWN_POLICY_IDS:
            errors.append(
                f"{loc}: unknown policy_id {rec.get('policy_id')!r}. "
                f"Known: {sorted(_KNOWN_POLICY_IDS)}"
            )

        # Absolute filesystem paths in governance metadata
        for meta_field in ("financial_reason", "manual_test_reference", "approval_basis"):
            val = str(rec.get(meta_field, ""))
            for marker in _ABSOLUTE_PATH_MARKERS:
                if marker in val:
                    errors.append(
                        f"{loc}: absolute filesystem path in {meta_field!r}: "
                        f"found {marker!r}. Use repository-relative paths only."
                    )

        # Delta consistency: stored delta must equal abs(candidate - baseline) when both numeric
        bv = rec.get("baseline_value")
        cv = rec.get("candidate_value")
        stored_delta = rec.get("delta")
        if (
            isinstance(bv, (int, float))
            and isinstance(cv, (int, float))
            and stored_delta is not None
        ):
            # delta is signed: stored as (candidate − baseline).
            expected_delta = cv - bv
            if not _float_exactly_equal(float(stored_delta), expected_delta):
                errors.append(
                    f"{loc} ({rec['field_path']}): "
                    f"stored delta {stored_delta} ≠ abs(candidate-baseline)={expected_delta}"
                )

        if errors:
            # Don't accumulate records that failed validation
            continue

        cr = CorrectionRecord(
            correction_id=rec["correction_id"],
            baseline_id=rec["baseline_id"],
            field_path=rec["field_path"],
            baseline_value=rec["baseline_value"],
            candidate_value=rec["candidate_value"],
            delta=rec.get("delta"),
            correction_category=rec["correction_category"],
            financial_reason=rec["financial_reason"],
            manual_test_reference=rec["manual_test_reference"],
            policy_id=rec["policy_id"],
            policy_version=rec["policy_version"],
            approval_basis=rec["approval_basis"],
            status=rec["status"],
        )
        records_by_baseline.setdefault(rec["baseline_id"], []).append(cr)

    if errors:
        raise LedgerValidationError(errors)

    return records_by_baseline


def match_differences(
    baseline_id: str,
    differences: list[Difference],
    ledger: dict[str, list[CorrectionRecord]],
) -> MatchResult:
    """Classify each Difference against the approved correction ledger.

    Bidirectional:
    - Every observed difference must have an exact approved record → else UNEXPLAINED_DRIFT.
    - Every approved record must be observed → else STALE_CORRECTION_RECORD (fails --check).

    Parameters
    ----------
    baseline_id:
        Which baseline's differences are being classified.
    differences:
        Observed Difference objects from the comparison engine.
    ledger:
        {baseline_id: [CorrectionRecord]} from load_and_validate_ledger().

    Returns
    -------
    MatchResult with approved/unexplained/stale_records lists.
    """
    if not differences and baseline_id not in ledger:
        # IDENTICAL — no differences, no approved records expected
        return MatchResult(baseline_id=baseline_id)

    approved_records = ledger.get(baseline_id, [])
    # Index by field_path for O(1) lookup (paths are unique per validation)
    records_by_path: dict[str, CorrectionRecord] = {r.field_path: r for r in approved_records}

    result = MatchResult(baseline_id=baseline_id)
    matched_paths: set[str] = set()

    for diff in differences:
        record = records_by_path.get(diff.path)
        if record is not None and record.matches(diff):
            result.approved.append(diff)
            matched_paths.add(diff.path)
        else:
            result.unexplained.append(diff)

    # Stale: approved records with no matching observed difference
    for record in approved_records:
        if record.field_path not in matched_paths:
            result.stale_records.append(record)

    return result
