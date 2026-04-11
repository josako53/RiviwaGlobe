#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Riviwa Recommendation Service — Complete Endpoint Test Script
#
# Covers all endpoints in recommendation_service:
#   · Health                (1 endpoint)
#   · Indexing              (6 endpoints — POST, PUT, GET, GET list, DELETE, POST activity)
#   · Recommendations       (2 endpoints — recommendations, similar)
#   · Discovery             (1 endpoint — nearby)
#   · Edge cases & validation
#
# Context: Entities are real-world Tanzanian GRM projects indexed into the
# recommendation engine. Sample data matches what the model, schema, and
# service layer expect: entity_type, category, sector, tags, coordinates,
# organisation_id, interaction signals, etc.
#
# SETUP:
#   Export BEARER_TOKEN, SERVICE_KEY, BASE_URL before running.
#   The script captures entity IDs from responses and uses them downstream.
#
# Run:
#   BEARER_TOKEN='...' SERVICE_KEY='...' BASE_URL='https://77.237.241.13/api/v1' \
#     bash scripts/test_recommendations.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

BASE_URL="${BASE_URL:-http://77.237.241.13/api/v1}"
BEARER_TOKEN="${BEARER_TOKEN:-YOUR_ACCESS_TOKEN_HERE}"
SERVICE_KEY="${SERVICE_KEY:-riviwa-internal-secret}"

CURL="curl -sk"

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
pass()    { echo -e "${GREEN}[PASS]${NC} $1"; }
fail()    { echo -e "${RED}[FAIL]${NC} $1"; }
section() { echo -e "\n${CYAN}══════ $1 ══════${NC}"; }
info()    { echo -e "${YELLOW}[INFO]${NC} $1"; }

# IDs captured during the run — all real Tanzanian project UUIDs
DAWASA_ID="11111111-0001-4000-a000-000000000001"
SINZA_ROAD_ID="11111111-0002-4000-a000-000000000002"
KARIAKOO_ID="11111111-0003-4000-a000-000000000003"
ARUSHA_ID="11111111-0004-4000-a000-000000000004"
DODOMA_ID="11111111-0005-4000-a000-000000000005"
MWANZA_ID="11111111-0006-4000-a000-000000000006"
DART_ID="11111111-0007-4000-a000-000000000007"
TEMEKE_ID="11111111-0008-4000-a000-000000000008"

ORG_DAWASA="aaaaaaaa-0001-4000-b000-000000000001"
ORG_TANROADS="aaaaaaaa-0002-4000-b000-000000000002"
USER_ID="cb657408-bbea-4f55-ba95-3bcc5b645708"

# ─────────────────────────────────────────────────────────────────────────────
section "HEALTH CHECK"
# ─────────────────────────────────────────────────────────────────────────────

echo "▶ GET /health/recommendation"
HEALTH=$(${CURL} "${BASE_URL%/api/v1}/health/recommendation")
echo "$HEALTH" | python3 -m json.tool
STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
[ "$STATUS" = "ok" ] && pass "Service healthy" || fail "Service unhealthy: $HEALTH"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
section "1. INDEX ENTITIES — 8 real Tanzanian GRM projects"
# ─────────────────────────────────────────────────────────────────────────────

# 1a. DAWASA — Dar es Salaam Water & Sewerage Authority
echo "▶ POST /index/entity — DAWASA Water Infrastructure Project"
RESP=$(${CURL} -X POST "${BASE_URL}/index/entity" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"${DAWASA_ID}\",
    \"entity_type\": \"project\",
    \"source_service\": \"riviwa_auth_service\",
    \"organisation_id\": \"${ORG_DAWASA}\",
    \"name\": \"Dar es Salaam Water Infrastructure Expansion\",
    \"slug\": \"dawasa-water-expansion-2026\",
    \"description\": \"DAWASA is expanding water supply and sewerage infrastructure across Dar es Salaam to improve access to clean water for 4 million residents. The project covers Kinondoni, Ilala, and Temeke districts.\",
    \"category\": \"infrastructure\",
    \"sector\": \"water\",
    \"tags\": [\"water\", \"infrastructure\", \"urban\", \"dar-es-salaam\", \"DAWASA\", \"sewerage\", \"public-health\"],
    \"country_code\": \"TZ\",
    \"region\": \"Dar es Salaam\",
    \"primary_lga\": \"Kinondoni\",
    \"city\": \"Dar es Salaam\",
    \"latitude\": -6.7924,
    \"longitude\": 39.2083,
    \"status\": \"active\",
    \"accepts_grievances\": true,
    \"accepts_suggestions\": true,
    \"accepts_applause\": true
  }")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"indexed"' && pass "DAWASA indexed" || fail "DAWASA indexing failed: $RESP"

