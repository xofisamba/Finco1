#!/usr/bin/env python3
"""
Patch historical engine workflow YAML files to add CI scope routing.

For each target workflow:
1. Add concurrency block (cancel stale PR runs)
2. Insert classify-scope steps after checkout / assert-exact-head steps
3. Add  if: steps.scope.outputs.engine_sensitive == 'true'  to all
   heavy steps (setup-python, pip install, pytest, governance scans)
   so they are skipped for proven UI-only PRs.

The job name/context is PRESERVED so required GitHub status checks remain
satisfiable — the job always completes (Success), heavy steps are skipped.
"""
import re
import sys
from pathlib import Path

# ── Classify + skip-notice block inserted after the safe "always-run" steps ──

CLASSIFY_BLOCK = """\
      - name: Classify CI scope
        id: scope
        shell: bash
        run: |
          python3 .github/scripts/classify_ci_scope.py \\
            --base "${{ github.event.pull_request.base.sha || github.event.before || 'HEAD~1' }}" \\
            --head "${{ github.event.pull_request.head.sha || github.sha }}" \\
            | tee -a "$GITHUB_OUTPUT"

      - name: ENGINE_REGRESSION_SKIPPED_SAFE_UI_ONLY
        if: steps.scope.outputs.engine_sensitive != 'true'
        shell: bash
        run: |
          echo "======================================================"
          echo "ENGINE_REGRESSION_SKIPPED_SAFE_UI_ONLY"
          echo "All changed files are in UI/template/presentation paths."
          echo "No financial engine authority regression required."
          echo "Frozen authority diff: ZERO (verified by classifier)."
          echo "Full engine regression: available via nightly / workflow_dispatch."
          echo "======================================================"

"""

CONCURRENCY_BLOCK_TEMPLATE = """\
concurrency:
  group: {wf_id}-${{{{ github.event.pull_request.number || github.ref }}}}
  cancel-in-progress: true

"""

IF_ENGINE = "        if: steps.scope.outputs.engine_sensitive == 'true'"

# Patterns that identify "heavy" step names — these get the engine_sensitive if
HEAVY_NAME_PATTERNS = [
    re.compile(r"Assert .*(ancestry|ancestor|base|B4|C3|C2|B2)", re.I),
    re.compile(r"(Install|Set up) (Python|dependencies|deps)", re.I),
    re.compile(r"(Run|Execute) .*test", re.I),
    re.compile(r"(Diff|hygiene)", re.I),
    re.compile(r"Governance", re.I),
    re.compile(r"(parity|authority|freeze|acceptance|promotion)", re.I),
    re.compile(r"(focused|regression|ring|gate|guard|scan|diagnostic)", re.I),
    re.compile(r"(B4 production|C1|C2|C3|G0|G1|G2|KUPI|PR-\d)", re.I),
    re.compile(r"Report .*(count|result)", re.I),
]

# Patterns identifying always-run step names (never get if: added)
ALWAYS_RUN_PATTERNS = [
    re.compile(r"[Cc]heckout", re.I),
    re.compile(r"Assert exact.?head", re.I),
    re.compile(r"ENGINE_REGRESSION_SKIPPED", re.I),
    re.compile(r"Classify CI scope", re.I),
]

# Step uses that are always heavy
HEAVY_USES = [
    "actions/setup-python",
]


def _is_always_run_name(name: str) -> bool:
    return any(p.search(name) for p in ALWAYS_RUN_PATTERNS)


def _is_heavy_name(name: str) -> bool:
    return any(p.search(name) for p in HEAVY_NAME_PATTERNS)


def _is_heavy_uses(uses: str) -> bool:
    return any(u in uses for u in HEAVY_USES)


def _step_blocks(content: str):
    """
    Yield (start_line_idx, step_name_or_uses, lines_of_step) for each YAML step.
    Steps are detected by '      - name:' or '      - uses:' at 6-space indentation.
    """
    lines = content.split("\n")
    STEP_RE = re.compile(r"^      - (name|uses):\s*(.*)$")
    i = 0
    while i < len(lines):
        m = STEP_RE.match(lines[i])
        if m:
            yield i, m.group(2).strip()
        i += 1


def find_insertion_point(lines: list[str]) -> int:
    """
    Return the index of the first line after the last "always-run" step.
    This is where we insert the classify block.
    Falls back to inserting right after the checkout step.
    """
    STEP_RE = re.compile(r"^      - (name|uses):\s*(.*)$")
    last_safe_end = -1
    last_step_start = -1
    in_safe_zone = False

    for i, line in enumerate(lines):
        m = STEP_RE.match(line)
        if m:
            step_label = m.group(2).strip()
            if "actions/checkout" in step_label or _is_always_run_name(step_label):
                last_step_start = i
                in_safe_zone = True
            else:
                if in_safe_zone:
                    last_safe_end = i  # First non-safe step
                    break
                in_safe_zone = False

    if last_safe_end > 0:
        return last_safe_end

    # Fallback: insert after the checkout step
    for i, line in enumerate(lines):
        if "actions/checkout" in line:
            # Find end of this step's with: block
            j = i + 1
            while j < len(lines):
                stripped = lines[j].strip()
                if not stripped or stripped.startswith("- "):
                    break
                if lines[j].startswith("      - "):
                    break
                j += 1
            return j

    return len(lines)  # Fallback: append at end


