# Pilot Issue Log Template

A shared table for tracking issues raised during the External Friendly
Pilot. Copy this table into a shared spreadsheet or tracker and add a
row per issue as it's reported.

## Categories

- **UX** — usability, clarity, navigation, wording
- **Validation** — validation status, known limitations, caveats
- **Scenario** — scenario creation, comparison
- **Export** — workbook export, export content
- **Data** — incorrect or unexpected calculated values
- **Performance** — slowness, timeouts, unresponsive UI
- **Documentation** — pilot guide, known limitations, help content
- **Other** — anything not covered above

## Severity

- **Blocker** — pilot user cannot complete a core workflow step
- **Major** — workflow completes but result is wrong, confusing, or
  untrustworthy
- **Minor** — cosmetic, wording, or low-impact friction
- **Suggestion** — not a defect; an idea for improvement

## Log Table

| Date | Reporter | Category | Severity | Description | Reproduction Steps | Workaround | Owner | Status |
|------|----------|----------|----------|--------------|---------------------|------------|-------|--------|
|      |          |          |          |              |                     |            |       | Open / In Review / Fixed / Won't Fix / Backlog |

## Status definitions

- **Open** — reported, not yet triaged
- **In Review** — triaged, owner assigned, under investigation
- **Fixed** — resolved and verified
- **Won't Fix** — acknowledged, intentionally not addressed for the
  pilot period (note reason in Description)
- **Backlog** — valid, deferred beyond the pilot period

## Triage guidance

- Any **Blocker** found during the pilot should be reviewed before the
  next pilot session proceeds.
- **Major** issues should be triaged within the pilot week.
- **Minor** issues and **Suggestions** can be batched and reviewed at
  the end of the pilot round (see `docs/pilot_execution_plan.md`).