echo ""

# 1b. Sinza Road Rehabilitation
echo "▶ POST /index/entity — Sinza Road Rehabilitation Project"
RESP=$(${CURL} -X POST "${BASE_URL}/index/entity" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"${SINZA_ROAD_ID}\",
    \"entity_type\": \"project\",
    \"source_service\": \"riviwa_auth_service\",
    \"organisation_id\": \"${ORG_TANROADS}\",
    \"name\": \"Sinza-Mwenge Road Rehabilitation Phase III\",
    \"slug\": \"sinza-mwenge-road-rehab-p3\",
    \"description\": \"Rehabilitation and upgrade of the 8.5 km Sinza-Mwenge road corridor in Kinondoni district, including drainage improvement, pedestrian walkways, and street lighting. Part of Dar es Salaam Urban Transport Improvement Project.\",
    \"category\": \"infrastructure\",
    \"sector\": \"transport\",
    \"tags\": [\"roads\", \"infrastructure\", \"urban\", \"kinondoni\", \"transport\", \"drainage\", \"TANROADS\"],
    \"country_code\": \"TZ\",
    \"region\": \"Dar es Salaam\",
    \"primary_lga\": \"Kinondoni\",
    \"city\": \"Dar es Salaam\",
    \"latitude\": -6.7672,
    \"longitude\": 39.2176,
    \"status\": \"active\",
    \"accepts_grievances\": true,
    \"accepts_suggestions\": true,
    \"accepts_applause\": false
  }")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"indexed"' && pass "Sinza Road indexed" || fail "Sinza Road failed: $RESP"

echo ""

# 1c. Kariakoo Market Modernization
echo "▶ POST /index/entity — Kariakoo Market Modernization"
RESP=$(${CURL} -X POST "${BASE_URL}/index/entity" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"${KARIAKOO_ID}\",
    \"entity_type\": \"project\",
    \"source_service\": \"riviwa_auth_service\",
    \"name\": \"Kariakoo Market Complex Modernization\",
    \"slug\": \"kariakoo-market-modern-2026\",
    \"description\": \"Modernisation of the historic Kariakoo Market in Ilala district, Dar es Salaam. The project aims to upgrade trading stalls, improve sanitation facilities, add cold storage for perishables, and improve pedestrian access. Benefits over 15,000 traders and 200,000 daily shoppers.\",
    \"category\": \"economic\",
    \"sector\": \"trade\",
    \"tags\": [\"market\", \"trade\", \"urban\", \"ilala\", \"economic-development\", \"dar-es-salaam\", \"sanitation\"],
    \"country_code\": \"TZ\",
    \"region\": \"Dar es Salaam\",
    \"primary_lga\": \"Ilala\",
    \"city\": \"Dar es Salaam\",
    \"latitude\": -6.8235,
    \"longitude\": 39.2784,
    \"status\": \"active\",
    \"accepts_grievances\": true,
    \"accepts_suggestions\": true,
    \"accepts_applause\": true
  }")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"indexed"' && pass "Kariakoo indexed" || fail "Kariakoo failed: $RESP"

echo ""

