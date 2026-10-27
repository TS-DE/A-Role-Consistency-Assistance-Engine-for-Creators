"""生成节点：把「人设 + 上一轮违规清单 + 用户输入」变成一段福尔摩斯的回复。

它是整张图里唯一"创作"的地方，所以读的状态最少：

    state["user_input"]      创作者给的情境
    state["rewrite_notes"]   上一轮被打回的理由（第一次为空）

它只写两个字段：

    state["draft"]           新草稿
    state["attempt"]         第几次生成（+1）

一个刻意的取舍：**生成节点不读那 8 条完整规则**。
如果把全部 anti_pattern 都塞进生成提示词，模型会开始"背规则"——写出来的每句都在
躲检查，结果是一个没有趣味的、扁平的福尔摩斯。生成只需要知道"我是谁"和
"上次哪句被打回了"，判定交给校验节点。
"""

from __future__ import annotations

from typing import Any

from src.graph.state import GraphState, trace_entry
from src.judge.chat_model import ChatModel

SYSTEM_PROMPT = """You are Sherlock Holmes of 221B Baker Street, London, in the 1890s.
Write ONLY his reply — no narration of your own, no explanation, no quotation marks around the whole text.

Style rules:
- Cold, precise, short sentences. Earnest for facts, indifferent to feelings.
- British English (colour, recognise, towards, whilst, got — never gotten).
- Never modern vocabulary: no DNA, no CCTV, no telephone calls of convenience, no data systems.
  (The word "data" itself is period-appropriate; machinery is not.)
- No exclamation marks. No warmth, no comfort, no phrases like "I understand your pain".
- You may be dryly sarcastic about Scotland Yard, criminals, or the client's lies.
- Never glorify yourself, never seek credit, never court the newspapers."""


class GenerateNode:
    """一次生成 = 一次模型调用，无状态（状态全在 State 里）。"""

    def __init__(self, spec: dict[str, Any], model: ChatModel, temperature: float = 0.8) -> None:
        self._spec = spec
        self._model = model
        self._temperature = temperature

    def __call__(self, state: GraphState) -> dict[str, Any]:
        """LangGraph 节点契约：接收整个 State，返回要合并进去的那部分字段。"""
        messages = self._build_messages(state)
        draft = self._model.complete(messages).strip().strip('"').strip()

        attempt = int(state.get("attempt", 0)) + 1
        return {
            "draft": draft,
            "attempt": attempt,
            # 违规清单已经被用掉了，清空避免下一轮重复回灌
            "rewrite_notes": [],
            "trace": list(state.get("trace", [])) + [
                trace_entry("generate", {"attempt": attempt, "chars": len(draft)})
            ],
        }

    def _build_messages(self, state: GraphState) -> list[dict]:
        persona = str(self._spec.get("persona", "")).strip()
        sections = [f"# Who you are\n{persona}"]

        forbidden = self._spec.get("voice", {}).get("forbidden_en") or []
        if forbidden:
            sections.append("# Never do these\n" + "\n".join(f"- {item}" for item in forbidden))

        notes = state.get("rewrite_notes") or []
        if notes:
            # TODO(你)：现在把「命中的 pattern + 引文」原样塞回去。
            # 试着只给"违反的规则 + 该怎么改"、不给原句，看模型是否更愿意改写而不是死守原句。
            # 这是生成节点唯一值得反复调的地方，改完用回归集 E01–E08 比对。
            sections.append(
                "# Your previous draft was rejected by the consistency check\n"
                "Rewrite it. Keep the facts, drop the behaviour that was flagged:\n"
                + "\n".join(f"- {note}" for note in notes)
            )

        sections.append(f"# The scene\n{state.get('user_input', '')}")
        sections.append("# Your reply")
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "\n\n".join(sections)},
        ]
