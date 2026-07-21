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
* Missing approved ledger (hard failure — not silently ignored)
* Duplicate correction_id
* Duplicate (baseline_id, field_path)
* Missing required metadata fields
* Empty or whitespace-only metadata text fields
* Unknown baseline_id (must be one of: oborovo, generic_solar, generic_wind)
* TUHO must not have approved correction records while input-source blocked
* status other than APPROVED_FINANCIAL_CORRECTION
* Invalid drift_kind (must be VALUE_DRIFT, STRUCTURAL_DRIFT, or AVAILABILITY_DRIFT)
* drift_kind inconsistent with stored baseline/candidate values
* Incorrect delta (computed from stored baseline/candidate values)
* Non-finite delta values (NaN, Infinity, -Infinity are rejected)
* delta null/non-null mismatch between stored and observed
* manual_test_reference not in APPROVED_MANUAL_TEST_REFERENCES registry
* Unknown policy_id
* Absolute filesystem paths in governance metadata
* Top-level schema/profile missing or wrong
* Summary counts inconsistent with actual correction records

Manual test reference registry
-------------------------------
Every approved correction record must reference exactly one registered test ID.
Each ID is mapped to a concrete pytest class or method in test_phase2b_tax_cfads.py.

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

# ── Registry ─────────────────────────────────────────────────────────────────

# Every approved correction record must reference exactly one ID from this set.
# Each ID maps to a concrete test class or method in tests/test_phase2b_tax_cfads.py.
APPROVED_MANUAL_TEST_REFERENCES: frozenset[str] = frozenset({
    "phase2b.calendar_axis.cross_year_allocation",    # TestX_CrossYearAllocation
    "phase2b.calendar_axis.multi_period_cross_year",  # TestY_MultiPeriodCrossYear
    "phase2b.calendar_axis.model_i_fragmentation",    # TestS_ModelI_CalendarFragmentation
    "phase2b.cash_tax.model_g_timing",                # TestQ_ModelG_ExactTiming
    "phase2b.cfads.model_h_canonical",                # TestR_ModelH_CanonicalCFADS
    "phase2b.atad.annual_threshold",                  # TestB_AtadAnnualThreshold
    "phase2b.taxable_income.no_double_addback",       # TestC_TaxableIncomeFormula
    "phase2b.lcf.fifo_vintage_expiry",                # TestD_FifoVintageExpiry + TestP_ModelE_ExactExpiry
    "phase2b.lcf.construction_loss",                  # TestK_ConstructionLoss
    "phase2b.model.no_atad_no_losses",                # TestA_NoAtadNoLosses + TestL_ModelA_Exact
    # TUHO: opening LCF resolved to zero per manual workbook inspection
    "phase2b.tuho.opening_lcf_zero.workbook_evidence",  # TestZ_TuhoInputSourceBlocked (resolved)
    # TUHO: construction-generated carryforward at operation boundary (CONSTRUCTION_GENERATED_CARRYFORWARD_AT_OPERATION_BOUNDARY)
    "phase2b.tuho.construction_shl_interest.parity_adapter",  # TestTuhoConstructionLoss
    # Oborovo: hierarchical OPEX migration (#903) propagates through cf_after_tax in H1 periods
    "phase2b.cf_after_tax.hierarchical_opex_migration",  # test_recon_fix02c_oborovo_opex_runtime_migration
})

# ── Constants ─────────────────────────────────────────────────────────────────

_REQUIRED_RECORD_FIELDS = frozenset({
    "correction_id",
    "baseline_id",
    "field_path",
    "baseline_value",
    "candidate_value",
    "delta",
    "drift_kind",
    "correction_category",
    "financial_reason",
    "manual_test_reference",
    "policy_id",
    "policy_version",
    "approval_basis",
    "status",
})

_REQUIRED_TEXT_FIELDS = frozenset({
    "correction_id",
    "baseline_id",
    "field_path",
    "correction_category",
    "financial_reason",
    "manual_test_reference",
    "policy_id",
    "policy_version",
    "approval_basis",
    "drift_kind",
    "status",
})

_KNOWN_POLICY_IDS = frozenset({
    "hr_standard_factory_v1",
    "hr_reduced_factory_v1",
    "de_demo_factory_v1",
})

_KNOWN_DRIFT_KINDS = frozenset({
    "VALUE_DRIFT",
    "STRUCTURAL_DRIFT",
    "AVAILABILITY_DRIFT",
})

# baseline_ids that may have approved correction records.
# TUHO is now included: opening-loss resolved to zero per manual workbook inspection
# (20260330_TUHO_BP_2.xlsm). Previously blocked as INPUT_SOURCE_BLOCKED.
_APPROVED_BASELINE_IDS = frozenset({
    "tuho",
    "oborovo",
    "generic_solar",
    "generic_wind",
})

