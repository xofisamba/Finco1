# Validation Golden Values

This document records the expected KPI outputs for all 6 standard scenarios.
Tests fail if KPIs drift beyond tolerance.

## Tolerances
- IRR: ±50 bps (0.50%)
- DSCR: ±0.05
- Revenue/EBITDA totals: ±5%
- Senior debt: ±5%
- Distributions: ±10%

## Solar Base
| KPI | Value | Unit |
|-----|-------|------|
| project_irr | 0.1040 | % |
| equity_irr | 0.1358 | % |
| min_dscr | 1.4421 | ratio |
| avg_dscr | 1.6502 | ratio |
| total_revenue_keur | 119531.69 | kEUR |
| total_ebitda_keur | 107361.21 | kEUR |

## Solar Downside
| KPI | Value | Unit |
|-----|-------|------|
| project_irr | 0.0812 | % |
| equity_irr | 0.0897 | % |
| min_dscr | 1.3302 | ratio |
| avg_dscr | 1.5182 | ratio |
| total_revenue_keur | 104754.20 | kEUR |
| total_ebitda_keur | 91366.68 | kEUR |

## Solar Upside
| KPI | Value | Unit |
|-----|-------|------|
| project_irr | 0.1169 | % |
| equity_irr | 0.1440 | % |
| min_dscr | 1.6083 | ratio |
| avg_dscr | 1.8400 | ratio |
| total_revenue_keur | 127561.16 | kEUR |
| total_ebitda_keur | 115999.21 | kEUR |

## Wind Base
| KPI | Value | Unit |
|-----|-------|------|
| project_irr | 0.1602 | % |
| equity_irr | 0.1574 | % |
| min_dscr | 2.3553 | ratio |
| avg_dscr | 2.7237 | ratio |
| total_revenue_keur | 265485.88 | kEUR |
| total_ebitda_keur | 247869.62 | kEUR |

## Wind Downside
| KPI | Value | Unit |
|-----|-------|------|
| project_irr | 0.1334 | % |
| equity_irr | 0.1445 | % |
| min_dscr | 1.9061 | ratio |
| avg_dscr | 2.2064 | ratio |
| total_revenue_keur | 233500.25 | kEUR |
| total_ebitda_keur | 214122.36 | kEUR |

## Wind Upside
| KPI | Value | Unit |
|-----|-------|------|
| project_irr | 0.1758 | % |
| equity_irr | 0.1654 | % |
| min_dscr | 2.6304 | ratio |
| avg_dscr | 3.0407 | ratio |
| total_revenue_keur | 282566.11 | kEUR |
| total_ebitda_keur | 265830.66 | kEUR |