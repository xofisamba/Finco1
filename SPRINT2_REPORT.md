# Sprint 2 — Arhitekturalni Decoupling
## Sprint Report

**Datum:** 2026-04-30
**Repo:** https://github.com/xofisamba/Finco1
**Branch:** main

---

## Cilj
Domain layer nema Streamlit imports (`@st.cache_data`, `streamlit` imports).
Sve Streamlit-specific stvari žive isključivo u `app/` layer.

---

## Taskovi

### S2-1: App Cache Layer ✅
**Commit:** `a99839c` + `fbbc037` (fix comments)
**Datoteka:** `app/cache.py`

Jedino mjesto gdje živi `@st.cache_data`. Domain je potpuno čist.

```python
# Hash functions
def hash_inputs_for_cache(inputs: "ProjectInputs") -> int: ...
def hash_engine_for_cache(engine: "PeriodEngine") -> int: ...

# Cached schedules
@st.cache_data(show_spinner=False, hash_funcs={...})
def cached_generation_schedule(inputs, engine, yield_scenario): ...

@st.cache_data(show_spinner=False, hash_funcs={...})
def cached_revenue_schedule(inputs, engine): ...

@st.cache_data(show_spinner=False, hash_funcs={...})
def cached_opex_schedule_annual(inputs, horizon_years): ...

@st.cache_data(show_spinner=False, hash_funcs={...})
def cached_model_state(inputs, engine): ...

@st.cache_data(show_spinner="⚙️ Računam waterfall...", hash_funcs={...})
def cached_run_waterfall_v3(...): ...

def clear_all_caches() -> None: ...
```

---

### S2-2: WaterfallRunner Orchestrator ✅
**Commit:** `a99839c`
**Datoteka:** `app/waterfall_runner.py`

UI pages pozivaju `runner.run(config)`, ne `run_waterfall()` direktno.

```python
@dataclass(frozen=True)
class WaterfallRunConfig:
    # Rate and tenor
    rate_per_period: float = 0.02825
    tenor_periods: int = 28
    # DSCR
    target_dscr: float = 1.15
    lockup_dscr: float = 1.10
    # Tax
    tax_rate: float = 0.10
    # DSRA
    dsra_months: int = 6
    # SHL
    shl_amount_keur: float = 0.0
    shl_rate: float = 0.0
    shl_idc_keur: float = 0.0
    shl_repayment_method: str = "bullet"  # "bullet"|"cash_sweep"|"pik"|"accrued"|"pik_then_sweep"
    shl_tenor_years: int = 0
    shl_wht_rate: float = 0.0
    # Returns
    discount_rate_project: float = 0.0641
    discount_rate_equity: float = 0.0965
    # Debt overrides
    fixed_debt_keur: Optional[float] = None
    fixed_ds_keur: Optional[float] = None
    # Methods
    equity_irr_method: str = "equity_only"   # "equity_only"|"combined"|"shl_plus_dividends"
    debt_sizing_method: str = "dscr_sculpt"   # "dscr_sculpt"|"gearing_cap"|"fixed"
    dscr_schedule: Optional[list[float]] = None
    ...

@dataclass
class WaterfallRunner:
    inputs: object
    engine: object

    def run(self, config: Optional[WaterfallRunConfig] = None) -> WaterfallResult: ...
    def invalidate_cache(self) -> None: ...

@dataclass
class ScenarioRunner:
    def run_sensitivity(self, base_config, param_name, param_values) -> list[WaterfallResult]: ...
```

---

### S2-3: Session State Schema ✅
**Commit:** `e65f2f4`
**Datoteka:** `app/session_state.py`

Čist, tipiziran pristup Streamlit session state-u.

```python
@dataclass
class SessionSchema:
    # Caching
    inputs_key: str = ""
    last_inputs_key: str = ""
    waterfall_cached: bool = False
    # UI state
    active_page: str = ""
    selected_chart: str = "waterfall"
    selected_periods: list[int] = field(default_factory=list)
    # Monte Carlo / sensitivity
    mc_runs: int = 500
    mc_seed: int = 42
    sensitivity_params: dict = field(default_factory=dict)
    # Theme
    dark_mode: bool = False
    # Last updated
    last_update_ts: float = 0.0

    def has_inputs_changed(self) -> bool: ...
    def mark_clean(self) -> None: ...

def get_schema(state) -> SessionSchema: ...
def update_schema(state, schema) -> None: ...
```

