"""走 LangGraph 状态图的闭环入口，含真 HITL（interrupt + 恢复）。

    python -m src.cli.run_graph
    python -m src.cli.run_graph "华生说他今晚还想再去现场守一夜。"

流程：生成 → 判定 → 通过则出口；被判违规则打回重写；打回用尽 → 中断，转人工。

人工那一步是真中断：图会挂起并把现场抛出来，CLI 打印三份材料让人裁决，
裁决结果用 Command(resume=...) 送回图里继续走。进程挂掉也不会丢现场（MemorySaver 在内存里，
换 SqliteSaver 就能落盘——这是下一步）。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

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


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="走状态图跑一次闭环")
    parser.add_argument("scene", nargs="?", default=DEFAULT_SCENE, help="创作者给的情境")
    parser.add_argument("--json-out", help="把本次 trace 落盘，供成本/延迟汇总（cost_report 读取）")
    return parser.parse_args(argv)


def _build_record(scene: str, gen_model: str, judge_model: str,
                  state: GraphState, total_ms: int) -> dict:
    """成本/延迟汇总要用的一条记录。字段保持扁平，便于脚本直接读。"""
    return {
        "scene": scene,
        "models": {"generate": gen_model, "judge": judge_model},
        "attempt": state.get("attempt", 0),
        "final_score": state.get("score"),
        "needs_human": bool(state.get("needs_human", False)),
        "total_ms": total_ms,
        "nodes": [dict(item) for item in state.get("trace", [])],
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    scene = args.scene

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
    if args.json_out:
        record = _build_record(scene, generator.model, judge.model, result, int(elapsed * 1000))
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)   # 目录不存在时直接写会抛错
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"trace 已写入 {out}（可用 cost_report 汇总）")
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
