#!/bin/bash
# =============================================================================
# Riviwa Load Balancer Setup
# Creates a Global HTTPS Load Balancer that routes api.riviwa.com to
# the correct Cloud Run service based on URL path.
# Run AFTER deploy.sh.
#
#   bash gcp/setup-lb.sh
# =============================================================================
set -euo pipefail

PROJECT_ID="riviwa"
REGION="me-west1"
DOMAIN="api.riviwa.com"

G='\033[0;32m'; Y='\033[1;33m'; N='\033[0m'
info() { echo -e "${G}[✓]${N} $*"; }
warn() { echo -e "${Y}[~]${N} $*"; }

# ── Get Cloud Run service URLs ────────────────────────────────────────────────
get_cr_url() {
  gcloud run services describe "$1" \
    --region=$REGION --platform=managed \
    --format='value(status.url)' --project=$PROJECT_ID 2>/dev/null || echo ""
}

declare -A SERVICE_URLS=(
  [riviwa-auth]=$(get_cr_url riviwa-auth)
  [riviwa-payment]=$(get_cr_url riviwa-payment)
  [riviwa-notification]=$(get_cr_url riviwa-notification)
  [riviwa-stakeholder]=$(get_cr_url riviwa-stakeholder)
  [riviwa-feedback]=$(get_cr_url riviwa-feedback)
  [riviwa-recommendation]=$(get_cr_url riviwa-recommendation)
  [riviwa-ai]=$(get_cr_url riviwa-ai)
  [riviwa-analytics]=$(get_cr_url riviwa-analytics)
  [riviwa-integration]=$(get_cr_url riviwa-integration)
  [riviwa-product]=$(get_cr_url riviwa-product)
  [riviwa-qr]=$(get_cr_url riviwa-qr)
  [riviwa-verification]=$(get_cr_url riviwa-verification)
  [riviwa-waiting]=$(get_cr_url riviwa-waiting)
  [riviwa-staff]=$(get_cr_url riviwa-staff)
  [riviwa-subscription]=$(get_cr_url riviwa-subscription)
)

# ── Create serverless NEGs for each Cloud Run service ────────────────────────
echo "Creating serverless NEGs..."
declare -A PATH_RULES=(
  [riviwa-auth]="/api/v1/auth/*,/api/v1/users/*,/api/v1/orgs/*,/api/v1/webhooks/auth/*"
  [riviwa-payment]="/api/v1/payments/*,/api/v1/webhooks/payment/*"
  [riviwa-notification]="/api/v1/notifications/*"
  [riviwa-stakeholder]="/api/v1/projects/*,/api/v1/stakeholders/*,/api/v1/activities/*,/api/v1/communications/*,/api/v1/focal-persons/*"
  [riviwa-feedback]="/api/v1/feedback/*,/api/v1/categories/*,/api/v1/channels/*,/api/v1/committees/*,/api/v1/pap/*,/api/v1/voice/*,/api/v1/reports/*,/api/v1/my/*,/api/v1/escalation-requests/*"
  [riviwa-ai]="/api/v1/ai/*,/api/v1/webhooks/whatsapp/*,/api/v1/webhooks/sms/*"
  [riviwa-analytics]="/api/v1/analytics/*"
  [riviwa-integration]="/api/v1/integrations/*,/api/v1/webhooks/integration/*"
  [riviwa-product]="/api/v1/products/*"
  [riviwa-qr]="/api/v1/qr/*"
  [riviwa-verification]="/api/v1/verify/*,/api/v1/scan/*"
  [riviwa-waiting]="/api/v1/queue/*,/api/v1/waiting/*"
  [riviwa-staff]="/api/v1/staff/*"
  [riviwa-subscription]="/api/v1/subscriptions/*,/api/v1/plans/*"
  [riviwa-recommendation]="/api/v1/recommendations/*"
)

BACKEND_SERVICES=""
URL_MAP_RULES=""

