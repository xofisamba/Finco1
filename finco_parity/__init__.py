"""
finco_parity — Finco One v2 parity harness.

This package contains the golden fixtures, regression tests, and parity
comparison infrastructure for validating the extracted financial engine
against the Legacy Engine Baseline (Finco1-RC2, SHA: b52d39c).

No application code lives here. No UI code. No persistence code.
This package depends only on finco_core.

Subpackages (populated during V2-4):
    fixtures    — TUHO Wind 1 and Oborovo Solar input fixtures
    golden      — Expected output baselines (from Finco1-RC2 reference run)
    regression  — Parametrised regression tests comparing extracted engine
                  output against golden baselines

Parity gate: every V2-3+ milestone PR must pass all tests in this package
before merge is permitted.
"""