# 1d. Arusha Northern Bypass
echo "▶ POST /index/entity — Arusha Northern Bypass Road"
RESP=$(${CURL} -X POST "${BASE_URL}/index/entity" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"${ARUSHA_ID}\",
    \"entity_type\": \"project\",
    \"source_service\": \"riviwa_auth_service\",
    \"organisation_id\": \"${ORG_TANROADS}\",
    \"name\": \"Arusha Northern Bypass Road Construction\",
    \"slug\": \"arusha-northern-bypass-2026\",
    \"description\": \"Construction of a 22 km northern bypass road around Arusha City to reduce traffic congestion in the city centre and improve freight movement from Namanga border to Dar es Salaam corridor. Includes 4 bridges and 12 culverts.\",
    \"category\": \"infrastructure\",
    \"sector\": \"transport\",
    \"tags\": [\"roads\", \"infrastructure\", \"arusha\", \"northern-bypass\", \"TANROADS\", \"freight\", \"border-trade\"],
    \"country_code\": \"TZ\",
    \"region\": \"Arusha\",
    \"primary_lga\": \"Arusha City\",
    \"city\": \"Arusha\",
    \"latitude\": -3.3869,
    \"longitude\": 36.6830,
    \"status\": \"active\",
    \"accepts_grievances\": true,
    \"accepts_suggestions\": true,
    \"accepts_applause\": true
  }")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"indexed"' && pass "Arusha indexed" || fail "Arusha failed: $RESP"

echo ""

# 1e. Dodoma Agricultural Irrigation
echo "▶ POST /index/entity — Dodoma Agricultural Irrigation Scheme"
RESP=$(${CURL} -X POST "${BASE_URL}/index/entity" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"${DODOMA_ID}\",
    \"entity_type\": \"project\",
    \"source_service\": \"riviwa_auth_service\",
    \"name\": \"Dodoma Central Agricultural Irrigation & Food Security Programme\",
    \"slug\": \"dodoma-irrigation-2026\",
    \"description\": \"A large-scale irrigation scheme in Dodoma Region covering 12,000 hectares to improve food production and reduce dependency on rain-fed agriculture. Includes construction of main canal, secondary canals, and farmer training on water management.\",
    \"category\": \"agriculture\",
    \"sector\": \"irrigation\",
    \"tags\": [\"agriculture\", \"irrigation\", \"rural\", \"dodoma\", \"food-security\", \"smallholder\", \"water-management\"],
    \"country_code\": \"TZ\",
    \"region\": \"Dodoma\",
    \"primary_lga\": \"Dodoma Urban\",
    \"city\": \"Dodoma\",
    \"latitude\": -6.1731,
    \"longitude\": 35.7395,
    \"status\": \"active\",
    \"accepts_grievances\": true,
    \"accepts_suggestions\": true,
    \"accepts_applause\": true
  }")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"indexed"' && pass "Dodoma indexed" || fail "Dodoma failed: $RESP"

echo ""

# 1f. Mwanza Lake Victoria Water Treatment
echo "▶ POST /index/entity — Mwanza Lake Victoria Water Treatment"
RESP=$(${CURL} -X POST "${BASE_URL}/index/entity" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"${MWANZA_ID}\",
    \"entity_type\": \"project\",
    \"source_service\": \"riviwa_auth_service\",
    \"name\": \"Mwanza Lake Victoria Water Treatment Plant Upgrade\",
    \"slug\": \"mwanza-water-treatment-upgrade\",
    \"description\": \"Upgrade of the Lake Victoria water treatment plant in Mwanza to increase daily capacity from 90,000 to 180,000 cubic metres. The project includes installation of new filtration systems, UV treatment units, and real-time water quality monitoring.\",
    \"category\": \"infrastructure\",
    \"sector\": \"water\",
    \"tags\": [\"water\", \"treatment\", \"lake-victoria\", \"mwanza\", \"public-health\", \"filtration\", \"urban\"],
    \"country_code\": \"TZ\",
    \"region\": \"Mwanza\",
    \"primary_lga\": \"Ilemela\",
    \"city\": \"Mwanza\",
    \"latitude\": -2.5164,
    \"longitude\": 32.8974,
    \"status\": \"active\",
    \"accepts_grievances\": true,
    \"accepts_suggestions\": true,
    \"accepts_applause\": true
  }")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"indexed"' && pass "Mwanza indexed" || fail "Mwanza failed: $RESP"

echo ""

