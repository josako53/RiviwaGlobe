"""
services/image_intelligence.py — AI-powered product image authenticity analysis.

Pipeline:
  1. CLIP ViT-B/32   → 512-dim image embedding (industry-standard for image similarity)
  2. Qdrant           → cosine similarity search against indexed product images
                        (org-scoped first, then platform-wide fallback)
  3. Llama 4 Scout   → multimodal visual reasoning about counterfeit indicators
                        (Groq meta-llama/llama-4-scout-17b-16e-instruct)

Design decisions:
  - CLIP ViT-B/32 chosen over ResNet/EfficientNet because it provides
    zero-shot image-image and image-text similarity without fine-tuning.
    It's the industry standard for product image similarity at scale.
  - Llama 4 Scout (Groq) chosen because it's a full multimodal model
    available through the existing Groq API key — no extra infrastructure.
  - Two-stage search: org-scope first (fast, relevant), then platform-wide
    (catch cross-brand counterfeits that impersonate a different org's products).
  - Similarity thresholds calibrated for consumer products:
      >= 0.82  VERY_SIMILAR   (almost certainly same product family)
      >= 0.70  SIMILAR        (likely related product / same brand)
      >= 0.55  POSSIBLY_RELATED
      <  0.55  DIFFERENT
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import uuid
from typing import Optional

import httpx
import numpy as np
import structlog

from core.config import settings

log = structlog.get_logger(__name__)

COLLECTION = "product_images"
CLIP_DIM   = 512

# Similarity thresholds
THRESH_VERY_SIMILAR = 0.82
THRESH_SIMILAR      = 0.70
THRESH_POSSIBLE     = 0.55

_clip_model = None


def _get_clip():
    """Lazy-load CLIP ViT-B/32. Cached globally — model stays in memory."""
    global _clip_model
    if _clip_model is None:
        from sentence_transformers import SentenceTransformer
        log.info("image_intelligence.loading_clip")
        _clip_model = SentenceTransformer("clip-ViT-B-32")
        log.info("image_intelligence.clip_ready", dim=CLIP_DIM)
    return _clip_model


def _get_qdrant():
    from qdrant_client import QdrantClient
    return QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


def _ensure_collection():
    """Create the product_images collection in Qdrant if it doesn't exist."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import VectorParams, Distance
    client = _get_qdrant()
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION not in existing:
        client.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=CLIP_DIM, distance=Distance.COSINE),
        )
        log.info("image_intelligence.collection_created", collection=COLLECTION)
    return client


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed_image_bytes(image_bytes: bytes) -> list[float]:
    """
    Generate a 512-dimensional CLIP ViT-B/32 embedding for an image.
    Normalised to unit length (Qdrant cosine distance handles this, but explicit
    normalisation ensures consistent behaviour with raw dot-product comparisons).
    """
    from PIL import Image
    model = _get_clip()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    emb = model.encode(img, convert_to_numpy=True, normalize_embeddings=True)
    return emb.tolist()


def embed_image_url_sync(url: str) -> Optional[list[float]]:
    """Download image from URL and embed. Returns None on any error."""
    try:
        import httpx as _httpx
        resp = _httpx.get(url, timeout=8.0, follow_redirects=True)
        if resp.status_code == 200:
            return embed_image_bytes(resp.content)
    except Exception as exc:
        log.warning("image_intelligence.embed_url_failed", url=url[:80], error=str(exc))
    return None


# ── Indexing ──────────────────────────────────────────────────────────────────

def index_product_images(
    product_id: str,
    org_id: str,
    image_urls: list[str],
    title: str = "",
    brand: str = "",
    rsin: str = "",
    image_roles: Optional[list[str]] = None,
) -> int:
    """
    Download and index all images for a product into Qdrant.
    Returns count of successfully indexed images.
    Called when a product QR is generated or a product is published.
    """
    from qdrant_client.models import PointStruct
    client = _ensure_collection()
    indexed = 0

    for i, url in enumerate(image_urls):
        embedding = embed_image_url_sync(url)
        if embedding is None:
            continue
        role = (image_roles or [])[i] if image_roles and i < len(image_roles) else "main"
        # Deterministic point ID from product_id + image index
        point_id = int(hashlib.sha256(f"{product_id}_{i}".encode()).hexdigest()[:15], 16)
        client.upsert(
            COLLECTION,
            points=[PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "product_id":   product_id,
                    "org_id":       org_id,
                    "image_url":    url,
                    "image_role":   role,
                    "title":        title,
                    "brand":        brand,
                    "rsin":         rsin,
                },
            )],
        )
        indexed += 1
        log.info("image_intelligence.indexed", product_id=product_id, image_index=i, role=role)

    return indexed


