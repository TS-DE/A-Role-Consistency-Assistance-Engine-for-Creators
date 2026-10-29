"""落句级统一裁决层（agent_docs/21 方案 A）：裁决只认「落句 + 严重度」，不认 pattern 编号。

为什么需要它（2026-10-29 实测）：同一句 `I am here for you...` 在 4 次运行里有 1 次被判成
"大段抒情"、3 次被判成"大男主腔"——归因（pattern/轴）会随采样摇摆，而旧聚合的 soft 计数
按"落句去重后的不同轴数"统计，一句的轴归属一换，分数就跟着换。**分数不该跟着归因摇摆。**

本层的三条纪律：
1. 合并只按落句（QuoteValidator.sentence_of，与聚合器同一套定位），绝不按 pattern 编号
   或字符串相似度模糊匹配——模糊匹配会把"同一句被判两次"粉饰成"只判一次"，那是掩盖问题；
2. 一个桶最多贡献一处命中，严重度取桶内最高（hard > soft，与聚合器同款"任一 hard 即 hard"）；
3. 不复制 `_decide`（单一真相来源）：把桶投影成"每桶恰好一条独立记录"后交给现有
   ScoreAggregator.score()。等价性论证见 claims_to_projection() 的注释。

边界（别指望这一步的东西）：不提升召回（G06-a 漏杀要靠第 4/5 步 exemplar/ReAct），
不修硬规则误触发（G08-a 要改 prompt 边界）。本轮只买"归因免疫 + 可审计重叠 + 报告干净"。
"""

from __future__ import annotations

from typing import Any, TypedDict

from src.graph.board import BoardEntry
from src.judge.quote_validator import QuoteValidator

NOLOC_PREFIX = "__noloc__"  # 落句定位失败的前缀标记：不合并，各算各的


class Claim(TypedDict):
    """一个落句桶 = 一处命中。字段全部可溯源，patterns 只做审计、绝不参与计分。"""

    sentence: str        # 落句原文（归一化文本：NFKC/折叠大小写，与聚合器同一套比对）
    severity: str        # hard / soft —— 桶内取最高（任一 hit 级 hard 即 hard）
    traits: list[str]    # 哪些轴共同命中这句（跨轴重叠从"隐没在去重里"变成可审计数据）
    patterns: list[str]  # 桶内出现过的所有 pattern（审计用）
    quotes: list[str]    # 原始引文（保留，便于人工复核"同一句被几种说法举证"）
    occurrences: int     # 桶内命中条目数 = 几个 pattern/轴报过这句
    _key: Any            # 内部去重键：落句=(start,end)；定位失败=唯一合成分布键


def _effective_severity(hit: dict, entry: BoardEntry) -> str:
    """hit 级严重度优先、缺省回落到轴级——与 ScoreAggregator.score 的取法逐字一致，
    保证归因免疫改的是"计数单位"，不是"什么算 hard"。"""
    return str(hit.get("severity") or entry["severity"]).lower()


