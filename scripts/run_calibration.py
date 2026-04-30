"""Run headless Excel calibration payload generation.

Usage:
    python scripts/run_calibration.py --project oborovo --output /tmp/oborovo.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.calibration import available_project_keys, run_project_calibration


def main() -> int:
    parser = argparse.ArgumentParser(description="Run headless waterfall calibration payload generation")
    parser.add_argument("--project", default="oborovo", help="Project key, e.g. oborovo or tuho when available")
    parser.add_argument("--output", default="", help="Optional JSON output path")
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation")
    args = parser.parse_args()

    payload = run_project_calibration(args.project)
    encoded = json.dumps(payload, indent=args.indent, ensure_ascii=False)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"Calibration failed: {exc}")
        print(f"Available project keys: {', '.join(available_project_keys())}")
        raise SystemExit(2)
