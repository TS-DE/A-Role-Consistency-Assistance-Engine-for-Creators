"""走 LangGraph 状态图的闭环入口。

    python -m src.cli.run_graph
    python -m src.cli.run_graph "华生说他今晚还想再去现场守一夜。"

与 smoke_loop 的区别：smoke_loop 手写 while，run_graph 走 builder 编译出来的图。
两者共用同一套节点、同一套路由，所以跑出来的结论应当一致 —— 这就是"手写一遍再上框架"的意义：
**换的是编排方式，不是判定逻辑。**
"""

from __future__ import annotations

import sys
import time

from src.graph.builder import build_graph
from src.graph.state import GraphState, new_state
from src.judge.chat_model import ChatModelError, build_generator_model, build_judge_model
from src.judge.constants import MAX_REWRITE_ATTEMPTS
from src.judge.env_loader import EnvLoader
from src.judge.spec_loader import SpecLoader

DEFAULT_SCENE = "华生说他今晚还想再去现场守一夜，让福尔摩斯把已知的线索讲一遍。"


def _fail_hook(_cand: str, trait: str, ok: bool, message: str) -> None:
    if not ok:
        print(f"      ! {trait} 失败：{message[:70]}")


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

    started = time.perf_counter()
    try:
        result = graph.invoke(new_state(scene))
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
    print(f"最终文本：{state.get('final', '')}")
    print(f"链路 {len(state.get('trace', []))} 条：")
    for item in state.get("trace", []):
        payload = {k: v for k, v in item.items() if k != "node"}
        print(f"  · {item.get('node'):<9s} {payload}")


if __name__ == "__main__":
    raise SystemExit(main())
