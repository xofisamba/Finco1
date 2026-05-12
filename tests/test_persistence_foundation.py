"""Tests for the persistence foundation layer.

Phase 7E: Persistence Foundation
Tests cover:
- Project snapshot creation
- Scenario snapshot creation
- Sponsor snapshot creation
- Serialization roundtrip
- Deterministic ordering
- Invalid schema rejection
- NaN/Inf rejection
- Immutable behavior
- Append-only semantics
- No mutation of source domain objects
"""
from __future__ import annotations

import copy
import math
import pytest
from datetime import datetime, timezone

from domain.persistence.snapshot_base import (
    SCHEMA_VERSION,
    SnapshotID,
    validate_schema_version,
    validate_timestamp,
    reject_nan_inf_float,
    reject_nan_inf_container,
    frozen_get_fields,
    to_primitive,
)
from domain.persistence.project_snapshot import ProjectSnapshot, TECHNOLOGY_TYPES
from domain.persistence.scenario_snapshot import (
    ScenarioSnapshot, InputSnapshot, ResultSnapshot,
)
from domain.persistence.sponsor_snapshot import (
    SponsorSnapshot, InvestorRegistrySnapshot, CapitalStackSnapshot,
)
from domain.persistence.snapshot_serializer import SnapshotSerializer
from domain.persistence.snapshot_store import (
    SnapshotStore,
    InMemorySnapshotStore,
    MultiSnapshotStore,
    SnapshotNotFoundError,
    SchemaVersionMismatchError,
    SnapshotCorruptedError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def aware_utc(**kwargs) -> datetime:
    return datetime.now(timezone.utc).replace(**kwargs)


# ===========================================================================
# snapshot_base — primitives
# ===========================================================================

class TestSnapshotID:
    def test_generate_produces_unique_ids(self):
        ids = [SnapshotID.generate() for _ in range(100)]
        assert len(set(str(i) for i in ids)) == 100

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="non-empty"):
            SnapshotID(value="   ")

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="non-empty"):
            SnapshotID(value="")

    def test_str_returns_value(self):
        sid = SnapshotID(value="abc-123")
        assert str(sid) == "abc-123"

    def test_equality(self):
        a = SnapshotID(value="abc")
        b = SnapshotID(value="abc")
        c = SnapshotID(value="def")
        assert a == b
        assert a != c

    def test_hashable(self):
        s = {SnapshotID(value="x"), SnapshotID(value="y")}
        assert len(s) == 2


class TestValidateSchemaVersion:
    def test_valid_version(self):
        assert validate_schema_version(SCHEMA_VERSION) == SCHEMA_VERSION

    def test_rejects_wrong_version(self):
        with pytest.raises(ValueError, match="not supported"):
            validate_schema_version(99)

    def test_rejects_non_int(self):
        with pytest.raises(TypeError, match="must be int"):
            validate_schema_version("1")  # type: ignore

    def test_rejects_none(self):
        with pytest.raises(TypeError, match="must be int"):
            validate_schema_version(None)  # type: ignore


