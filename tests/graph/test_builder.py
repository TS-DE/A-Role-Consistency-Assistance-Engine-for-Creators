"""状态图端到端单测（假模型，不联网）。需要已安装 langgraph。

跑法：python -m tests.graph.test_builder
"""

from __future__ import annotations

from langgraph.types import Command

from src.graph.builder import ABANDON, ACCEPT, EDIT_PREFIX, build_graph
from src.graph.state import new_state
from src.judge import evaluator as evaluator_module
from src.judge.chat_model import ChatModel

evaluator_module.CALL_GAP = 0.0
evaluator_module.BACKOFF_BASE = 0.0
evaluator_module.BACKOFF_CAP = 0.0
evaluator_module.MAX_CONSECUTIVE_FAILURES = 100

DRAFT = "You will not last the night, Watson."
EDITED = "Your colour is poor, Watson. Go to bed; I shall take the case."
SPEC = {
    "persona": "stub 侦探",
    "not_ooc": [],
    "voice": {"forbidden_en": []},
    "_traits_by_id": {
        "emotional_restraint": {"id": "emotional_restraint", "name": "情绪克制",
                                "severity": "hard", "rule": "不得抒情"},
        "watson_rapport": {"id": "watson_rapport", "name": "与华生",
                           "severity": "soft", "rule": "不得以健康冷嘲"},
    },
}

CLEAN = '{"hits": [], "ambiguity": []}'
SOFT_HIT = ('{"hits": [{"pattern": "以对方健康作冷嘲", '
            '"quote": "You will not last the night, Watson.", "severity": "soft"}], "ambiguity": []}')


class SplitModel(ChatModel):
    """靠提示词区分"生成"与"判定"两种请求。"""

    def __init__(self, judge_reply: str) -> None:
        self.judge_reply = judge_reply
        self.gen_calls = 0
        self.judge_calls = 0

    def complete(self, messages: list[dict]) -> str:
        if "判定器" in messages[0]["content"]:
            self.judge_calls += 1
            return self.judge_reply
        self.gen_calls += 1
        return DRAFT


def _config(tag: str) -> dict:
    return {"configurable": {"thread_id": tag}}


def test_clean_draft_reaches_end_in_one_pass() -> None:
    model = SplitModel(CLEAN)
    graph = build_graph(SPEC, model, model)
    out = graph.invoke(new_state("华生想再去守一夜"), _config("pass"))

    assert out["score"] == 2
    assert out["attempt"] == 1
    assert out["needs_human"] is False
    assert out["final"] == DRAFT, "通过时必须把草稿封成 final"
    assert model.gen_calls == 1 and model.judge_calls == 2


def test_persistent_drift_interrupts_for_human() -> None:
    model = SplitModel(SOFT_HIT)
    graph = build_graph(SPEC, model, model, max_attempts=3)
    paused = graph.invoke(new_state("华生想再去守一夜"), _config("hitl"))

    assert paused.get("__interrupt__"), "打回用尽必须挂起等人，而不是自己收场"
    payload = paused["__interrupt__"][0].value
    assert payload["draft"] == DRAFT
    assert payload["score"] == 1
    assert len(payload["violated"]) >= 1, "裁决时要看到违规证据"
    assert model.gen_calls == 3, "挂起前应该已经写了 3 稿"


def test_human_accept_resumes_and_records_reason() -> None:
    model = SplitModel(SOFT_HIT)
    graph = build_graph(SPEC, model, model, max_attempts=3)
    graph.invoke(new_state("华生想再去守一夜"), _config("accept"))
    out = graph.invoke(Command(resume=ACCEPT), _config("accept"))

    assert out["needs_human"] is True
    assert out["final"] == DRAFT
    assert out["trace"][-1]["node"] == "human"
    assert out["trace"][-1]["decision"] == "accepted_by_human", "人工放行要留痕，会计入漏杀统计"


def test_human_edit_takes_priority_over_draft() -> None:
    model = SplitModel(SOFT_HIT)
    graph = build_graph(SPEC, model, model, max_attempts=3)
    graph.invoke(new_state("华生想再去守一夜"), _config("edit"))
    out = graph.invoke(Command(resume=f"{EDIT_PREFIX}{EDITED}"), _config("edit"))

    assert out["final"] == EDITED
    assert out["trace"][-1]["decision"] == "edited_by_human"


def test_human_abandon_clears_final() -> None:
    model = SplitModel(SOFT_HIT)
    graph = build_graph(SPEC, model, model, max_attempts=2)
    graph.invoke(new_state("华生想再去守一夜"), _config("abandon"))
    out = graph.invoke(Command(resume=ABANDON), _config("abandon"))

    assert out["final"] == ""
    assert out["trace"][-1]["decision"] == "abandoned"


def main() -> int:
    try:
        import langgraph  # noqa: F401
    except ImportError:
        print("跳过：未安装 langgraph")
        return 0
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"test_builder OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
