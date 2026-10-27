"""LangSmith 接入自检：网络、鉴权、trace 环境变量，一次说清。

    python -m src.cli.check_observability

它做四件事，从"不通"到"能用"逐层往上：
  1. 裸 HTTP 打 /health —— 只证明网络通，不需要 key；
  2. 看 LANGSMITH_API_KEY 是否配置（掩码显示）；
  3. 有 key 就用官方客户端列一次项目 —— 证明鉴权通；
  4. 打印 LangGraph/LangChain 追踪需要的环境变量，以及怎么开。

注意：LangSmith 只追踪 LangChain/LangGraph 的 runnable。
裸 urllib 发的请求在 LangSmith 里看不到 prompt 与 token —— 要看到，就把
MODEL_BACKEND 切成 langchain（见 src/judge/langchain_model.py）。
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

from src.judge.env_loader import EnvLoader

HEALTH_URL = "https://api.smith.langchain.com/health"
KEY_VARS = ("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY")
TRACE_VARS = ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2")
PROJECT_VAR = "LANGSMITH_PROJECT"
DEFAULT_PROJECT = "roleguard"


def _mask(value: str) -> str:
    return f"{value[:6]}…{value[-4:]}" if len(value) > 12 else "已配置（过短，疑似占位符）"


def _health() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=15) as response:
            body = response.read().decode("utf-8", "replace")[:40]
        print(f"[1/4] 网络：/health 返回 {response.status} {body}")
        return response.status == 200
    except urllib.error.HTTPError as exc:
        print(f"[1/4] 网络：/health 返回 {exc.code}（非 200，但说明能连上）")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[1/4] 网络：不通 —— {type(exc).__name__}: {exc}")
        return False


def _key() -> str | None:
    for name in KEY_VARS:
        value = os.getenv(name)
        if value:
            print(f"[2/4] 鉴权：{name} = {_mask(value)}")
            return value
    print(f"[2/4] 鉴权：未配置 {' / '.join(KEY_VARS)}")
    return None


def _auth(ok: bool) -> bool:
    if not ok:
        print("[3/4] 鉴权测试：跳过（没有 key）")
        return False
    try:
        from langsmith import Client

        client = Client()
        projects = list(client.list_projects(limit=3))
        print(f"[3/4] 鉴权测试：通过，可见 {len(projects)} 个项目"
              + (f"（如 {projects[0].name}）" if projects else ""))
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[3/4] 鉴权测试：失败 —— {type(exc).__name__}: {str(exc)[:160]}")
        return False


def _trace_env() -> None:
    tracing = next((os.getenv(n) for n in TRACE_VARS if os.getenv(n)), None)
    project = os.getenv(PROJECT_VAR) or DEFAULT_PROJECT
    print(f"[4/4] 追踪开关：{'; '.join(TRACE_VARS)} = {tracing or '未开'}　项目 = {project}")
    if not tracing:
        print("\n开启方式（写进 .env 或当前终端）：")
        print(f"  {TRACE_VARS[0]}=true")
        print(f"  {PROJECT_VAR}={project}")
        print(f"  {KEY_VARS[0]}=lsv2_pt_xxx")
    print("\n提示：只开追踪不会记录裸 urllib 的请求。要在 LangSmith 看到 prompt 与 token，")
    print("     请把 MODEL_BACKEND 设为 langchain（走 langchain_openai，可被追踪）。")


def main(argv: list[str] | None = None) -> int:
    EnvLoader().load()
    print("LangSmith 接入自检\n" + "-" * 40)
    reachable = _health()
    key = _key()
    authed = _auth(bool(key))
    _trace_env()
    print("-" * 40)
    if reachable and authed:
        print("结论：可以接入。下一步把 LANGSMITH_TRACING=true 打开，跑一次 run_graph 看 trace。")
        return 0
    if reachable and not key:
        print("结论：网络通，缺 key。到 https://smith.langchain.com 建项目后复制 API Key。")
        return 0
    print("结论：暂不可用。不要在这上面耗时间，直接用本地 trace（已含每节点 ms）。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
