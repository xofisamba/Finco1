"""Narrow cross-arc allowance for the source-approved PR-5 delegation."""
from __future__ import annotations


APPROVED_WATERFALL_CORE_CHANGES = (
    "+from finco_core.ebitda import calculate_ebitda_keur",
    "+",
    "-        ebitda = max(0, rev - opex)",
    "+        ebitda = calculate_ebitda_keur(rev, opex)",
)

APPROVED_DOMAIN_CHANGES = (
    "-    return tuple(max(0.0, e) * (1.0 - tax_rate) for e in ebitda_schedule)",
    "+    return tuple(e * (1.0 - tax_rate) for e in ebitda_schedule)",
    "-        # Compute debt service capacity = sizing_cfads / target_dscr",
    "+        # Keep sizing CFADS signed. Only debt-service capacity is bounded at",
    "+        # zero; negative financial flow cannot support negative debt service.",
    "-                capacity = cfads / dscr",
    "+                capacity = max(0.0, cfads / dscr)",
    "-        # Compute debt service capacity = sizing_cfads / target_dscr",
    "+        # Keep derived sizing CFADS signed and bound only the capacity.",
    "-                capacity = cfads / dscr",
    "+                capacity = max(0.0, cfads / dscr)",
)


def _financial_changed_lines(diff_text: str) -> tuple[str, ...]:
    changed_lines = [
        line
        for line in diff_text.splitlines()
        if (line.startswith("+") and not line.startswith("+++"))
        or (line.startswith("-") and not line.startswith("---"))
    ]
    # Ignore a pure final-newline normalization represented as identical
    # removed/added source lines by git.
    return tuple(
        line
        for index, line in enumerate(changed_lines)
        if not (
            index + 1 < len(changed_lines)
            and line.startswith("-")
            and changed_lines[index + 1] == "+" + line[1:]
        )
        and not (
            index > 0
            and line.startswith("+")
            and changed_lines[index - 1] == "-" + line[1:]
        )
    )


def assert_only_approved_pr5_waterfall_diff(diff_text: str) -> None:
    """Accept no diff or exactly the approved signed-EBITDA delegation."""
    changed_lines = _financial_changed_lines(diff_text)
    assert changed_lines in ((), APPROVED_WATERFALL_CORE_CHANGES), (
        "app/waterfall_core.py contains changes beyond the source-approved "
        f"PR-5 EBITDA delegation: {changed_lines!r}"
    )


def assert_only_approved_pr5_domain_diff(diff_text: str) -> None:
    """Accept no domain diff or exactly the signed-CFADS/capacity boundary."""
    changed_lines = _financial_changed_lines(diff_text)
    assert changed_lines in ((), APPROVED_DOMAIN_CHANGES), (
        "domain sizing contains changes beyond the source-approved PR-5 "
        f"signed-CFADS boundary: {changed_lines!r}"
    )
