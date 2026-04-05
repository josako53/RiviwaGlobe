"""services/tag_service.py — Tag overlap and IDF-weighted similarity."""
from __future__ import annotations

import math
from collections import Counter
from typing import Dict, Set


def jaccard_similarity(tags_a: Set[str], tags_b: Set[str]) -> float:
    """Standard Jaccard: |A ∩ B| / |A ∪ B|."""
    if not tags_a or not tags_b:
        return 0.0
    intersection = tags_a & tags_b
    union = tags_a | tags_b
    return len(intersection) / len(union)


def build_idf_map(all_tag_sets: list[Set[str]]) -> Dict[str, float]:
    """
    Inverse document frequency for each tag.
    Tags that appear in fewer entities get higher weight.
    """
    n = len(all_tag_sets)
    if n == 0:
        return {}
    doc_freq: Counter = Counter()
    for tags in all_tag_sets:
        for tag in tags:
            doc_freq[tag] += 1
    return {
        tag: math.log((1 + n) / (1 + freq)) + 1.0
        for tag, freq in doc_freq.items()
    }


def idf_weighted_overlap(
    tags_a: Set[str],
    tags_b: Set[str],
    idf_map: Dict[str, float],
) -> float:
    """
    IDF-weighted overlap — rare shared tags score higher.
    Normalized to 0-1 by dividing by max possible score.
    """
    if not tags_a or not tags_b:
        return 0.0
    intersection = tags_a & tags_b
    if not intersection:
        return 0.0
    union = tags_a | tags_b
    shared_score = sum(idf_map.get(t, 1.0) for t in intersection)
    max_score = sum(idf_map.get(t, 1.0) for t in union)
    return shared_score / max_score if max_score > 0 else 0.0


def compute_tag_score(
    tags_a: Set[str],
    tags_b: Set[str],
    idf_map: Dict[str, float] | None = None,
) -> tuple[float, list[str]]:
    """
    Combined tag score: 50% Jaccard + 50% IDF-weighted.
    Returns (score, shared_tags_list).
    """
    shared = sorted(tags_a & tags_b)
    if idf_map:
        score = 0.5 * jaccard_similarity(tags_a, tags_b) + 0.5 * idf_weighted_overlap(tags_a, tags_b, idf_map)
    else:
        score = jaccard_similarity(tags_a, tags_b)
    return score, shared
