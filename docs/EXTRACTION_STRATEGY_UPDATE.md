# Extraction Strategy — Clarification and Updated Roadmap

**Date**: 2026-07-04  
**Supersedes**: Part 5 (Milestone Roadmap) of `docs/FINCO_V2_CONTROLLED_EXTRACTION_PLAN.md`  
**Status**: Active — binding

---

## Clarification: Extraction Happens Inside Finco1

The original `FINCO_V2_CONTROLLED_EXTRACTION_PLAN.md` described the target architecture without specifying where the extraction work would be performed.

This document clarifies:

**All extraction milestones V2-1 through V2-9 are executed inside the `xofisamba/Finco1` repository.**

`Finco2` is not created yet. `Finco2` will not be created during extraction. `Finco2` is created only after extraction is complete and parity is proven.

### Rationale

Working inside Finco1 during extraction provides:

1. **Full access to the reference baseline** — the engine, tests, fixtures, and golden outputs are all in the same repository; no cross-repo coordination is required during the port
2. **Parity validation in place** — the existing parity guardrail tests (Phase 51F) can be run against the extracted code without moving fixtures first
3. **Linear git history** — every extraction step is visible in the same history as the baseline it extracted from; the diff between RC2 and any milestone is unambiguous
4. **Safe iteration** — if an extraction step produces parity drift, the reference is immediately available without checkout-switching between repositories

### When Finco2 Is Created

Finco2 is created when all of the following are true:

- [ ] Engine extraction complete (V2-3 merged)
- [ ] Parity reproduced against RC2 baselines (V2-4 merged)
- [ ] Architecture stabilised (V2-5 merged)
- [ ] Migration validated (engineering review complete)

At that point the extracted code is copied into `xofisamba/Finco2` as a clean repository with no Finco1 shell, no legacy phase tests, no generated reports, and no identity-dispatch patterns.

### What Finco2 Will Not Inherit

- The `app/` shell (Streamlit monolith)
- `streamlit_app.py`
- Legacy phase-history test noise
- Generated reports (`reports/`)
- ~400 SQLite `.db` files from phase development
- Identity-dispatch patterns (eliminated in Stack AC + Phase 0 Y3, but the shell that contained them is not ported)
- Post-engine mutation patterns (eliminated in Phase 0 Z2)
- `app/export/calibration_reconciliation.py` (3,409 lines duplicating engine calculations)

### What Finco2 Will Receive

- The entire `domain/` financial kernel (Direct Port)
- The extracted `finco_core/` package (V2-1 through V2-3)
- The parity fixtures and golden harness (V2-4)
- The typed audit and export contracts (V2-5)
- The clean API shell (V2-6)
- The `finco_ui/` product UI (V2-7)
- The persistence layer (V2-8)

---

## Updated Milestone Roadmap

```
RC2 Freeze
    Branch: Finco1-RC2
    SHA: b52d39c79683a1ff6965ef197422056a541a81ab
    Status: COMPLETE

          ↓

V2-1 Repository Skeleton
    Location: Finco1/main (new top-level package skeleton)
    Deliverable: finco_core/, finco_app/, finco_parity/ directory structure
    No financial logic. No copied engine code.
    pyproject.toml. .gitignore. Package __init__.py files only.

          ↓

V2-2 Inputs
    Location: Finco1/main
    Deliverable: finco_core/inputs/ — port ProjectInputs, FinancingParams,
                 ProjectInfo, and supporting models from domain/inputs.py
    Parity gate: inputs round-trip test against RC2 fixture

          ↓

V2-3 Engine
    Location: Finco1/main
    Deliverable: finco_core/engine/ — port waterfall engine, tax engine,
                 debt engine, SHL engine from domain/
    Parity gate: TUHO and Oborovo outputs match RC2 baselines

          ↓

V2-4 Parity Harness
    Location: Finco1/main
    Deliverable: finco_parity/ — port TUHO and Oborovo fixtures and
                 golden regression tests; CI pipeline added
    Parity gate: all 21 guardrails green against finco_core

          ↓

V2-5 Audit and Export Contracts
    Location: Finco1/main
    Deliverable: typed AuditResult, ExportResult output contracts;
                 no post-engine mutation anywhere in the call chain

          ↓

V2-6 API Shell
    Location: Finco1/main
    Deliverable: finco_app/api/ — minimal FastAPI around finco_core engine;
                 no UI dependency

          ↓

V2-7 UI Shell
    Location: Finco1/main
    Deliverable: finco_ui/ — minimal product UI branded as Finco One;
                 depends only on API contract, not on engine

          ↓

V2-8 Persistence
    Location: Finco1/main
    Deliverable: finco_app/persistence/ — projects, scenarios, runs,
                 audit snapshots, exports

          ↓

V2-9 Commercial Beta Baseline
    Location: Finco1/main
    Deliverable: pilot-ready baseline; all parity green; all contracts stable

          ↓

Engineering Review Gate
    All extraction milestones passed.
    Parity reproduced against RC2 baselines.
    Architecture stabilised and reviewed.
    Migration validated.

          ↓

Repository Split
    Copy extracted architecture from Finco1 into xofisamba/Finco2.
    Finco2 receives only the extracted packages — no Finco1 shell.
    Finco1 enters archive state.

          ↓

Finco2 Created
    Clean repository with clean architecture.
    Product brand: Finco One.
    Development continues in Finco2.

          ↓

Finco1 Archived
    Finco1-RC2 branch preserved permanently as frozen audit reference.
    Finco1 main receives no further development.
```

---

## Engineering Policy

### Finco1 main during extraction

- Feature branches for each V2-x milestone
- Each milestone PR merges to `main`
- No modification to `Finco1-RC2` branch
- Parity guardrails must remain green on `main` at all times

### Parity protection

- RC2 baselines (see `docs/RC2_BASELINE.md`) are the permanent reference
- No milestone is complete until the extracted engine produces identical outputs
- Tolerance windows are unchanged: IRR ±0.05%, DSCR ±0.001, distributions ±200 kEUR, tax ±500 kEUR

### What does not move

The following are never ported to `finco_core/` or `Finco2`:

- Streamlit application shell
- Phase-history tests (`test_stack_*.py`, `test_phase*.py` where they test shell behaviour rather than engine behaviour)
- Generated report files
- SQLite `.db` files
- `app/export/calibration_reconciliation.py` (dead weight — duplicates engine calculations)

---

*This document is binding from the date above. Supersedes the milestone ordering in Part 5 of `FINCO_V2_CONTROLLED_EXTRACTION_PLAN.md`.*
