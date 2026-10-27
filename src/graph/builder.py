"""把两个节点连成状态图：生成 → 校验 → 通过 / 打回 / 人工裁决。

这张图只做"连"，不做"算"：判断在 routing.decide()，取证在节点里。

    START ─→ generate ─→ verify ─┬─ pass     → finalize → END
                ↑                ├─ rewrite  → rewrite ─┐
                └────────────────┼─────────────────────┘
                                 └─ human    → human(interrupt) → END

两条框架约束，是这两次踩坑的根源，值得记住：

1. **边只能决定去哪，不能写数据。** 所以打回必须经过一个 `rewrite` 节点把违规清单写进
   State；通过必须经过 `finalize` 把草稿封成 `final`。（第一版直接 pass→END，final 是空的。）

2. **interrupt() 必须配 checkpointer。** 它靠"从检查点重放"来恢复，没有 checkpointer
   就没有地方存现场，恢复时等于从头再跑一遍。
"""

from __future__ import annotations

from typing import Any, Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from src.graph.nodes.generate import GenerateNode
from src.graph.nodes.verify import VerifyNode
from src.graph.routing import HUMAN, PASS, REWRITE, decide
from src.graph.state import GraphState, trace_entry
from src.judge.chat_model import ChatModel
from src.judge.constants import MAX_REWRITE_ATTEMPTS

ProgressHook = Callable[[str, str, bool, str], None]

# 人工裁决的三种回传值，由 CLI 通过 Command(resume=...) 送回来
ACCEPT = "accept"                 # 强制通过：记成"人工放行"，会计入漏杀统计
ABANDON = "abandon"               # 放弃这一稿
EDIT_PREFIX = "edit:"             # "edit:<改后的文本>"：采用人工改写稿


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
    """出口节点：把最后一稿封成 final。"""
    return {
        "final": str(state.get("draft", "")),
        "needs_human": False,
        "trace": list(state.get("trace", []))
        + [trace_entry("finalize", {"score": state.get("score"), "attempt": state.get("attempt")})],
    }


def human_node(state: GraphState) -> dict[str, Any]:
    """人工裁决节点（真中断）。

    interrupt() 会在这里挂起整张图，并把 payload 抛给调用方；
    调用方用 `Command(resume=<ACCEPT|ABANDON|edit:...>)` 恢复执行。
    恢复时这个函数**从头再跑一遍**，但 interrupt() 这次直接返回 resume 值 —— 所以
    挂起前不要做副作用（写文件、发请求），否则重放会做两次。
    """
    payload = {
        "draft": state.get("draft", ""),
        "score": state.get("score"),
        "attempt": state.get("attempt"),
        "violated": list(state.get("violated", [])),
    }
    choice = str(interrupt(payload) or ABANDON)

    if choice.startswith(EDIT_PREFIX):
        final, decision = choice[len(EDIT_PREFIX):], "edited_by_human"
    elif choice == ACCEPT:
        # 人工放行 = 系统本该拦住却让过了，这条必须计入漏杀统计，不能当"通过"
        final, decision = str(state.get("draft", "")), "accepted_by_human"
    else:
        final, decision = "", "abandoned"

    return {
        "final": final,
        "needs_human": True,
        "trace": list(state.get("trace", []))
        + [trace_entry("human", {"decision": decision, "score": state.get("score")})],
    }


def build_graph(
    spec: dict[str, Any],
    generator: ChatModel,
    judge: ChatModel,
    *,
    max_attempts: int = MAX_REWRITE_ATTEMPTS,
    on_progress: ProgressHook | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """编译一张可执行的状态图。返回对象支持 .invoke(state, config)。"""
    generate = GenerateNode(spec, generator)
    verify = VerifyNode(spec, judge, on_progress=on_progress)

    def route(state: GraphState) -> str:
        """条件边：只返回目的地，不写数据。"""
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

    # 没有 checkpointer 就没有地方存现场，interrupt 无从恢复 —— 所以总是给一个。
    return builder.compile(checkpointer=checkpointer or MemorySaver())
