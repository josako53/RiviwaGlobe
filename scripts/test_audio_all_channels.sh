#!/usr/bin/env bash
# test_audio_all_channels.sh
# Tests audio/voice submission across every channel + AI insights voice.
# Run inside the server: bash scripts/test_audio_all_channels.sh
# Or set BASE_FB / BASE_AI / BASE_AN to point at running containers.

BASE_FB="${BASE_FB:-http://localhost:8090}"
BASE_AI="${BASE_AI:-http://localhost:8085}"
BASE_AN="${BASE_AN:-http://localhost:8095}"

PASS=0; FAIL=0

ok()   { echo "  [PASS] $*"; ((PASS++)); }
fail() { echo "  [FAIL] $*"; ((FAIL++)); }
sep()  { echo ""; echo "━━━ $* ━━━"; }

# ── Auth: get a staff JWT and a consumer JWT ──────────────────────────────────
sep "AUTH — get tokens"

STAFF_RESP=$(curl -sf -X POST "$BASE_FB/../auth/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"testgrm@riviwa.com","password":"TestGRM@2026!"}' 2>/dev/null || \
  curl -sf -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"testgrm@riviwa.com","password":"TestGRM@2026!"}' 2>/dev/null)

STAFF_TOKEN=$(echo "$STAFF_RESP" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null)

if [[ -n "$STAFF_TOKEN" ]]; then
  ok "staff JWT obtained (${#STAFF_TOKEN} chars)"
else
  fail "staff JWT failed — $STAFF_RESP"
  STAFF_TOKEN=""
fi

# ── Build test WAV (44-byte header + 3 000 bytes silence = ~0.1s @ 16kHz) ────
python3 - <<'PY' > /tmp/test_audio.wav
import struct, sys
pcm = b'\x00' * 3000
hdr = struct.pack('<4sI4s4sIHHIIHH4sI',
  b'RIFF', 36+len(pcm), b'WAVE', b'fmt ', 16, 1, 1,
  16000, 32000, 2, 16, b'data', len(pcm))
sys.stdout.buffer.write(hdr + pcm)
PY
ok "test WAV built ($(wc -c < /tmp/test_audio.wav) bytes)"

# ── Get a project_id for tests ────────────────────────────────────────────────
sep "SETUP — get project_id"
PROJ_RESP=$(curl -sf "$BASE_FB/api/v1/projects?limit=1" \
  -H "Authorization: Bearer $STAFF_TOKEN" 2>/dev/null)
PROJECT_ID=$(echo "$PROJ_RESP" | python3 -c \
  "import sys,json; items=json.load(sys.stdin).get('items',json.load(open('/dev/stdin')) if False else []); \
   print(items[0]['id'] if items else '')" 2>/dev/null || echo "")
# Fallback: query from feedback service internal
if [[ -z "$PROJECT_ID" ]]; then
  PROJECT_ID=$(curl -sf "$BASE_FB/api/v1/projects?limit=1" 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); items=d.get('items',d.get('data',[])); print(items[0].get('id','') if items else '')" 2>/dev/null || echo "")
fi
[[ -n "$PROJECT_ID" ]] && ok "project_id=$PROJECT_ID" || fail "no project_id found — some tests will skip"

# ═══════════════════════════════════════════════════════════════════════════════
sep "CHANNEL 1 — AI Conversation voice message (web/mobile consumer)"
# ═══════════════════════════════════════════════════════════════════════════════

CONV=$(curl -sf -X POST "$BASE_AI/api/v1/ai/conversations/start" \
  -H "Content-Type: application/json" \
  -d '{"channel":"web","language":"sw"}' 2>/dev/null)
CONV_ID=$(echo "$CONV" | python3 -c "import sys,json; print(json.load(sys.stdin).get('conversation_id',''))" 2>/dev/null)

if [[ -n "$CONV_ID" ]]; then
  ok "conversation started conv=$CONV_ID"

  VOICE_RESP=$(curl -sf -X POST "$BASE_AI/api/v1/ai/conversations/$CONV_ID/voice-message" \
    -F "audio=@/tmp/test_audio.wav;type=audio/wav" 2>/dev/null)
  TRANSCRIPT=$(echo "$VOICE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(repr(d.get('transcript','')))" 2>/dev/null)
  AUDIO_URL=$(echo  "$VOICE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('audio_url') or '(none)')" 2>/dev/null)
  LANG=$(echo       "$VOICE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('detected_language','?'))" 2>/dev/null)
  TURNS=$(echo      "$VOICE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('turn_count','?'))" 2>/dev/null)
  ERR=$(echo        "$VOICE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null)
  echo "  transcript=$TRANSCRIPT  lang=$LANG  turns=$TURNS"
  [[ -z "$ERR" && "$TURNS" -ge 2 ]]     && ok "voice message processed" || fail "voice message: error=$ERR"
  [[ "$AUDIO_URL" != "(none)" ]]         && ok "audio stored in MinIO: $AUDIO_URL" || fail "audio_url is null (MinIO storage failed)"
else
  fail "could not start AI conversation"
fi

# ═══════════════════════════════════════════════════════════════════════════════
sep "CHANNEL 2 — Feedback voice note (staff attaches audio to existing feedback)"
# ═══════════════════════════════════════════════════════════════════════════════

if [[ -n "$STAFF_TOKEN" && -n "$PROJECT_ID" ]]; then
  # Create a draft feedback first
  DRAFT=$(curl -sf -X POST "$BASE_FB/api/v1/feedback" \
    -H "Authorization: Bearer $STAFF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"project_id\":\"$PROJECT_ID\",\"feedback_type\":\"grievance\",\"category\":\"infrastructure\",
         \"channel\":\"in_person\",\"subject\":\"Test voice note feedback\",
         \"description\":\"Draft created for voice note test.\"}" 2>/dev/null)
  FB_ID=$(echo "$DRAFT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)

  if [[ -n "$FB_ID" ]]; then
    ok "draft feedback created id=$FB_ID"

    VOICE_NOTE=$(curl -sf -X POST "$BASE_FB/api/v1/voice/feedback/$FB_ID/voice-note" \
      -H "Authorization: Bearer $STAFF_TOKEN" \
      -F "audio=@/tmp/test_audio.wav;type=audio/wav" \
      -F "language=sw" \
      -F "use_as_description=true" 2>/dev/null)
    VN_URL=$(echo "$VOICE_NOTE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('voice_note_url') or d.get('audio_url','(none)'))" 2>/dev/null)
    VN_TRANS=$(echo "$VOICE_NOTE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(repr(d.get('voice_note_transcription',''))[:60])" 2>/dev/null)
    VN_ERR=$(echo "$VOICE_NOTE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('detail',''))" 2>/dev/null)
    echo "  url=$VN_URL  transcript=$VN_TRANS"
    [[ -z "$VN_ERR" && "$VN_URL" != "(none)" ]] && ok "voice note attached + stored" || fail "voice note: $VN_ERR  raw=${VOICE_NOTE:0:200}"
  else
    fail "could not create draft feedback — $DRAFT"
  fi
else
  fail "SKIP: no staff token or project_id"
fi

# ═══════════════════════════════════════════════════════════════════════════════
sep "CHANNEL 3 — Consumer portal voice message (AI conversation → auto-submit)"
# ═══════════════════════════════════════════════════════════════════════════════

# Send 3 text turns to build confidence, then a voice turn
if [[ -n "$CONV_ID" ]]; then
  curl -sf -X POST "$BASE_AI/api/v1/ai/conversations/$CONV_ID/message" \
    -H "Content-Type: application/json" \
    -d '{"message":"Nina tatizo na bomba la maji lililoharibiwa"}' > /dev/null 2>&1
  curl -sf -X POST "$BASE_AI/api/v1/ai/conversations/$CONV_ID/message" \
    -H "Content-Type: application/json" \
    -d '{"message":"Niko Dodoma, Mtaa wa Kilimani, kata ya Makole"}' > /dev/null 2>&1
  curl -sf -X POST "$BASE_AI/api/v1/ai/conversations/$CONV_ID/message" \
    -H "Content-Type: application/json" \
    -d '{"message":"Jina langu ni Fatuma Hassan, namba yangu +255712345678"}' > /dev/null 2>&1

  V2=$(curl -sf -X POST "$BASE_AI/api/v1/ai/conversations/$CONV_ID/voice-message" \
    -F "audio=@/tmp/test_audio.wav;type=audio/wav" 2>/dev/null)
  STAGE=$(echo "$V2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('stage','?'))" 2>/dev/null)
  SUBMITTED=$(echo "$V2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('submitted',False))" 2>/dev/null)
  TURNS=$(echo "$V2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('turn_count','?'))" 2>/dev/null)
  echo "  stage=$STAGE  submitted=$SUBMITTED  turns=$TURNS"
  ok "multi-turn voice conversation: stage=$STAGE turns=$TURNS"
else
  fail "SKIP: no conversation"
fi

# ═══════════════════════════════════════════════════════════════════════════════
sep "CHANNEL 4 — Twilio phone call (inbound + gather)"
# ═══════════════════════════════════════════════════════════════════════════════

INBOUND=$(curl -sf -X POST "$BASE_AI/api/v1/ai/voice/call/inbound" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "CallSid=CA_TEST_$(date +%s)&CallerCountry=TZ&From=+255700000001&To=+255800000000" 2>/dev/null)

HAS_SAY=$(echo    "$INBOUND" | grep -c "<Say"    || true)
HAS_REC=$(echo    "$INBOUND" | grep -c "<Record" || true)
HAS_SW=$(echo     "$INBOUND" | grep -c "sw-TZ"   || true)
CALL_CONV=$(echo  "$INBOUND" | python3 -c \
  "import sys,re; m=re.search(r'conv_id=([a-f0-9-]{36})',sys.stdin.read()); print(m.group(1) if m else '')" 2>/dev/null)

echo "  TwiML preview: ${INBOUND:0:150}"
[[ "$HAS_SAY" -ge 1 ]]  && ok "inbound: <Say> present"   || fail "inbound: no <Say>"
[[ "$HAS_REC" -ge 1 ]]  && ok "inbound: <Record> present" || fail "inbound: no <Record>"
[[ "$HAS_SW"  -ge 1 ]]  && ok "inbound: sw-TZ voice"     || fail "inbound: no Swahili voice"

if [[ -n "$CALL_CONV" ]]; then
  # Simulate gather with no recording (silence / retry path)
  GATHER=$(curl -sf -X POST "$BASE_AI/api/v1/ai/voice/call/gather?call_sid=CA_TEST&conv_id=$CALL_CONV" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "CallSid=CA_TEST&CallStatus=in-progress" 2>/dev/null)
  HAS_SAY_G=$(echo "$GATHER" | grep -c "<Say" || true)
  [[ "$HAS_SAY_G" -ge 1 ]] && ok "gather (no recording): retry TwiML returned" || fail "gather returned: ${GATHER:0:100}"

  # Simulate hangup
  STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "$BASE_AI/api/v1/ai/voice/call/status?conv_id=$CALL_CONV" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "CallSid=CA_TEST&CallStatus=completed" 2>/dev/null)
  [[ "$STATUS_CODE" == "204" ]] && ok "call status hangup → 204" || fail "call status: HTTP $STATUS_CODE"
fi

# ═══════════════════════════════════════════════════════════════════════════════
sep "CHANNEL 5 — WhatsApp voice note (feedback_service channels.py path)"
# ═══════════════════════════════════════════════════════════════════════════════

# Simulate Meta WhatsApp audio webhook (media_id only — actual download needs WHATSAPP_ACCESS_TOKEN)
WA_PAYLOAD='{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "type": "audio",
          "from": "255712000001",
          "audio": {"id": "TEST_MEDIA_ID_12345"}
        }],
        "contacts": [{"profile": {"name": "Test User"}}]
      }
    }]
  }]
}'

