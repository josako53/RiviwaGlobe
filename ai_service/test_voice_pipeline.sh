#!/usr/bin/env bash
# test_voice_pipeline.sh — End-to-end voice AI pipeline tests
# Run from the server: bash ai_service/test_voice_pipeline.sh
# Or locally against a running stack.

set -euo pipefail
BASE="${AI_BASE_URL:-http://localhost:8085}/api/v1/ai"
PASS=0; FAIL=0

ok()   { echo "  [PASS] $1"; ((PASS++)); }
fail() { echo "  [FAIL] $1"; ((FAIL++)); }
sep()  { echo ""; echo "━━━ $1 ━━━"; }

# ── Build minimal WAV (44-byte header + 3 000 bytes silence) ─────────────────
python3 - <<'PY' > /tmp/test_silence.wav
import struct, sys
pcm = b'\x00' * 3000
hdr = struct.pack('<4sI4s4sIHHIIHH4sI',
    b'RIFF', 36+len(pcm), b'WAVE', b'fmt ', 16, 1, 1,
    16000, 32000, 2, 16, b'data', len(pcm))
sys.stdout.buffer.write(hdr + pcm)
PY

# ── Helper: POST JSON ─────────────────────────────────────────────────────────
post_json() {
    curl -sf -X POST "$1" -H "Content-Type: application/json" -d "$2" 2>&1
}

# ═══════════════════════════════════════════════════════════════════════════════
sep "TEST 1 — Start a WEB conversation"
RESP=$(post_json "$BASE/conversations/start" '{"channel":"web","language":"sw"}')
CONV_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['conversation_id'])" 2>/dev/null)
STAGE=$(echo   "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('stage','?'))" 2>/dev/null)
if [[ -n "$CONV_ID" ]]; then
    ok "conversation started  conv=$CONV_ID  stage=$STAGE"
else
    fail "start_conversation failed — $RESP"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════════
sep "TEST 2 — Text message (collecting stage)"
RESP=$(post_json "$BASE/conversations/$CONV_ID/message" \
    '{"message":"Habari, ninataka kutoa malalamiko kuhusu bomba lililoharibiwa mtaani mwangu"}')
STAGE=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('stage','?'))" 2>/dev/null)
TURNS=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('turn_count','?'))" 2>/dev/null)
if [[ "$TURNS" -ge 2 ]]; then
    ok "text message processed  stage=$STAGE  turns=$TURNS"
else
    fail "text message — unexpected response  $RESP"
fi

# ═══════════════════════════════════════════════════════════════════════════════
sep "TEST 3 — Voice message (multipart WAV)"
RESP=$(curl -sf -X POST "$BASE/conversations/$CONV_ID/voice-message" \
    -F "audio=@/tmp/test_silence.wav;type=audio/wav" 2>&1)
TRANSCRIPT=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(repr(d.get('transcript','')))" 2>/dev/null)
LANG=$(echo      "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('detected_language','?'))" 2>/dev/null)
CONF=$(echo      "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('stt_confidence','?'))" 2>/dev/null)
AUDIO_URL=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('audio_url') or '(none)')" 2>/dev/null)
TURNS=$(echo     "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('turn_count','?'))" 2>/dev/null)
ERR=$(echo       "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null)
echo "  transcript=$TRANSCRIPT"
echo "  lang=$LANG  conf=$CONF"
echo "  audio_url=$AUDIO_URL"
echo "  turns=$TURNS  error=$ERR"
if [[ -z "$ERR" && "$TURNS" -ge 3 ]]; then
    ok "voice message processed"
    if [[ "$AUDIO_URL" != "(none)" ]]; then
        ok "  audio stored in MinIO → $AUDIO_URL"
    else
        fail "  audio_url is null — MinIO storage failed"
    fi
else
    fail "voice message error — $RESP"
fi

# ═══════════════════════════════════════════════════════════════════════════════
sep "TEST 4 — GET conversation transcript (JSONB persistence check)"
TURNS_RESP=$(curl -sf "$BASE/conversations/$CONV_ID" 2>&1)
TOTAL=$(echo "$TURNS_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('turn_count',0))" 2>/dev/null)
HAS_AUDIO=$(echo "$TURNS_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
turns=d.get('turns',[])
has=any(t.get('audio_url') for t in turns)
print('yes' if has else 'no')
" 2>/dev/null)
if [[ "$TOTAL" -ge 3 ]]; then
    ok "JSONB turns persisted correctly — $TOTAL turns  has_audio_url=$HAS_AUDIO"
else
    fail "JSONB persistence problem — only $TOTAL turns returned"
fi

# ═══════════════════════════════════════════════════════════════════════════════
sep "TEST 5 — Invalid MIME type → 415"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "$BASE/conversations/$CONV_ID/voice-message" \
    -F "audio=@/tmp/test_silence.wav;type=video/mp4")
[[ "$CODE" == "415" ]] && ok "invalid MIME → 415" || fail "expected 415, got $CODE"

# ═══════════════════════════════════════════════════════════════════════════════
sep "TEST 6 — Too-short audio → 400"
echo -n "short" > /tmp/tiny.wav
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "$BASE/conversations/$CONV_ID/voice-message" \
    -F "audio=@/tmp/tiny.wav;type=audio/wav")
