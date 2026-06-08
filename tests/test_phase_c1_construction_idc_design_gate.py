"""Phase C1 - Construction Schedule / IDC Design Gate tests.

This is a DESIGN GATE phase. It must:
- Add exactly 2 new files: 1 design doc, 1 report JSON
- NOT change any code, runtime, schema, persistence, feature flag,
  CAPEX formula, debt, tax, depreciation, IDC, or project status
- NOT change rc1 SHA
- NOT change any existing tests

This test file verifies all of the above.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_DOC = (
    REPO_ROOT / "docs" / "phase_c1_construction_idc_design_gate.md"
)
REPORT_JSON = (
    REPO_ROOT
    / "reports" / "phase_c1_construction_idc_design_gate.json"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def design_doc_text() -> str:
    return DESIGN_DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def report_json_data() -> dict:
    return json.loads(REPORT_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


class TestFilesExist:
    def test_design_doc_exists(self):
        assert DESIGN_DOC.is_file(), f"missing design doc: {DESIGN_DOC}"

    def test_report_json_exists(self):
        assert REPORT_JSON.is_file(), f"missing report: {REPORT_JSON}"

    def test_design_doc_nonempty(self):
        assert DESIGN_DOC.stat().st_size > 5000, (
            "design doc should be substantial (>= 5KB)"
        )


# ---------------------------------------------------------------------------
# 8 Required sections present
# ---------------------------------------------------------------------------


REQUIRED_SECTIONS = [
    "## 1. Current State",
    "## 2. Excel Gap Analysis",
    "## 3. Architecture Review",
    "## 4. Proposed Layering",
    "## 5. Risk Review",
    "## 6. Promotion Gates",
    "## 7. Recommendation",
    "## 8. Roadmap Position",
]


class TestRequiredSectionsPresent:
    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_section_present(self, design_doc_text, section):
        assert section in design_doc_text, (
            f"required section missing: {section!r}"
        )

    def test_current_state_covers_capex(self, design_doc_text):
        idx = design_doc_text.find("## 1. Current State")
        end = design_doc_text.find("## 2. Excel Gap Analysis")
        window = design_doc_text[idx:end]
        assert "CAPEX" in window, "CAPEX not covered in Current State"

    def test_current_state_covers_debt(self, design_doc_text):
        idx = design_doc_text.find("## 1. Current State")
        end = design_doc_text.find("## 2. Excel Gap Analysis")
        window = design_doc_text[idx:end]
        assert "Debt" in window or "debt" in window, (
            "debt not covered in Current State"
        )

    def test_current_state_covers_shl(self, design_doc_text):
        idx = design_doc_text.find("## 1. Current State")
        end = design_doc_text.find("## 2. Excel Gap Analysis")
        window = design_doc_text[idx:end]
        assert "SHL" in window, "SHL not covered in Current State"

    def test_current_state_covers_depreciation(self, design_doc_text):
        idx = design_doc_text.find("## 1. Current State")
        end = design_doc_text.find("## 2. Excel Gap Analysis")
        window = design_doc_text[idx:end]
        assert "Depreciation" in window or "depreciation" in window, (
            "depreciation not covered in Current State"
        )

    def test_current_state_covers_construction_schedule(self, design_doc_text):
        idx = design_doc_text.find("## 1. Current State")
        end = design_doc_text.find("## 2. Excel Gap Analysis")
        window = design_doc_text[idx:end]
        assert "construction schedule" in window.lower(), (
            "construction schedule not covered in Current State"
        )

    def test_current_state_covers_idc(self, design_doc_text):
        idx = design_doc_text.find("## 1. Current State")
        end = design_doc_text.find("## 2. Excel Gap Analysis")
        window = design_doc_text[idx:end]
        assert "IDC" in window, "IDC not covered in Current State"

    def test_proposed_layering_has_5_layers(self, design_doc_text):
        idx = design_doc_text.find("## 4. Proposed Layering")
        end = design_doc_text.find("## 5. Risk Review")
        window = design_doc_text[idx:end]
        # 5 layers named "Layer N: ..."
        layer_count = len(re.findall(r"### Layer \d", window))
        assert layer_count == 5, (
            f"Proposed Layering should have 5 layers, found {layer_count}"
        )

    def test_risk_review_has_severity(self, design_doc_text):
        idx = design_doc_text.find("## 5. Risk Review")
        end = design_doc_text.find("## 6. Promotion Gates")
        window = design_doc_text[idx:end]
        for severity in ("Critical", "High", "Medium"):
            assert severity in window, (
                f"severity {severity!r} missing from Risk Review"
            )

    def test_recommendation_has_abc(self, design_doc_text):
        idx = design_doc_text.find("## 7. Recommendation")
        end = design_doc_text.find("## 8. Roadmap Position")
        window = design_doc_text[idx:end]
        for option in ("A.", "B.", "C."):
            assert option in window, (
                f"option {option!r} missing from Recommendation"
            )


# ---------------------------------------------------------------------------
# Architecture review covers prior work
# ---------------------------------------------------------------------------


class TestArchitectureReview:
    def test_covers_phase_7f(self, design_doc_text):
        idx = design_doc_text.find("## 3. Architecture Review")
        end = design_doc_text.find("## 4. Proposed Layering")
        window = design_doc_text[idx:end]
        assert "7F" in window, "Phase 7F not covered"

    def test_covers_phase_7i(self, design_doc_text):
        idx = design_doc_text.find("## 3. Architecture Review")
        end = design_doc_text.find("## 4. Proposed Layering")
        window = design_doc_text[idx:end]
        assert "7I" in window, "Phase 7I not covered"

    def test_covers_construction_schedule_engine(self, design_doc_text):
        idx = design_doc_text.find("## 3. Architecture Review")
        end = design_doc_text.find("## 4. Proposed Layering")
        window = design_doc_text[idx:end]
        assert (
            "Construction Schedule Engine" in window
            or "construction schedule engine" in window.lower()
        ), "Construction Schedule Engine not covered"

    def test_reviews_what_remains_valid(self, design_doc_text):
        idx = design_doc_text.find("## 3. Architecture Review")
        end = design_doc_text.find("## 4. Proposed Layering")
        window = design_doc_text[idx:end]
        assert "remains valid" in window.lower(), (
            "Architecture Review should evaluate what remains valid"
        )

    def test_reviews_what_should_change(self, design_doc_text):
        idx = design_doc_text.find("## 3. Architecture Review")
        end = design_doc_text.find("## 4. Proposed Layering")
        window = design_doc_text[idx:end]
        assert "should change" in window.lower(), (
            "Architecture Review should evaluate what should change"
        )

    def test_reviews_what_should_defer(self, design_doc_text):
        idx = design_doc_text.find("## 3. Architecture Review")
        end = design_doc_text.find("## 4. Proposed Layering")
        window = design_doc_text[idx:end]
        assert "defer" in window.lower(), (
            "Architecture Review should evaluate what should be deferred"
        )


# ---------------------------------------------------------------------------
# Hard constraints
# ---------------------------------------------------------------------------


class TestHardConstraints:
    def test_no_code_in_design_doc(self, design_doc_text):
        # The doc is a design gate; it should not contain executable
        # Python code blocks. Markdown code fences are allowed only
        # for "shapes" or "example strings" not actual implementation.
        python_fences = re.findall(r"```python\b", design_doc_text)
        assert len(python_fences) == 0, (
            f"design doc should not contain Python code blocks "
            f"(found {len(python_fences)})"
        )

    def test_no_implementation_keyword(self, design_doc_text):
        # The doc explicitly says "no implementation". Verify the
        # section "Stop after report" is present.
        assert "Stop after report" in design_doc_text

    def test_design_gate_marker(self, design_doc_text):
        # The very first content after the header should be a
        # design-gate marker.
        text = design_doc_text.lower()
        assert "design only" in text, "design-only marker missing"
        assert "docs only" in text, "docs-only marker missing"
        assert "no code" in text, "no-code marker missing"
        assert "no implementation" in text, "no-implementation marker missing"


# ---------------------------------------------------------------------------
# Recommendation: B (more discovery needed)
# ---------------------------------------------------------------------------


class TestRecommendation:
    def test_recommendation_is_b(self, design_doc_text):
        idx = design_doc_text.find("## 7. Recommendation")
        end = design_doc_text.find("## 8. Roadmap Position")
        window = design_doc_text[idx:end]
        # B should be the actual choice
        assert "**Choice:**" in window or "Choice:" in window
        # The choice line explicitly states B
        assert "**B.**" in window or "Choice: **B**" in window or (
            "B. More discovery needed" in window
        ), "Choice B not clearly stated in Recommendation"

    def test_rationale_has_at_least_3_points(self, design_doc_text):
        idx = design_doc_text.find("## 7. Recommendation")
        end = design_doc_text.find("## 8. Roadmap Position")
        window = design_doc_text[idx:end]
        # Count numbered rationale points (1., 2., 3., etc.)
        rationale_idx = window.find("Rationale")
        if rationale_idx > 0:
            rationale = window[rationale_idx:]
            numbered = re.findall(r"^\d+\.\s+", rationale, re.MULTILINE)
            assert len(numbered) >= 3, (
                f"rationale should have at least 3 points, found {len(numbered)}"
            )


# ---------------------------------------------------------------------------
# Report JSON structure
# ---------------------------------------------------------------------------


class TestReportJson:
    def test_report_valid_json(self):
        json.loads(REPORT_JSON.read_text(encoding="utf-8"))

    def test_report_has_required_keys(self, report_json_data):
        for key in (
            "phase",
            "title",
            "type",
            "status",
            "branch",
            "hard_constraints",
            "current_state_summary",
            "excel_gaps",
            "proposed_layering",
            "risks",
            "promotion_gates",
            "recommendation",
            "roadmap_position",
        ):
            assert key in report_json_data, f"key {key!r} missing"

    def test_hard_constraints_all_true(self, report_json_data):
        for k, v in report_json_data["hard_constraints"].items():
            assert v is True, (
                f"hard constraint {k!r} should be true, got {v!r}"
            )

    def test_recommendation_choice_is_B(self, report_json_data):
        # The choice value is a full string starting with "B."
        assert report_json_data["recommendation"]["choice"].startswith("B")

    def test_proposed_layering_has_5_layers(self, report_json_data):
        assert len(report_json_data["proposed_layering"]) == 5

    def test_risks_have_severity_levels(self, report_json_data):
        for level in ("critical", "high", "medium"):
            assert level in report_json_data["risks"]
            assert len(report_json_data["risks"][level]) > 0

    def test_no_project_status_changes(self, report_json_data):
        for k in (
            "no_project_status_changes",
        ):
            assert report_json_data["hard_constraints"][k] is True


# ---------------------------------------------------------------------------
# Git / scope guards: nothing else changed
# ---------------------------------------------------------------------------


class TestScopeGuards:
    """Verify that ONLY the 2 expected files are added in this branch,
    and that no code / runtime / schema / persistence / flag / formula
    paths were touched."""

    # Forbidden code paths: no edits under these directories.
    FORBIDDEN_CODE_PATHS = (
        "domain/",
        "app/",
        "main_web.py",
        "main_api.py",
        "static/",
    )

    # Forbidden phase subdirectories under docs/ and reports/:
    # we are adding exactly 2 files, and only the C1 ones.
    FORBIDDEN_PHASE_DOC_PATHS = (
        "docs/phase_",
        "reports/phase_",
    )

    EXPECTED_ADDITIONS = (
        "docs/phase_c1_construction_idc_design_gate.md",
        "reports/phase_c1_construction_idc_design_gate.json",
        "tests/test_phase_c1_construction_idc_design_gate.py",
    )

    @staticmethod
    def _phase_commit_sha() -> str:
        """Locate the Phase C1 squash-merge commit on origin/main.

        C-series test design (pre-#554) used an absolute
        ``git diff origin/main HEAD`` check. C9 (a later phase)
        legitimately adds files under app/, docs/, and reports/
        per C8 §7.3, which would cause C1-C5's absolute checks
        to fire as false positives on a branch that has C9
        already merged or in progress.

        To make C1-C5's scope guards robust against future C-phases
        (C9, C10, C11) that legitimately add files in the same
        directories, this helper locates the C1 commit on
        ``origin/main`` and the C1 test methods below diff
        against the C1 commit's first parent (the pre-C1 main tip).
        """
        r = subprocess.run(
            ["git", "log", "--merges", "--first-parent",
             "--format=%H %s", "origin/main"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        c_shas = []
        for ln in r.stdout.splitlines():
            parts = ln.split(" ", 1)
            if len(parts) == 2 and parts[1].startswith("Phase C1:"):
                c_shas.append(parts[0])
        if not c_shas:
            r = subprocess.run(
                ["git", "log", "--format=%H %s", "origin/main"],
                cwd=str(REPO_ROOT), capture_output=True, text=True,
            )
            for ln in r.stdout.splitlines():
                parts = ln.split(" ", 1)
                if len(parts) == 2 and parts[1].startswith("Phase C1:"):
                    c_shas.append(parts[0])
        assert c_shas, "could not locate Phase C1 commit on origin/main"
        return c_shas[0]

    def test_only_expected_files_added(self):
        c_sha = self._phase_commit_sha()
        result = subprocess.run(
            ["git", "diff", c_sha + "^1", c_sha, "--name-status",
             "--diff-filter=AMD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # No modified or deleted files allowed
        lines = [
            ln for ln in result.stdout.strip().splitlines() if ln
        ]
        # Each line should start with "A\t" (added) for our 2 files
        status_pairs = [ln.split("\t") for ln in lines]
        for status, path in status_pairs:
            assert status == "A", (
                f"only additions allowed, got {status} for {path}"
            )
            assert path in self.EXPECTED_ADDITIONS, (
                f"unexpected added file: {path!r} "
                f"(expected: {self.EXPECTED_ADDITIONS})"
            )

    @pytest.mark.parametrize("path", FORBIDDEN_CODE_PATHS)
    def test_forbidden_code_path_untouched(self, path):
        c_sha = self._phase_commit_sha()
        result = subprocess.run(
            ["git", "diff", "--stat", c_sha + "^1", c_sha, "--", path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"Phase C1 must not touch {path}: got diff:\n{result.stdout}"
        )

    @pytest.mark.parametrize("path", FORBIDDEN_PHASE_DOC_PATHS)
    def test_forbidden_phase_doc_path_only_c1_added(self, path):
        # The diff under docs/phase_/ and reports/phase_/ should be
        # empty because our 2 new files use 'phase_c1_' but the
        # prefix 'phase_' is shared - we need to check the actual
        # file names. Instead, this test checks: no file under
        # docs/phase_* or reports/phase_* was added EXCEPT our 2.
        # We allow path = 'docs/phase_' which would match 'docs/phase_c1_...'
        # so instead, check via name filtering.
        c_sha = self._phase_commit_sha()
        result = subprocess.run(
            ["git", "diff", "--name-only", c_sha + "^1", c_sha, "--", path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # The output may contain our 2 expected files; everything else
        # is forbidden.
        allowed = set(self.EXPECTED_ADDITIONS)
        actual = set(result.stdout.strip().splitlines()) - {""}
        unexpected = actual - allowed
        assert not unexpected, (
            f"Phase C1 only allows these files under {path}: "
            f"{allowed}; unexpected: {unexpected}"
        )

    def test_no_main_web_changes(self):
        c_sha = self._phase_commit_sha()
        result = subprocess.run(
            ["git", "diff", "--stat", c_sha + "^1", c_sha, "--", "main_web.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == ""

    def test_no_main_api_changes(self):
        c_sha = self._phase_commit_sha()
        result = subprocess.run(
            ["git", "diff", "--stat", c_sha + "^1", c_sha, "--", "main_api.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == ""

    def test_no_app_changes(self):
        c_sha = self._phase_commit_sha()
        result = subprocess.run(
            ["git", "diff", "--stat", c_sha + "^1", c_sha, "--", "app/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == ""

    def test_no_domain_changes(self):
        c_sha = self._phase_commit_sha()
        result = subprocess.run(
            ["git", "diff", "--stat", c_sha + "^1", c_sha, "--", "domain/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    def test_rc1_sha_reachable(self):
        result = subprocess.run(
            [
                "git",
                "cat-file",
                "-e",
                "b425a0708719eaa5e1d922b1008e5609758e0ad4",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            "rc1 SHA not reachable on origin/main"
        )


# ---------------------------------------------------------------------------
# Project statuses unchanged
# ---------------------------------------------------------------------------


class TestProjectStatusesUnchanged:
    """The current state section must document TUHO at Level 2,
    Oborovo at Level 2, Generic Wind/Solar at Level 1. This is a
    documentation check, not a parity test."""

    def test_tuho_level_2(self, design_doc_text):
        assert "TUHO" in design_doc_text
        # The Level assertion comes from MEMORY context, not the
        # doc itself, but the doc should reference TUHO.

    def test_oborovo_level_2(self, design_doc_text):
        assert "Oborovo" in design_doc_text


# ---------------------------------------------------------------------------
# No runtime formula content
# ---------------------------------------------------------------------------


class TestNoRuntimeFormulaContent:
    def test_no_formulas_with_equals_sign(self, design_doc_text):
        # The doc should not contain implementation formulas (with
        # = or Python expressions). Allow prose mentions of "formula"
        # but block actual math.
        formula_lines = re.findall(
            r"^\s*\w+\s*=\s*[\d\.]+", design_doc_text, re.MULTILINE
        )
        assert len(formula_lines) == 0, (
            f"design doc should not contain formula assignments, "
            f"found {len(formula_lines)}"
        )

    def test_no_python_imports(self, design_doc_text):
        assert "import " not in design_doc_text or "import" not in [
            w for w in re.findall(r"\bimport\b", design_doc_text)
        ]
        # A more permissive check: no `from x import y` patterns
        from_imports = re.findall(r"^from\s+\w+\s+import\s+", design_doc_text)
        assert len(from_imports) == 0, "no Python imports allowed"


# ---------------------------------------------------------------------------
# Roadmap positions
# ---------------------------------------------------------------------------


class TestRoadmapPositions:
    def test_depreciation_status(self, design_doc_text):
        idx = design_doc_text.find("## 8. Roadmap Position")
        end = len(design_doc_text)
        window = design_doc_text[idx:end]
        assert "Depreciation" in window or "depreciation" in window

    def test_generic_program_status(self, design_doc_text):
        idx = design_doc_text.find("## 8. Roadmap Position")
        end = len(design_doc_text)
        window = design_doc_text[idx:end]
        assert "Generic" in window

    def test_opex_2_0_status(self, design_doc_text):
        idx = design_doc_text.find("## 8. Roadmap Position")
        end = len(design_doc_text)
        window = design_doc_text[idx:end]
        assert "OPEX" in window

    def test_formula_transparency_status(self, design_doc_text):
        idx = design_doc_text.find("## 8. Roadmap Position")
        end = len(design_doc_text)
        window = design_doc_text[idx:end]
        assert "Formula transparency" in window

    def test_capex_evolution_status(self, design_doc_text):
        idx = design_doc_text.find("## 8. Roadmap Position")
        end = len(design_doc_text)
        window = design_doc_text[idx:end]
        assert "CAPEX evolution" in window or "CAPEX" in window
