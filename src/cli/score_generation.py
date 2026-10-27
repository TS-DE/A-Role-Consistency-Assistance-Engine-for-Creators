"""生成质量报告：读人工打分表 → 出指标。

    python -m src.cli.score_generation
    python -m src.cli.score_generation --csv data/gen_eval/gen_scores.csv

口径见 docs/10-生成质量评估.md。四条指标写死，不许事后改：
    均分 / 可用率（>=4）/ 硬伤率（任一 check 为 0）/ 改写增益（第 2 稿 − 首稿）
另外出"同向性"：按判定器分数分组看人工均分，验证自动指标和人眼方向一致。
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

from src.judge.constants import PROJECT_ROOT

DEFAULT_CSV = PROJECT_ROOT / "data" / "gen_eval" / "gen_scores.csv"
CHECKS = ("period_voice", "on_scene", "no_anachronism")
USABLE_THRESHOLD = 4


def load_rows(path: Path) -> list[dict[str, Any]]:
    """读已填写的行。空行、示例行、没打分的行一律跳过。"""
    if not path.exists():
        raise SystemExit(f"找不到打分表：{path}\n先照 docs/10 建表并填写。")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        raw = list(csv.DictReader(handle))

    rows: list[dict[str, Any]] = []
    for item in raw:
        sample = (item.get("sample_id") or "").strip()
        if not sample or sample.upper() == "EXAMPLE":
            continue
        score = (item.get("human_score") or "").strip()
        if not score:
            continue
        rows.append(
            {
                "sample_id": sample,
                "scene_id": (item.get("scene_id") or "").strip() or sample,
                "attempt": _as_int(item.get("attempt"), default=1),
                "source": (item.get("source") or "").strip() or "loop_generated",
                "judge_score": _as_int(item.get("judge_score"), default=-1),
                "human_score": _as_int(score, default=0),
                "checks": {name: _as_int(item.get(name), default=-1) for name in CHECKS},
                "notes": (item.get("notes") or "").strip(),
            }
        )
    return rows


def _as_int(value: Any, *, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """把明细压成指标。没填够的行不算，也不假装算出来。"""
    if not rows:
        return {"n": 0}

    scores = [row["human_score"] for row in rows]
    usable = [s for s in scores if s >= USABLE_THRESHOLD]
    flawed = [
        row for row in rows
        if any(row["checks"].get(name) == 0 for name in CHECKS)
    ]

    first = [r["human_score"] for r in rows if r["attempt"] <= 1]
    later = [r["human_score"] for r in rows if r["attempt"] >= 2]

    by_judge: dict[str, list[int]] = {}
    for row in rows:
        if row["judge_score"] < 0:
            continue
        by_judge.setdefault(str(row["judge_score"]), []).append(row["human_score"])

    return {
        "n": len(rows),
        "mean": _mean([float(s) for s in scores]),
        "usable_rate": len(usable) / len(rows),
        "flaw_rate": len(flawed) / len(rows),
        "first_mean": _mean([float(s) for s in first]),
        "later_mean": _mean([float(s) for s in later]),
        "rewrite_gain": (
            _mean([float(s) for s in later]) - _mean([float(s) for s in first])
            if first and later else None
        ),
        "by_judge": {key: _mean([float(s) for s in val]) for key, val in sorted(by_judge.items())},
        "incomplete_checks": sum(
            1 for row in rows if any(row["checks"].get(name) < 0 for name in CHECKS)
        ),
    }


def _fmt(value: float | None, suffix: str = "") -> str:
    return "n/a" if value is None else f"{value:.2f}{suffix}"


def print_report(rows: list[dict[str, Any]], stats: dict[str, Any]) -> None:
    print("=" * 58)
    print(f"样本数 {stats['n']}")
    if stats["n"] == 0:
        print("还没有已打分的行。照 docs/10 填 data/gen_eval/gen_scores.csv。")
        print("=" * 58)
        return

    print(f"均分            {_fmt(stats['mean'])} / 5")
    print(f"可用率（≥4）    {stats['usable_rate']:.1%}   ← 创作者实际关心的数")
    print(f"硬伤率（任一×） {stats['flaw_rate']:.1%}")
    print(f"改写增益        {_fmt(stats['rewrite_gain'])}   ← 第 2 稿 − 首稿，>0 才说明打回有用")
    print("同向性（判定器分 → 人工均分）")
    for key, value in stats["by_judge"].items():
        print(f"  judge_score={key}  →  {_fmt(value)}")
    if stats["incomplete_checks"]:
        print(f"⚠ 有 {stats['incomplete_checks']} 行三个 check 没填全，硬伤率会偏低")
    print("=" * 58)
    print("口径与效度威胁见 docs/10-生成质量评估.md 第六节：单评分者、n 小，只报趋势不报百分点。")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成质量人工评分汇总")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="打分表路径")
    args = parser.parse_args(argv)

    rows = load_rows(Path(args.csv))
    print_report(rows, summarise(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
