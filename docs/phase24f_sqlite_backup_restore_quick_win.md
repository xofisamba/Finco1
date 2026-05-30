# Phase 24F: SQLite Backup/Restore Quick Win

## Base SHA
`187e41003813d2dd79524bbc5e3501c3f2ac44c4` (after PR #324 merge)

## Why Phase 24F
Phase 24C.1 decision doc explicitly recommended Phase 24F before broad pilot use because data-loss risk is more urgent than another reporting surface. The SQLite DB contains all runs, scenarios, projects, and workspace states — no backup/restore mechanism existed.

## PR #299 Status
`draft=True`, `state=open`, `merged=False` — superseded.

## DB Path Discovery

| Item | Value |
|------|-------|
| DB file | `data/finco_runs.db` (default, configurable via `FINCO_DB_PATH`) |
| Module | `app/persistence.db` |
| Mode | SQLite with WAL journal mode |
| Sidecars | `-wal` and `-shm` files when WAL mode active |
| Schema | Tables: `runs`, `projects`, `scenarios`, `scenario_exports`, `workspace_states` |
| Connection | `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=30000`, `PRAGMA foreign_keys=ON` |

## New Module

`app/persistence/backup_restore.py`

| Function | Description |
|---------|-------------|
| `get_sqlite_db_path()` | Returns current DB path |
| `get_backup_dir()` | Returns backup directory (creates if needed) |
| `create_sqlite_backup()` | Creates timestamped backup copy with WAL checkpoint |
| `list_sqlite_backups()` | Lists backups with mtime, size, path |
| `validate_sqlite_backup(path)` | Validates SQLite header |
| `restore_sqlite_backup(filename)` | Restores from backup (with pre-restore safety backup) |

## Backup Directory
`data/backups/sqlite/` (configurable via `FINCO_BACKUP_DIR`)

## Backup Naming Convention
`finco_runs_<YYYYMMDD>_<HHMMSS>_<ffffff>.db`

Example: `finco_runs_20250530_113620_123456.db`

## Restore Safety Rules

1. **Path traversal protection**: `restore_sqlite_backup()` only accepts a bare filename — no path separators (`/`, `\`) or `..` allowed
2. **Directory confinement**: resolved path must be inside configured backup directory
3. **Pre-restore safety backup**: always creates a `pre_restore_safety_<timestamp>.db` before overwriting current DB
4. **SQLite header validation**: file must have valid SQLite "SQLite format 3" header before restore
5. **WAL/SHM sidecar handling**: WAL checkpoint run before backup, sidecar files copied alongside DB

## What Is Included

| Item | Included |
|------|----------|
| Main DB file (`finco_runs.db`) | ✅ |
| WAL sidecar (`-wal`) | ✅ copied after checkpoint |
| SHM sidecar (`-shm`) | ✅ copied |
| Other data files | ❌ Not in scope |
| Export artifacts | ❌ Separate from DB |

## Known Limitations

- **No UI integration yet**: module is backend-only. UI/admin panel for backup/restore is a subsequent phase.
- **No automatic cleanup**: old backups accumulate. A retention policy is not yet implemented.
- **No backup compression**: backups are full copies. Compression is a future improvement.
- **No remote storage**: backups are local only. Offsite/cloud backup is out of scope.
- **Restore requires app restart**: current DB connections may hold locks. Restart recommended after restore.

## Future UI/Admin Integration Notes

- Add a small "Persistence / Admin" panel in the workspace settings area
- Expose backup list with one-click restore buttons
- Add "Download backup" for manual export
- Add retention policy (e.g., keep last10 backups)
- Show backup size and age in UI

## Guardrails

- ✅ No financial formula changes
- ✅ No Revenue/OPEX/CAPEX/Tax changes
- ✅ No factory flag changes
- ✅ No fixture value changes
- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ PR #299 remains draft / not merged / superseded
- ✅ Backend remains source of truth
- ✅ No JS financial calculations

## Tests

8 tests in `tests/test_phase24f_sqlite_backup_restore.py`:
1. `test_backup_creates_timestamped_copy` ✅
2. `test_backup_preserves_sqlite_contents` ✅
3. `test_list_backups_returns_metadata` ✅
4. `test_restore_creates_pre_restore_safety_backup` ✅
5. `test_restore_rejects_path_traversal` ✅
6. `test_restore_rejects_non_sqlite_file` ✅
7. `test_wal_shm_sidecars_handled_if_present` ✅
8. `test_guardrails_no_model_changes` ✅

Full suite: **98 passed** (all Phase 24F + regression tests)

## Recommended Next Phase

**Phase 24E — Audit / Reconciliation Tab**
- Revenue parity
- OPEX parity
- CAPEX source mapping
- Debt / DSCR parity
- SHL / distribution parity
- unresolved issues
- validation checks
- no formula/runtime changes
