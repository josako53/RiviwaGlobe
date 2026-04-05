# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  db/base.py
# ───────────────────────────────────────────────────────────────────────────
"""
db/base.py
════════════════════════════════════════════════════════════════════════════
Single import point for Alembic autogenerate.

Base = SQLModel → SQLModel.metadata is the shared MetaData registry that
Alembic reads to discover all tables. Every model class MUST be imported
here — if a model is not imported, Alembic will not know it exists and will
generate DROP TABLE in the next migration.

TABLE INVENTORY  (5 tables)
────────────────────────────────────────────────────────────────────────────
  notification_templates  — Jinja2 templates per (type × channel × language)
  notifications           — every dispatched or scheduled notification
  notification_deliveries — one row per channel attempt per notification
  notification_preferences— per-user opt-in/out per type × channel
  notification_devices    — FCM / APNs push token registry
════════════════════════════════════════════════════════════════════════════
"""
from sqlmodel import SQLModel

# Alembic target: target_metadata = Base.metadata
Base = SQLModel

# Import all five tables so SQLModel.metadata contains them all.
# Import order follows FK dependency chain:
#   NotificationTemplate  — no FKs
#   Notification          — no FKs (recipient_user_id is a plain UUID, not a DB FK)
#   NotificationDelivery  — FK → notifications.id
#   NotificationPreference— no FKs (user_id is a plain UUID)
#   NotificationDevice    — no FKs (user_id is a plain UUID)
from models.notification import (          # noqa: F401
    NotificationTemplate,
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationDevice,
)
