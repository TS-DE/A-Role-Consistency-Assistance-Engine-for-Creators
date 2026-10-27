"""把各 trait 的命中聚合成三档分。

分数是**算出来的**，不是模型给的：模型只举证，聚合规则在这里。
"""

from __future__ import annotations

from typing import Any

from src.judge.constants import SCORE_DRIFT, SCORE_OOC, SCORE_PASS, SOFT_HITS_TO_OOC
from src.judge.quote_validator import QuoteValidator


class ScoreAggregator:
    """按规格书 §一 的顺序聚合，顺序不许反。

    1. 任一 hard 命中                -> 0
    2. soft 命中（按 trait 去重）>= 2 -> 0
    3. soft 命中（按 trait）= 1       -> 1
    4. 否则                          -> 2
    """

    def __init__(self, validator: QuoteValidator | None = None) -> None:
        self._validator = validator or QuoteValidator()

    def score(self, results: list[dict], candidate: str = "") -> dict[str, Any]:
        haystack = self._validator.normalize(candidate)
        hard_hits: list[dict] = []
        soft_by_trait: dict[str, list[dict]] = {}
        claimed: list[tuple[tuple[int, int], str]] = []
        deduped: list[dict] = []

        for result in results:
            for hit in result["hits"]:
                severity = str(hit.get("severity") or result["severity"]).lower()
                if severity == "hard":
                    hard_hits.append({"trait": result["trait"], **hit})
                    continue
                kept_by = self._claim_sentence(haystack, hit, result["trait"], claimed)
                if kept_by is not None:
                    deduped.append(
                        {"trait": result["trait"], "quote": hit.get("quote"), "kept_by": kept_by}
                    )
                    continue
                soft_by_trait.setdefault(result["trait"], []).append(hit)

        return {
            "score": self._decide(hard_hits, len(soft_by_trait)),
            "hard_hits": hard_hits,
            "soft_traits": list(soft_by_trait),
            "n_soft": len(soft_by_trait),
            "deduped": deduped,
        }

    def _claim_sentence(
        self,
        haystack: str,
        hit: dict,
        trait: str,
        claimed: list[tuple[tuple[int, int], str]],
    ) -> str | None:
        """若该命中落在已被别的 trait 认领的句子里，返回认领者；否则登记并返回 None。"""
        span = self._validator.span_of(haystack, str(hit.get("quote") or ""))
        sentence = self._validator.sentence_of(haystack, span[0])
        if sentence[0] < 0:
            # 定位不到就不去重：宁可多计一条，也不要误并成一条。
            return None
        for owner_sentence, owner in claimed:
            if owner_sentence == sentence:
                return owner
        claimed.append((sentence, trait))
        return None

    @staticmethod
    def _decide(hard_hits: list[dict], soft_count: int) -> int:
        if hard_hits:
            return SCORE_OOC
        if soft_count >= SOFT_HITS_TO_OOC:
            return SCORE_OOC
        if soft_count == 1:
            return SCORE_DRIFT
        return SCORE_PASS
