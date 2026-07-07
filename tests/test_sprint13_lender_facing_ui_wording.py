from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TARGET_TEMPLATES = [
    ROOT / "app" / "templates" / "known_limitations_page.html",
    ROOT / "app" / "templates" / "partials" / "_kpi_strip.html",
    ROOT / "app" / "templates" / "partials" / "pilot_limitations_notice.html",
    ROOT / "app" / "templates" / "partials" / "pilot_help_onboarding.html",
    ROOT / "app" / "templates" / "partials" / "pilot_workflow_guide.html",
    ROOT / "app" / "templates" / "partials" / "new_project_form.html",
    ROOT / "app" / "templates" / "partials" / "debt_dscr_shl_panel.html",
    ROOT / "app" / "templates" / "partials" / "empty_states_notice.html",
    ROOT / "app" / "templates" / "partials" / "inputs_section.html",
    ROOT / "app" / "templates" / "partials" / "sheet_financials.html",
    ROOT / "app" / "templates" / "partials" / "sheet_shl.html",
    ROOT / "app" / "templates" / "partials" / "sheet_revenue.html",
    ROOT / "app" / "templates" / "partials" / "sheet_senior_debt.html",
    ROOT / "app" / "templates" / "partials" / "sheet_tax.html",
]

REMOVED_VISIBLE_WORDING = [
    "internal-use model only",
    "internal pilot mode",
    "internal review tooling",
    "internal reference workbooks",
    "not yet available",
    "not yet validated",
    "not yet configured",
    "Demo / Pilot mode",
    "Preview-only until saved",
    "coming soon",
    "static factory preview",
    "experimental, internal use only",
]

REQUIRED_REPLACEMENT_WORDING = [
    "preliminary review models",
    "reviewer evidence tooling",
    "committed reference workbooks",
    "outside current reporting scope",
    "outside current dashboard scope",
    "outside current runtime view",
    "not Excel-parity validated",
    "Draft-only until saved and re-run",
]


def _target_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in TARGET_TEMPLATES)


def test_lender_facing_ui_removed_legacy_wording():
    text = _target_text()

    for phrase in REMOVED_VISIBLE_WORDING:
        assert phrase not in text


def test_lender_facing_ui_uses_institutional_replacement_wording():
    text = _target_text()

    for phrase in REQUIRED_REPLACEMENT_WORDING:
        assert phrase in text
