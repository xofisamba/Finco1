# Auth & Security — Login Hardening

## What's Implemented

### 1. CSRF Protection on Login Form

**Mechanism:** Signed token via `itsdangerous` URLSafeTimedSerializer (separate key from session).

**Flow:**
1. `GET /login` → `generate_csrf_token()` creates a signed 48-char hex token
2. Token embedded as `<input type="hidden" name="csrf_token">` in login form
3. `POST /login` → `validate_csrf_token(csrf_token)` validates before processing
4. Invalid/expired/missing token → HTTP 403 with friendly error

**Key:** `FINCO_CSRF_SECRET` env var (defaults to `FINCO_SECRET_KEY`).

**Why separate CSRF key:** If session key leaks, CSRF tokens remain independently valid.

**Token TTL:** 24 hours (ample for a login form).

**Validation:** A new token is generated on every `GET /login` and after every failed POST.

---

### 2. Login Rate Limiting (In-Memory, Per-IP)

**Mechanism:** Simple in-memory store (`dict` + `Lock`) keyed by client IP.

**Limits:**
- `MAX_LOGIN_FAILURES = 5` failures before lockout
- `LOCKOUT_SECONDS = 300` (5 minutes) lockout duration

**Flow:**
1. Each failed login → `_record_failed_login(ip)` increments counter
2. On next request: `_check_rate_limit(ip)` returns `(allowed, seconds_remaining)`
3. If locked out: HTTP 429 with `"Too many failed attempts. Try again in Xs."`
4. Successful login → `_clear_failed_logins(ip)` resets counter

**Headers checked for IP:** `X-Forwarded-For` (first entry) → `request.client.host`

**In-Memory note:** Rate limit state is per-process. With gunicorn workers > 1, separate processes don't share state. For a single-admin VPS this is fine. If you scale to multiple workers, consider moving to a file-based or Redis store.

---

### 3. Error Messages

**Invalid credentials:** `"Invalid username or password."` (no leak of which field is wrong)

**CSRF failure:** `"Invalid or expired form. Please try again."` (HTTP 403)

**Rate limited:** `"Too many failed attempts. Try again in Xs."` (HTTP 429)

**All cases:** A fresh `csrf_token` is always included in the response context.

---

## Env Vars

| Variable | Default | Description |
|---|---|---|
| `FINCO_CSRF_SECRET` | `FINCO_SECRET_KEY` | Signing key for CSRF tokens |
| `FINCO_SESSION_HOURS` | `24` | Session TTL |
| `FINCO_COOKIE_SECURE` | `true` | Require HTTPS for cookie |

---

## Security Headers (nginx)

The nginx config sets:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

---

## What Could Be Added Later

- Failed login alerting (log + notification after N lockouts)
- Per-user lockout (not just per-IP) if multi-user
- Redis-backed rate limit store for multi-worker deployments
- CAPTCHA after 3rd failure
- MFA (TOTP)
- Login audit log in DB (who, when, IP, success/failure)

---

## Testing

```bash
# Smoke test
curl -X POST http://127.0.0.1:8000/login \
  -d "username=admin&password=wrong&csrf_token=invalid"

# Expect: 403 with "Invalid or expired form"

# Rate limit test (5 failures)
for i in {1..6}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://127.0.0.1:8000/login \
    -d "username=admin&password=wrong&csrf_token=$(python3 -c "from app.auth import generate_csrf_token; print(generate_csrf_token())")"
done
# Expect: 200, 200, 200, 200, 200, 429
```