def patch_workflow(filepath: Path) -> bool:
    """Patch a single workflow file. Returns True if modified."""
    original = filepath.read_text()
    lines = original.split("\n")

    # Skip if already patched
    if "Classify CI scope" in original:
        print(f"  SKIP (already patched): {filepath.name}")
        return False

    # Derive workflow id for concurrency group
    wf_id = filepath.stem.replace("_", "-")

    # 1. Add concurrency block if not present
    if "concurrency:" not in original:
        # Find 'jobs:' line and insert before it
        jobs_idx = next((i for i, l in enumerate(lines) if l.strip() == "jobs:"), None)
        if jobs_idx is not None:
            concurrency = CONCURRENCY_BLOCK_TEMPLATE.format(wf_id=wf_id)
            lines = lines[:jobs_idx] + concurrency.split("\n") + lines[jobs_idx:]

    # 2. Find insertion point for classify block
    insert_at = find_insertion_point(lines)

    # Insert classify block
    classify_lines = CLASSIFY_BLOCK.split("\n")
    lines = lines[:insert_at] + classify_lines + lines[insert_at:]

    # 3. Add if: to heavy steps after the insertion point
    # Re-scan from after the inserted classify block
    offset = insert_at + len(classify_lines)
    STEP_RE = re.compile(r"^      - (name|uses):\s*(.*)$")
    result = lines[:]

    i = offset
    insertions = []  # (after_line_idx, if_line_str)

    while i < len(result):
        line = result[i]
        m = STEP_RE.match(line)
        if m:
            kind = m.group(1)
            label = m.group(2).strip()

            # Skip always-run steps
            if _is_always_run_name(label):
                i += 1
                continue

            # Mark heavy steps
            should_mark = False
            if kind == "uses" and _is_heavy_uses(label):
                should_mark = True
            elif kind == "name" and _is_heavy_name(label):
                should_mark = True
            elif kind == "name":
                # Default for unrecognised steps: mark as heavy (fail-safe)
                # unless they look like reporting/summary steps
                if not re.search(r"(Report|Summary|Notice|Skip)", label, re.I):
                    should_mark = True

            if should_mark:
                # Check if if: already exists on the next non-blank line after this
                j = i + 1
                while j < len(result) and not result[j].strip():
                    j += 1
                if j < len(result) and "if:" in result[j]:
                    i += 1
                    continue  # already has if:

                insertions.append((i + 1, IF_ENGINE))

        i += 1

    # Apply insertions in reverse order to preserve indices
    for idx, if_line in reversed(insertions):
        result.insert(idx, if_line)

    patched = "\n".join(result)
    if patched == original:
        print(f"  NO CHANGE: {filepath.name}")
        return False

    filepath.write_text(patched)
    print(f"  PATCHED: {filepath.name}")
    return True


# ── Target workflows ──────────────────────────────────────────────────────────
# All heavy ENGINE_AUTHORITY/PARITY workflows that have pull_request trigger
# and no path-level filtering. ci.yml and parity_guardrails are lightweight
# and remain unchanged.

TARGET_WORKFLOWS = [
    "c3b1_diagnostic_check.yml",
    "c3b3a_clean_senior_debt_check.yml",
    "c3b3d2b5_shl_fixed_point_integration_check.yml",
    "c3b3d2b6_base_post_senior_cash_parity_check.yml",
    "c3b3d2b7_bank_case_senior_parity_check.yml",
    "c3b3d2b8_base_senior_shl_parity_check.yml",
    "kupi_k0_k3_causal_grid_check.yml",
    "mvp_g0_generic_clean_engine_check.yml",
    "mvp_g1_governance_methodology_lock.yml",
    "mvp_g2a_financing_stack_check.yml",
    "mvp_g2b_sponsor_returns_check.yml",
    "mvp_g2c_shareholder_waterfall_check.yml",
    "phaseb2_oborovo_clean_production_promotion.yml",
    "phaseb4_single_production_engine_check.yml",
    "phasec1_returns_maturity_check.yml",
    "phasec2_npv_llcr_plcr_authority.yml",
    "phasec3_clean_financial_statements_authority_check.yml",
    "prefreeze_pr5_canonical_ebitda_authority_check.yml",
    "prefreeze_pr6_typed_shl_repayment_policy_check.yml",
    "prefreeze_pr7_base_bank_case_authority_check.yml",
    "prefreeze_pr8_single_production_financial_authority_check.yml",
    "upstream_cash_reserve_interest_authority_check.yml",
]


def main():
    wf_dir = Path(__file__).resolve().parents[1] / "workflows"
    if not wf_dir.is_dir():
        print(f"ERROR: workflow dir not found: {wf_dir}", file=sys.stderr)
        sys.exit(1)

    patched = 0
    for name in TARGET_WORKFLOWS:
        fp = wf_dir / name
        if not fp.exists():
            print(f"  MISSING (skipped): {name}")
            continue
        if patch_workflow(fp):
            patched += 1

    print(f"\nDone. Patched {patched}/{len(TARGET_WORKFLOWS)} workflows.")


if __name__ == "__main__":
    main()
