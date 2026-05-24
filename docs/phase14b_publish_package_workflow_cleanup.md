# Phase 14B Publish / Package Workflow Cleanup

## Purpose

Phase 14B standardizes the ZIP publish fallback used when local branch creation,
staging, or push workflows are blocked by local `.git` ref-lock or permission
issues.

This branch does not change production application behavior. It adds:

- a documented handoff workflow
- a simple manifest convention
- a developer-only ZIP validation utility
- tests for the validator

## When To Use Normal Git

Use the normal branch / commit / push / PR workflow when:

- local `.git` writes are healthy
- the branch can be created normally
- the scoped file list can be staged directly
- local push and PR creation are available

## When To Use ZIP Publish Fallback

Use the ZIP fallback when:

- branch creation fails because `.git` cannot create refs or lock files
- local staging is unreliable
- CLI-based publish steps are blocked by local environment issues
- the worktree is dirty and a scoped handoff is safer than direct local staging

## Recommended ZIP Publish Workflow

### Codex side

1. Work only in the current worktree.
2. Keep the file list intentionally scoped.
3. Create a ZIP that preserves relative repository paths.
4. Include a manifest or clearly stated expected file list.
5. Run the validator against the ZIP before handoff.
6. Provide:
   - changed file list
   - tests run and results
   - compile results
   - guardrail confirmations
   - known environment notes

### OpenClaw side

1. Start from clean `main`.
2. Create the target branch from `main`.
3. Extract the ZIP into repository root.
4. Verify the ZIP file list matches the intended scoped list exactly.
5. Re-run the listed validation commands.
6. Review that no unrelated files changed.
7. Commit, push, and open the PR.

## Manifest Format

Use a simple Markdown manifest when needed.

Required structure:

```md
# Package Manifest

- Package Name: example_publish_bundle.zip
- Intended Branch: example-branch
- Base Branch: main

## Expected Files
- path/to/file_a.py
- docs/example.md

## Forbidden Categories
- runtime/model formula files
- workbook calculation files

## Validation Commands
- pytest tests/test_example.py
- python -m py_compile scripts/example.py main_web.py

## Guardrails
- no production application code changed
- no runtime/model formula changes

## Known Environment Notes
- local .git ref lock issue required ZIP publish fallback
```

The validator in this branch reads the `## Expected Files` list.

## Validator Usage

Validate with a manifest:

```text
python scripts/validate_publish_package.py package.zip --manifest package_manifest.md
```

Validate with explicit file paths:

```text
python scripts/validate_publish_package.py package.zip ^
  --expected-file docs/example.md ^
  --expected-file tests/test_example.py
```

The validator will:

- fail if the ZIP is empty
- fail if required files are missing
- fail if extra files are present
- fail on directory entries
- fail on path traversal entries
- fail on absolute paths or drive-qualified paths
- print a clean file summary when validation passes

## Required PR Handoff Summary

Every ZIP-based handoff should include:

- package name
- intended branch
- base branch
- expected file list
- tests run
- compile results
- guardrail confirmations
- known environment notes

## Required Guardrails

- no runtime/model formula changes
- no workbook calculation changes
- no persistence authority promotion
- no governance behavior changes unless explicitly intended
- no JavaScript financial calculations
- `audit_economic_mode` / `runtime_economic_mode` contracts unchanged unless explicitly in scope
- `G20` remains `BLOCKED`
- `R99/R102` remain `NOT APPROVED`

## Known Environment Notes

Recurring local issues observed in prior phases:

- `.git` ref-lock permission failures blocked branch creation
- `.git/index.lock` write failures blocked direct staging
- workspace cache permission warnings appeared during pytest
- optional dependency gaps sometimes affected test collection in non-auth flows

ZIP fallback is therefore treated as an operational safety valve, not as a
normal replacement for git.
