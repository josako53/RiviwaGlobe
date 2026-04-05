# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  channels/in_app.py
# ───────────────────────────────────────────────────────────────────────────
"""
channels/in_app.py
─────────────────────────────────────────────────────────────────────────────
In-app notification channel.

Unlike external channels, in_app delivery is always immediate and never
fails from a transport perspective.  The "send" is simply a no-op here —
the delivery record itself (created by DeliveryService) IS the notification.

Mobile/web clients poll GET /api/v1/notifications/unread or use SSE.
Read receipts are posted to PATCH /api/v1/notifications/deliveries/{id}/read.
"""
from __future__ import annotations

from channels.base import BaseChannel, ChannelPayload, ChannelResult


class InAppChannel(BaseChannel):

    channel_name = "in_app"

    async def send(self, payload: ChannelPayload) -> ChannelResult:
        """
        In-app notifications are stored as delivery records in the DB by
        DeliveryService before calling this method.  Nothing to dispatch here.
        """
        return ChannelResult.ok(provider_message_id="in_app_stored")

    def is_configured(self) -> bool:
        return True  # always available
