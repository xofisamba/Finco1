"""Auth lite — lightweight session-based auth for FincoGPT.

Architecture:
- Stateless signed cookies via itsdangerous URLSafeTimedSerializer
- Server-side session data (no DB, no Redis)
- bcrypt password hashing
- Session expiry enforced server-side

Env vars:
- FINCO_SECRET_KEY: signing key (required in production)
- FINCO_ADMIN_USER: username (default: admin)
- FINCO_ADMIN_PASSWORD: plain password (default: fincoGPT2026!)
- FINCO_ADMIN_PASSWORD_HASH: bcrypt hash (overrides FINCO_ADMIN_PASSWORD)
- FINCO_SESSION_HOURS: session TTL in hours (default: 24)
- FINCO_COOKIE_SECURE: cookie security (default: true)
"""

import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# ── Config ───────────────────────────────────────────────────────────────────

SECRET_KEY = os.getenv("FINCO_SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = "dev-secret-please-change-in-production"
    print("WARNING: FINCO_SECRET_KEY not set. Using insecure default.")

ADMIN_USERNAME = os.getenv("FINCO_ADMIN_USER", "admin")
ADMIN_PASSWORD_HASH_ENV = os.getenv("FINCO_ADMIN_PASSWORD_HASH")
ADMIN_PASSWORD_PLAIN = os.getenv("FINCO_ADMIN_PASSWORD", "fincoGPT2026!")

SESSION_MAX_AGE_HOURS = int(os.getenv("FINCO_SESSION_HOURS", "24"))
COOKIE_NAME = "finco_session"
COOKIE_SECURE = os.getenv("FINCO_COOKIE_SECURE", "true").lower() in ("true", "1", "yes")
COOKIE_SAMESITE = os.getenv("FINCO_COOKIE_SAMESITE", "lax")

# ── Password hashing ──────────────────────────────────────────────────────────

def _hash_password(password: str) -> bytes:
    """Hash a password with bcrypt, rounds=12."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))

def _verify_password(password: str, hashed: bytes) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed)

# ── Session serializer ────────────────────────────────────────────────────────

_serializer: Optional[URLSafeTimedSerializer] = None

def _get_serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        _serializer = URLSafeTimedSerializer(SECRET_KEY)
    return _serializer

# ── Session data ──────────────────────────────────────────────────────────────

class SessionData:
    """Lightweight session — user_id + username + login timestamp."""
    __slots__ = ("user_id", "username", "login_at")

    def __init__(self, user_id: str, username: str, login_at: datetime):
        self.user_id = user_id
        self.username = username
        self.login_at = login_at

    def is_expired(self, max_age_hours: int = SESSION_MAX_AGE_HOURS) -> bool:
        age = datetime.now(timezone.utc) - self.login_at
        return age > timedelta(hours=max_age_hours)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "login_at": self.login_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Optional["SessionData"]:
        try:
            login_at = datetime.fromisoformat(data["login_at"])
            if login_at.tzinfo is None:
                login_at = login_at.replace(tzinfo=timezone.utc)
            return cls(data["user_id"], data["username"], login_at)
        except (KeyError, ValueError, TypeError):
            return None

# ── Core auth functions ───────────────────────────────────────────────────────

def verify_login(username: str, password: str) -> bool:
    """Verify username + password. Returns True if valid."""
    if username != ADMIN_USERNAME:
        return False
    if ADMIN_PASSWORD_HASH_ENV:
        stored_hash = ADMIN_PASSWORD_HASH_ENV.encode()
    else:
        stored_hash = _hash_password(ADMIN_PASSWORD_PLAIN)
    return _verify_password(password, stored_hash)

def create_session_token(user_id: str = "1", username: str = ADMIN_USERNAME) -> str:
    """Create a signed session token."""
    login_at = datetime.now(timezone.utc)
    session = SessionData(user_id=user_id, username=username, login_at=login_at)
    serializer = _get_serializer()
    return serializer.dumps(session.to_dict())

def decode_session_token(token: str) -> Optional[SessionData]:
    """Decode + validate session token. Returns SessionData or None."""
    serializer = _get_serializer()
    max_age_seconds = SESSION_MAX_AGE_HOURS * 3600
    try:
        data = serializer.loads(token, max_age=max_age_seconds)
        session = SessionData.from_dict(data)
        if session and not session.is_expired():
            return session
        return None
    except (BadSignature, SignatureExpired, TypeError, ValueError):
        return None

def make_session_cookie(token: str) -> dict:
    """Build a session cookie dict for FastAPI responses."""
    return {
        "key": COOKIE_NAME,
        "value": token,
        "httponly": True,
        "secure": COOKIE_SECURE,
        "samesite": COOKIE_SAMESITE,
        "max_age": SESSION_MAX_AGE_HOURS * 3600,
        "path": "/",
    }

def clear_session_cookie() -> dict:
    """Build a clearing cookie (logout)."""
    return {
        "key": COOKIE_NAME,
        "value": "",
        "httponly": True,
        "secure": COOKIE_SECURE,
        "samesite": COOKIE_SAMESITE,
        "max_age": 0,
        "path": "/",
    }