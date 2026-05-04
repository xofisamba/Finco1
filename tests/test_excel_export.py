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


def test_excel_export_has_all_required_sheets():
    """All required sheets must be present in the export for Solar project."""
    import openpyxl
    result = run_demo_project("Solar")
    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        integration_status="full",
        integration_note=None,
        scenario="Base",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    sheet_names = wb.sheetnames
    required = [
        "Dashboard", "Inputs", "CapEx",
        "Revenue", "Debt", "Tax_Depreciation",
        "Waterfall", "Returns", "Validation", "Notes",
    ]
    missing = [s for s in required if s not in sheet_names]
    assert not missing, f"Missing sheets: {missing}"


def test_excel_export_no_formulas_in_cells():
    """All cells must be values only — no Excel formulas."""
    import openpyxl
    result = run_demo_project("Solar")
    data = build_excel_export(result=result.result, project_inputs=result.project_inputs)
    wb = openpyxl.load_workbook(BytesIO(data))
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        for row in ws.iter_rows():
            for cell in row:
                assert cell.data_type != 'f', \
                    f"Formula found in sheet '{sheet}' at {cell.coordinate}: {cell.value}"


def test_excel_export_annual_columns_are_years():
    """Annual-view sheets must have 4-digit year column headers (YYYY)."""
    import openpyxl, re
    result = run_demo_project("Solar")
    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        period_view="Annual",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    for sheet_name in ["Revenue", "Debt", "Tax_Depreciation", "Waterfall"]:
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        headers = [cell.value for cell in ws[1]]
        year_cols = [h for h in headers if isinstance(h, str) and re.match(r"\d{4}", h)]
        assert len(year_cols) > 0, \
            f"Sheet '{sheet_name}' has no year columns: {headers[:8]}"


def test_excel_export_contains_portfolio_sheet_when_portfolio_result_provided():
    import openpyxl
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


def test_excel_export_annual_view_has_year_columns():
    """Annual view in Excel should have year-labeled columns (YYYY format)."""
    import openpyxl, re
    result = run_demo_project("Solar")
    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        period_view="Annual",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    for sheet_name in ["Revenue", "Debt", "Tax_Depreciation", "Waterfall"]:
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        headers = [cell.value for cell in ws[1]]
        year_cols = [h for h in headers if h is not None and isinstance(h, str) and re.match(r"\d{4}", h)]
        assert len(year_cols) > 0, f"Sheet {sheet_name} has no year columns in headers: {headers}"


def test_excel_export_does_not_use_local_aggregate_annual():
    """excel_export.py must not define its own _aggregate_annual function."""
    import ast, inspect
    from app import excel_export
    src = inspect.getsource(excel_export)
    assert "def _aggregate_annual" not in src, \
        "_aggregate_annual should have been removed; use aggregate_period_table_annual from output_tables"


def test_excel_export_annual_view_uses_output_table_helper():
    """Annual view must use aggregate_period_table_annual from output_tables."""
    import ast, inspect
    from app import excel_export
    src = inspect.getsource(excel_export)
    tree = ast.parse(src)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "aggregate_period_table_annual":
            found = True
            break
    assert found, "aggregate_period_table_annual from output_tables not used in excel_export.py"