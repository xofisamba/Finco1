"""finco_recon.extract_oborovo_opex_structure — Deterministic OPEX structural truth extraction.

Reads the authoritative Oborovo workbook (SHA256-verified) and emits
tests/fixtures/excel_oborovo_opex_structural_truth.json.

This script is SOURCE TRUTH ONLY.  It performs zero financial computation
and changes no runtime code.  Run it only when the authoritative workbook
is updated and the fixture must be refreshed.

Usage:
    python3 -m finco_recon.extract_oborovo_opex_structure \\
        --workbook <path/to/workbook.xlsm> \\
        [--out tests/fixtures/excel_oborovo_opex_structural_truth.json]

Exit codes:
    0 — fixture written (or --dry-run: printed to stdout).
    1 — SHA256 mismatch or structural assertion failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl not installed. Run: pip install openpyxl", file=sys.stderr)
    sys.exit(1)

EXPECTED_SHA256 = "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920"

# OpEx sheet column indices (1-based, openpyxl)
_COL_CODE = 1       # A: category/subitem code
_COL_NAME = 2       # B: line-item name
_COL_BUDGET = 3     # C: budget kEUR
_COL_INFLATION = 4  # D: annual inflation rate
_COL_WHT = 5        # E: withholding tax
_COL_Y1 = 6         # F: Year 1 flag/value
_COL_Y30 = 35       # AE: Year 30 flag/value
_N_YEARS = 30

# Category (aggregate) rows on OpEx sheet: (code, row, name)
_CATEGORY_ROWS = [
    ("B.01", 3),
    ("B.02", 8),
    ("B.03", 26),
    ("B.04", 31),
    ("B.05", 35),
    ("B.06", 39),
    ("B.07", 45),
    ("B.08", 48),
    ("B.09", 53),
    ("B.10", 58),
    ("B.11", 65),
    ("B.12", 70),
    ("B.13", 76),
]

# Totals rows
_ROW_TOTAL_EXCL = 95
_ROW_TOTAL_INCL = 96

# Inputs cells
_INPUTS_INFLATION_CELL = (85, 4)   # D85
_INPUTS_DEBT_TENOR_1_CELL = (196, 4)  # D196
_INPUTS_DEBT_TENOR_2_CELL = (259, 4)  # D259

# Scenarios column for base-case values
_SCENARIOS_COL = 5  # E


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_flags(ws, row: int) -> list:
    return [ws.cell(row=row, column=col).value for col in range(_COL_Y1, _COL_Y30 + 1)]


def _read_annual(ws, row: int) -> list:
    return [ws.cell(row=row, column=col).value for col in range(_COL_Y1, _COL_Y30 + 1)]


def extract(workbook_path: Path) -> dict:
    """Extract OPEX structure from workbook and return fixture dict."""
    # 1. Verify SHA256
    digest = _sha256(workbook_path)
    if digest != EXPECTED_SHA256:
        raise ValueError(
            f"SHA256 mismatch.\n"
            f"  expected: {EXPECTED_SHA256}\n"
            f"  actual:   {digest}\n"
            f"The authoritative workbook has changed.  Update EXPECTED_SHA256 "
            f"only after confirming the new file is the correct authoritative source."
        )

    wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)

    ws_opex = wb["OpEx"]
    ws_inputs = wb["Inputs"]

    # 2. Read Inputs
    inflation_rate = ws_inputs.cell(*_INPUTS_INFLATION_CELL).value
    debt_tenor_1 = ws_inputs.cell(*_INPUTS_DEBT_TENOR_1_CELL).value
    debt_tenor_2 = ws_inputs.cell(*_INPUTS_DEBT_TENOR_2_CELL).value

    # 3. Read totals
    total_excl_row = ws_opex.cell(_ROW_TOTAL_EXCL, _COL_BUDGET).value
    total_incl_row = ws_opex.cell(_ROW_TOTAL_INCL, _COL_BUDGET).value
    total_excl_y1 = ws_opex.cell(_ROW_TOTAL_EXCL, _COL_Y1).value
    total_incl_y1 = ws_opex.cell(_ROW_TOTAL_INCL, _COL_Y1).value

    # 4. Read each category
    categories: dict[str, dict] = {}
    for code, row in _CATEGORY_ROWS:
        name = ws_opex.cell(row, _COL_NAME).value
        budget = ws_opex.cell(row, _COL_BUDGET).value
        inflation = ws_opex.cell(row, _COL_INFLATION).value
        wht = ws_opex.cell(row, _COL_WHT).value
        annual = _read_annual(ws_opex, row)
        entry: dict = {
            "code": code,
            "name": name,
            "budget_keur": budget,
            "inflation_rate": inflation,
            "wht": wht,
            "opex_row": row,
            "annual_values_y1_y30": annual,
        }
        if code == "B.13":
            entry["contingency_rate"] = inflation  # D column holds rate for B.13
        categories[code] = entry

    # 5. Read subitems for key structural rows
    subitems: dict[str, list[dict]] = {}

    def _subitem(row: int, code_override: str | None = None) -> dict:
        return {
            "code": code_override or ws_opex.cell(row, _COL_CODE).value,
            "name": ws_opex.cell(row, _COL_NAME).value,
            "budget_keur": ws_opex.cell(row, _COL_BUDGET).value,
            "opex_row": row,
            "activation_flags": _read_flags(ws_opex, row),
        }

    subitems["B.01"] = [_subitem(r) for r in [4, 5, 6, 7]]
    subitems["B.02"] = [_subitem(r) for r in [9, 10, 11, 14, 15, 16]]
    subitems["B.03"] = [_subitem(r) for r in [27, 28, 30]]
    subitems["B.04"] = [_subitem(r) for r in [32, 33, 34]]
    subitems["B.05"] = [_subitem(r) for r in [36, 37, 38]]
    subitems["B.06"] = [_subitem(r) for r in [40, 41, 42, 43, 44]]
    subitems["B.07"] = [_subitem(r) for r in [46, 47]]
    subitems["B.08"] = [_subitem(r) for r in [49, 50, 51, 52]]
    subitems["B.09"] = [_subitem(r) for r in [54, 55, 56, 57]]
    subitems["B.10"] = [_subitem(r) for r in [59, 60, 61, 62, 63, 64]]
    subitems["B.11"] = [_subitem(r) for r in [66, 67, 68, 69]]
    subitems["B.12"] = [_subitem(r) for r in [71, 72, 73, 74, 75]]

    return {
        "_meta": {
            "description": "Authoritative OPEX structural truth extracted from Oborovo sensitivity workbook",
            "source_file": workbook_path.name,
            "source_sha256": EXPECTED_SHA256,
            "sheet": "OpEx",
            "scenarios_sheet": "Scenarios",
            "inputs_sheet": "Inputs",
        },
        "inputs": {
            "inflation_rate": inflation_rate,
            "source_cell": "Inputs!D85",
            "senior_debt_tenor_1": debt_tenor_1,
            "senior_debt_tenor_1_cell": "Inputs!D196",
            "senior_debt_tenor_2": debt_tenor_2,
            "senior_debt_tenor_2_cell": "Inputs!D259",
            "b11_active_until_year": debt_tenor_1,
            "b11_activation_formula": "=IF(year<=Inputs!$D$196,1,0)",
        },
        "categories": {code: {**cat, "subitems": subitems.get(code, [])} for code, cat in categories.items()},
        "totals": {
            "total_opex_excl_contingencies_budget": total_excl_row,
            "total_opex_incl_contingencies_budget": total_incl_row,
            "total_opex_excl_contingencies_y1": total_excl_y1,
            "total_opex_incl_contingencies_y1": total_incl_y1,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", required=True, type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).parents[1] / "tests" / "fixtures" / "excel_oborovo_opex_structural_truth.json",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing file")
    args = parser.parse_args()

    if not args.workbook.exists():
        print(f"ERROR: workbook not found: {args.workbook}", file=sys.stderr)
        return 1

    try:
        data = extract(args.workbook)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    output = json.dumps(data, indent=2, ensure_ascii=False)

    if args.dry_run:
        print(output)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
        print(f"Fixture written: {args.out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
