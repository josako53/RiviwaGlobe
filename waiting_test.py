#!/usr/bin/env python3
"""Full end-to-end test for waiting_service at port 8130."""
import requests

BASE   = "http://localhost:8130/api/v1"
AUTH   = "http://localhost:8000/api/v1"
ORG_ID = "e50be2ae-e074-452f-8db7-8c87bbc41e24"

RESULTS = []

def get_token():
    r1 = requests.post(f"{AUTH}/auth/login", json={"identifier": "mnh_admin_v2@muhimbili.co.tz", "password": "MNH@Admin2026!"})
    lt = r1.json().get("login_token", "")
    r2 = requests.post(f"{AUTH}/auth/login/verify-otp", json={"login_token": lt, "otp_code": "000000"})
    at = r2.json().get("access_token", "")
    r3 = requests.post(f"{AUTH}/auth/switch-org", json={"org_id": ORG_ID},
                       headers={"Authorization": f"Bearer {at}", "Content-Type": "application/json"})
    return r3.json().get("tokens", {}).get("access_token", at)

OT = get_token()
AH = {"Authorization": f"Bearer {OT}", "Content-Type": "application/json"}

def ok(label, r):
    s = "PASS" if r.status_code < 300 else "FAIL"
    RESULTS.append(f"{s}  [{r.status_code}]  {label}")
    if r.status_code >= 300:
        try:
            print(f"  ERR {label}: {r.json()}")
        except Exception:
            print(f"  ERR {label}: {r.text[:100]}")
    return r


print("=== WAITING SERVICE FULL TEST ===\n")

# First fetch existing service points
SP_MAP = {}
r_list = requests.get(f"{BASE}/waiting/admin/service-points?org_id={ORG_ID}", headers=AH)
ok("list service points", r_list)
if r_list.status_code < 300:
    items = r_list.json() if isinstance(r_list.json(), list) else r_list.json().get("items", [])
    for sp in (items if isinstance(items, list) else []):
        if sp.get("code"):
            SP_MAP[sp["code"]] = sp["id"]

# Create service points (skip if already exist)
for sp_name, sp_code, sp_type, avg_min in [
    ("OPD Registration", "OPD-REG3", "DESK",    5),
    ("OPD Triage",       "OPD-TRG3", "DESK",    8),
    ("Doctor Room",      "OPD-DOC3", "ROOM",   15),
    ("Pharmacy",         "OPD-PHM3", "COUNTER",  5),
]:
    if SP_MAP.get(sp_code):
        RESULTS.append(f"PASS  [exists]  SP: {sp_code}")
        continue
    r = ok(f"SP: {sp_code}", requests.post(f"{BASE}/waiting/admin/service-points", json={
        "org_id": ORG_ID, "name": sp_name, "code": sp_code,
        "point_type": sp_type, "avg_service_minutes": avg_min,
    }, headers=AH))
    if r.status_code < 300:
        SP_MAP[sp_code] = r.json().get("id")

ok("get service point", requests.get(f"{BASE}/waiting/admin/service-points/{SP_MAP.get('OPD-REG3')}", headers=AH))

# Create flow with inline steps
steps = [{"service_point_id": SP_MAP[c], "step_order": i}
         for i, c in enumerate(["OPD-REG3", "OPD-TRG3", "OPD-DOC3", "OPD-PHM3"], 1) if SP_MAP.get(c)]
r = ok("create flow", requests.post(f"{BASE}/waiting/admin/flows", json={
    "org_id": ORG_ID, "name": "MNH OPD Standard Flow", "is_default": True, "steps": steps
}, headers=AH))
FLOW_ID = r.json().get("id") if r.status_code < 300 else None
if FLOW_ID:
    print(f"  flow_id: {FLOW_ID}")

ok("list flows", requests.get(f"{BASE}/waiting/admin/flows?org_id={ORG_ID}", headers=AH))
if FLOW_ID:
    ok("get flow", requests.get(f"{BASE}/waiting/admin/flows/{FLOW_ID}", headers=AH))

# Counters — fetch existing first
CTRS = {}
if SP_MAP.get("OPD-REG3"):
    r_ctr = requests.get(f"{BASE}/waiting/admin/counters?service_point_id={SP_MAP['OPD-REG3']}", headers=AH)
    if r_ctr.status_code < 300:
        ctrs = r_ctr.json() if isinstance(r_ctr.json(), list) else r_ctr.json().get("items", [])
        for c in (ctrs if isinstance(ctrs, list) else []):
            CTRS[c.get("code")] = c.get("id")

for sp_code, cname, ccode in [
    ("OPD-REG3", "Counter 1 - Registration", "REG-C3"),
    ("OPD-TRG3", "Counter 1 - Triage",       "TRG-C3"),
    ("OPD-DOC3", "Counter 1 - Doctor",        "DOC-C3"),
]:
    if CTRS.get(ccode):
        RESULTS.append(f"PASS  [exists]  counter {ccode}")
        continue
    if SP_MAP.get(sp_code):
        r = ok(f"counter {ccode}", requests.post(f"{BASE}/waiting/admin/counters", json={
            "org_id": ORG_ID, "service_point_id": SP_MAP[sp_code],
            "name": cname, "code": ccode,
        }, headers=AH))
        if r.status_code < 300:
            CTRS[ccode] = r.json().get("id")

ok("list counters", requests.get(f"{BASE}/waiting/admin/counters?service_point_id={SP_MAP.get('OPD-REG3')}", headers=AH))

