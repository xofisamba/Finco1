# FincoGPT Demo Script

> _Use this when presenting FincoGPT to investors, partners, or new team members._

---

## 1. Introduction — What is FincoGPT?

**FincoGPT** is a fast project-finance screening tool for solar and wind energy assets.

### What it does
- Computes **Project IRR**, **Equity IRR**, and **DSCR** in seconds
- Runs scenario analysis (Base / Downside / Upside) automatically
- Produces a full waterfall, revenue, debt, and tax schedule
- Exports everything to Excel — no formulas, just values

### The three key metrics
| Metric | What it measures | Typical investor threshold |
|--------|-----------------|---------------------------|
| **Project IRR** | Return on total capital (equity + debt) | 8–15% depending on risk |
| **Equity IRR** | Return on equity only (after debt service) | 10–20% for sponsors |
| **DSCR** | Cash cushion — can the project service debt? | ≥ 1.20x (often lockup at 1.10x) |

### Economic LCOE
The model also calculates **Economic LCOE** — the levelised cost of energy independent of financing. This is useful for comparing projects on a pure cost basis before financing decisions are made.

---

## 2. Solar Walkthrough

**Start:** Open FincoGPT → Select **Solar** → Click **Run Model**

### Base Case KPIs
Show the dashboard. Key numbers to highlight:
- **Project IRR** — should land around 10–12% for a well-structured solar project
- **Equity IRR** — typically 2–4 percentage points above Project IRR due to leverage
- **Min DSCR** — the tightest cash point; should be ≥ 1.20x for bankability
- **Avg DSCR** — average over the tenor; higher = more headroom

### Downside Scenario
Change scenario selector to **Downside** → Run again.

Highlight what moves:
- **P50 yield** drops 10% (less sun / more downtime)
- **CapEx** increases 5% (cost overruns)
- **OpEx** increases 10% (higher maintenance)
- **Tariff** drops 5%

Expected changes:
- Project IRR decreases by ~1.5–2.5 percentage points
- DSCR tightens by ~0.05–0.10x

**Talking point:** "Even in a downside scenario the DSCR stays above 1.15x — that's the kind of buffer banks look for."

### Upside Scenario
Change to **Upside** → Run again.

Highlight:
- P50 yield +5%, CapEx -3%, OpEx -5%, Tariff +3%
- IRR improves visibly
- DSCR improves

**Talking point:** "Upside shows what happens if conditions outperform the base case — useful for understanding optionality."

---

## 3. Key Metrics to Highlight During the Demo

### 3a. Project IRR Sensitivity to Tariff
The single biggest driver of IRR is the **PPA tariff**. Show this by noting:
- A EUR 5/MWh tariff change ≈ ~0.5–1.0 percentage point change in Project IRR
- This is why tariff risk is the first thing investors negotiate

### 3b. DSCR Across Scenarios
- The DSCR is calculated **every period** after debt sizing
- Downside DSCR is the relevant metric for bankability discussions
- Note the lockup threshold (typically 1.10x) vs. the target (1.20x)

### 3c. Economic LCOE
- LCOE in the Notes sheet is computed without financing costs
- It answers: "What is the unsubsidised cost of generation?"
- Useful when comparing to market price curves or merchant exposure

---

## 4. Talking Points

### "This is a screening model, not a bank model."
FincoGPT is designed for the first question: **"Is this worth spending more time on?"**

It answers that in seconds. A full bank model takes weeks and requires granular engineering, grid study, and full legal due diligence.

### "Use for quick decision: invest more time?"
- If Project IRR < 6% and DSCR < 1.15x → likely not bankable, pass
- If Project IRR > 10% and DSCR > 1.30x → promising, proceed to full model
- Everything in between → use FincoGPT scenario range to frame due diligence

### "Full bank model needs more diligence"
- topographic and grid studies
- full EPC contract review
- offtaker credit assessment
- detailed construction budget and timeline risk
- legal opinion on PPA enforceability

FincoGPT does not replace any of that. It helps you decide whether to begin that work.

---

## 5. Wind Walkthrough (Brief)

**Start:** Select **Wind** → Run Model

Key differences to highlight:
- Wind has **balancing costs** (~$8/MWh) deducted from revenue — solar does not
- Wind typically has **no degradation** in the base model
- P50 hours for wind are much higher (~2,800–3,500 vs ~1,500 for solar), so revenue per MW is higher
- But CapEx per MW is also higher for wind vs. solar

Run Base → Downside → Upside and note the same DSCR and IRR dynamics.

---

## 6. Demo Tips

- **Always start with Solar** — most investors immediately grasp solar PV economics
- **Show the waterfall tab** — point out CFADS → Senior Debt Service → Distributions flow
- **Toggle Annual view** — some investors prefer annual summaries; Semiannual is the default for precision
- **Export to Excel** — show that the exported workbook is clean, readable, and easy to share internally
- **Scenario table** — show the scenario delta table to explain what changed between Base/Downside/Upside
- **Don't demo Portfolio yet** — it is marked experimental; use Solar/Wind for the full experience

---

## 7. Limitations

- **No construction period modelling** — simplified construction schedule, not a full delay-risk model
- **Tax is simplified** — ATAD/LCF rules are included but custom structures need manual review
- **Revenue model** — PPA is assumed to be fully contracted; merchant exposure uses a simple price curve
- **No counterparty credit analysis** — offtaker risk is not modelled
- **DSCR sculpting** — debt sizing uses DSCR-target method; fixed-repayment structures need separate verification
