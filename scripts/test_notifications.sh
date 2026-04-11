#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Riviwa Notification Service — Complete Endpoint Test Script
#
# Covers every endpoint in notification_service:
#   · Devices          (4 endpoints)
#   · Notifications    (5 endpoints)
#   · Preferences      (3 endpoints)
#   · Internal Dispatch (2 endpoints)
#   · Templates         (3 endpoints)
#   · Webhooks (DLR)    (5 endpoints)
#
# SETUP:
#   1. Get a Bearer token:
#      Run the login flow on 77.237.241.13 then copy the access_token here.
#   2. Set BASE_URL to your server.
#   3. Run: bash scripts/test_notifications.sh
#
# The script runs tests in order, capturing IDs from responses to use in
# later tests (device_id, delivery_id, notification_id, template_id).
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_URL="${BASE_URL:-http://77.237.241.13/api/v1}"
BEARER_TOKEN="${BEARER_TOKEN:-YOUR_ACCESS_TOKEN_HERE}"
SERVICE_KEY="${SERVICE_KEY:-riviwa-internal-secret}"   # INTERNAL_SERVICE_KEY from .env

# Colour helpers
GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
section() { echo -e "\n${CYAN}══════ $1 ══════${NC}"; }

# IDs captured during the run
DEVICE_ID=""
DEVICE_ID_2=""
NOTIFICATION_ID=""
DELIVERY_ID=""
TEMPLATE_ID=""
SCHEDULED_NOTIF_ID=""

# ─────────────────────────────────────────────────────────────────────────────
section "HEALTH CHECK"
# ─────────────────────────────────────────────────────────────────────────────

echo "▶ GET /health"
curl -s "${BASE_URL%/api/v1}/health" | python3 -m json.tool
echo

# ─────────────────────────────────────────────────────────────────────────────
section "1. DEVICES — Register, list, update token, deregister"
# ─────────────────────────────────────────────────────────────────────────────

# 1a. Register FCM device (Android)
echo "▶ POST /devices — Register FCM (Android)"
RESP=$(curl -s -X POST "${BASE_URL}/devices" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "fcm",
    "push_token": "fJdKxMnOpQrStUvWxYz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij",
    "device_name": "Amina Samsung Galaxy A54",
    "app_version": "2.4.1"
  }')
echo "$RESP" | python3 -m json.tool
DEVICE_ID=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")
[ -n "$DEVICE_ID" ] && pass "Device registered: $DEVICE_ID" || fail "Device registration failed"

echo
# 1b. Register APNs device (iOS)
echo "▶ POST /devices — Register APNs (iOS)"
RESP=$(curl -s -X POST "${BASE_URL}/devices" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "apns",
    "push_token": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567890ABCDEF12",
    "device_name": "Joseph iPhone 13",
    "app_version": "2.4.1"
  }')
echo "$RESP" | python3 -m json.tool
DEVICE_ID_2=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")
[ -n "$DEVICE_ID_2" ] && pass "APNs device registered: $DEVICE_ID_2" || fail "APNs device registration failed"

echo
# 1c. List all devices for current user
echo "▶ GET /devices — List my devices"
curl -s "${BASE_URL}/devices" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" | python3 -m json.tool

echo
# 1d. Update push token (token rotation — called after OS refreshes token)
if [ -n "$DEVICE_ID" ]; then
  echo "▶ PATCH /devices/${DEVICE_ID}/token — Rotate push token"
  curl -s -X PATCH "${BASE_URL}/devices/${DEVICE_ID}/token" \
    -H "Authorization: Bearer ${BEARER_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "push_token": "ROTATED_TOKEN_XYZ999888777666555444333222111000aabbccddeeffgghhiijjkkllmm",
      "app_version": "2.4.2"
    }' | python3 -m json.tool
fi

echo
# 1e. Deregister second device (logout on device)
if [ -n "$DEVICE_ID_2" ]; then
  echo "▶ DELETE /devices/${DEVICE_ID_2} — Deregister APNs device"
  curl -s -X DELETE "${BASE_URL}/devices/${DEVICE_ID_2}" \
    -H "Authorization: Bearer ${BEARER_TOKEN}" | python3 -m json.tool
fi

