"""ChatModel 的第二个实现：走 LangChain 的 ChatOpenAI。

为什么要多一个实现，而不是把 urllib 那版换掉：

1. **LangSmith 只认 LangChain/LangGraph 的 runnable。** 我们现在的判定调用是裸 urllib，
   在 LangSmith 里只会看到节点级的 span，看不到 prompt、回复、token 用量 ——
   那恰好是排查"判定为什么不一致"最需要的三样东西。
2. **验证了 DIP 不是口号。** 换后端只新增一个子类，编排层、节点、评测脚本一行没改。
3. 顺带满足"项目要真的用到 LangChain"这条要求 —— 不是装饰，是承重的。

两个实现的取舍：
    urllib 版：零依赖、启动快、出错信息直白 → 适合评测脚本（要跑几百次、要盯失败率）
    LangChain 版：可观测、可换服务商、自带重试 → 适合演示与排查
用 `MODEL_BACKEND=urllib|langchain` 切换，默认 urllib。
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.judge.chat_model import ChatModel
from src.judge.constants import DEFAULT_RETRIES, DEFAULT_TIMEOUT
from src.judge.env_loader import EnvLoader

_ROLE_MAP = {"system": SystemMessage, "user": HumanMessage}


class LangChainChatModel(ChatModel):
    """把 messages 交给 LangChain 的 ChatOpenAI 发出去。

    chat 参数用于注入假客户端做离线测试（不联网也能验证消息转换）。
    """

    def __init__(
        self,
        model: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.0,
        chat: Any | None = None,
    ) -> None:
        self._model = model
        self._chat = chat or ChatOpenAI(
            model=model,
            base_url=base_url or EnvLoader.get("JUDGE_BASE_URL", "LLM_BASE_URL") or "https://api.deepseek.com/v1",
            api_key=api_key or EnvLoader.get("JUDGE_API_KEY", "LLM_API_KEY"),
            temperature=temperature,
            timeout=DEFAULT_TIMEOUT,
            max_retries=DEFAULT_RETRIES,
        )

    @property
    def model(self) -> str:
        return self._model

    def complete(self, messages: list[dict]) -> str:
        converted: list[BaseMessage] = [
            _ROLE_MAP.get(str(m.get("role", "user")), HumanMessage)(content=str(m.get("content", "")))
            for m in messages
        ]
        response = self._chat.invoke(converted)
        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        return "".join(str(part) for part in content)
