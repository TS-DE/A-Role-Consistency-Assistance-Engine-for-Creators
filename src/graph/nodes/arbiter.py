"""裁决者：读全板 → （可选）落句级统一裁决 → 调现有 ScoreAggregator → 写回与 VerifyNode 同形的字段。

两档行为，由 ARBITER_MERGE 开关切换（agent_docs/21）：
- `off`（回退/A/B 基线）：v0.9.1 逐字节——results 直喂 score()，violated 走 summarize_hits；
- `on`（默认）：hits 先按落句分桶（claims.merge_claims），桶投影后喂**同一个** score()，
  violated 换成一句一行的落句级格式，并写出 GraphState.claims 供 web/CLI 展示。

**ScoreAggregator 一行未改**：merge=on 只改变"喂给它的形状"（每桶恰一条独立记录），
分数语义 = _decide(∃hard桶, #soft桶)，等价性论证见 claims.claims_to_projection()。
禁止在这里复制 _decide——那是两份会漂移的真相。

保守闸不因开关退化：任一 failed / 缺板 / 空板 → score=-1 + incomplete（铁律 3）；
空草稿守卫与 VerifyNode 同形。落句合并只发生在"已经采信的命中"之间，不豁免任何完整性检查。
"""

from __future__ import annotations

from typing import Any

from src.graph.board import BoardEntry, entries_to_results, round_entries
from src.graph.claims import Claim, claim_lines, claims_to_projection, merge_claims
from src.graph.nodes.verify import INCOMPLETE_SCORE
from src.graph.state import GraphState, summarize_hits, trace_entry
from src.judge.aggregator import ScoreAggregator
from src.judge.quote_validator import QuoteValidator


class Arbiter:
    """黑板的集中式读取端。无状态：输入 State，输出字段 + trace。"""

    def __init__(self, aggregator: ScoreAggregator, trait_order: list[str] | None = None,
                 merge_claims_enabled: bool = True) -> None:
        self._aggregator = aggregator
        # trait_order = 规格的轴顺序：results 排序后 violated 清单顺序与 simple 模式逐字节一致
        self._trait_order = trait_order
        self._merge = merge_claims_enabled
        self._validator = QuoteValidator()

    def __call__(self, state: GraphState) -> dict[str, Any]:
        """读当前 attempt 的板面并聚合。

        入参 state：需要 draft / board / attempt。
        返回：{"verdicts","score","violated","verify_incomplete","trace"}（merge=on 另加 "claims"），
             字段形状与 VerifyNode.__call__ 一致（下游 routing/web 零感知）。
        异常场景：本方法不抛——空草稿守卫、缺板、failed 都收敛为 score=-1 + incomplete。
        """
        draft = str(state.get("draft", "")).strip()
        trace = list(state.get("trace", []))
        attempt = int(state.get("attempt", 0))

        if not draft:
            # 与 VerifyNode 的空草稿守卫同形：不发请求、直接未完成
            return self._guard(trace, "empty draft")

        entries = self._ordered(round_entries(state.get("board", []), attempt))
        failed = [e for e in entries if e["failed"]]
        successes = [e for e in entries if not e["failed"]]
        missing = self._missing_traits(entries)

        if self._merge:
            score, violated, verdicts, claims = self._score_merged(successes, draft)
        else:
            verdicts = entries_to_results(successes)
            score = self._aggregator.score(verdicts, draft)["score"]
            violated = summarize_hits(verdicts)
            claims = []

        entry = self._verify_trace(entries, successes, failed, missing, attempt,
                                   score, violated, claims)

        if failed or missing or not entries:
            # 缺条/全败/板为空 → 分数不可信，不许当通过（铁律 3）——两档同闸
            return {
                "verdicts": verdicts,
                "score": INCOMPLETE_SCORE,
                "violated": violated,
                "verify_incomplete": True,
                "trace": trace + [entry],
                **({"claims": claims} if self._merge else {}),
            }

        return {
            "verdicts": verdicts,
            "score": score,
            "violated": violated,
            "verify_incomplete": False,
            "trace": trace + [entry],
            **({"claims": claims} if self._merge else {}),
        }

    # ── merge=on：落句级统一裁决 ─────────────────────────
    def _score_merged(self, successes: list[BoardEntry], draft: str
                      ) -> tuple[int, list[str], list[dict], list[Claim]]:
        """先合并 claims，再算分。verdicts 保持逐轴原始形状（审计面不掺合），
        进分数的只有投影后的桶——归因（pattern/轴）怎么摇摆，桶数与桶严重度不动。"""
        claims = merge_claims(successes, draft, self._validator)
        aggregate = self._aggregator.score(claims_to_projection(claims), draft)
        return int(aggregate["score"]), claim_lines(claims), entries_to_results(successes), claims

    # ── 两档共用 ────────────────────────────────────────
    def _guard(self, trace: list[dict], reason: str) -> dict[str, Any]:
        """空草稿守卫：merge=off 时返回形状与 v0.9.1 逐字节一致（不带 claims 键）。"""
        out: dict[str, Any] = {
            "verdicts": [],
            "score": INCOMPLETE_SCORE,
            "violated": [],
            "verify_incomplete": True,
            "trace": trace + [trace_entry("verify", {"error": reason})],
        }
        if self._merge:
            out["claims"] = []
        return out

    def _verify_trace(self, entries: list[BoardEntry], successes: list[BoardEntry],
                      failed: list[BoardEntry], missing: list[str], attempt: int,
                      score: int, violated: list[str], claims: list[Claim]) -> dict[str, Any]:
        """verify 条目：既有字段口径一字不动（attempt=state 轮次、ms=最慢单轴≈墙钟，
        score=聚合原始分——即便随后被保守闸压成 -1，trace 仍如实留底，v0.9.1 同此），
        merge=on 才追加三个落句级审计指标——off 时连键都不出现，形状也逐字节回退，A/B 才干净。"""
        payload: dict[str, Any] = {
            "attempt": attempt,
            "score": score,
            "hits": len(violated),
            # failed_traits 与 simple 模式同口径：调用失败数（缺板另算，见 incomplete 判定）
            "failed_traits": len(failed) + len(missing),
            "ms": max((int(e["ms"]) for e in entries), default=0),
            "prompt_chars": sum(int(e["prompt_chars"]) for e in successes),
            "reply_chars": sum(int(e["reply_chars"]) for e in successes),
        }
        if self._merge:
            payload["n_claims"] = len(claims)
            payload["n_cross_axis"] = sum(1 for c in claims if len(c["traits"]) >= 2)
            payload["n_multi_pattern"] = sum(1 for c in claims if len(c["patterns"]) >= 2)
        return trace_entry("verify", payload)

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
