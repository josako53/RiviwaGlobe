#!/usr/bin/env python3
"""MNH full test — all endpoints with correct schemas."""
import time, requests

AUTH = "http://localhost:8000/api/v1"
FB   = "http://localhost:8090/api/v1"
AN   = "http://localhost:8095/api/v1"
ST   = "http://localhost:8070/api/v1"

ORG_ID = "e50be2ae-e074-452f-8db7-8c87bbc41e24"
PRJ_ID = "64bd1dc7-baa3-4efb-a77c-c2f15d0f93dc"

RESULTS = []

def ok(label, r):
    s = "PASS" if r.status_code < 300 else "FAIL"
    RESULTS.append(f"{s}  [{r.status_code}]  {label}")
    if r.status_code >= 300:
        try:
            print(f"  ERR [{r.status_code}] {label}: {r.json()}")
        except Exception:
            print(f"  ERR [{r.status_code}] {label}: {r.text[:150]}")
    return r

H = lambda t: {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}

def section(t):
    print(f"\n{'='*60}\n  {t}\n{'='*60}")

def get_token(email, pw, org_id=None):
    r1 = requests.post(f"{AUTH}/auth/login", json={"identifier": email, "password": pw})
    if r1.status_code >= 300:
        return ""
    lt = r1.json().get("login_token", "")
    r2 = requests.post(f"{AUTH}/auth/login/verify-otp", json={"login_token": lt, "otp_code": "000000"})
    if r2.status_code >= 300:
        return ""
    at = r2.json().get("access_token", "")
    if not org_id:
        return at
    r3 = requests.post(f"{AUTH}/auth/switch-org", json={"org_id": org_id}, headers=H(at))
    return r3.json().get("tokens", {}).get("access_token", at) if r3.status_code < 300 else at

ADMIN_EMAIL = "mnh_admin_v2@muhimbili.co.tz"
ADMIN_PASS  = "MNH@Admin2026!"
OT = get_token(ADMIN_EMAIL, ADMIN_PASS, ORG_ID)
r = requests.get(f"{AUTH}/users/me", headers=H(OT))
ADMIN_ID = r.json().get("id") if r.status_code < 300 else None
print(f"token={'OK' if OT else 'FAIL'}  admin_id={ADMIN_ID}")

# ─── AUTH ────────────────────────────────────────────────────
section("AUTH — org, branches, depts, services, project")

