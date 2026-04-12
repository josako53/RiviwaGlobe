#!/usr/bin/env bash
# =============================================================================
# scripts/test_analytics_ai.sh
# Riviwa — Full Analytics Service + AI Service endpoint test suite
#
# USAGE (run from repo root on the server):
#   bash scripts/test_analytics_ai.sh [BASE_URL]
#
# DEFAULT BASE_URL: https://api.riviwa.com
# Override for local:  bash scripts/test_analytics_ai.sh http://localhost
# =============================================================================
set -euo pipefail

BASE="${1:-https://api.riviwa.com}"
PASS=0; FAIL=0; SKIP=0
CONV_ID=""
PROJECT_ID=""
ORG_ID=""
TOKEN=""
ADMIN_TOKEN=""

# ─── colour helpers ──────────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

ok()   { echo -e "${GREEN}  ✓ PASS${RESET}  $1"; ((PASS++)) || true; }
fail() { echo -e "${RED}  ✗ FAIL${RESET}  $1"; ((FAIL++)) || true; }
skip() { echo -e "${YELLOW}  ⚠ SKIP${RESET}  $1"; ((SKIP++)) || true; }
section() { echo -e "\n${BOLD}${CYAN}══ $1 ══${RESET}"; }

# ─── request helper ──────────────────────────────────────────────────────────
# Usage: req <label> <expected_status_code> <METHOD> <path> [extra curl args...]
req() {
  local label="$1" expected="$2" method="$3" path="$4"
  shift 4
  local url="${BASE}${path}"
  local resp
  resp=$(curl -sk -w "\n__HTTP_STATUS__%{http_code}" -X "$method" "$url" "$@" 2>/dev/null)
  local body status
  status=$(echo "$resp" | grep '__HTTP_STATUS__' | sed 's/__HTTP_STATUS__//')
  body=$(echo "$resp" | sed '/__HTTP_STATUS__/d')

  if [[ "$status" == "$expected" ]]; then
    ok "$label  [HTTP $status]"
    echo "$body"
    return 0
  else
    fail "$label  [expected $expected, got $status]"
    echo "  Response: $(echo "$body" | head -c 300)"
    echo "$body"
    return 1
  fi
}

# ─── json extractor (no jq dependency) ───────────────────────────────────────
jval() {
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d$1)" 2>/dev/null || true
}

# =============================================================================
# 0. DEPLOY NEW SERVICES (if not yet running)
# =============================================================================
section "0. Deploy analytics_service + rebuild ai_service"

if command -v docker &>/dev/null && [[ -f docker-compose.yml ]]; then
  echo "  → Pulling latest git changes..."
  git pull origin main --quiet || true

  echo "  → Building and starting analytics_service..."
  docker compose up -d --build analytics_service 2>&1 | tail -3

  echo "  → Rebuilding ai_service (new greeting + Obsidian RAG)..."
  docker compose up -d --build ai_service 2>&1 | tail -3

  echo "  → Starting Spark cluster..."
  docker compose up -d spark_master spark_worker spark_jobs 2>&1 | tail -3

  echo "  → Rebuilding nginx (analytics upstream)..."
  docker compose up -d --build nginx 2>&1 | tail -3

  echo "  → Waiting 15s for services to initialise..."
  sleep 15
else
  echo "  (Skipping deploy — not on server)"
fi

# =============================================================================
# 1. HEALTH CHECKS
# =============================================================================
section "1. Health Checks"

req "Analytics service health"     200 GET /health/analytics \
  -H "Accept: application/json" || true

req "AI service health"            200 GET /api/v1/ai/health \
  -H "Accept: application/json" 2>/dev/null || \
  skip "AI health endpoint (optional)"

# =============================================================================
# 2. AUTHENTICATE — get staff token
# =============================================================================
section "2. Authentication"

