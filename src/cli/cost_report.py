"""成本 / 延迟汇总：读 run_graph 落盘的 trace，出答辩要用的那张表。

    python -m src.cli.cost_report
    python -m src.cli.cost_report --dir reports/traces --judge-price 0.8,2.7 --gen-price 1,2

两条口径必须先说清楚，否则数字没法被信任：

1. **延迟是实测的**：每个节点都记了 `ms`，取自 `time.perf_counter()`。
2. **tokens 是估算的**：只记录了 prompt / reply 的**字符数**，按 `--chars-per-token`
   （默认 3.0，中英混排的经验值）折算。所以成本是"量级参考"，不是账单。

要拿到真实 tokens，就得在模型后端解析 usage 字段；那属于以后的事，
现在把估算的口径写死在命令行参数里，比偷偷用一个魔法数字强。
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

from src.judge.constants import PROJECT_ROOT

DEFAULT_DIR = PROJECT_ROOT / "reports" / "traces"
CHARS_PER_TOKEN = 3.0          # 中英混排经验值，可用 --chars-per-token 覆盖
DEFAULT_JUDGE_PRICE = (0.8, 2.7)   # 每百万 tokens 的（输入, 输出）价，flash 档
DEFAULT_GEN_PRICE = (1.0, 2.0)     # 生成侧默认按便宜档估，实际按你用的模型改


def _parse_price(text: str) -> tuple[float, float]:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError('价格格式应为 "输入,输出"，例如 0.8,2.7')
    return float(parts[0]), float(parts[1])


def load_records(directory: Path) -> list[dict[str, Any]]:
    """读目录下所有 trace。坏文件跳过并提示，不要因为一条烂数据整张表算不出来。"""
    if not directory.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"跳过 {path.name}：{exc}")
    return records


def _percentile(values: list[float], ratio: float) -> float:
    """线性插值分位数。样本少时 p95 就是最大值，注释里已说明。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = ratio * (len(ordered) - 1)
    low, high = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def summarise(records: list[dict], chars_per_token: float = CHARS_PER_TOKEN,
              judge_price: tuple[float, float] = DEFAULT_JUDGE_PRICE,
              gen_price: tuple[float, float] = DEFAULT_GEN_PRICE) -> dict[str, Any]:
    """把 N 条 trace 压成：耗时分布、节点占比、估算 tokens、估算成本。"""
    if not records:
        return {"n": 0}

    totals = [float(r.get("total_ms", 0)) for r in records]
    by_node: dict[str, dict[str, float]] = {}
    judge_in = judge_out = gen_in = gen_out = 0.0

    for record in records:
        for node in record.get("nodes", []):
            name = str(node.get("node", "?"))
            slot = by_node.setdefault(name, {"calls": 0, "ms": 0.0})
            slot["calls"] += 1
            slot["ms"] += float(node.get("ms", 0))

            prompt_chars = float(node.get("prompt_chars", 0))
            reply_chars = float(node.get("chars") or node.get("reply_chars") or 0)
            if name == "generate":
                gen_in += prompt_chars / chars_per_token
                gen_out += reply_chars / chars_per_token
            elif name == "verify":
                judge_in += prompt_chars / chars_per_token
                judge_out += reply_chars / chars_per_token

    node_ms_total = sum(slot["ms"] for slot in by_node.values()) or 1.0
    for slot in by_node.values():
        # 分母用"节点耗时之和"，不是"运行总耗时"：总耗时还含图调度开销，
        # 用它做分母会让各节点占比加起来不到 100%，读者会以为漏算了什么。
        slot["share"] = slot["ms"] / node_ms_total

    cost = (
        judge_in * judge_price[0] + judge_out * judge_price[1]
        + gen_in * gen_price[0] + gen_out * gen_price[1]
    ) / 1_000_000

    return {
        "n": len(records),
        "mean_ms": statistics.fmean(totals),
        "median_ms": statistics.median(totals),
        "p95_ms": _percentile(totals, 0.95),
        "by_node": by_node,
        "judge_tokens": (judge_in, judge_out),
        "gen_tokens": (gen_in, gen_out),
        "total_cost": cost,
        "per_run_cost": cost / len(records),
        "attempts": sum(int(r.get("attempt", 0)) for r in records),
        "human_needed": sum(1 for r in records if r.get("needs_human")),
    }


def print_report(stats: dict[str, Any]) -> None:
    print("=" * 64)
    if stats["n"] == 0:
        print("没有 trace 数据。先跑几次并落盘：")
        print("  python -m src.cli.run_graph --json-out reports/traces/run01.json")
        print("=" * 64)
        return

    print(f"运行次数 {stats['n']}　平均稿数 {stats['attempts'] / stats['n']:.2f}　"
          f"转人工 {stats['human_needed']}/{stats['n']}")
    print(f"\n总耗时（实测）  均值 {stats['mean_ms'] / 1000:.1f}s　"
          f"中位 {stats['median_ms'] / 1000:.1f}s　p95 {stats['p95_ms'] / 1000:.1f}s")
    print("\n节点耗时占比（实测）")
    for name, slot in sorted(stats["by_node"].items(), key=lambda kv: -kv[1]["ms"]):
        print(f"  {name:<10s} 调用 {int(slot['calls']):>3d} 次　"
              f"{slot['ms'] / 1000:>7.1f}s　{slot['share']:>6.1%}")

    print("\n估算 tokens（字符数 ÷ chars-per-token，非账单）")
    print(f"  判定  输入 {stats['judge_tokens'][0]:>9.0f}　输出 {stats['judge_tokens'][1]:>8.0f}")
    print(f"  生成  输入 {stats['gen_tokens'][0]:>9.0f}　输出 {stats['gen_tokens'][1]:>8.0f}")
    print(f"\n估算成本  单次 {stats['per_run_cost']:.4f} 元　合计 {stats['total_cost']:.4f} 元")
    print("=" * 64)
    print("口径：延迟实测、tokens 估算。价格用 --judge-price / --gen-price 按实际模型改。")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="成本 / 延迟汇总")
    parser.add_argument("--dir", default=str(DEFAULT_DIR), help="trace 目录")
    parser.add_argument("--chars-per-token", type=float, default=CHARS_PER_TOKEN)
    parser.add_argument("--judge-price", type=_parse_price, default=DEFAULT_JUDGE_PRICE)
    parser.add_argument("--gen-price", type=_parse_price, default=DEFAULT_GEN_PRICE)
    args = parser.parse_args(argv)

    records = load_records(Path(args.dir))
    print_report(
        summarise(records, args.chars_per_token, args.judge_price, args.gen_price)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