def merge_claims(entries: list[BoardEntry], candidate: str,
                 validator: QuoteValidator | None = None) -> list[Claim]:
    """把当前轮板面的全部 hits（跨轴、跨 pattern）按落句分桶。

    入参：entries=round_entries 过滤后的本轮板面（含失败条目也无妨，其 hits 为空）；
         candidate=当前草稿（落句定位的 haystack 来源）。
    返回：Claim 列表，按写入顺序（板面顺序）稳定排列。
    异常场景：定位不到落句（span=(-1,-1) 或越界）的命中各自成桶——
         宁可多算一处，也不许误并成一处（聚合器 _claim_sentence 同一条保守哲学）。
    """
    validator = validator or QuoteValidator()
    haystack = validator.normalize(candidate)
    buckets: dict[Any, Claim] = {}

    for entry in entries:
        for hit in entry["hits"]:
            quote = str(hit.get("quote") or "").strip()
            span = validator.span_of(haystack, quote)
            sentence = validator.sentence_of(haystack, span[0]) if span[0] >= 0 else (-1, -1)
            if sentence[0] >= 0:
                key: Any = sentence
                text = haystack[sentence[0]:sentence[1]].strip()
            else:
                # 每 hit 一桶：pattern 名可能重名，再带上引文与序号，保证键唯一
                key = (NOLOC_PREFIX, entry["trait"], str(hit.get("pattern") or ""), quote,
                       len(buckets))
                text = quote
            bucket = buckets.get(key)
            if bucket is None:
                buckets[key] = Claim(
                    sentence=text,
                    severity=_effective_severity(hit, entry),
                    traits=[entry["trait"]],
                    patterns=[str(hit.get("pattern") or "")],
                    quotes=[quote] if quote else [],
                    occurrences=1,
                    _key=key,
                )
                continue
            if _effective_severity(hit, entry) == "hard":
                bucket["severity"] = "hard"  # 桶内取最高
            if entry["trait"] not in bucket["traits"]:
                bucket["traits"].append(entry["trait"])
            pattern = str(hit.get("pattern") or "")
            if pattern not in bucket["patterns"]:
                bucket["patterns"].append(pattern)
            if quote and quote not in bucket["quotes"]:
                bucket["quotes"].append(quote)
            bucket["occurrences"] += 1

    return list(buckets.values())


def claims_to_projection(claims: list[Claim]) -> list[dict[str, Any]]:
    """把桶投成"每桶恰一条独立记录"喂给现有 ScoreAggregator.score()。

    等价性论证（任务书 §2.2 要求必须写清）——score() 的结论只由两个标量决定：
      ① hard_hits 是否非空：hard 桶的记录 severity=hard，score 里 hit 级 severity 直落
         hard_hits ⟺ 存在 hard 桶 ⟺ 旧规则"任一 hard 命中即 0"的落句级对应；
      ② soft_by_trait 的键数（len）：每个 soft 桶携带**唯一 trait 合成键**与**唯一落句**，
         句子互不相同 ⟹ _claim_sentence 首次登记必返回 None、不会互相吞并，
         合成键互不相同 ⟹ 键数恰等于 soft 桶数；
      定位失败的桶（引文不在原文/无法成句）：_claim_sentence 拿 (-1,-1) 走"定位不到不去重"
         分支照常计数——与桶本身"不合并各算各的"严格同口径。
    ⟹ score() 在此投影上的输出 = _decide(∃hard桶, #soft桶)：一个桶最多贡献一处，
      严重度取桶值。_decide 未复制、聚合器未改，分数语义只此一源。
    """
    projected: list[dict[str, Any]] = []
    for index, claim in enumerate(claims):
        quote = claim["quotes"][0] if claim["quotes"] else claim["sentence"]
        projected.append({
            # 合成唯一键：旧聚合的 soft 计数按"不同轴数"，方案 A 要按"不同落句数"；
            # 每桶一把钥匙让 score() 数桶而不是数轴。display trait 取主命中轴便于读日志。
            "trait": f"{claim['traits'][0]}#claim{index}",
            "severity": claim["severity"],
            "hits": [{"pattern": "落句级统一裁决", "quote": quote, "severity": claim["severity"]}],
            "invalid": [], "ambiguity": [], "parse_error": None,
            "prompt_chars": 0, "reply_chars": 0,
        })
    return projected


def claim_lines(claims: list[Claim]) -> list[str]:
    """violated 清单的落句级格式：`[severity] sentence ← "quote"（N 轴 / M pattern）`。

    旧格式按命中条目排，同一句会重复三行且行行不同 pattern（归因摇摆直接印在人读清单上）；
    新格式一句一行，重叠信息收进计数里。quotes 多版本时展示首见引文，全量在 Claim 里可查。
    """
    return [
        f"[{c['severity']}] {c['sentence']} ← \"{c['quotes'][0] if c['quotes'] else c['sentence']}\""
        f"（{len(c['traits'])} 轴 / {len(c['patterns'])} pattern）"
        for c in claims
    ]
