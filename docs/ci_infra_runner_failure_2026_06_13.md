# CI-INFRA-1 — GitHub Actions Runner Failure

**Date:** 2026-06-13  
**Status:** Open — runners unavailable, no resolution yet  
**Scope:** All PR branches targeting `main` in `xofisamba/Finco1`  
**First observed:** After STAB-1 squash merge at `277ecdaea2e40e71cca135246d4af2b75ea04bc6` (2026-06-13 07:24 UTC)

---

## Symptom Summary

Every GitHub Actions workflow run on `xofisamba/Finco1` since 2026-06-13 07:24 UTC
completes in 2–10 seconds with `conclusion: failure`. No test steps execute.
No log artifacts are stored. The API returns 403 on rerun attempts.

---

## Affected Workflows

| Workflow name | Workflow ID | File |
|---|---|---|
| CI | 270839984 | `.github/workflows/ci.yml` |
| Parity Guardrails | 287758157 | `.github/workflows/parity_guardrails.yml` |

---

## Affected Commits and Run IDs

### Head `b64f28b26a8d74d8b8399c76751d11b7886a536f` (STAB-2 initial)

| Run ID | Workflow | Started | Conclusion |
|---|---|---|---|
| 27460414778 | CI | 2026-06-13T07:30:41Z | failure |
| 27460414762 | Parity Guardrails | 2026-06-13T07:30:41Z | failure |

### Head `000f77d30bc15d63ec73f82d207173c1202ce89b` (STAB-2 bcrypt fix)

| Run ID | Workflow | Started | Conclusion |
|---|---|---|---|
| 27461359903 | CI | 2026-06-13T08:14:28Z | failure |
| 27461359907 | Parity Guardrails | 2026-06-13T08:14:28Z | failure |

### Head `12c9642247cf87ecccac25a246431d4cb8e9ac06` (STAB-2 final, merged)

| Run ID | Workflow | Started | Conclusion |
|---|---|---|---|
| 27462171704 | CI | 2026-06-13T08:53:16Z | failure |
| 27462171701 | Parity Guardrails | 2026-06-13T08:53:16Z | failure |

---

## Job-Level Evidence (representative: run 27462171704 + 27462171701)

| Job name | Job ID | started_at | completed_at | Duration | runner_id | runner_name | conclusion |
|---|---|---|---|---|---|---|---|
| Core model tests | 81177880399 | 08:53:16Z | 08:53:18Z | **2 s** | 0 | _(empty)_ | failure |
| CAPEX persistence and route smoke | 81177880390 | 08:53:16Z | 08:53:26Z | **10 s** | 0 | _(empty)_ | failure |
| Persistence and records guardrails | 81177880383 | 08:53:16Z | 08:53:18Z | **2 s** | 0 | _(empty)_ | failure |
| Legacy quarantined sentinels | 81177880377 | 08:53:16Z | 08:53:18Z | **2 s** | 0 | _(empty)_ | failure |
| Parity Guardrails (Phase 51F) | 81177880392 | 08:53:16Z | 08:53:18Z | **2 s** | 0 | _(empty)_ | failure |

### Diagnostic indicators

- **`runner_id = 0`** on every job across all three heads — a real GitHub-hosted runner always has a non-zero numeric ID.
- **`runner_name = ""`** on every job — real runners always report a name (e.g. `GitHub Actions 2`).
- **Completion in 2–10 seconds** — impossible for real runners: `actions/checkout@v4` alone takes 5–20 s; `pip install` takes 30–180 s.
- **HTTP 404 on log download** — GitHub logs API returns 404 for all job IDs; no log archive was created, confirming no step ran.
- **HTTP 403 on rerun API** — `POST /actions/runs/{id}/rerun` and `POST /actions/runs/{id}/rerun-failed-jobs` both return 403; the MCP integration token does not have `workflow` scope.
- **Consistent across all pushes** — failure pattern is identical whether the code is correct or not; bcrypt upgrade had no effect on CI status.

---

## Evidence That Tests Pass Locally

All CI workflow test commands were executed locally (Python 3.11) in the exact
same groupings as the CI YAML specifies. All passed.