# ─────────────────────────────────────────────────────────────────────────────
section "2. TEMPLATES — Create templates for all notification types"
# ─────────────────────────────────────────────────────────────────────────────

# 2a. Create in_app template for feedback acknowledged
echo "▶ PUT /templates — grm.feedback.acknowledged / in_app / en"
RESP=$(curl -s -X PUT "${BASE_URL}/templates" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "grm.feedback.acknowledged",
    "channel": "in_app",
    "language": "en",
    "title_template": "Your complaint has been received",
    "body_template": "Reference {{ unique_ref }}: Your {{ feedback_type }} about \"{{ subject }}\" was received on {{ submitted_at }}. We will respond within {{ sla_days }} working days.",
    "is_active": true
  }')
echo "$RESP" | python3 -m json.tool
TEMPLATE_ID=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")
[ -n "$TEMPLATE_ID" ] && pass "Template created: $TEMPLATE_ID" || fail "Template creation failed"

echo
# 2b. Swahili in_app template
echo "▶ PUT /templates — grm.feedback.acknowledged / in_app / sw"
curl -s -X PUT "${BASE_URL}/templates" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "grm.feedback.acknowledged",
    "channel": "in_app",
    "language": "sw",
    "title_template": "Malalamiko yako yamepokelewa",
    "body_template": "Kumbukumbu {{ unique_ref }}: {{ feedback_type }} yako kuhusu \"{{ subject }}\" imepokelewa tarehe {{ submitted_at }}. Tutajibu ndani ya siku {{ sla_days }} za kazi.",
    "is_active": true
  }' | python3 -m json.tool

echo
# 2c. SMS template for OTP
echo "▶ PUT /templates — auth.login.otp_requested / sms / en"
curl -s -X PUT "${BASE_URL}/templates" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "auth.login.otp_requested",
    "channel": "sms",
    "language": "en",
    "body_template": "Your Riviwa login code is {{ otp_code }}. Valid for {{ expires_in_minutes }} minutes. Do not share this code.",
    "is_active": true
  }' | python3 -m json.tool

echo
# 2d. WhatsApp template for feedback resolved
echo "▶ PUT /templates — grm.feedback.resolved / whatsapp / en"
curl -s -X PUT "${BASE_URL}/templates" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "grm.feedback.resolved",
    "channel": "whatsapp",
    "language": "en",
    "title_template": "Feedback Resolved — Ref {{ unique_ref }}",
    "body_template": "Hello {{ recipient_name }},\n\nYour {{ feedback_type }} (Ref: *{{ unique_ref }}*) has been resolved.\n\n*Resolution summary:* {{ resolution_summary }}\n\n*Were you satisfied?* Please reply YES or NO.\n\nThank you,\nRiviwa GRM Team",
    "is_active": true
  }' | python3 -m json.tool

echo
# 2e. Email template for grievance escalated
echo "▶ PUT /templates — grm.feedback.escalated / email / en"
curl -s -X PUT "${BASE_URL}/templates" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "grm.feedback.escalated",
    "channel": "email",
    "language": "en",
    "title_template": "Grievance Escalated — Ref {{ unique_ref }}",
    "subject_template": "Your Grievance ({{ unique_ref }}) Has Been Escalated to {{ to_level }}",
    "body_template": "<p>Dear {{ recipient_name }},</p><p>Your grievance <strong>{{ unique_ref }}</strong> regarding \"{{ subject }}\" has been escalated to the <strong>{{ to_level }}</strong> level for further review.</p><p><strong>Reason for escalation:</strong> {{ escalation_reason }}</p><p>You will receive an update within {{ sla_days }} working days.</p><p>Track your complaint at: <a href=\"{{ tracking_url }}\">{{ tracking_url }}</a></p><p>Regards,<br>Riviwa GRM Team</p>",
    "is_active": true
  }' | python3 -m json.tool

echo
# 2f. Push template for payment confirmed
echo "▶ PUT /templates — payment.confirmed / push / en"
curl -s -X PUT "${BASE_URL}/templates" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "payment.confirmed",
    "channel": "push",
    "language": "en",
    "title_template": "Payment Confirmed",
    "body_template": "Your payment of {{ currency }} {{ amount }} for {{ description }} has been confirmed. Transaction ID: {{ transaction_id }}",
    "is_active": true
  }' | python3 -m json.tool

