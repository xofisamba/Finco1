# MVP G1 Red Workflow Classification

Base evidence: `08f12a1516173efaab7d2569022a24b101b03976`.
G1 base: `c2942d736a1d08ddf503bc8098a6d6e6ea6cb18e`.

`A` means current regression, `B` superseded assertion, and `C` known
compatibility/governance debt. Direct GitHub logs showed no `A` item.

| Workflow/test | Old authority | Current authority | Class | Action |
|---|---|---|---|---|
| CI Oborovo frozen sizing mode | Phase 23A frozen schedule | C3B3A/B6-B8 calculation-driven Senior | B | Removed from current CI selection; retained test file |
| CI Oborovo distribution 71,598 | Phase 23O distribution snapshot | Later sponsor/distribution stage, not G0/G1 | C | Removed from current CI selection; retained diagnostic |
| Phase2A Oborovo period index | old OPERATING_CORE_V1 snapshot | canonical B6/B7 period axis | B | Phase2A manual diagnostic |
| Phase2A Oborovo production | old source snapshot | canonical Base performance | B | Phase2A manual diagnostic |
| Phase2A Oborovo revenue drift set | old B2 drift indices | C2B/B6 current performance | B | Phase2A manual diagnostic |
| Phase2A TUHO tax depreciation | old snapshot | unresolved project compatibility | C | Phase2A manual diagnostic |
| Phase2A Oborovo tax depreciation | old snapshot | B1/C3 canonical basis | B | Phase2A manual diagnostic |
| Phase2A governed surface | old book-only drift model | later tax-depreciation architecture | B | Phase2A manual diagnostic |
| Phase2A magnitude precondition | old B2 drift set | later revenue authority | B | Phase2A manual diagnostic |
| Phase2A schema/payload status | injected snapshots with stale identity | current identity-first comparator | B | Retained diagnostic, no assertion rewrite |
| Phase2A raw TUHO/Oborovo scanner (8 files) | substring absence | no identity-driven execution | B | Replaced by AST execution-dispatch guard |
| Phase2B Oborovo 488 differences | TAX_CFADS_V1 exact correction snapshot | canonical generic tax invariants/C3B1 evidence | C | Snapshot test marked historical; no ledger entries or baseline refresh |
| Phase2B TUHO exact matcher 172 differences | TAX_CFADS_V1 correction-ledger snapshot | canonical generic tax invariants/C3B1 evidence | C | Exact matcher marked historical; no ledger entries or baseline refresh |
| Parity Oborovo OPEX 48,847.5 | Phase 51E pre-hierarchical OPEX golden | hierarchical OPEX runtime | B | Replaced by finite/nonnegative semantic invariant |
| Parity waterfall_core SHA | Phase 51F implementation snapshot | semantic runtime gates | B | Removed; no replacement hash |
| Parity project_factories SHA | Phase 51F implementation snapshot | semantic factory/authority gates | B | Removed; no replacement hash |
| C3B3B residual/period/CIT assertions | pre-B5/B6 clean debt state | B5-B8/G0 authority | B | Manual diagnostic |
| Phase1B/Phase2C/Phase2D automatic checks | historical snapshot/phase authority | G1/G0/C3B3A/B5-B8 current gates | B/C | Manual diagnostic |

## Identity occurrence audit

The inspected strings in `shl_cash_seam.py`, `shl_inputs.py`, `tax_inputs.py`,
`policies/tax.py`, `shl/contracts.py`, `shl/day_count.py`, `shl/production.py`,
and `shl/waterfall.py` are comments, docstrings, validation/provenance labels, or
source-evidence descriptions. None controls execution through project name, code,
baseline ID, or workbook identity. The AST guard rejects such execution branches
while allowing those benign evidence labels.

## Workflow trigger decisions

- All historical/diagnostic workflows are `workflow_dispatch` only. The audited
  set is Phase 1B, Phase 2A, Phase 2B, C3B3B, C3B3C, C3B3D0, C3B3D1,
  C3B3D2A, B0, B1, B2C, B3, B4, Phase 2C, and Phase 2D.
- `CI`: remains automatic; its core job runs current semantic revenue/OPEX/SHL/G1
  checks, while route, persistence, records, and quarantine jobs remain unchanged.
- `Parity Guardrails`: remains automatic with semantic output validity, immutable
  source-extraction hashes, and service import boundaries.
- `MVP G1`: new exact-head automatic current-authority gate.
- G0, B5, B6, B7, B8, C3B1, and C3B3A remain current blocking exact-head gates.

The G0 textual calibration scan is restricted to production code. G1 owns the
negative-test corpus and AST identity-dispatch proof, so forbidden examples in
tests cannot masquerade as production violations.

## Trigger audit

| Historical workflow | Before G1 final fix | Final trigger | Authority action |
|---|---|---|---|
| Phase 1B | manual | `workflow_dispatch` | retain diagnostic |
| Phase 2A | manual | `workflow_dispatch` | retain diagnostic |
| Phase 2B | manual | `workflow_dispatch` | retain diagnostic |
| C3B3B | malformed dispatch plus stage-branch push | `workflow_dispatch` | remove invalid/stale triggers |
| C3B3C | PR plus stage-branch push | `workflow_dispatch` | demote superseded authority |
| C3B3D0 | PR plus stage-branch push | `workflow_dispatch` | demote superseded authority |
| C3B3D1 | PR plus stage-branch push | `workflow_dispatch` | demote superseded authority |
| C3B3D2A | PR plus stage-branch push | `workflow_dispatch` | demote superseded authority |
| B0 | PR plus stage-branch push | `workflow_dispatch` | demote superseded authority |
| B1 | PR plus stage-branch push | `workflow_dispatch` | demote superseded authority |
| B2C | PR plus stage-branch push | `workflow_dispatch` | demote superseded authority |
| B3 | PR plus stage-branch push | `workflow_dispatch` | demote superseded authority |
| B4 | PR plus stage-branch push | `workflow_dispatch` | demote superseded authority |
| Phase 2C | manual | `workflow_dispatch` | retain diagnostic |
| Phase 2D | manual | `workflow_dispatch` | retain diagnostic |

The blocking ring remains MVP G1, MVP G0, B5, B6, B7, B8, C3B1, C3B3A,
CI, and Parity Guardrails. The workflow-authority regression test prevents a
historical workflow from regaining an automatic trigger and prevents the current
ring from silently losing its pull-request trigger.
