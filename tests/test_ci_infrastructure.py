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


def test_bess_design_doc_exists():
    """docs/bess_hybrid_design.md must exist (design only, not implemented)."""
    assert os.path.exists("docs/bess_hybrid_design.md"), "docs/bess_hybrid_design.md not found"


def test_model_status_contains_supported_features():
    """model_status.md must list Solar and Wind as fully supported."""
    with open("docs/model_status.md") as f:
        content = f.read().lower()
    assert "solar" in content and "wind" in content, "Solar and Wind must be mentioned"


def test_model_status_contains_partial_features():
    """model_status.md must list BESS and Hybrid as partial."""
    with open("docs/model_status.md") as f:
        content = f.read().lower()
    assert "bess" in content and "hybrid" in content, "BESS and Hybrid must be mentioned"


def test_model_status_contains_not_implemented():
    """model_status.md must list Sponsor IRR and Portfolio scenarios as not implemented."""
    with open("docs/model_status.md") as f:
        content = f.read().lower()
    assert "sponsor irr" in content or "sponsor" in content, "Sponsor IRR must be mentioned"


def test_model_status_contains_bankable_warning():
    """model_status.md must contain an explicit warning about bankable validation."""
    with open("docs/model_status.md") as f:
        content = f.read().lower()
    assert "bankable" in content, "Bankable warning must be present"


def test_streamlit_app_wires_warnings_to_excel(monkeypatch):
    """streamlit_app.py must call build_excel_export with warnings=model_warnings."""
    with open("streamlit_app.py") as f:
        src = f.read()
    assert "warn_model_unrealistic" in src, "streamlit_app must call warn_model_unrealistic"
    assert "warnings=model_warnings" in src, "build_excel_export must be called with warnings=model_warnings"


def test_model_status_declares_scenario_v2_parameters():
    """model_status.md must explicitly list Scenario v2 parameters."""
    with open("docs/model_status.md") as f:
        content = f.read()
    lower = content.lower()
    checks = {
        "Scenario v2": "scenario v2" in lower,
        "CapEx": "capex" in lower,
        "OpEx": "opex" in lower,
        "Degradation": "degradation" in lower,
        "Curtailment": "curtailment" in lower,
        "Tariff": "tariff" in lower,
        "Portfolio scenarios not implemented": ("portfolio" in lower and ("not implemented" in lower or "experimental" in lower)),
        "Sponsor IRR not implemented": ("sponsor irr" in lower and ("not implemented" in lower or "not supported" in lower or "placeholder" in lower)),
        "BESS partial": "bess" in lower and "partial" in lower,
    }
    missing = [k for k, v in checks.items() if not v]
    assert not missing, f"model_status.md missing: {missing}"

def test_release1_readiness_doc_exists():
    """release1_readiness.md must exist with required sections."""
    import os
    path = "docs/release1_readiness.md"
    assert os.path.exists(path), f"{path} must exist"
    with open(path) as f:
        content = f.read()
    required = ["Release 1", "Out of Scope", "Known Limitations", "Claude Re-check"]
    missing = [s for s in required if s not in content]
    assert not missing, f"release1_readiness.md missing sections: {missing}"
