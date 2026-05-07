#!/bin/bash
# FincoGPT — Contabo Deployment Script
# Run as: sudo bash deploy.sh
# Target: Ubuntu 22.04 LTS on Contabo
# Domain: app.finco.one

set -euo pipefail

APP_DIR="/opt/finco1"
APP_USER="www-data"
APP_GROUP="www-data"
DOMAIN="app.finco.one"
EMAIL="admin@finco.one"

echo "=== FincoGPT Contabo Deployment ==="

# ── Phase 1: System packages ──────────────────────────────────────────────
echo "[1/7] Installing system packages..."
apt update
apt install -y \
    python3 python3-pip python3-venv \
    nginx certbot python3-certbot-nginx \
    apache2-utils git curl ufw

# ── Phase 2: Firewall ───────────────────────────────────────────────────────
echo "[2/7] Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 'Nginx Full'   # 80 + 443
ufw --force enable

# ── Phase 3: App directory ──────────────────────────────────────────────────
echo "[3/7] Setting up application directory..."
mkdir -p "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
    git clone https://github.com/xofisamba/Finco1.git "$APP_DIR"
    cd "$APP_DIR"
    git checkout main
else
    cd "$APP_DIR"
    git pull origin main
fi

# ── Phase 4: Python venv ────────────────────────────────────────────────────
echo "[4/7] Creating Python venv..."
python3 -m venv "$APP_DIR/.venv"
source "$APP_DIR/.venv/bin/activate"
pip install --upgrade pip
pip install gunicorn fastapi uvicorn jinja2

# Check requirements.txt exists and install
if [ -f "$APP_DIR/requirements.txt" ]; then
    pip install -r "$APP_DIR/requirements.txt"
fi

# ── Phase 5: pytest verification ────────────────────────────────────────────
echo "[5/7] Running pytest..."
cd "$APP_DIR"
source "$APP_DIR/.venv/bin/activate"
python3 -m pytest -p no:randomly -q || echo "WARNING: pytest had failures — review before proceeding"

# ── Phase 6: systemd service ───────────────────────────────────────────────
echo "[6/7] Creating systemd service..."
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
systemctl start finco-web
systemctl status finco-web --no-pager

# ── Phase 7: Nginx + Let's Encrypt ──────────────────────────────────────────
echo "[7/7] Configuring Nginx + HTTPS..."
cat > /etc/nginx/sites-available/finco-web << 'EOF'
server {
    listen 80;
    server_name app.finco.one;

    # Redirect all HTTP → HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name app.finco.one;

    # SSL (certbot will fill these)
    ssl_certificate /etc/letsencrypt/live/app.finco.one/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.finco.one/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Basic Auth (interim protection)
    # Uncomment the next 2 lines to enable:
    # auth_basic "FincoGPT Internal — Authorized Only";
    # auth_basic_user_file /etc/nginx/.htpasswd;

    # IP whitelist example (uncomment to enable):
    # allow YOUR_IP_HERE;
    # deny all;

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

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/javascript;
    gzip_min_length 1000;
}

# HTTP only (redirect)
server {
    listen 80;
    server_name app.finco.one;
    return 301 https://$host$request_uri;
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/finco-web /etc/nginx/sites-enabled/
nginx -t

# Stop nginx temporarily for certbot
systemctl stop nginx

# Obtain SSL certificate
echo "Running certbot — enter your email when prompted:"
certbot certonly --nginx -d "$DOMAIN" --register-unsafely-without-email --agree-tos -n || {
    echo "WARNING: certbot failed. Check DNS / firewall / port 80 access."
    echo "Nginx will start without HTTPS for now."
}

# Start nginx
systemctl start nginx
systemctl reload nginx

# Auto-renewal check
systemctl status certbot.timer --no-pager || echo "Note: certbot timer may not be enabled"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "NEXT STEPS:"
echo "1. Enable Basic Auth:"
echo "   htpasswd -c /etc/nginx/.htpasswd admin"
echo "   # uncomment auth_basic lines in /etc/nginx/sites-available/finco-web"
echo "   nginx -t && systemctl reload nginx"
echo ""
echo "2. Set IP whitelist (optional):"
echo "   # edit /etc/nginx/sites-available/finco-web, set your IP"
echo "   nginx -t && systemctl reload nginx"
echo ""
echo "3. Run smoke tests:"
echo "   curl https://$DOMAIN/health"
echo "   # See docs/deployment_smoke_checklist.md"
echo ""
echo "4. To restart after changes:"
echo "   systemctl restart finco-web && systemctl reload nginx"
echo ""