#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh  –  Full deploy script for hoodlink.duckdns.org
# Run this on your Linux server from the project directory.
# ─────────────────────────────────────────────────────────────────────────────
set -e

DOMAIN="hoodlink.duckdns.org"
EMAIL="nahid288724@gmail.com"   # Let's Encrypt notification email

echo "=============================="
echo " HoodLink Nginx Deploy Script "
echo "=============================="

# ── STEP 1: Start everything with HTTP-only nginx (for cert challenge) ────────
echo ""
echo "▶ Step 1: Starting services with HTTP-only Nginx config..."

# Temporarily use the init config (HTTP only, no SSL)
cp nginx/nginx.conf nginx/nginx.conf.bak 2>/dev/null || true
cp nginx/nginx-init.conf nginx/nginx.conf

docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d --build db redis web nginx

echo "   Waiting 10s for services to start..."
sleep 10

# ── STEP 2: Obtain SSL certificate via Certbot ────────────────────────────────
echo ""
echo "▶ Step 2: Obtaining SSL certificate from Let's Encrypt..."

docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN"

# Copy certs to nginx/ssl/ for nginx to use
echo "   Copying certs..."
docker compose run --rm --entrypoint="" certbot sh -c \
  "cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem /etc/letsencrypt/live/$DOMAIN/ && \
   cp /etc/letsencrypt/live/$DOMAIN/privkey.pem /etc/letsencrypt/live/$DOMAIN/"

# ── STEP 3: Switch to full HTTPS nginx config ─────────────────────────────────
echo ""
echo "▶ Step 3: Switching to full HTTPS Nginx config..."
cp nginx/nginx.conf.bak nginx/nginx.conf

# Reload nginx
docker compose exec nginx nginx -s reload

# ── STEP 4: Start certbot auto-renewal ────────────────────────────────────────
echo ""
echo "▶ Step 4: Starting Certbot auto-renewal service..."
docker compose up -d certbot

echo ""
echo "✅ Done! Your site is live at: https://$DOMAIN"
echo "   - HTTP  → 301 redirect to HTTPS"
echo "   - HTTPS → Django/Daphne on port 4003 (internal)"
echo "   - WebSockets on /ws/"
echo "   - Static files served by Nginx directly"
