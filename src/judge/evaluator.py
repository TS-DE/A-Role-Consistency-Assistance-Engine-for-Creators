"""编排：逐 trait 取证 → 聚合 → 完整性标记。只依赖 ChatModel 抽象。"""

from __future__ import annotations

from typing import Any, Callable

from src.judge.aggregator import ScoreAggregator
from src.judge.chat_model import ChatModel
from src.judge.constants import MAX_CONSECUTIVE_FAILURES
from src.judge.hit_parser import HitParser
from src.judge.prompt_builder import PromptBuilder
from src.judge.quote_validator import QuoteValidator

# (候选 id, trait id, 是否成功, 附注)
ProgressHook = Callable[[str, str, bool, str], None]


class JudgeAborted(RuntimeError):
    """连续失败过多：判定网络不可用，整批中止，别继续烧时间。"""


class TraitEvaluator:
    """一次判定的完整编排。状态只有"连续失败计数"，其余都是纯计算。"""

    def __init__(
        self,
        spec: dict[str, Any],
        model: ChatModel,
        on_progress: ProgressHook | None = None,
    ) -> None:
        self._model = model
        self._prompts = PromptBuilder(spec)
        self._parser = HitParser()
        self._validator = QuoteValidator()
        self._aggregator = ScoreAggregator(self._validator)
        self._on_progress = on_progress
        self._consecutive_failures = 0

    def judge_trait(self, candidate: str, trait: dict[str, Any]) -> dict[str, Any]:
        """判一条 trait：取证（模型）→ 解析 → 引文校验。"""
        raw = self._model.complete(self._prompts.build(candidate, trait))
        parsed = self._parser.parse(raw)
        passed, rejected = self._validator.validate(parsed["hits"], candidate)
        return {
            "trait": trait["id"],
            "severity": trait["severity"],
            "hits": passed,
            "invalid": rejected,
            "ambiguity": parsed["ambiguity"],
            "parse_error": parsed["parse_error"],
        }

    def judge_case(
        self,
        cand: dict[str, Any],
        traits: dict[str, Any],
        *,
        fanout: bool,
    ) -> tuple[dict[str, Any], list[dict], list[str]]:
        """判一条候选。返回 (聚合结果, 每 trait 明细, 失败列表)。

        任何一条 trait 失败，这条候选就不可信（缺 trait 的 soft 计数可能恰好等于 gold，
        那是假通过），所以失败列表要交给上层标记 incomplete。
        """
        trait_ids = list(traits) if fanout else [cand["trait"]]
        results: list[dict] = []
        failed: list[str] = []
        for trait_id in trait_ids:
            try:
                results.append(self.judge_trait(cand["text"], traits[trait_id]))
                self._consecutive_failures = 0
                self._emit(cand["id"], trait_id, True, "")
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{trait_id}: {exc}")
                self._consecutive_failures += 1
                self._emit(cand["id"], trait_id, False, str(exc))
                if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    raise JudgeAborted(
                        f"连续 {self._consecutive_failures} 次调用失败，判定网络不可用：{exc}"
                    ) from exc
        return self._aggregator.score(results, cand["text"]), results, failed

    def _emit(self, cand_id: str, trait_id: str, ok: bool, message: str) -> None:
        if self._on_progress is not None:
            self._on_progress(cand_id, trait_id, ok, message)