for SVC in "${!SERVICE_URLS[@]}"; do
  NEG_NAME="${SVC}-neg"
  BS_NAME="${SVC}-backend"

  # Serverless NEG pointing to Cloud Run
  gcloud compute network-endpoint-groups create $NEG_NAME \
    --region=$REGION \
    --network-endpoint-type=serverless \
    --cloud-run-service=$SVC \
    --project=$PROJECT_ID 2>/dev/null || warn "NEG $NEG_NAME exists"

  # Backend service
  gcloud compute backend-services create $BS_NAME \
    --global \
    --load-balancing-scheme=EXTERNAL_MANAGED \
    --project=$PROJECT_ID 2>/dev/null || warn "Backend $BS_NAME exists"

  gcloud compute backend-services add-backend $BS_NAME \
    --global \
    --network-endpoint-group=$NEG_NAME \
    --network-endpoint-group-region=$REGION \
    --project=$PROJECT_ID 2>/dev/null || warn "Backend binding exists"
done
info "Serverless NEGs and backends created"

# ── URL map ───────────────────────────────────────────────────────────────────
echo "Creating URL map..."
gcloud compute url-maps create riviwa-url-map \
  --default-service=riviwa-auth-backend \
  --project=$PROJECT_ID 2>/dev/null || warn "URL map exists"

# Add path matchers for each service
MATCHERS_JSON="[]"
for SVC in "${!PATH_RULES[@]}"; do
  BS_NAME="${SVC}-backend"
  IFS=',' read -ra PATHS <<< "${PATH_RULES[$SVC]}"
  PATHS_JSON=$(printf '"%s",' "${PATHS[@]}" | sed 's/,$//')

  gcloud compute url-maps add-path-matcher riviwa-url-map \
    --path-matcher-name="${SVC}-matcher" \
    --default-service=riviwa-auth-backend \
    --backend-service-path-rules="${PATH_RULES[$SVC]}=${BS_NAME}" \
    --new-hosts="$DOMAIN" \
    --project=$PROJECT_ID 2>/dev/null || warn "Path matcher for $SVC exists"
done
info "URL map configured"

# ── SSL certificate ───────────────────────────────────────────────────────────
echo "Creating managed SSL certificate..."
gcloud compute ssl-certificates create riviwa-ssl-cert \
  --domains="$DOMAIN" \
  --global \
  --project=$PROJECT_ID 2>/dev/null || warn "SSL cert exists"

# ── HTTPS proxy + forwarding rule ────────────────────────────────────────────
gcloud compute target-https-proxies create riviwa-https-proxy \
  --url-map=riviwa-url-map \
  --ssl-certificates=riviwa-ssl-cert \
  --global \
  --project=$PROJECT_ID 2>/dev/null || warn "HTTPS proxy exists"

gcloud compute addresses create riviwa-lb-ip \
  --ip-version=IPV4 \
  --global \
  --project=$PROJECT_ID 2>/dev/null || warn "LB IP exists"

LB_IP=$(gcloud compute addresses describe riviwa-lb-ip \
  --global --format='value(address)' --project=$PROJECT_ID)

gcloud compute forwarding-rules create riviwa-https-rule \
  --address=riviwa-lb-ip \
  --target-https-proxy=riviwa-https-proxy \
  --ports=443 \
  --global \
  --load-balancing-scheme=EXTERNAL_MANAGED \
  --project=$PROJECT_ID 2>/dev/null || warn "Forwarding rule exists"

# HTTP → HTTPS redirect
gcloud compute url-maps create riviwa-http-redirect \
  --default-redirect-response-code=301 \
  --redirect-to-https \
  --global \
  --project=$PROJECT_ID 2>/dev/null || warn "HTTP redirect map exists"

gcloud compute target-http-proxies create riviwa-http-proxy \
  --url-map=riviwa-http-redirect \
  --global \
  --project=$PROJECT_ID 2>/dev/null || warn "HTTP proxy exists"

gcloud compute forwarding-rules create riviwa-http-rule \
  --address=riviwa-lb-ip \
  --target-http-proxy=riviwa-http-proxy \
  --ports=80 \
  --global \
  --load-balancing-scheme=EXTERNAL_MANAGED \
  --project=$PROJECT_ID 2>/dev/null || warn "HTTP rule exists"

info "Load Balancer setup complete!"
echo ""
echo "  Load Balancer IP:  $LB_IP"
echo ""
echo "  ACTION REQUIRED: Point DNS A record for $DOMAIN → $LB_IP"
echo "  SSL cert provisioning takes ~15 minutes after DNS propagates."
echo ""
echo "  Verify: curl -H 'Host: $DOMAIN' https://$LB_IP/api/v1/auth/health"