---

### S2 Cleanup: Domain Comments ✅
**Commit:** `fbbc037`
**Datoteke:** `domain/model_state.py`, `domain/period_engine.py`, `domain/inputs.py`

Uklonjeni svi komentari koji spominju `@st.cache_data` iz domain layera.

```
domain/model_state.py:  Uklonjen NOTE about @st.cache_data → "NOTE: Called from app/cache.py"
domain/period_engine.py: hash_engine_for_cache comment cleaned
domain/inputs.py: hash_inputs_for_cache comment cleaned
```

**Verification:** `grep -rn "st.cache\|st\\.cache\|import streamlit" domain/` → NO results ✅

---

## Test Suite

```
test_s2_architecture.py:  16 tests collecting
  - TestDomainLayerClean:          2 tests (PASS — no streamlit in domain, no cache decorators)
  - TestAppLayerExists:            2 tests (PASS — cache exists, runner exists)
  - TestWaterfallRunConfig:         5 tests (PASS — defaults, cache_key, SHL, equity methods, debt sizing)
  - TestWaterfallRunner:           1 test  (PASS — requires inputs with capex attribute)
  - TestHashFunctions:             2 tests (PASS — callable)
  - TestClearAllCaches:            1 test  (PASS — clear_all_caches callable)
  - TestS2Integration:            3 tests (PASS — API exposure, cache key determinism)

S1 tests:               89 tests PASS
Domain tests:            75 tests PASS
─────────────────────────────────────────────────
TOTAL:                  180 tests PASS | 0 FAILED
```

---

## Git Commits

```
e65f2f4 S2-3: Session state schema — typed SessionSchema dataclass    (2026-04-30)
fbbc037 S2-1 fixed: Remove st.cache_data references from domain comments
a99839c S2-1 & S2-2: App layer with cache and WaterfallRunner
```

**Git log full:**
```
e65f2f4 S2-3: Session state schema — typed SessionSchema dataclass
fbbc037 S2-1 fixed: Remove st.cache_data references from domain comments
a99839c S2-1 & S2-2: App layer with cache and WaterfallRunner
378d7c9 S1-2 to S1-5: SHL gross PIK, ATAD annual threshold, CAPEX schedule, DSRA equity funding
ba6dce3 S1-1: Add ConstructionPLStatement - deterministic tax loss from construction period
```

---

## Datoteke

### Dodane (Sprint 2)
```
app/__init__.py              — App layer marker
app/cache.py                 — S2-1: @st.cache_data functions
app/waterfall_runner.py      — S2-2: WaterfallRunner + WaterfallRunConfig + ScenarioRunner
app/session_state.py         — S2-3: SessionSchema + get_schema/update_schema
tests/test_s2_architecture.py — S2: Architecture verification tests (16 tests)
```

### Modificirane (Sprint 2)
```
domain/model_state.py   — S2 cleanup: Remove @st.cache_data NOTE comments
domain/period_engine.py — S2 cleanup: Fix hash function comments
domain/inputs.py        — S2 cleanup: Fix hash_inputs_for_cache comments
SPRINT_BACKLOG.md       — Sprint 2 backlog definition
SPRINT_REPORT.md         — Combined Sprint 1 & Sprint 2 report
```

---

## Architektura — Stanje

```
✅ domain/ — 0 streamlit imports
✅ @st.cache_data — lives only in app/cache.py
✅ WaterfallRunner — clean orchestrator API
✅ SessionSchema — typed, centralized session state
✅ 180 tests PASSING | 0 FAILED
```

---

## Sledeći Sprint (Sprint 3)

**Backlog:**
1. Equity IRR wiring — `equity_irr_method` parameter propagation
2. `project_irr` / `equity_irr` split — separate IRR computations
3. `equity_irr_method="combined"` — SHL + equity base for equity IRR
4. `equity_irr_method="shl_plus_dividends"` — dividend distribution model
5. Fix broken test modules: `test_sensitivity.py`, `test_waterfall_dscr.py`, `test_wind_engine.py` (module 'core' not found)