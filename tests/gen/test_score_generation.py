"""score_generation 汇总逻辑的离线单测（构造内存行，不读文件）。

跑法：python -m tests.gen.test_score_generation
"""

from __future__ import annotations

from src.cli.score_generation import summarise


def _row(sample: str, attempt: int, human: int, judge: int = 2,
         checks: tuple[int, int, int] = (1, 1, 1)) -> dict:
    return {
        "sample_id": sample,
        "scene_id": "s",
        "attempt": attempt,
        "source": "loop_generated",
        "judge_score": judge,
        "human_score": human,
        "checks": {"period_voice": checks[0], "on_scene": checks[1], "no_anachronism": checks[2]},
        "notes": "",
    }


def test_empty_rows_returns_zero() -> None:
    assert summarise([])["n"] == 0


def test_takes_first_and_later_drafts_for_gain() -> None:
    """改写增益是核心指标：第 2 稿比首稿高多少。"""
    stats = summarise([_row("S01", 1, 2), _row("S01", 2, 4), _row("S02", 1, 3), _row("S02", 2, 5)])
    assert stats["first_mean"] == 2.5
    assert stats["later_mean"] == 4.5
    assert stats["rewrite_gain"] == 2.0


def test_usable_rate_counts_four_and_above() -> None:
    stats = summarise([_row("S01", 1, 5), _row("S02", 1, 4), _row("S03", 1, 3), _row("S04", 1, 1)])
    assert stats["usable_rate"] == 0.5


def test_flaw_rate_counts_any_failed_check() -> None:
    rows = [_row("S01", 1, 5), _row("S02", 1, 2, checks=(0, 1, 1)), _row("S03", 1, 2, checks=(1, 0, 1))]
    assert summarise(rows)["flaw_rate"] == 2 / 3


def test_judge_grouping_shows_direction() -> None:
    rows = [
        _row("S01", 1, 1, judge=0),
        _row("S02", 1, 4, judge=2),
        _row("S03", 1, 5, judge=2),
    ]
    stats = summarise(rows)
    assert stats["by_judge"]["0"] == 1.0
    assert stats["by_judge"]["2"] == 4.5, "判定器判 2 的稿子，人工均分也该高"


def test_missing_checks_are_counted_not_hidden() -> None:
    stats = summarise([_row("S01", 1, 4, checks=(-1, 1, 1))])
    assert stats["incomplete_checks"] == 1


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"test_score_generation OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
