"""
src/judge.py —— 单 trait 判定器（整个项目的第一个可运行单元）

【它做什么】
  给定「一条候选回复」+「一条 trait 的规则」，输出这条回复命中了哪些 anti_pattern，
  以及每条命中在候选原文里对应的**逐字片段（quote）**。

【它刻意不做什么】
  不检索、不生成、不连 LangGraph、不连 FastAPI。就一个函数：文本进，hits 出。
  这是能独立跑、独立测、独立讲的最小单元。

【为什么不让模型直接给 0/1/2】
  因为分数是**派生的**。模型只负责举证（命中哪条 pattern、引用哪段原文），
  分数由 aggregate() 按规格书 §一 的聚合顺序算出来。这样：
    1. 两人分歧时能定位到具体 pattern，而不是"我觉得 1 你觉得 2"；
    2. 分数规则改一行代码，不用重标 31 条；
    3. 模型没法"随便挑个数字"，它必须编出一段原文——编不出来就被程序拒绝。

【数据流】现在是函数参数；到 LangGraph 里就是 State 的字段：
      candidate / trait  ← State["draft_reply"] / State["active_traits"]
      hits               → State["judge_hits"]
      score              → State["trait_score"]
  参数怎么进来的，和以后 State 怎么传进来，是同一件事。

【跑法】
    python src/judge.py --dry                 # 只打印 prompt，不花钱，先读一遍
    python src/judge.py --selftest            # 不联网，验证解析/校验/聚合逻辑
    python src/judge.py                       # 跑全量 31 条，出第一个真数字
    python src/judge.py --limit 4 --trait era_consistency

依赖：pyyaml（已装）。网络走标准库 urllib，不需要 SDK。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
JUDGE_YAML = ROOT / "data" / "characters" / "sherlock.judge.yaml"
GOLDEN_JSON = ROOT / "tests" / "golden_cases.json"


def _force_utf8_stdout() -> None:
    """Windows 的 GBK 控制台会把 ✅ / ✓ 编成异常，直接崩掉整个评测。

    这不是显示问题，是崩溃 —— 一半的候选跑完才挂，还得重跑花钱。
    所以程序一开始就把 stdout/stderr 钉成 UTF-8。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001  某些宿主不提供 reconfigure，忽略即可
            pass


# ══════════════════════════════════════════════════════════════════
# 1. 环境
# ══════════════════════════════════════════════════════════════════
def load_env(path: Path | None = None) -> None:
    """极简 .env 解析。已存在的环境变量优先，不覆盖（便于临时 export 覆盖）。"""
    p = path or (ROOT / ".env")
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ══════════════════════════════════════════════════════════════════
# 2. 规格（judge 输入，不含任何 gold / 探针编号）
# ══════════════════════════════════════════════════════════════════
def load_spec() -> dict[str, Any]:
    spec = yaml.safe_load(JUDGE_YAML.read_text(encoding="utf-8"))
    spec["_traits_by_id"] = {t["id"]: t for t in spec["traits"]}
    return spec


# ══════════════════════════════════════════════════════════════════
# 3. 组装 prompt
# ══════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """你是一名严格的「角色一致性判定器」。每次只判断一条规则（trait），
不判断其他任何东西，也不评价文笔。

【硬性约束】
1. quote 必须是候选回复里**逐字存在**的片段，一个字都不能改、不能加省略号拼接之外的重写。
   程序会做子串校验，编造的引文会被整条丢弃。
2. 每条命中必须指认它落在哪一条 anti_pattern 上（pattern 字段写该 anti_pattern 的原文）。
3. 指不出片段、或指不出 pattern 的直觉，不要算命中，写进 ambiguity。
4. **不要给分数**。你只负责举证。
5. 不要因为"角色已经拒绝了 / 已经表达了正确立场"就放过字面上的违规。字面优先于意图。
6. 宁可少报，不要编造。少报只会让召回降低；编造会让整条作废。