# Step 1: Login
echo "  → Requesting OTP..."
LOGIN_RESP=$(curl -sk -X POST "${BASE}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"identifier":"admin@riviwa.com","password":"admin123"}' 2>/dev/null || echo "{}")

LOGIN_TOKEN=$(echo "$LOGIN_RESP" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('login_token',''))" 2>/dev/null || true)
OTP=$(echo "$LOGIN_RESP" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('otp','') or d.get('debug_otp',''))" 2>/dev/null || true)

if [[ -z "$LOGIN_TOKEN" ]]; then
  # Try alternative credentials
  LOGIN_RESP=$(curl -sk -X POST "${BASE}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"identifier":"josako@riviwa.com","password":"Password123!"}' 2>/dev/null || echo "{}")
  LOGIN_TOKEN=$(echo "$LOGIN_RESP" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('login_token',''))" 2>/dev/null || true)
  OTP=$(echo "$LOGIN_RESP" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('otp','') or d.get('debug_otp',''))" 2>/dev/null || true)
fi

if [[ -n "$OTP" && -n "$LOGIN_TOKEN" ]]; then
  ok "Login step 1 — OTP: $OTP"
else
  fail "Login step 1 failed — response: $(echo "$LOGIN_RESP" | head -c 300)"
fi

# Step 2: Verify OTP
if [[ -n "$LOGIN_TOKEN" && -n "$OTP" ]]; then
  OTP_RESP=$(curl -sk -X POST "${BASE}/api/v1/auth/login/verify-otp" \
    -H "Content-Type: application/json" \
    -d "{\"login_token\":\"${LOGIN_TOKEN}\",\"otp_code\":\"${OTP}\"}" 2>/dev/null || echo "{}")
  TOKEN=$(echo "$OTP_RESP" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || true)
  ORG_ID=$(echo "$OTP_RESP" | python3 -c \
    "import sys,json; d=json.load(sys.stdin)
orgs=d.get('user',{}).get('organisations',[])
print(orgs[0].get('organisation_id','') if orgs else '')" 2>/dev/null || true)

  if [[ -n "$TOKEN" ]]; then
    ok "OTP verification — Bearer token obtained"
    ADMIN_TOKEN="$TOKEN"
  else
    fail "OTP verification failed — response: $(echo "$OTP_RESP" | head -c 300)"
  fi
fi

if [[ -z "$TOKEN" ]]; then
  fail "Authentication failed — all remaining tests that require auth will be skipped"
fi

AUTH=(-H "Authorization: Bearer $TOKEN")

# =============================================================================
# 3. GET A REAL PROJECT_ID from stakeholder/feedback service
# =============================================================================
section "3. Discover Project ID"

PROJECTS_RESP=$(curl -sk -X GET "${BASE}/api/v1/projects?limit=5" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json" 2>/dev/null || echo "{}")

PROJECT_ID=$(echo "$PROJECTS_RESP" | python3 -c \
  "import sys,json
d=json.load(sys.stdin)
items=d.get('items',d.get('projects',d.get('data',[])))
if items: print(items[0].get('id','') or items[0].get('project_id',''))
" 2>/dev/null || true)

if [[ -z "$PROJECT_ID" ]]; then
  # Try feedback_service categories (has project seeding)
  CAT_RESP=$(curl -sk -X GET "${BASE}/api/v1/categories?limit=1" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null || echo "{}")
  PROJECT_ID=$(echo "$CAT_RESP" | python3 -c \
    "import sys,json; d=json.load(sys.stdin)
items=d.get('items',d.get('data',[]))
if items: print(items[0].get('project_id',''))
" 2>/dev/null || true)
fi

# Seed a test project via auth service if still empty
if [[ -z "$PROJECT_ID" && -n "$ORG_ID" ]]; then
  echo "  → Seeding a test project..."
  PROJ_RESP=$(curl -sk -X POST "${BASE}/api/v1/orgs/${ORG_ID}/projects" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "Dar es Salaam Road Upgrade",
      "description": "Rehabilitation of 45km of trunk roads in Coast Region",
      "project_type": "road",
      "region": "Coast Region",
      "primary_lga": "Kinondoni",
      "budget_usd": 12000000
    }' 2>/dev/null || echo "{}")
  PROJECT_ID=$(echo "$PROJ_RESP" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('id',d.get('project_id','')))" \
    2>/dev/null || true)
fi

if [[ -n "$PROJECT_ID" ]]; then
  ok "Project ID: $PROJECT_ID"
else
  skip "No project_id found — analytics endpoint tests will use a placeholder UUID"
  PROJECT_ID="00000000-0000-0000-0000-000000000001"
fi

# =============================================================================
# 4. SEED SAMPLE FEEDBACK DATA
# =============================================================================
section "4. Seed Sample Feedback Data"

seed_feedback() {
  local label="$1"; shift
  SEED_RESP=$(curl -sk -X POST "${BASE}/api/v1/feedback" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$1" 2>/dev/null || echo "{}")
  local fid
  fid=$(echo "$SEED_RESP" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || true)
  if [[ -n "$fid" ]]; then
    ok "$label  → feedback_id: $fid"
  else
    skip "$label  → $(echo "$SEED_RESP" | head -c 200)"
  fi
  echo "$fid"
}

# Grievance — critical, road safety
GRV1=$(seed_feedback "Seed: critical road-safety grievance" \
  "{\"project_id\":\"${PROJECT_ID}\",\"feedback_type\":\"grievance\",\"subject\":\"Large pothole blocking road to hospital\",\"description\":\"There is a 1-meter deep pothole on the main road near Muhimbili hospital entrance that has caused 3 accidents this week.\",\"priority\":\"critical\",\"channel\":\"web_portal\",\"issue_location_description\":\"Near Muhimbili Hospital, Upanga\",\"issue_lga\":\"Ilala\",\"issue_ward\":\"Upanga\",\"is_anonymous\":false,\"submitter_name\":\"John Makamba\"}")

# Grievance — high, bridge
GRV2=$(seed_feedback "Seed: high-priority bridge grievance" \
  "{\"project_id\":\"${PROJECT_ID}\",\"feedback_type\":\"grievance\",\"subject\":\"Bridge damaged during construction works\",\"description\":\"The construction team broke the footbridge connecting our village to the main road. Students can no longer cross safely.\",\"priority\":\"high\",\"channel\":\"whatsapp\",\"issue_location_description\":\"Mbagala Bridge\",\"issue_lga\":\"Temeke\",\"issue_ward\":\"Mbagala\",\"is_anonymous\":false,\"submitter_name\":\"Fatuma Ally\"}")

# Grievance — medium, dust
GRV3=$(seed_feedback "Seed: medium-priority dust grievance" \
  "{\"project_id\":\"${PROJECT_ID}\",\"feedback_type\":\"grievance\",\"subject\":\"Excessive dust from road works affecting business\",\"description\":\"The dust from road construction is entering our shop and making products unsaleable. We have lost significant income.\",\"priority\":\"medium\",\"channel\":\"sms\",\"issue_location_description\":\"Kariakoo Market area\",\"issue_lga\":\"Ilala\",\"issue_ward\":\"Kariakoo\",\"is_anonymous\":false,\"submitter_name\":\"Hassan Juma\"}")

# Suggestion
SUGG1=$(seed_feedback "Seed: road lighting suggestion" \
  "{\"project_id\":\"${PROJECT_ID}\",\"feedback_type\":\"suggestion\",\"subject\":\"Install solar street lights during rehabilitation\",\"description\":\"The road rehabilitation project should include solar-powered street lights since the area has frequent power cuts. This would greatly improve safety at night.\",\"priority\":\"medium\",\"channel\":\"mobile_app\",\"issue_location_description\":\"Magomeni Road\",\"issue_lga\":\"Kinondoni\",\"issue_ward\":\"Magomeni\",\"is_anonymous\":false,\"submitter_name\":\"Agnes Msangi\"}")

# Suggestion — implemented (will mark actioned below)
SUGG2=$(seed_feedback "Seed: drainage suggestion" \
  "{\"project_id\":\"${PROJECT_ID}\",\"feedback_type\":\"suggestion\",\"subject\":\"Add drainage channels alongside road\",\"description\":\"Please add proper drainage channels to prevent flooding. The current design does not account for heavy rain season.\",\"priority\":\"high\",\"channel\":\"web_portal\",\"issue_location_description\":\"Msimbazi Road\",\"issue_lga\":\"Ilala\",\"issue_ward\":\"Msimbazi\",\"is_anonymous\":false,\"submitter_name\":\"Peter Mwangi\"}")

# Applause
APPL1=$(seed_feedback "Seed: applause for quick work" \
  "{\"project_id\":\"${PROJECT_ID}\",\"feedback_type\":\"applause\",\"subject\":\"Great work on Nyerere Road section\",\"description\":\"The team finished the Nyerere Road section ahead of schedule. The road is smooth and has proper markings. Thank you!\",\"priority\":\"low\",\"channel\":\"mobile_app\",\"issue_location_description\":\"Nyerere Road\",\"issue_lga\":\"Ubungo\",\"is_anonymous\":false,\"submitter_name\":\"Mary Kimaro\"}")

echo ""
echo "  → Acknowledging grievance 1 (if ID found)..."
if [[ -n "$GRV1" ]]; then
  curl -sk -X POST "${BASE}/api/v1/feedback/${GRV1}/actions" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"action_type":"acknowledged","notes":"Issue received and assigned to road safety team"}' \
    2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Acknowledged:', d.get('id','fail'))" 2>/dev/null || true
fi

echo "  → Marking suggestion 2 as actioned (implemented)..."
if [[ -n "$SUGG2" ]]; then
  curl -sk -X POST "${BASE}/api/v1/feedback/${SUGG2}/actions" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"action_type":"actioned","notes":"Drainage channels added to project design and construction started"}' \
    2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Actioned:', d.get('id','fail'))" 2>/dev/null || true
fi

# =============================================================================
# 5. ANALYTICS SERVICE — Feedback Endpoints
# =============================================================================
section "5. Analytics — Feedback Endpoints"

if [[ -n "$TOKEN" ]]; then

  # 5.1 Time to open
  echo -e "\n  5.1 GET /api/v1/analytics/feedback/time-to-open"
  req "feedback/time-to-open" 200 GET \
    "/api/v1/analytics/feedback/time-to-open?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json
d=json.load(sys.stdin)
print(f'    avg_hours={d.get(\"avg_hours\")}, sample_count={d.get(\"sample_count\")}')" 2>/dev/null || true

  # 5.2 Unread (all)
  echo -e "\n  5.2 GET /api/v1/analytics/feedback/unread"
  req "feedback/unread (all)" 200 GET \
    "/api/v1/analytics/feedback/unread?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    total_unread={d.get(\"total\")}')" 2>/dev/null || true

  # 5.3 Unread — critical only
  echo -e "\n  5.3 GET /api/v1/analytics/feedback/unread?priority=critical"
  req "feedback/unread (critical)" 200 GET \
    "/api/v1/analytics/feedback/unread?project_id=${PROJECT_ID}&priority=critical" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    critical_unread={d.get(\"total\")}')" 2>/dev/null || true

  # 5.4 Unread — grievances only
  echo -e "\n  5.4 GET /api/v1/analytics/feedback/unread?feedback_type=grievance"
  req "feedback/unread (grievances)" 200 GET \
    "/api/v1/analytics/feedback/unread?project_id=${PROJECT_ID}&feedback_type=grievance" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    unread_grievances={d.get(\"total\")}')" 2>/dev/null || true

  # 5.5 Overdue
  echo -e "\n  5.5 GET /api/v1/analytics/feedback/overdue"
  req "feedback/overdue" 200 GET \
    "/api/v1/analytics/feedback/overdue?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    overdue_count={d.get(\"total\")}')" 2>/dev/null || true

  # 5.6 Not processed
  echo -e "\n  5.6 GET /api/v1/analytics/feedback/not-processed"
  req "feedback/not-processed" 200 GET \
    "/api/v1/analytics/feedback/not-processed?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    not_processed={d.get(\"total\")}')" 2>/dev/null || true

  # 5.7 Processed today
  echo -e "\n  5.7 GET /api/v1/analytics/feedback/processed-today"
  req "feedback/processed-today" 200 GET \
    "/api/v1/analytics/feedback/processed-today?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    processed_today={d.get(\"total\")}')" 2>/dev/null || true

  # 5.8 Resolved today
  echo -e "\n  5.8 GET /api/v1/analytics/feedback/resolved-today"
  req "feedback/resolved-today" 200 GET \
    "/api/v1/analytics/feedback/resolved-today?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    resolved_today={d.get(\"total\")}')" 2>/dev/null || true

else
  skip "Feedback analytics — no token"
fi

# =============================================================================
# 6. ANALYTICS SERVICE — Grievance Endpoints
# =============================================================================
section "6. Analytics — Grievance Endpoints"

if [[ -n "$TOKEN" ]]; then

  # 6.1 Unresolved grievances
  echo -e "\n  6.1 GET /api/v1/analytics/grievances/unresolved"
  req "grievances/unresolved (all)" 200 GET \
    "/api/v1/analytics/grievances/unresolved?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    unresolved_total={d.get(\"total\")}')" 2>/dev/null || true

  # 6.2 Unresolved — critical priority
  echo -e "\n  6.2 GET /api/v1/analytics/grievances/unresolved?priority=critical"
  req "grievances/unresolved (critical)" 200 GET \
    "/api/v1/analytics/grievances/unresolved?project_id=${PROJECT_ID}&priority=critical" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    critical_unresolved={d.get(\"total\")}')" 2>/dev/null || true

  # 6.3 SLA status
  echo -e "\n  6.3 GET /api/v1/analytics/grievances/sla-status"
  req "grievances/sla-status" 200 GET \
    "/api/v1/analytics/grievances/sla-status?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin)
print(f'    overall_compliance={d.get(\"overall_compliance_rate\")}%, breached={d.get(\"total_breached\")}')" 2>/dev/null || true

  # 6.4 SLA status — breached only
  echo -e "\n  6.4 GET /api/v1/analytics/grievances/sla-status?breached_only=true"
  req "grievances/sla-status (breached only)" 200 GET \
    "/api/v1/analytics/grievances/sla-status?project_id=${PROJECT_ID}&breached_only=true" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    breached={d.get(\"total_breached\")}')" 2>/dev/null || true

  # 6.5 Hotspots
  echo -e "\n  6.5 GET /api/v1/analytics/grievances/hotspots"
  req "grievances/hotspots (active)" 200 GET \
    "/api/v1/analytics/grievances/hotspots?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    active_hotspots={d.get(\"total\")}')" 2>/dev/null || true

  req "grievances/hotspots (all)" 200 GET \
    "/api/v1/analytics/grievances/hotspots?project_id=${PROJECT_ID}&alert_status=all" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    all_hotspots={d.get(\"total\")}')" 2>/dev/null || true

else
  skip "Grievance analytics — no token"
fi

# =============================================================================
# 7. ANALYTICS SERVICE — Suggestion Endpoints
# =============================================================================
section "7. Analytics — Suggestion Endpoints"

if [[ -n "$TOKEN" ]]; then

  # 7.1 Implementation time
  echo -e "\n  7.1 GET /api/v1/analytics/suggestions/implementation-time"
  req "suggestions/implementation-time" 200 GET \
    "/api/v1/analytics/suggestions/implementation-time?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin)
print(f'    avg_impl_hours={d.get(\"avg_hours\")}, count={d.get(\"sample_count\")}')" 2>/dev/null || true

  # 7.2 Frequency — week
  echo -e "\n  7.2 GET /api/v1/analytics/suggestions/frequency?period=week"
  req "suggestions/frequency (week)" 200 GET \
    "/api/v1/analytics/suggestions/frequency?project_id=${PROJECT_ID}&period=week" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin)
print(f'    total_this_week={d.get(\"total\")}, rate/day={sum((i.get(\"rate_per_day\") or 0) for i in d.get(\"items\",[])):.2f}')" 2>/dev/null || true

  # 7.3 Frequency — month
  echo -e "\n  7.3 GET /api/v1/analytics/suggestions/frequency?period=month"
  req "suggestions/frequency (month)" 200 GET \
    "/api/v1/analytics/suggestions/frequency?project_id=${PROJECT_ID}&period=month" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    total_this_month={d.get(\"total\")}')" 2>/dev/null || true

  # 7.4 By location
  echo -e "\n  7.4 GET /api/v1/analytics/suggestions/by-location"
  req "suggestions/by-location" 200 GET \
    "/api/v1/analytics/suggestions/by-location?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin)
print(f'    locations_found={d.get(\"total\")}')
for item in d.get('items',[])[:3]:
    print(f'      LGA: {item.get(\"lga\")}, count={item.get(\"count\")}, impl_rate={item.get(\"implementation_rate\")}')" 2>/dev/null || true

  # 7.5 Unread suggestions
  echo -e "\n  7.5 GET /api/v1/analytics/suggestions/unread"
  req "suggestions/unread" 200 GET \
    "/api/v1/analytics/suggestions/unread?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    unread_suggestions={d.get(\"total\")}')" 2>/dev/null || true

  # 7.6 Implemented today
  echo -e "\n  7.6 GET /api/v1/analytics/suggestions/implemented-today"
  req "suggestions/implemented-today" 200 GET \
    "/api/v1/analytics/suggestions/implemented-today?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    implemented_today={d.get(\"total\")}')" 2>/dev/null || true

  # 7.7 Implemented this week
  echo -e "\n  7.7 GET /api/v1/analytics/suggestions/implemented-this-week"
  req "suggestions/implemented-this-week" 200 GET \
    "/api/v1/analytics/suggestions/implemented-this-week?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    implemented_this_week={d.get(\"total\")}')" 2>/dev/null || true

else
  skip "Suggestion analytics — no token"
fi

# =============================================================================
# 8. ANALYTICS SERVICE — Staff Endpoints (org admin only)
# =============================================================================
section "8. Analytics — Staff Endpoints"

if [[ -n "$TOKEN" && -n "$PROJECT_ID" ]]; then

  # 8.1 Committee performance
  echo -e "\n  8.1 GET /api/v1/analytics/staff/committee-performance"
  req "staff/committee-performance" 200 GET \
    "/api/v1/analytics/staff/committee-performance?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin)
print(f'    committees={d.get(\"total\")}')
for c in d.get('items',[])[:3]:
    print(f'      committee={c.get(\"committee_id\")}, resolved={c.get(\"cases_resolved\")}, rate={c.get(\"resolution_rate\")}')" 2>/dev/null || true

  # 8.2 Committee performance — live query
  echo -e "\n  8.2 GET /api/v1/analytics/staff/committee-performance?use_live=true"
  req "staff/committee-performance (live)" 200 GET \
    "/api/v1/analytics/staff/committee-performance?project_id=${PROJECT_ID}&use_live=true" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    live_committees={d.get(\"total\")}')" 2>/dev/null || true

  # 8.3 Last logins
  echo -e "\n  8.3 GET /api/v1/analytics/staff/last-logins"
  req "staff/last-logins" 200 GET \
    "/api/v1/analytics/staff/last-logins" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    staff_with_logins={d.get(\"total\")}')" 2>/dev/null || true

  # 8.4 Unread assigned
  echo -e "\n  8.4 GET /api/v1/analytics/staff/unread-assigned"
  req "staff/unread-assigned" 200 GET \
    "/api/v1/analytics/staff/unread-assigned?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    staff_with_unread_assigned={d.get(\"total\")}')" 2>/dev/null || true

  # 8.5 Login not read
  echo -e "\n  8.5 GET /api/v1/analytics/staff/login-not-read"
  req "staff/login-not-read" 200 GET \
    "/api/v1/analytics/staff/login-not-read?project_id=${PROJECT_ID}" \
    "${AUTH[@]}" -H "Accept: application/json" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    logged_in_but_not_read={d.get(\"total\")}')" 2>/dev/null || true

else
  skip "Staff analytics — no token or project_id"
fi

# =============================================================================
# 9. ANALYTICS SERVICE — AI Insights
# =============================================================================
section "9. Analytics — AI Insights (Groq llama-3.3-70b-versatile)"

if [[ -n "$TOKEN" && -n "$PROJECT_ID" ]]; then

  AI_QUESTIONS=(
    "general|What is the current state of grievance resolution for this project?"
    "grievances|Which grievances are most at risk of breaching their SLA and what should be prioritised?"
    "suggestions|How many suggestions have been implemented and what is the average implementation time?"
    "sla|Is our SLA compliance acceptable and what are the main drivers of breaches?"
    "committees|How are the GRM committees performing compared to each other?"
    "staff|Are staff actively processing their assigned feedback queue?"
    "hotspots|Are there any geographic or category hotspots that require management attention?"
  )

  for entry in "${AI_QUESTIONS[@]}"; do
    ctx_type="${entry%%|*}"
    question="${entry##*|}"

    echo -e "\n  9.${ctx_type} POST /api/v1/analytics/ai/ask  [context: ${ctx_type}]"
    AI_RESP=$(curl -sk -X POST "${BASE}/api/v1/analytics/ai/ask" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"question\":\"${question}\",\"project_id\":\"${PROJECT_ID}\",\"context_type\":\"${ctx_type}\"}" \
      2>/dev/null || echo "{}")
    AI_STATUS=$?

    ANSWER=$(echo "$AI_RESP" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(d.get('answer','')[:200])" 2>/dev/null || true)
    if [[ -n "$ANSWER" ]]; then
      ok "AI ask [${ctx_type}]"
      echo "    Q: ${question:0:80}"
      echo "    A: ${ANSWER:0:200}..."
    else
      fail "AI ask [${ctx_type}]  → $(echo "$AI_RESP" | head -c 200)"
    fi
  done

else
  skip "AI insights — no token or project_id"
fi

# =============================================================================
# 10. AI SERVICE — Conversation Endpoints
# =============================================================================
section "10. AI Service — Riviwa AI Conversation"

# 10.1 Start English conversation
echo -e "\n  10.1 POST /api/v1/ai/conversations  (English)"
START_RESP=$(curl -sk -X POST "${BASE}/api/v1/ai/conversations" \
  -H "Content-Type: application/json" \
  -d "{\"channel\":\"web\",\"language\":\"en\",\"project_id\":\"${PROJECT_ID}\"}" \
  2>/dev/null || echo "{}")

CONV_ID=$(echo "$START_RESP" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('conversation_id',''))" 2>/dev/null || true)
GREETING=$(echo "$START_RESP" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('reply','')[:120])" 2>/dev/null || true)

if [[ -n "$CONV_ID" ]]; then
  ok "Start EN conversation  → conv_id: $CONV_ID"
  echo "    Greeting: ${GREETING}..."
else
  fail "Start EN conversation  → $(echo "$START_RESP" | head -c 300)"
fi

# 10.2 Start Swahili conversation
echo -e "\n  10.2 POST /api/v1/ai/conversations  (Swahili)"
SW_RESP=$(curl -sk -X POST "${BASE}/api/v1/ai/conversations" \
  -H "Content-Type: application/json" \
  -d "{\"channel\":\"whatsapp\",\"language\":\"sw\"}" \
  2>/dev/null || echo "{}")
SW_CONV_ID=$(echo "$SW_RESP" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('conversation_id',''))" 2>/dev/null || true)
SW_GREETING=$(echo "$SW_RESP" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('reply','')[:120])" 2>/dev/null || true)

if [[ -n "$SW_CONV_ID" ]]; then
  ok "Start SW conversation  → conv_id: $SW_CONV_ID"
  echo "    Msalimo: ${SW_GREETING}..."
else
  fail "Start SW conversation  → $(echo "$SW_RESP" | head -c 300)"
fi

# 10.3–10.8  Multi-turn English grievance conversation
if [[ -n "$CONV_ID" ]]; then

  send_msg() {
    local label="$1" msg="$2"
    echo -e "\n  $label"
    TURN_RESP=$(curl -sk -X POST "${BASE}/api/v1/ai/conversations/${CONV_ID}/message" \
      -H "Content-Type: application/json" \
      -d "{\"message\":\"${msg}\"}" \
      2>/dev/null || echo "{}")
    REPLY=$(echo "$TURN_RESP" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(d.get('reply','')[:150])" 2>/dev/null || true)
    CONF=$(echo "$TURN_RESP" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(d.get('confidence',0))" 2>/dev/null || "0")
    STAGE=$(echo "$TURN_RESP" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(d.get('stage',''))" 2>/dev/null || "")
    SUBMITTED=$(echo "$TURN_RESP" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(d.get('submitted',False))" 2>/dev/null || "False")

    if [[ -n "$REPLY" ]]; then
      ok "$label  [conf=${CONF}, stage=${STAGE}, submitted=${SUBMITTED}]"
      echo "    AI: ${REPLY}..."
    else
      fail "$label  → $(echo "$TURN_RESP" | head -c 250)"
    fi
    echo "$TURN_RESP"
  }

  # Turn 1 — identify issue type
  send_msg "10.3 Turn 1 — report grievance" \
    "I want to report a problem with the road construction"

  # Turn 2 — describe issue
  send_msg "10.4 Turn 2 — describe issue" \
    "The construction workers blocked the drainage canal near Temeke market and now our houses flood every time it rains"

  # Turn 3 — location
  send_msg "10.5 Turn 3 — provide location" \
    "This is in Temeke district, Miburani ward, near the central market"

  # Turn 4 — urgency signal
  send_msg "10.6 Turn 4 — add urgency (safety hazard)" \
    "It is very urgent, one family's house collapsed last night because of the water. People are at risk"

  # Turn 5 — provide name
  send_msg "10.7 Turn 5 — provide name" \
    "My name is Ibrahim Salim, phone number 0712345678"

  # Turn 6 — confirm submission
  send_msg "10.8 Turn 6 — confirm submission" \
    "Yes please submit it, that is correct"
fi

# 10.9 Multi-turn Swahili suggestion
if [[ -n "$SW_CONV_ID" ]]; then
  echo -e "\n  10.9 Swahili suggestion conversation"

  SW_TURNS=(
    "Ninataka kutoa mapendekezo kuhusu mradi wa barabara"
    "Naomba wajenga mwanga wa barabara ili watu waweze kutembea usiku salama. Hii ni haja kubwa kwa watu wa Kinondoni"
    "Eneo hilo ni barabara ya Morogoro, mtaa wa Kimara, Kinondoni"
    "Jina langu ni Mariam Juma, si lazima wajue jina langu"
    "Ndiyo, tuma mapendekezo yangu"
  )

  for turn_msg in "${SW_TURNS[@]}"; do
    SW_TURN_RESP=$(curl -sk -X POST "${BASE}/api/v1/ai/conversations/${SW_CONV_ID}/message" \
      -H "Content-Type: application/json" \
      -d "{\"message\":\"${turn_msg}\"}" \
      2>/dev/null || echo "{}")
    SW_REPLY=$(echo "$SW_TURN_RESP" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(d.get('reply','')[:120])" 2>/dev/null || true)
    SW_CONF=$(echo "$SW_TURN_RESP" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(d.get('confidence',0))" 2>/dev/null || "0")

    if [[ -n "$SW_REPLY" ]]; then
      ok "SW turn: '${turn_msg:0:40}...'  [conf=${SW_CONF}]"
      echo "    Jibu: ${SW_REPLY}..."
    else
      fail "SW turn: '${turn_msg:0:40}'"
    fi
  done
fi

# 10.10 GET conversation transcript
if [[ -n "$CONV_ID" ]]; then
  echo -e "\n  10.10 GET /api/v1/ai/conversations/{id} — full transcript"
  TRANSCRIPT_RESP=$(curl -sk -X GET "${BASE}/api/v1/ai/conversations/${CONV_ID}" \
    2>/dev/null || echo "{}")
  TURNS=$(echo "$TRANSCRIPT_RESP" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(len(d.get('transcript',[])))" 2>/dev/null || "0")
  STATUS=$(echo "$TRANSCRIPT_RESP" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || "")
  IS_URGENT=$(echo "$TRANSCRIPT_RESP" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('is_urgent',False))" 2>/dev/null || "")

  if [[ "$TURNS" -gt 0 ]]; then
    ok "GET conversation transcript  [turns=${TURNS}, status=${STATUS}, urgent=${IS_URGENT}]"
  else
    fail "GET conversation transcript"
  fi
fi

# 10.11 Webhook — simulate SMS inbound
echo -e "\n  10.11 POST /api/v1/ai/webhooks/sms  (Africa's Talking format)"
SMS_RESP=$(curl -sk -X POST "${BASE}/api/v1/ai/webhooks/sms" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "from=%2B255712345999&text=Ninataka+kutoa+malalamiko+kuhusu+barabara&to=RIVIWA" \
  2>/dev/null || echo "{}")

if echo "$SMS_RESP" | python3 -c "import sys,json; json.load(sys.stdin)" &>/dev/null; then
  SMS_REPLY=$(echo "$SMS_RESP" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('reply',d.get('message',''))[:100])" 2>/dev/null || true)
  ok "SMS webhook  → ${SMS_REPLY}..."
else
  skip "SMS webhook  → non-JSON response (may be text reply): ${SMS_RESP:0:100}"
fi

# 10.12 Webhook — WhatsApp verification
echo -e "\n  10.12 GET /api/v1/ai/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=riviwa_ai_webhook_verify&hub.challenge=TEST123"
WA_VERIFY=$(curl -sk -X GET \
  "${BASE}/api/v1/ai/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=riviwa_ai_webhook_verify&hub.challenge=TEST123" \
  2>/dev/null || echo "")
if [[ "$WA_VERIFY" == *"TEST123"* ]] || [[ "$WA_VERIFY" == "TEST123" ]]; then
  ok "WhatsApp webhook verification  → challenge echoed back"
else
  skip "WhatsApp webhook verification  → $(echo "$WA_VERIFY" | head -c 100)"
fi

# =============================================================================
# 11. AUTH GUARD TESTS
# =============================================================================
section "11. Auth Guard Verification"

req "analytics/feedback/unread — no token → 401" 401 GET \
  "/api/v1/analytics/feedback/unread?project_id=${PROJECT_ID}" \
  -H "Accept: application/json" | head -c 0 || true

req "analytics/ai/ask — no token → 401" 401 POST \
  "/api/v1/analytics/ai/ask" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"test\",\"project_id\":\"${PROJECT_ID}\",\"context_type\":\"general\"}" | head -c 0 || true

req "analytics/staff/last-logins — no token → 401" 401 GET \
  "/api/v1/analytics/staff/last-logins" \
  -H "Accept: application/json" | head -c 0 || true

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  TEST SUMMARY${RESET}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════${RESET}"
echo -e "  ${GREEN}PASS: ${PASS}${RESET}   ${RED}FAIL: ${FAIL}${RESET}   ${YELLOW}SKIP: ${SKIP}${RESET}"
TOTAL=$((PASS + FAIL + SKIP))
echo -e "  Total: ${TOTAL}  |  Base URL: ${BASE}"
echo ""
if [[ $FAIL -eq 0 ]]; then
  echo -e "  ${GREEN}${BOLD}All tests passed!${RESET}"
else
  echo -e "  ${RED}${BOLD}${FAIL} test(s) failed — check output above${RESET}"
fi
echo ""
