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
    ) -> None:
        self._model = model
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
            "temperature": 0.0,
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
