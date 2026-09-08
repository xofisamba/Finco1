"""
Tests for .github/scripts/engine_regression_manifest.py

Proves:
  - every manifest test path exists on disk
  - no duplicate entries
  - no `|| true` pattern in nightly workflow
  - manifest is non-empty
  - all required authority areas are represented
  - key frozen suites C1/C2/C3/B4/G0/G2A/G2B/G2C/U2/PR6/PR7/PR8/KUPI covered
"""
import sys
from pathlib import Path

# Make the scripts directory importable
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPTS_DIR.parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from engine_regression_manifest import (  # noqa: E402
    MANIFEST,
    REQUIRED_AREAS,
    TEST_PATHS,
    validate_manifest,
)


class TestManifestIntegrity:
    def test_manifest_non_empty(self):
        assert len(MANIFEST) > 0, "MANIFEST must not be empty"

    def test_no_duplicate_paths(self):
        paths = [e["path"] for e in MANIFEST]
        duplicates = [p for p in paths if paths.count(p) > 1]
        assert not duplicates, f"Duplicate manifest paths: {set(duplicates)}"

    def test_all_files_exist(self):
        missing = [e["path"] for e in MANIFEST if not (REPO_ROOT / e["path"]).exists()]
        assert not missing, f"Missing test files: {missing}"

    def test_required_areas_covered(self):
        covered = {a for e in MANIFEST for a in e.get("areas", [])}
        missing = REQUIRED_AREAS - covered
        assert not missing, f"Required areas not covered: {sorted(missing)}"

    def test_key_suites_present(self):
        key_labels = {
            "C1": "test_phasec1_returns_maturity_authority.py",
            "C2": "test_phasec2_npv_llcr_plcr_authority.py",
            "C3": "test_phasec3_clean_financial_statements_authority.py",
            "B4": "test_phaseb4_single_production_engine.py",
            "G0": "test_mvp_g0_generic_clean_engine_enablement.py",
            "G2B": "test_mvp_g2b_sponsor_returns.py",
            "G2C": "test_mvp_g2c_shareholder_waterfall.py",
            "U2": "test_upstream_cash_reserve_interest_policy.py",
            "PR6": "test_prefreeze_pr6_typed_shl_repayment_policy.py",
            "PR7": "test_prefreeze_pr7_typed_base_bank_case_authority.py",
            "PR8": "test_prefreeze_pr8_single_production_financial_authority.py",
            "KUPI": "test_kupi_k0_k3_causal_grid.py",
        }
        for area, filename in key_labels.items():
            found = any(filename in e["path"] for e in MANIFEST)
            assert found, f"Key suite for area {area!r} ({filename}) not in manifest"

    def test_each_entry_has_required_keys(self):
        for entry in MANIFEST:
            assert "path" in entry, f"Entry missing 'path': {entry}"
            assert "areas" in entry, f"Entry missing 'areas': {entry}"
            assert "label" in entry, f"Entry missing 'label': {entry}"
            assert isinstance(entry["areas"], list), f"'areas' must be a list: {entry}"
            assert len(entry["areas"]) > 0, f"'areas' must not be empty: {entry}"

    def test_c3b3a_represented(self):
        """C3B3A clean senior debt source contract must be in the manifest."""
        found = any("c3b3a" in e["path"] for e in MANIFEST)
        assert found, "test_stage_c3b3a_clean_senior_debt_source_contract.py not in manifest"

    def test_c3b3d2b5_represented(self):
        """C3B3D2B5 SHL fixed-point integration must be in the manifest."""
        found = any("c3b3d2b5" in e["path"] for e in MANIFEST)
        assert found, "test_stage_c3b3d2b5_shl_fixed_point_integration.py not in manifest"

    def test_validate_manifest_passes(self):
        errors = validate_manifest(REPO_ROOT)
        assert not errors, f"Manifest validation errors: {errors}"

    def test_test_paths_matches_manifest(self):
        assert TEST_PATHS == [e["path"] for e in MANIFEST]


