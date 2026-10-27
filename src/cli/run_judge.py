"""评测入口：批量跑候选，出三档指标。

    python -m src.cli.run_judge --fanout --cases tests/golden_holdout.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.judge.chat_model import ChatModel, ChatModelError, OpenAICompatChatModel
from src.judge.constants import GOLDEN_JSON, SCORE_PASS
from src.judge.env_loader import EnvLoader
from src.judge.evaluator import JudgeAborted, TraitEvaluator
from src.judge.prompt_builder import PromptBuilder
from src.judge.spec_loader import SpecLoader

PROBE_LABELS = {"leak": "0 档（漏杀探针）", "false_alarm": "2 档（误杀探针）", "boundary": "1 档（边界）"}


def _force_utf8_stdout() -> None:
    """GBK 控制台打印 ✅ 会抛 UnicodeEncodeError，跑到一半崩掉还白花钱。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="角色一致性判定器（批量评测）")
    parser.add_argument("--cases", help="测试集文件（默认 tests/golden_cases.json）")
    parser.add_argument("--limit", type=int, help="只跑前 N 条候选")
    parser.add_argument("--ids", help="只跑指定候选 id，逗号分隔")
    parser.add_argument("--trait", help="只跑某个 trait")
    parser.add_argument("--fanout", action="store_true", help="每条候选判定全部 trait 再聚合（推荐）")
    parser.add_argument("--repeat", type=int, default=1, help="同一候选重复判定 N 次，测 test-retest 稳定性")
    parser.add_argument("--json-out", help="把逐条结果写成 JSON")
    parser.add_argument("--dry", action="store_true", help="只打印第一条候选的 prompt，不发请求")
    parser.add_argument("--skip-preflight", action="store_true", help="跳过起跑前的连通性探测")
    return parser.parse_args(argv)


def _load_rows(args: argparse.Namespace) -> list[tuple[dict, dict]]:
    path = Path(args.cases) if args.cases else GOLDEN_JSON
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = [(case, cand) for case in payload["cases"] for cand in case["candidates"]]
    if args.trait:
        rows = [r for r in rows if r[1]["trait"] == args.trait]
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",") if x.strip()}
        rows = [r for r in rows if r[1]["id"] in wanted]
    if args.limit:
        rows = rows[: args.limit]
    return rows


def _build_model() -> ChatModel:
    EnvLoader().load()
    model_name = EnvLoader.get("JUDGE_MODEL", "LLM_MODEL")
    if not model_name:
        raise SystemExit("未配置 JUDGE_MODEL / LLM_MODEL")
    return OpenAICompatChatModel(model_name)


def _progress(cand_id: str, trait_id: str, ok: bool, message: str) -> None:
    if ok:
        print(f"      · {trait_id:<22s} ok")
    else:
        print(f"      · {trait_id:<22s} FAIL  {message[:70]}")


def _run_one(cand: dict, evaluator: TraitEvaluator, traits: dict,
             fanout: bool, repeats: int) -> dict[str, Any] | None:
    scores: list[int] = []
    last_agg: dict | None = None
    last_results: list[dict] = []
    failed_all: list[str] = []
    for _ in range(repeats):
        agg, results, failed = evaluator.judge_case(cand, traits, fanout=fanout)
        if failed:
            failed_all += failed
            break
        scores.append(agg["score"])
        last_agg, last_results = agg, results
    if not scores or last_agg is None:
        return None
    sys_score = max(set(scores), key=scores.count) if repeats > 1 else scores[0]
    return {
        "id": cand["id"], "trait": cand["trait"], "probe": cand["probe"], "gold": cand["gold"],
        "sys": sys_score, "repeat_scores": scores, "stable": len(set(scores)) == 1,
        "hard_hits": last_agg["hard_hits"], "soft_traits": last_agg["soft_traits"],
        "n_soft": last_agg["n_soft"],
        "hits": [{"trait": r["trait"], **h} for r in last_results for h in r["hits"]],
        "invalid": [{"trait": r["trait"], **h} for r in last_results for h in r["invalid"]],
        "ambiguity": [{"trait": r["trait"], "text": a} for r in last_results for a in r["ambiguity"]],
        "_results": last_results,
    }