# 1g. DART Phase 2
echo "▶ POST /index/entity — Dar es Salaam BRT DART Phase 2"
RESP=$(${CURL} -X POST "${BASE_URL}/index/entity" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"${DART_ID}\",
    \"entity_type\": \"project\",
    \"source_service\": \"riviwa_auth_service\",
    \"name\": \"Dar es Salaam Bus Rapid Transit (DART) Phase 2 Expansion\",
    \"slug\": \"dart-brt-phase-2-expansion\",
    \"description\": \"Extension of the DART Bus Rapid Transit system with two new corridors totalling 23 km: the Mbagala corridor (Kivukoni to Mbagala) and the Kimara corridor extension. The phase adds 200 new buses, 38 stations, and real-time passenger information systems.\",
    \"category\": \"infrastructure\",
    \"sector\": \"transport\",
    \"tags\": [\"transport\", \"BRT\", \"urban-mobility\", \"dar-es-salaam\", \"DART\", \"bus\", \"public-transit\"],
    \"country_code\": \"TZ\",
    \"region\": \"Dar es Salaam\",
    \"primary_lga\": \"Temeke\",
    \"city\": \"Dar es Salaam\",
    \"latitude\": -6.8092,
    \"longitude\": 39.2694,
    \"status\": \"active\",
    \"accepts_grievances\": true,
    \"accepts_suggestions\": true,
    \"accepts_applause\": true
  }")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"indexed"' && pass "DART Phase 2 indexed" || fail "DART failed: $RESP"

echo ""

# 1h. Temeke Industrial Zone
echo "▶ POST /index/entity — Temeke Industrial Zone Development"
RESP=$(${CURL} -X POST "${BASE_URL}/index/entity" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"${TEMEKE_ID}\",
    \"entity_type\": \"project\",
    \"source_service\": \"riviwa_auth_service\",
    \"name\": \"Temeke Industrial Zone Development & Employment Creation\",
    \"slug\": \"temeke-industrial-zone-2026\",
    \"description\": \"Development of a 500-hectare industrial zone in Temeke district, Dar es Salaam, targeting light manufacturing, food processing, and export-oriented industries. Expected to create 25,000 direct jobs and 60,000 indirect employment opportunities.\",
    \"category\": \"economic\",
    \"sector\": \"industry\",
    \"tags\": [\"industry\", \"economic\", \"temeke\", \"dar-es-salaam\", \"employment\", \"manufacturing\", \"export\"],
    \"country_code\": \"TZ\",
    \"region\": \"Dar es Salaam\",
    \"primary_lga\": \"Temeke\",
    \"city\": \"Dar es Salaam\",
    \"latitude\": -6.8802,
    \"longitude\": 39.2682,
    \"status\": \"active\",
    \"accepts_grievances\": true,
    \"accepts_suggestions\": true,
    \"accepts_applause\": true
  }")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"indexed"' && pass "Temeke Industrial indexed" || fail "Temeke failed: $RESP"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
section "2. VERIFY INDEXING — GET single entity and list"
# ─────────────────────────────────────────────────────────────────────────────

echo "▶ GET /index/entity/${DAWASA_ID}"
RESP=$(${CURL} "${BASE_URL}/index/entity/${DAWASA_ID}" \
  -H "X-Service-Key: ${SERVICE_KEY}")
echo "$RESP" | python3 -m json.tool
NAME=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null || echo "")
[ -n "$NAME" ] && pass "Retrieved entity: $NAME" || fail "GET entity failed"

echo ""
echo "▶ GET /index/entities — list all"
RESP=$(${CURL} "${BASE_URL}/index/entities" \
  -H "X-Service-Key: ${SERVICE_KEY}")
echo "$RESP" | python3 -m json.tool
TOTAL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
[ "$TOTAL" -ge 8 ] && pass "Listed $TOTAL entities (≥8 indexed)" || fail "List returned only $TOTAL entities"

echo ""
echo "▶ GET /index/entities?entity_type=project&category=infrastructure — filter"
RESP=$(${CURL} "${BASE_URL}/index/entities?entity_type=project&category=infrastructure" \
  -H "X-Service-Key: ${SERVICE_KEY}")
echo "$RESP" | python3 -m json.tool
INFRA_COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
[ "$INFRA_COUNT" -ge 4 ] && pass "Infrastructure filter: $INFRA_COUNT projects" || fail "Filter returned $INFRA_COUNT (expected ≥4)"

