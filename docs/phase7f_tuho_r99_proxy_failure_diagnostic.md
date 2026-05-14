# Phase 7F - TUHO R99 Proxy Failure Diagnostic

**Date:** 2026-05-14
**Branch:** `phase7f-tuho-distribution-calibration`
**Scope:** Diagnostic only; no runtime implementation.

## Purpose

PR B2 tested a mechanically correct SHL cash-interest-first waterfall with:

```text
fcf_for_shl = cf_after_tax_keur - senior_ds_keur
```

That failed calibration acceptance:

- Total distributions: 174,011 kEUR vs Excel R119 target 151,709 kEUR.
- SHL service: 75,589 kEUR vs Excel R104 approx 82,486 kEUR.
- SHL peak: 35,835 kEUR vs Excel approx 43,731 kEUR.
- First distribution: op_idx 34 / 2047-06-30, earlier than Excel timing.

This document explains why the proxy failed.

## Authoritative Mapping

- Excel R99 = R102 = `fcf_for_shl` input / cash available for SHL waterfall.
- Excel R104 = SHL cash outflow after the SHL waterfall.
- Excel R119 = net dividends and remains the official calibration target.

## Sources

- Excel values: `tests/fixtures/excel_tuho_full_model_extract.json`
- Python values: current PR B1 TUHO model run, using the same `cf_after_tax - senior_ds`
  input that PR B2 used.
- Python SHL gross interest, PIK, and closing balance below are simulated using
  the rejected PR B2 cash-interest-first formula, without reintroducing runtime
  `fcf_waterfall` code.

## Period Comparison, op_idx 0-36

