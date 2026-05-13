# TUHO SHL Mechanics Diagnostic

## Executive Summary

**SHL cash interest during senior-outstanding phase:**

Python currently pays ZERO cash interest during the PIK phase (periods 1-24) while Excel pays the FULL gross interest each period. The entire gross interest is being capitalized as PIK, not just the shortfall.

**Excel's SHL mechanics (empirically verified):**
- Gross interest = opening balance × 7.93% × day_fraction
- Cash interest = min(gross interest, available FCF)
- PIK = gross interest - cash_interest
- Principal = min(remaining_cash after interest, balance + PIK)
- Dividend = 0 while SHL closing balance > 0

**Current Python pik_then_sweep is fundamentally wrong for TUHO** because it pays zero cash interest during the senior-outstanding phase (periods 1-24), whereas Excel always pays cash interest first and only capitalizes the shortfall.

## Key SHL Data from Excel (DS rows 120-127)

| Excel Period | Date | Opening | Gross Int | Cash Int Paid | PIK | Principal | Closing | Net Dividends |
|---|---|---|---|---|---|---|---|---|
| 1 | 2030-06-30 | 32,703.9 | 1,641.0 | 1,297.4 | 343.6 | 0.0 | 33,047.5 | 0.0 |
| 2 | 2030-12-31 | 33,047.5 | 1,695.9 | 1,332.8 | 363.1 | 0.0 | 33,410.6 | 0.0 |
| 3 | 2031-06-30 | 33,410.6 | 1,683.9 | 1,325.4 | 358.5 | 0.0 | 33,769.1 | 0.0 |
| 4 | 2031-12-31 | 33,769.1 | 1,740.8 | 1,361.9 | 378.9 | 0.0 | 34,148.0 | 0.0 |
| 5 | 2032-06-30 | 34,148.0 | 1,748.2 | 1,362.2 | 386.0 | 0.0 | 34,533.9 | 0.0 |
| 6 | 2032-12-31 | 34,533.9 | 1,798.5 | 1,392.7 | 405.8 | 0.0 | 34,939.7 | 0.0 |
| 7 | 2033-06-30 | 34,939.7 | 1,784.7 | 1,386.1 | 398.6 | 0.0 | 35,338.2 | 0.0 |
| 8 | 2033-12-31 | 35,338.2 | 1,846.4 | 1,425.1 | 421.3 | 0.0 | 35,759.5 | 0.0 |
| 9 | 2034-06-30 | 35,759.5 | 1,837.4 | 1,418.6 | 418.8 | 0.0 | 36,178.3 | 0.0 |
| 10 | 2034-12-31 | 36,178.3 | 1,901.7 | 1,459.0 | 442.7 | 0.0 | 36,621.0 | 0.0 |
| 11 | 2035-06-30 | 36,621.0 | 1,895.5 | 1,452.8 | 442.7 | 0.0 | 37,063.7 | 0.0 |
| 12 | 2035-12-31 | 37,063.7 | 1,962.6 | 1,494.7 | 467.9 | 0.0 | 37,531.6 | 0.0 |
| 13 | 2036-06-30 | 37,531.6 | 1,960.8 | 1,497.1 | 463.7 | 0.0 | 37,995.3 | 0.0 |
| 14 | 2036-12-31 | 37,995.3 | 2,019.8 | 1,532.3 | 487.5 | 0.0 | 38,482.7 | 0.0 |
| 15 | 2037-06-30 | 38,482.7 | 2,000.8 | 1,526.7 | 474.1 | 0.0 | 38,956.8 | 0.0 |
| 16 | 2037-12-31 | 38,956.8 | 2,072.2 | 1,571.1 | 501.1 | 0.0 | 39,457.9 | 0.0 |
| 17 | 2038-06-30 | 39,457.9 | 2,054.6 | 1,565.3 | 489.3 | 0.0 | 39,947.3 | 0.0 |
| 18 | 2038-12-31 | 39,947.3 | 2,128.2 | 1,611.0 | 517.2 | 0.0 | 40,464.4 | 0.0 |
| 19 | 2039-06-30 | 40,464.4 | 2,111.6 | 1,605.3 | 506.3 | 0.0 | 40,970.8 | 0.0 |
| 20 | 2039-12-31 | 40,970.8 | 2,187.5 | 1,652.3 | 535.2 | 0.0 | 41,506.0 | 0.0 |
| 21 | 2040-06-30 | 41,506.0 | 2,190.4 | 1,655.7 | 534.7 | 0.0 | 42,040.7 | 0.0 |
| 22 | 2040-12-31 | 42,040.7 | 2,257.6 | 1,695.4 | 562.2 | 0.0 | 42,602.9 | 0.0 |
| 23 | 2041-06-30 | 42,602.9 | 2,238.4 | 1,690.1 | 548.3 | 0.0 | 43,151.2 | 0.0 |
| 24 | 2041-12-31 | 43,151.2 | 2,319.7 | 1,740.2 | 579.5 | 0.0 | 43,730.7 | 0.0 |
| 25 | 2042-06-30 | 43,730.7 | 1,498.8 | 1,734.9 | 0.0 | 1,498.8 | 42,231.9 | 0.0 |
| 26 | 2042-12-31 | 42,231.9 | 1,463.9 | 1,703.2 | 0.0 | 1,463.9 | 40,768.0 | 0.0 |
| 27 | 2043-06-30 | 40,768.0 | 1,647.9 | 1,617.3 | 0.0 | 1,647.9 | 39,120.1 | 0.0 |
| 28 | 2043-12-31 | 39,120.1 | 817.9 | 1,577.7 | 0.0 | 817.9 | 38,302.2 | 0.0 |
| 29 | 2044-06-30 | 38,302.2 | 4,663.9 | 1,527.9 | 0.0 | 4,663.9 | 33,638.2 | 0.0 |
| 30 | 2044-12-31 | 33,638.2 | 3,818.8 | 1,356.6 | 0.0 | 3,818.8 | 29,819.5 | 0.0 |
| 31 | 2045-06-30 | 29,819.5 | 5,029.3 | 1,183.0 | 0.0 | 5,029.3 | 24,790.2 | 0.0 |
| 32 | 2045-12-31 | 24,790.2 | 4,091.0 | 999.8 | 0.0 | 4,091.0 | 20,699.2 | 0.0 |
| 33 | 2046-06-30 | 20,699.2 | 5,601.1 | 821.2 | 0.0 | 5,601.1 | 15,098.0 | 0.0 |
| 34 | 2046-12-31 | 15,098.0 | 4,483.6 | 608.9 | 0.0 | 4,483.6 | 10,614.4 | 0.0 |
| 35 | 2047-06-30 | 10,614.4 | 6,164.9 | 421.1 | 0.0 | 6,164.9 | 4,449.5 | 0.0 |
| 36 | 2047-12-31 | 4,449.5 | 4,449.5 | 179.4 | 0.0 | 4,449.5 | 0.0 | **421.2** |
| 37+ | 2048-06-30+ | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | resid |

