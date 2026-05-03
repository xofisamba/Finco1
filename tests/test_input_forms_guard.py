"""Verify input_forms has no runtime calibration imports."""
import ast
import inspect
from app import input_forms


def test_input_forms_does_not_import_calibration_modules():
    src = inspect.getsource(input_forms)
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
    )]
    assert not bad, f"Bad imports: {bad}"