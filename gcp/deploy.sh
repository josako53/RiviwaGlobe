#!/bin/bash
# =============================================================================
# Riviwa Cloud Run Deployment
# Builds all Docker images, pushes to Artifact Registry, deploys to Cloud Run.
# Run after setup.sh and setup-secrets.sh.
#
#   bash gcp/deploy.sh [SERVICE_NAME]   # deploy one service
#   bash gcp/deploy.sh                  # deploy all services
# =============================================================================
set -euo pipefail

PROJECT_ID="riviwa"
REGION="me-west1"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/riviwa-services"
CONNECTOR="projects/${PROJECT_ID}/locations/${REGION}/connectors/riviwa-connector"
CR_SA="riviwa-cloudrun@${PROJECT_ID}.iam.gserviceaccount.com"
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")

G='\033[0;32m'; Y='\033[1;33m'; N='\033[0m'
info() { echo -e "${G}[✓]${N} $*"; }

# ── Secret reference helpers ─────────────────────────────────────────────────
# Returns gcloud --set-secrets flag value for a given secret name
S() { echo "reviwa-${1}:latest"; }  # shorthand
# Build --set-secrets string for a list of "ENV_VAR=secret-name" pairs
secrets_flags() {
  local flags=""
  for pair in "$@"; do
    flags+="${pair},"
  done
  echo "${flags%,}"
}

# ── Common secrets shared by all services ────────────────────────────────────
COMMON_SECRETS=$(secrets_flags \
  "KAFKA_BOOTSTRAP_SERVERS=riviwa-KAFKA_BOOTSTRAP_SERVERS" \
  "INTERNAL_SERVICE_KEY=riviwa-INTERNAL_SERVICE_KEY" \
  "SECRET_KEY=riviwa-SECRET_KEY" \
  "ALGORITHM=riviwa-ALGORITHM" \
  "ENVIRONMENT=riviwa-ENVIRONMENT" \
  "MINIO_ENDPOINT=riviwa-MINIO_ENDPOINT" \
  "MINIO_ACCESS_KEY=riviwa-MINIO_ACCESS_KEY" \
  "MINIO_SECRET_KEY=riviwa-MINIO_SECRET_KEY"
)

# ── Service definitions ───────────────────────────────────────────────────────
# Format: "name:dir:port:memory:cpu:extra_secrets"
declare -a SERVICES=(
  "riviwa-auth:riviwa_auth_service:8000:512Mi:1:AUTH_DATABASE_URL=riviwa-AUTH_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL,TWILIO_ACCOUNT_SID=riviwa-TWILIO_ACCOUNT_SID,TWILIO_AUTH_TOKEN=riviwa-TWILIO_AUTH_TOKEN,TWILIO_VERIFY_SERVICE_SID=riviwa-TWILIO_VERIFY_SERVICE_SID,SENDGRID_API_KEY=riviwa-SENDGRID_API_KEY"
  "riviwa-payment:payment:8040:512Mi:1:PAYMENT_DATABASE_URL=riviwa-PAYMENT_DATABASE_URL,AZAMPAY_CLIENT_ID=riviwa-AZAMPAY_CLIENT_ID,AZAMPAY_CLIENT_SECRET=riviwa-AZAMPAY_CLIENT_SECRET,SELCOM_API_KEY=riviwa-SELCOM_API_KEY,SELCOM_API_SECRET=riviwa-SELCOM_API_SECRET,MPESA_API_KEY=riviwa-MPESA_API_KEY,STRIPE_SECRET_KEY=riviwa-STRIPE_SECRET_KEY"
  "riviwa-notification:notification_service:8060:512Mi:1:NOTIFICATION_DATABASE_URL=riviwa-NOTIFICATION_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL,FCM_SERVER_KEY=riviwa-FCM_SERVER_KEY,SENDGRID_API_KEY=riviwa-SENDGRID_API_KEY,TWILIO_ACCOUNT_SID=riviwa-TWILIO_ACCOUNT_SID,TWILIO_AUTH_TOKEN=riviwa-TWILIO_AUTH_TOKEN,AT_API_KEY=riviwa-AT_API_KEY,WHATSAPP_ACCESS_TOKEN=riviwa-WHATSAPP_ACCESS_TOKEN"
  "riviwa-stakeholder:stakeholder_service:8070:512Mi:1:STAKEHOLDER_DATABASE_URL=riviwa-STAKEHOLDER_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL"
  "riviwa-feedback:feedback_service:8090:512Mi:1:FEEDBACK_DATABASE_URL=riviwa-FEEDBACK_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL,OPENAI_API_KEY=riviwa-OPENAI_API_KEY,VOICE_STORAGE_BUCKET=riviwa-VOICE_STORAGE_BUCKET"
  "riviwa-recommendation:recommendation_service:8055:512Mi:1:RECOMMENDATION_DATABASE_URL=riviwa-RECOMMENDATION_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL,QDRANT_HOST=riviwa-QDRANT_HOST,QDRANT_PORT=riviwa-QDRANT_PORT,EMBEDDING_MODEL=riviwa-EMBEDDING_MODEL"
  "riviwa-ai:ai_service:8085:1Gi:2:AI_DATABASE_URL=riviwa-AI_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL,QDRANT_HOST=riviwa-QDRANT_HOST,QDRANT_PORT=riviwa-QDRANT_PORT,OLLAMA_BASE_URL=riviwa-OLLAMA_BASE_URL,GROQ_API_KEY=riviwa-GROQ_API_KEY,WHATSAPP_ACCESS_TOKEN=riviwa-WHATSAPP_ACCESS_TOKEN,WHATSAPP_VERIFY_TOKEN=riviwa-WHATSAPP_VERIFY_TOKEN"
  "riviwa-analytics:analytics_service:8095:512Mi:1:ANALYTICS_DATABASE_URL=riviwa-ANALYTICS_DATABASE_URL,FEEDBACK_DATABASE_URL=riviwa-FEEDBACK_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL,GROQ_API_KEY=riviwa-GROQ_API_KEY"
  "riviwa-integration:integration_service:8100:512Mi:1:INTEGRATION_DATABASE_URL=riviwa-INTEGRATION_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL,INTEGRATION_ENCRYPTION_KEY=riviwa-INTEGRATION_ENCRYPTION_KEY,RIVIWA_WIDGET_BASE_URL=riviwa-RIVIWA_WIDGET_BASE_URL"
  "riviwa-product:product_service:8110:512Mi:1:PRODUCT_DATABASE_URL=riviwa-PRODUCT_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL,QDRANT_HOST=riviwa-QDRANT_HOST"
  "riviwa-qr:qr_service:8120:512Mi:1:QR_DATABASE_URL=riviwa-QR_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL"
  "riviwa-verification:verification_service:8125:512Mi:1:VERIFICATION_DATABASE_URL=riviwa-VERIFICATION_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL,QDRANT_HOST=riviwa-QDRANT_HOST,OLLAMA_BASE_URL=riviwa-OLLAMA_BASE_URL"
  "riviwa-waiting:waiting_service:8130:512Mi:1:WAITING_DATABASE_URL=riviwa-WAITING_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL,AT_API_KEY=riviwa-AT_API_KEY"
  "riviwa-staff:staff_service:8135:512Mi:1:STAFF_DATABASE_URL=riviwa-STAFF_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL"
  "riviwa-subscription:subscription_service:8140:512Mi:1:SUBSCRIPTION_DATABASE_URL=riviwa-SUBSCRIPTION_DATABASE_URL,REDIS_URL=riviwa-REDIS_URL,STRIPE_SECRET_KEY=riviwa-STRIPE_SECRET_KEY,AZAMPAY_CLIENT_ID=riviwa-AZAMPAY_CLIENT_ID,AZAMPAY_CLIENT_SECRET=riviwa-AZAMPAY_CLIENT_SECRET"
)

