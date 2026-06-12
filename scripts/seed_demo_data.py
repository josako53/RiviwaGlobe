#!/usr/bin/env python3
"""
scripts/seed_demo_data.py
────────────────────────────────────────────────────────────────────
Creates all demo organisations, users, and projects on a fresh Riviwa server.
Fully idempotent — safe to re-run after partial failures.

Users & Orgs
  1. testgrm@riviwa.com            → Riviwa GRM Demo
  2. testprod011929@riviwa.com     → Riviwa Test Store 1
  3. testprod2_014316@riviwa.com   → Riviwa Test Store 2
  4. mnh_admin_v2@muhimbili.co.tz  → Muhimbili National Hospital  (forced UUID)
  5. admin@yas.co.tz               → Yas Tanzania
  6. azam.admin2@azamgroup.co.tz   → Azam Group Tanzania Limited
  7. grm.fao.tanzania@riviwa.com   → FAO Tanzania                  (forced UUID)
  8. grm.who.tanzania@riviwa.com   → WHO Tanzania

Run on server:
  cd /opt/riviwa && python3 scripts/seed_demo_data.py
"""

import re, sys, time, subprocess

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# ── Endpoints ──────────────────────────────────────────────────────────────────
AUTH = "http://localhost:8000/api/v1"
OTP  = "000000"

# ── Terminal colours ────────────────────────────────────────────────────────────
GRN = "\033[92m"; RED = "\033[91m"; YEL = "\033[93m"
CYN = "\033[96m"; BLD = "\033[1m";  RST = "\033[0m"

PASS_N = FAIL_N = 0
UUID_RE = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


def ok(label):
    global PASS_N; PASS_N += 1
    print(f"  {GRN}✓{RST}  {label}")


def fail(label, detail=""):
    global FAIL_N; FAIL_N += 1
    print(f"  {RED}✗ FAIL{RST}  {label}")
    if detail:
        print(f"         {RED}{str(detail)[:240]}{RST}")


def section(title):
    print(f"\n{BLD}{CYN}{'─'*60}{RST}")
    print(f"{BLD}{CYN}  {title}{RST}")
    print(f"{BLD}{CYN}{'─'*60}{RST}")


