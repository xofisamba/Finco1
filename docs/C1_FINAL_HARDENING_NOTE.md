# C1 Final Hardening — Implementation Note

This PR closes out the C1 Interaction Layer effort (C1 PR1-PR9, plus
the CAPEX/OPEX/Inputs/Revenue/Senior Debt/Tax/Export-Audit/
Scenarios-Compare sheet migrations). It implements exactly three
hardening tasks, with no new functionality, no C2 work, and no
modelling/financial changes.

## Task 1 — Bounded Undo Stack

**Problem.** `FcUndoManager` (`static/interaction/undo-manager.js`)
maintained `_undoStack` as a plain JS array with no upper bound. A
long editing session (many cell edits / pastes) could grow this
array without limit, holding onto transaction objects (and the
`{addr, before, after}` values inside them) indefinitely.

**Fix.** Introduced `MAX_UNDO = 300`, documented inline in the
module's header comment. `recordTransaction()` now evicts the
oldest transaction(s) via `Array.prototype.splice(0, n)` (FIFO)
whenever a push would leave the stack longer than `MAX_UNDO`. 300 was
chosen as a generous but fixed session history — comfortably more
than a user is likely to need to step back through in one sitting,
while bounding worst-case memory to a fixed, small footprint (each
transaction holds only a handful of primitive values, never DOM
references). `MAX_UNDO` is exposed read-only on
`window.FcUndoManager.MAX_UNDO` for tests.

No other behaviour changed:
- Newest transactions are always preserved (the array's tail is
  never touched by eviction).
- Redo is untouched — `_redoStack` is still cleared on every new
  transaction, exactly as before; it can never exceed the (now
  bounded) undo stack's own size since it only ever holds
  transactions popped off the undo stack by `undo()`.
- `undo()`/`redo()` logic is completely unmodified.

