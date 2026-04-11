#!/usr/bin/env python3
"""
Riviwa End-to-End Endpoint Test
================================
Chains every endpoint from user registration through feedback resolution.
Runs exactly like Postman would — each step's output feeds the next.

Usage
-----
  # Full flow (registers a brand-new user, prompts for OTPs)
  python scripts/test_endpoints.py

  # Skip auth — supply an existing org-scoped access token
  python scripts/test_endpoints.py --token eyJhbGciOiJIUzI1NiJ9...

  # Custom server
  python scripts/test_endpoints.py --base-url https://api.riviwa.com

  # Skip the org-verify step (requires a separate platform-admin token)
  python scripts/test_endpoints.py --skip-verify

Requirements
------------
  pip install requests
"""

import argparse
import json
import sys
import time
from typing import Any, Dict, Optional

import requests

# ─── Terminal colours ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

PASS = f"{GREEN}✓{RESET}"
FAIL = f"{RED}✗{RESET}"
SKIP = f"{YELLOW}⊘{RESET}"
INFO = f"{CYAN}ℹ{RESET}"


# ══════════════════════════════════════════════════════════════════════════════
# Test Runner
# ══════════════════════════════════════════════════════════════════════════════

class RiviwaTestRunner:
    def __init__(self, base_url: str, access_token: Optional[str] = None):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.results: list[tuple[str, bool, int]] = []

        # ── IDs accumulated during the run ─────────────────────────────────
        self.access_token:    Optional[str] = None
        self.refresh_token:   Optional[str] = None
        self.user_id:         Optional[str] = None
        self.org_id:          Optional[str] = None
        self.project_id:      Optional[str] = None
        self.stage_id:        Optional[str] = None
        self.subproject_id:   Optional[str] = None
        self.stakeholder_id:  Optional[str] = None
        self.contact_id:      Optional[str] = None
        self.activity_id:     Optional[str] = None
        self.engagement_id:   Optional[str] = None
        self.category_slug:   str = "compensation"
        self.feedback_id:     Optional[str] = None
        self.tracking_number: Optional[str] = None

        if access_token:
            self._auth(access_token)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _auth(self, token: str):
        self.access_token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _call(
        self,
        method:          str,
        path:            str,
        body:            Optional[Dict] = None,
        expected_status: int            = None,
        label:           str            = None,
        show_response:   bool           = True,
    ) -> Optional[Dict]:
        url   = f"{self.base}{path}"
        label = label or f"{method} {path}"

        try:
            resp = self.session.request(
                method, url,
                json=body if body is not None else None,
                timeout=30,
            )
        except requests.RequestException as exc:
            print(f"  {FAIL} {BOLD}{label}{RESET}  {RED}NETWORK ERROR: {exc}{RESET}")
            self.results.append((label, False, 0))
            return None

        ok_codes = {200, 201, 204} if expected_status is None else {expected_status}
        ok = resp.status_code in ok_codes

        status_colour = GREEN if ok else RED
        print(f"  {'  ' if ok else ''}{PASS if ok else FAIL} "
              f"{BOLD}{label}{RESET}  "
              f"{status_colour}HTTP {resp.status_code}{RESET}")

        try:
            data = resp.json()
        except Exception:
            data = {}

        if not ok:
            snippet = json.dumps(data, indent=2)[:600] if data else resp.text[:600]
            print(f"    {RED}{snippet}{RESET}")
            self.results.append((label, False, resp.status_code))
            return None

        if show_response and data:
            # Print key fields only — avoids walls of text
            preview = {k: v for k, v in data.items()
                       if k in ("id", "feedback_id", "tracking_number",
                                "session_token", "continuation_token",
                                "login_token", "access_token", "org_id",
                                "status", "action", "otp_channel",
                                "otp_destination", "message", "count")}
            if preview:
                print(f"    {DIM}{json.dumps(preview)}{RESET}")

        self.results.append((label, True, resp.status_code))
        return data

    def _heading(self, title: str):
        bar = "─" * 66
        print(f"\n{CYAN}{bar}{RESET}")
        print(f"{CYAN}{BOLD} {title}{RESET}")
        print(f"{CYAN}{bar}{RESET}")

    def _save(self, key: str, value: Any):
        if value:
            setattr(self, key, str(value))
            print(f"    {INFO} saved {key} = {DIM}{str(value)[:60]}{RESET}")

    # ── summary ───────────────────────────────────────────────────────────────

    def print_summary(self):
        passed = sum(1 for _, ok, _ in self.results if ok)
        failed = sum(1 for _, ok, _ in self.results if not ok)
        total  = len(self.results)
        bar    = "═" * 66

        print(f"\n{BOLD}{bar}{RESET}")
        print(f"{BOLD} TEST SUMMARY — {passed}/{total} passed{RESET}")
        print(f"{BOLD}{bar}{RESET}")

        for label, ok, code in self.results:
            icon = PASS if ok else FAIL
            colour = GREEN if ok else RED
            print(f"  {icon} {colour}{label}{RESET}  HTTP {code}")

        print(f"\n{BOLD}{bar}{RESET}")
        if failed:
            print(f"{RED}{BOLD} {failed} FAILED{RESET}")
        else:
            print(f"{GREEN}{BOLD} All {total} steps passed!{RESET}")
        print(f"{BOLD}{bar}{RESET}\n")

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 1 — User Registration & Authentication
    # ══════════════════════════════════════════════════════════════════════════

    def phase1_auth(self):
        self._heading("PHASE 1 — User Registration & Authentication")

        # Step 1 — register init
        body = {
            "email":        "testuser@riviwa.dev",
            "phone_number": "",
            "username":     "riviwatest01",
            "display_name": "Riviwa Tester",
            "full_name":    "Riviwa Test User",
            "country_code": "TZ",
            "fingerprint":  "",
            "behavioral":   "",
        }
        r = self._call("POST", "/auth/register/init", body,
                       label="[1] POST /auth/register/init")
        if not r:
            return False
        session_token = r.get("session_token")
        otp_channel   = r.get("otp_channel", "email")
        otp_dest      = r.get("otp_destination", "testuser@riviwa.dev")
        self._save("_session_token", session_token)

        # Step 2 — verify OTP
        print(f"\n  {YELLOW}►{RESET} OTP sent via {otp_channel} to {otp_dest}")
        otp = input(f"  {BOLD}Enter OTP code:{RESET} ").strip()
        r = self._call("POST", "/auth/register/verify-otp",
                       {"session_token": session_token, "otp_code": otp},
                       label="[2] POST /auth/register/verify-otp")
        if not r:
            return False
        continuation_token = r.get("continuation_token")
        self._save("_continuation_token", continuation_token)

        # Step 3 — complete registration
        r = self._call("POST", "/auth/register/complete",
                       {"continuation_token": continuation_token,
                        "password": "StrongPass@2026!"},
                       expected_status=201,
                       label="[3] POST /auth/register/complete")
        if not r:
            return False
        print(f"    {INFO} action = {r.get('action')}")

        # Step 4 — login
        r = self._call("POST", "/auth/login",
                       {"identifier": "testuser@riviwa.dev",
                        "password":   "StrongPass@2026!"},
                       label="[4] POST /auth/login")
        if not r:
            return False
        login_token = r.get("login_token")
        otp_channel = r.get("otp_channel", "email")
        otp_dest    = r.get("otp_destination", "testuser@riviwa.dev")
        self._save("_login_token", login_token)

        # Step 5 — verify login OTP
        print(f"\n  {YELLOW}►{RESET} Login OTP sent via {otp_channel} to {otp_dest}")
        otp = input(f"  {BOLD}Enter Login OTP:{RESET} ").strip()
        r = self._call("POST", "/auth/login/verify-otp",
                       {"login_token": login_token, "otp_code": otp},
                       label="[5] POST /auth/login/verify-otp")
        if not r:
            return False

        self._auth(r["access_token"])
        self._save("refresh_token", r.get("refresh_token"))
        print(f"    {GREEN}Tokens stored. Access token active.{RESET}")
        return True

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 2 — Organisation
    # ══════════════════════════════════════════════════════════════════════════

    def phase2_org(self, skip_verify: bool = False):
        self._heading("PHASE 2 — Organisation Setup")

        # Step 6 — create org
        r = self._call("POST", "/orgs", {
            "legal_name":          "Riviera Infrastructure Ltd",
            "display_name":        "Riviera Infra",
            "slug":                f"riviera-infra-{int(time.time())}",
            "org_type":            "CORPORATE",
            "description":         "Infrastructure development and GRM testing",
            "country_code":        "TZ",
            "timezone":            "Africa/Dar_es_Salaam",
            "registration_number": "TZ-REG-2026-001",
            "support_email":       "support@riviera-infra.tz",
            "support_phone":       "+255712000001",
        }, expected_status=201, label="[6] POST /orgs")
        if not r:
            return False
        self._save("org_id", r.get("id"))

        # Step 7 — get org detail
        self._call("GET", f"/orgs/{self.org_id}",
                   label="[7] GET /orgs/{org_id}")

        # Step 8 — verify org (platform admin only — may 403 with regular user)
        if skip_verify:
            print(f"  {SKIP} [8] POST /orgs/{{org_id}}/verify  — skipped (--skip-verify)")
            self.results.append(("[8] POST /orgs/{org_id}/verify (skipped)", True, 0))
        else:
            r2 = self._call("POST", f"/orgs/{self.org_id}/verify",
                            {"reason": "Documents verified — test run"},
                            label="[8] POST /orgs/{org_id}/verify")
            if not r2:
                print(f"    {YELLOW}(Org verify needs platform admin token — run with --skip-verify "
                      f"if your token is not admin){RESET}")

        # Step 9 — switch to org context → new token with org_id claim
        r = self._call("POST", "/auth/switch-org",
                       {"org_id": self.org_id},
                       label="[9] POST /auth/switch-org")
        if not r:
            return False
        self._auth(r["tokens"]["access_token"])
        self._save("refresh_token", r["tokens"].get("refresh_token"))
        print(f"    {GREEN}Switched to org context. New token stored.{RESET}")
        return True

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 3 — Project & Stages
    # ══════════════════════════════════════════════════════════════════════════

    def phase3_project(self):
        self._heading("PHASE 3 — Project, Stages & Sub-Projects")

        # Step 10 — create project
        r = self._call("POST", f"/orgs/{self.org_id}/projects", {
            "name":                "Dar es Salaam Road Rehabilitation",
            "code":                "DSRR-2026",
            "slug":                f"dsrr-{int(time.time())}",
            "category":            "infrastructure",
            "sector":              "transport",
            "description":         "Rehabilitation of urban roads in Ilala and Kinondoni districts",
            "country_code":        "TZ",
            "region":              "Dar es Salaam",
            "primary_lga":         "Ilala",
            "start_date":          "2026-05-01",
            "end_date":            "2028-04-30",
            "accepts_grievances":  True,
            "accepts_suggestions": True,
            "accepts_applause":    True,
        }, expected_status=201, label="[10] POST /orgs/{org_id}/projects")
        if not r:
            return False
        self._save("project_id", r.get("id"))

        # Step 11 — list projects
        self._call("GET", f"/orgs/{self.org_id}/projects",
                   label="[11] GET /orgs/{org_id}/projects")

        # Step 12 — get project detail
        self._call("GET", f"/orgs/{self.org_id}/projects/{self.project_id}",
                   label="[12] GET /orgs/{org_id}/projects/{project_id}")

        # Step 13 — create stage
        r = self._call("POST", f"/orgs/{self.org_id}/projects/{self.project_id}/stages", {
            "name":                "Phase 1 — Site Preparation",
            "stage_order":         1,
            "description":         "Land clearing and utility relocation",
            "objectives":          "Complete site assessment and relocate underground utilities",
            "start_date":          "2026-05-01",
            "end_date":            "2026-10-31",
            "accepts_grievances":  True,
            "accepts_suggestions": True,
            "accepts_applause":    False,
        }, expected_status=201, label="[13] POST /orgs/{org_id}/projects/{project_id}/stages")
        if not r:
            return False
        self._save("stage_id", r.get("id"))

        # Step 14 — list stages
        self._call("GET", f"/orgs/{self.org_id}/projects/{self.project_id}/stages",
                   label="[14] GET stages")

        # Step 15 — add in-charge to project
        # Use the logged-in user_id if available, else skip gracefully
        r_user = self._call("GET", "/users/me", label="[15a] GET /users/me", show_response=False)
        if r_user:
            self._save("user_id", r_user.get("id"))
            self._call("POST",
                       f"/orgs/{self.org_id}/projects/{self.project_id}/in-charges",
                       {"user_id": self.user_id, "role_title": "Project Director",
                        "duties": "Overall project oversight", "is_lead": True},
                       expected_status=201,
                       label="[15b] POST project in-charge")

        # Step 16 — create sub-project
        r = self._call("POST",
                       f"/orgs/{self.org_id}/projects/{self.project_id}"
                       f"/stages/{self.stage_id}/subprojects", {
            "name":          "Kariakoo Road Widening",
            "code":          "DSRR-SP-001",
            "description":   "Widen Msimbazi Street from 6m to 12m carriageway",
            "objectives":    "Complete road widening within Phase 1 timeline",
            "start_date":    "2026-05-15",
            "end_date":      "2026-09-30",
            "budget_amount": 450000000,
            "currency_code": "TZS",
            "location":      "Kariakoo, Ilala, Dar es Salaam",
            "display_order": 1,
        }, expected_status=201, label="[16] POST subproject")
        if r:
            self._save("subproject_id", r.get("id"))

        # Step 17 — activate project (PLANNING → ACTIVE, fires Kafka)
        self._call("POST",
                   f"/orgs/{self.org_id}/projects/{self.project_id}/activate",
                   label="[17] POST activate project")

        # Step 18 — activate stage (fires Kafka → stakeholder_service syncs)
        self._call("POST",
                   f"/orgs/{self.org_id}/projects/{self.project_id}"
                   f"/stages/{self.stage_id}/activate",
                   label="[18] POST activate stage")

        print(f"\n  {YELLOW}►{RESET} Waiting 3 s for Kafka consumer to sync project to stakeholder_service…")
        time.sleep(3)
        return True

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 4 — Stakeholder Management
    # ══════════════════════════════════════════════════════════════════════════

    def phase4_stakeholders(self):
        self._heading("PHASE 4 — Stakeholder Management")

        # Step 19 — verify project synced to stakeholder_service
        self._call("GET", f"/projects/{self.project_id}",
                   label="[19] GET /projects/{project_id} (stakeholder_service)")

        # Step 20 — register stakeholder
        r = self._call("POST", "/stakeholders", {
            "stakeholder_type":  "pap",
            "entity_type":       "individual",
            "category":          "individual",
            "first_name":        "Juma",
            "last_name":         "Bakari",
            "affectedness":      "negatively_affected",
            "importance_rating": "high",
            "lga":               "Ilala",
            "ward":              "Kariakoo",
            "language_preference": "sw",
            "preferred_channel": "sms",
            "needs_translation": False,
            "needs_transport":   False,
            "needs_childcare":   False,
            "is_vulnerable":     False,
            "notes":             "Land acquisition — 0.5 acres near Kariakoo market",
        }, expected_status=201, label="[20] POST /stakeholders")
        if not r:
            return False
        self._save("stakeholder_id", r.get("id"))

        # Step 21 — list stakeholders
        self._call("GET", "/stakeholders",
                   label="[21] GET /stakeholders")

        # Step 22 — get stakeholder detail
        self._call("GET", f"/stakeholders/{self.stakeholder_id}",
                   label="[22] GET /stakeholders/{id}")

        # Step 23 — add contact
        r = self._call("POST", f"/stakeholders/{self.stakeholder_id}/contacts", {
            "full_name":                    "Amina Bakari",
            "title":                        "Ms.",
            "role_in_org":                  "Spouse / Representative",
            "phone":                        "+255787654321",
            "email":                        "amina.bakari@example.com",
            "preferred_channel":            "phone_call",
            "is_primary":                   True,
            "can_submit_feedback":          True,
            "can_receive_communications":   True,
            "can_distribute_communications": False,
        }, expected_status=201, label="[23] POST /stakeholders/{id}/contacts")
        if r:
            self._save("contact_id", r.get("id"))

        # Step 24 — list contacts
        self._call("GET", f"/stakeholders/{self.stakeholder_id}/contacts",
                   label="[24] GET /stakeholders/{id}/contacts")

        # Step 25 — link stakeholder to project (PAP registration)
        self._call("POST", f"/stakeholders/{self.stakeholder_id}/projects", {
            "project_id":        self.project_id,
            "is_pap":            True,
            "affectedness":      "negatively_affected",
            "impact_description": "Land acquisition for road widening affects 0.5 acres of farmland",
        }, expected_status=201, label="[25] POST /stakeholders/{id}/projects (PAP link)")

        # Step 26 — stakeholder project list
        self._call("GET", f"/stakeholders/{self.stakeholder_id}/projects",
                   label="[26] GET /stakeholders/{id}/projects")

        return True

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 5 — Engagement Activities
    # ══════════════════════════════════════════════════════════════════════════

    def phase5_activities(self):
        self._heading("PHASE 5 — Engagement Activities")

        # Step 27 — create activity
        r = self._call("POST", "/activities", {
            "project_id":    self.project_id,
            "stage_id":      self.stage_id,
            "activity_type": "public_meeting",
            "stage":         "planning",
            "title":         "Community Consultation — Kariakoo Ward",
            "description":   "Public consultation to discuss project impacts and compensation",
            "venue":         "Kariakoo Community Hall",
            "lga":           "Ilala",
            "ward":          "Kariakoo",
            "scheduled_at":  "2026-05-15T10:00:00",
            "expected_count": 50,
            "languages_used": ["sw", "en"],
        }, expected_status=201, label="[27] POST /activities")
        if not r:
            return False
        self._save("activity_id", r.get("id"))

        # Step 28 — list activities
        self._call("GET", f"/activities?project_id={self.project_id}",
                   label="[28] GET /activities?project_id=...")

        # Step 29 — get activity detail
        self._call("GET", f"/activities/{self.activity_id}",
                   label="[29] GET /activities/{id}")

        # Step 30 — log attendance
        attendance_body = {
            "contact_id":       self.contact_id,
            "attendance_status": "attended",
            "concerns_raised":  "Compensation amount is below market rate for agricultural land",
            "response_given":   "PIU will commission an independent valuation within 30 days",
            "feedback_submitted": False,
        }
        r = self._call("POST", f"/activities/{self.activity_id}/attendances",
                       attendance_body, expected_status=201,
                       label="[30] POST /activities/{id}/attendances")
        if r:
            self._save("engagement_id", r.get("id"))

        # Step 31 — mark activity conducted
        self._call("PATCH", f"/activities/{self.activity_id}", {
            "status":          "conducted",
            "conducted_at":    "2026-05-15T12:30:00",
            "actual_count":    47,
            "female_count":    21,
            "vulnerable_count": 5,
            "summary_of_issues":    "Key concern: compensation below market rate",
            "summary_of_responses": "Independent valuation to be commissioned within 30 days",
            "action_items": [
                {"item": "Commission independent land valuation", "due_date": "2026-06-15",
                 "responsible": "PIU Land Officer"}
            ],
        }, label="[31] PATCH /activities/{id} (mark conducted)")

        # Step 32 — get activity with attendances
        self._call("GET", f"/activities/{self.activity_id}",
                   label="[32] GET /activities/{id} (with attendances)")

        # Step 33 — stakeholder analysis matrix
        self._call("GET", f"/stakeholders/analysis?project_id={self.project_id}",
                   label="[33] GET /stakeholders/analysis (SEP matrix)")

        return True

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 6 — Feedback
    # ══════════════════════════════════════════════════════════════════════════

    def phase6_feedback(self):
        self._heading("PHASE 6 — Feedback Submission & Lifecycle")

        # Step 34 — create category
        r = self._call("POST", "/categories", {
            "project_id":    self.project_id,
            "name":          "Compensation",
            "slug":          "compensation",
            "feedback_type": "grievance",
            "description":   "Issues related to land acquisition compensation and valuation",
            "source":        "manual",
        }, expected_status=201, label="[34] POST /categories")
        if r:
            self.category_slug = r.get("slug", "compensation")

        # Step 35 — list categories
        self._call("GET", f"/categories?project_id={self.project_id}",
                   label="[35] GET /categories")

        # Step 36 — submit feedback (staff)
        r = self._call("POST", "/feedback", {
            "project_id":                   self.project_id,
            "feedback_type":                "grievance",
            "category":                     self.category_slug,
            "channel":                      "in_person",
            "subject":                      "Compensation below market rate for acquired farmland",
            "description":                  (
                "PAP Juma Bakari claims the TZS 2.5M offered for 0.5 acres of farmland "
                "in Kariakoo is well below the current market rate of TZS 8M per acre. "
                "Land was acquired in April 2026 for road widening."
            ),
            "is_anonymous":                 False,
            "submitter_name":               "Juma Bakari",
            "submitter_phone":              "+255787654321",
            "submitter_type":               "individual",
            "submitter_location_lga":       "Ilala",
            "submitter_location_ward":      "Kariakoo",
            "priority":                     "high",
            "issue_lga":                    "Ilala",
            "issue_ward":                   "Kariakoo",
            "issue_location_description":   "Plot 23, Msimbazi Street near the blue gate",
            "issue_gps_lat":                -6.8161,
            "issue_gps_lng":                39.2894,
            "date_of_incident":             "2026-04-10",
            "subproject_id":                self.subproject_id,
            "submitted_by_stakeholder_id":  self.stakeholder_id,
            "submitted_by_contact_id":      self.contact_id,
            "stakeholder_engagement_id":    self.engagement_id,
            "officer_recorded":             True,
            "internal_notes":               "PAP provided land title documents. Awaiting independent valuation.",
        }, expected_status=201, label="[36] POST /feedback")
        if not r:
            return False
        self._save("feedback_id", r.get("feedback_id") or r.get("id"))
        self._save("tracking_number", r.get("tracking_number"))

        # Step 37 — list feedback
        self._call("GET", f"/feedback?project_id={self.project_id}",
                   label="[37] GET /feedback?project_id=...")

        # Step 38 — get feedback detail
        self._call("GET", f"/feedback/{self.feedback_id}",
                   label="[38] GET /feedback/{feedback_id}")

        # Step 39 — acknowledge
        self._call("PATCH", f"/feedback/{self.feedback_id}/acknowledge", {
            "acknowledgement_note": "Grievance received and logged. PIU will review within 10 working days.",
        }, label="[39] PATCH /feedback/{id}/acknowledge")

        # Step 40 — assign (to self)
        self._call("PATCH", f"/feedback/{self.feedback_id}/assign", {
            "assigned_to_user_id": self.user_id,
            "note": "Assigned to land compensation officer for valuation review",
        }, label="[40] PATCH /feedback/{id}/assign")

        # Step 41 — log action
        self._call("POST", f"/feedback/{self.feedback_id}/actions", {
            "action_type": "field_visit",
            "description": "Visited Juma Bakari's land plot on 20 May 2026. Area confirmed at 0.5 acres.",
            "performed_at": "2026-05-20T09:00:00",
        }, expected_status=201, label="[41] POST /feedback/{id}/actions")

        # Step 42 — resolve
        self._call("POST", f"/feedback/{self.feedback_id}/resolve", {
            "resolution_type":    "compensation_adjusted",
            "resolution_summary": (
                "Independent valuation commissioned. Compensation revised to TZS 4.2M "
                "based on current Ilala district market rates. PAP accepted revised offer."
            ),
            "resolved_at":       "2026-06-10T09:00:00",
            "notify_submitter":  True,
        }, label="[42] POST /feedback/{id}/resolve")

        # Step 43 — close
        self._call("PATCH", f"/feedback/{self.feedback_id}/close", {
            "closing_note": "PAP confirmed acceptance of revised compensation. Case closed.",
        }, label="[43] PATCH /feedback/{id}/close")

        # Step 44 — final detail with full history
        self._call("GET", f"/feedback/{self.feedback_id}",
                   label="[44] GET /feedback/{id} (final state + history)")

        print(f"\n  {GREEN}{BOLD}Tracking number: {self.tracking_number}{RESET}")
        return True

    # ══════════════════════════════════════════════════════════════════════════
    # Main runner
    # ══════════════════════════════════════════════════════════════════════════

    def run(self, skip_auth: bool = False, skip_verify: bool = False):
        print(f"\n{BOLD}{'═' * 66}{RESET}")
        print(f"{BOLD}  Riviwa End-to-End Test  →  {self.base}{RESET}")
        print(f"{BOLD}{'═' * 66}{RESET}")

        if skip_auth:
            print(f"\n  {SKIP} Auth phase skipped — using supplied access token")
            self.results.append(("[1–5] Auth (skipped — token supplied)", True, 0))
            # Still need user_id for in-charge assignment
            r = self._call("GET", "/users/me", label="[0] GET /users/me", show_response=False)
            if r:
                self._save("user_id", r.get("id"))
                self._save("org_id", r.get("active_org_id"))
        else:
            if not self.phase1_auth():
                self.print_summary()
                return

        if not self.org_id:
            if not self.phase2_org(skip_verify=skip_verify):
                self.print_summary()
                return
        else:
            # token already org-scoped
            self.results.append(("[6–9] Org (pre-existing org from token)", True, 0))
            print(f"\n  {SKIP} Org phase skipped — org_id already in token")

        if not self.phase3_project():
            self.print_summary()
            return

        if not self.phase4_stakeholders():
            self.print_summary()
            return

        if not self.phase5_activities():
            self.print_summary()
            return

        self.phase6_feedback()
        self.print_summary()


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Riviwa end-to-end endpoint test — runs every step from "
                    "registration to feedback resolution."
    )
    parser.add_argument(
        "--base-url", default="https://api.riviwa.com/api/v1",
        help="API base URL  (default: https://api.riviwa.com/api/v1)",
    )
    parser.add_argument(
        "--token", default=None,
        help="Supply an existing org-scoped access token to skip registration + login",
    )
    parser.add_argument(
        "--skip-verify", action="store_true",
        help="Skip POST /orgs/{id}/verify (requires platform-admin token)",
    )
    args = parser.parse_args()

    runner = RiviwaTestRunner(
        base_url=args.base_url,
        access_token=args.token,
    )
    runner.run(
        skip_auth=bool(args.token),
        skip_verify=args.skip_verify,
    )


if __name__ == "__main__":
    main()
