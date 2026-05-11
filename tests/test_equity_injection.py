"""Tests for Phase 6F-B EquityInjection schema."""
from __future__ import annotations

import math
import pytest

from domain.sponsor.equity_injection import EquityInjection


class TestEquityInjectionValidation:
    """Validation rules for EquityInjection construction."""

    def test_period_index_must_be_non_negative(self):
        with pytest.raises(ValueError, match="period_index must be >= 0"):
            EquityInjection(
                period_index=-1,
                amount_keur=1000.0,
                investor_id="SPONSOR-1",
                target_entity="SPV-1",
                purpose="equityContribution",
            )

    def test_amount_keur_must_be_non_negative(self):
        with pytest.raises(ValueError, match="amount_keur must be >= 0"):
            EquityInjection(
                period_index=0,
                amount_keur=-500.0,
                investor_id="SPONSOR-1",
                target_entity="SPV-1",
                purpose="equityContribution",
            )

    def test_amount_keur_rejects_nan(self):
        with pytest.raises(ValueError, match="amount_keur must be finite"):
            EquityInjection(
                period_index=0,
                amount_keur=float('nan'),
                investor_id="SPONSOR-1",
                target_entity="SPV-1",
                purpose="equityContribution",
            )

    def test_amount_keur_rejects_inf(self):
        with pytest.raises(ValueError, match="amount_keur must be finite"):
            EquityInjection(
                period_index=0,
                amount_keur=float('inf'),
                investor_id="SPONSOR-1",
                target_entity="SPV-1",
                purpose="equityContribution",
            )

    def test_investor_id_cannot_be_empty(self):
        with pytest.raises(ValueError, match="investor_id must be a non-empty string"):
            EquityInjection(
                period_index=0,
                amount_keur=1000.0,
                investor_id="",
                target_entity="SPV-1",
                purpose="equityContribution",
            )

    def test_investor_id_cannot_be_whitespace(self):
        with pytest.raises(ValueError, match="investor_id must be a non-empty string"):
            EquityInjection(
                period_index=0,
                amount_keur=1000.0,
                investor_id="   ",
                target_entity="SPV-1",
                purpose="equityContribution",
            )

    def test_target_entity_cannot_be_empty(self):
        with pytest.raises(ValueError, match="target_entity must be a non-empty string"):
            EquityInjection(
                period_index=0,
                amount_keur=1000.0,
                investor_id="SPONSOR-1",
                target_entity="",
                purpose="equityContribution",
            )

    def test_target_entity_cannot_be_whitespace(self):
        with pytest.raises(ValueError, match="target_entity must be a non-empty string"):
            EquityInjection(
                period_index=0,
                amount_keur=1000.0,
                investor_id="SPONSOR-1",
                target_entity="  ",
                purpose="equityContribution",
            )

    def test_purpose_cannot_be_empty(self):
        with pytest.raises(ValueError, match="purpose must be a non-empty string"):
            EquityInjection(
                period_index=0,
                amount_keur=1000.0,
                investor_id="SPONSOR-1",
                target_entity="SPV-1",
                purpose="",
            )

    def test_purpose_cannot_be_whitespace(self):
        with pytest.raises(ValueError, match="purpose must be a non-empty string"):
            EquityInjection(
                period_index=0,
                amount_keur=1000.0,
                investor_id="SPONSOR-1",
                target_entity="SPV-1",
                purpose="   ",
            )

    def test_notes_must_be_str_or_none(self):
        with pytest.raises(TypeError, match="notes must be str or None"):
            EquityInjection(
                period_index=0,
                amount_keur=1000.0,
                investor_id="SPONSOR-1",
                target_entity="SPV-1",
                purpose="equityContribution",
                notes=123,
            )

    def test_metadata_must_be_dict_or_none(self):
        with pytest.raises(TypeError, match="metadata must be dict or None"):
            EquityInjection(
                period_index=0,
                amount_keur=1000.0,
                investor_id="SPONSOR-1",
                target_entity="SPV-1",
                purpose="equityContribution",
                metadata=["not", "a", "dict"],
            )

    def test_metadata_keys_must_be_str(self):
        with pytest.raises(TypeError, match="metadata keys must be str"):
            EquityInjection(
                period_index=0,
                amount_keur=1000.0,
                investor_id="SPONSOR-1",
                target_entity="SPV-1",
                purpose="equityContribution",
                metadata={123: "value"},
            )

    def test_metadata_values_must_be_json_serializable(self):
        with pytest.raises(TypeError, match="metadata values must be immutable JSON scalars"):
            EquityInjection(
                period_index=0,
                amount_keur=1000.0,
                investor_id="SPONSOR-1",
                target_entity="SPV-1",
                purpose="equityContribution",
                metadata={"key": object()},
            )

    def test_metadata_rejects_list_values(self):
        with pytest.raises(TypeError, match="immutable JSON scalars"):
            EquityInjection(
                period_index=0,
                amount_keur=1000.0,
                investor_id="SPONSOR-1",
                target_entity="SPV-1",
                purpose="equityContribution",
                metadata={"key": [1, 2, 3]},
            )

    def test_metadata_rejects_dict_values(self):
        with pytest.raises(TypeError, match="immutable JSON scalars"):
            EquityInjection(
                period_index=0,
                amount_keur=1000.0,
                investor_id="SPONSOR-1",
                target_entity="SPV-1",
                purpose="equityContribution",
                metadata={"key": {"nested": "dict"}},
            )

    @pytest.mark.parametrize("purpose", [
        "equityContribution",
        "topUp",
        "reganEquity",
        "deferredEquity",
        "equityFirstLoss",
        "reserveTopUp",
    ])
    def test_valid_purpose_values_accepted(self, purpose):
        inj = EquityInjection(
            period_index=1,
            amount_keur=500.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose=purpose,
        )
        assert inj.purpose == purpose

    @pytest.mark.parametrize("period_index,amount_keur", [
        (0, 0.0),      # zero amount allowed
        (0, 1_000.0),  # normal
        (10, 50_000.0), # large amount, later period
        (0, 0.01),     # very small amount
    ])
    def test_valid_minimal_construction(self, period_index, amount_keur):
        inj = EquityInjection(
            period_index=period_index,
            amount_keur=amount_keur,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
        )
        assert inj.period_index == period_index
        assert inj.amount_keur == amount_keur