**Tests.** `tests/test_c1_final_hardening_undo_bound_browser.py`
(Playwright, against `tests/fixtures/c1_undo_redo_fixture.html`):
pushes `MAX_UNDO + N` synthetic transactions via the existing public
`recordTransaction()` entry point and asserts: the stack settles at
exactly `MAX_UNDO`; the oldest evicted transactions are genuinely
unreachable (undoing all the way down stops at the oldest *surviving*
transaction's `before` value, never the very first ever pushed); the
newest transaction still undoes to its correct value after overflow;
redo round-trips correctly after overflow; and pushing fewer than
`MAX_UNDO` transactions causes no eviction at all.

## Task 2 — Explicit Active Cell Restore Ordering

**Problem.** After an htmx swap, both `FcSwapLifecycle` and
`FcActiveCellManager` independently registered a listener for the
same `fc:gridsScanned` event:
- `FcSwapLifecycle._onGridsScanned` held its own pre-swap snapshot
  (captured at `htmx:beforeSwap`) and used it to authoritatively
  decide whether to call `setActiveCell()` or `clearActiveCell()`.
- `FcActiveCellManager._onGridsScanned` independently re-derived its
  *own* prior `_activeGridId`/`_activeCell` against the freshly
  rebuilt `FcGridRegistry` state and reapplied (or dropped) the
  visual class accordingly.

Because both were plain `document.addEventListener('fc:gridsScanned',
...)` registrations, the *effective* order they ran in was determined
by `<script>` load order in `base.html` (i.e. which module's `init()`
ran first), not by any explicit contract between the two modules.
This is exactly the kind of order-dependence the task asked to
eliminate.

**Fix.** `FcActiveCellManager`'s reconciliation logic was extracted
into a standalone, idempotent, side-effect-pure function,
`reconcileAfterScan(gridIds)`, exposed publicly on
`window.FcActiveCellManager.reconcileAfterScan`. It has no
decision-making power of its own — it only ever re-reads
`FcGridRegistry.getActiveCell(gridId)` (the single source of truth,
already correctly re-attached by `FcGridRegistry.scan()`) and
re-applies (or drops) the visual class to match. Calling it any
number of times, in any order, always converges to the same state.

`FcSwapLifecycle` is now the sole authority for *deciding* what the
active cell should be after a swap (it alone owns and acts on the
pre-swap snapshot). Immediately after making that decision (calling
`setActiveCell()`/`clearActiveCell()` and restoring scroll), it
explicitly calls `FcActiveCellManager.reconcileAfterScan(grids)`
itself — a direct function call, not a second independent event
listener. This fixes the relative ordering of "authoritative decision"
and "idempotent reconciliation" in code, removing any dependency on
which module's `<script>` tag (or `init()` call) happened to run
first.

`FcActiveCellManager` still also listens to `fc:gridsScanned` /
`fc:engineReady` directly (useful for the initial page load, where no
swap/`FcSwapLifecycle` restore happens at all, and harmless — by
design — if it also fires after a swap, since it is now a pure
idempotent re-derivation with no power to clobber `FcSwapLifecycle`'s
decision).

No dependence on script inclusion order, no duplicate restores (the
function is idempotent), no flicker (the visual class is recomputed
from current state, not toggled off-then-on), no focus loss (this
module never calls `.focus()` at all, so it cannot move focus away
from wherever the browser currently has it).

**Tests.**
`tests/test_c1_final_hardening_restore_order_browser.py` (Playwright,
reusing `tests/fixtures/c1_focus_scroll_fixture.html`): simulates both
possible relative orderings of `FcSwapLifecycle`'s restore and
`FcActiveCellManager.reconcileAfterScan()` (the practical equivalent
of varying script-load/listener-registration order within a single
page) and asserts active cell, scroll position, and focus are
restored identically in both orderings, with no duplicate
`fc-active-cell` CSS class application (no flicker) and no spurious
focus changes across repeated reconciliation calls.

## Task 3 — Global C1 Markup Conformance Test

**Problem.** Each of the 10 migrated production surfaces (CAPEX,
OPEX, Inputs, Revenue, Senior Debt, Tax, Export, Audit, Scenarios,
Compare) had its own `tests/test_*_c1_markup_contract.py` file
asserting that surface's `data-fc-*` contract in isolation. There was
no single test asserting properties that only make sense in
aggregate — most importantly, that no two surfaces accidentally
reuse the same `data-fc-grid` id or emit colliding `data-fc-addr`
strings.

**Fix.** Added `tests/test_c1_markup_conformance.py`. It reuses each
surface's existing Jinja2 standalone-rendering recipe and
`SAMPLE_PROJECT_CTX`-style fixture verbatim (importing them directly
from the corresponding `test_*_c1_markup_contract.py` module rather
than re-inventing rendering infrastructure), rendering all 12 grids
across the 10 surfaces (Scenarios contributes 3: `scenarios`,
`scenario-inputs`, `scenario-summary`; Compare contributes 1:
`scenario-compare`) and asserting, for every grid:

- globally unique `data-fc-grid` id (no two surfaces collide)
- unique `data-fc-addr` within each grid
- every editable cell has `data-fc-raw`
- every editable cell that belongs to a surface whose own per-surface
  contract requires a real `<input>`/`<select>`/`<textarea>`
  descendant (CAPEX, Inputs, Revenue, Senior Debt) has one — the two
  Scenarios surfaces that use a different, pre-existing
  dblclick-popover editing convention are correctly excluded from
  this specific check, matching their own contract tests exactly (no
  stricter rule was invented for this aggregate test than already
  exists per-surface)
- read-only cells are never required to have a writable control
- every cell has `data-fc-kind` and a valid `data-fc-editable`
- no empty `data-fc-addr` values
- no malformed addresses (must match `gridid!key`, no whitespace)
- deterministic address ordering across two renders of the same
  surface
- no address string is shared across two different surfaces (a
  stronger guarantee than per-grid uniqueness alone)

This becomes the permanent regression guardrail for the whole C1
effort: a future change to any surface's template or address scheme
that accidentally collides with another surface's grid id or address
namespace will fail here, even if each surface's own narrower
contract test still passes in isolation.

## Why C1 is now considered complete and closed

With this hardening pass:
- The undo stack (the one piece of unbounded memory growth left in
  the entire interaction layer) is now bounded.
- Active-cell restoration after an htmx swap has exactly one,
  explicit, code-enforced ordering between the two modules involved,
  with no remaining dependency on script load order.
- Every production surface migrated under C1 is covered by both its
  own per-surface contract test and a single cross-cutting
  conformance sweep that guards the whole-effort invariants (global
  id/address uniqueness) no individual surface test could catch on
  its own.

No open hardening concerns remain against the scope C1 PR1-PR9 and
the sheet migrations were chartered to deliver: a foundational,
read-mostly spreadsheet interaction layer (grid registry, active
cell, focus/scroll preservation, keyboard navigation, selection,
clipboard, undo/redo, fill, cell I/O) plus the markup contract that
lets real production sheets opt into it. This PR is the last planned
work item against that scope.

## Explicitly out of scope here (belongs to C2)

The following remain entirely out of scope for this PR and for C1 as
a whole — they are C2 concerns:

- Incremental recalculation / dependency graph / formula engine.
- Dirty-state reconciliation between draft and saved/run state.
- Any scheduler or background recompute pipeline.
- Save/Run integration changes.
- Any new editability (no `data-fc-editable` value was changed
  anywhere by this PR; no cell that was read-only became editable or
  vice versa).
- Clipboard UX improvements, dashboard changes, or any other new
  interaction-layer functionality beyond the three hardening tasks
  above.

This PR makes zero changes to `domain/*`, `app/waterfall_core.py`,
`app/input_adapter.py`, `app/project_factories.py`, persistence code,
export logic, or any financial calculation/formula code — confirmed
via `git diff --stat main -- domain app/waterfall_core.py
app/input_adapter.py app/project_factories.py` returning empty. No
production template (`app/templates/**`) was modified by this PR;
both Task 1 and Task 2 are JS-only changes, and Task 3 is test-only.
