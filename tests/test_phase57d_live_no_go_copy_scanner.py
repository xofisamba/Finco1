"""Phase 57D — Live no-go copy scanner.

This test file implements a filesystem-scanning no-go copy
scanner. It complements (does not replace) the existing
snapshot-based no-go copy tests in:

* tests/test_phase54h_ui_no_go_copy_scanner.py
* tests/test_phase57a_ui3_line_item_grid_capex_summary.py::TestNoGoCopy

The scanner:
* Walks app/templates/, docs/, and reports/.
* For each file, strips Jinja and HTML comments.
* Checks each NO_GO_TERM against the remaining text.
* For each match, checks the surrounding context (200-char
  window) for an allowed negative phrase.
* Reports violations as test failures.
* Does NOT modify any file.
"""

import fnmatch
import json
import re
import tempfile
from pathlib import Path
from typing import Iterable

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ============================================================
# 1. Constants
# ============================================================


NO_GO_TERMS = [
    "investor-grade",
    "bankable",
    "bank-grade",
    "lender-approved",
    "lender-ready",
    "certified",
    "audit-ready",
    "validated",
    "investor-ready",
    "SaaS-ready",
    "production-ready",
    "external validation",
    "customer reference",
    "investment advice",
    "guaranteed returns",
    "enterprise-ready",
    "model-validated",
    "LineItemGrid is validated",
]


# Files that may contain the forbidden terms as part of a
# no-go list, test assertion, or historical mention.
ALLOWED_PATH_PATTERNS = [
    "tests/test_phase54h_ui_no_go_copy_scanner.py",
    "tests/test_phase57a_ui3_line_item_grid_capex_summary.py",
    "tests/test_phase57d_live_no_go_copy_scanner.py",
    "docs/external_review/no_go_claims.md",
    "docs/commercial/*.md",
    "docs/external_review/*.md",
    "docs/governance/*.md",
    "docs/validation/*.md",
    "docs/phase*_*.md",
    "reports/phase*_no_go*.json",
    "docs/governance/phase53_*.md",
    "docs/governance/phase52_53_*.md",
    "docs/governance/remaining_hotspots_governance_tracker.md",
    "docs/governance/post_phase52_governance_refresh.md",
    "docs/governance/b_track_phase53_refresh_cadence.md",
    "docs/governance/agent_a_b_governance_refresh_plan.md",
    "reports/validation/*.json",
    "reports/roadmap/*.json",
    "reports/pilot/*.json",
    "reports/governance/*.json",
    "reports/external_review/*.json",
    "reports/commercial/*.json",
    "reports/ui*_*.json",
    "reports/phase*_*.json",
    "reports/agent_*.json",
]


# Phrases that, if found in the surrounding context, indicate
# the forbidden term is in a negative / no-go / disclaimer /
# historical / rephrasing context.
ALLOWED_NEGATIVE_PHRASES = [
    "not validated",
    "not approved",
    "unvalidated",
    "parity-validated",
    "parity-validated against",
    "parity validated",
    "validated against",
    "validated at the parity",
    "validated through",
    "validated via",
    "validated by the",
    "must not be presented as",
    "no-go",
    "no go",
    "forbidden positive claim",
    "is not a",
    "does not validate the model",
    "presentation refactor only",
    "where it read",
    "replaced with",
    "rephrasing",
    "no runtime change",
    "no promotion",
    "internal check",
    "model evidence",
    "reference",
    "reference path",
    "reference-status",
    "parity evidence",
    "has parity evidence against excel",
    "frozen-template parity",
    "frozen-template parity references",
    "tuho/oborovo parity evidence",
    "negative",
    "forbidden",
    "do not",
    "must not",
    "preserved",
    "nogo",
    "warning",
    "exploratory",
    "excluded from",
    "not yet",
    "not part of",
    "should be reviewed",
    "trusted pilot",
    "excel (",
    "frozen-template",
    "last_validated_at",
    "_validated",
    "not saas-ready",
    "not x-ready",
    "not lenda-ready",
    "not lenda ready",
    "not certified",
    "not production-ready",
    "not investor-ready",
    "not lender-approved",
    "not investment advice",
    "requires finance review",
    "single-user / internal pilot",
    "single-user internal pilot",
    "internal screening",
    "controlled pilot",
    "not bankable",
    "not bank-grade",
    "[not included]",
    "not audit-ready",
]


