"""三个 MCP 工具的实现（不依赖 MCP SDK，便于离线测试）。

设计原则：**工具层只做协议适配，判定逻辑一行不重写**——直接复用 `TraitEvaluator`。
所以 MCP 上判出来的分，和评测脚本、闭环里的分是同一套口径。若各自实现一遍，
三个月后就会出现"编辑器里说是 2 分、报表里说是 0 分"的情况。
"""

from __future__ import annotations

from typing import Any

from src.graph.state import summarize_hits
from src.judge.evaluator import TraitEvaluator

SCORE_LABELS = {
    2: "pass（符合人设）",
    1: "drift（轻微漂移）",
    0: "OOC（出戏）",
    -1: "incomplete（判定未完成，不可当通过）",
}


class RoleGuardTools:
    """把"查规则"和"判一条回复"包成三件事。"""

    def __init__(self, spec: dict[str, Any], evaluator: TraitEvaluator) -> None:
        self._spec = spec
        self._traits: dict[str, dict] = spec["_traits_by_id"]
        self._evaluator = evaluator

    def list_traits(self) -> list[dict[str, Any]]:
        """列出人设卡里全部判定轴，让调用方知道有哪些规则可选。"""
        return [
            {"id": trait["id"], "name": trait.get("name", ""), "severity": trait.get("severity", "")}
            for trait in self._spec["traits"]
        ]

    def get_trait_rule(self, trait_id: str) -> dict[str, Any]:
        """取某条轴的完整规则（rule + anti_patterns），便于调用方自查为何被判违规。"""
        trait = self._traits.get(trait_id)
        if trait is None:
            return {"error": f"未知 trait：{trait_id}", "available": sorted(self._traits)}
        return {
            "id": trait["id"],
            "name": trait.get("name", ""),
            "severity": trait.get("severity", ""),
            "rule": str(trait.get("rule", "")).strip(),
            "anti_patterns": [
                {"level": item.get("level", "soft"), "pattern": item.get("pattern", "")}
                for item in (trait.get("anti_patterns") or [])
            ],
        }

    def judge_reply(self, candidate: str, traits: list[str] | None = None) -> dict[str, Any]:
        """判一条回复。traits 为空则判全部；否则只判指定几条。

        返回里的 `violations` 每条都带**能在原文里逐字找到的引文** —— 这是这套判定
        唯一不能被模型自由发挥的地方：编不出引文的命中会被程序丢弃。
        """
        if not candidate or not candidate.strip():
            return {"score": -1, "label": SCORE_LABELS[-1], "error": "候选文本为空"}

        if traits:
            missing = [name for name in traits if name not in self._traits]
            if missing:
                return {
                    "score": -1,
                    "label": SCORE_LABELS[-1],
                    "error": f"未知 trait：{missing}",
                    "available": sorted(self._traits),
                }
            selected = {name: self._traits[name] for name in traits}
        else:
            selected = dict(self._traits)

        aggregate, results, failed = self._evaluator.judge_case(
            {"id": "mcp-call", "text": candidate}, selected, fanout=True
        )
        violations = summarize_hits(results)
        score = -1 if failed else int(aggregate["score"])

        return {
            "score": score,
            "label": SCORE_LABELS.get(score, "unknown"),
            "violations": violations,
            "hit_count": len(violations),
            "soft_traits": aggregate["soft_traits"],
            "soft_count": aggregate["n_soft"],
            "incomplete": bool(failed),
            "failed_traits": failed,
            "judged_traits": list(selected),
        }
