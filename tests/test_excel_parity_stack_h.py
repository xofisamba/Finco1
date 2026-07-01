"""Excel Parity Stack H — Sponsor Engine Runtime Handoff characterization tests.

Verifies:
- _run_sponsor_engine() and _serialize_sponsor_schedule() are defined
- run_service.py threads sponsor_schedule through all 3 paths
- sessionStorage["lastSponsorSchedule"] is wired
- _sheet_sponsor_partial.html renders from lastSponsorSchedule
- pre-Run unavailable panel remains
- No client-side JS calculations
- No sponsor engine internals modified
- Engine remains single source of truth
"""
import os
import re

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def project_runner_src():
    path = os.path.join(PROJECT_ROOT, "app/api/project_runner.py")
    return open(path, encoding="utf-8").read()


@pytest.fixture(scope="module")
def run_service_src():
    path = os.path.join(PROJECT_ROOT, "app/services/run_service.py")
    return open(path, encoding="utf-8").read()


@pytest.fixture(scope="module")
def sponsor_template():
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/_sheet_sponsor_partial.html")
    return open(path, encoding="utf-8").read()


@pytest.fixture(scope="module")
def tuho_sponsor_payload():
    from app.ui_runner import run_demo_project
    from app.api.project_runner import _run_sponsor_engine, _serialize_sponsor_schedule
    demo = run_demo_project("TUHO", "Base")
    result = demo.result
    sponsor_result = _run_sponsor_engine(result, demo.project_inputs, "TUHO")
    assert sponsor_result is not None, "TUHO sponsor engine returned None"
    cf, irr, moic = sponsor_result
    return _serialize_sponsor_schedule(cf, irr, moic)


@pytest.fixture(scope="module")
def oborovo_sponsor_payload():
    from app.ui_runner import run_demo_project
    from app.api.project_runner import _run_sponsor_engine, _serialize_sponsor_schedule
    demo = run_demo_project("Oborovo", "Base")
    result = demo.result
    sponsor_result = _run_sponsor_engine(result, demo.project_inputs, "Oborovo")
    assert sponsor_result is not None, "Oborovo sponsor engine returned None"
    cf, irr, moic = sponsor_result
    return _serialize_sponsor_schedule(cf, irr, moic)


# ── H1: Sponsor engine bridge defined ────────────────────────────────────────

class TestSponsorEngineBridgeDefined:

    def test_run_sponsor_engine_defined(self, project_runner_src):
        assert "def _run_sponsor_engine(" in project_runner_src

    def test_serialize_sponsor_schedule_defined(self, project_runner_src):
        assert "def _serialize_sponsor_schedule(" in project_runner_src

    def test_sponsor_schedule_in_return_dict(self, project_runner_src):
        assert '"sponsor_schedule": sponsor_schedule_payload' in project_runner_src

    def test_sponsor_capital_structures_defined(self, project_runner_src):
        assert "_SPONSOR_CAPITAL_STRUCTURES" in project_runner_src
        assert '"TUHO"' in project_runner_src
        assert '"Oborovo"' in project_runner_src

    def test_run_sponsor_engine_uses_phase7a_runner(self, project_runner_src):
        assert "run_sponsor_cashflows" in project_runner_src
        assert "SponsorCashflowRunnerInputs" in project_runner_src

    def test_run_sponsor_engine_uses_phase7b_runner(self, project_runner_src):
        assert "run_sponsor_irr" in project_runner_src
        assert "run_sponsor_moic" in project_runner_src

    def test_no_domain_modifications(self):
        """domain/sponsor/ files must not import from app/."""
        sponsor_dir = os.path.join(PROJECT_ROOT, "domain/sponsor")
        for fname in os.listdir(sponsor_dir):
            if not fname.endswith(".py"):
                continue
            content = open(os.path.join(sponsor_dir, fname), encoding="utf-8").read()
            assert "from app." not in content, f"{fname} imports from app/ (circular)"
            assert "import app." not in content, f"{fname} imports from app/ (circular)"