class TestValidateTimestamp:
    def test_accepts_utc_datetime(self):
        ts = datetime.now(timezone.utc)
        result = validate_timestamp(ts)
        assert result.tzinfo == timezone.utc

    def test_rejects_naive_datetime(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            validate_timestamp(datetime.now())

    def test_rejects_non_datetime(self):
        with pytest.raises(TypeError, match="must be datetime"):
            validate_timestamp("2026-01-01T00:00:00Z")  # type: ignore


class TestRejectNaNInf:
    def test_accepts_valid_float(self):
        assert reject_nan_inf_float(0.0, field_name="val") == 0.0
        assert reject_nan_inf_float(1.5, field_name="val") == 1.5
        assert reject_nan_inf_float(-999.0, field_name="val") == -999.0
        assert reject_nan_inf_float(1, field_name="val") == 1.0  # int is OK

    def test_rejects_nan(self):
        with pytest.raises(ValueError, match="NaN"):
            reject_nan_inf_float(float("nan"), field_name="val")

    def test_rejects_inf(self):
        with pytest.raises(ValueError, match="Inf"):
            reject_nan_inf_float(float("inf"), field_name="val")
        with pytest.raises(ValueError, match="Inf"):
            reject_nan_inf_float(float("-inf"), field_name="val")

    def test_rejects_non_float(self):
        with pytest.raises(TypeError, match="must be float"):
            reject_nan_inf_float("1.0", field_name="val")  # type: ignore

    def test_container_rejects_nan_in_dict(self):
        with pytest.raises(ValueError, match="NaN"):
            reject_nan_inf_container({"key": float("nan")})

    def test_container_rejects_inf_in_list(self):
        with pytest.raises(ValueError, match="Inf"):
            reject_nan_inf_container([1, 2, float("inf")])

    def test_container_accepts_clean_data(self):
        reject_nan_inf_container({"a": 1, "b": [2, 3], "c": {"d": 4}})
        reject_nan_inf_container([{"x": 1.0}, {"y": 2.0}])

    def test_to_primitive_datetime(self):
        ts = datetime.now(timezone.utc)
        assert to_primitive(ts) == ts.isoformat()

    def test_to_primitive_uuid(self):
        import uuid
        u = uuid.uuid4()
        assert to_primitive(u) == str(u)


# ===========================================================================
# ProjectSnapshot
# ===========================================================================

class TestProjectSnapshotCreation:
    def test_create_with_valid_data(self):
        ts = aware_utc()
        ps = ProjectSnapshot.create(
            name="Oborovo Solar",
            technology_type="solar",
            description="53.63 MW solar plant",
            owner_id="user-1",
            now=ts,
        )
        assert ps.name == "Oborovo Solar"
        assert ps.technology_type == "solar"
        assert ps.description == "53.63 MW solar plant"
        assert ps.owner_id == "user-1"
        assert ps.created_at == ts
        assert ps.updated_at == ts
        assert ps.schema_version == SCHEMA_VERSION
        assert isinstance(ps.id, SnapshotID)

    def test_rejects_invalid_technology_type(self):
        with pytest.raises(ValueError, match="technology_type must be one of"):
            ProjectSnapshot.create(name="Test", technology_type="rocket")

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError, match="name must be non-empty"):
            ProjectSnapshot.create(name="", technology_type="solar")

    def test_all_technology_types_accepted(self):
        for tt in TECHNOLOGY_TYPES:
            ps = ProjectSnapshot.create(name="Test", technology_type=tt)
            assert ps.technology_type == tt

    def test_schema_version_required(self):
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        assert ps.schema_version == SCHEMA_VERSION


class TestProjectSnapshotRoundtrip:
    def test_to_dict_roundtrip(self):
        ps = ProjectSnapshot.create(name="TUHO Wind", technology_type="wind")
        d = ps.to_dict()
        restored = ProjectSnapshot.from_dict(d)
        assert restored == ps

    def test_to_json_roundtrip(self):
        ps = ProjectSnapshot.create(name="TUHO Wind", technology_type="wind")
        json_str = ps.to_json()
        restored = SnapshotSerializer.deserialize_project(json_str)
        assert restored == ps

    def test_deterministic_serialization(self):
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        s1 = ps.to_json()
        s2 = ps.to_json()
        assert s1 == s2  # Same bytes every time


class TestProjectSnapshotImmutable:
    def test_cannot_mutate_after_creation(self):
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        with pytest.raises(Exception):  # frozen dataclass raises AttributeError
            ps.name = "Hacked"  # type: ignore

    def test_deepcopy_not_equal(self):
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        copied = copy.deepcopy(ps)
        assert copied == ps
        assert copied is not ps


# ===========================================================================
# InputSnapshot & ResultSnapshot
# ===========================================================================

