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


def test_oborovo_shim_available_in_isolated_test_context():
    """ProjectInputs.create_default_oborovo must be accessible after app.project_factories import."""
    # This verifies the shim works even in an isolated context
    import importlib
    import sys

    # Remove app.project_factories from cache to simulate isolated import
    mods_to_remove = [k for k in sys.modules if k.startswith("app.project_factories") or k.startswith("domain.inputs")]
    for m in mods_to_remove:
        del sys.modules[m]

    # Import fresh — shim should be installed
    from app.project_factories import create_default_oborovo
    proj = create_default_oborovo()
    assert proj is not None
    assert proj.info.name