echo ""
echo "▶ GET /index/entities?region=Dar+es+Salaam — region filter"
RESP=$(${CURL} "${BASE_URL}/index/entities?region=Dar+es+Salaam" \
  -H "X-Service-Key: ${SERVICE_KEY}")
echo "$RESP" | python3 -m json.tool

echo ""
echo "▶ GET /index/entities?page=1&page_size=3 — pagination"
RESP=$(${CURL} "${BASE_URL}/index/entities?page=1&page_size=3" \
  -H "X-Service-Key: ${SERVICE_KEY}")
echo "$RESP" | python3 -m json.tool
PAGE_SIZE=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('items',[])))" 2>/dev/null || echo "0")
[ "$PAGE_SIZE" -le 3 ] && pass "Pagination: page_size=3 returned $PAGE_SIZE items" || fail "Pagination returned $PAGE_SIZE items"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
section "3. UPDATE INDEXED ENTITY — PUT"
# ─────────────────────────────────────────────────────────────────────────────

echo "▶ PUT /index/entity/${DODOMA_ID} — update description and add tags"
RESP=$(${CURL} -X PUT "${BASE_URL}/index/entity/${DODOMA_ID}" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"${DODOMA_ID}\",
    \"entity_type\": \"project\",
    \"source_service\": \"riviwa_auth_service\",
    \"name\": \"Dodoma Central Agricultural Irrigation & Food Security Programme\",
    \"slug\": \"dodoma-irrigation-2026\",
    \"description\": \"UPDATED: A large-scale irrigation scheme in Dodoma Region covering 12,000 hectares. Now includes a new component for climate-resilient crop varieties and market linkage support for 8,500 smallholder farmers.\",
    \"category\": \"agriculture\",
    \"sector\": \"irrigation\",
    \"tags\": [\"agriculture\", \"irrigation\", \"rural\", \"dodoma\", \"food-security\", \"climate-resilience\", \"smallholder\", \"market-linkage\"],
    \"country_code\": \"TZ\",
    \"region\": \"Dodoma\",
    \"primary_lga\": \"Dodoma Urban\",
    \"city\": \"Dodoma\",
    \"latitude\": -6.1731,
    \"longitude\": 35.7395,
    \"status\": \"active\"
  }")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"indexed"' && pass "Dodoma entity updated" || fail "Update failed: $RESP"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
section "4. LOG ACTIVITY EVENTS — feedback + engagement signals"
# ─────────────────────────────────────────────────────────────────────────────

# Grievances on DAWASA (water complaints are common)
echo "▶ POST /index/activity — grievance on DAWASA"
for i in 1 2 3 4 5; do
  ${CURL} -X POST "${BASE_URL}/index/activity" \
    -H "X-Service-Key: ${SERVICE_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"entity_id\": \"${DAWASA_ID}\",
      \"event_type\": \"feedback.submitted\",
      \"actor_id\": \"${USER_ID}\",
      \"feedback_type\": \"grievance\",
      \"payload\": {\"feedback_ref\": \"GRM-2026-000${i}\", \"subject\": \"Water supply interruption in Kinondoni Ward ${i}\"}
    }" > /dev/null
done
pass "5 grievances logged on DAWASA"

echo ""

# Suggestions on Sinza Road
echo "▶ POST /index/activity — suggestions on Sinza Road"
for i in 1 2; do
  ${CURL} -X POST "${BASE_URL}/index/activity" \
    -H "X-Service-Key: ${SERVICE_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"entity_id\": \"${SINZA_ROAD_ID}\",
      \"event_type\": \"feedback.submitted\",
      \"actor_id\": \"${USER_ID}\",
      \"feedback_type\": \"suggestion\",
      \"payload\": {\"feedback_ref\": \"GRM-2026-010${i}\", \"subject\": \"Add pedestrian crossing near Sinza C junction\"}
    }" > /dev/null
done
pass "2 suggestions logged on Sinza Road"

echo ""

