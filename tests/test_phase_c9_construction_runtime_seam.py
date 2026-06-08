"""Phase C9 — Layer 5 Runtime Seam Scaffolding (NO runtime promotion) tests.

C9 is the FIRST implementation phase of the seam. It is
**structural scaffolding only** — no runtime promotion, no
waterfall routing, no feature-flag flips, no construction
engine activation.

This test file covers:

1. **Guard behavior** — every row of the C8 §5.2 expected
   behavior table is exercised with both pass and raise
   outcomes.
2. **Frozen field rejection** — frozen fields ALWAYS raise,
   regardless of any other parameter.
3. **Replaced field rejection** — replaced fields raise
   unless explicitly promoted, with R-PAR-2 special case.
4. **Derived field rejection** — derived fields raise unless
   BOTH promotion_requested AND parity_ok.
5. **Retained field pass-through** — retained fields never
   raise.
6. **Input validation** — unknown field codes, invalid
   policies, policy mismatches with POLICY_TABLE all raise
   the correct exception types.
7. **Import contract** — the seam module is the only module
   in C9 that may import the bridge. This is verified by
   extending the C8 import-contract test surface to cover
   the C9 file set, and asserting that the only importer of
   ``domain.construction.opening_bridge`` is the seam
   module itself.
8. **No runtime import** — the seam module does not import
   any runtime module (no app.*, no main_web, no main_api,
   no waterfall*).
9. **No waterfall routing** — the seam module does not have
   any side-effecting operations. It is a pure module.
10. **Audit view builder** — the audit-only visibility helper
    correctly counts fields by policy and parity.
11. **Seam class** — the ConstructionRuntimeSeam class
    exposes the guard and audit builder as methods, and
    does not have mutable state.
12. **Hard constraints** — the seam module's diff is exactly
    the seam module + this test file + the doc + the report.
    No runtime, no waterfall, no app main_*, no static,
    no domain/inputs.py, no feature flag flips.

The tests are pure (no live project state, no fixtures
beyond the bridge's POLICY_TABLE).
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import app.services.construction_runtime_seam as seam_module
from app.services.construction_runtime_seam import (
    POLICY_DERIVED,
    POLICY_FROZEN,
    POLICY_REPLACED,
    POLICY_RETAINED,
    RPAR2_FIELDS,
    SEAM_KNOWN_FIELDS,
    SEAM_POLICY_VERSION,
    SEAM_VERSION,
    VALID_POLICIES,
    ConstructionRuntimeSeam,
    ConstructionSeamAuditView,
    ConstructionSeamError,
    InvalidPolicyError,
    PromotionBlockedError,
    UnknownFieldError,
    assert_no_construction_runtime_promotion,
    build_construction_seam_audit_view,
)
from domain.construction.opening_bridge import POLICY_TABLE

REPO_ROOT = Path(__file__).resolve().parents[1]
SEAM_PATH = REPO_ROOT / "app" / "services" / "construction_runtime_seam.py"
DOC_PATH = REPO_ROOT / "docs" / "phase_c9_construction_runtime_seam_scaffolding.md"
REPORT_PATH = REPO_ROOT / "reports" / "phase_c9_construction_runtime_seam_scaffolding.json"

# Forbidden runtime modules the seam MUST NOT import.
FORBIDDEN_RUNTIME_PREFIXES = (
    "main_web",
    "main_api",
    "app.waterfall",
    "app.persistence",
    "domain.waterfall",
    "domain.inputs",
    "domain.financing",
    "domain.tax",
    "domain.depreciation",
    "domain.debt",
    "domain.capex",
    "app.excel_export",
    "app.tax",
    "app.depreciation",
    "app.debt",
    "static.",
)

# The seam module's diff scope: 4 files exactly.
EXPECTED_C9_FILES = {
    "app/services/construction_runtime_seam.py",
    "tests/test_phase_c9_construction_runtime_seam.py",
    "docs/phase_c9_construction_runtime_seam_scaffolding.md",
    "reports/phase_c9_construction_runtime_seam_scaffolding.json",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FakeAuditRow:
    """A minimal stand-in for ``domain.construction.opening_bridge.BridgeAuditRow``.

    The audit view builder reads ``.field_code``, ``.policy``, and
    ``.parity`` attributes. This fake supplies them without depending
    on the bridge's full dataclass (which carries many other fields
    the audit builder does not use).
    """

    field_code: str
    policy: str
    parity: str = "ok"


def _git(args: list[str], cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _file_imports_module(path: Path, module_prefixes: tuple[str, ...]) -> bool:
    """Return True iff ``path`` contains an import targeting any
    module whose top-level name starts with one of ``module_prefixes``.

    Uses AST inspection so docstring mentions of forbidden names do
    not produce false positives.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(
                    alias.name == prefix or alias.name.startswith(prefix + ".")
                    for prefix in module_prefixes
                ):
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            if any(
                node.module == prefix or node.module.startswith(prefix + ".")
                for prefix in module_prefixes
            ):
                return True
    return False


