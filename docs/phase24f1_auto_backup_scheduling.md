# Phase 24F.1 — Auto-Backup Scheduling

## Base SHA
`6881c51dd21bfceaad1a94fe63363949e314a1a9` (after PR #331 merge)

## Existing Phase 24F Foundation

Phase 24F added `app/persistence/backup_restore.py` with:
- `create_sqlite_backup()` — timestamped manual backup
- `list_sqlite_backups()` — list backups by mtime
- `restore_sqlite_backup()` — restore with pre-restore safety backup
- `validate_sqlite_backup()` — SQLite header validation
- `get_sqlite_db_path()` / `get_backup_dir()` — path resolution
- `pre_restore_safety_*.db` never listed as regular backups

Phase 26A documented SQLite backup posture (backup dir gitignored, not committed).

---

## New: Auto-Backup Functions

### `get_auto_backup_config() → AutoBackupConfig`

Returns named tuple with:
- `enabled: bool`
- `interval_hours: int`
- `max_files: int`

### `should_create_auto_backup(now=None) → bool`

Returns `True` if an auto-backup should be created. A backup is due when:
- Auto-backup is enabled
- DB file exists
- No prior auto-backup exists **OR** latest auto-backup is older than configured interval

### `create_auto_backup_if_due(now=None) → BackupMetadata | None`

Creates an auto-backup if due, then prunes old auto backups. Returns `BackupMetadata` if a backup was created, or `None` if not due.

Naming: `auto_finco_runs_{ts}.db` — auto backups are distinguished from manual backups (`finco_runs_*.db`) so pruning only touches auto backups.

### `prune_auto_backups(max_backups=None) → int`

Removes oldest auto backups beyond `FINCO_AUTO_BACKUP_MAX_FILES`. Returns number deleted.

**Never removes:**
- Manual backups (`finco_runs_*.db`)
- Pre-restore safety backups (`pre_restore_safety_*.db`)

---

## Auto-Backup Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FINCO_AUTO_BACKUP_ENABLED` | `true` | Enable auto-backup scheduling |
| `FINCO_AUTO_BACKUP_INTERVAL_HOURS` | `24` | Hours between auto backups |
| `FINCO_AUTO_BACKUP_MAX_FILES` | `10` | Max auto backups to retain |

---

## Default Behavior

| Mode | Default | Notes |
|------|---------|-------|
| development | Enabled | Lightweight, UTC interval check |
| internal | Enabled | Same as development |
| pilot | Enabled (recommended) | No hard fail on backup error |

---

## Startup / Trigger Strategy

**Helper-only design**: Does not auto-wire to app startup. Call `create_auto_backup_if_due()` from app startup if desired.

```python
# Example: call from app startup (main_web.py)
from app.persistence.backup_restore import create_auto_backup_if_due
create_auto_backup_if_due()  # best-effort; raises on DB not found
```

This avoids background threads, cron, or OS scheduler dependencies.

---

## Retention Policy

- Max `FINCO_AUTO_BACKUP_MAX_FILES` auto backups retained
- Oldest auto backups deleted first
- Manual backups never touched
- Pre-restore safety backups never touched

---

## Safety Limitations

| Limitation | Status |
|------------|--------|
| No background thread | ✅ intentional — keeps shutdown clean |
| No cron/system scheduler | ✅ intentional — no external deps |
| No cloud/offsite backup | ✅ out of scope |
| Backup failures do not crash startup | ✅ development/internal mode |
| Pilot mode backup failures | ⚠️ best-effort; no hard fail in this phase |
| No multi-user backup policy | ✅ out of scope |

---

## What Remains Out of Scope

| Item | Reason |
|------|--------|
| Cloud/offsite backup | Phase 26D or later |
| Cron/system scheduler integration | No OS-level dependencies |
| Enterprise DR | Beyond pilot-readiness |
| Admin UI for backups | Phase 24F.2 or later |
| Multi-user backup policy | Single-user mode |

---

## Guardrails

- ✅ No runtime formula changes
- ✅ No financial formula changes
- ✅ No JS financial calculations
- ✅ No factory flag changes
- ✅ No fixture value changes
- ✅ No Revenue/OPEX/CAPEX/Tax formula changes
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

| File | Change |
|------|--------|
| `app/persistence/backup_restore.py` | Added auto-backup functions |
| `.env.example` | Added `FINCO_AUTO_BACKUP_*` variables |
| `docs/phase24f1_auto_backup_scheduling.md` | **NEW** |
| `tests/test_phase24f1_auto_backup_scheduling.py` | **NEW** |

---

## Recommended Next Phases

| Order | Phase | Description |
|-------|-------|-------------|
| 1 | Phase 25B — Onboarding / Help / Demo Mode | User-facing help, demo workflow |
| 2 | Phase 26D — Deployment / Observability | Docker, TLS, monitoring |
