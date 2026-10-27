"""手写闭环冒烟：不装 langgraph，先把「生成 → 校验 → 打回 → 重写」跑通。

为什么要先手写一遍：LangGraph 只是把这三个函数连起来。先亲眼看见连接处的数据长什么样，
再看框架的 State 图，才知道框架到底替我们做了什么 —— 这是"白盒"和"调包"的分界。

跑法（Windows 单行）：
    python -m src.cli.smoke_loop
    python -m src.cli.smoke_loop "华生说他今晚还想再去现场守一夜。"

每次运行 = 1 次生成 + 8 次判定（fanout），失败会重写再来一轮，最多 3 稿。
"""

from __future__ import annotations

import sys
import time
from typing import Any

from src.graph.nodes.generate import GenerateNode
from src.graph.nodes.verify import VerifyNode
from src.graph.routing import HUMAN, PASS, decide, explain
from src.graph.state import GraphState, new_state
from src.judge.chat_model import ChatModel, ChatModelError, OpenAICompatChatModel
from src.judge.constants import MAX_REWRITE_ATTEMPTS
from src.judge.env_loader import EnvLoader
from src.judge.spec_loader import SpecLoader

DEFAULT_SCENE = "华生说他今晚还想再去现场守一夜，让福尔摩斯把已知的线索讲一遍。"


def _build_generator() -> ChatModel:
    """生成侧：优先 LLM_* 变量（写台词用更好的模型）。"""
    model = EnvLoader.get("LLM_MODEL", "JUDGE_MODEL")
    if not model:
        raise SystemExit("未配置 LLM_MODEL / JUDGE_MODEL")
    return OpenAICompatChatModel(
        model,
        base_url=EnvLoader.get("LLM_BASE_URL", "JUDGE_BASE_URL"),
        api_key=EnvLoader.get("LLM_API_KEY", "JUDGE_API_KEY"),
    )


def _build_judge() -> ChatModel:
    """判定侧：优先 JUDGE_* 变量（判定用便宜、够稳的模型）。"""
    model = EnvLoader.get("JUDGE_MODEL", "LLM_MODEL")
    if not model:
        raise SystemExit("未配置 JUDGE_MODEL / LLM_MODEL")
    return OpenAICompatChatModel(
        model,
        base_url=EnvLoader.get("JUDGE_BASE_URL", "LLM_BASE_URL"),
        api_key=EnvLoader.get("JUDGE_API_KEY", "LLM_API_KEY"),
    )


def _fail_hook(_cand: str, trait: str, ok: bool, message: str) -> None:
    """只在失败时出声，成功的 8 条不刷屏。"""
    if not ok:
        print(f"      ! {trait} 失败：{message[:70]}")


def _print_round(state: GraphState, elapsed: float) -> None:
    print(f"\n── 第 {state.get('attempt', 0)} 稿 ──────────────────────────────")
    print(f"草稿：{state.get('draft', '')}")
    print(f"判定：score={state.get('score')}　证据 {len(state.get('violated', []))} 条　耗时 {elapsed:.1f}s")
    for note in state.get("violated", []):
        print(f"      ✗ {note}")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    scene = args[0] if args else DEFAULT_SCENE

    EnvLoader().load()
    spec = SpecLoader().load()
    generator, judging = _build_generator(), _build_judge()
    print(f"场景：{scene}")
    print(f"生成模型：{generator.model}　判定模型：{judging.model}")

    generate = GenerateNode(spec, generator)
    verify = VerifyNode(spec, judging, on_progress=_fail_hook)
    state = new_state(scene)

    while True:
        started = time.perf_counter()
        try:
            state.update(generate(state))
            state.update(verify(state))
        except ChatModelError as exc:
            print(f"\n调用失败，中止：{exc}")
            return 2
        _print_round(state, time.perf_counter() - started)

        action = decide(
            score=int(state.get("score", -1)),
            attempt=int(state.get("attempt", 0)),
            incomplete=bool(state.get("verify_incomplete", False)),
            max_attempts=MAX_REWRITE_ATTEMPTS,
        )
        print(f"  → 路由 {action}：{explain(action, int(state.get('score', -1)),
                                     int(state.get('attempt', 0)),
                                     bool(state.get('verify_incomplete', False)))}")

        if action == PASS:
            state["final"] = state.get("draft", "")
            break
        if action == HUMAN:
            state["final"] = state.get("draft", "")
            print("\n【需要人工裁决】这一稿将交给创作者确认或手改。")
            break
        # 打回：把违规证据清单塞回生成节点（方案 A：规则 + 原句）
        state["rewrite_notes"] = list(state.get("violated", []))

    _print_summary(state)
    return 0


def _print_summary(state: GraphState) -> None:
    print("\n" + "=" * 62)
    print(f"共生成 {state.get('attempt', 0)} 稿，最终 score={state.get('score')}")
    print(f"最终文本：{state.get('final', '')}")
    print(f"链路：{len(state.get('trace', []))} 条 trace")
    for item in state.get("trace", []):
        payload: dict[str, Any] = {k: v for k, v in item.items() if k != "node"}
        print(f"  · {item.get('node'):<9s} {payload}")


if __name__ == "__main__":
    raise SystemExit(main())
