"""编排：逐 trait 取证 → 聚合 → 完整性标记。只依赖 ChatModel 抽象。"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from src.judge.aggregator import ScoreAggregator
from src.judge.chat_model import ChatModel
from src.judge.constants import (
    BACKOFF_BASE,
    BACKOFF_CAP,
    CALL_GAP,
    MAX_CONSECUTIVE_FAILURES,
    MAX_JUDGE_WORKERS,
    MISSING_RETRIES,
)
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
        """判一条 trait：取证（模型）→ 解析 → 引文校验。

        顺带记录 prompt / 回复的字符数 —— 成本表要靠它，而 tokens 只能估算，
        字符数是实测的，把实测值留全，估算才有据可依。
        """
        messages = self._prompts.build(candidate, trait)
        prompt_chars = sum(len(str(m.get("content", ""))) for m in messages)
        raw = self._model.complete(messages)
        parsed = self._parser.parse(raw)
        passed, rejected = self._validator.validate(parsed["hits"], candidate)
        return {
            "trait": trait["id"],
            "severity": trait["severity"],
            "hits": passed,
            "invalid": rejected,
            "ambiguity": parsed["ambiguity"],
            "parse_error": parsed["parse_error"],
            "prompt_chars": prompt_chars,
            "reply_chars": len(raw),
        }

    def judge_case(
        self,
        cand: dict[str, Any],
        traits: dict[str, Any],
        *,
        fanout: bool,
        missing_retries: int = MISSING_RETRIES,
    ) -> tuple[dict[str, Any], list[dict], list[str]]:
        """判一条候选。返回 (聚合结果, 每 trait 明细, 失败列表)。

        8 条 trait 彼此独立，所以并发跑：实测串行 155s / 轮，并发后降到 40s 量级。
        分页与重试逻辑不变，只有"怎么发"变了。
        """
        trait_ids = list(traits) if fanout else [cand["trait"]]
        results: list[dict] = []
        pending: list[str] = list(trait_ids)
        failures: dict[str, str] = {}

        for attempt in range(max(0, missing_retries) + 1):
            if attempt:
                time.sleep(min(BACKOFF_CAP, BACKOFF_BASE * (2 ** attempt)))
            batch = self._run_batch(cand["text"], traits, pending)

            still_failed: list[str] = []
            for trait_id, outcome in batch:
                if isinstance(outcome, Exception):
                    still_failed.append(trait_id)
                    failures[trait_id] = str(outcome)
                    self._consecutive_failures += 1
                    self._emit(cand["id"], trait_id, False, str(outcome))
                else:
                    results.append(outcome)
                    failures.pop(trait_id, None)
                    self._consecutive_failures = 0
                    self._emit(cand["id"], trait_id, True, "")

            if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                # 把最近两条失败原因带上：只说"网络不可用"等于让人猜，
                # 而 429（限流）与 DNS（断网）的处理方式完全不同。
                reasons = "; ".join(list(failures.values())[:2])
                raise JudgeAborted(
                    f"连续 {self._consecutive_failures} 次调用失败，判定中断：{reasons[:200]}"
                )
            pending = still_failed
            if not pending:
                break

        return (
            self._aggregator.score(results, cand["text"]),
            results,
            [f"{trait}: {msg}" for trait, msg in failures.items()],
        )

    def _run_batch(
        self, text: str, traits: dict[str, Any], trait_ids: list[str]
    ) -> list[tuple[str, Any]]:
        """跑一批 trait，返回 [(trait_id, 结果或异常)]，顺序与入参一致。"""
        if len(trait_ids) <= 1 or MAX_JUDGE_WORKERS <= 1:
            outcomes: list[tuple[str, Any]] = []
            for trait_id in trait_ids:
                try:
                    outcomes.append((trait_id, self.judge_trait(text, traits[trait_id])))
                except Exception as exc:  # noqa: BLE001
                    outcomes.append((trait_id, exc))
                if CALL_GAP:
                    time.sleep(CALL_GAP)
            return outcomes

        collected: dict[str, Any] = {}
        workers = min(MAX_JUDGE_WORKERS, len(trait_ids))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self.judge_trait, text, traits[trait_id]): trait_id
                for trait_id in trait_ids
            }
            for future in as_completed(futures):
                trait_id = futures[future]
                try:
                    collected[trait_id] = future.result()
                except Exception as exc:  # noqa: BLE001
                    collected[trait_id] = exc
        return [(trait_id, collected[trait_id]) for trait_id in trait_ids]

    def emit_progress(self, cand_id: str, trait_id: str, ok: bool, message: str = "") -> None:
        """供黑板模式的专家节点按轴回调进度；judge_case 内部仍走 _emit，行为不变。

        回调自身的异常在这里吞掉（硬约束：进度上报失败不得影响判定结果）——
        专家节点在 try/except 之外调用本方法，若让它冒泡就会中断整张图。
        """
        try:
            self._emit(cand_id, trait_id, ok, message)
        except Exception:  # noqa: BLE001  只吞不报：进度丢一次，好过判定结果丢一轮
            pass

    def has_progress_hook(self) -> bool:
        return self._on_progress is not None

    def _emit(self, cand_id: str, trait_id: str, ok: bool, message: str) -> None:
        if self._on_progress is not None:
            self._on_progress(cand_id, trait_id, ok, message)