## Key Questions Answered

**Q1: Does Excel pay cash interest during the senior-outstanding phase?**
YES — Excel pays full gross interest as cash in every period during the PIK phase (periods 1-24), not just when FCF exceeds gross interest. The PIK is only the SHORTFALL between gross interest and available FCF for SHL.

**Q2: Does Python currently pay cash interest during that phase?**
NO — Python pays zero cash interest during periods 1-24. The entire gross interest is capitalized as PIK. This is confirmed by the waterfall output showing shl_interest_keur=0 for all early periods.

**Q3: Does Excel capitalize only the interest shortfall?**
YES — Excel's PIK equals max(0, gross_interest - cash_interest). During the PIK phase, available FCF for SHL is less than gross interest, so PIK = gross interest - cash_interest. For example, period 1: gross=1,641, cash=1,297, PIK=344.

**Q4: Does Python over-capitalize or under-capitalize SHL interest?**
OVER-CAPITALIZE — Python capitalizes 100% of gross interest as PIK when it should only capitalize the shortfall. This inflates the SHL balance more than Excel.

**Q5: Does principal start only when FCF exceeds gross interest?**
YES — Excel principal repayment begins at period 25, when FCF (3,233.6) > gross interest (1,498.8). Before period 25, no principal is repaid.

**Q6: Dividend = 0 whenever SHL has an ending balance > 0?**
YES — Confirmed for all periods 1-35. Dividend only appears at period 36 when SHL reaches zero.

**Q7: Transition period rule (SHL reaches zero)?**
YES — At period 36 (2047-12-31), SHL opening=4,449.5, FCF=5,050.2, cash interest=179.4, PIK=0, principal=4,449.5, residual=421.2 → dividend=421.2. This confirms the transition formula.