class TestInputSnapshotCreation:
    def test_create_with_hash(self):
        ts = aware_utc()
        inputs = {"capex": {"total": 50000}, "debt": {"senior_debt": 30000}}
        inp = InputSnapshot.create(inputs_json=inputs, now=ts)
        assert inp.inputs_hash
        assert len(inp.inputs_hash) == 64
        assert inp.inputs_json == inputs
        assert inp.created_at == ts

    def test_rejects_nan_in_inputs(self):
        with pytest.raises(ValueError, match="NaN"):
            InputSnapshot.create(inputs_json={"x": float("nan")})

    def test_rejects_inf_in_inputs(self):
        with pytest.raises(ValueError, match="Inf"):
            InputSnapshot.create(inputs_json={"x": float("inf")})

    def test_roundtrip(self):
        inp = InputSnapshot.create(inputs_json={"key": "value", "num": 123})
        d = inp.to_dict()
        restored = InputSnapshot.from_dict(d)
        assert restored == inp


class TestResultSnapshotCreation:
    def test_create_validates_hash(self):
        rs = ResultSnapshot.create(
            results_json={"equity_irr": 0.11, "project_irr": 0.09},
            inputs_hash="a" * 64,
        )
        assert len(rs.inputs_hash) == 64

    def test_rejects_short_hash(self):
        with pytest.raises(ValueError, match="64-char"):
            ResultSnapshot.create(
                results_json={"irr": 0.10},
                inputs_hash="abc",
            )

    def test_roundtrip(self):
        rs = ResultSnapshot.create(
            results_json={"equity_irr": 0.1161, "total_distributions_keur": 150000},
            inputs_hash="a" * 64,
        )
        d = rs.to_dict()
        restored = ResultSnapshot.from_dict(d)
        assert restored == rs


# ===========================================================================
# ScenarioSnapshot
# ===========================================================================

class TestScenarioSnapshotCreation:
    def test_create_with_all_fields(self):
        ts = aware_utc()
        inp = InputSnapshot.create(inputs_json={"capex": 100})
        sc = ScenarioSnapshot.create(
            project_id="proj-1",
            name="Base Case",
            is_base_case=True,
            description="Base scenario",
            parent_scenario_id="parent-scen-1",
            input_snapshot=inp,
            now=ts,
        )
        assert sc.name == "Base Case"
        assert sc.is_base_case is True
        assert str(sc.project_id) == "proj-1"
        assert str(sc.parent_scenario_id) == "parent-scen-1"
        assert sc.input_snapshot is inp

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError, match="name must be non-empty"):
            ScenarioSnapshot.create(project_id="p1", name="   ")

    def test_roundtrip(self):
        inp = InputSnapshot.create(inputs_json={"test": True})
        sc = ScenarioSnapshot.create(
            project_id="proj-x",
            name="P90 Scenario",
            input_snapshot=inp,
        )
        d = sc.to_dict()
        restored = ScenarioSnapshot.from_dict(d)
        assert restored == sc

    def test_json_roundtrip(self):
        sc = ScenarioSnapshot.create(project_id="proj-x", name="Test")
        json_str = sc.to_json()
        restored = SnapshotSerializer.deserialize_scenario(json_str)
        assert restored == sc


# ===========================================================================
# SponsorSnapshot
# ===========================================================================

