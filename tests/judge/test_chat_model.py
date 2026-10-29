"""chat_model 离线用例：temperature 接线（任务 20 · 任务 4）。

跑法：python -m tests.judge.test_chat_model
背景：2026-10-29 实测发现 urllib 后端把请求体 temperature 硬编码 0.0，
LLM_/JUDGE_TEMPERATURE 两个 env 键从未生效（"死键"）。本组用例锁死接线结果：
兜底=0.0（与旧实际行为一致）、env 值真的进请求体、非法值显式报错。
不联网：实例属性替换 _post，录下"本应发出"的请求体本身。
"""

from __future__ import annotations

import os

from src.judge.chat_model import (
    ChatModelError,
    OpenAICompatChatModel,
    build_generator_model,
    build_judge_model,
)


def _capturing_model(**kwargs) -> tuple[OpenAICompatChatModel, list]:
    model = OpenAICompatChatModel("test-model", base_url="http://x.invalid/v1",
                                  api_key="k", **kwargs)
    sent: list[dict] = []
    model._post = lambda payload: sent.append(payload) or "ok"
    return model, sent


def test_default_temperature_is_zero() -> None:
    model, sent = _capturing_model()
    model.complete([{"role": "user", "content": "hi"}])
    assert sent[0]["temperature"] == 0.0, "兜底必须等于接线前的实际生效值，否则就不是行为不变"


def test_explicit_temperature_reaches_payload() -> None:
    model, sent = _capturing_model(temperature=0.9)
    model.complete([{"role": "user", "content": "hi"}])
    assert sent[0]["temperature"] == 0.9


def test_factories_read_env_temperature() -> None:
    keys = ("LLM_MODEL", "LLM_TEMPERATURE", "JUDGE_MODEL", "JUDGE_TEMPERATURE",
            "MODEL_BACKEND", "LLM_API_KEY", "JUDGE_API_KEY")
    old = {k: os.environ.get(k) for k in keys}
    try:
        # 构造期只查 key 非空、不联网（工厂测试验的是温度接线，请求根本发不出去）
        for k in ("LLM_MODEL", "JUDGE_MODEL"):
            os.environ[k] = "test-model"
        for k in ("LLM_API_KEY", "JUDGE_API_KEY"):
            os.environ[k] = "test-key-offline"
        os.environ["MODEL_BACKEND"] = "urllib"
        os.environ["LLM_TEMPERATURE"] = "0.9"
        os.environ["JUDGE_TEMPERATURE"] = "0.0"
        assert build_generator_model()._temperature == 0.9, "生成侧要读 LLM_TEMPERATURE"
        assert build_judge_model()._temperature == 0.0, "判定侧要读 JUDGE_TEMPERATURE"

        os.environ["LLM_TEMPERATURE"] = ""
        assert build_generator_model()._temperature == 0.0, "空串按未配置处理，兜底 0.0"

        os.environ["LLM_TEMPERATURE"] = "abc"
        try:
            build_generator_model()
            raise AssertionError("非法温度必须显式报错，不许静默兜底")
        except ChatModelError:
            pass
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"test_chat_model OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
