#!/usr/bin/env python3
"""
scripts/seed_demo_data.py
────────────────────────────────────────────────────────────────────
Creates all demo organisations and users on a fresh Riviwa server.

Users & Orgs created
  1. testgrm@riviwa.com            → Riviwa GRM Demo
  2. testprod011929@riviwa.com     → Test Product Store 1
  3. testprod2_014316@riviwa.com   → Test Product Store 2
  4. mnh_admin_v2@muhimbili.co.tz  → Muhimbili National Hospital
  5. admin@yas.co.tz               → Yas Tanzania
  6. azam.admin2@azamgroup.co.tz   → Azam Group Tanzania Limited
  7. grm.fao.tanzania@riviwa.com   → FAO Tanzania
  8. grm.who.tanzania@riviwa.com   → WHO Tanzania

Run:
  cd /opt/riviwa && python3 scripts/seed_demo_data.py

Requires:  requests  (auto-installed if missing)
"""

import json, sys, time, subprocess, base64

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# ── Endpoints ────────────────────────────────────────────────────────────────
AUTH = "http://localhost:8000/api/v1"
FEED = "http://localhost:8090/api/v1"

OTP = "000000"

# ── Colours ───────────────────────────────────────────────────────────────────
GRN = "\033[92m"; RED = "\033[91m"; YEL = "\033[93m"
CYN = "\033[96m"; BLD = "\033[1m";  RST = "\033[0m"

PASS_N = FAIL_N = 0

def ok(label):
    global PASS_N; PASS_N += 1
    print(f"  {GRN}✓{RST}  {label}")

def fail(label, detail=""):
    global FAIL_N; FAIL_N += 1
    print(f"  {RED}✗ FAIL{RST}  {label}")
    if detail: print(f"         {RED}{str(detail)[:220]}{RST}")

def section(title):
    print(f"\n{BLD}{CYN}{'─'*60}{RST}")
    print(f"{BLD}{CYN}  {title}{RST}")
    print(f"{BLD}{CYN}{'─'*60}{RST}")

