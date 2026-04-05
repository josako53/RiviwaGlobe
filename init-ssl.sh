#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# init-ssl.sh — Obtain initial Let's Encrypt certificate for api.riviwa.com
#
# Run ONCE on the server before starting the full stack:
#   chmod +x init-ssl.sh && ./init-ssl.sh
#
# After this script completes, start the full stack:
#   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

DOMAIN="api.riviwa.com"
EMAIL="johnsabaskomba@gmail.com"

echo "==> Step 1: Starting Nginx with HTTP-only config for ACME challenge..."

# Use the init config (HTTP only, no SSL)
cp nginx/nginx-init.conf nginx/nginx-temp.conf

# Start just nginx with the init config
docker compose run -d --name nginx-init \
  -p 80:80 \
  -v "$(pwd)/nginx/nginx-temp.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$(docker volume create certbot_www):/var/www/certbot:ro" \
  nginx:1.27-alpine

echo "==> Step 2: Requesting certificate from Let's Encrypt..."

docker run --rm \
  -v certbot_www:/var/www/certbot \
  -v certbot_certs:/etc/letsencrypt \
  certbot/certbot:v3.4.0 certonly \
    --webroot \
    -w /var/www/certbot \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --non-interactive

echo "==> Step 3: Stopping temporary Nginx..."
docker stop nginx-init && docker rm nginx-init
rm -f nginx/nginx-temp.conf

echo ""
echo "==> SSL certificate obtained successfully!"
echo "    You can now start the full stack:"
echo "    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