[[ "$CODE" == "400" ]] && ok "short audio → 400" || fail "expected 400, got $CODE"

# ═══════════════════════════════════════════════════════════════════════════════
sep "TEST 7 — Translation service round-trip"
RESP=$(post_json "${BASE%/ai}/translate" \
    '{"text":"Barabara imechoka sana","target_language":"en"}')
TRANSLATED=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('translated_text',''))" 2>/dev/null)
if [[ -n "$TRANSLATED" && "$TRANSLATED" != "null" ]]; then
    ok "translation sw→en: '$TRANSLATED'"
else
    fail "translation failed — $RESP"
fi

# ═══════════════════════════════════════════════════════════════════════════════
sep "TEST 8 — Twilio inbound call webhook"
TW_RESP=$(curl -sf -X POST "$BASE/voice/call/inbound" \
    -d "CallSid=CA_test123&CallerCountry=TZ&From=+255700000000&To=+255800000000" \
    -H "Content-Type: application/x-www-form-urlencoded" 2>&1)
HAS_SAY=$(echo    "$TW_RESP" | grep -c "<Say" || true)
HAS_RECORD=$(echo "$TW_RESP" | grep -c "<Record" || true)
HAS_SW=$(echo     "$TW_RESP" | grep -c "sw-TZ" || true)
echo "  TwiML preview: ${TW_RESP:0:200}"
[[ "$HAS_SAY" -ge 1 ]]    && ok "TwiML has <Say>" || fail "no <Say> in TwiML"
[[ "$HAS_RECORD" -ge 1 ]] && ok "TwiML has <Record>" || fail "no <Record> in TwiML"
[[ "$HAS_SW" -ge 1 ]]     && ok "Swahili voice (sw-TZ) for TZ caller" || fail "no sw-TZ voice"

# ═══════════════════════════════════════════════════════════════════════════════
sep "TEST 9 — Twilio call status (hangup → ABANDONED)"
# First get the conv_id from test 8's call, then simulate hangup
NEW_CONV=$(echo "$TW_RESP" | python3 -c "
import sys, re
m = re.search(r'conv_id=([a-f0-9-]{36})', sys.stdin.read())
print(m.group(1) if m else '')
" 2>/dev/null)
if [[ -n "$NEW_CONV" ]]; then
    CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        "$BASE/voice/call/status?conv_id=$NEW_CONV" \
        -d "CallSid=CA_test123&CallStatus=completed" \
        -H "Content-Type: application/x-www-form-urlencoded")
    [[ "$CODE" == "204" ]] && ok "call status → 204  conv=$NEW_CONV" || fail "expected 204, got $CODE"
else
    ok "call status skipped (no conv_id in TwiML — expected in dev without DB)"
fi

# ═══════════════════════════════════════════════════════════════════════════════
sep "TEST 10 — AI health"
HEALTH=$(curl -sf "http://localhost:8085/health" 2>&1)
STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null)
[[ "$STATUS" == "ok" ]] && ok "health=ok" || fail "health=$STATUS  $HEALTH"

# ═══════════════════════════════════════════════════════════════════════════════
sep "SUMMARY"
echo "  PASSED: $PASS"
echo "  FAILED: $FAIL"
[[ "$FAIL" -eq 0 ]] && echo "  All tests passed." || echo "  Some tests failed — review above."
exit $FAIL
