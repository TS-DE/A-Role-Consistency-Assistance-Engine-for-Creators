"""图状态：节点之间唯一的通信方式。

为什么单独一个文件：LangGraph 里节点不互相调用，它们只读写 State。
把字段定义集中在一处，才能一眼看清"数据怎么从上一个节点流到下一个节点"——
面试问"状态怎么传递"，答案就是这张表。
"""

from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    """一次请求的完整状态。total=False 表示每个节点只写自己负责的字段。"""

    # ── 入口 ────────────────────────────────────────────
    user_input: str          # 创作者给的情境/台词
    character_id: str        # 人设卡 id，如 sherlock_holmes
    history: list[dict]      # 前几轮对话（多轮一致性用，W2 再填）

    # ── 生成节点 ────────────────────────────────────────
    draft: str               # 当前草稿
    attempt: int             # 第几次生成（0 起）
    rewrite_notes: list[str] # 上一轮判定的违规清单，喂回生成节点

    # ── 校验节点 ────────────────────────────────────────
    verdicts: list[dict]     # 每个 trait 的 {trait, hits[], ambiguity[]}
    score: int               # 聚合后的三档分：0 OOC / 1 drift / 2 pass / -1 未完成
    violated: list[str]      # 命中的 pattern 摘要，供人读与回写
    verify_incomplete: bool  # 有 trait 调用失败：这次判定不可信，不许当成"通过"

    # ── 出口 ────────────────────────────────────────────
    final: str               # 最终交给创作者的文本
    needs_human: bool        # 走到人工裁决分支（打回用尽 / 校验未完成）
    trace: list[dict]        # 全链路日志：每轮草稿、判定、耗时、成本


def new_state(user_input: str, character_id: str = "sherlock_holmes") -> GraphState:
    """构造一个干净的初始状态。所有计数器显式归零，别依赖默认值。"""
    return GraphState(
        user_input=user_input,
        character_id=character_id,
        history=[],
        draft="",
        attempt=0,
        rewrite_notes=[],
        verdicts=[],
        score=-1,
        violated=[],
        verify_incomplete=False,
        final="",
        needs_human=False,
        trace=[],
    )


def summarize_hits(verdicts: list[dict]) -> list[str]:
    """把校验结果压成人类可读的违规清单。

    生成节点和 CLI 都读这份清单：前者据此改写，后者据此告诉创作者"哪句踩了哪条规则"。
    """
    notes: list[str] = []
    for verdict in verdicts:
        for hit in verdict.get("hits", []):
            pattern = hit.get("pattern", "?")
            quote = hit.get("quote", "")
            notes.append(f"[{verdict.get('trait', '?')}] {pattern} ← \"{quote}\"")
    return notes


def trace_entry(node: str, payload: dict[str, Any]) -> dict:
    """统一的日志条目格式，便于最后一次性落盘成 JSON。"""
    return {"node": node, **payload}
