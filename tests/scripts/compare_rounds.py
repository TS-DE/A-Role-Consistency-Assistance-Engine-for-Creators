#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多方对比：gold vs 各标注者

支持"部分覆盖"的标注者（例如只打了分歧项的轮次）：覆盖率不足 31 条也照样算，
只是在相关对比对里分母变小，并在报表里标注 coverage。

标注者来源两种：
  json —— 遮罩副本的 my_score 字段（A01 / A02 / A03）
  md   —— scoring_rounds.md 的某一轮表格（H = 第一轮，H2 = 第二轮）

运行:  py -3 tests/compare_rounds.py
输出:  reports/compare_data.md / reports/compare_data.json
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = ROOT / "data" / "golden" / "golden_cases.json"
HUMAN_MD = ROOT / "scoring_rounds.md"

SOURCES = {
    "A01": ("json", ROOT / "test_A01" / "golden_cases_masked_A01.json", None),
    "A02": ("json", ROOT / "test_A02" / "golden_cases_maskes_A02.json", None),
    "A03": ("json", ROOT / "test_A03" / "golden_cases_masked_A03.json", None),
    "H":   ("md", None, "round1"),
    "H2":  ("md", None, "round2"),
}

OUT_MD = ROOT / "reports" / "compare_data.md"
OUT_JSON = ROOT / "reports" / "compare_data.json"

ROW = re.compile(r"^\|\s*(D\d{2}-[a-d])\s*\|[^|]*\|\s*([012])\s*\|")


def load_gold():
    data = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    return {c["id"]: {**c, "case": case["id"], "category": case["category"],
                      "probe": c.get("probe", "?")}
            for case in data["cases"] for c in case["candidates"]}


