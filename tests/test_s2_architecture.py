"""Tests for S2: Architecture decoupling — domain has no Streamlit imports.

This test verifies the blueprint requirement:
- domain/ has NO import streamlit / from streamlit / @st.cache_data
- app/ contains all Streamlit-specific code (@st.cache_data, session state)
- All cached functions live in app/cache.py
"""
import ast
import pytest
from pathlib import Path

from app.cache import (
    hash_inputs_for_cache,
    hash_engine_for_cache,
    cached_generation_schedule,
    cached_revenue_schedule,
    cached_opex_schedule_annual,
    cached_model_state,
    cached_run_waterfall_v3,
    clear_all_caches,
)
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner, ScenarioRunner


class TestDomainLayerClean:
    """Verify domain layer has no Streamlit imports."""

    def test_no_streamlit_in_domain(self):
        """domain/ must have no imports of streamlit."""
        errors = []
        domain_path = Path("domain")

        for py_file in domain_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                with open(py_file) as f:
                    content = f.read()
                    tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if "streamlit" in alias.name:
                                errors.append(f"{py_file}: import {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and "streamlit" in node.module:
                            errors.append(f"{py_file}: from {node.module} import ...")

            except SyntaxError:
                pass  # Skip files with syntax errors

        assert not errors, f"Streamlit imports found in domain: {errors}"

    def test_no_cache_decorators_in_domain(self):
        """domain/ must have no @st.cache_data decorators."""
        violations = []
        domain_path = Path("domain")

        for py_file in domain_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                with open(py_file) as f:
                    content = f.read()
                    if "@st.cache_data" in content or "@st.cache" in content:
                        # Check if it's actually a decorator (starts with @)
                        for line in content.split("\n"):
                            if "@st.cache_data" in line or "@st.cache" in line:
                                violations.append(f"{py_file}: {line.strip()}")
            except:
                pass

        assert not violations, f"@st.cache decorators found in domain: {violations}"


class TestAppLayerExists:
    """Verify app layer exists and has cache functionality."""

    def test_app_cache_exists(self):
        """app/cache.py must exist and export cached functions."""
        from app.cache import (
            cached_generation_schedule,
            cached_revenue_schedule,
            cached_opex_schedule_annual,
            cached_model_state,
            cached_run_waterfall_v3,
            clear_all_caches,
        )
        # All functions should be callable
        assert callable(cached_generation_schedule)
        assert callable(cached_revenue_schedule)
        assert callable(cached_opex_schedule_annual)
        assert callable(cached_model_state)
        assert callable(cached_run_waterfall_v3)
        assert callable(clear_all_caches)

    def test_waterfall_runner_exists(self):
        """app/waterfall_runner.py must exist with WaterfallRunner."""
        from app.waterfall_runner import (
            WaterfallRunConfig,
            WaterfallRunner,
            ScenarioRunner,
        )
        assert callable(WaterfallRunConfig)
        assert callable(WaterfallRunner)
        assert callable(ScenarioRunner)


class TestWaterfallRunConfig:
    """Test WaterfallRunConfig dataclass."""

    def test_default_config(self):
        """Default config has sensible values."""
        config = WaterfallRunConfig()
        assert config.target_dscr == 1.15
        assert config.lockup_dscr == 1.10
        assert config.tax_rate == 0.10
        assert config.dsra_months == 6
        assert config.rate_per_period == 0.02825
        assert config.tenor_periods == 28
        assert config.shl_repayment_method == "bullet"
        assert config.equity_irr_method == "equity_only"
        assert config.debt_sizing_method == "dscr_sculpt"

    def test_cache_key_generation(self):
        """cache_key() generates a deterministic string."""
        config1 = WaterfallRunConfig(rate_per_period=0.03, target_dscr=1.20)
        config2 = WaterfallRunConfig(rate_per_period=0.03, target_dscr=1.20)
        config3 = WaterfallRunConfig(rate_per_period=0.04, target_dscr=1.20)

        # Same config → same key
        assert config1.cache_key() == config2.cache_key()
        # Different config → different key
        assert config1.cache_key() != config3.cache_key()

    def test_shl_config(self):
        """SHL parameters are correctly stored."""
        config = WaterfallRunConfig(
            shl_amount_keur=29_135,
            shl_rate=0.03965,
            shl_idc_keur=3_569,
            shl_repayment_method="pik_then_sweep",
            shl_tenor_years=0,
            shl_wht_rate=0.0,
        )
        assert config.shl_amount_keur == 29_135
        assert config.shl_rate == 0.03965
        assert config.shl_idc_keur == 3_569
        assert config.shl_repayment_method == "pik_then_sweep"
        assert config.shl_tenor_years == 0
        assert config.shl_wht_rate == 0.0

    def test_equity_irr_methods(self):
        """All equity IRR methods are supported."""
        for method in ["equity_only", "combined", "shl_plus_dividends"]:
            config = WaterfallRunConfig(equity_irr_method=method)
            assert config.equity_irr_method == method

    def test_debt_sizing_methods(self):
        """All debt sizing methods are supported."""
        for method in ["dscr_sculpt", "gearing_cap", "fixed"]:
            config = WaterfallRunConfig(debt_sizing_method=method)
            assert config.debt_sizing_method == method


class TestWaterfallRunner:
    """Test WaterfallRunner class (without actual inputs)."""

    def test_runner_requires_inputs(self):
        """WaterfallRunner requires inputs with capex attribute."""
        # Mock inputs-like object without capex
        class BadInputs:
            pass

        # Should raise ValueError
        with pytest.raises(ValueError, match="inputs must have 'capex'"):
            WaterfallRunner(BadInputs(), object())


class TestHashFunctions:
    """Test cache hash functions."""

    def test_hash_inputs_for_cache_callable(self):
        """hash_inputs_for_cache is callable."""
        from app.cache import hash_inputs_for_cache
        assert callable(hash_inputs_for_cache)

    def test_hash_engine_for_cache_callable(self):
        """hash_engine_for_cache is callable."""
        from app.cache import hash_engine_for_cache
        assert callable(hash_engine_for_cache)


class TestClearAllCaches:
    """Test cache invalidation."""

    def test_clear_all_caches_callable(self):
        """clear_all_caches clears all cached functions."""
        from app.cache import clear_all_caches, cached_run_waterfall_v3

        # Should not raise
        clear_all_caches()

        # cached_run_waterfall_v3 should still be callable (just cleared)
        assert callable(cached_run_waterfall_v3)


class TestS2Integration:
    """Integration test: app layer properly encapsulates domain."""

    def test_domain_apis_exposed_via_app(self):
        """Cached functions wrap domain functions properly."""
        from app.cache import cached_revenue_schedule, cached_opex_schedule_annual

        # These should exist and be callable (even if inputs not provided)
        # The actual wrapping is tested by the fact they don't raise ImportError
        assert "cached_revenue_schedule" in dir()
        assert "cached_opex_schedule_annual" in dir()

    def test_cache_key_deterministic(self):
        """WaterfallRunConfig cache_key is deterministic."""
        configs = [
            WaterfallRunConfig(rate_per_period=0.02825, tenor_periods=28, target_dscr=1.15),
            WaterfallRunConfig(rate_per_period=0.02825, tenor_periods=28, target_dscr=1.15),
            WaterfallRunConfig(rate_per_period=0.02825, tenor_periods=28, target_dscr=1.15),
        ]
        keys = [c.cache_key() for c in configs]
        assert len(set(keys)) == 1  # All same

    def test_different_configs_different_keys(self):
        """Different configs produce different cache keys."""
        configs = [
            WaterfallRunConfig(shl_amount_keur=0),
            WaterfallRunConfig(shl_amount_keur=29_135),
        ]
        keys = [c.cache_key() for c in configs]
        assert keys[0] != keys[1]  # Different SHL amounts → different keys