| op_idx | date | Excel R99/R102 | Python cf_after_tax | Python senior_ds | Python proxy cf_after_tax-senior_ds | Delta proxy vs Excel R99 | Excel SHL gross interest | Python gross interest | Excel PIK | Python PIK | Excel SHL closing | Python SHL closing |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2030-06-30 | 953.8 | 3053.2 | 1945.5 | 1107.8 | +153.9 | 1297.4 | 1296.7 | 343.6 | 188.9 | 33047.5 | 32892.6 |
| 1 | 2030-12-31 | 969.6 | 3121.1 | 1988.7 | 1132.4 | +162.7 | 1332.8 | 1304.2 | 363.1 | 171.8 | 33410.6 | 33064.5 |
| 2 | 2031-06-30 | 967.0 | 3134.9 | 1997.5 | 1137.4 | +170.4 | 1325.4 | 1311.0 | 358.5 | 173.6 | 33769.1 | 33238.1 |
| 3 | 2031-12-31 | 983.0 | 3186.8 | 2030.6 | 1156.2 | +173.2 | 1361.9 | 1317.9 | 378.9 | 161.7 | 34148.0 | 33399.8 |
| 4 | 2032-06-30 | 976.2 | 3209.6 | 2045.1 | 1164.5 | +188.3 | 1362.2 | 1324.3 | 386.0 | 159.8 | 34533.9 | 33559.6 |
| 5 | 2032-12-31 | 987.0 | 3244.8 | 2067.6 | 1177.3 | +190.3 | 1392.7 | 1330.6 | 405.8 | 153.4 | 34939.7 | 33712.9 |
| 6 | 2033-06-30 | 987.5 | 3267.7 | 2082.1 | 1185.6 | +198.0 | 1386.1 | 1336.7 | 398.6 | 151.2 | 35338.2 | 33864.1 |
| 7 | 2033-12-31 | 1003.9 | 3321.8 | 2116.6 | 1205.2 | +201.3 | 1425.1 | 1342.7 | 421.3 | 137.5 | 35759.5 | 34001.6 |
| 8 | 2034-06-30 | 999.8 | 3335.9 | 2125.6 | 1210.3 | +210.5 | 1418.6 | 1348.2 | 418.8 | 137.9 | 36178.3 | 34139.5 |
| 9 | 2034-12-31 | 1016.4 | 3391.2 | 2160.8 | 1230.4 | +214.0 | 1459.0 | 1353.6 | 442.7 | 123.3 | 36621.0 | 34262.7 |
| 10 | 2035-06-30 | 1010.1 | 3405.3 | 2169.8 | 1235.5 | +225.4 | 1452.8 | 1358.5 | 442.7 | 123.0 | 37063.7 | 34385.8 |
| 11 | 2035-12-31 | 1026.8 | 3461.7 | 2205.7 | 1256.0 | +229.1 | 1494.7 | 1363.4 | 467.9 | 107.4 | 37531.6 | 34493.2 |
| 12 | 2036-06-30 | 1033.5 | 3485.5 | 2220.9 | 1264.6 | +231.1 | 1497.1 | 1367.7 | 463.7 | 103.1 | 37995.3 | 34596.3 |
| 13 | 2036-12-31 | 1044.8 | 3523.8 | 2245.3 | 1278.5 | +233.7 | 1532.3 | 1371.7 | 487.5 | 93.2 | 38482.7 | 34689.5 |
| 14 | 2037-06-30 | 1052.6 | 3547.7 | 2260.5 | 1287.2 | +234.6 | 1526.7 | 1375.4 | 474.1 | 88.3 | 38956.8 | 34777.8 |
| 15 | 2037-12-31 | 1070.0 | 3606.5 | 2298.0 | 1308.5 | +238.5 | 1571.1 | 1378.9 | 501.1 | 70.4 | 39457.9 | 34848.2 |
| 16 | 2038-06-30 | 1076.0 | 3620.8 | 2307.1 | 1313.7 | +237.7 | 1565.3 | 1381.7 | 489.3 | 68.1 | 39947.3 | 34916.3 |
| 17 | 2038-12-31 | 1093.8 | 3680.8 | 2345.4 | 1335.5 | +241.6 | 1611.0 | 1384.4 | 517.2 | 49.0 | 40464.4 | 34965.3 |
| 18 | 2039-06-30 | 1098.9 | 3695.1 | 2354.5 | 1340.7 | +241.7 | 1605.3 | 1386.4 | 506.3 | 45.7 | 40970.8 | 35011.0 |
| 19 | 2039-12-31 | 1117.1 | 3752.8 | 2393.5 | 1359.2 | +242.1 | 1652.3 | 1388.2 | 535.2 | 29.0 | 41506.0 | 35040.0 |
| 20 | 2040-06-30 | 1121.0 | 3781.2 | 2409.3 | 1371.9 | +250.9 | 1655.7 | 1389.3 | 534.7 | 17.4 | 42040.7 | 35057.4 |
| 21 | 2040-12-31 | 1133.3 | 3439.1 | 2435.8 | 1003.3 | -130.0 | 1695.4 | 1390.0 | 562.2 | 386.7 | 42602.9 | 35444.1 |
| 22 | 2041-06-30 | 1141.8 | 3847.7 | 2451.7 | 1396.0 | +254.2 | 1690.1 | 1405.4 | 548.3 | 9.4 | 43151.2 | 35453.5 |
| 23 | 2041-12-31 | 1160.7 | 3492.1 | 2492.3 | 999.7 | -161.0 | 1740.2 | 1405.7 | 579.5 | 406.0 | 43730.7 | 35859.5 |
| 24 | 2042-06-30 | 3233.6 | 3925.9 | 2125.2 | 1800.7 | -1432.9 | 1734.9 | 1421.8 | 0.0 | 0.0 | 42231.9 | 35480.6 |
| 25 | 2042-12-31 | 3167.0 | 5539.4 | 3482.2 | 2057.2 | -1109.9 | 1703.2 | 1406.8 | 0.0 | 0.0 | 40768.0 | 34830.3 |
| 26 | 2043-06-30 | 3265.3 | 6309.6 | 3415.6 | 2894.1 | -371.2 | 1617.3 | 1381.0 | 0.0 | 0.0 | 39120.1 | 33317.2 |
| 27 | 2043-12-31 | 2395.6 | 5490.9 | 3472.2 | 2018.8 | -376.8 | 1577.7 | 1321.0 | 0.0 | 0.0 | 38302.2 | 32619.5 |
| 28 | 2044-06-30 | 6191.8 | 6414.6 | 0.0 | 6414.6 | +222.7 | 1527.9 | 1293.4 | 0.0 | 0.0 | 33638.2 | 27498.3 |
| 29 | 2044-12-31 | 5175.3 | 5531.0 | 0.0 | 5531.0 | +355.6 | 1356.6 | 1090.3 | 0.0 | 0.0 | 29819.5 | 23057.6 |
| 30 | 2045-06-30 | 6212.3 | 6484.5 | 0.0 | 6484.5 | +272.2 | 1183.0 | 914.2 | 0.0 | 0.0 | 24790.2 | 17487.4 |
| 31 | 2045-12-31 | 5090.8 | 5619.2 | 0.0 | 5619.2 | +528.5 | 999.8 | 693.4 | 0.0 | 0.0 | 20699.2 | 12561.5 |
| 32 | 2046-06-30 | 6422.3 | 6574.1 | 0.0 | 6574.1 | +151.8 | 821.2 | 498.1 | 0.0 | 0.0 | 15098.0 | 6485.4 |
| 33 | 2046-12-31 | 5092.5 | 5694.0 | 0.0 | 5694.0 | +601.4 | 608.9 | 257.1 | 0.0 | 0.0 | 10614.4 | 1048.6 |
| 34 | 2047-06-30 | 6585.9 | 6663.5 | 0.0 | 6663.5 | +77.6 | 421.1 | 41.6 | 0.0 | 0.0 | 4449.5 | 0.0 |
| 35 | 2047-12-31 | 5050.2 | 5768.5 | 0.0 | 5768.5 | +718.3 | 179.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 36 | 2048-06-30 | 6765.1 | 6772.8 | 0.0 | 6772.8 | +7.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Phase Split

