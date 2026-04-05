# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  services/template_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/template_service.py
═══════════════════════════════════════════════════════════════════════════════
Looks up NotificationTemplate rows and renders them with Jinja2.

Template lookup strategy:
  1. Exact match: (notification_type, channel, language)
  2. Language fallback: (notification_type, channel, "en")  — if sw not found
  3. Returns None if no template found → DeliveryService skips this channel

The notification_service is IGNORANT of what variables mean.  It just
renders {{ feedback_ref }} as-is, whatever the originating service provides.
Unknown variables silently render as empty string (Jinja2 undefined=Undefined).

Templates are cached in memory for 5 minutes to reduce DB lookups.
"""
from __future__ import annotations

import time
from typing import Optional

import structlog
from jinja2 import Environment, Undefined
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import NotificationTemplate
from events.topics import NotificationChannel

log = structlog.get_logger(__name__)

# Simple in-process cache: {(type, channel, lang) → (template, timestamp)}
_TEMPLATE_CACHE: dict[tuple, tuple] = {}
_CACHE_TTL_SEC = 300  # 5 minutes


# Jinja2 environment — undefined variables render as empty string
_jinja = Environment(
    autoescape=False,       # SMS/push; email templates handle their own escaping
    undefined=Undefined,    # unknown variables → empty string, no error
)


class RenderedMessage:
    """Output of template rendering — ready to pass to a channel."""
    __slots__ = ("title", "subject", "body")

    def __init__(
        self,
        title:   Optional[str],
        subject: Optional[str],
        body:    str,
    ) -> None:
        self.title   = title
        self.subject = subject
        self.body    = body


class TemplateService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Public API ────────────────────────────────────────────────────────────

    async def render(
        self,
        notification_type: str,
        channel:           str,
        language:          str,
        variables:         dict,
    ) -> Optional[RenderedMessage]:
        """
        Load the best matching template and render it with variables.
        Returns None if no template exists for this combination.
        """
        tmpl = await self._load(notification_type, channel, language)
        if tmpl is None:
            return None
        if not tmpl.is_active:
            log.debug("template.inactive_skipped",
                      notification_type=notification_type, channel=channel)
            return None

        return RenderedMessage(
            title   = self._render_str(tmpl.title_template,   variables),
            subject = self._render_str(tmpl.subject_template, variables),
            body    = self._render_str(tmpl.body_template,    variables) or "",
        )

    # ── Template loader with cache ────────────────────────────────────────────

    async def _load(
        self,
        notification_type: str,
        channel:           str,
        language:          str,
    ) -> Optional[NotificationTemplate]:
        # Try exact language first, then 'en' fallback
        for lang in [language, "en"]:
            key = (notification_type, channel, lang)
            cached = _TEMPLATE_CACHE.get(key)
            if cached:
                tmpl, ts = cached
                if time.monotonic() - ts < _CACHE_TTL_SEC:
                    return tmpl

            # DB lookup
            q = select(NotificationTemplate).where(
                NotificationTemplate.notification_type == notification_type,
                NotificationTemplate.channel           == channel,
                NotificationTemplate.language          == lang,
            )
            row = (await self.db.execute(q)).scalar_one_or_none()
            if row:
                _TEMPLATE_CACHE[key] = (row, time.monotonic())
                return row

        log.debug("template.not_found",
                  notification_type=notification_type,
                  channel=channel,
                  language=language)
        return None

    # ── Render helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _render_str(
        template_src: Optional[str],
        variables:    dict,
    ) -> Optional[str]:
        if not template_src:
            return None
        try:
            return _jinja.from_string(template_src).render(**(variables or {}))
        except Exception as exc:
            log.warning("template.render_error", error=str(exc), src=template_src[:80])
            return template_src  # fallback: return raw template rather than empty

    # ── Invalidate cache (called when templates are updated via API) ───────────

    @staticmethod
    def invalidate_cache(
        notification_type: Optional[str] = None,
        channel:           Optional[str] = None,
        language:          Optional[str] = None,
    ) -> None:
        """
        Invalidate specific or all template cache entries.
        Called after admin updates a template via the API.
        """
        if notification_type is None:
            _TEMPLATE_CACHE.clear()
            return
        keys_to_remove = [
            k for k in _TEMPLATE_CACHE
            if k[0] == notification_type
            and (channel is None or k[1] == channel)
            and (language is None or k[2] == language)
        ]
        for k in keys_to_remove:
            _TEMPLATE_CACHE.pop(k, None)
