# Riviwa — Google Cloud Platform Deployment

Migrates the Riviwa microservices platform from Contabo to Google Cloud.

## Architecture

| What | Where | Why |
|---|---|---|
| 15 FastAPI services | Cloud Run (`me-west1`) | Auto-scale, serverless |
| 16 PostgreSQL databases | Cloud SQL (PostgreSQL 15) | Managed, HA |
| Redis | Memorystore (`me-west1`) | Managed, low-latency |
| File storage | Cloud Storage | Replaces MinIO (S3-compatible) |
| Kafka + Qdrant + Ollama + Translation + Spark | Compute Engine VM (`10.10.0.100`) | Stateful / GPU / heavy model |
| Routing | Cloud Load Balancer | Replaces Nginx |
| CI/CD | Cloud Build | Auto-deploy on push to `main` |
| Secrets | Secret Manager | Replaces `.env.production` |

**Note:** Translation service runs on the VM (not Cloud Run) because the NLLB-200 model (~2.6 GB) causes unacceptable cold starts on serverless containers.

## Prerequisites

1. `gcloud` CLI installed: https://cloud.google.com/sdk/docs/install
2. Logged in and project set:
   ```bash
   gcloud auth login
   gcloud config set project riviwa
   gcloud auth configure-docker me-west1-docker.pkg.dev
   ```
3. Docker installed and running (for local builds)
4. `.env.production` file in repo root with production secrets

---

## Deployment Steps

### Step 1 — Provision infrastructure (run once)
```bash
bash gcp/setup.sh
```
Creates: VPC, Cloud SQL, Memorystore, Cloud Storage buckets,
Artifact Registry, service accounts, IAM roles, and the infra VM.

**Time:** ~15 minutes (Cloud SQL takes the longest).

### Step 2 — Push all secrets
```bash
bash gcp/setup-secrets.sh
```
Reads `.env.production`, injects real GCP endpoint IPs, and stores
every secret in Secret Manager. Cloud Run services pull from here.

### Step 3 — First deployment
```bash
bash gcp/deploy.sh
```
Builds all 15 Docker images, pushes to Artifact Registry, and deploys
each service to Cloud Run with the correct secrets and VPC connector.

**Time:** ~20-30 minutes for all 15 services in parallel.

### Step 4 — Connect GitHub CI/CD (run once)
```bash
bash gcp/connect-github.sh
```
Links `josako53/RiviwaGlobe` main branch → Cloud Build.
Future `git push` to `main` triggers a full rebuild + deploy automatically.

### Step 5 — Set up Load Balancer
```bash
bash gcp/setup-lb.sh
```
Creates the HTTPS Load Balancer with URL routing that maps all
`api.riviwa.com` paths to the correct Cloud Run service.

**After this:** Update your DNS A record → Load Balancer IP.
SSL cert auto-provisions within ~15 min of DNS propagation.

---

## Deploy a Single Service

```bash
bash gcp/deploy.sh riviwa-auth
bash gcp/deploy.sh riviwa-feedback
# etc.
```

## SSH into the Infra VM

The VM has no public IP — use IAP:
```bash
gcloud compute ssh riviwa-infra-vm --zone=me-west1-b --tunnel-through-iap
```

## Update Infra VM Docker Compose

```bash
gcloud compute ssh riviwa-infra-vm --zone=me-west1-b --tunnel-through-iap -- \
  "cd /opt/riviwa-infra && docker compose pull && docker compose up -d"
```

---

## Service → Port → Cloud Run URL Mapping

| Service | Port | Cloud Run Name |
|---|---|---|
| auth | 8000 | `riviwa-auth` |
| payment | 8040 | `riviwa-payment` |
| translation | 8050 | VM only (`10.10.0.100:8050`) |
| recommendation | 8055 | `riviwa-recommendation` |
| notification | 8060 | `riviwa-notification` |
| stakeholder | 8070 | `riviwa-stakeholder` |
| ai | 8085 | `riviwa-ai` |
| feedback | 8090 | `riviwa-feedback` |
| analytics | 8095 | `riviwa-analytics` |
| integration | 8100 | `riviwa-integration` |
| product | 8110 | `riviwa-product` |
| qr | 8120 | `riviwa-qr` |
| verification | 8125 | `riviwa-verification` |
| waiting | 8130 | `riviwa-waiting` |
| staff | 8135 | `riviwa-staff` |
| subscription | 8140 | `riviwa-subscription` |

---

## Cost Estimate (me-west1)

| Resource | Approx/month |
|---|---|
| Cloud Run (15 services, low traffic) | $20–80 |
| Cloud SQL (db-custom-4-15360) | ~$350 |
| Memorystore Redis (5 GB) | ~$100 |
| Compute Engine VM (n1-standard-8 + T4 GPU) | ~$450 |
| Cloud Storage + Load Balancer | ~$20 |
| **Total** | **~$950–1000/month** |

---

## Troubleshooting

**Cloud Run can't reach Kafka/Redis/Qdrant:**
Check VPC connector is attached: `gcloud run services describe <service> --region=me-west1 | grep vpcAccess`

**Translation service unreachable:**
SSH to infra VM and check: `docker ps | grep translation` and `docker logs riviwa-translation`

**Ollama model not loaded:**
```bash
gcloud compute ssh riviwa-infra-vm --zone=me-west1-b --tunnel-through-iap -- \
  "docker exec reviwa-ollama ollama list"
```

**Secret not found in Cloud Run:**
Verify it exists: `gcloud secrets list --project=riviwa --filter="name~riviwa-"`
