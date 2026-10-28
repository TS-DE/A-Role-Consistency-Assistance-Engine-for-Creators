# RoleGuard · 面向创作者的角色一致性辅助引擎

> 表层场景：同人创作者的 AI 写作助手，防止角色 OOC（Out Of Character）。
> 技术内核：**在长上下文中维持特定实体的属性与语气一致性**，并给出可量化的判定。

## 一句话说清这个项目

不是"让 AI 扮演福尔摩斯"，而是**让 AI 扮演完之后，系统能判断它有没有演崩，崩了能拦住、能重写、拦不住能交给人**。

## 企业级映射（面试重点）

| 本项目 | 企业场景 |
|---|---|
| 福尔摩斯人设校验 | 客服 Agent 话术合规拦截 |
| 设定/台词 RAG 召回 | 企业文档助手的防幻觉 |
| 语气一致性打分 | 品牌语气控制 |
| 连续失败 → HITL 审批 | 高风险操作的人工兜底 |

## 当前状态

- [x] 第 0 步：一致性规格书 + 黄金测试集骨架（**你正在填**）
- [ ] W1：福尔摩斯语料入库 → FastAPI 接口 → LangGraph 生成/校验双节点闭环
- [ ] W2：混合检索（BM25 + 向量 + RRF）→ HITL 中断/恢复 → CLI 交互
- [ ] W3：测试集跑指标（OOC 率）→ README → 面试话术

## 指标口径（每个数字必须带"模型 / 集合 / n"才许出口）

- **主数**：判定器人机一致率 **73.7%（14/19）** —— qwen3.8-flash / G 集留出 / n=19 / 只跑一次即退役。
  划界修订的目标轴 watson_rapport 探针 4/4 全对（G07，见 `docs/07` §十一）。
- **历史基线**：**94.1%（16/17）** —— qwen3.8-27b / F 集留出 / n=17 / 已退役。
  与主数**不同仪器**，任何场合不得并排比较涨跌。
- **回归**：E 集 16/17 —— qwen3.8-flash / E 集（回归集）/ n=17。只用于防倒退；
  它与 F 的 94.1% 同值纯属巧合，不得当留出成绩报（`docs/07` §六 表）。
- **闭环**：一轮两稿 91 秒、判定占 92.7%、单次估算成本 0.016 元
  （qwen3.8-flash 判定 + deepseek-chat 生成；延迟实测、tokens 估算，见 `python -m src.cli.eval.cost_report`）。

## 目录

```
docs/01-一致性规格书.md    ← 把"人设"变成可判定规则（核心，先填这个）
docs/02-黄金测试集.md      ← 25 条带基准分的用例（dev / test 分离）
docs/03-架构决策记录.md    ← ADR，每周补一条，面试直接讲
data/characters/sherlock.yaml  ← 机器可读人设卡，生成/校验节点都读它
data/corpus/               ← 原文语料（raw/ 不入库）
src/                       ← 代码（W1 开始，一个节点一个函数地写）
```

## 环境

Python 3.12 / git 已就绪。核心判定与闭环只依赖 `pyyaml`（网络走标准库 `urllib`）；
演示界面另需 `streamlit`，MCP 另需 `mcp`。

## 运行

**演示界面（推荐先跑这个）**

```bash
streamlit run src/web/app.py
```

**命令行**

```bash
python -m tests.judge.test_aggregator        # 离线单测，不联网
python -m tests.judge.test_quote_validator   # 离线单测，不联网
python -m src.cli.eval.run_judge --limit 1 --dry  # 只看提示词，不发请求
python -m src.cli.eval.run_judge --fanout --cases data/golden/golden_holdout.json --json-out reports/holdout_run_03.json
python -m src.cli.serve.run_graph --json-out reports/traces/run01.json
python -m src.cli.eval.cost_report
```

> Windows 下命令一律写成**单行**（不支持 bash 的 `\` 续行）。

模块分层、数据流与设计取舍见 [docs/08-判定器模块结构.md](docs/08-判定器模块结构.md)
与 [docs/09-闭环与状态图.md](docs/09-闭环与状态图.md)。旧的 `python src/judge.py` 已废弃。


