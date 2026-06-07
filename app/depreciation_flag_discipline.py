"""Phase D2 — Depreciation Flag Discipline Hardening.

This module is AUDIT / READ-ONLY. It does NOT enable any
depreciation feature flag, does NOT change any formula, does
NOT change any schedule, and does NOT change waterfall
runtime authority. Its sole purpose is to:

- inventory the canonical / tax-bridge / book-pnl
  depreciation feature flags in one place
- provide a single authoritative helper that callers can
  use to confirm that a given flag snapshot has not
  silently promoted canonical depreciation to runtime
  authority
- provide a read-only summary suitable for export audit
  surfaces (Phase D1's "Depreciation Audit" sheet can
  consume it)

The four depreciation flags this module tracks are:

- ``use_depreciation_canonical_engine`` (canonical
  DepreciationEngine replaces legacy runtime)
- ``use_canonical_tax_depreciation_bridge`` (canonical
  tax-bridge replaces legacy tax-bridge)
- ``use_tax_bridge_engine`` (tax-bridge engine takes over
  waterfall tax handling)
- ``use_book_depreciation_for_pnl`` (book depreciation
  replaces tax depreciation on the P&L line)

All four default to ``False`` in the factory templates
(TUHO, Oborovo, Generic Solar, Generic Wind). D1 already
verifies that the D1 sheet correctly reports the flag
state. D2 adds the missing structural piece: a single
source of truth for the flag names and a guard helper
that callers can use to refuse to take a runtime
depreciation shortcut.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional


# Single source of truth for the canonical / tax-bridge /
# book-pnl depreciation feature flag names. Adding a new
# flag here automatically updates the D2 helpers and the
# D1 audit disclosure.
DEPRECIATION_FLAG_NAMES: tuple[str, ...] = (
    "use_depreciation_canonical_engine",
    "use_canonical_tax_depreciation_bridge",
    "use_tax_bridge_engine",
    "use_book_depreciation_for_pnl",
)


def get_depreciation_flag_snapshot(
    project_inputs: Any,
) -> dict[str, bool]:
    """Return the current depreciation flag snapshot for a
    given project inputs object. Missing flags are reported
    as ``False`` (the default). The snapshot is a dict keyed
    by the flag name in :data:`DEPRECIATION_FLAG_NAMES`.

    Reads from ``project_inputs.info`` (the canonical home
    for the info-level flags) and falls back to ``False``
    for missing attributes. This helper does NOT raise on
    missing attributes — it reports the safe default.
    """
    info = getattr(project_inputs, "info", None)
    out: dict[str, bool] = {}
    for name in DEPRECIATION_FLAG_NAMES:
        if info is None:
            out[name] = False
        else:
            out[name] = bool(getattr(info, name, False))
    return out


def any_canonical_depreciation_enabled(
    flag_snapshot: dict[str, bool],
    *,
    also_include: Optional[Iterable[str]] = None,
) -> bool:
    """Return ``True`` iff any of the canonical / tax-bridge
    / book-pnl depreciation flags in
    :data:`DEPRECIATION_FLAG_NAMES` is enabled.

    ``also_include`` is an optional iterable of additional
    flag names to consider; this lets the helper be
    extended for future flags without changing the call
    sites that pin D2's discipline contract.
    """
    for name in DEPRECIATION_FLAG_NAMES:
        if flag_snapshot.get(name, False):
            return True
    if also_include:
        for name in also_include:
            if flag_snapshot.get(name, False):
                return True
    return False


def assert_no_canonical_depreciation_runtime_promotion(
    project_inputs: Any,
    *,
    source: str = "runtime",
) -> dict[str, bool]:
    """Read-only guard: if any canonical / tax-bridge /
    book-pnl depreciation flag is enabled on the given
    project inputs, raise ``PermissionError`` with a
    reviewer-friendly message.

    D2 is purely audit / visibility only — the factory
    templates (TUHO, Oborovo, Generic Solar, Generic Wind)
    do NOT enable any of these flags, so this assertion
    passes for the default factory runtime. Callers that
    opt in to a controlled enablement can use the
    ``source=`` parameter to make the assertion point
    explicit in the failure message.

    The function is safe to call from any code path. It
    only reads attributes; it never writes.
    """
    flag_snapshot = get_depreciation_flag_snapshot(
        project_inputs
    )
    enabled = [
        name
        for name, value in flag_snapshot.items()
        if value
    ]
    if enabled:
        raise PermissionError(
            f"Phase D2: canonical / tax-bridge / book-pnl "
            f"depreciation runtime promotion is not allowed "
            f"in {source!r}. Detected enabled flags: "
            f"{enabled}. The active runtime path remains "
            f"the legacy depreciation path until a future "
            f"controlled-enablement PR explicitly approves "
            f"promotion."
        )
    return flag_snapshot


def get_depreciation_flag_discipline_summary(
    project_inputs: Any,
) -> dict[str, Any]:
    """Build a JSON-friendly summary of the depreciation
    flag discipline for export / audit surfaces.

    The summary is consumed by Phase D1's "Depreciation
    Audit" sheet to keep the disclosure consistent with
    the runtime flag snapshot. The structure is:

    - ``canonical_promotion_blocked: bool`` — ``True`` iff
      all four canonical / tax-bridge / book-pnl flags
      are off
    - ``enabled_canonical_flags: list[str]`` — list of
      canonical flag names currently enabled (empty in
      baseline)
    - ``runtime_authority_path: str`` — name of the active
      runtime path (``legacy_depreciation_runtime`` when
      canonical is off; would switch to
      ``canonical_depreciation_engine`` if a future
      enablement PR allowed it)
    - ``discipline_phase: str`` — the D2 phase label
    """
    flag_snapshot = get_depreciation_flag_snapshot(
        project_inputs
    )
    enabled = [
        name
        for name, value in flag_snapshot.items()
        if value
    ]
    if enabled:
        runtime_path = "canonical_depreciation_engine"
    else:
        runtime_path = "legacy_depreciation_runtime"
    return {
        "canonical_promotion_blocked": (
            len(enabled) == 0
        ),
        "enabled_canonical_flags": list(enabled),
        "runtime_authority_path": runtime_path,
        "discipline_phase": "D2",
    }


__all__ = [
    "DEPRECIATION_FLAG_NAMES",
    "get_depreciation_flag_snapshot",
    "any_canonical_depreciation_enabled",
    "assert_no_canonical_depreciation_runtime_promotion",
    "get_depreciation_flag_discipline_summary",
]
