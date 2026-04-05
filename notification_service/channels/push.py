# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  channels/push.py
# ───────────────────────────────────────────────────────────────────────────
"""
channels/push.py
─────────────────────────────────────────────────────────────────────────────
Push notification channel — Firebase Cloud Messaging (FCM) + APNs.

FCM covers:  Android devices, web browsers
APNs covers: iOS devices

Tokens come from NotificationDevice table, loaded by DeliveryService and
passed in as payload.push_tokens.

FCM is used as the primary provider.  For iOS apps using FCM SDK, FCM
handles APNs proxying — no separate APNs integration needed unless the iOS
app uses native APNs (not Firebase).

Priority mapping:
  critical → FCM.priority=HIGH + apns-priority=10
  high     → FCM.priority=HIGH
  medium   → FCM.priority=NORMAL
  low      → FCM.priority=NORMAL

Invalid token handling:
  · INVALID_REGISTRATION / NOT_REGISTERED → permanent_fail (token must be removed)
  · QUOTA_EXCEEDED → should_retry = True
  · Everything else → should_retry = True
"""
from __future__ import annotations

import json
import structlog

from channels.base import BaseChannel, ChannelPayload, ChannelResult
from core.config import settings

log = structlog.get_logger(__name__)


class PushChannel(BaseChannel):

    channel_name = "push"

    def is_configured(self) -> bool:
        return bool(settings.FCM_SERVICE_ACCOUNT_JSON and settings.FCM_PROJECT_ID)

    async def send(self, payload: ChannelPayload) -> ChannelResult:
        if not payload.push_tokens:
            return ChannelResult.permanent_fail(
                "No push tokens available for this user/device."
            )

        if not self.is_configured():
            return ChannelResult.fail("FCM not configured.", should_retry=False)

        try:
            import firebase_admin
            from firebase_admin import credentials, messaging

            # Initialise Firebase app once
            if not firebase_admin._apps:
                cred_dict = json.loads(settings.FCM_SERVICE_ACCOUNT_JSON)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)

            fcm_priority = (
                "high"
                if payload.priority in ("critical", "high")
                else "normal"
            )

            # Send to each token; collect results
            errors = []
            sent_ids = []

            for token in payload.push_tokens:
                message = messaging.Message(
                    token=token,
                    notification=messaging.Notification(
                        title=payload.rendered_title or "",
                        body=payload.rendered_body,
                    ),
                    data={
                        "notification_type": payload.notification_type,
                        "language":          payload.language,
                    },
                    android=messaging.AndroidConfig(
                        priority=fcm_priority,
                        notification=messaging.AndroidNotification(
                            sound="default",
                        ),
                    ),
                    apns=messaging.APNSConfig(
                        headers={"apns-priority": "10" if fcm_priority == "high" else "5"},
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(sound="default"),
                        ),
                    ),
                )
                try:
                    message_id = messaging.send(message)
                    sent_ids.append(message_id)
                except messaging.UnregisteredError:
                    log.warning("push.token_unregistered", token=token[:20])
                    errors.append(f"token {token[:12]}... is unregistered")
                except messaging.InvalidArgumentError as exc:
                    errors.append(str(exc))
                except Exception as exc:
                    errors.append(str(exc))
                    log.error("push.send_failed", token=token[:20], error=str(exc))

            if sent_ids:
                return ChannelResult.ok(
                    provider_message_id=";".join(sent_ids[:3])
                )
            permanent = all("unregistered" in e or "invalid" in e.lower() for e in errors)
            return (
                ChannelResult.permanent_fail("; ".join(errors))
                if permanent
                else ChannelResult.fail("; ".join(errors))
            )

        except ImportError:
            return ChannelResult.fail(
                "firebase-admin not installed. Run: pip install firebase-admin",
                should_retry=False,
            )
        except Exception as exc:
            log.error("push.unexpected_error", error=str(exc))
            return ChannelResult.fail(str(exc))
