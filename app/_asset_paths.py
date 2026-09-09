"""Installed-package web application factory.

Resolves templates and static assets from their installed locations
(site-packages) rather than relative to a source checkout directory.
Used by the packaging smoke test and by main_web.py as a path resolver.
"""
import os


def _installed_static_dir() -> str | None:
    """Return the directory of the installed `static` package, or None."""
    try:
        import static as _static_pkg
        return os.path.dirname(os.path.abspath(_static_pkg.__file__))
    except ImportError:
        return None


def _installed_templates_dir() -> str:
    """Return the templates directory from the installed `app` package."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def resolve_static_dir(source_base_dir: str) -> str | None:
    """
    Return the static assets directory to mount, preferring the
    source-checkout path when it exists (dev mode), falling back to the
    installed `static` package (clean-install mode).
    """
    source_static = os.path.join(source_base_dir, "static")
    if os.path.isdir(source_static):
        return source_static
    return _installed_static_dir()


def create_smoke_app():
    """
    Minimal FastAPI application used only by packaging smoke tests.

    Mounts templates and static from installed package locations.
    Returns HTTP 200 on /health and serves /static/** from the installed
    static package.  Not used in production — main_web.py is the production
    entry point.
    """
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates  # noqa: F401

    smoke_app = FastAPI(title="finco1-smoke")

    templates_dir = _installed_templates_dir()
    static_dir = _installed_static_dir()
    if static_dir:
        smoke_app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @smoke_app.get("/health")
    async def health(request: Request):
        return JSONResponse({
            "status": "ok",
            "templates_dir": templates_dir,
            "static_dir": static_dir,
        })

    return smoke_app