echo
# 2g. System welcome — in_app
echo "▶ PUT /templates — system.welcome / in_app / en"
curl -s -X PUT "${BASE_URL}/templates" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "system.welcome",
    "channel": "in_app",
    "language": "en",
    "title_template": "Welcome to Riviwa!",
    "body_template": "Hi {{ first_name }}, welcome to Riviwa. You can now submit feedback, track grievances, and stay informed about projects in your area.",
    "is_active": true
  }' | python3 -m json.tool

echo
# 2h. Activity reminder — push
echo "▶ PUT /templates — activity.reminder / push / en"
curl -s -X PUT "${BASE_URL}/templates" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "activity.reminder",
    "channel": "push",
    "language": "en",
    "title_template": "Community Meeting Tomorrow",
    "body_template": "Reminder: {{ activity_title }} is scheduled for {{ scheduled_at }} at {{ venue }}. Expected attendees: {{ expected_count }}.",
    "is_active": true
  }' | python3 -m json.tool

echo
# 2i. List templates
echo "▶ GET /templates — list all"
curl -s "${BASE_URL}/templates" \
  -H "X-Service-Key: ${SERVICE_KEY}" | python3 -m json.tool

echo
# 2j. Filter templates by type
echo "▶ GET /templates?notification_type=grm.feedback.acknowledged — filter by type"
curl -s "${BASE_URL}/templates?notification_type=grm.feedback.acknowledged" \
  -H "X-Service-Key: ${SERVICE_KEY}" | python3 -m json.tool

# ─────────────────────────────────────────────────────────────────────────────
section "3. INTERNAL DISPATCH — Simulate notifications from other services"
# ─────────────────────────────────────────────────────────────────────────────

# 3a. Feedback acknowledged — in_app immediate
echo "▶ POST /internal/dispatch — grm.feedback.acknowledged (in_app, immediate)"
RESP=$(curl -s -X POST "${BASE_URL}/internal/dispatch" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"notification_type\": \"grm.feedback.acknowledged\",
    \"recipient_user_id\": \"$(python3 -c "import sys,json,base64; parts=sys.argv[1].split('.'); print(json.loads(base64.b64decode(parts[1]+'==').decode()).get('sub','00000000-0000-0000-0000-000000000001'))" "${BEARER_TOKEN}" 2>/dev/null || echo "00000000-0000-0000-0000-000000000001")\",
    \"language\": \"en\",
    \"preferred_channels\": [\"in_app\"],
    \"priority\": \"medium\",
    \"idempotency_key\": \"test:feedback:ack:$(date +%s)\",
    \"source_service\": \"feedback_service\",
    \"source_entity_id\": \"c1a2b3c4-d5e6-f7a8-b9c0-d1e2f3a4b5c6\",
    \"variables\": {
      \"unique_ref\": \"GRM-2026-00147\",
      \"feedback_type\": \"grievance\",
      \"subject\": \"Road pothole near Sinza Market damaging vehicles\",
      \"submitted_at\": \"2026-04-11\",
      \"sla_days\": \"21\",
      \"recipient_name\": \"Amina Juma\",
      \"project_name\": \"Dar es Salaam Urban Roads Rehabilitation\"
    }
  }")
echo "$RESP" | python3 -m json.tool
NOTIFICATION_ID=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('notification_id',''))" 2>/dev/null || echo "")
[ -n "$NOTIFICATION_ID" ] && pass "Notification dispatched: $NOTIFICATION_ID" || fail "Dispatch failed"

echo
# 3b. OTP — sms (synchronous — used by auth_service)
echo "▶ POST /internal/dispatch — auth.login.otp_requested (sms, critical)"
curl -s -X POST "${BASE_URL}/internal/dispatch" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "auth.login.otp_requested",
    "recipient_phone": "+255712345678",
    "language": "sw",
    "preferred_channels": ["sms"],
    "priority": "critical",
    "idempotency_key": "otp:login:+255712345678:2026041112001",
    "source_service": "riviwa_auth_service",
    "variables": {
      "otp_code": "847293",
      "expires_in_minutes": "5",
      "identifier": "+255712345678"
    }
  }' | python3 -m json.tool

