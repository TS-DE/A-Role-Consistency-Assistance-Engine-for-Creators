"""落句级裁决层的单元用例（假数据，不联网）：合并、投影等价、人读格式。

跑法：python -m tests.graph.test_claims
与 test_board 的分工：那边验"图里接线与分数行为"，这边验 claims.py 三个纯函数本身。
"""

from __future__ import annotations

from src.graph.board import BoardEntry
from tests.graph import test_board as tb  # 借用 stub 脚手架：DRAFT/SPEC/StubModel/_arbiter_graph 等
from src.graph.claims import claim_lines, claims_to_projection, merge_claims
from src.judge.aggregator import ScoreAggregator

D1 = "There, there, Watson. Let it all out. I am here for you, my dear friend."


def _hit(pattern: str, quote: str, severity: str = "soft") -> dict:
    return {"pattern": pattern, "quote": quote, "severity": severity}


def _entry(trait: str, severity: str, hits: list[dict]) -> BoardEntry:
    return BoardEntry(trait=trait, severity=severity, hits=hits, invalid=[],
                      ambiguity=[], failed="", prompt_chars=5, reply_chars=5,
                      parse_error=None, ms=1, attempt=1)


def test_bucket_fields_and_severity_max() -> None:
    """跨轴同句：soft(轴aa) + hard(轴bb 的 hit 级 hard) → 1 桶，severity=hard，全量审计。"""
    claims = merge_claims([
        _entry("aa", "soft", [_hit("安慰关怀", "There, there, Watson.")]),
        _entry("bb", "soft", [_hit("自我情绪表露", "There, there, Watson.", "hard")]),
    ], D1)
    assert len(claims) == 1
    c = claims[0]
    assert c["severity"] == "hard" and c["occurrences"] == 2
    assert c["traits"] == ["aa", "bb"] and c["patterns"] == ["安慰关怀", "自我情绪表露"]
    assert c["quotes"] == ["There, there, Watson."], "quotes 去重收集（occurrences 才数条目）"


def test_unlocatable_quotes_never_merge() -> None:
    """定位不到的引文（编造/越界）逐条成桶：宁可多算，不许误并——模糊匹配禁令的正体。"""
    claims = merge_claims([_entry("aa", "soft", [
        _hit("P1", "这不是原文里的句子"), _hit("P2", "这不是原文里的句子")])], D1)
    assert len(claims) == 2 and all(c["occurrences"] == 1 for c in claims)


def test_projection_matches_bucket_semantics() -> None:
    """投影等价性的机械自证：score(投影) 必须等于 _decide(∃hard桶, #soft桶) 的三档结论，
    而 _decide 我们不许复制——所以这里用"公开行为"验证：桶数与严重度直接决定档位。"""
    agg = ScoreAggregator()
    from src.graph.board import entries_to_results
    # 3 个不同落句的 soft 桶（同一轴）→ 旧口径 n_soft=1（按轴数）漂移；新口径 3 桶 ≥2 → OOC。
    # 这是方案 A 最实质的口径变化：一句一处，单轴多句不再被"同轴"豁免升级。
    entries = [_entry("aa", "soft", [
        _hit("P1", "There, there, Watson."), _hit("P2", "Let it all out."),
        _hit("P3", "I am here for you, my dear friend.")])]
    old = agg.score(entries_to_results(entries), D1)["score"]
    new = agg.score(claims_to_projection(merge_claims(entries, D1)), D1)["score"]
    assert old == 1 and new == 0, "本用例同时锁定：这是有意的行为变化（按句计数）"

    # 单桶 → 两档同分（无回归区）：一句多 pattern 只算一处
    one = [_entry("aa", "soft", [_hit("P1", "Let it all out."),
                                 _hit("P2", "Let it all out.")])]
    assert agg.score(claims_to_projection(merge_claims(one, D1)), D1)["score"] == 1
    # hard 桶一票否决（两档同分）
    hard = [_entry("aa", "soft", [_hit("P1", "Let it all out.", "hard")])]
    assert agg.score(claims_to_projection(merge_claims(hard, D1)), D1)["score"] == 0