def jh(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# ─────────────────────────────────────────────────────────────────────────────
# Core helpers
# ─────────────────────────────────────────────────────────────────────────────

def register(email, username, display_name, full_name, password, phone=None):
    """Register a new user.  Returns True on success (or already exists)."""
    payload = {
        "email": email, "username": username,
        "display_name": display_name, "full_name": full_name,
        "country_code": "TZ",
    }
    if phone:
        payload["phone"] = phone

    r = requests.post(f"{AUTH}/auth/register/init", json=payload, timeout=20)
    if r.status_code == 409:
        ok(f"User already exists — skipping registration: {email}")
        return True
    if r.status_code != 200:
        fail(f"register/init {email}", r.text[:200])
        return False

    session_token = r.json().get("session_token", "")
    r2 = requests.post(f"{AUTH}/auth/register/verify-otp",
                       json={"session_token": session_token, "otp_code": OTP}, timeout=20)
    if r2.status_code != 200:
        fail(f"register/verify-otp {email}", r2.text[:200])
        return False

    cont = r2.json().get("continuation_token", "")
    r3 = requests.post(f"{AUTH}/auth/register/complete",
                       json={"continuation_token": cont, "password": password,
                             "password_confirm": password}, timeout=20)
    if r3.status_code not in (200, 201):
        fail(f"register/complete {email}", r3.text[:200])
        return False

    ok(f"Registered: {email}")
    return True


def login(email, password, org_id=None):
    """Login, verify OTP, optionally switch-org.  Returns access_token or ''."""
    r = requests.post(f"{AUTH}/auth/login",
                      json={"identifier": email, "password": password}, timeout=20)
    if r.status_code != 200:
        fail(f"login {email}", r.text[:200])
        return ""

    lt = r.json().get("login_token", "")
    r2 = requests.post(f"{AUTH}/auth/login/verify-otp",
                       json={"login_token": lt, "otp_code": OTP}, timeout=20)
    if r2.status_code != 200:
        fail(f"login/verify-otp {email}", r2.text[:200])
        return ""

    token = r2.json().get("access_token", "")
    if not token:
        fail(f"No access_token in response for {email}")
        return ""

    ok(f"Logged in: {email}")

    if org_id:
        r3 = requests.post(f"{AUTH}/auth/switch-org",
                           json={"org_id": str(org_id)},
                           headers=jh(token), timeout=20)
        if r3.status_code == 200:
            token = r3.json().get("tokens", {}).get("access_token", token)
            ok(f"Switched to org: {org_id}")
        else:
            fail(f"switch-org {org_id}", r3.text[:200])

    return token


def create_org(token, legal_name, display_name, slug, org_type="NGO",
               description="", website="", email="", phone=""):
    """Create an organisation and return its id."""
    payload = {
        "legal_name": legal_name, "display_name": display_name,
        "slug": slug, "org_type": org_type,
        "country_code": "TZ",
    }
    if description: payload["description"] = description
    if website:     payload["website_url"] = website
    if email:       payload["contact_email"] = email
    if phone:       payload["contact_phone"] = phone

    r = requests.post(f"{AUTH}/orgs", json=payload,
                      headers=jh(token), timeout=20)
    if r.status_code not in (200, 201):
        fail(f"create_org {display_name}", r.text[:200])
        return None

    data = r.json()
    org_id = (data.get("id") or data.get("org_id") or
              data.get("organisation", {}).get("id") or
              data.get("data", {}).get("id"))
    if org_id:
        ok(f"Org created: {display_name}  →  {org_id}")
    return org_id


def activate_org_in_db(org_id):
    """Directly set org status=ACTIVE, is_verified=True in auth_db."""
    sql = (f"UPDATE organisations SET status='ACTIVE', is_verified=true, "
           f"verified_at=NOW() WHERE id='{org_id}'; "
           f"SELECT id, status, is_verified FROM organisations WHERE id='{org_id}';")
    res = subprocess.run(
        ["docker", "exec", "riviwa_auth_db", "psql",
         "-U", "riviwa_auth_admin", "-d", "auth_db", "-c", sql],
        capture_output=True, text=True, timeout=15)
    if "ACTIVE" in res.stdout:
        ok(f"Org activated in DB: {org_id}")
        return True
    fail(f"activate_org_in_db {org_id}", res.stderr[:200])
    return False


def force_org_id(old_id, new_id):
    """Rename an org's UUID to a specific legacy value in auth_db."""
    sqls = [
        f"UPDATE organisations SET id='{new_id}' WHERE id='{old_id}';",
        f"UPDATE organisation_members SET organisation_id='{new_id}' WHERE organisation_id='{old_id}';",
        f"UPDATE organisation_invites SET organisation_id='{new_id}' WHERE organisation_id='{old_id}';",
    ]
    for sql in sqls:
        subprocess.run(
            ["docker", "exec", "riviwa_auth_db", "psql",
             "-U", "riviwa_auth_admin", "-d", "auth_db", "-c", sql],
            capture_output=True, text=True, timeout=15)
    ok(f"Org ID forced: {old_id} → {new_id}")


def create_project(token, org_id, name, description=""):
    """Create a feedback project and return its id."""
    payload = {"name": name, "description": description or name,
               "org_id": str(org_id)}
    r = requests.post(f"{FEED}/projects", json=payload,
                      headers=jh(token), timeout=20)
    if r.status_code not in (200, 201):
        fail(f"create_project {name}", r.text[:200])
        return None
    data = r.json()
    proj_id = data.get("id") or data.get("project_id")
    if proj_id:
        ok(f"Project created: {name}  →  {proj_id}")
    return proj_id


def force_project_id(old_id, new_id):
    """Rename a project UUID to a specific legacy value in feedback_db."""
    sql = f"UPDATE fb_projects SET id='{new_id}' WHERE id='{old_id}';"
    subprocess.run(
        ["docker", "exec", "feedback_db", "psql",
         "-U", "feedback_admin", "-d", "feedback_db", "-c", sql],
        capture_output=True, text=True, timeout=15)
    ok(f"Project ID forced: {old_id} → {new_id}")


# ─────────────────────────────────────────────────────────────────────────────
# Demo accounts definition
# ─────────────────────────────────────────────────────────────────────────────

ACCOUNTS = [
    {
        "email":        "testgrm@riviwa.com",
        "password":     "TestGRM@2026!",
        "username":     "testgrm",
        "display_name": "Test GRM User",
        "full_name":    "Test GRM User",
        "phone":        "+255700000001",
        "org": {
            "legal_name":   "Riviwa GRM Demo",
            "display_name": "Riviwa GRM Demo",
            "slug":         "riviwa-grm-demo",
            "org_type":     "NGO",
            "description":  "General test account for GRM demos",
        },
        "project": "GRM Demo Project",
    },
    {
        "email":        "testprod011929@riviwa.com",
        "password":     "TestProd@2026!",
        "username":     "testprod011929",
        "display_name": "Test Product User 1",
        "full_name":    "Test Product Tester 1",
        "phone":        "+255700000002",
        "org": {
            "legal_name":   "Riviwa Test Store 1",
            "display_name": "Test Store 1",
            "slug":         "teststore-1",
            "org_type":     "BUSINESS",
            "description":  "Test merchant account 1",
        },
        "project": None,
    },
    {
        "email":        "testprod2_014316@riviwa.com",
        "password":     "TestProd2@2026!",
        "username":     "testprod2014316",
        "display_name": "Test Product User 2",
        "full_name":    "Test Product Tester 2",
        "phone":        "+255700000003",
        "org": {
            "legal_name":   "Riviwa Test Store 2",
            "display_name": "Test Store 2",
            "slug":         "teststore-2",
            "org_type":     "BUSINESS",
            "description":  "Test merchant account 2",
        },
        "project": None,
    },
    {
        "email":        "mnh_admin_v2@muhimbili.co.tz",
        "password":     "MNH@Admin2026!",
        "username":     "mnh_admin_v2",
        "display_name": "MNH Admin",
        "full_name":    "Muhimbili Admin",
        "phone":        "+255222150610",
        "org": {
            "legal_name":   "Muhimbili National Hospital",
            "display_name": "Muhimbili National Hospital",
            "slug":         "muhimbili-national-hospital",
            "org_type":     "GOVERNMENT",
            "description":  "Tanzania national referral hospital",
            "website":      "https://mnh.or.tz",
            "email":        "info@mnh.or.tz",
        },
        "force_org_id":     "e50be2ae-e074-452f-8db7-8c87bbc41e24",
        "project":          "Muhimbili GRM 2026",
        "force_project_id": "64bd1dc7-baa3-4efb-a77c-c2f15d0f93dc",
    },
    {
        "email":        "admin@yas.co.tz",
        "password":     "YasTZ_Admin@2026!",
        "username":     "yas_admin",
        "display_name": "Yas Tanzania Admin",
        "full_name":    "Yas Tanzania Admin",
        "phone":        "+255789000100",
        "org": {
            "legal_name":   "Yas Tanzania",
            "display_name": "Yas Tanzania",
            "slug":         "yas-tanzania",
            "org_type":     "BUSINESS",
            "description":  "Yas mobile services Tanzania",
            "website":      "https://yas.co.tz",
            "email":        "customercare@yas.co.tz",
        },
        "project": "Yas Customer Feedback 2026",
    },
    {
        "email":        "azam.admin2@azamgroup.co.tz",
        "password":     "AzamGroup@2026!",
        "username":     "azam_admin2",
        "display_name": "Azam Group Admin",
        "full_name":    "Azam Group Admin",
        "phone":        "+255222700700",
        "org": {
            "legal_name":   "Azam Group Tanzania Limited",
            "display_name": "Azam Group Tanzania",
            "slug":         "azam-group-tanzania",
            "org_type":     "BUSINESS",
            "description":  "Azam Group diversified conglomerate",
            "website":      "https://azamgroup.co.tz",
            "email":        "info@azamgroup.co.tz",
        },
        "project": "Azam Group GRM 2026",
    },
    {
        "email":        "grm.fao.tanzania@riviwa.com",
        "password":     "FAO_Tanzania@2026!",
        "username":     "grm_fao_tanzania",
        "display_name": "FAO Tanzania Admin",
        "full_name":    "FAO Tanzania Admin",
        "phone":        "+255222700800",
        "org": {
            "legal_name":   "FAO Tanzania",
            "display_name": "FAO Tanzania",
            "slug":         "fao-tanzania",
            "org_type":     "NGO",
            "description":  "Food and Agriculture Organization — Tanzania",
            "website":      "https://www.fao.org/tanzania",
            "email":        "FAO-TZ@fao.org",
        },
        "force_org_id":     "c011921c-c33f-4ed1-97e7-46cf490acd33",
        "project":          "AFR100 Tanzania — Monduli-Karatu",
        "force_project_id": "7c10205e-17c5-4e8e-82dc-5e533c4257d3",
    },
    {
        "email":        "grm.who.tanzania@riviwa.com",
        "password":     "WHO_Tanzania@2026!",
        "username":     "grm_who_tanzania",
        "display_name": "WHO Tanzania Admin",
        "full_name":    "WHO Tanzania Admin",
        "phone":        "+255222700900",
        "org": {
            "legal_name":   "WHO Tanzania",
            "display_name": "WHO Tanzania",
            "slug":         "who-tanzania",
            "org_type":     "NGO",
            "description":  "World Health Organization — Tanzania Country Office",
            "website":      "https://www.afro.who.int/countries/united-republic-of-tanzania",
            "email":        "afrotzr@who.int",
        },
        "project": "WHO Tanzania GRM 2026",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

summary = []   # list of dicts for final printout

for acc in ACCOUNTS:
    email = acc["email"]
    section(f"{email}")

    # 1 — Register
    register(email, acc["username"], acc["display_name"],
             acc["full_name"], acc["password"], acc.get("phone"))

    time.sleep(0.5)

    # 2 — Login (no org yet)
    token = login(email, acc["password"])
    if not token:
        summary.append({"email": email, "status": "LOGIN FAILED"})
        continue

    # 3 — Create org
    org_cfg = acc.get("org", {})
    org_id = create_org(
        token,
        org_cfg.get("legal_name", email),
        org_cfg.get("display_name", email),
        org_cfg.get("slug", email.split("@")[0]),
        org_cfg.get("org_type", "NGO"),
        org_cfg.get("description", ""),
        org_cfg.get("website", ""),
        org_cfg.get("email", ""),
        org_cfg.get("phone", ""),
    )

    # 4 — Switch to org
    if org_id:
        token = login(email, acc["password"], org_id)

    # 5 — Activate org in DB
    if org_id:
        activate_org_in_db(org_id)

    # 6 — Force legacy org UUID if specified
    target_org_id = acc.get("force_org_id")
    if org_id and target_org_id and org_id != target_org_id:
        force_org_id(org_id, target_org_id)
        org_id = target_org_id
        # Re-login with corrected org id
        token = login(email, acc["password"], org_id)

    # 7 — Create feedback project
    proj_id = None
    project_name = acc.get("project")
    if project_name and org_id and token:
        proj_id = create_project(token, org_id, project_name)

    # 8 — Force legacy project UUID if specified
    target_proj_id = acc.get("force_project_id")
    if proj_id and target_proj_id and proj_id != target_proj_id:
        force_project_id(proj_id, target_proj_id)
        proj_id = target_proj_id

    summary.append({
        "email":      email,
        "password":   acc["password"],
        "org_name":   org_cfg.get("display_name", ""),
        "org_id":     org_id or "—",
        "project_id": proj_id or "—",
        "status":     "OK",
    })

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BLD}{'═'*70}{RST}")
print(f"{BLD}  SEED SUMMARY{RST}")
print(f"{BLD}{'═'*70}{RST}")
for s in summary:
    colour = GRN if s["status"] == "OK" else RED
    print(f"\n  {colour}{s['status']}{RST}  {BLD}{s['email']}{RST}")
    print(f"        Password  : {s.get('password','')}")
    print(f"        Org       : {s.get('org_name','')}  ({s.get('org_id','')})")
    print(f"        Project   : {s.get('project_id','')}")

print(f"\n{BLD}{'═'*70}{RST}")
print(f"  PASS: {GRN}{PASS_N}{RST}   FAIL: {RED}{FAIL_N}{RST}")
print(f"{BLD}{'═'*70}{RST}\n")

if FAIL_N:
    sys.exit(1)
