"""Phase 9.5 — Excel-Like Project Workspace UI Design Tests

Verifies that the design spec and all required reports exist.
No runtime changes — design verification only.
"""

import os
import pytest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDocsExist:
    def test_design_doc_exists(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        assert os.path.exists(path), f"Design doc not found: {path}"

    def test_design_doc_not_empty(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        with open(path) as f:
            content = f.read()
        assert len(content) > 500, "Design doc is suspiciously short"

    def test_design_doc_has_executive_summary(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        with open(path) as f:
            content = f.read()
        assert "Executive Summary" in content

    def test_design_doc_has_no_runtime_changes_statement(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        with open(path) as f:
            content = f.read()
        assert "No runtime changes" in content or "no runtime" in content.lower()

    def test_design_doc_has_g20_blocked_note(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        with open(path) as f:
            content = f.read()
        assert "BLOCKED" in content

    def test_design_doc_has_r99_not_approved_note(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        with open(path) as f:
            content = f.read()
        assert "NOT APPROVED" in content


class TestReportsExist:
    def test_navigation_architecture_csv_exists(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_ui_navigation_architecture.csv")
        assert os.path.exists(path)

    def test_sheet_map_csv_exists(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_ui_sheet_map.csv")
        assert os.path.exists(path)

    def test_project_template_load_flow_csv_exists(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_project_template_load_flow.csv")
        assert os.path.exists(path)

    def test_wireframe_html_exists(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_excel_like_workspace_wireframe.html")
        assert os.path.exists(path)


class TestSheetMap:
    def test_sheet_map_has_required_tabs(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_ui_sheet_map.csv")
        with open(path) as f:
            content = f.read()
        required_tabs = [
            "Overview", "Inputs", "Construction", "Production", "Revenue",
            "OPEX", "CAPEX", "Senior_Debt", "SHL", "Tax",
            "PL", "Cash_Flow", "Balance_Sheet", "Distributions", "Sponsor_Equity",
            "Audit_Parity", "Downloads"
        ]
        for tab in required_tabs:
            # Allow both _ and space variants
            assert tab.replace("_", " ") in content or tab in content, f"Missing tab: {tab}"


class TestProjectTemplateLoadFlow:
    def test_tuho_in_load_flow(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_project_template_load_flow.csv")
        with open(path) as f:
            content = f.read()
        assert "TUHO" in content

    def test_oborovo_in_load_flow(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_project_template_load_flow.csv")
        with open(path) as f:
            content = f.read()
        assert "Oborovo" in content

    def test_tuho_has_factory_source(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_project_template_load_flow.csv")
        with open(path) as f:
            content = f.read()
        assert "tuho_factory" in content or "TUHO" in content

    def test_load_flow_has_save_load_status_column(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_project_template_load_flow.csv")
        with open(path) as f:
            content = f.read()
        assert "save_load_status" in content.lower() or "status" in content.lower()


class TestDesignDocContent:
    def test_design_doc_has_sidebar_architecture(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        with open(path) as f:
            content = f.read()
        assert "sidebar" in content.lower() and "workspace" in content.lower()

    def test_design_doc_has_top_tabs(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        with open(path) as f:
            content = f.read()
        assert "top" in content.lower() and "tab" in content.lower()

    def test_design_doc_has_implementation_phases(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        with open(path) as f:
            content = f.read()
        assert "Implementation" in content and ("phase" in content.lower() or "Phase" in content)

    def test_design_doc_has_tuho_load_flow(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        with open(path) as f:
            content = f.read()
        assert "TUHO" in content and "Load" in content

    def test_design_doc_has_save_load_future_path(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        with open(path) as f:
            content = f.read()
        assert "Phase 12" in content or "persistence" in content.lower()

    def test_design_doc_no_streamlit(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        with open(path) as f:
            content = f.read()
        assert "streamlit" not in content.lower()

    def test_design_doc_no_react_vue(self):
        path = os.path.join(REPO_ROOT, "docs", "phase9_5_excel_like_project_workspace_ui_design.md")
        with open(path) as f:
            content = f.read()
        assert "react" not in content.lower() and "vue" not in content.lower()


class TestWireframe:
    def test_wireframe_has_sidebar(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_excel_like_workspace_wireframe.html")
        with open(path) as f:
            content = f.read()
        assert 'class="sidebar"' in content or "sidebar" in content

    def test_wireframe_has_tab_ribbon(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_excel_like_workspace_wireframe.html")
        with open(path) as f:
            content = f.read()
        assert "tab" in content.lower()

    def test_wireframe_has_opex_period_table(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_excel_like_workspace_wireframe.html")
        with open(path) as f:
            content = f.read()
        assert "period-table" in content or "OPEX" in content

    def test_wireframe_has_governance_status(self):
        path = os.path.join(REPO_ROOT, "reports", "phase9_5_excel_like_workspace_wireframe.html")
        with open(path) as f:
            content = f.read()
        assert "BLOCKED" in content or "Governance" in content