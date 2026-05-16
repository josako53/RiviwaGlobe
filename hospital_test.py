#!/usr/bin/env python3
"""
Muhimbili National Hospital — full Riviwa test suite.
Pre-conditions (already done via direct DB):
  - Org e50be2ae-e074-452f-8db7-8c87bbc41e24 created and ACTIVE
  - Project 64bd1dc7-baa3-4efb-a77c-c2f15d0f93dc in feedback_db and stakeholder_db
  - Admin user mnh_admin_v2@muhimbili.co.tz registered
Auth flow: login → login/verify-otp → switch-org → use org-scoped token
"""
import time, requests

AUTH  = "http://localhost:8000/api/v1"
FB    = "http://localhost:8090/api/v1"
AN    = "http://localhost:8095/api/v1"
ST    = "http://localhost:8070/api/v1"

ORG_ID  = "e50be2ae-e074-452f-8db7-8c87bbc41e24"
PRJ_ID  = "64bd1dc7-baa3-4efb-a77c-c2f15d0f93dc"

RESULTS = []

def ok(label, r):
    status = "PASS" if r.status_code < 300 else "FAIL"
    RESULTS.append(f"{status}  [{r.status_code}]  {label}")
    if r.status_code >= 300:
        try:
            print(f"  ERROR [{r.status_code}] {label}: {r.json()}")
        except Exception:
            print(f"  ERROR [{r.status_code}] {label}: {r.text[:200]}")
    return r

def hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def get_token(email, password, org_id=None):
    """2-step login, optional switch-org."""
    r1 = requests.post(f"{AUTH}/auth/login", json={"identifier": email, "password": password})
    if r1.status_code >= 300:
        print(f"  login FAILED {email}: {r1.json()}")
        return ""
    lt = r1.json().get("login_token", "")
    r2 = requests.post(f"{AUTH}/auth/login/verify-otp", json={"login_token": lt, "otp_code": "000000"})
    if r2.status_code >= 300:
        print(f"  verify-otp FAILED {email}: {r2.json()}")
        return ""
    at = r2.json().get("access_token", "")
    if not org_id:
        return at
    r3 = requests.post(f"{AUTH}/auth/switch-org", json={"org_id": org_id}, headers=hdr(at))
    if r3.status_code >= 300:
        print(f"  switch-org FAILED: {r3.json()}")
        return at
    return r3.json().get("tokens", {}).get("access_token", at)


def register_and_login(email, username, display_name, full_name, password, phone=None, org_id=None):
    """3-step register then login with optional org switch."""
    payload = {"email": email, "username": username,
               "display_name": display_name, "full_name": full_name}
    if phone:
        payload["phone"] = phone

    r = requests.post(f"{AUTH}/auth/register/init", json=payload)
    if r.status_code < 300:
        session_token = r.json().get("session_token", "")
        r2 = requests.post(f"{AUTH}/auth/register/verify-otp",
                           json={"session_token": session_token, "otp_code": "000000"})
        if r2.status_code < 300:
            cont = r2.json().get("continuation_token", "")
            requests.post(f"{AUTH}/auth/register/complete",
                          json={"continuation_token": cont, "password": password,
                                "password_confirm": password})

    return get_token(email, password, org_id)


# ─── 1. ADMIN LOGIN ───────────────────────────────────────────
section("1. AUTH — Admin login + switch org")

ADMIN_EMAIL = "mnh_admin_v2@muhimbili.co.tz"
ADMIN_PASS  = "MNH@Admin2026!"
ADMIN_TOKEN = get_token(ADMIN_EMAIL, ADMIN_PASS, ORG_ID)
print(f"  admin token: {'OK' if ADMIN_TOKEN else 'FAILED'}")

r = ok("get me", requests.get(f"{AUTH}/users/me", headers=hdr(ADMIN_TOKEN)))
ADMIN_ID = r.json().get("id") if r.status_code < 300 else None
print(f"  admin_id: {ADMIN_ID}")

ok("get org", requests.get(f"{AUTH}/orgs/{ORG_ID}", headers=hdr(ADMIN_TOKEN)))
ok("list orgs", requests.get(f"{AUTH}/orgs", headers=hdr(ADMIN_TOKEN)))

# ─── 2. BRANCHES ─────────────────────────────────────────────
section("2. AUTH — Branches")

BRANCH_IDS = {}
for b in [
    {"name": "Outpatient Department",    "code": "OPD"},
    {"name": "Emergency & Trauma",       "code": "EMG"},
    {"name": "Inpatient Ward",           "code": "IPW"},
    {"name": "Pharmacy",                 "code": "PHM"},
    {"name": "Laboratory & Diagnostics", "code": "LAB"},
    {"name": "Administration",           "code": "ADM"},
]:
    r = ok(f"branch {b['code']}", requests.post(
        f"{AUTH}/orgs/{ORG_ID}/branches", json=b, headers=hdr(ADMIN_TOKEN)
    ))
    if r.status_code < 300:
        BRANCH_IDS[b["code"]] = r.json().get("id")

