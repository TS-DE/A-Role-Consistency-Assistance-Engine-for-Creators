"""路由决策：校验完之后，这条草稿该往哪走。

单独成文件的原因：这是**产品决策**，不是实现细节。
把它写成纯函数，冒烟脚本和 LangGraph 的条件边就能共用同一份判断——
否则两处各写一遍，迟早漂移出"演示时打回、上线时放行"的经典事故。

规格来源（2026-10-27 与作者确认）：
  1. score == 2           → 出口
  2. score == 0 或 1      → 打回重写（drift 也打回，宁可多花一次调用）
  3. 打回满 max_attempts 次仍 < 2 → 转人工
  4. verify_incomplete    → **立刻**转人工，不重试
"""

from __future__ import annotations

from src.judge.constants import SCORE_PASS

PASS = "pass"
REWRITE = "rewrite"
HUMAN = "human"


def decide(
    score: int,
    attempt: int,
    incomplete: bool,
    max_attempts: int,
) -> str:
    """返回 PASS / REWRITE / HUMAN 之一。

    参数：
        score       校验节点的三档分（0/1/2/-1）
        attempt     已经生成过几次（1 表示这是第一稿）
        incomplete  校验是否有 trait 调用失败
        max_attempts 最多允许生成几次

    为什么 incomplete 优先于一切：判定器没跑完时，score 是 -1，
    它既不是"通过"也不是"违规"。这时重试只会更烧钱，而且网络不通时
    会一路重试到天亮 —— 交给人是唯一不会失控的出路。
    """
    if incomplete:
        return HUMAN
    if score == SCORE_PASS:
        return PASS
    if attempt >= max_attempts:
        return HUMAN
    return REWRITE


def explain(action: str, score: int, attempt: int, incomplete: bool) -> str:
    """给 CLI 和人看的一句话理由。别让路由变成黑盒。"""
    if action == PASS:
        return "三档判定为 2（符合），直接出口"
    if action == REWRITE:
        why = "命中 hard 违规" if score == 0 else "轻微漂移（score=1）"
        return f"{why}，第 {attempt} 稿打回重写"
    if incomplete:
        return "校验未完成（有 trait 调用失败），转人工——不重试，避免死循环烧钱"
    return f"已打回 {attempt} 次仍低于 2 分，转人工裁决"