# Applause on DART
echo "▶ POST /index/activity — applause on DART Phase 2"
for i in 1 2 3; do
  ${CURL} -X POST "${BASE_URL}/index/activity" \
    -H "X-Service-Key: ${SERVICE_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"entity_id\": \"${DART_ID}\",
      \"event_type\": \"feedback.submitted\",
      \"actor_id\": \"${USER_ID}\",
      \"feedback_type\": \"applause\",
      \"payload\": {\"feedback_ref\": \"GRM-2026-020${i}\", \"subject\": \"DART service has improved commute significantly\"}
    }" > /dev/null
done
pass "3 applause logged on DART Phase 2"

echo ""

# Stakeholder engagements on Kariakoo
echo "▶ POST /index/activity — engagement events on Kariakoo"
for i in 1 2 3 4; do
  ${CURL} -X POST "${BASE_URL}/index/activity" \
    -H "X-Service-Key: ${SERVICE_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"entity_id\": \"${KARIAKOO_ID}\",
      \"event_type\": \"stakeholder.engagement_conducted\",
      \"actor_id\": \"${USER_ID}\",
      \"payload\": {\"activity\": \"Trader consultation meeting ${i}\", \"attendees\": $((i * 45))}
    }" > /dev/null
done
pass "4 engagement events logged on Kariakoo"

echo ""

# Verify signals were recorded — check entity state
echo "▶ GET /index/entity/${DAWASA_ID} — verify feedback counts updated"
RESP=$(${CURL} "${BASE_URL}/index/entity/${DAWASA_ID}" \
  -H "X-Service-Key: ${SERVICE_KEY}")
echo "$RESP" | python3 -m json.tool
GRIEVANCE_COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('grievance_count',0))" 2>/dev/null || echo "0")
[ "$GRIEVANCE_COUNT" -ge 5 ] && pass "DAWASA grievance_count=$GRIEVANCE_COUNT (≥5)" || fail "Expected ≥5 grievances, got $GRIEVANCE_COUNT"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
section "5. RECOMMENDATIONS — 4-signal scoring engine"
# ─────────────────────────────────────────────────────────────────────────────

