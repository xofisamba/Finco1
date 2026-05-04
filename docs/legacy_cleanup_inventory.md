# Legacy Cleanup Inventory

## archive/
**Description:** Contains deprecated handoff documents and old design docs from the Oborovo→Finco1 transition.
**Files:**
- `CODEX_HANDOFF_FINCOGPT.md` (20 KB) — handoff notes, likely stale
- `FINCOGPT_MODEL_FILE_MANIFEST.md` (2.6 KB) — old file manifest
**Recommendation:** Delete — these are transition artifacts; the actual code has moved on.

---

## app/calibration.py
**Description:** Standalone calibration script that pre-dates the current project factory/input system.
**Recommendation:** Refactor — extract reusable calibration constants into `app/demo_presets.py` or a shared constants module, then delete the standalone file.

---

## app/ui/calibration_legacy/
**Description:** Legacy UI components for calibration (replaced by current input forms).
**Files:** Old Streamlit pages/widget definitions.
**Recommendation:** Delete — superseded by `app/ui/components.py` and `app/ui/pages.py`.

---

## tests/conftest.py — `_oborovo_compat_shim`
**Description:** Shim that imports `app.project_factories` to ensure Oborovo compatibility layer is installed before tests run.
**Recommendation:** Refactor — once all tests are confirmed to use the new factory path, remove the shim and the `pytest_ignore_collect` hook.

---

## app/ui/ (old pages)
**Description:** Pre-refactor Streamlit page modules (replaced by current `pages.py`).
**Files:** `__init__.py`, `components.py`, `pages.py` under `app/ui/`.
**Note:** These appear to be the current active files — not legacy. Confirm before acting.
**Recommendation:** Keep — likely active. Verify by checking imports in `app/main.py`.

---

## docs/ (unused .md files)
**Description:** Several docs may be stale after the refactor:
- `oborovo_compat_cleanup_plan.md` — cleanup plan itself (implemented)
- `repo_cleanup_inventory.md` — older cleanup inventory, may overlap with this doc
**Recommendation:** Review — delete if content has been superseded by this inventory or implementation notes.

---

## domain/portfolio/waterfall.py — Pooled CFADS vs per-project CF
**Description:** Comment in source notes that `portfolio_sponsor_irr` is a placeholder requiring equity-level CF aggregation. The `PortfolioResult` dataclass exposes per-project results but the sponsor-level waterfall is not yet wired.
**Recommendation:** Keep — this is the known gap documented in Phase 3 roadmap (Portfolio v1 Hardening). Do not delete; track as a planned feature.