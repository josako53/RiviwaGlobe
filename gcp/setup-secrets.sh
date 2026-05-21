#!/bin/bash
# =============================================================================
# Riviwa Secret Manager Setup
# Run AFTER setup.sh. Reads .env.production and pushes all secrets to GCP.
# Automatically replaces Docker service names with real GCP endpoints.
#
#   bash gcp/setup-secrets.sh
# =============================================================================
set -euo pipefail

PROJECT_ID="riviwa"
REGION="me-west1"
SQL_INSTANCE="riviwa-postgres"
REDIS_INSTANCE="riviwa-redis"
VM_IP="10.10.0.100"

G='\033[0;32m'; Y='\033[1;33m'; N='\033[0m'
info() { echo -e "${G}[✓]${N} $*"; }
warn() { echo -e "${Y}[~]${N} $*"; }

# ── Resolve live GCP endpoints ───────────────────────────────────────────────
echo "Resolving GCP endpoint IPs..."
SQL_IP=$(gcloud sql instances describe $SQL_INSTANCE \
  --format='value(ipAddresses[0].ipAddress)' --project=$PROJECT_ID)
REDIS_IP=$(gcloud redis instances describe $REDIS_INSTANCE \
  --region=$REGION --format='value(host)' --project=$PROJECT_ID)

info "Cloud SQL:  $SQL_IP"
info "Redis:      $REDIS_IP"
info "Infra VM:   $VM_IP"

# ── Helper: create or update a secret ───────────────────────────────────────
put_secret() {
  local NAME="$1"
  local VALUE="$2"
  echo -n "$VALUE" | gcloud secrets create "riviwa-${NAME}" \
    --data-file=- --project=$PROJECT_ID 2>/dev/null || \
  echo -n "$VALUE" | gcloud secrets versions add "riviwa-${NAME}" \
    --data-file=- --project=$PROJECT_ID
}

# ── Service database URLs (replaced with Cloud SQL IPs) ─────────────────────
# Passwords are fetched from the secrets created during setup.sh
get_db_pass() {
  gcloud secrets versions access latest \
    --secret="db-pass-${1}" --project=$PROJECT_ID 2>/dev/null || echo "CHANGE_ME"
}

put_secret "AUTH_DATABASE_URL"         "postgresql+asyncpg://riviwa_auth_admin:$(get_db_pass riviwa_auth_admin)@${SQL_IP}:5432/riviwa_auth_db"
put_secret "FEEDBACK_DATABASE_URL"     "postgresql+asyncpg://feedback_admin:$(get_db_pass feedback_admin)@${SQL_IP}:5432/feedback_db"
put_secret "PAYMENT_DATABASE_URL"      "postgresql+asyncpg://payment_user:$(get_db_pass payment_user)@${SQL_IP}:5432/payment_db"
put_secret "STAKEHOLDER_DATABASE_URL"  "postgresql+asyncpg://stakeholder_admin:$(get_db_pass stakeholder_admin)@${SQL_IP}:5432/stakeholder_db"
put_secret "NOTIFICATION_DATABASE_URL" "postgresql+asyncpg://notification_admin:$(get_db_pass notification_admin)@${SQL_IP}:5432/notification_db"
put_secret "TRANSLATION_DATABASE_URL"  "postgresql+asyncpg://trans_admin:$(get_db_pass trans_admin)@${SQL_IP}:5432/translation_db"
put_secret "RECOMMENDATION_DATABASE_URL" "postgresql+asyncpg://rec_admin:$(get_db_pass rec_admin)@${SQL_IP}:5432/recommendation_db"
put_secret "AI_DATABASE_URL"           "postgresql+asyncpg://ai_admin:$(get_db_pass ai_admin)@${SQL_IP}:5432/ai_db"
put_secret "ANALYTICS_DATABASE_URL"    "postgresql+asyncpg://analytics_admin:$(get_db_pass analytics_admin)@${SQL_IP}:5432/analytics_db"
put_secret "INTEGRATION_DATABASE_URL"  "postgresql+asyncpg://integration_admin:$(get_db_pass integration_admin)@${SQL_IP}:5432/integration_db"
put_secret "PRODUCT_DATABASE_URL"      "postgresql+asyncpg://product_admin:$(get_db_pass product_admin)@${SQL_IP}:5432/product_db"
put_secret "QR_DATABASE_URL"           "postgresql+asyncpg://qr_admin:$(get_db_pass qr_admin)@${SQL_IP}:5432/qr_db"
put_secret "VERIFICATION_DATABASE_URL" "postgresql+asyncpg://verification_admin:$(get_db_pass verification_admin)@${SQL_IP}:5432/verification_db"
put_secret "WAITING_DATABASE_URL"      "postgresql+asyncpg://waiting_admin:$(get_db_pass waiting_admin)@${SQL_IP}:5432/waiting_db"
put_secret "STAFF_DATABASE_URL"        "postgresql+asyncpg://staff_admin:$(get_db_pass staff_admin)@${SQL_IP}:5432/staff_db"
put_secret "SUBSCRIPTION_DATABASE_URL" "postgresql+asyncpg://subscription_admin:$(get_db_pass subscription_admin)@${SQL_IP}:5432/subscription_db"

