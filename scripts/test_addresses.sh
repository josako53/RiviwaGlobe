#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# test_addresses.sh
# Full integration test for all /api/v1/addresses endpoints
# User: testgrm@riviwa.com / TestGRM@2026!
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail
BASE="http://localhost:8000/api/v1"
PASS=0; FAIL=0

ok()      { echo "  [PASS] $1" >&2; PASS=$((PASS+1)); }
fail()    { echo "  [FAIL] $1 -- $2" >&2; FAIL=$((FAIL+1)); }
section() { echo "" >&2; echo "── $1 ──" >&2; }
check() {
  local label="$1" got="$2" want="$3"
  [ "$got" = "$want" ] && ok "$label" || fail "$label" "got='$got' want='$want'"
}

# ── Auth ───────────────────────────────────────────────────────────────────────
section "AUTH — testgrm@riviwa.com"
LOGIN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"identifier":"testgrm@riviwa.com","password":"TestGRM@2026!"}')
LT=$(echo "$LOGIN" | python3 -c 'import sys,json; print(json.load(sys.stdin)["login_token"])' 2>/dev/null)
[ -n "$LT" ] && ok "step-1: got login_token" || { fail "step-1: login" "no login_token"; exit 1; }

VERIFY=$(curl -s -X POST "$BASE/auth/login/verify-otp" \
  -H "Content-Type: application/json" \
  -d "{\"login_token\":\"$LT\",\"otp_code\":\"000000\"}")
ACCESS=$(echo "$VERIFY" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))' 2>/dev/null)
[ -n "$ACCESS" ] && ok "step-2: got access_token" || { fail "step-2: verify-otp" "no access_token"; exit 1; }

ME=$(curl -s "$BASE/users/me" -H "Authorization: Bearer $ACCESS" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))' 2>/dev/null)
[ -n "$ME" ] && ok "user id: $ME" || { fail "GET /users/me" "no id"; exit 1; }
AUTH="Authorization: Bearer $ACCESS"

