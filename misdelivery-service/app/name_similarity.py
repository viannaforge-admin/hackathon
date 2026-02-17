from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class SimilarityCandidate:
    selected_recipient_id: str
    selected_recipient_name: str
    similar_known_recipient_id: str
    similar_known_recipient_name: str
    similarity: float


def normalized_similarity(a: str, b: str) -> float:
    a_norm = " ".join(a.lower().split())
    b_norm = " ".join(b.lower().split())
    if not a_norm or not b_norm:
        return 0.0

    ratio_direct = SequenceMatcher(None, a_norm, b_norm).ratio()
    ratio_sorted = SequenceMatcher(None, " ".join(sorted(a_norm.split())), " ".join(sorted(b_norm.split()))).ratio()
    score = max(ratio_direct, ratio_sorted)

    a_first, a_last = _first_last_tokens(a_norm)
    b_first, b_last = _first_last_tokens(b_norm)
    if a_first and b_first and a_first == b_first:
        distance = _levenshtein(a_last, b_last)
        if distance <= 2:
            score = max(score, 0.93)
        elif a_last and b_last and min(len(a_last), len(b_last)) >= 4 and distance <= 4:
            score = max(score, 0.90)
        elif a_last and b_last:
            last_ratio = SequenceMatcher(None, a_last, b_last).ratio()
            if last_ratio >= 0.6:
                score = max(score, 0.91)

    return round(score, 4)


def _first_last_tokens(name: str) -> tuple[str, str]:
    parts = name.split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr_row = [i]
        for j, cb in enumerate(b, start=1):
            insertions = prev_row[j] + 1
            deletions = curr_row[j - 1] + 1
            substitutions = prev_row[j - 1] + (ca != cb)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]
