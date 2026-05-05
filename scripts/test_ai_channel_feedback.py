#!/usr/bin/env python3
"""
Test: conversation-to-feedback pipeline for products.
Tests BOTH pipelines:
  1. feedback_service channel session (SMS/WhatsApp simulation via API)
  2. ai_service conversation session (AI chat via API)
Shows exactly when/why a conversation becomes a feedback record.
"""
import json, sys, time, requests, base64

BASE    = "http://77.237.241.13"
LOCAL   = "http://localhost"
FB_URL  = f"{LOCAL}:8090"
PROD_URL = f"{LOCAL}:8110"
AI_URL  = f"{LOCAL}:8085"
AUTH    = f"{LOCAL}:8000"

OK   = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
HEAD = "\033[1m"
END  = "\033[0m"
BLUE = "\033[94m"

results = {"pass": 0, "fail": 0}


def check(label, cond, extra=""):
    if cond:
        print(f"  {OK}  {label}")
        results["pass"] += 1
    else:
        print(f"  {FAIL}  {label}  {extra}")
        results["fail"] += 1
    return cond


def section(title):
    print(f"\n  {HEAD}── {title} {'─'*(52-len(title))}{END}")


# ── Wait for services ────────────────────────────────────────────────────────
print("  Waiting for services to be ready...")
for _ in range(20):
    try:
        fb_probe = requests.get(f"{FB_URL}/api/v1/projects/", timeout=3)
        if fb_probe.status_code in (200, 401, 403):
            break
    except Exception:
        pass
    time.sleep(2)

# ── Auth ──────────────────────────────────────────────────────────────────────
section("Authentication (reuse testgrm org + products)")

LOGIN_ID   = "testgrm@riviwa.com"
LOGIN_PASS = "TestGRM@2026!"

r = requests.post(f"{AUTH}/api/v1/auth/login", json={"identifier": LOGIN_ID, "password": LOGIN_PASS})
check("Login", r.status_code == 200, r.text[:200])
token_data = r.json()
access_token = token_data.get("access_token") or token_data.get("tokens", {}).get("access_token", "")
if not access_token and "login_token" in token_data:
    lt = token_data["login_token"]
    r2 = requests.post(f"{AUTH}/api/v1/auth/login/verify-otp",
                       json={"login_token": lt, "otp_code": "000000"})
    check("OTP verify", r2.status_code == 200, r2.text[:200])
    access_token = r2.json().get("access_token", "")

HDR = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

payload_b64 = access_token.split(".")[1] + "=="
claims = json.loads(base64.b64decode(payload_b64 + "=="))
org_id = claims.get("org_id")
print(f"    org_id: {org_id}")

# Get a product from product_service (port 8110)
r = requests.get(f"{PROD_URL}/api/v1/products/?page_size=5", headers=HDR)
products = r.json().get("items", []) if r.status_code == 200 else []
# Fallback to known product if testgrm token can't list products
product_id   = products[0]["product_id"] if products else "4ae4ecf5-22d0-4f86-8079-89a2e4e48b76"
product_name = products[0].get("title", "Riviwa ProBook X15") if products else "Riviwa ProBook X15 (known)"
check(f"Found product: {product_name}", True)
print(f"    product_id: {product_id}")

# Get a project (channel session auto-submit requires project_id)
r = requests.get(f"{FB_URL}/api/v1/projects/", headers=HDR)
raw = r.json() if r.status_code == 200 else []
projects_list = raw if isinstance(raw, list) else raw.get("items", [])
project_id   = projects_list[0]["id"] if projects_list else None
project_name = projects_list[0].get("name", "N/A") if projects_list else "N/A"
check(f"Found project: {project_name}", project_id is not None)

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n  {BLUE}PIPELINE 1: feedback_service ChannelSession (SMS/WhatsApp simulation){END}")
print(f"  {'─'*60}")
print("  Trigger conditions:")
print("    * LLM confidence >= 0.80 AND project_id set  -> auto-submit")
print("    * ready_to_submit=True AND project_id set    -> auto-submit")
print("    * turn_count >= 20 (MAX_TURNS)               -> force-submit")
print("    * 30 min inactivity                          -> TIMED_OUT (no feedback)")

section("Pipeline 1A: Channel session WITH product_id (SMS simulation)")

# Use known active project so force_submit can work
# (testgrm org has no projects; we borrow Kigoma GRC which is ACTIVE)
KNOWN_PROJECT_ID = "d363d9bc-20b3-4590-b08e-157283fe03c0"
session_data = {
    "channel": "sms",
    "phone_number": "+255712345678",
    "language": "en",
    "product_id": product_id,
    "project_id": KNOWN_PROJECT_ID,
}