def _print_details(results: list[dict]) -> None:
    for result in results:
        for hit in result["hits"]:
            print(f"          ✓ [{result['trait']}] {hit.get('pattern', '?')} → \"{hit.get('quote', '')}\"")
        for hit in result["invalid"]:
            print(f"          ✗引文无效 [{result['trait']}] {hit.get('quote', '')} ({hit.get('_reason')})")
        for note in result["ambiguity"]:
            print(f"          ? [{result['trait']}] {note}")


def _print_summary(checked: list[dict], incomplete: list[str], repeats: int) -> None:
    def rate(probe: str) -> tuple[int, int]:
        subset = [c for c in checked if c["probe"] == probe]
        return sum(c["gold"] == c["sys"] for c in subset), len(subset)

    def pct(a: int, b: int) -> str:
        return f"{a / b:.1%}" if b else "n/a"

    total_ok = sum(c["gold"] == c["sys"] for c in checked)
    print("\n" + "=" * 62)
    print(f"有效样本       {len(checked)}/{len(checked) + len(incomplete)}"
          + (f"（未完成：{', '.join(incomplete)}）" if incomplete else ""))
    print(f"全量一致率     {total_ok}/{len(checked)} = {pct(total_ok, len(checked))}   ← 分母只含完整样本")
    for probe, label in PROBE_LABELS.items():
        ok, n = rate(probe)
        print(f"{label:<14s}{ok}/{n} = {pct(ok, n)}")
    if repeats > 1:
        stable = sum(1 for c in checked if c["stable"])
        print(f"自我一致率     {stable}/{len(checked)} = {pct(stable, len(checked))}   ← test-retest")
        flaky = [c["id"] for c in checked if not c["stable"]]
        if flaky:
            print(f"结论会翻转的：{', '.join(flaky)}")
    invalid = sum(len(c["invalid"]) for c in checked)
    notes = sum(len(c["ambiguity"]) for c in checked)
    print(f"被拒引文 {invalid} 条 / ambiguity {notes} 条   ← 编造引文的量比准确率更能说明判定器老不老实")
    print("=" * 62)
    if incomplete:
        print("⚠ 有未完成样本：它们的聚合分不可信，补跑后再出数，别把本次当结论。")


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    args = _parse_args(argv)
    spec = SpecLoader().load()
    traits = spec["_traits_by_id"]
    rows = _load_rows(args)
    repeats = max(1, args.repeat)
    if not rows:
        print("没有匹配的候选。")
        return 1

    if args.dry:
        _candidate = rows[0][1]
        for message in PromptBuilder(spec).build(_candidate["text"], traits[_candidate["trait"]]):
            print(f"\n--- {message['role']}（{len(message['content'])} 字符）---\n{message['content']}")
        print(f"\n共 {len(rows)} 条候选待跑。看完删掉 --dry 再跑。")
        return 0

    model = _build_model()
    if not args.skip_preflight:
        print(f"起跑前连通性探测（{model.model}）…", flush=True)
        try:
            model.preflight()
            print("  连通正常，开始评测\n", flush=True)
        except ChatModelError as exc:
            print(f"  探测失败，立即中止：{exc}")
            print("  网络恢复后重跑；确实要跳过探测可加 --skip-preflight")
            return 2

    if args.fanout:
        print(f"fanout：{len(rows)} 条候选 × {len(traits)} 条 trait × {repeats} 轮 = "
              f"{len(rows) * len(traits) * repeats} 次调用\n", flush=True)

    evaluator = TraitEvaluator(spec, model, on_progress=_progress)
    checked: list[dict] = []
    incomplete: list[str] = []
    try:
        for index, (_case, cand) in enumerate(rows, 1):
            print(f"[{index}/{len(rows)}] {cand['id']}", flush=True)
            record = _run_one(cand, evaluator, traits, args.fanout, repeats)
            if record is None:
                print(f"      ⚠ 未完成，不计入统计")
                incomplete.append(cand["id"])
                continue
            _print_details(record.pop("_results"))
            mark = "✅" if record["sys"] == cand["gold"] else "❌"
            extra = "" if repeats == 1 else f"  scores={record['repeat_scores']}"
            print(f"    → gold={cand['gold']} sys={record['sys']} {mark}{extra}", flush=True)
            record["trait"] = cand["trait"]
            record["probe"] = cand["probe"]
            checked.append(record)
    except JudgeAborted as exc:
        print(f"\n中止：{exc}")
        print("已完成的样本仍会汇总，但不足以当结论。")

    if not checked:
        print("没有可统计的结果。")
        return 1
    _print_summary(checked, incomplete, repeats)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(checked, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写入 {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
