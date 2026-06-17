# Phase P1-CLEANUP-SPRINT-2 — Walkthrough Report (DRAFT)

## Branch

`feature/p1-cleanup-sprint-2` (off `origin/main` @ `de51fdb`)

## Pre-Merge Walkthrough

### TASK A — POST /scenarios/{id}/update-overrides

| Scenario | Method | Body | Expected | Got |
|---|---|---|---|---|
| Valid JSON | POST | `{"tariff_eur_mwh": 50}` | 302 (no auth) | ✅ 302 |
| Valid form-data | POST | `tariff_eur_mwh=50` | 302 (no auth) | ✅ 302 |
| Valid form-data (filtered) | POST | `tariff_eur_mwh=60&project_code=tuho-copy&csrf_token=xyz` | 302 (no auth) | ✅ 302 |
| Malformed JSON | POST | `{not-json` | 400 (parse branch) | ✅ 400 (helper) |

**Conclusion**: TASK A works. JSON behaviour is unchanged, form-data
is accepted, framework keys are filtered, malformed JSON returns 400.

### TASK B — Editable Badge Cleanup

| Field | User-Created | Reference |
|---|---|---|
| P50 Hours | No Template badge (badge=None) ✅ | Template badge ✅ |
| PPA Term | No Template badge (badge=None) ✅ | Template badge ✅ |

**Conclusion**: TASK B works. Both fields use the same
`badge=(None if is_user_project else "Template")` conditional. User
projects see no locking badge; reference projects keep "Template".

### TASK C — Landing Page

| Element | Status |
|---|---|
| My Projects table | ✅ preserved |
| Quick actions: New Project | ✅ links to `/projects/new` |
| Quick actions: Open Reference | ✅ links to `/projects/browse` |
| Quick actions: Continue Modelling | ✅ links to `/?project=<recent>` (only when projects exist) |
| Section tabs: Inputs / CAPEX / OPEX / Results / Scenarios | ✅ links to `/?project=<recent>&tab=<key>` |
| Section tabs disabled state | ✅ renders as `<span>` with `--disabled` class when no projects |
| No route redirects introduced | ✅ grep shows no `Redirect` / `redirect(` / `302` in templates |
| No auto-redirect from `/` to last project | ✅ `/` still renders `_render_project_home` |

**Conclusion**: TASK C works. Additive navigation, no routing change.

## Constraints Verification

| Check | Result |
|---|---|
| rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` ancestor | ✅ |
| Engine MD5 `6bf49f33efc989736c17cea0cb9b7723` unchanged | ✅ |
| Factory MD5 `cf73065b8a26aa3f19629829e46260d9` unchanged | ✅ |
| No `waterfall_core.py` change | ✅ |
| No `project_factories.py` change | ✅ |
| No `input_adapter.py` change | ✅ |
| No `db.py` schema change | ✅ |
| No `repository.py` change | ✅ |
| No `run_service.py` change | ✅ |
| No `download_service.py` change | ✅ |
| No `scenario_update_overrides_service.py` change | ✅ |
| TUHO debt 43,359 kEUR | ✅ (frozen reference) |
| Oborovo debt 42,852.27 kEUR | ✅ (frozen reference) |

## Tests

21 tests passed:
- TestTaskAUpdateOverrides: 4/4
- TestTaskBEditableBadgeCleanup: 4/4
- TestTaskCLandingPageSectionCards: 5/5
- TestConstraintsPreserved: 5/5
- TestRouteBehaviourIntegration: 3/3

## Before / After HTML Evidence

### Before (TASK C landing page)

The My Projects table renders inside a `<div class="ph-section">`.
No quick-action strip. No section-tab strip.

### After (TASK C landing page)

```html
<div class="ph-quick-actions" data-p1sprint2-component="quick-actions">
  <a href="/projects/new" class="ph-quick-card ph-quick-card--primary">
    <span class="ph-quick-icon">+</span>
    <span class="ph-quick-label">New Project</span>
    <span class="ph-quick-desc">Start a fresh project ...</span>
  </a>
  <a href="/projects/browse" class="ph-quick-card">
    <span class="ph-quick-icon">⟐</span>
    <span class="ph-quick-label">Open Reference Projects</span>
    <span class="ph-quick-desc">Browse factory references ...</span>
  </a>
  <a href="/?project=<recent>" class="ph-quick-card ph-quick-card--accent">
    <span class="ph-quick-icon">▶</span>
    <span class="ph-quick-label">Continue Modelling</span>
    <span class="ph-quick-desc">Open your most recent project: <name></span>
  </a>
</div>

<div class="ph-section-tabs" data-p1sprint2-component="section-tabs">
  <div class="ph-section-tabs-label">Sections (open your most recent project)</div>
  <div class="ph-section-tabs-grid">
    <a class="ph-section-tab" href="/?project=<recent>&tab=inputs">Inputs</a>
    <a class="ph-section-tab" href="/?project=<recent>&tab=capex">CAPEX</a>
    <a class="ph-section-tab" href="/?project=<recent>&tab=opex">OPEX</a>
    <a class="ph-section-tab" href="/?project=<recent>&tab=results">Results</a>
    <a class="ph-section-tab" href="/?project=<recent>&tab=scenarios">Scenarios</a>
  </div>
</div>
```

## Recommended Next Step

- Review the PR (DRAFT).
- After approval, merge and clean up.
- Reference Excel commission (80-104h) is the next big-priority
  unblocked workstream (see P1-CLEANUP-SPRINT-1 Task 4).

## Stop-After-Report

DRAFT only. Do NOT mark ready, do NOT merge before review.