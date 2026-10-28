"""RoleGuard 演示界面。

    streamlit run src/web/app.py

两个页签：
  创作台 —— 输入情境 → 生成 → 判定 →（可能打回重写）→ 人工裁决，右侧显示真实耗时时间线
  指标看板 —— 从 reports/ 下的真实结果文件读，不写死数字

界面只做"展示与交互"，判定、聚合、路由全部复用 `src.graph` + `src.judge`，
所以页面上看到的分和评测脚本、CLI 里算出来的是同一个分。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Streamlit 会把脚本目录加入 sys.path，但我们要 import src.*，所以把项目根补进去
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from langgraph.types import Command

from src.graph.builder import ABANDON, ACCEPT, EDIT_PREFIX, build_graph
from src.graph.state import new_state
from src.judge.chat_model import ChatModelError, build_generator_model, build_judge_model
from src.judge.constants import MAX_REWRITE_ATTEMPTS, PROJECT_ROOT
from src.judge.env_loader import EnvLoader
from src.judge.evaluator import JudgeAborted
from src.judge.spec_loader import SpecLoader

PRESETS = {
    "守夜（会触发打回）": "华生说他今晚还想再去现场守一夜，让福尔摩斯把已知的线索讲一遍。",
    "劝退（测健康冷嘲）": "华生说他一个人去码头查案就够了，让福尔摩斯别管。",
    "记者（测慕名利）": "案子告破，一群记者围上来，问这案子到底是谁破的。",
    "时代（测穿帮）": "你让苏格兰场调一下街口的监控，看看昨晚谁经过。",
}
SCORE_STYLE = {
    2: ("符合人设", "#1a7f37"),
    1: ("轻微漂移", "#9a6700"),
    0: ("出戏 OOC", "#cf222e"),
    -1: ("判定未完成", "#57606a"),
}


# ── 资源加载（只在首次调用时构造，避免每点一次按钮就重建客户端）──
@st.cache_resource(show_spinner=False)
def load_spec() -> dict:
    EnvLoader().load()
    return SpecLoader().load()


@st.cache_resource(show_spinner=False)
def make_graph():
    spec = load_spec()
    generator, judge = build_generator_model(), build_judge_model()
    return build_graph(spec, generator, judge, max_attempts=MAX_REWRITE_ATTEMPTS), generator, judge


def _init_state() -> None:
    defaults = {
        "scene": PRESETS["守夜（会触发打回）"],
        "result": None,
        "pending": None,
        "thread": None,
        "error": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _friendly_error(exc: Exception) -> str:
    """把技术异常翻译成"下一步该干什么"。演示时绝不把 traceback 甩给观众。"""
    text = str(exc)
    lowered = text.lower()
    if "429" in text or "rate limit" in lowered or "too many" in lowered:
        return f"被服务端限流（429）。等 1 分钟再点重试；反复出现就把 .env 的并发调小。\n\n{text[:300]}"
    if "timed out" in lowered or "timeout" in lowered:
        return f"调用超时。网络抖动或服务端慢，重试通常就好。\n\n{text[:300]}"
    if "getaddrinfo" in lowered or "resolve" in lowered:
        return f"域名解析失败——本机此刻连不上模型服务。检查网络后重试。\n\n{text[:300]}"
    return f"{type(exc).__name__}: {text[:300]}"


def _run(scene: str) -> None:
    graph, generator, judge = make_graph()
    thread = {"configurable": {"thread_id": f"ui-{time.time_ns()}"}}
    st.session_state["error"] = None
    with st.spinner(f"生成（{generator.model}）→ 判定（{judge.model}，8 轴并发）…约 40–90 秒"):
        try:
            state = graph.invoke(new_state(scene), thread)
        except (ChatModelError, JudgeAborted) as exc:
            st.session_state["error"] = _friendly_error(exc)
            return
        except Exception as exc:  # noqa: BLE001  兜底：页面永远不该出现 traceback
            st.session_state["error"] = _friendly_error(exc)
            return
    st.session_state.update(
        result=state,
        thread=thread,
        pending=state["__interrupt__"][0].value if state.get("__interrupt__") else None,
    )


def _resume(choice: str) -> None:
    graph, _generator, _judge = make_graph()
    thread = st.session_state["thread"]
    st.session_state["error"] = None
    with st.spinner("恢复执行…"):
        try:
            state = graph.invoke(Command(resume=choice), thread)
        except (ChatModelError, JudgeAborted) as exc:
            st.session_state["error"] = _friendly_error(exc)
            return
        except Exception as exc:  # noqa: BLE001
            st.session_state["error"] = _friendly_error(exc)
            return
    st.session_state.update(result=state, pending=None)


# ── 展示片段 ──────────────────────────────────────────────
def _show_score(score: int) -> None:
    label, color = SCORE_STYLE.get(score, ("未知", "#57606a"))
    st.markdown(
        f"<div style='padding:10px 14px;border-radius:8px;background:{color}18;"
        f"border-left:4px solid {color};margin-bottom:8px'>"
        f"<b style='color:{color};font-size:18px'>score = {score} · {label}</b></div>",
        unsafe_allow_html=True,
    )


def _show_timeline(state: dict) -> None:
    rows = []
    for item in state.get("trace", []):
        node = item.get("node", "?")
        ms = item.get("ms")
        note = ""
        if node == "generate":
            note = f"{item.get('chars', 0)} 字符"
        elif node == "verify":
            note = f"命中 {item.get('hits', 0)} 条 · 失败 {item.get('failed_traits', 0)} 条"
        elif node == "rewrite":
            note = f"回灌 {item.get('notes', 0)} 条违规证据"
        elif node in ("finalize", "human"):
            note = str(item.get("decision", "出口"))
        rows.append(
            {"节点": node, "耗时(s)": round(ms / 1000, 1) if ms else "—", "说明": note}
        )
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _tab_create() -> None:
    left, right = st.columns([3, 2])
    with left:
        st.text_area("创作者给的情境", key="scene", height=120)
        if st.button("生成并校验", type="primary", use_container_width=True):
            _run(st.session_state["scene"])
        _render_result()
    with right:
        state = st.session_state.get("result")
        st.subheader("时间线（实测）")
        if state:
            _show_timeline(state)
            total = sum(int(i.get("ms", 0)) for i in state.get("trace", []))
            st.caption(f"本轮总耗时 {total / 1000:.1f}s　共 {state.get('attempt', 0)} 稿")
        else:
            st.caption("跑一次后这里会显示每个节点的真实耗时——**判定通常占 90% 以上**。")


def _render_result() -> None:
    # 先看错误：失败时 result 仍是 None，若先判空返回，错误永远显示不出来
    if st.session_state.get("error"):
        st.error(f"这次没跑成：\n\n{st.session_state['error']}")
        if st.button("重试", use_container_width=True):
            st.session_state["error"] = None
            _run(st.session_state["scene"])
            st.rerun()
        return

    state = st.session_state.get("result")
    if not state:
        st.info("左侧输入情境后点「生成并校验」。判定跑 8 条规则，约 40–90 秒。")
        return

    pending = st.session_state.get("pending")
    if pending:
        _render_human(pending)
        return

    _show_score(int(state.get("score", -1)))
    if state.get("violated"):
        st.warning("违规证据（每条都可在原文逐字定位）")
        for note in state["violated"]:
            st.markdown(f"- `{note}`")
    st.subheader("最终文本")
    st.text_area("final", value=state.get("final", ""), height=220, label_visibility="collapsed")
    if state.get("needs_human"):
        st.caption("这一稿经过人工裁决：" + str(state.get("trace", [])[-1].get("decision", "")))


def _render_human(payload: dict) -> None:
    st.error("自动流程没能让这一稿达标，转人工裁决（图已中断）")
    _show_score(int(payload.get("score", -1)))
    st.markdown("**待裁决草稿**")
    st.text_area("draft", value=payload.get("draft", ""), height=180, label_visibility="collapsed")
    if payload.get("violated"):
        for note in payload["violated"]:
            st.markdown(f"- `{note}`")

    col1, col2 = st.columns(2)
    if col1.button("强制通过", use_container_width=True):
        _resume(ACCEPT)
        st.rerun()
    if col2.button("放弃", use_container_width=True):
        _resume(ABANDON)
        st.rerun()
    edited = st.text_area("手改稿（填了就用它）", height=100)
    if st.button("采用手改稿") and edited.strip():
        _resume(f"{EDIT_PREFIX}{edited.strip()}")
        st.rerun()


# ── 指标看板：只读真实结果文件 ─────────────────────────────
def _discover_holdout_reports() -> list[Path]:
    """列出留出集实测结果（holdout_<集>_run_<序>.json），按 mtime 降序=最新一次在前。

    为什么按文件发现而不是写死文件名：写死会把看板永远停在 F 集（v0.8.0 的缺陷）。
    E 代旧命名 `holdout_run_04.json` 不含 `_集_run_` 段，此通配天然不匹配，不会混入。
    """
    reports = PROJECT_ROOT / "reports"
    return sorted(reports.glob("holdout_*_run_*.json"),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def _holdout_stats(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list) or not data:
        return None
    by_probe: dict[str, list[int]] = {}
    for row in data:
        probe = str(row.get("probe", "?"))
        slot = by_probe.setdefault(probe, [0, 0])
        slot[1] += 1
        if row.get("gold") == row.get("sys"):
            slot[0] += 1
    # 文件名形如 holdout_<集>_run_<序>.json → 取集合名；异常命名回退 "?"
    parts = path.stem.split("_")
    split_name = parts[1] if len(parts) >= 4 else "?"
    return {
        "n": len(data),
        "ok": sum(1 for r in data if r.get("gold") == r.get("sys")),
        "by_probe": by_probe,
        "model": data[0].get("model", "?"),
        "split": split_name,
        "file": path.name,
    }


def _tab_metrics() -> None:
    st.subheader("留出集成绩")
    files = _discover_holdout_reports()
    stats = _holdout_stats(files[0]) if files else None
    if stats:
        if len(files) > 1:  # 两套以上留出结果时可切换对比
            pick = st.radio("数据集（默认最新一次）", files, index=0, format_func=lambda p: p.stem)
            stats = _holdout_stats(pick)
        cols = st.columns(4)
        cols[0].metric("人机一致率", f"{stats['ok'] / stats['n']:.1%}", f"{stats['ok']}/{stats['n']}")
        for i, (probe, label) in enumerate(
            [("leak", "漏杀探针"), ("false_alarm", "误杀探针"), ("boundary", "边界档")], start=1
        ):
            ok, total = stats["by_probe"].get(probe, [0, 0])
            cols[i].metric(label, f"{ok}/{total}")
        # 显著标注口径：离开"模型·集合·n"这个数就不允许出口
        st.markdown(
            f"**{stats['model']} · {stats['split']} 集 · n={stats['n']} · 只跑一次**"
        )
        st.caption(f"数据来自 reports/{stats['file']}。换模型等于换仪器，不同集合的数字不可并排比。")
    else:
        st.info("还没有留出集结果文件。跑一次："
                "python -m src.cli.eval.run_judge --fanout --cases data/golden/golden_holdout_g.json "
                "--json-out reports/holdout_G_run_01.json")

    st.divider()
    st.subheader("成本与延迟")
    from src.cli.eval.cost_report import load_records, summarise

    records = load_records(PROJECT_ROOT / "reports" / "traces")
    if records:
        cost = summarise(records)
        cols = st.columns(4)
        cols[0].metric("运行次数", cost["n"])
        cols[1].metric("平均总耗时", f"{cost['mean_ms'] / 1000:.0f}s")
        cols[2].metric("平均稿数", f"{cost['attempts'] / cost['n']:.1f}")
        cols[3].metric("单次估算成本", f"{cost['per_run_cost']:.4f} 元")
        st.caption("延迟实测；tokens 与成本为估算（字符数 ÷ 3），口径见 docs/12 与 cost_report。")
    else:
        st.info("还没有 trace 文件。跑一次：python -m src.cli.serve.run_graph --json-out reports/traces/run01.json")


def main() -> None:
    st.set_page_config(page_title="RoleGuard · 角色一致性校验", layout="wide")
    _init_state()

    st.title("RoleGuard · 角色一致性辅助引擎")
    st.caption("长上下文里的实体一致性：生成 → 8 轴校验 → 打回重写 → 人工兜底")

    with st.sidebar:
        st.subheader("场景预设")
        choice = st.selectbox("选一个", list(PRESETS), label_visibility="collapsed")
        if st.button("载入到输入框", use_container_width=True):
            st.session_state["scene"] = PRESETS[choice]
            st.rerun()
        st.divider()
        st.subheader("运行配置")
        env = EnvLoader()
        env.load()
        st.code(
            f"生成 {env.get('LLM_MODEL', '?')}\n判定 {env.get('JUDGE_MODEL', '?')}",
            language="text",
        )
        st.caption("换模型等于换仪器，历史分数不能并排比较。")

    tab_create, tab_metrics = st.tabs(["创作台", "指标看板"])
    with tab_create:
        _tab_create()
    with tab_metrics:
        _tab_metrics()


if __name__ == "__main__":
    main()
