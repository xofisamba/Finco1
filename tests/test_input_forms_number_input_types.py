"""Regression test: ensure no StreamlitMixedNumericTypesError in st.number_input calls.

Streamlit raises StreamlitMixedNumericTypesError when a number_input has a float value
but int min/max/step (or vice versa). This test parses input_forms.py and verifies
all st.number_input calls use consistent numeric types.
"""
import ast
import re
import sys
from typing import NamedTuple


class NumberInputCall(NamedTuple):
    label: str
    lineno: int
    value_type: str  # "int", "float", or "unknown"
    min_type: str
    max_type: str
    step_type: str
    has_mixed_types: bool


class NumberInputVisitor(ast.NodeVisitor):
    """AST visitor that finds all st.number_input() calls."""

    def __init__(self):
        self.calls: list[NumberInputCall] = []

    def visit_Call(self, node):
        # Check if this is st.number_input(...)
        is_number_input = False
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "number_input":
                # Check if it's st.number_input
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "st":
                    is_number_input = True

        if is_number_input:
            # Extract label from first positional arg
            label = ""
            if node.args and isinstance(node.args[0], ast.Constant):
                label = str(node.args[0].value)

            kwargs = {kw.arg: kw.value for kw in node.keywords}

            def get_type(kw_value) -> str:
                if kw_value is None:
                    return "notset"
                if isinstance(kw_value, ast.Constant):
                    if isinstance(kw_value.value, int):
                        return "int"
                    elif isinstance(kw_value.value, float):
                        return "float"
                    elif isinstance(kw_value.value, str):
                        return "str"
                elif isinstance(kw_value, ast.UnaryOp) and isinstance(kw_value.op, (ast.UAdd, ast.USub)):
                    operand = kw_value.operand
                    if isinstance(operand, ast.Constant) and isinstance(operand.value, (int, float)):
                        return "float" if isinstance(operand.value, float) else "int"
                elif isinstance(kw_value, ast.Name):
                    return "var"
                elif isinstance(kw_value, ast.Call):
                    # e.g. float(something) - treat as float
                    if isinstance(kw_value.func, ast.Name) and kw_value.func.id == "float":
                        return "float"
                    elif isinstance(kw_value.func, ast.Name) and kw_value.func.id == "int":
                        return "int"
                return "unknown"

            value_type = get_type(kwargs.get("value"))
            min_type = get_type(kwargs.get("min_value"))
            max_type = get_type(kwargs.get("max_value"))
            step_type = get_type(kwargs.get("step"))

            numeric_types = [t for t in [value_type, min_type, max_type, step_type] if t in ("int", "float")]
            has_mixed_types = len(set(numeric_types)) > 1 if numeric_types else False

            self.calls.append(NumberInputCall(
                label=label,
                lineno=node.lineno,
                value_type=value_type,
                min_type=min_type,
                max_type=max_type,
                step_type=step_type,
                has_mixed_types=has_mixed_types,
            ))

        self.generic_visit(node)


def extract_number_input_calls(source: str) -> list[NumberInputCall]:
    """Parse input_forms.py and extract all st.number_input calls using AST."""
    tree = ast.parse(source)
    visitor = NumberInputVisitor()
    visitor.visit(tree)
    return visitor.calls


def test_no_mixed_numeric_types_in_number_inputs():
    """Test that all st.number_input calls use consistent int/float types."""
    import app.input_forms

    source_file = app.input_forms.__file__
    with open(source_file) as f:
        source = f.read()

    calls = extract_number_input_calls(source)

    mixed = [c for c in calls if c.has_mixed_types]
    failures = []
    for c in mixed:
        failures.append(
            f"Line {c.lineno}: st.number_input('{c.label}') has mixed types — "
            f"value={c.value_type}, min_value={c.min_type}, max_value={c.max_type}, step={c.step_type}"
        )

    assert not failures, "Mixed numeric types found:\n" + "\n".join(failures)


def test_p50_inputs_are_all_float():
    """Specifically verify that p50_h number_inputs use float types (not int)."""
    import app.input_forms

    source_file = app.input_forms.__file__
    with open(source_file) as f:
        source = f.read()

    calls = extract_number_input_calls(source)
    p50_calls = [c for c in calls if "P50" in c.label]

    assert p50_calls, f"No P50 number_inputs found. All calls: {[(c.label, c.lineno) for c in calls]}"

    for c in p50_calls:
        assert c.value_type == "float", f"P50 '{c.label}' at line {c.lineno}: value_type={c.value_type}, expected float"
        assert c.min_type in ("float", "notset"), f"P50 '{c.label}' at line {c.lineno}: min_type={c.min_type}, expected float"
        assert c.max_type in ("float", "notset"), f"P50 '{c.label}' at line {c.lineno}: max_type={c.max_type}, expected float"
        assert c.step_type in ("float", "notset"), f"P50 '{c.label}' at line {c.lineno}: step_type={c.step_type}, expected float"


def test_all_number_inputs_summary():
    """Print summary of all number_input calls for transparency."""
    import app.input_forms

    source_file = app.input_forms.__file__
    with open(source_file) as f:
        source = f.read()

    calls = extract_number_input_calls(source)
    print(f"\nFound {len(calls)} st.number_input calls:")
    for c in calls:
        mixed = " [MIXED]" if c.has_mixed_types else ""
        print(f"  Line {c.lineno}: '{c.label}' value={c.value_type} min={c.min_type} max={c.max_type} step={c.step_type}{mixed}")