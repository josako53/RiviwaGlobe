#!/bin/bash
# =============================================================================
# Riviwa GCP Infrastructure Setup — run ONCE to provision all GCP resources
#
# Prerequisites:
#   gcloud auth login
#   gcloud config set project riviwa
#   bash gcp/setup.sh
# =============================================================================
set -euo pipefail

PROJECT_ID="riviwa"
REGION="me-west1"
ZONE="me-west1-b"
AR_REPO="riviwa-services"
VPC_NAME="riviwa-vpc"
SUBNET_NAME="riviwa-subnet"
SUBNET_RANGE="10.10.0.0/24"
VM_NAME="riviwa-infra-vm"
VM_IP="10.10.0.100"       # Fixed static internal IP — used in all service configs
VM_MACHINE="n1-standard-8"
SQL_INSTANCE="riviwa-postgres"
REDIS_INSTANCE="riviwa-redis"
CONNECTOR="riviwa-connector"

G='\033[0;32m'; Y='\033[1;33m'; N='\033[0m'
info() { echo -e "${G}[✓]${N} $*"; }
warn() { echo -e "${Y}[~]${N} $*"; }
step() { echo -e "\n${G}━━━ $* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"; }

gcloud config set project "$PROJECT_ID"

# ── 1. Enable APIs ──────────────────────────────────────────────────────────
step "1/8  Enabling APIs"
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  compute.googleapis.com \
  secretmanager.googleapis.com \
  vpcaccess.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  servicenetworking.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com
info "APIs enabled"

# ── 2. VPC + Subnet ─────────────────────────────────────────────────────────
step "2/8  VPC network"
gcloud compute networks create $VPC_NAME \
  --subnet-mode=custom --bgp-routing-mode=regional 2>/dev/null || warn "VPC exists"

gcloud compute networks subnets create $SUBNET_NAME \
  --network=$VPC_NAME --region=$REGION --range=$SUBNET_RANGE 2>/dev/null || warn "Subnet exists"

# Private services IP peering (Cloud SQL + Memorystore require this)
gcloud compute addresses create google-managed-services-$VPC_NAME \
  --global --purpose=VPC_PEERING --prefix-length=16 \
  --network=$VPC_NAME 2>/dev/null || warn "IP range allocated"

gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-$VPC_NAME \
  --network=$VPC_NAME 2>/dev/null || warn "VPC peering exists"

# VPC Access Connector — lets Cloud Run reach private IPs
gcloud compute networks vpc-access connectors create $CONNECTOR \
  --region=$REGION --subnet=$SUBNET_NAME \
  --min-instances=2 --max-instances=10 2>/dev/null || warn "VPC connector exists"
info "VPC ready"

# ── 3. Artifact Registry ────────────────────────────────────────────────────
step "3/8  Artifact Registry"
gcloud artifacts repositories create $AR_REPO \
  --repository-format=docker --location=$REGION \
  --description="Riviwa Docker images" 2>/dev/null || warn "Registry exists"
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
info "Registry: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}"

# ── 4. Cloud SQL (PostgreSQL 15) — ~5 min ───────────────────────────────────
step "4/8  Cloud SQL PostgreSQL 15  (this takes ~5 minutes)"
gcloud sql instances create $SQL_INSTANCE \
  --database-version=POSTGRES_15 \
  --tier=db-custom-4-15360 \
  --region=$REGION \
  --network="projects/${PROJECT_ID}/global/networks/${VPC_NAME}" \
  --no-assign-ip \
  --availability-type=REGIONAL \
  --backup-start-time=02:00 \
  --storage-type=SSD \
  --storage-size=100 \
  --storage-auto-increase 2>/dev/null || warn "Cloud SQL exists"

DATABASES=(
  riviwa_auth_db feedback_db payment_db stakeholder_db
  notification_db translation_db recommendation_db ai_db
  analytics_db integration_db product_db qr_db
  verification_db waiting_db staff_db subscription_db
)
for DB in "${DATABASES[@]}"; do
  gcloud sql databases create "$DB" --instance=$SQL_INSTANCE 2>/dev/null || warn "DB $DB exists"
done

# Create per-service DB users (from .env values)
declare -A DB_USERS=(
  [riviwa_auth_db]="riviwa_auth_admin"
  [feedback_db]="feedback_admin"
  [payment_db]="payment_user"
  [stakeholder_db]="stakeholder_admin"
  [notification_db]="notification_admin"
  [translation_db]="trans_admin"
  [recommendation_db]="rec_admin"
  [ai_db]="ai_admin"
  [analytics_db]="analytics_admin"
  [integration_db]="integration_admin"
  [product_db]="product_admin"
  [qr_db]="qr_admin"
  [verification_db]="verification_admin"
  [waiting_db]="waiting_admin"
  [staff_db]="staff_admin"
  [subscription_db]="subscription_admin"
)
for DB in "${!DB_USERS[@]}"; do
  USER="${DB_USERS[$DB]}"
  PASS=$(openssl rand -base64 24 | tr -d '/+=')
  gcloud sql users create "$USER" \
    --instance=$SQL_INSTANCE --password="$PASS" 2>/dev/null || warn "User $USER exists"
  # Store the generated password as a GCP secret so setup-secrets.sh can use it
  echo -n "$PASS" | gcloud secrets create "db-pass-${USER}" --data-file=- \
    --project=$PROJECT_ID 2>/dev/null || \
    echo -n "$PASS" | gcloud secrets versions add "db-pass-${USER}" --data-file=-