def test_claim_lines_format() -> None:
    """人读清单：一句一行，`[severity] sentence ← "quote"（N 轴 / M pattern）`。"""
    claims = merge_claims([
        _entry("aa", "soft", [_hit("P1", "Let it all out."), _hit("P2", "Let it all out.")]),
        _entry("bb", "soft", [_hit("P3", "Let it all out.")]),
    ], D1)
    lines = claim_lines(claims)
    assert len(lines) == 1
    assert lines[0].startswith("[soft] ")
    assert "（2 轴 / 3 pattern）" in lines[0]
    assert "let it all out." in lines[0], "句面取归一化文本（与聚合器同一比对口径）"


DRAFT = tb.DRAFT  # 落句锚点文本与 test_board 共用同一份，防止两边 fixture 漂移


# ── 第 21 号任务书 · merge 开关与归因不变性 ──────────────────
def _arbiter(entries: list[tb.BoardEntry], draft: str = tb.DRAFT,
                 merge: bool = True) -> dict:
    """直调 Arbiter（不建图）：验证裁决层本身，board 即输入。"""
    out = tb._arbiter_graph(["aa", "bb"], merge=merge).invoke(
        {"board": entries, "draft": draft, "attempt": 1, "trace": []})
    return out


def _soft_entry(trait: str, quote: str, pattern: str, attempt: int = 1) -> BoardEntry:
    return tb.BoardEntry(trait=trait, severity="soft",
                      hits=[{"pattern": pattern, "quote": quote, "severity": "soft"}],
                      invalid=[], ambiguity=[], failed="",
                      prompt_chars=5, reply_chars=5, parse_error=None, ms=1, attempt=attempt)


def _clean_entry(trait: str) -> BoardEntry:
    """补板用：同轮同轴的重复条目会被 round_entries 折叠（防重放双写），
    所以参与对比的每一轮都要把 trait_order 的轴写满，否则触发缺板闸（score=-1）。"""
    return tb.BoardEntry(trait=trait, severity="soft", hits=[],
                      invalid=[], ambiguity=[], failed="",
                      prompt_chars=5, reply_chars=5, parse_error=None, ms=1, attempt=1)


def test_attribution_flip_does_not_move_score() -> None:
    """本轮核心证据：一句的轴归属在两次运行间摇摆（观测到的归因噪声形态），
    merge=on 分数必须不动；merge=off（v0.9.1 基线）会跟着摇摆——差值就是要修的东西。

    场景：两句 S1/S2。run1 里 S1、S2 都被轴 aa 报（旧聚合按"不同轴数"→ n_soft=1 → 1 分）；
    run2 里 S2 改挂到轴 bb（旧：n_soft=2 → 0 分——分数随归因跳）。
    新口径下两次都是 2 个落句桶 → 恒 0 分。
    """
    s1, s2 = "You will not last the night, Watson.", "Fetch my coat."
    two_sentences = "You will not last the night, Watson. Fetch my coat. The game is afoot."
    aa_two = tb.BoardEntry(trait="aa", severity="soft",
                        hits=[{"pattern": "P1", "quote": s1, "severity": "soft"},
                              {"pattern": "P2", "quote": s2, "severity": "soft"}],
                        invalid=[], ambiguity=[], failed="",
                        prompt_chars=5, reply_chars=5, parse_error=None, ms=1, attempt=1)
    run1 = [aa_two, _clean_entry("bb")]          # 两句都挂在轴 aa 上
    run2 = [_soft_entry("aa", s1, "P1"), _soft_entry("bb", s2, "P3")]  # S2 改挂轴 bb（归因摇摆）

    assert _arbiter(run1, two_sentences, merge=False)["score"] == 1
    assert _arbiter(run2, two_sentences, merge=False)["score"] == 0, \
        "先自证旧口径确实会随归因摇摆（否则这个用例什么都没测到）"
    on1 = _arbiter(run1, two_sentences, merge=True)
    on2 = _arbiter(run2, two_sentences, merge=True)
    assert on1["score"] == on2["score"] == 0, "落句桶计数与轴归属无关——分数免疫"
    assert on1["verify_incomplete"] is False and len(on1["claims"]) == 2


