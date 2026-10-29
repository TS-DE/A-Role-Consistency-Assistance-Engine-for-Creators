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
from langgraph.types import Send, interrupt

from src.graph.nodes.arbiter import Arbiter
from src.graph.nodes.experts import TraitExpert
from src.graph.nodes.generate import GenerateNode
from src.graph.nodes.verify import VerifyNode
from src.graph.routing import HUMAN, PASS, REWRITE, decide
from src.graph.state import GraphState, trace_entry
from src.judge.aggregator import ScoreAggregator
from src.judge.chat_model import ChatModel
from src.judge.constants import MAX_REWRITE_ATTEMPTS
from src.judge.env_loader import EnvLoader
from src.judge.evaluator import TraitEvaluator

# 回退开关：AGENT_MODE 环境变量（默认 simple，即现行为；blackboard=8 专家写板 + 裁决者读板）
AGENT_MODE_SIMPLE = "simple"
AGENT_MODE_BLACKBOARD = "blackboard"

# 入口层（run_graph / web）展示用的统一文案：口径必须与 _resolve_agent_mode 同源，
# 防止"页面显示 simple、图里跑 blackboard"这类两张皮。
AGENT_MODE_LABELS = {
    AGENT_MODE_SIMPLE: "simple（单节点并行直判）",
    AGENT_MODE_BLACKBOARD: "blackboard（8 专家写板 + 裁决者）",
}

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


def _resolve_agent_mode(agent_mode: str | None) -> str:
    """显式参数 > 环境变量 AGENT_MODE > simple。

    默认必须落在 simple：这是回退开关，环境变量缺失/拼写外的值都要能退回现行为；
    未知取值直接报错，不静默降级——静默回退会让"以为开了黑板其实没开"成为最难查的 bug。
    """
    resolved = (agent_mode or EnvLoader.get("AGENT_MODE", default=AGENT_MODE_SIMPLE)
                or AGENT_MODE_SIMPLE).strip().lower()
    if resolved not in (AGENT_MODE_SIMPLE, AGENT_MODE_BLACKBOARD):
        raise ValueError(f"未知 AGENT_MODE：{resolved}（可用：simple / blackboard）")
    return resolved


def current_agent_mode(agent_mode: str | None = None) -> str:
    """入口层（CLI/web）获取"当前生效模式"的唯一来源：与建图解析同源，杜绝两张皮。

    异常场景：AGENT_MODE 取值非法时按硬约束显式抛 ValueError（不静默回退），
    由调用方决定是打印中止（CLI）还是报错停渲染（web）。
    """
    return _resolve_agent_mode(agent_mode)


def agent_mode_label(mode: str) -> str:
    return AGENT_MODE_LABELS[mode]


def _wire_blackboard(builder: StateGraph, spec: dict[str, Any], judge: ChatModel,
                     route: Callable[[GraphState], str],
                     on_progress: ProgressHook | None) -> None:
    """黑板接线：generate → fan_out --Send×N--> expert__轴 → arbiter → route。

    共享一个 TraitEvaluator 实例（连续失败计数等内部状态本就应全局共享），
    每个 TraitExpert 节点只往 board 追加自己的一条；聚合只在 Arbiter。
    """
    trait_ids = list(spec["_traits_by_id"])
    # 进度回调传给专家：黑板路径里 judge_case 不被调用，逐轴勾选只能由专家自己发
    # （judge_case 的 _emit 路径一字未动，simple 模式进度逐字节不变）。
    evaluator = TraitEvaluator(spec, judge, on_progress=on_progress)
    expert = TraitExpert(spec, evaluator, on_progress=on_progress)

    def fan_out_node(state: GraphState) -> dict[str, Any]:
        """只记一条调度日志。trace 通道无 reducer，并行分支不许写它——所以日志记在扇出点。"""
        dispatched = 0 if not str(state.get("draft", "")).strip() else len(trait_ids)
        return {"trace": list(state.get("trace", []))
                + [trace_entry("fan_out", {"attempt": int(state.get("attempt", 0)),
                                            "dispatched": dispatched})]}

    def dispatch(state: GraphState) -> Any:
        draft = str(state.get("draft", "")).strip()
        if not draft:
            # 空草稿不派专家（等于 simple 模式 VerifyNode 的守卫前置）；arbiter 里出同形结果
            return "arbiter"
        attempt = int(state.get("attempt", 0))
        return [Send(f"expert__{tid}", {"candidate": draft, "trait_id": tid, "attempt": attempt})
                for tid in trait_ids]

    arbiter = Arbiter(ScoreAggregator(), trait_order=trait_ids)
    builder.add_node("fan_out", fan_out_node)
    builder.add_node("arbiter", arbiter)
    for tid in trait_ids:
        builder.add_node(f"expert__{tid}", expert)
        builder.add_edge(f"expert__{tid}", "arbiter")
    builder.add_edge("generate", "fan_out")
    builder.add_conditional_edges("fan_out", dispatch)
    builder.add_conditional_edges(
        "arbiter", route, {PASS: "finalize", REWRITE: "rewrite", HUMAN: "human"}
    )


def build_graph(
    spec: dict[str, Any],
    generator: ChatModel,
    judge: ChatModel,
    *,
    max_attempts: int = MAX_REWRITE_ATTEMPTS,
    on_progress: ProgressHook | None = None,
    checkpointer: Any | None = None,
    agent_mode: str | None = None,
) -> Any:
    """编译一张可执行的状态图。返回对象支持 .invoke(state, config)。

    agent_mode：simple（默认，逐字节现行为）/ blackboard（8 专家写板 + 裁决者读板）。
    """
    mode = _resolve_agent_mode(agent_mode)
    generate = GenerateNode(spec, generator)

    def route(state: GraphState) -> str:
        """条件边：只返回目的地，不写数据。两种模式共用同一个闭包，路由一行不改。"""
        return decide(
            score=int(state.get("score", -1)),
            attempt=int(state.get("attempt", 0)),
            incomplete=bool(state.get("verify_incomplete", False)),
            max_attempts=max_attempts,
        )

    builder = StateGraph(GraphState)
    builder.add_node("generate", generate)
    builder.add_node("rewrite", rewrite_node)
    builder.add_node("finalize", finalize_node)
    builder.add_node("human", human_node)

    builder.add_edge(START, "generate")
    builder.add_edge("rewrite", "generate")
    builder.add_edge("finalize", END)
    builder.add_edge("human", END)

    if mode == AGENT_MODE_BLACKBOARD:
        _wire_blackboard(builder, spec, judge, route, on_progress)
    else:
        verify = VerifyNode(spec, judge, on_progress=on_progress)
        builder.add_node("verify", verify)
        builder.add_edge("generate", "verify")
        builder.add_conditional_edges(
            "verify", route, {PASS: "finalize", REWRITE: "rewrite", HUMAN: "human"}
        )

    # 没有 checkpointer 就没有地方存现场，interrupt 无从恢复 —— 所以总是给一个。
    return builder.compile(checkpointer=checkpointer or MemorySaver())