class TestSponsorSnapshotCreation:
    def test_create_full_sponsor_snapshot(self):
        ts = aware_utc()
        reg = InvestorRegistrySnapshot.create(
            entries_json=[
                {"investor_id": "LP-1", "role": "LP", "ownership_pct": 0.80, "committed_capital_keur": 8000},
                {"investor_id": "GP-1", "role": "GP", "ownership_pct": 0.20, "committed_capital_keur": 2000},
            ],
            total_ownership_pct=1.0,
            total_committed_keur=10000.0,
            now=ts,
        )
        stack = CapitalStackSnapshot.create(
            total_committed_keur=10000.0,
            total_contributed_by_period_keur=[0.0, 5000.0, 10000.0],
            investor_ids=["LP-1", "GP-1"],
            now=ts,
        )
        sponsor = SponsorSnapshot.create(
            investor_registry=reg,
            capital_stack=stack,
            waterfall_result_json={
                "total_allocated_keur": 15000.0,
                "per_investor_results": [],
            },
            now=ts,
        )
        assert sponsor.investor_registry.total_committed_keur == 10000.0
        assert sponsor.capital_stack.total_committed_keur == 10000.0

    def test_rejects_nan_in_waterfall_result(self):
        reg = InvestorRegistrySnapshot.create(
            entries_json=[],
            total_ownership_pct=1.0,
            total_committed_keur=0.0,
        )
        stack = CapitalStackSnapshot.create(
            total_committed_keur=0.0,
            total_contributed_by_period_keur=[],
            investor_ids=[],
        )
        with pytest.raises(ValueError, match="NaN"):
            SponsorSnapshot.create(
                investor_registry=reg,
                capital_stack=stack,
                waterfall_result_json={"irr": float("nan")},
            )

    def test_roundtrip(self):
        reg = InvestorRegistrySnapshot.create(
            entries_json=[{"investor_id": "LP-1", "role": "LP", "ownership_pct": 0.8, "committed_capital_keur": 8000}],
            total_ownership_pct=0.8,
            total_committed_keur=8000.0,
        )
        stack = CapitalStackSnapshot.create(
            total_committed_keur=8000.0,
            total_contributed_by_period_keur=[0.0, 4000.0, 8000.0],
            investor_ids=["LP-1"],
        )
        sp = SponsorSnapshot.create(
            investor_registry=reg,
            capital_stack=stack,
            waterfall_result_json={"total_allocated_keur": 8000.0},
        )
        d = sp.to_dict()
        restored = SponsorSnapshot.from_dict(d)
        assert restored == sp


# ===========================================================================
# SnapshotSerializer — deterministic roundtrip
# ===========================================================================

class TestSnapshotSerializer:
    def test_deterministic_ordering(self):
        """A single ProjectSnapshot.to_json() produces the same bytes every time."""
        fixed_now = aware_utc(microsecond=123456)
        ps = ProjectSnapshot.create(name="A", technology_type="solar", description="Long desc", now=fixed_now)
        json1 = ps.to_json()
        json2 = ps.to_json()
        assert json1 == json2

    def test_different_data_different_hash(self):
        ps1 = ProjectSnapshot.create(name="A", technology_type="solar")
        ps2 = ProjectSnapshot.create(name="B", technology_type="solar")
        h1 = SnapshotSerializer.compute_hash(ps1)
        h2 = SnapshotSerializer.compute_hash(ps2)
        assert h1 != h2

    def test_same_snapshot_same_hash(self):
        """SnapshotSerializer.compute_hash() is deterministic for the same snapshot."""
        fixed_now = aware_utc(microsecond=789012)
        ps = ProjectSnapshot.create(name="X", technology_type="wind", now=fixed_now)
        h1 = SnapshotSerializer.compute_hash(ps)
        h2 = SnapshotSerializer.compute_hash(ps)
        assert h1 == h2

    def test_roundtrip_project(self):
        ps = ProjectSnapshot.create(name="Test", technology_type="bess")
        data = SnapshotSerializer.serialize_to_dict(ps)
        assert data["name"] == "Test"
        assert data["technology_type"] == "bess"


# ===========================================================================
# SnapshotStore — append-only & no mutation
# ===========================================================================

