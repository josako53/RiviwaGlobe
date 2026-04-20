"""
events/publisher.py
═══════════════════════════════════════════════════════════════════════════════
Typed domain event publisher.

Wraps KafkaEventProducer with per-entity publish methods that build a
standard event envelope and fire publish() on the underlying producer.

Event envelope
──────────────
    {
        "event_type":     "user.registered",
        "event_id":       "uuid4",
        "occurred_at":    "2024-01-15T10:30:00.000000Z",
        "schema_version": "1.0",
        "service":        "riviwa_auth_service",
        "payload":        { … entity-specific fields … }
    }

  event_id  — consumers use this UUID for idempotent deduplication.
  occurred_at — wall-clock time at point of publish (not DB commit time).
  schema_version — bump when payload shape changes; consumers can gate on it.

At-least-once delivery
──────────────────────
  The Kafka producer is configured with acks="all", enable_idempotence=True,
  and retries=5.  Consumers MUST be idempotent (deduplicate on event_id).

Fire-and-forget
──────────────────────────────────────────────
  Kafka publish failures are LOGGED but NEVER raised to the caller.
  The committed DB transaction is never rolled back due to a broker fault.
  For strict at-least-once with rollback safety, adopt the transactional
  outbox pattern (DB row → Debezium → Kafka).

Dependency injection
──────────────────────────────────────────────
  EventPublisher is constructed once per request by the FastAPI dependency:

      async def get_publisher(
          producer: KafkaEventProducer = Depends(get_kafka_producer_dep),
      ) -> EventPublisher:
          return EventPublisher(producer)

  The producer is passed in rather than fetched lazily so that tests can
  inject a mock without patching module globals.

Named methods — complete inventory
──────────────────────────────────────────────
  USER
    user_registered(user, method)
    user_registered_social(user, provider)
    user_registration_blocked(email, ip_address, fraud_score)
    user_email_verified(user)
    user_phone_verified(user)
    user_id_verification_required(user, verification_session_id)
    user_id_verified(user)
    user_status_changed(user, event_type, reason)
    user_password_changed(user, all_sessions_revoked)
    user_password_reset(user)
    user_profile_updated(user, changed_fields)
    user_oauth_linked(user, provider)

  ORGANISATION
    organisation_created(org, created_by_id)
    organisation_updated(org, changed_fields)
    organisation_verified(org, verified_by_id)
    organisation_status_changed(org, event_type, reason)
    organisation_member_added(membership, invited_by_id)
    organisation_member_removed(org_id, user_id, removed_by_id, reason)
    organisation_member_role_changed(org_id, user_id, from_role, to_role, changed_by_id)
    organisation_ownership_transferred(org_id, previous_owner_id, new_owner_id)
    organisation_invite_sent(org_id, invited_by_id, invited_email, invited_user_id, invited_role)
    organisation_invite_accepted(org_id, user_id, invite_id)
    organisation_invite_declined(org_id, user_id, invite_id)
    organisation_invite_cancelled(org_id, invite_id, cancelled_by_id)

  AUTH
    auth_login_success(user_id, ip_address, user_agent)
    auth_login_failed(identifier, ip_address, reason)
    auth_login_locked(user_id, ip_address)
    auth_logout(user_id, jti)
    auth_token_refreshed(user_id, ip_address)
    auth_dashboard_switched(user_id, org_id)

  FRAUD
    fraud_score_computed(user_id, total_score, action, details)
    fraud_id_verification_passed(user_id, provider)
    fraud_id_verification_failed(user_id, provider, rejection_reason)

  ADDRESS  (topic: riviwa.organisation.events — consumed by stakeholder_service)
    address_created(address, created_by_id)
    address_updated(address, changed_fields)
    address_deleted(address_id, entity_type, entity_id)
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog

from core.config import settings
from events.topics import AddressEvents, AuthEvents, FraudEvents, KafkaTopics, OrgDepartmentEvents, OrgEvents, OrgServiceEvents, OrgProjectEvents, OrgProjectStageEvents, UserEvents
from models.organisation import Organisation, OrganisationMember
from models.user import User
from workers.kafka_producer import KafkaEventProducer

log = structlog.get_logger(__name__)


class EventPublisher:
    """
    Typed domain event publisher.
    Instantiate once per request via FastAPI dependency injection.
    Pass the KafkaEventProducer singleton in; do not fetch it lazily.
    """

    def __init__(self, producer: KafkaEventProducer) -> None:
        self._producer = producer

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _envelope(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Build the standard event envelope."""
        return {
            "event_type":     event_type,
            "event_id":       str(uuid.uuid4()),
            "occurred_at":    datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0",
            "service":        settings.RIVIWA_AUTH_SERVICE_NAME,
            "payload":        payload,
        }

    async def _publish(
        self,
        topic:      str,
        event_type: str,
        key:        str,
        payload:    dict[str, Any],
    ) -> None:
        """
        Build envelope, publish to Kafka, swallow exceptions.

        Failures are logged with full context but never re-raised so that a
        broker fault never rolls back a committed DB transaction.
        """
        envelope = self._envelope(event_type, payload)
        try:
            await self._producer.publish(topic=topic, value=envelope, key=key)
            log.debug(
                "event.published",
                topic=topic,
                event_type=event_type,
                key=key,
                event_id=envelope["event_id"],
            )
        except Exception as exc:
            log.error(
                "event.publish_failed",
                topic=topic,
                event_type=event_type,
                key=key,
                error=str(exc),
                exc_info=exc,
            )

    # ─────────────────────────────────────────────────────────────────────────
    # User events
    # ─────────────────────────────────────────────────────────────────────────

    async def user_registered(
        self,
        user:   User,
        method: str = "email_phone",   # "email_phone" | "google" | "apple" | "facebook"
    ) -> None:
        await self._publish(
            topic=KafkaTopics.USER_EVENTS,
            event_type=UserEvents.REGISTERED,
            key=str(user.id),
            payload={
                "user_id":      str(user.id),
                "username":     user.username,
                "email":        user.email,
                "phone_number": user.phone_number,
                "status":       user.status.value,
                "method":       method,
                "country_code": user.country_code,
                "language":     user.language,
                "fraud_score":  user.fraud_score,
                "created_at":   user.created_at.isoformat() if user.created_at else None,
            },
        )

    async def user_registered_social(
        self,
        user:     User,
        provider: str,   # "google" | "apple" | "facebook"
    ) -> None:
        await self._publish(
            topic=KafkaTopics.USER_EVENTS,
            event_type=UserEvents.REGISTERED_SOCIAL,
            key=str(user.id),
            payload={
                "user_id":        str(user.id),
                "username":       user.username,
                "email":          user.email,
                "status":         user.status.value,
                "oauth_provider": provider,
                "country_code":   user.country_code,
                "created_at":     user.created_at.isoformat() if user.created_at else None,
            },
        )

    async def user_registration_blocked(
        self,
        email:       str,
        ip_address:  str,
        fraud_score: int,
    ) -> None:
        """
        Fired when the fraud engine hard-blocks a registration before any
        User row is created.  No user_id is available; key = sha256(email)[:16].
        """
        key = hashlib.sha256(email.encode()).hexdigest()[:16]
        await self._publish(
            topic=KafkaTopics.USER_EVENTS,
            event_type=UserEvents.REGISTRATION_BLOCKED,
            key=key,
            payload={
                "email":       email,
                "ip_address":  ip_address,
                "fraud_score": fraud_score,
            },
        )

    async def user_email_verified(self, user: User) -> None:
        await self._publish(
            topic=KafkaTopics.USER_EVENTS,
            event_type=UserEvents.EMAIL_VERIFIED,
            key=str(user.id),
            payload={
                "user_id":           str(user.id),
                "email":             user.email,
                "email_verified_at": (
                    user.email_verified_at.isoformat()
                    if user.email_verified_at else None
                ),
            },
        )

    async def user_phone_verified(self, user: User) -> None:
        await self._publish(
            topic=KafkaTopics.USER_EVENTS,
            event_type=UserEvents.PHONE_VERIFIED,
            key=str(user.id),
            payload={
                "user_id":      str(user.id),
                "phone_number": user.phone_number,
            },
        )

    async def user_id_verification_required(
        self,
        user:                    User,
        verification_session_id: str,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.USER_EVENTS,
            event_type=UserEvents.ID_VERIFICATION_REQUIRED,
            key=str(user.id),
            payload={
                "user_id":                 str(user.id),
                "verification_session_id": verification_session_id,
                "fraud_score":             user.fraud_score,
            },
        )

    async def user_id_verified(self, user: User) -> None:
        await self._publish(
            topic=KafkaTopics.USER_EVENTS,
            event_type=UserEvents.ID_VERIFIED,
            key=str(user.id),
            payload={
                "user_id":        str(user.id),
                "id_verified_at": (
                    user.id_verified_at.isoformat()
                    if user.id_verified_at else None
                ),
            },
        )

    async def user_status_changed(
        self,
        user:       User,
        event_type: str,   # UserEvents.SUSPENDED | BANNED | DEACTIVATED | REACTIVATED
        reason:     Optional[str] = None,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.USER_EVENTS,
            event_type=event_type,
            key=str(user.id),
            payload={
                "user_id": str(user.id),
                "status":  user.status.value,
                "reason":  reason,
            },
        )

    async def user_password_changed(
        self,
        user:                 User,
        all_sessions_revoked: bool = True,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.USER_EVENTS,
            event_type=UserEvents.PASSWORD_CHANGED,
            key=str(user.id),
            payload={
                "user_id":              str(user.id),
                "all_sessions_revoked": all_sessions_revoked,
            },
        )

    async def user_password_reset(self, user: User) -> None:
        await self._publish(
            topic=KafkaTopics.USER_EVENTS,
            event_type=UserEvents.PASSWORD_RESET,
            key=str(user.id),
            payload={"user_id": str(user.id), "email": user.email},
        )

    async def user_profile_updated(
        self,
        user:           User,
        changed_fields: list[str],
    ) -> None:
        await self._publish(
            topic=KafkaTopics.USER_EVENTS,
            event_type=UserEvents.PROFILE_UPDATED,
            key=str(user.id),
            payload={
                "user_id":        str(user.id),
                "changed_fields": changed_fields,
            },
        )

    async def user_oauth_linked(self, user: User, provider: str) -> None:
        await self._publish(
            topic=KafkaTopics.USER_EVENTS,
            event_type=UserEvents.OAUTH_LINKED,
            key=str(user.id),
            payload={"user_id": str(user.id), "provider": provider},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Organisation events
    # ─────────────────────────────────────────────────────────────────────────

    async def organisation_created(
        self,
        org:           Organisation,
        created_by_id: uuid.UUID,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgEvents.CREATED,
            key=str(org.id),
            payload={
                "org_id":        str(org.id),
                "slug":          org.slug,
                "legal_name":    org.legal_name,
                "display_name":  org.display_name,
                "org_type":      org.org_type.value,
                "status":        org.status.value,
                "country_code":  org.country_code,
                "created_by_id": str(created_by_id),
                "created_at":    org.created_at.isoformat() if org.created_at else None,
            },
        )

    async def organisation_updated(
        self,
        org:            Organisation,
        changed_fields: list[str],
    ) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgEvents.UPDATED,
            key=str(org.id),
            payload={
                "org_id":         str(org.id),
                "changed_fields": changed_fields,
                # Include current profile so consumers can sync names/logo
                "display_name":   org.display_name,
                "legal_name":     org.legal_name,
                "logo_url":       getattr(org, "logo_url", None),
            },
        )

    async def organisation_verified(
        self,
        org:            Organisation,
        verified_by_id: uuid.UUID,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgEvents.VERIFIED,
            key=str(org.id),
            payload={
                "org_id":         str(org.id),
                "verified_by_id": str(verified_by_id),
                "verified_at":    org.verified_at.isoformat() if org.verified_at else None,
            },
        )

    async def organisation_status_changed(
        self,
        org:        Organisation,
        event_type: str,   # OrgEvents.SUSPENDED | BANNED | DEACTIVATED
        reason:     Optional[str] = None,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=event_type,
            key=str(org.id),
            payload={
                "org_id": str(org.id),
                "status": org.status.value,
                "reason": reason,
            },
        )

    async def organisation_member_added(
        self,
        membership:    OrganisationMember,
        invited_by_id: Optional[uuid.UUID] = None,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgEvents.MEMBER_ADDED,
            key=str(membership.organisation_id),
            payload={
                "org_id":        str(membership.organisation_id),
                "user_id":       str(membership.user_id),
                "org_role":      membership.org_role.value,
                "invited_by_id": str(invited_by_id) if invited_by_id else None,
                "joined_at":     membership.joined_at.isoformat() if membership.joined_at else None,
            },
        )

    async def organisation_member_removed(
        self,
        org_id:        uuid.UUID,
        user_id:       uuid.UUID,
        removed_by_id: uuid.UUID,
        reason:        Optional[str] = None,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgEvents.MEMBER_REMOVED,
            key=str(org_id),
            payload={
                "org_id":        str(org_id),
                "user_id":       str(user_id),
                "removed_by_id": str(removed_by_id),
                "reason":        reason,
            },
        )

    async def organisation_member_role_changed(
        self,
        org_id:        uuid.UUID,
        user_id:       uuid.UUID,
        from_role:     str,
        to_role:       str,
        changed_by_id: uuid.UUID,
    ) -> None:
        """Replaces the direct _publish() call in organisation_service.change_member_role."""
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgEvents.MEMBER_ROLE_CHANGED,
            key=str(org_id),
            payload={
                "org_id":        str(org_id),
                "user_id":       str(user_id),
                "from_role":     from_role,
                "to_role":       to_role,
                "changed_by_id": str(changed_by_id),
            },
        )

    async def organisation_ownership_transferred(
        self,
        org_id:            uuid.UUID,
        previous_owner_id: uuid.UUID,
        new_owner_id:      uuid.UUID,
    ) -> None:
        """Replaces the direct _publish() call in organisation_service.transfer_ownership."""
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgEvents.OWNER_TRANSFERRED,
            key=str(org_id),
            payload={
                "org_id":            str(org_id),
                "previous_owner_id": str(previous_owner_id),
                "new_owner_id":      str(new_owner_id),
            },
        )

    async def organisation_invite_sent(
        self,
        org_id:          uuid.UUID,
        invited_by_id:   uuid.UUID,
        invited_email:   Optional[str],
        invited_user_id: Optional[uuid.UUID],
        invited_role:    str,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgEvents.INVITE_SENT,
            key=str(org_id),
            payload={
                "org_id":          str(org_id),
                "invited_by_id":   str(invited_by_id),
                "invited_email":   invited_email,
                "invited_user_id": str(invited_user_id) if invited_user_id else None,
                "invited_role":    invited_role,
            },
        )

    async def organisation_invite_accepted(
        self,
        org_id:    uuid.UUID,
        user_id:   uuid.UUID,
        invite_id: uuid.UUID,
    ) -> None:
        """Replaces the direct _publish() call in organisation_service.accept_invite."""
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgEvents.INVITE_ACCEPTED,
            key=str(org_id),
            payload={
                "org_id":    str(org_id),
                "user_id":   str(user_id),
                "invite_id": str(invite_id),
            },
        )

    async def organisation_invite_declined(
        self,
        org_id:    uuid.UUID,
        user_id:   uuid.UUID,
        invite_id: uuid.UUID,
    ) -> None:
        """Replaces the direct _publish() call in organisation_service.decline_invite."""
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgEvents.INVITE_DECLINED,
            key=str(org_id),
            payload={
                "org_id":    str(org_id),
                "user_id":   str(user_id),
                "invite_id": str(invite_id),
            },
        )

    async def organisation_invite_cancelled(
        self,
        org_id:          uuid.UUID,
        invite_id:       uuid.UUID,
        cancelled_by_id: uuid.UUID,
    ) -> None:
        """Replaces the direct _publish() call in organisation_service.cancel_invite."""
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgEvents.INVITE_CANCELLED,
            key=str(org_id),
            payload={
                "org_id":          str(org_id),
                "invite_id":       str(invite_id),
                "cancelled_by_id": str(cancelled_by_id),
            },
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Auth events
    # ─────────────────────────────────────────────────────────────────────────

    async def auth_login_success(
        self,
        user_id:    uuid.UUID,
        ip_address: str,
        user_agent: Optional[str] = None,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.AUTH_EVENTS,
            event_type=AuthEvents.LOGIN_SUCCESS,
            key=str(user_id),
            payload={
                "user_id":    str(user_id),
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
        )

    async def auth_login_failed(
        self,
        identifier: str,
        ip_address: str,
        reason:     str,
    ) -> None:
        """
        The raw identifier (email / phone) is hashed before publishing.
        Never emit PII into the event bus — downstream services receive
        only the truncated hash for correlation.
        """
        identifier_hash = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        await self._publish(
            topic=KafkaTopics.AUTH_EVENTS,
            event_type=AuthEvents.LOGIN_FAILED,
            key=identifier_hash,
            payload={
                "identifier_hash": identifier_hash,
                "ip_address":      ip_address,
                "reason":          reason,
            },
        )

    async def auth_login_locked(
        self,
        user_id:    uuid.UUID,
        ip_address: str,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.AUTH_EVENTS,
            event_type=AuthEvents.LOGIN_LOCKED,
            key=str(user_id),
            payload={"user_id": str(user_id), "ip_address": ip_address},
        )

    async def auth_logout(self, user_id: uuid.UUID, jti: str) -> None:
        await self._publish(
            topic=KafkaTopics.AUTH_EVENTS,
            event_type=AuthEvents.LOGOUT,
            key=str(user_id),
            payload={"user_id": str(user_id), "jti": jti},
        )

    async def auth_token_refreshed(
        self,
        user_id:    uuid.UUID,
        ip_address: str,
    ) -> None:
        """Replaces the direct _publish() call in auth_service.refresh_tokens."""
        await self._publish(
            topic=KafkaTopics.AUTH_EVENTS,
            event_type=AuthEvents.TOKEN_REFRESHED,
            key=str(user_id),
            payload={"user_id": str(user_id), "ip_address": ip_address},
        )

    async def auth_dashboard_switched(
        self,
        user_id: uuid.UUID,
        org_id:  Optional[uuid.UUID],
    ) -> None:
        await self._publish(
            topic=KafkaTopics.AUTH_EVENTS,
            event_type=AuthEvents.DASHBOARD_SWITCHED,
            key=str(user_id),
            payload={
                "user_id": str(user_id),
                "org_id":  str(org_id) if org_id else None,
                "view":    "org" if org_id else "personal",
            },
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Fraud events
    # ─────────────────────────────────────────────────────────────────────────

    async def fraud_score_computed(
        self,
        user_id:     Optional[uuid.UUID],
        total_score: int,
        action:      str,
        details:     dict,
    ) -> None:
        key = str(user_id) if user_id else "anonymous"
        await self._publish(
            topic=KafkaTopics.FRAUD_EVENTS,
            event_type=FraudEvents.SCORE_COMPUTED,
            key=key,
            payload={
                "user_id":     str(user_id) if user_id else None,
                "total_score": total_score,
                "action":      action,
                "details":     details,
            },
        )

    async def fraud_id_verification_passed(
        self,
        user_id:  uuid.UUID,
        provider: str,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.FRAUD_EVENTS,
            event_type=FraudEvents.ID_VERIFICATION_PASSED,
            key=str(user_id),
            payload={"user_id": str(user_id), "provider": provider},
        )

    async def fraud_id_verification_failed(
        self,
        user_id:          uuid.UUID,
        provider:         str,
        rejection_reason: Optional[str] = None,
    ) -> None:
        await self._publish(
            topic=KafkaTopics.FRAUD_EVENTS,
            event_type=FraudEvents.ID_VERIFICATION_FAILED,
            key=str(user_id),
            payload={
                "user_id":          str(user_id),
                "provider":         provider,
                "rejection_reason": rejection_reason,
            },
        )

    # ── OrgService events ─────────────────────────────────────────────────────
    # These are published to KafkaTopics.ORG_EVENTS and consumed by
    # stakeholder_service and feedback_service to maintain their ProjectCache.

    def _org_service_payload(self, service) -> dict:
        """Build the standard ProjectCache sync payload from an OrgService row."""
        return {
            "org_service_id":     str(service.id),
            "org_id":             str(service.organisation_id),
            "org_branch_id":      str(service.branch_id) if service.branch_id else None,
            "title":              service.title,
            "slug":               service.slug,
            "service_type":       service.service_type.value if hasattr(service.service_type, "value") else str(service.service_type),
            "delivery_mode":      service.delivery_mode.value if hasattr(service.delivery_mode, "value") else str(service.delivery_mode),
            "status":             service.status.value if hasattr(service.status, "value") else str(service.status),
            "category":           service.category,
            "description":        service.summary,
            "country_code":       None,   # resolved at service layer if needed
            "primary_lga":        None,
            # Default acceptance flags — all true unless overridden at stage level
            "accepts_grievances":  True,
            "accepts_suggestions": True,
            "accepts_applause":    True,
        }

    async def org_service_published(self, service) -> None:
        """
        Published when an OrgService transitions DRAFT → ACTIVE (publish_service).
        Triggers ProjectCache creation in stakeholder_service and feedback_service.
        """
        await self._publish(
            topic      = KafkaTopics.ORG_EVENTS,
            event_type = OrgServiceEvents.PUBLISHED,
            key        = str(service.id),
            payload    = self._org_service_payload(service),
        )

    async def org_service_updated(self, service, changed_fields: list[str]) -> None:
        """
        Published when an active OrgService's content changes (update_service).
        Downstream services update their cached fields.
        """
        payload = self._org_service_payload(service)
        payload["changed_fields"] = changed_fields
        await self._publish(
            topic      = KafkaTopics.ORG_EVENTS,
            event_type = OrgServiceEvents.UPDATED,
            key        = str(service.id),
            payload    = payload,
        )

    async def org_service_suspended(self, service) -> None:
        """Published when an OrgService is suspended. ProjectCache.status → SUSPENDED."""
        await self._publish(
            topic      = KafkaTopics.ORG_EVENTS,
            event_type = OrgServiceEvents.SUSPENDED,
            key        = str(service.id),
            payload    = {"org_service_id": str(service.id), "status": "suspended"},
        )

    async def org_service_closed(self, service) -> None:
        """Published when an OrgService is archived/deleted. ProjectCache.status → CLOSED."""
        await self._publish(
            topic      = KafkaTopics.ORG_EVENTS,
            event_type = OrgServiceEvents.CLOSED,
            key        = str(service.id),
            payload    = {"org_service_id": str(service.id), "status": "closed"},
        )

    # ── OrgProject events ─────────────────────────────────────────────────────
    # Published to KafkaTopics.ORG_EVENTS and consumed by
    # stakeholder_service and feedback_service to maintain ProjectCache.

    def _project_payload(self, project, status_override: str | None = None) -> dict:
        """Build standard ProjectCache sync payload from an OrgProject row."""
        return {
            "id":                  str(project.id),
            "organisation_id":     str(project.organisation_id),
            "branch_id":           str(project.branch_id) if project.branch_id else None,
            "org_service_id":      str(project.org_service_id) if project.org_service_id else None,
            "name":                project.name,
            "slug":                project.slug,
            "status":              status_override or (project.status.value if hasattr(project.status, "value") else str(project.status)),
            "category":            project.category,
            "sector":              getattr(project, "sector", None),
            "description":         project.description,
            "country_code":        project.country_code,
            "region":              getattr(project, "region", None),
            "primary_lga":         project.primary_lga,
            "start_date":          project.start_date.isoformat() if project.start_date else None,
            "end_date":            project.end_date.isoformat()   if project.end_date   else None,
            "accepts_grievances":  project.accepts_grievances,
            "accepts_suggestions": project.accepts_suggestions,
            "accepts_applause":    project.accepts_applause,
            "requires_grm":        getattr(project, "requires_grm", False),
            # ── Media — received by consumers to sync ProjectCache ──────────
            "cover_image_url":     getattr(project, "cover_image_url", None),
            "org_logo_url":        None,  # populated by org.events logo upload
            # ── Org identity — consumers can cache org name without extra calls
            "org_display_name":    getattr(project, "organisation", None) and getattr(project.organisation, "display_name", None),
        }

    def _stage_payload(self, stage, project, status_override: str | None = None) -> dict:
        """Build standard ProjectStageCache sync payload from an OrgProjectStage row."""
        return {
            "stage_id":            str(stage.id),
            "project_id":          str(stage.project_id),
            "organisation_id":     str(project.organisation_id),
            "name":                stage.name,
            "stage_order":         stage.stage_order,
            "status":              status_override or (stage.status.value if hasattr(stage.status, "value") else str(stage.status)),
            "description":         stage.description,
            "start_date":          stage.start_date.isoformat() if stage.start_date else None,
            "end_date":            stage.end_date.isoformat()   if stage.end_date   else None,
            "accepts_grievances":  stage.accepts_grievances,
            "accepts_suggestions": stage.accepts_suggestions,
            "accepts_applause":    stage.accepts_applause,
        }

    async def org_project_published(self, project) -> None:
        """PLANNING → ACTIVE. Triggers ProjectCache creation downstream."""
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgProjectEvents.PUBLISHED,
            key=str(project.id),
            payload=self._project_payload(project, "active"),
        )

    async def org_project_updated(self, project, changed_fields: list[str]) -> None:
        payload = self._project_payload(project)
        payload["changed_fields"] = changed_fields
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgProjectEvents.UPDATED,
            key=str(project.id),
            payload=payload,
        )

    async def org_project_paused(self, project) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgProjectEvents.PAUSED,
            key=str(project.id),
            payload=self._project_payload(project, "paused"),
        )

    async def org_project_resumed(self, project) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgProjectEvents.RESUMED,
            key=str(project.id),
            payload=self._project_payload(project, "active"),
        )

    async def org_project_completed(self, project) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgProjectEvents.COMPLETED,
            key=str(project.id),
            payload=self._project_payload(project, "completed"),
        )

    async def org_project_cancelled(self, project) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgProjectEvents.CANCELLED,
            key=str(project.id),
            payload=self._project_payload(project, "cancelled"),
        )

    async def org_project_stage_activated(self, stage, project) -> None:
        """
        Critical: triggers ProjectStageCache.status → ACTIVE downstream.
        Downstream services use the accepts_* flags on the stage to override
        project-level feedback gates for the duration of this stage.
        """
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgProjectStageEvents.ACTIVATED,
            key=str(project.id),
            payload=self._stage_payload(stage, project, "active"),
        )

    async def org_project_stage_completed(self, stage, project) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgProjectStageEvents.COMPLETED,
            key=str(project.id),
            payload=self._stage_payload(stage, project, "completed"),
        )

    async def org_project_stage_skipped(self, stage, project) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgProjectStageEvents.SKIPPED,
            key=str(project.id),
            payload=self._stage_payload(stage, project, "skipped"),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Address events  (topic: riviwa.organisation.events)
    # Consumed by stakeholder_service to keep soft-link address data in sync.
    # Partition key = entity_id so all address events for an entity are ordered.
    # ─────────────────────────────────────────────────────────────────────────

    async def address_created(self, address, created_by_id: Optional[uuid.UUID] = None) -> None:
        """Fired when a new Address row is persisted."""
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=AddressEvents.CREATED,
            key=str(address.entity_id),
            payload={
                "address_id":   str(address.id),
                "entity_type":  address.entity_type,
                "entity_id":    str(address.entity_id),
                "address_type": address.address_type,
                "source":       address.source,
                "is_default":   address.is_default,
                "region":       address.region,
                "district":     address.district,
                "lga":          address.lga,
                "ward":         address.ward,
                "mtaa":         address.mtaa,
                "display_name": address.display_name,
                "gps_latitude":  address.gps_latitude,
                "gps_longitude": address.gps_longitude,
                "created_by_id": str(created_by_id) if created_by_id else None,
            },
        )

    async def address_updated(self, address, changed_fields: list[str]) -> None:
        """Fired when address fields are modified (PATCH or set-default)."""
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=AddressEvents.UPDATED,
            key=str(address.entity_id),
            payload={
                "address_id":    str(address.id),
                "entity_type":   address.entity_type,
                "entity_id":     str(address.entity_id),
                "changed_fields": changed_fields,
                "is_default":    address.is_default,
                "region":        address.region,
                "district":      address.district,
                "lga":           address.lga,
                "ward":          address.ward,
                "mtaa":          address.mtaa,
                "display_name":  address.display_name,
                "gps_latitude":  address.gps_latitude,
                "gps_longitude": address.gps_longitude,
            },
        )

    async def address_deleted(
        self,
        address_id:  uuid.UUID,
        entity_type: str,
        entity_id:   uuid.UUID,
    ) -> None:
        """
        Fired after an Address row is deleted.
        stakeholder_service consumers must null Stakeholder.address_id
        wherever it equals address_id.
        """
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=AddressEvents.DELETED,
            key=str(entity_id),
            payload={
                "address_id":  str(address_id),
                "entity_type": entity_type,
                "entity_id":   str(entity_id),
            },
        )

    # ── Department events ─────────────────────────────────────────────────────

    def _dept_payload(self, dept) -> dict:
        return {
            "department_id": str(dept.id),
            "org_id":        str(dept.org_id),
            "branch_id":     str(dept.branch_id) if dept.branch_id else None,
            "name":          dept.name,
            "code":          dept.code,
            "is_active":     dept.is_active,
        }

    async def org_department_created(self, dept) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgDepartmentEvents.CREATED,
            key=str(dept.org_id),
            payload=self._dept_payload(dept),
        )

    async def org_department_updated(self, dept, changed_fields: list[str]) -> None:
        payload = self._dept_payload(dept)
        payload["changed_fields"] = changed_fields
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgDepartmentEvents.UPDATED,
            key=str(dept.org_id),
            payload=payload,
        )

    async def org_department_deactivated(self, dept) -> None:
        await self._publish(
            topic=KafkaTopics.ORG_EVENTS,
            event_type=OrgDepartmentEvents.DEACTIVATED,
            key=str(dept.org_id),
            payload=self._dept_payload(dept),
        )
