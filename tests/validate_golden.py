"""黄金测试集结构校验 + 分布报告。

用法： python tests/validate_golden.py
退出码：0 = 通过，1 = 有错。

它只做"体检"，不跑 LLM —— W1 就能用，不必等校验器写完。
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden_cases.json"

REQUIRED_CASE = {"id", "trait", "category", "input", "input_lang", "lang", "candidates"}
REQUIRED_CAND = {"id", "trait", "probe", "gold", "text"}
CATEGORIES = {"ooc_typical", "induced", "negative_control", "boundary"}
PROBES = {"leak", "false_alarm", "boundary"}

# 候选回复里不许出现的美式拼写（en-GB 校验）
US_SPELLING = re.compile(
    r"\b(color|favor|honor|recognize|apologize|analyze|center|gotten|"
    r"defense|gray|tire|candy|movie|apartment|sidewalk|vacation)\b",
    re.IGNORECASE,
)


def main() -> int:
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    errors: list[str] = []
    cases = data["cases"]

    cand_ids: set[str] = set()
    for case in cases:
        missing = REQUIRED_CASE - case.keys()
        if missing:
            errors.append(f"{case.get('id', '?')}: 缺字段 {sorted(missing)}")
        if case.get("category") not in CATEGORIES:
            errors.append(f"{case['id']}: 非法 category {case.get('category')!r}")

        for cand in case["candidates"]:
            cid = cand.get("id", "?")
            missing = REQUIRED_CAND - cand.keys()
            if missing:
                errors.append(f"{cid}: 缺字段 {sorted(missing)}")
            if cid in cand_ids:
                errors.append(f"{cid}: 候选 id 重复")
            cand_ids.add(cid)
            if cand.get("gold") not in (0, 1, 2):
                errors.append(f"{cid}: gold 必须是 0/1/2，实际 {cand.get('gold')!r}")
            if cand.get("probe") not in PROBES:
                errors.append(f"{cid}: 非法 probe {cand.get('probe')!r}")
            # probe 与 gold 必须自洽
            want = {"leak": 0, "boundary": 1, "false_alarm": 2}
            if cand.get("probe") in want and cand.get("gold") != want[cand["probe"]]:
                errors.append(f"{cid}: probe={cand['probe']} 与 gold={cand.get('gold')} 不自洽")
            if m := US_SPELLING.search(cand.get("text", "")):
                errors.append(f"{cid}: 美式拼写 {m.group(0)!r}，应为英式")

    cands = [c for cs in cases for c in cs["candidates"]]
    gold = Counter(c["gold"] for c in cands)
    print(f"输入 {len(cases)} 条 / 判定样本 {len(cands)} 条")
    print(f"gold 分布  0:{gold[0]}  1:{gold[1]}  2:{gold[2]}")
    print(f"probe 分布 {dict(Counter(c['probe'] for c in cands))}")
    print(f"主 trait    {dict(Counter(cs['trait'] for cs in cases))}")
    print(f"category   {dict(Counter(cs['category'] for cs in cases))}")

    if errors:
        print("\n发现问题：")
        for e in errors:
            print("  -", e)
        return 1
    print("\n结构校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
