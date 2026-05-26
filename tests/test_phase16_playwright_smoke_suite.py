from __future__ import annotations

import csv
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest


BASE_DIR = Path(__file__).resolve().parents[1]


def _read_text(*parts: str) -> str:
    return (BASE_DIR.joinpath(*parts)).read_text(encoding="utf-8")


def _read_csv(*parts: str) -> list[dict[str, str]]:
    with BASE_DIR.joinpath(*parts).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _wait_for_public_health(base_url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/public-health", timeout=2.0) as response:
                body = response.read().decode("utf-8", errors="replace")
                if response.status == 200 and '"status":"ok"' in body.replace(" ", ""):
                    return
        except Exception as exc:  # pragma: no cover - only used on live-browser path
            last_error = exc
            time.sleep(0.25)
            continue
        time.sleep(0.25)
    raise AssertionError(f"Local app did not become healthy at {base_url!r}; last error={last_error!r}")


def test_docs_and_reports_describe_optional_playwright_scope_honestly():
    docs = _read_text("docs", "phase16_playwright_smoke_suite.md")
    smoke = _read_text("reports", "phase16_playwright_smoke_matrix.csv")
    closure = _read_text("reports", "phase16_browser_automation_gap_closure.csv")
    deps = _read_text("reports", "phase16_playwright_optional_dependency_matrix.csv")

    assert "optional" in docs and "Playwright smoke suite" in docs
    assert "If the Python Playwright package is missing, the live-browser smoke test skips" in docs
    assert "Runtime remains backend-authoritative." in docs
    assert "Frontend/browser state does not become runtime authority." in docs
    assert "Browser smoke does not fabricate pilot evidence." in docs
    assert "`G20` remains `BLOCKED`." in docs
    assert "`R99/R102` remain `NOT APPROVED`." in docs

    lowered = docs.lower()
    for forbidden in ("lender-ready", "audit-certified", "saas", "multi-tenant ready"):
        assert forbidden not in lowered

    assert "OPTIONAL_NOT_RUN" in smoke
    assert "partially_closed_optional_playwright_suite_added" in closure
    assert "playwright,no,yes" in deps
    assert "chromium_browser_binaries,no,yes" in deps


def test_optional_dependency_reports_and_statuses_are_explicit():
    smoke_rows = _read_csv("reports", "phase16_playwright_smoke_matrix.csv")
    dep_rows = _read_csv("reports", "phase16_playwright_optional_dependency_matrix.csv")
    closure_rows = _read_csv("reports", "phase16_browser_automation_gap_closure.csv")

    expected_ids = {
        "pw-001",
        "pw-002",
        "pw-003",
        "pw-004",
        "pw-005",
        "pw-006",
        "pw-007",
        "pw-008",
        "pw-009",
    }
    assert {row["smoke_id"] for row in smoke_rows} == expected_ids

    allowed_statuses = {"PASS", "FAIL", "OPTIONAL_NOT_RUN", "NOT_APPLICABLE"}
    assert all(row["status"] in allowed_statuses for row in smoke_rows)
    assert any(row["status"] == "OPTIONAL_NOT_RUN" for row in smoke_rows)
    assert any(
        row["browser_check"] == "optional_browser_suite_gates_cleanly"
        and row["status"] == "PASS"
        for row in smoke_rows
    )

    dep_map = {row["dependency"]: row for row in dep_rows}
    assert dep_map["playwright"]["required_for_standard_suite_yes_no"] == "no"
    assert dep_map["playwright"]["required_for_optional_browser_suite_yes_no"] == "yes"
    assert "skips" in dep_map["playwright"]["behavior_if_missing"].lower()
    assert dep_map["chromium_browser_binaries"]["required_for_standard_suite_yes_no"] == "no"
    assert dep_map["chromium_browser_binaries"]["required_for_optional_browser_suite_yes_no"] == "yes"

    assert any(row["closure_status"] == "still_open" for row in closure_rows)


def test_optional_playwright_live_browser_smoke():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run live browser smoke",
    )

    port = _pick_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
    env.setdefault("FINCO_COOKIE_SECURE", "false")

    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main_web:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(BASE_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    browser = None
    playwright_context = None
    try:
        _wait_for_public_health(base_url)

        sync_playwright = playwright.sync_playwright
        try:
            playwright_context = sync_playwright().start()
            browser = playwright_context.chromium.launch()
        except Exception as exc:  # pragma: no cover - environment-dependent
            pytest.skip(f"OPTIONAL_BROWSER_DEPENDENCY_MISSING_BROWSER_BINARIES: {exc}")

        page_errors: list[str] = []
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        page.goto(f"{base_url}/public-health", wait_until="networkidle")
        assert "ok" in page.text_content("body")

        page.goto(f"{base_url}/login", wait_until="networkidle")
        assert page.locator("h1.login-title").text_content().strip() == "Sign in"
        assert page.locator('input[name="username"]').count() == 1
        assert page.locator('input[name="password"]').count() == 1

        username = os.environ.get("FINCO_E2E_USERNAME") or os.environ.get("FINCO_ADMIN_USER")
        password = os.environ.get("FINCO_E2E_PASSWORD") or os.environ.get("FINCO_ADMIN_PASSWORD")
        if not username or not password:
            pytest.skip("E2E credentials not configured: set FINCO_E2E_USERNAME and FINCO_E2E_PASSWORD")
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        page.locator("#project-selector").wait_for(state="visible", timeout=10000)

        assert page.locator("#ps-tuho").count() == 1
        assert page.locator("#ps-oborovo").count() == 1

        # The base.html shell div and the HTMX partial both carry several IDs
        # (saved-scenario-panel, btn-run-model, btn-compare-draft, btn-save-run,
        # workspace-content, etc.).  After HTMX partial swap both copies remain
        # live in the DOM.  Count >= 1 is the correct presence assertion for all
        # of these — the intent is "element is present and usable", not
        # "exactly one occurrence exists globally".
        assert page.locator("#saved-scenario-panel").count() >= 1
        assert page.locator("#workspace-content").count() >= 1
        assert page.locator("[data-grid-source]").count() >= 1
        assert page.locator("#workspace-unsaved-banner").count() >= 1
        assert page.locator("#workspace-strip-dirty").count() >= 1
        assert page.locator("#btn-run-model").count() >= 1
        assert page.locator("#btn-compare-draft").count() >= 1
        assert page.locator("#btn-save-run").count() >= 1

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(150)
        assert page.locator("#project-selector").count() >= 1
        assert page.locator("#workspace-content").count() >= 1

        assert not page_errors
    finally:
        if browser is not None:
            browser.close()
        if playwright_context is not None:
            playwright_context.stop()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive cleanup
            process.kill()
            process.wait(timeout=10)