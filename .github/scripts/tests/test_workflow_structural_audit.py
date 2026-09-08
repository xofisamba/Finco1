"""
Structural audit tests for .github/workflows/*.yml

Proves that no future workflow can accidentally reintroduce unconditional
engine fanout on main PRs without triggering a test failure.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPTS_DIR.parents[1]
WF_DIR = REPO_ROOT / ".github/workflows"

sys.path.insert(0, str(SCRIPTS_DIR))

# Explicitly allowed lightweight workflows: these may run pytest on every PR
# without a classifier guard because they are intentionally fast.
LIGHTWEIGHT_ALLOWLIST = {
    "ci.yml",                # has its own classify-scope job
    "parity_guardrails.yml", # fast ~60s, Phase 51F guardrails only
}


def _load_workflows():
    """Yield (path, raw_content, parsed_yaml, pr_trigger) for all main-PR workflows."""
    try:
        import yaml
    except ImportError:
        return
    for f in sorted(WF_DIR.glob("*.yml")):
        try:
            data = yaml.safe_load(f.read_text())
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        on = data.get("on") or {}
        if isinstance(on, str):
            continue
        pr = on.get("pull_request") or {}
        branches = pr.get("branches", []) if isinstance(pr, dict) else []
        if "main" not in branches:
            continue
        yield f, f.read_text(), data, pr


class TestStructuralAudit:
    def test_yaml_importable(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            import subprocess, sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
            import yaml  # noqa: F401

    def test_all_main_pr_workflows_guarded(self):
        # NOTE: path-filtered workflows are NOT exempt. A path-filtered heavy
        # workflow can still execute its full body when triggered by a workflow-only
        # PR that touches a .github/ file listed in its paths: filter.
        # Every workflow with pytest must have a classifier guard OR be explicitly
        # in the lightweight allowlist.
        violations = []
        for f, content, data, pr in _load_workflows():
            name = f.name
            has_classifier = (
                "classify_ci_scope" in content or "Classify CI scope" in content
            )
            has_pytest = "pytest" in content
            in_allowlist = name in LIGHTWEIGHT_ALLOWLIST
            if has_pytest and not has_classifier and not in_allowlist:
                violations.append(name)
        assert not violations, (
            f"Workflows trigger on main PRs with pytest but no classifier guard "
            f"or allowlist entry (path filter alone is not sufficient):\n  "
            + "\n  ".join(violations)
        )

    def test_no_engine_workflow_suppresses_failures(self):
        """Classifier-guarded workflows must not use '|| true' to swallow pytest failures."""
        violations = []
        for f, content, data, pr in _load_workflows():
            if "Classify CI scope" in content and "|| true" in content:
                violations.append(f.name)
        assert not violations, (
            f"Classifier-guarded workflows contain '|| true': {violations}"
        )

    def test_classifier_steps_reference_script(self):
        for f, content, data, pr in _load_workflows():
            if "Classify CI scope" in content:
                assert "classify_ci_scope.py" in content, (
                    f"{f.name}: 'Classify CI scope' step must call classify_ci_scope.py"
                )

    def test_all_workflows_parse_as_valid_yaml(self):
        import yaml
        errors = []
        for wf in sorted(WF_DIR.glob("*.yml")):
            try:
                yaml.safe_load(wf.read_text())
            except yaml.YAMLError as e:
                errors.append(f"{wf.name}: {e}")
        assert not errors, "YAML parse errors:\n" + "\n".join(errors)

    def test_allowlist_workflows_exist(self):
        for name in LIGHTWEIGHT_ALLOWLIST:
            assert (WF_DIR / name).exists(), (
                f"Allowlisted lightweight workflow does not exist: {name}"
            )

    def test_ci_yml_exposes_all_scope_outputs(self):
        """ci.yml must expose all four scope outputs so jobs can route explicitly."""
        content = (WF_DIR / "ci.yml").read_text()
        for key in ("engine_sensitive", "ui_only", "docs_only", "workflow_only"):
            assert key in content, (
                f"ci.yml must expose '{key}' as a job output for explicit routing"
            )

    def test_c3b3a_is_guarded(self):
        """c3b3a_clean_senior_debt_check.yml must have classifier + step guards."""
        f = WF_DIR / "c3b3a_clean_senior_debt_check.yml"
        assert f.exists()
        content = f.read_text()
        assert "Classify CI scope" in content, "c3b3a must have Classify CI scope step"
        assert "classify_ci_scope.py" in content, "c3b3a must call classify_ci_scope.py"
        assert "engine_sensitive == 'true'" in content, (
            "c3b3a must guard heavy steps with engine_sensitive == 'true'"
        )
        # setup-python must be guarded
        setup_idx = content.find("actions/setup-python")
        assert setup_idx != -1
        before_setup = content[max(0, setup_idx-200):setup_idx]
        assert "engine_sensitive" in before_setup, (
            "c3b3a: setup-python must be guarded with engine_sensitive"
        )
        # Check original job name preserved
        assert "C3B3A Clean Senior Debt Source Contract" in content, (
            "c3b3a: job name must be preserved"
        )

    def test_c3b3d2b5_is_guarded(self):
        """c3b3d2b5_shl_fixed_point_integration_check.yml must have classifier + step guards."""
        f = WF_DIR / "c3b3d2b5_shl_fixed_point_integration_check.yml"
        assert f.exists()
        content = f.read_text()
        assert "Classify CI scope" in content, "c3b3d2b5 must have Classify CI scope step"
        assert "classify_ci_scope.py" in content, "c3b3d2b5 must call classify_ci_scope.py"
        assert "engine_sensitive == 'true'" in content, (
            "c3b3d2b5 must guard heavy steps with engine_sensitive == 'true'"
        )
        # setup-python must be guarded
        setup_idx = content.find("actions/setup-python")
        assert setup_idx != -1
        before_setup = content[max(0, setup_idx-200):setup_idx]
        assert "engine_sensitive" in before_setup, (
            "c3b3d2b5: setup-python must be guarded with engine_sensitive"
        )
        # pytest steps must be guarded
        for step_name in [
            "C3B3D2B5 full suite",
            "C3B3D2B4 post-senior cash authority regression",
            "C3B3A clean senior debt regression",
            "Production governance scans",
        ]:
            idx = content.find(f"- name: {step_name}")
            assert idx != -1, f"c3b3d2b5: step '{step_name}' not found"
            after = content[idx:idx+150]
            assert "engine_sensitive" in after, (
                f"c3b3d2b5: step '{step_name}' must be guarded with engine_sensitive"
            )
        # Check original job name preserved
        assert "C3B3D2B5 SHL fixed-point integration" in content, (
            "c3b3d2b5: job name must be preserved"
        )

    def test_nightly_not_in_pr_trigger(self):
        """Nightly regression must not trigger on pull_request."""
        nightly = WF_DIR / "nightly_full_engine_regression.yml"
        assert nightly.exists()
        content = nightly.read_text()
        # schedule and workflow_dispatch are expected; pull_request is not
        assert "schedule:" in content
        assert "workflow_dispatch" in content
        # pull_request trigger would mean it runs on every PR — not allowed
        assert "pull_request:" not in content, (
            "nightly_full_engine_regression.yml must not trigger on pull_request"
        )
