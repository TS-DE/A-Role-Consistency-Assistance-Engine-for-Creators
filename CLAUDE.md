# CLAUDE.md — RoleGuard 项目全局规则

> 本文件是给 AI 编码助手的**唯一规范来源**。若与其他文档冲突，以本文件为准。
> ⚠️ 根目录的 `CLAUDE_front_backend.md` 是课程模板（Vue3/FastAPI/MySQL），**不是本项目的规范**，
> 不要按它建目录、不要引入前端框架、不要引入数据库。

---

## 1. 这个项目是什么

RoleGuard：面向创作者的角色一致性辅助引擎。用户给一个情境，系统让大模型写出指定角色的回复，
再用 8 条可判定的规则打分；不合格打回重写，重写三次不合格则中断转人工。

**非目标（明确不做）**：
- 不是聊天产品，当前没有多轮对话与会话管理（未来可能做，见交接文档）
- 没有用户系统、没有权限、没有数据库
- 不做前端框架工程化（界面是 Streamlit 演示壳子）

## 2. 技术栈（真实情况）

| 层 | 实际用的 |
|---|---|
| 语言 | Python 3.12（conda 环境，见第 8 节） |
| 编排 | LangGraph 1.2.x（状态图 + interrupt + checkpointer） |
| 模型调用 | 自研 `ChatModel` 抽象，两个实现：`urllib`（默认）/ `langchain_openai` |
| 配置 | `pyyaml` 读人设卡，`.env` 读密钥 |
| 界面 | Streamlit（演示用，非生产） |
| 外部接入 | MCP（FastMCP），三个工具 |
| 可观测 | 自研 trace（毫秒级）+ LangSmith（可选，默认关闭） |

**没有**：FastAPI（当前）、MySQL、Vue、TypeScript、Redis、Docker。

## 3. 目录与分层（硬约束）

```
src/
├─ judge/            判定域（当前为扁平结构，10 个模块）
│  ├─ constants.py       路径、档位、超时、并发、阈值（唯一常量来源）
│  ├─ env_loader.py      读 .env（UTF-8/GBK 回退）
│  ├─ spec_loader.py     载入判定输入 sherlock.judge.yaml
│  ├─ prompt_builder.py  按 trait 组装提示词
│  ├─ chat_model.py      ChatModel(ABC) + urllib 实现 + 模型工厂
│  ├─ langchain_model.py LangChain 实现（可被 LangSmith 追踪）
│  ├─ hit_parser.py      模型输出 → hits[]
│  ├─ quote_validator.py 引文子串校验、区间与落句定位
│  ├─ aggregator.py      ScoreAggregator：hits → 0/1/2
│  └─ evaluator.py       TraitEvaluator：单次判定的编排
├─ graph/            闭环域：state / routing / builder / nodes
│  └─ nodes/         generate.py / verify.py
├─ cli/
│  ├─ eval/          离线评测入口（不参与线上）
│  ├─ serve/         运行时入口（真调模型）
│  └─ tools/         构建维护脚本
├─ mcp_server/       MCP 工具层
└─ web/              Streamlit 界面
tests/               与 src 同构的测试域，test_<被测模块>.py
data/
├─ characters/       人设卡（sherlock.yaml 人读版 / sherlock.judge.yaml 判定输入）
├─ golden/           三套测试集（dev / 回归 / 留出）
└─ gen_eval/         生成质量人工评分表
docs/                08 判定器结构、09 闭环、10 生成评估、11 MCP、12 结构自查
reports/             评测结果与 trace
agent_docs/          AI 产出的私有材料（已 gitignore，不入库）
```

规则：
1. 每个目录必须有 `__init__.py`，且用一行 docstring 写明职责。
2. 父目录下不得出现裸文件（根目录的 README / CHANGELOG / CLAUDE / config 除外）。
3. 单文件 ≤ 300 行，单函数 ≤ 60 行，单类 ≤ 250 行。
4. 常量统一进 `src/judge/constants.py`，业务文件禁止裸数字。
5. 依赖单向向下：入口层 → 编排层 → 能力层 → 常量。

## 4. 项目铁律（违反即 Bug，优先级高于任何"优化建议"）

1. **分数是算出来的，不是模型给的。** 模型只负责举证（命中哪条规则 + 原文引文），
   聚合规则写在 `ScoreAggregator` 里。不要让模型直接输出 0/1/2。
