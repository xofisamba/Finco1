# Phase 26B — Auth / Single-user Mode Boundary

## Base SHA
`50a5915d0e528286b10215ebfbc1814e9d80c1fb` (after PR #328 merge)

## Scope
Narrow auth/config boundary hardening. No multi-user roles, no redesign of auth architecture.

---

## Existing Auth Posture

`app/auth.py` provides stateless signed-cookie auth with:
- `FINCO_SECRET_KEY` — signing key (falls back to `"dev-secret-please-change-in-production"` with WARNING)
- `FINCO_ADMIN_PASSWORD` — default `"fincoGPT2026!"` (an obvious placeholder)
- bcrypt password hashing, CSRF protection, per-IP rate limiting on login

Phase 26A documented this posture and created `.env.example` with placeholder values.

---

## New: Mode Boundary — `FINCO_APP_MODE`

### Environment Variable

```
FINCO_APP_MODE=development | internal | pilot
```

- **Default**: `development`
- **development / internal**: placeholder credentials allowed, WARNINGs printed
- **pilot / production-like**: **fails fast** on placeholder/insecure secrets

### Helper Functions

| Function | Description |
|----------|-------------|
| `get_app_mode()` | Returns `development`, `internal`, or `pilot`. Unknown values fall back to `development` with WARNING. |
| `is_placeholder_secret(value)` | Returns `True` for obvious placeholder strings: `changeme`, `dev-only`, `example`, `password`, `secret`, `fincoGPT2026!`, `fincoGPT`, etc. |
| `_is_pilot_mode()` | Returns `True` if `FINCO_APP_MODE == "pilot"` |

### Fail-Fast Conditions (Pilot Mode)

| Condition | Behavior |
|-----------|----------|
| `FINCO_SECRET_KEY` missing or placeholder | `RuntimeError` at startup |
| `FINCO_ADMIN_PASSWORD` is placeholder | `RuntimeError` at startup |
| Unknown `FINCO_APP_MODE` value | Falls back to `development` with WARNING |

### Development Mode

- Placeholder secrets **allowed** (with WARNING prints)
- Default admin password `"fincoGPT2026!"` accepted
- Dev secret fallback `"dev-secret-please-change-in-production"` used

---

## Single-User Boundary — Documented

This app is currently **single-user/internal or pilot-controlled only**:

| Out of Scope | Reason |
|-------------|--------|
| Multi-user role model | Not designed yet |
| Tenant isolation | Not implemented |
| Enterprise permission model | Not designed yet |
| SaaS-ready auth | Not implemented |
| Roles / governance workflow | Deferred to later phase |

---

## `.env.example` Changes

Updated to include:
- `FINCO_APP_MODE=development` (documented as dev default)
- `FINCO_SECRET_KEY=changeme-dev-only-not-for-pilot` (clearer placeholder)
- `FINCO_ADMIN_PASSWORD=changeme-dev-only-not-for-pilot`
- Comments explaining pilot mode requires real secrets

---

## What Was Changed

| File | Change |
|------|--------|
| `app/auth.py` | Added `FINCO_APP_MODE`, `get_app_mode()`, `is_placeholder_secret()`, pilot-mode fail-fast on placeholders |
| `.env.example` | Added `FINCO_APP_MODE`, clearer placeholder names, pilot-mode warnings |

---

## What Was NOT Changed

- No runtime formula changes
- No auth redesign
- No multi-user logic
- No roles/permissions
- No external auth providers
- No billing/tenant logic
- No session/cookie architecture changes

---

## Guardrails

- ✅ No runtime formula changes
- ✅ No financial formula changes
- ✅ No JS financial calculations
- ✅ No factory flag changes
- ✅ No fixture value changes
- ✅ No Revenue/OPEX/CAPEX/Tax formula changes
- ✅ No SHL/distribution logic changes
- ✅ No senior debt sizing logic changes
- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ `partial_pay_sweep` not promoted
- ✅ `flat_dscr_sculpted` not promoted
- ✅ `minimum_dscr_sculpted` not promoted
- ✅ PR #299 remains draft / not merged / superseded
- ✅ Backend remains source of truth
- ✅ No lender/bank/audit/SaaS claims

---

## Recommended Next Phase

| Option | Description |
|--------|-------------|
| **A: Phase 25 — Pilot Product Polish** | UI polish, error message improvements |
| **B: Phase 26C — Deployment/CI/Config Hardening** | Docker, TLS, reverse proxy, CI guardrails |
| **C: Phase 24D — Shared LineItemGrid** | UI refactor, reduce duplication |

**Recommended: Option A (Phase 25)** — Phase 24/26A/26B have established the safety and honesty layer. Pilot readiness next needs polish and usability work, not more infrastructure.