ok("list branches", requests.get(f"{AUTH}/orgs/{ORG_ID}/branches", headers=hdr(ADMIN_TOKEN)))

if BRANCH_IDS.get("OPD"):
    ok("branch children OPD", requests.get(
        f"{AUTH}/orgs/{ORG_ID}/branches/{BRANCH_IDS['OPD']}/children", headers=hdr(ADMIN_TOKEN)
    ))
    ok("branch tree OPD", requests.get(
        f"{AUTH}/orgs/{ORG_ID}/branches/{BRANCH_IDS['OPD']}/tree", headers=hdr(ADMIN_TOKEN)
    ))

# ─── 3. DEPARTMENTS ───────────────────────────────────────────
section("3. AUTH — Departments")

DEPT_IDS = {}
for d in [
    {"name": "General Medicine",     "branch_code": "OPD"},
    {"name": "Surgery",              "branch_code": "OPD"},
    {"name": "Paediatrics",          "branch_code": "OPD"},
    {"name": "Trauma Unit",          "branch_code": "EMG"},
    {"name": "ICU",                  "branch_code": "IPW"},
    {"name": "Pharmacy Dispensing",  "branch_code": "PHM"},
    {"name": "Haematology",          "branch_code": "LAB"},
    {"name": "Radiology",            "branch_code": "LAB"},
    {"name": "HR & Payroll",         "branch_code": "ADM"},
    {"name": "Finance",              "branch_code": "ADM"},
]:
    bid = BRANCH_IDS.get(d["branch_code"])
    payload = {"name": d["name"]}
    if bid:
        payload["branch_id"] = bid
    r = ok(f"dept {d['name']}", requests.post(
        f"{AUTH}/orgs/{ORG_ID}/departments", json=payload, headers=hdr(ADMIN_TOKEN)
    ))
    if r.status_code < 300:
        DEPT_IDS[d["name"]] = r.json().get("id")

ok("list departments", requests.get(f"{AUTH}/orgs/{ORG_ID}/departments", headers=hdr(ADMIN_TOKEN)))

# ─── 4. SERVICES ─────────────────────────────────────────────
section("4. AUTH — Services, FAQs, Content, Locations")

SERVICE_IDS = {}
for s in [
    {"name": "General Consultation", "code": "GEN-01", "description": "OPD consultation"},
    {"name": "Emergency Triage",     "code": "EMG-01", "description": "24/7 triage"},
    {"name": "Laboratory Tests",     "code": "LAB-01", "description": "Blood, urine tests"},
    {"name": "Pharmacy Dispensing",  "code": "PHM-01", "description": "Medication"},
    {"name": "Medical Imaging",      "code": "IMG-01", "description": "X-ray, CT, MRI"},
]:
    r = ok(f"service {s['code']}", requests.post(
        f"{AUTH}/orgs/{ORG_ID}/services", json=s, headers=hdr(ADMIN_TOKEN)
    ))
    if r.status_code < 300:
        sid = r.json().get("id")
        SERVICE_IDS[s["code"]] = sid
        ok(f"publish {s['code']}", requests.post(
            f"{AUTH}/orgs/{ORG_ID}/services/{sid}/publish", headers=hdr(ADMIN_TOKEN)
        ))

# Link to branches
for code, branch_code in [("GEN-01", "OPD"), ("EMG-01", "EMG"), ("PHM-01", "PHM"), ("LAB-01", "LAB")]:
    sid = SERVICE_IDS.get(code)
    bid = BRANCH_IDS.get(branch_code)
    if sid and bid:
        ok(f"link {code}→{branch_code}", requests.post(
            f"{AUTH}/orgs/{ORG_ID}/branches/{bid}/services/{sid}/link", headers=hdr(ADMIN_TOKEN)
        ))

ok("list services", requests.get(f"{AUTH}/orgs/{ORG_ID}/services", headers=hdr(ADMIN_TOKEN)))

for faq in [
    {"question": "What are OPD hours?",          "answer": "Mon–Fri 08:00–17:00, Sat 08:00–12:00"},
    {"question": "How do I get emergency care?",  "answer": "Emergency block is open 24/7."},
    {"question": "How do I collect lab results?", "answer": "Results ready in 2–24 hours."},
    {"question": "Is parking available?",         "answer": "Yes, free parking on north side."},
    {"question": "What insurance is accepted?",   "answer": "NHIF, AAR, Jubilee, Sanlam and most corporate covers."},
]:
    ok("faq", requests.post(f"{AUTH}/orgs/{ORG_ID}/faqs", json=faq, headers=hdr(ADMIN_TOKEN)))