class TestInMemorySnapshotStore:
    def test_save_and_load(self):
        store: InMemorySnapshotStore[ProjectSnapshot] = InMemorySnapshotStore()
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        store.save(ps)
        loaded = store.load(ps.id)
        assert loaded == ps
        assert loaded is not ps  # not same object

    def test_load_returns_copy_not_same_object(self):
        store: InMemorySnapshotStore[ProjectSnapshot] = InMemorySnapshotStore()
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        store.save(ps)
        a = store.load(ps.id)
        b = store.load(ps.id)
        assert a is not b  # each load returns a fresh copy

    def test_append_only_rejects_overwrite(self):
        store: InMemorySnapshotStore[ProjectSnapshot] = InMemorySnapshotStore()
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        store.save(ps)
        with pytest.raises(SnapshotCorruptedError, match="Append-only"):
            store.save(ps)

    def test_not_found_error(self):
        store: InMemorySnapshotStore[ProjectSnapshot] = InMemorySnapshotStore()
        with pytest.raises(SnapshotNotFoundError):
            store.load(SnapshotID.generate())

    def test_exists(self):
        store: InMemorySnapshotStore[ProjectSnapshot] = InMemorySnapshotStore()
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        assert store.exists(ps.id) is False
        store.save(ps)
        assert store.exists(ps.id) is True

    def test_list_ids_ordered(self):
        store: InMemorySnapshotStore[ProjectSnapshot] = InMemorySnapshotStore()
        p1 = ProjectSnapshot.create(name="First", technology_type="solar")
        p2 = ProjectSnapshot.create(name="Second", technology_type="wind")
        store.save(p1)
        store.save(p2)
        ids = store.list_ids()
        assert len(ids) == 2

    def test_list_snapshots(self):
        store: InMemorySnapshotStore[ProjectSnapshot] = InMemorySnapshotStore()
        p1 = ProjectSnapshot.create(name="A", technology_type="solar")
        p2 = ProjectSnapshot.create(name="B", technology_type="wind")
        store.save(p1)
        store.save(p2)
        snapshots = store.list_snapshots()
        assert len(snapshots) == 2
        assert all(s is not p1 and s is not p2 for s in snapshots)

    def test_save_does_not_mutate_source(self):
        store: InMemorySnapshotStore[ProjectSnapshot] = InMemorySnapshotStore()
        ps = ProjectSnapshot.create(name="Orig", technology_type="solar")
        ps_json_before = ps.to_json()
        store.save(ps)
        ps_json_after = ps.to_json()
        assert ps_json_before == ps_json_after  # source unchanged

    def test_multiple_snapshot_types_independent_stores(self):
        mstore = MultiSnapshotStore()
        ps = ProjectSnapshot.create(name="P", technology_type="solar")
        sc = ScenarioSnapshot.create(project_id="p1", name="S")
        mstore.projects.save(ps)
        mstore.scenarios.save(sc)
        assert mstore.projects.load(ps.id) == ps
        assert mstore.scenarios.load(sc.id) == sc
        assert not mstore.projects.exists(sc.id)

    def test_load_rejects_wrong_schema_version(self):
        """load() must raise SchemaVersionMismatchError when stored schema_version is unsupported."""
        store: InMemorySnapshotStore[ProjectSnapshot] = InMemorySnapshotStore()
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        # Manually plant a corrupted snapshot with wrong schema_version
        import copy
        corrupted = copy.deepcopy(ps)
        object.__setattr__(corrupted, "schema_version", 99)
        store.save(corrupted)
        # Confirm the corrupted snapshot is stored
        assert store.exists(ps.id)
        # load() must raise, not silently return the corrupted object
        with pytest.raises(SchemaVersionMismatchError, match="schema_version=99"):
            store.load(ps.id)


# ===========================================================================
# Immutability guarantees
# ===========================================================================