# ── Build + push + deploy one service ────────────────────────────────────────
deploy_service() {
  local ENTRY="$1"
  IFS=: read -r SVC_NAME SVC_DIR PORT MEMORY CPU EXTRA_SECRETS <<< "$ENTRY"

  local IMAGE="${REGISTRY}/${SVC_NAME}:${COMMIT_SHA}"
  local IMAGE_LATEST="${REGISTRY}/${SVC_NAME}:latest"

  echo ""
  info "Building ${SVC_NAME} → ${SVC_DIR}"
  docker build -t "$IMAGE" -t "$IMAGE_LATEST" "./${SVC_DIR}"
  docker push "$IMAGE"
  docker push "$IMAGE_LATEST"
  info "Pushed ${IMAGE}"

  local ALL_SECRETS="${COMMON_SECRETS},${EXTRA_SECRETS}"

  info "Deploying ${SVC_NAME} to Cloud Run (${REGION})"
  gcloud run deploy "$SVC_NAME" \
    --image="$IMAGE" \
    --region="$REGION" \
    --platform=managed \
    --service-account="$CR_SA" \
    --vpc-connector="$CONNECTOR" \
    --vpc-egress=private-ranges-only \
    --memory="$MEMORY" \
    --cpu="$CPU" \
    --port="$PORT" \
    --concurrency=80 \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=300 \
    --set-secrets="$ALL_SECRETS" \
    --set-env-vars="APP_V1_STR=/api/v1,PAYMENT_CALLBACK_BASE_URL=https://api.riviwa.com" \
    --allow-unauthenticated \
    --project="$PROJECT_ID"

  info "✓ ${SVC_NAME} deployed"
}

# ── Main ──────────────────────────────────────────────────────────────────────
TARGET="${1:-all}"

if [[ "$TARGET" == "all" ]]; then
  echo "Deploying all ${#SERVICES[@]} Cloud Run services..."
  for SVC in "${SERVICES[@]}"; do
    deploy_service "$SVC"
  done
  info "All services deployed."
  echo ""
  echo "Service URLs:"
  gcloud run services list --region=$REGION --platform=managed \
    --format="table(SERVICE:metadata.name, URL:status.url)" --project=$PROJECT_ID
else
  # Deploy a single named service
  for SVC in "${SERVICES[@]}"; do
    SVC_NAME="${SVC%%:*}"
    if [[ "$SVC_NAME" == "$TARGET" || "${SVC_NAME#riviwa-}" == "$TARGET" ]]; then
      deploy_service "$SVC"
      exit 0
    fi
  done
  echo "Service '$TARGET' not found. Available: ${SERVICES[*]%%:*}" >&2
  exit 1
fi
