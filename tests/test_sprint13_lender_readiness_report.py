from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "sprint13_institutional_validation" / "sprint13_lender_readiness_report.md"


REQUIRED_SECTIONS = (
    "Overall institutional readiness",
    "Remaining UI gaps",
    "Remaining reporting gaps",
    "Remaining runtime gaps",
    "Remaining export gaps",
    "Commercial readiness",
    "Pilot readiness",
    "Top 10 remaining improvements",
    "Estimated days remaining until v1.0 pilot freeze",
    "GO / NO-GO",
)


def test_sprint13_lender_readiness_report_exists():
    assert REPORT.exists()


def test_sprint13_lender_readiness_report_has_required_sections():
    text = REPORT.read_text(encoding="utf-8")

    for section in REQUIRED_SECTIONS:
        assert section in text


def test_sprint13_lender_readiness_report_preserves_no_go_confirmations():
    text = REPORT.read_text(encoding="utf-8")

    for phrase in (
        "No financial equation changes.",
        "No tax engine changes.",
        "No debt engine changes.",
        "No Financial Statement engine changes.",
        "No persistence changes.",
        "No schema changes.",
        "No parity target changes.",
        "No project factory changes.",
    ):
        assert phrase in text
