"""Security headers middleware — adds X-Frame-Options, X-Content-Type-Options, Referrer-Policy, CSP."""
import typing


class SecurityHeadersMiddleware:
    """Adds security headers to every HTTP response."""

    # CSP allows: self, inline styles (needed for Jinja2), no external scripts
    CSP = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
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