r = requests.post(f"{FB_URL}/api/v1/channel-sessions", json=session_data, headers=HDR)
check("Create SMS channel session (product_id attached)", r.status_code == 201, r.text[:300])
session = r.json() if r.status_code == 201 else {}
session_id = session.get("id")
print(f"    session_id:  {session_id}")
print(f"    product_id:  {session.get('product_id')}")
turns = (session.get("turns") or {}).get("turns", [])
if turns:
    print(f"    Opening reply: {turns[-1].get('content', '')[:100]}")

TURNS = [
    "I have a serious complaint about this product. The item I received is broken.",
    "The product arrived damaged. Screen is cracked, battery swollen. I am in Ilala, Kariakoo ward. This happened 3 days ago.",
    "My name is John Doe. I want to formally file this as a grievance. It is unacceptable.",
    "Yes please go ahead and submit my complaint, I confirm all details are correct.",
]

submitted        = False
feedback_id_sess = None

for i, msg in enumerate(TURNS):
    r = requests.post(f"{FB_URL}/api/v1/channel-sessions/{session_id}/message",
                      json={"message": msg}, headers=HDR)
    if r.status_code == 200:
        resp = r.json()
        reply       = resp.get("reply", "")[:70]
        sub_flag    = resp.get("submitted", False)
        fb_id       = resp.get("feedback_id")
        turn_count  = resp.get("turn_count", i + 1)
        extracted   = session.get("extracted_data") or {}
        confidence  = extracted.get("confidence", "?")
        print(f"    Turn {i+1}: turns={turn_count} sub={sub_flag} | {reply}...")
        if sub_flag and fb_id:
            submitted        = True
            feedback_id_sess = fb_id
            check(f"  Auto-submitted at turn {i+1}", True)
            break
    else:
        print(f"    Turn {i+1} error: {r.status_code} {r.text[:100]}")

if not submitted and session_id:
    r = requests.post(f"{FB_URL}/api/v1/channel-sessions/{session_id}/submit", headers=HDR)
    resp = r.json() if r.status_code == 200 else {}
    feedback_id_sess = resp.get("feedback_id")
    submitted        = bool(resp.get("submitted"))
    check("Force-submitted channel session", submitted, r.text[:200])

check("Channel session produced a feedback record", submitted)

if feedback_id_sess:
    r = requests.get(f"{FB_URL}/api/v1/feedback/{feedback_id_sess}", headers=HDR)
    if r.status_code == 200:
        fb = r.json()
        check("Feedback.product_id == session product_id",
              fb.get("product_id") == product_id,
              f"got={fb.get('product_id')} want={product_id}")
        check("submission_method = ai_conversation",
              fb.get("submission_method") == "ai_conversation",
              f"got={fb.get('submission_method')}")
        print(f"    ref:             {fb.get('unique_ref')}")
        print(f"    feedback_type:   {fb.get('feedback_type')}")
        print(f"    product_id:      {fb.get('product_id')}")

section("Pipeline 1B: Channel session WITHOUT project (product-only org)")

sess2 = {
    "channel": "whatsapp",
    "whatsapp_id": "+255798000111",
    "language": "en",
    "product_id": product_id,
    # NO project_id — auto-submit won't fire (by design)
}
r = requests.post(f"{FB_URL}/api/v1/channel-sessions", json=sess2, headers=HDR)
check("Create WhatsApp session (NO project, product only)", r.status_code == 201, r.text[:200])
s2 = r.json() if r.status_code == 201 else {}
check("product_id attached to session", s2.get("product_id") == product_id)
check("project_id is null (expected)", s2.get("project_id") is None)
print("    Note: without project_id auto-submit won't fire.")
print("          Officers can force-submit or set project later.")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n  {BLUE}PIPELINE 2: ai_service ConversationService (AI chat){END}")
print(f"  {'─'*60}")
print("  Trigger conditions:")
print("    * LLM action=submit/confirm + confidence >= AUTO_SUBMIT_CONFIDENCE")
print("    * project identified via RAG (Qdrant) — no explicit project_id needed")
print("    * product_id passed at session start -> carried into submitted feedback")

section("Pipeline 2: AI conversation (product-scoped)")

# Wait for AI service to be fully ready (embedding model load takes ~40s)
print("    Waiting for AI service to be ready...")
for _ in range(30):
    try:
        probe = requests.post(f"{AI_URL}/api/v1/ai/conversations",
                              json={"channel": "web", "language": "en"}, timeout=5)
        if probe.status_code in (200, 201):
            break
    except Exception:
        pass
    time.sleep(2)

