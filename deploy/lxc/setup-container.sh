#!/usr/bin/env bash
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────
REPO_URL="${REPO_URL:-https://github.com/your-org/message.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="/opt/message"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="/var/log/message"
NGINX_SITE="message"
DOMAIN="${DOMAIN:-api.example.com}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"

# ── Colors ─────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── System packages ────────────────────────────────────────────
info "Installing system packages..."
apt update -qq
apt install -y -qq nginx redis-server python3.14-venv git curl certbot python3-certbot-nginx

# ── Create directories ─────────────────────────────────────────
info "Creating directories..."
mkdir -p "$APP_DIR" "$LOG_DIR" "$APP_DIR/uploads"

# ── Clone / sync code ──────────────────────────────────────────
if [ -d "$APP_DIR/.git" ]; then
    info "Updating existing repo..."
    cd "$APP_DIR" && git pull origin "$BRANCH"
else
    info "Cloning repo..."
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

# ── Python venv ────────────────────────────────────────────────
info "Setting up Python virtual environment..."
python3.14 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
"$VENV_DIR/bin/pip" install -e "$APP_DIR"

# ── Environment file ───────────────────────────────────────────
if [ ! -f "$APP_DIR/.env" ]; then
    info "Creating .env from template..."
    cp "$APP_DIR/deploy/lxc/.env.prod" "$APP_DIR/.env"
    SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/change-me-to-a-random-secret/$SECRET/" "$APP_DIR/.env"
    sed -i "s/change-me-to-another-random-secret/$JWT_SECRET/" "$APP_DIR/.env"
else
    info ".env already exists, skipping."
fi

# ── Database ───────────────────────────────────────────────────
info "Running database migrations..."
cd "$APP_DIR"
"$VENV_DIR/bin/flask" db upgrade

info "Seeding initial data..."
"$VENV_DIR/bin/flask" seed

# ── systemd service ────────────────────────────────────────────
info "Installing systemd service..."
cp "$APP_DIR/deploy/lxc/message.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable message.service
systemctl restart message.service

# ── Nginx ──────────────────────────────────────────────────────
info "Configuring Nginx..."
cp "$APP_DIR/deploy/lxc/message.nginx" "/etc/nginx/sites-available/$NGINX_SITE"
if [ ! -L "/etc/nginx/sites-enabled/$NGINX_SITE" ]; then
    ln -s "/etc/nginx/sites-available/$NGINX_SITE" "/etc/nginx/sites-enabled/"
fi
rm -f /etc/nginx/sites-enabled/default
systemctl enable nginx
systemctl restart nginx

# ── Logrotate ──────────────────────────────────────────────────
info "Setting up log rotation..."
cat > /etc/logrotate.d/message <<'EOF'
/var/log/message/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF

# ── Firewall hint ──────────────────────────────────────────────
info "---"
info "Container setup complete!"
info ""
info "  App running at: http://localhost:8080/api/v1/"
info "  Health check:   http://localhost:8080/health"
info ""
info "Next steps on the HOST (not inside container):"
info "  1. Install nginx on host:  apt install nginx"
info "  2. Proxy host:80 → container:8080"
info "  3. Run certbot:            certbot --nginx -d $DOMAIN"
info ""
info "Or forward ports in LXC config:"
info "  lxc config device add message proxy80 proxy listen=tcp:0.0.0.0:80 connect=tcp:127.0.0.1:8080"
info "---"
