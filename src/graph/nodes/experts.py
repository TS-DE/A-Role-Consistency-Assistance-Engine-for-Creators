"""规则专家：单条 trait 的判定工人，结论写黑板，不做任何聚合。

设计契约（agent_docs/19 §2.3）：
1. 专家只读"自己的规则 + 候选文本"，看不到别的专家的结论——上下文 O(N) 而非 O(N²)；
2. 判定本体直接复用 TraitEvaluator.judge_trait，与 VerifyNode 走同一份代码：
   图里再实现一遍判定，就是埋两份会各自漂移的真相；
3. 任何异常写进 BoardEntry.failed，绝不让它冒泡——8 个并行分支里炸一个就中断
   整张图的话，黑板架构比单节点更脆，这是经典翻车点；失败是否可信由 Arbiter 统一裁决。
"""

from __future__ import annotations

import time
from typing import Any

from src.graph.board import BoardEntry
from src.judge.evaluator import TraitEvaluator

FAILED_REASON_LIMIT = 200  # 失败原因截断长度：整段 traceback 进黑板会把裁决者淹死


class TraitExpert:
    """一个实例负责一条 trait；同一实例被 Send 反复调用（自身无状态，状态在 evaluator）。"""

    def __init__(self, spec: dict[str, Any], evaluator: TraitEvaluator) -> None:
        self._traits = spec["_traits_by_id"]
        self._evaluator = evaluator

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        """LangGraph Send 的节点只收到 payload，拿不到完整 State —— 这是 Send 的契约。

        入参 payload：{"candidate": str, "trait_id": str, "attempt": int}
        返回：{"board": [BoardEntry]} —— 只追加自己这一条。
        异常场景：judge_trait 抛出的任何异常被捕获为 failed 条目；本方法自身不抛。
        """
        candidate = str(payload.get("candidate", ""))
        trait_id = str(payload.get("trait_id", ""))
        attempt = int(payload.get("attempt", 0))
        started = time.perf_counter()

        # 未知 trait_id 也走 failed：Send 的 payload 是外部输入，契约要求本方法自身不抛
        trait = self._traits.get(trait_id) or {}
        if not trait:
            return {"board": [self._entry_failed(trait_id, trait, attempt,
                                                 f"unknown trait: {trait_id}", started)]}
        try:
            result = self._evaluator.judge_trait(candidate, trait)
        except Exception as exc:  # noqa: BLE001 —— 契约要求：专家只准报伤亡，不准沉船
            return {"board": [self._entry_failed(trait_id, trait, attempt,
                                                  str(exc)[:FAILED_REASON_LIMIT], started)]}

        return {"board": [BoardEntry(
            trait=trait_id,
            # severity 取规格不取结果：虽然 judge_trait 的回显也来自规格，
            # 但契约要写在读取侧可见的地方——裁决者据此算分，绝不信模型自述的档位
            severity=str(trait.get("severity", "soft")),
            hits=result["hits"],
            invalid=result["invalid"],
            ambiguity=result["ambiguity"],
            failed="",
            prompt_chars=int(result.get("prompt_chars", 0)),
            reply_chars=int(result.get("reply_chars", 0)),
            parse_error=result.get("parse_error"),
            ms=self._ms(started),
            attempt=attempt,
        )]}

    @staticmethod
    def _ms(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)

    def _entry_failed(self, trait_id: str, trait: dict[str, Any], attempt: int,
                      reason: str, started: float) -> BoardEntry:
        """失败条目：hits 全空但 failed 非空——裁决者看到 failed 就知道这块板不完整。"""
        return BoardEntry(
            trait=trait_id,
            severity=str(trait.get("severity", "soft")),
            hits=[], invalid=[], ambiguity=[],
            failed=reason,
            prompt_chars=0, reply_chars=0,
            parse_error=None,
            ms=self._ms(started),
            attempt=attempt,
        )
