"""
api/v1/image_intelligence.py — Internal endpoints for image-based product authentication.

Called by:
  - verification_service  → POST /analyze  (when fake report has a photo)
  - qr_service            → POST /index    (when a product QR is generated)
  - product_service       → POST /index    (when a product is published)
  - Admin                 → GET  /stats    (collection health check)
"""
from __future__ import annotations

import base64
import io
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from core.dependencies import InternalKeyDep
from services.image_intelligence import (
    analyze_authenticity,
    collection_stats,
    embed_image_bytes,
    index_product_images,
    search_similar_products,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/ai/internal/image", tags=["AI — Image Intelligence"])


@router.post("/analyze", status_code=200)
async def analyze_image(
    body: dict,
    _=InternalKeyDep,
) -> dict:
    """
    Analyze a submitted image for product authenticity.

    Performs:
      1. CLIP ViT-B/32 embedding of the submitted image
      2. Qdrant similarity search (org-scoped → platform-wide)
      3. Llama 4 Scout (Groq vision) comparison with matched genuine products

    Body:
      image_base64   — Base64-encoded JPEG/PNG image (required)
      org_id         — Organisation UUID (optional — scopes initial search to org)
      product_id     — Known product UUID (optional — narrows search)
      short_code     — QR/SMS code that triggered this report (for context)
      location       — Where the suspected fake was found (for context)

    Returns structured authenticity verdict with confidence score.
    """
    image_b64 = body.get("image_base64", "")
    if not image_b64:
        raise HTTPException(status_code=422, detail={"error": "image_base64 required"})

    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception:
        raise HTTPException(status_code=422, detail={"error": "invalid base64 image"})

    org_id     = body.get("org_id")
    short_code = body.get("short_code")
    location   = body.get("location")

    log.info("image_intelligence.analyze_request",
             org_id=org_id, has_location=bool(location), bytes=len(image_bytes))

    # 1. Generate CLIP embedding
    try:
        embedding = await _run_sync(embed_image_bytes, image_bytes)
    except Exception as exc:
        log.error("image_intelligence.embed_failed", error=str(exc))
        raise HTTPException(status_code=500, detail={"error": "embedding_failed", "detail": str(exc)})

    # 2. Search Qdrant for similar genuine products
    try:
        matches = await _run_sync(search_similar_products, embedding, org_id, 5)
    except Exception as exc:
        log.warning("image_intelligence.search_failed", error=str(exc))
        matches = []

    # 3. Llama 4 Scout visual reasoning
    context = {"short_code": short_code, "location": location} if (short_code or location) else None
    result = await analyze_authenticity(image_bytes, matches, report_context=context)

    log.info("image_intelligence.analyze_done",
             verdict=result.get("ai_verdict", {}).get("verdict"),
             top_similarity=matches[0]["similarity"] if matches else 0)

    return result


@router.post("/index", status_code=status.HTTP_201_CREATED)
async def index_product(
    body: dict,
    _=InternalKeyDep,
) -> dict:
    """
    Index a product's images into the Qdrant product_images collection.
    Call this when a product is published or its images are updated.

    Body:
      product_id   — Product UUID
      org_id       — Organisation UUID
      image_urls   — List of image URLs (presigned MinIO or CDN)
      title        — Product title
      brand        — Brand name
      rsin         — Riviwa Standard Identification Number
      image_roles  — Optional list of roles (e.g. ["main","side","detail"])
    """
    product_id  = body.get("product_id", "")
    org_id      = body.get("org_id", "")
    image_urls  = body.get("image_urls", [])

    if not product_id or not org_id or not image_urls:
        raise HTTPException(status_code=422, detail={
            "error": "product_id, org_id, and image_urls are required"
        })

    log.info("image_intelligence.index_request",
             product_id=product_id, image_count=len(image_urls))

    indexed = await _run_sync(
        index_product_images,
        product_id,
        org_id,
        image_urls,
        body.get("title", ""),
        body.get("brand", ""),
        body.get("rsin", ""),
        body.get("image_roles"),
    )

    return {
        "product_id":    product_id,
        "org_id":        org_id,
        "indexed_count": indexed,
        "total_urls":    len(image_urls),
        "message":       f"{indexed}/{len(image_urls)} images indexed successfully.",
    }


@router.post("/index-url", status_code=status.HTTP_201_CREATED)
async def index_single_image_url(
    body: dict,
    _=InternalKeyDep,
) -> dict:
    """Index a single product image by URL. Lightweight version of /index."""
    indexed = await _run_sync(
        index_product_images,
        body["product_id"],
        body["org_id"],
        [body["image_url"]],
        body.get("title", ""),
        body.get("brand", ""),
        body.get("rsin", ""),
        [body.get("image_role", "main")],
    )
    return {"indexed": indexed == 1, "product_id": body["product_id"]}


@router.get("/stats", status_code=200)
async def get_collection_stats(_=InternalKeyDep) -> dict:
    """Return Qdrant product_images collection statistics."""
    return await _run_sync(collection_stats)


@router.post("/search", status_code=200)
async def search_by_image(
    body: dict,
    _=InternalKeyDep,
) -> dict:
    """
    Search for similar products by image (without full analysis).
    Returns ranked list of matching products.
    """
    image_b64 = body.get("image_base64", "")
    if not image_b64:
        raise HTTPException(status_code=422, detail={"error": "image_base64 required"})

    image_bytes = base64.b64decode(image_b64)
    embedding   = await _run_sync(embed_image_bytes, image_bytes)
    matches     = await _run_sync(search_similar_products, embedding, body.get("org_id"), body.get("top_k", 5))
    return {"matches": matches, "total": len(matches)}


async def _run_sync(fn, *args):
    """Run a CPU-bound sync function in the default executor (avoids blocking event loop)."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn, *args)
