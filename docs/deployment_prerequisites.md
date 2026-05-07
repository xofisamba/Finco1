# Deployment Prerequisites — app.finco.one

**Date:** 2026-05-07
**Purpose:** Exact list of what the operator must provide before running `deploy.sh`

---

## Required from Operator

### 1. DNS — A Record (must exist BEFORE deployment)

```
app.finco.one → YOUR_VPS_IP
```

**How to verify:**
```bash
# From any machine:
dig +short app.finco.one
# or:
nslookup app.finco.one
```

If this returns nothing or wrong IP → deployment will fail at certbot step.

**Who provides this:** DNS registrar (if using Cloudflare, GoDaddy, etc.) — NOT Contabo panel.

---

### 2. Server Access

| Item | Value | Notes |
|------|-------|-------|
| VPS IP | `___.___.___.___` | Must be reachable from internet |
| SSH username | e.g. `root` or `ubuntu` | Sudo privileges required |
| SSH access | Password OR SSH key | Key preferred for security |
| sudo/root | Required | Script runs `apt install`, `systemctl`, etc. |

**How to verify:**
```bash
ssh user@YOUR_VPS_IP
# Should get shell prompt
sudo whoami  # should return: root
```

---

### 3. Deployment Decisions

| Item | Required | Notes |
|------|----------|-------|
| `FINCO_AUTH_USER` | ✅ Required | Basic Auth username (e.g. `admin`) |
| `FINCO_AUTH_PASS` | ✅ Required | Basic Auth password (use strong password) |
| Production email | For certbot | Used for Let's Encrypt expiry alerts |

**To run deploy script:**
```bash
sudo FINCO_AUTH_USER=admin FINCO_AUTH_PASS=your_password_here bash deploy.sh
```

---

## What Operator Does NOT Need to Provide

- ❌ Registrar credentials (if DNS already configured)
- ❌ Contabo billing access
- ❌ SSL certificates (certbot obtains automatically)
- ❌ Nginx configuration knowledge
- ❌ Python/deployment experience
- ❌ Contabo panel access (SSH is sufficient)

---

## Pre-Deployment Checklist

Run this on your local machine BEFORE running deploy.sh:

```bash
# 1. DNS check
dig +short app.finco.one   # Must return VPS IP

# 2. SSH check
ssh user@vps_ip "echo 'SSH OK'"   # Must work

# 3. Email for certbot (optional, can use --register-unsafely-without-email)
#    If you want expiry alerts, have email ready

# 4. Strong password generated
#    e.g. 16+ chars, mix of letters/numbers/symbols
```

---

## What Happens If DNS Is Wrong

If `app.finco.one` does not resolve to the VPS IP:
- `certbot` will fail with "DNS lookup failed"
- Deployment script will warn but continue on HTTP only
- **No HTTPS** will be obtained
- Deploy script exits with warning (not error) after certbot step

**Fix:** Add A record at DNS registrar, wait 5-30 min for propagation, then re-run:
```bash
sudo bash deploy.sh   # will retry certbot
```

---

## What Happens If pytest Fails

Deploy script **exits immediately** with error message.
`nginx` and `finco-web.service` are NOT started.

Fix the test failures first, then re-run deployment.

---

## What Happens If Basic Auth Credentials Wrong

If `FINCO_AUTH_USER` or `FINCO_AUTH_PASS` env vars are missing:
```
ERROR: FINCO_AUTH_USER and FINCO_AUTH_PASS env vars are required.
```

Fix: re-run with correct env vars.

---

## Security Notes

- Basic Auth is **interim protection only** — not real auth
- Credentials transmitted over HTTPS (certbot must succeed)
- htpasswd file stored at `/etc/nginx/.htpasswd`
- Real session-based auth (bcrypt + cookies) required before B2B/public use
- Do NOT share htpasswd credentials broadly

---

## Related Docs

- `docs/deploy_to_contabo.sh` — the actual deployment script
- `docs/contabo_private_deployment.md` — detailed manual setup guide
- `docs/deployment_smoke_checklist.md` — post-deploy verification