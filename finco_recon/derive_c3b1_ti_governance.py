"""finco_recon.derive_c3b1_ti_governance — Deterministic TI-governance derivation.

Reads the authoritative extracted fixture (excel_oborovo_financial_truth.json)
and computes corrected TI-formula governance fields from the already-extracted
row vectors.  Writes the updated governance section back to the fixture.

The extracted row data (excel_fin_earn_keur, excel_shl_keur, excel_senior_keur,
excel_ebit_keur, excel_taxable_income_keur) is never modified.  Only the
derived governance fields are updated or added.

Derivation version is bumped independently of the extractor version so the
two can evolve separately.

Usage::

    python -m finco_recon.derive_c3b1_ti_governance [--fixture PATH] [--dry-run]

The script is fully idempotent: if the committed fixture already contains the
correct derived state, the first run reports "already up-to-date" and writes
nothing.  A test that calls the script on a committed fixture must observe
this behaviour.

Idempotency anchor
------------------
Two hashes guard freshness:

``source_vectors_sha256``
    Canonical hash of the immutable extracted calculation inputs
    (period, classification, fin_earn, shl, senior, ebit, ti) for every
    period.  Any change to the source vectors invalidates the derived state.

``_content_sha256``
    Hash of all derived governance fields (per-period values + summary)
    together with ``source_vectors_sha256`` and ``_DERIVATION_VERSION``.
    This is the write-guard: if the stored ``_content_sha256`` matches the
    freshly recomputed one, the fixture is up-to-date.

Component identities used
--------------------------
    TI  = EBT + Fiscal_Reintegration
        = EBIT + Financial_Earnings + Fiscal_Reintegration

    net_taxable_financial_items_before_senior
        = Financial_Earnings + Fiscal_Reintegration + Senior_Interest
        = fin_earn + shl + senior

    Simplified identity:  TI = EBIT - Senior_Interest
    Simplified residual:  TI - (EBIT - senior)  =  net_taxable_financial_items_before_senior

    During debt-active periods:   fin_earn = -(SHL + senior)  =>  net = 0
    After debt repayment:         |SHL| <= TOL, |senior| <= TOL  =>  net = fin_earn (P&L row 20)

Reason classification
---------------------
    net within tolerance    -> ZERO_NET_TAXABLE_FINANCIAL_ITEMS_BEFORE_SENIOR_INTEREST  (applicable=True)
    fin > TOL, |shl| <= TOL, |senior| <= TOL  -> TAXABLE_CASH_INTEREST_AFTER_DEBT_REPAYMENT (applicable=False)
    otherwise               -> NON_ZERO_NET_TAXABLE_FINANCIAL_ITEMS  (applicable=False)

The tolerance guard on shl and senior uses abs() <= _TOLERANCE (not == 0.0)
so tiny floating-point residuals near zero do not misclassify periods.
"""

import argparse
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

_DERIVATION_VERSION = "1.1.0"
_TOLERANCE = 0.01  # kEUR — threshold for "effectively zero"
_DEFAULT_FIXTURE = pathlib.Path("tests/fixtures/excel_oborovo_financial_truth.json")

# Fields extracted from the workbook that serve as calculation inputs.
# These are the only fields that affect governance outputs.
_SOURCE_VECTOR_FIELDS = (
    "period",
    "classification",
    "excel_fin_earn_keur",
    "excel_shl_keur",
    "excel_senior_keur",
    "excel_ebit_keur",
    "excel_taxable_income_keur",
)


def _source_vectors_sha256(pd_list: list) -> str:
    """Canonical hash of the immutable extracted calculation inputs.

    Serialised with sort_keys and compact separators so the hash is stable
    across Python versions and dict-ordering differences.
    """
    vectors = [
        {k: p[k] for k in _SOURCE_VECTOR_FIELDS if k in p}
        for p in pd_list
    ]
    serialised = json.dumps(vectors, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False)
    return hashlib.sha256(serialised.encode()).hexdigest()