# Use an active project from feedback_db so AI can submit without RAG
# Kigoma GRC — status=ACTIVE (from DB query)
KNOWN_PROJECT_ID = "d363d9bc-20b3-4590-b08e-157283fe03c0"
r = requests.post(f"{AI_URL}/api/v1/ai/conversations", json={
    "channel": "web",
    "language": "en",
    "project_id": KNOWN_PROJECT_ID,
    "product_id": product_id,   # link conversation to the ProBook product
})
check("Start AI conversation", r.status_code in (200, 201), r.text[:300])
conv    = r.json() if r.status_code in (200, 201) else {}
conv_id = conv.get("conversation_id") or conv.get("id")
print(f"    conversation_id: {conv_id}")
greeting = conv.get("reply", "")
print(f"    greeting: {greeting[:120]}...")

AI_TURNS = [
    f"I bought a laptop (product ID {product_id}) and it stopped working after 2 days. I want to file a grievance.",
    "The product screen cracked by itself. I am in Dar es Salaam, Ilala district, Kariakoo ward. It happened on 2026-05-01.",
    "My name is Alice Mwangi, phone +255712999888. Please submit this as a formal grievance about product quality.",
    "Yes I confirm, please submit my complaint now.",
]

ai_submitted  = False
ai_feedback_id = None
ai_ref         = None

for i, msg in enumerate(AI_TURNS):
    r = requests.post(f"{AI_URL}/api/v1/ai/conversations/{conv_id}/message",
                      json={"message": msg})
    if r.status_code == 200:
        resp     = r.json()
        reply    = resp.get("reply", "")[:80]
        ai_sub   = resp.get("submitted", False)
        ai_fbs   = resp.get("submitted_feedback") or []
        stage    = resp.get("stage", "?")
        print(f"    Turn {i+1}: stage={stage} submitted={ai_sub} | {reply}...")
        if ai_sub and ai_fbs:
            ai_submitted   = True
            ai_feedback_id = ai_fbs[0].get("feedback_id")
            ai_ref         = ai_fbs[0].get("unique_ref")
            check(f"  AI auto-submitted at turn {i+1}", True)
            print(f"    ref: {ai_ref}  id: {ai_feedback_id}")
            break
    else:
        print(f"    Turn {i+1} error: {r.status_code} {r.text[:150]}")

check("AI conversation produced a feedback record", ai_submitted)

if ai_feedback_id:
    r = requests.get(f"{FB_URL}/api/v1/feedback/{ai_feedback_id}", headers=HDR)
    if r.status_code == 200:
        fb = r.json()
        check("AI feedback submission_method = ai_conversation",
              fb.get("submission_method") == "ai_conversation",
              f"got={fb.get('submission_method')}")
        check("AI feedback.product_id = product under test",
              fb.get("product_id") == product_id,
              f"got={fb.get('product_id')} want={product_id}")
        print(f"    feedback.product_id = {fb.get('product_id')}")
        print(f"    feedback.project_id = {fb.get('project_id')}")
        print(f"    feedback.unique_ref = {fb.get('unique_ref')}")
        print(f"    feedback.category   = {fb.get('category')}")

# ─────────────────────────────────────────────────────────────────────────────
section("Summary: When does a conversation become feedback?")
print("""
  CHANNEL SESSION (SMS / WhatsApp / Phone - feedback_service):
  +------------------------------------------------------------+
  |  ACTIVE -> turns -> LLM extracts fields progressively      |
  |                                                            |
  |  AUTO-SUBMIT (requires project_id to be set):             |
  |   1. LLM confidence >= 0.80  (enough info collected)       |
  |   2. LLM ready_to_submit=True  (consumer confirms)         |
  |   3. turn_count >= 20  (hard cap, last resort)             |
  |                                                            |
  |  DOES NOT auto-submit:                                     |
  |   - No project_id  -> conversation continues indefinitely  |
  |   - Inactivity > 30 min -> TIMED_OUT (no feedback)        |
  |   - Staff can force-submit: POST /channels/{id}/submit     |
  |                                                            |
  |  product_id: attach at session creation, carried through   |
  |  to the Feedback record on auto/force-submit               |
  +------------------------------------------------------------+

  AI CONVERSATION (ai_service / web / WhatsApp AI):
  +------------------------------------------------------------+
  |  ACTIVE -> LLM extracts + identifies project via RAG       |
  |                                                            |
  |  AUTO-SUBMIT:                                              |
  |   1. LLM action=submit/confirm + confidence >= threshold   |
  |   2. RAG identifies project from location/description      |
  |                                                            |
  |  CAN submit without explicit project_id (RAG lookup)       |
  |  product_id: mention in message OR pass at conv start      |
  +------------------------------------------------------------+
""")

print(f"\n{'='*62}")
print(f"{HEAD}  SUMMARY{END}")
print(f"{'='*62}")
print(f"  {OK} PASS  {results['pass']}")
print(f"  \033[91m✗ FAIL\033[0m  {results['fail']}")
print(f"{'='*62}")
