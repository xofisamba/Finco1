# Phase 7F TUHO Excel vs Python R99 Bridge Summary
1. Output Excel file path: `C:\Users\Ivan\Documents\New project 2\phase7f-current-20260514213554\xofisamba-Finco1-bf6ec5ff444994a582d4d4de452c6cfe99147d8e\phase7f_tuho_excel_vs_python_r99_bridge.xlsx`
2. Excel workbook/sheet/range used: `20260330_TUHO_BP.xlsm`; sheets `CF`, `DS`, `Eq`; operating period columns matched by CF row 2 EoP dates from 30/06/2030 through model horizon. Construction column `G` ending 31/12/2029 was excluded.
3. Period mapping: Excel dates from `CF!H2:...` were matched to Python `WaterfallPeriod.date`; no raw index alignment was used.
4. Senior loan schedule labels used: `DS!47 Beginning`, `DS!50 Net Interests`, `DS!49 Principal`, `DS!54 Senior Debt Service`, `DS!53 End`.
5. SHL schedule labels used: `DS!120 Beginning`, `DS!122 Net interest payment`, `DS!125 Interests to capitalize`, `DS!124 Principal`, `DS!127 Debt Service (incl. WHT)`, `DS!126 End`. Cash interest is reconstructed as `DS!122 - DS!125`.
6. Top 10 total deltas by absolute value:
   - SHL opening balance: -156,613.4 kEUR
   - SHL closing balance: -156,613.2 kEUR
   - R119 Net dividends / official equity distribution target: 23,184.4 kEUR
   - R106 FCF for dividends / gross dividends: 22,634.4 kEUR
   - Senior opening balance: 18,840.9 kEUR
   - Senior closing balance: 18,840.4 kEUR
   - R67 CorpTax: 18,304.3 kEUR
   - R84 FCF Junior: 14,800.0 kEUR
   - R98 Distribution Account: 14,800.0 kEUR
   - R99/R102 FCF for SHL input: 14,800.0 kEUR

7. Top 10 period deltas by absolute value:
   - SHL opening balance, 30/06/2042: -8,289.9 kEUR
   - SHL closing balance, 31/12/2041: -8,289.9 kEUR
   - SHL opening balance, 31/12/2041: -8,111.4 kEUR
   - SHL closing balance, 30/06/2041: -8,111.4 kEUR
   - SHL opening balance, 30/06/2047: -7,903.9 kEUR
   - SHL closing balance, 31/12/2046: -7,903.9 kEUR
   - SHL opening balance, 30/06/2041: -7,563.1 kEUR
   - SHL closing balance, 31/12/2040: -7,563.1 kEUR
   - SHL opening balance, 31/12/2040: -7,379.5 kEUR
   - SHL closing balance, 30/06/2040: -7,379.5 kEUR

8. Component explaining most of the R99/R102 gap: the bridge confirms R99/R102 is not solved by the simple Python proxy. The largest related contributors remain R69/tax timing and op_idx 24 revenue/PPA boundary timing; the workbook includes both current simple proxy and C1a helper diagnostic rows.
9. Component explaining most of the senior debt service gap: total senior DS is close after PR B1, but period timing differences remain, especially around op_idx 24-27 transition.
10. Component explaining most of the SHL balance/service gap: current Python `pik_then_sweep` pays/records cash service differently from Excel cash-interest-first mechanics, so SHL PIK/cash interest timing and principal timing dominate.
11. Missing difference classification: mainly mixed R69/tax timing, period mapping around PPA/merchant transition, senior interest/principal timing, and SHL interest/PIK/principal timing. DSRA/JDSRA/reserve sweep/junior debt are either zero or diagnostic proxies in current Python output.
12. Recommendation: do not enable C1b or B2 yet. Use this workbook to isolate op_idx 24 revenue boundary and tax payable timing before attempting a TUHO-only R99 helper opt-in, then retry SHL fcf_waterfall only after R99 input is within tolerance.

## Rows not directly mapped / limitations
- Python local_tax_keur not exposed; R63 defaults to 0.0.
- Python reserve/cash interest income not exposed; R66 defaults to 0.0.
- Python junior debt service is not implemented/exposed for TUHO; R85 defaults to 0.0.
- Python reserve sweep not exposed; R96 defaults to 0.0.
- Python gross dividend before WHT not separately exposed; R106 uses distribution_keur as proxy.
- Python SHL gross interest is diagnostic: opening SHL balance * shl_rate / 2. Current pik_then_sweep exposes shl_interest_keur and shl_pik_keur, not an explicit gross-interest field.
- Python R104 uses sign-adjusted cash service: -(cash interest paid + principal). Cash interest paid is interpreted as max(0, shl_interest_keur - shl_pik_keur).
- Excel R98/R100 are extracted directly from CF rows, but Python R98/R100 are diagnostic proxies, not runtime fields.
- Python gross dividend before withholding is not separately exposed; R106 uses `distribution_keur` as proxy.
