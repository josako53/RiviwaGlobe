"""
services/entity_resolution_service.py — Resolve entity mentions to UUIDs.

When the AI extracts a raw text mention (e.g. "Kariakoo Branch", "Dr. Amina",
"Mobile Banking service"), this service resolves it to the actual UUID in the
platform by doing a vector similarity search against the entity Qdrant collections.

Collections (all use all-MiniLM-L6-v2, 384-dim, cosine):
  riviwa_orgs         → Organisation
  riviwa_branches     → OrgBranch
  riviwa_departments  → OrgDepartment
  riviwa_services     → OrgService (service/product/program)
  riviwa_staff        → StaffProfile

Confidence thresholds (reject if below):
  Org:        0.70   — high bar; wrong org is a serious misrouting
  Branch:     0.65
  Department: 0.60
  Service:    0.65
  Staff:      0.70   — high bar; wrong staff name is a serious misattribution
"""
from __future__ import annotations

from typing import Optional, Tuple

import structlog

from core.config import settings
from services.rag_service import get_rag

log = structlog.get_logger(__name__)

# Confidence thresholds — resolve only when confident
_THRESHOLDS = {
    "org":        0.70,
    "branch":     0.65,
    "department": 0.60,
    "service":    0.65,
    "staff":      0.70,
}


def _resolve(
    entity_type: str,
    collection_setting: str,
    mention: str,
    org_id: Optional[str] = None,
) -> Tuple[Optional[str], float, dict]:
    """
    Search Qdrant for the best match to `mention` in the given collection.
    Optionally filters by org_id in the payload.

    Returns: (entity_id, score, payload) or (None, 0.0, {})
    """
    rag      = get_rag()
    coll     = collection_setting
    thresh   = _THRESHOLDS[entity_type]

    results = rag.search_entity(mention, collection=coll, top_k=3, score_threshold=thresh)
    if not results:
        return None, 0.0, {}

    # If org_id supplied, prefer results scoped to that org
    if org_id:
        org_matches = [(eid, sc, pl) for eid, sc, pl in results
                       if pl.get("org_id") == org_id]
        if org_matches:
            results = org_matches

    entity_id, score, payload = results[0]
    log.debug(
        "entity_resolution.resolved",
        entity_type=entity_type,
        mention=mention,
        entity_id=entity_id,
        score=round(score, 3),
    )
    return entity_id, score, payload


# ── Public resolve functions ──────────────────────────────────────────────────

def resolve_org(mention: str) -> Tuple[Optional[str], float, dict]:
    """
    Resolve an org name mention to org_id.
    E.g. "CRDB Bank" → (org_id_uuid, 0.88, {"display_name": "CRDB Bank Tanzania", ...})
    """
    return _resolve("org", settings.QDRANT_COLLECTION_ORGS, mention)


def resolve_branch(mention: str, org_id: Optional[str] = None) -> Tuple[Optional[str], float, dict]:
    """
    Resolve a branch name mention to branch_id.
    E.g. "Kariakoo Branch" → (branch_id_uuid, 0.82, {...})
    """
    return _resolve("branch", settings.QDRANT_COLLECTION_BRANCHES, mention, org_id=org_id)


def resolve_department(mention: str, org_id: Optional[str] = None) -> Tuple[Optional[str], float, dict]:
    """
    Resolve a department name mention to department_id.
    E.g. "Loans Department" → (dept_id_uuid, 0.75, {...})
    """
    return _resolve("department", settings.QDRANT_COLLECTION_DEPARTMENTS, mention, org_id=org_id)


def resolve_service(mention: str, org_id: Optional[str] = None) -> Tuple[Optional[str], float, dict]:
    """
    Resolve a service/product/program name mention to service_id.
    E.g. "Safari Loan" → (service_id_uuid, 0.79, {"service_type": "product", ...})
    """
    return _resolve("service", settings.QDRANT_COLLECTION_SERVICES, mention, org_id=org_id)


def resolve_staff(mention: str, org_id: Optional[str] = None) -> Tuple[Optional[str], float, dict]:
    """
    Resolve a staff name mention to staff_id.
    E.g. "Dr. Amina Juma" → (staff_id_uuid, 0.83, {"position": "Doctor", ...})
    """
    return _resolve("staff", settings.QDRANT_COLLECTION_STAFF, mention, org_id=org_id)


def resolve_all(
    mentions: dict,
    org_id: Optional[str] = None,
) -> dict:
    """
    Resolve all entity mentions extracted by the LLM in a single pass.

    Args:
        mentions: {
            "org_mentioned":        str|None,
            "branch_mentioned":     str|None,
            "department_mentioned": str|None,
            "service_mentioned":    str|None,
            "staff_mentioned":      str|None,
        }
        org_id: Already-resolved org_id (used to scope branch/dept/service/staff)

    Returns:
        {
            "org_id":        str|None,
            "branch_id":     str|None,
            "department_id": str|None,
            "service_id":    str|None,
            "staff_id":      str|None,
            "org_name":      str|None,   # payload display name for confirmation
            "branch_name":   str|None,
            "confidence":    dict,        # per-entity confidence scores
        }
    """
    resolved: dict = {
        "org_id":        None,
        "branch_id":     None,
        "department_id": None,
        "service_id":    None,
        "staff_id":      None,
        "org_name":      None,
        "branch_name":   None,
        "confidence":    {},
    }

    # Resolve org first (needed to scope everything else)
    if mentions.get("org_mentioned") and not org_id:
        eid, score, payload = resolve_org(mentions["org_mentioned"])
        if eid:
            resolved["org_id"]    = eid
            resolved["org_name"]  = payload.get("display_name") or payload.get("legal_name")
            resolved["confidence"]["org"] = round(score, 3)
            org_id = eid

    # Use already-known org_id if passed in
    if org_id and not resolved["org_id"]:
        resolved["org_id"] = org_id

    if mentions.get("branch_mentioned"):
        eid, score, payload = resolve_branch(mentions["branch_mentioned"], org_id=org_id)
        if eid:
            resolved["branch_id"]   = eid
            resolved["branch_name"] = payload.get("name")
            resolved["confidence"]["branch"] = round(score, 3)

    if mentions.get("department_mentioned"):
        eid, score, _ = resolve_department(mentions["department_mentioned"], org_id=org_id)
        if eid:
            resolved["department_id"] = eid
            resolved["confidence"]["department"] = round(score, 3)

    if mentions.get("service_mentioned"):
        eid, score, _ = resolve_service(mentions["service_mentioned"], org_id=org_id)
        if eid:
            resolved["service_id"] = eid
            resolved["confidence"]["service"] = round(score, 3)

    if mentions.get("staff_mentioned"):
        eid, score, _ = resolve_staff(mentions["staff_mentioned"], org_id=org_id)
        if eid:
            resolved["staff_id"] = eid
            resolved["confidence"]["staff"] = round(score, 3)

    return resolved