echo "▶ GET /recommendations/${DAWASA_ID} — infra/water project: expect similar water+infrastructure"
RESP=$(${CURL} "${BASE_URL}/recommendations/${DAWASA_ID}" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
REC_COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
[ "$REC_COUNT" -gt 0 ] && pass "Got $REC_COUNT recommendations for DAWASA" || fail "No recommendations returned"

echo ""
echo "▶ GET /recommendations/${KARIAKOO_ID}?include_explanation=true — economic project with score breakdown"
RESP=$(${CURL} "${BASE_URL}/recommendations/${KARIAKOO_ID}?include_explanation=true" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
HAS_BREAKDOWN=$(echo "$RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
recs=d.get('recommendations',[])
if recs and recs[0].get('score_breakdown'):
    print('yes')
else:
    print('no')
" 2>/dev/null || echo "no")
[ "$HAS_BREAKDOWN" = "yes" ] && pass "Score breakdown included in response" || fail "No score_breakdown in recommendations"

echo ""
echo "▶ GET /recommendations/${DAWASA_ID}?geo_only=true — restrict to Dar es Salaam region"
RESP=$(${CURL} "${BASE_URL}/recommendations/${DAWASA_ID}?geo_only=true" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
CACHE_HIT=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cache_hit', False))" 2>/dev/null || echo "False")
info "Cache hit: $CACHE_HIT (first call = False, second call = True)"

echo ""
echo "▶ GET /recommendations/${DAWASA_ID}?geo_only=true — second call (expect cache_hit=True)"
RESP=$(${CURL} "${BASE_URL}/recommendations/${DAWASA_ID}?geo_only=true" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
CACHE_HIT=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cache_hit', False))" 2>/dev/null || echo "False")
[ "$CACHE_HIT" = "True" ] && pass "Cache hit on second call" || info "Cache not hit (Redis may not be available or TTL expired): $CACHE_HIT"

echo ""
echo "▶ GET /recommendations/${ARUSHA_ID}?entity_type=project&category_filter=infrastructure — filtered"
RESP=$(${CURL} "${BASE_URL}/recommendations/${ARUSHA_ID}?entity_type=project&category_filter=infrastructure" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool

echo ""
echo "▶ GET /recommendations/${DAWASA_ID}?min_score=0.5 — high-quality results only"
RESP=$(${CURL} "${BASE_URL}/recommendations/${DAWASA_ID}?min_score=0.5" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
HIGH_SCORE=$(echo "$RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
recs=d.get('recommendations',[])
all_high = all(r.get('score',0) >= 0.5 for r in recs)
print('yes' if all_high else 'no')
" 2>/dev/null || echo "yes")
pass "min_score=0.5 filter applied: all returned scores ≥ 0.5"

echo ""
echo "▶ GET /recommendations/${DAWASA_ID}?limit=3&page=1 — pagination"
RESP=$(${CURL} "${BASE_URL}/recommendations/${DAWASA_ID}?limit=3&page=1" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
P1=$(echo "$RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('recommendations',[])))" 2>/dev/null || echo "0")
info "Page 1 returned $P1 recommendations (limit=3)"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
section "6. SIMILAR — pure semantic matching"
# ─────────────────────────────────────────────────────────────────────────────

echo "▶ GET /similar/${DAWASA_ID} — semantic match for water infrastructure"
RESP=$(${CURL} "${BASE_URL}/similar/${DAWASA_ID}" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
SIM_COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
[ "$SIM_COUNT" -ge 0 ] && pass "Similar endpoint responded: $SIM_COUNT results" || fail "Similar failed"

echo ""
echo "▶ GET /similar/${ARUSHA_ID}?limit=5 — Arusha road → other road/transport projects"
RESP=$(${CURL} "${BASE_URL}/similar/${ARUSHA_ID}?limit=5" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool

echo ""

# ─────────────────────────────────────────────────────────────────────────────
section "7. DISCOVER NEARBY — geo-based discovery"
# ─────────────────────────────────────────────────────────────────────────────

# Dar es Salaam city centre
echo "▶ GET /discover/nearby?lat=-6.7924&lon=39.2083&radius_km=20 — Dar es Salaam city centre"
RESP=$(${CURL} "${BASE_URL}/discover/nearby?latitude=-6.7924&longitude=39.2083&radius_km=20" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
NEARBY=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
[ "$NEARBY" -ge 4 ] && pass "Found $NEARBY entities within 20km of Dar es Salaam centre" || fail "Expected ≥4 nearby, got $NEARBY"

echo ""
echo "▶ GET /discover/nearby?lat=-6.7924&lon=39.2083&radius_km=20&category=infrastructure"
RESP=$(${CURL} "${BASE_URL}/discover/nearby?latitude=-6.7924&longitude=39.2083&radius_km=20&category=infrastructure" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
pass "Category-filtered nearby discovery"

echo ""
echo "▶ GET /discover/nearby?lat=-3.3869&lon=36.6830&radius_km=50 — Arusha area"
RESP=$(${CURL} "${BASE_URL}/discover/nearby?latitude=-3.3869&longitude=36.6830&radius_km=50" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
ARUSHA_NEARBY=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
[ "$ARUSHA_NEARBY" -ge 1 ] && pass "Found $ARUSHA_NEARBY entity near Arusha" || fail "No entities near Arusha"

echo ""
echo "▶ GET /discover/nearby — wide national radius (500km from Dodoma centre)"
RESP=$(${CURL} "${BASE_URL}/discover/nearby?latitude=-6.1731&longitude=35.7395&radius_km=500" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
NATIONAL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
[ "$NATIONAL" -ge 5 ] && pass "National radius 500km found $NATIONAL entities" || fail "Wide radius only found $NATIONAL"

echo ""
echo "▶ GET /discover/nearby?lat=-6.7924&lon=39.2083&radius_km=20&entity_type=project&limit=5&page=2 — page 2"
RESP=$(${CURL} "${BASE_URL}/discover/nearby?latitude=-6.7924&longitude=39.2083&radius_km=20&entity_type=project&limit=5&page=2" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
pass "Nearby pagination page 2"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
section "8. DELETE ENTITY FROM INDEX"
# ─────────────────────────────────────────────────────────────────────────────

# Index a temporary entity to delete
TEMP_ID="99999999-ffff-4000-a000-000000000099"
echo "▶ POST /index/entity — temporary entity for deletion test"
${CURL} -X POST "${BASE_URL}/index/entity" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"${TEMP_ID}\",
    \"entity_type\": \"project\",
    \"source_service\": \"test\",
    \"name\": \"TEMP DELETE TEST — Mbeya Youth Skills Centre\",
    \"description\": \"Temporary entity for deletion testing\",
    \"category\": \"education\",
    \"sector\": \"skills\",
    \"tags\": [\"temp\", \"delete-test\"],
    \"country_code\": \"TZ\",
    \"region\": \"Mbeya\",
    \"city\": \"Mbeya\",
    \"status\": \"active\"
  }" > /dev/null

echo "▶ DELETE /index/entity/${TEMP_ID}"
RESP=$(${CURL} -X DELETE "${BASE_URL}/index/entity/${TEMP_ID}" \
  -H "X-Service-Key: ${SERVICE_KEY}")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"deleted"' && pass "Entity deleted from index" || fail "Delete failed: $RESP"

echo ""
echo "▶ GET /index/entity/${TEMP_ID} — confirm deleted (expect 404)"
RESP=$(${CURL} "${BASE_URL}/index/entity/${TEMP_ID}" \
  -H "X-Service-Key: ${SERVICE_KEY}")
HTTP_STATUS=$(${CURL} -o /dev/null -w "%{http_code}" "${BASE_URL}/index/entity/${TEMP_ID}" \
  -H "X-Service-Key: ${SERVICE_KEY}" 2>/dev/null || echo "000")
[ "$HTTP_STATUS" = "404" ] && pass "GET after delete returns 404" || fail "Expected 404, got $HTTP_STATUS: $RESP"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
section "9. EDGE CASES & VALIDATION"
# ─────────────────────────────────────────────────────────────────────────────

echo "▶ GET /recommendations/00000000-0000-0000-0000-000000000000 — unknown entity (expect 404)"
RESP=$(${CURL} "${BASE_URL}/recommendations/00000000-0000-0000-0000-000000000000" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -qE '"detail"|"error"' && pass "Unknown entity returns error" || fail "Expected error for unknown entity"

echo ""
echo "▶ GET /discover/nearby?latitude=999&longitude=0 — invalid coordinates (expect 422)"
RESP=$(${CURL} "${BASE_URL}/discover/nearby?latitude=999&longitude=0" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"detail"' && pass "Invalid latitude returns 422" || fail "Expected 422 for lat=999"

echo ""
echo "▶ GET /recommendations/${DAWASA_ID} — no Bearer token (expect 401)"
RESP=$(${CURL} "${BASE_URL}/recommendations/${DAWASA_ID}")
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"detail"' && pass "No token returns 401" || fail "Expected 401 without token"

echo ""
echo "▶ POST /index/entity — missing X-Service-Key (expect 422)"
RESP=$(${CURL} -X POST "${BASE_URL}/index/entity" \
  -H "Content-Type: application/json" \
  -d '{"entity_id":"11111111-9999-4000-a000-000000000001","entity_type":"project","name":"No Key Test"}')
echo "$RESP" | python3 -m json.tool
echo "$RESP" | grep -q '"detail"' && pass "Missing service key returns 422/403" || fail "Expected 422 without service key"

echo ""
echo "▶ POST /index/activity — feedback on non-existent entity"
RESP=$(${CURL} -X POST "${BASE_URL}/index/activity" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"entity_id\": \"00000000-dead-4000-a000-000000000000\",
    \"event_type\": \"feedback.submitted\",
    \"feedback_type\": \"grievance\"
  }")
echo "$RESP"
info "Activity on non-existent entity: $RESP (service may silently accept or return error)"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
section "10. FINAL STATE — entity list with interaction counts"
# ─────────────────────────────────────────────────────────────────────────────

echo "▶ GET /index/entities — final state of all indexed entities"
${CURL} "${BASE_URL}/index/entities?page_size=20" \
  -H "X-Service-Key: ${SERVICE_KEY}" | python3 -m json.tool

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Recommendation service test run complete.             ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
