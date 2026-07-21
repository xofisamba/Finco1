"""finco_recon.generate_oborovo — CLI entry point for the Oborovo reconciliation workbook.

Usage::

    python -m finco_recon.generate_oborovo
    python -m finco_recon.generate_oborovo --output artifacts/reconciliation/oborovo_excel_python_reconciliation.xlsx

Exit codes:
  0  Workbook generated successfully.
  1  Unexpected error.
"""
from __future__ import annotations

import argparse
import pathlib
import sys


_DEFAULT_OUTPUT = pathlib.Path(
    "artifacts/reconciliation/oborovo_excel_python_reconciliation.xlsx"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m finco_recon.generate_oborovo",
        description="Generate the Oborovo Excel↔Python reconciliation workbook.",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=_DEFAULT_OUTPUT,
        metavar="PATH",
        help=f"Output path (default: {_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--abs-tol",
        type=float,
        default=None,
        metavar="KEUR",
        help="Override absolute materiality threshold (kEUR)",
    )
    parser.add_argument(
        "--rel-tol",
        type=float,
        default=None,
        metavar="FRAC",
        help="Override relative materiality threshold (fraction, e.g. 0.001)",
    )
    args = parser.parse_args(argv)

    output_path: pathlib.Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from finco_recon.materiality import MaterialitySettings, DEFAULT_MATERIALITY
        from finco_recon.sources import load_oborovo_sources
        from finco_recon.workbook import build_workbook

        mat = DEFAULT_MATERIALITY
        if args.abs_tol is not None or args.rel_tol is not None:
            mat = MaterialitySettings(
                absolute_keur=args.abs_tol if args.abs_tol is not None else mat.absolute_keur,
                relative_fraction=args.rel_tol if args.rel_tol is not None else mat.relative_fraction,
            )

        print("Loading Oborovo sources...", flush=True)
        sources = load_oborovo_sources()
        print(
            f"  Excel periods : {len(sources.excel)}\n"
            f"  Engine periods: {len(sources.engine)}\n"
            f"  Legacy periods: {len(sources.legacy) if sources.legacy else 'N/A'}",
            flush=True,
        )

        print(f"Building workbook → {output_path} ...", flush=True)
        wb = build_workbook(sources, output_path, materiality=mat)

        sheet_names = wb.sheetnames
        print(f"  Sheets ({len(sheet_names)}): {', '.join(sheet_names)}", flush=True)
        print("Done.", flush=True)
        return 0

    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