class TestEquityInjectionImmutability:
    """Frozen dataclass immutability enforcement."""

    def test_instance_is_frozen(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
        )
        with pytest.raises(Exception):
            inj.amount_keur = 2000.0

    def test_metadata_internal_tuple_cannot_be_mutated(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
            metadata={"key": "value"},
        )
        # Internal tuple is immutable
        with pytest.raises(Exception):
            inj._metadata_tuple[0] = ("new", "value")

    def test_metadata_property_returns_fresh_dict_each_call(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
            metadata={"key": "value"},
        )
        m1 = inj.metadata
        m2 = inj.metadata
        assert m1 is not m2           # different dict instances
        assert m1 == m2 == {"key": "value"}
        m1["new_key"] = "mutation"    # mutate m1
        assert inj.metadata == {"key": "value"}  # internal state unchanged

    def test_with_metadata_returns_new_instance(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
        )
        inj2 = inj.with_metadata(country="HR", year=2026)
        assert inj2 is not inj
        assert inj.metadata is None
        assert inj2.metadata == {"country": "HR", "year": 2026}
        # original unchanged
        assert inj.metadata is None

    def test_with_metadata_merges_with_existing(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
            metadata={"existing": "value"},
        )
        inj2 = inj.with_metadata(new_key="new_value")
        assert inj2.metadata == {"existing": "value", "new_key": "new_value"}
        # original unchanged
        assert inj.metadata == {"existing": "value"}

    def test_with_metadata_overwrites_duplicate_keys(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
            metadata={"key": "old"},
        )
        inj2 = inj.with_metadata(key="new")
        assert inj2.metadata == {"key": "new"}


class TestEquityInjectionMetadataNormalization:
    """Metadata dict normalization to frozen sorted tuple."""

    def test_frozen_metadata_returns_empty_when_none(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
        )
        assert inj.frozen_metadata == ()

    def test_frozen_metadata_returns_sorted_tuples(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
            metadata={"z_key": 1, "a_key": 2, "m_key": 3},
        )
        fm = inj.frozen_metadata
        assert isinstance(fm, tuple)
        assert all(isinstance(k, str) for k, _ in fm)
        keys = [k for k, _ in fm]
        assert keys == sorted(keys)  # sorted ascending

    def test_frozen_metadata_is_frozen_tuple(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
            metadata={"key": "value"},
        )
        with pytest.raises(Exception):
            inj.frozen_metadata[0] = ("new", "value")


class TestEquityInjectionAuditNote:
    """Audit note property."""

    def test_audit_note_is_present(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
        )
        assert "AUDIT-ONLY" in inj.audit_note
        assert "read-only governance artifact" in inj.audit_note

    def test_audit_note_is_stable(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
            metadata={"key": "value"},
        )
        # audit note same after metadata operations
        assert inj.audit_note == inj.with_metadata(x=1).audit_note


class TestEquityInjectionRoundtrip:
    """Construction roundtrip and field access."""

    def test_all_fields_accessible(self):
        inj = EquityInjection(
            period_index=5,
            amount_keur=25_000.0,
            investor_id="EQUITY-CO-1",
            target_entity="HOLDCO",
            purpose="topUp",
            notes="Initial sponsor top-up at construction",
            metadata={"tranche": "A", "currency": "EUR"},
        )
        assert inj.period_index == 5
        assert inj.amount_keur == 25_000.0
        assert inj.investor_id == "EQUITY-CO-1"
        assert inj.target_entity == "HOLDCO"
        assert inj.purpose == "topUp"
        assert inj.notes == "Initial sponsor top-up at construction"
        assert inj.metadata == {"tranche": "A", "currency": "EUR"}

    def test_optional_notes_can_be_omitted(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
        )
        assert inj.notes is None

    def test_optional_metadata_can_be_omitted(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
        )
        assert inj.metadata is None
        assert inj.frozen_metadata == ()

    @pytest.mark.parametrize("metadata_value", [
        42,
        3.14,
        True,
        "string",
        None,
    ])
    def test_metadata_values_immutable_json_scalars_only(self, metadata_value):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
            metadata={"key": metadata_value},
        )
        assert inj.metadata["key"] == metadata_value

    def test_metadata_key_order_deterministic_after_normalization(self):
        inj = EquityInjection(
            period_index=0,
            amount_keur=1000.0,
            investor_id="SPONSOR-1",
            target_entity="SPV-1",
            purpose="equityContribution",
            metadata={"z": 1, "a": 2, "m": 3, "b": 4},
        )
        # frozen_metadata is sorted — deterministic regardless of input order
        keys = [k for k, _ in inj.frozen_metadata]
        assert keys == ["a", "b", "m", "z"]