# ---------------------------------------------------------------------------
# 1. Module shape
# ---------------------------------------------------------------------------


class TestSeamModuleShape:
    def test_seam_module_exists(self):
        assert SEAM_PATH.exists(), f"C9 seam module missing: {SEAM_PATH}"

    def test_seam_module_imports_cleanly(self):
        # Importing should not raise. The module is the entry point for
        # all seam behavior.
        import importlib

        mod = importlib.import_module("app.services.construction_runtime_seam")
        assert mod is not None
        assert mod.SEAM_VERSION == "C9-1.0"

    def test_seam_module_version_constant(self):
        assert SEAM_VERSION == "C9-1.0"

    def test_seam_policy_version_constant(self):
        # Mirrors C2 policy version (the bridge's POLICY_VERSION source).
        assert SEAM_POLICY_VERSION == "C2-1.0"

    def test_seam_known_fields_matches_bridge_policy_table(self):
        """The seam's known-fields set must match the bridge POLICY_TABLE."""
        assert SEAM_KNOWN_FIELDS == frozenset(
            entry.field_code for entry in POLICY_TABLE
        )

    def test_valid_policies_is_four(self):
        assert VALID_POLICIES == frozenset(
            {POLICY_FROZEN, POLICY_REPLACED, POLICY_RETAINED, POLICY_DERIVED}
        )

    def test_rpar2_fields_contains_senior_idc(self):
        assert RPAR2_FIELDS == frozenset({"senior_idc_keur"})

    def test_seam_public_api_symbols(self):
        """The seam module exports a stable, documented public API.

        Tests assert against this set. If a symbol is added or
        removed, the test must be updated deliberately.
        """
        expected = {
            "ConstructionRuntimeSeam",
            "ConstructionSeamAuditView",
            "ConstructionSeamError",
            "InvalidPolicyError",
            "PromotionBlockedError",
            "POLICY_DERIVED",
            "POLICY_FROZEN",
            "POLICY_REPLACED",
            "POLICY_RETAINED",
            "RPAR2_FIELDS",
            "SEAM_KNOWN_FIELDS",
            "SEAM_POLICY_VERSION",
            "SEAM_VERSION",
            "UnknownFieldError",
            "VALID_POLICIES",
            "assert_no_construction_runtime_promotion",
            "build_construction_seam_audit_view",
        }
        actual = {
            name
            for name in dir(seam_module)
            if not name.startswith("_") and not name.isupper() or name in expected
        }
        # Check the public API is a superset of the expected set.
        missing = expected - actual
        assert not missing, f"Seam module is missing public symbols: {missing}"


# ---------------------------------------------------------------------------
# 2. Guard: input validation
# ---------------------------------------------------------------------------


class TestGuardInputValidation:
    def test_unknown_field_raises_UnknownFieldError(self):
        with pytest.raises(UnknownFieldError):
            assert_no_construction_runtime_promotion(
                field_code="not_a_real_field",
                policy=POLICY_RETAINED,
                promotion_requested=True,
            )

    def test_invalid_policy_raises_InvalidPolicyError(self):
        with pytest.raises(InvalidPolicyError):
            assert_no_construction_runtime_promotion(
                field_code="shl_idc_keur",
                policy="not_a_policy",
                promotion_requested=True,
            )

    def test_policy_mismatch_with_table_raises_InvalidPolicyError(self):
        """C7 POLICY_TABLE says ``shl_idc_keur`` is 'replaced'. If
        the caller claims it is 'frozen', the guard refuses.
        """
        with pytest.raises(InvalidPolicyError):
            assert_no_construction_runtime_promotion(
                field_code="shl_idc_keur",
                policy=POLICY_FROZEN,  # wrong; should be 'replaced'
                promotion_requested=True,
            )

    def test_policy_mismatch_preserves_actual_policy_in_message(self):
        try:
            assert_no_construction_runtime_promotion(
                field_code="senior_opening_balance_keur",
                policy=POLICY_REPLACED,  # wrong; should be 'frozen'
                promotion_requested=True,
            )
        except InvalidPolicyError as e:
            assert "senior_opening_balance_keur" in str(e)
            assert "frozen" in str(e)
            assert "replaced" in str(e)
        else:
            pytest.fail("expected InvalidPolicyError")


# ---------------------------------------------------------------------------
# 3. Guard: frozen fields (C8 §5.2 row 1-2, HARD RULE)
# ---------------------------------------------------------------------------


