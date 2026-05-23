#!/usr/bin/env python3
"""Build the Phase 10 calibration reconciliation pack artifacts."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.export.calibration_reconciliation import (  # noqa: E402
    DEFAULT_GAP_REGISTER,
    DEFAULT_SOURCE_INVENTORY,
    DEFAULT_SUMMARY,
    DEFAULT_WORKBOOK,
    write_calibration_reconciliation_pack,
)


def main() -> int:
    artifacts = write_calibration_reconciliation_pack(
        workbook_path=DEFAULT_WORKBOOK,
        gap_register_path=DEFAULT_GAP_REGISTER,
        source_inventory_path=DEFAULT_SOURCE_INVENTORY,
        summary_path=DEFAULT_SUMMARY,
    )
    print(artifacts.workbook_path)
    print(artifacts.gap_register_path)
    print(artifacts.source_inventory_path)
    print(artifacts.summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
