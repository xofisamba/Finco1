"""U8-EXTERNAL-PILOT-GUIDE: docs-only addition of an external pilot guide.

Verifies docs/external_pilot_guide.md exists, covers the 8 required
sections, and includes the required disclaimer wording. Docs-only --
no code, engine, or template changes.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GUIDE_PATH = REPO_ROOT / "docs" / "external_pilot_guide.md"

REQUIRED_SECTIONS = (
    "## 1. Create a Project",
    "## 2. Edit Inputs",
    "## 3. Run the Model",
    "## 4. Validation Status",
    "## 5. Create a Scenario",
    "## 6. Compare Scenarios",
    "## 7. Export Results",
    "## 8. Known Limitations",
)

DISCLAIMER = (
    "Outputs are financial modelling estimates and not legal, "
    "tax, accounting or investment advice."
)


def test_guide_file_exists():
    assert GUIDE_PATH.exists(), "docs/external_pilot_guide.md must exist"


def test_guide_covers_all_required_sections():
    text = GUIDE_PATH.read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert section in text, f"guide missing required section: {section!r}"


def test_guide_sections_in_order():
    text = GUIDE_PATH.read_text(encoding="utf-8")
    positions = [text.index(section) for section in REQUIRED_SECTIONS]
    assert positions == sorted(positions), (
        "guide sections must appear in the specified order"
    )


def test_guide_contains_disclaimer():
    text = GUIDE_PATH.read_text(encoding="utf-8")
    assert DISCLAIMER in text, "guide must contain the required disclaimer text"


def test_guide_is_reasonably_substantial():
    text = GUIDE_PATH.read_text(encoding="utf-8")
    # Roughly 5-10 pages equivalent; a generous lower-bound word check.
    word_count = len(text.split())
    assert word_count > 800, (
        f"guide should be substantial (5-10 pages equivalent), got "
        f"{word_count} words"
    )


def test_guide_section_8_stays_in_sync_with_known_limitations_page():
    """U6 added a DSCR caveat, a sensitivity-testing observation, and an
    advanced debt-sculpting/cash-sweep "not yet supported" item to the
    Known Limitations page. Section 8 of this guide summarizes that page,
    so it must mention the same items rather than going stale."""
    text = GUIDE_PATH.read_text(encoding="utf-8")
    section_8 = text[text.index("## 8. Known Limitations"):]
    assert "sensitivity-testing" in section_8.lower()
    assert "cash-sweep" in section_8.lower()
    assert "DSCR figures" in section_8 or "DSCR" in section_8
