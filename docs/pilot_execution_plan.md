# Pilot Execution Plan

A practical plan for running the External Friendly Pilot, from
preparation through follow-up. Use alongside `docs/pilot_candidate_profile.md`,
`docs/pilot_user_script.md`, `docs/pilot_feedback_form.md`,
`docs/pilot_issue_log_template.md`, and `docs/pilot_success_criteria.md`.

## 1. Preparation

- Confirm the app is on the latest main with all pilot-readiness work
  merged (see `docs/pilot_readiness_checklist.md`).
- Select pilot users per `docs/pilot_candidate_profile.md`, matching
  the recommended persona mix for the pilot size chosen below.
- Create a login/session for each pilot user.
- Share `docs/external_pilot_guide.md` and `docs/pilot_user_script.md`
  with each user ahead of their session.
- Set up a shared copy of `docs/pilot_feedback_form.md` and
  `docs/pilot_issue_log_template.md` for the round (e.g. one form per
  user, one shared issue log).

## 2. Onboarding session

- Short (10-15 minute) live or recorded walkthrough covering: what the
  tool is, what it isn't (see Known Limitations), and where to find
  the Pilot Guide and Validation Status if they get stuck.
- Make clear that this is a friendly pilot: feedback and bug reports
  are expected and welcome, not a sign the user is "doing it wrong."

## 3. User testing

- Each pilot user works through `docs/pilot_user_script.md`
  independently, ideally without the facilitator intervening unless
  asked.
- Facilitator notes (but does not correct) anywhere the user pauses,
  asks a question, or appears stuck — this is workflow-completion
  signal for `docs/pilot_success_criteria.md`.
- Encourage users to also explore beyond the script if time allows
  (their own project data, edge-case inputs).

## 4. Feedback collection

- Immediately after testing, the user completes
  `docs/pilot_feedback_form.md`.
- Any bugs found during the session are logged in
  `docs/pilot_issue_log_template.md` as they occur, not just at the
  end, so reproduction steps stay fresh.

## 5. Issue triage

- After each session (or daily, for overlapping sessions), triage new
  issue log entries: assign severity, owner, and status per the
  definitions in `docs/pilot_issue_log_template.md`.
- Any Blocker is reviewed before the next scheduled pilot session.

## 6. Follow-up review

- At the end of the pilot round, compile all feedback forms and the
  issue log.
- Score the round against `docs/pilot_success_criteria.md` and assign
  an overall verdict (Success / Success with follow-up / Not ready).
- Decide next step: proceed to a larger pilot round, address Major
  issues first, or hold a focused follow-up session with the same
  users once fixes land.

## Recommended pilot sizes

### 1-user pilot

- Best for: a first smoke test of the whole onboarding flow before
  inviting more people.
- Recommended persona: Project Finance Analyst (most likely to
  surface real defects early).
- Duration: a single session, same-day feedback form and triage.

### 3-user pilot

- Best for: the first real external pilot round.
- Recommended persona mix: one Project Finance Analyst, one Finance
  Manager or Investor/IC Reviewer, one Renewable Developer.
- Duration: sessions can run across the same week; triage Blockers
  between sessions, full follow-up review at the end of the week.

### 5-user pilot

- Best for: validating that the pilot is ready to widen further.
- Recommended persona mix: all five personas from
  `docs/pilot_candidate_profile.md`, one each.
- Duration: spread across one to two weeks; run a mid-round issue
  triage checkpoint in addition to the final follow-up review, so
  Blockers found by early users don't repeat for later users.