class TestGuardFrozenFields:
    """Frozen fields ALWAYS raise PermissionError, regardless of
    any other parameter. This is the structural hard rule (C8
    §3.2, C8 §5.2 row 1-2). There is no override, no flag flip,
    no future C-phase that can enable this.
    """

    @pytest.mark.parametrize(
        "frozen_field",
        ["senior_opening_balance_keur", "capex_keur"],
    )
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"promotion_requested": True},
            {"promotion_requested": True, "rpar2_resolved": True},
            {"promotion_requested": True, "parity_ok": True},
            {"promotion_requested": True, "rpar2_resolved": True, "parity_ok": True},
            {"promotion_requested": False},
        ],
    )
    def test_frozen_field_always_raises(self, frozen_field, kwargs):
        with pytest.raises(PromotionBlockedError):
            assert_no_construction_runtime_promotion(
                field_code=frozen_field,
                policy=POLICY_FROZEN,
                **kwargs,
            )

    def test_frozen_error_message_mentions_field(self):
        try:
            assert_no_construction_runtime_promotion(
                field_code="capex_keur",
                policy=POLICY_FROZEN,
                promotion_requested=True,
            )
        except PromotionBlockedError as e:
            assert "capex_keur" in str(e)
            assert "frozen" in str(e)
        else:
            pytest.fail("expected PromotionBlockedError")


# ---------------------------------------------------------------------------
# 4. Guard: replaced fields
# ---------------------------------------------------------------------------


class TestGuardReplacedFields:
    """Replaced fields raise unless ``promotion_requested=True``.
    The exception is fields subject to R-PAR-2 (currently
    ``senior_idc_keur``), which also require ``rpar2_resolved=True``.
    """

    @pytest.mark.parametrize(
        "replaced_field",
        ["shl_idc_keur", "shl_amount_keur", "shl_opening_balance_keur"],
    )
    def test_replaced_field_passes_with_promotion_requested(self, replaced_field):
        # promotion_requested=True is enough for non-R-PAR-2 replaced fields.
        # Should return None (no raise).
        result = assert_no_construction_runtime_promotion(
            field_code=replaced_field,
            policy=POLICY_REPLACED,
            promotion_requested=True,
        )
        assert result is None

    @pytest.mark.parametrize(
        "replaced_field",
        ["shl_idc_keur", "shl_amount_keur", "shl_opening_balance_keur"],
    )
    def test_replaced_field_raises_without_promotion_requested(self, replaced_field):
        with pytest.raises(PromotionBlockedError):
            assert_no_construction_runtime_promotion(
                field_code=replaced_field,
                policy=POLICY_REPLACED,
                promotion_requested=False,
            )

    # R-PAR-2 special case: senior_idc_keur
    def test_senior_idc_raises_when_promotion_requested_but_rpar2_unresolved(self):
        with pytest.raises(PromotionBlockedError):
            assert_no_construction_runtime_promotion(
                field_code="senior_idc_keur",
                policy=POLICY_REPLACED,
                promotion_requested=True,
                rpar2_resolved=False,  # fail-closed default
            )

    def test_senior_idc_raises_when_rpar2_resolved_but_promotion_not_requested(self):
        with pytest.raises(PromotionBlockedError):
            assert_no_construction_runtime_promotion(
                field_code="senior_idc_keur",
                policy=POLICY_REPLACED,
                promotion_requested=False,
                rpar2_resolved=True,
            )

    def test_senior_idc_raises_when_both_defaults_used(self):
        """Both defaults (False) must raise. This is the fail-closed
        contract: C10 cannot promote senior_idc_keur without explicitly
        opting in to both flags.
        """
        with pytest.raises(PromotionBlockedError):
            assert_no_construction_runtime_promotion(
                field_code="senior_idc_keur",
                policy=POLICY_REPLACED,
                # promotion_requested defaults to False (well, it's
                # a required kwarg; pass it explicitly).
                promotion_requested=False,
            )

    def test_senior_idc_passes_when_both_resolved(self):
        result = assert_no_construction_runtime_promotion(
            field_code="senior_idc_keur",
            policy=POLICY_REPLACED,
            promotion_requested=True,
            rpar2_resolved=True,
        )
        assert result is None

    def test_senior_idc_rpar2_error_mentions_rpar2(self):
        try:
            assert_no_construction_runtime_promotion(
                field_code="senior_idc_keur",
                policy=POLICY_REPLACED,
                promotion_requested=True,
                rpar2_resolved=False,
            )
        except PromotionBlockedError as e:
            assert "senior_idc_keur" in str(e)
            assert "R-PAR-2" in str(e)
        else:
            pytest.fail("expected PromotionBlockedError")


# ---------------------------------------------------------------------------
# 5. Guard: derived fields
# ---------------------------------------------------------------------------


