# Merge Readiness Assessment

## post-rc1-structure-roadmap
- Status: Stabilized, regression-tested
- Tests: 1036 passed
- Known limitations: CAPEX depreciation gap, BESS partial, Portfolio experimental
- Ready: YES

## feature/cli-runner
- Contains: CLI runner (app/cli/), tests, docs
- Merge risk: LOW — additive only
- Dependencies: None beyond post-rc1-structure-roadmap
- Recommended: MERGE AFTER post-rc1-structure-roadmap
- Ready: YES

## feature/api-wrapper
- Contains: FastAPI layer (app/api/), tests, docs
- Merge risk: LOW — additive only
- Future: HTMX frontend will extend this layer
- Recommended: MERGE AFTER post-rc1-structure-roadmap (can be before or after cli-runner)
- Ready: YES

## Recommended merge order
1. post-rc1-structure-roadmap → main (stabilization + new features)
2. feature/cli-runner → main (CLI runner)
3. feature/api-wrapper → main (FastAPI layer)

## Rollback guidance
- All branches are additive — rollback means reverting the merge commit
- No database migrations, no auth changes, no portfolio logic
- CLI and API are thin wrappers — rollback is safe

## Pre-merge checklist
- [ ] Full pytest passes on each branch
- [ ] Smoke tests verified manually
- [ ] Docs updated
- [ ] No forbidden files modified (rc1 untouched)
