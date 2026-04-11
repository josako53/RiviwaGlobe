"""repositories/conversation_repo.py — DB queries for ai_service."""
from __future__ import annotations
import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from models.conversation import (
    AIConversation, ConversationStatus,
    ProjectKnowledgeBase, StakeholderCache,
)
from core.exceptions import ConversationNotFoundError


class ConversationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict) -> AIConversation:
        conv = AIConversation(**data)
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def get(self, conv_id: uuid.UUID) -> Optional[AIConversation]:
        result = await self.db.execute(select(AIConversation).where(AIConversation.id == conv_id))
        return result.scalar_one_or_none()

    async def get_or_404(self, conv_id: uuid.UUID) -> AIConversation:
        conv = await self.get(conv_id)
        if not conv:
            raise ConversationNotFoundError()
        return conv

    async def find_active_by_phone(self, phone: str) -> Optional[AIConversation]:
        """Find the most recent active session for a phone number."""
        result = await self.db.execute(
            select(AIConversation)
            .where(
                AIConversation.phone_number == phone,
                AIConversation.status == ConversationStatus.ACTIVE,
            )
            .order_by(AIConversation.last_active_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def find_active_by_whatsapp(self, whatsapp_id: str) -> Optional[AIConversation]:
        result = await self.db.execute(
            select(AIConversation)
            .where(
                AIConversation.whatsapp_id == whatsapp_id,
                AIConversation.status == ConversationStatus.ACTIVE,
            )
            .order_by(AIConversation.last_active_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def find_active_by_web_token(self, token: str) -> Optional[AIConversation]:
        result = await self.db.execute(
            select(AIConversation)
            .where(
                AIConversation.web_token == token,
                AIConversation.status == ConversationStatus.ACTIVE,
            )
            .order_by(AIConversation.last_active_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save(self, conv: AIConversation) -> AIConversation:
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def list(
        self,
        status: Optional[str] = None,
        channel: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[AIConversation]:
        q = select(AIConversation)
        if status:
            q = q.where(AIConversation.status == status)
        if channel:
            q = q.where(AIConversation.channel == channel)
        q = q.order_by(AIConversation.last_active_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())


class ProjectKBRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(self, project_id: uuid.UUID, data: dict) -> ProjectKnowledgeBase:
        result = await self.db.execute(
            select(ProjectKnowledgeBase).where(ProjectKnowledgeBase.project_id == project_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            self.db.add(existing)
            return existing
        kb = ProjectKnowledgeBase(project_id=project_id, **data)
        self.db.add(kb)
        await self.db.flush()
        await self.db.refresh(kb)
        return kb

    async def get_by_project_id(self, project_id: uuid.UUID) -> Optional[ProjectKnowledgeBase]:
        result = await self.db.execute(
            select(ProjectKnowledgeBase).where(ProjectKnowledgeBase.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> List[ProjectKnowledgeBase]:
        result = await self.db.execute(
            select(ProjectKnowledgeBase).where(ProjectKnowledgeBase.status == "active")
        )
        return list(result.scalars().all())

    async def mark_vector_indexed(self, project_id: uuid.UUID) -> None:
        kb = await self.get_by_project_id(project_id)
        if kb:
            kb.vector_indexed = True
            self.db.add(kb)

    async def keyword_search(self, query: str, limit: int = 5) -> List[ProjectKnowledgeBase]:
        """Simple ILIKE keyword search as fallback when Qdrant is unavailable."""
        terms = query.lower().split()
        q = select(ProjectKnowledgeBase).where(ProjectKnowledgeBase.status == "active")
        results = await self.db.execute(q)
        projects = list(results.scalars().all())
        # Score projects by how many query terms match their searchable text
        scored = []
        for p in projects:
            text = p.get_searchable_text().lower()
            score = sum(1 for t in terms if t in text)
            if score > 0:
                scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]


class StakeholderCacheRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(self, stakeholder_id: uuid.UUID, data: dict) -> StakeholderCache:
        result = await self.db.execute(
            select(StakeholderCache).where(StakeholderCache.stakeholder_id == stakeholder_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            self.db.add(existing)
            return existing
        sc = StakeholderCache(stakeholder_id=stakeholder_id, **data)
        self.db.add(sc)
        await self.db.flush()
        return sc

    async def get_incharge_for_project(self, project_id: uuid.UUID) -> Optional[StakeholderCache]:
        result = await self.db.execute(
            select(StakeholderCache).where(
                StakeholderCache.project_id == project_id,
                StakeholderCache.is_incharge == True,
            ).limit(1)
        )
        return result.scalar_one_or_none()
