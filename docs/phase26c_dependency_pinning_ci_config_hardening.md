# Phase 26C — Dependency Pinning / CI / Config Hardening

## Base SHA
`a78538455987cfe0d7ad820261728e4b4eeec7f2` (after PR #330 merge)

---

## Dependency State Before Phase 26C

| File | State |
|------|-------|
| `requirements.txt` | `>=` lower bounds only (e.g. `fastapi>=0.100.0`) |
| `pyproject.toml` | Unpinned dependencies |
| CI workflow | `pip install -e .` + `pip install pytest` — no version pins |
| No lock file | — |

---

## Chosen Strategy: Option B (Constraints File)

**Constraints file**: `constraints.txt` with exact `==` pins for direct runtime and test dependencies.

**Why not Option A (fully pin requirements.txt)?**
- Changing `requirements.txt` from `>=` to `==` would be a large, disruptive change to the human-maintained file
- A constraints file achieves reproducibility without altering the main dependency declaration
- Allows intentional single-package upgrades without editing two files

**Why constraints file and not `requirements.lock`?**
- `constraints.txt` is the standard pip mechanism for this use case
- Works with `pip install -e .` (editable install from `pyproject.toml`)
- No third-party tooling required

**Why not perform broad upgrades?**
- Pilot stability: upgrades should be intentional, tested, and reviewed
- No automatic upgrades in a pilot-use branch
- New dependency families would require separate review

---

## `constraints.txt` — Pinned Direct Dependencies

| Package | Pinned Version | Notes |
|---------|---------------|-------|
| `bcrypt` | `3.2.2` | Auth |
| `fastapi` | `0.136.1` | Web framework |
| `httpx` | `0.28.1` | HTTP client |
| `itsdangerous` | `2.2.0` | Signing/serialization |
| `jinja2` | `3.1.6` | Templating |
| `numpy` | `1.26.4` | Numerical |
| `openpyxl` | `3.1.5` | Excel I/O |
| `pandas` | `2.2.3` | DataFrame |
| `pydantic` | `2.13.2` | Data validation |
| `pytest` | `9.0.3` | Testing |
| `python-multipart` | `0.0.27` | Form data |
| `uvicorn` | `0.46.0` | ASGI server |

---

## CI Changes

**`.github/workflows/ci.yml`** — updated to use constraints file:

```bash
pip install --no-cache-dir -c constraints.txt -e .
pip install --no-cache-dir -c constraints.txt pytest
```

No other CI changes. No new jobs added. No lint/type-check added.

---

## Reproducible Install Steps

```bash
# Clone
git clone https://github.com/xofisamba/Finco1.git
cd Finco1

# Install with pinned dependencies
pip install -c constraints.txt -e .
pip install -c constraints.txt pytest

# Run tests
python3 -m pytest -q --tb=short
```

For **development** (non-reproducible, uses lower bounds):
```bash
pip install -e .
pip install pytest
```

---

## App Mode / Config Expectations (from Phase 26B)

| Mode | Description |
|------|-------------|
| `development` (default) | Allows placeholder secrets with WARNING; dev mode only |
| `internal` | Same as development; single-user internal use |
| `pilot` | **Fails fast** if `FINCO_SECRET_KEY` or `FINCO_ADMIN_PASSWORD` is a placeholder |

**Pilot-required env vars:**
- `FINCO_APP_MODE=pilot`
- `FINCO_SECRET_KEY=<real-long-random-string>` (not a placeholder)
- `FINCO_ADMIN_PASSWORD=<real-secure-password>` (not a placeholder)

**`.env.example`** (from Phase 26A) documents all `FINCO_*` variables with placeholder values.

---

## Known Limitations

| Item | Status |
|------|--------|
| `requirements.txt` / `pyproject.toml` lower bounds | Unchanged — human-maintained, not locked |
| Broad dependency upgrades | Not performed — intentional upgrades only |
| Lock file | No third-party lock file; `constraints.txt` used instead |
| Auth/RBAC | Single-user mode only (Phase 26B) |
| Deployment hardening | Not in scope; see Phase 26D |

---

## What Remains Out of Scope

| Item | Reason |
|------|--------|
| Full auth/RBAC | Phase 26B established boundary |
| Shared LineItemGrid | Refactor-oriented |
| Auto-backup scheduling | Phase 24F.1 |
| Onboarding/help/demo | Phase 25B |
| Deployment/observability | Phase 26D |

---

## Guardrails

- ✅ No runtime formula changes
- ✅ No financial formula changes
- ✅ No JS financial calculations
- ✅ No factory flag changes
- ✅ No fixture value changes
- ✅ No Revenue/OPEX/CAPEX/Tax formula changes
- ✅ No model code changes
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
| `constraints.txt` | **NEW** — exact pinned versions for 12 direct deps |
| `.github/workflows/ci.yml` | Updated to use `-c constraints.txt` for reproducible install |
| `docs/phase26c_dependency_pinning_ci_config_hardening.md` | **NEW** |
| `tests/test_phase26c_dependency_pinning_ci_config_hardening.py` | **NEW** |

---

## Recommended Next Phases

| Order | Phase | Description |
|-------|-------|-------------|
| 1 | Phase 24F.1 — Auto-Backup Scheduling | Automated SQLite backup scheduling |
| 2 | Phase 25B — Onboarding / Help / Demo Mode | User-facing help, demo workflow |
| 3 | Phase 26D — Deployment / Observability | Docker, TLS, monitoring |