class TestNightlyWorkflowTrustworthy:
    """Nightly workflow must not suppress test failures."""

    NIGHTLY_PATH = REPO_ROOT / ".github/workflows/nightly_full_engine_regression.yml"

    def test_nightly_file_exists(self):
        assert self.NIGHTLY_PATH.exists(), "nightly_full_engine_regression.yml not found"

    def test_no_or_true_in_nightly(self):
        content = self.NIGHTLY_PATH.read_text()
        assert "|| true" not in content, (
            "nightly_full_engine_regression.yml must not suppress failures with '|| true'"
        )

    def test_no_continue_on_error_without_aggregator(self):
        content = self.NIGHTLY_PATH.read_text()
        # continue-on-error is allowed ONLY if there is a final aggregation step
        # that exits non-zero. We check: if continue-on-error exists, then
        # "exit 1" or "sys.exit(1)" must also appear (the aggregator).
        if "continue-on-error: true" in content:
            assert "exit 1" in content, (
                "continue-on-error used without a failure-aggregating 'exit 1'"
            )

    def test_manifest_paths_referenced_in_nightly(self):
        content = self.NIGHTLY_PATH.read_text()
        # The nightly should reference the manifest or test files directly
        assert (
            "engine_regression_manifest" in content
            or any(Path(p).name in content for p in TEST_PATHS[:5])
        ), "nightly workflow does not appear to reference the canonical manifest"

    def test_nightly_has_schedule_trigger(self):
        content = self.NIGHTLY_PATH.read_text()
        assert "schedule:" in content, "Nightly workflow must have a schedule trigger"
        assert "cron:" in content, "Nightly workflow must have a cron expression"

    def test_nightly_has_workflow_dispatch(self):
        content = self.NIGHTLY_PATH.read_text()
        assert "workflow_dispatch" in content, "Nightly workflow must support workflow_dispatch"


class TestWorkflowStructuralAudit:
    """
    Structural audit: every workflow that triggers on PRs to main with
    expensive pytest must either have a classifier guard or a path filter.
    """

    WF_DIR = REPO_ROOT / ".github/workflows"

    # Explicitly allowed lightweight workflows that may run pytest without
    # a classifier guard, because they are fast and always safe.
    LIGHTWEIGHT_ALLOWLIST = {
        "ci.yml",                # has its own classify-scope job
        "parity_guardrails.yml", # fast ~60s, intentionally minimal (Phase 51F)
    }

    def _parse_workflows(self):
        import yaml
        results = []
        for f in sorted(self.WF_DIR.glob("*.yml")):
            try:
                data = yaml.safe_load(f.read_text())
            except Exception:
                continue
            on = data.get("on") or {}
            if isinstance(on, str):
                continue
            pr = on.get("pull_request") or {}
            branches = pr.get("branches", []) if pr else []
            if "main" not in branches:
                continue
            results.append((f, data, pr))
        return results

    def test_all_main_pr_workflows_are_guarded_or_allowlisted_or_path_filtered(self):
        import yaml
        violations = []
        for f, data, pr in self._parse_workflows():
            name = f.name
            content = f.read_text()
            has_path_filter = bool(pr.get("paths") or pr.get("paths-ignore"))
            has_classifier = "classify_ci_scope" in content or "Classify CI scope" in content
            has_pytest = "pytest" in content
            in_allowlist = name in self.LIGHTWEIGHT_ALLOWLIST

            if has_pytest and not has_classifier and not has_path_filter and not in_allowlist:
                violations.append(name)

        assert not violations, (
            f"Workflows trigger on main PRs with pytest but no classifier guard, "
            f"path filter, or allowlist entry: {violations}"
        )

    def test_all_classifier_guards_reference_correct_script(self):
        for f, data, pr in self._parse_workflows():
            content = f.read_text()
            if "Classify CI scope" in content:
                assert "classify_ci_scope.py" in content, (
                    f"{f.name}: has 'Classify CI scope' step but does not call "
                    f"classify_ci_scope.py"
                )

    def test_no_or_true_in_engine_authority_workflows(self):
        """Engine authority workflows must not suppress pytest failures."""
        engine_wfs = [
            f for f, data, pr in self._parse_workflows()
            if "Classify CI scope" in f.read_text()
        ]
        violations = []
        for f in engine_wfs:
            if "|| true" in f.read_text():
                violations.append(f.name)
        assert not violations, (
            f"Engine authority workflows contain '|| true': {violations}"
        )
