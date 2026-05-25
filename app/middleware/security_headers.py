"""Security headers middleware — adds X-Frame-Options, X-Content-Type-Options, Referrer-Policy, CSP."""
import typing


class SecurityHeadersMiddleware:
    """Adds security headers to every HTTP response."""

    # NOTE: script-src 'self' is strict — no unsafe-inline.
    # Inline workspace init scripts (applyWorkspaceStateMeta, applyScenarioSnapshot)
    # have been moved to static/app.js via DOM data attributes (see index.html).
    # New Project onclick has been externalized to static/app.js event binding.
    # discard button onclick has been removed (replaced by JS event listener in app.js).
    # If CSP needs to be relaxed for any inline script, document in:
    #   docs/phase16_csp_inline_script_fix.md
    #   reports/phase16_csp_security_tradeoff_register.csv
    CSP = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )

    HEADERS = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "same-origin",
        "Content-Security-Policy": CSP,
    }

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status_code = 200
        headers = []

        async def security_send(message):
            nonlocal status_code, headers
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                # Add security headers
                for name, value in self.HEADERS.items():
                    headers.append([name.encode(), value.encode()])
                await send({
                    "type": "http.response.start",
                    "status": status_code,
                    "headers": headers,
                })
            else:
                await send(message)

        await self.app(scope, receive, security_send)