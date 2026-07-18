"""
finco_parity.generate_tax_cfads_corrections — Generate the Phase 2B proposed corrections file.

Runs the TAX_CFADS_V1 comparison for all non-blocked baselines, records each
difference as a PENDING_REVIEW record in
``finco_parity/corrections/tax_cfads_v1_proposed.json``.

GOVERNANCE RULES
----------------
* This generator writes ONLY to ``tax_cfads_v1_proposed.json``.
* It NEVER writes to ``tax_cfads_v1_exact.json`` (the approved ledger).
* Status is always ``PENDING_REVIEW`` — a human reviewer must inspect proposed
  records and manually promote them to the approved ledger with full metadata.
* Blocked baselines (e.g. TUHO with unresolved opening vintage) are skipped
  and reported as ``INPUT_SOURCE_BLOCKED`` in the summary.

Usage::

    python -m finco_parity.generate_tax_cfads_corrections

After reviewing the proposed file, manually add approved records to
``tax_cfads_v1_exact.json`` following the approved-correction schema (fields:
correction_id, correction_category, financial_reason, manual_test_reference,
policy_id, policy_version, approval_basis, status=APPROVED_FINANCIAL_CORRECTION).

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
  - financial_engine.*  (deferred via candidate provider)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROPOSED_PATH = Path(__file__).parent / "corrections" / "tax_cfads_v1_proposed.json"
APPROVED_PATH = Path(__file__).parent / "corrections" / "tax_cfads_v1_exact.json"

_ALL_BASELINE_IDS = ("tuho", "oborovo", "generic_solar", "generic_wind")

_BASELINE_REASONS: dict[str, str] = {
    "oborovo": (
        "Phase 2B uses hr_reduced_factory_v1 (10%) vs legacy (~18% assumed); "
        "introduces calendar-year tax axis (Dec31 splitting), TAX_YEAR_LAST_PERIOD "
        "cash timing, and canonical CFADS computation."
    ),
    "generic_solar": (
        "Phase 2B uses de_demo_factory_v1 (25% factory assumption) vs legacy; "
        "introduces calendar-year tax axis, TAX_YEAR_LAST_PERIOD cash timing, "
        "and canonical CFADS computation."
    ),
    "generic_wind": (
        "Phase 2B uses de_demo_factory_v1 (25% factory assumption) vs legacy; "
        "introduces calendar-year tax axis, TAX_YEAR_LAST_PERIOD cash timing, "
        "and canonical CFADS computation."
    ),
}


def generate_proposed_corrections() -> dict:
    """Run TAX_CFADS_V1 comparison for runnable baselines, collect per-field diffs.

    Returns a dict with schema, summary, and corrections (all PENDING_REVIEW).
    Blocked baselines are listed in the summary with status=INPUT_SOURCE_BLOCKED.
    """
    from finco_parity.financial_engine_tax_cfads_candidate import (
        generate_tax_cfads_candidate_snapshot,
    )
    from finco_parity.manifest import SNAPSHOTS_DIR
    from finco_parity.profiles import ComparisonProfile, project_for_profile
    from finco_parity.comparison import compare_snapshots
    from finco_parity.tax_reference_inputs import (
        TuhoOpeningLossVintageUnresolved,
        build_opening_loss_vintages,
    )

    profile = ComparisonProfile.TAX_CFADS_V1
    records: list[dict] = []
    summary: dict[str, dict] = {}

    for baseline_id in _ALL_BASELINE_IDS:
        # Check for blocked baselines before running.
        try:
            build_opening_loss_vintages(baseline_id)
        except TuhoOpeningLossVintageUnresolved as exc:
            print(f"  [{baseline_id}] INPUT_SOURCE_BLOCKED — skipping: {str(exc)[:120]}",
                  flush=True)
            summary[baseline_id] = {
                "status": "INPUT_SOURCE_BLOCKED",
                "n_pending_review": 0,
                "block_reason": str(exc)[:200],
            }
            continue

        print(f"  [{baseline_id}] generating candidate ...", flush=True)
        snapshot_path = SNAPSHOTS_DIR / f"{baseline_id}.json"
        with open(snapshot_path) as f:
            baseline_snap = json.load(f)

        candidate_snap = generate_tax_cfads_candidate_snapshot(baseline_id)
        baseline_proj = project_for_profile(baseline_snap, profile)
        candidate_proj = project_for_profile(candidate_snap, profile)

        cmp = compare_snapshots(baseline_proj, candidate_proj, baseline_id)
        diffs = cmp.differences

        reason = _BASELINE_REASONS.get(baseline_id, "Phase 2B candidate vs baseline")
        for d in diffs:
            records.append({
                "baseline_id": baseline_id,
                "field_path": d.path,
                "baseline_value": d.baseline_value,
                "candidate_value": d.current_value,
                "delta": (
                    (d.current_value - d.baseline_value)
                    if isinstance(d.baseline_value, (int, float))
                    and isinstance(d.current_value, (int, float))
                    else None
                ),
                "observed_reason": reason,
                # NOT approved — human review required before promotion to exact.json.
                "status": "PENDING_REVIEW",
            })

        n_identical = len(cmp.differences) == 0
        summary[baseline_id] = {
            "status": "IDENTICAL" if n_identical else "PENDING_REVIEW",
            "n_pending_review": len(diffs),
        }
        print(f"  [{baseline_id}] {len(diffs)} pending-review records", flush=True)

    return {
        "schema": "tax_cfads_proposed_corrections/1.0",
        "profile": "TAX_CFADS_V1",
        "description": (
            "Per-field, per-baseline, per-period PENDING_REVIEW corrections for Phase 2B "
            "TAX_CFADS_V1 parity. Generated by generate_tax_cfads_corrections.py. "
            "DO NOT commit this file — it is for human review only. "
            "Approved records must be manually promoted to tax_cfads_v1_exact.json "
            "with full governance metadata (correction_id, correction_category, "
            "financial_reason, manual_test_reference, policy_id, policy_version, "
            "approval_basis, status=APPROVED_FINANCIAL_CORRECTION)."
        ),
        "governance": {
            "proposed_file": str(PROPOSED_PATH),
            "approved_file": str(APPROVED_PATH),
            "rule": "This generator NEVER writes to the approved ledger.",
        },
        "summary": summary,
        "corrections": records,
    }


def main() -> int:
    print("Generating TAX_CFADS_V1 proposed corrections (PENDING_REVIEW only) ...",
          flush=True)
    print(f"  Output: {PROPOSED_PATH}", flush=True)
    print(f"  Approved ledger: {APPROVED_PATH} (NOT modified)", flush=True)
    print()

    ledger = generate_proposed_corrections()
    PROPOSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROPOSED_PATH.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n")
    n = len(ledger["corrections"])
    print(f"\nWritten {n} PENDING_REVIEW records to {PROPOSED_PATH}", flush=True)
    print("Next step: human review → promote approved records to tax_cfads_v1_exact.json",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
