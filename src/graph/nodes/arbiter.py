"""裁决者：读全板 → 调现有 ScoreAggregator → 写回与 VerifyNode 同形状的四字段。

本轮（第 2 步）的唯一目标：**零行为变化**。
- 聚合规则一行不新增，直接调用 ScoreAggregator.score（hard→0 / soft≥2→0 / =1→1）；
- 19 号方案 §2.4 的"跨轴追加、落句去重升级"属于第 3 步，这里不做；
- 裁决者必须比单节点更保守：任何一块板没写全（failed/缺条）都判未完成——
  缺一条规则算出的分可能恰好是 2，那是假通过（铁律 3）。
"""

from __future__ import annotations

from typing import Any

from src.graph.board import BoardEntry, entries_to_results, round_entries
from src.graph.nodes.verify import INCOMPLETE_SCORE
from src.graph.state import GraphState, summarize_hits, trace_entry
from src.judge.aggregator import ScoreAggregator


class Arbiter:
    """黑板的集中式读取端。无状态：输入 State，输出四字段 + trace。"""

    def __init__(self, aggregator: ScoreAggregator, trait_order: list[str] | None = None) -> None:
        self._aggregator = aggregator
        # trait_order = 规格的轴顺序：results 排序后 violated 清单顺序与 simple 模式逐字节一致
        self._trait_order = trait_order

    def __call__(self, state: GraphState) -> dict[str, Any]:
        """读当前 attempt 的板面并聚合。

        入参 state：需要 draft / board / attempt。
        返回：{"verdicts","score","violated","verify_incomplete","trace"}，
             字段形状与 VerifyNode.__call__ 完全一致（下游 routing/web 零感知）。
        异常场景：本方法不抛——空草稿守卫、缺板、failed 都收敛为 score=-1 + incomplete。
        """
        draft = str(state.get("draft", "")).strip()
        trace = list(state.get("trace", []))
        attempt = int(state.get("attempt", 0))

        if not draft:
            # 与 VerifyNode 的空草稿守卫同形：不发请求、直接未完成
            return {
                "verdicts": [],
                "score": INCOMPLETE_SCORE,
                "violated": [],
                "verify_incomplete": True,
                "trace": trace + [trace_entry("verify", {"error": "empty draft"})],
            }

        entries = self._ordered(round_entries(state.get("board", []), attempt))
        failed = [e for e in entries if e["failed"]]
        successes = [e for e in entries if not e["failed"]]
        missing = self._missing_traits(entries)

        results = entries_to_results(successes)
        aggregate = self._aggregator.score(results, draft)
        violated = summarize_hits(results)

        entry = trace_entry("verify", {
            "attempt": attempt,
            "score": aggregate["score"],
            "hits": len(violated),
            # failed_traits 与 simple 模式同口径：调用失败数（缺板另算，见下方 incomplete 判定）
            "failed_traits": len(failed) + len(missing),
            "ms": sum(int(e["ms"]) for e in entries),
            "prompt_chars": sum(int(e["prompt_chars"]) for e in successes),
            "reply_chars": sum(int(e["reply_chars"]) for e in successes),
        })

        if failed or missing or not entries:
            # 缺条/全败/板为空 → 分数不可信，不许当通过（铁律 3）
            return {
                "verdicts": results,
                "score": INCOMPLETE_SCORE,
                "violated": violated,
                "verify_incomplete": True,
                "trace": trace + [entry],
            }

        return {
            "verdicts": results,
            "score": aggregate["score"],
            "violated": violated,
            "verify_incomplete": False,
            "trace": trace + [entry],
        }

    def _ordered(self, entries: list[BoardEntry]) -> list[BoardEntry]:
        """按规格轴顺序排列板面；不在 order 里的（理论上不该出现）保持原序放末尾。"""
        if not self._trait_order:
            return entries
        rank = {tid: i for i, tid in enumerate(self._trait_order)}
        return sorted(entries, key=lambda e: rank.get(e["trait"], len(rank)))

    def _missing_traits(self, entries: list[BoardEntry]) -> list[str]:
        """扇出应覆盖的轴里有几条根本没写板——丢 Send / 图被改坏时的最后一道闸。"""
        if not self._trait_order:
            return []
        seen = {e["trait"] for e in entries}
        return [t for t in self._trait_order if t not in seen]
