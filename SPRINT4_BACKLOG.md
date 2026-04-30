# Sprint 4 — Equity IRR Wiring + IRR Split

## Repo
https://github.com/xofisamba/Finco1
Branch: main

## Kontekst
Sprinti 1-3 su završeni (202 testa PASS). Arhitektura je čista.

## Cilj Sprinta 4
Ispravno žičanje equity_irr_method parametra kroz cijeli waterfall stack,
te razdvajanje project_irr i equity_irr u zasebne, provjerljive kalkulacije.

## Taskovi

### S4-1: Equity IRR Method Propagacija
- `sculpt_capex_keur=inputs.capex.sculpt_capex_keur` ← dodati u WaterfallRunner.run()
- Datoteka: app/waterfall_runner.py

### S4-2: prior_tax_loss_keur Propagacija
- prior_tax_loss_keur=inputs.tax.initial_tax_loss_keur
- U cached_run_waterfall_v3 (utils/cache.py) i app/cache.py

### S4-3: Project IRR vs Equity IRR Split
- Unit test za sva 3 equity_irr_methoda
- Datoteka: tests/test_equity_irr_methods.py

### S4-4: Popravi Broken Test Module (test_sensitivity.py)
- `module 'core' not found` greška
- Opcija A: Preseli u domain/analytics/scenarios.py

### S4-5: Kalibracijska Verifikacija — Oborovo
Target: project_irr=7.96%, equity_irr=10.6%, debt=42,852 kEUR, avg_dscr=1.147

## Acceptance Criteria
- [ ] S4-1: sculpt_capex_keur propagiran iz inputs.capex
- [ ] S4-2: prior_tax_loss_keur = inputs.tax.initial_tax_loss_keur
- [ ] S4-3: Sva 3 equity_irr_method rade ispravno, unit test prolazi
- [ ] S4-4: test_sensitivity.py prolazi (5/5 testova)
- [ ] S4-5: Devijacije dokumentirane, current_outputs.json ažuriran
- [ ] 210+ testova PASS | 0 FAILED
