"""
Security unit tests for app.utils.script_json.dumps_for_script.

Tests the shared HTML-script-safe JSON serializer that replaces bare
json.dumps calls in script-context HTML emission (RuntimeResult and
run_service._build_sessionstorage_save_tag).

Property tested: no user-controlled value can produce a literal "<" in the
serialized output, preventing </script> from terminating the enclosing HTML
script element.
"""
from __future__ import annotations

import json

import pytest

from app.utils.script_json import dumps_for_script

_XSS_MARKER = 'Project </script><script>window.__fincoXssMarker="executed"</script>'
_INERT_PAYLOAD = _XSS_MARKER  # alias for clarity in tests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_no_literal_lt(result: str, label: str = "") -> None:
    assert "<" not in result, (
        f"Literal '<' found in output{(' (' + label + ')') if label else ''}: {result!r}"
    )


def _assert_no_script_close(result: str) -> None:
    assert "</script" not in result.lower(), (
        f"Closing-script sequence found: {result!r}"
    )


def _assert_valid_json_roundtrip(original, result: str) -> None:
    parsed = json.loads(result)
    assert parsed == original, (
        f"Round-trip failed.\nOriginal: {original!r}\nParsed:   {parsed!r}"
    )


# ---------------------------------------------------------------------------
# A. Core escaping contract
# ---------------------------------------------------------------------------

class TestCoreEscaping:
    def test_lt_is_escaped(self):
        r = dumps_for_script("<")
        _assert_no_literal_lt(r)

    def test_gt_is_escaped(self):
        r = dumps_for_script(">")
        assert ">" not in r

    def test_amp_is_escaped(self):
        r = dumps_for_script("&")
        assert "&" not in r

    def test_ls_escaped(self):
        ls = chr(0x2028)
        r = dumps_for_script(ls)
        assert ls not in r
        assert "\\u2028" in r

    def test_ps_escaped(self):
        ps = chr(0x2029)
        r = dumps_for_script(ps)
        assert ps not in r
        assert "\\u2029" in r

    def test_lt_uses_u003c(self):
        r = dumps_for_script("<")
        assert "\\u003c" in r

    def test_gt_uses_u003e(self):
        r = dumps_for_script(">")
        assert "\\u003e" in r

    def test_amp_uses_u0026(self):
        r = dumps_for_script("&")
        assert "\\u0026" in r

    def test_no_closing_script_simple(self):
        r = dumps_for_script("</script>")
        _assert_no_script_close(r)

    def test_no_closing_script_mixed_case(self):
        r = dumps_for_script("</ScRiPt>")
        _assert_no_script_close(r)

    def test_full_xss_payload_no_literal_lt(self):
        r = dumps_for_script(_XSS_MARKER)
        _assert_no_literal_lt(r, "full XSS marker")
        _assert_no_script_close(r)

    def test_full_xss_payload_is_valid_json(self):
        r = dumps_for_script(_XSS_MARKER)
        assert json.loads(r) == _XSS_MARKER

    def test_result_is_valid_json(self):
        r = dumps_for_script({"key": _INERT_PAYLOAD})
        parsed = json.loads(r)
        assert parsed == {"key": _INERT_PAYLOAD}


# ---------------------------------------------------------------------------
# B. Round-trip contract for many value types
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [
    # Strings
    "hello",
    "",
    "\u010d\u0107\u017e\u0161\u0111",  # Croatian chars
    '"',
    "'",
    "back\\slash",
    "line\nnewline\ttab",
    "<angle brackets>",
    "fish & chips",
    "</script>",
    "</ScRiPt>",
    _XSS_MARKER,
    # Scalars
    0,
    -1,
    3.14,
    True,
    False,
    None,
    # Containers
    [],
    {},
    [1, 2, 3],
    {"a": 1, "b": [None, False, 0, ""]},
    {"xss": _XSS_MARKER, "nested": {"also": "<bad>"}},
])
def test_round_trip(value):
    result = dumps_for_script(value)
    assert isinstance(result, str)
    _assert_no_literal_lt(result, repr(value)[:60])
    _assert_valid_json_roundtrip(value, result)


