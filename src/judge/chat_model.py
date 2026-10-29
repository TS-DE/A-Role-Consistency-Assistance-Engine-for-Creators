"""模型调用的抽象与实现。

高层（编排层）只依赖 ChatModel 这个抽象，不 import urllib ——
换服务商只加一个子类，不动业务代码（OCP + DIP）。
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

from src.judge.constants import (
    BACKOFF_BASE,
    BACKOFF_CAP,
    DEFAULT_RETRIES,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT,
    PREFLIGHT_PROMPT,
)
from src.judge.env_loader import EnvLoader


class ChatModelError(RuntimeError):
    """调用失败：带上最后一次错误，由上层决定是否中止整批。"""


class ChatModel(ABC):
    """一次问答能力的抽象。"""

    @abstractmethod
    def complete(self, messages: list[dict]) -> str:
        """给定 messages，返回模型输出的纯文本。"""

    def preflight(self) -> None:
        """起跑前的连通性探测。

        没有这一步，网络不通时会安静地重试一整个小时 —— 这是实际踩过的坑：
        整批 136 次调用，第 1 条候选的 8 条规则全部超时，屏幕上一个字都没有。
        探测一次只要一秒，失败立刻抛。
        """
        self.complete([{"role": "user", "content": PREFLIGHT_PROMPT}])


class OpenAICompatChatModel(ChatModel):
    """OpenAI 兼容的 /chat/completions 实现（DeepSeek、通义、vLLM 等都兼容）。"""

    def __init__(
        self,
        model: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        self._model = model
        # 2026-10-29 实测修正：此前请求体把 temperature 硬编码 0.0，本类没有该参数，
        # LLM_TEMPERATURE/JUDGE_TEMPERATURE 两个 env 键从未生效（"死键"）。现在接上，
        # 兜底默认仍为 0.0 —— 与接线前的实际行为一致，不改变既有输出分布。
        self._temperature = temperature
        self._base_url = (
            base_url
            or EnvLoader.get("JUDGE_BASE_URL", "LLM_BASE_URL")
            or "https://api.deepseek.com/v1"
        ).rstrip("/")
        self._api_key = api_key or EnvLoader.get("JUDGE_API_KEY", "LLM_API_KEY")
        if not self._api_key:
            raise ChatModelError("缺少 API Key：请在 .env 里设 JUDGE_API_KEY（或 LLM_API_KEY）")
        self._timeout = timeout
        self._retries = retries
        self._json_mode = True

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: list[dict]) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
        }
        if self._json_mode:
            payload["response_format"] = {"type": "json_object"}
        return self._request_with_retry(payload)

    # ── 内部 ────────────────────────────────────────────────
    def _request_with_retry(self, payload: dict[str, Any]) -> str:
        last_error = "unknown"
        for attempt in range(self._retries + 1):
            try:
                return self._post(payload)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:300]
                if exc.code == 400 and "response_format" in payload:
                    payload.pop("response_format")   # 服务商不支持 JSON 模式
                    self._json_mode = False
                    continue
                last_error = f"HTTP {exc.code}: {detail}"
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(min(BACKOFF_CAP, BACKOFF_BASE * (2 ** attempt)))
        raise ChatModelError(f"模型调用失败：{last_error}")

    def _post(self, payload: dict[str, Any]) -> str:
        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]


# ── 工厂：模型构造只在这一个文件里，CLI 不许自己拼 env ──────────
def _backend() -> str:
    """后端选择：urllib（默认，评测用）或 langchain（可观测，演示/排查用）。"""
    return (EnvLoader.get("MODEL_BACKEND") or "urllib").lower()


def _env_temperature(name: str) -> float:
    """从 env 读采样温度。此前 LLM_/JUDGE_TEMPERATURE 两键从未生效（请求体硬编码 0.0），
    2026-10-29 接线后生效；未配置/空串一律兜底 DEFAULT_TEMPERATURE=0.0（与旧实际行为一致）。
    配置了但不是数字 → 显式报错，不静默兜底：静默吞配置错误会让"改了没生效"重演一次。
    """
    raw = EnvLoader.get(name)
    if raw is None or not raw.strip():
        return DEFAULT_TEMPERATURE
    try:
        return float(raw)
    except ValueError as exc:
        raise ChatModelError(f"{name} 不是合法数字：{raw!r}（留空则用默认 {DEFAULT_TEMPERATURE}）") from exc


def _make(model: str, base_url: str | None, api_key: str | None, temperature: float) -> ChatModel:
    if _backend() == "langchain":
        # 延迟 import：避免 chat_model ←→ langchain_model 循环依赖
        from src.judge.langchain_model import LangChainChatModel

        return LangChainChatModel(
            model, base_url=base_url, api_key=api_key, temperature=temperature
        )
    return OpenAICompatChatModel(
        model, base_url=base_url, api_key=api_key, timeout=DEFAULT_TIMEOUT,
        retries=DEFAULT_RETRIES, temperature=temperature,
    )


def build_generator_model() -> ChatModel:
    """生成侧：优先 LLM_*（写台词用文笔更好的模型）。"""
    model = EnvLoader.get("LLM_MODEL", "JUDGE_MODEL")
    if not model:
        raise ChatModelError("未配置 LLM_MODEL / JUDGE_MODEL")
    return _make(
        model,
        EnvLoader.get("LLM_BASE_URL", "JUDGE_BASE_URL"),
        EnvLoader.get("LLM_API_KEY", "JUDGE_API_KEY"),
        # 兜底从 0.8 改为 0.0：接线前的实际生效值一直是 0.0（请求体硬编码），
        # 兜底必须等于旧实际值才算"行为不变"；想要 0.8 由 .env 显式声明。
        temperature=_env_temperature("LLM_TEMPERATURE"),
    )


def build_judge_model() -> ChatModel:
    """判定侧：优先 JUDGE_*（判定用便宜、够稳、够快的模型）。"""
    model = EnvLoader.get("JUDGE_MODEL", "LLM_MODEL")
    if not model:
        raise ChatModelError("未配置 JUDGE_MODEL / LLM_MODEL")
    return _make(
        model,
        EnvLoader.get("JUDGE_BASE_URL", "LLM_BASE_URL"),
        EnvLoader.get("JUDGE_API_KEY", "LLM_API_KEY"),
        temperature=_env_temperature("JUDGE_TEMPERATURE"),
    )