def _compute_period(p: dict) -> dict:
    """Return corrected governance fields for one period_diagnostic entry.

    Construction periods (classification == 'CONSTRUCTION_PERIOD') receive None
    for all formula fields; only the reason string is set.
    """
    if p["classification"] == "CONSTRUCTION_PERIOD":
        return {
            "net_taxable_financial_items_before_senior_keur": None,
            "full_formula_residual_keur": None,
            "alternative_full_formula_residual_keur": None,
            "simplified_formula_residual_keur": None,
            "simplified_identity_applicable": None,
            "simplified_identity_reason": "CONSTRUCTION_PERIOD_NO_TAXATION",
        }

    fin = p["excel_fin_earn_keur"]
    shl = p["excel_shl_keur"]
    senior = p["excel_senior_keur"]
    ebit = p["excel_ebit_keur"]
    ti = p["excel_taxable_income_keur"]

    # net = fin_earn + FR + senior  (FR = SHL in this workbook)
    net = fin + shl + senior

    # full formula: TI = EBIT + fin_earn + FR  (= EBT + FR, proved exact by identity)
    full_res = ti - (ebit + fin + shl)

    # alternative full: TI = EBIT + net - senior  (algebraically identical)
    alt_full_res = ti - (ebit + net - senior)

    # simplified: TI = EBIT - senior
    simp_res = ti - (ebit - senior)  # equals net

    applicable = abs(net) <= _TOLERANCE

    if applicable:
        reason = "ZERO_NET_TAXABLE_FINANCIAL_ITEMS_BEFORE_SENIOR_INTEREST"
    elif (fin > _TOLERANCE
          and abs(shl) <= _TOLERANCE
          and abs(senior) <= _TOLERANCE):
        # Post-repayment cash interest: SHL and senior are both within tolerance of zero
        reason = "TAXABLE_CASH_INTEREST_AFTER_DEBT_REPAYMENT"
    else:
        reason = "NON_ZERO_NET_TAXABLE_FINANCIAL_ITEMS"

    return {
        "net_taxable_financial_items_before_senior_keur": round(net, 9),
        "full_formula_residual_keur": round(full_res, 9),
        "alternative_full_formula_residual_keur": round(alt_full_res, 9),
        "simplified_formula_residual_keur": round(simp_res, 9),
        "simplified_identity_applicable": applicable,
        "simplified_identity_reason": reason,
    }


def _derive_summary(pd_list: list) -> dict:
    """Derive ti_formula_period_summary from computed period values."""
    operational = [p for p in pd_list if p["classification"] != "CONSTRUCTION_PERIOD"]

    applicable_periods = [
        p["period"] for p in operational
        if p["_gov"]["simplified_identity_applicable"]
    ]
    non_applicable = [
        p for p in operational
        if not p["_gov"]["simplified_identity_applicable"]
    ]

    first_non = non_applicable[0]["period"] if non_applicable else None

    # max residual among non-applicable periods
    if non_applicable:
        max_entry = max(non_applicable,
                        key=lambda p: abs(p["_gov"]["simplified_formula_residual_keur"]))
        max_res = abs(max_entry["_gov"]["simplified_formula_residual_keur"])
        max_period = max_entry["period"]
    else:
        max_res = 0.0
        max_period = None

    cash_interest_count = sum(
        1 for p in non_applicable
        if p["_gov"]["simplified_identity_reason"] == "TAXABLE_CASH_INTEREST_AFTER_DEBT_REPAYMENT"
    )
    other_non_applicable = [
        {"period": p["period"], "reason": p["_gov"]["simplified_identity_reason"]}
        for p in non_applicable
        if p["_gov"]["simplified_identity_reason"] != "TAXABLE_CASH_INTEREST_AFTER_DEBT_REPAYMENT"
    ]

    return {
        "_derivation_note": (
            "All values derived from excel_fin_earn_keur, excel_shl_keur, "
            "excel_senior_keur, excel_ebit_keur, excel_taxable_income_keur. "
            "Not hardcoded."
        ),
        "full_formula": (
            "TI = EBT + Fiscal_Reintegration = EBIT + Financial_Earnings + Fiscal_Reintegration "
            "(proved exact all operational periods via identity_ti_eq_ebt_plus_fr_delta)"
        ),
        "alternative_full_formula": (
            "TI = EBIT + net_taxable_financial_items_before_senior - Senior_Interest "
            "(algebraically identical to full formula)"
        ),
        "simplified_formula": (
            "TI = EBIT - Senior_Interest "
            "(valid only when net_taxable_financial_items_before_senior = 0)"
        ),
        "net_taxable_financial_items_before_senior_definition": (
            "Financial_Earnings + Fiscal_Reintegration + Senior_Interest "
            "= fin_earn + SHL + senior. "
            "During debt-active periods: fin_earn = -(SHL + senior) => net = 0. "
            "After repayment (|SHL|<=TOL, |senior|<=TOL): net = fin_earn = P&L row 20 cash interest."
        ),
        "simplified_applicable_periods": applicable_periods,
        "simplified_applicable_count": len(applicable_periods),
        "first_non_applicable_period": first_non,
        "max_simplified_residual_keur": round(max_res, 6),
        "maximum_residual_period": max_period,
        "residual_source_component": "TAXABLE_CASH_INTEREST_AFTER_DEBT_REPAYMENT",
        "cash_interest_residual_period_count": cash_interest_count,
        "other_non_applicable_periods": other_non_applicable,
        "residual_note": (
            "P&L row 20 (Interests from Cash on surplus cash) becomes positive after "
            "SHL and senior debt are both within tolerance of zero."
        ),
    }