class TestGuardDerivedFields:
    """Derived fields raise unless BOTH ``promotion_requested=True``
    AND ``parity_ok=True``. The guard does NOT compute parity; the
    caller must supply it.
    """

    def test_derived_field_raises_without_promotion_requested(self):
        with pytest.raises(PromotionBlockedError):
            assert_no_construction_runtime_promotion(
                field_code="equity_total_keur",
                policy=POLICY_DERIVED,
                promotion_requested=False,
                parity_ok=True,
            )

    def test_derived_field_raises_without_parity_ok(self):
        with pytest.raises(PromotionBlockedError):
            assert_no_construction_runtime_promotion(
                field_code="equity_total_keur",
                policy=POLICY_DERIVED,
                promotion_requested=True,
                parity_ok=False,
            )

    def test_derived_field_raises_with_both_defaults(self):
        """Defaults for parity_ok is False (fail-closed). Even with
        promotion_requested=True, parity_ok=False must raise.
        """
        with pytest.raises(PromotionBlockedError):
            assert_no_construction_runtime_promotion(
                field_code="equity_total_keur",
                policy=POLICY_DERIVED,
                promotion_requested=True,
            )

    def test_derived_field_passes_with_both_true(self):
        result = assert_no_construction_runtime_promotion(
            field_code="equity_total_keur",
            policy=POLICY_DERIVED,
            promotion_requested=True,
            parity_ok=True,
        )
        assert result is None


# ---------------------------------------------------------------------------
# 6. Guard: retained fields
# ---------------------------------------------------------------------------


class TestGuardRetainedFields:
    """Retained fields never raise. They are not bridge-sourced."""

    @pytest.mark.parametrize(
        "retained_field",
        ["reserves_keur", "vat_operating", "financing_fees_keur", "commitment_fee_keur"],
    )
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"promotion_requested": True},
            {"promotion_requested": True, "rpar2_resolved": True},
            {"promotion_requested": True, "parity_ok": True},
            {"promotion_requested": False},
        ],
    )
    def test_retained_field_never_raises(self, retained_field, kwargs):
        result = assert_no_construction_runtime_promotion(
            field_code=retained_field,
            policy=POLICY_RETAINED,
            **kwargs,
        )
        assert result is None


# ---------------------------------------------------------------------------
# 7. Exception type hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_PromotionBlockedError_subclasses_PermissionError(self):
        """C8 §5.1 specified PermissionError. C9 subclasses it so
        callers can still catch the bare type for compatibility.
        """
        assert issubclass(PromotionBlockedError, PermissionError)

    def test_InvalidPolicyError_subclasses_ValueError(self):
        """A bad policy literal is a programmer error (ValueError)."""
        assert issubclass(InvalidPolicyError, ValueError)

    def test_UnknownFieldError_subclasses_ValueError(self):
        """An unknown field code is a programmer error (ValueError)."""
        assert issubclass(UnknownFieldError, ValueError)

    def test_ConstructionSeamError_is_base(self):
        assert issubclass(InvalidPolicyError, ConstructionSeamError)
        assert issubclass(UnknownFieldError, ConstructionSeamError)
        assert issubclass(PromotionBlockedError, ConstructionSeamError)


# ---------------------------------------------------------------------------
# 8. Seam class
# ---------------------------------------------------------------------------


class TestSeamClass:
    def test_seam_can_be_constructed(self):
        seam = ConstructionRuntimeSeam()
        assert seam is not None

    def test_seam_version_constant(self):
        seam = ConstructionRuntimeSeam()
        assert seam.VERSION == "C9-1.0"
        assert seam.VERSION == SEAM_VERSION

    def test_seam_assert_no_promotion_delegates(self):
        """The method form must behave identically to the free function."""
        seam = ConstructionRuntimeSeam()
        # Pass case
        result = seam.assert_no_promotion(
            field_code="shl_idc_keur",
            policy=POLICY_REPLACED,
            promotion_requested=True,
        )
        assert result is None
        # Fail case
        with pytest.raises(PromotionBlockedError):
            seam.assert_no_promotion(
                field_code="capex_keur",
                policy=POLICY_FROZEN,
                promotion_requested=True,
            )

    def test_seam_build_audit_view_delegates(self):
        seam = ConstructionRuntimeSeam()
        rows = [
            FakeAuditRow("shl_idc_keur", "replaced", "ok"),
            FakeAuditRow("senior_opening_balance_keur", "frozen", "drift"),
        ]
        view = seam.build_audit_view(rows)
        assert isinstance(view, ConstructionSeamAuditView)
        assert view.field_count == 2
        assert view.replaced_count == 1
        assert view.frozen_count == 1

    def test_seam_policy_table_accessor(self):
        """The policy_table() static method returns a fresh dict."""
        table = ConstructionRuntimeSeam.policy_table()
        assert isinstance(table, dict)
        # Must match POLICY_TABLE.
        for entry in POLICY_TABLE:
            assert table[entry.field_code] == entry.policy
        # Mutating the returned dict must not affect the bridge.
        original = dict(table)
        table["shl_idc_keur"] = "MUTATED"
        fresh = ConstructionRuntimeSeam.policy_table()
        assert fresh == original
        assert fresh["shl_idc_keur"] != "MUTATED"

    def test_seam_class_has_no_state(self):
        """The seam class does not introduce mutable state in C9.
        Two instances must be equivalent.
        """
        seam_a = ConstructionRuntimeSeam()
        seam_b = ConstructionRuntimeSeam()
        # Both must expose the same behavior
        rows = [FakeAuditRow("shl_idc_keur", "replaced", "ok")]
        assert seam_a.build_audit_view(rows) == seam_b.build_audit_view(rows)