# ── Search ────────────────────────────────────────────────────────────────────

def search_similar_products(
    embedding: list[float],
    org_id: Optional[str] = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Search Qdrant for products with similar images.
    If org_id given: scope to that org first, then fall back to platform-wide.
    Returns list of matches sorted by similarity score (descending).
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    client = _ensure_collection()

    results = []

    if org_id:
        # 1. Org-scoped search — most relevant (same org's genuine products)
        hits = client.search(
            COLLECTION,
            query_vector=embedding,
            limit=top_k,
            query_filter=Filter(must=[
                FieldCondition(key="org_id", match=MatchValue(value=org_id))
            ]),
        )
        results.extend(hits)

    # 2. Platform-wide search (catches cross-org counterfeits)
    platform_hits = client.search(
        COLLECTION,
        query_vector=embedding,
        limit=top_k,
    )
    # Merge, deduplicate by product_id, keep highest score
    seen_products = {r.payload["product_id"]: r.score for r in results}
    for hit in platform_hits:
        pid = hit.payload["product_id"]
        if pid not in seen_products or hit.score > seen_products[pid]:
            seen_products[pid] = hit.score
            results.append(hit)

    # Sort by score descending, return top_k
    results.sort(key=lambda x: x.score, reverse=True)
    return [
        {
            "product_id":     r.payload["product_id"],
            "org_id":         r.payload["org_id"],
            "title":          r.payload.get("title", ""),
            "brand":          r.payload.get("brand", ""),
            "rsin":           r.payload.get("rsin", ""),
            "image_url":      r.payload.get("image_url", ""),
            "similarity":     round(r.score, 4),
            "similarity_pct": round(r.score * 100, 1),
        }
        for r in results[:top_k]
    ]


# ── Vision Analysis ───────────────────────────────────────────────────────────

async def analyze_authenticity(
    fake_image_bytes: bytes,
    matched_products: list[dict],
    report_context: Optional[dict] = None,
) -> dict:
    """
    Use Llama 4 Scout (Groq multimodal) to reason about a suspected counterfeit image.

    Sends the fake image alongside top-N genuine product images from Qdrant matches.
    Returns a structured verdict with confidence and reasoning.
    """
    if not matched_products:
        return _no_match_verdict()

    top_match = matched_products[0]
    similarity = top_match["similarity"]

    # Build visual comparison message
    content = []

    # The suspected fake image
    fake_b64 = base64.b64encode(fake_image_bytes).decode()
    content.append({
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{fake_b64}"},
    })

    # Include genuine product image (first match) for side-by-side comparison
    if top_match.get("image_url"):
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(top_match["image_url"], follow_redirects=True)
                if resp.status_code == 200:
                    genuine_b64 = base64.b64encode(resp.content).decode()
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{genuine_b64}"},
                    })
        except Exception:
            pass  # Continue without genuine image

    # Build structured analysis prompt
    matched_summary = "\n".join(
        f"  - {m['title']} (brand: {m['brand']}, RSIN: {m['rsin']}) — visual similarity: {m['similarity_pct']}%"
        for m in matched_products[:3]
    )
    context_str = ""
    if report_context:
        context_str = f"\nContext: QR code was unrecognized (code: {report_context.get('short_code', 'N/A')}), reported at {report_context.get('location', 'unknown location')}."

    content.append({
        "type": "text",
        "text": f"""You are an expert product authenticity analyst for Riviwa, a consumer protection platform.

Image 1 (first image) is a SUSPECTED COUNTERFEIT product submitted by a consumer.
{f'Image 2 (second image) is the GENUINE product from our database for comparison.' if len(content) > 2 else 'No genuine product image available for comparison.'}
{context_str}

Our CLIP visual similarity search found these genuine products in our database:
{matched_summary}

Top match similarity: {top_match['similarity_pct']}% with "{top_match['title']}" by {top_match['brand']}.

Analyze the suspected counterfeit image and provide your verdict in valid JSON:
{{
  "verdict": "CONFIRMED_COUNTERFEIT" | "LIKELY_COUNTERFEIT" | "POSSIBLY_COUNTERFEIT" | "AUTHENTIC" | "DIFFERENT_PRODUCT" | "INCONCLUSIVE",
  "confidence": 0.0-1.0,
  "suspected_brand": "brand name if identifiable",
  "suspected_product": "product name if identifiable",
  "counterfeit_indicators": ["list", "of", "visual", "red flags"],
  "genuine_indicators": ["list", "of", "features", "matching", "genuine"],
  "reasoning": "brief explanation",
  "recommended_action": "what Riviwa agents should do"
}}

Base your verdict primarily on:
1. Visual differences from the genuine product
2. Quality indicators (print quality, colors, materials, logos)
3. The {top_match['similarity_pct']}% visual similarity score
4. Whether the product matches the claimed brand/model

Return ONLY the JSON object, no other text.""",
    })

    # Call Llama 4 Scout via Groq
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.GROQ_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                json={
                    "model":       "meta-llama/llama-4-scout-17b-16e-instruct",
                    "messages":    [{"role": "user", "content": content}],
                    "max_tokens":  600,
                    "temperature": 0.1,
                },
            )

        if resp.status_code == 200:
            raw_text = resp.json()["choices"][0]["message"]["content"].strip()
            # Extract JSON from response
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
            ai_result = json.loads(raw_text)
            log.info("image_intelligence.vision_analysis_done",
                     verdict=ai_result.get("verdict"),
                     confidence=ai_result.get("confidence"))
            return {
                "analysis_method":  "clip_similarity + llama4_scout_vision",
                "clip_similarity":  top_match["similarity"],
                "top_matches":      matched_products[:3],
                "ai_verdict":       ai_result,
            }
        else:
            log.warning("image_intelligence.vision_api_failed",
                        status=resp.status_code, body=resp.text[:200])

    except Exception as exc:
        log.error("image_intelligence.vision_error", error=str(exc))

    # Fallback: CLIP-only verdict (no LLM reasoning)
    return _clip_only_verdict(top_match, matched_products)


