"""Narrow cross-arc allowance for the source-approved PR-5 delegation."""
from __future__ import annotations

import hashlib
from pathlib import Path


APPROVED_WATERFALL_CORE_FINGERPRINTS = {
    "c22f19d93014af8d658096c366c30002335595c9910113ff5c8a40543aa074df",
    "7f4cc5baaa9fcf7da0b91f7e9ff1e362d986e75cb29c8070f4a06f5c5e3c00ac",
}

PR5_DOMAIN_PATHS = (
    "domain/senior_debt_sizing/canonical_wiring.py",
    "domain/senior_debt_sizing/engine.py",
)

APPROVED_PR5_DOMAIN_FINGERPRINTS = {
    "b9e93547d3e4f6cdaef342b80a655a69e388dbb1251de3bb2424261e5c0e832b",
    "bc4383eeffdead7c89d766e3c093033b0294549fc2b996fb90465a6c173b576c",
}


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


def _normalized_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def assert_approved_pr5_waterfall_state(repo_root: Path) -> None:
    digest = hashlib.sha256(
        _normalized_bytes(repo_root / "app" / "waterfall_core.py")
    ).hexdigest()
    assert digest in APPROVED_WATERFALL_CORE_FINGERPRINTS, (
        "app/waterfall_core.py is neither the historical base nor the exact "
        f"source-approved PR-5 state: {digest}"
    )


def assert_approved_pr5_domain_state(repo_root: Path) -> None:
    digest = hashlib.sha256()
    for relative in PR5_DOMAIN_PATHS:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_normalized_bytes(repo_root / relative))
        digest.update(b"\0")
    value = digest.hexdigest()
    assert value in APPROVED_PR5_DOMAIN_FINGERPRINTS, (
        "PR-5 Senior sizing domain files are neither the historical base nor the exact "
        f"source-approved PR-5 state: {value}"
    )


def assert_only_approved_pr5_waterfall_diff(diff_text: str) -> None:
    """Accept no diff or exactly the approved signed-EBITDA delegation."""
    changed_lines = _financial_changed_lines(diff_text)
    assert changed_lines in ((), APPROVED_WATERFALL_CORE_CHANGES), (
        "app/waterfall_core.py contains changes beyond the source-approved "
        f"PR-5 EBITDA delegation: {changed_lines!r}"
    )


def assert_only_approved_pr5_domain_diff(diff_text: str) -> None:
    """Accept no PR-5 sizing diff or exactly its approved boundary change."""
    relevant_lines: list[str] = []
    in_pr5_path = False
    saw_diff_header = False
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            saw_diff_header = True
            parts = line.split()
            in_pr5_path = len(parts) >= 4 and parts[3][2:] in PR5_DOMAIN_PATHS
        if in_pr5_path:
            relevant_lines.append(line)

    relevant_diff = "\n".join(relevant_lines) if saw_diff_header else diff_text
    changed_lines = _financial_changed_lines(relevant_diff)
    assert changed_lines in ((), APPROVED_DOMAIN_CHANGES), (
        "domain sizing contains changes beyond the source-approved PR-5 "
        f"signed-CFADS boundary: {changed_lines!r}"
    )