ok("list faqs", requests.get(f"{AUTH}/orgs/{ORG_ID}/faqs", headers=hdr(ADMIN_TOKEN)))

ok("set content", requests.put(f"{AUTH}/orgs/{ORG_ID}/content", json={
    "mission": "To provide quality healthcare to all Tanzanians.",
    "vision": "A healthy nation with world-class healthcare.",
    "about": "MNH is Tanzania's largest national referral hospital.",
}, headers=hdr(ADMIN_TOKEN)))

ok("get content", requests.get(f"{AUTH}/orgs/{ORG_ID}/content", headers=hdr(ADMIN_TOKEN)))

ok("add location", requests.post(f"{AUTH}/orgs/{ORG_ID}/locations", json={
    "name": "MNH Main Campus",
    "address": "United Nations Road, Upanga",
    "city": "Dar es Salaam", "country": "TZ",
    "latitude": -6.8072, "longitude": 39.2666, "is_primary": True,
}, headers=hdr(ADMIN_TOKEN)))

ok("list locations", requests.get(f"{AUTH}/orgs/{ORG_ID}/locations", headers=hdr(ADMIN_TOKEN)))

# ─── 5. PROJECT OPERATIONS ───────────────────────────────────
section("5. AUTH — Project + stages + checklist")

# Project already exists as PRJ_ID; activate it
ok("activate project", requests.post(
    f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/activate", headers=hdr(ADMIN_TOKEN)
))

stages = []
for s in [
    {"name": "Phase 1: Queue Analysis",    "description": "Audit current wait times"},
    {"name": "Phase 2: System Deployment", "description": "Deploy queue management system"},
    {"name": "Phase 3: Staff Training",    "description": "Train all OPD staff"},
    {"name": "Phase 4: Full Operation",    "description": "Go live with monitoring"},
]:
    r = ok(f"stage: {s['name'][:22]}", requests.post(
        f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/stages", json=s, headers=hdr(ADMIN_TOKEN)
    ))
    if r.status_code < 300:
        stages.append(r.json().get("id"))

if stages:
    ok("activate stage 1", requests.post(
        f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/stages/{stages[0]}/activate",
        headers=hdr(ADMIN_TOKEN)
    ))

ok("list stages", requests.get(
    f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/stages", headers=hdr(ADMIN_TOKEN)
))

for item in ["Collect baseline wait time data", "Interview 50 patients", "Review international benchmarks"]:
    r = ok(f"checklist: {item[:30]}", requests.post(
        f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/checklist",
        json={"title": item, "description": item}, headers=hdr(ADMIN_TOKEN)
    ))
    if r.status_code < 300:
        ok(f"complete: {item[:20]}", requests.post(
            f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/checklist/{r.json()['id']}/done",
            headers=hdr(ADMIN_TOKEN)
        ))

ok("checklist progress", requests.get(
    f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/checklist/progress", headers=hdr(ADMIN_TOKEN)
))
ok("list projects", requests.get(f"{AUTH}/orgs/{ORG_ID}/projects", headers=hdr(ADMIN_TOKEN)))

# ─── 6. REGISTER EXTRA USERS ─────────────────────────────────
section("6. Register patients and staff users")

USER_TOKENS = {}
USER_IDS    = {}
for u in [
    {"email": "pt_john_v3@mnh.test",    "username": "john_mnh_v3",   "display_name": "John M.",    "full_name": "John Msoka",   "password": "Patient@2026!", "phone": "+255712800002"},
    {"email": "pt_grace_v3@mnh.test",   "username": "grace_mnh_v3",  "display_name": "Grace N.",   "full_name": "Grace Nyama",  "password": "Patient@2026!", "phone": "+255712800003"},
    {"email": "pt_hassan_v3@mnh.test",  "username": "hassan_mnh_v3", "display_name": "Hassan J.",  "full_name": "Hassan Juma",  "password": "Patient@2026!", "phone": "+255712800004"},
    {"email": "nurse_mary_v3@mnh.test", "username": "nurse_mary_v3", "display_name": "Nurse Mary", "full_name": "Mary Ngowi",   "password": "Nurse@MNH2026!", "phone": "+255712800005"},
]:
    token = register_and_login(**{k: v for k, v in u.items()})
    ok(f"reg+login {u['email']}", type('R', (), {'status_code': 200 if token else 401})())
    if token:
        USER_TOKENS[u["email"]] = token
        r2 = requests.get(f"{AUTH}/users/me", headers=hdr(token))
        if r2.status_code < 300:
            USER_IDS[u["email"]] = r2.json().get("id")