echo
# 3c. Grievance escalated — push + email
echo "▶ POST /internal/dispatch — grm.feedback.escalated (push + email, high)"
curl -s -X POST "${BASE_URL}/internal/dispatch" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"notification_type\": \"grm.feedback.escalated\",
    \"recipient_user_id\": \"$(python3 -c "import sys,json,base64; parts=sys.argv[1].split('.'); print(json.loads(base64.b64decode(parts[1]+'==').decode()).get('sub','00000000-0000-0000-0000-000000000001'))" "${BEARER_TOKEN}" 2>/dev/null || echo "00000000-0000-0000-0000-000000000001")\",
    \"recipient_email\": \"amina.juma@example.com\",
    \"language\": \"en\",
    \"preferred_channels\": [\"push\", \"email\", \"in_app\"],
    \"priority\": \"high\",
    \"idempotency_key\": \"test:feedback:escalated:$(date +%s)\",
    \"source_service\": \"feedback_service\",
    \"source_entity_id\": \"c1a2b3c4-d5e6-f7a8-b9c0-d1e2f3a4b5c6\",
    \"variables\": {
      \"unique_ref\": \"GRM-2026-00147\",
      \"feedback_type\": \"grievance\",
      \"subject\": \"Road pothole near Sinza Market\",
      \"to_level\": \"LGA PIU\",
      \"escalation_reason\": \"No response from ward committee after 14 days\",
      \"sla_days\": \"14\",
      \"recipient_name\": \"Amina Juma\",
      \"tracking_url\": \"https://riviwa.com/track/GRM-2026-00147\"
    }
  }" | python3 -m json.tool

echo
# 3d. Payment confirmed — push
echo "▶ POST /internal/dispatch — payment.confirmed (push, high)"
curl -s -X POST "${BASE_URL}/internal/dispatch" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"notification_type\": \"payment.confirmed\",
    \"recipient_user_id\": \"$(python3 -c "import sys,json,base64; parts=sys.argv[1].split('.'); print(json.loads(base64.b64decode(parts[1]+'==').decode()).get('sub','00000000-0000-0000-0000-000000000001'))" "${BEARER_TOKEN}" 2>/dev/null || echo "00000000-0000-0000-0000-000000000001")\",
    \"language\": \"en\",
    \"preferred_channels\": [\"push\", \"in_app\"],
    \"priority\": \"high\",
    \"idempotency_key\": \"test:payment:confirmed:$(date +%s)\",
    \"source_service\": \"payment_service\",
    \"source_entity_id\": \"pay-uuid-abc123\",
    \"variables\": {
      \"currency\": \"TZS\",
      \"amount\": \"50,000\",
      \"description\": \"GRM project contribution\",
      \"transaction_id\": \"TXN-2026-00892\",
      \"recipient_name\": \"Joseph Makundi\"
    }
  }" | python3 -m json.tool

echo
# 3e. Activity reminder — scheduled for 24 hours from now
SCHED_AT=$(python3 -c "from datetime import datetime, timezone, timedelta; print((datetime.now(timezone.utc)+timedelta(hours=24)).isoformat())")
echo "▶ POST /internal/dispatch — activity.reminder (push, scheduled for 24h from now)"
RESP=$(curl -s -X POST "${BASE_URL}/internal/dispatch" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"notification_type\": \"activity.reminder\",
    \"recipient_user_id\": \"$(python3 -c "import sys,json,base64; parts=sys.argv[1].split('.'); print(json.loads(base64.b64decode(parts[1]+'==').decode()).get('sub','00000000-0000-0000-0000-000000000001'))" "${BEARER_TOKEN}" 2>/dev/null || echo "00000000-0000-0000-0000-000000000001")\",
    \"language\": \"en\",
    \"preferred_channels\": [\"push\"],
    \"priority\": \"medium\",
    \"idempotency_key\": \"test:activity:reminder:$(date +%s)\",
    \"scheduled_at\": \"${SCHED_AT}\",
    \"source_service\": \"stakeholder_service\",
    \"variables\": {
      \"activity_title\": \"Community Consultation — Msimbazi River Project\",
      \"scheduled_at\": \"2026-04-12 10:00 AM\",
      \"venue\": \"Kinondoni District Commissioner's Hall\",
      \"expected_count\": \"120\",
      \"project_name\": \"Msimbazi River Basin Development\"
    }
  }")
