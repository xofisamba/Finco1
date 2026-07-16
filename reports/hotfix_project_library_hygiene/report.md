# Hotfix: safe legacy-test archive tooling, flag-aware Project Library routing, and true same-manifest replay

**Branch**: `hotfix-project-library-data-hygiene`
**Base SHA**: `08ea9d50b0f23d72baf02e283c572682c7c1dc81` (PR #885)
**Status**: DRAFT, not for merge.

## Purpose

PR #886 introduces:

1. **Safe legacy-test archive tooling** — a fail-closed
   maintenance command that:
   * generates an operator-local manifest pinned to the
     **two authoritative logical DB state fingerprints**
     (`pre_apply_project_state_sha256` and
     `replay_state_sha256`), the schema fingerprint, the
     canonical table counts, and the per-row identity
     fingerprint;
   * validates the manifest against the current DB inside
     one ``BEGIN IMMEDIATE`` write lock;
   * classifies the validation state as exactly one of
     `NO_CANDIDATES`, `FIRST_APPLY`, `ALREADY_APPLIED`, or
     `PARTIAL_REPLAY` (the last always fails closed);
   * creates a timestamped backup **only** on a
     `FIRST_APPLY` transition, in a directory outside the
     repository and outside the live DB directory, and
     verifies the backup against the locked pre-update
     state;
   * returns a structured `ApplyResult` with `status`,
     `rows_archived_now`, the exact `backup_path`, and the
     post-update logical fingerprint;
   * writes no DB-specific or user-specific data to Git.
2. **Flag-aware Project Library routing** — a single
   authoritative helper
   `app.library.router.workbook_destination(project_code)`
   chooses between the legacy workspace and the Workbook
   V2 route based on the canonical truthy value of
   `FINCO_WORKBOOK_V2` (accepted: `1`, `true`, `yes`, `on`,
   case-insensitive, whitespace-stripped). The same helper
   is used for:
   * the Project Library Open link (`/library` and
     `/library/list`),
   * the working-copy clone redirect
     (`POST /library/clone/{id}`),
   * the HTMX `HX-Redirect` and the non-HTMX 303 `Location`.
   The helper probes the app for a mounted `/v2` route and
   falls back to the legacy workspace if the operator sets
   `FINCO_WORKBOOK_V2=1` but the V2 router is not mounted.
   Project Library navigation therefore never targets an
   unmounted route.
3. **Canonical paginated Project Library entry point** —
   `GET /` with no project now 302-redirects to `/library`
   (the single authoritative Project Library, 20/page,
   search, role filter, cross-user isolation).
   `GET /?project=...` continues to open the named project
   workspace unchanged.
4. **Corrected reference card copy** — the
   "Open Reference Projects" card description was changed
   from "Browse example projects (TUHO, Oborovo, Generic)"
   to "Browse reference models (TUHO and Oborovo)". The
   card link points to `/library` (was `/projects/browse`).
5. **Test-database isolation guardrails** — a module-level
   pytest guard pins `FINCO_DB_PATH` to a session-owned
   temporary directory for every test in the session, so no
   test that runs through this hotfix's conftest can write
   to the repository default
   `app/data/finco_runs.db`. The contract uses
   `Path(value).expanduser().resolve()` and rejects any
   input that resolves inside the repository, equals the
   production default, or is a symlink to the production
   default. Subprocess-based tests prove the actual
   module-import behavior end-to-end.

## What this PR does NOT do

* It does NOT complete Inputs browser acceptance.
* It does NOT activate the Inputs Slice deployment flags in
  any environment. The two flags remain OFF by default in
  source code.
* It does NOT activate `FINCO_WORKBOOK_V2`. The flag is
  accepted but the V2 router is NOT mounted in this
  checkout. The Project Library Open link therefore
  resolves to the legacy workspace by default.
* It does NOT modify the deployment database. The
  repository default DB is untouched.
* It does NOT start Default Product Surface Convergence or
  Scenarios Slice work.
* It does NOT change financial formulas, registry
  definitions, ProjectInputs schemas, runtime calculations,
  scenario behavior, CAPEX / OPEX / Revenue / Debt / Tax /
  Financial Statements calculations, the persistence schema,
  parity targets, or golden fixtures.

## Manifest v2 contract

The committed manifest schema records:

* `manifest_version` — `2`.
* `generated_at` — UTC ISO timestamp.
* `database.absolute_path` — exact resolved DB path used
  for the same-DB validation.
* `database.schema_fingerprint` — SHA-256 of the
  `(table, columns)` description.
* `database.pre_apply_project_state_sha256` —
  authoritative logical fingerprint the *first* apply
  must match. Computed inside one read transaction over
  the project rows + schema + table counts. Serialized
  with canonical JSON so `None`, `""`, `0`, and `False`
  are preserved exactly. **This is the authoritative
  pre-apply fingerprint; the raw file SHA is
  informational only.**
* `database.replay_state_sha256` — authoritative
  logical fingerprint a *same-manifest replay* must
  match. Same construction as above, but with two
  normalizations for the candidate set:
  * `archived` is forced to `1`,
  * `updated_at` is forced to `created_at`.
  The candidate identity fingerprint, the protected
  status, the non-candidate project rows, the schema
  fingerprint, and the protected table counts are all
  preserved exactly. A non-candidate mutation, a
  candidate identity mutation, a candidate becoming
  protected, a candidate disappearing, a schema
  change, or a protected table count change all
  invalidate the replay fingerprint and the replay
  fails closed.
* `database.table_counts` — `projects`, `scenarios`,
  `runs`, `workspace_states`. Any divergence fails
  closed.
* `database.raw_file_sha256` / `database.raw_size_bytes`
  — **informational only**, recorded but not
  authoritative. The logical fingerprints are
  authoritative.
* `candidate_count` and `candidates[]` — each with
  `project_id`, `user_id`, `project_code`,
  `project_name`, `project_origin`, `template_source`,
  `created_at`, `classification_rule`, and
  `row_fingerprint` (SHA-256 of the nine
  `ROW_IDENTITY_FIELDS`, canonical-serialized).

## Validation states

The locked validator
`validate_manifest_against_connection` returns exactly
one of:

* **`NO_CANDIDATES`** — manifest has zero candidates.
  Apply commits the (empty) transaction, reports
  `status=NO_CANDIDATES`, `rows_archived_now=0`, and
  creates no backup.
* **`FIRST_APPLY`** — every manifest candidate is still
  `archived=0` and the pre-apply fingerprint matches.
  Apply creates one backup, archives the active
  candidates, verifies the post-update state, and
  commits. `status=APPLIED`, `rows_archived_now=N`,
  `backup_path=<exact>`.
* **`ALREADY_APPLIED`** — every manifest candidate is
  already `archived=1`, every identity still matches,
  and the replay fingerprint matches the current state
  (with the candidate-set normalization). Apply commits
  the (empty) transaction, reports
  `status=ALREADY_APPLIED`, `rows_archived_now=0`, and
  creates no second backup.
* **`PARTIAL_REPLAY`** — a mix of `archived=0` and
  `archived=1` candidates. **Always fails closed** with
  `ERROR: partial replay`. There is no boolean parameter
  that can permit a partial replay.

## Locked apply flow

```
BEGIN IMMEDIATE
  validate (exact path, schema, table counts, every
            candidate identity, classification rule,
            protected status, appropriate logical
            fingerprint)
  if NO_CANDIDATES:
    COMMIT
    return NO_CANDIDATES
    no backup
  if ALREADY_APPLIED:
    COMMIT
    return ALREADY_APPLIED
    no backup
  if PARTIAL_REPLAY:
    ROLLBACK
    exit non-zero
    no backup
  if FIRST_APPLY:
    create and verify backup (under the lock)
    update exactly the active candidate rows
    verify every manifest candidate is archived
    COMMIT
    return APPLIED with exact backup path
on any failure:
  ROLLBACK
  zero updates
  no partial archive
```

Any database failure rolls back all project updates. A
successfully verified pre-update backup may remain as
operator evidence after a failed first-apply attempt.
No partial archive is committed. The implementation
does not delete a successfully verified backup on a
later exception; the operator may inspect or remove it
manually.

The backup is only created for a `FIRST_APPLY`. The
exact path returned by the backup function is the one
recorded in the audit. The audit does not discover the
backup by globbing the backup directory.

## Operator workflow

```bash
# 1. Generate a fresh operator-local manifest.
python scripts/archive_legacy_test_projects.py \
    --db <exact-db-path> \
    --generate-manifest <path>.archive-manifest.local.json

# 2. Dry-run review (default mode). Reports
#    status=NO_CANDIDATES / FIRST_APPLY / ALREADY_APPLIED
#    / partial replay / other invalid state. No writes.
python scripts/archive_legacy_test_projects.py \
    --db <exact-db-path> \
    --manifest <path>.archive-manifest.local.json

# 3. Apply. Requires --backup-dir OUTSIDE the repository
#    and OUTSIDE the live DB directory. Recommended
#    operator path: /var/backups/finco.
python scripts/archive_legacy_test_projects.py \
    --db <exact-db-path> \
    --manifest <path>.archive-manifest.local.json \
    --backup-dir /var/backups/finco \
    --apply
```

The backup filename is
`finco_runs.db.backup.<UTC-timestamp>.sqlite3`. The
`*.db.backup.*.sqlite3` rule in `.gitignore` is a
defense-in-depth backstop.

## CI result on the final head

| workflow | jobs | status |
|----------|------|--------|
| CI | 4 | succeeded |
| Parity Guardrails (Phase 51F) | 1 | succeeded |

**Total successful jobs: 5 (2 workflows, 5 jobs).**

No browser-gated CI job was added. The existing
browser test for the Inputs Slice
(`test_slice1_htmx_before_swap_synthetic_event_browser`)
continues to require playwright + chromium and is not
exercised by CI.

## Fixture size: 11 evidence-backed candidates, 10 protected/ambiguous

The catalogue produces **11 evidence-backed candidates**
for a clean sandbox DB of 21 rows. The breakdown by rule
family is:

| rule_id | candidates detected |
|---------|---------------------|
| `ph3-working-copy-series` | 1 |
| `p1-ux-fix1-fixtures` | 1 |
| `ph2-test-walkthrough` | 1 |
| `testpilotproj-fixtures` | 1 |
| `opex-lifecycle-fixture` | 3 |
| `inputs-test-fixture` | 1 |
| `inputs-slice1-fixture` | 1 |
| `p2fix1-route-rewiring-fixture` | 2 |
| **Total classified** | **11** |

The remaining 10 rows are retained by one of the actual
reasons in the implementation. The committed
`CANONICAL_TEMPLATE_SOURCES` constant is exactly
`('tuho', 'oborovo')`. The committed
`NON_USER_ORIGINS` constant is exactly
`('factory_template', 'saved_baseline')`. The
protected-keyword whitelist is exactly
`('proba', 'grubi', 'idemo')`. The per-row check is
`_is_protected_row` plus `_has_protected_keyword`. A
row is retained if it satisfies ANY of:

* canonical template source (`tuho` or `oborovo`),
* system origin (`factory_template` or
  `saved_baseline`),
* read-only (`is_readonly = 1`),
* protected keyword (`proba`, `grubi`, or `idemo`
  appears in `project_code` or `project_name`),
* no exact candidate-rule match against the
  evidence-backed catalogue.

The sandbox counts are pinned by
`TestAnchoredCandidateClassification` and
`TestCanonicalReferenceProtection` in
`tests/test_hotfix_project_library_hygiene.py`.

## Explicit rule match policy

Every rule carries an explicit `match_policy` field that
controls which identity fields must match:

| rule_id | match_policy | required field(s) |
|---------|--------------|-------------------|
| `ph3-working-copy-series` | `code_only` | project_code |
| `p1-ux-fix1-fixtures` | `code_only` | project_code |
| `testpilotproj-fixtures` | `code_only` | project_code |
| `opex-lifecycle-fixture` | `name_only` | project_name |
| `ph2-test-walkthrough` | `name_and_code` | project_name AND project_code |
| `inputs-test-fixture` | `name_and_code` | project_name AND project_code |
| `inputs-slice1-fixture` | `name_and_code` | project_name AND project_code |
| `p2fix1-route-rewiring-fixture` | `name_and_code` | project_name AND project_code |

Semantics:

* `code_only` — the rule's `code_prefixes` /
  `code_fullmatch` must match the project_code.
* `name_only` — the rule's `name_prefixes` /
  `name_fullmatch` must match the project_name.
* `name_and_code` — BOTH the project_name AND the
  project_code must match. A fixture-like name with a
  customer project_code, or a fixture-like code with a
  customer project_name, is NOT classified.

Unknown or missing `match_policy` is rejected with
`SystemExit` so a future catalogue cannot silently
regress to OR behavior. The cross-mismatch and
single-field behaviors are pinned by
`TestNameAndCodeConjunction` and
`TestSingleFieldRules` in
`tests/test_hotfix_project_library_hygiene.py`.