# Invite nurse to org
ok("invite nurse", requests.post(f"{AUTH}/orgs/{ORG_ID}/invites", json={
    "email": "nurse_mary_v3@mnh.test", "role": "STAFF"
}, headers=hdr(ADMIN_TOKEN)))

ok("list org invites", requests.get(f"{AUTH}/orgs/{ORG_ID}/invites", headers=hdr(ADMIN_TOKEN)))

# ─── 7. FEEDBACK CATEGORIES ───────────────────────────────────
section("7. FEEDBACK — Categories")

CAT_IDS = {}
for c in [
    {"name": "Patient Safety",        "category_type": "GRIEVANCE",  "applicable_types": ["grievance"]},
    {"name": "Staff Conduct",         "category_type": "GRIEVANCE",  "applicable_types": ["grievance"]},
    {"name": "Waiting Times",         "category_type": "GRIEVANCE",  "applicable_types": ["grievance", "suggestion"]},
    {"name": "Facility & Equipment",  "category_type": "SUGGESTION", "applicable_types": ["suggestion"]},
    {"name": "Clinical Excellence",   "category_type": "COMPLIMENT", "applicable_types": ["applause"]},
    {"name": "Medication Error",      "category_type": "GRIEVANCE",  "applicable_types": ["grievance"]},
    {"name": "Billing Dispute",       "category_type": "GRIEVANCE",  "applicable_types": ["grievance"]},
    {"name": "Cleanliness",           "category_type": "SUGGESTION", "applicable_types": ["suggestion"]},
    {"name": "General Inquiry",       "category_type": "INQUIRY",    "applicable_types": ["inquiry"]},
]:
    r = ok(f"cat {c['name'][:15]}", requests.post(f"{FB}/categories", json={
        **c, "org_id": ORG_ID
    }, headers=hdr(ADMIN_TOKEN)))
    if r.status_code < 300:
        CAT_IDS[c["name"]] = r.json().get("id")

ok("list categories", requests.get(f"{FB}/categories?org_id={ORG_ID}", headers=hdr(ADMIN_TOKEN)))
ok("categories summary", requests.get(f"{FB}/categories/summary?org_id={ORG_ID}", headers=hdr(ADMIN_TOKEN)))

# ─── 8. ESCALATION PATH + COMMITTEE ───────────────────────────
section("8. FEEDBACK — Escalation path + committee")

r = ok("create escalation path", requests.post(f"{FB}/escalation-paths", json={
    "org_id": ORG_ID,
    "name": "Clinical Complaint Path",
    "description": "Standard clinical complaint escalation",
    "levels": [
        {"level_number": 1, "name": "Department Head",  "max_days": 3},
        {"level_number": 2, "name": "Medical Director", "max_days": 7},
        {"level_number": 3, "name": "Hospital Board",   "max_days": 14},
    ],
}, headers=hdr(ADMIN_TOKEN)))
ESC_PATH_ID = r.json().get("id") if r.status_code < 300 else None

r = ok("create committee", requests.post(f"{FB}/committees", json={
    "org_id": ORG_ID,
    "name": "Patient Rights & Safety Committee",
    "description": "Oversees clinical grievances and patient safety",
    "committee_type": "GRIEVANCE",
    "members": [],
}, headers=hdr(ADMIN_TOKEN)))
COMMITTEE_ID = r.json().get("id") if r.status_code < 300 else None

ok("list escalation paths", requests.get(f"{FB}/escalation-paths?org_id={ORG_ID}", headers=hdr(ADMIN_TOKEN)))
ok("list committees",       requests.get(f"{FB}/committees?org_id={ORG_ID}", headers=hdr(ADMIN_TOKEN)))

# ─── 9. SUBMIT FEEDBACK ───────────────────────────────────────
section("9. FEEDBACK — Submit all types")

FB_IDS = {}

def submit(label, payload, token=None):
    """Submit feedback and store id."""
    t = token or ADMIN_TOKEN
    r = ok(label, requests.post(f"{FB}/feedback", json=payload, headers=hdr(t)))
    if r.status_code < 300:
        FB_IDS[label] = r.json().get("id")
    return r

def fb_payload(feedback_type, subject, description, category_key, channel="WEB_PORTAL",
               priority="MEDIUM", **extra):
    return {
        "org_id": ORG_ID,
        "project_id": PRJ_ID,
        "feedback_type": feedback_type,
        "category": "STAFF_CONDUCT" if "Staff" in category_key else
                    "SAFETY" if "Safety" in category_key else
                    "OTHER" if "Error" in category_key or "Billing" in category_key else
                    "TIMELINESS" if "Waiting" in category_key else
                    "QUALITY" if "Excellence" in category_key or "Cleanliness" in category_key else
                    "GENERAL_INQUIRY",
        "category_def_id": CAT_IDS.get(category_key),
        "channel": channel,
        "subject": subject,
        "description": description,
        "priority": priority,
        **extra,
    }

