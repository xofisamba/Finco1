"""Tests for CI infrastructure and model status documentation."""
import os

def test_ci_workflow_exists():
    """.github/workflows/ci.yml must exist."""
    path = ".github/workflows/ci.yml"
    assert os.path.exists(path), f"CI workflow not found at {path}"


def test_model_status_doc_exists():
    """docs/model_status.md must exist."""
    assert os.path.exists("docs/model_status.md"), "docs/model_status.md not found"


def test_model_status_contains_sections():
    """model_status.md must contain required sections."""
    with open("docs/model_status.md") as f:
        content = f.read().lower()
    required = ["supported features", "partial features", "not implemented",
                "known limitations", "warning"]
    missing = [s for s in required if s not in content]
    assert not missing, f"model_status.md missing sections: {missing}"


def test_scenario_v2_scope_doc_exists():
    """docs/scenario_v2_scope.md must exist (placeholder, not implemented)."""
    assert os.path.exists("docs/scenario_v2_scope.md"), "docs/scenario_v2_scope.md not found"


def test_oborovo_cleanup_plan_doc_exists():
    """docs/oborovo_compat_cleanup_plan.md must exist."""
    assert os.path.exists("docs/oborovo_compat_cleanup_plan.md"), \
        "docs/oborovo_compat_cleanup_plan.md not found"
