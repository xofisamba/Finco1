"""Phase 57B — Agent B post-56 / post-57A governance refresh tests.

This test file is a docs/report-only test. It does not modify
runtime code. It pins:

* The 57B docs/report files exist.
* They reference the correct current main SHA.
* They preserve all forbidden positive claims in the no-go list.
* They correctly identify the post-57A governance map.
* They do not claim LineItemGrid is model validation.
* They do not claim UI state components are external validation.
* They do not promote G20 / R99 / R102.
* They do not introduce generic Solar/Wind runtime work.
* They do not introduce BESS/Hybrid/Portfolio work.
* rc1 frozen SHA is still in the doc/report.
* No runtime / model / persistence / CSS / JS / schema / formula
  changes were introduced in 57B.
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs" / "phase57b_agent_b_post56_post57a_governance_refresh.md"
REPORT = REPO_ROOT / "reports" / "phase57b_agent_b_post56_post57a_governance_refresh.json"
RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"

FORBIDDEN_POSITIVE_CLAIMS = [
    "bankable",
    "bank-grade",
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
]


# ============================================================
# 1. Files exist
# ============================================================


class TestFilesExist:
    def test_docs_file_exists(self):
        assert DOCS.exists(), f"57B doc file missing: {DOCS}"

    def test_report_file_exists(self):
        assert REPORT.exists(), f"57B report file missing: {REPORT}"

    def test_doc_minimum_size(self):
        size = DOCS.stat().st_size
        assert size > 8000, (
            f"57B doc is suspiciously small ({size} bytes). "
            f"Expected a comprehensive governance refresh."
        )

    def test_report_is_valid_json(self):
        with open(REPORT) as f:
            data = json.load(f)
        assert "phase" in data
        assert data["phase"] == "57B"


# ============================================================
# 2. SHA references
# ============================================================


class TestShaReferences:
    def test_doc_references_current_main_sha(self):
        """The 57B doc must reference the post-57A main SHA."""
        text = DOCS.read_text()
        assert "b173355b6021577f6567069ebd748aa3176f2475" in text, (
            "57B doc must reference the post-57A main SHA "
            "(b173355b...)."
        )

    def test_doc_references_rc1_frozen_sha(self):
        text = DOCS.read_text()
        assert RC1_SHA in text, (
            f"57B doc must reference the rc1 frozen SHA {RC1_SHA}."
        )

    def test_doc_references_55e_55f_55g_wires_live(self):
        text = DOCS.read_text()
        for k in ["55E", "55F", "55G"]:
            assert k in text, f"57B doc must reference phase {k}."

    def test_doc_references_57a_lineitemgrid(self):
        text = DOCS.read_text()
        assert "57A" in text
        assert "LineItemGrid" in text or "line item grid" in text.lower()

    def test_report_references_current_main_sha(self):
        data = json.loads(REPORT.read_text())
        assert data["base_sha_start"] == (
            "b173355b6021577f6567069ebd748aa3176f2475"
        )

    def test_report_references_rc1_frozen_sha(self):
        data = json.loads(REPORT.read_text())
        assert data["rc1_frozen_sha"] == RC1_SHA


# ============================================================
# 3. No-go claims preserved
# ============================================================


class TestNoGoClaimsPreserved:
    @pytest.mark.parametrize("claim", FORBIDDEN_POSITIVE_CLAIMS)
    def test_doc_references_forbidden_claim_in_no_go_list(self, claim):
        """Each forbidden claim must be referenced in the 57B
        doc as part of the preserved no-go list."""
        text = DOCS.read_text()
        assert claim in text, (
            f"Forbidden positive claim {claim!r} must be "
            f"referenced in the 57B no-go list."
        )

    def test_report_preserves_no_go_list(self):
        data = json.loads(REPORT.read_text())
        canonical_lower = [c.lower() for c in FORBIDDEN_POSITIVE_CLAIMS]
        for claim in data["no_go_claims_preserved"]:
            # Strip parenthetical qualifiers like
            # "validated (positive user-facing)" so we
            # match the core claim.
            core = re.sub(r"\s*\([^)]*\)", "", claim).strip().lower()
            assert core in canonical_lower, (
                f"57B report no-go claim {claim!r} (core: {core!r}) "
                f"is not in the canonical forbidden list."
            )

    def test_report_doc_mentions_validated_only_in_no_go_context(self):
        """'validated' must appear only in negative/no-go
        contexts in the 57B doc."""
        text = DOCS.read_text()
        # Find every occurrence of "validated" and verify it
        # is in a no-go / negative statement / historical-
        # mention context.
        for m in re.finditer(r"validated", text, re.IGNORECASE):
            # Use a wider window so the test catches the
            # surrounding "no-go" / "forbidden positive
            # claims" header / list context.
            start = max(0, m.start() - 200)
            end = min(len(text), m.end() + 200)
            context = text[start:end]
            # Acceptable contexts: "not validated",
            # "no-go list", "forbidden", "negative statement",
            # or historical mention ("where it read 'validated'",
            # "replaced with", etc.).
            ok = any(
                k in context.lower()
                for k in [
                    "not validated",
                    "no-go",
                    "no go",
                    "forbidden",
                    "negative",
                    "must not",
                    "do not",
                    "preserved",
                    "where it read",
                    "replaced with",
                    "instead of",
                    "not\nvalidated",  # wraps across lines
                    "reference",
                    "rephrasing",
                ]
            )
            assert ok, (
                f"'validated' found in 57B doc outside a "
                f"no-go/negative/historical context: "
                f"...{context!r}..."
            )


# ============================================================
# 4. LineItemGrid is presentation refactor only
# ============================================================


class TestLineItemGridIsPresentationRefactor:
    def test_doc_says_lineitemgrid_is_presentation_refactor(self):
        text = DOCS.read_text()
        assert "presentation refactor" in text.lower(), (
            "57B doc must explicitly say LineItemGrid is a "
            "presentation refactor only."
        )

    def test_doc_says_lineitemgrid_does_not_validate_model(self):
        text = DOCS.read_text()
        assert (
            "does not validate the model" in text
            or "not a validation" in text.lower()
            or "not validate" in text.lower()
        ), (
            "57B doc must explicitly say LineItemGrid does "
            "not validate the model."
        )

    def test_doc_forbids_lineitemgrid_validation_claim(self):
        text = DOCS.read_text()
        # The new forbidden LineItemGrid claims must be in
        # the no-go list.
        for k in [
            "model-validated",
            "LineItemGrid is validated",
            "LineItemGrid is audit-ready",
            "LineItemGrid is certified",
        ]:
            assert k in text, (
                f"57B doc must forbid the positive claim {k!r}."
            )


# ============================================================
# 5. UI state components are internal model-evidence only
# ============================================================


class TestUIStateComponentsInternalOnly:
    def test_doc_says_ui_state_components_are_internal(self):
        text = DOCS.read_text()
        assert (
            "internal model-evidence" in text.lower()
            or "internal model evidence" in text.lower()
        ), (
            "57B doc must say UI state components are "
            "internal model-evidence tooling only."
        )

    def test_doc_lists_ui_2_components(self):
        text = DOCS.read_text()
        for k in [
            "UI-2.1",
            "UI-2.2",
            "UI-2.3",
            "UI-2.4",
            "UI-2.5",
            "UI-2.6",
        ]:
            assert k in text, f"57B doc must list UI component {k}."


# ============================================================
# 6. Governance map
# ============================================================


class TestGovernanceMap:
    @pytest.mark.parametrize(
        "arc",
        [
            "persistence",
            "ui-1",
            "ui-2",
            "context",
            "ux cleanup",
            "57A",
            "57B",
        ],
    )
    def test_doc_mentions_arc(self, arc):
        text = DOCS.read_text()
        assert arc.lower() in text.lower(), (
            f"57B doc must mention arc {arc!r} in the "
            f"governance map."
        )

    def test_report_governance_map_includes_post_57a_state(self):
        data = json.loads(REPORT.read_text())
        map_ = data["governance_map_post_57a"]
        for k in [
            "lineitemgrid_capex_pilot_57a",
            "phase_57b_this_refresh",
        ]:
            assert k in map_, f"Governance map must include {k!r}."


# ============================================================
# 7. Hard no-go / scope
# ============================================================


class TestHardNoGoScope:
    @pytest.mark.parametrize(
        "forbidden_change",
        [
            "waterfall_core",
            "project_factories",
            "persistence",
            "main_web.py",
            "static/app.js",
            "static/styles.css",
            "schema",
            "fixture",
            "tailwind",
            "alpine",
            "react",
            "vue",
            "svelte",
        ],
    )
    def test_doc_mentions_forbidden_change(self, forbidden_change):
        text = DOCS.read_text().lower()
        assert forbidden_change.lower() in text, (
            f"57B doc must mention {forbidden_change!r} in the "
            f"hard no-go section."
        )

    def test_doc_says_rc1_untouched(self):
        text = DOCS.read_text()
        assert "rc1" in text.lower()
        # Must say rc1 is untouched / frozen
        m = re.search(r"rc1[^\n]{0,200}", text, re.IGNORECASE)
        assert m is not None
        ctx = m.group(0).lower()
        assert "untouched" in ctx or "frozen" in ctx


# ============================================================
# 8. Recommended next refresh
# ============================================================


class TestRecommendedNextRefresh:
    def test_doc_has_recommended_next_refresh_section(self):
        text = DOCS.read_text()
        assert "Recommended Agent B next refresh" in text, (
            "57B doc must have a 'Recommended Agent B next "
            "refresh' section."
        )

    def test_report_recommends_specific_updates(self):
        data = json.loads(REPORT.read_text())
        recs = data["recommended_next_agent_b_refresh"]
        assert len(recs) >= 5, (
            "57B report must recommend at least 5 specific "
            "updates for the next Agent B refresh."
        )


# ============================================================
# 9. 57A preservation (no regression on prior phases)
# ============================================================


class TestPriorPhasePreservation:
    def test_doc_acknowledges_57a_as_merged(self):
        text = DOCS.read_text()
        assert "57A" in text
        assert "merged" in text.lower() or "pilot" in text.lower()

    def test_doc_acknowledges_57pre_as_merged(self):
        text = DOCS.read_text()
        # 57-pre is referenced via "57-pre" or "57 pre" or
        # "route-render smoke"
        assert "57-pre" in text or "57 pre" in text.lower() or (
            "route-render smoke" in text.lower()
            or "route render smoke" in text.lower()
        )

    def test_doc_acknowledges_56h_1_as_merged(self):
        text = DOCS.read_text()
        assert "56H-1" in text or "56H 1" in text or "NameError" in text


# ============================================================
# 10. Diff scope (no runtime changes)
# ============================================================


class Test57BIsDocsOnly:
    def test_57b_diff_has_no_runtime_files(self):
        """57B must be docs/report/test-only. Use git
        diff against main to confirm."""
        import subprocess
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on 57B branch or no diff")
        changed = set(r.stdout.strip().split("\n"))
        forbidden = [
            "main_web.py",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "static/app.js",
            "static/styles.css",
        ]
        for f in forbidden:
            for c in changed:
                assert not c.endswith(f), (
                    f"57B must not modify {f!r}. "
                    f"Found in diff: {c!r}."
                )
        # No persistence/ or services/ changes
        for c in changed:
            assert not c.startswith("app/persistence/"), (
                f"57B must not modify app/persistence/. "
                f"Found: {c!r}."
            )
            assert not c.startswith("app/services/"), (
                f"57B must not modify app/services/. "
                f"Found: {c!r}."
            )

    def test_57b_diff_only_in_docs_reports_tests(self):
        """57B diff must be exactly in docs/, reports/, tests/."""
        import subprocess
        r = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not r.stdout.strip():
            pytest.skip("Not on 57B branch or no diff")
        changed = set(r.stdout.strip().split("\n"))
        for c in changed:
            assert (
                c.startswith("docs/")
                or c.startswith("reports/")
                or c.startswith("tests/")
            ), (
                f"57B diff file {c!r} is outside "
                f"docs/reports/tests. 57B must be docs/report/test-only."
            )
