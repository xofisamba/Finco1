# Phase 51S-2 — POST /scenarios/{scenario_id}/select route vertical extraction

> **Phase 51S-2** — vertical extraction.

## Summary

**New module:** `app/services/scenario_select_service.py` (~6,300 bytes, 6 callables).

**Service API:**

```python
@dataclass
class ScenarioSelectRouteOutcome:
    template_name: str = "partials/scenario_tab.html"
    context: dict = field(default_factory=dict)
    payload: dict = field(default_factory=dict)
    status_code: int = 200
    headers: dict = field(default_factory=dict)
    rendered_response: Any = None

@dataclass
class ScenarioSelectRouteDeps:  # 6 callables
    get_scenario
    select_scenario
    get_workspace_state
    get_project_record
    list_scenarios
    build_scenario_tab_context

async def execute_scenario_select_route(
    *,
    request, scenario_id, user, deps,
) -> ScenarioSelectRouteOutcome:
    ...
```

## Tests

- 27 new in test_phase51s2 (all pass)
- 54 S-1 re-pointed (all pass)
- 21 guardrails (all pass)
- **Total: 102/102 ✓**

## Phase 51F guardrails: PASS (21/21)
## rc1: untouched

## Ready for merge

Behavior-preserving. All 10 quirks preserved. No production code outside route + new service.
