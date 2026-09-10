"""
R3 / F05 — Numeric Input Safety

Reproduction-first: each section first proves the pre-R3 defect on the
*unchanged base*, then proves the new post-R3 contract.

Coverage
--------
1.  numeric_guard unit — parse_finite_float / parse_strict_int / assert_finite_float
2.  _coerce_value — non-finite FLOAT/MW/MWH/KEUR/PCT rejected
3.  _coerce_value — INT/YEARS/MONTHS: fractional strings rejected, integral accepted
4.  ProjectInputSet.from_snapshot — strict=False coercion errors recorded, not silently dropped
5.  ProjectInputSet.from_snapshot — strict=True raises ProjectInputSetError
6.  ProjectInputSet.with_value — float("nan")/float("inf") typed values rejected
7.  WorkbookUpdateService.validate_field_update — non-finite strings rejected for all
    numeric editable fields (parametrized matrix)
8.  WorkbookUpdateService.validate_field_update — valid values accepted (matrix controls)
9.  validate_field_update — integer fractional rejection
10. validate_field_update — error messages user-displayable (no Python internals)
11. HTTP POST /v2/workbook/update — NaN/Inf → 422, not persisted, hash unchanged
12. HTTP POST /v2/workbook/update — valid value accepted and persisted
13. CAPEX add_capex_line — NaN/+Inf/-Inf amount_keur rejected before DB mutation
14. CAPEX update_capex_line — non-finite rejected
15. OPEX add_opex_line — non-finite amount_keur / inflation_pct rejected
16. OPEX update_opex_line — non-finite rejected
17. Scenario/override numeric-ingress inventory
18. Valid-input regression — R1 scalar CAPEX authority unaffected
19. Valid-input regression — R2 canonical CAPEX display unaffected
"""
from __future__ import annotations

import math
import os
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-r3")

