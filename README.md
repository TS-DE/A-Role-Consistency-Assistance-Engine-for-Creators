# RoleGuard · 面向创作者的角色一致性辅助引擎

> 让 AI 写出特定角色的回复之后，系统能判断它**有没有跑偏**；跑偏能拦住、能改，改不出来交给人。
> 表层场景是《福尔摩斯》同人创作（公版原文可作判定依据），技术内核是
> **在长上下文里维持一个实体的属性与语气，并证明这套判定是可靠的**。

---

## 1. 一句话说清它做什么

用户给一个情境 → 大模型写出角色的回复 → **8 条可判定规则**打分 → 不合格**带违规证据打回重写**
→ 重写 3 次仍不合格则**真中断**、转人工裁决。

企业映射：客服 Agent 话术合规拦截 / 企业文档助手防幻觉 / 品牌语气控制 / 高风险操作人工兜底。

## 2. 当前指标（口径必须连模型一起说）

| 指标 | 值 | 口径 |
|---|---|---|
| **主数**：人机一致率 | **73.7%**（14/19） | `qwen3.8-flash` · 留出集 **G** · n=19 · **只跑一次** |
| 漏杀 / 误杀 / 边界 | 3/4 · 8/9 · 3/6 | 同上 |
| 引文编造 | **0 条** | 每条命中都必须能在原文逐字定位 |
| 历史基线 | 94.1%（16/17） | `qwen3.8-27b` · 留出集 **F** · n=17 · **不同仪器，不可与主数并排** |
| 回归集（不得当留出成绩报） | 16/17 | `flash` · 回归集 **E** |
| 一轮两稿闭环耗时 | ≈ 91 s | 实测，判定占 92.7% |
| 单次闭环估算成本 | ≈ 0.016 元 | 字符数÷3 估算，非账单 |
| 离线用例 | 63 个 | 11 个测试模块，全部不联网 |

> **换模型等于换仪器。** 任何两个数字并排时，必须同时给出「模型 / 集合 / n」。

## 3. 目录结构

```
.
├─ src/
│  ├─ judge/            判定域（10 模块，扁平）
│  │  ├─ constants.py       路径、档位、超时、并发、阈值（唯一常量来源）
│  │  ├─ env_loader.py      读 .env（UTF-8/GBK 回退）
│  │  ├─ spec_loader.py     载入判定输入 sherlock.judge.yaml
│  │  ├─ prompt_builder.py  按 trait 组装提示词
│  │  ├─ chat_model.py      ChatModel(ABC) + urllib 实现 + 模型工厂
│  │  ├─ langchain_model.py LangChain 实现（可被 LangSmith 追踪）
│  │  ├─ hit_parser.py      模型输出 → hits[]
│  │  ├─ quote_validator.py 引文子串校验、区间与落句定位
│  │  ├─ aggregator.py      hits → 0/1/2（分数是算出来的，不是模型给的）
│  │  └─ evaluator.py       单次判定编排（8 轴并发）
│  ├─ graph/            编排域：LangGraph 五节点状态图
│  │  ├─ state.py           GraphState 契约
│  │  ├─ routing.py         decide() 纯函数路由
│  │  ├─ builder.py         连边 + 条件边 + checkpointer
│  │  └─ nodes/             generate.py / verify.py
│  ├─ cli/
│  │  ├─ eval/              离线评测（run_judge / score_generation / cost_report）
│  │  ├─ serve/             运行时入口（run_graph / smoke_loop / check_observability）
│  │  └─ tools/             构建维护（build_judge_yaml）
│  ├─ mcp_server/       MCP 工具层（list_traits / get_trait_rule / judge_reply）
│  └─ web/app.py        Streamlit 演示界面
├─ data/
│  ├─ characters/       人设卡：sherlock.yaml（人读）/ sherlock.judge.yaml（判定输入）
│  ├─ golden/           三套测试集：dev / 回归 / 留出（身份见该目录 README）
│  └─ gen_eval/         生成质量人工评分表
├─ tests/               与 src 同构；另有 scripts/ 放运维脚本
├─ docs/                01 规格书 · 02 测试集 · 07 泄漏审计 · 08 判定器结构
│                       09 闭环与状态图 · 10 生成评估 · 11 MCP · 12 结构自查
├─ reports/             评测结果与 trace
└─ CLAUDE.md            给 AI 编码助手的全局规则（含七条项目铁律）
```

## 4. 系统架构

```
 Streamlit 界面  ─┐
 CLI (run_graph) ─┼→  LangGraph 状态图  ─→  GenerateNode ─┐
 MCP 客户端      ─┘         ↑                             │
                            │                    VerifyNode（8 轴并发）
                            │                             │
                     rewrite_node ←── routing.decide ─────┤
                            │                    ├→ finalize → 出口
                            └────────────────────┼→ human_node（interrupt）
```

**五个节点**：`generate`（唯一创作处，不读规则）→ `verify`（取证+聚合）→ `routing.decide`（纯函数）
→ `rewrite`（违规证据回灌）/ `finalize`（出口）/ `human`（interrupt + 三种裁决）。

**分层的意义**：入口层只做参数与展示，编排层只按顺序调用，能力层是纯计算。
判定、聚合、路由三处逻辑全复用，所以**界面上的分和评测脚本算出的分是同一个分**。

## 5. 快速开始

### 5.1 环境

