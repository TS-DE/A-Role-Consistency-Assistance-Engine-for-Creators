"""VerifyNode 的离线单测（假模型，不联网）。

跑法：python -m tests.graph.test_verify
"""

from src.graph.nodes.verify import INCOMPLETE_SCORE, VerifyNode
from src.graph.state import new_state
from src.judge import evaluator as evaluator_module
from src.judge.chat_model import ChatModel

# 测试里不要真睡
evaluator_module.CALL_GAP = 0.0
evaluator_module.BACKOFF_BASE = 0.0
evaluator_module.BACKOFF_CAP = 0.0
evaluator_module.MAX_CONSECUTIVE_FAILURES = 100

DRAFT = "You will not last the night, Watson. Go to bed."
SPEC = {
    "persona": "stub",
    "not_ooc": [],
    "_traits_by_id": {
        "emotional_restraint": {"id": "emotional_restraint", "name": "情绪克制",
                                "severity": "hard", "rule": "不得抒情安慰"},
        "watson_rapport": {"id": "watson_rapport", "name": "与华生",
                           "severity": "soft", "rule": "不得以健康冷嘲"},
    },
}


class ScriptedModel(ChatModel):
    """按脚本返回固定 JSON 或抛错，用来验证节点接线，不触碰网络。"""

    def __init__(self, reply: str = '{"hits": [], "ambiguity": []}', fail: bool = False) -> None:
        self.reply = reply
        self.fail = fail
        self.calls = 0

    def complete(self, messages: list[dict]) -> str:
        self.calls += 1
        if self.fail:
            raise TimeoutError("scripted timeout")
        return self.reply


def _state_with_draft() -> dict:
    state = new_state("华生想再去守一夜")
    state["draft"] = DRAFT
    state["attempt"] = 1
    return state


def test_clean_draft_passes() -> None:
    out = VerifyNode(SPEC, ScriptedModel())(_state_with_draft())
    assert out["score"] == 2
    assert out["violated"] == []
    assert out["verify_incomplete"] is False
    assert out["trace"][-1]["node"] == "verify"


def test_soft_hit_becomes_drift_and_is_reported() -> None:
    reply = '{"hits": [{"pattern": "以对方健康作冷嘲", "quote": "You will not last the night, Watson.", "severity": "soft"}], "ambiguity": []}'
    out = VerifyNode(SPEC, ScriptedModel(reply))(_state_with_draft())
    assert out["score"] == 1
    assert any("You will not last the night" in note for note in out["violated"])


def test_fanout_calls_every_trait() -> None:
    model = ScriptedModel()
    VerifyNode(SPEC, model)(_state_with_draft())
    assert model.calls == 2, "两条 trait 都要判，不许只判一条"


def test_failed_call_marks_incomplete_not_pass() -> None:
    out = VerifyNode(SPEC, ScriptedModel(fail=True))(_state_with_draft())
    assert out["score"] == INCOMPLETE_SCORE
    assert out["verify_incomplete"] is True


def test_empty_draft_marks_incomplete() -> None:
    state = new_state("空")
    out = VerifyNode(SPEC, ScriptedModel())(state)
    assert out["verify_incomplete"] is True
    assert out["trace"][-1]["error"] == "empty draft"


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"test_verify OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
