"""finco_recon — Oborovo Excel↔Python reconciliation framework.

Generates an audit-grade Excel workbook comparing the authoritative source
Excel model against the clean Python financial engine.

Usage::

    python -m finco_recon.generate_oborovo
    python -m finco_recon.generate_oborovo --output artifacts/reconciliation/oborovo_excel_python_reconciliation.xlsx

Exit codes:
  0  Workbook generated successfully.
  1  Unexpected error.

Import boundary
---------------
This package may import from:
  - Python standard library
  - finco_parity.*
  - financial_engine.*
  - app.project_factories (factory inputs only)
It must NOT modify financial_engine.* or finco_parity.baselines.*
"""