| Phase | op_idx | Excel R99/R102 | Python proxy | Proxy delta |
| --- | --- | ---: | ---: | ---: |
| PIK phase | 0-24 | 28,258.2 | 31,257.7 | +2,999.5 |
| Sweep overlap | 25-33 | 43,012.9 | 43,287.4 | +274.4 |
| Python post-SHL / Excel final sweep | 34-36 | 18,401.2 | 19,204.7 | +803.5 |
| Excel post-SHL | 37-59 | 145,073.1 | 155,795.6 | +10,722.5 |
| Full operating horizon | 0-59 | 234,745.4 | 249,545.4 | +14,800.0 |

## Answers

### 1. Is the proxy too high mainly during PIK phase, sweep phase, or post-SHL phase?

Across the full horizon, the proxy is too high mainly **post-SHL**: +10,722.5
kEUR of the +14,800.0 kEUR full-horizon gap occurs in op_idx 37-59.

For the PR B2 failure mechanics, the important early damage happens during the
PIK phase. In op_idx 0-24, the proxy is +2,999.5 kEUR too high net, with
+4,723.4 kEUR of positive-period excess cash. That excess cash is used to pay
cash interest instead of allowing PIK to capitalize, so the Python SHL balance
never builds to Excel's peak.

### 2. How much of the SHL peak gap is explained by early-period excess proxy cash?

Excel peak SHL balance is 43,730.7 kEUR. The simulated Python PR B2 peak is
35,859.5 kEUR. The peak gap is therefore 7,871.2 kEUR.

The cumulative positive proxy excess during op_idx 0-24 is 4,723.4 kEUR, which
explains about 60% of the peak gap directly:

```text
4,723.4 / 7,871.2 = 60.0%
```

The remainder is explained by compounding: once the Python balance is lower, its
gross interest is lower in every later period, so Excel continues to capitalize
larger interest amounts while Python has less balance on which to accrue.

### 3. Which component causes the proxy to exceed Excel R99?

The direct bridge is:

```text
Python proxy = cf_after_tax_keur - senior_ds_keur
Excel R99   = R69 + R70 + R82/R98/R100 distribution account effects
```

The full-horizon gap is:

```text
Python cf_after_tax - Excel R69:       approx +14,264 kEUR
Senior DS timing difference:           approx +536 kEUR
Total proxy - Excel R99 gap:           approx +14,800 kEUR
```

So the primary cause is **not senior DS timing** after PR B1. Senior DS explains
only about 536 kEUR full-horizon. The dominant issue is that Python
`cf_after_tax_keur` is not an Excel R69-equivalent.

Component-level notes:

- **Revenue:** contributes to some period noise, especially around the PPA /
  merchant boundary, but does not explain the full gap.
- **OPEX:** not the dominant driver.
- **Tax timing / basis:** important. Existing diagnostics show Python
  `cf_after_tax_keur` is semantically different from Excel R69 because Python
  uses the current tax engine output/timing rather than Excel's explicit
  R69 component sum.
