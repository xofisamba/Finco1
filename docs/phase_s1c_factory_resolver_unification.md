# Phase S1-C — Generic Factory vs Resolver Unification

**Status**: DRAFT, awaiting review
**Branch**: `phase/s1c-unify-generic-factory-resolver`
**Base**: `main` @ `9fc58a5` (post S1-A)
**Risk**: Medium (factory defaults change, Generic runtime outputs change)
**rc1**: untouched
**TUHO / Oborovo**: bit-identical parity preserved

---

## 1. Goal

Eliminate the remaining Generic factory-direct vs resolver divergence
identified by the S1-C audit. The Generic factory financial CAPEX
sub-fields (`idc_keur`, `bank_fees_keur`, etc.) are now zero by
default, matching the resolver's `_zero_financial_capex_subfields`
normalization. The resolver function remains as a defensive no-op
for any non-zero factory defaults that may slip in.

---

## 2. Audit findings (from S1-C analysis)

The S1-C audit (`docs/phase_s1c_factory_vs_resolver_consistency_audit.md`)
confirmed:

- Generic Solar pre-S1-C: factory `idc=500, bank_fees=200,
  total_capex=30,700, debt_keur=22,650`
- Generic Solar pre-S1-C: resolver `idc=0, bank_fees=0,
  total_capex=30,000, debt_keur=22,500`
- **Delta**: `debt_keur=-150 kEUR`, `project_irr=+0.0025`,
  `equity_irr=+0.0109`
- Root cause: factory defaults populate non-zero financial
  sub-fields; resolver zeros them
- Scope: affects every consumer of Generic runtime (KPIs, exports,
  matrix, equity IRR)

---

## 3. Fix

### 3.1 Factory default zeroing

All five Generic factories now populate zero financial CAPEX
sub-fields:

| Factory | Old idc / bank_fees | New idc / bank_fees |
| --- | --- | --- |
| `create_default_solar_project` | 500 / 200 | 0 / 0 |
| `create_default_wind_project` | 800 / 300 | 0 / 0 |
| `create_default_bess_project` | 500 / 200 | 0 / 0 |
| `create_default_solar_bess_project` | 500 / 200 | 0 / 0 |
| `create_default_wind_bess_project` | 800 / 300 | 0 / 0 |

### 3.2 Resolver unchanged

`_zero_financial_capex_subfields` in `app/input_adapter.py` is
**unchanged**. It continues to zero the six financial sub-fields
as a defensive no-op for any future factory that does not pre-zero.
The S1 contract ("form path and snapshot path produce equal
ProjectInputs") is preserved.

### 3.3 TUHO/Oborovo factories unchanged

TUHO factory (`create_default_tuho_wind1`) and Oborovo factory
(`create_default_oborovo`) keep their frozen Excel-derived
`idc_keur/bank_fees_keur` values. They are template-seeded and
have `fixed_debt_keur > 0` that overrides any sub-field divergence.

---

## 4. Empirical results

### 4.1 Generic Solar before vs after S1-C

| Metric | Pre-S1-C Factory | Post-S1-C Factory | Pre-S1-C Resolver | Post-S1-C Resolver |
| --- | ---: | ---: | ---: | ---: |
| `idc_keur` | 500.00 | **0.00** | 0.00 | 0.00 |
| `bank_fees_keur` | 200.00 | **0.00** | 0.00 | 0.00 |
| `total_capex` | 30,700.00 | **30,000.00** | 30,000.00 | 30,000.00 |
| `debt_keur` | 22,650.00 | **22,500.00** | 22,500.00 | 22,500.00 |
| `project_irr` | 0.0896 | **0.0921** | 0.0921 | 0.0921 |
| `equity_irr` | 0.1311 | **0.1420** | 0.1420 | 0.1420 |

### 4.2 Generic Wind before vs after S1-C

| Metric | Pre-S1-C Factory | Post-S1-C Factory | Pre-S1-C Resolver | Post-S1-C Resolver |
| --- | ---: | ---: | ---: | ---: |
| `idc_keur` | 800.00 | **0.00** | 0.00 | 0.00 |
| `bank_fees_keur` | 300.00 | **0.00** | 0.00 | 0.00 |
| `total_capex` | 40,100.00 | **39,000.00** | 39,000.00 | 39,000.00 |
| `debt_keur` | 29,550.00 | **29,250.00** | 29,250.00 | 29,250.00 |

### 4.3 TUHO/Oborovo parity (frozen, unchanged)

| Project | `debt_keur` (Pre) | `debt_keur` (Post) | Delta |
| --- | ---: | ---: | ---: |
| TUHO | 43,359.00 | 43,359.00 | 0 |
| Oborovo | 42,852.27 | 42,852.27 | 0 |

TUHO/Oborovo paritet bitno identičan. Frozen.

---

## 5. Important note on Generic exploratory outputs

This is **not an engine formula change**. The runtime sculpt
formula is unchanged. The debt-sizing math is unchanged.

It **IS a Generic runtime output change**. Generic exploratory
defaults (factory outputs) now match what the user sees after
form submission (resolver outputs). This was the goal of S1-C.

Generic Solar `debt_keur` changes from 22,650 → 22,500 (factory
path). This is the same value the resolver was producing. The
delta of -150 kEUR is intentional and aligns the two paths.

Generic Solar `project_irr` changes from 0.0896 → 0.0921
(factory path). Same as resolver.

Generic Solar `equity_irr` changes from 0.1311 → 0.1420
(factory path). Same as resolver.

TUHO and Oborovo are unchanged.

---

## 6. Constraints preserved (all pinned by tests)

- ✅ rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` untouched
- ✅ Engine MD5 `6bf49f33efc989736c17cea0cb9b7723` UNCHANGED
- ✅ TUHO debt_keur `43,359.00` (frozen)
- ✅ Oborovo debt_keur `42,852.27` (frozen)
- ✅ Phase 51F parity guardrails 21/21 PASS
- ✅ Phase 23s combined frozen-schedule parity 9/9 PASS
- ✅ Phase 23a frozen schedule runtime wiring 16/16 PASS
- ✅ Phase S1-A export tests 20/20 PASS (TUHO/Oborovo parity)
- ✅ Phase 1 generic sculpt unify 42/42 PASS
- ✅ New S1-C tests 26/26 PASS
- ✅ No financial formula / debt / DSCR sculpt / tax / IDC / construction / sponsor changes
- ✅ No persistence schema migration
- ✅ No R99 / R102 / G20 work
- ✅ `_zero_financial_capex_subfields` retained as defensive no-op

---

## 7. Files changed

| File | Change | Purpose |
| --- | --- | --- |
| `app/project_factories.py` | 5 factories, 5 LOC | Zero Generic factory financial sub-fields |
| `tests/test_phase_s1c_factory_resolver_consistency.py` | NEW, 26 tests, ~360 lines | Regression suite |
| `tests/test_phase51f_parallel_work_guardrails.py` | 1 LOC | Update factory MD5 baseline |
| `tests/test_phase_s1a_export_runtime_senior_debt.py` | +12/-1 LOC | Update factory MD5 baseline comment |
| `docs/phase_s1c_factory_resolver_unification.md` | NEW | Phase brief |
| `reports/phase_s1c_factory_resolver_unification.md` | NEW | Implementation report |

No other files modified.

---

## 8. Stop-after-report contract

DRAFT only. Do NOT mark ready, do NOT merge, awaiting user
review and explicit go-ahead.

After approval, the next step is **S1-D** (documentation
update, no risk, ~1h) or pause and review the arc.