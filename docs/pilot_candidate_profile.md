# Pilot Candidate Profile

Who should take part in the first External Friendly Pilot, what each
profile should focus on while testing, and what feedback from them is
most valuable. This is a guide for selecting and briefing pilot users —
it does not change any product behaviour.

## 1. Finance Manager

**Who they are:** Manages budgets, reporting and internal financial
planning at a developer, fund, or operating company. Comfortable with
spreadsheets and standard financial statements, but not necessarily a
project-finance modelling specialist.

**What they should test:**
- Creating a project and editing assumptions (capacity, tariff, OPEX)
  without help.
- Saving and reopening a project across sessions.
- Reading the KPI summary (IRR, DSCR, payback) and judging whether it's
  understandable without a modelling background.
- Exporting the institutional workbook and opening it in Excel.

**Most valuable feedback:**
- Whether the inputs and outputs are clear to someone who isn't a
  modelling specialist.
- Whether the language and labels feel trustworthy or "black box."
- Whether the export is usable for internal reporting as-is.

## 2. Renewable Developer

**Who they are:** Originates and develops solar/wind projects day to
day. Knows the assumptions that matter (capacity, tariff structure,
construction timeline, OPEX) better than most other personas.

**What they should test:**
- Creating a Standard Solar or Standard Wind project from scratch with
  their own real-world assumptions.
- Editing assumptions to match a project they actually know.
- Creating a Downside scenario and comparing it against Base.
- Whether results (IRR, DSCR) are directionally sensible for the
  inputs they entered.

**Most valuable feedback:**
- Whether the inputs cover the assumptions they'd actually need to
  model a real deal.
- Whether anything is missing that would block them from using this
  instead of, or alongside, their existing spreadsheet.
- Whether scenario comparison helps or hinders their usual workflow.

## 3. Project Finance Analyst

**Who they are:** Builds and audits project finance models for a
living — typically at a developer, advisor, or fund. The most
technically demanding user of the five.

**What they should test:**
- The full workflow end to end: project creation, inputs, run, KPIs,
  scenarios, comparison, export.
- Cross-checking exported workbook numbers against their own
  understanding of standard project finance mechanics.
- Reading the Known Limitations and Validation Status pages closely.
- Probing edge cases: unusual tariff structures, aggressive downside
  assumptions, multiple scenarios.

**Most valuable feedback:**
- Specific, technical gaps versus what they'd expect from a
  lender-grade or IC-grade model.
- Whether the Known Limitations page accurately reflects what they
  find when they test the model.
- Concrete bug reports with reproduction steps (this group is best
  placed to find real issues, not just UX friction).

## 4. Lender Reviewer

**Who they are:** Reviews financial models on behalf of a lender,
typically as part of due diligence. Highly sensitive to model
provenance, validation status, and what is/isn't approved for
financing decisions.

**What they should test:**
- The Validation Status and Known Limitations pages, specifically.
- Whether the app's caveats and disclaimers are clear about what the
  outputs are and are not suitable for.
- The exported workbook's documentation/governance content, if they
  choose to explore it.

**Most valuable feedback:**
- Whether the validation/caveat language meets their expectations for
  honesty and clarity about model status.
- Whether anything in the app or export could be mistaken for a
  lender-approved or audited model when it is not.
- Whether the caveats are pitched at the right level — neither
  alarmist nor understated.

## 5. Investor / IC Reviewer

**Who they are:** Reviews investment opportunities at an investment
committee or similar level. Time-constrained; cares about headline
metrics, scenario comparison, and overall credibility of the tool
rather than line-by-line mechanics.

**What they should test:**
- Whether they can get from project creation to a credible-looking
  KPI summary and scenario comparison quickly, without training.
- Whether the export is something they'd be comfortable forwarding to
  a committee.
- Their overall first impression and trust level.

**Most valuable feedback:**
- Whether the tool would change how quickly they could screen a deal.
- Whether they'd trust the headline numbers enough to use them in an
  initial screening conversation.
- Whether the experience feels "ready" for non-technical decision
  makers, or still feels like an internal tool.

## Selecting the first pilot group

For a small first pilot (1-3 users), prioritise a mix that includes at
least one **Project Finance Analyst** (most likely to surface real
bugs) and one **Finance Manager** or **Investor/IC Reviewer** (most
likely to surface clarity and trust issues). Add a **Renewable
Developer** or **Lender Reviewer** as the pilot group grows to 5.
