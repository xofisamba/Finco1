# Phase 26A — Security / Dependency Quick Wins

## Base SHA
`6e632fa5134470bfa33e3d5e3440f4ef4405c4e4` (after PR #327 merge)

## Scope
Security, configuration, and dependency hardening only. No financial model changes, no UI redesign, no formula/runtime changes.

## What Was Inspected

| File / Area | Finding |
|------------|---------|
| `requirements.txt` | Unpinned (`>=` pins only) |
| `pyproject.toml` | Unpinned (`>=` pins only) |
| `.gitignore` | Has `*.db`, `app/data/*`, WAL/SHM/journal ignored |
| `.env.example` | Missing — created |
| `app/auth.py` | WARNING print for insecure SECRET_KEY fallback; default admin password is an obvious placeholder |
| `app/persistence/backup_restore.py` | Backup dir `app/data/backups/sqlite/`, already gitignored |
| CI workflow | No secret scanning; no dependency pinning guardrail |

---

## Dependency Pinning Policy

- `requirements.txt` uses `>=` lower bounds (e.g. `fastapi>=0.100.0`)
- `pyproject.toml` uses `>=` lower bounds
- **No changes made to pinning** — broad upgrade of pinned versions is out of scope for this phase
- **Policy**: direct app/test dependencies should use pinned versions; upgrades handled intentionally in later maintenance PRs
- **Rationale**: pilot stability; no automatic broad upgrades in a pilot-use branch

---

## Environment Variable Policy

### Created: `.env.example`

New file documenting all supported environment variables with placeholder values:

| Variable | Default | Required | Notes |
|----------|---------|----------|-------|
| `FINCO_SECRET_KEY` | — | **Yes (production)** | Long random string; dev fallback emits WARNING |
| `FINCO_ADMIN_USER` | `admin` | No | Single-user dev default |
| `FINCO_ADMIN_PASSWORD` | `fincoGPT2026!` | No | Dev placeholder; **change in production** |
| `FINCO_ADMIN_PASSWORD_HASH` | — | No | Overrides plain password |
| `FINCO_SESSION_HOURS` | `24` | No | Session TTL |
| `FINCO_COOKIE_SECURE` | `true` | No | `false` only for local HTTP dev |
| `FINCO_COOKIE_SAMESITE` | `lax` | No | — |
| `FINCO_CSRF_SECRET` | same as `FINCO_SECRET_KEY` | No | — |
| `FINCO_DB_PATH` | `app/data/finco_runs.db` | No | SQLite path |
| `FINCO_BACKUP_DIR` | `app/data/backups/sqlite` | No | Backup directory |
| `DEBUG` | — | No | Development only; **never true in production** |

### Production Warning

- App currently operates in **single-user/internal mode only**
- No multi-user, no tenant isolation, no role-based access control
- Default admin credentials are dev placeholders — must be changed for any production-like deployment
- `FINCO_SECRET_KEY` dev fallback emits a `WARNING` at startup

---

## Secret/Config Handling

### `app/auth.py` findings

- `SECRET_KEY` falls back to `"dev-secret-please-change-in-production"` if env var not set — **WARNING printed**
- Default `FINCO_ADMIN_PASSWORD` is `"fincoGPT2026!"` — an obvious placeholder, not a real credential
- No real tokens or keys embedded in source
- No `.env` file committed to repo (verified via `git ls-tree`)

---

## SQLite Backup/Restore Posture (Phase 24F)

Phase 24F added `app/persistence/backup_restore.py` with:
- Default backup dir: `app/data/backups/sqlite/`
- Safety: `pre_restore_safety_*.db` backup before restore, WAL/SHM handled
- Backup dir gitignored via `app/data/*` in `.gitignore`
- **Backup files are NOT committed to repo** (verified via `git ls-tree HEAD`)
- Restore requires explicit confirmation

---

## What Remains Out of Scope

| Item | Reason |
|------|--------|
| Full auth / login system | Implemented but single-user only |
| Role-based access control (RBAC) | Multi-user not yet designed |
| Multi-user / tenant isolation | Out of scope for this phase |
| Deployment hardening (TLS, reverse proxy) | Infrastructure concern |
| SOC2-style controls | Beyond pilot-readiness scope |
| Broad dependency upgrades | Handled intentionally in maintenance PRs |
| New financial model logic | N/A — no runtime formula changes |

---

## Recommended Next Phase

**Option A: Phase 26B — Auth / Single-user Mode Boundary**

Clarify and document the auth boundary, admin credentials policy, session management, and production readiness checklist.

**Option B: Phase 25 — Pilot Product Polish**

UI polish, error message improvements, user onboarding docs.

**Option C: Phase 24D — Shared LineItemGrid**

Reduce UI duplication across sheet partials — useful but refactor-oriented.

**Recommended: Option A (Phase 26B)** — Auth boundary and production readiness checklist are more critical for pilot use than UI deduplication.

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

## Changed Files

- `.env.example` — **NEW** (documentation; placeholder values only)
- `.gitignore` — unchanged (already had `*.db`, `app/data/`, WAL/SHM/journal)
- `requirements.txt` — unchanged
- `docs/phase26a_security_dependency_quick_wins.md` — **NEW**
- `tests/test_phase26a_security_dependency_quick_wins.py` — **NEW**
