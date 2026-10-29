"""黑板：多专家判定层的唯一写入面（设计依据 agent_docs/19 §二）。

为什么单独一个文件：BoardEntry 是"专家怎么写"与"裁决者怎么读"的双边契约，
放进一个文件才不会两边各自漂移。黑板本体就是 GraphState 上
`Annotated[list[BoardEntry], operator.add]` 这一个字段——LangGraph 的 reducer
保证同一 superstep 内的并行 append 按创建顺序确定性合并，不需要自己加锁。

写入端（TraitExpert）只追加自己的一条；读取端（Arbiter）一次看全板。
"去中心化写、集中式读"正是黑板比群聊省上下文的原因：每个专家只拿
自己的规则 + 候选文本（约 3KB），而不是 8 份别人结论。
"""

from __future__ import annotations

from typing import Any, TypedDict


class BoardEntry(TypedDict):
    """一个专家对一条 trait 的完整结论。字段全部可溯源，裁决者只信这些。"""

    trait: str               # 哪条轴（evidence_first / era_consistency ...）
    severity: str            # hard / soft —— 取自规格，不取自模型（铁律：分数不由模型给）
    hits: list[dict]         # [{pattern, quote, severity}]，quote 已过 QuoteValidator 子串校验
    invalid: list[dict]      # 被拒引文（编造/改写），是"判定器老不老实"的审计证据
    ambiguity: list          # 模型想报但指不出原文的理由
    failed: str              # 调用失败原因；空串=成功。异常写这里，绝不让它冒泡中断整张图
    prompt_chars: int        # 成本口径：实测字符数（tokens 只能估算）
    reply_chars: int
    parse_error: Any         # 原样透传 judge_trait 的 parse_error（成功=None）：不许 bool 归一，
                             # 否则 verdicts 与 simple 模式差一个 None/False，等价性断言会炸
    ms: int                  # 单轴耗时。verify 的 trace 聚合与 19 号方案 §七"定位慢轴"都要它
    attempt: int             # 本条属于第几稿。黑板跨打回轮次是累加的（operator.add），
                             # 裁决者必须只取当前 attempt，否则上一稿的命中会被重复计分——那是分数变化，本轮禁止


def round_entries(board: list[BoardEntry], attempt: int) -> list[BoardEntry]:
    """取当前轮的板面：只留本 attempt 的条目，同 trait 取最后一条（防御重放时同轮双写）。

    入参：board=全板累加值，attempt=当前稿序号。
    返回：按写入顺序的 BoardEntry 列表。
    异常场景：无——空板返回空表，缺 attempt 字段的脏条目直接跳过（读端宽容，写端契约）。
    """
    latest: dict[str, BoardEntry] = {}
    for entry in board:
        if int(entry.get("attempt", -1)) != int(attempt):
            continue
        latest[str(entry.get("trait", "?"))] = entry
    return list(latest.values())


def entries_to_results(entries: list[BoardEntry]) -> list[dict[str, Any]]:
    """把板面条目映射回 ScoreAggregator.score 需要的 results 形状（字段与 judge_trait 输出对齐）。

    失败条目不应出现在这里——调用方先按 failed 过滤；severity 已在专家侧取规格值。
    """
    return [
        {
            "trait": e["trait"],
            "severity": e["severity"],
            "hits": e["hits"],
            "invalid": e["invalid"],
            "ambiguity": e["ambiguity"],
            "parse_error": e["parse_error"],
            "prompt_chars": e["prompt_chars"],
            "reply_chars": e["reply_chars"],
        }
        for e in entries
    ]