| 项 | 值 |
|---|---|
| Python | `E:\Anaconda_download\envs\py312_env\python.exe`（即 PATH 的 `python`，3.12） |
| 依赖 | `pyyaml` `langgraph` `langchain-core` `langchain-openai` `langsmith` `mcp` `streamlit` |
| 密钥 | 复制 `.env.example` 为 `.env`，填 `JUDGE_API_KEY` / `LLM_API_KEY` |

装包（本机 C 盘空间紧张，包缓存必须先挪走）：

```cmd
setx CONDA_PKGS_DIRS D:\conda-pkgs
E:\Anaconda_download\Scripts\conda.exe install -p E:\Anaconda_download\envs\py312_env -c conda-forge <包> -y
```

conda 源不通时用 pip 镜像：

```cmd
E:\Anaconda_download\envs\py312_env\python.exe -m pip install <包> -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 5.2 启动

```bash
streamlit run src/web/app.py                                        # 演示界面
python -m src.cli.serve.run_graph --json-out reports/traces/run01.json   # 命令行闭环
python -m src.mcp_server.server --selftest                          # MCP 自检（不花钱）
```

### 5.3 自测（全部不联网、不花钱）

```bash
python -m tests.judge.test_aggregator
python -m tests.judge.test_quote_validator
python -m tests.judge.test_evaluator
python -m tests.judge.test_langchain_model
python -m tests.graph.test_routing
python -m tests.graph.test_verify
python -m tests.graph.test_generate
python -m tests.graph.test_builder
python -m tests.gen.test_score_generation
python -m tests.mcp_server.test_roleguard_tools
python -m tests.cli.test_cost_report
```

> 逐个跑、逐个看退出码。不要用 `cmd1; cmd2 | Out-Null` —— 链式执行只取最后一条的返回值，
> 会掩盖前面的失败（本项目踩过）。

## 6. 常用命令

| 目的 | 命令 |
|---|---|
| 演示界面 | `streamlit run src/web/app.py` |
| 跑一次闭环（含人工兜底） | `python -m src.cli.serve.run_graph` |
| 批量评测 | `python -m src.cli.eval.run_judge --fanout --cases data/golden/golden_holdout_g.json` |
| 成本 / 延迟 | `python -m src.cli.eval.cost_report` |
| 规格重建（改完 yaml 必跑） | `python -m src.cli.tools.build_judge_yaml` |
| 泄漏审计 | `python -m tests.scripts.audit_leakage data/characters/sherlock.judge.yaml` |
| 生成质量汇总 | `python -m src.cli.eval.score_generation` |
| LangSmith 自检 | `python -m src.cli.serve.check_observability` |

## 7. 技术栈（以及**没有**什么）

| 层 | 实际 |
|---|---|
| 编排 | LangGraph（状态图 + interrupt + checkpointer） |
| 模型 | 自研 `ChatModel` 抽象，两个实现：`urllib`（默认）/ `langchain_openai` |
| 配置 | `pyyaml` + `.env` |
| 界面 | Streamlit（演示壳，非生产） |
| 外部接入 | MCP（FastMCP） |
| 可观测 | 自研 trace（毫秒级）+ LangSmith（可选） |

**没有**：Vue、TypeScript、MySQL、Redis、Docker。这不是缺失——本项目没有持久化与多用户需求，
引入它们只会增加故障面。

## 8. 项目铁律（改代码前必读）

1. **分数是算出来的，不是模型给的。** 模型只举证，聚合法在代码里。
2. **每条命中必须带能在原文逐字定位的引文**，编造的整条作废。
3. **判定未完成不许当通过**（`score=-1` → 转人工）。
4. **留出集只跑一次**；被用来改规则后立即降级为回归集。
5. 不为让指标好看改规格或改标注。
6. 人工放行记 `accepted_by_human`，它是漏杀，不是通过。

完整规则见 `CLAUDE.md` §4。

## 9. 已知限制

| 限制 | 说明 |
|---|---|
| 单轮交互 | `history` 字段已预留未用；"长上下文"目前靠人设卡而非多轮记忆 |
| 判定耗时 30–58 s/轮 | 8 轴并发已是上限；再快需减少轴数或换更快的模型 |
| 生成质量无自动化指标 | 方案与打分表已备（`docs/10`），数据待人工填 |
| `src/web/app.py` 342 行 | 超出 300 行上限，待结构批次拆分 |
| 单供应商 | `ChatModel` 可插拔，加本地 Ollama 实现即可降级 |

## 10. 文档索引

| 文档 | 内容 |
|---|---|
| `docs/01-一致性规格书.md` | 把"人设"变成可判定规则（项目的根） |
| `docs/02-黄金测试集.md` | 三档打分、候选回复、探针类型 |
| `docs/07-A03泄漏审计.md` | 泄漏三层、留出集退役规则、模型对照实验 |
| `docs/08-判定器模块结构.md` | 判定域分层、数据流、设计取舍 |
| `docs/09-闭环与状态图.md` | 五节点、路由理由、五个坑、答辩骨架 |
| `docs/10-生成质量评估.md` | 人工评分方案（均分/可用率/改写增益/同向性） |
| `docs/11-MCP能力外置.md` | 三个工具与接入方式 |
| `docs/12-结构合规自查.md` | 目录规范对照与整改批次 |
| `CLAUDE.md` | 给 AI 助手的全局规则与七条铁律 |

## 11. 版本

当前 `v0.8.1`。变更历史见 `CHANGELOG.md`（每版四段：原有缺陷 → 改进技术 → 代码位置 → 验证流程）。
