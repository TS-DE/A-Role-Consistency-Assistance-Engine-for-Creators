"""把两个节点连成状态图：生成 → 校验 → 三条出口。

这张图只做"连"，不做"算"。所有判断都在 routing.decide()，所有取证都在节点里，
所以图本身薄得可以一眼看完——这正是它的价值：**改流程不用改逻辑**。

    START ─→ generate ─→ verify ─┬─ pass    → END
                ↑                ├─ rewrite → rewrite ─┐
                └────────────────┼────────────────────┘
                                 └─ human   → human ─→ END

为什么 rewrite 要单独一个节点、而不是让 conditional edge 直接跳回 generate：
LangGraph 的边只决定"去哪"，不能写数据。而打回必须把违规清单写进 State，
所以中间必须有个节点干这件事。这类"边不能写状态"的约束，是框架逼你想清楚数据流的地方。
"""

from __future__ import annotations

from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from src.graph.nodes.generate import GenerateNode
from src.graph.nodes.verify import VerifyNode
from src.graph.routing import HUMAN, PASS, REWRITE, decide
from src.graph.state import GraphState, trace_entry
from src.judge.chat_model import ChatModel
from src.judge.constants import MAX_REWRITE_ATTEMPTS

ProgressHook = Callable[[str, str, bool, str], None]


def rewrite_node(state: GraphState) -> dict[str, Any]:
    """打回节点：把违规清单塞回生成节点（方案 A：pattern + 原句），并清空分数。"""
    notes = list(state.get("violated", []))
    return {
        "rewrite_notes": notes,
        "score": -1,
        "trace": list(state.get("trace", []))
        + [trace_entry("rewrite", {"notes": len(notes), "next_attempt": int(state.get("attempt", 0)) + 1})],
    }


def finalize_node(state: GraphState) -> dict[str, Any]:
    """出口节点：把最后一稿封成 final。

    为什么需要它：条件边只能"去某个节点"，不能写数据。若 pass 直接连 END，
    State 里就没有 final 字段 —— 第一次跑真实闭环时 final 是空字符串，就是踩了这个坑。
    """
    return {
        "final": str(state.get("draft", "")),
        "needs_human": False,
        "trace": list(state.get("trace", []))
        + [trace_entry("finalize", {"score": state.get("score"), "attempt": state.get("attempt")})],
    }


def human_node(state: GraphState) -> dict[str, Any]:
    """人工裁决节点：把当前稿封存成 final 并打标记，交给 CLI 处理。

    真正的 HITL 应该用 langgraph 的 interrupt() + checkpointer（进程挂了还能接着走）。
    这里先做"标记 + 落盘"，等装包验证过 interrupt 的版本 API 再升级——
    宁可少一个花架子，也不要一个演示时才炸的假 HITL。
    """
    return {
        "final": str(state.get("draft", "")),
        "needs_human": True,
        "trace": list(state.get("trace", []))
        + [trace_entry("human", {"reason": "rewrite_exhausted_or_verify_incomplete",
                                 "score": state.get("score"),
                                 "attempt": state.get("attempt")})],
    }


def build_graph(
    spec: dict[str, Any],
    generator: ChatModel,
    judge: ChatModel,
    *,
    max_attempts: int = MAX_REWRITE_ATTEMPTS,
    on_progress: ProgressHook | None = None,
) -> Any:
    """编译一张可执行的状态图。返回的对象有 .invoke(state) 接口。"""
    generate = GenerateNode(spec, generator)
    verify = VerifyNode(spec, judge, on_progress=on_progress)

    def route(state: GraphState) -> str:
        """条件边：只返回目的地，不写数据（写数据交给 rewrite / human 节点）。"""
        return decide(
            score=int(state.get("score", -1)),
            attempt=int(state.get("attempt", 0)),
            incomplete=bool(state.get("verify_incomplete", False)),
            max_attempts=max_attempts,
        )

    builder = StateGraph(GraphState)
    builder.add_node("generate", generate)
    builder.add_node("verify", verify)
    builder.add_node("rewrite", rewrite_node)
    builder.add_node("finalize", finalize_node)
    builder.add_node("human", human_node)

    builder.add_edge(START, "generate")
    builder.add_edge("generate", "verify")
    builder.add_conditional_edges(
        "verify", route, {PASS: "finalize", REWRITE: "rewrite", HUMAN: "human"}
    )
    builder.add_edge("rewrite", "generate")
    builder.add_edge("finalize", END)
    builder.add_edge("human", END)
    return builder.compile()