def _clip_only_verdict(top_match: dict, matches: list[dict]) -> dict:
    """Fallback verdict based solely on CLIP similarity when vision LLM fails."""
    sim = top_match["similarity"]
    if sim >= THRESH_VERY_SIMILAR:
        verdict = "LIKELY_COUNTERFEIT"
        confidence = 0.75
        reasoning = f"Image is {sim*100:.0f}% visually similar to '{top_match['title']}' — strongly suggests counterfeit."
    elif sim >= THRESH_SIMILAR:
        verdict = "POSSIBLY_COUNTERFEIT"
        confidence = 0.55
        reasoning = f"Image shows {sim*100:.0f}% similarity to '{top_match['title']}' — possible counterfeit."
    elif sim >= THRESH_POSSIBLE:
        verdict = "INCONCLUSIVE"
        confidence = 0.30
        reasoning = f"Low similarity ({sim*100:.0f}%) to known products — cannot determine authenticity from image alone."
    else:
        verdict = "DIFFERENT_PRODUCT"
        confidence = 0.60
        reasoning = f"Image ({sim*100:.0f}% similarity) does not closely match any known products in our database."

    return {
        "analysis_method":  "clip_similarity_only",
        "clip_similarity":  top_match["similarity"],
        "top_matches":      matches[:3],
        "ai_verdict": {
            "verdict":               verdict,
            "confidence":            confidence,
            "suspected_brand":       top_match.get("brand", "Unknown"),
            "suspected_product":     top_match.get("title", "Unknown"),
            "counterfeit_indicators": [],
            "genuine_indicators":    [],
            "reasoning":             reasoning,
            "recommended_action":    "Dispatch field agent to investigate.",
        },
    }


def _no_match_verdict() -> dict:
    return {
        "analysis_method":  "clip_similarity",
        "clip_similarity":  0.0,
        "top_matches":      [],
        "ai_verdict": {
            "verdict":               "UNKNOWN_PRODUCT",
            "confidence":            0.0,
            "suspected_brand":       None,
            "suspected_product":     None,
            "counterfeit_indicators": [],
            "genuine_indicators":    [],
            "reasoning":             "No product images indexed in the database yet. Cannot perform similarity analysis.",
            "recommended_action":    "Ensure product images are indexed before analysis.",
        },
    }


def collection_stats() -> dict:
    """Return stats about the product_images Qdrant collection."""
    try:
        client = _get_qdrant()
        info = client.get_collection(COLLECTION)
        return {
            "collection":   COLLECTION,
            "total_images": info.points_count,
            "vector_dim":   CLIP_DIM,
            "model":        "clip-ViT-B-32",
        }
    except Exception:
        return {"collection": COLLECTION, "total_images": 0, "vector_dim": CLIP_DIM}
