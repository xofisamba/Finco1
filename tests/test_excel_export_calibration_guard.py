"""Verify Excel export has no runtime calibration imports."""
import ast
import inspect
from app import excel_export


def test_excel_export_does_not_import_calibration_modules():
    src = inspect.getsource(excel_export)
    tree = ast.parse(src)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    
    bad = [i for i in imports if i and (
        "calibration" in i.lower()
        or "excel_oborovo" in i.lower()
        or "excel_tuho" in i.lower()
        or "oborovo" in i.lower()
        or "tuho" in i.lower()
    )]
    assert not bad, f"Bad imports found: {bad}"