"""ScoreAggregator 的离线单测（不联网）。

跑法：python -m tests.judge.test_aggregator
"""

from src.judge.aggregator import ScoreAggregator
from src.judge.constants import SCORE_DRIFT, SCORE_OOC, SCORE_PASS

AGG = ScoreAggregator()


def _result(trait: str, severity: str, quotes: list[str]) -> dict:
    return {"trait": trait, "severity": severity, "hits": [{"quote": q} for q in quotes]}


def test_hard_hit_is_zero() -> None:
    results = [{"trait": "era_consistency", "severity": "hard",
                "hits": [{"quote": "DNA", "severity": "hard"}]}]
    assert AGG.score(results, "Run a DNA test on the glass.")["score"] == SCORE_OOC


def test_two_soft_traits_is_zero() -> None:
    text = "You will not leave this house. I forbid it."
    results = [_result("watson_rapport", "soft", ["You will not leave this house."]),
               _result("voice_register", "soft", ["I forbid it."])]
    assert AGG.score(results, text)["score"] == SCORE_OOC


def test_one_soft_trait_is_drift() -> None:
    text = "You will not last the night, Watson. Go to bed."
    results = [_result("emotional_restraint", "soft",
                       ["You will not last the night, Watson.", "Go to bed."])]
    assert AGG.score(results, text)["score"] == SCORE_DRIFT, "同一 trait 多处只计 1 条"


def test_same_sentence_two_traits_count_once() -> None:
    text = "Oh, how dreadful for poor Lestrade! One does feel for the man."
    results = [_result("voice_register", "soft", ["Oh, how dreadful for poor Lestrade!"]),
               _result("emotional_restraint", "soft", [text])]
    assert AGG.score(results, text)["score"] == SCORE_DRIFT, "同一句被两个 trait 各截一段，只计 1 条"


def test_cross_sentence_counts_twice() -> None:
    text = "You are not going. Your heart would give out. I forbid it."
    results = [_result("watson_rapport", "soft", ["Your heart would give out."]),
               _result("voice_register", "soft", ["I forbid it."])]
    assert AGG.score(results, text)["score"] == SCORE_OOC, "跨句的两处漂移应计 2 条"


def test_unlocatable_quote_is_not_merged() -> None:
    results = [_result("a", "soft", ["not in text"]), _result("b", "soft", ["also missing"])]
    assert AGG.score(results, "")["score"] == SCORE_OOC, "定位不到就不去重，宁可多计"


def test_no_hits_is_pass() -> None:
    assert AGG.score([_result("a", "soft", [])], "Go to bed, Watson.")["score"] == SCORE_PASS


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"test_aggregator OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
