"""路由决策的离线单测（纯函数，不联网）。

跑法：python -m tests.graph.test_routing
"""

from src.graph.routing import HUMAN, PASS, REWRITE, decide, explain

MAX = 3


def test_pass_goes_out() -> None:
    assert decide(2, 1, False, MAX) == PASS


def test_hard_violation_rewrites() -> None:
    assert decide(0, 1, False, MAX) == REWRITE


def test_drift_also_rewrites() -> None:
    assert decide(1, 1, False, MAX) == REWRITE, "score=1 也要打回（作者决定）"


def test_exhausted_budget_goes_human() -> None:
    assert decide(1, 3, False, MAX) == HUMAN
    assert decide(0, 3, False, MAX) == HUMAN


def test_incomplete_goes_human_immediately() -> None:
    assert decide(-1, 1, True, MAX) == HUMAN, "未完成必须立刻转人工"
    assert decide(2, 1, True, MAX) == HUMAN, "即使分数是 2，未完成也不许放行"


def test_incomplete_beats_exhaustion() -> None:
    assert decide(-1, 9, True, MAX) == HUMAN


def test_explain_mentions_incomplete_reason() -> None:
    text = explain(HUMAN, -1, 1, True)
    assert "未完成" in text and "死循环" in text


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"test_routing OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
