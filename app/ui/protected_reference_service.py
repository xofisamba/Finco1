"""Phase P2-FIX-3: Protected Reference Project Service (C2 architecture).

Implements the minimal additive helpers for the C2 "first-edit
trigger" behavior:

- Protected reference projects (TUHO Wind, Oborovo Solar PV) appear
  in the normal UI as plain project names.
- Opening them does NOT create a working copy. The user views, runs,
  and exports the read-only reference.
- The first edit / save attempt triggers an explicit transition:
  "This is a protected reference project. Create an editable copy?"
- Only after the user confirms (via /projects/{code}/confirm-first-
  edit-copy), a user-owned working copy is created.
- The protected reference fixture never mutates.

Helpers
-------
- ``is_protected_reference(project_record)`` — true if the project
  record is a TUHO or Oborovo factory_template.
- ``first_edit_response(project_record)`` — returns the 409 dict that
  /scenarios/state/draft returns when a draft save is attempted on a
  protected reference.
- ``create_working_copy_from_protected_reference(...)`` — wraps the
  existing /save-as machinery to create a user-owned working copy
  with ``project_origin = "user_created"`` and a metadata tag
  indicating the source.

The data model is unchanged. We rely on existing fields
(``project_origin``, ``template_source``, ``source_project_template``,
``baseline_snapshot``) and existing save_project / save-as machinery.

The C2 protected reference is identified by the
``template_source in ("tuho", "oborovo")`` AND
``project_origin == "factory_template"`` combination. Other factory
templates (e.g. generic_solar, generic_wind) are NOT protected
references — they are "internal-use model only" and can already be
edited / saved as user_created via the existing
/projects/{code}/save-as route.
"""

from __future__ import annotations

from typing import Any, Optional


# Internal codes identifying the protected reference projects.
# Hidden != deleted: the data model still has project_origin =
# "factory_template" and template_source = "tuho" / "oborovo".
PROTECTED_REFERENCE_TEMPLATE_SOURCES: frozenset[str] = frozenset({
    "tuho",
    "oborovo",
})


def is_protected_reference(project_record: Any) -> bool:
    """Return True if the project is a protected reference (TUHO
    or Oborovo factory template)."""
    if project_record is None:
        return False
    project_origin = getattr(project_record, "project_origin", None)
    template_source = getattr(project_record, "template_source", None)
    source_project_template = getattr(
        project_record, "source_project_template", None
    )
    if project_origin != "factory_template":
        return False
    # The factory templates use template_source == source_project_template.
    if template_source in PROTECTED_REFERENCE_TEMPLATE_SOURCES:
        return True
    if source_project_template in PROTECTED_REFERENCE_TEMPLATE_SOURCES:
        return True
    return False


def first_edit_response(project_record: Any) -> dict[str, Any]:
    """The 409 response that /scenarios/state/draft returns when a
    draft save is attempted on a protected reference. The frontend
    uses this to show a 'Create editable copy?' confirmation prompt.

    The response includes the project_code, project_name, and
    template_source so the frontend can build the confirm dialog
    without a follow-up request.
    """
    return {
        "error": "protected_reference",
        "needs_copy_confirmation": True,
        "project_code": getattr(project_record, "project_code", None),
        "project_name": getattr(project_record, "project_name", None),
        "template_source": getattr(project_record, "template_source", None),
        "message": (
            "This is a protected reference project. "
            "Create an editable copy?"
        ),
    }


def working_copy_replay_metadata(
    source_project_code: str,
    source_project_origin: str,
) -> dict[str, Any]:
    """Replay metadata for a working copy created from a protected
    reference. The metadata records the source project and the
    transition type so audit / reviewer can trace the lineage."""
    return {
        "export_type": "working_copy_from_protected_reference",
        "source_project_code": source_project_code,
        "source_project_origin": source_project_origin,
        "created_via": "p2fix3_first_edit_confirmation",
        "baseline_source": False,
    }