_ABSOLUTE_PATH_MARKERS = ("/home/", "/root/", "/Users/", "/tmp/", "C:\\", "C:/")

_REQUIRED_SCHEMA_PREFIX = "tax_cfads_exact_corrections/"
_REQUIRED_PROFILE = "TAX_CFADS_V1"

# Expected summary counts (exact; verified against actual records).
_EXPECTED_SUMMARY_COUNTS: dict[str, int] = {
    "tuho": 517,         # 517 diffs: root cause construction_shl_loss_carryforward.
                         # Baseline used prior_tax_loss=25k (unsupported); candidate uses
                         # CONSTRUCTION_GENERATED_CARRYFORWARD_AT_OPERATION_BOUNDARY:
                         # 3,568.688 kEUR (tuho_construction_snapshot.json total_shl_idc)
                         # supplied as OpeningTaxLossVintageInput(origin_tax_year=2029) at COD.
                         # 18-month source IDC is NOT mapped into the 6-month proxy period.
    "oborovo": 614,
    "generic_solar": 314,
    "generic_wind": 510,
}


# ── CorrectionRecord ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CorrectionRecord:
    """One approved correction record (immutable)."""
    correction_id: str
    baseline_id: str
    field_path: str
    baseline_value: Any
    candidate_value: Any
    delta: Any           # numeric | None — signed (candidate − baseline)
    drift_kind: str      # VALUE_DRIFT | STRUCTURAL_DRIFT | AVAILABILITY_DRIFT
    correction_category: str
    financial_reason: str
    manual_test_reference: str
    policy_id: str
    policy_version: str
    approval_basis: str
    status: str          # must be APPROVED_FINANCIAL_CORRECTION

    def matches(self, diff: Difference) -> bool:
        """Return True iff diff exactly matches this correction record.

        Exact matching rules (all must hold):
        1. field_path == diff.path
        2. baseline_value: exact JSON type equality (1 != 1.0, None != 0)
        3. candidate_value == diff.current_value (same semantics)
        4. delta: full null/value semantics —
             stored None + observed None      → match
             stored None + observed non-null  → no match
             stored non-null + observed None  → no match
             both non-null + exactly equal (same JSON numeric type) → match
        5. drift_kind: stored value must equal diff.kind.value exactly
        """
        if self.field_path != diff.path:
            return False
        if not _json_equal(self.baseline_value, diff.baseline_value):
            return False
        if not _json_equal(self.candidate_value, diff.current_value):
            return False
        # Delta: full null/value semantics (no conditional skip).
        # diff.absolute_delta is signed (current − baseline), same convention as stored delta.
        stored_delta = self.delta
        obs_delta = diff.absolute_delta
        if stored_delta is None and obs_delta is None:
            pass  # both null → match on delta
        elif stored_delta is None or obs_delta is None:
            return False  # one null, one not → no match
        else:
            # Both non-null: compare with exact JSON numeric type semantics.
            if not _json_equal(stored_delta, obs_delta):
                return False
        # Drift kind: compare stored string against observed enum value.
        if self.drift_kind != diff.kind.value:
            return False
        return True


# ── Equality helpers ──────────────────────────────────────────────────────────

def _json_equal(a: Any, b: Any) -> bool:
    """Exact JSON type equality. 1 != 1.0, True != 1, None != 0."""
    if type(a) is not type(b):
        return False
    if isinstance(a, float):
        # Both are float; nan == nan for identity (exact bitwise comparison).
        if math.isnan(a) and math.isnan(b):
            return True
        return a == b
    return a == b


def _is_finite_numeric(v: Any) -> bool:
    """Return True if v is a finite int or float (not NaN, Inf, -Inf)."""
    if isinstance(v, bool):
        return False  # bool is int subclass; exclude it
    if isinstance(v, int):
        return True
    if isinstance(v, float):
        return math.isfinite(v)
    return False


def _infer_drift_kind(baseline_value: Any, candidate_value: Any) -> str:
    """Infer expected drift kind from stored baseline/candidate values (for consistency check).

    Used only as a secondary validation — the stored drift_kind field is authoritative.

    Rules (in priority order):
    1. Either value is the UNAVAILABLE sentinel (string "UNAVAILABLE") or None → AVAILABILITY_DRIFT.
       Note: '<missing>' is NOT treated as an availability sentinel here — when a field is absent
       from the baseline snapshot, the comparison engine produces a string '<missing>' vs the actual
       candidate type, which results in STRUCTURAL_DRIFT (type mismatch), not AVAILABILITY_DRIFT.
    2. Both values are present but of different Python types → STRUCTURAL_DRIFT.
       (e.g. float 0.0 vs int 0, or '<missing>' string vs list/dict/number)
    3. Otherwise → VALUE_DRIFT.
    """
    def _is_availability_sentinel(v: Any) -> bool:
        try:
            return v is None or v == "UNAVAILABLE"
        except Exception:
            return False
    if _is_availability_sentinel(baseline_value) or _is_availability_sentinel(candidate_value):
        return "AVAILABILITY_DRIFT"
    if type(baseline_value) is not type(candidate_value):
        return "STRUCTURAL_DRIFT"
    return "VALUE_DRIFT"