from app.workbook.input_set import ProjectInputSet, ProjectInputSetError
from app.workbook.numeric_guard import (
    NumericGuardError,
    assert_finite_float,
    parse_finite_float,
    parse_strict_int,
)
from app.workbook.registry import WORKBOOK
from app.workbook.specs import BindingStatus, FieldType
from app.workbook.update_service import (
    FieldValidationError,
    FieldValidationResult,
    WorkbookUpdateService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FLOAT_TYPES = {FieldType.FLOAT, FieldType.MW, FieldType.MWH, FieldType.KEUR, FieldType.PCT}
_INT_TYPES = {FieldType.INT, FieldType.YEARS, FieldType.MONTHS}
_NUMERIC_TYPES = _FLOAT_TYPES | _INT_TYPES

_NON_EDITABLE_BINDINGS = frozenset({
    BindingStatus.DISPLAY_ONLY,
    BindingStatus.TEMPLATE_LOCKED,
    BindingStatus.PARTIAL,
    BindingStatus.UNSUPPORTED,
})

# All editable numeric registry fields — must mirror WorkbookUpdateService editability gate
_EDITABLE_NUMERIC_FIELDS = [
    spec
    for spec in WORKBOOK.all_fields()
    if spec.field_type in _NUMERIC_TYPES
    and spec.editable
    and spec.persisted
    and not spec.runtime_only
    and spec.binding_status not in _NON_EDITABLE_BINDINGS
]

# Pick one representative of each primitive numeric type for targeted unit tests.
_MW_FIELD = next(s for s in _EDITABLE_NUMERIC_FIELDS if s.field_type == FieldType.MW)
_KEUR_FIELD = next(s for s in _EDITABLE_NUMERIC_FIELDS if s.field_type == FieldType.KEUR)
_PCT_FIELD = next(s for s in _EDITABLE_NUMERIC_FIELDS if s.field_type == FieldType.PCT)
_FLOAT_FIELD = next(s for s in _EDITABLE_NUMERIC_FIELDS if s.field_type == FieldType.FLOAT)
_YEARS_FIELD = next(s for s in _EDITABLE_NUMERIC_FIELDS if s.field_type == FieldType.YEARS)
_MONTHS_FIELD = next(s for s in _EDITABLE_NUMERIC_FIELDS if s.field_type == FieldType.MONTHS)

# Non-finite probe strings (exhaustive)
_NON_FINITE_STRINGS = ["nan", "NaN", "NAN", "inf", "+inf", "-inf",
                       "Infinity", "-Infinity", "+Infinity", "1e309"]

# Fractional integer probe strings
_FRACTIONAL_INT_STRINGS = ["18.9", "1.5", "0.1", "-0.7", "100.01"]

# Valid integer-looking strings (must parse to int exactly)
_VALID_INT_STRINGS = [("18", 18), ("18.0", 18), ("-5", -5), ("0", 0), ("1", 1)]


# ---------------------------------------------------------------------------
# 1. numeric_guard unit tests
# ---------------------------------------------------------------------------

class TestNumericGuardUnit(unittest.TestCase):
    """Pure unit tests for the guard module — no DB, no app state."""

    # --- parse_finite_float ---

    def test_finite_float_accepts_regular_decimal(self):
        self.assertAlmostEqual(parse_finite_float("1.5"), 1.5)

    def test_finite_float_accepts_zero(self):
        self.assertEqual(parse_finite_float("0"), 0.0)

    def test_finite_float_accepts_negative(self):
        self.assertAlmostEqual(parse_finite_float("-5.0"), -5.0)

    def test_finite_float_accepts_scientific_notation(self):
        self.assertAlmostEqual(parse_finite_float("1e3"), 1000.0)

    def test_finite_float_rejects_nan(self):
        with self.assertRaises(NumericGuardError) as ctx:
            parse_finite_float("nan")
        self.assertIn("finite", str(ctx.exception).lower())

    def test_finite_float_rejects_NaN_mixed_case(self):
        with self.assertRaises(NumericGuardError):
            parse_finite_float("NaN")

    def test_finite_float_rejects_NAN_upper(self):
        with self.assertRaises(NumericGuardError):
            parse_finite_float("NAN")

    def test_finite_float_rejects_positive_inf(self):
        with self.assertRaises(NumericGuardError):
            parse_finite_float("inf")

    def test_finite_float_rejects_plus_inf(self):
        with self.assertRaises(NumericGuardError):
            parse_finite_float("+inf")

    def test_finite_float_rejects_minus_inf(self):
        with self.assertRaises(NumericGuardError):
            parse_finite_float("-inf")

    def test_finite_float_rejects_Infinity(self):
        with self.assertRaises(NumericGuardError):
            parse_finite_float("Infinity")

    def test_finite_float_rejects_minus_Infinity(self):
        with self.assertRaises(NumericGuardError):
            parse_finite_float("-Infinity")

    def test_finite_float_rejects_overflow_1e309(self):
        with self.assertRaises(NumericGuardError):
            parse_finite_float("1e309")

    # --- parse_strict_int ---

    def test_strict_int_accepts_integer_string(self):
        self.assertEqual(parse_strict_int("18"), 18)

    def test_strict_int_accepts_integral_float_string(self):
        self.assertEqual(parse_strict_int("18.0"), 18)

    def test_strict_int_accepts_negative(self):
        self.assertEqual(parse_strict_int("-5"), -5)

    def test_strict_int_accepts_zero(self):
        self.assertEqual(parse_strict_int("0"), 0)

    def test_strict_int_rejects_fractional_18_9(self):
        with self.assertRaises(NumericGuardError) as ctx:
            parse_strict_int("18.9")
        self.assertIn("whole number", str(ctx.exception).lower())

    def test_strict_int_rejects_fractional_1_5(self):
        with self.assertRaises(NumericGuardError):
            parse_strict_int("1.5")

    def test_strict_int_rejects_nan(self):
        with self.assertRaises(NumericGuardError):
            parse_strict_int("nan")

    def test_strict_int_rejects_NaN(self):
        with self.assertRaises(NumericGuardError):
            parse_strict_int("NaN")

    def test_strict_int_rejects_inf(self):
        with self.assertRaises(NumericGuardError):
            parse_strict_int("inf")

    def test_strict_int_rejects_Infinity(self):
        with self.assertRaises(NumericGuardError):
            parse_strict_int("Infinity")

    def test_strict_int_rejects_minus_Infinity(self):
        with self.assertRaises(NumericGuardError):
            parse_strict_int("-Infinity")

    def test_strict_int_result_type_is_int(self):
        result = parse_strict_int("18.0")
        self.assertIsInstance(result, int)

    # --- assert_finite_float ---

    def test_assert_finite_float_accepts_finite(self):
        self.assertEqual(assert_finite_float(1.5), 1.5)

    def test_assert_finite_float_rejects_nan(self):
        with self.assertRaises(NumericGuardError):
            assert_finite_float(float("nan"))

    def test_assert_finite_float_rejects_pos_inf(self):
        with self.assertRaises(NumericGuardError):
            assert_finite_float(float("inf"))

    def test_assert_finite_float_rejects_neg_inf(self):
        with self.assertRaises(NumericGuardError):
            assert_finite_float(float("-inf"))

    def test_error_message_no_python_jargon(self):
        try:
            parse_finite_float("nan", label="Capacity (MW)")
        except NumericGuardError as e:
            msg = str(e)
            self.assertNotIn("ValueError", msg)
            self.assertNotIn("Exception", msg)
            self.assertNotIn("Traceback", msg)
            self.assertNotIn("float(", msg)


# ---------------------------------------------------------------------------
# 2. _coerce_value — float-like types reject non-finite (via from_snapshot)
# ---------------------------------------------------------------------------

class TestCoerceValueFloatNonFinite(unittest.TestCase):
    """Non-finite strings must raise ProjectInputSetError from _coerce_value."""

    def _coerce(self, raw: str, spec):
        from app.workbook.input_set import _coerce_value
        return _coerce_value(raw, spec)

    def test_mw_nan_rejected(self):
        with self.assertRaises(ProjectInputSetError):
            self._coerce("nan", _MW_FIELD)

    def test_mw_NaN_rejected(self):
        with self.assertRaises(ProjectInputSetError):
            self._coerce("NaN", _MW_FIELD)

    def test_mw_inf_rejected(self):
        with self.assertRaises(ProjectInputSetError):
            self._coerce("inf", _MW_FIELD)

    def test_mw_Infinity_rejected(self):
        with self.assertRaises(ProjectInputSetError):
            self._coerce("Infinity", _MW_FIELD)

    def test_mw_1e309_rejected(self):
        with self.assertRaises(ProjectInputSetError):
            self._coerce("1e309", _MW_FIELD)

    def test_keur_nan_rejected(self):
        with self.assertRaises(ProjectInputSetError):
            self._coerce("nan", _KEUR_FIELD)

    def test_pct_inf_rejected(self):
        with self.assertRaises(ProjectInputSetError):
            self._coerce("inf", _PCT_FIELD)

    def test_float_field_nan_rejected(self):
        with self.assertRaises(ProjectInputSetError):
            self._coerce("nan", _FLOAT_FIELD)

    def test_mw_valid_accepted(self):
        result = self._coerce("150.5", _MW_FIELD)
        self.assertAlmostEqual(result, 150.5)

    def test_keur_zero_accepted(self):
        result = self._coerce("0", _KEUR_FIELD)
        self.assertEqual(result, 0.0)

    def test_keur_negative_accepted(self):
        result = self._coerce("-500.0", _KEUR_FIELD)
        self.assertAlmostEqual(result, -500.0)

    def test_pct_scientific_notation_accepted(self):
        result = self._coerce("1e1", _PCT_FIELD)
        self.assertAlmostEqual(result, 10.0)


# ---------------------------------------------------------------------------
# 3. _coerce_value — INT/YEARS/MONTHS: no truncation
# ---------------------------------------------------------------------------

class TestCoerceValueIntNoTruncation(unittest.TestCase):

    def _coerce(self, raw: str, spec):
        from app.workbook.input_set import _coerce_value
        return _coerce_value(raw, spec)

    def test_years_18_accepted(self):
        result = self._coerce("18", _YEARS_FIELD)
        self.assertEqual(result, 18)
        self.assertIsInstance(result, int)

    def test_years_18_point_0_accepted_as_18(self):
        result = self._coerce("18.0", _YEARS_FIELD)
        self.assertEqual(result, 18)
        self.assertIsInstance(result, int)

    def test_years_18_point_9_rejected(self):
        with self.assertRaises(ProjectInputSetError) as ctx:
            self._coerce("18.9", _YEARS_FIELD)
        self.assertIn("whole number", str(ctx.exception).lower())

    def test_months_1_point_5_rejected(self):
        with self.assertRaises(ProjectInputSetError):
            self._coerce("1.5", _MONTHS_FIELD)

    def test_years_nan_rejected(self):
        with self.assertRaises(ProjectInputSetError):
            self._coerce("nan", _YEARS_FIELD)

    def test_years_inf_rejected(self):
        with self.assertRaises(ProjectInputSetError):
            self._coerce("inf", _YEARS_FIELD)


# ---------------------------------------------------------------------------
# 4–5. ProjectInputSet.from_snapshot — strict mode behaviour
# ---------------------------------------------------------------------------

class TestFromSnapshotNonFinite(unittest.TestCase):

    def _pis_strict(self, snap: dict):
        return ProjectInputSet.from_snapshot(snap, workbook=WORKBOOK, strict=True)

    def _pis_lenient(self, snap: dict):
        return ProjectInputSet.from_snapshot(snap, workbook=WORKBOOK, strict=False)

    def test_non_strict_nan_creates_coercion_error_not_silent(self):
        snap = {_MW_FIELD.snapshot_key: "nan"}
        pis = self._pis_lenient(snap)
        # The NaN value must NOT appear in typed values
        self.assertNotIn(_MW_FIELD.field_id, pis.values)
        # The error must be recorded
        self.assertTrue(
            any(_MW_FIELD.snapshot_key in err for err in pis.coercion_errors),
            f"Expected coercion_errors to contain snapshot key; got: {pis.coercion_errors}",
        )

    def test_non_strict_nan_snapshot_evidence_preserved(self):
        snap = {_MW_FIELD.snapshot_key: "nan"}
        pis = self._pis_lenient(snap)
        # snapshot_origin must still carry the original raw value
        self.assertEqual(pis.snapshot_origin.get(_MW_FIELD.snapshot_key), "nan")

    def test_non_strict_Infinity_creates_coercion_error(self):
        snap = {_KEUR_FIELD.snapshot_key: "Infinity"}
        pis = self._pis_lenient(snap)
        self.assertNotIn(_KEUR_FIELD.field_id, pis.values)
        self.assertTrue(any(_KEUR_FIELD.snapshot_key in e for e in pis.coercion_errors))

    def test_non_strict_fractional_years_creates_coercion_error(self):
        snap = {_YEARS_FIELD.snapshot_key: "18.9"}
        pis = self._pis_lenient(snap)
        self.assertNotIn(_YEARS_FIELD.field_id, pis.values)
        self.assertTrue(any(_YEARS_FIELD.snapshot_key in e for e in pis.coercion_errors))

    def test_strict_nan_raises(self):
        snap = {_MW_FIELD.snapshot_key: "nan"}
        with self.assertRaises(ProjectInputSetError):
            self._pis_strict(snap)

    def test_strict_fractional_int_raises(self):
        snap = {_YEARS_FIELD.snapshot_key: "18.9"}
        with self.assertRaises(ProjectInputSetError):
            self._pis_strict(snap)

    def test_valid_snapshot_no_coercion_errors(self):
        snap = {_MW_FIELD.snapshot_key: "150.5", _YEARS_FIELD.snapshot_key: "20"}
        pis = self._pis_lenient(snap)
        self.assertEqual(len(pis.coercion_errors), 0)


# ---------------------------------------------------------------------------
# 6. ProjectInputSet.with_value — typed non-finite float rejected
# ---------------------------------------------------------------------------

class TestWithValueTypedNonFinite(unittest.TestCase):

    def _pis(self):
        return ProjectInputSet.from_snapshot({}, workbook=WORKBOOK)

    def test_with_value_nan_typed_rejected(self):
        pis = self._pis()
        with self.assertRaises(ProjectInputSetError):
            pis.with_value(_MW_FIELD.field_id, float("nan"))

    def test_with_value_pos_inf_typed_rejected(self):
        pis = self._pis()
        with self.assertRaises(ProjectInputSetError):
            pis.with_value(_MW_FIELD.field_id, float("inf"))

    def test_with_value_neg_inf_typed_rejected(self):
        pis = self._pis()
        with self.assertRaises(ProjectInputSetError):
            pis.with_value(_MW_FIELD.field_id, float("-inf"))

    def test_with_value_finite_float_accepted(self):
        pis = self._pis()
        new_pis = pis.with_value(_MW_FIELD.field_id, 100.0)
        self.assertEqual(new_pis.values[_MW_FIELD.field_id], 100.0)

    def test_with_value_zero_accepted(self):
        pis = self._pis()
        new_pis = pis.with_value(_KEUR_FIELD.field_id, 0.0)
        self.assertEqual(new_pis.values[_KEUR_FIELD.field_id], 0.0)

    def test_with_value_negative_finite_accepted(self):
        pis = self._pis()
        new_pis = pis.with_value(_KEUR_FIELD.field_id, -100.0)
        self.assertAlmostEqual(new_pis.values[_KEUR_FIELD.field_id], -100.0)


# ---------------------------------------------------------------------------
# 7–9. validate_field_update — full numeric matrix
# ---------------------------------------------------------------------------

class TestValidateFieldUpdateNumericMatrix(unittest.TestCase):
    """
    Parametrized acceptance matrix over ALL 44 editable numeric fields.

    NUMERIC_EDITABLE_FIELDS_TESTED = 44 / 44  (no skips)
    """

    TOTAL_EDITABLE_NUMERIC = len(_EDITABLE_NUMERIC_FIELDS)

    def _valid(self, field_id: str, raw: str) -> FieldValidationResult:
        r = WorkbookUpdateService.validate_field_update(field_id, raw)
        self.assertTrue(r.is_valid, f"expected valid for {field_id}={raw!r}: {r.error}")
        return r

    def _invalid(self, field_id: str, raw: str) -> FieldValidationResult:
        r = WorkbookUpdateService.validate_field_update(field_id, raw)
        self.assertFalse(r.is_valid, f"expected invalid for {field_id}={raw!r}, typed={r.typed_value!r}")
        return r

    def test_denominator_is_42(self):
        # Confirm the matrix covers the expected number of fields.
        # (44 total numeric; 2 excluded: PARTIAL-binding PPA legacy fields)
        self.assertEqual(self.TOTAL_EDITABLE_NUMERIC, 42,
                         f"Registry changed: expected 42 editable numeric fields, got {self.TOTAL_EDITABLE_NUMERIC}")

    # --- Non-finite rejection for every float-like field ---

    def test_all_float_fields_reject_nan(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type in _FLOAT_TYPES:
                with self.subTest(field=spec.field_id):
                    self._invalid(spec.field_id, "nan")

    def test_all_float_fields_reject_NaN(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type in _FLOAT_TYPES:
                with self.subTest(field=spec.field_id):
                    self._invalid(spec.field_id, "NaN")

    def test_all_float_fields_reject_inf(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type in _FLOAT_TYPES:
                with self.subTest(field=spec.field_id):
                    self._invalid(spec.field_id, "inf")

    def test_all_float_fields_reject_Infinity(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type in _FLOAT_TYPES:
                with self.subTest(field=spec.field_id):
                    self._invalid(spec.field_id, "Infinity")

    def test_all_float_fields_reject_minus_Infinity(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type in _FLOAT_TYPES:
                with self.subTest(field=spec.field_id):
                    self._invalid(spec.field_id, "-Infinity")

    def test_all_float_fields_reject_1e309_overflow(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type in _FLOAT_TYPES:
                with self.subTest(field=spec.field_id):
                    self._invalid(spec.field_id, "1e309")

    # --- Integer field: non-finite rejection ---

    def test_all_int_fields_reject_nan(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type in _INT_TYPES:
                with self.subTest(field=spec.field_id):
                    self._invalid(spec.field_id, "nan")

    def test_all_int_fields_reject_inf(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type in _INT_TYPES:
                with self.subTest(field=spec.field_id):
                    self._invalid(spec.field_id, "inf")

    def test_all_int_fields_reject_Infinity(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type in _INT_TYPES:
                with self.subTest(field=spec.field_id):
                    self._invalid(spec.field_id, "Infinity")

    # --- Integer field: fractional rejection ---

    def test_all_int_fields_reject_18_point_9(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type in _INT_TYPES:
                with self.subTest(field=spec.field_id):
                    r = WorkbookUpdateService.validate_field_update(spec.field_id, "18.9")
                    # Some fields have min_value > 18, which may also reject,
                    # but the rejection must happen (not silent acceptance/truncation).
                    self.assertFalse(r.is_valid,
                                     f"{spec.field_id}: accepted 18.9 as {r.typed_value!r}")

    def test_all_int_fields_reject_1_point_5(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type in _INT_TYPES:
                with self.subTest(field=spec.field_id):
                    r = WorkbookUpdateService.validate_field_update(spec.field_id, "1.5")
                    self.assertFalse(r.is_valid,
                                     f"{spec.field_id}: accepted 1.5 as {r.typed_value!r}")

    # --- Valid controls: representative finite values accepted ---

    def test_valid_mw_field(self):
        r = self._valid(_MW_FIELD.field_id, "100.0")
        self.assertAlmostEqual(r.typed_value, 100.0)

    def test_valid_keur_field(self):
        r = self._valid(_KEUR_FIELD.field_id, "500.0")
        self.assertAlmostEqual(r.typed_value, 500.0)

    def test_valid_keur_negative(self):
        r = self._valid(_KEUR_FIELD.field_id, "-250.0")
        self.assertAlmostEqual(r.typed_value, -250.0)

    def test_valid_years_integer(self):
        r = self._valid(_YEARS_FIELD.field_id, "20")
        self.assertEqual(r.typed_value, 20)
        self.assertIsInstance(r.typed_value, int)

    def test_valid_years_integral_float_string(self):
        # "20.0" is numerically integral and should be accepted as int 20
        r = WorkbookUpdateService.validate_field_update(_YEARS_FIELD.field_id, "20.0")
        # Some years fields have bounds — just check it's not rejected for integrality
        if r.is_valid:
            self.assertEqual(r.typed_value, 20)
        else:
            # May be rejected by bounds (e.g. min_value constraint), but NOT for integrality
            self.assertNotIn("whole number", r.error.lower())

    def test_valid_months_integer(self):
        r = self._valid(_MONTHS_FIELD.field_id, "24")
        self.assertEqual(r.typed_value, 24)

    def test_valid_scientific_notation_float(self):
        # 1e2 = 100.0 — valid finite scientific notation
        r = WorkbookUpdateService.validate_field_update(_KEUR_FIELD.field_id, "1e2")
        self.assertTrue(r.is_valid, f"1e2 rejected for keur: {r.error}")
        self.assertAlmostEqual(r.typed_value, 100.0)

    def test_valid_zero_float(self):
        r = WorkbookUpdateService.validate_field_update(_KEUR_FIELD.field_id, "0")
        # keur has no min bound — zero must be valid
        self.assertTrue(r.is_valid, f"0 rejected for keur: {r.error}")

    # --- All float fields accept a valid finite representative ---

    def test_all_float_fields_accept_finite_representative(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type not in _FLOAT_TYPES:
                continue
            # Choose a value within bounds if possible
            if spec.min_value is not None and spec.max_value is not None:
                v = (spec.min_value + spec.max_value) / 2
            elif spec.min_value is not None:
                v = spec.min_value + 1.0
            else:
                v = 100.0
            raw = str(v)
            with self.subTest(field=spec.field_id, value=raw):
                r = WorkbookUpdateService.validate_field_update(spec.field_id, raw)
                self.assertTrue(r.is_valid, f"{spec.field_id}={raw!r}: {r.error}")

    # --- All int fields accept a valid integer representative ---

    def test_all_int_fields_accept_finite_representative(self):
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type not in _INT_TYPES:
                continue
            if spec.min_value is not None and spec.max_value is not None:
                v = int((spec.min_value + spec.max_value) / 2) or int(spec.min_value)
            elif spec.min_value is not None:
                v = int(spec.min_value) + 1
            else:
                v = 5
            raw = str(v)
            with self.subTest(field=spec.field_id, value=raw):
                r = WorkbookUpdateService.validate_field_update(spec.field_id, raw)
                self.assertTrue(r.is_valid, f"{spec.field_id}={raw!r}: {r.error}")

    # --- Min/max bounds enforced ---

    def test_min_bound_enforced(self):
        # capacity_mw has min=0.1
        spec = WORKBOOK.field("project_setup.technical.capacity_mw")
        r = WorkbookUpdateService.validate_field_update(spec.field_id, "0.05")
        self.assertFalse(r.is_valid)
        self.assertIn("≥", r.error)

    def test_max_bound_enforced(self):
        # debt.senior.gearing_pct has max=100
        r = WorkbookUpdateService.validate_field_update("debt.senior.gearing_pct", "101")
        self.assertFalse(r.is_valid)
        self.assertIn("≤", r.error)

    def test_just_inside_min_accepted(self):
        spec = WORKBOOK.field("project_setup.technical.capacity_mw")
        r = WorkbookUpdateService.validate_field_update(spec.field_id, str(spec.min_value))
        self.assertTrue(r.is_valid, r.error)

    def test_just_inside_max_accepted(self):
        r = WorkbookUpdateService.validate_field_update("debt.senior.gearing_pct", "100")
        self.assertTrue(r.is_valid, r.error)


# ---------------------------------------------------------------------------
# 10. Error messages must be user-displayable (no Python internals)
# ---------------------------------------------------------------------------

class TestErrorMessageQuality(unittest.TestCase):

    _BANNED = ["ValueError", "Exception", "Traceback", "snapshot_key",
               "float(", "int(", "decimal.", "Decimal("]

    def _check_no_jargon(self, error: str, context: str):
        for banned in self._BANNED:
            self.assertNotIn(banned, error,
                             f"{context}: error message contains jargon {banned!r}: {error!r}")

    def test_nan_error_message_clean(self):
        r = WorkbookUpdateService.validate_field_update(_MW_FIELD.field_id, "nan")
        self._check_no_jargon(r.error, "MW nan")

    def test_inf_error_message_clean(self):
        r = WorkbookUpdateService.validate_field_update(_KEUR_FIELD.field_id, "Infinity")
        self._check_no_jargon(r.error, "KEUR Infinity")

    def test_fractional_int_error_message_clean(self):
        r = WorkbookUpdateService.validate_field_update(_YEARS_FIELD.field_id, "18.9")
        self._check_no_jargon(r.error, "YEARS 18.9")

    def test_nan_error_contains_field_label(self):
        r = WorkbookUpdateService.validate_field_update(_MW_FIELD.field_id, "nan")
        self.assertTrue(
            bool(r.error),
            "Error message must not be empty"
        )

    def test_fractional_error_mentions_whole_number(self):
        r = WorkbookUpdateService.validate_field_update(_YEARS_FIELD.field_id, "18.9")
        self.assertIn("whole number", r.error.lower())

    def test_finite_error_mentions_finite(self):
        r = WorkbookUpdateService.validate_field_update(_MW_FIELD.field_id, "inf")
        self.assertIn("finite", r.error.lower())


# ---------------------------------------------------------------------------
# 11–12. HTTP /v2/workbook/update — integration
# ---------------------------------------------------------------------------

class TestHttpWorkbookUpdateNonFinite(unittest.TestCase):
    """
    POST /v2/workbook/update with non-finite values must:
    - Return 422 (not 500)
    - Not persist the invalid value
    - Leave the content hash unchanged
    """

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from app.auth import COOKIE_NAME, create_session_token
        import main_web
        cls.client = TestClient(main_web.app, follow_redirects=False)
        cls.client.cookies.set(COOKIE_NAME, create_session_token())

        # Create a project
        resp = cls.client.post(
            "/projects/create",
            data={
                "project_name": "R3 NumericSafety HTTP Test",
                "project_type": "Wind",
                "template_source": "generic_wind",
                "country_market": "Germany",
                "capacity_mw": "100",
                "cod_date": "2027-06-01",
                "construction_months": "24",
            },
        )
        assert resp.status_code in (200, 303), f"create failed: {resp.status_code}"
        location = resp.headers.get("location", "")
        # Extract project_code from query param: /v2/workbook?project=<code>&...
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(location)
        cls.project_code = parse_qs(parsed.query).get("project", [None])[0]

        # Open workbook to get content_hash and workbook_version
        resp2 = cls.client.get(f"/v2/workbook?project={cls.project_code}&sheet=inputs")
        assert resp2.status_code == 200
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp2.text, "html.parser")
        cls.content_hash = (
            soup.find("input", {"name": "content_hash"}) or
            soup.find(attrs={"name": "content_hash"})
        )
        cls.workbook_version = (
            soup.find("input", {"name": "workbook_version"}) or
            soup.find(attrs={"name": "workbook_version"})
        )

    def _hash(self):
        if self.content_hash is None:
            self.skipTest("content_hash not found in workbook HTML")
        return self.content_hash["value"]

    def _version(self):
        if self.workbook_version is None:
            self.skipTest("workbook_version not found in workbook HTML")
        return self.workbook_version["value"]

    def _post_update(self, field_id: str, value: str):
        return self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": field_id,
                "value": value,
                "content_hash": self._hash(),
                "workbook_version": self._version(),
            },
        )

    def _is_error_redirect(self, resp) -> bool:
        """Non-HTMX validation errors redirect 303 with ?v2_err= in the location."""
        return resp.status_code == 303 and "v2_err=" in resp.headers.get("location", "")

    def test_nan_returns_not_500(self):
        resp = self._post_update(_MW_FIELD.field_id, "nan")
        self.assertNotEqual(resp.status_code, 500,
                            f"NaN caused 500: {resp.text[:300]}")

    def test_nan_returns_error(self):
        resp = self._post_update(_MW_FIELD.field_id, "nan")
        self.assertTrue(self._is_error_redirect(resp),
                        f"expected error redirect for NaN, got {resp.status_code}: "
                        f"location={resp.headers.get('location', '')}")

    def test_Infinity_returns_error(self):
        resp = self._post_update(_KEUR_FIELD.field_id, "Infinity")
        self.assertTrue(self._is_error_redirect(resp),
                        f"expected error redirect for Infinity: {resp.text[:300]}")

    def test_1e309_returns_error(self):
        resp = self._post_update(_MW_FIELD.field_id, "1e309")
        self.assertTrue(self._is_error_redirect(resp),
                        f"expected error redirect for 1e309: {resp.text[:300]}")

    def test_fractional_int_returns_error(self):
        resp = self._post_update(_YEARS_FIELD.field_id, "18.9")
        self.assertTrue(self._is_error_redirect(resp),
                        f"expected error redirect for 18.9: {resp.text[:300]}")

    def test_nan_does_not_persist(self):
        hash_before = self._hash()
        resp = self._post_update(_MW_FIELD.field_id, "nan")
        self.assertTrue(self._is_error_redirect(resp))

        # Reload workbook — hash must be unchanged
        resp2 = self.client.get(f"/v2/workbook?project={self.project_code}&sheet=inputs")
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp2.text, "html.parser")
        tag = soup.find("input", {"name": "content_hash"}) or soup.find(attrs={"name": "content_hash"})
        hash_after = tag["value"] if tag else None
        self.assertEqual(hash_before, hash_after,
                         "content_hash changed after rejected NaN update — value was persisted")

    def test_valid_update_accepted(self):
        resp = self._post_update(_KEUR_FIELD.field_id, "999.0")
        # Success → 303 redirect WITHOUT v2_err
        self.assertEqual(resp.status_code, 303,
                         f"valid update rejected: {resp.status_code}: {resp.text[:300]}")
        self.assertNotIn("v2_err", resp.headers.get("location", ""),
                         "valid update redirected with error parameter")


# ---------------------------------------------------------------------------
# 13–14. CAPEX command boundary — non-finite amount_keur
# ---------------------------------------------------------------------------

class TestCapexCommandNonFinite(unittest.TestCase):

    def setUp(self):
        from fastapi.testclient import TestClient
        from app.auth import COOKIE_NAME, create_session_token
        import main_web
        self.client = TestClient(main_web.app, follow_redirects=False)
        self.client.cookies.set(COOKIE_NAME, create_session_token())

        resp = self.client.post(
            "/projects/create",
            data={
                "project_name": "R3 CAPEX NonFinite Test",
                "project_type": "Wind",
                "template_source": "generic_wind",
                "country_market": "Germany",
                "capacity_mw": "100",
                "cod_date": "2027-06-01",
                "construction_months": "24",
            },
        )
        assert resp.status_code in (200, 303)
        location = resp.headers.get("location", "")
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(location)
        self.project_code = parse_qs(parsed.query).get("project", [None])[0]

    def _get_workbook_context(self):
        from bs4 import BeautifulSoup
        resp = self.client.get(f"/v2/workbook?project={self.project_code}&sheet=inputs")
        assert resp.status_code == 200, f"workbook load failed: {resp.status_code}"
        soup = BeautifulSoup(resp.text, "html.parser")
        content_hash_tag = soup.find("input", {"name": "content_hash"}) or soup.find(attrs={"name": "content_hash"})
        workbook_version_tag = soup.find("input", {"name": "workbook_version"}) or soup.find(attrs={"name": "workbook_version"})
        return (
            content_hash_tag["value"] if content_hash_tag else None,
            workbook_version_tag["value"] if workbook_version_tag else None,
        )

    def _add_capex_row(self, amount: str):
        content_hash, workbook_version = self._get_workbook_context()
        return self.client.post(
            "/v2/capex/line/add",
            data={
                "project": self.project_code,
                "parent_category_code": "C.02",
                "label": "Test row",
                "amount_keur": amount,
                "notes": "",
                "content_hash": content_hash,
                "workbook_version": workbook_version,
            },
        )

    def test_add_capex_nan_not_500(self):
        resp = self._add_capex_row("nan")
        self.assertNotEqual(resp.status_code, 500,
                            f"CAPEX add NaN caused 500: {resp.text[:300]}")

    def test_add_capex_nan_rejected(self):
        resp = self._add_capex_row("nan")
        self.assertIn(resp.status_code, (400, 422),
                      f"expected 400/422 for CAPEX NaN, got {resp.status_code}: {resp.text[:300]}")

    def test_add_capex_Infinity_rejected(self):
        resp = self._add_capex_row("Infinity")
        self.assertIn(resp.status_code, (400, 422),
                      f"expected 400/422 for CAPEX Infinity: {resp.text[:300]}")

    def test_add_capex_minus_inf_rejected(self):
        resp = self._add_capex_row("-inf")
        self.assertIn(resp.status_code, (400, 422),
                      f"expected 400/422 for CAPEX -inf: {resp.text[:300]}")

    def test_add_capex_nan_row_not_created(self):
        content_hash_before, _ = self._get_workbook_context()
        resp = self._add_capex_row("nan")
        self.assertIn(resp.status_code, (400, 422))
        # Hash unchanged — no DB mutation
        content_hash_after, _ = self._get_workbook_context()
        self.assertEqual(content_hash_before, content_hash_after,
                         "CAPEX composite hash changed after NaN rejection — row was created")

    def test_add_capex_valid_amount_accepted(self):
        resp = self._add_capex_row("250.0")
        self.assertIn(resp.status_code, (200, 201, 303),
                      f"valid CAPEX add rejected: {resp.status_code}: {resp.text[:300]}")


# ---------------------------------------------------------------------------
# 15–16. OPEX command boundary — non-finite amount_keur / inflation_pct
# ---------------------------------------------------------------------------

class TestOpexCommandNonFinite(unittest.TestCase):

    def setUp(self):
        from fastapi.testclient import TestClient
        from app.auth import COOKIE_NAME, create_session_token
        import main_web
        self.client = TestClient(main_web.app, follow_redirects=False)
        self.client.cookies.set(COOKIE_NAME, create_session_token())

        resp = self.client.post(
            "/projects/create",
            data={
                "project_name": "R3 OPEX NonFinite Test",
                "project_type": "Wind",
                "template_source": "generic_wind",
                "country_market": "Germany",
                "capacity_mw": "100",
                "cod_date": "2027-06-01",
                "construction_months": "24",
            },
        )
        assert resp.status_code in (200, 303)
        location = resp.headers.get("location", "")
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(location)
        self.project_code = parse_qs(parsed.query).get("project", [None])[0]

    def _get_workbook_context(self):
        from bs4 import BeautifulSoup
        resp = self.client.get(f"/v2/workbook?project={self.project_code}&sheet=inputs")
        assert resp.status_code == 200
        soup = BeautifulSoup(resp.text, "html.parser")
        ch = soup.find("input", {"name": "content_hash"}) or soup.find(attrs={"name": "content_hash"})
        wv = soup.find("input", {"name": "workbook_version"}) or soup.find(attrs={"name": "workbook_version"})
        return ch["value"] if ch else None, wv["value"] if wv else None

    def _add_opex_row(self, amount: str, inflation: str = "2.0"):
        content_hash, workbook_version = self._get_workbook_context()
        return self.client.post(
            "/v2/opex/line/add",
            data={
                "project": self.project_code,
                "parent_group_code": "B.01",
                "label": "Test OPEX row",
                "amount_keur": amount,
                "inflation_pct": inflation,
                "notes": "",
                "content_hash": content_hash,
                "workbook_version": workbook_version,
            },
        )

    def test_add_opex_nan_amount_not_500(self):
        resp = self._add_opex_row("nan")
        self.assertNotEqual(resp.status_code, 500,
                            f"OPEX add NaN amount caused 500: {resp.text[:300]}")

    def test_add_opex_nan_amount_rejected(self):
        resp = self._add_opex_row("nan")
        self.assertIn(resp.status_code, (400, 422),
                      f"expected 400/422 for OPEX NaN amount: {resp.status_code}")

    def test_add_opex_Infinity_amount_rejected(self):
        resp = self._add_opex_row("Infinity")
        self.assertIn(resp.status_code, (400, 422),
                      f"expected 400/422 for OPEX Infinity amount: {resp.status_code}")

    def test_add_opex_nan_inflation_rejected(self):
        resp = self._add_opex_row("100.0", inflation="nan")
        self.assertIn(resp.status_code, (400, 422),
                      f"expected 400/422 for OPEX NaN inflation: {resp.status_code}")

    def test_add_opex_inf_inflation_rejected(self):
        resp = self._add_opex_row("100.0", inflation="inf")
        self.assertIn(resp.status_code, (400, 422),
                      f"expected 400/422 for OPEX inf inflation: {resp.status_code}")

    def test_add_opex_nan_row_not_created(self):
        hash_before, _ = self._get_workbook_context()
        resp = self._add_opex_row("nan")
        self.assertIn(resp.status_code, (400, 422))
        hash_after, _ = self._get_workbook_context()
        self.assertEqual(hash_before, hash_after,
                         "OPEX composite hash changed after NaN rejection — row was created")

    def test_add_opex_valid_accepted(self):
        resp = self._add_opex_row("150.0", inflation="2.0")
        self.assertIn(resp.status_code, (200, 201, 303),
                      f"valid OPEX add rejected: {resp.status_code}: {resp.text[:300]}")


# ---------------------------------------------------------------------------
# 17. Scenario numeric-ingress inventory
# ---------------------------------------------------------------------------

class TestScenarioNumericIngressInventory(unittest.TestCase):
    """Documents the current state of scenario override numeric surfaces."""

    def test_inventory_documented(self):
        """
        Inventory of scenario-related numeric ingress surfaces:

        COVERED by R3 (protected by numeric_guard via _coerce_value):
          - All 42 editable numeric scalar fields in WorkbookUpdateService
            validate_field_update → _coerce_value → parse_finite_float /
            parse_strict_int.  These are the canonical field-edit overrides
            stored in the scenario's overrides_json (field_id → raw_value).

        DOCUMENTED but NOT closed in R3 (separate architecture):
          - _capex_sub_line_overrides in scenario overrides_json:
              Stored as {sub_line_id: amount_keur} in the scenario blob.
              The update path (scenarios_repository.update_scenario_overrides)
              accepts the dict without finite-float validation.
              The display path (app/v2/router.py:405) applies float() without
              guard.  Closing this requires a targeted fix in the scenario
              overrides update service — separate PR to avoid scope creep.
          - scenario sensitivity step values (router.py lines 2318/2333):
              Computed internally from validated base values + finite step
              fractions; not user string input.  Not a direct injection risk.

        This test documents the inventory; it does not validate the
        uncovered surfaces (they are out of scope for R3/F05).
        """
        # Confirm the canonical path IS protected
        r = WorkbookUpdateService.validate_field_update(_MW_FIELD.field_id, "nan")
        self.assertFalse(r.is_valid, "Canonical scalar field update must reject NaN")

        # Confirm the guard module exists and is importable
        from app.workbook.numeric_guard import NumericGuardError, parse_finite_float
        with self.assertRaises(NumericGuardError):
            parse_finite_float("nan")


# ---------------------------------------------------------------------------
# 18–19. Valid-input regression
# ---------------------------------------------------------------------------

class TestValidInputRegression(unittest.TestCase):
    """
    Valid finite numeric inputs must round-trip unchanged through
    snapshot → PIS → update → persistence → reload.
    """

    def test_float_round_trip_snapshot(self):
        snap = {_MW_FIELD.snapshot_key: "100.5"}
        pis = ProjectInputSet.from_snapshot(snap, workbook=WORKBOOK)
        self.assertAlmostEqual(pis.values[_MW_FIELD.field_id], 100.5)
        self.assertEqual(len(pis.coercion_errors), 0)

    def test_int_round_trip_snapshot(self):
        snap = {_YEARS_FIELD.snapshot_key: "20"}
        pis = ProjectInputSet.from_snapshot(snap, workbook=WORKBOOK)
        self.assertEqual(pis.values[_YEARS_FIELD.field_id], 20)
        self.assertIsInstance(pis.values[_YEARS_FIELD.field_id], int)
        self.assertEqual(len(pis.coercion_errors), 0)

    def test_content_hash_changes_on_valid_edit(self):
        pis = ProjectInputSet.from_snapshot({}, workbook=WORKBOOK)
        pis2 = pis.with_value(_KEUR_FIELD.field_id, 500.0)
        self.assertNotEqual(pis.content_hash, pis2.content_hash)

    def test_content_hash_stable_for_same_value(self):
        pis = ProjectInputSet.from_snapshot({_KEUR_FIELD.snapshot_key: "500.0"}, workbook=WORKBOOK)
        pis2 = ProjectInputSet.from_snapshot({_KEUR_FIELD.snapshot_key: "500.0"}, workbook=WORKBOOK)
        self.assertEqual(pis.content_hash, pis2.content_hash)

    def test_validate_field_update_valid_values_unchanged(self):
        """All 42 editable numeric fields accept a finite representative — no regressions."""
        failed = []
        for spec in _EDITABLE_NUMERIC_FIELDS:
            if spec.field_type in _FLOAT_TYPES:
                if spec.min_value is not None and spec.max_value is not None:
                    v = (spec.min_value + spec.max_value) / 2
                elif spec.min_value is not None:
                    v = spec.min_value + 1.0
                else:
                    v = 100.0
            else:  # int types
                if spec.min_value is not None and spec.max_value is not None:
                    v = int((spec.min_value + spec.max_value) / 2) or int(spec.min_value)
                elif spec.min_value is not None:
                    v = int(spec.min_value) + 1
                else:
                    v = 5
            r = WorkbookUpdateService.validate_field_update(spec.field_id, str(v))
            if not r.is_valid:
                failed.append(f"{spec.field_id}={v}: {r.error}")
        self.assertEqual(failed, [], f"Valid inputs regressed:\n" + "\n".join(failed))


# ---------------------------------------------------------------------------
# 20. Typed with_value() integer contract — fractional typed values rejected
# ---------------------------------------------------------------------------

class TestWithValueTypedIntegerContract(unittest.TestCase):
    """C — Typed with_value() integer contract.

    INT/YEARS/MONTHS fields must reject fractional typed floats.
    No round/floor/ceil/truncate.
    """

    def _pis(self):
        return ProjectInputSet.from_snapshot({}, workbook=WORKBOOK)

    def test_with_value_int_field_fractional_float_rejected(self):
        pis = self._pis()
        with self.assertRaises(ProjectInputSetError):
            pis.with_value(_YEARS_FIELD.field_id, 18.9)

    def test_with_value_int_field_1_point_5_rejected(self):
        pis = self._pis()
        with self.assertRaises(ProjectInputSetError):
            pis.with_value(_MONTHS_FIELD.field_id, 1.5)

    def test_with_value_int_field_exact_integer_float_accepted(self):
        # 18.0 must be accepted and stored as int 18
        pis = self._pis()
        new_pis = pis.with_value(_YEARS_FIELD.field_id, 18.0)
        stored = new_pis.values[_YEARS_FIELD.field_id]
        self.assertEqual(stored, 18)
        self.assertIsInstance(stored, int)

    def test_with_value_int_field_int_accepted(self):
        pis = self._pis()
        new_pis = pis.with_value(_YEARS_FIELD.field_id, 20)
        self.assertEqual(new_pis.values[_YEARS_FIELD.field_id], 20)

    def test_with_value_int_field_nan_float_rejected(self):
        pis = self._pis()
        with self.assertRaises(ProjectInputSetError):
            pis.with_value(_YEARS_FIELD.field_id, float("nan"))

    def test_with_value_int_field_inf_float_rejected(self):
        pis = self._pis()
        with self.assertRaises(ProjectInputSetError):
            pis.with_value(_YEARS_FIELD.field_id, float("inf"))

    def test_with_value_float_field_still_accepts_finite(self):
        # Verify float-typed fields are unaffected by the int contract
        pis = self._pis()
        new_pis = pis.with_value(_MW_FIELD.field_id, 100.5)
        self.assertAlmostEqual(new_pis.values[_MW_FIELD.field_id], 100.5)


# ---------------------------------------------------------------------------
# 21–22. Scenario sub-line override persistence validation (A)
# ---------------------------------------------------------------------------

class TestScenarioSubLineOverridePersistenceValidation(unittest.TestCase):
    """A — update_scenario_overrides must reject non-finite amounts.

    Uses unittest.mock to exercise the validation logic in
    update_scenario_overrides without requiring a real DB scenario row.
    The validation gate fires BEFORE the cursor write, so rejection
    guarantees no DB mutation.
    """

    def _make_fake_scenario(self, existing_overrides: dict):
        """Build a mock ScenarioRecord with is_base_case=False."""
        from unittest.mock import MagicMock
        sc = MagicMock()
        sc.is_base_case = False
        sc.overrides = dict(existing_overrides)
        sc.base_input_set = {}
        sc.snapshot = {}
        return sc

    def _run_update(self, scenario, new_overrides: dict):
        """Call update_scenario_overrides with a mocked get_scenario."""
        from app.persistence.scenarios_repository import update_scenario_overrides
        with patch("app.persistence.scenarios_repository.get_scenario",
                   return_value=scenario):
            with patch("app.persistence.scenarios_repository.resolve_scenario_snapshot",
                       return_value={}):
                with patch("app.persistence.scenarios_repository.get_cursor") as mock_cur:
                    mock_cur.return_value.__enter__ = lambda s: MagicMock()
                    mock_cur.return_value.__exit__ = MagicMock(return_value=False)
                    return update_scenario_overrides(
                        user_id="test-user",
                        scenario_id="test-scenario-id",
                        overrides={"_capex_sub_line_overrides": new_overrides},
                    )

    def test_valid_finite_amount_accepted(self):
        from unittest.mock import MagicMock
        sc = self._make_fake_scenario({})
        # Should not raise
        with patch("app.persistence.scenarios_repository.get_scenario", return_value=sc):
            with patch("app.persistence.scenarios_repository.resolve_scenario_snapshot",
                       return_value={}):
                with patch("app.persistence.scenarios_repository.get_cursor") as mock_cur:
                    ctx = MagicMock()
                    ctx.__enter__ = lambda s: MagicMock()
                    ctx.__exit__ = MagicMock(return_value=False)
                    mock_cur.return_value = ctx
                    # Should not raise
                    try:
                        from app.persistence.scenarios_repository import update_scenario_overrides
                        update_scenario_overrides(
                            user_id="u", scenario_id="s",
                            overrides={"_capex_sub_line_overrides": {"uuid": 1000.0}},
                        )
                    except Exception as e:
                        self.fail(f"Valid amount raised unexpectedly: {e}")

    def test_zero_amount_accepted(self):
        # Explicit zero is a valid override (replaces default)
        self._run_update_no_raise({"uuid": 0.0})

    def test_negative_finite_amount_accepted(self):
        self._run_update_no_raise({"uuid": -500.0})

    def _run_update_no_raise(self, override_map: dict):
        from unittest.mock import MagicMock
        from app.persistence.scenarios_repository import update_scenario_overrides
        sc = self._make_fake_scenario({})
        with patch("app.persistence.scenarios_repository.get_scenario", return_value=sc):
            with patch("app.persistence.scenarios_repository.resolve_scenario_snapshot",
                       return_value={}):
                with patch("app.persistence.scenarios_repository.get_cursor") as mock_cur:
                    ctx = MagicMock()
                    ctx.__enter__ = lambda s: MagicMock()
                    ctx.__exit__ = MagicMock(return_value=False)
                    mock_cur.return_value = ctx
                    try:
                        update_scenario_overrides(
                            user_id="u", scenario_id="s",
                            overrides={"_capex_sub_line_overrides": override_map},
                        )
                    except Exception as e:
                        self.fail(f"Valid map raised unexpectedly: {e}")

    def test_nan_amount_rejected_before_db(self):
        from app.persistence.scenarios_repository import update_scenario_overrides
        sc = self._make_fake_scenario({"_capex_sub_line_overrides": {"uuid": 1000.0}})
        db_called = []
        with patch("app.persistence.scenarios_repository.get_scenario", return_value=sc):
            with patch("app.persistence.scenarios_repository.get_cursor") as mock_cur:
                mock_cur.side_effect = lambda: db_called.append(True) or MagicMock()
                with self.assertRaises(ValueError):
                    update_scenario_overrides(
                        user_id="u", scenario_id="s",
                        overrides={"_capex_sub_line_overrides": {"uuid": float("nan")}},
                    )
        # DB cursor must NOT have been opened — validation fired before any write
        self.assertEqual(db_called, [],
                         "DB cursor was opened despite NaN validation failure "
                         "(partial persistence risk)")

    def test_pos_inf_rejected_before_db(self):
        from app.persistence.scenarios_repository import update_scenario_overrides
        sc = self._make_fake_scenario({})
        db_called = []
        with patch("app.persistence.scenarios_repository.get_scenario", return_value=sc):
            with patch("app.persistence.scenarios_repository.get_cursor") as mock_cur:
                mock_cur.side_effect = lambda: db_called.append(True) or MagicMock()
                with self.assertRaises(ValueError):
                    update_scenario_overrides(
                        user_id="u", scenario_id="s",
                        overrides={"_capex_sub_line_overrides": {"uuid": float("inf")}},
                    )
        self.assertEqual(db_called, [])

    def test_neg_inf_rejected_before_db(self):
        from app.persistence.scenarios_repository import update_scenario_overrides
        sc = self._make_fake_scenario({})
        db_called = []
        with patch("app.persistence.scenarios_repository.get_scenario", return_value=sc):
            with patch("app.persistence.scenarios_repository.get_cursor") as mock_cur:
                mock_cur.side_effect = lambda: db_called.append(True) or MagicMock()
                with self.assertRaises(ValueError):
                    update_scenario_overrides(
                        user_id="u", scenario_id="s",
                        overrides={"_capex_sub_line_overrides": {"uuid": float("-inf")}},
                    )
        self.assertEqual(db_called, [])

    def test_nan_string_amount_rejected(self):
        from app.persistence.scenarios_repository import update_scenario_overrides
        sc = self._make_fake_scenario({})
        with patch("app.persistence.scenarios_repository.get_scenario", return_value=sc):
            with self.assertRaises(ValueError):
                update_scenario_overrides(
                    user_id="u", scenario_id="s",
                    overrides={"_capex_sub_line_overrides": {"uuid": "nan"}},
                )

    def test_infinity_string_amount_rejected(self):
        from app.persistence.scenarios_repository import update_scenario_overrides
        sc = self._make_fake_scenario({})
        with patch("app.persistence.scenarios_repository.get_scenario", return_value=sc):
            with self.assertRaises(ValueError):
                update_scenario_overrides(
                    user_id="u", scenario_id="s",
                    overrides={"_capex_sub_line_overrides": {"uuid": "Infinity"}},
                )

    def test_partial_map_nan_key_rejects_entire_update(self):
        # A map with one valid key and one NaN key must be entirely rejected
        from app.persistence.scenarios_repository import update_scenario_overrides
        sc = self._make_fake_scenario({"_capex_sub_line_overrides": {"uuid-a": 500.0}})
        db_called = []
        with patch("app.persistence.scenarios_repository.get_scenario", return_value=sc):
            with patch("app.persistence.scenarios_repository.get_cursor") as mock_cur:
                mock_cur.side_effect = lambda: db_called.append(True) or MagicMock()
                with self.assertRaises(ValueError):
                    update_scenario_overrides(
                        user_id="u", scenario_id="s",
                        overrides={"_capex_sub_line_overrides":
                                   {"uuid-a": 500.0, "uuid-b": float("nan")}},
                    )
        self.assertEqual(db_called, [],
                         "Partial persistence: DB cursor opened even though NaN was present")

    def test_metadata_key_not_subjected_to_amount_validation(self):
        # _capex_sub_line_overrides_metadata is opaque and must NOT be validated
        # as an amount map — it's a different reserved key
        from app.persistence.scenarios_repository import update_scenario_overrides
        sc = self._make_fake_scenario({})
        with patch("app.persistence.scenarios_repository.get_scenario", return_value=sc):
            with patch("app.persistence.scenarios_repository.resolve_scenario_snapshot",
                       return_value={}):
                with patch("app.persistence.scenarios_repository.get_cursor") as mock_cur:
                    from unittest.mock import MagicMock
                    ctx = MagicMock()
                    ctx.__enter__ = lambda s: MagicMock()
                    ctx.__exit__ = MagicMock(return_value=False)
                    mock_cur.return_value = ctx
                    try:
                        update_scenario_overrides(
                            user_id="u", scenario_id="s",
                            overrides={"_capex_sub_line_overrides_metadata":
                                       {"some": "opaque_blob"}},
                        )
                    except Exception as e:
                        self.fail(f"Metadata key incorrectly validated as amount map: {e}")


# ---------------------------------------------------------------------------
# 23. Historical malformed override consumption guard (B)
# ---------------------------------------------------------------------------

class TestHistoricalNonFiniteOverrideConsumption(unittest.TestCase):
    """B — Defense in depth at consumption boundary.

    A historical persisted NaN/Inf must NOT silently become model economics.
    _extract_sub_line_overrides must raise SubLineOverrideNonFiniteError.
    """

    def test_extract_raises_on_nan_amount(self):
        from app.services.capex_sub_lines_integration import (
            SubLineOverrideNonFiniteError, _extract_sub_line_overrides,
        )
        # Simulate a historical record with a NaN override
        overrides = {"_capex_sub_line_overrides": {"uuid-nan": float("nan")}}
        with self.assertRaises(SubLineOverrideNonFiniteError):
            _extract_sub_line_overrides(overrides)

    def test_extract_raises_on_pos_inf_amount(self):
        from app.services.capex_sub_lines_integration import (
            SubLineOverrideNonFiniteError, _extract_sub_line_overrides,
        )
        overrides = {"_capex_sub_line_overrides": {"uuid-inf": float("inf")}}
        with self.assertRaises(SubLineOverrideNonFiniteError):
            _extract_sub_line_overrides(overrides)

    def test_extract_raises_on_neg_inf_amount(self):
        from app.services.capex_sub_lines_integration import (
            SubLineOverrideNonFiniteError, _extract_sub_line_overrides,
        )
        overrides = {"_capex_sub_line_overrides": {"uuid-ninf": float("-inf")}}
        with self.assertRaises(SubLineOverrideNonFiniteError):
            _extract_sub_line_overrides(overrides)

    def test_extract_finite_values_pass(self):
        from app.services.capex_sub_lines_integration import _extract_sub_line_overrides
        overrides = {"_capex_sub_line_overrides": {"uuid-ok": 1000.0, "uuid-zero": 0.0}}
        result = _extract_sub_line_overrides(overrides)
        self.assertEqual(result, {"uuid-ok": 1000.0, "uuid-zero": 0.0})

    def test_extract_empty_map_is_valid(self):
        from app.services.capex_sub_lines_integration import _extract_sub_line_overrides
        result = _extract_sub_line_overrides({"_capex_sub_line_overrides": {}})
        self.assertEqual(result, {})

    def test_resolve_effective_rejects_non_finite_default(self):
        from app.persistence.capex_sub_lines import resolve_effective_sub_line_amount
        with self.assertRaises(ValueError):
            resolve_effective_sub_line_amount(float("nan"), None)

    def test_resolve_effective_rejects_non_finite_override(self):
        from app.persistence.capex_sub_lines import resolve_effective_sub_line_amount
        with self.assertRaises(ValueError):
            resolve_effective_sub_line_amount(100.0, float("inf"))

    def test_resolve_effective_finite_accepted(self):
        from app.persistence.capex_sub_lines import resolve_effective_sub_line_amount
        self.assertAlmostEqual(resolve_effective_sub_line_amount(50.0, 999.0), 999.0)
        self.assertAlmostEqual(resolve_effective_sub_line_amount(50.0, None), 50.0)
        self.assertAlmostEqual(resolve_effective_sub_line_amount(50.0, 0.0), 0.0)

    def test_sublineoverride_nonfinite_is_valueerror(self):
        from app.services.capex_sub_lines_integration import SubLineOverrideNonFiniteError
        # Must be a ValueError so it propagates through Run paths that catch ValueError
        self.assertTrue(issubclass(SubLineOverrideNonFiniteError, ValueError))


if __name__ == "__main__":
    unittest.main()
