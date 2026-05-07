# Security Rotation Note

**Date:** 2026-05-07
**Context:** Deployment on Contabo (app.finco.one)

---

## Password Rotation Required

The default login password (`fincoGPT2026!`) was documented in early deployment docs and chat screenshots.

**You must rotate this password before production use.**

### On Contabo VPS, run:

```bash
# Generate a new strong password
NEW_PASSWORD=$(openssl rand -base64 24)

# Update the session auth password (set as environment variable)
# Option 1: Set in systemd service override
sudo systemctl set-environment FINCO_ADMIN_PASSWORD="$NEW_PASSWORD"
sudo systemctl restart finco-web

# Option 2: Add to /etc/environment
echo "FINCO_ADMIN_PASSWORD=$NEW_PASSWORD" | sudo tee -a /etc/environment
sudo systemctl restart finco-web

# Update nginx htpasswd (if nginx Basic Auth is still used as extra layer)
sudo htpasswd -b /etc/nginx/.htpasswd admin "$NEW_PASSWORD"
sudo systemctl reload nginx

# Verify new password works
curl -s -u admin:"$NEW_PASSWORD" https://app.finco.one/health
```

### Generate a strong password locally:

```bash
# Linux/macOS:
openssl rand -base64 32

# Or use a password manager's generator
```

---

## What This Protects Against

- Early docs/chat messages contained the default password
- If those messages were screenshotted/shared, the password may be compromised
- Rotating ensures only current credentials are valid

---

## Future: Store Secrets Properly

For production, store secrets in:
- `/etc/environment` (simple, limited)
- `.env` file with restricted permissions
- HashiCorp Vault
- Cloud provider secrets manager

Never commit real passwords to the repository.