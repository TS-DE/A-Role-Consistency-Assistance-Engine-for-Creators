#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
泄漏审计：判定输入里，到底藏了多少"答案"

背景
----
A03（豆包）只读 sherlock.yaml + 遮罩候选，打出 31/31。这个 100% 必须先排除污染才能当结论。
本脚本量化三件事：

  1. 候选**整句**是否出现在判定输入里（example_bad 常常就是测试候选原句）
  2. 候选**某个句子**是否出现在判定输入里（半泄漏：判定器能背下开场白）
  3. 是否出现探针编号（D07-b）/ gold 分数（"gold = 0"、"判 1"）—— 直接给答案

一个文件同时承担"给人看的说明书"和"给模型看的判分输入"时，这三样必然发生。

运行:  py -3 tests/audit_leakage.py [判定输入路径]
退出码: 0 = 无泄漏；1 = 有泄漏（可用于 CI 门禁）
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "data" / "golden" / "golden_cases.json"
DEFAULT = ROOT / "data" / "characters" / "sherlock.yaml"

PROBE_ID = re.compile(r"D\d{2}-[a-d]")
GOLD_ANNOUNCE = re.compile(r"gold\s*[=＝]\s*[012]|判\s*[012]|=\s*[012]\b")
NORM = re.compile(r"[\s\"'“”‘’]+")
SENT = re.compile(r"(?<=[.!?;])\s+")


def norm(s: str) -> str:
    return NORM.sub("", s).lower()


def main() -> int:
    path = (Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT).resolve()
    raw = path.read_text(encoding="utf-8")
    flat = norm(raw)

    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    cands = [(c["id"], c["text"]) for case in gold["cases"] for c in case["candidates"]]

    full, partial = [], {}
    for cid, text in cands:
        if norm(text) and norm(text) in flat:
            full.append(cid)
            continue
        hits = [s for s in SENT.split(text)
                if len(norm(s)) >= 20 and norm(s) in flat]
        if hits:
            partial[cid] = hits

    ids = sorted(set(PROBE_ID.findall(raw)))
    ans_lines = [(n, ln.strip()) for n, ln in enumerate(raw.splitlines(), 1)
                 if GOLD_ANNOUNCE.search(ln) or PROBE_ID.search(ln)]

    try:
        label = path.relative_to(ROOT)
    except ValueError:
        label = path
    print(f"target: {label}  ({len(raw)} chars)")
    print(f"1) 整句逐字命中: {len(full)}/{len(cands)}  {full}")
    print(f"2) 句子级泄漏:   {len(partial)}/{len(cands)}")
    for cid, hits in partial.items():
        print(f"     {cid}: " + " | ".join(h.strip()[:80] for h in hits))
    print(f"3) 带编号/答案的行: {len(ans_lines)}")
    for n, ln in ans_lines:
        print(f"     L{n}: {ln[:100]}")

    leak = len(full) + len(partial)
    print(f"\n可被判定器『认出来』的候选: {leak}/{len(cands)}")
    print("VERDICT:", "LEAKED" if (full or partial or ids) else "CLEAN")
    return 1 if (full or partial or ids) else 0


if __name__ == "__main__":
    sys.exit(main())
