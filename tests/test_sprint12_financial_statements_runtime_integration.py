from __future__ import annotations

from pathlib import Path

from jinja2 import Environment


REPO_ROOT = Path(__file__).resolve().parents[1]
SHEET = REPO_ROOT / "app" / "templates" / "partials" / "sheet_financials.html"


def _dummy_financial_statements() -> dict:
    return {
        "source": "assemble_financial_statements(WaterfallResult)",
        "pnl": {
            "periods": [
                {
                    "date": "2027-06-30",
                    "revenues_keur": 1000.0,
                    "operating_expenses_keur": -200.0,
                    "depreciation_keur": -50.0,
                    "ebit_keur": 750.0,
                    "senior_interest_expense_keur": -40.0,
                    "shl_interest_expense_keur": -10.0,
                    "earnings_before_tax_keur": 700.0,
                    "cit_accrual_keur": -126.0,
                    "net_income_keur": 574.0,
                    "retained_earnings_keur": 574.0,
                    "net_dividends_keur": 0.0,
                }
            ]
        },
        "balance_sheet": {
            "periods": [
                {
                    "date": "2027-06-30",
                    "net_fixed_assets_keur": 9000.0,
                    "dsra_balance_keur": 100.0,
                    "cash_keur": 250.0,
                    "total_assets_keur": 9350.0,
                    "share_capital_keur": 1000.0,
                    "retained_earnings_keur": 574.0,
                    "shl_balance_keur": 1200.0,
                    "senior_balance_keur": 6576.0,
                    "total_liabilities_equity_keur": 9350.0,
                    "balance_check_keur": 0.0,
                }
            ]
        },
        "pf_cash_waterfall": {
            "periods": [
                {
                    "date": "2027-06-30",
                    "revenue_cash_keur": 1000.0,
                    "opex_cash_keur": -200.0,
                    "ebitda_cash_keur": 800.0,
                    "cash_tax_keur": -126.0,
                    "fcf_banks_keur": 674.0,
                    "senior_total_ds_keur": -300.0,
                    "dsra_funding_keur": 0.0,
                    "dsra_release_keur": 0.0,
                    "fcf_junior_keur": 374.0,
                    "fcf_for_distribution_keur": 374.0,
                    "net_dividends_keur": 0.0,
                }
            ]
        },
    }


def _render(**ctx) -> str:
    template = Environment().from_string(SHEET.read_text(encoding="utf-8"))
    return template.render(**ctx)


def test_financial_statements_sheet_server_renders_canonical_runtime_payload():
    html = _render(financial_statements=_dummy_financial_statements())

    assert 'data-fs-source="canonical-runtime-financial-statements"' in html
    assert 'id="fs-statements-block"' in html
    assert 'id="fs-unavailable-panel"\n     style="display:none;"' in html
    assert "Revenue" in html
    assert "1000" in html
    assert "Total Assets" in html
    assert "9350" in html
    assert "FCF for Banks" in html
    assert "674" in html


def test_financial_statements_sheet_preserves_pre_run_unavailable_state():
    html = _render()

    assert 'id="fs-unavailable-panel"' in html
    assert 'id="fs-statements-block" style="display:none;"' in html
    assert 'data-fs-source="session-storage-runtime-fallback"' in html
    assert "No model results available." in html
    assert "Run the model to generate financial statements." in html


def test_run_route_active_sheet_oob_passes_financial_statements_context():
    source = (REPO_ROOT / "main_web.py").read_text(encoding="utf-8")

    assert '"financial_statements": outcome.context.get("financial_statements")' in source


def test_run_service_returns_financial_statements_in_all_success_contexts():
    source = (REPO_ROOT / "app" / "services" / "run_service.py").read_text(encoding="utf-8")

    assert source.count('"financial_statements": result.get("financial_statements")') >= 3


def test_sessionstorage_fallback_clears_rows_before_rendering():
    source = SHEET.read_text(encoding="utf-8")

    assert "headRow.innerHTML = \"\";" in source
    assert "tbody.innerHTML = \"\";" in source


def test_financial_statements_sheet_does_not_render_developer_source_copy():
    html = _render(financial_statements=_dummy_financial_statements())

    assert "assemble_financial_statements(WaterfallResult)" not in html
