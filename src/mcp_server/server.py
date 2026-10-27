"""MCP server：把 RoleGuard 暴露给任意 MCP 客户端。

    # 给 Cursor / Claude Desktop 用（stdio 传输）
    python -m src.mcp_server.server

    # 不接客户端、不花钱的自检
    python -m src.mcp_server.server --selftest

三个工具：
    list_traits()                       列出全部判定轴
    get_trait_rule(trait_id)            查看某条轴的规则与反例
    judge_reply(candidate, traits=None) 判一条回复，返回分数 + 逐字证据

模型在**第一次调用工具时才构造**：MCP 客户端常常只是列举工具就退出，
启动时就去连模型既慢又可能失败。
"""

from __future__ import annotations

import json
import sys

from mcp.server.fastmcp import FastMCP

from src.judge.chat_model import build_judge_model
from src.judge.env_loader import EnvLoader
from src.judge.evaluator import TraitEvaluator
from src.judge.spec_loader import SpecLoader
from src.mcp_server.roleguard_tools import RoleGuardTools

SERVER_NAME = "roleguard"
mcp = FastMCP(SERVER_NAME)

_tools: RoleGuardTools | None = None


def _get_tools() -> RoleGuardTools:
    """懒加载：只有真正调用工具时才读配置、建模型。"""
    global _tools
    if _tools is None:
        spec = SpecLoader().load()
        _tools = RoleGuardTools(spec, TraitEvaluator(spec, build_judge_model()))
    return _tools


def _dump(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool()
def list_traits() -> str:
    """列出人设卡里全部判定轴（id / 名称 / severity），用于选择要判哪些规则。"""
    return _dump(_get_tools().list_traits())


@mcp.tool()
def get_trait_rule(trait_id: str) -> str:
    """查看某条判定轴的完整规则与反例（anti_patterns），用于解释"为什么这句话违规"。"""
    return _dump(_get_tools().get_trait_rule(trait_id))


@mcp.tool()
def judge_reply(candidate: str, traits: str = "") -> str:
    """判定一段角色回复是否符合人设。

    candidate: 待判定的英文回复原文。
    traits: 逗号分隔的判定轴（如 "era_consistency,emotional_restraint"），留空判全部。
    返回 JSON：score（2 符合 / 1 漂移 / 0 出戏 / -1 未完成）、label、
    violations（每条含可在原文逐字定位的引文）、soft_count、incomplete。
    """
    selected = [name.strip() for name in traits.split(",") if name.strip()] or None
    return _dump(_get_tools().judge_reply(candidate, selected))


def _selftest() -> int:
    """不联网：只验证规格能读、工具能列、规则能取。判定调用需要 API key，跳过。"""
    EnvLoader().load()
    spec = SpecLoader().load()
    tools = RoleGuardTools(spec, evaluator=_NeverCalled())

    traits = tools.list_traits()
    assert traits, "规格里至少该有一条 trait"
    first = tools.get_trait_rule(traits[0]["id"])
    assert "rule" in first and first["rule"], "规则文本不应为空"
    bad = tools.get_trait_rule("no_such_trait")
    assert "error" in bad and "available" in bad

    print(f"自检通过：{len(traits)} 条判定轴、规则可读、未知 trait 有明确报错")
    print("工具：" + ", ".join(t["id"] for t in traits))
    print("judge_reply 需要 JUDGE_API_KEY，这里不发起调用。")
    return 0


class _NeverCalled:
    """自检用的占位 evaluator：一旦被调用就说明自检逻辑写错了。"""

    def judge_case(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("自检不应触发模型调用")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if "--selftest" in args:
        return _selftest()
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
