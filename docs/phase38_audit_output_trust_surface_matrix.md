# Phase 38 - Audit Output Trust-Surface Matrix

| Surface | Current issue | Change made or recommendation | Validation status affected? | User impact | Trusted pilot blocker? | Follow-up phase |
|---|---|---|---|---|---|---|
| Audit / Reconciliation tab | Validated TUHO/Oborovo evidence was mixed with generic, pending, and future-scope rows | Added explicit `Validated pilot evidence` and `Pending / unvalidated / future scope` groupings | No | Easier to read what is trusted vs contextual | No | Phase 38B / 39 |
| Validation panel | Input-check message had garbled display text and could be over-read as broader trust approval | Cleaned wording; kept it scoped to input checks only | No | Cleaner and less misleading | No | Monitor |
| Debt / DSCR / SHL panel | Frozen-schedule trust message had mojibake and generic-path boundary was implicit | Cleaned copy and reinforced exploratory generic boundary | No | Better debt-surface trust clarity | No | Future polish |
| Runtime summary | Runtime banner had mojibake and clean-run boundary was still cognitively dense | Clarified that runtime and exports reflect the last clean backend run | No | Better operator understanding of stale vs clean runtime | No | Future simplification |
| Downloads / export artifacts | Export names were team-friendly but not always operator-friendly | Clarified purpose of Values-only Excel, Runtime Summary CSV, Institutional Workbook, Parity Workbook, Gap Register, and Source Map | No | Easier artefact selection | No | Future catalogue polish |
| Scenario version history / stale runtime | Draft vs saved vs runtime remains accurate but dense | No structural change; keep Phase 37 explanation and consider future simplification | No | Still honest, but cognitively heavy | No | Future polish |
| Generic project warning | Generic exclusion was correct but easy to miss among denser surfaces | Repeated generic unvalidated/exploratory warning in audit and export trust surfaces | No | Stronger trust boundary | Yes, if ignored | Keep prominent |
| Backup/restore expectations | Documented, but not very discoverable in-product | Recommendation only; no product-behavior change in Phase 38 | No | Mild operator friction remains | No | Operational UX follow-up |
| Non-claims / limitations | Some trust-facing docs still had garbled presentation and scattered non-claims | Cleaned wording in pilot and validation docs; kept non-claims explicit | No | Reduces overclaiming risk | No | Ongoing copy maintenance |