echo "$RESP" | python3 -m json.tool
SCHEDULED_NOTIF_ID=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('notification_id',''))" 2>/dev/null || echo "")
[ -n "$SCHEDULED_NOTIF_ID" ] && pass "Scheduled notification: $SCHEDULED_NOTIF_ID" || fail "Scheduled dispatch failed"

echo
# 3f. System welcome — multi-channel
echo "▶ POST /internal/dispatch — system.welcome (in_app + push, medium)"
curl -s -X POST "${BASE_URL}/internal/dispatch" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"notification_type\": \"system.welcome\",
    \"recipient_user_id\": \"$(python3 -c "import sys,json,base64; parts=sys.argv[1].split('.'); print(json.loads(base64.b64decode(parts[1]+'==').decode()).get('sub','00000000-0000-0000-0000-000000000001'))" "${BEARER_TOKEN}" 2>/dev/null || echo "00000000-0000-0000-0000-000000000001")\",
    \"language\": \"en\",
    \"preferred_channels\": [\"in_app\", \"push\"],
    \"priority\": \"low\",
    \"idempotency_key\": \"test:welcome:$(date +%s)\",
    \"source_service\": \"riviwa_auth_service\",
    \"variables\": {
      \"first_name\": \"Amina\",
      \"full_name\": \"Amina Juma\",
      \"email\": \"amina@example.com\"
    }
  }" | python3 -m json.tool

echo
# 3g. Batch dispatch — notify multiple recipients
echo "▶ POST /internal/dispatch/batch — batch (2 project activation notifications)"
curl -s -X POST "${BASE_URL}/internal/dispatch/batch" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "[
    {
      \"notification_type\": \"project.activated\",
      \"recipient_user_id\": \"00000000-0000-0000-0000-000000000001\",
      \"language\": \"en\",
      \"preferred_channels\": [\"in_app\"],
      \"priority\": \"medium\",
      \"idempotency_key\": \"test:batch:proj:act:user1:$(date +%s)\",
      \"source_service\": \"riviwa_auth_service\",
      \"variables\": {
        \"project_name\": \"Dar es Salaam Roads Phase III\",
        \"org_name\": \"TANROADS\",
        \"activated_by\": \"John Doe\"
      }
    },
    {
      \"notification_type\": \"project.activated\",
      \"recipient_user_id\": \"00000000-0000-0000-0000-000000000002\",
      \"language\": \"sw\",
      \"preferred_channels\": [\"in_app\"],
      \"priority\": \"medium\",
      \"idempotency_key\": \"test:batch:proj:act:user2:$(date +%s)\",
      \"source_service\": \"riviwa_auth_service\",
      \"variables\": {
        \"project_name\": \"Dar es Salaam Roads Phase III\",
        \"org_name\": \"TANROADS\",
        \"activated_by\": \"John Doe\"
      }
    }
  ]" | python3 -m json.tool

# ─────────────────────────────────────────────────────────────────────────────
section "4. NOTIFICATION INBOX — Get, count, mark read"
# ─────────────────────────────────────────────────────────────────────────────

echo
# 4a. Get unread count (badge)
echo "▶ GET /notifications/unread-count"
curl -s "${BASE_URL}/notifications/unread-count" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" | python3 -m json.tool

echo
# 4b. Get full inbox
echo "▶ GET /notifications — full inbox"
RESP=$(curl -s "${BASE_URL}/notifications?skip=0&limit=10" \
  -H "Authorization: Bearer ${BEARER_TOKEN}")
