# Sprint Report: Finco1 — Sprint 1 & Sprint 2

**Datum:** 2026-04-30
**Repo:** https://github.com/xofisamba/Finco1
**Branch:** main

---

## Sprint 1 — Domain Layer Extensions

### S1-1: ConstructionPLStatement ✅
**Datoteka:** `domain/tax/construction_pl.py`

Deterministički tax loss iz construction perioda. Uzima prednost pred `prior_tax_loss_keur` za backward compatibility.

```python
@dataclass(frozen=True)
class ConstructionPLStatement:
    idc_keur: float
    bank_fees_keur: float
    commitment_fees_keur: float
    pre_operational_opex_keur: float
    construction_period_revenue_keur: float
    other_book_tax_difference_keur: float

    @property
    def book_loss_keur(self) -> float
    @property
    def initial_tax_loss_keur(self) -> float  # max(0, book_loss)
```

---

### S1-2: SHL Gross PIK ✅
**Datoteka:** `domain/waterfall/shl_engine.py`

PIK računat na gross kamati (ne net). WHT primjenjuje se SAMO na cash payments.

```python
# Bug fix: PIK = gross_interest - cash_paid (NE net - cash_paid)
gross_interest = balance * shl_rate_per_period
cash_paid = min(cf_after_senior_ds, gross_interest)
pik = gross_interest - cash_paid
new_balance = balance + pik
wht = cash_paid * wht_rate  # WHT only on cash
```

---

### S1-3: ATAD Annual Threshold ✅
**Datoteka:** `domain/tax/atad_engine.py`

ATAD threshold od 3M EUR je GODIŠNJI, ne po periodu. H1 uvijek prolazi.

```python
# atad_adjustment_v3: accumulated annual totals
if is_first_half:
    # H1: fully deductible
    deductible = interest
    disallowed = 0.0
else:
    # H2: check against accumulated annual limit
    annual_limit = atad_limit(accumulated_ebitda_annual)
    total_deductible = min(accumulated_interest_annual, annual_limit)
```

---

### S1-4: CAPEX Cash Flow Schedule ✅
**Datoteka:** `domain/capex/capex_schedule.py`

CAPEX distributed across construction periods, NOT all at FC (period 0).

```python
@dataclass(frozen=True)
class CapexCashFlowEntry:
    period: int
    amount_keur: float
    is_investment: bool

def build_capex_cashflow_schedule(
    capex_items: tuple[CapexItem, ...],
    periods: list[PeriodMeta],
    anchor_date: date,
    construction_months: int,
) -> CapexCashFlowSchedule: ...
```

---

### S1-5: DSRA Equity Funding at FC ✅
**Datoteka:** `domain/waterfall/dsra_engine.py`

DSRA initial funding dolazi iz EQUITY na FC, ne iz operating CF.

```python
def compute_initial_dsra(
    annual_debt_service_keur: float,
    dsra_months: int = 6,
) -> DSRAEngineResult:
    initial_funding = (annual_debt_service_keur / 2) * (dsra_months / 6)
    return DSRAEngineResult(initial_contribution=initial_funding, ...)
```

---

### Sprint 1 — Rezultat testova

```
89 S1-specific tests (S1-1 do S1-5)
+ 75 existing tests
= 164 tests PASSING ✅
```

### Git commits (Sprint 1)
```
ba6dce3 S1-1: Add ConstructionPLStatement
378d7c9 S1-2 to S1-5: SHL gross PIK, ATAD annual threshold, CAPEX schedule, DSRA equity funding
```

---

## Sprint 2 — Arhitekturalni Decoupling

### Cilj
Domain layer nema Streamlit imports. Sve Streamlit-specific stvari žive isključivo u `app/` layer.

---

### S2-1: App Cache Layer ✅
**Datoteka:** `app/cache.py`

Jedino mjesto gdje živi `@st.cache_data`. Domain ostaje clean.