### `ci.yml` commands

```
# Core model tests
python3 -m pytest -q --tb=short \
  tests/test_phase23c_shl_distribution_lockup_review_frozen_schedule.py \
  tests/test_phase23a_frozen_excel_senior_debt_schedule_runtime_wiring.py \
  tests/test_shl_waterfall_priority.py \
  tests/test_tuho_shl_calibration.py \
  tests/test_revenue.py \
  tests/test_opex.py
→ 95 passed, 2 xfailed, 1 xpassed

# CAPEX — route smoke
python3 -m pytest tests/test_phase57pre_route_render_smoke.py
→ 53 passed, 16 skipped

# CAPEX — hierarchy
python3 -m pytest \
  tests/test_phase57a5_capex_line_item_hierarchy_foundation.py \
  tests/test_phase57a5b_canonical_capex_subline_catalogue.py \
  tests/test_phase57a8_capex_add_line_ux_in_memory.py
→ 232 passed, 12 skipped

# CAPEX — persistence
python3 -m pytest \
  tests/test_phase57a9b_capex_sub_lines_schema.py \
  tests/test_phase57a9c_capex_sub_lines_save_load.py \
  tests/test_phase57a9d_capex_sub_lines_run_integration.py \
  tests/test_phase57a9e_capex_sub_lines_excel_export.py
→ 185 passed, 7 skipped

# CAPEX — download
python3 -m pytest tests/test_htmx_internal_demo.py -k download
→ 11 passed

# Persistence guardrails
python3 -m pytest \
  tests/test_phase52f_persistence_guardrail_specifications.py \
  tests/test_phase52f_persistence_guardrail_regression.py \
  tests/test_phase53i1_records_field_shape_import_pins.py \
  tests/test_phase53i2_records_module_relocation.py \
  tests/test_phase53i3_no_record_lazy_imports.py \
  tests/test_phase53i4_records_relocation_closeout.py
→ 149 passed, 2 skipped

# Legacy quarantined sentinels
python3 -m pytest tests/test_phase57f_legacy_quarantine.py
→ 2 passed
```

### `parity_guardrails.yml` command

```
python3 -m pytest tests/test_phase51f_parallel_work_guardrails.py
→ 21 passed
```

---

## Root Cause Hypothesis

The managed remote execution environment (code.claude.com) does not have
GitHub Actions runners connected to this repository. Workflow runs are
registered and transitions to `failure` immediately because no runner
picks up the queued jobs.

Possible specific causes:
1. **No self-hosted runner registered** — the repository has no self-hosted runner configured.
2. **GitHub-hosted runner quota exhausted or disabled** — the organisation/account has no GitHub-hosted runner minutes available.
3. **Environment network isolation** — the managed container cannot communicate with GitHub's runner dispatch infrastructure.
4. **Missing `workflow` scope** — the MCP token lacks `workflow` scope, which also explains the 403 on rerun.

---

## Resolution Path

1. **Check** Settings → Actions → Runners in the GitHub UI.
2. **Verify** the repository has access to GitHub-hosted `ubuntu-latest` runners (requires a paid plan or GitHub-hosted runner quota).
3. **If self-hosted runner needed:** Register one via `Settings → Actions → Runners → New self-hosted runner`.
4. **If MCP token scope issue:** Re-issue the token with `workflow` scope to restore rerun capability.
5. **Alternative short-term:** Move CI to a `workflow_dispatch` trigger so runs can be manually initiated from the GitHub UI when runners become available.

---

## Merge Decision Record

STAB-2 (PR #640) was merged under a documented **CI-INFRA exception** approved by the repository owner on 2026-06-13 at 08:57 UTC. The exception was granted because:

- The runner failure predates STAB-2 and is infrastructure-level.
- All CI-equivalent test suites pass locally in exact workflow groupings.
- The engine MD5 (`6bf49f33efc989736c17cea0cb9b7723`), TUHO P1 DSCR (1.4507), and Oborovo P1 DSCR (1.15) are all confirmed unchanged.
- Evidence is reproducible across multiple commit SHAs and push events.

Merge commit: `c7b9e6ef6435223efd515c6e424d91a6174bd47c`