def test_round_trip_croatian():
    """Croatian Unicode characters survive round-trip."""
    s = "\u010d\u0107\u017e\u0161\u0111"  # \u010d=c with caron etc
    result = dumps_for_script(s)
    assert json.loads(result) == s


def test_round_trip_ls_ps():
    """U+2028 and U+2029 survive round-trip."""
    s = chr(0x2028) + chr(0x2029)
    result = dumps_for_script(s)
    assert chr(0x2028) not in result
    assert chr(0x2029) not in result
    assert json.loads(result) == s


# ---------------------------------------------------------------------------
# C. Output is valid JSON (parseable by standard library)
# ---------------------------------------------------------------------------

def test_output_parseable_dict():
    d = {"project": "My Project", "xss": _XSS_MARKER, "n": 42, "flag": True}
    r = dumps_for_script(d)
    json.loads(r)  # must not raise


def test_output_parseable_nested_list():
    lst = [{"k": "</script>"}, [1, 2], None]
    r = dumps_for_script(lst)
    json.loads(r)


# ---------------------------------------------------------------------------
# D. json_options pass-through
# ---------------------------------------------------------------------------

def test_sort_keys_option():
    d = {"z": 1, "a": 2}
    r = dumps_for_script(d, sort_keys=True)
    parsed = json.loads(r)
    assert list(parsed.keys()) == ["a", "z"]
    _assert_no_literal_lt(r)


def test_ensure_ascii_false_still_escapes_dangerous_chars():
    r = dumps_for_script("<safe_ascii>", ensure_ascii=False)
    _assert_no_literal_lt(r)
    assert json.loads(r) == "<safe_ascii>"


# ---------------------------------------------------------------------------
# E. No double-encoding
# ---------------------------------------------------------------------------

def test_no_double_encoding_of_complete_document():
    r = dumps_for_script("&")
    assert "&amp;" not in r
    assert "&lt;" not in r
    assert "&gt;" not in r


def test_normal_unicode_preserved():
    s = "\u010d\u0107\u017e\u0161\u0111"
    r = dumps_for_script(s)
    assert json.loads(r) == s


def test_double_quotes_not_converted_to_html_entity():
    r = dumps_for_script('"hello"')
    assert "&quot;" not in r
    assert json.loads(r) == '"hello"'


# ---------------------------------------------------------------------------
# F. Emitter-level tests -- RuntimeResult.to_sessionstorage_script()
# ---------------------------------------------------------------------------