class TestImmutableBehavior:
    def test_project_snapshot_frozen(self):
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        assert hasattr(ps, "__dataclass_fields__")
        # frozen dataclass: assignment raises AttributeError
        with pytest.raises(Exception):  # frozen dataclass raises frozen_instance_error
            ps.name = "Mutated"  # type: ignore

    def test_scenario_snapshot_frozen(self):
        sc = ScenarioSnapshot.create(project_id="p1", name="Test")
        with pytest.raises(Exception):
            sc.name = "Mutated"  # type: ignore

    def test_sponsor_snapshot_frozen(self):
        reg = InvestorRegistrySnapshot.create(
            entries_json=[], total_ownership_pct=1.0, total_committed_keur=0.0,
        )
        stack = CapitalStackSnapshot.create(
            total_committed_keur=0.0, total_contributed_by_period_keur=[], investor_ids=[],
        )
        sp = SponsorSnapshot.create(
            investor_registry=reg, capital_stack=stack, waterfall_result_json={},
        )
        with pytest.raises(Exception):
            sp.investor_registry = reg  # type: ignore  # frozen

    def test_input_snapshot_frozen(self):
        inp = InputSnapshot.create(inputs_json={"key": "val"})
        with pytest.raises(Exception):
            inp.inputs_json = {}  # type: ignore

    def test_result_snapshot_frozen(self):
        rs = ResultSnapshot.create(results_json={"x": 1}, inputs_hash="a" * 64)
        with pytest.raises(Exception):
            rs.results_json = {}  # type: ignore


# ===========================================================================
# No mutation of source domain objects
# ===========================================================================

class TestNoMutationOfSource:
    def test_save_preserves_source_integrity(self):
        """Saving a snapshot must not change its contents or identity."""
        store: InMemorySnapshotStore[ProjectSnapshot] = InMemorySnapshotStore()
        ps = ProjectSnapshot.create(name="Preserved", technology_type="wind")
        original_id = str(ps.id)
        original_json = ps.to_json()
        store.save(ps)
        assert str(ps.id) == original_id
        assert ps.to_json() == original_json

    def test_load_returns_structurally_equal_not_identical(self):
        store: InMemorySnapshotStore[ProjectSnapshot] = InMemorySnapshotStore()
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        store.save(ps)
        loaded = store.load(ps.id)
        assert loaded == ps
        assert loaded is not ps  # not the same object in memory

    def test_multiple_loads_all_equal(self):
        store: InMemorySnapshotStore[ProjectSnapshot] = InMemorySnapshotStore()
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        store.save(ps)
        a = store.load(ps.id)
        b = store.load(ps.id)
        assert a == b
        assert a is not b
        assert b is not ps


# ===========================================================================
# Schema evolution preparedness
# ===========================================================================

class TestSchemaVersionOnAllTypes:
    def test_project_snapshot_has_schema_version(self):
        ps = ProjectSnapshot.create(name="Test", technology_type="solar")
        assert ps.schema_version == SCHEMA_VERSION

    def test_scenario_snapshot_has_schema_version(self):
        sc = ScenarioSnapshot.create(project_id="p1", name="Test")
        assert sc.schema_version == SCHEMA_VERSION

    def test_input_snapshot_has_schema_version(self):
        inp = InputSnapshot.create(inputs_json={})
        assert inp.schema_version == SCHEMA_VERSION

    def test_result_snapshot_has_schema_version(self):
        rs = ResultSnapshot.create(results_json={}, inputs_hash="a" * 64)
        assert rs.schema_version == SCHEMA_VERSION

    def test_sponsor_snapshot_has_schema_version(self):
        reg = InvestorRegistrySnapshot.create(
            entries_json=[], total_ownership_pct=1.0, total_committed_keur=0.0,
        )
        stack = CapitalStackSnapshot.create(
            total_committed_keur=0.0, total_contributed_by_period_keur=[], investor_ids=[],
        )
        sp = SponsorSnapshot.create(
            investor_registry=reg, capital_stack=stack, waterfall_result_json={},
        )
        assert sp.schema_version == SCHEMA_VERSION


class TestBackwardsCompatibility:
    def test_unknown_schema_version_rejected(self):
        data = {
            "id": "test-id",
            "name": "Test",
            "technology_type": "solar",
            "description": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": 99,  # unknown version
            "owner_id": None,
        }
        with pytest.raises(SchemaVersionMismatchError, match="not supported"):
            ProjectSnapshot.from_dict(data)