echo "$RESP" | python3 -m json.tool
DELIVERY_ID=$(echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('items', [])
print(items[0]['delivery_id'] if items else '')
" 2>/dev/null || echo "")
[ -n "$DELIVERY_ID" ] && pass "Got delivery_id: $DELIVERY_ID" || echo "(no items yet — templates may not match)"

echo
# 4c. Unread only
echo "▶ GET /notifications?unread_only=true"
curl -s "${BASE_URL}/notifications?unread_only=true&limit=5" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" | python3 -m json.tool

echo
# 4d. Mark single delivery as read
if [ -n "$DELIVERY_ID" ]; then
  echo "▶ PATCH /notifications/deliveries/${DELIVERY_ID}/read"
  curl -s -X PATCH "${BASE_URL}/notifications/deliveries/${DELIVERY_ID}/read" \
    -H "Authorization: Bearer ${BEARER_TOKEN}" | python3 -m json.tool
else
  echo "(skipping mark-read — no delivery_id captured)"
fi

echo
# 4e. Mark all as read
echo "▶ POST /notifications/mark-all-read"
curl -s -X POST "${BASE_URL}/notifications/mark-all-read" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" | python3 -m json.tool

echo
# 4f. Cancel a scheduled notification
if [ -n "$SCHEDULED_NOTIF_ID" ]; then
  echo "▶ DELETE /notifications/${SCHEDULED_NOTIF_ID} — cancel scheduled"
  curl -s -X DELETE "${BASE_URL}/notifications/${SCHEDULED_NOTIF_ID}" \
    -H "Authorization: Bearer ${BEARER_TOKEN}" | python3 -m json.tool
else
  echo "(skipping cancel — no scheduled notification_id captured)"
fi

# ─────────────────────────────────────────────────────────────────────────────
section "5. PREFERENCES — Opt-out and opt back in"
# ─────────────────────────────────────────────────────────────────────────────

echo
# 5a. Get all preferences (empty by default = all enabled)
echo "▶ GET /notification-preferences"
curl -s "${BASE_URL}/notification-preferences" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" | python3 -m json.tool

echo
# 5b. Disable all GRM notifications on WhatsApp (wildcard)
echo "▶ PUT /notification-preferences — disable grm.* on whatsapp"
curl -s -X PUT "${BASE_URL}/notification-preferences" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "grm.*",
    "channel": "whatsapp",
    "enabled": false
  }' | python3 -m json.tool

echo
# 5c. Disable SMS for low-priority activity reminders specifically
echo "▶ PUT /notification-preferences — disable activity.reminder on sms"
curl -s -X PUT "${BASE_URL}/notification-preferences" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "activity.reminder",
    "channel": "sms",
    "enabled": false
  }' | python3 -m json.tool

echo
# 5d. Disable email for project lifecycle notifications
echo "▶ PUT /notification-preferences — disable project.* on email"
curl -s -X PUT "${BASE_URL}/notification-preferences" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "project.*",
    "channel": "email",
    "enabled": false
  }' | python3 -m json.tool

echo
# 5e. Keep push enabled for payment notifications (explicit opt-in)
echo "▶ PUT /notification-preferences — enable payment.* on push (explicit opt-in)"
curl -s -X PUT "${BASE_URL}/notification-preferences" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "payment.*",
    "channel": "push",
    "enabled": true
  }' | python3 -m json.tool

echo
# 5f. View updated preferences
echo "▶ GET /notification-preferences — after updates"
curl -s "${BASE_URL}/notification-preferences" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" | python3 -m json.tool

echo
# 5g. Reset (delete) one preference back to default
echo "▶ DELETE /notification-preferences/activity.reminder/sms — reset to default"
curl -s -X DELETE "${BASE_URL}/notification-preferences/activity.reminder/sms" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" | python3 -m json.tool

# ─────────────────────────────────────────────────────────────────────────────
section "6. PROVIDER DLR WEBHOOKS — Simulate delivery confirmations"
# ─────────────────────────────────────────────────────────────────────────────

# 6a. Africa's Talking SMS DLR
echo "▶ POST /webhooks/sms/at/dlr — Africa's Talking delivery receipt"
curl -s -X POST "${BASE_URL}/webhooks/sms/at/dlr" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "messageId=ATXid_sample123456&status=Success&phoneNumber=%2B255712345678&networkCode=62002" \
  | python3 -m json.tool 2>/dev/null || echo "(response may not be JSON)"

echo
# 6b. Africa's Talking — failed delivery
echo "▶ POST /webhooks/sms/at/dlr — Africa's Talking failed delivery"
curl -s -X POST "${BASE_URL}/webhooks/sms/at/dlr" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "messageId=ATXid_failed789&status=Failed&phoneNumber=%2B255787654321&networkCode=62001" \
  | python3 -m json.tool 2>/dev/null || echo "(no JSON)"