# Grievances
submit("grievance: OPD wait", fb_payload(
    "GRIEVANCE", "Waited 4 hours in OPD with no update",
    "I arrived at 8am with a referral letter but was not seen until noon. No staff communication at all.",
    "Waiting Times", priority="HIGH",
    submitter_name="John Msoka", submitter_phone="+255712800002", is_anonymous=False,
), USER_TOKENS.get("pt_john_v3@mnh.test"))

submit("grievance: rude nurse", fb_payload(
    "GRIEVANCE", "Nurse was rude and dismissive during triage",
    "The night shift nurse at emergency block shouted at me when I asked about results.",
    "Staff Conduct", channel="IN_PERSON", priority="HIGH",
    submitter_name="Grace Nyama", submitter_phone="+255712800003", is_anonymous=False,
), USER_TOKENS.get("pt_grace_v3@mnh.test"))

submit("grievance: medication error (CRITICAL)", fb_payload(
    "GRIEVANCE", "Wrong medication dispensed at pharmacy",
    "I was given Amoxicillin 500mg instead of the prescribed Azithromycin 250mg. Noticed only at home.",
    "Medication Error", priority="CRITICAL",
    submitter_name="Hassan Juma", submitter_phone="+255712800004", is_anonymous=False,
), USER_TOKENS.get("pt_hassan_v3@mnh.test"))

submit("grievance: overcrowding", fb_payload(
    "GRIEVANCE", "Overcrowding in inpatient ward C",
    "Patients are sharing beds. Family members are sleeping on the floor due to lack of space.",
    "Facility & Equipment", is_anonymous=True,
))

submit("grievance: double billing", fb_payload(
    "GRIEVANCE", "Billed twice for the same chest X-ray",
    "My receipt shows two charges for a chest X-ray performed only once. Requesting a refund urgently.",
    "Billing Dispute",
    submitter_name="John Msoka", is_anonymous=False,
), USER_TOKENS.get("pt_john_v3@mnh.test"))

# Suggestions
submit("suggestion: queue screens", fb_payload(
    "SUGGESTION", "Install digital queue display screens in OPD",
    "A digital display screen showing ticket numbers would reduce patient anxiety and confusion.",
    "Facility & Equipment", priority="LOW", is_anonymous=True,
))

submit("suggestion: online booking", fb_payload(
    "SUGGESTION", "Online appointment booking via mobile phone",
    "Patients could book OPD appointments via mobile to avoid early-morning queuing outside.",
    "Facility & Equipment",
    submitter_name="Grace Nyama", is_anonymous=False,
), USER_TOKENS.get("pt_grace_v3@mnh.test"))

submit("suggestion: bathroom cleanliness", fb_payload(
    "SUGGESTION", "Improve bathroom cleanliness in ward C",
    "Ward C bathrooms need more frequent cleaning especially at night. Odour is a problem.",
    "Cleanliness", is_anonymous=True,
))

# Compliments
submit("compliment: surgical team", fb_payload(
    "APPLAUSE", "Dr Rashid saved my mother's life",
    "The surgical team's rapid response during my mother's emergency surgery was extraordinary. Professional and caring.",
    "Clinical Excellence", priority="LOW",
    submitter_name="Amina Ally", submitter_phone="+255712999001", is_anonymous=False,
))

submit("compliment: ICU nurses", fb_payload(
    "APPLAUSE", "Outstanding nursing care in the ICU",
    "ICU nursing staff were attentive, compassionate and professional throughout my week-long stay.",
    "Clinical Excellence", priority="LOW",
    submitter_name="Ibrahim Nkusi", is_anonymous=False,
))

submit("compliment: pharmacy staff", fb_payload(
    "APPLAUSE", "Pharmacy staff are extremely helpful",
    "The pharmacist explained my medications clearly, provided dosage instructions and suggested a cheaper equivalent.",
    "Clinical Excellence", priority="LOW",
    submitter_name="Fatuma Said", is_anonymous=False,
))

# Inquiry
submit("inquiry: medical certificate", fb_payload(
    "INQUIRY", "How to apply for a medical fitness certificate",
    "I need a medical fitness certificate for my employer. Which department processes this and how long does it take?",
    "General Inquiry", priority="LOW",
    submitter_name="John Msoka", is_anonymous=False,
), USER_TOKENS.get("pt_john_v3@mnh.test"))

