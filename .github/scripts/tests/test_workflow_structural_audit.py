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
        violations = []
        for f, content, data, pr in _load_workflows():
            name = f.name
            has_path_filter = bool(pr.get("paths") or pr.get("paths-ignore"))
            has_classifier = (
                "classify_ci_scope" in content or "Classify CI scope" in content
            )
            has_pytest = "pytest" in content
            in_allowlist = name in LIGHTWEIGHT_ALLOWLIST
            if has_pytest and not has_classifier and not has_path_filter and not in_allowlist:
                violations.append(name)
        assert not violations, (
            f"Workflows trigger on main PRs with pytest but no classifier guard, "
            f"path filter, or allowlist entry:\n  " + "\n  ".join(violations)
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
