"""LangChainChatModel 的离线单测（注入假 chat，不联网）。

跑法：python -m tests.judge.test_langchain_model
"""

from __future__ import annotations

from src.judge.langchain_model import LangChainChatModel


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChat:
    """记录收到的 LangChain 消息对象，返回固定文本。"""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.seen: list = []

    def invoke(self, messages):  # noqa: ANN001
        self.seen = messages
        return _FakeResponse(self.reply)


MESSAGES = [
    {"role": "system", "content": "你是判定器"},
    {"role": "user", "content": "请判这一句"},
]


def test_converts_roles_to_langchain_messages() -> None:
    fake = _FakeChat('{"hits": []}')
    model = LangChainChatModel("stub-model", chat=fake)
    model.complete(MESSAGES)

    assert len(fake.seen) == 2
    assert fake.seen[0].type == "system" and fake.seen[0].content == "你是判定器"
    assert fake.seen[1].type == "human" and fake.seen[1].content == "请判这一句"


def test_returns_string_content() -> None:
    model = LangChainChatModel("stub-model", chat=_FakeChat("ANSWER"))
    assert model.complete(MESSAGES) == "ANSWER"


def test_exposes_model_name_for_reporting() -> None:
    model = LangChainChatModel("qwen3.8-flash", chat=_FakeChat("x"))
    assert model.model == "qwen3.8-flash", "结果文件要记录模型名，换模型等于换仪器"


def test_unknown_role_falls_back_to_human() -> None:
    fake = _FakeChat("x")
    LangChainChatModel("m", chat=fake).complete([{"role": "tool", "content": "?"}])
    assert fake.seen[0].type == "human"


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"test_langchain_model OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