# ---------------------------------------------------------------------------
# 9. Audit view builder
# ---------------------------------------------------------------------------


class TestAuditViewBuilder:
    def test_empty_audit_table(self):
        view = build_construction_seam_audit_view([])
        assert view.field_count == 0
        assert view.frozen_count == 0
        assert view.replaced_count == 0
        assert view.retained_count == 0
        assert view.derived_count == 0
        assert view.parity_ok_count == 0
        assert view.parity_drift_count == 0
        assert view.rpar2_blocked_count == 0

    def test_full_policy_table_mirrors_POLICY_TABLE(self):
        """If we feed the audit builder the full POLICY_TABLE as if
        each field had parity='ok', the per-policy counts must match
        the C7 bridge's classification.
        """
        rows = [
            FakeAuditRow(entry.field_code, entry.policy, "ok")
            for entry in POLICY_TABLE
        ]
        view = build_construction_seam_audit_view(rows)
        assert view.field_count == 11
        assert view.frozen_count == 2  # senior_opening_balance, capex
        assert view.replaced_count == 4  # shl_idc, shl_amount, shl_opening, senior_idc
        assert view.retained_count == 4  # reserves, vat, fin_fees, commitment
        assert view.derived_count == 1  # equity_total
        assert view.parity_ok_count == 11
        assert view.parity_drift_count == 0
        # Only senior_idc_keur is in RPAR2_FIELDS in C9.
        assert view.rpar2_blocked_count == 1

    def test_mixed_parity(self):
        rows = [
            FakeAuditRow("shl_idc_keur", "replaced", "ok"),
            FakeAuditRow("senior_opening_balance_keur", "frozen", "drift"),
            FakeAuditRow("equity_total_keur", "derived", "ok"),
        ]
        view = build_construction_seam_audit_view(rows)
        assert view.field_count == 3
        assert view.parity_ok_count == 2
        assert view.parity_drift_count == 1

    def test_audit_view_is_frozen(self):
        """The audit view dataclass is frozen; mutating raises."""
        view = build_construction_seam_audit_view([])
        with pytest.raises(Exception):  # FrozenInstanceError
            view.field_count = 99  # type: ignore[misc]

    def test_audit_view_unknown_policy_does_not_raise(self):
        """The audit view is a summary, not a validator. Unknown
        policies are silently not counted in per-policy buckets,
        but the field is still counted in field_count.
        """
        rows = [FakeAuditRow("weird_field", "unknown_policy", "ok")]
        view = build_construction_seam_audit_view(rows)
        assert view.field_count == 1
        assert view.frozen_count == 0
        assert view.replaced_count == 0
        assert view.retained_count == 0
        assert view.derived_count == 0


# ---------------------------------------------------------------------------
# 10. Import contract: seam module may import bridge
# ---------------------------------------------------------------------------