- **Senior DS timing:** small residual driver after B1.
- **Reserve / distribution account logic:** important for exact R99. Excel R99
  is gated through R84/R98/R100, not just a raw cashflow subtraction.
- **Carry-forward / R98/R100 behavior:** required for an exact engine. This
  is where Excel preserves distribution-account state and lockup/carry-forward
  effects that the simple proxy cannot represent.

### 4. Is there a simple existing Python component closer to Excel R99?

No existing component is reliable enough.

| Candidate | Total op_idx 0-36 | Delta vs Excel 0-36 | MAE 0-36 | Total op_idx 0-59 | Delta vs Excel 0-59 | MAE 0-59 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `cf_after_tax_keur` | 159,394.9 | +69,722.6 | 1,884.4 | 315,190.5 | +80,445.1 | 1,467.6 |
| `cf_after_tax_keur - senior_ds_keur` | 93,749.8 | +4,077.5 | 303.8 | 249,545.4 | +14,800.0 | 492.9 |
| `cf_after_reserves_keur` | 54,668.7 | -35,003.7 | 1,008.7 | 210,464.3 | -24,281.2 | 927.5 |
| `ebitda_keur - senior_ds_keur` | 100,294.6 | +10,622.2 | 396.3 | 269,482.0 | +34,736.5 | 773.1 |

`cf_after_tax - senior_ds` is the closest simple proxy, but it is still too high
exactly where PR B2 is most sensitive: the early PIK phase and late post-SHL
dividend phase.

### 5. Is a minimal R99/R102 engine needed after all?

Yes. PR B2 should not be retried with `cf_after_tax - senior_ds` as the SHL
cash input. The failure is not in the fcf_waterfall formula; it is in the input
cash source.

A minimal R99/R102 engine is needed because Excel R99/R102 is not just:

```text
after_tax_cash - senior_debt_service
```

It is an Excel distribution-account result:

```text
R69 -> R84 -> R98/R100 -> R99/R102
```

### 6. Smallest R99/R102 engine version

The smallest acceptable version should avoid a full tax refactor and avoid
hardcoded Excel rows. It should be TUHO-only behind a feature flag.

Minimum scope:

1. Compute an explicit R69-equivalent from existing Python components:

   ```text
   r69_fcf_banks_keur =
       revenue_keur
     - opex_keur
     + local_tax_keur
     + cash_interest_on_reserves_keur
     - corporate_tax_keur
   ```

   Missing components can default to zero, but must be named audit fields.

2. Compute R84:

   ```text
   r84_fcf_junior_keur = r69_fcf_banks_keur - senior_ds_keur + dsra_release_or_funding_keur
   ```

3. Compute R98/R100 distribution-account carry-forward:

   ```text
   r98_distribution_account_keur =
       r84_fcf_junior_keur
     + junior_debt_service_keur
     + reserve_sweep_keur
     + previous_r100_carryforward_keur
   ```

4. Apply the Excel-style R99 gate:

   ```text
   if year <= senior_tenor_years and (
       dscr < lockup_dscr
       or year == 0
       or r98_distribution_account_keur < 0
       or dsra_balance_keur < dsra_target_keur
       or jdsra_balance_keur < jdsra_target_keur
   ):
       r99_fcf_for_distribution_keur = 0
       r100_carryforward_keur = r98_distribution_account_keur
   else:
       r99_fcf_for_distribution_keur = r98_distribution_account_keur
       r100_carryforward_keur = 0
   ```

5. Feed PR B2 SHL waterfall with:

   ```text
   fcf_for_shl = max(0, r99_fcf_for_distribution_keur)
   ```

Guardrails:

- TUHO feature flag only.
- No revenue engine changes.
- No OPEX engine changes.
- No full tax refactor.
- No hardcoded Excel period values.
- Do not reimplement `fcf_waterfall` until this R99/R102 input is measured.

## Recommendation

Do not revive PR B2 until a TUHO-only R99/R102 input engine is measured against
Excel R99/R102. The first acceptance gate should be:

```text
Python R99/R102 total within +/-1% of Excel 234,745 kEUR
Selected periods 0, 10, 20, 24, 28, 34, 36 within +/-100 kEUR
```

Only after that should the SHL `fcf_waterfall` mechanics be reintroduced.
