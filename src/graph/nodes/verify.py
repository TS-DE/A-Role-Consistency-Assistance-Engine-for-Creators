"""校验节点：拿草稿去挨 8 条规则，把"命中了什么"写回 State。

读：state["draft"]
写：state["verdicts"] / state["score"] / state["violated"] / state["verify_incomplete"]

三条设计决定，都有踩坑记录：

1. **永远 fanout**（8 条 trait 全判）。D04-b 的教训：一条回复的违规可能落在
   被标注之外的另一条轴（健康冷嘲在 watson_rapport，却被标在 emotional_restraint 下），
   只判一条必然漏。所以这里不提供"只判某一条"的开关。

2. **复用 TraitEvaluator，不重写判定逻辑**。判定器已经过 22 个离线用例和三轮留出集验证，
   图里再实现一遍就是两份会各自漂移的真相。

3. **判定没跑完不许当通过**。任何一条 trait 调用失败 → score 记 -1、verify_incomplete 记 True，
   路由层必须把它送去人工，而不是当成"没命中所以通过了"。
   缺一条规则的聚合分可能恰好等于 2 分，那是假通过。
"""

from __future__ import annotations

from typing import Any, Callable

from src.graph.state import GraphState, summarize_hits, trace_entry
from src.judge.chat_model import ChatModel
from src.judge.evaluator import TraitEvaluator

INCOMPLETE_SCORE = -1


class VerifyNode:
    """一次校验 = 8 次单规则判定 + 一次聚合。状态全在 State 里，节点本身无状态。"""

    def __init__(
        self,
        spec: dict[str, Any],
        model: ChatModel,
        on_progress: Callable[[str, str, bool, str], None] | None = None,
    ) -> None:
        self._traits = spec["_traits_by_id"]
        self._evaluator = TraitEvaluator(spec, model, on_progress=on_progress)

    def __call__(self, state: GraphState) -> dict[str, Any]:
        draft = str(state.get("draft", "")).strip()
        trace = list(state.get("trace", []))

        if not draft:
            return {
                "verdicts": [],
                "score": INCOMPLETE_SCORE,
                "violated": [],
                "verify_incomplete": True,
                "trace": trace + [trace_entry("verify", {"error": "empty draft"})],
            }

        # judge_case 只需要 text；fanout=True 时不会去读 cand["trait"]
        candidate = {"id": f"draft-a{state.get('attempt', 0)}", "text": draft}
        aggregate, results, failed = self._evaluator.judge_case(
            candidate, self._traits, fanout=True
        )

        violated = summarize_hits(results)
        # TODO(你)：现在的 violated 把"pattern + 原句"都塞回去给生成节点。
        # 留一处自己试：只回传"违反了哪条规则"，不给原句，看模型是否更愿意真改，
        # 而不是把原句保留一半再绕过去。改完用回归集 E01–E08 比对。
        entry = trace_entry(
            "verify",
            {
                "attempt": state.get("attempt", 0),
                "score": aggregate["score"],
                "hits": len(violated),
                "failed_traits": len(failed),
            },
        )

        if failed:
            return {
                "verdicts": results,
                "score": INCOMPLETE_SCORE,
                "violated": violated,
                "verify_incomplete": True,
                "trace": trace + [entry],
            }

        return {
            "verdicts": results,
            "score": aggregate["score"],
            "violated": violated,
            "verify_incomplete": False,
            "trace": trace + [entry],
        }
