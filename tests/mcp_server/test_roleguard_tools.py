"""RoleGuardTools 的离线单测（假 evaluator，不联网、不装 MCP 客户端）。

跑法：python -m tests.mcp_server.test_roleguard_tools
"""

from __future__ import annotations

from src.mcp_server.roleguard_tools import RoleGuardTools

SPEC = {
    "traits": [
        {"id": "era_consistency", "name": "时代自洽", "severity": "hard",
         "rule": "禁止出现现代词汇", "anti_patterns": [{"level": "hard", "pattern": "出现DNA"}]},
        {"id": "watson_rapport", "name": "与华生", "severity": "soft",
         "rule": "不得以健康作冷嘲", "anti_patterns": [{"level": "soft", "pattern": "健康冷嘲"}]},
    ],
    "_traits_by_id": {},
}
SPEC["_traits_by_id"] = {t["id"]: t for t in SPEC["traits"]}


class FakeEvaluator:
    """记录被调用的参数，按预设返回聚合结果。"""

    def __init__(self, score: int = 2, failed: list[str] | None = None,
                 violations: list[dict] | None = None) -> None:
        self.score = score
        self.failed = failed or []
        self.violations = violations or []
        self.calls: list[dict] = []

    def judge_case(self, cand, traits, *, fanout=True):
        first_trait = next(iter(traits)) if isinstance(traits, dict) else (traits[0] if traits else "x")
        self.calls.append({"text": cand["text"], "traits": list(traits), "fanout": fanout})
        aggregate = {"score": self.score, "hard_hits": [], "soft_traits": [], "n_soft": 0, "deduped": []}
        results = [{"trait": first_trait, "severity": "hard", "hits": self.violations,
                    "invalid": [], "ambiguity": []}]
        return aggregate, results, self.failed


def test_list_traits_exposes_ids_and_severity() -> None:
    tools = RoleGuardTools(SPEC, FakeEvaluator())
    traits = tools.list_traits()
    assert [t["id"] for t in traits] == ["era_consistency", "watson_rapport"]
    assert traits[0]["severity"] == "hard"


def test_get_trait_rule_returns_rule_and_patterns() -> None:
    tools = RoleGuardTools(SPEC, FakeEvaluator())
    detail = tools.get_trait_rule("era_consistency")
    assert detail["rule"] == "禁止出现现代词汇"
    assert detail["anti_patterns"][0]["pattern"] == "出现DNA"


def test_unknown_trait_reports_available_list() -> None:
    tools = RoleGuardTools(SPEC, FakeEvaluator())
    detail = tools.get_trait_rule("nope")
    assert "error" in detail and "era_consistency" in detail["available"]


def test_judge_reply_passes_everything_by_default() -> None:
    evaluator = FakeEvaluator(score=2)
    tools = RoleGuardTools(SPEC, evaluator)
    out = tools.judge_reply("Go to bed, Watson.")
    assert out["score"] == 2 and out["label"].startswith("pass")
    assert len(evaluator.calls[0]["traits"]) == 2, "留空应判全部轴"
    assert evaluator.calls[0]["fanout"] is True


def test_judge_reply_can_limit_traits() -> None:
    evaluator = FakeEvaluator(score=1)
    tools = RoleGuardTools(SPEC, evaluator)
    out = tools.judge_reply("x", ["watson_rapport"])
    assert out["score"] == 1
    assert evaluator.calls[0]["traits"] == ["watson_rapport"]


def test_incomplete_is_not_reported_as_pass() -> None:
    tools = RoleGuardTools(SPEC, FakeEvaluator(score=2, failed=["era: timeout"]))
    out = tools.judge_reply("x")
    assert out["score"] == -1, "判定没跑完绝不能报 2"
    assert out["incomplete"] is True
    assert out["failed_traits"] == ["era: timeout"]


def test_empty_candidate_is_rejected() -> None:
    tools = RoleGuardTools(SPEC, FakeEvaluator())
    assert tools.judge_reply("   ")["score"] == -1


def test_violations_carry_quotes() -> None:
    violation = {"pattern": "出现DNA", "quote": "a DNA test", "severity": "hard"}
    tools = RoleGuardTools(SPEC, FakeEvaluator(score=0, violations=[violation]))
    out = tools.judge_reply("We can run a DNA test on the glass.")
    assert out["hit_count"] == 1
    assert "a DNA test" in out["violations"][0], "证据必须带可在原文定位的引文"


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"test_roleguard_tools OK：{len(tests)} 个用例通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