# Open staff session on REG counter
if CTRS.get("REG-C3"):
    ok("open session REG", requests.post(
        f"{BASE}/waiting/admin/counters/{CTRS['REG-C3']}/session/open", json={}, headers=AH
    ))

# 4 patients join (different priorities — URGENT should come first)
ticket_ids = []
if FLOW_ID:
    for name, phone, priority in [
        ("Amina Ally",   "+255712901011", "NORMAL"),
        ("Ibrahim Nkusi","+255712901012", "HIGH"),
        ("Salma Omar",   "+255712901013", "URGENT"),
        ("Peter Mwangi", "+255712901014", "NORMAL"),
    ]:
        r = ok(f"join: {name}", requests.post(f"{BASE}/waiting/join", json={
            "org_id": ORG_ID, "flow_id": FLOW_ID,
            "submitter_name": name, "phone_number": phone,
            "channel": "KIOSK", "priority": priority,
        }))
        if r.status_code < 300:
            d = r.json()
            ticket_ids.append(d.get("id"))
            print(f"  {d.get('ticket_number')}  pos={d.get('position_in_queue')}  priority={priority}")

print(f"\n  Queued: {len(ticket_ids)} tickets")

# Staff call-next — should get URGENT (Salma)
if SP_MAP.get("OPD-REG3"):
    r = ok("call-next", requests.post(f"{BASE}/waiting/staff/call-next", json={
        "service_point_id": SP_MAP["OPD-REG3"]
    }, headers=AH))
    if r.status_code < 300:
        d = r.json()
        print(f"  >> {d.get('message')}")
        ticket_obj = d.get("ticket") or {}
        serving = ticket_obj.get("id")
        tn      = ticket_obj.get("ticket_number")
        print(f"  ticket: {tn}")

        # Ticket status check
        if serving:
            ok("ticket status (unauth)", requests.get(f"{BASE}/waiting/ticket/{serving}/status"))
            ok("ticket status (auth)",   requests.get(f"{BASE}/waiting/ticket/{serving}/status", headers=AH))

        # Set HIGH priority on a waiting ticket
        waiter = next((t for t in ticket_ids if t != serving), None)
        if waiter:
            ok("set priority", requests.post(f"{BASE}/waiting/staff/ticket/{waiter}/priority",
                json={"priority": "HIGH", "reason": "Elderly patient"}, headers=AH))

        # Finish serving ticket (advances to next flow step — triage)
        if serving:
            r2 = ok("finish", requests.post(f"{BASE}/waiting/staff/ticket/{serving}/finish",
                json={"notes": "Registration done. Sent to triage."}, headers=AH))
            if r2.status_code < 300:
                d2 = r2.json()
                print(f"  is_final={d2.get('is_final')}  next={d2.get('next_point')}  {d2.get('message')}")

# View queue
r = ok("view queue", requests.get(f"{BASE}/waiting/staff/queue/{SP_MAP.get('OPD-REG3')}", headers=AH))
if r.status_code < 300:
    d = r.json()
    print(f"  waiting={len(d.get('waiting', []))}  attending={len(d.get('attending', []))}")

# Call next #2 + mark no-show
if SP_MAP.get("OPD-REG3"):
    r = ok("call-next #2", requests.post(f"{BASE}/waiting/staff/call-next", json={
        "service_point_id": SP_MAP["OPD-REG3"]
    }, headers=AH))
    if r.status_code < 300:
        t2 = (r.json().get("ticket") or {}).get("id")
        if t2 and CTRS.get("REG-C3"):
            ok("no-show", requests.post(f"{BASE}/waiting/ticket/{t2}/no-show",
                json={"staff_counter_id": CTRS["REG-C3"]}, headers=AH))

# Cancel a remaining ticket
if ticket_ids and len(ticket_ids) > 2:
    ok("cancel", requests.post(f"{BASE}/waiting/ticket/{ticket_ids[3]}/cancel", headers=AH))

# Urgency request
if ticket_ids:
    ok("urgency request", requests.post(f"{BASE}/waiting/ticket/{ticket_ids[0]}/urgency",
        json={"urgency_type": "MEDICAL_EMERGENCY", "evidence_notes": "Patient showing signs of distress"},
        headers=AH))

    ok("list urgency requests", requests.get(f"{BASE}/waiting/admin/urgency-requests?org_id={ORG_ID}", headers=AH))

# Analytics dashboard
ok("analytics dashboard", requests.get(f"{BASE}/waiting/analytics/dashboard?org_id={ORG_ID}", headers=AH))

# Close REG session
if CTRS.get("REG-C3"):
    ok("close session", requests.post(
        f"{BASE}/waiting/admin/counters/{CTRS['REG-C3']}/session/close", json={}, headers=AH
    ))

print("\n=== RESULTS ===")
passed = sum(1 for r in RESULTS if r.startswith("PASS"))
failed = sum(1 for r in RESULTS if r.startswith("FAIL"))
for result in RESULTS:
    print(result)
print(f"\nTOTAL: {len(RESULTS)}  PASS: {passed}  FAIL: {failed}  RATE: {round(passed/len(RESULTS)*100)}%")

import time
with open("/tmp/waiting_test_results.txt", "w") as f:
    f.write(f"Waiting Service Test — {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
    for r in RESULTS:
        f.write(r + "\n")
    f.write(f"\nTOTAL: {len(RESULTS)}  PASS: {passed}  FAIL: {failed}\n")
    f.write(f"ORG_ID: {ORG_ID}\n")
    if FLOW_ID:
        f.write(f"FLOW_ID: {FLOW_ID}\n")

print("\nResults -> /tmp/waiting_test_results.txt")
