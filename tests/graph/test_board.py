"""黑板用例（假模型，不联网）：合并、等价、分轮、失败路径。

跑法：python -m tests.graph.test_board
验收两条硬断言（任务书 §3）：
  ① reducer 合并：8 个 Send 分支各写一条，board 长度为 8，不丢不重；
  ② 等价性：同组 results 下 Arbiter 的 score/violated 与直调 ScoreAggregator 逐字段相等，
     并把整个 blackboard 图与 simple 图的四个校验字段做全等比较。
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.graph.board import BoardEntry, round_entries
from src.graph.builder import ABANDON, build_graph
from src.graph.nodes.arbiter import Arbiter
from src.graph.state import GraphState, new_state, summarize_hits
from src.judge import evaluator as evaluator_module
from src.judge.aggregator import ScoreAggregator
from src.judge.chat_model import ChatModel

evaluator_module.CALL_GAP = 0.0
evaluator_module.BACKOFF_BASE = 0.0
evaluator_module.BACKOFF_CAP = 0.0
evaluator_module.MAX_CONSECUTIVE_FAILURES = 100

DRAFT = "You will not last the night, Watson."
TRAIT_IDS = ["aa", "bb", "cc", "dd", "ee", "ff", "gg", "hh"]
SPEC = {
    "persona": "stub 侦探", "not_ooc": [], "voice": {"forbidden_en": []},
    "_traits_by_id": {tid: {"id": tid, "name": f"轴{tid}", "severity": "soft", "rule": "r"}
                      for tid in TRAIT_IDS},
}
SPEC_HARD = {**SPEC, "_traits_by_id": {
    tid: {**SPEC["_traits_by_id"][tid], "severity": "hard" if tid == "aa" else "soft"}
    for tid in TRAIT_IDS}}

CLEAN = '{"hits": [], "ambiguity": []}'
SOFT_HIT = ('{"hits": [{"pattern": "以对方健康作冷嘲", "quote": "'
            + DRAFT
            + '", "severity": "soft"}], "ambiguity": []}')


class StubModel(ChatModel):
    """按 prompt 里的 trait 行分流回复；boom_on 指定的轴抛异常模拟调用失败。"""

    model = "stub"

    def __init__(self, reply_by_trait: dict[str, str] | None = None,
                 default: str = CLEAN, boom_on: str = "") -> None:
        self._by_trait = reply_by_trait or {}
        self._default = default
        self._boom_on = boom_on
        self.judge_calls = 0

    def complete(self, messages: list[dict]) -> str:
        content = str(messages[0].get("content", "")) + str(messages[1].get("content", ""))
        if "判定器" not in content:
            return DRAFT
        self.judge_calls += 1
        if self._boom_on and f"trait: {self._boom_on}" in content:
            raise ConnectionError(f"stub down: {self._boom_on}")
        for tid, reply in self._by_trait.items():
            if f"trait: {tid}" in content:
                return reply
        return self._default


def _entry(trait: str, severity: str, hits: list[dict], attempt: int = 1) -> BoardEntry:
    return BoardEntry(trait=trait, severity=severity, hits=hits, invalid=[],
                      ambiguity=[], failed="", prompt_chars=5, reply_chars=5,
                      parse_error=False, ms=1, attempt=attempt)


def _arbiter_graph(trait_order: list[str] | None = None,
                   merge: bool = False) -> object:
    """单节点图直调 Arbiter。trait_order 默认全 8 轴——缺板闸会拒绝只写一半的板，
    等价性用例只放两条轴时要把期望轴序收窄，否则测的是"缺板"而不是"聚合"。

    merge 默认 off：这些老用例锚定的是 v0.9.1 逐字节基线；落句合并的行为变化
    由第 21 号用例组（_arbiter_run / test_claims）显式开 merge 来测。
    """
    builder = StateGraph(GraphState)
    builder.add_node("arbiter", Arbiter(ScoreAggregator(),
                                         trait_order=trait_order or TRAIT_IDS,
                                         merge_claims_enabled=merge))
    builder.add_edge(START, "arbiter")
    builder.add_edge("arbiter", END)
    return builder.compile()


def _config(tag: str) -> dict:
    return {"configurable": {"thread_id": tag}}


# ── ① reducer 合并 ───────────────────────────────────────
def test_eight_sends_merge_without_loss_or_duplication() -> None:
    graph = build_graph(SPEC, StubModel(), StubModel(), agent_mode="blackboard")
    out = graph.invoke(new_state("华生想再去守一夜"), _config("merge8"))

    assert len(out["board"]) == 8, "8 个 Send 分支各写一条，不丢"
    traits = [e["trait"] for e in out["board"]]
    assert sorted(traits) == sorted(TRAIT_IDS), "不重、不缺"
    assert all(e["failed"] == "" and e["attempt"] == 1 for e in out["board"])
    assert out["score"] == 2


# ── ② 等价性：Arbiter vs 直调聚合 ────────────────────────
def test_arbiter_equals_direct_aggregator_field_by_field() -> None:
    hit_a = [{"pattern": "p1", "quote": DRAFT, "severity": "soft"}]
    results = [
        {"trait": "aa", "severity": "soft", "hits": hit_a, "invalid": [],
         "ambiguity": [], "parse_error": False, "prompt_chars": 5, "reply_chars": 5},
        {"trait": "bb", "severity": "soft", "hits": hit_a, "invalid": [],
         "ambiguity": [], "parse_error": False, "prompt_chars": 5, "reply_chars": 5},
    ]
    direct = ScoreAggregator().score(results, DRAFT)

    board = [_entry("aa", "soft", hit_a), _entry("bb", "soft", hit_a)]
    out = _arbiter_graph(trait_order=["aa", "bb"]).invoke(
        {"board": board, "draft": DRAFT, "attempt": 1, "trace": []})

    # 同句两条 soft：第二条落句被 aa 认领（dedup），n_soft=1 → score=1 —— 两边走的是同一个聚合
    assert out["score"] == direct["score"] == 1
    assert out["violated"] == summarize_hits(results)
    assert out["verify_incomplete"] is False
    assert out["verdicts"] == results, "verdicts 字段形状与 judge_trait 输出完全一致"


def _hard_reply() -> StubModel:
    return StubModel({"aa": ('{"hits": [{"pattern": "p", "quote": '
                             f'"You will not last the night, Watson.", '
                             '"severity": "hard"}], "ambiguity": []}')})


def _clone(tag: str) -> StubModel:
    if tag == "pass":
        return StubModel()
    if tag == "drift":
        return StubModel(default=SOFT_HIT)
    return _hard_reply()


def _run_to_end(graph: object, tag: str) -> dict:
    """跑到出口：若挂起则回 ABANDON，返回最终状态。"""
    out = graph.invoke(new_state("华生想再去守一夜"), _config(tag))
    if out.get("__interrupt__"):
        out = graph.invoke(Command(resume=ABANDON), _config(tag))
    return out


def test_modes_full_equivalence_on_score_fields() -> None:
    """同一批 stub 场景：simple 与 blackboard(merge=off) 的四个校验字段 + 出口字段全等。

    merge=off 是 v0.9.1 的逐字节基线，所以连 violated 的字面格式都要相等；
    merge=on 的输出变化是第 21 号任务书的**有意行为变化**，由下面的归因不变性用例单独管。
    三档都过一遍：pass（一稿 2 分）、drift（恒 1 分打到打满转人工）、hard（0 分）。
    """
    for tag in ("pass", "drift", "hard"):
        g_s = build_graph(SPEC_HARD, _clone(tag), _clone(tag), max_attempts=2)
        out_s = _run_to_end(g_s, f"eqs-{tag}")

        g_b = build_graph(SPEC_HARD, _clone(tag), _clone(tag), max_attempts=2,
                          agent_mode="blackboard", arbiter_merge=False)
        out_b = _run_to_end(g_b, f"eqb-{tag}")

        for field in ("score", "verdicts", "violated", "verify_incomplete",
                      "final", "needs_human", "attempt"):
            assert out_s[field] == out_b[field], f"{tag} 场景 {field} 不一致"
        assert tag != "pass" or out_s["score"] == 2, "pass 场景本身要对（防止两边同错）"
        # claims 通道由 new_state 初始化为空表（惰性），merge=off 的 Arbiter 绝不写它
        assert out_b["claims"] == [], "merge=off 裁决层不许碰 claims"


# ── 分轮板面：打回后的第 2 轮不许把第 1 轮的命中算进来 ────
def test_stale_rounds_are_not_scored() -> None:
    stale_hits = [{"pattern": "p", "quote": DRAFT, "severity": "soft"}]
    board = [_entry(t, "soft", stale_hits, attempt=1) for t in TRAIT_IDS[:4]] \
        + [_entry(t, "soft", [], attempt=2) for t in TRAIT_IDS]
    out = _arbiter_graph().invoke({"board": board, "draft": DRAFT, "attempt": 2, "trace": []})

    assert len(round_entries(board, 1)) == 4 and len(round_entries(board, 2)) == 8
    assert out["score"] == 2, "若误读第 1 轮旧命中，soft≥2 会算出 0 —— 那是分数变化"


# ── 失败路径：专家报伤亡不沉船，裁决者转人工 ──────────────
def test_expert_failure_becomes_incomplete_not_crash() -> None:
    model = StubModel(boom_on="cc")
    graph = build_graph(SPEC, model, model, max_attempts=1, agent_mode="blackboard")
    paused = graph.invoke(new_state("华生想再去守一夜"), _config("fail1"))

    payload = paused["__interrupt__"][0].value
    assert payload["score"] == -1, "缺一条规则不许当通过"
    out = graph.invoke(Command(resume=ABANDON), _config("fail1"))
    assert out["verify_incomplete"] is True and out["needs_human"] is True

    board = out["board"]
    assert sum(1 for e in board if e["attempt"] == 1) == 8, "8 条都在板上（含伤亡报告）"
    assert sum(1 for e in board if e["attempt"] == 1 and e["failed"]) == 1, "只有 cc 失败"
    assert sum(1 for e in board if e["attempt"] == 1 and not e["failed"]) == 7


# ── 任务 20 · 逐轴进度：专家发勾选，回调炸了也不许拖累判定 ────────
def test_blackboard_emits_per_axis_progress() -> None:
    seen: list[tuple] = []
    graph = build_graph(SPEC, StubModel(), StubModel(), agent_mode="blackboard",
                        on_progress=lambda *row: seen.append(row))
    graph.invoke(new_state("华生想再去守一夜"), _config("prog1"))

    assert len(seen) == 8, "8 个专家各发一行（成功分支）"
    assert {r[1] for r in seen} == set(TRAIT_IDS), "每轴恰好一次，不重不漏"
    assert all(r[0] == "draft#1" and r[2] is True for r in seen), \
        "cand_id 用 draft#轮次：Send 的 payload 里没有候选 id，这是闭环里仅有的身份"


def test_progress_reports_failure_and_swallows_hook_errors() -> None:
    seen: list[tuple] = []
    model = StubModel(boom_on="cc")
    graph = build_graph(SPEC, model, model, max_attempts=1, agent_mode="blackboard",
                        on_progress=lambda *row: seen.append(row))
    out = _run_to_end(graph, "prog2")

    fails = [r for r in seen if not r[2]]
    assert len(fails) == 1 and fails[0][1] == "cc" and "stub down" in fails[0][3], \
        "失败轴要报 ok=False 带原因，其余 7 轴正常报成功"
    assert len(seen) == 8 and out["score"] == -1

    def boom(*_row):
        raise RuntimeError("进度回调自己炸了")

    graph2 = build_graph(SPEC, StubModel(), StubModel(), agent_mode="blackboard",
                         on_progress=boom)
    out2 = graph2.invoke(new_state("华生想再去守一夜"), _config("prog3"))
    assert out2["score"] == 2, "硬约束：进度上报失败不许影响判定——丢一次进度，好过丢一轮结果"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"test_board OK：{len(tests)} 个用例通过")
