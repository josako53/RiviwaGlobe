"""
models/post.py — CMS content models.

Tables
──────
  org_posts                 Post / article / announcement content.
  org_post_categories       Category taxonomy per org (tree structure).
  org_post_category_links   M2M: posts ↔ categories.
  org_post_revisions        Full revision history for every content change.
  org_post_comments         Threaded comments with moderation workflow.

Design decisions
────────────────
  - org_id / author_id / user_id are plain UUID columns (no FK to external
    services) — cross-service referential integrity is enforced in the service
    layer, not at the DB level.
  - content is stored as HTML (rich text). The API accepts Markdown and the
    service layer converts it before storage if needed.
  - Scheduling: status=SCHEDULED + scheduled_at in the future → APScheduler
    flips status to PUBLISHED at scheduled_at time.
  - Soft-delete via deleted_at; all queries filter deleted_at IS NULL.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, DateTime, Field, SQLModel, text


# ── Enums ──────────────────────────────────────────────────────────────────────

class PostStatus(str, Enum):
    DRAFT      = "DRAFT"
    IN_REVIEW  = "IN_REVIEW"
    SCHEDULED  = "SCHEDULED"
    PUBLISHED  = "PUBLISHED"
    ARCHIVED   = "ARCHIVED"


class PostType(str, Enum):
    NEWS          = "NEWS"
    UPDATE        = "UPDATE"
    ANNOUNCEMENT  = "ANNOUNCEMENT"
    BLOG          = "BLOG"
    POLICY        = "POLICY"
    EVENT         = "EVENT"
    PRESS_RELEASE = "PRESS_RELEASE"


class CommentStatus(str, Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SPAM     = "SPAM"


# ── OrgPost ────────────────────────────────────────────────────────────────────

class OrgPost(SQLModel, table=True):
    """
    A piece of CMS content (news article, announcement, blog post, policy, etc.)
    published by an organisation.

    Workflow:
      DRAFT → IN_REVIEW → PUBLISHED | SCHEDULED | ARCHIVED
      SCHEDULED → PUBLISHED (automatic via scheduler when scheduled_at passes)
      PUBLISHED → ARCHIVED

    slug is unique per org (enforced by UNIQUE(org_id, slug)).
    """
    __tablename__ = "org_posts"
    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_org_post_slug"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # Ownership (plain UUIDs — no DB FK to external services)
    org_id:    uuid.UUID           = Field(nullable=False, index=True,
                                           description="Owning organisation")
    branch_id: Optional[uuid.UUID] = Field(default=None, nullable=True, index=True,
                                           description="Branch-specific post (NULL=org-wide)")

    # ── Content ───────────────────────────────────────────────────────────────
    title:   str           = Field(max_length=500, nullable=False)
    slug:    str           = Field(max_length=500, nullable=False,
                                   description="URL-friendly, unique per org")
    excerpt: Optional[str] = Field(default=None, max_length=1000, nullable=True,
                                   description="Short summary shown in listing views")
    content: str           = Field(sa_column=Column(Text, nullable=False),
                                   description="Full post body (HTML or Markdown)")

    # ── Classification ────────────────────────────────────────────────────────
    post_type: PostType = Field(
        default=PostType.NEWS,
        sa_column=Column(SAEnum(PostType, name="post_type"), nullable=False, index=True),
    )
    status: PostStatus = Field(
        default=PostStatus.DRAFT,
        sa_column=Column(SAEnum(PostStatus, name="post_status"), nullable=False, index=True),
    )
    tags: Optional[list] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description='Array of tag strings e.g. ["health","policy","2026"]',
    )

    # ── Media ─────────────────────────────────────────────────────────────────
    featured_image_url: Optional[str] = Field(default=None, max_length=1024, nullable=True)
    featured_image_alt: Optional[str] = Field(default=None, max_length=500,  nullable=True)

    # ── SEO ───────────────────────────────────────────────────────────────────
    seo_title:       Optional[str] = Field(default=None, max_length=200, nullable=True)
    seo_description: Optional[str] = Field(default=None, max_length=500, nullable=True)

    # ── Authoring ─────────────────────────────────────────────────────────────
    author_id:   Optional[uuid.UUID] = Field(default=None, nullable=True, index=True,
                                             description="User who authored")
    author_name: Optional[str]       = Field(default=None, max_length=200, nullable=True,
                                             description="Denormalized for display")
    editor_id:   Optional[uuid.UUID] = Field(default=None, nullable=True,
                                             description="User who published/approved")
    editor_name: Optional[str]       = Field(default=None, max_length=200, nullable=True)

    # ── Scheduling ────────────────────────────────────────────────────────────
    scheduled_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Auto-publish at this time when status=SCHEDULED",
    )
    published_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the post was actually published",
    )

    # ── Engagement ────────────────────────────────────────────────────────────
    view_count:      int  = Field(default=0,    sa_column=Column(Integer, nullable=False))
    is_pinned:       bool = Field(default=False, nullable=False,
                                  description="Pin to top of listing")
    is_featured:     bool = Field(default=False, nullable=False,
                                  description="Feature on org homepage / dashboard")
    allows_comments: bool = Field(default=True,  nullable=False)

    # ── Audience ──────────────────────────────────────────────────────────────
    is_public:       bool           = Field(default=True, nullable=False,
                                           description="Visible to public; False=staff only")
    target_audience: Optional[str]  = Field(default=None, max_length=50, nullable=True,
                                            description="'all'|'staff'|'customers'|'stakeholders'")

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Soft delete timestamp",
    )


# ── OrgPostCategory ────────────────────────────────────────────────────────────

class OrgPostCategory(SQLModel, table=True):
    """
    Category taxonomy for CMS posts. Supports unlimited depth via parent_id.
    Each org maintains its own category tree (slug unique per org).
    """
    __tablename__ = "org_post_categories"
    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_org_category_slug"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    org_id:      uuid.UUID           = Field(nullable=False, index=True)
    parent_id:   Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("org_post_categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        description="For nested categories (NULL = top-level)",
    )
    name:        str           = Field(max_length=200, nullable=False)
    slug:        str           = Field(max_length=200, nullable=False)
    description: Optional[str] = Field(default=None, max_length=500, nullable=True)
    sort_order:  int           = Field(default=0, sa_column=Column(Integer, nullable=False))
    is_active:   bool          = Field(default=True, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )


# ── OrgPostCategoryLink ────────────────────────────────────────────────────────

class OrgPostCategoryLink(SQLModel, table=True):
    """M2M junction: OrgPost ↔ OrgPostCategory."""
    __tablename__ = "org_post_category_links"
    __table_args__ = (
        UniqueConstraint("post_id", "category_id", name="uq_post_category"),
    )

    id:          uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    post_id:     uuid.UUID = Field(
        sa_column=Column(ForeignKey("org_posts.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    )
    category_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("org_post_categories.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    )


# ── OrgPostRevision ────────────────────────────────────────────────────────────

class OrgPostRevision(SQLModel, table=True):
    """
    Immutable revision history. Every content save creates a new row.
    Allows rolling back and auditing all changes to a post.
    """
    __tablename__ = "org_post_revisions"

    id:              uuid.UUID      = Field(default_factory=uuid.uuid4, primary_key=True)
    post_id:         uuid.UUID      = Field(
        sa_column=Column(ForeignKey("org_posts.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    )
    title:           str            = Field(max_length=500, nullable=False)
    content:         str            = Field(sa_column=Column(Text, nullable=False))
    excerpt:         Optional[str]  = Field(default=None, max_length=1000, nullable=True)
    revised_by_id:   uuid.UUID      = Field(nullable=False)
    revised_by_name: Optional[str]  = Field(default=None, max_length=200, nullable=True)
    revision_note:   Optional[str]  = Field(default=None, max_length=500, nullable=True,
                                            description="Summary of what changed")
    revision_number: int            = Field(default=1, sa_column=Column(Integer, nullable=False))

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )


# ── OrgPostComment ─────────────────────────────────────────────────────────────

class OrgPostComment(SQLModel, table=True):
    """
    Threaded comments on a post with moderation workflow.

    Workflow:
      PENDING → APPROVED | REJECTED | SPAM

    Threading via parent_id (NULL = top-level comment, non-NULL = reply).
    is_staff_reply flags official org responses to highlight in the UI.
    """
    __tablename__ = "org_post_comments"

    id:           uuid.UUID           = Field(default_factory=uuid.uuid4, primary_key=True)
    post_id:      uuid.UUID           = Field(
        sa_column=Column(ForeignKey("org_posts.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    )
    parent_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("org_post_comments.id", ondelete="CASCADE"),
            nullable=True,
        ),
        description="NULL = top-level; set = reply to another comment",
    )

    # Author — registered user OR anonymous
    user_id:      Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)
    author_name:  Optional[str]       = Field(default=None, max_length=200, nullable=True)
    author_email: Optional[str]       = Field(default=None, max_length=255, nullable=True)

    content: str = Field(sa_column=Column(Text, nullable=False))

    status: CommentStatus = Field(
        default=CommentStatus.PENDING,
        sa_column=Column(SAEnum(CommentStatus, name="comment_status"),
                         nullable=False, index=True),
    )
    is_staff_reply: bool = Field(default=False, nullable=False,
                                  description="Official org response (highlighted in UI)")

    moderated_by_id:   Optional[uuid.UUID] = Field(default=None, nullable=True)
    moderated_by_name: Optional[str]       = Field(default=None, max_length=200, nullable=True)
    moderation_note:   Optional[str]       = Field(default=None, max_length=500, nullable=True)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
