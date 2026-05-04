# Enterprise Data Model — Finco1

## Overview

Finco1 uses a structured data model to capture project configuration,
scenario definitions, run metadata, and financial results for audit and
comparison purposes.

---

## Project

Represents a project configuration (solar/wind/bess).

```json
{
  "project_id": "SOLAR-001",
  "name": "Oborovo Solar Farm",
  "project_type": "solar",
  "asset_class": "solar_pv",
  "company": "SolarCo d.o.o.",
  "created_at": "2026-05-01T10:00:00Z"
}
```

Fields:
- `project_id`: unique identifier (from ProjectInfo.code)
- `name`: human-readable name
- `project_type`: solar | wind | bess | hybrid
- `asset_class`: civil_grid | wind | battery | hybrid
- `company`: entity name

---

## Scenario

Represents a scenario configuration (Base/Downside/Upside or custom).

```json
{
  "scenario_id": "base",
  "name": "Base Case",
  "capex_multiplier": 1.0,
  "opex_multiplier": 1.0,
  "degradation_multiplier": 1.0,
  "curtailment_multiplier": 1.0,
  "tariff_multiplier": 1.0,
  "description": "Central case assumptions"
}
```

Relationships:
- Scenario applies to a Project
- Multiple scenarios per project

---

## Run

Represents a single execution of the model.

```json
{
  "run_id": "run-2026-05-04-001",
  "project_id": "SOLAR-001",
  "scenario_id": "base",
  "timestamp": "2026-05-04T14:30:00Z",
  "model_version": "industry-engine-refactor",
  "git_sha": "9ffbc2d",
  "duration_ms": 1523,
  "warnings": ["W_DSCR_BELOW_TARGET"],
  "notes": "First validation run"
}
```

Relationships:
- Run references a Project and Scenario
- Run produces a Result

---

## Result

Represents the financial output of a run.

```json
{
  "run_id": "run-2026-05-04-001",
  "project_type": "solar",
  "project_irr": 0.1234,
  "equity_irr": 0.1567,
  "total_revenue_keur": 45678,
  "total_ebitda_keur": 34567,
  "target_dscr": 1.20,
  "actual_min_dscr": 1.35,
  "actual_avg_dscr": 1.48,
  "senior_debt_keur": 35000,
  "total_distribution_keur": 22000
}
```

Relationships:
- Result belongs to a Run
- Result has many Period records

---

## Assumptions

Represents a committed set of project inputs.

```json
{
  "assumptions_id": " assumptions-2026-05-04-001",
  "project_id": "SOLAR-001",
  "scenario_id": "base",
  "created_at": "2026-05-04T14:25:00Z",
  "hash": "sha256:abc123...",
  "inputs_snapshot": { ... }
}
```

Relationships:
- Assumptions reference a Project and Scenario
- Assumptions are immutable once created

---

## Version

Represents a model version.

```json
{
  "version": "1.0.0",
  "git_sha": "9ffbc2d",
  "branch": "industry-engine-refactor",
  "released_at": "2026-05-04"
}
```

---

## Relationships Summary

```
Project (1) ─── (N) Scenario
  │                   │
  │                   │
  ▼                   ▼
Assumptions        Run
  │                   │
  │                   │
  └──► Run ───────────┘
            │
            ▼
          Result
            │
            ▼
        Period (N)
```

---

## Future Extension

In Phase 3, add:
- Portfolio: links multiple Projects to a single Run
- RunComparison: diff between two Runs
- AuditLog: immutable chain of assumption changes