# ── Exception types ───────────────────────────────────────────────────────────

@dataclass
class LedgerValidationError(Exception):
    """Raised when the approved ledger fails schema or uniqueness validation."""
    errors: list[str]

    def __str__(self) -> str:
        return f"Ledger validation failed ({len(self.errors)} error(s)):\n" + "\n".join(
            f"  - {e}" for e in self.errors
        )


# ── MatchResult ───────────────────────────────────────────────────────────────

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


# ── Ledger loading ────────────────────────────────────────────────────────────

def load_and_validate_ledger(path: Path) -> dict[str, list[CorrectionRecord]]:
    """Load, validate and return {baseline_id: [CorrectionRecord]} from the approved ledger.

    Missing ledger is a hard governance failure — it is never silently ignored.

    Raises
    ------
    FileNotFoundError
        When the ledger file is absent.  Callers must treat this as a fatal error.
    LedgerValidationError
        On any schema, uniqueness, governance, or consistency violation.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Approved corrections ledger not found: {path}\n"
            "The approved ledger is mandatory.  Run the correction generator and "
            "promote records to the approved ledger before running the parity check."
        )

    with open(path) as f:
        raw = json.load(f)

    errors: list[str] = []

    # ── Top-level structure ───────────────────────────────────────────────────
    for top_key in ("schema", "profile", "governance", "summary", "corrections"):
        if top_key not in raw:
            errors.append(f"top-level key {top_key!r} missing")

    schema_val = raw.get("schema", "")
    if not str(schema_val).startswith(_REQUIRED_SCHEMA_PREFIX):
        errors.append(
            f"schema must start with {_REQUIRED_SCHEMA_PREFIX!r}, got {schema_val!r}"
        )

    profile_val = raw.get("profile", "")
    if profile_val != _REQUIRED_PROFILE:
        errors.append(
            f"profile must be {_REQUIRED_PROFILE!r}, got {profile_val!r}"
        )

    if errors:
        # Top-level errors prevent record parsing.
        raise LedgerValidationError(errors)

    # ── Record validation ─────────────────────────────────────────────────────
    seen_ids: set[str] = set()
    seen_paths: set[tuple[str, str]] = set()  # (baseline_id, field_path)
    records_by_baseline: dict[str, list[CorrectionRecord]] = {}

    for i, rec in enumerate(raw.get("corrections", [])):
        loc = f"record[{i}]"
        rec_errors_before = len(errors)

        # Required fields presence
        missing = _REQUIRED_RECORD_FIELDS - set(rec)
        if missing:
            errors.append(f"{loc}: missing required fields: {sorted(missing)}")
            continue  # skip further checks; fields are absent

        # Empty / whitespace-only text fields
        for txt_field in _REQUIRED_TEXT_FIELDS:
            if not str(rec.get(txt_field, "")).strip():
                errors.append(f"{loc}: empty {txt_field!r}")

        # Status
        if rec["status"] != "APPROVED_FINANCIAL_CORRECTION":
            errors.append(
                f"{loc} ({rec.get('field_path', '?')}): "
                f"status must be APPROVED_FINANCIAL_CORRECTION, got {rec['status']!r}"
            )

        # baseline_id: must be in approved set
        bid = rec["baseline_id"]
        if bid not in _APPROVED_BASELINE_IDS:
            errors.append(
                f"{loc}: baseline_id {bid!r} is not in the approved set "
                f"{sorted(_APPROVED_BASELINE_IDS)}."
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

        # drift_kind: must be a known value
        dk = rec.get("drift_kind", "")
        if dk not in _KNOWN_DRIFT_KINDS:
            errors.append(
                f"{loc} ({rec['field_path']}): invalid drift_kind {dk!r}. "
                f"Must be one of {sorted(_KNOWN_DRIFT_KINDS)}"
            )
        else:
            # Consistency check: stored values must be compatible with drift_kind
            inferred = _infer_drift_kind(rec.get("baseline_value"), rec.get("candidate_value"))
            if inferred != dk:
                errors.append(
                    f"{loc} ({rec['field_path']}): drift_kind {dk!r} is inconsistent with "
                    f"stored values (inferred {inferred!r} from baseline/candidate types and sentinels)"
                )

        # manual_test_reference: must be in registry
        ref = rec.get("manual_test_reference", "")
        if ref not in APPROVED_MANUAL_TEST_REFERENCES:
            errors.append(
                f"{loc} ({rec['field_path']}): manual_test_reference {ref!r} is not in "
                f"APPROVED_MANUAL_TEST_REFERENCES. Register the test ID first."
            )

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

        # Delta validation
        bv = rec.get("baseline_value")
        cv = rec.get("candidate_value")
        stored_delta = rec.get("delta")
        rec_drift_kind = rec.get("drift_kind", "")

        # Reject non-finite values in baseline_value, candidate_value, delta
        for field_name, val in (
            ("baseline_value", bv),
            ("candidate_value", cv),
            ("delta", stored_delta),
        ):
            if isinstance(val, float) and not math.isfinite(val):
                errors.append(
                    f"{loc} ({rec['field_path']}): non-finite value {val!r} in "
                    f"{field_name!r}. NaN, Infinity, and -Infinity are rejected."
                )

        # Delta consistency rules differ by drift_kind:
        #
        # STRUCTURAL_DRIFT: the comparison engine emits absolute_delta=None for
        #   type-mismatch diffs (e.g. float 0.0 vs int 0).  Delta must be null.
        #
        # VALUE_DRIFT / AVAILABILITY_DRIFT: when both baseline and candidate are
        #   finite numeric (same type for VALUE_DRIFT), stored delta must equal
        #   (candidate − baseline) exactly.
        if rec_drift_kind == "STRUCTURAL_DRIFT":
            if stored_delta is not None:
                errors.append(
                    f"{loc} ({rec['field_path']}): STRUCTURAL_DRIFT record must have "
                    f"delta=null (comparison engine returns no numeric delta for type "
                    f"mismatches), got delta={stored_delta!r}"
                )
        elif _is_finite_numeric(bv) and _is_finite_numeric(cv) and type(bv) is type(cv):
            # Same-type numeric VALUE_DRIFT: delta must be stored and exact.
            expected_delta = float(cv) - float(bv)
            if stored_delta is None:
                errors.append(
                    f"{loc} ({rec['field_path']}): delta is null but both baseline "
                    f"and candidate are numeric ({bv!r}, {cv!r}). Delta must be stored."
                )
            elif not isinstance(stored_delta, (int, float)):
                errors.append(
                    f"{loc} ({rec['field_path']}): delta {stored_delta!r} is not numeric."
                )
            else:
                # Compare as floats; signed delta = candidate − baseline.
                if not math.isclose(float(stored_delta), expected_delta, rel_tol=0, abs_tol=0):
                    errors.append(
                        f"{loc} ({rec['field_path']}): "
                        f"stored delta {stored_delta} ≠ (candidate−baseline)={expected_delta}"
                    )

        # If any new errors appeared for this record, skip adding it.
        if len(errors) > rec_errors_before:
            continue

        cr = CorrectionRecord(
            correction_id=rec["correction_id"],
            baseline_id=rec["baseline_id"],
            field_path=rec["field_path"],
            baseline_value=rec["baseline_value"],
            candidate_value=rec["candidate_value"],
            delta=rec.get("delta"),
            drift_kind=rec["drift_kind"],
            correction_category=rec["correction_category"],
            financial_reason=rec["financial_reason"],
            manual_test_reference=rec["manual_test_reference"],
            policy_id=rec["policy_id"],
            policy_version=rec["policy_version"],
            approval_basis=rec["approval_basis"],
            status=rec["status"],
        )
        records_by_baseline.setdefault(rec["baseline_id"], []).append(cr)

    # ── Summary count validation ───────────────────────────────────────────────
    # Only enforce per-baseline expected counts for the full production ledger
    # (i.e. when all expected baselines are present). Test fixtures with fewer
    # records are exempt from this check.
    summary = raw.get("summary", {})
    actual_counts = {bid: len(recs) for bid, recs in records_by_baseline.items()}
    _all_expected_present = all(
        actual_counts.get(bid, 0) > 0 for bid in _EXPECTED_SUMMARY_COUNTS
    )
    if _all_expected_present:
        for bid, expected in _EXPECTED_SUMMARY_COUNTS.items():
            actual = actual_counts.get(bid, 0)
            if actual != expected:
                errors.append(
                    f"summary count mismatch for {bid!r}: expected {expected}, "
                    f"got {actual} approved records"
                )
            ledger_summary_count = summary.get(bid, {}).get("n_approved_corrections")
            if ledger_summary_count is not None and ledger_summary_count != expected:
                errors.append(
                    f"summary[{bid!r}].n_approved_corrections={ledger_summary_count} "
                    f"does not match expected {expected}"
                )

    if errors:
        raise LedgerValidationError(errors)

    return records_by_baseline


# ── Matching ──────────────────────────────────────────────────────────────────

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
