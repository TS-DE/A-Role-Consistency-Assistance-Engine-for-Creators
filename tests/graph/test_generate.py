"""GenerateNode 的离线单测（假模型，不联网）。

跑法：python -m tests.graph.test_generate
"""

from src.graph.nodes.generate import GenerateNode
from src.graph.state import new_state, summarize_hits
from src.judge.chat_model import ChatModel

SPEC = {
    "persona": "贝克街 221B 的咨询侦探。语气冷、句子短。",
    "voice": {"forbidden_en": ["American-only vocabulary (gotten, fall = autumn)", "Exclamation marks"]},
}

SCENE = "华生说他想再去现场守一夜。"


class RecordingModel(ChatModel):
    """记录收到的 messages，返回固定文本。用于验证提示词拼装，不触碰网络。"""

    def __init__(self, reply: str = "\"Then we go at first light.\"") -> None:
        self.reply = reply
        self.seen: list[list[dict]] = []

    def complete(self, messages: list[dict]) -> str:
        self.seen.append(messages)
        return self.reply


def test_writes_draft_and_increments_attempt() -> None:
    model = RecordingModel()
    node = GenerateNode(SPEC, model)
    out = node(new_state(SCENE))
    assert out["draft"] == "Then we go at first light.", "应去掉整体包裹的引号"
    assert out["attempt"] == 1
    assert out["rewrite_notes"] == [], "违规清单用掉后要清空"
    assert out["trace"][0]["node"] == "generate"


def test_prompt_carries_persona_scene_and_forbidden() -> None:
    model = RecordingModel()
    GenerateNode(SPEC, model)(new_state(SCENE))
    prompt = model.seen[0][1]["content"]
    assert "221B" in prompt, "人设必须进提示词"
    assert SCENE in prompt, "场景必须进提示词"
    assert "gotten" in prompt, "声音禁区必须进提示词"
    assert "rejected" not in prompt, "第一轮没有违规清单，不该出现改写区块"


def test_rewrite_notes_are_injected_and_consumed() -> None:
    model = RecordingModel()
    node = GenerateNode(SPEC, model)
    state = new_state(SCENE)
    state["attempt"] = 1
    state["rewrite_notes"] = ['[emotional_restraint] 抒情式共情 ← "Let it out, old fellow."']

    out = node(state)
    prompt = model.seen[0][1]["content"]
    assert "rejected" in prompt and "Let it out, old fellow." in prompt
    assert out["attempt"] == 2
    assert out["rewrite_notes"] == []


def test_summarize_hits_flattens_verdicts() -> None:
    verdicts = [
        {"trait": "emotional_restraint",
         "hits": [{"pattern": "肢体温情", "quote": "took Watson's hand"}]},
        {"trait": "era_consistency", "hits": [{"pattern": "现代词汇", "quote": "DNA"}]},
    ]
    notes = summarize_hits(verdicts)
    assert len(notes) == 2
    assert "emotional_restraint" in notes[0] and "DNA" in notes[1]


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"test_generate OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
