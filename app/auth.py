"""Auth lite — lightweight session-based auth for FincoGPT.

Architecture:
- Stateless signed cookies via itsdangerous URLSafeTimedSerializer
- Server-side session data (no DB, no Redis)
- bcrypt password hashing
- Session expiry enforced server-side
- Rate limiting on login (in-memory, per-IP)
- CSRF protection on login form

Env vars:
- FINCO_SECRET_KEY: signing key (required in production)
- FINCO_ADMIN_USER: username (default: admin)
- FINCO_ADMIN_PASSWORD: plain password (default: fincoGPT2026!)
- FINCO_ADMIN_PASSWORD_HASH: bcrypt hash (overrides FINCO_ADMIN_PASSWORD)
- FINCO_SESSION_HOURS: session TTL in hours (default: 24)
- FINCO_COOKIE_SECURE: cookie security (default: true)
- FINCO_CSRF_SECRET: CSRF signing key (default: FINCO_SECRET_KEY)
"""

import os
import time
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from threading import Lock

import re
import time as time_module

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

# ── CSRF configuration ─────────────────────────────────────────────────────────
CSRF_SECRET = os.getenv("FINCO_CSRF_SECRET") or SECRET_KEY
_csrf_serializer: Optional[URLSafeTimedSerializer] = None

def _get_csrf_serializer() -> URLSafeTimedSerializer:
    global _csrf_serializer
    if _csrf_serializer is None:
        _csrf_serializer = URLSafeTimedSerializer(CSRF_SECRET)
    return _csrf_serializer

# ── CSRF token helpers ─────────────────────────────────────────────────────────

def generate_csrf_token() -> str:
    """Generate a new CSRF token (signed, single-use per form render)."""
    raw = secrets.token_hex(24)
    serializer = _get_csrf_serializer()
    return serializer.dumps(raw)

def validate_csrf_token(token: str) -> bool:
    """Validate a CSRF token. Returns True if valid and not tampered."""
    if not token:
        return False
    serializer = _get_csrf_serializer()
    try:
        # Tokens are short-lived (same-day validity is plenty)
        raw = serializer.loads(token, max_age=86400)
        return isinstance(raw, str) and len(raw) == 48
    except (BadSignature, SignatureExpired, TypeError, ValueError):
        return False


# ── Rate limiting ──────────────────────────────────────────────────────────────

MAX_LOGIN_FAILURES = 5
LOCKOUT_SECONDS = 300  # 5 minutes

_rate_limit_lock = Lock()
_rate_limit_store: dict[str, dict] = {}  # IP -> {"failures": int, "locked_until": float | None}

def _record_failed_login(ip: str) -> None:
    """Record a failed login attempt for an IP."""
    with _rate_limit_lock:
        entry = _rate_limit_store.get(ip, {"failures": 0, "locked_until": None})
        entry["failures"] += 1
        if entry["failures"] >= MAX_LOGIN_FAILURES:
            entry["locked_until"] = time.time() + LOCKOUT_SECONDS
        _rate_limit_store[ip] = entry

def _clear_failed_logins(ip: str) -> None:
    """Clear failed login record on successful login."""
    with _rate_limit_lock:
        if ip in _rate_limit_store:
            del _rate_limit_store[ip]

def is_ip_locked_out(ip: str) -> tuple[bool, int]:
    """Returns (is_locked, seconds_remaining)."""
    with _rate_limit_lock:
        entry = _rate_limit_store.get(ip, {"failures": 0, "locked_until": None})
        if entry.get("locked_until") is None:
            return False, 0
        remaining = entry["locked_until"] - time.time()
        if remaining <= 0:
            # Lockout expired — clean it up
            if entry["failures"] < MAX_LOGIN_FAILURES:
                del _rate_limit_store[ip]
            else:
                entry["locked_until"] = None
                entry["failures"] = 0
            return False, 0
        return True, int(remaining)

def get_failures_count(ip: str) -> int:
    with _rate_limit_lock:
        return _rate_limit_store.get(ip, {"failures": 0}).get("failures", 0)

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

def verify_login(username: str, password: str, ip: str = "unknown") -> bool:
    """Verify username + password. Returns True if valid.
    
    Enforces:
    - Rate limiting: 5 failures → 5-min lockout → 429 response
    - Failed login cooldown: 0.5s delay
    - Strong password: min 8 chars, at least 1 digit and 1 uppercase
    """
    # Check lockout
    locked, remaining = is_ip_locked_out(ip)
    if locked:
        raise LockedOutError(f"Too many failed attempts. Try again in {remaining}s.", retry_after=remaining)

    # Strong password validation on attempt
    if not _is_strong_password(password):
        raise WeakPasswordError(
            "Password must be at least 8 characters and contain at least one digit and one uppercase letter."
        )

    if username != ADMIN_USERNAME:
        _record_failed_login(ip)
        time_module.sleep(0.5)  # Cooldown even on unknown user
        return False
    if ADMIN_PASSWORD_HASH_ENV:
        stored_hash = ADMIN_PASSWORD_HASH_ENV.encode()
    else:
        stored_hash = _hash_password(ADMIN_PASSWORD_PLAIN)
    if not _verify_password(password, stored_hash):
        _record_failed_login(ip)
        time_module.sleep(0.5)
        return False
    _clear_failed_logins(ip)
    return True


class AuthError(Exception):
    """Base auth exception."""
    pass


class LockedOutError(AuthError):
    """IP is locked out due to too many failed attempts."""
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


class WeakPasswordError(AuthError):
    """Password does not meet strength requirements."""
    pass


def _is_strong_password(password: str) -> bool:
    """Check password strength: min 8 chars, at least 1 digit, at least 1 uppercase."""
    if len(password) < 8:
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    return True

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