"""api/v1/router.py"""
from __future__ import annotations

from fastapi import APIRouter

from api.v1 import projects, stakeholders, contacts, activities, communications, focal_persons, reports

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(projects.router)
api_v1_router.include_router(stakeholders.router)
api_v1_router.include_router(contacts.router)
api_v1_router.include_router(activities.router)
api_v1_router.include_router(communications.router)
api_v1_router.include_router(focal_persons.router)
api_v1_router.include_router(reports.router)
