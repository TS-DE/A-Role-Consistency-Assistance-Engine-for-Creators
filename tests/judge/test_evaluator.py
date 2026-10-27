"""TraitEvaluator 的补跑逻辑单测（用假模型，不联网）。

跑法：python -m tests.judge.test_evaluator
"""

from src.judge import evaluator as evaluator_module
from src.judge.chat_model import ChatModel
from src.judge.evaluator import TraitEvaluator

# 测试里不要真睡；默认关掉熔断，需要它的用例自己开
evaluator_module.CALL_GAP = 0.0
evaluator_module.BACKOFF_BASE = 0.0
evaluator_module.BACKOFF_CAP = 0.0
evaluator_module.MAX_CONSECUTIVE_FAILURES = 100

SPEC = {"persona": "stub", "not_ooc": [], "traits": []}
TRAITS = {"t": {"id": "t", "name": "stub", "severity": "soft", "rule": "stub rule"}}
EMPTY_HITS = '{"hits": [], "ambiguity": []}'
CANDIDATE = {"id": "X", "text": "Go to bed, Watson.", "trait": "t"}


class ScriptedModel(ChatModel):
    """按脚本失败 N 次后返回空命中。用来验证补跑逻辑，不触碰网络。"""

    def __init__(self, failures: int) -> None:
        self.failures_left = failures
        self.calls = 0

    def complete(self, messages: list[dict]) -> str:
        self.calls += 1
        if self.failures_left > 0:
            self.failures_left -= 1
            raise TimeoutError("scripted timeout")
        return EMPTY_HITS


def test_recovers_after_transient_failure() -> None:
    model = ScriptedModel(failures=1)
    aggregate, results, failed = TraitEvaluator(SPEC, model).judge_case(
        CANDIDATE, TRAITS, fanout=False
    )
    assert not failed, "一次瞬时失败应被补跑救回来"
    assert len(results) == 1
    assert aggregate["score"] == 2
    assert model.calls == 2, "只补跑失败的那一条，不重跑已成功的"


def test_gives_up_after_missing_retries() -> None:
    model = ScriptedModel(failures=99)
    aggregate, results, failed = TraitEvaluator(SPEC, model).judge_case(
        CANDIDATE, TRAITS, fanout=False, missing_retries=1
    )
    assert failed and not results, "补跑用尽仍失败，必须报失败而不是给个分"
    assert model.calls == 2, "missing_retries=1 表示首轮 + 1 轮补跑"
    assert aggregate["score"] == 2, "空结果聚合为 2 分，但上层会按 failed 标记 incomplete"


def test_consecutive_failures_abort() -> None:
    from src.judge.evaluator import JudgeAborted

    model = ScriptedModel(failures=999)
    evaluator = TraitEvaluator(SPEC, model)
    original = evaluator_module.MAX_CONSECUTIVE_FAILURES
    evaluator_module.MAX_CONSECUTIVE_FAILURES = 2
    try:
        evaluator.judge_case(CANDIDATE, TRAITS, fanout=False, missing_retries=3)
    except JudgeAborted:
        pass
    else:
        raise AssertionError("连续失败应抛 JudgeAborted")
    finally:
        evaluator_module.MAX_CONSECUTIVE_FAILURES = original


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"test_evaluator OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