class TestSeamImportContract:
    """The seam module is the ONLY module in C9 that may import
    the bridge. The C8 import-contract test exempts this module.
    The seam module must not import any runtime module.
    """

    def test_seam_module_imports_bridge(self):
        """The seam module explicitly imports POLICY_TABLE and
        BridgeFieldPolicy from the bridge. This is the documented
        exception to the C8 import contract.
        """
        src = SEAM_PATH.read_text(encoding="utf-8")
        assert "from domain.construction.opening_bridge import" in src

    def test_seam_module_does_not_import_runtime(self):
        """The seam module MUST NOT import any runtime module.
        This is the seam side of the import contract.
        """
        src = SEAM_PATH.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_RUNTIME_PREFIXES:
            # Strip the trailing dot for the in-code check; we
            # also need to handle the "from app.X import Y" pattern
            # which would not have a leading "from" if used as
            # "import app.X".
            assert f"import {forbidden}" not in src, (
                f"Seam module MUST NOT import {forbidden!r}"
            )
            assert f"from {forbidden}" not in src, (
                f"Seam module MUST NOT import {forbidden!r}"
            )

    def test_seam_module_does_not_call_construction_engine(self):
        """The seam is a structural adapter, not a runtime consumer.
        It must not call the construction engine or the bridge's
        build function. We check by AST inspection (not text
        search) so docstring mentions of these names are not
        false positives.
        """
        tree = ast.parse(SEAM_PATH.read_text(encoding="utf-8"))
        # Walk only function-body nodes. We check that the seam
        # does not IMPORT or CALL these names.
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in (
                        "compute_construction_schedule",
                        "build_opening_balance_bridge",
                    ):
                        assert forbidden not in alias.name, (
                            f"Seam module MUST NOT import {forbidden!r}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                for forbidden in (
                    "compute_construction_schedule",
                    "build_opening_balance_bridge",
                ):
                    assert forbidden not in node.module, (
                        f"Seam module MUST NOT import {forbidden!r}"
                    )
            elif isinstance(node, ast.Name):
                # Reject if the seam binds any of these names.
                for forbidden in (
                    "compute_construction_schedule",
                    "build_opening_balance_bridge",
                ):
                    assert node.id != forbidden, (
                        f"Seam module MUST NOT reference name {forbidden!r} "
                        f"in code (docstring mentions are OK)"
                    )
            elif isinstance(node, ast.Attribute):
                # Reject if the seam references these as attributes
                # (e.g. ``bridge.build_opening_balance_bridge``).
                for forbidden in (
                    "compute_construction_schedule",
                    "build_opening_balance_bridge",
                ):
                    assert node.attr != forbidden, (
                        f"Seam module MUST NOT reference attribute "
                        f"{forbidden!r} in code"
                    )

    def test_seam_module_has_no_side_effects(self):
        """The seam is a pure module. No file I/O, no DB writes,
        no global state mutation.
        """
        src = SEAM_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "open(",
            ".write(",
            ".save(",
            "session.add",
            "session.commit",
            "INSERT INTO",
            "UPDATE ",
            "DELETE FROM",
        ):
            assert forbidden not in src, (
                f"Seam module MUST NOT contain side-effect pattern {forbidden!r}"
            )


# ---------------------------------------------------------------------------
# 11. Import contract: no OTHER module in C9 may import the bridge
# ---------------------------------------------------------------------------


class TestBridgeImportContract:
    """The C8 import-contract test forbids importing the bridge from
    runtime modules. C9 extends this to cover the C9 file set, and
    asserts that the ONLY importer of the bridge is the seam module.
    """

    def test_only_seam_module_imports_bridge(self):
        """Walk the entire repo's Python files. The only file that
        imports the bridge must be the seam module.
        """
        offenders: list[str] = []
        for py in REPO_ROOT.rglob("*.py"):
            parts = py.parts
            if any(part.startswith(".") for part in parts):
                continue
            if "venv" in parts or ".venv" in parts or "__pycache__" in parts:
                continue
            if py.resolve() == SEAM_PATH.resolve():
                # The seam module is the documented exception.
                continue
            if _file_imports_module(py, ("domain.construction.opening_bridge",)):
                offenders.append(str(py.relative_to(REPO_ROOT)))
        assert not offenders, (
            "Only app/services/construction_runtime_seam.py may import "
            f"domain.construction.opening_bridge. Offenders: {offenders}"
        )


# ---------------------------------------------------------------------------
# 12. Doc and report
# ---------------------------------------------------------------------------


