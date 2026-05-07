#!/bin/bash
# FincoGPT — Contabo Deployment Script (Hardened v2)
# Run as: sudo FINCO_AUTH_USER=admin FINCO_AUTH_PASS=secret123 bash deploy.sh
# Target: Ubuntu 22.04 LTS on Contabo
# Domain: app.finco.one

set -euo pipefail

APP_DIR="/opt/finco1"
APP_USER="www-data"
APP_GROUP="www-data"
DOMAIN="app.finco.one"
EMAIL="${FINCO_EMAIL:-admin@finco.one}"

echo "=== FincoGPT Contabo Deployment (Hardened v2) ==="
echo ""

# ── Validate root ────────────────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: Must run as root (sudo)."
    exit 1
fi

# ── Env vars (required) ─────────────────────────────────────────────────────
if [ -z "${FINCO_AUTH_USER:-}" ] || [ -z "${FINCO_AUTH_PASS:-}" ]; then
    echo "ERROR: FINCO_AUTH_USER and FINCO_AUTH_PASS env vars are required."
    echo "  sudo FINCO_AUTH_USER=admin FINCO_AUTH_PASS=secret123 bash deploy.sh"
    exit 1
fi

AUTH_USER="$FINCO_AUTH_USER"
AUTH_PASS="$FINCO_AUTH_PASS"

# ── Phase 1: System packages ──────────────────────────────────────────────────
echo "[1/8] Installing system packages..."
apt update
apt install -y \
    python3 python3-pip python3-venv \
    nginx certbot python3-certbot-nginx \
    apache2-utils git curl ufw

# ── Phase 2: Firewall ────────────────────────────────────────────────────────
echo "[2/8] Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 'Nginx Full'
ufw --force enable

# ── Phase 3: App directory ────────────────────────────────────────────────────
echo "[3/8] Setting up application directory..."
mkdir -p "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
    git clone https://github.com/xofisamba/Finco1.git "$APP_DIR"
    cd "$APP_DIR"
    git checkout main
else
    cd "$APP_DIR"
    git fetch origin main && git pull origin main --ff || { echo "ERROR: failed to pull latest main"; exit 1; }
fi

# ── Phase 4: Python venv ──────────────────────────────────────────────────────
echo "[4/8] Creating Python venv..."
python3 -m venv "$APP_DIR/.venv"
source "$APP_DIR/.venv/bin/activate"
pip install --upgrade pip
pip install gunicorn fastapi uvicorn jinja2 pytest

if [ -f "$APP_DIR/requirements.txt" ]; then
    pip install -r "$APP_DIR/requirements.txt" 2>/dev/null || true
fi

# ── Phase 5: pytest verification — FAIL FAST ─────────────────────────────────
echo "[5/8] Running pytest (must pass before deployment continues)..."
cd "$APP_DIR"
source "$APP_DIR/.venv/bin/activate"
if ! /opt/finco1/.venv/bin/python -m pytest -p no:randomly -q 2>&1 | tail -5; then
    echo ""
    echo "ERROR: pytest failed. Fix failures before deploying."
    echo "nginx and finco-web will NOT be started."
    exit 1
fi
echo "pytest: all pass ✅"

# ── Phase 6: systemd service (idempotent) ────────────────────────────────────
echo "[6/8] Creating systemd service (idempotent)..."
cat > /etc/systemd/system/finco-web.service << 'EOF'
[Unit]
Description=FincoGPT Internal Demo
After=network.target
Wants=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/finco1
ExecStart=/opt/finco1/.venv/bin/gunicorn \
    --workers 2 \
    --threads 4 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --keep-alive 65 \
    --log-level info \
    --access-logfile /var/log/finco-web/access.log \
    --error-logfile /var/log/finco-web/error.log \
    -k uvicorn.workers.UvicornWorker \
    main_web:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

mkdir -p /var/log/finco-web
chown -R www-data:www-data /var/log/finco-web
# Fix permissions on app directory
chown -R www-data:www-data "$APP_DIR" 2>/dev/null || true

systemctl daemon-reload
systemctl enable finco-web
systemctl restart finco-web || systemctl start finco-web
sleep 2
echo "finco-web service: $(systemctl is-active finco-web) ✅"

# Verify service is running
if ! systemctl is-active finco-web > /dev/null 2>&1; then
    echo "ERROR: finco-web service failed to start. Check logs:"
    journalctl -u finco-web --no-pager -n 20
    exit 1
fi

# ── Phase 7: Nginx + Let's Encrypt (safe 2-step flow) ───────────────────────
echo "[7/8] Configuring Nginx + HTTPS (2-step flow)..."

# ── Step A: HTTP-only nginx config with ACME challenge ─────────────────────
# This config does NOT reference SSL certificates (they don't exist yet)
mkdir -p /var/www/html/.well-known/acme-challenge
chown -R www-data:www-data /var/www/html 2>/dev/null || true

cat > /etc/nginx/sites-available/finco-web-http << 'EOF'
server {
    listen 80;
    server_name app.finco.one;

    # Let's Encrypt ACME challenge — must be served from /var/www/html
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 120s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }
}
EOF

# Remove old HTTPS config if exists
rm -f /etc/nginx/sites-enabled/finco-web
rm -f /etc/nginx/sites-available/finco-web

# Enable HTTP config and test
ln -sf /etc/nginx/sites-available/finco-web-http /etc/nginx/sites-enabled/finco-web
nginx -t || { echo "ERROR: HTTP nginx config invalid"; exit 1; }
systemctl reload nginx
echo "Nginx HTTP config: loaded ✅"