【输出格式】只输出 JSON，不要任何解释文字：
{"hits": [{"pattern": "<anti_pattern 原文>", "quote": "<候选原文逐字片段>", "severity": "hard" 或 "soft"}],
 "ambiguity": ["<想报但指不出片段的理由>"]}"""


def build_messages(candidate: str, trait: dict[str, Any], spec: dict[str, Any]) -> list[dict]:
    """把「规格 + 一条规则 + 候选文本」拼成 messages。纯函数，可离线单测。"""
    lines: list[str] = []
    lines.append("# 角色\n" + str(spec.get("persona", "")).strip())
    lines.append(
        f"\n# 待判定的规则（只判这一条）\n"
        f"trait: {trait['id']} / {trait.get('name', '')}\n"
        f"severity: {trait['severity']}\n"
        f"rule:\n{str(trait.get('rule', '')).strip()}"
    )

    obs = trait.get("observable_behaviors") or []
    if obs:
        lines.append("\n符合时长这样（observable_behaviors）：\n" + "\n".join(f"- {o}" for o in obs))

    pats = trait.get("anti_patterns") or []
    if pats:
        block = ["\n违反时长这样（anti_patterns）："]
        for p in pats:
            block.append(f"- [{p.get('level', 'soft')}] pattern: {p.get('pattern', '')}")
            if p.get("example_bad"):
                block.append(f"  反例：{p['example_bad']}")
        lines.append("\n".join(block))

    ex = trait.get("exemplars") or []
    if ex:
        block = ["\n原文正例（柯南·道尔原作，用来校准『这条规则在真人笔下长什么样』）："]
        block += [f'- "{e.get("text", "")}" —— 《{e.get("source", "")}》' for e in ex]
        lines.append("\n".join(block))

    # 豁免清单：不塞这一段，判定器会把"冷淡但符合人设"的回复误判成违规（误杀）
    not_ooc = spec.get("not_ooc") or []
    if not_ooc:
        lines.append("\n# 豁免清单（下列情况不算违规，必须放行）\n" + "\n".join(f"- {n}" for n in not_ooc))

    lines.append('\n# 待判定回复\n"""\n' + candidate.strip() + '\n"""')
    lines.append("\n只输出 JSON。")
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(lines)},
    ]


# ══════════════════════════════════════════════════════════════════
# 4. 调模型（OpenAI 兼容 /chat/completions，标准库实现）
# ══════════════════════════════════════════════════════════════════
def _chat(messages: list[dict], *, model: str, temperature: float = 0.0,
          timeout: int = 60, retries: int = 2) -> str:
    base = os.getenv("JUDGE_BASE_URL") or os.getenv("LLM_BASE_URL") or "https://api.deepseek.com/v1"
    key = os.getenv("JUDGE_API_KEY") or os.getenv("LLM_API_KEY")
    if not key:
        raise SystemExit("缺少 API Key：请在 .env 里设 JUDGE_API_KEY(或 LLM_API_KEY)")

    url = base.rstrip("/") + "/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},  # 不支持的服务商 → 下面自动摘掉重试
    }

    last_err = "unknown"
    for attempt in range(retries + 1):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            if e.code == 400 and "response_format" in payload:
                payload.pop("response_format")   # 服务商不支持 JSON 模式，摘掉再来
                continue
            last_err = f"HTTP {e.code}: {detail}"
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(1.5 * (attempt + 1))          # TODO(你)：生产里应改成指数退避 + 限流
    raise RuntimeError(f"模型调用失败：{last_err}")


# ══════════════════════════════════════════════════════════════════
# 5. 解析模型输出
# ══════════════════════════════════════════════════════════════════
def parse_hits(raw: str) -> dict[str, Any]:
    """容错解析：去 ```json 围栏、去前后废话，取第一个 { 到最后一个 }。"""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    obj = None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                obj = json.loads(text[start:end + 1])
            except json.JSONDecodeError as e:
                return {"hits": [], "ambiguity": [], "parse_error": str(e)}

    if not isinstance(obj, dict):
        return {"hits": [], "ambiguity": [], "parse_error": "no json object"}

    hits = [h for h in (obj.get("hits") or []) if isinstance(h, dict)]
    amb = obj.get("ambiguity") or []
    if not isinstance(amb, list):
        amb = [str(amb)]
    return {"hits": hits, "ambiguity": amb, "parse_error": None}


# ══════════════════════════════════════════════════════════════════
# 6. 引文校验 —— 本文件的核心
# ══════════════════════════════════════════════════════════════════
_PUNCT_MAP = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2014": "-", "\u2013": "-"})
_ELLIPSIS = re.compile(r"\s*(?:\.\.\.+|…)\s*")


def _norm(s: str) -> str:
    """归一化：全角→半角、弯引号→直引号、空白压缩、大小写折叠。只用于比对，不用于展示。"""
    s = unicodedata.normalize("NFKC", s or "")
    s = s.translate(_PUNCT_MAP)
    s = re.sub(r"\s+", " ", s)
    return s.strip().casefold()


def validate_hits(hits: list[dict], candidate: str) -> tuple[list[dict], list[dict]]:
    """每条 quote 必须能在候选原文里找到。返回 (通过, 被拒)。

    允许模型用 "..." 连接两段不连续原文——拆开逐段校验，每段都必须在原文里。
    这一层就是把"可举证"从口号变成机器可检查的东西：编造引文一律作废，
    模型只能靠真的引用原文才能拿到命中。
    """
    hay = _norm(candidate)
    ok: list[dict] = []
    bad: list[dict] = []
    for h in hits:
        quote = str(h.get("quote") or "").strip()
        if not quote:
            bad.append({**h, "_reason": "empty_quote"})
            continue
        parts = [p for p in _ELLIPSIS.split(quote) if p.strip()]
        if parts and all(_norm(p) in hay for p in parts):
            ok.append(h)
        else:
            bad.append({**h, "_reason": "quote_not_in_candidate"})
    return ok, bad


# ══════════════════════════════════════════════════════════════════
# 7. 聚合 —— 分数是算出来的，不是模型给的
# ══════════════════════════════════════════════════════════════════
def _span_of(hay: str, quote: str) -> tuple[int, int]:
    """在归一化后的候选文本里定位引文区间；定位不到返回 (-1, -1)。

    为什么用区间、不用字符串相等：两个 trait 常常引用**同一句、但截的长度不同**
    （"Oh, how dreadful for poor Lestrade!" vs 整句）。字符串不等，区间却重叠。
    run_02 的 D09-c 就是这么被双计、判成 0 的。
    """
    parts = [p for p in _ELLIPSIS.split(quote) if p.strip()]
    if not parts:
        return (-1, -1)
    start = hay.find(_norm(parts[0]))
    if start == -1:
        return (-1, -1)
    if len(parts) == 1:
        return (start, start + len(_norm(parts[0])))
    last = hay.find(_norm(parts[-1]), start)
    return (start, last + len(_norm(parts[-1])) if last != -1 else start + len(_norm(parts[0])))


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    if a[0] < 0 or b[0] < 0:
        return False
    return a[0] < b[1] and b[0] < a[1]


def aggregate(results: list[dict], candidate: str = "") -> dict[str, Any]:
    """results: [{"trait", "severity", "hits":[...]}] + 候选原文 → 三档分。

    严格按 judge.yaml 的 aggregate_order，顺序不许反：
      1. 任一 hard 命中                -> 0
      2. soft 命中（按 trait 去重）>= 2 -> 0
      3. soft 命中（按 trait）= 1       -> 1
      4. 否则                          -> 2

    计数规则（同 judge.yaml soft_hit_counting）：
      - 单位是 trait：同一 trait 内多处漂移只计 1 条
      - 同一片段不得同时计入两个 trait —— **按区间重叠判，不按字符串相等**
    """
    hay = _norm(candidate)
    hard: list[dict] = []
    soft_by_trait: dict[str, list[dict]] = {}
    claimed: list[tuple[tuple[int, int], str]] = []
    deduped: list[dict] = []

    for r in results:
        for h in r["hits"]:
            sev = str(h.get("severity") or r["severity"]).lower()
            if sev == "hard":
                hard.append({"trait": r["trait"], **h})
                continue
            span = _span_of(hay, str(h.get("quote") or ""))
            owner = next((o for owner_span, o in claimed if _overlaps(span, owner_span)), None)
            if owner is not None:
                deduped.append({"trait": r["trait"], "quote": h.get("quote"), "kept_by": owner})
                continue
            claimed.append((span, r["trait"]))
            soft_by_trait.setdefault(r["trait"], []).append(h)

    n_soft = len(soft_by_trait)
    if hard:
        score = 0
    elif n_soft >= 2:
        score = 0
    elif n_soft == 1:
        score = 1
    else:
        score = 2
    return {
        "score": score,
        "hard_hits": hard,
        "soft_traits": list(soft_by_trait),
        "n_soft": n_soft,
        "deduped": deduped,
    }


# ══════════════════════════════════════════════════════════════════
# 8. 单条判定（对外就这一个函数）
# ══════════════════════════════════════════════════════════════════
def judge_trait(candidate: str, trait: dict[str, Any], spec: dict[str, Any], *,
                model: str, dry: bool = False) -> dict[str, Any]:
    messages = build_messages(candidate, trait, spec)
    if dry:
        return {"trait": trait["id"], "messages": messages}

    raw = _chat(messages, model=model)
    parsed = parse_hits(raw)
    ok, bad = validate_hits(parsed["hits"], candidate)
    return {
        "trait": trait["id"],
        "severity": trait["severity"],
        "hits": ok,
        "invalid": bad,
        "ambiguity": parsed["ambiguity"],
        "parse_error": parsed["parse_error"],
        "raw": raw,
    }


# ══════════════════════════════════════════════════════════════════
# 9. CLI
# ══════════════════════════════════════════════════════════════════
def selftest() -> int:
    """不联网，只验证 第 5–7 节 的逻辑。改完 aggregate 先跑这个。"""
    cand = 'Go to bed, Watson. I shall take the case.'
    raw = '```json\n{"hits": [{"pattern": "p1", "quote": "Go to bed, Watson.", "severity": "soft"}], "ambiguity": []}\n```'
    parsed = parse_hits(raw)
    ok, bad = validate_hits(parsed["hits"], cand)
    assert len(ok) == 1 and not bad, "正常引文应通过"

    fake = [{"pattern": "p2", "quote": "I forbid you to go.", "severity": "soft"}]
    _, bad2 = validate_hits(fake, cand)
    assert bad2 and bad2[0]["_reason"] == "quote_not_in_candidate", "编造引文应被拒"

    span = [{"pattern": "p3", "quote": "Go to bed...I shall take the case.", "severity": "soft"}]
    ok3, _ = validate_hits(span, cand)
    assert len(ok3) == 1, "省略号拼接的两段原文都应通过"

    # 聚合四档
    r_hard = [{"trait": "era_consistency", "severity": "hard",
               "hits": [{"pattern": "x", "quote": "DNA", "severity": "hard"}]}]
    r_two = [{"trait": "a", "severity": "soft", "hits": [{"quote": "q1"}]},
             {"trait": "b", "severity": "soft", "hits": [{"quote": "q2"}]}]
    r_one = [{"trait": "a", "severity": "soft", "hits": [{"quote": "q1"}, {"quote": "q9"}]}]
    r_none = [{"trait": "a", "severity": "soft", "hits": []}]
    assert aggregate(r_hard)["score"] == 0
    assert aggregate(r_two)["score"] == 0
    assert aggregate(r_one)["score"] == 1, "同 trait 多处只计 1 条"
    assert aggregate(r_none)["score"] == 2

    # 跨 trait 引同一句、但截断长度不同 → 只计 1 条（run_02 的 D09-c 就是这么被判 0 的）
    s = "Oh, how dreadful for poor Lestrade! One does feel for the man."
    r_dup = [{"trait": "a", "severity": "soft",
              "hits": [{"quote": "Oh, how dreadful for poor Lestrade!", "severity": "soft"}]},
             {"trait": "b", "severity": "soft", "hits": [{"quote": s, "severity": "soft"}]}]
    assert aggregate(r_dup, s)["score"] == 1, "同一句被两个 trait 各截一段，只应计 1 条"

    print("selftest OK：解析 / 引文校验 / 聚合 / 区间去重 全部通过")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="单 trait 角色一致性判定器")
    ap.add_argument("--dry", action="store_true", help="只打印 prompt，不发请求")
    ap.add_argument("--selftest", action="store_true", help="离线自测，不联网")
    ap.add_argument("--limit", type=int, help="只跑前 N 条候选")
    ap.add_argument("--trait", help="只跑某个 trait")
    ap.add_argument("--fanout", action="store_true",
                    help="每条候选判定全部 trait 再聚合（推荐：这才是真实链路的形状）")
    ap.add_argument("--json-out", help="把逐条结果写成 JSON")
    ap.add_argument("--cases", help="换一个测试集文件（默认 tests/golden_cases.json）")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    load_env()
    spec = load_spec()
    traits = spec["_traits_by_id"]
    model = os.getenv("JUDGE_MODEL") or os.getenv("LLM_MODEL")

    golden_path = Path(args.cases) if args.cases else GOLDEN_JSON
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    rows = [
        (case, cand)
        for case in golden["cases"]
        for cand in case["candidates"]
        if not args.trait or cand["trait"] == args.trait
    ]
    if args.limit:
        rows = rows[: args.limit]

    if args.dry:
        case, cand = rows[0]
        tr = traits[cand["trait"]]
        msgs = build_messages(cand["text"], tr, spec)
        print(f"===== {cand['id']} / {cand['trait']} =====")
        for m in msgs:
            print(f"\n--- {m['role']} ({len(m['content'])} 字符) ---\n{m['content']}")
        print(f"\n共 {len(rows)} 条候选待跑。看完 prompt 删掉 --dry 再跑。")
        return 0

    checked, errors = [], 0
    if args.fanout:
        print(f"fanout：{len(rows)} 条候选 × {len(traits)} 条 trait = {len(rows) * len(traits)} 次调用，"
              f"预计 8–15 分钟\n")

    for i, (case, cand) in enumerate(rows, 1):
        # 默认只判被标注的那条 trait（快、便宜）；--fanout 判全部 8 条再聚合。
        # 真实链路一定是 fanout：一条回复可能同时踩好几条轴，只看一条必然漏跨轴违规。
        # （D04-b 就是这么漏的：它的违规在 watson_rapport，却被标在 emotional_restraint 下。）
        trait_ids = list(traits) if args.fanout else [cand["trait"]]
        results: list[dict[str, Any]] = []
        for tid in trait_ids:
            try:
                results.append(judge_trait(cand["text"], traits[tid], spec, model=model))
            except Exception as e:  # noqa: BLE001
                errors += 1
                print(f"    ! {cand['id']} / {tid} 调用失败：{e}")
        if not results:
            continue

        agg = aggregate(results, cand["text"])
        mark = "✅" if agg["score"] == cand["gold"] else "❌"
        print(f"[{i}/{len(rows)}] {cand['id']:7s} gold={cand['gold']} sys={agg['score']} {mark}")
        for r in results:
            for h in r["hits"]:
                print(f"          ✓ [{r['trait']}] {h.get('pattern', '?')} → \"{h.get('quote', '')}\"")
            for h in r["invalid"]:
                print(f"          ✗引文无效 [{r['trait']}] {h.get('pattern', '?')} → "
                      f"\"{h.get('quote', '')}\" ({h.get('_reason')})")
            for a in r["ambiguity"]:
                print(f"          ? [{r['trait']}] {a}")

        checked.append({
            "id": cand["id"], "trait": cand["trait"], "probe": cand["probe"],
            "gold": cand["gold"], "sys": agg["score"],
            "scored_traits": trait_ids,
            "hard_hits": agg["hard_hits"],
            "soft_traits": agg["soft_traits"],
            "n_soft": agg["n_soft"],
            "hits": [{"trait": r["trait"], **h} for r in results for h in r["hits"]],
            "invalid": [{"trait": r["trait"], **h} for r in results for h in r["invalid"]],
            "ambiguity": [{"trait": r["trait"], "text": a} for r in results for a in r["ambiguity"]],
        })

    if not checked:
        print("没有可统计的结果。")
        return 1 if errors else 0

    # ── 汇总：三档分开报。只报一个总一致率会掩盖"只擅长抓硬违规"这件事 ──
    def rate(ids: set[str]) -> tuple[int, int]:
        sub = [c for c in checked if c["probe"] in ids]
        return sum(c["gold"] == c["sys"] for c in sub), len(sub)

    leak_ok, leak_n = rate({"leak"})
    fa_ok, fa_n = rate({"false_alarm"})
    bd_ok, bd_n = rate({"boundary"})
    total_ok = sum(c["gold"] == c["sys"] for c in checked)

    def pct(a: int, b: int) -> str:
        return f"{a / b:.1%}" if b else "n/a"

    print("\n" + "=" * 58)
    print(f"全量一致率     {total_ok}/{len(checked)} = {pct(total_ok, len(checked))}")
    print(f"0 档（漏杀探针）{leak_ok}/{leak_n} = {pct(leak_ok, leak_n)}   ← 该抓的抓到了吗")
    print(f"2 档（误杀探针）{fa_ok}/{fa_n} = {pct(fa_ok, fa_n)}   ← 不该抓的放过了吗")
    print(f"1 档（边界）    {bd_ok}/{bd_n} = {pct(bd_ok, bd_n)}   ← 三档里最难，预期最低")
    n_inv = sum(len(c["invalid"]) for c in checked)
    n_amb = sum(len(c["ambiguity"]) for c in checked)
    print(f"被拒引文 {n_inv} 条 / ambiguity {n_amb} 条   ← 编造引文的量，比准确率更能说明判定器老不老实")
    print("=" * 58)
    if errors:
        print(f"调用失败 {errors} 条（未计入统计）")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(checked, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写入 {args.json_out}")
    return 0


if __name__ == "__main__":
    _force_utf8_stdout()
    sys.exit(main())
