"""services/notification_client.py — fire subscription notifications via notification_service."""
from __future__ import annotations

import asyncio
import uuid
from datetime import date
from typing import Any, Dict, List, Optional

import httpx
import structlog

from core.config import settings

log = structlog.get_logger(__name__)

_AUTH_BASE  = settings.AUTH_SERVICE_URL
_NOTIF_BASE = settings.NOTIFICATION_SERVICE_URL
_SVC_HEADERS = {"X-Service-Key": settings.INTERNAL_SERVICE_KEY}


async def _get_owner_contact(org_id: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(
                f"{_AUTH_BASE}/api/v1/internal/orgs/{org_id}/owner-contact",
                headers=_SVC_HEADERS,
            )
            if r.status_code == 200:
                return r.json()
    except Exception as exc:
        log.warning("notification_client.owner_contact_failed", org_id=org_id, error=str(exc))
    return None


async def _dispatch(
    notification_type: str,
    org_id:            str,
    variables:         Dict[str, Any],
    channels:          List[str],
    priority:          str,
    idempotency_key:   str,
) -> None:
    contact = await _get_owner_contact(org_id)
    if not contact:
        log.warning("notification_client.no_owner_contact", org_id=org_id, type=notification_type)
        return

    body = {
        "notification_type":  notification_type,
        "recipient_user_id":  contact.get("user_id"),
        "recipient_email":    contact.get("email"),
        "recipient_phone":    contact.get("phone"),
        "language":           contact.get("language", "en"),
        "variables":          {**variables, "owner_name": contact.get("display_name") or contact.get("org_name", ""),
                               "org_name": contact.get("org_name", "")},
        "preferred_channels": channels,
        "priority":           priority,
        "idempotency_key":    idempotency_key,
        "source_service":     "subscription_service",
        "source_entity_id":   org_id,
    }

    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post(
                f"{_NOTIF_BASE}/api/v1/internal/dispatch",
                headers=_SVC_HEADERS,
                json=body,
            )
            if r.status_code not in (200, 202):
                log.warning("notification_client.dispatch_failed",
                            type=notification_type, org_id=org_id,
                            status=r.status_code, body=r.text[:200])
    except Exception as exc:
        log.warning("notification_client.dispatch_error",
                    type=notification_type, org_id=org_id, error=str(exc))


def notify(
    notification_type: str,
    org_id:            str,
    variables:         Dict[str, Any],
    channels:          Optional[List[str]] = None,
    priority:          str = "high",
    idempotency_key:   Optional[str] = None,
) -> None:
    """Fire-and-forget notification. Call from sync/async context; never blocks."""
    key = idempotency_key or f"{notification_type}:{org_id}:{date.today()}"
    chs = channels or ["email", "in_app"]
    asyncio.ensure_future(
        _dispatch(notification_type, org_id, variables, chs, priority, key)
    )


# ── Typed helpers ─────────────────────────────────────────────────────────────

def notify_trial_started(org_id: str, plan_name: str, trial_days: int, trial_end_date: str) -> None:
    notify("subscription.trial_started", org_id,
           {"plan_name": plan_name, "trial_days": trial_days, "trial_end_date": trial_end_date},
           idempotency_key=f"trial_started:{org_id}")

def notify_subscribed(org_id: str, plan_name: str, billing_cycle: str, price_usd: str,
                      next_renewal_date: str, invoice_number: str) -> None:
    notify("subscription.subscribed", org_id,
           {"plan_name": plan_name, "billing_cycle": billing_cycle, "price_usd": price_usd,
            "next_renewal_date": next_renewal_date, "invoice_number": invoice_number},
           idempotency_key=f"subscribed:{org_id}:{invoice_number}")

def notify_payment_receipt(org_id: str, plan_name: str, billing_cycle: str, invoice_number: str,
                           amount_usd: str, period_start: str, period_end: str,
                           next_renewal_date: str) -> None:
    notify("subscription.payment_receipt", org_id,
           {"plan_name": plan_name, "billing_cycle": billing_cycle, "invoice_number": invoice_number,
            "amount_usd": amount_usd, "period_start": period_start, "period_end": period_end,
            "next_renewal_date": next_renewal_date},
           idempotency_key=f"receipt:{invoice_number}")

def notify_upgraded(org_id: str, old_plan: str, new_plan: str) -> None:
    notify("subscription.upgraded", org_id, {"old_plan": old_plan, "new_plan": new_plan},
           idempotency_key=f"upgraded:{org_id}:{new_plan}")

def notify_downgraded(org_id: str, old_plan: str, new_plan: str, effective_date: str) -> None:
    notify("subscription.downgraded", org_id,
           {"old_plan": old_plan, "new_plan": new_plan, "effective_date": effective_date},
           idempotency_key=f"downgraded:{org_id}:{new_plan}")

def notify_cancelled(org_id: str, plan_name: str, access_end_date: str) -> None:
    notify("subscription.cancelled", org_id,
           {"plan_name": plan_name, "access_end_date": access_end_date},
           idempotency_key=f"cancelled:{org_id}")

def notify_paused(org_id: str, plan_name: str, pause_months: int, resume_date: str) -> None:
    notify("subscription.paused", org_id,
           {"plan_name": plan_name, "pause_months": pause_months, "resume_date": resume_date},
           idempotency_key=f"paused:{org_id}")

def notify_resumed(org_id: str, plan_name: str, next_renewal_date: str) -> None:
    notify("subscription.resumed", org_id,
           {"plan_name": plan_name, "next_renewal_date": next_renewal_date},
           idempotency_key=f"resumed:{org_id}")

def notify_payment_failed(org_id: str, plan_name: str, invoice_number: str,
                          amount_usd: str, failure_reason: str) -> None:
    notify("subscription.payment_failed", org_id,
           {"plan_name": plan_name, "invoice_number": invoice_number,
            "amount_usd": amount_usd, "failure_reason": failure_reason or "Payment declined"},
           priority="high", idempotency_key=f"pay_failed:{invoice_number}")

def notify_past_due(org_id: str, plan_name: str) -> None:
    notify("subscription.past_due", org_id, {"plan_name": plan_name},
           priority="high", idempotency_key=f"past_due:{org_id}:{date.today()}")

def notify_renewal_reminder(org_id: str, plan_name: str, days_left: int,
                            renewal_date: str, amount_usd: str, billing_cycle: str) -> None:
    notify("subscription.renewal_reminder", org_id,
           {"plan_name": plan_name, "days_left": days_left, "renewal_date": renewal_date,
            "amount_usd": amount_usd, "billing_cycle": billing_cycle},
           priority="medium", idempotency_key=f"renewal_reminder:{org_id}:{days_left}d:{renewal_date[:10]}")

def notify_trial_ending(org_id: str, plan_name: str, days_left: int,
                        trial_end_date: str, price_usd: str, billing_cycle: str) -> None:
    notify("subscription.trial_ending_soon", org_id,
           {"plan_name": plan_name, "days_left": days_left, "trial_end_date": trial_end_date,
            "price_usd": price_usd, "billing_cycle": billing_cycle},
           priority="high", idempotency_key=f"trial_ending:{org_id}:{days_left}d")
