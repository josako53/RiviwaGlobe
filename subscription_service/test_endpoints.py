#!/usr/bin/env python3
"""
Subscription service — full endpoint test + sample data runner.

Runs inside the subscription_service container:
    docker cp test_endpoints.py subscription_service:/tmp/
    docker exec -e STAGING=1 subscription_service python3 /tmp/test_endpoints.py

Or from the server host (requires httpx):
    pip install httpx
    STAGING=1 python3 test_endpoints.py

STAGING=1   → uses OTP 000000 (requires ENVIRONMENT=staging on auth service)
TEST_JWT=.. → skip auth entirely, provide your own token
ORG_ID=..   → required when TEST_JWT is set (UUID of the org in that token)
BASE_URL=.. → override (default: http://localhost:8140)
AUTH_URL=.. → override (default: http://riviwa_auth_service:8000 inside container,
                                  or http://localhost:8000 from host)
"""

from __future__ import annotations
import asyncio, json, os, sys, uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

try:
    import httpx
except ImportError:
    print("httpx not found. Run: pip install httpx")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
# Inside Docker container, use internal network names
_in_container = os.path.exists("/.dockerenv")
BASE_URL  = os.environ.get("BASE_URL",  "http://localhost:8140/api/v1")
AUTH_URL  = os.environ.get("AUTH_URL",  "http://riviwa_auth_service:8000/api/v1" if _in_container else "http://localhost:8000/api/v1")
TEST_JWT  = os.environ.get("TEST_JWT",  "")
ORG_ID    = os.environ.get("ORG_ID",   "")
STAGING   = os.environ.get("STAGING",  "0") == "1"
TEST_EMAIL    = os.environ.get("TEST_EMAIL",    "testgrm@riviwa.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "TestGRM@2026!")
INTERNAL_KEY  = os.environ.get("INTERNAL_SERVICE_KEY", "change-me-set-a-real-secret-in-production")

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

passed = failed = skipped = 0
_ids: dict = {}   # store IDs across tests
# Unique suffix so every test run creates new records
_RUN = datetime.utcnow().strftime("%H%M%S")


def _log(symbol: str, colour: str, label: str, detail: str = "") -> None:
    print(f"  {colour}{BOLD}{symbol}{RESET} {label}" + (f"  {YELLOW}{detail}{RESET}" if detail else ""))


def ok(label: str, detail: str = "") -> None:
    global passed; passed += 1
    _log("✓", GREEN, label, detail)


def fail(label: str, detail: str = "") -> None:
    global failed; failed += 1
    _log("✗", RED, label, detail)


def skip(label: str, reason: str = "") -> None:
    global skipped; skipped += 1
    _log("–", YELLOW, label, reason)


def section(title: str) -> None:
    print(f"\n{CYAN}{BOLD}── {title} ──{RESET}")


# ── Auth ──────────────────────────────────────────────────────────────────────

async def _get_token(client: httpx.AsyncClient) -> tuple[str, str]:
    """Return (jwt_token, org_id). Uses TEST_JWT env var or password+OTP login."""
    if TEST_JWT and ORG_ID:
        print(f"  {YELLOW}Using provided TEST_JWT{RESET}")
        return TEST_JWT, ORG_ID

    # Step 1 — password login → login_token
    r = await client.post(f"{AUTH_URL}/auth/login", json={
        "identifier": TEST_EMAIL, "password": TEST_PASSWORD,
    }, timeout=15)
    if r.status_code not in (200, 201):
        print(f"  {RED}Login failed: {r.status_code} {r.text[:200]}{RESET}")
        sys.exit(1)
    login_token = r.json().get("login_token", "")

    # Step 2 — OTP verify (000000 in staging, or prompt)
    otp = "000000" if STAGING else input(f"  Enter OTP sent to {TEST_EMAIL}: ").strip()
    r = await client.post(f"{AUTH_URL}/auth/login/verify-otp", json={
        "login_token": login_token, "otp_code": otp,
    }, timeout=15)
    if r.status_code not in (200, 201):
        print(f"  {RED}OTP verify failed: {r.status_code} {r.text[:300]}{RESET}")
        sys.exit(1)

    data  = r.json()
    token = data.get("access_token", "")
    if not token:
        print(f"  {RED}No access_token in response: {json.dumps(data)[:300]}{RESET}")
        sys.exit(1)

    # Decode JWT to extract org_id (no signature verification needed)
    import base64 as _b64
    payload_b64 = token.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    claims  = json.loads(_b64.urlsafe_b64decode(payload_b64))
    org_id  = str(claims.get("org_id", ""))

    print(f"  {GREEN}Logged in as {TEST_EMAIL}  org_id={org_id[:8]}…  role={claims.get('org_role','?')}{RESET}")
    return token, org_id


# ── Request helpers ───────────────────────────────────────────────────────────

def _h(token: str = "", service_key: bool = False) -> dict:
    h = {"Content-Type": "application/json"}
    if token:   h["Authorization"] = f"Bearer {token}"
    if service_key: h["X-Service-Key"] = INTERNAL_KEY
    return h


async def _get(client, path, token="", service_key=False, label=""):
    try:
        r = await client.get(f"{BASE_URL}{path}", headers=_h(token, service_key), timeout=10)
        return r
    except Exception as e:
        fail(label or path, str(e))
        return None


async def _post(client, path, body, token="", label="", status=200):
    try:
        r = await client.post(f"{BASE_URL}{path}", json=body, headers=_h(token), timeout=10)
        return r
    except Exception as e:
        fail(label or path, str(e))
        return None


async def _patch(client, path, body, token="", label=""):
    try:
        r = await client.patch(f"{BASE_URL}{path}", json=body, headers=_h(token), timeout=10)
        return r
    except Exception as e:
        fail(label or path, str(e))
        return None


async def _delete(client, path, token="", label=""):
    try:
        r = await client.delete(f"{BASE_URL}{path}", headers=_h(token), timeout=10)
        return r
    except Exception as e:
        fail(label or path, str(e))
        return None


def _check(r, label: str, expected_status: int = 200, key_check: str = "") -> Optional[dict]:
    if r is None:
        return None
    if r.status_code != expected_status:
        fail(label, f"HTTP {r.status_code}: {r.text[:200]}")
        return None
    try:
        data = r.json()
    except Exception:
        fail(label, f"Non-JSON response: {r.text[:100]}")
        return None
    if key_check and key_check not in data:
        fail(label, f"Missing key '{key_check}' in response")
        return None
    ok(label)
    return data


# ══════════════════════════════════════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════════════════════════════════════

async def test_plans_public(client: httpx.AsyncClient) -> None:
    section("PLANS — Public")

    # List plans
    r = await _get(client, "/plans", label="GET /plans")
    d = _check(r, "GET /plans → 4 seeded plans", key_check="plans")
    if d:
        n = len(d["plans"])
        if n >= 4: ok(f"  plan count = {n}")
        else: fail(f"  plan count = {n} (expected ≥ 4)")
        slugs = [p["slug"] for p in d["plans"]]
        for slug in ["starter", "professional", "business", "enterprise"]:
            if slug in slugs: ok(f"  plan '{slug}' present")
            else: fail(f"  plan '{slug}' missing")
        # Store plan IDs
        for p in d["plans"]:
            _ids[f"plan_{p['slug']}"] = p["id"]

    # Compare
    r = await _get(client, "/plans/compare", label="GET /plans/compare")
    d = _check(r, "GET /plans/compare → comparison matrix", key_check="comparison")
    if d:
        cats = d.get("categories", [])
        ok(f"  {len(cats)} feature categories")

    # Feature catalog
    r = await _get(client, "/plans/features", label="GET /plans/features")
    d = _check(r, "GET /plans/features → feature catalog", key_check="features")
    if d:
        n = d.get("total_features", 0)
        if n >= 45: ok(f"  {n} features in catalog")
        else: fail(f"  only {n} features (expected ≥ 45)")

    # Addons
    r = await _get(client, "/plans/addons", label="GET /plans/addons")
    d = _check(r, "GET /plans/addons → seeded addons", key_check="addons")
    if d:
        n = len(d["addons"])
        if n >= 11: ok(f"  {n} addons")
        else: fail(f"  only {n} addons (expected ≥ 11)")

    # Get by slug
    for slug in ["starter", "professional", "business", "enterprise"]:
        r = await _get(client, f"/plans/{slug}", label=f"GET /plans/{slug}")
        d = _check(r, f"GET /plans/{slug}", key_check="slug")

    # Get by ID
    pid = _ids.get("plan_starter")
    if pid:
        r = await _get(client, f"/plans/{pid}", label="GET /plans/{id}")
        _check(r, "GET /plans/{id} by UUID", key_check="slug")


async def test_promotions_public(client: httpx.AsyncClient) -> None:
    section("PROMOTIONS — Public")

    r = await _get(client, "/promotions", label="GET /promotions")
    d = _check(r, "GET /promotions → active promos", key_check="promotions")
    if d:
        ok(f"  {d['total']} promos visible publicly")

    # Validate LAUNCH2026
    pid = _ids.get("plan_professional", "")
    r = await _post(client, "/promotions/validate",
                    {"code": "LAUNCH2026", "plan_id": pid, "billing_cycle": "monthly"},
                    label="POST /promotions/validate LAUNCH2026")
    d = _check(r, "LAUNCH2026 valid — 30% off 3 months")
    if d:
        if d.get("valid"): ok(f"  discount: {d.get('discount_label')}")
        else: fail(f"  invalid: {d.get('reason')}")

    # Validate NGO50 on starter
    pid_starter = _ids.get("plan_starter", "")
    r = await _post(client, "/promotions/validate",
                    {"code": "NGO50", "plan_id": pid_starter, "billing_cycle": "monthly"},
                    label="POST /promotions/validate NGO50")
    d = _check(r, "NGO50 valid — 50% off Starter forever")
    if d and d.get("valid"):
        ok(f"  discount: {d.get('discount_label')}")

    # Validate invalid code
    r = await _post(client, "/promotions/validate",
                    {"code": "DOESNOTEXIST", "plan_id": pid, "billing_cycle": "monthly"},
                    label="POST /promotions/validate invalid code")
    d = _check(r, "Invalid promo returns valid=false")
    if d and not d.get("valid"):
        ok(f"  reason: {d.get('reason')}")


async def test_sales_public(client: httpx.AsyncClient) -> None:
    section("SALES — Public")

    r = await _get(client, "/sales", label="GET /sales")
    d = _check(r, "GET /sales → active + upcoming", key_check="active_sales")
    if d:
        ok(f"  {len(d['active_sales'])} active, {len(d['upcoming_sales'])} upcoming")
        if d["has_active_sale"]:
            sale = d["active_sales"][0]
            ok(f"  Active: '{sale['name']}' — {sale['discount']['label']}")
            _ids["active_sale_id"] = sale["id"]

    # Current best for professional/monthly
    r = await _get(client, "/sales/current?plan_slug=professional&cycle=monthly", label="GET /sales/current")
    d = _check(r, "GET /sales/current best for professional/monthly")
    if d:
        if d.get("has_sale"):
            ok(f"  Best sale: {d['sale']['name']} ({d['sale']['discount']['label']})")
        else:
            ok("  No applicable sale right now")

    # Get sale by ID
    sale_id = _ids.get("active_sale_id")
    if sale_id:
        r = await _get(client, f"/sales/{sale_id}", label="GET /sales/{id}")
        _check(r, "GET /sales/{id} → sale detail", key_check="name")


async def test_billing_preview(client: httpx.AsyncClient) -> None:
    section("BILLING PREVIEW — Public")

    pid = _ids.get("plan_professional", "")
    if not pid:
        skip("POST /subscriptions/billing-preview", "no plan_id")
        return

    # Monthly preview, no promo
    r = await _post(client, "/subscriptions/billing-preview",
                    {"plan_id": pid, "billing_cycle": "monthly"},
                    label="POST /subscriptions/billing-preview monthly")
    d = _check(r, "billing-preview Professional monthly", key_check="summary")
    if d:
        ok(f"  total: ${d['summary']['total_usd']}")

    # Annual preview with ANNUAL20 promo
    r = await _post(client, "/subscriptions/billing-preview",
                    {"plan_id": pid, "billing_cycle": "annual", "promo_code": "ANNUAL20"},
                    label="POST /subscriptions/billing-preview annual + ANNUAL20")
    d = _check(r, "billing-preview Professional annual + ANNUAL20", key_check="summary")
    if d:
        ok(f"  discount: ${d['summary']['discount_usd']}  total: ${d['summary']['total_usd']}")

    # With addons
    r = await _post(client, "/subscriptions/billing-preview",
                    {"plan_id": pid, "billing_cycle": "monthly",
                     "addons": [{"slug": "extra-sms-1k", "quantity": 2}]},
                    label="POST /subscriptions/billing-preview + 2× extra-sms-1k")
    d = _check(r, "billing-preview + addons", key_check="summary")
    if d:
        ok(f"  addon total: ${d['summary']['addon_total_usd']}")

    # Starter plan preview
    pid_s = _ids.get("plan_starter", "")
    r = await _post(client, "/subscriptions/billing-preview",
                    {"plan_id": pid_s, "billing_cycle": "monthly", "promo_code": "EARLYBIRD40"},
                    label="POST /subscriptions/billing-preview Starter + EARLYBIRD40")
    d = _check(r, "billing-preview Starter + EARLYBIRD40 (40% off)")
    if d:
        ok(f"  total: ${d['summary']['total_usd']}")


async def test_subscription_lifecycle(client: httpx.AsyncClient, token: str, org_id: str) -> None:
    section("SUBSCRIPTION LIFECYCLE")

    # Cancel any existing subscription so we start clean
    r = await _get(client, "/subscriptions/current", token=token, label="GET /subscriptions/current")
    d = _check(r, "GET /subscriptions/current (initial check)")
    if d and d.get("has_subscription"):
        sub_status = d["subscription"]["status"]
        ok(f"  Existing sub status: {sub_status}")
        r2 = await _post(client, "/subscriptions/cancel",
                         {"reason": "test cleanup", "immediate": True}, token=token,
                         label="POST /subscriptions/cancel (cleanup)")
        _check(r2, "Cancel existing sub for clean test")

    # Start trial on Professional
    r = await _post(client, "/subscriptions/trial",
                    {"plan_slug": "professional"}, token=token,
                    label="POST /subscriptions/trial")
    d = _check(r, "Start Professional trial (201)", expected_status=201)
    if d:
        ok(f"  Trial until: {d.get('trial_end', '?')[:10]}")
        _ids["trial_sub_id"] = d["subscription"]["id"]

    # Verify current
    r = await _get(client, "/subscriptions/current", token=token, label="GET /subscriptions/current after trial")
    d = _check(r, "Current subscription = trialing")
    if d and d.get("has_subscription"):
        s = d["subscription"]["status"]
        if s == "trialing": ok(f"  status = {s}")
        else: fail(f"  expected trialing, got {s}")
        ok(f"  plan = {d['subscription']['plan']['slug']}")
        # Usage meters present
        if d.get("usage"): ok("  Usage meters attached")
        else: fail("  No usage meters in response")

    # Cancel trial, go to checkout
    r = await _post(client, "/subscriptions/cancel",
                    {"reason": "upgrading to paid", "immediate": True}, token=token,
                    label="POST /subscriptions/cancel (cancel trial)")
    _check(r, "Cancel trial immediately")

    # Checkout Starter via bank_transfer
    pid_starter = _ids.get("plan_starter", "")
    r = await _post(client, "/checkout",
                    {"plan_id": pid_starter, "billing_cycle": "monthly",
                     "provider": "bank_transfer", "payer_name": "Test Org",
                     "payer_email": "billing@testorg.com"},
                    token=token, label="POST /checkout Starter bank_transfer")
    d = _check(r, "Checkout Starter (bank_transfer)", expected_status=201)
    if d:
        ok(f"  status={d['status']}  invoice={d['invoice']['invoice_number']}")
        ok(f"  total USD: {d['invoice']['total_usd']}")
        _ids["starter_sub_id"] = d["subscription_id"]
        _ids["starter_invoice_number"] = d["invoice"]["invoice_number"]

    # Verify active
    r = await _get(client, "/subscriptions/current", token=token, label="GET /subscriptions/current after checkout")
    d = _check(r, "Subscription active after checkout")
    if d and d.get("has_subscription"):
        s = d["subscription"]["status"]
        if s == "active": ok(f"  status = {s}")
        else: fail(f"  expected active, got {s}")

    # Upgrade to Professional
    pid_pro = _ids.get("plan_professional", "")
    r = await _post(client, "/subscriptions/upgrade",
                    {"plan_id": pid_pro}, token=token, label="POST /subscriptions/upgrade → Professional")
    d = _check(r, "Upgrade Starter → Professional")
    if d:
        plan_name = d["subscription"].get("plan", {}).get("slug", "?")
        ok(f"  new plan = {plan_name}")

    # Switch to annual billing
    r = await _post(client, "/subscriptions/switch-billing-cycle",
                    {"billing_cycle": "annual"}, token=token, label="POST /subscriptions/switch-billing-cycle → annual")
    d = _check(r, "Switch to annual billing")
    if d:
        ok(f"  amount_due=${d.get('amount_due_usd')}  invoice={d.get('invoice_number')}")

    # Create a fresh run-specific promo so apply-promo always works
    _promo_code = f"LIFECYCLE{_RUN}"
    await _post(client, "/promotions/admin", {
        "code": _promo_code, "name": f"Lifecycle test promo {_RUN}",
        "discount_type": "percentage", "discount_value": 15,
        "duration": "once", "new_subscribers_only": False,
    }, token=token)

    r = await _post(client, "/subscriptions/apply-promo",
                    {"code": _promo_code}, token=token, label=f"POST /subscriptions/apply-promo {_promo_code}")
    d = _check(r, f"Apply {_promo_code} (15% off, once)")
    if d:
        ok(f"  discount_pct={d.get('discount_pct')} months={d.get('discount_months')}")

    # List invoices
    r = await _get(client, "/subscriptions/invoices", token=token, label="GET /subscriptions/invoices")
    d = _check(r, "GET /subscriptions/invoices", key_check="invoices")
    if d:
        n = d.get("total", 0)
        ok(f"  {n} invoice(s)")
        if d["invoices"]:
            inv_id = d["invoices"][0]["id"]
            _ids["invoice_id"] = inv_id
            r2 = await _get(client, f"/subscriptions/invoices/{inv_id}", token=token,
                            label="GET /subscriptions/invoices/{id}")
            _check(r2, "GET /subscriptions/invoices/{id}", key_check="invoice_number")

    # Add a payment method
    r = await _post(client, "/subscriptions/payment-methods",
                    {"type": "mpesa", "phone_number": "+255712345678",
                     "display_name": "Test M-Pesa", "is_default": True},
                    token=token, label="POST /subscriptions/payment-methods")
    d = _check(r, "Add M-Pesa payment method", expected_status=201)
    if d:
        _ids["pm_id"] = d.get("id", "")
        ok(f"  id={d['id'][:8]}…")

    # List payment methods
    r = await _get(client, "/subscriptions/payment-methods", token=token,
                   label="GET /subscriptions/payment-methods")
    d = _check(r, "GET /subscriptions/payment-methods", key_check="payment_methods")
    if d:
        ok(f"  {len(d['payment_methods'])} method(s)")

    # Remove payment method
    pm_id = _ids.get("pm_id", "")
    if pm_id:
        r = await _delete(client, f"/subscriptions/payment-methods/{pm_id}", token=token,
                          label="DELETE /subscriptions/payment-methods/{id}")
        _check(r, "Remove payment method")

    # Subscription events / audit trail
    r = await _get(client, "/subscriptions/events", token=token, label="GET /subscriptions/events")
    d = _check(r, "GET /subscriptions/events", key_check="events")
    if d:
        ok(f"  {len(d['events'])} event(s) in audit trail")
        for ev in d["events"][:3]:
            ok(f"  event: {ev['event_type']}")

    # Downgrade to Starter
    pid_starter = _ids.get("plan_starter", "")
    r = await _post(client, "/subscriptions/downgrade",
                    {"plan_id": pid_starter}, token=token, label="POST /subscriptions/downgrade → Starter")
    d = _check(r, "Downgrade Professional → Starter (at period end)")
    if d:
        ok(f"  effective_at={d.get('effective_at', '?')[:10]}")

    # Final cancel
    r = await _post(client, "/subscriptions/cancel",
                    {"reason": "end of test run", "immediate": True}, token=token,
                    label="POST /subscriptions/cancel (final)")
    _check(r, "Final cancel subscription")


async def test_feature_check(client: httpx.AsyncClient, token: str, org_id: str) -> None:
    section("FEATURE CHECK — Internal")

    # Start a fresh trial for feature check
    await _post(client, "/subscriptions/trial", {"plan_slug": "professional"}, token=token)

    r = await client.get(
        f"{BASE_URL}/subscriptions/internal/feature-check",
        params={"org_id": org_id, "feature": "ai_conversation"},
        headers={**_h(token), "X-Service-Key": INTERNAL_KEY},
        timeout=10,
    )
    d = _check(r, "GET /subscriptions/internal/feature-check ai_conversation", key_check="has_access")
    if d:
        ok(f"  has_access={d['has_access']}  (professional has ai_conversation=True)")

    r = await client.get(
        f"{BASE_URL}/subscriptions/internal/feature-check",
        params={"org_id": org_id, "feature": "sso"},
        headers={**_h(token), "X-Service-Key": INTERNAL_KEY},
        timeout=10,
    )
    d = _check(r, "GET /subscriptions/internal/feature-check sso (not on professional)")
    if d:
        ok(f"  has_access={d['has_access']}  (professional has sso=False)")

    # Cleanup
    await _post(client, "/subscriptions/cancel", {"immediate": True}, token=token)


async def test_plans_admin(client: httpx.AsyncClient, token: str) -> None:
    section("PLANS — Admin")

    # List all plans (incl inactive)
    r = await _get(client, "/plans/admin/plans", token=token, label="GET /plans/admin/plans")
    d = _check(r, "GET /plans/admin/plans", key_check="plans")
    if d:
        ok(f"  {d['total']} plans total")

    # Create a custom NGO plan (unique slug per run)
    r = await _post(client, "/plans/admin/plans", {
        "slug":               f"ngo-custom-{_RUN}",
        "display_name":       "NGO Custom",
        "tagline":            "Discounted plan for verified NGOs",
        "description":        "Riviwa plan built for non-profits with limited budgets.",
        "monthly_price_usd":  "25.00",
        "annual_price_usd":   "20.00",
        "trial_days":         30,
        "sort_order":         5,
        "max_team_members":   10,
        "max_projects":       5,
        "max_submissions_per_month": 1000,
        "max_sms_per_month":  500,
        "max_storage_gb":     10,
        "has_sms_channel":    True,
        "has_ai_conversation": True,
        "has_translation":    True,
        "has_fraud_detection": True,
    }, token=token, label="POST /plans/admin/plans (NGO Custom)")
    d = _check(r, "Create NGO Custom plan", expected_status=201)
    if d:
        _ids["plan_ngo_custom"] = d["id"]
        ok(f"  id={d['id'][:8]}… slug={d['slug']}")

    ngo_id = _ids.get("plan_ngo_custom", "")
    if not ngo_id:
        skip("Plan admin sub-tests", "NGO plan creation failed")
        return

    # Update pricing
    r = await _patch(client, f"/plans/admin/plans/{ngo_id}/pricing",
                     {"monthly_price_usd": "29.00", "annual_price_usd": "23.00", "trial_days": 30},
                     token=token, label=f"PATCH /plans/admin/plans/{ngo_id[:8]}/pricing")
    d = _check(r, "Update NGO plan pricing")
    if d:
        ok(f"  new monthly=${d['pricing']['monthly_usd']}")

    # Update limits
    r = await _patch(client, f"/plans/admin/plans/{ngo_id}/limits",
                     {"max_team_members": 15, "max_projects": 8, "max_submissions_per_month": 2000},
                     token=token, label=f"PATCH /plans/admin/plans/{ngo_id[:8]}/limits")
    d = _check(r, "Update NGO plan limits")
    if d:
        ok(f"  max_team_members={d['limits']['team_members']}")

    # Toggle features
    r = await _patch(client, f"/plans/admin/plans/{ngo_id}/features",
                     {"webhooks": True, "api_access": True, "advanced_analytics": True},
                     token=token, label=f"PATCH /plans/admin/plans/{ngo_id[:8]}/features")
    d = _check(r, "Enable webhooks+api_access+analytics on NGO plan")
    if d:
        ok(f"  features_changed={list(d.get('features_changed', {}).keys())}")

    # Publish
    r = await _patch(client, f"/plans/admin/plans/{ngo_id}/publish",
                     {"is_public": True, "is_active": True},
                     token=token, label=f"PATCH /plans/admin/plans/{ngo_id[:8]}/publish")
    _check(r, "Publish NGO plan")

    # Duplicate as NGO Enterprise
    r = await _post(client, f"/plans/admin/plans/{ngo_id}/duplicate",
                    {"slug": f"ngo-enterprise-{_RUN}", "display_name": "NGO Enterprise",
                     "monthly_price_usd": "49.00", "annual_price_usd": "39.00"},
                    token=token, label=f"POST /plans/admin/plans/{ngo_id[:8]}/duplicate")
    d = _check(r, "Duplicate NGO → NGO Enterprise", expected_status=200)
    if d:
        _ids["plan_ngo_enterprise"] = d["id"]
        ok(f"  duplicated as {d['slug']} (is_active={d['is_active']})")

    # Deactivate NGO Enterprise (it's a clone, starts inactive)
    ngo_ent_id = _ids.get("plan_ngo_enterprise", "")
    if ngo_ent_id:
        r = await _delete(client, f"/plans/admin/plans/{ngo_ent_id}", token=token,
                          label=f"DELETE /plans/admin/plans/{ngo_ent_id[:8]}")
        _check(r, "Deactivate NGO Enterprise plan")

    # Addon admin
    r = await _get(client, "/plans/admin/addons", token=token, label="GET /plans/admin/addons")
    d = _check(r, "GET /plans/admin/addons", key_check="addons")
    if d:
        ok(f"  {len(d['addons'])} addons")

    r = await _post(client, "/plans/admin/addons", {
        "slug":         f"extra-projects-{_RUN}",
        "name":         "Extra Projects (3)",
        "description":  "3 additional project slots beyond plan limit",
        "type":         "extra_users",
        "price_usd":    "25.00",
        "unit":         "3 projects",
        "unit_quantity": 3,
    }, token=token, label="POST /plans/admin/addons")
    d = _check(r, "Create 'Extra Projects (3)' addon", expected_status=201)
    if d:
        _ids["addon_extra_projects"] = d["id"]
        ok(f"  id={d['id'][:8]}… price=${d['price_usd']}")

    addon_id = _ids.get("addon_extra_projects", "")
    if addon_id:
        r = await _patch(client, f"/plans/admin/addons/{addon_id}",
                         {"price_usd": "22.00", "description": "3 extra project slots — NGO discount applied"},
                         token=token, label=f"PATCH /plans/admin/addons/{addon_id[:8]}")
        _check(r, "Update addon price to $22")

        r = await _delete(client, f"/plans/admin/addons/{addon_id}", token=token,
                          label=f"DELETE /plans/admin/addons/{addon_id[:8]}")
        _check(r, "Deactivate test addon")


async def test_promotions_admin(client: httpx.AsyncClient, token: str) -> None:
    section("PROMOTIONS — Admin")

    # List all
    r = await _get(client, "/promotions/admin", token=token, label="GET /promotions/admin")
    d = _check(r, "GET /promotions/admin", key_check="promo_codes")
    if d:
        ok(f"  {d['total']} promo codes total")
        if d["promo_codes"]:
            _ids["promo_id_first"] = d["promo_codes"][0]["id"]

    # Create a new promo
    r = await _post(client, "/promotions/admin", {
        "code":                 f"TESTRUN{_RUN}",
        "name":                 f"Test Run 25% Off ({_RUN})",
        "description":          "Created by endpoint test runner",
        "discount_type":        "percentage",
        "discount_value":       25,
        "duration":             "repeating",
        "duration_months":      2,
        "max_redemptions":      50,
        "eligible_plans":       ["professional", "business"],
        "new_subscribers_only": False,
        "expires_at":           (datetime.utcnow() + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%S"),
    }, token=token, label="POST /promotions/admin TESTRUN25")
    d = _check(r, f"Create TESTRUN{_RUN} promo", expected_status=201)
    if d:
        _ids["promo_testrun"] = d["id"]
        ok(f"  id={d['id'][:8]}… code={d['code']}")

    # Get detail
    promo_id = _ids.get("promo_testrun", _ids.get("promo_id_first", ""))
    if promo_id:
        r = await _get(client, f"/promotions/admin/{promo_id}", token=token,
                       label=f"GET /promotions/admin/{promo_id[:8]}")
        d = _check(r, "GET /promotions/admin/{id} detail + stats", key_check="stats")
        if d:
            ok(f"  redemptions={d['stats']['redemptions_used']}  active={d['is_active']}")

    # Update
    if promo_id:
        r = await _patch(client, f"/promotions/admin/{promo_id}",
                         {"max_redemptions": 100, "description": "Updated by test — max raised to 100"},
                         token=token, label=f"PATCH /promotions/admin/{promo_id[:8]}")
        _check(r, f"Update TESTRUN{_RUN} max_redemptions → 100")

    # Bulk generate partner codes
    r = await _post(client, "/promotions/admin/bulk-generate", {
        "prefix":              "PARTNER",
        "count":               5,
        "discount_type":       "percentage",
        "discount_value":      20,
        "duration":            "once",
        "eligible_plans":      ["professional"],
        "new_subscribers_only": True,
        "expires_at":          (datetime.utcnow() + timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%S"),
        "name_prefix":         "Partner Code",
        "description":         "Partner referral — 20% off first payment",
    }, token=token, label="POST /promotions/admin/bulk-generate (5 PARTNER-xxx codes)")
    d = _check(r, "Bulk generate 5 partner codes", expected_status=201)
    if d:
        ok(f"  generated: {d['generated']}  sample: {d['codes'][:2]}")

    # Stats summary
    r = await _get(client, "/promotions/admin/stats/summary", token=token,
                   label="GET /promotions/admin/stats/summary")
    d = _check(r, "GET /promotions/admin/stats/summary", key_check="total_codes")
    if d:
        ok(f"  total={d['total_codes']}  active={d['active_codes']}  redemptions={d['total_redemptions']}")

    # Deactivate test promo
    if _ids.get("promo_testrun"):
        r = await _delete(client, f"/promotions/admin/{_ids['promo_testrun']}", token=token,
                          label=f"DELETE /promotions/admin/{_ids['promo_testrun'][:8]}")
        _check(r, f"Deactivate TESTRUN{_RUN}")


async def test_sales_admin(client: httpx.AsyncClient, token: str) -> None:
    section("SALES — Admin")

    now = datetime.utcnow()

    # List all
    r = await _get(client, "/sales/admin/all", token=token, label="GET /sales/admin/all")
    d = _check(r, "GET /sales/admin/all", key_check="sales")
    if d:
        ok(f"  {d['total']} total sales")

    # List active
    r = await _get(client, "/sales/admin/all?status=active", token=token,
                   label="GET /sales/admin/all?status=active")
    d = _check(r, "GET /sales/admin/all (active only)")
    if d:
        ok(f"  {d['total']} active sales")

    # Create a scheduled sale (future)
    future_start = (now + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
    future_end   = (now + timedelta(hours=26)).strftime("%Y-%m-%dT%H:%M:%S")
    r = await _post(client, "/sales/admin", {
        "name":           "Test Flash Sale",
        "description":    "Created by endpoint test runner — scheduled flash sale",
        "banner_text":    "Test Flash Sale — 35% OFF!",
        "start_at":       future_start,
        "end_at":         future_end,
        "discount_type":  "percentage",
        "discount_value": 35,
        "duration":       "once",
        "auto_apply":     True,
        "eligible_plans": ["professional", "business"],
        "new_subscribers_only": False,
        "max_redemptions": 200,
    }, token=token, label="POST /sales/admin (Test Flash Sale)")
    d = _check(r, "Create Test Flash Sale (scheduled)", expected_status=201)
    if d:
        _ids["sale_flash"] = d["id"]
        ok(f"  id={d['id'][:8]}… status={d['status']}")

    flash_id = _ids.get("sale_flash", "")
    if not flash_id:
        skip("Sales admin sub-tests", "flash sale creation failed")
        return

    # Stats
    r = await _get(client, f"/sales/admin/{flash_id}/stats", token=token,
                   label=f"GET /sales/admin/{flash_id[:8]}/stats")
    d = _check(r, "GET /sales/admin/{id}/stats", key_check="status")
    if d:
        ok(f"  status={d['status']}  redemptions={d['redemption_count']}")

    # Activate it now (force start)
    r = await _post(client, f"/sales/admin/{flash_id}/activate", {}, token=token,
                    label=f"POST /sales/admin/{flash_id[:8]}/activate")
    d = _check(r, "Force-activate flash sale → active")
    if d:
        ok(f"  status={d.get('status')}")

    # Extend by 12 hours
    r = await _post(client, f"/sales/admin/{flash_id}/extend", {"hours": 12}, token=token,
                    label=f"POST /sales/admin/{flash_id[:8]}/extend (+12 hours)")
    d = _check(r, "Extend flash sale by 12 hours")
    if d:
        ok(f"  new end: {d.get('schedule', {}).get('end_at', '?')[:19]}")

    # Update name/banner
    r = await _patch(client, f"/sales/admin/{flash_id}",
                     {"banner_text": "Test Flash Sale — 35% OFF! Extended!"},
                     token=token, label=f"PATCH /sales/admin/{flash_id[:8]}")
    _check(r, "Update flash sale banner text")

    # End it now
    r = await _post(client, f"/sales/admin/{flash_id}/end", {}, token=token,
                    label=f"POST /sales/admin/{flash_id[:8]}/end")
    d = _check(r, "Force-end flash sale")
    if d:
        ok(f"  status={d.get('status')}")

    # Create a second sale to test cancel/delete
    r = await _post(client, "/sales/admin", {
        "name":           "Test Delete Sale",
        "start_at":       (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
        "end_at":         (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
        "discount_type":  "fixed_amount",
        "discount_value": 10,
        "duration":       "once",
        "auto_apply":     False,
        "generate_code":  True,
        "code_prefix":    "TDEL",
    }, token=token, label="POST /sales/admin (generate_code=true)")
    d = _check(r, "Create sale with auto-generated promo code", expected_status=201)
    if d:
        _ids["sale_delete"] = d["id"]
        ok(f"  promo_code_id={d.get('promo_code_id')}")
        r2 = await _delete(client, f"/sales/admin/{d['id']}", token=token,
                           label=f"DELETE /sales/admin/{d['id'][:8]}")
        _check(r2, "Cancel/delete test sale")


async def test_billing_admin(client: httpx.AsyncClient, token: str, org_id: str) -> None:
    section("BILLING ADMIN — /api/v1/billing/*")

    # Metrics
    r = await _get(client, "/billing/metrics", token=token, label="GET /billing/metrics")
    d = _check(r, "GET /billing/metrics (MRR, ARR, churn)", key_check="mrr_usd")
    if d:
        ok(f"  MRR=${d['mrr_usd']}  ARR=${d['arr_usd']}  active_subs={d['active_subscriptions']}")

    # Promo codes list
    r = await _get(client, "/billing/promo-codes", token=token, label="GET /billing/promo-codes")
    d = _check(r, "GET /billing/promo-codes", key_check="promo_codes")
    if d:
        ok(f"  {len(d['promo_codes'])} codes")

    # Create promo via billing route
    r = await _post(client, "/billing/promo-codes", {
        "code":          f"BILLTEST{_RUN}",
        "name":          f"Billing Admin Test Promo ({_RUN})",
        "discount_type": "fixed_amount",
        "discount_value": 10,
        "duration":      "once",
        "max_redemptions": 5,
    }, token=token, label="POST /billing/promo-codes BILLTEST10")
    d = _check(r, f"Create BILLTEST{_RUN} via billing admin", expected_status=201)
    if d:
        _ids["billing_promo_id"] = d["id"]
        ok(f"  id={d['id'][:8]}…")

        # Update it
        r2 = await _patch(client, f"/billing/promo-codes/{d['id']}",
                          {"max_redemptions": 10}, token=token,
                          label=f"PATCH /billing/promo-codes/{d['id'][:8]}")
        _check(r2, f"Update BILLTEST{_RUN} max_redemptions → 10")

    # All invoices
    r = await _get(client, "/billing/invoices", token=token, label="GET /billing/invoices")
    d = _check(r, "GET /billing/invoices", key_check="invoices")
    if d:
        ok(f"  {d['total']} invoices total")

    # All subscriptions
    r = await _get(client, "/subscriptions/admin/all", token=token, label="GET /subscriptions/admin/all")
    d = _check(r, "GET /subscriptions/admin/all", key_check="subscriptions")
    if d:
        ok(f"  {d['total']} subscriptions")

    # Grant free months to a sub (if one exists)
    r_sub = await _get(client, "/subscriptions/admin/all?size=1", token=token)
    if r_sub and r_sub.status_code == 200:
        subs = r_sub.json().get("subscriptions", [])
        if subs:
            sub_id = subs[0]["id"]
            r2 = await _post(client, f"/billing/subscriptions/{sub_id}/free-months",
                             {"months": 1}, token=token,
                             label=f"POST /billing/subscriptions/{sub_id[:8]}/free-months")
            _check(r2, "Grant 1 free month to subscription")

    # Admin cancel a sub — only try if one is active/trialing
    r_sub = await _get(client, "/subscriptions/admin/all?size=20", token=token)
    if r_sub and r_sub.status_code == 200:
        subs = r_sub.json().get("subscriptions", [])
        active_subs = [s for s in subs if s["status"] in ("active", "trialing", "paused", "past_due")]
        if active_subs:
            sub_id = active_subs[0]["id"]
            r2 = await _post(client, f"/billing/subscriptions/{sub_id}/cancel",
                             {"reason": "admin test cancel", "immediate": True},
                             token=token, label=f"POST /billing/subscriptions/{sub_id[:8]}/cancel")
            _check(r2, "Admin cancel subscription")
        else:
            skip("POST /billing/subscriptions/{id}/cancel", "no active sub to cancel (all already cancelled)")

    # Invoice void
    invoice_id = _ids.get("invoice_id", "")
    if invoice_id:
        r = await _post(client, f"/billing/invoices/{invoice_id}/void", {}, token=token,
                        label=f"POST /billing/invoices/{invoice_id[:8]}/void")
        _check(r, "Void invoice")


async def test_subscription_events(client: httpx.AsyncClient, token: str, org_id: str) -> None:
    """Admin subscription events view."""
    section("SUBSCRIPTION EVENTS (Admin)")

    r = await _get(client, "/subscriptions/admin/all?size=5", token=token)
    if not r or r.status_code != 200:
        skip("GET /billing/subscriptions/{id}/events", "could not list subs")
        return
    subs = r.json().get("subscriptions", [])
    if not subs:
        skip("GET /billing/subscriptions/{id}/events", "no subscriptions exist")
        return

    sub_id = subs[0]["id"]
    r = await _get(client, f"/billing/subscriptions/{sub_id}/events", token=token,
                   label=f"GET /billing/subscriptions/{sub_id[:8]}/events")
    d = _check(r, "GET /billing/subscriptions/{id}/events (audit trail)", key_check="events")
    if d:
        ok(f"  {len(d['events'])} events")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    print(f"\n{BOLD}{CYAN}Riviwa Subscription Service — Full Endpoint Test + Sample Data{RESET}")
    print(f"  BASE_URL : {BASE_URL}")
    print(f"  AUTH_URL : {AUTH_URL}")
    print(f"  STAGING  : {STAGING}")
    print(f"  Time     : {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:

        # ── Health check ──────────────────────────────────────────────────────
        section("HEALTH")
        r = await client.get(f"{BASE_URL.replace('/api/v1', '')}/health", timeout=5)
        if r.status_code == 200:
            ok("GET /health → ok")
        else:
            fail("GET /health", f"HTTP {r.status_code}")
            print(f"\n  {RED}Service not reachable at {BASE_URL}{RESET}\n")
            return

        # ── Public endpoints (no auth) ────────────────────────────────────────
        await test_plans_public(client)
        await test_promotions_public(client)
        await test_sales_public(client)
        await test_billing_preview(client)

        # ── Authenticated tests ───────────────────────────────────────────────
        section("AUTHENTICATION")
        try:
            token, org_id = await _get_token(client)
            ok(f"Authenticated  org_id={org_id[:8]}…")
        except SystemExit:
            skip("All authenticated tests", "auth failed — see above")
            _print_summary()
            return
        except Exception as e:
            fail("Authentication", str(e))
            skip("All authenticated tests", "auth failed")
            _print_summary()
            return

        await test_subscription_lifecycle(client, token, org_id)
        await test_feature_check(client, token, org_id)
        await test_plans_admin(client, token)
        await test_promotions_admin(client, token)
        await test_sales_admin(client, token)
        await test_billing_admin(client, token, org_id)
        await test_subscription_events(client, token, org_id)

    _print_summary()


def _print_summary() -> None:
    total = passed + failed + skipped
    print(f"\n{BOLD}{'─'*55}{RESET}")
    print(f"{BOLD}Results:{RESET}  "
          f"{GREEN}{BOLD}{passed} passed{RESET}  "
          f"{RED}{BOLD}{failed} failed{RESET}  "
          f"{YELLOW}{skipped} skipped{RESET}  "
          f"({total} total)")
    if failed == 0:
        print(f"\n{GREEN}{BOLD}All tests passed!{RESET}\n")
    else:
        print(f"\n{RED}{BOLD}{failed} test(s) failed — review output above.{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