done
info "Cloud SQL ready with ${#DATABASES[@]} databases"

# ── 5. Memorystore Redis 7 ──────────────────────────────────────────────────
step "5/8  Memorystore Redis"
gcloud redis instances create $REDIS_INSTANCE \
  --size=5 --region=$REGION \
  --network="projects/${PROJECT_ID}/global/networks/${VPC_NAME}" \
  --redis-version=redis_7_0 --tier=BASIC 2>/dev/null || warn "Redis exists"
info "Redis provisioning (async — check: gcloud redis instances describe $REDIS_INSTANCE --region=$REGION)"

# ── 6. Cloud Storage buckets (MinIO replacement) ────────────────────────────
step "6/8  Cloud Storage buckets"
for BUCKET in riviwa-voice riviwa-images riviwa-qr-codes riviwa-verification riviwa-staff; do
  gcloud storage buckets create "gs://${BUCKET}" \
    --project=$PROJECT_ID --location=$REGION \
    --uniform-bucket-level-access 2>/dev/null || warn "Bucket $BUCKET exists"
done

# HMAC key for MinIO-compatible SDK access (no code changes in services)
SA_STORAGE="riviwa-storage@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud iam service-accounts create riviwa-storage \
  --display-name="Riviwa Storage SA" 2>/dev/null || warn "Storage SA exists"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_STORAGE" \
  --role="roles/storage.objectAdmin" --quiet
HMAC_OUT=$(gcloud storage hmac create "$SA_STORAGE" --project=$PROJECT_ID --format=json 2>/dev/null || echo "{}")
echo "$HMAC_OUT" > /tmp/hmac_keys.json
info "Buckets ready. HMAC keys saved to /tmp/hmac_keys.json — add to secrets"

# ── 7. Cloud Run service account ────────────────────────────────────────────
step "7/8  Service accounts & IAM"
gcloud iam service-accounts create riviwa-cloudrun \
  --display-name="Riviwa Cloud Run" 2>/dev/null || warn "CR SA exists"
CR_SA="riviwa-cloudrun@${PROJECT_ID}.iam.gserviceaccount.com"
for ROLE in \
  roles/secretmanager.secretAccessor \
  roles/cloudsql.client \
  roles/storage.objectAdmin \
  roles/run.invoker; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CR_SA" --role="$ROLE" --quiet
done

# Grant Cloud Build SA permission to deploy Cloud Run
CB_SA="$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')@cloudbuild.gserviceaccount.com"
for ROLE in roles/run.admin roles/iam.serviceAccountUser roles/artifactregistry.writer; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CB_SA" --role="$ROLE" --quiet
done
info "IAM configured"

# ── 8. Compute Engine VM (Kafka + Qdrant + Ollama + Spark) ──────────────────
step "8/8  Infrastructure VM (Kafka / Qdrant / Ollama / Spark)"
gcloud compute instances create $VM_NAME \
  --zone=$ZONE \
  --machine-type=$VM_MACHINE \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --maintenance-policy=TERMINATE \
  --restart-on-failure \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=200 --boot-disk-type=pd-ssd \
  --network=$VPC_NAME --subnet=$SUBNET_NAME \
  --private-network-ip=$VM_IP \
  --no-address \
  --scopes=cloud-platform \
  --metadata-from-file=startup-script=gcp/infra-vm/startup.sh \
  --tags=riviwa-infra \
  --project=$PROJECT_ID 2>/dev/null || warn "VM exists"

# Firewall rules (internal only — no public exposure)
declare -A RULES=(
  ["allow-kafka-internal"]="tcp:9092-9095"
  ["allow-qdrant-internal"]="tcp:6333,tcp:6334"
  ["allow-ollama-internal"]="tcp:11434"
  ["allow-translation-internal"]="tcp:8050"
  ["allow-spark-internal"]="tcp:7077,tcp:8082"
)
for RULE in "${!RULES[@]}"; do
  gcloud compute firewall-rules create $RULE \
    --network=$VPC_NAME --allow="${RULES[$RULE]}" \
    --source-ranges=$SUBNET_RANGE \
    --target-tags=riviwa-infra 2>/dev/null || warn "Rule $RULE exists"
done
# IAP SSH (no public IP needed)
gcloud compute firewall-rules create allow-iap-ssh-infra \
  --network=$VPC_NAME --allow=tcp:22 \
  --source-ranges=35.235.240.0/20 \
  --target-tags=riviwa-infra 2>/dev/null || warn "IAP rule exists"
info "VM created at static IP $VM_IP"

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
info "Infrastructure setup complete."
echo ""
echo "  Cloud SQL:   $(gcloud sql instances describe $SQL_INSTANCE --format='value(ipAddresses[0].ipAddress)' 2>/dev/null)"
echo "  Redis:       run 'gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format=value(host)' once provisioned"
echo "  Infra VM:    $VM_IP (internal, me-west1-b)"
echo ""
echo "  Next steps:"
echo "    1. bash gcp/setup-secrets.sh        # push all secrets to Secret Manager"
echo "    2. bash gcp/deploy.sh               # deploy all Cloud Run services"
echo "    3. bash gcp/setup-lb.sh             # configure Load Balancer + api.riviwa.com"
