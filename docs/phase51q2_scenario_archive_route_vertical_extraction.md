# Phase 51Q-2 — POST /scenarios/{scenario_id}/archive route vertical extraction

> **Phase 51Q-2** — vertical extraction of the
> `/scenarios/{scenario_id}/archive` route family
> (single canonical POST route, handler
> `archive_scenario_endpoint`) into a new dedicated service module.

## Summary

**New module:** `app/services/scenario_archive_service.py`
(~6,500 bytes, 9 callables).

**Service API:**

```python
@dataclass
class ScenarioArchiveRouteOutcome:
    status_code: int = 200
    payload: dict = field(default_factory=dict)
    rendered_response: Any = None

@dataclass
class ScenarioArchiveRouteDeps:  # 9 callables
    get_scenario
    archive_scenario
    get_project_by_code
    list_scenarios
    get_scenario_history
    list_exports
    build_export_lineage
    get_workspace_state
    render_scenario_workspace

async def execute_scenario_archive_route(
    *,
    request: Any,
    scenario_id: str,
    user: Any,
    deps: ScenarioArchiveRouteDeps,
) -> ScenarioArchiveRouteOutcome:
    ...
```

## Route thinned

| Metric | Pre-Q-2 (Q-1) | Post-Q-2 (51Q-2) | Delta |
|---|---|---|---|
| `/scenarios/{id}/archive` total lines | 50 | 70 | +20 (+40%) |
| `/scenarios/{id}/archive` non-blank | 47 | 65 | +18 (+38%) |

> Route did NOT shrink significantly because the
> `_render_with_summary_cards` wrapper (which builds the
> `scenario_summary_cards` list) was kept in the route. The
> orchestration body (scenario lookup, gate, archive call,
> project/scenario/history/exports/lineage/workspace_state
> lookups, render call) has moved to the service.

## Behaviors preserved (10 quirks, 9 from P-1 + soft-archive-specific)

- Soft archive (no delete)
- 404 if scenario not found
- `archive_scenario(user.user_id, scenario_id)` — NO third arg
- Full workspace re-render
- Same list_scenarios / get_scenario_history / list_exports / build_export_lineage parameters
- `include_archived=False` (archived scenario won't show)
- `scenario_summary_cards` built by iterating scenarios (in route wrapper)
- Success message uses `record.scenario_name`
- No HTMX headers, no form input
- Positional `get_scenario(scenario_id, user.user_id)`

## Tests

- 30 new in test_phase51q2 (all pass)
- 53 Q-1 re-pointed (all pass)
- 21 guardrails (all pass)
- **Total: 104/104 ✓**

## Phase 51F guardrails: PASS (21/21)
## rc1: untouched

## Ready for merge

Behavior-preserving. No production code outside route + new service. All quirks preserved.