```python
# Hash functions for cache keying
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
**Datoteka:** `app/waterfall_runner.py`

UI pages pozivaju `runner.run(config)`, ne `run_waterfall()` direktno.

```python
@dataclass(frozen=True)
class WaterfallRunConfig:
    rate_per_period: float = 0.02825
    tenor_periods: int = 28
    target_dscr: float = 1.15
    lockup_dscr: float = 1.10
    tax_rate: float = 0.10
    dsra_months: int = 6
    # SHL
    shl_amount_keur: float = 0.0
    shl_rate: float = 0.0
    shl_idc_keur: float = 0.0
    shl_repayment_method: str = "bullet"
    shl_tenor_years: int = 0
    shl_wht_rate: float = 0.0
    # Returns
    discount_rate_project: float = 0.0641
    discount_rate_equity: float = 0.0965
    # Debt overrides
    fixed_debt_keur: Optional[float] = None
    fixed_ds_keur: Optional[float] = None
    # Methods
    equity_irr_method: str = "equity_only"
    debt_sizing_method: str = "dscr_sculpt"
    ...

@dataclass
class WaterfallRunner:
    inputs: object
    engine: object

    def run(self, config: Optional[WaterfallRunConfig] = None) -> WaterfallResult: ...
    def invalidate_cache(self) -> None: ...
```

---

### S2-3: Session State Schema ✅
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
    # Monte Carlo
    mc_runs: int = 500
    mc_seed: int = 42
    sensitivity_params: dict = field(default_factory=dict)
    ...

def get_schema(state) -> SessionSchema: ...
def update_schema(state, schema) -> None: ...
def (schema).has_inputs_changed() -> bool: ...
def (schema).mark_clean() -> None: ...
```

---

### S2 — Cleanup: Domain Comments Fix ✅
**Datoteke:** `domain/model_state.py`, `domain/period_engine.py`, `domain/inputs.py`

Uklonjeni svi komentari koji spominju `@st.cache_data` iz domain layera.

```
domain/model_state.py: Remove @st.cache_data NOTE comments
domain/period_engine.py: Fix hash function comment (no st.cache_data)
domain/inputs.py: Fix hash_inputs_for_cache comment (no st.cache_data)
```

---

### Sprint 2 — Rezultat testova

```
S2 architecture tests: 16 passing (test_s2_architecture.py)
+ S1 tests: 89 passing
+ Existing domain tests: 75 passing
= 180 tests PASSING ✅
```

### Git commits (Sprint 2)
```
a99839c S2-1 & S2-2: App layer with cache and WaterfallRunner
fbbc037 S2-1 fixed: Remove st.cache_data references from domain comments
e65f2f4 S2-3: Session state schema — typed SessionSchema dataclass
```

---

## Ukupno — Sprint 1 & Sprint 2

### Datoteke dodane
```
domain/tax/construction_pl.py      # S1-1
domain/waterfall/shl_engine.py      # S1-2
domain/tax/atad_engine.py           # S1-3
domain/capex/capex_schedule.py      # S1-4
domain/waterfall/dsra_engine.py     # S1-5
app/__init__.py                     # S2
app/cache.py                        # S2-1
app/waterfall_runner.py             # S2-2
app/session_state.py                 # S2-3
tests/test_s1_construction_pl.py    # S1-1
tests/test_s1_shl_gross_pik.py      # S1-2
tests/test_s1_atad_annual_threshold.py  # S1-3
tests/test_s1_capex_schedule.py     # S1-4
tests/test_s1_dsra_equity_funding.py # S1-5
tests/test_s2_architecture.py       # S2
```

### Test suite
```
S1: 89 tests
S2: 16 tests  
Domain: 75 tests (period_engine, xirr, financing, tax, depreciation)
= 180 tests PASSING ✅
0 FAILED
```

### Git log
```
e65f2f4 S2-3: Session state schema
fbbc037 S2-1 fixed: Remove st.cache_data references from domain comments
a99839c S2-1 & S2-2: App layer with cache and WaterfallRunner
378d7c9 S1-2 to S1-5: SHL gross PIK, ATAD annual threshold, CAPEX schedule, DSRA equity funding
ba6dce3 S1-1: Add ConstructionPLStatement
```

### Architektura — Čistoća

```
✅ domain/ — NEMA streamlit imports
✅ @st.cache_data — isključivo u app/cache.py
✅ Hash funkcije — u domain/ ali bez st.cache_data u komentarima
✅ WaterfallRunner — clean API隔离
✅ SessionSchema — centraliziran, tipiziran
```

---

## Sledeći korak

Sprint 3 — Equity IRR wiring i project/equity split.

ili po potrebi, nastavi s specifičnim taskovima iz backlog-a.