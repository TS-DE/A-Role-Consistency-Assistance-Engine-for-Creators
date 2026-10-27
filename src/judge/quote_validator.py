"""引文校验与区间定位：判定器的"可举证"硬保证。

每条命中必须给出能在候选原文里逐字找到的片段，否则整条作废。
编造引文拿不到分 —— 这是把"可举证"从口号变成机器可检查的东西。
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from src.judge.constants import QUOTE_ELLIPSIS, SENTENCE_ENDS

_PUNCT_MAP = str.maketrans(
    {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2014": "-", "\u2013": "-"}
)


class QuoteValidator:
    """归一化、区间定位、子串校验、落句定位。"""

    _ellipsis = re.compile(QUOTE_ELLIPSIS)

    def normalize(self, text: str) -> str:
        """全角→半角、弯引号→直引号、空白压缩、大小写折叠。只用于比对。"""
        text = unicodedata.normalize("NFKC", text or "")
        text = text.translate(_PUNCT_MAP)
        return re.sub(r"\s+", " ", text).strip().casefold()

    def validate(self, hits: list[dict], candidate: str) -> tuple[list[dict], list[dict]]:
        """返回 (通过, 被拒)。允许用 ... 连接两段不连续原文，逐段校验。"""
        haystack = self.normalize(candidate)
        passed: list[dict] = []
        rejected: list[dict] = []
        for hit in hits:
            quote = str(hit.get("quote") or "").strip()
            if not quote:
                rejected.append({**hit, "_reason": "empty_quote"})
                continue
            parts = [p for p in self._ellipsis.split(quote) if p.strip()]
            if parts and all(self.normalize(p) in haystack for p in parts):
                passed.append(hit)
            else:
                rejected.append({**hit, "_reason": "quote_not_in_candidate"})
        return passed, rejected

    def span_of(self, haystack: str, quote: str) -> tuple[int, int]:
        """在归一化文本里定位引文区间；定位不到返回 (-1, -1)。"""
        parts = [p for p in self._ellipsis.split(quote) if p.strip()]
        if not parts:
            return (-1, -1)
        start = haystack.find(self.normalize(parts[0]))
        if start == -1:
            return (-1, -1)
        if len(parts) == 1:
            return (start, start + len(self.normalize(parts[0])))
        last = haystack.find(self.normalize(parts[-1]), start)
        end = last + len(self.normalize(parts[-1])) if last != -1 else start + len(self.normalize(parts[0]))
        return (start, end)

    def sentence_of(self, haystack: str, position: int) -> tuple[int, int]:
        """返回 position 所在句子的区间（含句末标点）。

        这是跨 trait 去重的判据：**同一句里被两个 trait 各报一次算一处漂移，跨句算两处**。
        为什么不用"引文区间是否重叠"：模型有时引整句、有时只引一个从句，区间随之伸缩，
        重叠判定就跟着抖（E06-a 三轮跑出 0/1/0 正是如此）。换用落句判断与引文长短无关。
        """
        if position < 0 or position >= len(haystack):
            return (-1, -1)
        start = 0
        for index in range(position - 1, -1, -1):
            if haystack[index] in SENTENCE_ENDS:
                start = index + 1
                break
        end = len(haystack)
        for index in range(position, len(haystack)):
            if haystack[index] in SENTENCE_ENDS:
                end = index + 1
                break
        return (start, end)