class TestRuntimeResultEmitter:
    """Verify the security property via the real to_sessionstorage_script()."""

    def _make_rr(self, name: str = "safe"):
        from app.workbook.runtime_result import RuntimeResult
        return RuntimeResult(
            snapshot_id="snap-001",
            ran_at="2026-07-17T00:00:00Z",
            origin="user_created",
            runtime_summary={"project_name": name, "kpi": 1.0},
            financial_statements={"pnl": {"periods": []}},
            debt_schedule=None,
            tax_schedule=None,
            distribution_schedule=None,
            sponsor_schedule=None,
        )

    def test_safe_name_produces_script(self):
        rr = self._make_rr("Ordinary Project")
        script = rr.to_sessionstorage_script()
        assert script.startswith("<script>")
        assert script.endswith("</script>")

    def test_xss_name_no_literal_lt(self):
        rr = self._make_rr(_XSS_MARKER)
        script = rr.to_sessionstorage_script()
        inner = script[len("<script>"):-len("</script>")]
        _assert_no_literal_lt(inner, "RuntimeResult script inner")

    def test_xss_name_no_closing_script_in_inner(self):
        rr = self._make_rr(_XSS_MARKER)
        inner = rr.to_sessionstorage_script()[len("<script>"):-len("</script>")]
        assert "</script" not in inner.lower()

    def test_xss_name_roundtrip_via_double_parse(self):
        rr = self._make_rr(_XSS_MARKER)
        script = rr.to_sessionstorage_script()
        import re
        m = re.search(r'sessionStorage\.setItem\("lastRuntimeSummary",\s*(.*?)\);', script)
        assert m, "lastRuntimeSummary setItem not found"
        outer_json_str = m.group(1)
        inner_json_str = json.loads(outer_json_str)
        obj = json.loads(inner_json_str)
        assert obj["project_name"] == _XSS_MARKER

    def test_sessionStorage_keys_unchanged(self):
        rr = self._make_rr("Normal")
        script = rr.to_sessionstorage_script()
        assert "lastRuntimeSummary" in script
        assert "lastFinancialStatements" in script

    def test_payload_structure_preserved(self):
        rr = self._make_rr("Normal")
        script = rr.to_sessionstorage_script()
        import re
        m = re.search(r'sessionStorage\.setItem\("lastRuntimeSummary",\s*(.*?)\);', script)
        inner_json = json.loads(json.loads(m.group(1)))
        assert inner_json["project_name"] == "Normal"
        assert inner_json["kpi"] == 1.0


# ---------------------------------------------------------------------------
# G. Emitter-level tests -- _build_sessionstorage_save_tag()
# ---------------------------------------------------------------------------

class TestBuildSessionstorageTag:
    """Verify the security property via _build_sessionstorage_save_tag()."""

    def _make_ws(self):
        from unittest.mock import MagicMock
        ws = MagicMock()
        ws.active_scenario_id = ""
        ws.active_scenario_name = _XSS_MARKER
        return ws

    def _call(self, runtime_summary=None, financial_statements=None):
        from app.services.run_service import _build_sessionstorage_save_tag
        return _build_sessionstorage_save_tag(
            runtime_summary=runtime_summary or {"kpi": 1.0},
            runtime_origin="user_created",
            workspace_state=self._make_ws(),
            runtime_snapshot_id="snap-1",
            financial_statements=financial_statements,
        )

    def test_produces_script_block(self):
        tag = self._call()
        assert tag.startswith("<script>")
        assert tag.endswith("</script>")

    def test_xss_in_runtime_summary_no_literal_lt(self):
        tag = self._call(runtime_summary={"name": _XSS_MARKER})
        inner = tag[len("<script>"):-len("</script>")]
        _assert_no_literal_lt(inner, "_build_sessionstorage_save_tag runtime_summary")

    def test_xss_in_financial_statements_no_literal_lt(self):
        tag = self._call(financial_statements={"project_name": _XSS_MARKER})
        inner = tag[len("<script>"):-len("</script>")]
        _assert_no_literal_lt(inner, "_build_sessionstorage_save_tag financial_statements")

    def test_xss_in_workspace_meta_no_literal_lt(self):
        """active_scenario_name is user-controlled — must be escaped in applyWorkspaceStateMeta."""
        tag = self._call()
        inner = tag[len("<script>"):-len("</script>")]
        _assert_no_literal_lt(inner, "_build_sessionstorage_save_tag workspace meta")

    def test_xss_in_runtime_summary_roundtrip(self):
        import re
        tag = self._call(runtime_summary={"name": _XSS_MARKER})
        m = re.search(r'sessionStorage\.setItem\("lastRuntimeSummary",\s*(.*?)\);', tag)
        assert m
        obj = json.loads(json.loads(m.group(1)))
        assert obj["name"] == _XSS_MARKER

    def test_no_closing_script_sequence(self):
        tag = self._call(runtime_summary={"name": _XSS_MARKER})
        inner = tag[len("<script>"):-len("</script>")]
        assert "</script" not in inner.lower()
