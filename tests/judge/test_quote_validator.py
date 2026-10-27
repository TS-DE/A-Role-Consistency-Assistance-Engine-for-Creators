"""QuoteValidator 的离线单测（不联网）。

跑法：python -m tests.judge.test_quote_validator
"""

from src.judge.quote_validator import QuoteValidator

VALIDATOR = QuoteValidator()
CANDIDATE = 'Go to bed, Watson. I shall take the case.'


def test_accepts_verbatim_quote() -> None:
    passed, rejected = VALIDATOR.validate([{"quote": "Go to bed, Watson."}], CANDIDATE)
    assert len(passed) == 1 and not rejected


def test_rejects_fabricated_quote() -> None:
    passed, rejected = VALIDATOR.validate([{"quote": "I forbid you to go."}], CANDIDATE)
    assert not passed and rejected[0]["_reason"] == "quote_not_in_candidate"


def test_accepts_ellipsis_joined_parts() -> None:
    passed, _ = VALIDATOR.validate(
        [{"quote": "Go to bed...I shall take the case."}], CANDIDATE
    )
    assert len(passed) == 1, "省略号连接的两段原文都应通过"


def test_normalize_is_case_insensitive() -> None:
    passed, _ = VALIDATOR.validate([{"quote": "go to bed, WATSON."}], CANDIDATE)
    assert len(passed) == 1


def test_normalize_maps_curly_quotes() -> None:
    assert VALIDATOR.normalize("“hi”") == '"hi"'


def test_sentence_of_returns_full_sentence() -> None:
    haystack = VALIDATOR.normalize("First one. Second one here! Third?")
    start = haystack.find("second")
    begin, end = VALIDATOR.sentence_of(haystack, start)
    assert haystack[begin:end].strip() == "second one here!"


def test_sentence_of_missing_position() -> None:
    assert VALIDATOR.sentence_of("abc", -1) == (-1, -1)


def test_span_of_missing_quote() -> None:
    assert VALIDATOR.span_of(VALIDATOR.normalize("abc"), "zzz") == (-1, -1)


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"test_quote_validator OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