# ── Step B: DNS verification before certbot ────────────────────────────────
echo "Verifying DNS for $DOMAIN..."
VPS_IP=$(curl -s ifconfig.me 2>/dev/null || echo "")
EXPECTED_IP="156.67.24.119"

# Check if domain resolves to this server
RESOLVED_IP=$(dig +short "$DOMAIN" A 2>/dev/null | grep -v '\.$' | head -1)
if [ -z "$RESOLVED_IP" ]; then
    echo "WARNING: $DOMAIN does not resolve to any IP yet."
    echo "  DNS may still be propagating. Waiting 10s..."
    sleep 10
    RESOLVED_IP=$(dig +short "$DOMAIN" A 2>/dev/null | grep -v '\.$' | head -1)
fi

if [ "$RESOLVED_IP" != "$EXPECTED_IP" ]; then
    echo "ERROR: $DOMAIN resolves to $RESOLVED_IP, expected $EXPECTED_IP"
    echo "  Add A record: app.finco.one → $EXPECTED_IP"
    echo "  Current resolve: $(dig +short "$DOMAIN" A)"
    echo "  Skipping HTTPS setup — HTTP-only mode active."
    HTTPS_ENABLED="no"
else
    echo "DNS OK: $DOMAIN → $RESOLVED_IP ✅"
    HTTPS_ENABLED="yes"
fi

# ── Step C: certbot (only if DNS resolves) ───────────────────────────────────
if [ "$HTTPS_ENABLED" = "yes" ]; then
    echo "Running certbot..."
    if certbot certonly --webroot -w /var/www/html -d "$DOMAIN" --register-unsafely-without-email --agree-tos -n 2>&1; then
        echo "SSL certificate obtained ✅"
    else
        echo "WARNING: certbot failed. Check DNS / firewall."
        echo "App is still accessible over HTTP (unencrypted)."
        HTTPS_ENABLED="no"
    fi
fi

# ── Step D: HTTPS config (only if certs exist) ─────────────────────────────────
if [ "$HTTPS_ENABLED" = "yes" ]; then
    # Verify cert files exist before writing HTTPS config
    CERT_CHAIN="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    CERT_KEY="/etc/letsencrypt/live/$DOMAIN/privkey.pem"

    if [ ! -f "$CERT_CHAIN" ] || [ ! -f "$CERT_KEY" ]; then
        echo "ERROR: SSL certificates not found at expected paths."
        echo "  Expected: $CERT_CHAIN"
        echo "  Expected: $CERT_KEY"
        echo "  This should not happen if certbot succeeded."
        HTTPS_ENABLED="no"
    fi
fi

if [ "$HTTPS_ENABLED" = "yes" ]; then
    # Create Basic Auth htpasswd
    htpasswd -bc /etc/nginx/.htpasswd "$AUTH_USER" "$AUTH_PASS" 2>/dev/null || \
        htpasswd -b /etc/nginx/.htpasswd "$AUTH_USER" "$AUTH_PASS"

    # Write HTTPS nginx config
    cat > /etc/nginx/sites-available/finco-web << EOF
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name $DOMAIN;

    ssl_certificate $CERT_CHAIN;
    ssl_certificate_key $CERT_KEY;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Basic Auth — ENABLED by default (interim protection)
    auth_basic "FincoGPT Internal — Authorized Only";
    auth_basic_user_file /etc/nginx/.htpasswd;

    # Optional IP whitelist (uncomment and set your IP):
    # allow YOUR_IP;
    # deny all;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 120s;
    }

    location /static/ {
        alias /opt/finco1/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }

    gzip on;
    gzip_types text/plain text/css application/javascript;
    gzip_min_length 1000;
}
EOF

    nginx -t || { echo "ERROR: HTTPS nginx config invalid"; exit 1; }
    systemctl reload nginx
    echo "Nginx HTTPS config: loaded with Basic Auth ✅"
else
    # HTTP-only mode: enable Basic Auth on HTTP config
    htpasswd -bc /etc/nginx/.htpasswd "$AUTH_USER" "$AUTH_PASS" 2>/dev/null || \
        htpasswd -b /etc/nginx/.htpasswd "$AUTH_USER" "$AUTH_PASS"

    # Add Basic Auth to HTTP config
    sed -i '/server_name/i\    auth_basic "FincoGPT Internal — Authorized Only";\n    auth_basic_user_file /etc/nginx/.htpasswd;' /etc/nginx/sites-available/finco-web-http
    nginx -t && systemctl reload nginx || true
    echo "Nginx HTTP config: loaded with Basic Auth (no HTTPS yet) ⚠️"
fi

# ── Phase 8: Verify ───────────────────────────────────────────────────────────
echo "[8/8] Verification..."
sleep 2

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "Service health: HTTP $HTTP_CODE ✅"
else
    echo "WARNING: health check returned HTTP $HTTP_CODE"
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "URL: https://app.finco.one"
echo "Auth: $AUTH_USER (Basic Auth)"
echo "HTTPS enabled: $HTTPS_ENABLED"
echo ""
if [ "$HTTPS_ENABLED" = "no" ]; then
    echo "⚠️  HTTPS not enabled — fix DNS A record for app.finco.one → 156.67.24.119"
    echo "   Then re-run: sudo bash deploy.sh"
fi
echo ""
echo "NOTE: Basic Auth is interim protection only."
echo "      Real session-based auth required before B2B/public use."
echo ""