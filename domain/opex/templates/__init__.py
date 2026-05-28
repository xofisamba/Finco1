"""Offline OPEX templates."""

from domain.opex.templates.oborovo import build_oborovo_opex_template
from domain.opex.templates.tuho import build_tuho_opex_template

__all__ = ["build_oborovo_opex_template", "build_tuho_opex_template"]