# ── H2: run_service.py wiring ─────────────────────────────────────────────────

class TestRunServiceSponsorrWiring:

    def test_sponsor_schedule_param_in_build_tag(self, run_service_src):
        assert 'sponsor_schedule: "dict | None" = None' in run_service_src or \
               "sponsor_schedule=None" in run_service_src

    def test_last_sponsor_schedule_setitem(self, run_service_src):
        assert 'lastSponsorSchedule' in run_service_src
        assert 'sessionStorage.setItem("lastSponsorSchedule"' in run_service_src

    def test_last_sponsor_schedule_removeitem(self, run_service_src):
        assert 'sessionStorage.removeItem("lastSponsorSchedule")' in run_service_src

    def test_sponsor_schedule_threaded_3_paths(self, run_service_src):
        assert run_service_src.count('sponsor_schedule=result.get("sponsor_schedule")') >= 3

    def test_no_sponsor_calculations_in_run_service(self, run_service_src):
        assert "run_sponsor_cashflows" not in run_service_src
        assert "SponsorCashflowRunnerInputs" not in run_service_src


# ── H3: Template wiring ───────────────────────────────────────────────────────

class TestSponsorTemplateWiring:

    def test_last_sponsor_schedule_read_in_js(self, sponsor_template):
        assert 'lastSponsorSchedule' in sponsor_template
        assert 'sessionStorage.getItem("lastSponsorSchedule")' in sponsor_template

    def test_sponsor_schedule_block_present(self, sponsor_template):
        assert 'id="sponsor-schedule-block"' in sponsor_template

    def test_sponsor_unavailable_panel_present(self, sponsor_template):
        assert "sponsor-unavailable-panel" in sponsor_template or \
               "empty-state-notice" in sponsor_template

    def test_no_inline_style_blocks(self, sponsor_template):
        inline_styles = re.findall(r'<style[^>]*>', sponsor_template, re.IGNORECASE)
        assert not inline_styles

    def test_no_js_arithmetic(self, sponsor_template):
        """No financial calculations in the template JS."""
        script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', sponsor_template,
                                   re.DOTALL | re.IGNORECASE)
        for block in script_blocks:
            lines = block.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('//') or not stripped:
                    continue
                # Reject arithmetic that looks like financial calculations
                # (multiplication of financial variables)
                assert not re.search(r'\bkeur\b.*\*.*\bkeur\b', stripped, re.IGNORECASE), \
                    f"Possible JS financial calculation: {stripped}"

    def test_template_reads_summary_fields(self, sponsor_template):
        assert "gross_sponsor_irr" in sponsor_template or "summary" in sponsor_template


# ── H4: Characterization — TUHO ──────────────────────────────────────────────

