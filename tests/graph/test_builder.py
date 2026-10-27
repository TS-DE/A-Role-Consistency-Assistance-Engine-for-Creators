"""状态图端到端单测（假模型，不联网）。需要已安装 langgraph。

跑法：python -m tests.graph.test_builder
"""

from __future__ import annotations

from src.graph.builder import build_graph
from src.graph.state import new_state
from src.judge import evaluator as evaluator_module
from src.judge.chat_model import ChatModel

evaluator_module.CALL_GAP = 0.0
evaluator_module.BACKOFF_BASE = 0.0
evaluator_module.BACKOFF_CAP = 0.0
evaluator_module.MAX_CONSECUTIVE_FAILURES = 100

DRAFT = "You will not last the night, Watson."
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
    """靠提示词区分"生成"与"判定"两种请求，各返回不同内容。"""

    def __init__(self, judge_reply: str) -> None:
        self.judge_reply = judge_reply
        self.gen_calls = 0
        self.judge_calls = 0

    def complete(self, messages: list[dict]) -> str:
        system = messages[0]["content"]
        if "判定器" in system:
            self.judge_calls += 1
            return self.judge_reply
        self.gen_calls += 1
        return DRAFT


def test_clean_draft_reaches_end_in_one_pass() -> None:
    model = SplitModel(CLEAN)
    graph = build_graph(SPEC, model, model)
    out = graph.invoke(new_state("华生想再去守一夜"))
    assert out["score"] == 2
    assert out["attempt"] == 1
    assert out["needs_human"] is False
    assert out["final"] == DRAFT, "通过时必须把草稿封成 final（否则 CLI 拿到空字符串）"
    assert model.gen_calls == 1 and model.judge_calls == 2, "一轮 = 1 次生成 + 每条 trait 一次判定"


def test_persistent_drift_rewrites_then_goes_human() -> None:
    model = SplitModel(SOFT_HIT)
    graph = build_graph(SPEC, model, model, max_attempts=3)
    out = graph.invoke(new_state("华生想再去守一夜"))
    assert out["score"] == 1, "每轮都判 1（drift）"
    assert out["attempt"] == 3, "打满 3 稿"
    assert out["needs_human"] is True, "打回用尽必须转人工"
    assert model.gen_calls == 3
    nodes = [entry["node"] for entry in out["trace"]]
    assert nodes.count("rewrite") == 2, "前两稿打回，第三稿转人工"


def test_rewrite_notes_are_consumed_by_next_generation() -> None:
    model = SplitModel(SOFT_HIT)
    graph = build_graph(SPEC, model, model, max_attempts=2)
    out = graph.invoke(new_state("华生想再去守一夜"))
    # 最后一稿生成时，违规清单应已被 rewrite 节点写回、再被生成节点消费掉
    assert out["rewrite_notes"] == []
    assert any(entry["node"] == "rewrite" for entry in out["trace"])


def main() -> int:
    try:
        import langgraph  # noqa: F401
    except ImportError:
        print("跳过：未安装 langgraph，先跑 conda install langgraph")
        return 0
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"test_builder OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
