from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from models.post import CommentStatus, PostStatus, PostType


# ── Post schemas ───────────────────────────────────────────────────────────────

class PostCreate(BaseModel):
    title:              str
    slug:               Optional[str]       = None
    excerpt:            Optional[str]       = None
    content:            str
    post_type:          PostType            = PostType.NEWS
    tags:               Optional[List[str]] = None
    featured_image_url: Optional[str]       = None
    featured_image_alt: Optional[str]       = None
    seo_title:          Optional[str]       = None
    seo_description:    Optional[str]       = None
    branch_id:          Optional[uuid.UUID] = None
    is_public:          bool                = True
    target_audience:    Optional[str]       = None
    allows_comments:    bool                = True
    is_pinned:          bool                = False
    is_featured:        bool                = False
    category_ids:       Optional[List[uuid.UUID]] = None


class PostUpdate(BaseModel):
    title:              Optional[str]             = None
    slug:               Optional[str]             = None
    excerpt:            Optional[str]             = None
    content:            Optional[str]             = None
    post_type:          Optional[PostType]        = None
    tags:               Optional[List[str]]       = None
    featured_image_url: Optional[str]             = None
    featured_image_alt: Optional[str]             = None
    seo_title:          Optional[str]             = None
    seo_description:    Optional[str]             = None
    is_public:          Optional[bool]            = None
    target_audience:    Optional[str]             = None
    allows_comments:    Optional[bool]            = None
    is_pinned:          Optional[bool]            = None
    is_featured:        Optional[bool]            = None
    category_ids:       Optional[List[uuid.UUID]] = None
    revision_note:      Optional[str]             = None


class PostSchedule(BaseModel):
    scheduled_at: datetime


class PostOut(BaseModel):
    id:                 uuid.UUID
    org_id:             uuid.UUID
    branch_id:          Optional[uuid.UUID]
    title:              str
    slug:               str
    excerpt:            Optional[str]
    content:            str
    post_type:          str
    status:             str
    tags:               Optional[List[str]]
    featured_image_url: Optional[str]
    featured_image_alt: Optional[str]
    seo_title:          Optional[str]
    seo_description:    Optional[str]
    author_id:          Optional[uuid.UUID]
    author_name:        Optional[str]
    editor_id:          Optional[uuid.UUID]
    editor_name:        Optional[str]
    scheduled_at:       Optional[datetime]
    published_at:       Optional[datetime]
    view_count:         int
    is_pinned:          bool
    is_featured:        bool
    allows_comments:    bool
    is_public:          bool
    target_audience:    Optional[str]
    created_at:         datetime
    updated_at:         datetime
    categories:         List[dict] = []

    model_config = {"from_attributes": True}


class PostListOut(BaseModel):
    items: List[PostOut]
    count: int
    total: int
    skip:  int
    limit: int


# ── Category schemas ───────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name:        str
    slug:        Optional[str]       = None
    description: Optional[str]       = None
    parent_id:   Optional[uuid.UUID] = None
    sort_order:  int                 = 0


class CategoryUpdate(BaseModel):
    name:        Optional[str]       = None
    slug:        Optional[str]       = None
    description: Optional[str]       = None
    parent_id:   Optional[uuid.UUID] = None
    sort_order:  Optional[int]       = None
    is_active:   Optional[bool]      = None


class CategoryOut(BaseModel):
    id:          uuid.UUID
    org_id:      uuid.UUID
    parent_id:   Optional[uuid.UUID]
    name:        str
    slug:        str
    description: Optional[str]
    sort_order:  int
    is_active:   bool
    created_at:  datetime
    updated_at:  datetime

    model_config = {"from_attributes": True}


# ── Comment schemas ────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    content:      str
    author_name:  Optional[str]       = None
    author_email: Optional[str]       = None
    parent_id:    Optional[uuid.UUID] = None


class CommentModerate(BaseModel):
    status:          CommentStatus
    moderation_note: Optional[str] = None


class CommentOut(BaseModel):
    id:                uuid.UUID
    post_id:           uuid.UUID
    parent_id:         Optional[uuid.UUID]
    user_id:           Optional[uuid.UUID]
    author_name:       Optional[str]
    content:           str
    status:            str
    is_staff_reply:    bool
    created_at:        datetime
    updated_at:        datetime
    replies:           List["CommentOut"] = []

    model_config = {"from_attributes": True}


CommentOut.model_rebuild()


# ── Revision schema ────────────────────────────────────────────────────────────

class RevisionOut(BaseModel):
    id:              uuid.UUID
    post_id:         uuid.UUID
    title:           str
    excerpt:         Optional[str]
    revised_by_id:   uuid.UUID
    revised_by_name: Optional[str]
    revision_note:   Optional[str]
    revision_number: int
    created_at:      datetime

    model_config = {"from_attributes": True}
