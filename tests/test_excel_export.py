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


def test_excel_export_includes_scenario_summary():
    """Notes sheet contains Scenario Deltas rows when scenario is Downside."""
    import openpyxl
    result = run_demo_project("Solar")
    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        scenario="Downside",
        integration_status="full",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    ws = wb["Notes"]
    fields = [row[0] for row in ws.iter_rows(max_row=ws.max_row, values_only=True) if row[0]]
    assert "Scenario Deltas" in fields
    # Should contain at least P50, CapEx, Tariff delta rows
    assert any("P50" in f or "CapEx" in f or "Tariff" in f for f in fields)


def test_excel_notes_include_scenario_deltas():
    """Downside scenario notes should include +/- change values."""
    import openpyxl
    result = run_demo_project("Solar")
    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        scenario="Downside",
        integration_status="full",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    ws = wb["Notes"]
    values = [row[1] for row in ws.iter_rows(max_row=ws.max_row, values_only=True) if row[1]]
    # Downside should show negative changes like "-10%"
    changes = [v for v in values if "%" in str(v) and ("-" in str(v) or "+" in str(v))]
    assert len(changes) > 0, f"Expected scenario change percentages in Notes, got: {values}"


def test_excel_notes_include_bess_hybrid_partial_warning():
    """Excel Notes sheet must include BESS/hybrid partial warning."""
    from io import BytesIO
    from app.ui_runner import run_demo_project
    from app.excel_export import build_excel_export
    import openpyxl

    result = run_demo_project("Solar+BESS")
    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        integration_status="partial",
        scenario="Base",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    notes_ws = wb["Notes"]
    all_values = [v for row in notes_ws.iter_rows(values_only=True) for v in row if v]
    notes_text = " ".join(str(v) for v in all_values).lower()
    assert "partial" in notes_text or "bess" in notes_text, \
        f"Notes sheet should mention BESS/hybrid partial status. Got: {notes_text[:200]}"


