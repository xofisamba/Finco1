# OpusCore v2 — Calibration Memory
# Ažurirano: 2026-04-29
# NIKAD ne mijenjaj ove vrijednosti bez eksplicitne potvrde iz Excel modela

## TUHO Wind (35 MW) — Verificirani Excel parametri

### Tehnički inputi
- Kapacitet: 35 MW
- operating_hours_p50: 4,164 h (145,740 MWh/god ÷ 35 MW)
- Availability: 100%
- PPA tariff Y1: 60.0 EUR/MWh, escalacija 2%/god
- PPA tenor: 12 godina
- Post-PPA spot: ~102 EUR/MWh (Y13+)

### Revenue struktura
- PPA Revenue Y1-H1: 4,336 kEUR
- CO2 Revenue Y1-H1: 303 kEUR ← MODEL NEMA OVO!
- CO2 Revenue Y1-H2: 308 kEUR
- CO2 Y1 ukupno: 611 kEUR, godišnji pad ~10%
- Balancing costs: uključeni u OpEx (ne oduzimaju od revenue)
- Y1 Total Revenue target: 9,355 kEUR (PPA 8,744 + CO2 611)

### OpEx
- Y1 OpEx target: 1,998 kEUR ✅ (model je točan)
- Escalacija: 2%/god

### Dug
- Senior Debt: 43,359 kEUR (fixed, metoda: "fixed")
- All-in rate: 5.95%/god
- Tenor: 14 godina = 28 polugodišta
- Fixed DS: 2,116 kEUR/period

### SHL (Shareholder Loan)
- shl_amount_keur: 29,135
- shl_idc_keur: 3,569 (construction IDC)
- shl_opening_balance: 32,704 (= 29,135 + 3,569)
- shl_rate: 8.00%/god
- shl_wht_rate: 0.0% (NULA — ne 18%!)
- shl_repayment_method: "pik_then_sweep"
- shl_interest_shortfall_treatment: "capitalize"
- PIK switch trigger: FCF > accrued (NE senior_balance=0!)
- cf_for_shl formula: ebitda - senior_ds (BEZ poreza)

### SHL Balance profil (DS sheet verificirano)
| Period | Beginning | Accrued | FCF | Paid | PIK | Principal | Closing |
|--------|-----------|---------|------|------|------|-----------|---------|
| Y0 | 0 | 3,569 | 0 | 0 | 3,569| 0 | 32,704 |
| Y1-H1 | 32,704 | 1,297 | 954 | 954 | 344 | 0 | 33,047 |
| Y1-H2 | 33,047 | 1,333 | 970 | 970 | 363 | 0 | 33,411 |
| Y13-H1 | 43,151 | 1,735 | 3,234| 1,735| 0 | 1,499 | 42,232 |
| Y20-H2 | ~2,108 | 84 | 2,781| 84 | 0 | 2,108 | 0 |

### Equity IRR
- equity_irr_method: "shl_plus_dividends"
- equity_investment: shl_amount + share_capital = 29,135 + 500 = 29,635
- equity_cf: SHL net interest (uvijek) + dividende (kad SHL=0)
- SHL principal se NE uključuje u equity CF!
- Target: 11.61%

---

## Oborovo Solar (75 MW) — Verificirani Excel parametri

### Tehnički inputi
- Kapacitet: 75 MW AC
- operating_hours_p50: 1,494 h
- Availability: 98.01%
- PV degradation: 0.40%/god
- PPA tariff Y1: 57.0 EUR/MWh, escalacija 2%/god
- PPA tenor: 12 godina

### Revenue
- Y1 Revenue target: 3,250 kEUR (Y1 je stub period H1!)
- Y1-H2 Revenue: 3,197 kEUR (prvi puni polugodišnji period)
- Nema CO2 revenue za Oborovo

### OpEx — KRITIČNO: duplikati su bug!
Ispravne stavke (bez duplikata):
| Kod | Stavka | Y1 kEUR |
|-------|-----------------------|---------|
| B.01 | Technical Management | 198 | ← samo agregat, NE B.01.1 i B.01.2 zasebno!
| B.02 | Infrastructure Maint | 244 | ← samo agregat, NE B.02.1 zasebno!
| B.03 | Maintain Site | 45 |
| B.04 | Clean Material | 40 |
| B.05 | Security | 30 |
| B.06 | Insurance | 255 |
| B.07 | Lease & Property Tax | 208 |
| B.08 | Power Expenses | 177 |
| B.09 | Fees | 14 |
| B.10 | Audit & Legal | 24 |
| B.11 | Bank Fees | 20 |
| B.12 | Environmental&Social | 32 |
| B.13 | Contingencies | 51 |
| TOTAL | | 1,338 | ← target (ne 1,998!)

### Dug
- Senior Debt: 42,852 kEUR (metoda: "gearing_cap")
- All-in rate: provjeriti iz DS sheet
- Tenor: 14 godina = 28 polugodišta

### SHL (Shareholder Loan)
- shl_amount_keur: 14,621
- shl_idc_keur: 1,169 (construction IDC)
- shl_opening_balance: 15,790 (= 14,621 + 1,169)
- shl_rate: 8.00%/god
- shl_wht_rate: 0.0%
- shl_repayment_method: "pik_then_sweep"
- shl_interest_shortfall_treatment: "capitalize"
- PIK switch trigger: FCF > accrued (NE senior_balance=0!)
- cf_for_shl formula: ebitda - senior_ds (BEZ poreza)

### SHL Balance profil (DS sheet verificirano)
| Period | Beginning | Accrued | FCF | Paid | PIK | Principal | Closing |
|--------|-----------|---------|------|------|------|-----------|---------|
| Y0 | 0 | 1,170 | 0 | 0 | 1,170| 0 | 15,790 |
| Y1-H1 | 15,790 | 637 | 336 | 336 | 301 | 0 | 16,091 |
| Y1-H2 | 16,091 | 638 | 330 | 330 | 308 | 0 | 16,399 |
| Y13-H1 | 26,080 | 1,035 | 343 | 343 | 691 | 0 | 26,772 |
| Y13-H2 | 26,772 | 1,080 | 1,304| 1,080| 0 | 224 | 26,548 |
| Y20-H2 | 2,108 | 84 | 2,781| 84 | 0 | 2,108 | 0 |

### Equity IRR
- equity_irr_method: "shl_plus_dividends"
- equity_investment: shl_amount + share_capital = 14,621 + 500 = 15,121
- equity_cf: SHL net interest (uvijek) + dividende (kad SHL=0)
- SHL principal se NE uključuje u equity CF!
- Target: 10.60%

---

## Shared waterfall logika — KRITIČNO

### PIK/Sweep trigger
```python
# ISPRAVNO:
_pik_trigger = (cf_for_shl > shl_balance * shl_rate / 2)

# POGREŠNO (NE KORISTITI):
_pik_trigger = (senior_balance <= 0)
```

### cf_for_shl za pik_then_sweep
```python
# ISPRAVNO:
if shl_repayment_method == "pik_then_sweep":
 _cf_for_shl = ebitda - senior_ds # BEZ poreza!

# POGREŠNO:
_cf_for_shl = cf_after_tax - senior_ds
```

### WHT na SHL
```python
# WHT = 0% za OBA projekta (verificirano iz Excel Inputs)
shl_wht_rate = 0.0 # NE 0.18!
```

### Equity CF za shl_plus_dividends
```python
# ISPRAVNO:
equity_cf = shl_interest_keur + distribution_keur
# BEZ shl_principal_keur!

# POGREŠNO:
equity_cf = shl_interest_keur + shl_principal_keur + distribution_keur
```