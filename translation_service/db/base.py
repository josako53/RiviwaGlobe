# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  db/base.py
# ───────────────────────────────────────────────────────────────────────────
"""
db/base.py — Import all models so SQLModel.metadata knows every table.

Used by entrypoint.sh to create tables via metadata.create_all when no
Alembic migration files exist.
"""
from sqlmodel import SQLModel

# Import all table models so they register with SQLModel.metadata
from models.language import (  # noqa: F401
    SupportedLanguage,
    UserLanguagePreference,
    LanguageDetectionLog,
)

# Alias for entrypoint.sh: `from db.base import Base`
Base = SQLModel