def load_round_json(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {c["id"]: int(c["my_score"])
            for case in data["cases"] for c in case["candidates"]
            if c.get("my_score") is not None}


def _table_slice(path: Path, start_marker: str, end_marker: str) -> dict[str, int]:
    """截取某两张小标题之间的表格行。

    必须切片：文件里『两轮一致率对照』『争议项复核』的行首同样是 D06-a、列里也有 0/1/2，
    不切片会静默读到 gold 列，覆盖掉真实分数。
    """
    out, inside = {}, False
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not inside:
            if s.startswith(start_marker):
                inside = True
            continue
        if s.startswith(end_marker):
            break
        m = ROW.match(s)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def load_round_md(which: str) -> dict[str, int]:
    if which == "round1":
        return _table_slice(HUMAN_MD, "## 第一轮", "### 第一轮小结")
    return _table_slice(HUMAN_MD, "## 第二轮", "### 第二轮小结")


def agreement(a, b, ids):
    ids = [i for i in ids if a.get(i) is not None and b.get(i) is not None]
    return sum(1 for i in ids if a[i] == b[i]), len(ids)


def qwk(a, b, ids):
    ids = [i for i in ids if a.get(i) is not None and b.get(i) is not None]
    n = len(ids)
    if not n:
        return float("nan")
    obs = Counter((a[i], b[i]) for i in ids)
    ha = Counter(a[i] for i in ids)
    hb = Counter(b[i] for i in ids)
    num = den = 0.0
    for x in (0, 1, 2):
        for y in (0, 1, 2):
            w = ((x - y) ** 2) / 4.0
            num += w * obs.get((x, y), 0)
            den += w * ha[x] * hb[y] / n
    return 1.0 - num / den if den else 1.0


def main() -> int:
    gold = load_gold()
    ids = sorted(gold)
    scores = {"gold": {i: gold[i]["gold"] for i in ids}}
    for name, (kind, jpath, which) in SOURCES.items():
        sc = load_round_json(jpath) if kind == "json" else load_round_md(which)
        if sc:
            scores[name] = sc
    raters = [k for k in scores if k != "gold"]

    rows = []
    for i in ids:
        votes = {k: scores[k].get(i) for k in ["gold"] + raters}
        present = [v for v in votes.values() if v is not None]
        uniq = set(present)
        if len(uniq) == 1:
            kind = "—"
        elif len(uniq) == len(present):
            kind = "全分裂"
        else:
            cnt = Counter(present)
            kind = "离群:" + "/".join(k for k, v in votes.items()
                                     if v is not None and cnt[v] == 1)
        rows.append({"id": i, **{k: gold[i][k] for k in ("trait", "probe")},
                     **votes, "agree_all": len(uniq) == 1, "kind": kind})

    pairs = {}
    for a, b in combinations(["gold"] + raters, 2):
        same, n = agreement(scores[a], scores[b], ids)
        pairs[f"{a}-{b}"] = {"same": same, "n": n,
                             "pct": round(100 * same / n, 1) if n else None,
                             "qwk": round(qwk(scores[a], scores[b], ids), 3) if n else None}

    coverage = {k: sum(1 for i in ids if scores[k].get(i) is not None) for k in raters}

    # 全同率只在"全体覆盖"的标注者上算。若只有部分轮次（如 H2 只补了 8 条分歧），
    # 它会被排除在 core 之外 —— 否则会拿"分歧项集合"当总体样本，得到 12.5% 这种假数字。
    core = [k for k in raters if coverage[k] == len(ids)]
    core_rows = [r for r in rows if all(r[k] is not None for k in ["gold"] + core)]
    allagree = sum(1 for r in core_rows if r["agree_all"])
    allagree_scope = f"{len(core)+1} 方（gold+{'+'.join(core)}）在全量 {len(core_rows)} 条上"
    diverged = [r for r in rows if not r["agree_all"]]

    L = ["# 多方对比数据（gold vs 各标注者）\n",
         "> 由 `tests/compare_rounds.py` 自动生成，勿手改。",
         "> 手写分析：`docs/04`（三方）、`docs/06`（首轮人工）、`docs/07`（A03 泄漏审计）。\n",
         f"\n- 样本：{len(rows)} 条判定样本（12 条输入）",
         "- 覆盖率：" + "，".join(f"{k} {v}/{len(rows)}" for k, v in coverage.items()) + "\n"]

    L.append("\n## 1. 两两一致率\n")
    L.append("| 对比对 | 相同 / 可比 | 一致率 | 二次加权 κ |")
    L.append("| --- | --- | --- | --- |")
    for k, v in pairs.items():
        L.append(f"| {k} | {v['same']}/{v['n']} | {v['pct']}% | {v['qwk']} |")
    L.append(f"\n**{allagree_scope}，全同：{allagree}/{len(core_rows)} = "
             f"{100*allagree/len(core_rows):.1f}%**")
    if core != raters:
        L.append(f"\n> 覆盖率不足的轮次（{', '.join(k for k in raters if k not in core)}）不计入全同率，"
                 "只看它自己的两两对比。")

    L.append("\n## 2. 明细\n")
    hdr = " | ".join(["候选", "trait", "probe", "gold"] + raters)
    L.append(f"| {hdr} | 全同? |")
    L.append("| " + " | ".join(["---"] * (4 + len(raters) + 1)) + " |")
    for r in rows:
        vals = " | ".join(str(r["id"] if k == "id" else ("—" if r[k] is None else r[k]))
                          for k in ["id", "trait", "probe", "gold"] + raters)
        L.append(f"| {vals} | {'✅' if r['agree_all'] else '❌'} |")

    L.append("\n## 3. 分歧清单\n")
    for r in diverged:
        L.append(f"- `{r['id']}`（" + " / ".join(
            f"{k}={'—' if r[k] is None else r[k]}" for k in ["gold"] + raters)
            + f"）　{r['kind']}")

    L.append("\n## 4. 各标注者对 gold 的错误方向\n")
    L.append("| 标注者 | leak 漏杀(gold=0 判高) | false_alarm 误杀(gold=2 判低) | boundary 错档 |")
    L.append("| --- | --- | --- | --- |")
    for k in raters:
        c = Counter(gold[i]["probe"] for i in ids
                    if scores[k].get(i) is not None and scores[k][i] != gold[i]["gold"])
        L.append(f"| {k} | {c.get('leak', 0)} | {c.get('false_alarm', 0)} | {c.get('boundary', 0)} |")

    OUT_MD.parent.mkdir(exist_ok=True)
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(
        {"pairs": pairs, "coverage": coverage, "core": core,
         "all_agree": {"same": allagree, "n": len(core_rows), "scope": allagree_scope},
         "diverged": [{k: r[k] for k in ["id", "gold"] + raters} for r in diverged]},
        ensure_ascii=False, indent=2), encoding="utf-8")

    print("raters:", raters, "coverage:", coverage, "core:", core)
    for k, v in pairs.items():
        print(f"  {k}: {v['same']}/{v['n']} = {v['pct']}%  qwk={v['qwk']}")
    print(f"  ALL: {allagree}/{len(core_rows)} = {100*allagree/len(core_rows):.1f}%  [{allagree_scope}]")
    print("diverged:", [(r["id"], *[r[k] for k in ["gold"] + raters]) for r in diverged])
    return 0


if __name__ == "__main__":
    sys.exit(main())