2. **每条命中必须带能在原文中逐字定位的引文**，`QuoteValidator` 做子串校验，编造的整条丢弃。
3. **判定未完成不许当通过。** 任何一条规则调用失败 → `score = -1` + `incomplete = True`，
   路由必须转人工。缺一条规则算出的分可能恰好是 2，那是假通过。
4. **留出集只跑一次。** 一批样本一旦被用来改规则，立即降级为回归集；要报数必须新写一批。
   （`data/golden/README.md` 有三套集的身份表。）
5. **不允许为了让指标好看而改规格或改标注。** 规则与标注打架时改规则，并在文档里写清理由。
6. **跨 trait 去重按"落句"判，不按字符串或区间重叠。** 详见 `docs/08` 与 `aggregator.py`。
7. **人工放行必须记成 `accepted_by_human`**，它是漏杀，不能记成"通过"。

## 5. 编码规范

- 注释：中文，说明"为什么"而不是"做了什么"；函数写清入参、返回、异常场景。
- 命名：文件/函数 `snake_case`，类 `PascalCase`，常量 `UPPER_SNAKE`。
- 每个技术能力先定义抽象基类（ABC）再写实现；实现之间不互相 import，只依赖抽象。
- 外部资源（模型、存储）一律构造注入，不在业务代码里直接实例化。
- 禁止裸 `except`；禁止 `print` 调试（用返回值或日志）；禁止在源码硬编码密钥。
- Windows 终端是 GBK：**不要往 stdout 打 emoji**（`✅` 会抛 `UnicodeEncodeError`）。

## 6. 与 AI 协作规则

1. 用户提需求，先输出**改动文件清单**（含文件路径与改动要点），再写代码。
2. 改现有代码要标注「位置 + 原因」，不要全量覆盖。
3. 改动后必须跑离线用例：`python -m tests.<域>.test_<模块>`，并报告实际输出。
4. 新增功能按 `tests/` 同构结构补测试；跑测试要**逐个检查退出码**，
   不要用 `| Out-Null` 链式执行（最后一条的返回值会掩盖前面的失败）。
5. 每次改动后：更新 CHANGELOG（四段式：原有缺陷 → 改进技术 → 代码位置 → 验证流程），
   并按语义化版本号递增。

## 7. 禁止行为

1. 不擅自改变项目形态：不引入 Vue/TS/MySQL/FastAPI，除非用户明确要求。
2. 不重构已稳定且被测试覆盖的业务代码。
3. 不删除或削弱校验、异常捕获、失败熔断逻辑。
4. 不输出明文密钥、`.env` 内容。
5. 不在同一轮里既做新功能又做大范围结构重构（回归无法归因）。
6. 不把 `agent_docs/` 加入 git（该目录已在 `.gitignore`）。

## 8. 环境

| 项 | 值 |
|---|---|
| Python | `E:\Anaconda_download\envs\py312_env\python.exe`（即 PATH 里的 `python`） |
| 装包（优先 conda） | `E:\Anaconda_download\Scripts\conda.exe install -p E:\Anaconda_download\envs\py312_env -c conda-forge <包> -y` |
| conda 包缓存 | 必须先 `setx CONDA_PKGS_DIRS D:\conda-pkgs`（C 盘只剩几百 MB） |
| 装包（conda 无此包时） | `E:\Anaconda_download\envs\py312_env\python.exe -m pip install <包> -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 已装关键库 | `pyyaml`、`langgraph`、`langchain-core`、`langchain-openai`、`langsmith`、`mcp`、`streamlit` |

**禁止**：新建虚拟环境、使用系统全局 Python、把依赖装到 C 盘。

## 9. 常用命令

```bash
# 演示界面
streamlit run src/web/app.py

# 跑一次闭环（含真 HITL）
python -m src.cli.serve.run_graph --json-out reports/traces/run01.json

# 批量评测
python -m src.cli.eval.run_judge --fanout --cases data/golden/golden_holdout.json

# 成本 / 延迟
python -m src.cli.eval.cost_report

# MCP 自检（不花钱、不联网）
python -m src.mcp_server.server --selftest

# 全量离线用例（11 个模块，逐个检查退出码）
python -m tests.judge.test_aggregator
python -m tests.graph.test_builder
python -m tests.cli.test_cost_report
```

## 10. 输出格式要求

每次代码回复固定四段：**改动说明 → 文件路径 → 完整代码 → 运行/验证命令（含预期输出）**。
