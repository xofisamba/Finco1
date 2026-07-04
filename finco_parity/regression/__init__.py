"""
finco_parity.regression — Parametrised regression tests.

Populated during V2-4. Will contain pytest parametrised tests that:
1. Load a fixture from finco_parity.fixtures
2. Run the extracted engine via finco_core
3. Compare all KPI outputs against finco_parity.golden baselines
4. Assert within the RC2 tolerance windows

A failing regression test means parity drift — the extraction milestone
may not be merged until all regression tests are green.
"""
