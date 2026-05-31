# FincoGPT - Pilot User Guide

> **Note:** FincoGPT is an internal pilot tool. It is not a lender approval, bank approval, external audit, or SaaS-ready product.

---

## What is FincoGPTv

FincoGPT is an internal pilot tool for structured financial modelling of renewable energy projects (wind and solar). It computes:

- Senior debt sizing
- Equity returns (IRR)
- Debt service coverage ratios (DSCR)
- Distributions to sponsors

All calculations are performed by a Python backend engine. The browser shows results - it does not calculate them.

---

## Quick Start

1. **Open a project** - Use TUHO Wind or Oborovo Solar for validated results
2. **Review inputs** - Check capacity, tariff, CAPEX, OPEX in the sidebar
3. **Save a scenario** - Give it a name before changing anything
4. **Run the model** - Click Run; wait for backend to finish
5. **Review results** - KPIs appear in Overview; detailed tables in each tab
6. **Check Audit / Parity** - See how results compare to the Excel reference
7. **Export** - Download XLSX, CSV, or parity workbooks from the Downloads tab

---

## Validated Scope

| Project | Status |
|---------|--------|
| TUHO Wind (72 MW, Croatia) | [Validated] Parity-validated |
| Oborovo Solar (53.63 MW, Croatia) | [Validated] Parity-validated |
| Generic / new projects | [Warning] Unvalidated - review independently |

TUHO and Oborovo are frozen-templates verified against Excel. Their outputs (senior debt, SHL opening, distributions, CO2 revenue) are considered reliable within tolerance.

Generic projects are for exploration. Do not treat their outputs as validated until a separate review is completed.

---

## How to Read the Results

### KPIs (Overview tab)
- **Project IRR** - return on total capital; +/-0.5pp tolerance vs Excel
- **Equity IRR** - return on equity; +/-1.0pp tolerance vs Excel
- **Avg DSCR** - average debt service coverage; target typically 1.30-1.50x
- **Senior Debt** - total debt quantum from the model

### Audit / Parity tab
This tab summarises how closely the model matches the Excel reference. It is **internal review tooling, not a certified external audit**.

| Colour | Meaning |
|--------|---------|
| Green Green | Within tolerance |
| Yellow Yellow | Accepted convention difference |
| Red Red | Gap - review |

The primary anchors are Senior Debt, SHL Opening, and Distributions.

---

## Export and Download

Exports are based on the **last clean backend run**, not unsaved draft edits. If you changed inputs after the last run:

1. Save the scenario
2. Run the model again
3. Then export

Available exports:
- **Values-only Excel** - model outputs with provenance notes
- **Runtime Summary CSV** - KPIs and governance posture
- **Institutional Workbook** - reviewer-facing workbook with cover notes
- **Parity Workbook** - TUHO horizontal review vs Excel
- **Gap Register** - all parity gaps and statuses
- **Source Map** - column-by-column provenance

---

## Backup and Restore

### Auto-backup
The app creates an automatic backup of the database every 24 hours (configurable). Up to 10 auto-backups are kept. Manual backups and pre-restore safety backups are never automatically deleted.

### Restore
Go to the Downloads tab or settings to find and restore a backup. This replaces the current database state - use with care.

### Scope
Auto-backup is for single-user internal recovery. No offsite or cloud backup is provided.

---

## What FincoGPT is NOT

| Claim | Status |
|-------|--------|
| Lender / bank approval | [Not included] Not provided |
| External audit | [Not included] Not provided |
| Certification | [Not included] Not provided |
| SaaS-ready / multi-tenant | [Not included] Not implemented |
| Live sculpting solver | [Not included] Frozen fixture-backed schedule |
| Multi-user with RBAC | [Not included] Single-user internal mode |

---

## If Results Look Stale

Outputs reflect the last backend run. If the current draft differs from the last run:

1. Save the current scenario
2. Run the model again
3. Re-export

Do not share exported results if inputs changed after the last run.

---

## Getting Help

- Overview tab -> workflow guide at the top
- Downloads tab -> limitations banner
- Audit / Parity tab -> parity evidence and conventions
- Help icon (Help) -> collapsible onboarding panel

For technical issues, contact the team maintaining the backend.

---

*Last updated: Phase 25B. FincoGPT internal pilot - not for external distribution.*
