from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REPORTING_SOURCE_FILES = [
    ROOT / "app" / "excel_export.py",
    ROOT / "app" / "export" / "institutional_workbook.py",
    ROOT / "app" / "export" / "registry.py",
    ROOT / "app" / "templates" / "partials" / "export_registry.html",
]

REMOVED_LENDER_FACING_PHRASES = [
    "For internal scenario review only.",
    "Screening-grade, not lender-grade or bank-certified.",
    "Not yet supported",
    "Manual or hardcoded values present",
    "Experimental - sponsor IRR is placeholder",
    "Experimental \u2014 sponsor IRR is placeholder",
    "Runtime / preview",
    "Runtime/preview",
    "runtime/preview",
    "runtime_or_preview",
    "remaining_placeholders",
    "Detailed construction schedule not exported in this branch",
    "Validated against the internal reference workbook.",
    "explicit placeholders where evidence is still pending",
    "Is Hardcoded",
    "internal sketching",
    "Coming Soon",
    "not yet available",
    "Not yet available",
]

REQUIRED_INSTITUTIONAL_PHRASES = [
    "For investment committee scenario review.",
    "Institutional review draft; external model audit required before lender reliance.",
    "Outside current reporting scope",
    "Manual or fixed assumptions present",
    "Portfolio sponsor IRR evidence unavailable in this reporting package",
    "Evidence status",
    "Detailed construction schedule is outside this report scope",
    "Runtime/evidence boundary",
    "runtime_or_evidence",
    "remaining_evidence_gaps",
    "Runtime authority remains explicit.",
    "Validated against reference workbook evidence.",
    "explicit unavailable-evidence notes where support is still pending",
    "Fixed Assumption",
    "Unavailable in current reporting package",
    "outside current package",
]


def _reporting_source_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in REPORTING_SOURCE_FILES)


def test_removed_lender_facing_export_wording_stays_removed():
    source = _reporting_source_text()

    for phrase in REMOVED_LENDER_FACING_PHRASES:
        assert phrase not in source


def test_institutional_export_wording_is_present():
    source = _reporting_source_text()

    for phrase in REQUIRED_INSTITUTIONAL_PHRASES:
        assert phrase in source


def test_sprint13_wording_guardrail_does_not_touch_calculation_engines():
    no_go_paths = [
        ROOT / "app" / "waterfall_core.py",
        ROOT / "app" / "services" / "run_service.py",
        ROOT / "app" / "project_factories.py",
    ]

    for path in no_go_paths:
        assert path.exists(), f"Expected no-go path to remain present: {path}"
