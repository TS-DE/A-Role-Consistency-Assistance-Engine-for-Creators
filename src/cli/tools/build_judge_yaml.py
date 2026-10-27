#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从「人看的角色卡」生成「模型看的判定输入」

问题
----
data/characters/sherlock.yaml 同时承担两个角色：
  ① 给人读的说明书（note / why / 探针编号 / gold 分数）
  ② 给判定器读的 prompt（rule / anti_patterns / exemplars）

结果就是：判定器在 ② 里能读到 ① 里写的"D07-b 探针，gold = 0"。
A03 的 31/31 有一部分是这么来的（见 docs/07）。

做法
----
白名单重建一份 sherlock.judge.yaml，只保留"判定需要的字段"：
  meta（精简）/ persona / voice / scoring / traits（去掉 note、why）
  cross_trait_index（去掉 probes）/ knowledge（去掉说明性注释）
并保留 exemplars 的 text/source/gloss/verdict —— 那是 few-shot 正例，不是答案。

注意：这不解决"example_bad 就是测试候选原文"的问题（那是数据层面的污染，
只能靠换测试样本解决，见 docs/07 §三）。本脚本只解决"标注泄漏"。

运行:  python -m src.cli.tools.build_judge_yaml
输出:  data/characters/sherlock.judge.yaml
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "data" / "characters" / "sherlock.yaml"
DST = ROOT / "data" / "characters" / "sherlock.judge.yaml"

# 从保留字段里剔除标注：探针编号、"= 2" 这类分数、含编号的括号
SANITIZE = [
    (re.compile(r"[（(][^（）()]*D\d{2}-[a-d][^（）()]*[）)]"), ""),
    (re.compile(r"\s*D\d{2}-[a-d]\s*[=＝]\s*[012]"), ""),
    (re.compile(r"\s*D\d{2}-[a-d]"), ""),
]


def clean(v):
    """递归清洗字符串（只用于 traits/cross_trait_index/not_ooc/knowledge，不碰 scoring）。"""
    if isinstance(v, str):
        for pat, rep in SANITIZE:
            v = pat.sub(rep, v)
        return v.strip()
    if isinstance(v, list):
        return [clean(x) for x in v]
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items()}
    return v

HEADER = """\
# ═══════════════════════════════════════════════════════════════════
# 判定输入（judge input）—— 自动生成，勿手改
# 由 tools/build_judge_yaml.py 从 sherlock.yaml 重建。
# 本文件不含：探针编号 / gold 分数 / "判 X" 之类的标注信息。
# 人类说明请读 sherlock.yaml 与 docs/。
# ═══════════════════════════════════════════════════════════════════
"""


def main() -> int:
    src = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    out = {}

    meta = src.get("meta", {})
    out["meta"] = {k: meta[k] for k in
                   ("id", "name", "name_en", "era", "profession", "canon")
                   if k in meta}
    out["persona"] = src.get("persona")
    out["voice"] = src.get("voice")
    out["scoring"] = src.get("scoring")

    out["traits"] = []
    for t in src.get("traits", []):
        nt = {k: t[k] for k in ("id", "name", "severity", "source", "rule")
              if k in t}
        nt["observable_behaviors"] = t.get("observable_behaviors") or []
        nt["anti_patterns"] = [
            {k: ap[k] for k in ("level", "pattern", "example_bad") if k in ap}
            for ap in (t.get("anti_patterns") or [])
        ]
        # exemplar 的 note/why 常带探针编号 → 只留 文本/出处/译文/判定
        nt["exemplars"] = [
            {k: ex[k] for k in ("text", "source", "gloss", "verdict") if k in ex}
            for ex in (t.get("exemplars") or [])
        ]
        out["traits"].append(nt)

    cti = []
    for row in src.get("cross_trait_index", []):
        cti.append({k: row[k] for k in ("when", "trait", "severity", "example")
                    if k in row})
    if cti:
        out["cross_trait_index"] = cti

    kn = src.get("knowledge")
    if kn:
        out["knowledge"] = {k: kn[k] for k in ("trait_id", "severity", "strong", "weak")
                            if k in kn}
        out["knowledge"]["anti_patterns"] = [
            {k: ap[k] for k in ("level", "pattern", "example_bad") if k in ap}
            for ap in (kn.get("anti_patterns") or [])
        ]

    out["not_ooc"] = src.get("not_ooc")

    for key in ("traits", "cross_trait_index", "knowledge", "not_ooc"):
        if key in out:
            out[key] = clean(out[key])

    body = yaml.dump(out, allow_unicode=True, sort_keys=False,
                     default_flow_style=False, width=100)
    DST.write_text(HEADER + "\n" + body, encoding="utf-8")
    print(f"wrote {DST.relative_to(ROOT)}  ({len(body)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
