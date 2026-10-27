"""成本/延迟汇总的离线单测（构造记录，不读文件）。

跑法：python -m tests.cli.test_cost_report
"""

from __future__ import annotations

from src.cli.eval.cost_report import summarise


def _record(total_ms: int, nodes: list[dict], attempt: int = 1) -> dict:
    return {"scene": "s", "attempt": attempt, "total_ms": total_ms, "nodes": nodes}


GEN = {"node": "generate", "ms": 4000, "chars": 1200, "prompt_chars": 3000}
VER = {"node": "verify", "ms": 56000, "prompt_chars": 16000, "reply_chars": 2400}


def test_empty_records() -> None:
    assert summarise([])["n"] == 0


def test_latency_stats_and_node_share() -> None:
    stats = summarise([_record(60000, [GEN, VER]), _record(60000, [GEN, VER])])
    assert stats["n"] == 2
    assert stats["mean_ms"] == 60000
    assert stats["median_ms"] == 60000
    shares = [slot["share"] for slot in stats["by_node"].values()]
    assert abs(sum(shares) - 1.0) < 1e-9, "节点占比之和必须为 1（分母取节点耗时之和）"
    assert stats["by_node"]["verify"]["ms"] > stats["by_node"]["generate"]["ms"]


def test_token_estimation_separates_judge_and_generator() -> None:
    stats = summarise([_record(60000, [GEN, VER])], chars_per_token=3.0)
    judge_in, judge_out = stats["judge_tokens"]
    gen_in, gen_out = stats["gen_tokens"]
    assert round(judge_in) == round(16000 / 3)
    assert round(judge_out) == round(2400 / 3)
    assert round(gen_in) == round(3000 / 3)
    assert round(gen_out) == round(1200 / 3)


def test_cost_uses_separate_prices() -> None:
    stats = summarise(
        [_record(60000, [GEN, VER])],
        chars_per_token=3.0,
        judge_price=(1.0, 3.0),
        gen_price=(2.0, 6.0),
    )
    expected = (
        (16000 / 3) * 1.0 + (2400 / 3) * 3.0 + (3000 / 3) * 2.0 + (1200 / 3) * 6.0
    ) / 1_000_000
    assert abs(stats["total_cost"] - expected) < 1e-12
    assert abs(stats["per_run_cost"] - expected) < 1e-12


def test_p95_uses_linear_interpolation() -> None:
    """样本少时 p95 接近最大值；这里刻意验证插值结果，防止以后有人把算法改掉。"""
    stats = summarise([_record(1000, [GEN]), _record(9000, [GEN]), _record(5000, [GEN])])
    assert stats["p95_ms"] == 8600


def test_counts_attempts_and_human_escalation() -> None:
    record = _record(1000, [GEN], attempt=3)
    record["needs_human"] = True
    stats = summarise([record])
    assert stats["attempts"] == 3
    assert stats["human_needed"] == 1


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"test_cost_report OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
