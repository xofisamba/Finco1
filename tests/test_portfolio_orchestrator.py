"""Tests for portfolio orchestrator."""
import pytest
from unittest.mock import MagicMock, patch
from app.portfolio_orchestrator import (
    PortfolioMode,
    PortfolioRunOutput,
    run_portfolio_orchestrated,
)


class TestPortfolioOrchestrator:
    def test_independent_mode_returns_independent_result(self):
        mock_inputs = MagicMock()
        mock_result = MagicMock()
        mock_result.warnings = ()
        with patch('domain.portfolio.independent.runner.run_independent_portfolio', return_value=mock_result):
            output = run_portfolio_orchestrated(mock_inputs, mode="independent")
        assert output.mode == "independent"
        assert output.independent_result is mock_result
        assert output.holdco_result is None

    def test_independent_with_holdco_returns_holdco_result(self):
        mock_inputs = MagicMock()
        mock_ind_result = MagicMock()
        mock_ind_result.warnings = ()
        mock_ind_result.spv_outputs = ()
        mock_holdco_inputs = MagicMock()
        mock_holdco_result = MagicMock()
        mock_holdco_result.warnings = ()
        with patch('domain.portfolio.independent.runner.run_independent_portfolio', return_value=mock_ind_result):
            with patch('domain.portfolio.holdco.runner.build_holdco_result', return_value=mock_holdco_result):
                output = run_portfolio_orchestrated(mock_inputs, mode="independent", holdco_inputs=mock_holdco_inputs)
        assert output.holdco_result is mock_holdco_result

    def test_pooled_mode_returns_pooled_result(self):
        mock_inputs = MagicMock()
        mock_pooled = MagicMock()
        with patch('app.portfolio_runner.run_portfolio_from_inputs', return_value=mock_pooled):
            output = run_portfolio_orchestrated(mock_inputs, mode="pooled")
        assert output.mode == "pooled"
        assert output.pooled_result is mock_pooled
        assert "legacy" in output.warnings[0].lower()

    def test_pooled_with_holdco_emits_warning(self):
        mock_inputs = MagicMock()
        mock_pooled = MagicMock()
        mock_holdco = MagicMock()
        with patch('app.portfolio_runner.run_portfolio_from_inputs', return_value=mock_pooled):
            output = run_portfolio_orchestrated(mock_inputs, mode="pooled", holdco_inputs=mock_holdco)
        assert "HoldCo cannot be used" in output.warnings[-1]

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="Invalid mode"):
            run_portfolio_orchestrated(MagicMock(), mode="invalid")