ok("get org",        requests.get(f"{AUTH}/orgs/{ORG_ID}", headers=H(OT)))
ok("list orgs",      requests.get(f"{AUTH}/orgs", headers=H(OT)))
ok("get me",         requests.get(f"{AUTH}/users/me", headers=H(OT)))
ok("list branches",  requests.get(f"{AUTH}/orgs/{ORG_ID}/branches", headers=H(OT)))
ok("list depts",     requests.get(f"{AUTH}/orgs/{ORG_ID}/departments", headers=H(OT)))
ok("list services",  requests.get(f"{AUTH}/orgs/{ORG_ID}/services", headers=H(OT)))
ok("list faqs",      requests.get(f"{AUTH}/orgs/{ORG_ID}/faqs", headers=H(OT)))
ok("get content",    requests.get(f"{AUTH}/orgs/{ORG_ID}/content", headers=H(OT)))
ok("list locations", requests.get(f"{AUTH}/orgs/{ORG_ID}/locations", headers=H(OT)))
ok("list projects",  requests.get(f"{AUTH}/orgs/{ORG_ID}/projects", headers=H(OT)))
ok("get project",    requests.get(f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}", headers=H(OT)))

for b in [{"name":"Outpatient Department","code":"OPD-B"},{"name":"Emergency Block","code":"EMG-B"},
          {"name":"Inpatient Ward","code":"IPW-B"},{"name":"Pharmacy","code":"PHM-B"},
          {"name":"Laboratory","code":"LAB-B"},{"name":"Administration","code":"ADM-B"}]:
    r = ok(f"branch {b['code']}", requests.post(f"{AUTH}/orgs/{ORG_ID}/branches", json=b, headers=H(OT)))

BRANCH_IDS = {}
r2 = requests.get(f"{AUTH}/orgs/{ORG_ID}/branches", headers=H(OT))
if r2.status_code < 300:
    data = r2.json()
    blist = data if isinstance(data, list) else data.get("items", data.get("results", []))
    for b in (blist if isinstance(blist, list) else []):
        if isinstance(b, dict) and b.get("code"):
            BRANCH_IDS[b["code"]] = b.get("id")

for d in [{"name":"General Medicine"},{"name":"Surgery"},{"name":"Paediatrics"},
          {"name":"Trauma Unit"},{"name":"ICU"},{"name":"Radiology"},{"name":"Finance"}]:
    ok(f"dept {d['name']}", requests.post(f"{AUTH}/orgs/{ORG_ID}/departments", json=d, headers=H(OT)))

ok("list depts v2", requests.get(f"{AUTH}/orgs/{ORG_ID}/departments", headers=H(OT)))

SIDS = {}
for s in [("General Consultation","gen-con-mnh3","service"),("Emergency Triage","emg-trg-mnh3","service"),
          ("Laboratory Tests","lab-tst-mnh3","service"),("Pharmacy","phm-mnh3","service"),
          ("Medical Imaging","img-mnh3","service")]:
    r = ok(f"service {s[1]}", requests.post(f"{AUTH}/orgs/{ORG_ID}/services",
            json={"title":s[0],"slug":s[1],"service_type":s[2]}, headers=H(OT)))
    if r.status_code < 300:
        sid = r.json().get("id")
        SIDS[s[1]] = sid
        ok(f"publish {s[1]}", requests.post(f"{AUTH}/orgs/{ORG_ID}/services/{sid}/publish", headers=H(OT)))

ok("list services v2", requests.get(f"{AUTH}/orgs/{ORG_ID}/services", headers=H(OT)))

for q in ["OPD hours?","Emergency care?","Lab results?","Parking?","Insurance?"]:
    ok("faq", requests.post(f"{AUTH}/orgs/{ORG_ID}/faqs",
               json={"question":q,"answer":"Please contact our help desk for details."}, headers=H(OT)))

ok("set content", requests.put(f"{AUTH}/orgs/{ORG_ID}/content",
    json={"mission":"Provide quality healthcare.","about":"MNH - Tanzania's main referral hospital."},
    headers=H(OT)))

ok("add location", requests.post(f"{AUTH}/orgs/{ORG_ID}/locations",
    json={"line1":"United Nations Road","city":"Dar es Salaam","country_code":"TZ",
          "latitude":-6.8072,"longitude":39.2666,"is_primary":True}, headers=H(OT)))

# Project stages with correct stage_order
stages = []
for i, name in enumerate(["Queue Analysis","System Deployment","Staff Training","Go Live"], 1):
    r = ok(f"stage {i}: {name}", requests.post(f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/stages",
            json={"name":name,"stage_order":i,"description":f"Phase {i}"}, headers=H(OT)))
    if r.status_code < 300:
        stages.append(r.json().get("id"))

if stages:
    ok("activate stage 1", requests.post(
        f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/stages/{stages[0]}/activate", headers=H(OT)))

ok("list stages", requests.get(f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/stages", headers=H(OT)))

CHECKLIST_IDS = []
for item in ["Collect baseline data","Interview 50 patients","Review benchmarks"]:
    r = ok(f"checklist: {item}", requests.post(f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/checklist",
            json={"title":item,"description":item}, headers=H(OT)))
    if r.status_code < 300:
        CHECKLIST_IDS.append(r.json().get("id"))

for cid in CHECKLIST_IDS:
    ok("mark done", requests.post(
        f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/checklist/{cid}/done",
        json={}, headers=H(OT)))

ok("checklist progress", requests.get(
    f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/checklist/progress", headers=H(OT)))

ok("invite MEMBER", requests.post(f"{AUTH}/orgs/{ORG_ID}/invites",
    json={"invited_email":"nurse_mary_v3@mnh.test","invited_role":"MEMBER"}, headers=H(OT)))

ok("checklist perf", requests.get(
    f"{AUTH}/orgs/{ORG_ID}/projects/{PRJ_ID}/checklist-performance", headers=H(OT)))
ok("org checklist perf", requests.get(
    f"{AUTH}/orgs/{ORG_ID}/checklist-performance", headers=H(OT)))

# ─── FEEDBACK ────────────────────────────────────────────────
section("FEEDBACK — categories, escalation, committee")

CAT_IDS = {}
for c in [
    {"name":"Patient Safety v2",       "category_type":"GRIEVANCE", "applicable_types":["grievance"]},
    {"name":"Staff Conduct v2",        "category_type":"GRIEVANCE", "applicable_types":["grievance"]},
    {"name":"Waiting Times v2",        "category_type":"GRIEVANCE", "applicable_types":["grievance","suggestion"]},
    {"name":"Facility Equipment v2",   "category_type":"SUGGESTION","applicable_types":["suggestion"]},
    {"name":"Clinical Excellence v2",  "category_type":"COMPLIMENT","applicable_types":["applause"]},
    {"name":"Medication Error v2",     "category_type":"GRIEVANCE", "applicable_types":["grievance"]},
    {"name":"Billing Dispute v2",      "category_type":"GRIEVANCE", "applicable_types":["grievance"]},
    {"name":"Hygiene v2",              "category_type":"SUGGESTION","applicable_types":["suggestion"]},
    {"name":"General Inquiry v2",      "category_type":"INQUIRY",   "applicable_types":["inquiry"]},
]:
    r = ok(f"cat {c['name'][:20]}", requests.post(f"{FB}/categories",
            json={**c,"org_id":ORG_ID,"project_id":PRJ_ID}, headers=H(OT)))
    if r.status_code < 300:
        CAT_IDS[c["name"]] = r.json().get("id")

ok("list cats", requests.get(f"{FB}/categories?org_id={ORG_ID}", headers=H(OT)))
ok("cats summary", requests.get(f"{FB}/categories/summary?project_id={PRJ_ID}", headers=H(OT)))

r = ok("escalation path", requests.post(f"{FB}/escalation-paths", json={
    "org_id": ORG_ID,
    "name": "MNH Clinical Complaint Path",
    "description": "Standard hospital escalation",
    "levels": [
        {"level_order":1,"code":"DHD","name":"Department Head","max_days":3},
        {"level_order":2,"code":"MED","name":"Medical Director","max_days":7},
        {"level_order":3,"code":"BOD","name":"Hospital Board","max_days":14},
    ],
}, headers=H(OT)))
ESC_PATH_ID = r.json().get("id") if r.status_code < 300 else None

r = ok("committee", requests.post(f"{FB}/committees", json={
    "org_id": ORG_ID,
    "name": "MNH Patient Safety Committee",
    "level": "ward",
    "committee_type": "GRIEVANCE",
}, headers=H(OT)))
COMMITTEE_ID = r.json().get("id") if r.status_code < 300 else None

ok("list esc paths", requests.get(f"{FB}/escalation-paths?org_id={ORG_ID}", headers=H(OT)))
ok("list committees", requests.get(f"{FB}/committees?org_id={ORG_ID}", headers=H(OT)))

section("FEEDBACK — submit 12 items")
FB_IDS = {}
BASE = {"org_id": ORG_ID, "project_id": PRJ_ID}

def sub(label, payload):
    r = ok(label, requests.post(f"{FB}/feedback", json=payload, headers=H(OT)))
    if r.status_code < 300:
        FB_IDS[label] = r.json().get("id")
    return r

sub("G: OPD wait", {**BASE, "feedback_type":"GRIEVANCE","category":"TIMELINESS",
    "channel":"IN_PERSON","priority":"HIGH",
    "subject":"Waited 4 hours in OPD with no update from staff",
    "description":"I arrived at 8am with a referral letter. Not seen until noon. No communication throughout.",
    "submitter_name":"John Msoka","submitter_phone":"+255712800002","is_anonymous":False})

sub("G: rude nurse", {**BASE, "feedback_type":"GRIEVANCE","category":"STAFF_CONDUCT",
    "channel":"IN_PERSON","priority":"HIGH",
    "subject":"Night shift nurse shouted at patient requesting results",
    "description":"Emergency block night shift nurse was rude and dismissive when I asked about my test results.",
    "submitter_name":"Grace Nyama","submitter_phone":"+255712800003","is_anonymous":False})

sub("G: medication error", {**BASE, "feedback_type":"GRIEVANCE","category":"SAFETY",
    "channel":"WEB_PORTAL","priority":"CRITICAL",
    "subject":"Wrong medication dispensed at pharmacy — Amoxicillin instead of Azithromycin",
    "description":"Pharmacy dispensed Amoxicillin 500mg instead of Azithromycin 250mg. I noticed only at home.",
    "submitter_name":"Hassan Juma","submitter_phone":"+255712800004","is_anonymous":False})

sub("G: overcrowding", {**BASE, "feedback_type":"GRIEVANCE","category":"OTHER",
    "channel":"IN_PERSON","priority":"MEDIUM",
    "subject":"Severe overcrowding in inpatient ward C",
    "description":"Patients are sharing beds. Family members are sleeping on the floor due to lack of space.",
    "is_anonymous":True})

sub("G: double billing", {**BASE, "feedback_type":"GRIEVANCE","category":"OTHER",
    "channel":"WEB_PORTAL","priority":"MEDIUM",
    "subject":"Billed twice for the same chest X-ray",
    "description":"My receipt shows two charges for a single chest X-ray. Requesting full refund urgently.",
    "submitter_name":"John Msoka","is_anonymous":False})

sub("S: queue screens", {**BASE, "feedback_type":"SUGGESTION","category":"QUALITY",
    "channel":"EMAIL","priority":"LOW",
    "subject":"Install digital queue display screens in OPD waiting area",
    "description":"Digital screens showing ticket numbers would reduce anxiety and confusion in the OPD.",
    "is_anonymous":True})

sub("S: online booking", {**BASE, "feedback_type":"SUGGESTION","category":"TIMELINESS",
    "channel":"MOBILE_APP","priority":"MEDIUM",
    "subject":"Introduce online appointment booking via mobile phone",
    "description":"A mobile booking system would allow patients to reserve OPD slots and avoid early queuing.",
    "submitter_name":"Grace Nyama","is_anonymous":False})

sub("S: bathroom hygiene", {**BASE, "feedback_type":"SUGGESTION","category":"QUALITY",
    "channel":"PAPER_FORM","priority":"MEDIUM",
    "subject":"Improve bathroom cleanliness in ward C overnight",
    "description":"Ward C bathrooms need more frequent cleaning from 10pm onwards. Strong odour at night.",
    "is_anonymous":True})

sub("A: surgical team", {**BASE, "feedback_type":"APPLAUSE","category":"QUALITY",
    "channel":"WEB_PORTAL","priority":"LOW",
    "subject":"Surgical team saved my mother's life with exceptional speed",
    "description":"The surgical team responded with extraordinary speed to my mother's emergency. Truly life-saving.",
    "submitter_name":"Amina Ally","submitter_phone":"+255712999001","is_anonymous":False})

sub("A: ICU nurses", {**BASE, "feedback_type":"APPLAUSE","category":"QUALITY",
    "channel":"EMAIL","priority":"LOW",
    "subject":"Outstanding compassionate nursing care in the ICU unit",
    "description":"ICU nurses were attentive, compassionate and highly professional throughout my week of care.",
    "submitter_name":"Ibrahim Nkusi","is_anonymous":False})

sub("A: pharmacy staff", {**BASE, "feedback_type":"APPLAUSE","category":"QUALITY",
    "channel":"IN_PERSON","priority":"LOW",
    "subject":"Pharmacy staff went above and beyond to help with medications",
    "description":"The pharmacist explained all medications clearly and suggested a cheaper effective equivalent.",
    "submitter_name":"Fatuma Said","is_anonymous":False})

sub("I: certificate", {**BASE, "feedback_type":"INQUIRY","category":"INFORMATION_REQUEST",
    "channel":"EMAIL","priority":"LOW",
    "subject":"Requesting information on how to get a medical fitness certificate",
    "description":"I need a medical fitness certificate for my new employer. Which department handles this?",
    "submitter_name":"John Msoka","is_anonymous":False})

print(f"\nSubmitted: {len(FB_IDS)} items")

section("FEEDBACK — lifecycle")
fid1 = FB_IDS.get("G: OPD wait")
fid2 = FB_IDS.get("G: rude nurse")
fid3 = FB_IDS.get("G: medication error")

if fid1:
    ok("ack G1", requests.patch(f"{FB}/feedback/{fid1}/acknowledge",
        json={"notes":"OPD manager notified."}, headers=H(OT)))
if fid2:
    ok("ack G2", requests.patch(f"{FB}/feedback/{fid2}/acknowledge",
        json={"notes":"Nursing supervisor review."}, headers=H(OT)))
if fid3:
    ok("ack G3 CRITICAL", requests.patch(f"{FB}/feedback/{fid3}/acknowledge",
        json={"notes":"Pharmacy director alerted immediately. Incident form opened."}, headers=H(OT)))

    if COMMITTEE_ID and ADMIN_ID:
        ok("assign G3", requests.patch(f"{FB}/feedback/{fid3}/assign",
            json={"committee_id":COMMITTEE_ID,"assigned_to_user_id":ADMIN_ID,
                  "notes":"Pharmacy audit triggered"}, headers=H(OT)))

    if ESC_PATH_ID:
        ok("escalate G3", requests.post(f"{FB}/feedback/{fid3}/escalate",
            json={"escalation_path_id":ESC_PATH_ID,
                  "reason":"Critical patient safety. Director review required.","to_level":2},
            headers=H(OT)))

if fid2:
    ok("action G2", requests.post(f"{FB}/feedback/{fid2}/actions",
        json={"action_type":"INVESTIGATION",
              "description":"Night shift nurses interviewed. CCTV review requested."}, headers=H(OT)))
    ok("get actions G2", requests.get(f"{FB}/feedback/{fid2}/actions", headers=H(OT)))
    ok("dismiss G2", requests.patch(f"{FB}/feedback/{fid2}/dismiss",
        json={"reason":"No misconduct found. Nurse counselled on communication."}, headers=H(OT)))

if fid1:
    ok("resolve G1", requests.post(f"{FB}/feedback/{fid1}/resolve",
        json={"resolution_summary":"Display boards ordered. Process revised.",
              "resolution_type":"CORRECTIVE_ACTION",
              "action_taken":"OPD staff briefed on communication protocols."},
        headers=H(OT)))
    ok("close G1", requests.patch(f"{FB}/feedback/{fid1}/close",
        json={"notes":"Patient confirmed satisfied."}, headers=H(OT)))

for label, fid in list(FB_IDS.items())[:4]:
    ok(f"get: {label}", requests.get(f"{FB}/feedback/{fid}", headers=H(OT)))

ok("my feedback",    requests.get(f"{FB}/my/feedback", headers=H(OT)))
ok("my fb summary",  requests.get(f"{FB}/my/feedback/summary", headers=H(OT)))

section("FEEDBACK — admin views + all reports")
ok("all fb",       requests.get(f"{FB}/feedback?org_id={ORG_ID}", headers=H(OT)))
ok("grievances",   requests.get(f"{FB}/feedback?org_id={ORG_ID}&feedback_type=GRIEVANCE", headers=H(OT)))
ok("suggestions",  requests.get(f"{FB}/feedback?org_id={ORG_ID}&feedback_type=SUGGESTION", headers=H(OT)))
ok("applause",     requests.get(f"{FB}/feedback?org_id={ORG_ID}&feedback_type=APPLAUSE", headers=H(OT)))
ok("inquiries",    requests.get(f"{FB}/feedback?org_id={ORG_ID}&feedback_type=INQUIRY", headers=H(OT)))
ok("critical",     requests.get(f"{FB}/feedback?org_id={ORG_ID}&priority=CRITICAL", headers=H(OT)))

for rpt in ["performance","grievances","grievance-performance","suggestions","suggestion-performance",
            "applause","applause-performance","channels","grievance-log","suggestion-log",
            "applause-log","overdue"]:
    ok(f"rpt:{rpt}", requests.get(f"{FB}/reports/{rpt}?org_id={ORG_ID}", headers=H(OT)))

ok("rpt:summary", requests.get(f"{FB}/reports/summary?project_id={PRJ_ID}", headers=H(OT)))
ok("esc requests", requests.get(f"{FB}/escalation-requests?org_id={ORG_ID}", headers=H(OT)))

section("ANALYTICS — org, project, platform")
for ep in [
    f"org/{ORG_ID}/summary", f"org/{ORG_ID}/by-project", f"org/{ORG_ID}/by-period",
    f"org/{ORG_ID}/by-channel", f"org/{ORG_ID}/by-branch", f"org/{ORG_ID}/by-department",
    f"org/{ORG_ID}/by-service", f"org/{ORG_ID}/by-category",
    f"org/{ORG_ID}/grievances/summary", f"org/{ORG_ID}/grievances/dashboard",
    f"org/{ORG_ID}/grievances/sla", f"org/{ORG_ID}/grievances/by-level",
    f"org/{ORG_ID}/grievances/by-location",
    f"org/{ORG_ID}/suggestions/summary", f"org/{ORG_ID}/applause/summary",
    f"org/{ORG_ID}/inquiries/summary",
    "platform/summary","platform/by-org","platform/by-period","platform/by-channel",
    "platform/by-branch","platform/by-department","platform/by-service","platform/by-category",
    "platform/grievances/summary","platform/grievances/dashboard","platform/grievances/sla",
    "platform/suggestions/summary","platform/applause/summary","platform/inquiries/summary",
]:
    ok(f"an:{ep[:50]}", requests.get(f"{AN}/analytics/{ep}", headers=H(OT)))

p = f"project_id={PRJ_ID}"
for ep in [
    "feedback/unread","feedback/overdue","feedback/by-category","feedback/by-branch",
    "feedback/by-department","feedback/by-stage","feedback/not-processed",
    "feedback/processed-today","feedback/resolved-today","feedback/time-to-open",
    "grievances/unresolved","grievances/sla-status","grievances/dashboard","grievances/hotspots",
    "suggestions/frequency","suggestions/unread","suggestions/implemented-today",
    "suggestions/implemented-this-week","suggestions/by-location",
    "inquiries/summary","inquiries/unread","inquiries/overdue","inquiries/by-channel","inquiries/by-category",
    "staff/committee-performance","staff/unread-assigned","staff/login-not-read",
]:
    ok(f"an:{ep}", requests.get(f"{AN}/analytics/{ep}?{p}", headers=H(OT)))

ok("AI ask (org scope)", requests.post(f"{AN}/analytics/ai/ask",
    json={"question":"What are the main issues at this hospital?","org_id":ORG_ID,"scope":"org"},
    headers=H(OT)))

section("STAKEHOLDER — stakeholders + activities")
STK_IDS = []
for s in [
    {"stakeholder_type":"interested_party","entity_type":"organization","category":"national_government",
     "org_name":"Ministry of Health Tanzania","affectedness":"positively_affected","importance_rating":"high",
     "language_preference":"sw","preferred_channel":"email",
     "needs_translation":False,"needs_transport":False,"needs_childcare":False,"is_vulnerable":False},
    {"stakeholder_type":"interested_party","entity_type":"organization","category":"private_company",
     "org_name":"National Health Insurance Fund","affectedness":"both","importance_rating":"high",
     "language_preference":"sw","preferred_channel":"email",
     "needs_translation":False,"needs_transport":False,"needs_childcare":False,"is_vulnerable":False},
    {"stakeholder_type":"consumer","entity_type":"group","category":"community_group",
     "org_name":"MNH Patient Community Association","affectedness":"both","importance_rating":"medium",
     "language_preference":"sw","preferred_channel":"in_person",
     "needs_translation":False,"needs_transport":False,"needs_childcare":False,"is_vulnerable":False},
]:
    r = ok(f"stk:{s['org_name'][:25]}", requests.post(f"{ST}/stakeholders",
            json={**s,"org_id":ORG_ID,"project_id":PRJ_ID}, headers=H(OT)))
    if r.status_code < 300:
        STK_IDS.append(r.json().get("id"))

ok("list stk", requests.get(f"{ST}/stakeholders?org_id={ORG_ID}", headers=H(OT)))

for a in [
    {"title":"Quarterly Patient Forum","activity_type":"public_meeting","stage":"operation","date":"2026-05-15","description":"Community forum"},
    {"title":"MoH Annual Inspection",  "activity_type":"site_visit",   "stage":"construction","date":"2026-06-01","description":"Quality review"},
    {"title":"NHIF Claims Audit",      "activity_type":"round_table",  "stage":"finalization","date":"2026-05-20","description":"Claims audit"},
]:
    ok(f"act:{a['title'][:25]}", requests.post(f"{ST}/activities",
        json={**a,"org_id":ORG_ID,"project_id":PRJ_ID,"stakeholder_ids":STK_IDS[:1]},
        headers=H(OT)))

ok("list activities", requests.get(f"{ST}/activities?org_id={ORG_ID}", headers=H(OT)))

# ─── SUMMARY ─────────────────────────────────────────────────
section("RESULTS")
passed = sum(1 for r in RESULTS if r.startswith("PASS"))
failed = sum(1 for r in RESULTS if r.startswith("FAIL"))
total  = len(RESULTS)

for result in RESULTS:
    print(result)

rate = round(passed/total*100) if total else 0
print(f"\nTOTAL: {total}  PASS: {passed}  FAIL: {failed}  RATE: {rate}%")

with open("/tmp/hospital_results_final.txt","w") as f:
    f.write(f"MNH Test — {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
    for r in RESULTS:
        f.write(r+"\n")
    f.write(f"\nTOTAL: {total}  PASS: {passed}  FAIL: {failed}  RATE: {rate}%\n")
    f.write(f"ORG_ID: {ORG_ID}\nPRJ_ID: {PRJ_ID}\nADMIN: {ADMIN_EMAIL}/{ADMIN_PASS}\n\n")
    for k,v in FB_IDS.items():
        f.write(f"{k}: {v}\n")

print("Results -> /tmp/hospital_results_final.txt")
print(f"ORG: {ORG_ID}")
print(f"PRJ: {PRJ_ID}")
print(f"Admin: {ADMIN_EMAIL} / {ADMIN_PASS}")