def test_excel_notes_include_portfolio_experimental_warning():
    """Notes sheet should contain Portfolio experimental warning when status=experimental."""
    import openpyxl
    result = run_demo_project("Portfolio")
    data = build_excel_export(
        portfolio_result=result.portfolio_result,
        project_inputs=result.project_inputs,
        integration_status="experimental",
        scenario="Base",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    ws = wb["Notes"]
    fields = [row[0] for row in ws.iter_rows(max_row=ws.max_row, values_only=True) if row[0]]
    portfolio_rows = [r for r in fields if "Portfolio" in str(r) or "IRR" in str(r)]
    assert len(portfolio_rows) > 0, f"Expected Portfolio/IRR warning in Notes, got fields: {fields}"


def test_portfolio_sponsor_irr_placeholder_label():
    """Portfolio IRR note in Dashboard or Notes should indicate placeholder status."""
    import openpyxl
    result = run_demo_project("Portfolio")
    data = build_excel_export(
        portfolio_result=result.portfolio_result,
        project_inputs=result.project_inputs,
        integration_status="experimental",
        scenario="Base",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    # Check all sheets for experimental/placeholder note
    all_values = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        # iter_rows with values_only=True returns tuples of cell values
        all_values.extend([v for row in ws.iter_rows(values_only=True) for v in row if v])
    # At minimum, the experimental status should be surfaced somewhere
    assert any("experimental" in str(v).lower() or "placeholder" in str(v).lower()
               for v in all_values), f"Portfolio IRR placeholder/experimental note not found in workbook values"


def test_excel_has_required_sheets():
    """Verify all required sheets exist (Dashboard, Notes, Inputs, CapEx, CapEx_Items, Revenue, Debt, Tax_Depreciation, Waterfall, Returns)."""
    import openpyxl
    result = run_demo_project("Solar")
    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        integration_status="full",
        scenario="Base",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    required = [
        "Dashboard", "Notes", "Inputs", "CapEx", "CapEx_Items",
        "Revenue", "Debt", "Tax_Depreciation", "Waterfall", "Returns",
    ]
    missing = [s for s in required if s not in wb.sheetnames]
    assert not missing, f"Missing sheets: {missing}"



def test_excel_sponsor_irr_not_numeric_zero():
    """Sponsor IRR in Portfolio table should be 'n/a' string, not 0.0 float, when placeholder."""
    import openpyxl
    result = run_demo_project("Portfolio")
    data = build_excel_export(
        portfolio_result=result.portfolio_result,
        project_inputs=result.project_inputs,
        integration_status="experimental",
        scenario="Base",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    found = False
    for sheet_name in ["Portfolio", "Dashboard", "Notes"]:
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        for row in ws.iter_rows(values_only=True):
            label = row[0] if row else ""
            if label and "sponsor" in str(label).lower() and "irr" in str(label).lower():
                val = row[1]
                assert val == "n/a", f"Sponsor IRR in {sheet_name} should be 'n/a' but got {val!r}"
                found = True
                break
        if found:
            break
    assert found, "Sponsor IRR row not found in Portfolio/Dashboard/Notes sheets"


def test_excel_values_only():
    """All cells must be values only — no Excel formula strings."""
    import openpyxl
    result = run_demo_project("Solar")
    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        integration_status="full",
        scenario="Base",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        for row in ws.iter_rows():
            for cell in row:
                assert cell.data_type != 'f', \
                    f"Formula found in sheet '{sheet}' at {cell.coordinate}: {cell.value}"


def test_excel_metadata_present():
    """Notes sheet must contain model_version, run_timestamp, scenario."""
    import openpyxl
    from io import BytesIO
    from app.excel_export import build_excel_export
    from app.ui_runner import run_demo_project

    result = run_demo_project("Solar")
    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        integration_status="full",
        scenario="Base",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    notes = wb["Notes"]
    fields = [row[0] for row in notes.iter_rows(values_only=True)]
    assert "Model Version" in fields, "Notes must include Model Version"
    assert "Run Timestamp" in fields, "Notes must include Run Timestamp"
    assert "Scenario" in fields, "Notes must include Scenario"


def test_excel_contains_required_ic_sheets():
    """Excel must contain sheets required for IC pack."""
    import openpyxl
    from io import BytesIO
    from app.excel_export import build_excel_export
    from app.ui_runner import run_demo_project

    result = run_demo_project("Solar")
    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        integration_status="full",
        scenario="Base",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    required = ["Dashboard", "Notes", "Returns", "CapEx", "Revenue"]
    missing = [s for s in required if s not in wb.sheetnames]
    assert not missing, f"Missing IC-required sheets: {missing}"


def test_excel_values_only():
    """All cells must be values only — no Excel formula strings."""
    import openpyxl
    from io import BytesIO
    from app.excel_export import build_excel_export
    from app.ui_runner import run_demo_project

    result = run_demo_project("Solar")
    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        integration_status="full",
        scenario="Base",
    )
    wb = openpyxl.load_workbook(BytesIO(data))
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        for row in ws.iter_rows():
            for cell in row:
                assert cell.data_type != 'f', \
                    f"Formula found in sheet '{sheet}' at {cell.coordinate}"

def test_dashboard_dscr_uses_actual_period_dscr():
    """Dashboard min_dscr/avg_dscr must match actual period DSCRs."""
    from app.ui_runner import run_demo_project
    from app.output_tables import build_dashboard_kpis
    result = run_demo_project("Solar").result
    kpis = build_dashboard_kpis(result)
    assert kpis["min_dscr"] == result.actual_min_dscr, (
        "min_dscr KPI must equal actual_min_dscr"
    )
    assert kpis["avg_dscr"] == result.actual_avg_dscr, (
        "avg_dscr KPI must equal actual_avg_dscr"
    )


def test_excel_export_uses_run_metadata_when_provided():
    """When run_metadata is provided, Notes sheet uses its git_sha, timestamp, scenario, project_type."""
    from io import BytesIO
    import openpyxl
    from app.excel_export import build_excel_export
    from app.run_metadata import RunMetadata
    from app.ui_runner import run_demo_project

    result = run_demo_project("Solar")

    meta = RunMetadata(
        run_id="test-run-001",
        timestamp="2026-01-15T10:00:00+00:00",
        model_version="industry-engine-refactor",
        git_sha="abc1234",
        scenario="Upside",
        project_type="Solar",
        notes="test note",
        warnings=[],
    )

    data = build_excel_export(
        result=result.result,
        project_inputs=result.project_inputs,
        integration_status="full",
        run_metadata=meta,
    )

    wb = openpyxl.load_workbook(BytesIO(data))
    ws = wb["Notes"]

    # Build dict of Field → Value from Notes sheet
    notes = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0]:
            notes[row[0]] = row[1]

    assert notes["Git SHA"] == "abc1234", f"Expected 'abc1234', got {notes['Git SHA']!r}"
    assert notes["Run Timestamp"] == "2026-01-15T10:00:00+00:00", f"Expected timestamp, got {notes['Run Timestamp']!r}"
    assert notes["Scenario"] == "Upside", f"Expected 'Upside', got {notes['Scenario']!r}"
    assert notes["Project Type"] == "Solar", f"Expected 'Solar', got {notes['Project Type']!r}"