print(f"\n  Submitted: {len(FB_IDS)} feedback items")
for label, fid in FB_IDS.items():
    print(f"    {label[:40]}: {fid}")

# ─── 10. LIFECYCLE ────────────────────────────────────────────
section("10. FEEDBACK — Lifecycle operations")

fid_wait   = FB_IDS.get("grievance: OPD wait")
fid_nurse  = FB_IDS.get("grievance: rude nurse")
fid_med    = FB_IDS.get("grievance: medication error (CRITICAL)")
fid_bill   = FB_IDS.get("grievance: double billing")

if fid_wait:
    ok("acknowledge: OPD wait (PATCH)", requests.patch(f"{FB}/feedback/{fid_wait}/acknowledge", json={
        "notes": "Received and logged. OPD department manager notified."
    }, headers=hdr(ADMIN_TOKEN)))

if fid_nurse:
    ok("acknowledge: rude nurse (PATCH)", requests.patch(f"{FB}/feedback/{fid_nurse}/acknowledge", json={
        "notes": "Under review by nursing supervisor."
    }, headers=hdr(ADMIN_TOKEN)))

if fid_med:
    ok("acknowledge: medication (PATCH)", requests.patch(f"{FB}/feedback/{fid_med}/acknowledge", json={
        "notes": "CRITICAL: Pharmacy director notified. Incident investigation opened."
    }, headers=hdr(ADMIN_TOKEN)))

    if COMMITTEE_ID and ADMIN_ID:
        ok("assign: medication to committee (PATCH)", requests.patch(f"{FB}/feedback/{fid_med}/assign", json={
            "committee_id": COMMITTEE_ID,
            "assigned_to_user_id": ADMIN_ID,
            "notes": "Pharmacy audit triggered",
        }, headers=hdr(ADMIN_TOKEN)))

    if ESC_PATH_ID:
        ok("escalate: medication (POST)", requests.post(f"{FB}/feedback/{fid_med}/escalate", json={
            "escalation_path_id": ESC_PATH_ID,
            "reason": "Critical patient safety incident. Director-level review required.",
            "target_level": 2,
        }, headers=hdr(ADMIN_TOKEN)))

if fid_nurse:
    ok("add action: investigation", requests.post(f"{FB}/feedback/{fid_nurse}/actions", json={
        "action_type": "INVESTIGATION",
        "description": "Interviewed night shift nurses. CCTV review requested.",
    }, headers=hdr(ADMIN_TOKEN)))

    ok("get actions", requests.get(f"{FB}/feedback/{fid_nurse}/actions", headers=hdr(ADMIN_TOKEN)))

    ok("dismiss: rude nurse (PATCH)", requests.patch(f"{FB}/feedback/{fid_nurse}/dismiss", json={
        "reason": "After review, no misconduct found. Nurse has been counselled on communication."
    }, headers=hdr(ADMIN_TOKEN)))

if fid_wait:
    ok("resolve: OPD wait (POST)", requests.post(f"{FB}/feedback/{fid_wait}/resolve", json={
        "resolution_summary": "Appointment system reviewed. Display boards ordered for OPD.",
        "resolution_type": "CORRECTIVE_ACTION",
        "action_taken": "OPD queue process revised. Staff briefed on communication protocols.",
    }, headers=hdr(ADMIN_TOKEN)))

    ok("close: OPD wait (PATCH)", requests.patch(f"{FB}/feedback/{fid_wait}/close", json={
        "notes": "Patient contacted and confirmed satisfaction."
    }, headers=hdr(ADMIN_TOKEN)))

if fid_bill:
    ok("classify: billing (POST)", requests.post(f"{FB}/feedback/{fid_bill}/classify", json={
        "category_def_id": CAT_IDS.get("Billing Dispute"),
    }, headers=hdr(ADMIN_TOKEN)))

# Patient views
pt = USER_TOKENS.get("pt_john_v3@mnh.test", ADMIN_TOKEN)
ok("my feedback list", requests.get(f"{FB}/my/feedback", headers=hdr(pt)))
ok("my feedback summary", requests.get(f"{FB}/my/feedback/summary", headers=hdr(pt)))

# Patient escalation request on billing
if fid_bill:
    ok("patient escalation request", requests.post(
        f"{FB}/my/feedback/{fid_bill}/escalation-request",
        json={"reason": "Issue unresolved after 1 week. Double charge still not refunded."},
        headers=hdr(pt),
    ))

# Grace views her items
grace = USER_TOKENS.get("pt_grace_v3@mnh.test", ADMIN_TOKEN)
ok("grace: my feedback", requests.get(f"{FB}/my/feedback", headers=hdr(grace)))