class TestTuhoSponsorPayload:

    def test_payload_not_none(self, tuho_sponsor_payload):
        assert tuho_sponsor_payload is not None

    def test_payload_has_required_keys(self, tuho_sponsor_payload):
        assert "periods" in tuho_sponsor_payload
        assert "summary" in tuho_sponsor_payload
        assert "source" in tuho_sponsor_payload

    def test_periods_non_empty(self, tuho_sponsor_payload):
        assert len(tuho_sponsor_payload["periods"]) > 0

    def test_periods_have_required_fields(self, tuho_sponsor_payload):
        p = tuho_sponsor_payload["periods"][0]
        assert "period_index" in p
        assert "equity_injected_keur" in p
        assert "distribution_received_keur" in p
        assert "wht_on_distribution_keur" in p
        assert "net_cashflow_keur" in p
        assert "capital_account_balance_keur" in p

    def test_summary_has_required_fields(self, tuho_sponsor_payload):
        s = tuho_sponsor_payload["summary"]
        assert "total_equity_injected_keur" in s
        assert "total_distributions_received_keur" in s
        assert "gross_sponsor_irr" in s
        assert "gross_sponsor_moic" in s
        assert "xirr_converged" in s
        assert "investor_id" in s

    def test_xirr_converged(self, tuho_sponsor_payload):
        assert tuho_sponsor_payload["summary"]["xirr_converged"] is True

    def test_equity_injected_positive(self, tuho_sponsor_payload):
        assert tuho_sponsor_payload["summary"]["total_equity_injected_keur"] > 0

    def test_distributions_positive(self, tuho_sponsor_payload):
        assert tuho_sponsor_payload["summary"]["total_distributions_received_keur"] > 0

    def test_irr_is_float(self, tuho_sponsor_payload):
        irr = tuho_sponsor_payload["summary"]["gross_sponsor_irr"]
        assert isinstance(irr, (int, float))

    def test_moic_is_float(self, tuho_sponsor_payload):
        moic = tuho_sponsor_payload["summary"]["gross_sponsor_moic"]
        assert isinstance(moic, (int, float))

    def test_no_nan_or_inf_in_periods(self, tuho_sponsor_payload):
        import math
        for p in tuho_sponsor_payload["periods"]:
            for k, v in p.items():
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    assert not math.isnan(v), f"NaN in period field {k}"
                    assert not math.isinf(v), f"Inf in period field {k}"

    def test_source_field(self, tuho_sponsor_payload):
        assert "SponsorCashflowRunner" in tuho_sponsor_payload["source"]

    def test_period_count_matches_waterfall(self, tuho_sponsor_payload):
        from app.ui_runner import run_demo_project
        demo = run_demo_project("TUHO", "Base")
        waterfall_period_count = len(demo.result.periods)
        assert len(tuho_sponsor_payload["periods"]) == waterfall_period_count


# ── H5: Characterization — Oborovo ────────────────────────────────────────────

class TestOborovoSponsorPayload:

    def test_payload_not_none(self, oborovo_sponsor_payload):
        assert oborovo_sponsor_payload is not None

    def test_periods_non_empty(self, oborovo_sponsor_payload):
        assert len(oborovo_sponsor_payload["periods"]) > 0

    def test_xirr_converged(self, oborovo_sponsor_payload):
        assert oborovo_sponsor_payload["summary"]["xirr_converged"] is True

    def test_irr_is_float(self, oborovo_sponsor_payload):
        irr = oborovo_sponsor_payload["summary"]["gross_sponsor_irr"]
        assert isinstance(irr, (int, float))


# ── H6: Guardrail checks ──────────────────────────────────────────────────────

class TestStackHGuardrails:

    def test_waterfall_core_not_modified(self):
        """waterfall_core.py must not import from domain/sponsor."""
        path = os.path.join(PROJECT_ROOT, "app/waterfall_core.py")
        content = open(path, encoding="utf-8").read()
        assert "domain.sponsor" not in content
        assert "SponsorCashflowRunner" not in content

    def test_project_factories_not_modified(self):
        """project_factories.py must not contain sponsor wiring."""
        path = os.path.join(PROJECT_ROOT, "app/project_factories.py")
        content = open(path, encoding="utf-8").read()
        assert "SponsorCashflowRunnerInputs" not in content
        assert "_serialize_sponsor_schedule" not in content

    def test_no_duplicate_sponsor_calc_in_runner(self, project_runner_src):
        """project_runner.py must delegate to domain engine, not reimplement."""
        assert "xirr_with_convergence" not in project_runner_src
        assert "def run_sponsor_cashflows" not in project_runner_src

    def test_sponsor_engine_failure_degrades_gracefully(self, project_runner_src):
        """Sponsor engine failure must not break the run path."""
        assert "except Exception:" in project_runner_src
        assert "sponsor_schedule_payload = None" in project_runner_src

    def test_input_adapter_not_modified(self):
        path = os.path.join(PROJECT_ROOT, "app/input_adapter.py")
        content = open(path, encoding="utf-8").read()
        assert "_run_sponsor_engine" not in content
        assert "_serialize_sponsor_schedule" not in content


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