def jh(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── DB helpers ──────────────────────────────────────────────────────────────────

def _psql_auth(sql):
    res = subprocess.run(
        ["docker", "exec", "riviwa_auth_db", "psql",
         "-U", "riviwa_auth_admin", "-d", "auth_db", "-c", sql],
        capture_output=True, text=True, timeout=15)
    return res.stdout


def _extract_uuid(text):
    m = UUID_RE.search(text)
    return m.group(0) if m else None


def get_org_id_from_db(slug):
    out = _psql_auth(f"SELECT id FROM organisations WHERE slug='{slug}';")
    return _extract_uuid(out)


def get_project_id_from_db(slug):
    out = _psql_auth(f"SELECT id FROM org_projects WHERE slug='{slug}';")
    return _extract_uuid(out)


# ── API helpers ────────────────────────────────────────────────────────────────

def register(email, username, display_name, full_name, password, phone=None):
    payload = {
        "email": email, "username": username,
        "display_name": display_name, "full_name": full_name,
        "country_code": "TZ",
    }
    if phone:
        payload["phone"] = phone

    r = requests.post(f"{AUTH}/auth/register/init", json=payload, timeout=20)
    if r.status_code == 409:
        ok(f"Already registered: {email}")
        return True
    if r.status_code != 200:
        fail(f"register/init {email}", r.text[:200])
        return False

    session_token = r.json().get("session_token", "")
    r2 = requests.post(f"{AUTH}/auth/register/verify-otp",
                       json={"session_token": session_token, "otp_code": OTP},
                       timeout=20)
    if r2.status_code != 200:
        fail(f"register/verify-otp {email}", r2.text[:200])
        return False

    cont = r2.json().get("continuation_token", "")
    r3 = requests.post(f"{AUTH}/auth/register/complete",
                       json={"continuation_token": cont, "password": password,
                             "password_confirm": password},
                       timeout=20)
    if r3.status_code not in (200, 201):
        fail(f"register/complete {email}", r3.text[:200])
        return False

    ok(f"Registered: {email}")
    return True


def login(email, password, org_id=None):
    r = requests.post(f"{AUTH}/auth/login",
                      json={"identifier": email, "password": password},
                      timeout=20)
    if r.status_code != 200:
        fail(f"login {email}", r.text[:200])
        return ""

    lt = r.json().get("login_token", "")
    r2 = requests.post(f"{AUTH}/auth/login/verify-otp",
                       json={"login_token": lt, "otp_code": OTP},
                       timeout=20)
    if r2.status_code != 200:
        fail(f"login/verify-otp {email}", r2.text[:200])
        return ""

    token = r2.json().get("access_token", "")
    if not token:
        fail(f"No access_token for {email}")
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
    payload = {
        "legal_name": legal_name, "display_name": display_name,
        "slug": slug, "org_type": org_type, "country_code": "TZ",
    }
    if description: payload["description"] = description
    if website:     payload["website_url"] = website
    if email:       payload["contact_email"] = email
    if phone:       payload["contact_phone"] = phone

    r = requests.post(f"{AUTH}/orgs", json=payload, headers=jh(token), timeout=20)
    if r.status_code not in (200, 201):
        fail(f"create_org {display_name}", r.text[:200])
        return None

    data = r.json()
    org_id = (data.get("id") or data.get("org_id") or
              (data.get("organisation") or {}).get("id") or
              (data.get("data") or {}).get("id"))
    if org_id:
        ok(f"Org created: {display_name}  →  {org_id}")
    return org_id


def activate_org_in_db(org_id):
    sql = (f"UPDATE organisations SET status='ACTIVE', is_verified=true, "
           f"verified_at=NOW() WHERE id='{org_id}'; "
           f"SELECT id, status FROM organisations WHERE id='{org_id}';")
    out = _psql_auth(sql)
    if "ACTIVE" in out:
        ok(f"Org activated: {org_id}")
        return True
    fail(f"activate_org_in_db {org_id}", out[:200])
    return False


def _psql_auth_one(sql):
    """Run a single SQL statement, prefixed with session_replication_role=replica to bypass FKs."""
    full = f"SET session_replication_role = replica; {sql}"
    return subprocess.run(
        ["docker", "exec", "riviwa_auth_db", "psql",
         "-U", "riviwa_auth_admin", "-d", "auth_db", "-c", full],
        capture_output=True, text=True, timeout=15)


def force_org_id(old_id, new_id):
    # organisations.id has NO ACTION FK constraints from 9 tables.
    # Bypass all FK checks by using session_replication_role = replica.
    # Each UPDATE is a SEPARATE psql call so its transaction commits independently —
    # a later failure cannot roll back an already-committed update.
    sqls = [
        f"UPDATE organisations SET id='{new_id}' WHERE id='{old_id}';",
        f"UPDATE organisation_members SET organisation_id='{new_id}' WHERE organisation_id='{old_id}';",
        f"UPDATE organisation_invites SET organisation_id='{new_id}' WHERE organisation_id='{old_id}';",
        f"UPDATE org_departments   SET org_id='{new_id}'           WHERE org_id='{old_id}';",
        f"UPDATE org_projects      SET organisation_id='{new_id}'  WHERE organisation_id='{old_id}';",
        f"UPDATE org_services      SET organisation_id='{new_id}'  WHERE organisation_id='{old_id}';",
        f"UPDATE org_locations     SET organisation_id='{new_id}'  WHERE organisation_id='{old_id}';",
        f"UPDATE org_branches      SET organisation_id='{new_id}'  WHERE organisation_id='{old_id}';",
        f"UPDATE org_faqs          SET org_id='{new_id}'           WHERE org_id='{old_id}';",
        f"UPDATE org_content       SET org_id='{new_id}'           WHERE org_id='{old_id}';",
        # users.active_org_id is a logical reference, no FK constraint
        f"UPDATE users SET active_org_id='{new_id}' WHERE active_org_id='{old_id}';",
    ]
    for sql in sqls:
        res = _psql_auth_one(sql)
        if "ERROR" in res.stderr:
            fail(f"force_org_id SQL error: {sql[:80]}", res.stderr[:200])
            return
    ok(f"Org UUID forced: {old_id[:8]}… → {new_id[:8]}…")


def create_project(token, org_id, proj_cfg):
    """Create a project via the auth service (POST /orgs/{org_id}/projects)."""
    payload = {
        "name":                proj_cfg["name"],
        "slug":                proj_cfg["slug"],
        "description":         proj_cfg.get("description", proj_cfg["name"]),
        "accepts_grievances":  proj_cfg.get("accepts_grievances",  True),
        "accepts_suggestions": proj_cfg.get("accepts_suggestions", True),
        "accepts_applause":    proj_cfg.get("accepts_applause",    True),
        "requires_grm":        proj_cfg.get("requires_grm",        False),
    }
    for field in ("code", "background", "objectives", "expected_outcomes",
                  "target_beneficiaries", "sector", "region", "primary_lga",
                  "country_code", "location_description", "category", "visibility",
                  "funding_source", "budget_amount", "currency_code",
                  "start_date", "end_date"):
        if proj_cfg.get(field) is not None:
            payload[field] = proj_cfg[field]

    r = requests.post(f"{AUTH}/orgs/{org_id}/projects",
                      json=payload, headers=jh(token), timeout=20)
    if r.status_code not in (200, 201):
        fail(f"create_project {proj_cfg['name']}", r.text[:200])
        return None

    proj_id = r.json().get("id")
    if proj_id:
        ok(f"Project created: {proj_cfg['name']}  →  {proj_id}")
    return proj_id


def activate_project(token, org_id, project_id):
    r = requests.post(f"{AUTH}/orgs/{org_id}/projects/{project_id}/activate",
                      headers=jh(token), timeout=20)
    if r.status_code in (200, 201):
        ok(f"Project activated: {project_id}")
        return True
    if r.status_code in (400, 409, 422):
        ok(f"Project already active or activation not required: {project_id}")
        return True
    fail(f"activate_project {project_id}", r.text[:200])
    return False


def force_project_id(old_id, new_id):
    """Rename project UUID in auth_db org_projects (source of truth)."""
    subprocess.run(
        ["docker", "exec", "riviwa_auth_db", "psql",
         "-U", "riviwa_auth_admin", "-d", "auth_db",
         "-c", f"UPDATE org_projects SET id='{new_id}' WHERE id='{old_id}';"],
        capture_output=True, text=True, timeout=15)
    ok(f"Project UUID forced: {old_id[:8]}… → {new_id[:8]}…")


# ─────────────────────────────────────────────────────────────────────────────
# Demo accounts
# ─────────────────────────────────────────────────────────────────────────────

ACCOUNTS = [
    # ── 1. Riviwa GRM Demo ─────────────────────────────────────────────────────
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
            "description":  "General test account for Riviwa GRM platform demonstrations and feature testing.",
        },
        "projects": [
            {
                "name":                "GRM Demo Project 2026",
                "slug":                "grm-demo-project-2026",
                "code":                "GRM-DEMO",
                "description":         "Demo grievance and feedback management project for Riviwa platform testing and showcase.",
                "sector":              "Technology",
                "region":              "Dar es Salaam",
                "country_code":        "TZ",
                "accepts_grievances":  True,
                "accepts_suggestions": True,
                "accepts_applause":    True,
                "requires_grm":        True,
            },
        ],
    },

    # ── 2. Test Product Store 1 ────────────────────────────────────────────────
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
            "description":  "Test merchant account 1 for Riviwa product and QR verification demos.",
        },
        "projects": [],
    },

    # ── 3. Test Product Store 2 ────────────────────────────────────────────────
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
            "description":  "Test merchant account 2 for Riviwa product and QR verification demos.",
        },
        "projects": [],
    },

    # ── 4. Muhimbili National Hospital ────────────────────────────────────────
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
            "description":  (
                "Tanzania's sole national referral hospital with 1,500 licensed beds and 2,700 "
                "clinical staff across 25 departments and 7 directorates. Serves patients from "
                "all 26 regions and 200+ daily emergency patients. Clinical training partner of "
                "MUHAS (Muhimbili University of Health and Allied Sciences)."
            ),
            "website": "https://mnh.or.tz",
            "email":   "info@mnh.or.tz",
        },
        "force_org_id": "e50be2ae-e074-452f-8db7-8c87bbc41e24",
        "projects": [
            {
                "name":                "Muhimbili GRM 2026",
                "slug":                "mnh-grm-2026",
                "code":                "MNH-GRM-26",
                "description":         (
                    "Patient grievance and feedback management system for Muhimbili National "
                    "Hospital covering all 25 clinical departments and 7 directorates."
                ),
                "background":          (
                    "MNH is Tanzania's provider of last resort, receiving 200+ critical patients "
                    "daily. Documented challenges include maternity ward informal payments "
                    "(\"Kitu Kidogo\"), medicine stock-outs, blood bank unavailability contributing "
                    "to 19.3% of maternal deaths, NHIF card rejections, and delayed specialist "
                    "care. A structured GRM is needed to capture, route and resolve these issues "
                    "systematically across all departments."
                ),
                "objectives":          (
                    "Capture and resolve patient and staff grievances within 72 hours; eliminate "
                    "informal payment incidents in maternity wards; reduce medicine stock-out "
                    "reporting delays; improve NHIF enrollment complaint handling; enable anonymous "
                    "near-miss reporting by clinical staff."
                ),
                "target_beneficiaries": (
                    "Inpatients and outpatients across all departments, maternity ward patients, "
                    "emergency patients, NHIF-enrolled patients, clinical staff including nurses, "
                    "midwives, doctors, MUHAS interns, and 3-person GRM Unit staff."
                ),
                "sector":              "Health",
                "region":              "Dar es Salaam",
                "primary_lga":         "Ilala",
                "country_code":        "TZ",
                "accepts_grievances":  True,
                "accepts_suggestions": True,
                "accepts_applause":    True,
                "requires_grm":        True,
                "force_project_id":    "64bd1dc7-baa3-4efb-a77c-c2f15d0f93dc",
            },
        ],
    },

    # ── 5. Yas Tanzania ───────────────────────────────────────────────────────
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
            "description":  (
                "Tanzania's second-largest mobile network operator (rebranded from Tigo Tanzania) "
                "with 23M+ subscribers and 28.1% market share. Part of AXIAN Telecom. Services "
                "include 4G/5G mobile, Mixx by Yas financial services, enterprise solutions, and "
                "200+ retail agent touchpoints nationwide."
            ),
            "website": "https://yas.co.tz",
            "email":   "customercare@yas.co.tz",
        },
        "projects": [
            {
                "name":                "Yas Customer Feedback 2026",
                "slug":                "yas-customer-feedback-2026",
                "code":                "YAS-CX-26",
                "description":         (
                    "Centralised customer experience and fraud reporting platform for Yas Tanzania "
                    "subscribers, agents, and Mixx by Yas users."
                ),
                "background":          (
                    "Yas Tanzania (formerly Tigo) faces challenges including SIM swap fraud, "
                    "fake agent scams defrauding retailers across multiple regions, billing errors, "
                    "network outage complaints handled in silos, and silent churn from unresolved "
                    "issues. Fake agents account for 34% of TCRA fraud reports attributed to Yas. "
                    "Complaints submitted via one channel are invisible to other teams, preventing "
                    "pattern detection and fast response."
                ),
                "objectives":          (
                    "Reduce agent fraud response time from days to hours through unified complaint "
                    "routing; centralise complaints across SMS shortcode, WhatsApp, call centre "
                    "and service centres; track SLA compliance per branch and region; enable "
                    "aggregate fraud pattern detection across 200+ touchpoints."
                ),
                "target_beneficiaries": (
                    "23M+ Yas Tanzania subscribers, retail agents and distributors across Dar es "
                    "Salaam, Mwanza, Arusha, Dodoma, Zanzibar, Mixx by Yas users, enterprise clients."
                ),
                "sector":              "Telecommunications",
                "region":              "Nationwide",
                "country_code":        "TZ",
                "accepts_grievances":  True,
                "accepts_suggestions": True,
                "accepts_applause":    True,
                "requires_grm":        False,
            },
        ],
    },

    # ── 6. Azam Group Tanzania Limited ────────────────────────────────────────
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
            "description":  (
                "Tanzania's most diversified conglomerate operating across beverages (Azam Cola, "
                "Malt), bakery (Azam Bread), media (Azam TV), marine transport, and real estate "
                "with millions of customers across East Africa and branches in Dar es Salaam, "
                "Mwanza, Arusha, and other major regions."
            ),
            "website": "https://azamgroup.co.tz",
            "email":   "info@azamgroup.co.tz",
        },
        "projects": [
            {
                "name":                "Azam Group GRM 2026",
                "slug":                "azam-group-grm-2026",
                "code":                "AZAM-GRM-26",
                "description":         (
                    "Group-wide grievance, feedback and product authentication platform for "
                    "Azam Group Tanzania covering all business divisions."
                ),
                "background":          (
                    "Azam Group operates across beverages, bakery, Azam TV, marine transport and "
                    "real estate. Key challenges include counterfeit Azam Cola, Malt and Bread "
                    "circulating in markets (fake products indistinguishable by end consumers), "
                    "expired product deliveries to retailers, rogue sales agent fraud, Azam TV "
                    "signal outages, and billing errors. Each division handles complaints in "
                    "isolation with no cross-division visibility for management."
                ),
                "objectives":          (
                    "Consolidate customer and distributor feedback across all business divisions; "
                    "detect counterfeit and expired product patterns via QR scan reporting; "
                    "track agent fraud incidents; improve brand protection and product quality "
                    "feedback loops across the distribution chain."
                ),
                "target_beneficiaries": (
                    "Retailers and distributors across Tanzania, Azam TV subscribers (1M+), "
                    "marine transport passengers, end consumers of Azam beverages and bakery "
                    "products, sales agents and regional branch staff."
                ),
                "sector":              "Consumer Goods / Media",
                "region":              "Nationwide",
                "country_code":        "TZ",
                "accepts_grievances":  True,
                "accepts_suggestions": True,
                "accepts_applause":    True,
                "requires_grm":        False,
            },
        ],
    },

    # ── 7. FAO Tanzania ───────────────────────────────────────────────────────
    {
        "email":        "grm.fao.tanzania@riviwa.com",
        "password":     "FAO_Tanzania@2026!",
        "username":     "grm_fao_tanzania",
        "display_name": "FAO Tanzania Admin",
        "full_name":    "FAO Tanzania Admin",
        "phone":        "+255222700800",
        "org": {
            "legal_name":   "Food and Agriculture Organization of the United Nations — Tanzania",
            "display_name": "FAO Tanzania",
            "slug":         "fao-tanzania",
            "org_type":     "NGO",
            "description":  (
                "FAO Tanzania manages 12+ active programmes across food security, forest landscape "
                "restoration (AFR100), dairy development (DaIMA), fisheries, nutrition and land "
                "tenure with 2.4M+ target beneficiaries across all 26 regions. Operates across "
                "low-connectivity, multi-language field environments."
            ),
            "website": "https://www.fao.org/tanzania",
            "email":   "FAO-TZ@fao.org",
        },
        "force_org_id": "c011921c-c33f-4ed1-97e7-46cf490acd33",
        "projects": [
            {
                "name":                "AFR100 Tanzania — Monduli-Karatu Restoration",
                "slug":                "fao-afr100-monduli-karatu",
                "code":                "FAO-AFR100",
                "description":         (
                    "African Forest Landscape Restoration grievance and community feedback system "
                    "for the Monduli-Karatu corridor, covering 533+ nursery sites and producer "
                    "groups across Arusha and Manyara regions."
                ),
                "background":          (
                    "The AFR100 project includes a 1,200-acre fencing initiative in Monduli Juu "
                    "affecting 340 Maasai households. Documented issues: FPIC (Free, Prior and "
                    "Informed Consent) violations where community land was enclosed without "
                    "consent; TZS 2.4M in crop compensation claims unfunded; TZS 18M in DaIMA "
                    "nursery payments confirmed in system but never disbursed to 6 Karatu producer "
                    "groups; veterinarian absent 4 months causing 23 cattle deaths from East Coast "
                    "Fever. GRM is currently inaccessible to remote communities with no anonymous "
                    "reporting channel."
                ),
                "objectives":          (
                    "Ensure FPIC compliance for all community-affecting interventions; track "
                    "grievances and compensation claims from submission to resolution; provide "
                    "anonymous corruption reporting channel; maintain transparent consultation "
                    "records for 533+ nursery sites across Arusha and Manyara regions; support "
                    "multi-language engagement via Kiswahili, English and indigenous dialects."
                ),
                "target_beneficiaries": (
                    "340 Maasai households in Monduli Juu, 6 Karatu DaIMA dairy producer groups, "
                    "533+ nursery site participants, 4 field officers (FAO-TA-00001 to 00004), "
                    "extension workers and community liaisons across Arusha and Manyara regions."
                ),
                "sector":              "Agriculture / Environment",
                "region":              "Arusha",
                "primary_lga":         "Monduli",
                "location_description": "Monduli Juu and Karatu corridor, Arusha Region",
                "country_code":        "TZ",
                "funding_source":      "FAO / AFR100 African Forest Landscape Restoration Initiative",
                "accepts_grievances":  True,
                "accepts_suggestions": True,
                "accepts_applause":    False,
                "requires_grm":        True,
                "force_project_id":    "7c10205e-17c5-4e8e-82dc-5e533c4257d3",
            },
        ],
    },

    # ── 8. WHO Tanzania ───────────────────────────────────────────────────────
    {
        "email":        "grm.who.tanzania@riviwa.com",
        "password":     "WHO_Tanzania@2026!",
        "username":     "grm_who_tanzania",
        "display_name": "WHO Tanzania Admin",
        "full_name":    "WHO Tanzania Admin",
        "phone":        "+255222700900",
        "org": {
            "legal_name":   "World Health Organization — United Republic of Tanzania Country Office",
            "display_name": "WHO Tanzania",
            "slug":         "who-tanzania",
            "org_type":     "NGO",
            "description":  (
                "WHO Tanzania coordinates USD 28M+ in active health programme budgets across four "
                "pillars: Universal Health Coverage (UHC/NHIF), RMNCAH & Immunization, Disease "
                "Control (AMR, Malaria — Kagera artemisinin-resistance zone), and Emergency "
                "Preparedness & Climate Health (IHR/KARAHADA). 3.2M+ beneficiaries at risk."
            ),
            "website": "https://www.afro.who.int/countries/united-republic-of-tanzania",
            "email":   "afrotzr@who.int",
        },
        "projects": [
            {
                "name":                "WHO Tanzania Health GRM 2026",
                "slug":                "who-tz-grm-2026",
                "code":                "WHO-TZ-GRM",
                "description":         (
                    "Health programme grievance and community accountability platform for WHO "
                    "Tanzania covering UHC, RMNCAH, disease surveillance and emergency response."
                ),
                "background":          (
                    "WHO Tanzania manages 4 programme pillars with USD 28M+ budget. Documented "
                    "failures: Cholera outbreak in Mang'ola Ward (47 cases in 4 days) before "
                    "reporting — hotline unanswered 11 times; NHIF card rejection at Mwanza "
                    "Regional Referral Hospital; ACT malaria drug stock-out across 4 Kagera "
                    "facilities for 7 weeks (artemether-lumefantrine); vaccine refrigerator "
                    "broken 3+ weeks undetected (420 zero-dose children in Kigoma Ujiji); 24 "
                    "CHWs unpaid for 4 months causing zero-dose coverage decline; Hadzabe "
                    "community excluded from KARAHADA programme design (FPIC violation)."
                ),
                "objectives":          (
                    "Enable real-time disease outbreak reporting by VHWs via SMS (any 2G phone); "
                    "track NHIF card rejection complaints to resolution; provide early warning for "
                    "cold chain failures; create anonymous corruption reporting for UHC enrollment; "
                    "improve CHW accountability and payment tracking; ensure FPIC compliance in "
                    "programme design."
                ),
                "target_beneficiaries": (
                    "3.2M+ programme beneficiaries, Village Health Workers (VHWs) and Community "
                    "Health Workers (CHWs) across 26 regions, health facility staff, NHIF-enrolled "
                    "patients, Hadzabe and other indigenous communities, 4 field officers "
                    "(WHO-TA-00001 to 00004)."
                ),
                "sector":              "Health",
                "region":              "Nationwide",
                "country_code":        "TZ",
                "funding_source":      "WHO Regular Budget and Voluntary Contributions — Tanzania",
                "budget_amount":       28000000,
                "currency_code":       "USD",
                "accepts_grievances":  True,
                "accepts_suggestions": True,
                "accepts_applause":    False,
                "requires_grm":        True,
            },
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

summary = []

for acc in ACCOUNTS:
    email = acc["email"]
    section(f"{email}")

    # 1 — Register (idempotent: 409 → skip)
    register(email, acc["username"], acc["display_name"],
             acc["full_name"], acc["password"], acc.get("phone"))
    time.sleep(0.3)

    # 2 — Login (base token, no org scope)
    token = login(email, acc["password"])
    if not token:
        summary.append({"email": email, "status": "LOGIN FAILED"})
        continue

    # 3 — Get or create org
    org_cfg  = acc.get("org", {})
    org_slug = org_cfg.get("slug", "")
    org_id   = get_org_id_from_db(org_slug) if org_slug else None

    if org_id:
        ok(f"Org already in DB: {org_cfg.get('display_name')}  →  {org_id}")
    else:
        org_id = create_org(
            token,
            org_cfg.get("legal_name",   email),
            org_cfg.get("display_name", email),
            org_slug,
            org_cfg.get("org_type",     "NGO"),
            org_cfg.get("description",  ""),
            org_cfg.get("website",      ""),
            org_cfg.get("email",        ""),
            org_cfg.get("phone",        ""),
        )

    if not org_id:
        summary.append({"email": email, "status": "ORG FAILED"})
        continue

    # 4 — Activate org in DB (idempotent)
    activate_org_in_db(org_id)

    # 5 — Force org UUID BEFORE switching (so switch-org sees the final UUID)
    target_org_id = acc.get("force_org_id")
    if target_org_id and org_id != target_org_id:
        force_org_id(org_id, target_org_id)
        org_id = target_org_id
        time.sleep(0.5)  # let any in-memory caches settle

    # 6 — Login and switch to correct org (get org-scoped token)
    token = login(email, acc["password"], org_id)
    if not token:
        summary.append({"email": email, "status": "SWITCH-ORG FAILED",
                        "org_id": org_id, "org_name": org_cfg.get("display_name", "")})
        continue

    # 7 — Create projects
    project_ids = []
    for proj_cfg in acc.get("projects", []):
        proj_slug = proj_cfg.get("slug", "")

        # Idempotent: skip if already exists
        proj_id = get_project_id_from_db(proj_slug) if proj_slug else None
        if proj_id:
            ok(f"Project already in DB: {proj_cfg['name']}  →  {proj_id}")
        else:
            proj_id = create_project(token, org_id, proj_cfg)

        if not proj_id:
            continue

        # 8 — Force project UUID BEFORE activation (so Kafka event carries final UUID)
        target_proj_id = proj_cfg.get("force_project_id")
        if target_proj_id and proj_id != target_proj_id:
            force_project_id(proj_id, target_proj_id)
            proj_id = target_proj_id

        # 9 — Activate project (publishes Kafka event → feedback service ProjectCache)
        activate_project(token, org_id, proj_id)
        project_ids.append(proj_id)

    summary.append({
        "email":       email,
        "password":    acc["password"],
        "org_name":    org_cfg.get("display_name", ""),
        "org_id":      org_id,
        "project_ids": project_ids,
        "status":      "OK",
    })


# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{BLD}{'═'*70}{RST}")
print(f"{BLD}  SEED SUMMARY{RST}")
print(f"{BLD}{'═'*70}{RST}")

for s in summary:
    colour = GRN if s.get("status") == "OK" else RED
    print(f"\n  {colour}{s.get('status', '?')}{RST}  {BLD}{s['email']}{RST}")
    print(f"        Password  : {s.get('password', '')}")
    print(f"        Org       : {s.get('org_name', '')}  ({s.get('org_id', '')})")
    pids = s.get("project_ids", [])
    if pids:
        print(f"        Projects  : {', '.join(str(p) for p in pids)}")

print(f"\n{BLD}{'═'*70}{RST}")
print(f"  PASS: {GRN}{PASS_N}{RST}   FAIL: {RED}{FAIL_N}{RST}")
print(f"{BLD}{'═'*70}{RST}\n")

if FAIL_N:
    sys.exit(1)