def test_multi_pattern_same_sentence_is_one_claim_score_unchanged() -> None:
    """2026-10-29 观测到的形态：同一句同轴报了两个 pattern（归因摇摆）。
    → 1 个 claim、patterns 长度 2、occurrences 2；单句单轴时分数与 merge=off 一致（都是 1）。

    注意两个 hit 必须挂在**同一条 BoardEntry** 里：round_entries 同轮同轴取最后一条
    （防重放双写的契约），分两条写会被折叠成一条——那是测合并器，不是测板面语义。
    """
    entry = tb.BoardEntry(trait="aa", severity="soft",
                       hits=[{"pattern": "大男主腔", "quote": DRAFT, "severity": "soft"},
                             {"pattern": "大段抒情", "quote": DRAFT, "severity": "soft"}],
                       invalid=[], ambiguity=[], failed="",
                       prompt_chars=5, reply_chars=5, parse_error=None, ms=1, attempt=1)
    out = _arbiter([entry, _clean_entry("bb")], merge=True)
    assert len(out["claims"]) == 1
    assert out["claims"][0]["patterns"] == ["大男主腔", "大段抒情"]
    assert out["claims"][0]["occurrences"] == 2
    assert out["score"] == _arbiter([entry, _clean_entry("bb")], merge=False)["score"] == 1


def test_cross_axis_hard_soft_same_sentence_merges_to_hard() -> None:
    """跨轴同句 hard+soft → 只出 1 个 claim，severity=hard；traits 记满两轴。"""
    hard_board = tb.BoardEntry(trait="bb", severity="hard",
                            hits=[{"pattern": "硬规则", "quote": DRAFT, "severity": "hard"}],
                            invalid=[], ambiguity=[], failed="",
                            prompt_chars=5, reply_chars=5, parse_error=None, ms=1, attempt=1)
    out = _arbiter([_soft_entry("aa", DRAFT, "P1"), hard_board], merge=True)
    assert len(out["claims"]) == 1
    assert out["claims"][0]["severity"] == "hard"
    assert sorted(out["claims"][0]["traits"]) == ["aa", "bb"]
    assert out["score"] == 0


def test_two_sentences_not_over_merged() -> None:
    """两句各自被同一轴命中 → 2 个 claim。过度合并按字符串相似度粉饰太平，禁止。"""
    two_sentences = "You will not last the night, Watson. Fetch my coat. The game is afoot."
    two_hits = tb.BoardEntry(trait="aa", severity="soft",
                          hits=[{"pattern": "P1", "quote": "You will not last the night, Watson.",
                                 "severity": "soft"},
                                {"pattern": "P2", "quote": "Fetch my coat.", "severity": "soft"}],
                          invalid=[], ambiguity=[], failed="",
                          prompt_chars=5, reply_chars=5, parse_error=None, ms=1, attempt=1)
    out = _arbiter([two_hits, _clean_entry("bb")], draft=two_sentences, merge=True)
    assert len(out["claims"]) == 2
    assert all(c["occurrences"] == 1 for c in out["claims"])


def test_merge_off_trace_shape_is_v091_exactly() -> None:
    """merge=off 时 verify trace 的键集合与 n_claims 等新增字段必须整体缺席——
    A/B 对比与回退的可信度全押在'形状也是旧的'上。"""
    graph = tb.build_graph(tb.SPEC, tb.StubModel(default=tb.SOFT_HIT), tb.StubModel(default=tb.SOFT_HIT),
                        max_attempts=1, agent_mode="blackboard", arbiter_merge=False)
    out = tb._run_to_end(graph, "shapeoff")
    ver = [e for e in out["trace"] if e.get("node") == "verify"][0]
    assert set(ver.keys()) == {"node", "attempt", "score", "hits", "failed_traits",
                               "ms", "prompt_chars", "reply_chars"}
    assert out["claims"] == []

    graph_on = tb.build_graph(tb.SPEC, tb.StubModel(default=tb.SOFT_HIT), tb.StubModel(default=tb.SOFT_HIT),
                           max_attempts=1, agent_mode="blackboard", arbiter_merge=True)
    out_on = tb._run_to_end(graph_on, "shapeon")
    ver_on = [e for e in out_on["trace"] if e.get("node") == "verify"][0]
    assert {"n_claims", "n_cross_axis", "n_multi_pattern"} <= set(ver_on.keys())
    assert ver_on["n_claims"] == 1, "8 轴全报同一句 DRAFT → 归并成 1 个落句桶"
    assert ver_on["n_cross_axis"] == 1, "这一桶 8 轴共同命中——跨轴重叠第一次变成可审计数据"
    # stub 的 8 条命中写的是同一个 pattern 名，patterns 去重后只剩 1 → 计数为 0 是正确行为，
    # 真实的"同句多 pattern"由 test_multi_pattern_same_sentence_is_one_claim 覆盖
    assert ver_on["n_multi_pattern"] == 0
    assert len(out_on["violated"]) == 1, "一句一行：人读清单不再重复八遍"
    assert out_on["score"] == 1, "旧口径 n_soft=1（同句被他轴去重）→ 新口径 1 桶 → 都是 1，无回归"