echo
# 6c. Twilio SMS DLR
echo "▶ POST /webhooks/sms/twilio/dlr — Twilio delivery receipt"
curl -s -X POST "${BASE_URL}/webhooks/sms/twilio/dlr" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "MessageSid=SM123456789abcdef&MessageStatus=delivered" \
  | python3 -m json.tool 2>/dev/null || echo "(may return empty)"

echo
# 6d. SendGrid email webhook (batch of events)
echo "▶ POST /webhooks/email/sendgrid — SendGrid event webhook"
curl -s -X POST "${BASE_URL}/webhooks/email/sendgrid" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "event": "delivered",
      "sg_message_id": "sendgrid-msg-id-abc123",
      "email": "amina.juma@example.com",
      "timestamp": 1744364400,
      "smtp-id": "<abc123.sendgrid.net>"
    },
    {
      "event": "open",
      "sg_message_id": "sendgrid-msg-id-abc123",
      "email": "amina.juma@example.com",
      "timestamp": 1744364500,
      "useragent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"
    },
    {
      "event": "bounce",
      "sg_message_id": "sendgrid-msg-id-def456",
      "email": "bad-address@invalid.domain",
      "timestamp": 1744364600,
      "reason": "550 5.1.1 The email account that you tried to reach does not exist",
      "type": "bounce"
    }
  ]' | python3 -m json.tool

echo
# 6e. Meta WhatsApp status webhook
echo "▶ POST /webhooks/whatsapp/meta — WhatsApp delivery status"
curl -s -X POST "${BASE_URL}/webhooks/whatsapp/meta" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
      "changes": [{
        "value": {
          "messaging_product": "whatsapp",
          "metadata": {
            "display_phone_number": "255712345678",
            "phone_number_id": "PHONE_NUMBER_ID"
          },
          "statuses": [{
            "id": "wamid.HBgMKzI1NTcxMjM0NTY3NhUCABIYFjNFQjBDNTYwNkI3QkE2NzExODkwNwA=",
            "status": "delivered",
            "timestamp": "1744364400",
            "recipient_id": "255712345678",
            "conversation": {
              "id": "CONVERSATION_ID",
              "expiration_timestamp": "1744450800",
              "origin": {"type": "utility"}
            },
            "pricing": {
              "billable": true,
              "pricing_model": "CBP",
              "category": "utility"
            }
          }]
        },
        "field": "messages"
      }]
    }]
  }' | python3 -m json.tool

echo
# 6f. Meta WhatsApp "read" status
echo "▶ POST /webhooks/whatsapp/meta — WhatsApp read receipt"
curl -s -X POST "${BASE_URL}/webhooks/whatsapp/meta" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
      "changes": [{
        "value": {
          "messaging_product": "whatsapp",
          "statuses": [{
            "id": "wamid.HBgMKzI1NTcxMjM0NTY3NhUCABIYFjNFQjBDNTYwNkI3QkE2NzExODkwNwA=",
            "status": "read",
            "timestamp": "1744364800",
            "recipient_id": "255712345678"
          }]
        },
        "field": "messages"
      }]
    }]
  }' | python3 -m json.tool

echo
# 6g. Meta WhatsApp hub verification
echo "▶ GET /webhooks/whatsapp/meta — hub.challenge verification"
curl -sv "${BASE_URL}/webhooks/whatsapp/meta?hub.mode=subscribe&hub.verify_token=riviwa_meta_webhook_token&hub.challenge=1234567890" 2>&1 | grep -E "< HTTP|^1234"

# ─────────────────────────────────────────────────────────────────────────────
section "7. TEMPLATE MANAGEMENT — Update and delete"
# ─────────────────────────────────────────────────────────────────────────────

echo
# 7a. Update template body (e.g. after copy review)
if [ -n "$TEMPLATE_ID" ]; then
  echo "▶ PUT /templates — update grm.feedback.acknowledged/in_app/en body"
  curl -s -X PUT "${BASE_URL}/templates" \
    -H "X-Service-Key: ${SERVICE_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "notification_type": "grm.feedback.acknowledged",
      "channel": "in_app",
      "language": "en",
      "title_template": "Your feedback has been received ✓",
      "body_template": "Ref {{ unique_ref }}: Your {{ feedback_type }} about \"{{ subject }}\" was logged on {{ submitted_at }}. Expected response: {{ sla_days }} working days. Thank you.",
      "is_active": true
    }' | python3 -m json.tool
