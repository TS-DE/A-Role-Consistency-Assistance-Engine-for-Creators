#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多方对比：gold vs 各标注者（两个独立模型 A01/A02 + 人工首轮 H）

用途
----
docs/01-一致性规格书.md 的 DoD 要求"一致率 >= 90%"。人工第二轮尚未打，
所以现在能算的是**跨标注者一致率**（inter-rater / 人机一致率），
它比 test-retest 更硬：能扛住不同读者，才谈得上"换个人打出同一个分"。

标注者是可为空的：文件里 my_score 全为 null（还没打）会自动跳过，不算失败。
人工轮从 scoring_rounds.md 的第一轮表格解析。

输出
----
reports/compare_data.md   明细 + 统计（供 docs/04、docs/06 引用）
reports/compare_data.json 机器可读结果

运行
----
    py -3 tests/compare_rounds.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "tests" / "golden_cases.json"

# 标注者：名字 -> 来源（json 遮罩副本，或 md 评分记录的第一轮表）
SOURCES = {
    "A01": ("json", ROOT / "test_A01" / "golden_cases_masked_A01.json",
            ROOT / "test_A01" / "scoring_rounds_A01.md"),
    "A02": ("json", ROOT / "test_A02" / "golden_cases_maskes_A02.json",
            ROOT / "test_A02" / "scoring_rounds_A02.md"),
    "H":   ("md", None, ROOT / "scoring_rounds.md"),
}

OUT_MD = ROOT / "reports" / "compare_data.md"
OUT_JSON = ROOT / "reports" / "compare_data.json"


# ---------------------------------------------------------------- load

def load_gold() -> dict[str, dict]:
    data = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    out = {}
    for case in data["cases"]:
        for cand in case["candidates"]:
            out[cand["id"]] = {
                "case": case["id"],
                "trait": cand["trait"],
                "category": case["category"],
                "probe": cand.get("probe", "?"),
                "gold": cand["gold"],
                "text": cand["text"],
            }
    return out


def load_round_json(path: Path) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for case in data["cases"]:
        for cand in case["candidates"]:
            if cand.get("my_score") is not None:
                out[cand["id"]] = int(cand["my_score"])
    return out


ROW = re.compile(r"^\|\s*(D\d{2}-[a-d])\s*\|[^|]*\|\s*([012])\s*\|")


def load_round_md(path: Path) -> dict[str, int]:
    """只抽『第一轮』那张表的分数。

    注意：文件里后面还有『两轮一致率对照』和『争议项复核』两张表，行首同样是 D06-a 这类 id，
    列里也有数字。所以必须在第一轮结束处停下，否则会用 gold 列覆盖第一轮的分数。
    """
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("### 第一轮小结") or s.startswith("## 第二轮"):
            break
        m = ROW.match(s)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def load_all(gold_ids: list[str]) -> tuple[dict[str, dict[str, int]], list[str]]:
    scores: dict[str, dict[str, int]] = {"gold": {}}
    notes: list[str] = []
    for name, (kind, jpath, mpath) in SOURCES.items():
        if kind == "json":
            js = load_round_json(jpath)
            md = load_round_md(mpath) if mpath.exists() else {}
            diff = {i for i in set(js) & set(md) if js[i] != md[i]}
            if diff:
                notes.append(f"{name}: json 与 md 分数不一致 -> {sorted(diff)}")
            sc = js
        else:
            sc = load_round_md(mpath)
        missing = set(gold_ids) - set(sc)
        if missing:
            notes.append(f"{name}: 缺 {len(missing)} 条（{sorted(missing)}）—— 未完成，本轮跳过")
            continue
        scores[name] = sc
    return scores, notes


# ---------------------------------------------------------------- metrics

def agreement(a: dict[str, int], b: dict[str, int]) -> tuple[int, int]:
    ids = sorted(set(a) & set(b))
    return sum(1 for i in ids if a[i] == b[i]), len(ids)


def confusion(a: dict[str, int], b: dict[str, int]) -> Counter:
    return Counter((a[i], b[i]) for i in sorted(set(a) & set(b)))