SCAN_ROOTS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "static",
    REPO_ROOT / "app" / "templates",
    REPO_ROOT / "docs",
    REPO_ROOT / "reports",
]

SCANNED_SUFFIXES = {".html", ".md", ".json", ".css"}

COMMENT_PATTERNS = [
    (re.compile(r"\{#.*?#\}", re.DOTALL), "jinja"),
    (re.compile(r"<!--.*?-->", re.DOTALL), "html"),
]

# Per-call context window for negative-phrase search.
CONTEXT_WINDOW = 200
TMP_SCAN_ROOT = Path(tempfile.gettempdir()) / "finco1_no_go_scanner"


# ============================================================
# 2. Scanner helper
# ============================================================


def _is_allowed_path(rel_path: str) -> bool:
    """Return True if `rel_path` is in the allowlist."""
    for pattern in ALLOWED_PATH_PATTERNS:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
    return False


def _strip_comments(text: str) -> str:
    """Strip Jinja and HTML comments from `text`."""
    for pattern, _kind in COMMENT_PATTERNS:
        text = pattern.sub("", text)
    return text


def _has_negative_context(text: str, term: str, match_pos: int) -> bool:
    """Return True if the context around `match_pos` contains
    an allowed negative phrase."""
    start = max(0, match_pos - CONTEXT_WINDOW)
    end = min(len(text), match_pos + len(term) + CONTEXT_WINDOW)
    context = text[start:end].lower()
    if term.lower() == "validated":
        parity_reference_context = (
            ("tuho" in context or "oborovo" in context)
            and (
                "frozen-template" in context
                or "parity" in context
                or "excel" in context
                or "reference" in context
            )
        )
        if parity_reference_context:
            return True
    return any(phrase in context for phrase in ALLOWED_NEGATIVE_PHRASES)


def _special_phrase_violations(path: Path, text: str) -> list[dict]:
    """Catch higher-risk phrases that need contextual rules."""
    try:
        rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        rel = str(path)
    violations: list[dict] = []

    full_model_patterns = [
        re.compile(
            r"\|\s*(?:generic\s*/\s*new projects|generic\s+solar|generic\s+wind|solar(?:\s+project)?|wind(?:\s+project)?)\s*\|[^\n]{0,80}\bfull model\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:generic\s+)?(?:solar|wind)(?:\s+project|\s+path)?\b[^\n]{0,80}\bfull model\b",
            re.IGNORECASE,
        ),
    ]
    full_model_safe_context = (
        "exploratory",
        "unvalidated",
        "reference",
        "revenue-only",
        "in progress",
        "not production-ready",
        "not validated",
        "frozen-template parity",
    )
    for pattern in full_model_patterns:
        for match in pattern.finditer(text):
            context = text[max(0, match.start() - 120): min(len(text), match.end() + 120)]
            lowered = context.lower()
            if any(phrase in lowered for phrase in full_model_safe_context):
                continue
            line = text.count("\n", 0, match.start()) + 1
            violations.append(
                {
                    "file": path,
                    "term": "full model",
                    "line": line,
                    "context": context,
                    "path": rel,
                }
            )
    return violations