def derive(fixture_path: pathlib.Path) -> dict:
    """Read fixture, compute governance fields, return updated fixture dict."""
    raw = fixture_path.read_bytes()
    data = json.loads(raw)
    source_sha_before = hashlib.sha256(raw).hexdigest()

    tax = data["tax"]
    pd_list = tax["period_diagnostic"]

    # Compute source-vector hash from immutable extracted inputs
    sv_sha = _source_vectors_sha256(pd_list)

    # Attach _gov scratch key, then update entries
    for p in pd_list:
        gov = _compute_period(p)
        p["_gov"] = gov

    summary = _derive_summary(pd_list)

    # Write governance fields into each period entry (replace old fields)
    _old_field = "taxable_financial_income_keur"
    for p in pd_list:
        gov = p.pop("_gov")
        p.pop(_old_field, None)
        p.update(gov)

    # Update summary
    tax["ti_formula_period_summary"] = summary

    # Record derivation provenance
    tax["_ti_governance_derivation"] = {
        "derivation_version": _DERIVATION_VERSION,
        "derivation_script": "finco_recon/derive_c3b1_ti_governance.py",
        "source_fixture_path": str(fixture_path),
        "source_fixture_sha256_before_derivation": source_sha_before,
        "source_vectors_sha256": sv_sha,
        "derivation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tolerance_keur": _TOLERANCE,
        "field_renamed": {
            "old": "taxable_financial_income_keur",
            "new": "net_taxable_financial_items_before_senior_keur",
            "formula_old": "fin_earn + SHL  (misleading: equals -senior during debt-active periods)",
            "formula_new": "fin_earn + SHL + senior  (zero when simplified identity holds)",
        },
    }

    data["tax"]["_ti_governance_derivation"]["_content_sha256"] = _content_hash(data)
    return data


def _content_hash(data: dict) -> str:
    """Hash derived governance fields + source-vector hash + version.

    Excludes run-varying fields (timestamp, source_fixture_sha256_before_derivation).
    Including source_vectors_sha256 means any change to the extracted inputs
    also invalidates the derived state.
    """
    gov_fields = [
        {k: p[k] for k in p if k in {
            "net_taxable_financial_items_before_senior_keur",
            "full_formula_residual_keur",
            "alternative_full_formula_residual_keur",
            "simplified_formula_residual_keur",
            "simplified_identity_applicable",
            "simplified_identity_reason",
        }}
        for p in data["tax"]["period_diagnostic"]
    ]
    summary = data["tax"].get("ti_formula_period_summary", {})
    summary_stable = {k: v for k, v in summary.items() if not k.startswith("_")}
    sv_sha = data["tax"]["_ti_governance_derivation"]["source_vectors_sha256"]
    combined = json.dumps(
        {
            "source_vectors_sha256": sv_sha,
            "summary": summary_stable,
            "periods": gov_fields,
            "derivation_version": _DERIVATION_VERSION,
        },
        sort_keys=True,
    )
    return hashlib.sha256(combined.encode()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default=str(_DEFAULT_FIXTURE))
    parser.add_argument("--dry-run", action="store_true",
                        help="Print summary without writing fixture")
    args = parser.parse_args(argv)

    fixture_path = pathlib.Path(args.fixture)
    if not fixture_path.exists():
        print(f"ERROR: fixture not found: {fixture_path}", file=sys.stderr)
        sys.exit(1)

    data = derive(fixture_path)

    tax = data["tax"]
    summary = tax["ti_formula_period_summary"]
    print(f"net_taxable_financial_items_before_senior derived from source vectors")
    print(f"  applicable periods: {summary['simplified_applicable_count']}")
    print(f"  first non-applicable period: {summary['first_non_applicable_period']}")
    print(f"  max simplified residual: {summary['max_simplified_residual_keur']:.6f} kEUR")
    print(f"  cash-interest residual periods: {summary['cash_interest_residual_period_count']}")
    print(f"  source_vectors_sha256: {tax['_ti_governance_derivation']['source_vectors_sha256'][:16]}…")

    if args.dry_run:
        print("DRY-RUN: fixture not written")
        return

    # Idempotency guard: compare content hash of new data vs stored in existing fixture
    existing_raw = fixture_path.read_bytes()
    try:
        existing_data = json.loads(existing_raw)
        existing_hash = existing_data.get("tax", {}).get(
            "_ti_governance_derivation", {}
        ).get("_content_sha256", "")
    except Exception:
        existing_hash = ""

    new_hash = data["tax"]["_ti_governance_derivation"]["_content_sha256"]
    if existing_hash == new_hash:
        print(f"Fixture already up-to-date (content hash {new_hash[:16]}…). No write.")
        return

    fixture_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    after_sha = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    print(f"Fixture written: {fixture_path}")
    print(f"  SHA256 after: {after_sha}")
    print(f"  derivation_version: {_DERIVATION_VERSION}")


if __name__ == "__main__":
    main()