def qwk(a: dict[str, int], b: dict[str, int]) -> float:
    """三类有序标签的二次加权 kappa：2↔0 比 1↔2 严重得多。"""
    ids = sorted(set(a) & set(b))
    n = len(ids)
    if not n:
        return float("nan")
    obs, ha, hb = confusion(a, b), Counter(), Counter()
    for i in ids:
        ha[a[i]] += 1
        hb[b[i]] += 1
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
    scores, notes = load_all(ids)
    scores["gold"] = {i: gold[i]["gold"] for i in ids}
    raters = [k for k in scores if k != "gold"]

    rows = []
    for i in ids:
        votes = {"gold": gold[i]["gold"], **{r: scores[r][i] for r in raters}}
        uniq = set(votes.values())
        if len(uniq) == 1:
            kind = "—"
        elif len(uniq) == len(votes):
            kind = "全分裂"
        else:
            cnt = Counter(votes.values())
            kind = "离群:" + "/".join(n for n, v in votes.items() if cnt[v] == 1)
        rows.append({"id": i, **{k: gold[i][k] for k in ("trait", "probe", "text")},
                     **votes, "agree_all": len(uniq) == 1, "kind": kind})

    pairs = {}
    for a, b in combinations(["gold"] + raters, 2):
        same, n = agreement(scores[a], scores[b])
        pairs[f"{a}-{b}"] = {"same": same, "n": n, "pct": round(100 * same / n, 1),
                             "qwk": round(qwk(scores[a], scores[b]), 3)}

    allagree = sum(1 for r in rows if r["agree_all"])
    diverged = [r for r in rows if not r["agree_all"]]

    probe_err, confuse, ooc = {}, {}, {}
    for r in raters:
        c = Counter(rows_["probe"] for rows_ in rows if rows_[r] != rows_["gold"])
        probe_err[r] = dict(c)
        confuse[r] = confusion(scores[r], scores["gold"])
        ooc[r] = sum(1 for i in ids if scores[r][i] == 0)
    ooc["gold"] = sum(1 for i in ids if gold[i]["gold"] == 0)
    dist = {k: dict(Counter(scores[k][i] for i in ids)) for k in ["gold"] + raters}

    # ------------------------------------------------------------ output
    OUT_MD.parent.mkdir(exist_ok=True)
    L = ["# 多方对比数据（gold vs 各标注者）\n",
         "> 由 `tests/compare_rounds.py` 自动生成，勿手改。",
         "> 手写分析：`docs/04-三方对比与规格书漏洞.md`、`docs/06-首轮人工评分校正.md`。\n",
         f"\n- 样本：{len(rows)} 条判定样本（12 条输入）",
         f"- 标注者：{', '.join(raters)}",
         f"- 分布：" + " / ".join(f"{k} {dist[k]}" for k in ["gold"] + raters),
         f"- OOC 率：" + " / ".join(f"{k} {ooc[k]}/{len(rows)} = {100*ooc[k]/len(rows):.1f}%"
                                   for k in ["gold"] + raters) + "\n"]

    L.append("\n## 1. 两两一致率与加权 kappa\n")
    L.append("| 对比对 | 相同 / 总数 | 一致率 | 二次加权 kappa |")
    L.append("| --- | --- | --- | --- |")
    for k, v in pairs.items():
        L.append(f"| {k} | {v['same']}/{v['n']} | {v['pct']}% | {v['qwk']} |")

    L.append(f"\n## 2. 全体一致率\n")
    L.append(f"**{allagree}/{len(rows)} = {100*allagree/len(rows):.1f}%**（{len(raters)+1} 方全同）")

    L.append("\n## 3. 明细\n")
    hdr = " | ".join(["候选", "trait", "probe", "gold"] + raters)
    L.append(f"| {hdr} | 全同? | 分歧类型 |")
    L.append("| " + " | ".join(["---"] * (4 + len(raters) + 2)) + " |")
    for r in rows:
        vals = " | ".join(str(r[x]) for x in ["id", "trait", "probe", "gold"] + raters)
        L.append(f"| {vals} | {'✅' if r['agree_all'] else '❌'} | {r['kind']} |")

    L.append("\n## 4. 分歧清单\n")
    for r in diverged:
        L.append(f"### {r['id']}（" + " / ".join(f"{k}={r[k]}" for k in ["gold"] + raters) + "）\n")
        L.append(f"- trait: `{r['trait']}`　probe: `{r['probe']}`")
        L.append(f"- 原文：`{r['text']}`\n")

    L.append("\n## 5. 各标注者错误按探针类型\n")
    L.append("| 标注者 | leak 漏杀 | false_alarm 误杀 | boundary 错档 |")
    L.append("| --- | --- | --- | --- |")
    for r in raters:
        p = probe_err[r]
        L.append(f"| {r} | {p.get('leak', 0)} | {p.get('false_alarm', 0)} | {p.get('boundary', 0)} |")

    L.append("\n## 6. 混淆矩阵（行=标注者，列=gold）\n")
    for r in raters:
        L.append(f"\n**{r}**\n")
        L.append("| 标注者 \\ gold | 0 | 1 | 2 |")
        L.append("| --- | --- | --- | --- |")
        for x in (0, 1, 2):
            L.append(f"| {x} | " + " | ".join(str(confuse[r].get((x, y), 0)) for y in (0, 1, 2)) + " |")

    if notes:
        L.append("\n## ⚠ 数据说明\n")
        for n in notes:
            L.append(f"- {n}")

    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(
        {"pairs": pairs, "all_agree": {"same": allagree, "n": len(rows)},
         "ooc": ooc, "dist": {k: {str(a): b for a, b in v.items()} for k, v in dist.items()},
         "probe_errors": probe_err,
         "diverged": [{k: r[k] for k in ["id", "gold"] + raters} for r in diverged],
         "notes": notes}, ensure_ascii=False, indent=2), encoding="utf-8")

    print("raters:", raters, "| samples:", len(rows))
    for k, v in pairs.items():
        print(f"  {k}: {v['same']}/{v['n']} = {v['pct']}%  qwk={v['qwk']}")
    print(f"  ALL: {allagree}/{len(rows)} = {100*allagree/len(rows):.1f}%")
    print("diverged:", [(r["id"], r["gold"], *[r[x] for x in raters]) for r in diverged])
    print("probe_errors:", probe_err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
