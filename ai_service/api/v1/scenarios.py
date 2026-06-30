"""
api/v1/scenarios.py — Platform super_admin CRUD for KB_88 industry scenarios.

Endpoints:
  GET    /ai/industry-scenarios                       List all KB_88 files + scenario counts
  GET    /ai/industry-scenarios/{filename}            Read all scenarios from one industry file
  POST   /ai/industry-scenarios/{filename}            Manually add a scenario to an industry file
  DELETE /ai/industry-scenarios/{filename}/{num}      Remove a scenario by its number (e.g. "01-11")
  POST   /ai/industry-scenarios/reindex               Re-index all KB_88 files into Qdrant

All endpoints require platform_role = super_admin.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.config import settings
from core.dependencies import get_current_token, TokenClaims
from services.rlhf_service import slug_to_kb88_filename

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/ai/industry-scenarios", tags=["AI — Industry Scenarios (Super Admin)"])

_VAULT = Path(settings.OBSIDIAN_VAULT_PATH)
_KB88_PATTERN = re.compile(r"KB_88_\d+_owner_scenarios_.+\.md")


# ── Auth dependency ────────────────────────────────────────────────────────────

async def _require_super_admin(
    token: Annotated[TokenClaims, Depends(get_current_token)],
) -> TokenClaims:
    if token.platform_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "SUPER_ADMIN_REQUIRED",
                    "message": "This endpoint is restricted to platform super admins."},
        )
    return token


SuperAdminDep = Annotated[TokenClaims, Depends(_require_super_admin)]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _scenario_count(content: str) -> int:
    return len(re.findall(r'^### Scenario \d+-\d+', content, re.MULTILINE))


def _parse_scenarios(content: str, filename: str) -> list[dict]:
    """Extract each scenario block from a KB_88 file."""
    blocks = re.split(r'\n---\n|\n(?=### Scenario )', content)
    scenarios = []
    for block in blocks:
        m = re.search(r'### Scenario (\d+-\d+): (.+?)(?:\s*\*.*?\*)?\s*\n', block)
        if not m:
            continue
        num   = m.group(1)
        title = m.group(2).strip()

        def _field(label: str) -> str:
            fm = re.search(rf'\*\*{label}:\*\*\s*(.+?)(?=\n\*\*|\n---|\Z)', block, re.DOTALL)
            return fm.group(1).strip() if fm else ""

        rlhf_match = re.search(r'\*(RLHF[^*]*)\*', block)
        scenarios.append({
            "num":            num,
            "title":          title,
            "problem":        _field("The Problem"),
            "staff_response": _field("What staff would do"),
            "owner_does":     _field("What the Owner does"),
            "is_rlhf":        bool(rlhf_match),
            "rlhf_tag":       rlhf_match.group(1) if rlhf_match else None,
            "source_file":    filename,
        })
    return scenarios


def _remove_scenario(content: str, num: str) -> Optional[str]:
    """
    Remove a scenario block identified by its num (e.g. '01-11').
    Returns updated content, or None if scenario not found.
    """
    pattern = re.compile(
        rf'(\n---\n\n)?### Scenario {re.escape(num)}:.*?(?=\n---\n|\n### Scenario |\Z)',
        re.DOTALL,
    )
    new_content, count = pattern.subn("", content)
    return new_content if count > 0 else None


# ── Request models ─────────────────────────────────────────────────────────────

class ManualScenarioIn(BaseModel):
    title: str
    problem: str
    staff_response: str
    owner_does: str
    ai_reply: str
    direct_to: str
    is_urgent: bool = False
    pattern: str = "A"
    category_tag: str = "other"


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("", summary="List all KB_88 industry files with scenario counts")
async def list_industry_files(_: SuperAdminDep) -> dict:
    if not _VAULT.exists():
        raise HTTPException(status_code=503, detail="Obsidian vault path not found.")

    files = sorted(f for f in _VAULT.iterdir() if _KB88_PATTERN.match(f.name))
    items = []
    for fp in files:
        content = fp.read_text(encoding="utf-8", errors="ignore")
        rlhf_count = len(re.findall(r'\(RLHF', content))
        items.append({
            "filename":       fp.name,
            "total_scenarios": _scenario_count(content),
            "rlhf_scenarios": rlhf_count,
            "curated_scenarios": _scenario_count(content) - rlhf_count,
            "size_bytes":     fp.stat().st_size,
        })

    return {"count": len(items), "files": items}


@router.get("/{filename}", summary="Read all scenarios from a specific KB_88 file")
async def get_industry_scenarios(filename: str, _: SuperAdminDep) -> dict:
    if not _KB88_PATTERN.match(filename):
        raise HTTPException(status_code=400, detail="Invalid KB_88 filename.")

    fp = _VAULT / filename
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    content   = fp.read_text(encoding="utf-8", errors="ignore")
    scenarios = _parse_scenarios(content, filename)
    return {
        "filename":  filename,
        "count":     len(scenarios),
        "scenarios": scenarios,
    }


@router.post("/{filename}", summary="Manually add a scenario to a KB_88 file", status_code=201)
async def add_manual_scenario(
    filename: str,
    body: ManualScenarioIn,
    _: SuperAdminDep,
) -> dict:
    if not _KB88_PATTERN.match(filename):
        raise HTTPException(status_code=400, detail="Invalid KB_88 filename.")

    fp = _VAULT / filename
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    content = fp.read_text(encoding="utf-8")

    matches    = re.findall(r'### Scenario \d+-(\d+)', content)
    next_num   = max(int(m) for m in matches) + 1 if matches else 11
    num_match  = re.match(r'KB_88_(\d+)_', filename)
    industry_n = num_match.group(1) if num_match else "XX"
    today      = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scenario_id = f"{industry_n}-{next_num}"

    new_block = (
        f"\n---\n\n"
        f"### Scenario {scenario_id}: {body.title} *(Manual — {today})*\n\n"
        f"**Real Basis:** Manually added by platform administrator.\n\n"
        f"**The Problem:** {body.problem}\n\n"
        f"**What staff would do:** {body.staff_response}\n\n"
        f"**What the Owner does:** {body.owner_does}\n\n"
        f"**Riviwa AI Instruction:**\n"
        f"- is_urgent: {str(body.is_urgent).lower()}\n"
        f"- reply: {body.ai_reply}\n"
        f"- direct_to: {body.direct_to}\n"
        f"- category_tag: {body.category_tag}\n"
        f"- pattern: {body.pattern}\n"
    )

    with open(fp, "a", encoding="utf-8") as fh:
        fh.write(new_block)

    # Re-index the updated file
    try:
        from services.rlhf_service import get_rlhf_service
        get_rlhf_service()._reindex_single_file(filename)
    except Exception as exc:
        log.warning("scenarios.reindex_failed", file=filename, error=str(exc))

    log.info("scenarios.manual_added", file=filename, scenario=scenario_id)
    return {"scenario_id": scenario_id, "file": filename, "title": body.title}


@router.delete(
    "/{filename}/scenario/{num}",
    summary="Remove a scenario from a KB_88 file by its number (e.g. 01-11)",
)
async def delete_scenario(filename: str, num: str, _: SuperAdminDep) -> dict:
    if not _KB88_PATTERN.match(filename):
        raise HTTPException(status_code=400, detail="Invalid KB_88 filename.")
    if not re.match(r'^\d+-\d+$', num):
        raise HTTPException(status_code=400, detail="num must be in format NN-MM, e.g. 01-11.")

    fp = _VAULT / filename
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    content     = fp.read_text(encoding="utf-8")
    new_content = _remove_scenario(content, num)
    if new_content is None:
        raise HTTPException(status_code=404, detail=f"Scenario {num} not found in {filename}.")

    fp.write_text(new_content, encoding="utf-8")

    try:
        from services.rlhf_service import get_rlhf_service
        get_rlhf_service()._reindex_single_file(filename)
    except Exception as exc:
        log.warning("scenarios.reindex_failed", file=filename, error=str(exc))

    log.info("scenarios.deleted", file=filename, num=num)
    return {"deleted": num, "file": filename}


@router.post("/reindex", summary="Re-index all KB_88 scenario files into Qdrant")
async def reindex_all_kb88(_: SuperAdminDep) -> dict:
    if not _VAULT.exists():
        raise HTTPException(status_code=503, detail="Obsidian vault path not found.")

    kb88_files = [f.name for f in _VAULT.iterdir() if _KB88_PATTERN.match(f.name)]

    try:
        from services.rlhf_service import get_rlhf_service
        svc     = get_rlhf_service()
        results = {}
        for fname in sorted(kb88_files):
            try:
                svc._reindex_single_file(fname)
                results[fname] = "ok"
            except Exception as exc:
                results[fname] = f"error: {exc}"
        return {"reindexed": len(kb88_files), "results": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