# ── 裁决确认单 · 第 1 项：机制等价性（固定 board 输入，不调模型，确定性）────────
def test_merge_score_equivalence_on_four_attribution_shapes() -> None:
    """用户裁决要求（2026-10-29）：四类归因形态的固定输入上，merge on/off 的 score 必须完全相同。
    相等 ⟹ 合并层对计分语义是"归并已有证据"、不制造新证据 ⟹ E03-a 的 2→0 与它无关。
    有任何不等即停手（本用例断言即闸，CI 意义上永久生效）。"""
    s1, s2 = "You will not last the night, Watson.", "Fetch my coat."
    two = "You will not last the night, Watson. Fetch my coat. The game is afoot."

    def board(*hits_by_trait: tuple) -> list[tb.BoardEntry]:
        """按 (trait, [(quote, pattern, hit_severity)]) 组固定板面；轴序 aa/bb 都写满防缺板闸。"""
        seen = {t for t, _ in hits_by_trait}
        entries = [tb.BoardEntry(trait=t, severity="soft",
                                 hits=[{"pattern": p, "quote": q, "severity": sv} for q, p, sv in hs],
                                 invalid=[], ambiguity=[], failed="",
                                 prompt_chars=5, reply_chars=5, parse_error=None, ms=1, attempt=1)
                   for t, hs in hits_by_trait]
        for rest in ({"aa", "bb"} - seen):
            entries.append(_clean_entry(rest))
        return entries

    shapes = {
        "a 同句跨轴 hard+soft": board(("aa", [(tb.DRAFT, "P1", "soft")]),
                                       ("bb", [(tb.DRAFT, "P2", "hard")])),
        "b 同句同轴双 pattern": board(("aa", [(tb.DRAFT, "P1", "soft"), (tb.DRAFT, "P2", "soft")])),
        "c 两句各自单轴命中":   board(("aa", [(s1, "P1", "soft")]),
                                       ("bb", [(s2, "P2", "soft")])),
        "d 单句单轴单 pattern": board(("aa", [(tb.DRAFT, "P1", "soft")])),
    }
    for name, entries in shapes.items():
        draft = two if name.startswith("c") else tb.DRAFT
        off = _arbiter(entries, draft, merge=False)["score"]
        on = _arbiter(entries, draft, merge=True)["score"]
        assert off == on, f"形态「{name}」两臂分数不等（off={off} on={on}）——按裁决单立即停手"


def test_same_axis_multi_sentence_is_documented_divergence() -> None:
    """单独立基线的"有意分歧"（不混进上面四类等价断言）：同一轴命中两句——
    旧口径按轴数=1 判漂移，新口径按落句数=2 判 OOC。这是方案 A 的设计本身
    （一句一处、≥2 处即 OOC），不是归因修复的副作用；test_claims 桶级用例已锁同一事实。"""
    s1, s2 = "You will not last the night, Watson.", "Fetch my coat."
    two = "You will not last the night, Watson. Fetch my coat. The game is afoot."
    entries = [tb.BoardEntry(trait="aa", severity="soft",
                             hits=[{"pattern": "P1", "quote": s1, "severity": "soft"},
                                   {"pattern": "P2", "quote": s2, "severity": "soft"}],
                             invalid=[], ambiguity=[], failed="",
                             prompt_chars=5, reply_chars=5, parse_error=None, ms=1, attempt=1),
               _clean_entry("bb")]
    assert _arbiter(entries, two, merge=False)["score"] == 1
    assert _arbiter(entries, two, merge=True)["score"] == 0, "有意口径变化：两句两处 → OOC"


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"test_claims OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