# Individual feedback get
for label, fid in list(FB_IDS.items())[:3]:
    ok(f"get feedback: {label[:20]}", requests.get(f"{FB}/feedback/{fid}", headers=hdr(ADMIN_TOKEN)))

# ─── 11. ADMIN FEEDBACK VIEWS ────────────────────────────────
section("11. FEEDBACK — Admin filters & reports")

ok("all feedback",     requests.get(f"{FB}/feedback?org_id={ORG_ID}&page=1&size=20", headers=hdr(ADMIN_TOKEN)))
ok("grievances only",  requests.get(f"{FB}/feedback?org_id={ORG_ID}&feedback_type=GRIEVANCE", headers=hdr(ADMIN_TOKEN)))
ok("suggestions only", requests.get(f"{FB}/feedback?org_id={ORG_ID}&feedback_type=SUGGESTION", headers=hdr(ADMIN_TOKEN)))
ok("applause only",    requests.get(f"{FB}/feedback?org_id={ORG_ID}&feedback_type=APPLAUSE", headers=hdr(ADMIN_TOKEN)))
ok("critical only",    requests.get(f"{FB}/feedback?org_id={ORG_ID}&priority=CRITICAL", headers=hdr(ADMIN_TOKEN)))

for rpt in ["performance", "grievances", "grievance-performance", "suggestions",
            "suggestion-performance", "applause", "applause-performance", "channels",
            "grievance-log", "suggestion-log", "applause-log", "summary", "overdue"]:
    ok(f"report: {rpt}", requests.get(f"{FB}/reports/{rpt}?org_id={ORG_ID}", headers=hdr(ADMIN_TOKEN)))

ok("escalation requests", requests.get(f"{FB}/escalation-requests?org_id={ORG_ID}", headers=hdr(ADMIN_TOKEN)))

# ─── 12. ANALYTICS ────────────────────────────────────────────
section("12. ANALYTICS")

for ep in [
    f"org/{ORG_ID}/summary",
    f"org/{ORG_ID}/by-project",
    f"org/{ORG_ID}/by-period",
    f"org/{ORG_ID}/by-channel",
    f"org/{ORG_ID}/by-branch",
    f"org/{ORG_ID}/by-department",
    f"org/{ORG_ID}/by-category",
    f"org/{ORG_ID}/grievances/summary",
    f"org/{ORG_ID}/grievances/dashboard",
    f"org/{ORG_ID}/grievances/sla",
    f"org/{ORG_ID}/grievances/by-level",
    f"org/{ORG_ID}/grievances/by-location",
    f"org/{ORG_ID}/suggestions/summary",
    f"org/{ORG_ID}/applause/summary",
    f"org/{ORG_ID}/inquiries/summary",
    "feedback/unread",
    "feedback/overdue",
    "feedback/by-category",
    "feedback/by-branch",
    "feedback/by-department",
    "feedback/by-stage",
    "feedback/not-processed",
    "feedback/processed-today",
    "feedback/resolved-today",
    "grievances/unresolved",
    "grievances/sla-status",
    "grievances/dashboard",
    "grievances/hotspots",
    "suggestions/frequency",
    "suggestions/unread",
    "suggestions/implemented-today",
    "suggestions/implemented-this-week",
    "inquiries/summary",
    "inquiries/unread",
    "inquiries/overdue",
    "inquiries/by-channel",
    "inquiries/by-category",
    "staff/committee-performance",
    "staff/last-logins",
    "staff/unread-assigned",
    "staff/login-not-read",
    "platform/summary",
    "platform/grievances/summary",
    "platform/grievances/dashboard",
    "platform/grievances/sla",
    "platform/suggestions/summary",
    "platform/applause/summary",
    "platform/inquiries/summary",
]:
    ok(f"analytics: {ep[:50]}", requests.get(f"{AN}/analytics/{ep}", headers=hdr(ADMIN_TOKEN)))

ok("AI ask (POST)", requests.post(f"{AN}/analytics/ai/ask", json={
    "question": "What are the top issues patients face at the hospital and how can we improve care?",
    "org_id": ORG_ID,
}, headers=hdr(ADMIN_TOKEN)))

# ─── 13. STAKEHOLDER ─────────────────────────────────────────
section("13. STAKEHOLDER — Stakeholders, activities")

