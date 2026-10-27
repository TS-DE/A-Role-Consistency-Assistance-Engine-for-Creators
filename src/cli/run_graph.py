"""走 LangGraph 状态图的闭环入口，含真 HITL（interrupt + 恢复）。

    python -m src.cli.run_graph
    python -m src.cli.run_graph "华生说他今晚还想再去现场守一夜。"

流程：生成 → 判定 → 通过则出口；被判违规则打回重写；打回用尽 → 中断，转人工。

人工那一步是真中断：图会挂起并把现场抛出来，CLI 打印三份材料让人裁决，
裁决结果用 Command(resume=...) 送回图里继续走。进程挂掉也不会丢现场（MemorySaver 在内存里，
换 SqliteSaver 就能落盘——这是下一步）。
"""

from __future__ import annotations

import sys
import time

from langgraph.types import Command

from src.graph.builder import ABANDON, ACCEPT, EDIT_PREFIX, build_graph
from src.graph.state import GraphState, new_state
from src.judge.chat_model import ChatModelError, build_generator_model, build_judge_model
from src.judge.constants import MAX_REWRITE_ATTEMPTS
from src.judge.env_loader import EnvLoader
from src.judge.spec_loader import SpecLoader

DEFAULT_SCENE = "华生说他今晚还想再去现场守一夜，让福尔摩斯把已知的线索讲一遍。"


def _fail_hook(_cand: str, trait: str, ok: bool, message: str) -> None:
    if not ok:
        print(f"      ! {trait} 失败：{message[:70]}")


def _ask_human(payload: dict) -> str:
    """打印裁决材料，读一个决定，返回 Command 需要的 resume 值。"""
    print("\n" + "─" * 62)
    print("【需要人工裁决】自动流程没能让这一稿达标")
    print(f"判定：score={payload.get('score')}　第 {payload.get('attempt')} 稿")
    print(f"\n草稿：\n{payload.get('draft', '')}\n")
    violations = payload.get("violated") or []
    if violations:
        print("违规证据：")
        for note in violations:
            print(f"  ✗ {note}")
    else:
        print("违规证据：无（可能是校验未完成）")

    print("\n决定：[a] 强制通过（会计入漏杀统计）  [e] 手改  [r] 放弃")
    choice = input("> ").strip().lower()

    if choice == "a":
        return ACCEPT
    if choice == "e":
        print("粘贴/改写你的版本（单行，空行表示放弃）：")
        edited = input("> ").strip()
        return f"{EDIT_PREFIX}{edited}" if edited else ABANDON
    return ABANDON


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    scene = args[0] if args else DEFAULT_SCENE

    EnvLoader().load()
    spec = SpecLoader().load()
    generator, judge = build_generator_model(), build_judge_model()
    print(f"场景：{scene}")
    print(f"生成模型：{generator.model}　判定模型：{judge.model}")

    graph = build_graph(
        spec, generator, judge,
        max_attempts=MAX_REWRITE_ATTEMPTS,
        on_progress=_fail_hook,
    )
    config = {"configurable": {"thread_id": f"roleguard-{int(time.time())}"}}

    started = time.perf_counter()
    try:
        result = graph.invoke(new_state(scene), config)
        # 图挂起了：把现场拿出来交给人
        if result.get("__interrupt__"):
            payload = result["__interrupt__"][0].value
            result = graph.invoke(Command(resume=_ask_human(payload)), config)
    except ChatModelError as exc:
        print(f"\n调用失败，中止：{exc}")
        return 2
    elapsed = time.perf_counter() - started

    _print_result(result, elapsed)
    return 0


def _print_result(state: GraphState, elapsed: float) -> None:
    print("\n" + "=" * 62)
    print(f"共生成 {state.get('attempt', 0)} 稿　最终 score={state.get('score')}　总耗时 {elapsed:.1f}s")
    print(f"需要人工：{'是' if state.get('needs_human') else '否'}")
    print(f"最终文本：{state.get('final', '') or '（无：已放弃）'}")
    print(f"链路 {len(state.get('trace', []))} 条：")
    for item in state.get("trace", []):
        payload = {k: v for k, v in item.items() if k != "node"}
        print(f"  · {item.get('node'):<9s} {payload}")


if __name__ == "__main__":
    raise SystemExit(main())