fi

echo
# 7b. Deactivate a template (without deleting — channel will be skipped)
echo "▶ PUT /templates — deactivate activity.reminder/push/en"
curl -s -X PUT "${BASE_URL}/templates" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "activity.reminder",
    "channel": "push",
    "language": "en",
    "title_template": "Community Meeting Tomorrow",
    "body_template": "Reminder: {{ activity_title }} at {{ venue }} on {{ scheduled_at }}.",
    "is_active": false
  }' | python3 -m json.tool

echo
# 7c. Delete template
if [ -n "$TEMPLATE_ID" ]; then
  echo "▶ DELETE /templates/${TEMPLATE_ID}"
  curl -s -X DELETE "${BASE_URL}/templates/${TEMPLATE_ID}" \
    -H "X-Service-Key: ${SERVICE_KEY}" | python3 -m json.tool
fi

# ─────────────────────────────────────────────────────────────────────────────
section "8. EDGE CASES & VALIDATION"
# ─────────────────────────────────────────────────────────────────────────────

echo
# 8a. Invalid priority → 422
echo "▶ POST /internal/dispatch — invalid priority (expect 422)"
curl -s -X POST "${BASE_URL}/internal/dispatch" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "system.welcome",
    "recipient_user_id": "00000000-0000-0000-0000-000000000001",
    "priority": "urgent",
    "variables": {}
  }' | python3 -m json.tool

echo
# 8b. Invalid channel → 422
echo "▶ PUT /notification-preferences — invalid channel (expect 422)"
curl -s -X PUT "${BASE_URL}/notification-preferences" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "grm.*",
    "channel": "telegram",
    "enabled": false
  }' | python3 -m json.tool

echo
# 8c. Missing service key → 403
echo "▶ POST /internal/dispatch — missing X-Service-Key (expect 403)"
curl -s -X POST "${BASE_URL}/internal/dispatch" \
  -H "Content-Type: application/json" \
  -d '{"notification_type": "system.welcome", "variables": {}}' \
  | python3 -m json.tool

echo
# 8d. Idempotency — send same notification twice, should get same notification_id
IDEM_KEY="test:idempotency:$(date +%s)"
PAYLOAD="{
  \"notification_type\": \"system.welcome\",
  \"recipient_user_id\": \"00000000-0000-0000-0000-000000000001\",
  \"language\": \"en\",
  \"preferred_channels\": [\"in_app\"],
  \"priority\": \"low\",
  \"idempotency_key\": \"${IDEM_KEY}\",
  \"variables\": {\"first_name\": \"Test\"}
}"
echo "▶ POST /internal/dispatch — first send (idempotency key: ${IDEM_KEY})"
FIRST=$(curl -s -X POST "${BASE_URL}/internal/dispatch" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$FIRST" | python3 -m json.tool
echo "▶ POST /internal/dispatch — second send (same idempotency key — should return same notification_id)"
SECOND=$(curl -s -X POST "${BASE_URL}/internal/dispatch" \
  -H "X-Service-Key: ${SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$SECOND" | python3 -m json.tool
FIRST_ID=$(echo "$FIRST" | python3 -c "import sys,json; print(json.load(sys.stdin).get('notification_id',''))" 2>/dev/null || echo "")
SECOND_ID=$(echo "$SECOND" | python3 -c "import sys,json; print(json.load(sys.stdin).get('notification_id',''))" 2>/dev/null || echo "")
[ "$FIRST_ID" = "$SECOND_ID" ] && [ -n "$FIRST_ID" ] && pass "Idempotency OK — same notification_id: $FIRST_ID" || fail "Idempotency FAILED: $FIRST_ID vs $SECOND_ID"

echo
# 8e. Unauthenticated inbox request → 401
echo "▶ GET /notifications — no Bearer token (expect 401)"
curl -s "${BASE_URL}/notifications" | python3 -m json.tool

echo
# 8f. Register device with invalid platform → 422
echo "▶ POST /devices — invalid platform (expect 422)"
curl -s -X POST "${BASE_URL}/devices" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "gcm",
    "push_token": "some-token"
  }' | python3 -m json.tool

echo
echo -e "\n${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Notification service test run complete.               ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
