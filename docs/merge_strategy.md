# Merge Strategy — post-rc1-structure-roadmap

_Generated: 2026-05-06_

---

## 1. Current Branch Inventory

| Branch | Status | Contents |
|--------|--------|----------|
| `rc1` | **Frozen** | v1.0.0-rc1 baseline. No further changes. Hotfixes only via cherry-pick to `rc1`-derived patch branch. |
| `post-rc1-structure-roadmap` | **Active** | Advanced CAPEX engine (`app/capex_engine.py`), ScenarioManager foundation, UI polish, documentation. |
| `feature/api-wrapper` | **Active** | FastAPI wrapper for the model, exposes HTTP endpoints for core model runs. |
| `feature/cli-runner` | **Exists** | CLI entrypoint (`cli/`) — currently missing from `post-rc1-structure-roadmap` (test failing because `cli` module not present on this branch). |

---

## 2. What Each Branch Contains

### `rc1` (frozen)
- Stable: `streamlit_app.py`, domain engines (waterfall, debt, revenue, tax, depreciation), scenario logic (legacy path), portfolio runner.
- Includes: Basic OPEX (OpexItem), CAPEX (CapexItem defaults), Excel export.
- **Do not merge anything into `rc1` without explicit approval.**

### `post-rc1-structure-roadmap`
- CAPEX line-item engine (`app/capex_engine.py`) with matrix UI in CapEx tab.
- ScenarioManager (`app/scenario_manager.py`) — clean scenario dataclass + manager, wired into `run_demo_project()`.
- Advanced OPEX line-item engine (`app/opex_engine.py`) with matrix UI in OPEX tab.
- UI polish: status badges, version display, KPI section headers, divider usage.
- Documentation: `ARCHITECTURE.md`, `pre_claude_review_summary.md`.
- Deprecation shims for legacy scenario path.

### `feature/api-wrapper`
- FastAPI app (`main_api.py`) with endpoints for project run, scenario run, Excel export.
- Request/response schemas, error handling.
- Ties into `app.ui_runner.run_demo_project()`.

### `feature/cli-runner`
- Click-based CLI (`cli/`) with `run` command — same execution path as `run_demo_project()`.
- Same execution path as `run_demo_project()`.
- **Note:** This branch exists but `cli` module is not present on `post-rc1-structure-roadmap` — tests fail because they import `cli`.

---

## 3. Recommended Merge Order

```
Step 1 ── Stabilize post-rc1-structure-roadmap
         │
         ├─ Fix test_cli.py failure (cli module missing on this branch)
         │    Option A: Merge post-rc1-structure-roadmap ← feature/cli-runner
         │    Option B: Skip test_cli.py on this branch; mark for resolution pre-merge
         │
         ├─ Smoke test passes (see §6)
         └─ PR review

Step 2 ── Review & merge feature/api-wrapper
         │
         ├─ Verify API contract against internal B2B requirements
         ├─ Confirm /health, /run, /export endpoints
         └─ Run integration smoke test against post-rc1-structure-roadmap

Step 3 ── Review & merge feature/cli-runner
         │
         ├─ After post-rc1-structure-roadmap is stable
         ├─ Verify all CLI commands work
         └─ CLI test should pass on merged target

Step 4 ── Integrate advanced CAPEX depreciation into waterfall
         (known limitation: CAPEX depreciation uses legacy CapexItem path,
          not CapexLineItem breakdown — must resolve before full RC2)

Step 5 ── HTMX portal (future, separate roadmap)
         Not for RC2. Separate workstream.
```

---

## 4. What Must NOT Merge Yet

1. **CLI runner into `rc1`** — not reviewed, could introduce breaking changes.
2. **API wrapper into `rc1`** — contract not finalized, internal B2B requirements not confirmed.
3. **Any HTMX work** — out of scope for RC2.
4. **`feature/cli-runner` into `post-rc1-structure-roadmap`** — without resolving the missing `cli` module gap (test will fail).
5. **Portfolio sponsor IRR placeholder** — not production-ready; must not ship as real IRR.

---

## 5. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CAPEX depreciation uses legacy path, not line-item breakdown | High | Medium | Document as known limitation; track for RC2 fix |
| CLI test failure on `post-rc1-structure-roadmap` (missing `cli` module) | High | Low | Option A: merge cli-runner first; Option B: mark test as expected-fail |
| API wrapper contract changes break internal B2B clients | Medium | High | Lock API contract doc before merging |
| ScenarioManager not fully covering all edge cases | Medium | Medium | Expand smoke test + add regression tests |
| Advanced OPEX performance at scale (>30 year horizon) | Low | Low | Already tested; monitor |

---

## 6. Smoke Test Criteria

Before merging `post-rc1-structure-roadmap` into `rc1`:

```bash
cd /root/.openclaw/workspace/finco1_new && git checkout post-rc1-structure-roadmap
python3 -c "
from app.ui_runner import run_demo_project
from app.capex_engine import build_capex_line_items_from_defaults
from app.opex_engine import build_opex_line_items_from_defaults

flows = [('Solar','Base'),('Solar','Downside'),('Wind','Base'),('Wind','Upside')]
for pt, sc in flows:
    r = run_demo_project(pt, sc).result
    print(f'{pt} {sc}: IRR={r.project_irr*100:.2f}%, minDSCR={r.actual_min_dscr:.3f}')

opex = build_opex_line_items_from_defaults('solar')
r1 = run_demo_project('Solar','Base').result
r2 = run_demo_project('Solar','Base', advanced_opex_line_items=opex).result
assert r2.project_irr != r1.project_irr, 'OPEX must affect IRR'

cap = build_capex_line_items_from_defaults('solar', 50.0)
r3 = run_demo_project('Solar','Base', advanced_capex_line_items=cap).result
assert r3.project_irr != r1.project_irr, 'CAPEX must affect IRR'
print('All smoke tests passed.')
"

python3 -m pytest tests/ -x -q  # skip test_cli if cli module missing
```

---

## 7. Rollback Plan

- **If smoke test fails after merge into `rc1`**: Revert the merge commit (git revert), investigate, fix in `post-rc1-structure-roadmap`, re-merge.
- **If API contract broken**: Revert API wrapper merge, lock contract version, re-introduce against pinned interface.
- **If CLI regression**: Revert CLI merge, keep CLI runner branch open, rebase after stabilization.

All rollbacks should be documented in the release notes.

---

## 8. Pre-Merge Checklist

- [ ] Smoke test passes (Python script above)
- [ ] `pytest tests/ -x -q` passes (or known-fail test_cli.py is documented)
- [ ] Advanced OPEX matrix editable and updates results on re-run
- [ ] Advanced CAPEX matrix editable and updates results on re-run
- [ ] ScenarioManager correctly applies Base/Downside/Upside for Solar/Wind
- [ ] Dashboard shows correct `actual_min_dscr` / `actual_avg_dscr`
- [ ] Excel export contains correct project_type in filename and Notes sheet
- [ ] No new `print()` statements or debug artifacts left in code
- [ ] Documentation (`ARCHITECTURE.md`, `pre_claude_review_summary.md`) up to date