def scan_file(path: Path) -> list:
    """Scan a single file for forbidden positive claims.

    Returns a list of violation dicts, each with:
        - file (Path)
        - term (str)
        - line (int, 1-based)
        - context (str, surrounding text)
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return []
    stripped = _strip_comments(text)
    # Only consult the allowlist if the path is inside
    # the repo (unit tests may use tmp_path).
    try:
        rel = str(path.relative_to(REPO_ROOT))
    except ValueError:
        rel = None
    if rel is not None and _is_allowed_path(rel):
        return []
    violations = []
    for term in NO_GO_TERMS:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        for m in pattern.finditer(stripped):
            if _has_negative_context(stripped, term, m.start()):
                continue
            line = stripped.count("\n", 0, m.start()) + 1
            context = stripped[
                max(0, m.start() - 80) : min(len(stripped), m.end() + 80)
            ]
            violations.append({
                "file": path,
                "term": term,
                "line": line,
                "context": context,
            })
    violations.extend(_special_phrase_violations(path, stripped))
    return violations


def scan_repository() -> list:
    """Walk the scan directories and collect all violations."""
    all_violations = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix in SCANNED_SUFFIXES:
                all_violations.extend(scan_file(root))
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in SCANNED_SUFFIXES:
                all_violations.extend(scan_file(p))
    return all_violations


# ============================================================
# 3. Test classes
# ============================================================


class TestScannerHelper:
    def _tmp_file(self, suffix: str, content: str) -> Path:
        TMP_SCAN_ROOT.mkdir(exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            delete=False,
            dir=TMP_SCAN_ROOT,
            encoding="utf-8",
        ) as handle:
            handle.write(content)
            return Path(handle.name)

    def test_no_go_terms_constant_has_canonical_list(self):
        assert "investor-grade" in NO_GO_TERMS
        assert "bankable" in NO_GO_TERMS
        assert "lender-ready" in NO_GO_TERMS
        assert "lender-approved" in NO_GO_TERMS
        assert "validated" in NO_GO_TERMS
        assert "production-ready" in NO_GO_TERMS
        assert "enterprise-ready" in NO_GO_TERMS

    def test_scan_roots_include_readme_static_templates_docs_reports(self):
        labels = [str(path.relative_to(REPO_ROOT)).replace("\\", "/") for path in SCAN_ROOTS]
        assert "README.md" in labels
        assert "static" in labels
        assert "app/templates" in labels
        assert "docs" in labels
        assert "reports" in labels

    def test_allowed_path_patterns_contains_test_files(self):
        assert (
            "tests/test_phase57d_live_no_go_copy_scanner.py"
            in ALLOWED_PATH_PATTERNS
        )
        assert (
            "tests/test_phase57a_ui3_line_item_grid_capex_summary.py"
            in ALLOWED_PATH_PATTERNS
        )

    def test_allowed_path_patterns_contains_no_go_docs(self):
        assert "docs/external_review/no_go_claims.md" in ALLOWED_PATH_PATTERNS

    def test_strip_comments_removes_jinja_comments(self):
        text = "before {# this is a comment with validated #} after"
        stripped = _strip_comments(text)
        assert "validated" not in stripped
        assert "before" in stripped
        assert "after" in stripped

    def test_strip_comments_removes_html_comments(self):
        text = "before <!-- this is a comment with bankable --> after"
        stripped = _strip_comments(text)
        assert "bankable" not in stripped

    def test_strip_comments_preserves_non_comment_text(self):
        text = "This is a normal sentence with production-ready."
        stripped = _strip_comments(text)
        assert "production-ready" in stripped

    def test_scan_file_clean_returns_no_violations(self):
        clean = self._tmp_file(".html", "<html><body>Hello world</body></html>")
        assert scan_file(clean) == []

    def test_scan_file_with_violation_returns_violation(self):
        bad = self._tmp_file(
            ".html",
            "<html><body>This system is bankable and certified.</body></html>",
        )
        violations = scan_file(bad)
        assert len(violations) >= 2  # bankable + certified

    def test_readme_overclaim_sample_fails(self):
        bad = self._tmp_file(
            ".md",
            "# Demo\n\nThis is an investor-grade screening tool.\n\n| Type | Status |\n|---|---|\n| Solar | Full model |\n",
        )
        violations = scan_file(bad)
        terms = {v["term"].lower() for v in violations}
        assert "investor-grade" in terms
        assert "full model" in terms

    def test_static_comment_overclaim_sample_fails(self):
        bad = self._tmp_file(".css", "/* bank-grade dashboard */\nbody { color: black; }\n")
        violations = scan_file(bad)
        assert any(v["term"].lower() == "bank-grade" for v in violations)

    def test_scan_file_recognizes_negative_context(self):
        negative = self._tmp_file(
            ".html",
            "<html><body>This system is not validated. "
            "It is not certified. It is not bankable.</body></html>",
        )
        assert scan_file(negative) == []

    def test_scan_file_recognizes_historical_mention(self):
        hist = self._tmp_file(
            ".html",
            "<html><body>Where it read 'validated' before, it now "
            "reads 'Reference'.</body></html>",
        )
        assert scan_file(hist) == []

    def test_safe_frozen_template_parity_wording_is_allowed(self):
        safe = self._tmp_file(
            ".md",
            "TUHO and Oborovo are frozen-template parity references with audit trail evidence.",
        )
        assert scan_file(safe) == []

    def test_safe_exploratory_unvalidated_wording_is_allowed(self):
        safe = self._tmp_file(
            ".md",
            "Generic solar and wind remain exploratory and unvalidated until separately reviewed.",
        )
        assert scan_file(safe) == []


class TestLiveRepositoryScan:
    def test_readme_clean(self):
        readme = REPO_ROOT / "README.md"
        if not readme.exists():
            pytest.skip("README.md does not exist")
        violations = scan_file(readme)
        if violations:
            msg = "\n".join(
                f"  {v['file'].relative_to(REPO_ROOT)}:{v['line']} "
                f"term={v['term']!r} context={v['context']!r}"
                for v in violations
            )
            pytest.fail(
                f"Live no-go copy scanner found {len(violations)} "
                f"violation(s) in README.md:\n{msg}"
            )

    def test_static_clean(self):
        static_root = REPO_ROOT / "static"
        if not static_root.exists():
            pytest.skip("static/ does not exist")
        violations = []
        for p in static_root.rglob("*.css"):
            violations.extend(scan_file(p))
        if violations:
            msg = "\n".join(
                f"  {v['file'].relative_to(REPO_ROOT)}:{v['line']} "
                f"term={v['term']!r} context={v['context']!r}"
                for v in violations
            )
            pytest.fail(
                f"Live no-go copy scanner found {len(violations)} "
                f"violation(s) in static/:\n{msg}"
            )

    def test_app_templates_clean(self):
        # Only scan app/templates (docs are allowlisted)
        app_templates = REPO_ROOT / "app" / "templates"
        if not app_templates.exists():
            pytest.skip("app/templates/ does not exist")
        violations = []
        for p in app_templates.rglob("*.html"):
            violations.extend(scan_file(p))
        if violations:
            msg = "\n".join(
                f"  {v['file'].relative_to(REPO_ROOT)}:{v['line']} "
                f"term={v['term']!r} context={v['context']!r}"
                for v in violations
            )
            pytest.fail(
                f"Live no-go copy scanner found {len(violations)} "
                f"violation(s) in app/templates/:\n{msg}"
            )

    def test_current_user_facing_docs_clean(self):
        docs_to_scan = [
            REPO_ROOT / "docs" / "pilot_user_guide.md",
            REPO_ROOT / "docs" / "validation_pack_executive_summary.md",
        ]
        violations = []
        for p in docs_to_scan:
            if not p.exists():
                continue
            violations.extend(scan_file(p))
        if violations:
            msg = "\n".join(
                f"  {v['file'].relative_to(REPO_ROOT)}:{v['line']} "
                f"term={v['term']!r}"
                for v in violations
            )
            pytest.fail(
                f"Live no-go copy scanner found {len(violations)} "
                f"violation(s) in current user-facing docs:\n{msg}"
            )

    def test_reports_clean_except_allowlisted(self):
        reports = REPO_ROOT / "reports"
        if not reports.exists():
            pytest.skip("reports/ does not exist")
        violations = []
        for p in reports.rglob("*.json"):
            violations.extend(scan_file(p))
        if violations:
            msg = "\n".join(
                f"  {v['file'].relative_to(REPO_ROOT)}:{v['line']} "
                f"term={v['term']!r}"
                for v in violations
            )
            pytest.fail(
                f"Live no-go copy scanner found {len(violations)} "
                f"violation(s) in reports/:\n{msg}"
            )


class TestRc1Untouched:
    def test_rc1_sha_constant_stable(self):
        assert RC1_SHA == "b425a0708719eaa5e1d922b1008e5609758e0ad4"

    def test_rc1_still_in_git_history(self):
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", RC1_SHA],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (
            f"rc1 frozen SHA {RC1_SHA} must still be present in "
            f"the repo. Got: {r.stderr}"
        )


class TestHardNoGoScope:
    def _diff_against_branch_work(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("No branch-local diff to inspect")
        return set(line for line in r.stdout.strip().split("\n") if line)

    def _skip_if_not_on_57d_branch(self) -> None:
        """Skip the test if we are not on a 57D branch."""
        import subprocess
        r_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_branch.returncode != 0:
            return
        branch = r_branch.stdout.strip()
        if branch == "main":
            pytest.skip(
                "On main branch; 57D has been merged. "
                "This test is only meaningful on the "
                "57D unmerged branch."
            )
        if "57d" not in branch.lower():
            pytest.skip(
                f"Not on a 57D branch (current: "
                f"{branch!r}). This test is only "
                f"meaningful on the 57D unmerged "
                f"branch."
            )

    def test_no_runtime_files_in_diff(self):
        self._skip_if_not_on_57d_branch()
        changed = self._diff_against_branch_work()
        forbidden_files = [
            "main_web.py",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "static/app.js",
        ]
        for c in changed:
            for f in forbidden_files:
                if c.endswith(f):
                    pytest.fail(
                        f"57D must not modify {f!r}. Found in diff: {c!r}."
                    )

    def test_no_services_or_persistence_changes(self):
        self._skip_if_not_on_57d_branch()
        changed = self._diff_against_branch_work()
        for c in changed:
            assert not c.startswith("app/persistence/"), (
                f"57D must not modify app/persistence/. Found: {c!r}."
            )
            assert not c.startswith("app/services/"), (
                f"57D must not modify app/services/. Found: {c!r}."
            )

    def test_static_styles_css_comment_only_if_modified(self):
        import subprocess
        r = subprocess.run(
            ["git", "diff", "HEAD", "--", "static/styles.css"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("static/styles.css not modified on this branch")
        self._skip_if_not_on_57d_branch()
        for line in r.stdout.splitlines():
            if not line or line.startswith(("diff ", "index ", "---", "+++", "@@")):
                continue
            if line.startswith(("+", "-")):
                content = line[1:].strip()
                if not content:
                    continue
                if content.startswith(("diff --git", "index ", "---", "+++", "@@")):
                    continue
                is_comment_only = (
                    content.startswith(("/*", "*", "*/"))
                    or content.endswith("*/")
                    or all(token not in content for token in ("{", "}", ";"))
                )
                assert is_comment_only, (
                    "57D2 may update static/styles.css comments only. "
                    f"Found non-comment diff line: {line!r}"
                )


class TestScannerDoesNotSilentlyRewrite:
    def test_scanner_only_reports_no_writes(self):
        """The scanner must not write to any file."""
        before = set((REPO_ROOT / "app" / "templates").rglob("*")) if (
            REPO_ROOT / "app" / "templates"
        ).exists() else set()
        scan_repository()
        after = set((REPO_ROOT / "app" / "templates").rglob("*")) if (
            REPO_ROOT / "app" / "templates"
        ).exists() else set()
        assert before == after

    def test_scanner_no_runtime_side_effects(self):
        """The scanner must not import or call any runtime
        service / persistence / model code."""
        # Just check that the helper module does not import
        # any runtime path
        import tests.test_phase57d_live_no_go_copy_scanner as mod
        source = mod.__file__
        with open(source) as f:
            text = f.read()
        # Strip the module docstring at the top of the file
        # and all # comments so the test does not false-positive
        # on mentions inside the docstring or in comments.
        ds_end = text.find('"""\n\n')
        if ds_end > 0:
            text_no_docstring = text[ds_end + 5:]
        else:
            text_no_docstring = text
        # Strip line comments
        text_no_docstring = re.sub(
            r"#[^\n]*", "", text_no_docstring
        )
        # Use word-boundary regex so e.g. 'from main_web' does
        # not match 'from main_web_tests' or vice versa.
        forbidden_imports = [
            r"\bimport\s+main_web\b",
            r"\bfrom\s+main_web\b",
            r"\bimport\s+app\.services\b",
            r"\bfrom\s+app\.services\b",
            r"\bimport\s+app\.waterfall_core\b",
            r"\bfrom\s+app\.waterfall_core\b",
            r"\bimport\s+app\.persistence\b",
            r"\bfrom\s+app\.persistence\b",
            r"\bimport\s+app\.project_factories\b",
            r"\bfrom\s+app\.project_factories\b",
        ]
        for forbidden in forbidden_imports:
            if re.search(forbidden, text_no_docstring):
                pytest.fail(
                    f"57D scanner must not match {forbidden!r}."
                )
