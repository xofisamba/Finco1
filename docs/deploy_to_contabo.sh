#!/bin/bash
# FincoGPT — Contabo Deployment Script (Hardened)
# Run as: sudo bash deploy.sh
# Target: Ubuntu 22.04 LTS on Contabo
# Domain: app.finco.one

set -euo pipefail

APP_DIR="/opt/finco1"
APP_USER="www-data"
APP_GROUP="www-data"
DOMAIN="app.finco.one"

echo "=== FincoGPT Contabo Deployment (Hardened) ==="
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
    git fetch origin main && git checkout main
    git pull origin main --ff || { echo "ERROR: failed to pull latest main"; exit 1; }
fi

# ── Phase 4: Python venv ──────────────────────────────────────────────────────
echo "[4/8] Creating Python venv..."
python3 -m venv "$APP_DIR/.venv"
source "$APP_DIR/.venv/bin/activate"
pip install --upgrade pip
pip install gunicorn fastapi uvicorn jinja2

if [ -f "$APP_DIR/requirements.txt" ]; then
    pip install -r "$APP_DIR/requirements.txt"
fi

# ── Phase 5: pytest verification — FAIL FAST ─────────────────────────────────
echo "[5/8] Running pytest (must pass before deployment continues)..."
cd "$APP_DIR"
source "$APP_DIR/.venv/bin/activate"
if ! python3 -m pytest -p no:randomly -q; then
    echo ""
    echo "ERROR: pytest failed. Fix failures before deploying."
    echo "Do NOT proceed with deployment — nginx and systemd will NOT start."
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
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
EOF

mkdir -p /var/log/finco-web
chown -R www-data:www-data /var/log/finco-web
systemctl daemon-reload
systemctl enable finco-web
systemctl restart finco-web || systemctl start finco-web
echo "finco-web service: $(systemctl is-active finco-web) ✅"

# ── Phase 7: Nginx + Let's Encrypt (safe 2-step flow) ───────────────────────
echo "[7/8] Configuring Nginx + HTTPS (2-step flow)..."

# Step A: HTTP-only nginx config (no SSL references — passes nginx -t before certs exist)
cat > /etc/nginx/sites-available/finco-web-http << 'EOF'
server {
    listen 80;
    server_name app.finco.one;

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

# Remove old HTTPS config if exists (will be replaced after certbot)
rm -f /etc/nginx/sites-available/finco-web
rm -f /etc/nginx/sites-enabled/finco-web

# Enable HTTP config, test, start
ln -sf /etc/nginx/sites-available/finco-web-http /etc/nginx/sites-enabled/finco-web
nginx -t || { echo "ERROR: nginx config invalid"; exit 1; }
systemctl reload nginx

# Step B: Obtain SSL certificate
echo "Running certbot..."
if certbot certonly --webroot -w /var/www/html -d "$DOMAIN" --register-unsafely-without-email --agree-tos -n; then
    echo "SSL certificate obtained ✅"
else
    echo "WARNING: certbot failed. Check DNS A record for $DOMAIN → $(curl -s ifconfig.me)"
    echo "Nginx will start on HTTP only. Fix DNS and re-run certbot separately."
fi

# Step C: Install HTTPS nginx config (now that SSL files exist or we use HTTP fallback)
cat > /etc/nginx/sites-available/finco-web << EOF
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name $DOMAIN;

    # SSL certificate (only if certbot succeeded)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Basic Auth — ENABLED by default (interim protection, not real auth)
    # This is REQUIRED — app.finco.one must never be publicly accessible without protection
    auth_basic "FincoGPT Internal — Authorized Only";
    auth_basic_user_file /etc/nginx/.htpasswd;

    # Optional: IP whitelist (uncomment and set your IP)
    # allow YOUR_IP_HERE;
    # deny all;

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

# Create htpasswd (Basic Auth enforced — no fallback to open access)
htpasswd -bc /etc/nginx/.htpasswd "$AUTH_USER" "$AUTH_PASS" 2>/dev/null || {
    # If file exists, just add user
    htpasswd -b /etc/nginx/.htpasswd "$AUTH_USER" "$AUTH_PASS"
}

nginx -t || { echo "ERROR: HTTPS nginx config invalid"; exit 1; }
systemctl reload nginx
echo "Nginx: reloaded with Basic Auth ✅"

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
echo "URL: https://$DOMAIN"
echo "Auth: $AUTH_USER (Basic Auth)"
echo ""
echo "NOTE: Basic Auth is interim protection only."
echo "      Real session-based auth must be added before B2B/public use."
echo ""
echo "To restart after changes:"
echo "  systemctl restart finco-web && systemctl reload nginx"
echo ""