"""把模型输出解析成 {"hits": [...], "ambiguity": [...]}，容忍围栏与多余废话。"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_START = re.compile(r"^```(?:json)?\s*")
_FENCE_END = re.compile(r"\s*```$")


class HitParser:
    """模型输出 → 结构化命中。解析失败不抛异常，而是返回 parse_error 交给上层记账。"""

    def parse(self, raw: str) -> dict[str, Any]:
        text = _FENCE_END.sub("", _FENCE_START.sub("", raw.strip(), count=1), count=1)
        payload = self._loads(text)
        if payload is None:
            return {"hits": [], "ambiguity": [], "parse_error": "no json object"}
        if not isinstance(payload, dict):
            return {"hits": [], "ambiguity": [], "parse_error": "not a json object"}

        hits = [h for h in (payload.get("hits") or []) if isinstance(h, dict)]
        ambiguity = payload.get("ambiguity") or []
        if not isinstance(ambiguity, list):
            ambiguity = [str(ambiguity)]
        return {"hits": hits, "ambiguity": ambiguity, "parse_error": None}

    @staticmethod
    def _loads(text: str) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start == -1 or end <= start:
                return None
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return None
