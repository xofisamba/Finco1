# Phase 51R-2 — POST /scenarios/{scenario_id}/update-overrides route vertical extraction

> **Phase 51R-2** — vertical extraction.

## Summary

**New module:** `app/services/scenario_update_overrides_service.py` (~7,500 bytes, 6 callables).

**Service API:**

```python
@dataclass
class ScenarioUpdateOverridesRouteOutcome:
    template_name: str = "partials/scenario_tab.html"
    context: dict = field(default_factory=dict)
    payload: dict = field(default_factory=dict)
    status_code: int = 200
    headers: dict = field(default_factory=dict)
    rendered_response: Any = None

@dataclass
class ScenarioUpdateOverridesRouteDeps:  # 6 callables
    get_scenario
    update_scenario_overrides
    get_project_record
    get_workspace_state
    list_scenarios
    build_scenario_tab_context

async def execute_scenario_update_overrides_route(
    *,
    request, scenario_id, overrides, user, deps,
) -> ScenarioUpdateOverridesRouteOutcome:
    ...
```

## Tests

- 29 new in test_phase51r2 (all pass)
- 56 R-1 re-pointed (all pass)
- 21 guardrails (all pass)
- **Total: 106/106 ✓**

## Phase 51F guardrails: PASS (21/21)
## rc1: untouched

## Ready for merge

Behavior-preserving. All 10 quirks preserved. No production code outside route + new service.