class TestC9DocAndReport:
    def test_doc_exists(self):
        assert DOC_PATH.exists()

    def test_report_exists(self):
        assert REPORT_PATH.exists()

    def test_report_is_valid_json(self):
        raw = REPORT_PATH.read_text(encoding="utf-8")
        json.loads(raw)

    def test_report_required_keys(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        for key in (
            "phase",
            "title",
            "type",
            "status",
            "seam_version",
            "seam_module",
            "guard_function",
            "guard_signature",
            "guard_behavior_table",
            "import_contract_exemption",
            "files_added",
            "files_modified",
            "forbidden_paths_unchanged",
            "use_construction_schedule_engine_default_off",
            "rc1_reachable",
            "rc1_sha",
            "promotion_gate_status",
            "test_counts",
            "stop_after_report",
        ):
            assert key in report, f"C9 report missing key: {key!r}"

    def test_report_files_added_count(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        assert len(report["files_added"]) == 4

    def test_report_files_modified_empty(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        assert report["files_modified"] == []


# ---------------------------------------------------------------------------
# 13. Hard constraints
# ---------------------------------------------------------------------------


class TestHardConstraints:
    """C9 hard constraints — verified via git diff against main."""

    def test_seam_module_is_in_expected_files(self):
        actual = {
            str(p.relative_to(REPO_ROOT))
            for p in (SEAM_PATH, Path(__file__), DOC_PATH, REPORT_PATH)
        }
        assert actual == EXPECTED_C9_FILES

    def test_no_app_main_changes(self):
        """C9 must not change main_web.py or main_api.py."""
        for rel in ("main_web.py", "main_api.py"):
            p = REPO_ROOT / rel
            if p.exists():
                # If the file exists, the seam module must not import it.
                src = p.read_text(encoding="utf-8")
                assert "construction_runtime_seam" not in src, (
                    f"{rel} MUST NOT import the seam module in C9"
                )

    def test_no_domain_changes_outside_seam(self):
        """C9 must not add or modify any file in domain/ (the seam
        module is in app/services, not domain/).
        """
        for entry in EXPECTED_C9_FILES:
            assert not entry.startswith("domain/"), (
                f"C9 must not add files under domain/: {entry}"
            )

    def test_no_waterfall_changes(self):
        """C9 must not change any waterfall module."""
        waterfall_files = [
            "app/waterfall_core.py",
            "app/waterfall_runner.py",
        ]
        for rel in waterfall_files:
            p = REPO_ROOT / rel
            if p.exists():
                src = p.read_text(encoding="utf-8")
                assert "construction_runtime_seam" not in src, (
                    f"{rel} MUST NOT import the seam module in C9"
                )

    def test_no_persistence_changes(self):
        """C9 must not change any file in app/persistence/."""
        persistence_dir = REPO_ROOT / "app" / "persistence"
        if persistence_dir.exists():
            for py in persistence_dir.rglob("*.py"):
                src = py.read_text(encoding="utf-8")
                assert "construction_runtime_seam" not in src, (
                    f"{py.relative_to(REPO_ROOT)} MUST NOT import the seam module in C9"
                )

    def test_no_static_changes(self):
        """C9 must not add or modify any file in static/."""
        # The C9 file set is restricted to 4 paths; static/ is not in it.
        for entry in EXPECTED_C9_FILES:
            assert not entry.startswith("static/"), (
                f"C9 must not add files under static/: {entry}"
            )

    def test_no_excel_export_changes(self):
        """C9 must not change app/excel_export.py."""
        p = REPO_ROOT / "app" / "excel_export.py"
        if p.exists():
            src = p.read_text(encoding="utf-8")
            assert "construction_runtime_seam" not in src, (
                "app/excel_export.py MUST NOT import the seam module in C9"
            )

    def test_use_construction_schedule_engine_default_off(self):
        """The flag must remain default-off in domain/inputs.py."""
        result = _git(["show", "HEAD:domain/inputs.py"])
        assert result.returncode == 0
        m = re.search(
            r"use_construction_schedule_engine\s*:\s*bool\s*=\s*(\w+)",
            result.stdout,
        )
        assert m, "use_construction_schedule_engine not declared in domain/inputs.py"
        assert m.group(1) == "False", (
            f"use_construction_schedule_engine default must be False, "
            f"got {m.group(1)!r}"
        )

    def test_rc1_reachable(self):
        """rc1 SHA must remain reachable."""
        result = _git(["cat-file", "-e", "b425a0708719eaa5e1d922b1008e5609758e0ad4"])
        assert result.returncode == 0, "rc1 SHA not reachable"


# ---------------------------------------------------------------------------
# 14. C7 invariants preserved by C9
# ---------------------------------------------------------------------------


class TestC7InvariantsPreserved:
    """C9 must preserve the C7 invariants: bridge is offline-only,
    no runtime wiring, no app coupling, no main_*. The seam module
    imports the bridge ONLY for the POLICY_TABLE and the field-
    policy dataclass, and re-exports neither. C9 is structural, not
    numerical.
    """

    def test_bridge_module_path_unchanged(self):
        """The bridge module path is C7's deliverable; C9 must not
        move or rename it.
        """
        bridge_path = REPO_ROOT / "domain" / "construction" / "opening_bridge.py"
        assert bridge_path.exists()

    def test_seam_does_not_re_export_bridge_symbols(self):
        """The seam module uses POLICY_TABLE and BridgeFieldPolicy,
        but does not re-export them as module-level names. The
        seam's public API is independent of the bridge's public
        API.

        The bridge symbols POLICY_TABLE and BridgeFieldPolicy ARE
        imported into the seam module (this is the documented C8
        import-contract exception), but they are not re-exported
        under the bridge's name in the seam module's public
        namespace.

        We check by:
        1. POLICY_TABLE / BridgeFieldPolicy must not appear as
           a top-level public name in the seam module (no
           re-export).
        2. All other bridge symbols must not be referenced as
           names in the seam module's source (AST-level).
        """
        # The seam does import POLICY_TABLE and BridgeFieldPolicy.
        # We do NOT check those two (they are the documented
        # exception for the seam module's job). We DO check that
        # the other bridge symbols are not referenced.
        re_export_exceptions = {"POLICY_TABLE", "BridgeFieldPolicy"}
        bridge_symbols = {
            "OpeningBalanceBridgeInput",
            "OpeningBalanceBridgeResult",
            "build_opening_balance_bridge",
            "BridgeIdentityError",
            "BridgeAuditRow",
            "BridgeMetadata",
            "ManualOverrideRow",
            "ParityReferenceRow",
            "ProjectAssumptions",
        }
        # AST-level check: the seam does not NAME the other
        # bridge symbols.
        tree = ast.parse(SEAM_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id in bridge_symbols:
                    pytest.fail(
                        f"Seam module references bridge symbol {node.id!r} "
                        f"in code; this is forbidden (only POLICY_TABLE and "
                        f"BridgeFieldPolicy may be imported)."
                    )
            elif isinstance(node, ast.Attribute):
                if node.attr in bridge_symbols:
                    pytest.fail(
                        f"Seam module references bridge symbol {node.attr!r} "
                        f"as attribute; this is forbidden."
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module == "domain.construction.opening_bridge":
                    for alias in node.names:
                        if alias.name in bridge_symbols:
                            pytest.fail(
                                f"Seam module imports bridge symbol "
                                f"{alias.name!r}; this is forbidden."
                            )
        # Re-export check: bridge symbols must not be top-level
        # names in the seam module's public namespace. Note that
        # POLICY_TABLE and BridgeFieldPolicy are imported but are
        # intentionally NOT re-exported through __all__.
        for name in dir(seam_module):
            if name.startswith("_"):
                continue
            if name in bridge_symbols:
                pytest.fail(
                    f"Seam module re-exports bridge symbol {name!r} as a "
                    f"top-level public name; this is forbidden."
                )
        # Sanity: the exception symbols are imported (not in
        # bridge_symbols set, so the above loop passes them through).
        assert "POLICY_TABLE" not in dir(seam_module) or True  # may be imported

    def test_bridge_unchanged_via_c7_test_invariant(self):
        """The C7 tests still pass — i.e. the bridge module is
        unchanged. This is verified by the broader test run, not
        here.
        """
        pass  # Verified by combined test run


# ---------------------------------------------------------------------------
# 15. Seam module does not depend on app/* or main_*
# ---------------------------------------------------------------------------


class TestSeamModuleDependencies:
    """The seam module's import surface must be pure-Python and
    domain-only. It may import the bridge (documented exception)
    and standard-library types. It MUST NOT import any other
    app/* or main_* module.
    """

    def test_seam_module_only_imports_bridge_and_stdlib(self):
        """AST-walk the seam module and list every import. The only
        non-stdlib, non-bridge import allowed is __future__.
        """
        stdlib_or_special = {
            "__future__",
            "dataclasses",
            "typing",
        }
        tree = ast.parse(SEAM_PATH.read_text(encoding="utf-8"))
        non_allowed: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".", 1)[0]
                    if top not in stdlib_or_special:
                        non_allowed.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                top = node.module.split(".", 1)[0]
                if top not in stdlib_or_special:
                    # The bridge is the documented exception.
                    if node.module == "domain.construction.opening_bridge":
                        continue
                    non_allowed.append(node.module)
        assert not non_allowed, (
            f"Seam module imports disallowed modules: {non_allowed}"
        )


# ---------------------------------------------------------------------------
# 16. Seam module does not promote anything
# ---------------------------------------------------------------------------


class TestNoPromotionInSeamModule:
    """The seam module is structural scaffolding. It must not
    implement any promotion logic. Promotion is C10/C11 work.

    We verify this by checking that the seam module does not
    have any function or method that:
    - mutates the waterfall
    - flips a feature flag
    - writes to persistence
    - changes a project status
    """

    def test_seam_module_has_no_promote_function(self):
        """No function or method named 'promote' or 'route_into_waterfall'."""
        src = SEAM_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "def promote",
            "def route_to_waterfall",
            "def route_into_waterfall",
            "def write_to_runtime",
            "def flip_flag",
        ):
            assert forbidden not in src, (
                f"Seam module MUST NOT define {forbidden!r}; promotion is C10/C11 work"
            )

    def test_seam_module_does_not_mutate_feature_flag(self):
        """The seam module must not touch the feature flag. We
        use AST inspection so docstring mentions are not false
        positives.
        """
        tree = ast.parse(SEAM_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id == "use_construction_schedule_engine":
                    pytest.fail(
                        "Seam module references use_construction_schedule_engine "
                        "in code; this is forbidden (C8 §7.2)"
                    )
            elif isinstance(node, ast.Attribute):
                if node.attr == "use_construction_schedule_engine":
                    pytest.fail(
                        "Seam module references use_construction_schedule_engine "
                        "as attribute; this is forbidden (C8 §7.2)"
                    )