# Sync DB URLs for services (for alembic / psycopg)
put_secret "AUTH_DATABASE_URL_SYNC"         "postgresql+psycopg://riviwa_auth_admin:$(get_db_pass riviwa_auth_admin)@${SQL_IP}:5432/riviwa_auth_db"

info "Database URLs written"

# ── Infrastructure endpoints ─────────────────────────────────────────────────
put_secret "KAFKA_BOOTSTRAP_SERVERS"   "${VM_IP}:9092,${VM_IP}:9093,${VM_IP}:9094,${VM_IP}:9095"
put_secret "REDIS_URL"                 "redis://${REDIS_IP}:6379"
put_secret "QDRANT_HOST"               "${VM_IP}"
put_secret "QDRANT_PORT"               "6333"
put_secret "OLLAMA_BASE_URL"           "http://${VM_IP}:11434"
# Translation service runs on VM — Cloud Run services point here
put_secret "TRANSLATION_SERVICE_URL"   "http://${VM_IP}:8050"

# MinIO-compatible config pointing to GCS
HMAC_ACCESS=$(cat /tmp/hmac_keys.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('metadata',{}).get('accessId','CHANGE_ME'))" 2>/dev/null || echo "CHANGE_ME")
HMAC_SECRET=$(cat /tmp/hmac_keys.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('secret','CHANGE_ME'))" 2>/dev/null || echo "CHANGE_ME")
put_secret "MINIO_ENDPOINT"            "https://storage.googleapis.com"
put_secret "MINIO_ACCESS_KEY"          "${HMAC_ACCESS}"
put_secret "MINIO_SECRET_KEY"          "${HMAC_SECRET}"
put_secret "STORAGE_PROVIDER"          "minio"

info "Infrastructure endpoints written"

# ── Read .env.production and push remaining secrets ──────────────────────────
if [[ -f ".env.production" ]]; then
  ENV_FILE=".env.production"
elif [[ -f ".env" ]]; then
  ENV_FILE=".env"
  warn "No .env.production found — using .env (review before production!)"
else
  echo "ERROR: No .env file found. Run from repo root."; exit 1
fi

# Skip vars we've already set above (infrastructure endpoints)
SKIP_PATTERN="^(AUTH|FEEDBACK|PAYMENT|STAKEHOLDER|NOTIFICATION|TRANSLATION|RECOMMENDATION|AI|ANALYTICS|INTEGRATION|PRODUCT|QR|VERIFICATION|WAITING|STAFF|SUBSCRIPTION)_DATABASE_URL|KAFKA_BOOTSTRAP|REDIS_URL|QDRANT|OLLAMA|MINIO|STORAGE_PROVIDER|TRANSLATION_SERVICE_URL"

echo "Pushing remaining secrets from $ENV_FILE..."
while IFS= read -r line || [[ -n "$line" ]]; do
  # Skip comments and blank lines
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${line// }" ]] && continue
  # Must be KEY=VALUE format
  [[ "$line" =~ ^([A-Z_][A-Z0-9_]*)=(.*)$ ]] || continue

  KEY="${BASH_REMATCH[1]}"
  VALUE="${BASH_REMATCH[2]}"

  # Skip already-set infra vars and empty values
  [[ "$KEY" =~ $SKIP_PATTERN ]] && continue
  [[ -z "$VALUE" ]] && continue

  put_secret "$KEY" "$VALUE"
done < "$ENV_FILE"

info "All secrets pushed to Secret Manager"
echo ""
echo "View secrets: gcloud secrets list --project=$PROJECT_ID"
echo ""
echo "Next: bash gcp/deploy.sh"
