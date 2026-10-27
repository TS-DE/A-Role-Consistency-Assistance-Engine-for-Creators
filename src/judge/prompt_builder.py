"""把「规格 + 一条 trait + 候选文本」拼成 messages。纯函数式，不联网。"""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """你是一名严格的「角色一致性判定器」。每次只判断一条规则（trait），
不判断其他任何东西，也不评价文笔。

【硬性约束】
1. quote 必须是候选回复里**逐字存在**的片段，一个字都不能改、不能加省略号拼接之外的重写。
   程序会做子串校验，编造的引文会被整条丢弃。
2. 每条命中必须指认它落在哪一条 anti_pattern 上（pattern 字段写该 anti_pattern 的原文）。
3. 指不出片段、或指不出 pattern 的直觉，不要算命中，写进 ambiguity。
4. **不要给分数**。你只负责举证。
5. 不要因为"角色已经拒绝了 / 已经表达了正确立场"就放过字面上的违规。字面优先于意图。
6. 宁可少报，不要编造。少报只会让召回降低；编造会让整条作废。
7. quote 尽量取**完整的一整句**（到 . / ? / ! 为止），不要只截半句。
   一句话里有两处问题才拆两条；跨了两句话一定拆两条。

【输出格式】只输出 JSON，不要任何解释文字：
{"hits": [{"pattern": "<anti_pattern 原文>", "quote": "<候选原文逐字片段>", "severity": "hard" 或 "soft"}],
 "ambiguity": ["<想报但指不出片段的理由>"]}"""


class PromptBuilder:
    """按 trait 组装判定提示词。

    not_ooc 豁免清单必须塞进去，否则"冷淡但符合人设"的回复会被误杀。
    """

    def __init__(self, spec: dict[str, Any]) -> None:
        self._spec = spec

    def build(self, candidate: str, trait: dict[str, Any]) -> list[dict]:
        blocks: list[str] = ["# 角色\n" + str(self._spec.get("persona", "")).strip()]
        blocks.append(
            "\n# 待判定的规则（只判这一条）\n"
            f"trait: {trait['id']} / {trait.get('name', '')}\n"
            f"severity: {trait['severity']}\n"
            f"rule:\n{str(trait.get('rule', '')).strip()}"
        )
        blocks.append(self._behaviours(trait))
        blocks.append(self._anti_patterns(trait))
        blocks.append(self._exemplars(trait))
        blocks.append(self._exemptions())
        blocks.append('\n# 待判定回复\n"""\n' + candidate.strip() + '\n"""')
        blocks.append("\n只输出 JSON。")
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "\n".join(b for b in blocks if b)},
        ]

    @staticmethod
    def _behaviours(trait: dict[str, Any]) -> str:
        items = trait.get("observable_behaviors") or []
        if not items:
            return ""
        return "\n符合时长这样（observable_behaviors）：\n" + "\n".join(f"- {i}" for i in items)

    @staticmethod
    def _anti_patterns(trait: dict[str, Any]) -> str:
        items = trait.get("anti_patterns") or []
        if not items:
            return ""
        lines = ["\n违反时长这样（anti_patterns）："]
        for item in items:
            lines.append(f"- [{item.get('level', 'soft')}] pattern: {item.get('pattern', '')}")
            if item.get("example_bad"):
                lines.append(f"  反例：{item['example_bad']}")
        return "\n".join(lines)

    @staticmethod
    def _exemplars(trait: dict[str, Any]) -> str:
        items = trait.get("exemplars") or []
        if not items:
            return ""
        lines = ["\n原文正例（柯南·道尔原作，用来校准『这条规则在真人笔下长什么样』）："]
        lines += [f'- "{i.get("text", "")}" —— 《{i.get("source", "")}》' for i in items]
        return "\n".join(lines)

    def _exemptions(self) -> str:
        items = self._spec.get("not_ooc") or []
        if not items:
            return ""
        return "\n# 豁免清单（下列情况不算违规，必须放行）\n" + "\n".join(f"- {i}" for i in items)