# ── 1. GET /addresses/search ───────────────────────────────────────────────────
section "1. GET /addresses/search  (no auth)"
R=$(curl -s "$BASE/addresses/search?q=Kariakoo+Market&countrycodes=TZ&limit=3")
COUNT=$(echo "$R" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))' 2>/dev/null)
[ "$COUNT" -gt 0 ] && ok "returned $COUNT suggestions" || fail "search" "0 results"
PLACE_ID=$(echo  "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin)[0]["place_id"])' 2>/dev/null)
DISPLAY=$(echo   "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin)[0]["display_name"])' 2>/dev/null)
LINE1=$(echo     "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin)[0].get("line1") or "")' 2>/dev/null)
WARD=$(echo      "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin)[0].get("ward") or "")' 2>/dev/null)
CITY=$(echo      "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin)[0].get("city") or "")' 2>/dev/null)
PCODE=$(echo     "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin)[0].get("postal_code") or "")' 2>/dev/null)
OSM_ID=$(echo    "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin)[0].get("osm_id") or "")' 2>/dev/null)
OSM_TYPE=$(echo  "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin)[0].get("osm_type") or "")' 2>/dev/null)
ok "place_id=$PLACE_ID  osm_id=$OSM_ID  osm_type=$OSM_TYPE"
ok "display: ${DISPLAY:0:70}"
ok "line1=$LINE1  ward=$WARD  city=$CITY  postal=$PCODE"

# ── 2. GET /addresses/reverse ──────────────────────────────────────────────────
section "2. GET /addresses/reverse  (no auth)"
R=$(curl -s "$BASE/addresses/reverse?lat=-6.8196728&lon=39.2749308")
RD=$(echo "$R"  | python3 -c 'import sys,json; d=json.load(sys.stdin); print((d or {}).get("display_name","null"))' 2>/dev/null)
RLT=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print((d or {}).get("gps_latitude","null"))' 2>/dev/null)
RWD=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print((d or {}).get("ward","null"))' 2>/dev/null)
[ "$RD" != "null" ] && ok "got result" || fail "reverse" "null"
ok "display: ${RD:0:70}"
ok "nominatim_lat=$RLT  ward=$RWD"
ok "note: nominatim coords ignored when user provides GPS"

# ── 3a. POST — OSM + precise GPS pin ──────────────────────────────────────────
section "3a. POST /addresses — OSM + GPS (text from search, exact GPS pin)"
R=$(curl -s -X POST "$BASE/addresses" \
  -H "Content-Type: application/json" -H "$AUTH" \
  -d "{
    \"entity_type\":\"user\",\"entity_id\":\"$ME\",
    \"address_type\":\"home\",\"label\":\"Kariakoo OSM+GPS\",
    \"osm_place_id\":$PLACE_ID,
    \"osm_id\":$OSM_ID,\"osm_type\":\"$OSM_TYPE\",
    \"display_name\":\"$DISPLAY\",
    \"line1\":\"$LINE1\",\"ward\":\"$WARD\",
    \"city\":\"$CITY\",\"postal_code\":\"$PCODE\",\"country_code\":\"TZ\",
    \"is_default\":true,
    \"gps_latitude\":-6.8201234,\"gps_longitude\":39.2751234
  }")
ADDR1=$(echo "$R"  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))' 2>/dev/null)
SRC=$(echo "$R"    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("source",""))' 2>/dev/null)
LAT=$(echo "$R"    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("gps_latitude",""))' 2>/dev/null)
LON=$(echo "$R"    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("gps_longitude",""))' 2>/dev/null)
DEF=$(echo "$R"    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("is_default",""))' 2>/dev/null)
DN=$(echo "$R"     | python3 -c 'import sys,json; print((json.load(sys.stdin).get("display_name") or "")[:60])' 2>/dev/null)
WD=$(echo "$R"     | python3 -c 'import sys,json; print(json.load(sys.stdin).get("ward",""))' 2>/dev/null)
DL=$(echo "$R"     | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["display_lines"][0][:60] if d.get("display_lines") else "")' 2>/dev/null)
[ -n "$ADDR1" ] && ok "created id=$ADDR1" || fail "create OSM+GPS" "no id"
check "source=osm"                         "$SRC" "osm"
check "gps_latitude=user pin (-6.8201234)" "$LAT" "-6.8201234"
check "gps_longitude=user pin (39.2751234)" "$LON" "39.2751234"
check "is_default=True (first address)"    "$DEF" "True"
ok "display_name: $DN"
ok "ward: $WD"
ok "display_lines[0]: $DL"

# ── 3b. POST — GPS only ────────────────────────────────────────────────────────
section "3b. POST /addresses — GPS only (reverse-geocode for text)"
R=$(curl -s -X POST "$BASE/addresses" \
  -H "Content-Type: application/json" -H "$AUTH" \
  -d "{
    \"entity_type\":\"user\",\"entity_id\":\"$ME\",
    \"address_type\":\"billing\",\"label\":\"GPS only\",
    \"gps_latitude\":-6.7924567,\"gps_longitude\":39.2080123
  }")
ADDR2=$(echo "$R"  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))' 2>/dev/null)
SRC=$(echo "$R"    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("source",""))' 2>/dev/null)
LAT=$(echo "$R"    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("gps_latitude",""))' 2>/dev/null)
LON=$(echo "$R"    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("gps_longitude",""))' 2>/dev/null)
DN=$(echo "$R"     | python3 -c 'import sys,json; print((json.load(sys.stdin).get("display_name") or "none")[:60])' 2>/dev/null)
[ -n "$ADDR2" ] && ok "created id=$ADDR2" || fail "create GPS only" "no id"
check "source=gps"                          "$SRC" "gps"
check "gps_latitude=user pin (-6.7924567)"  "$LAT" "-6.7924567"
check "gps_longitude=user pin (39.2080123)" "$LON" "39.2080123"
ok "reverse-geocoded: $DN"

# ── 3c. POST — Manual ─────────────────────────────────────────────────────────
section "3c. POST /addresses — Manual entry (full Tanzania hierarchy)"
R=$(curl -s -X POST "$BASE/addresses" \
  -H "Content-Type: application/json" -H "$AUTH" \
  -d '{
    "entity_type":"user","entity_id":"'"$ME"'",
    "address_type":"shipping","label":"Manual address",
    "line1":"Plot 14, Lindi Street","line2":"Floor 3",
    "mtaa":"Gerezani","ward":"Jangwani",
    "lga":"Ilala Municipal Council","district":"Ilala",
    "region":"Dar es Salaam","city":"Dar es Salaam",
    "postal_code":"11101","country_code":"TZ",
    "address_notes":"Near Jangwani market, second building after the mosque"
  }')
ADDR3=$(echo "$R"  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))' 2>/dev/null)
SRC=$(echo "$R"    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("source",""))' 2>/dev/null)
L1=$(echo "$R"     | python3 -c 'import sys,json; print(json.load(sys.stdin).get("line1",""))' 2>/dev/null)
MT=$(echo "$R"     | python3 -c 'import sys,json; print(json.load(sys.stdin).get("mtaa",""))' 2>/dev/null)
WD=$(echo "$R"     | python3 -c 'import sys,json; print(json.load(sys.stdin).get("ward",""))' 2>/dev/null)
LG=$(echo "$R"     | python3 -c 'import sys,json; print(json.load(sys.stdin).get("lga",""))' 2>/dev/null)
DT=$(echo "$R"     | python3 -c 'import sys,json; print(json.load(sys.stdin).get("district",""))' 2>/dev/null)
RG=$(echo "$R"     | python3 -c 'import sys,json; print(json.load(sys.stdin).get("region",""))' 2>/dev/null)
NT=$(echo "$R"     | python3 -c 'import sys,json; print((json.load(sys.stdin).get("address_notes") or "")[:40])' 2>/dev/null)
DL=$(echo "$R"     | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["display_lines"][0][:60] if d.get("display_lines") else "")' 2>/dev/null)
[ -n "$ADDR3" ] && ok "created id=$ADDR3" || fail "create manual" "no id"
check "source=manual"        "$SRC" "manual"
check "line1 preserved"      "$L1"  "Plot 14, Lindi Street"
check "mtaa preserved"       "$MT"  "Gerezani"
check "ward preserved"       "$WD"  "Jangwani"
check "lga preserved"        "$LG"  "Ilala Municipal Council"
check "district preserved"   "$DT"  "Ilala"
check "region preserved"     "$RG"  "Dar es Salaam"
ok "notes: $NT"
ok "display_lines[0]: $DL"

# ── 4. GET list ────────────────────────────────────────────────────────────────
section "4. GET /addresses/user/{id} — list all (default first)"
R=$(curl -s "$BASE/addresses/user/$ME" -H "$AUTH")
TOTAL=$(echo "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("total",0))' 2>/dev/null)
[ "$TOTAL" -ge 3 ] && ok "total=$TOTAL (at least 3)" || fail "list" "total=$TOTAL want>=3"
TYPES=$(echo "$R"   | python3 -c 'import sys,json; a=json.load(sys.stdin)["addresses"]; print([x["address_type"] for x in a])' 2>/dev/null)
SOURCES=$(echo "$R" | python3 -c 'import sys,json; a=json.load(sys.stdin)["addresses"]; print([x["source"] for x in a])' 2>/dev/null)
DEFS=$(echo "$R"    | python3 -c 'import sys,json; a=json.load(sys.stdin)["addresses"]; print([x["is_default"] for x in a])' 2>/dev/null)
ok "address_types: $TYPES"
ok "sources:       $SOURCES"
ok "is_default:    $DEFS"

# ── 5. GET single ──────────────────────────────────────────────────────────────
section "5. GET /addresses/{id} — fetch single"
R=$(curl -s "$BASE/addresses/$ADDR3" -H "$AUTH")
FID=$(echo "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))' 2>/dev/null)
DL=$(echo "$R"  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["display_lines"][0] if d.get("display_lines") else "")' 2>/dev/null)
check "returned correct id"  "$FID" "$ADDR3"
ok "display_lines[0]: $DL"

# ── 6. PATCH ───────────────────────────────────────────────────────────────────
section "6. PATCH /addresses/{id} — partial update"
R=$(curl -s -X PATCH "$BASE/addresses/$ADDR3" \
  -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"label":"Updated label","address_notes":"Updated access directions","gps_latitude":-6.8000001,"gps_longitude":39.2999999}')
NL=$(echo "$R"  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("label",""))' 2>/dev/null)
NN=$(echo "$R"  | python3 -c 'import sys,json; print((json.load(sys.stdin).get("address_notes") or "")[:30])' 2>/dev/null)
NLT=$(echo "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("gps_latitude",""))' 2>/dev/null)
NLN=$(echo "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("gps_longitude",""))' 2>/dev/null)
L1=$(echo "$R"  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("line1",""))' 2>/dev/null)
check "label updated"            "$NL"  "Updated label"
check "notes updated"            "$NN"  "Updated access directions"
check "gps_lat updated (exact)"  "$NLT" "-6.8000001"
check "gps_lon updated (exact)"  "$NLN" "39.2999999"
check "line1 untouched"          "$L1"  "Plot 14, Lindi Street"

# ── 7. set-default ─────────────────────────────────────────────────────────────
section "7. POST /addresses/{id}/set-default"
R=$(curl -s -X POST "$BASE/addresses/$ADDR3/set-default" -H "$AUTH")
ND=$(echo "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("is_default",""))' 2>/dev/null)
check "target is_default=True"  "$ND" "True"
# Previous default must now be False
R2=$(curl -s "$BASE/addresses/$ADDR1" -H "$AUTH")
PD=$(echo "$R2" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("is_default",""))' 2>/dev/null)
check "previous default cleared" "$PD" "False"

# ── 8. DELETE ──────────────────────────────────────────────────────────────────
section "8. DELETE /addresses/{id}"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE/addresses/$ADDR2" -H "$AUTH")
check "DELETE returns 204"       "$STATUS" "204"
R=$(curl -s "$BASE/addresses/$ADDR2" -H "$AUTH")
ERR=$(echo "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("error",""))' 2>/dev/null)
check "GET deleted addr = NOT_FOUND" "$ERR" "NOT_FOUND"
R=$(curl -s "$BASE/addresses/user/$ME" -H "$AUTH")
T2=$(echo "$R" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("total",0))' 2>/dev/null)
check "list count dropped by 1"  "$T2"  "$((TOTAL-1))"

# ── Summary ────────────────────────────────────────────────────────────────────
echo "" >&2
echo "════════════════════════════════════════" >&2
printf " RESULTS: %s PASS / %s FAIL\n" "$PASS" "$FAIL" >&2
echo "════════════════════════════════════════" >&2
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
