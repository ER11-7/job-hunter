from __future__ import annotations

import math
import re
from collections import Counter


WORD_PATTERN = re.compile(r"[A-Za-z0-9\+\#\.-]{2,}")


def normalize_tokens(text: str) -> list[str]:
    return [token.lower() for token in WORD_PATTERN.findall(text or "")]


def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item.strip())
    return result


def cosine_similarity(left: str, right: str) -> float:
    left_counter = Counter(normalize_tokens(left))
    right_counter = Counter(normalize_tokens(right))
    if not left_counter or not right_counter:
        return 0.0

    shared = set(left_counter) & set(right_counter)
    numerator = sum(left_counter[token] * right_counter[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left_counter.values()))
    right_norm = math.sqrt(sum(value * value for value in right_counter.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
