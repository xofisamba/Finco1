# Auth Lite — Internal Access Control

**Date:** 2026-05-07
**Branch:** `feature/auth-lite` (merged to main)
**Target:** `app.finco.one`

---

## Architecture

**Stack:** FastAPI sessions + signed cookies via `itsdangerous` + bcrypt password hashing

**No database, no Redis, no JWT.** Stateless server-side sessions with signed cookies.

### Session Flow

```
User → GET / → no cookie → Redirect to /login
User → POST /login (admin/[SET_ON_SERVER]) → bcrypt verify → create session token
  → set secure httponly samesite=lax cookie (finco_session)
  → Redirect to /
User → subsequent requests → cookie sent automatically
  → decode_session_token() → SessionData (user_id, username, login_at)
  → validate not expired → request proceeds
User → POST /logout → clear cookie → redirect to /login
```

### Session Data

```python
class SessionData:
    user_id: str      # "1" (single-user mode)
    username: str     # "admin"
    login_at: datetime  # UTC timestamp
    is_expired() -> bool  # checks against SESSION_MAX_AGE_HOURS (default 24h)
```

### Token Format

```
base64(timestamp.user_id.username.login_at).base64(signature)
```

Signed with `FINCO_SECRET_KEY` using itsdangerous `URLSafeTimedSerializer`.

---

## Env Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `FINCO_SECRET_KEY` | `dev-secret-please-change...` | Signing key for session cookies |
| `FINCO_ADMIN_USER` | `admin` | Login username |
| `FINCO_ADMIN_PASSWORD` | `[SET_ON_SERVER]` | Login password (plain) |
| `FINCO_ADMIN_PASSWORD_HASH` | (none) | bcrypt hash (overrides plain password) |
| `FINCO_SESSION_HOURS` | `24` | Session TTL |
| `FINCO_COOKIE_SECURE` | `true` | Cookie security (HTTPS only) |
| `FINCO_COOKIE_SAMESITE` | `lax` | Cookie samesite policy |

**Production note:** Set `FINCO_SECRET_KEY` to a long random string. In production, never use the default.

---

## Routes

### Public (no auth)
- `GET /public-health` — safe health check, no auth required
- `GET /login` — login form page

### Auth routes
- `POST /login` — verify credentials, set session cookie
- `POST /logout` — clear session cookie, redirect to /login

### Protected (requires valid session)
- `GET /` — main dashboard
- `POST /run` — run model
- `POST /compare` — scenario comparison
- `POST /validate` — inline form validation
- `GET/POST /download` — Excel export
- `GET /health` — private health check (returns 401 without auth)

---

## Security Properties

| Property | Implementation |
|----------|----------------|
| Passwords | bcrypt (rounds=12), never stored in plain text |
| Cookies | `httponly=True` — JS cannot read session |
| Cookie signing | itsdangerous prevents tampering |
| Session expiry | Server-side check via `is_expired()` |
| Secure flag | `FINCO_COOKIE_SECURE=true` (HTTPS only in production) |
| Samesite | `lax` — CSRF-safe in most scenarios |

**NOT implemented:** CSRF token per request, rate limiting, brute-force lockout, refresh tokens.

---

## Limitations

- Single user only (no multi-user, no roles)
- No refresh tokens (session expires, user re-logs in)
- No brute-force protection
- No password change UI
- No user management

---

## Future Migration Path

To full auth, the following would be needed:
1. Database with users table (替代 single-user hardcoded admin)
2. Role-based access control (admin vs viewer)
3. Password change UI
4. Brute-force protection (rate limiting or lockout)
5. CSRF tokens for form POSTs
6. Audit log (who ran what, when)
7. Optional: OAuth/SSO integration

The session architecture is compatible with adding any of these later.

---

## Nginx Basic Auth — Deprecated

**Old:** nginx `auth_basic` + htpasswd (used in previous deployments)

**New:** Application-level session auth (this feature)

Nginx `auth_basic` can be removed from nginx config. The app now handles authentication.

To keep both (extra defense in depth):
```
# Keep Basic Auth as additional layer (optional)
location / {
    auth_basic "FincoGPT";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://127.0.0.1:8000;
}
```

But for internal use, app-level auth alone is sufficient.

---

## Default Credentials

| Setting | Value |
|---------|-------|
| Username | `admin` |
| Password | `[SET_ON_SERVER]` |
| Session TTL | 24 hours |

**Change password** via env var: `FINCO_ADMIN_PASSWORD=your_strong_password`

Or use bcrypt hash: `FINCO_ADMIN_PASSWORD_HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw('secret'.encode(), bcrypt.gensalt(rounds=12)).decode())")`