STK_IDS = []
for s in [
    {
        "stakeholder_type": "INTERESTED_PARTY",
        "entity_type": "ORGANIZATION",
        "category": "NATIONAL_GOVERNMENT",
        "org_name": "Ministry of Health Tanzania",
        "affectedness": "POSITIVELY_AFFECTED",
        "importance_rating": "HIGH",
        "language_preference": "sw",
        "preferred_channel": "EMAIL",
        "needs_translation": False,
        "needs_transport": False,
        "needs_childcare": False,
        "is_vulnerable": False,
    },
    {
        "stakeholder_type": "INTERESTED_PARTY",
        "entity_type": "ORGANIZATION",
        "category": "PRIVATE_COMPANY",
        "org_name": "National Health Insurance Fund (NHIF)",
        "affectedness": "BOTH",
        "importance_rating": "HIGH",
        "language_preference": "sw",
        "preferred_channel": "EMAIL",
        "needs_translation": False,
        "needs_transport": False,
        "needs_childcare": False,
        "is_vulnerable": False,
    },
    {
        "stakeholder_type": "CONSUMER",
        "entity_type": "GROUP",
        "category": "COMMUNITY_GROUP",
        "org_name": "Patient Community Association",
        "affectedness": "BOTH",
        "importance_rating": "MEDIUM",
        "language_preference": "sw",
        "preferred_channel": "IN_PERSON",
        "needs_translation": False,
        "needs_transport": False,
        "needs_childcare": False,
        "is_vulnerable": False,
    },
]:
    r = ok(f"stakeholder: {s['org_name'][:30]}", requests.post(f"{ST}/stakeholders", json={
        **s, "org_id": ORG_ID, "project_id": PRJ_ID,
    }, headers=hdr(ADMIN_TOKEN)))
    if r.status_code < 300:
        STK_IDS.append(r.json().get("id"))

ok("list stakeholders", requests.get(f"{ST}/stakeholders?org_id={ORG_ID}", headers=hdr(ADMIN_TOKEN)))

for a in [
    {"title": "Quarterly Patient Forum",       "activity_type": "CONSULTATION", "date": "2026-05-15",
     "description": "Community feedback session on hospital improvements"},
    {"title": "MoH Annual Site Inspection",    "activity_type": "SITE_VISIT",   "date": "2026-06-01",
     "description": "Annual quality assurance review by Ministry"},
    {"title": "NHIF Quarterly Billing Audit",  "activity_type": "MEETING",      "date": "2026-05-20",
     "description": "Quarterly billing and claims audit by NHIF"},
]:
    ok(f"activity: {a['title'][:30]}", requests.post(f"{ST}/activities", json={
        **a, "org_id": ORG_ID, "project_id": PRJ_ID,
        "stakeholder_ids": STK_IDS[:1] if STK_IDS else [],
    }, headers=hdr(ADMIN_TOKEN)))

ok("list activities", requests.get(f"{ST}/activities?org_id={ORG_ID}", headers=hdr(ADMIN_TOKEN)))

# ─── 14. VERIFY ORG STATUS ───────────────────────────────────
section("14. AUTH — Admin org actions")

ok("list org branches", requests.get(f"{AUTH}/orgs/{ORG_ID}/branches", headers=hdr(ADMIN_TOKEN)))
ok("get project", requests.get(f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}", headers=hdr(ADMIN_TOKEN)))
ok("org checklist perf", requests.get(f"{AUTH}/orgs/{ORG_ID}/checklist-performance", headers=hdr(ADMIN_TOKEN)))
ok("project checklist perf", requests.get(
    f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/checklist-performance", headers=hdr(ADMIN_TOKEN)
))

# ─── SUMMARY ─────────────────────────────────────────────────
section("FINAL RESULTS")

passed = sum(1 for r in RESULTS if r.startswith("PASS"))
failed = sum(1 for r in RESULTS if r.startswith("FAIL"))
total  = len(RESULTS)

for result in RESULTS:
    print(result)

print(f"\n{'='*60}")
print(f"  TOTAL: {total}  |  PASS: {passed}  |  FAIL: {failed}")
print(f"  PASS RATE: {round(passed/total*100)}%" if total else "")
print('='*60)

with open("/tmp/hospital_test_results.txt", "w") as f:
    f.write(f"Hospital Test — {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
    for r in RESULTS:
        f.write(r + "\n")
    f.write(f"\nTOTAL: {total}  PASS: {passed}  FAIL: {failed}\n")
    f.write(f"ORG_ID:    {ORG_ID}\n")
    f.write(f"PRJ_ID:    {PRJ_ID}\n")
    f.write(f"ADMIN:     {ADMIN_EMAIL} / {ADMIN_PASS}\n")
    f.write(f"\nFeedback IDs:\n")
    for label, fid in FB_IDS.items():
        f.write(f"  {label}: {fid}\n")

print(f"\nResults → /tmp/hospital_test_results.txt")
print(f"ORG_ID:  {ORG_ID}")
print(f"PRJ_ID:  {PRJ_ID}")
print(f"Admin:   {ADMIN_EMAIL} / {ADMIN_PASS}")
