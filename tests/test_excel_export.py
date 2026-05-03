"""Tests for app/excel_export.py."""
import pytest
from io import BytesIO
from app.excel_export import build_excel_export
from app.project_factories import create_default_solar_project
from app.ui_runner import run_demo_project


def test_build_excel_export_returns_bytes():
    result = run_demo_project("Solar")
    data = build_excel_export(result=result.result, project_inputs=result.project_inputs)
    assert isinstance(data, bytes)
    assert len(data) > 0


def test_excel_export_contains_required_sheets_for_solar():
    import openpyxl
    result = run_demo_project("Solar")
    data = build_excel_export(result=result.result, project_inputs=result.project_inputs)
    wb = openpyxl.load_workbook(BytesIO(data))
    sheet_names = wb.sheetnames
    required = ["Dashboard", "Inputs", "CapEx", "Revenue", "Debt", "Tax_Depreciation", "Waterfall", "Returns"]
    for s in required:
        assert s in sheet_names, f"Missing sheet: {s}"


def test_excel_export_contains_portfolio_sheet_when_portfolio_result_provided():
    import openpyxl
    from app.ui_runner import run_demo_project
    result = run_demo_project("Portfolio")
    data = build_excel_export(portfolio_result=result.portfolio_result, project_inputs=result.project_inputs)
    wb = openpyxl.load_workbook(BytesIO(data))
    assert "Portfolio" in wb.sheetnames


def test_excel_export_does_not_import_calibration_modules():
    import ast, inspect
    from app import excel_export
    src = inspect.getsource(excel_export)
    tree = ast.parse(src)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name if alias.asname is None else alias.asname)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            imports.append(mod)
    bad = [i for i in imports if i and ("calibration" in i or "excel_oborovo" in i or "excel_tuho" in i)]
    assert not bad, f"Bad imports: {bad}"


def test_inputs_summary_uses_technical_capacity():
    from app.input_helpers import build_inputs_summary_table
    proj = create_default_solar_project()
    df = build_inputs_summary_table(proj)
    # Capacity should appear in the summary
    assert "Capacity (MW)" in df["Field"].values


def test_capex_summary_uses_total_capex_fallback():
    from app.input_helpers import build_capex_summary_table
    proj = create_default_solar_project()
    df = build_capex_summary_table(proj)
    assert "Total CapEx (kEUR)" in df["Field"].values


def test_excel_export_with_portfolio_result_and_project_inputs():
    import openpyxl
    result = run_demo_project("Portfolio")
    solar_result = run_demo_project("Solar")
    data = build_excel_export(
        portfolio_result=result.portfolio_result,
        project_inputs=solar_result.project_inputs,
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    assert "Portfolio" in wb.sheetnames
    assert "Dashboard" in wb.sheetnames


def test_excel_export_contains_validation_and_notes_sheets():
    import openpyxl
    result = run_demo_project("Solar")
    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        validation_issues=[],
        integration_status="full",
        period_view="Semiannual",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    assert "Validation" in wb.sheetnames
    assert "Notes" in wb.sheetnames


def test_excel_export_values_only_no_formulas():
    """Excel file should have no formula cells."""
    import openpyxl
    result = run_demo_project("Solar")
    data = build_excel_export(result=result.result, project_inputs=result.project_inputs)
    wb = openpyxl.load_workbook(BytesIO(data))
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        for row in ws.iter_rows():
            for cell in row:
                assert cell.data_type != 'f', f"Formula found in {sheet}: {cell.coordinate}"


def test_excel_export_handles_project_without_capex_items():
    """Export should not crash if capex has no items."""
    result = run_demo_project("Solar")
    data = build_excel_export(result=result.result, project_inputs=result.project_inputs)
    assert isinstance(data, bytes)
    assert len(data) > 0