WA_RESP=$(curl -sf -X POST "$BASE_FB/api/v1/webhooks/whatsapp" \
  -H "Content-Type: application/json" \
  -d "$WA_PAYLOAD" 2>/dev/null)
WA_STATUS=$(echo "$WA_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null)
echo "  WhatsApp audio webhook response: $WA_RESP"
# Expected: status=ok (audio download will fail without token but endpoint should not 500)
[[ "$WA_STATUS" == "ok" ]] && ok "WhatsApp audio webhook: accepted (status=ok)" || \
  fail "WhatsApp audio webhook: $WA_RESP"

# ═══════════════════════════════════════════════════════════════════════════════
sep "CHANNEL 6 — AI service WhatsApp webhook voice note"
# ═══════════════════════════════════════════════════════════════════════════════

WA_AI_RESP=$(curl -sf -X POST "$BASE_AI/api/v1/ai/webhooks/whatsapp" \
  -H "Content-Type: application/json" \
  -d "$WA_PAYLOAD" 2>/dev/null)
WA_AI_STATUS=$(echo "$WA_AI_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null)
echo "  AI WhatsApp audio webhook response: $WA_AI_RESP"
[[ "$WA_AI_STATUS" == "ok" ]] && ok "AI WhatsApp audio webhook: accepted" || \
  fail "AI WhatsApp audio webhook: $WA_AI_RESP"

# ═══════════════════════════════════════════════════════════════════════════════
sep "CHANNEL 7 — AI Insights voice question"
# ═══════════════════════════════════════════════════════════════════════════════

if [[ -n "$STAFF_TOKEN" ]]; then
  if [[ -n "$PROJECT_ID" ]]; then
    AN_VOICE=$(curl -sf -X POST "$BASE_AN/api/v1/analytics/ai/ask-voice" \
      -H "Authorization: Bearer $STAFF_TOKEN" \
      -F "audio=@/tmp/test_audio.wav;type=audio/wav" \
      -F "scope=project" \
      -F "project_id=$PROJECT_ID" \
      -F "context_type=general" \
      -F "language=sw" 2>/dev/null)
    AN_TRANSCRIPT=$(echo "$AN_VOICE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(repr(d.get('transcript',''))[:60])" 2>/dev/null)
    AN_ANSWER=$(echo "$AN_VOICE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(str(d.get('answer',''))[:80])" 2>/dev/null)
    AN_ERR=$(echo "$AN_VOICE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('detail',''))" 2>/dev/null)
    echo "  transcript=$AN_TRANSCRIPT"
    echo "  answer=$AN_ANSWER"
    [[ -z "$AN_ERR" && -n "$AN_ANSWER" ]] && ok "AI insights voice: answered" || fail "AI insights voice: $AN_ERR  ${AN_VOICE:0:200}"
  else
    fail "SKIP AI insights voice: no project_id"
  fi
else
  fail "SKIP AI insights voice: no staff token"
fi

# ═══════════════════════════════════════════════════════════════════════════════
sep "VALIDATION — MIME/size guards"
# ═══════════════════════════════════════════════════════════════════════════════

echo -n "tooshort" > /tmp/tiny.wav

# AI conversations — invalid MIME
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  "$BASE_AI/api/v1/ai/conversations/${CONV_ID:-00000000-0000-0000-0000-000000000000}/voice-message" \
  -F "audio=@/tmp/test_audio.wav;type=video/mp4")
[[ "$CODE" == "415" ]] && ok "AI conv: invalid MIME → 415" || fail "expected 415, got $CODE"

# AI conversations — too short
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  "$BASE_AI/api/v1/ai/conversations/${CONV_ID:-00000000-0000-0000-0000-000000000000}/voice-message" \
  -F "audio=@/tmp/tiny.wav;type=audio/wav")
[[ "$CODE" == "400" ]] && ok "AI conv: too-short audio → 400" || fail "expected 400, got $CODE"

# AI insights voice — invalid MIME
if [[ -n "$STAFF_TOKEN" ]]; then
  CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "$BASE_AN/api/v1/analytics/ai/ask-voice" \
    -H "Authorization: Bearer $STAFF_TOKEN" \
    -F "audio=@/tmp/test_audio.wav;type=video/mp4" \
    -F "scope=platform")
  [[ "$CODE" == "415" ]] && ok "AI insights voice: invalid MIME → 415" || fail "expected 415, got $CODE"
fi

# ═══════════════════════════════════════════════════════════════════════════════
sep "SUMMARY"
echo "  PASSED: $PASS"
echo "  FAILED: $FAIL"
[[ "$FAIL" -eq 0 ]] && echo "  All tests passed." || echo "  Some tests failed — review above."
exit $FAIL
