# 11 · MCP：把判定能力外置

> 目标：让别人**在自己的编辑器里**调用你的角色一致性校验，而不是只能看你的 CLI。
> 代码：`src/mcp_server/`。工具实现 8 个离线用例，服务端提供 `--selftest`。

---

## 一、为什么做这件事（不是凑技术栈）

判定器现在有三个入口，底层是**同一套 `TraitEvaluator`**：

| 入口 | 谁用 | 形态 |
|---|---|---|
| `run_judge` | 你，做实验 | 批量评测脚本 |
| `run_graph` | 你，演示闭环 | CLI 交互 |
| **MCP server** | **别人** | 标准协议，任意 MCP 客户端可调 |

MCP 的价值在于第三行：**把能力从"我的程序"变成"可被调用的服务"**。
Cursor、Claude Desktop、任何支持 MCP 的工具，都能直接问：

> "帮我判一下这句福尔摩斯台词符不符合人设。"

它同时解决了课程要求"项目里要真用到 MCP"——而且是**承重**的用法，不是挂个 hello world。

---

## 二、三个工具

| 工具 | 作用 | 返回 |
|---|---|---|
| `list_traits()` | 列出全部 8 条判定轴 | `[{id, name, severity}]` |
| `get_trait_rule(trait_id)` | 取某条轴的规则与反例 | `{rule, anti_patterns[], severity}` |
| `judge_reply(candidate, traits="")` | 判一条回复 | `{score, label, violations[], soft_count, incomplete}` |

三个设计要点：

1. **不重写判定逻辑**，直接复用 `TraitEvaluator`。三个入口一个口径——
   否则三个月后会出现"编辑器里 2 分、报表里 0 分"。
2. **`violations` 每条都带逐字引文**。判官不能只说"我觉得不像"，
   它必须交出能在原文里定位的片段。
3. **`score=-1` 表示判定未完成**，绝不当成通过。缺一条规则算出的分可能恰好是 2，那是假通过。

---

## 三、接进 Cursor（Windows）

在项目根建 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "roleguard": {
      "command": "E:\\Anaconda_download\\envs\\py312_env\\python.exe",
      "args": ["-m", "src.mcp_server.server"],
      "cwd": "D:\\A Role Consistency Assistance Engine for Creators"
    }
  }
}
```

**三个字段都别省**：`command` 用**绝对路径**（MCP 客户端不继承你的 shell 环境），
`cwd` 必须是项目根（`src.` 是包导入前缀），`-m` 才能让 `src.mcp_server` 被解析到。

接进 Claude Desktop 同理，配置在 `%APPDATA%\Claude\claude_desktop_config.json`，结构一样。

重启客户端 → 工具列表里应出现 `roleguard` → 问它：

> 用 roleguard 的 judge_reply 判一下这句：We can run a DNA test on the glass.

预期返回 `score: 0`、`label: OOC（出戏）`，`violations` 里带 `"a DNA test"` 这类可定位片段。

---

## 四、自检（不接客户端、不花钱）

```bash
python -m src.mcp_server.server --selftest
```

它验证：规格能读、8 条轴能列、规则能取、未知 trait 有明确报错。**不发起模型调用**——
`judge_reply` 需要 `JUDGE_API_KEY`。

实测输出：

```
自检通过：8 条判定轴、规则可读、未知 trait 有明确报错
工具：evidence_first, emotional_restraint, no_glory_seeking, era_consistency,
      voice_register, watson_rapport, intellectual_appetite, moral_flexibility
judge_reply 需要 JUDGE_API_KEY，这里不发起调用。
```

---

## 五、局限（先说清楚，别让人问出来）

| 局限 | 说明 | 后果 |
|---|---|---|
| **stdio 单机** | 现在的传输是 stdio，只能本机同进程启动 | 别人要用得先有你的仓库；要远程得换 SSE / streamable HTTP 传输 |
| **每次调用要花 token** | 一次 `judge_reply` = 8 次判定调用 | 客户端里随手多问几次就是几毛钱，说明文档里要写一句 |
| **只判不写** | 没有暴露生成能力 | 想让它"写一段并自检"，得再加一个 `generate_reply` 工具（可作为下一步） |

---

## 六、如果被问"这和直接调 API 有什么区别"

> "直接调 API 是调我的 HTTP 接口，要部署、要域名、要鉴权；
> MCP 是让我的能力**直接长在别人的工具链里**，客户端不用知道我在哪、用什么模型。
> 而且工具描述里就写着判定口径，模型可以自己决定什么时候该调用它。"

更实际的一句：**课程要求的 MCP，在这里是"能力的第二个出口"，不是演示品**——
`judge_reply` 走的是和评测脚本、闭环里完全相同的判定代码。

---

## 七、下一步（如果要继续）

1. 加 `generate_reply` 工具：暴露 `GenerateNode`，让客户端"写一段并自检"一步到位。
2. 换成 streamable HTTP 传输 + 一个公网地址，这才谈得上"别人能用"。
3. 给工具加示例（`examples` 字段），客户端选择工具时会更准。