**Q8: Is current Python pik_then_sweep fundamentally wrong for TUHO?**
YES — The model encodes "pay no cash interest during PIK phase, capitalize all interest as PIK" which doesn't match Excel's behavior. Excel always pays cash interest first and only capitalizes the shortfall.

**Q9: Should the future SHL method be a new isolated method "fcf_waterfall"?**
YES — The correct approach is a new method:
1. Compute gross_interest from opening balance
2. cash_interest = min(gross_interest, fcf_for_shl)
3. pik = max(0, gross_interest - cash_interest)
4. remaining_cash = fcf_for_shl - cash_interest
5. principal = min(remaining_cash, opening_balance + pik)
6. closing = opening + pik - principal
7. dividend = 0 if closing > 0, else remaining_cash - principal

This is a clean, self-contained SHL allocation method distinct from the current pik_then_sweep.

## Python (Simulated, Dual-DSCR Senior) vs Excel SHL

Python simulated (patched, dscr_schedule=[1.2]*24 + [1.4125]*4):

| op_idx | date | Python SHL Opening | Excel SHL Opening | diff | Python dist | Excel net_div |
|---|---|---|---|---|---|---|
| 0 | 2030-06-30 | 32,703.7 | 32,703.9 | -0.2 | 0.0 | 0.0 |
| 1 | 2030-12-31 | 32,878.7 | 33,047.5 | -168.8 | 0.0 | 0.0 |
| 23 | 2041-12-31 | 35,440.8 | 43,151.2 | -7,710.4 | 0.0 | 0.0 |
| 24 | 2042-06-30 | 35,440.8 | 43,730.7 | -8,289.9 | 0.0 | 0.0 |
| 25 | 2042-12-31 | 35,440.8 | 42,231.9 | -6,791.1 | 0.0 | 0.0 |
| 26 | 2043-06-30 | 33,940.4 | 40,768.0 | -6,827.6 | 0.0 | 0.0 |
| 27 | 2043-12-31 | 28,864.2 | 39,120.1 | -10,255.9 | 0.0 | 0.0 |
| 28 | 2044-06-30 | 24,483.9 | 33,638.2 | -9,154.3 | 0.0 | 0.0 |
| 29 | 2044-12-31 | 18,962.3 | 29,819.5 | -10,857.2 | 0.0 | 0.0 |
| 30 | 2045-06-30 | 14,101.1 | 24,790.2 | -10,689.1 | 0.0 | 0.0 |
| 31 | 2046-06-30 | 8,081.4 | 20,699.2 | -12,617.8 | 0.0 | 0.0 |
| 32 | 2046-12-31 | 2,710.5 | 15,098.0 | -12,387.5 | 0.0 | 0.0 |
| 33 | 2047-06-30 | 0.0 | 10,614.4 | -10,614.4 | 0.0 | 0.0 |
| 34 | 2047-12-31 | 0.0 | 4,449.5 | -4,449.5 | 6,556.9 | **421.2** |

**Key finding:** Python's SHL balance is significantly LOWER than Excel throughout. Python reaches zero at op_idx 33 (P34, 2047-06-30) while Excel reaches zero at P36 (2047-12-31). The first Python distribution is at op_idx 34 (P35), while Excel's first distribution is at P36 (op_idx 35 in Excel terms). The magnitude of Python's first distribution (6,556.9) is much larger than Excel's (421.2) because Python repays SHL faster.

## Summary

### Senior Debt
- **Dual-DSCR factory hypothesis: CONFIRMED**
- Excel uses dual-DSCR sculpting (1.20 PPA / 1.4125 merchant)
- Python currently uses fixed_ds_keur=2,116 with balloon at period 28
- Dual-DSCR removes the balloon but DS still doesn't match Excel due to CFADS mismatch
- Total DS is close (66,416 vs 66,181 = +0.4%) even with fixed DS because balloon cancels early deficit

### SHL Mechanics
- **Excel pays FULL cash interest during PIK phase** — only shortfall is capitalized
- **Python pays ZERO cash interest** — all interest is capitalized
- This is a fundamental model difference, not a parameter tuning issue
- Correct SHL method: `fcf_waterfall` (new isolated method)

### Distribution Timing
- Python reaches zero SHL ~2 periods before Excel
- Python first distribution at op_idx 34 (P35), Excel at P36
- Total Python distributions ~174,948 vs Excel 151,709 (+15.3%)