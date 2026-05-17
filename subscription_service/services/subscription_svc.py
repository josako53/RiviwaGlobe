"""services/subscription_svc.py — Core subscription lifecycle logic."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import (
    ConflictError, NotFoundError, SubscriptionError, PromoError
)
from models.subscription import (
    BillingCycle, Invoice, InvoiceStatus, OrgAddOn, Plan, PromoCode,
    PromoRedemption, Subscription, SubscriptionEvent, SubscriptionEventType,
    SubscriptionStatus, UsageMeter,
)

log = structlog.get_logger(__name__)

# Dunning retry schedule (days after invoice due)
DUNNING_SCHEDULE = [3, 5, 7]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _period_end(start: datetime, cycle: str) -> datetime:
    if cycle == BillingCycle.ANNUAL.value:
        return start + timedelta(days=365)
    return start + timedelta(days=30)


def _invoice_number() -> str:
    import random, string
    suffix = ''.join(random.choices(string.digits, k=6))
    return f"INV-{datetime.utcnow().year}-{suffix}"


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Plan helpers ──────────────────────────────────────────────────────────

    async def get_plan(self, plan_id: str) -> Plan:
        plan = await self.db.get(Plan, uuid.UUID(plan_id))
        if not plan or not plan.is_active:
            raise NotFoundError("Plan")
        return plan

    async def get_plan_by_slug(self, slug: str) -> Plan:
        plan = (await self.db.execute(
            select(Plan).where(Plan.slug == slug, Plan.is_active == True)
        )).scalar_one_or_none()
        if not plan:
            raise NotFoundError("Plan")
        return plan

    async def list_plans(self) -> list[Plan]:
        result = await self.db.execute(
            select(Plan).where(Plan.is_active == True, Plan.is_public == True)
            .order_by(Plan.sort_order)
        )
        return list(result.scalars().all())

    # ── Subscription lookup ───────────────────────────────────────────────────

    async def get_org_subscription(self, org_id: str) -> Optional[Subscription]:
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.org_id == uuid.UUID(org_id),
                Subscription.status.notin_([
                    SubscriptionStatus.CANCELLED.value,
                    SubscriptionStatus.EXPIRED.value,
                ])
            ).order_by(Subscription.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_subscription_or_404(self, subscription_id: str, org_id: str) -> Subscription:
        sub = await self.db.get(Subscription, uuid.UUID(subscription_id))
        if not sub or str(sub.org_id) != org_id:
            raise NotFoundError("Subscription")
        return sub

    # ── Trial start ───────────────────────────────────────────────────────────

    async def start_trial(self, org_id: str, plan_slug: str = "professional") -> Subscription:
        existing = await self.get_org_subscription(org_id)
        if existing:
            raise ConflictError("Organisation already has an active subscription or trial.")

        plan = await self.get_plan_by_slug(plan_slug)
        now = _now()
        trial_end = now + timedelta(days=plan.trial_days)

        sub = Subscription(
            org_id=uuid.UUID(org_id),
            plan_id=plan.id,
            status=SubscriptionStatus.TRIALING.value,
            billing_cycle=BillingCycle.MONTHLY.value,
            current_period_start=now,
            current_period_end=trial_end,
            trial_start=now,
            trial_end=trial_end,
        )
        self.db.add(sub)
        await self.db.flush()

        await self._create_usage_meter(sub)
        await self._log_event(sub, SubscriptionEventType.TRIAL_STARTED, actor_type="system")
        await self.db.commit()

        log.info("subscription.trial_started", org_id=org_id, plan=plan_slug,
                 trial_end=trial_end.isoformat())
        return sub

    # ── Subscribe (checkout) ──────────────────────────────────────────────────

    async def create_subscription(
        self,
        org_id:            str,
        plan_id:           str,
        billing_cycle:     str,
        payment_method_id: Optional[str] = None,
        promo_code:        Optional[str] = None,
        actor_id:          Optional[str] = None,
    ) -> tuple[Subscription, Invoice]:

        plan = await self.get_plan(plan_id)
        if plan.is_custom:
            raise SubscriptionError("Enterprise plans require contacting sales. Email sales@riviwa.com")

        # Cancel any existing trial
        existing = await self.get_org_subscription(org_id)
        if existing:
            if existing.status not in (SubscriptionStatus.TRIALING.value,):
                raise ConflictError("Organisation already has an active subscription. Upgrade or downgrade instead.")
            existing.status = SubscriptionStatus.CANCELLED.value
            existing.cancelled_at = _now()

        now = _now()
        period_end = _period_end(now, billing_cycle)

        # Promo code
        discount_pct = Decimal("0")
        discount_months = 0
        promo_obj = None
        if promo_code:
            promo_obj, discount_pct, discount_months = await self._validate_promo(
                promo_code, plan, org_id, new_subscriber=True
            )

        price = plan.annual_price_usd if billing_cycle == BillingCycle.ANNUAL.value else plan.monthly_price_usd
        effective_price = price

        sub = Subscription(
            org_id=uuid.UUID(org_id),
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            billing_cycle=billing_cycle,
            current_period_start=now,
            current_period_end=period_end,
            promo_code_id=promo_obj.id if promo_obj else None,
            discount_pct=discount_pct,
            discount_months_remaining=discount_months,
            default_payment_method_id=uuid.UUID(payment_method_id) if payment_method_id else None,
            effective_monthly_usd=effective_price,
        )
        self.db.add(sub)
        await self.db.flush()

        # Promo redemption
        if promo_obj:
            self.db.add(PromoRedemption(
                promo_code_id=promo_obj.id,
                org_id=uuid.UUID(org_id),
                subscription_id=sub.id,
            ))
            promo_obj.redemption_count += 1

        # Usage meter
        await self._create_usage_meter(sub)

        # Generate invoice
        invoice = await self._generate_invoice(sub, plan, billing_cycle, discount_pct)

        await self._log_event(sub, SubscriptionEventType.SUBSCRIBED,
                              actor_id=actor_id, actor_type="org",
                              metadata={"plan": plan.slug, "billing_cycle": billing_cycle})
        await self.db.commit()
        log.info("subscription.created", org_id=org_id, plan=plan.slug, cycle=billing_cycle)
        return sub, invoice

    # ── Upgrade ───────────────────────────────────────────────────────────────

    async def upgrade(self, org_id: str, new_plan_id: str, actor_id: Optional[str] = None) -> Subscription:
        sub = await self.get_org_subscription(org_id)
        if not sub:
            raise NotFoundError("Subscription")

        old_plan = await self.get_plan(str(sub.plan_id))
        new_plan = await self.get_plan(new_plan_id)

        if new_plan.sort_order <= old_plan.sort_order:
            raise SubscriptionError("Use downgrade endpoint to move to a lower plan.")

        # Proration — use the actual period price (monthly or annual total)
        now = _now()
        days_remaining = max((sub.current_period_end - now).days, 0)
        total_days     = max((sub.current_period_end - sub.current_period_start).days, 1)
        is_annual      = sub.billing_cycle == BillingCycle.ANNUAL.value

        old_period_price = (old_plan.annual_price_usd * 12) if is_annual else old_plan.monthly_price_usd
        new_period_price = (new_plan.annual_price_usd * 12) if is_annual else new_plan.monthly_price_usd

        credit          = old_period_price * Decimal(days_remaining) / Decimal(total_days)
        prorated_amount = max(new_period_price - credit, Decimal("0"))

        old_plan_id = sub.plan_id
        sub.plan_id = new_plan.id
        sub.effective_monthly_usd = new_plan.annual_price_usd if is_annual else new_plan.monthly_price_usd
        sub.updated_at = now

        if prorated_amount > Decimal("0"):
            await self._generate_invoice(
                sub, new_plan, "monthly", Decimal("0"),
                description=f"Upgrade from {old_plan.display_name} to {new_plan.display_name} (prorated {days_remaining}d)",
                amount_override=prorated_amount,
            )

        await self._log_event(sub, SubscriptionEventType.UPGRADED, actor_id=actor_id,
                              from_plan_id=old_plan_id, to_plan_id=new_plan.id)
        await self.db.commit()
        log.info("subscription.upgraded", org_id=org_id, from_plan=old_plan.slug, to_plan=new_plan.slug)
        return sub

    # ── Downgrade ─────────────────────────────────────────────────────────────

    async def downgrade(self, org_id: str, new_plan_id: str, actor_id: Optional[str] = None) -> Subscription:
        sub = await self.get_org_subscription(org_id)
        if not sub:
            raise NotFoundError("Subscription")

        old_plan = await self.get_plan(str(sub.plan_id))
        new_plan = await self.get_plan(new_plan_id)

        if new_plan.sort_order >= old_plan.sort_order:
            raise SubscriptionError("Use upgrade endpoint to move to a higher plan.")

        old_plan_id = sub.plan_id
        sub.plan_id = new_plan.id
        sub.cancel_at_period_end = False  # takes effect at period end
        sub.effective_monthly_usd = new_plan.monthly_price_usd
        sub.updated_at = _now()

        await self._log_event(sub, SubscriptionEventType.DOWNGRADED, actor_id=actor_id,
                              from_plan_id=old_plan_id, to_plan_id=new_plan.id,
                              metadata={"effective_at": sub.current_period_end.isoformat()})
        await self.db.commit()
        log.info("subscription.downgraded", org_id=org_id, from_plan=old_plan.slug, to_plan=new_plan.slug)
        return sub

    # ── Cancel ────────────────────────────────────────────────────────────────

    async def cancel(
        self,
        org_id:     str,
        reason:     Optional[str] = None,
        immediate:  bool = False,
        actor_id:   Optional[str] = None,
    ) -> Subscription:
        sub = await self.get_org_subscription(org_id)
        if not sub:
            raise NotFoundError("Subscription")
        if sub.status == SubscriptionStatus.CANCELLED.value:
            raise SubscriptionError("Subscription is already cancelled.")

        now = _now()
        if immediate:
            sub.status = SubscriptionStatus.CANCELLED.value
            sub.cancelled_at = now
        else:
            sub.cancel_at_period_end = True
        sub.cancellation_reason = reason
        sub.updated_at = now

        await self._log_event(sub, SubscriptionEventType.CANCELLED, actor_id=actor_id,
                              actor_type="org",
                              metadata={"reason": reason, "immediate": immediate})
        await self.db.commit()
        return sub

    # ── Pause ─────────────────────────────────────────────────────────────────

    async def pause(self, org_id: str, months: int = 1, actor_id: Optional[str] = None) -> Subscription:
        sub = await self.get_org_subscription(org_id)
        if not sub:
            raise NotFoundError("Subscription")

        plan = await self.get_plan(str(sub.plan_id))
        if not plan.has_dedicated_support:
            raise SubscriptionError("Pause is available on Business and Enterprise plans only.")
        if sub.status == SubscriptionStatus.PAUSED.value:
            raise SubscriptionError("Subscription is already paused.")

        now = _now()
        sub.status = SubscriptionStatus.PAUSED.value
        sub.paused_at = now
        sub.pause_resume_at = now + timedelta(days=30 * months)
        sub.updated_at = now

        await self._log_event(sub, SubscriptionEventType.PAUSED, actor_id=actor_id,
                              metadata={"months": months, "resume_at": sub.pause_resume_at.isoformat()})
        await self.db.commit()
        return sub

    # ── Resume ────────────────────────────────────────────────────────────────

    async def resume(self, org_id: str, actor_id: Optional[str] = None) -> Subscription:
        sub = await self.get_org_subscription(org_id)
        if not sub:
            raise NotFoundError("Subscription")
        if sub.status != SubscriptionStatus.PAUSED.value:
            raise SubscriptionError("Subscription is not paused.")

        now = _now()
        sub.status = SubscriptionStatus.ACTIVE.value
        sub.paused_at = None
        sub.pause_resume_at = None
        sub.current_period_start = now
        sub.current_period_end = _period_end(now, sub.billing_cycle)
        sub.updated_at = now

        await self._log_event(sub, SubscriptionEventType.RESUMED, actor_id=actor_id)
        await self.db.commit()
        return sub

    # ── Usage ─────────────────────────────────────────────────────────────────

    async def get_usage(self, org_id: str) -> Optional[UsageMeter]:
        sub = await self.get_org_subscription(org_id)
        if not sub:
            return None
        result = await self.db.execute(
            select(UsageMeter).where(
                UsageMeter.subscription_id == sub.id,
                UsageMeter.period_start <= _now(),
                UsageMeter.period_end >= _now(),
            )
        )
        return result.scalar_one_or_none()

    async def increment_usage(self, org_id: str, metric: str, amount: int = 1) -> None:
        meter = await self.get_usage(org_id)
        if not meter:
            return
        setattr(meter, metric, getattr(meter, metric, 0) + amount)
        meter.updated_at = _now()
        await self.db.commit()

    # ── Feature check ─────────────────────────────────────────────────────────

    async def check_feature(self, org_id: str, feature: str) -> bool:
        sub = await self.get_org_subscription(org_id)
        if not sub or sub.status not in (SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value):
            return False
        plan = await self.get_plan(str(sub.plan_id))
        return getattr(plan, f"has_{feature}", False)

    async def get_limits(self, org_id: str) -> dict:
        sub = await self.get_org_subscription(org_id)
        if not sub:
            return {}
        plan = await self.get_plan(str(sub.plan_id))
        return {
            "max_team_members":          plan.max_team_members,
            "max_projects":              plan.max_projects,
            "max_submissions_per_month": plan.max_submissions_per_month,
            "max_sms_per_month":         plan.max_sms_per_month,
            "max_api_calls_per_month":   plan.max_api_calls_per_month,
            "max_storage_gb":            plan.max_storage_gb,
            "max_qr_per_month":          plan.max_qr_per_month,
            "max_staff_profiles":        plan.max_staff_profiles,
        }

    # ── Promo validation ──────────────────────────────────────────────────────

    async def _validate_promo(
        self, code: str, plan: Plan, org_id: str, new_subscriber: bool
    ) -> tuple[PromoCode, Decimal, int]:
        promo = (await self.db.execute(
            select(PromoCode).where(PromoCode.code == code.upper(), PromoCode.is_active == True)
        )).scalar_one_or_none()
        if not promo:
            raise PromoError("Promo code not found or expired.")

        now = _now()
        if promo.expires_at and promo.expires_at < now:
            raise PromoError("This promo code has expired.")
        if promo.max_redemptions != -1 and promo.redemption_count >= promo.max_redemptions:
            raise PromoError("This promo code has reached its maximum redemptions.")
        if promo.new_subscribers_only and not new_subscriber:
            raise PromoError("This promo code is for new subscribers only.")

        # Check plan eligibility
        if promo.eligible_plans:
            if plan.slug not in promo.eligible_plans:
                raise PromoError(f"This promo code is not valid for the {plan.display_name} plan.")

        # Already redeemed by this org?
        already = (await self.db.execute(
            select(PromoRedemption).where(
                PromoRedemption.promo_code_id == promo.id,
                PromoRedemption.org_id == uuid.UUID(org_id),
            )
        )).scalar_one_or_none()
        if already:
            raise PromoError("You have already used this promo code.")

        discount_pct = Decimal("0")
        discount_months = 0
        if promo.discount_type == "percentage":
            discount_pct = promo.discount_value
        if promo.duration == "repeating":
            discount_months = promo.duration_months
        elif promo.duration == "forever":
            discount_months = 9999
        else:
            discount_months = 1

        return promo, discount_pct, discount_months

    # ── Invoice generation ────────────────────────────────────────────────────

    async def _generate_invoice(
        self,
        sub: Subscription,
        plan: Plan,
        billing_cycle: str,
        discount_pct: Decimal,
        description: str = "",
        amount_override: Optional[Decimal] = None,
    ) -> Invoice:
        # amount_override is always the final subtotal — never multiplied.
        # Only when no override is given do we compute from the cycle.
        if amount_override is not None:
            subtotal = amount_override
        elif billing_cycle == BillingCycle.ANNUAL.value:
            subtotal = plan.annual_price_usd * 12
        else:
            subtotal = plan.monthly_price_usd

        discount = subtotal * (discount_pct / Decimal("100")) if discount_pct else Decimal("0")
        taxable = subtotal - discount
        tax = taxable * settings.TAX_RATE
        total = taxable + tax

        line_items = [
            {
                "description": description or f"{plan.display_name} — {billing_cycle.title()}",
                "amount_usd": str(subtotal),
                "quantity": 1,
            }
        ]
        if discount > 0:
            line_items.append({
                "description": f"Promo discount ({discount_pct}%)",
                "amount_usd": str(-discount),
                "quantity": 1,
            })
        line_items.append({
            "description": f"VAT ({int(settings.TAX_RATE * 100)}%)",
            "amount_usd": str(tax),
            "quantity": 1,
        })

        invoice = Invoice(
            invoice_number=_invoice_number(),
            org_id=sub.org_id,
            subscription_id=sub.id,
            status=InvoiceStatus.OPEN.value,
            subtotal_usd=subtotal,
            discount_usd=discount,
            tax_usd=tax,
            total_usd=total,
            billing_period_start=sub.current_period_start,
            billing_period_end=sub.current_period_end,
            due_date=_now() + timedelta(days=3),
            line_items=line_items,
        )
        self.db.add(invoice)
        await self.db.flush()
        return invoice

    # ── Usage meter init ──────────────────────────────────────────────────────

    async def _create_usage_meter(self, sub: Subscription) -> UsageMeter:
        meter = UsageMeter(
            org_id=sub.org_id,
            subscription_id=sub.id,
            period_start=sub.current_period_start,
            period_end=sub.current_period_end,
        )
        self.db.add(meter)
        await self.db.flush()
        return meter

    # ── Audit event ───────────────────────────────────────────────────────────

    async def _log_event(
        self,
        sub: Subscription,
        event_type: SubscriptionEventType,
        actor_id: Optional[str] = None,
        actor_type: str = "org",
        from_plan_id: Optional[uuid.UUID] = None,
        to_plan_id: Optional[uuid.UUID] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        self.db.add(SubscriptionEvent(
            org_id=sub.org_id,
            subscription_id=sub.id,
            event_type=event_type.value,
            from_plan_id=from_plan_id,
            to_plan_id=to_plan_id,
            actor_id=uuid.UUID(actor_id) if actor_id else None,
            actor_type=actor_type,
            metadata=metadata,
        ))
