# CHANGELOG

> 版本号遵循语义化版本；每节按「原有缺陷 → 改进技术 → 对应代码位置 → 验证流程」四段记录。

## 版本对照表

| 版本 | 日期 | 主题 | 关键产物 |
| --- | --- | --- | --- |
| v0.8.0 | 2026-10-28 | G01–G08 留出集（一次性实测并退役） | `data/golden/golden_holdout_g.json`（19 条，spec 0.4 盲写）；**14/19 = 73.7%（qwen3.8-flash）**；目标轴 G07 4/4 全对；5 条新分歧记入 docs/07 §九 转 H 批 |
| v0.7.1 | 2026-10-28 | watson_rapport 划界修订（修 F07-b 漏杀 + 守夜误杀） | spec 0.4：调侃/否定界 + 健康界两条可判定分界；两轮 E 回归终验 16/17（flash）；docs/01 四·补三、docs/07 §八 |
| v0.7.0 | 2026-10-27 | 演示界面（Streamlit） | `src/web/app.py` 双页签：创作台（含真 HITL 交互与实测时间线）、指标看板（读真实结果文件） |
| v0.6.2 | 2026-10-27 | 结构整改批次 B | `src/cli/` 拆 `eval/`（离线评测）与 `serve/`（运行时入口），文档与测试 import 同步 |
| v0.6.1 | 2026-10-27 | 结构整改批次 A | 数据迁至 `data/golden/`、运维脚本迁至 `tests/scripts/`、`tools/` 并入 `src/cli/tools/`、12 个文档路径同步 |
| v0.6.0 | 2026-10-27 | 成本/延迟汇总 + 结构自查 | `cost_report`（实测延迟 + 估算 tokens/成本）、trace 落盘、`docs/12` 合规自查与三批整改计划 |
| v0.5.1 | 2026-10-27 | MCP 能力外置 | 三个 MCP 工具、stdio server、`--selftest`、8 个用例、`docs/11` 接入指南 |
| v0.5.0 | 2026-10-27 | 生成质量评估 | `docs/10` 评分方案、可填打分表 CSV、汇总脚本（均分/可用率/硬伤率/改写增益/同向性）、6 个用例 |
| v0.4.3 | 2026-10-27 | 闭环文档 | `docs/09`：状态契约、时序实测、四条路由理由、五个坑、答辩骨架 |
| v0.4.2 | 2026-10-27 | LangChain 适配器 + LangSmith 自检 | `LangChainChatModel`、`MODEL_BACKEND` 切换、`check_observability`、4 个用例 |
| v0.4.1 | 2026-10-27 | 真 HITL：interrupt + 恢复 | 人工裁决节点、三种回传协议、`Command(resume)` 恢复、5 个含中断的用例 |
| v0.4.0 | 2026-10-27 | LangGraph 状态图闭环 + 判定并发 | 5 节点图、`finalize` 修复、判定并发 155s→30–58s、模型工厂收口、`.env` 编码回退 |
| v0.3.2 | 2026-10-27 | 闭环跑通（手写串联） | `routing.decide` 纯函数路由、`smoke_loop` 手写闭环、判定耗时暴露 |
| v0.3.1 | 2026-10-27 | 校验节点接入闭环 | `VerifyNode` 全轴判定、未完成不许当通过、5 个离线用例 |
| v0.3.0 | 2026-10-27 | 闭环起步：状态契约 + 生成节点 | `GraphState`、`GenerateNode`、违规清单回灌、4 个离线用例 |
| v0.2.4 | 2026-10-27 | F 集成绩归档并退役 | **可报数字：17 条未见样本 94.1%**、F07-b 暴露规格自相矛盾、Windows 单行命令、换后端成本方案 |
| v0.2.3 | 2026-10-27 | 留出集退役 + F 集封存 + 推功酸味规则 | E 集转回归集、F01–F08、`no_glory_seeking` 第 3 条 soft、泄漏复检 |
| v0.2.2 | 2026-10-27 | 超时放宽 + 失败补跑 + 空档告警 | 超时 60s、调用间隔 0.6s、`--missing-retries` 补跑、空档显式告警、`test_evaluator` |
| v0.2.1 | 2026-10-27 | 判定器模块化重构 + 运行时保护 | 10 个模块分层、`ChatModel` ABC、preflight、逐 trait 进度、失败熔断、离线单测 |
| v0.2.0 | 2026-10-26 | 判定器跨 trait 评测 + 首次留出集盲跑 | `--fanout`、区间去重聚合、`--cases`、留出集 E01–E08、GBK 崩栈修复 |
| v0.1.0 | 2026-10-26 | 初始项目导入与版本化 | 一致性规格书、黄金测试集、人设卡、评测脚本与对比报告 |

---

## v0.8.0 · 2026-10-28 · G 留出集：一次性实测并退役

### 1. 原有缺陷

- F 集（94.1%，qwen3.8-27b）已退役，**修好的 spec 0.4 没有任何可报的新数字**（§4.2 待办 #2）。
- v0.7.1 的两条分界线只在回归集（旧标注）上验证过，缺一个"规则修订后新写、
  判定器从未见过"的独立样本批。

### 2. 改进技术

- 新增 `data/golden/golden_holdout_g.json`：G01–G08 共 **19 条候选**（gold 0/1/2 = 4/6/9，
  probe leak/boundary/false_alarm = 4/6/9），8 个情境全部新写：
  - **同轴不同皮**：复刻 E/F/dev 的 8 条判定轴与两个结构弱点（G06 跨句双轴计数、
    G05-a/G07-b 复述换皮探针），零原句复用（脚本自检与 D/E/F 零子串重合、与 judge yaml 零字面泄漏）；
  - **G07 四条专测新界线**：a/b 测调侃-否定界（框架内 vs 永久资格否定），
    c/d 测健康界（症状事实关心 vs 宿命预言）——G07-c 判 1 即修复失败；
  - **先定 gold 再跑**：gold 依冻结的 spec 0.4 盲写，写作未参考任何判定输出；
    头部 how_to_use 含"写集与调规为同一 AI"的诚实声明与分界说明。
- 只跑一次并即刻退役（README 身份表已改"已用尽"）；5 条分歧只诊断记录（docs/07 §九），
  规则零改动——改了规则 G 作废得更快，验证归 H 批。

### 3. 对应代码位置

- `data/golden/golden_holdout_g.json`（新建，sealed/retired）
- `data/golden/README.md`：身份表 G 行（未跑 → 已用尽）
- `docs/07-A03泄漏审计.md`：§九（口径、G07 验证表、5 条分歧诊断、结论）
- `reports/holdout_G_run_01.json`：逐条原始结果（含 hits/ambiguity/invalid）

### 4. 验证流程

```bash
# 封存前自检（结构/泄漏/重合，全部离线免费）
python -I -c "…见开发过程…"   # 8 情境 19 候选、字段合法、id 唯一；
                               # G-vs-judgeYAML 字面泄漏 []；G-vs-D/E/F 子串重合 0
python -m src.cli.eval.run_judge --fanout --cases data/golden/golden_holdout_g.json \
       --json-out reports/holdout_G_run_01.json        # 唯一一次，用户发令后执行
```

实测结果（**qwen3.8-flash**，与 27b 的 F 数字不同仪器不可并排）：

- 一致率 **14/19 = 73.7%**；分档：hard 探针 3/4、合规放行 8/9、边界 3/6；
  **被拒引文 0 条、incomplete 0 条**。
- 主目标达成：**G07 修复验证 4/4 全对**（调侃放行、否定命中、关心放行、预言命中）——
  F07-b 同类句与守夜误杀两类失败在新规则下均被正确处置。
- 新记录 5 条分歧（2 漏杀、2 跨轴误杀、1 计数），全部是语用边界族，转 H 批待办
  （docs/07 §九 表）。flash 总分与其在 F 上的 76.5% 同档，n=19 下 1 条=5.3%，不作模型结论。

## v0.7.1 · 2026-10-28 · watson_rapport 划界修订

### 1. 原有缺陷

- **规则自相矛盾（F 留出集唯一漏杀的根因）**：`watson_rapport` rule(2)(5) 允许"调侃观察力、判断力"，
  anti(2) 又禁止"否定判断力"，两者之间没划界。F07-b（"The meaning is beyond you"，gold 1）被判 2，
  判定器的理由原话："规则允许调侃华生的观察力与判断力，且未否定其参与办案，因此不报命中"
  （`reports/holdout_F_run_01.json`）。这不是判定器执行错，是规格内部不自洽（docs/07 §六 已记录）。
- **健康断言过宽（守夜场景三轮误杀）**：rule(6) "关心句里不得夹带对身体的负面断言"把
  "你咳嗽，别去"这类**原作常态**（症状事实 + 保护建议）也判成 drift（交接文档 §7.3 已知问题）。
- **缺口记录**：docs/07 另记"当差使唤（Fetch my coat）无规则覆盖"，判据不明。

### 2. 改进技术

给 watson_rapport 划出**两条可判定的分界线**（spec_version 0.1 → 0.4；条目编号保持不变，
E06 canon_note / docs/01 等外部引用安全）：

- **调侃/否定界**：调侃是否把对方**留在"我们·搭档"框架内**。指"这一次"的疏漏＝合规
  （"You see, but you do not observe"）；宣布对方**永久性**不行、无用、只配单一功能＝能力否定，命中
  （rule(2)(3) + anti(2) 重写）。
- **健康界**：症状/风险的**事实陈述 + 命令式关心**放行（修守夜误杀）；"你不行/撑不住"式**能力判词**、
  **宿命预言**、**以身体状况对人归类排除**（"你这种身子骨的人去不了"式）才违规（rule(5)(6) + anti(3)）。
  末式为 E 回归第一轮暴露的缝隙（E06-b 被放行），第二轮前补入。
- 使唤跑腿按**"非违规"**划出而非补成 anti_pattern：原作风常差遣华生，补成违规会批量误杀。
- cross_trait_index 第 1 条同步收窄；exemplar note 判据改为"是否留在搭档框架内"。
- 文档：docs/01 新增四·补三（判据表 + 锚点对照 + 代价），docs/07 新增 §八（修订落地 + G 封存声明）。

### 3. 对应代码位置

- `data/characters/sherlock.yaml`：`meta.spec_version`、`watson_rapport.rule(2)(3)(5)(6)`、
  `anti_patterns[1][2]`、`exemplars[0].why/note`、`cross_trait_index[0].when`、卡头修订注释
- `data/characters/sherlock.judge.yaml`：重建产物（不手改）
- `docs/01-一致性规格书.md`：四·补三；`docs/07-A03泄漏审计.md`：§八

### 4. 验证流程

```bash
python -m src.cli.tools.build_judge_yaml        # 重建判定输入
python -m tests.judge.test_* …(11 个模块)        # 全量离线用例
python -m src.cli.eval.run_judge --fanout --cases data/golden/golden_holdout_g.json --dry \
       --trait watson_rapport                    # 确认新措辞进入发给模型的 prompt（不花钱）
python -m src.cli.eval.run_judge --fanout --cases data/golden/golden_holdout.json \
       --json-out reports/regression_E_after_v0.4_flash.json    # E 回归（README 硬要求）
```

实测结果（qwen3.8-flash——注意与历史基线 16/17(qwen3.8-27b) 是不同仪器，数字不可并排比较）：

- 11 个离线模块全部 exit=0；判定输入两次重建与 git 无脱节；`--dry` 确认 rule/anti 新措辞原文进 prompt。
- **第一轮 E 回归 15/17**：五个边界锚点中 E06-b（gold 1）被划界放成 2——rule(6) 宽了，
  漏掉"以身体状况对人归类排除"式；补入该式后复跑。E06-c 的偏差是 flash 在未改动的
  `voice_register` 轴上的误伤（把 "We go together" 读成大男主腔），按"不顺手改稳定规则"记录不动。
- **第二轮 E 回归 16/17 = 94.1%**：E06-a(0)/E06-b(1)/E06-c(2)/E07-a(2)/E07-b(1) **五锚点全过**，
  唯一失分 E03-a（evidence_first，与本次修订无关的轴；同一规则同一输入第一轮判对、第二轮判错，
  属已记录的模型复跑不稳，见 `reports/stability_run_01.json`）。被拒引文 0 条。
- 规则自此**冻结**；G01–G08 依冻结后的 spec 0.4 盲写（尚未跑，只跑一次）。

## v0.7.0 · 2026-10-27 · 演示界面（Streamlit）

### 1. 原有缺陷

- 全部能力只在命令行，**没有可演示的界面**；而课程检查要求"介绍前端页面并录讲解视频"，
  纯 CLI 无法满足。
- 闭环的杀手级证据（第一稿被打回、第二稿通过、判定占 90% 耗时）只存在于终端滚动输出里，
  演示时讲不清。

### 2. 改进技术

- 新增 `src/web/app.py`（Streamlit 单页，双页签），**零 HTTP 层**：页面内直接
  `build_graph()` + `graph.invoke()`，与 CLI、评测脚本共用同一套节点与判定逻辑。
- 创作台：
  - 情境预设（含"会触发打回"的场景，方便演示）；
  - `score` 徽章 + 违规证据（每条带可在原文逐字定位的引文）；
  - **真 HITL 交互**：图中断后页面出现「强制通过 / 手改 / 放弃」，用 `Command(resume=...)` 恢复；
  - 右侧时间线用 `trace` 的实测 `ms` 渲染，判定占比一眼可见。
- 指标看板：从 `reports/holdout_F_run_01.json` 与 `reports/traces/*.json` **读真实文件**，
  没有文件就提示"先跑一次"，绝不写死数字。
- 模型客户端与图用 `st.cache_resource` 缓存；每次运行生成独立 `thread_id`，避免 HITL 现场串台。
- 依赖：`streamlit` 装入 `E:\Anaconda_download\envs\py312_env`（pip 镜像）。
- 文档：`docs/09` 新增第十节（界面三个取舍与局限），README 补演示界面命令。

### 3. 对应代码位置

- `src/web/app.py`：`_run()` / `_resume()` / `_tab_create()` / `_render_human()` /
  `_tab_metrics()` / `_holdout_stats()`
- `src/web/__init__.py`（职责说明）
- `docs/09-闭环与状态图.md`：第十节
- `README.md`：运行章节

### 4. 验证流程

```bash
python -c "import src.web.app"                                  # 导入与依赖检查
python -m streamlit run src/web/app.py --server.headless true --server.port 8511
curl http://127.0.0.1:8511/_stcore/health                       # 期望 ok
```

实测结果：

- 导入通过；headless 启动成功，健康检查返回 `ok`。
- 页面启动不触发模型调用（图与客户端懒加载），只有点「生成并校验」才真正花钱。
- 全量离线用例不受影响：61/61 通过（本次未改判定与图逻辑）。

---

## v0.6.2 · 2026-10-27 · 结构整改批次 B

### 1. 原有缺陷

- `src/cli/` 下 6 个入口脚本混在一起（同类 ≥3 未归档），职责分不清：
  哪些是"跑一次真模型"的运行时入口，哪些是"算指标"的离线脚本，光看文件名看不出来。

### 2. 改进技术

- 拆成两个子包：
  - `src/cli/eval/`：`run_judge`、`score_generation`、`cost_report` —— **不参与线上流程**，只回答准、贵、快。
  - `src/cli/serve/`：`run_graph`、`smoke_loop`、`check_observability` —— **真调模型**的运行时入口。
  - `src/cli/tools/`：`build_judge_yaml` 等构建与维护脚本。
- 三个子包各带 `__init__.py` 写明职责与 `python -m` 跑法；`src/cli/` 根只剩 `__init__.py`。
- 批次 C（`src/judge` 分包）按作者决定暂缓，理由与代价写入 `docs/12`。

### 3. 对应代码位置

- `src/cli/eval/{__init__,run_judge,score_generation,cost_report}.py`
- `src/cli/serve/{__init__,run_graph,smoke_loop,check_observability}.py`
- `tests/cli/test_cost_report.py`：import 改为 `src.cli.eval.cost_report`
- 6 个文档的命令路径同步；`docs/12` 记录批次 B 结果与 C 的暂缓理由

### 4. 验证流程

迁移后逐个真跑入口（路径类改动唯一可靠的验证方式）：

```bash
python -m src.cli.eval.cost_report                    # 出表正常
python -m src.cli.eval.run_judge --limit 1 --dry      # 提示词正常构造
python -m src.cli.serve.check_observability           # 自检正常
python -c "import src.cli.serve.run_graph, src.cli.serve.smoke_loop, src.cli.eval.score_generation, src.cli.tools.build_judge_yaml"
```

- 全部离线用例：**61/61 通过**（judge 22 + graph 19 + gen 6 + mcp 8 + cli 6）。
- `src/cli/` 目录：根 1 个文件、eval 4 个、serve 4 个、tools 2 个，均符合归档规则。

---

## v0.6.1 · 2026-10-27 · 结构整改批次 A

### 1. 原有缺陷

- 违反《通用约束提示词》第二节的目录规则：`tests/` 根同时躺着 3 个脚本与 3 个 golden JSON
  （父目录裸文件 + 同类 ≥3 未归档）；`tools/` 下 1 个源码工具落在 `src/` 之外。
- 数据与代码混在一起，换数据集就要动测试目录结构。

### 2. 改进技术

- 数据分层：`data/golden/` 收纳三套测试集，并补 `README.md` 说明 **dev / 回归 / 留出** 三种身份
  与修改纪律（改留出集等于换仪器）。
- 运维脚本分层：`tests/scripts/` 收纳 `validate_golden` / `compare_rounds` / `audit_leakage`，
  补 `__init__.py` 说明必须用 `python -m` 跑（脚本内依赖 `from src.*` 的包导入）。
- 源码工具归位：`tools/build_judge_yaml.py` → `src/cli/tools/build_judge_yaml.py`，`tools/` 目录清空删除。
- 路径常量同步：`constants.py` 增加 `GOLDEN_DIR` 与 `HOLDOUT_F_JSON`；
  三个脚本的 `ROOT` 各退一层，`build_judge_yaml` 因多了一层目录改为 `parents[3]`。
- 12 个文档里的旧命令与旧路径批量改到新位置，`docs/12` 的整改计划表保留为历史记录。

### 3. 对应代码位置

- `src/judge/constants.py`：`GOLDEN_DIR` / `GOLDEN_JSON` / `HOLDOUT_JSON` / `HOLDOUT_F_JSON`
- `tests/scripts/{validate_golden,compare_rounds,audit_leakage}.py`：`ROOT` 与 `GOLD*` 路径
- `src/cli/tools/build_judge_yaml.py`：`ROOT = parents[3]`
- `data/golden/README.md`、`tests/scripts/__init__.py`、`src/cli/tools/__init__.py`（新增）
- `docs/12-结构合规自查.md`：批次 A 执行结果与经验

### 4. 验证流程

路径迁移的风险不在 import，而在**静默找不到文件**，所以四个入口都真的跑了一遍：

```bash
python -m tests.scripts.validate_golden            # 结构校验通过
python -m tests.scripts.compare_rounds             # 24/31 = 77.4%（与迁移前一致）
python -m tests.scripts.audit_leakage data/characters/sherlock.judge.yaml
python -m src.cli.tools.build_judge_yaml           # 重建 10788 字符
python -m src.cli.eval.run_judge --cases data/golden/golden_holdout_f.json --limit 1 --dry
```

- 全部离线用例：**61/61 通过**（judge 22 + graph 19 + gen 6 + mcp 8 + cli 6）。
- 文档复查：`grep` 旧路径已无残留（仅 `docs/12` 的历史计划表保留对照）。
- 结论：批次 A 干净，可以进入批次 B（`src/cli` 分 `eval/` 与 `serve/`）。

---

## v0.6.0 · 2026-10-27 · 成本/延迟汇总 + 结构自查

### 1. 原有缺陷

- **没有成本与延迟的数字**：`trace` 只在终端打印，跑完即失，无法汇总；
  答辩被问"跑一次多少钱、多少秒"只能凭记忆。
- **无法归因**：只有节点总耗时，没有 prompt / 回复的字符数，连量级都估不出。
- **结构合规未自查**：`tests/` 根有 6 个裸文件、`tools/` 有 1 个、`src/cli` 6 个入口未归档，
  违反《通用约束提示词》第二节的目录规则，且一直没有一份可核对的清单。

### 2. 改进技术

- `GenerateNode` / `VerifyNode` 的 trace 增加 `prompt_chars`、`reply_chars`（实测字符数）。
- `run_graph --json-out` 落盘本次 trace（`reports/traces/*.json`），并补上目录自动创建。
- 新增 `src/cli/cost_report.py`：读 trace 目录出表——
  **延迟实测**（均值/中位/p95、节点耗时占比），**tokens 与成本是估算**
  （字符数 ÷ `--chars-per-token`，价格由 `--judge-price` / `--gen-price` 传入）。
  估算口径写死在命令行参数里，不藏魔法数字。
- 节点占比的分母改用"节点耗时之和"而非"运行总耗时"：总耗时含图调度开销，
  用它做分母会让占比加起来不到 100%，读者会以为漏算。
- 新增 `docs/12-结构合规自查.md`：逐条对照九项规则、五项违规按风险排序、
  三批整改计划（A 路径常量 / B CLI 归档 / C judge 分包），并点明批次 C 里
  `PROJECT_ROOT = parents[2] → parents[3]` 是唯一会静默失败的改动。

### 3. 对应代码位置

- `src/cli/cost_report.py`：`load_records()` / `summarise()` / `print_report()`
- `src/cli/run_graph.py`：`--json-out`、`_build_record()`、目录自动创建
- `src/graph/nodes/generate.py` / `verify.py`：trace 增加字符数字段
- `src/judge/evaluator.py`：`judge_trait()` 记录 `prompt_chars` / `reply_chars`
- `tests/cli/test_cost_report.py`（新增，6 个用例）
- `docs/12-结构合规自查.md`（新增）

### 4. 验证流程

```bash
python -m tests.cli.test_cost_report
python -m src.cli.serve.run_graph --json-out reports/traces/run01.json
python -m src.cli.eval.cost_report
```

实测结果（一次真实两稿闭环）：

```
运行次数 1　平均稿数 2.00　转人工 0/1
总耗时（实测）均值 91.1s
verify 2 次 84.3s 92.7%　generate 2 次 6.6s 7.3%
估算 tokens：判定 输入 15041 / 输出 653；生成 输入 1019 / 输出 659
估算成本：单次 0.0161 元
```

- `test_cost_report` 6/6：空数据、耗时分布与节点占比之和为 1、判定/生成 tokens 分开折算、
  双价格成本、p95 线性插值、稿数与转人工计数。
- 全量离线用例：judge 22 + graph 19 + gen 6 + mcp 8 + cli 6 = **61/61 通过**。

### 5. 未完成（见 docs/12 第三节）

结构整改批次 A / B / C **未在本次执行**。理由：本轮已改 6 个文件并新增一个功能，
而结构重构要动约 40 处 import 与 5 处路径常量，必须留独立验证预算，否则回归无法归因。

---

## v0.5.1 · 2026-10-27 · MCP 能力外置

### 1. 原有缺陷

- 判定能力只有两个入口（批量评测、闭环 CLI），**别人无法调用**：要用就得进项目、跑脚本。
- 课程要求落地 MCP，但此前没有任何"MCP 相关"的东西；若只是挂个 hello world 反而减分。

### 2. 改进技术

- 新增 `src/mcp_server/`：`RoleGuardTools`（纯逻辑、可离线测）+ `server.py`（FastMCP 协议层）。
- 三个工具：`list_traits` / `get_trait_rule` / `judge_reply`。
  **判定逻辑零重写**，直接复用 `TraitEvaluator` —— 评测脚本、闭环、MCP 三个入口同一口径。
- 模型懒加载：只有真正调用工具时才构造，客户端"列举工具后退出"不会触发建连。
- `judge_reply` 保留两条硬约束：`violations` 必须带**可在原文逐字定位的引文**；
  任一条 trait 调用失败则 `score=-1`（未完成），**绝不报成通过**。
- `--selftest`：不接客户端、不花钱地验证规格加载、8 条轴列举、未知 trait 报错。
- `docs/11-MCP能力外置.md`：为什么做、三个工具、Cursor/Claude Desktop 接入配置（含绝对路径与 cwd 的坑）、
  自检、三条局限、下一步。

### 3. 对应代码位置

- `src/mcp_server/roleguard_tools.py`：`RoleGuardTools.list_traits()` / `get_trait_rule()` / `judge_reply()`
- `src/mcp_server/server.py`：`FastMCP` 注册、`_get_tools()` 懒加载、`_selftest()`
- `tests/mcp_server/test_roleguard_tools.py`（新增，8 个用例）
- `docs/11-MCP能力外置.md`（新增）

### 4. 验证流程

```bash
python -m tests.mcp_server.test_roleguard_tools
python -m src.mcp_server.server --selftest
```

实测结果：

- 工具层 8/8：轴列举、规则读取、未知 trait 报错、默认判全部、可限定轴、
  **未完成不报通过**、空候选拒绝、违规证据带引文。
- 服务端自检通过：8 条判定轴、规则可读、未知 trait 有明确报错。
- 全量离线用例：judge 22 + graph 19 + gen 6 + mcp 8 = **55/55 通过**。

---

## v0.5.0 · 2026-10-27 · 生成质量评估

### 1. 原有缺陷

- **生成侧没有任何指标**：判定器测的是"像不像福尔摩斯"，测不出"写得好不好"。
  答辩被问"你怎么评价生成质量"只能答"我看了觉得还行"。
- 闭环虽然有 `judge_score` 与打回次数，但**没有任何数字能证明"打回重写让稿子变好"**——
  如果第 2 稿不比第 1 稿好，整个闭环就是在烧钱。

### 2. 改进技术

- `docs/10-生成质量评估.md`：一维总分（1–5 整体可用性）+ 三个二值检查
  （`period_voice` 语体 / `on_scene` 接题 / `no_anachronism` 无穿帮），刻意压低维度以保信度。
- 抽样与禁则写死：10 个场景、记录每一次 attempt、不许挑场景、盲评（先打分后抄 judge_score）。
- 指标口径固化：均分 / 可用率（≥4）/ 硬伤率（任一检查为 0）/ **改写增益**（第 2 稿 − 首稿）/
  **同向性**（按 judge_score 分组看人工均分，验证自动指标与人眼方向一致）。
- 可填打分表 `data/gen_eval/gen_scores.csv`（UTF-8 BOM，Excel 直接打开不乱码）；
  含一行 `EXAMPLE` 示例，汇总脚本自动跳过。
- `src/cli/score_generation.py`：读表出报告；空表给出指引而不是报错。
- 效度威胁写进文档第六节（单评分者、n≈20、顺序偏差、单一生成模型），并要求写进报告。

### 3. 对应代码位置

- `docs/10-生成质量评估.md`（新增）
- `data/gen_eval/gen_scores.csv`（新增，可填）
- `src/cli/score_generation.py`：`load_rows()` / `summarise()` / `print_report()`
- `tests/gen/test_score_generation.py`（新增，6 个用例）

### 4. 验证流程

```bash
python -m tests.gen.test_score_generation
python -m src.cli.eval.score_generation
```

实测结果：

- `test_score_generation` 6/6：改写增益取首稿与 2+ 稿之差、可用率阈值为 4、硬伤率为任一检查失败、
  同向性按 judge 分组、缺检查项被计数而不是被隐藏。
- 空表运行输出"还没有已打分的行"并给出下一步指引，exit 0。
- 全量离线用例：judge 22 + graph 19 + gen 6 = **47/47 通过**。

---

## v0.4.3 · 2026-10-27 · 闭环文档

### 1. 原有缺陷

- 代码量已到 judge 10 个模块 + graph 6 个模块，**没有任何一份文档解释闭环怎么转**。
  docs/08 只覆盖判定器，状态流转、路由依据、五个踩过的坑全靠对话记忆 ——
  两天后自己都要重读代码。
- 答辩缺一份"三分钟怎么讲"的骨架，容易变成现场即兴。

### 2. 改进技术

- 新增 `docs/09-闭环与状态图.md`：状态图、字段读写契约、实测时序（含耗时归因）、
  四条路由决定及其理由、五个坑（`final` 为空 / interrupt 重放 / 串行慢 / 耗时归因错两次 / 人工放行留痕）、
  离线评测与在线闭环的关系、跑法、与通用约束的对照、答辩 3 分钟骨架 + 三个必备追问答案。

### 3. 对应代码位置

- `docs/09-闭环与状态图.md`（新增）
- 本文件：版本对照表 + 本节

### 4. 验证流程

文档类改动，验证口径为"每条结论都能指向代码或实测数据"：

- 时序数字取自 `run_graph` 的真实 trace（generate 4072ms / verify 58377ms / 33120ms / 30755ms）；
- 路由四条来自 `src/graph/routing.py` 的实现与作者确认；
- 五个坑各自对应一次真实运行：`final` 空字符串、interrupt 重放、155s→58s、ms 字段上线、
  `accepted_by_human` 留痕。

---

## v0.4.2 · 2026-10-27 · LangChain 适配器 + LangSmith 自检

### 1. 原有缺陷

- **判定与生成的模型调用是裸 urllib**：LangSmith 只追踪 LangChain/LangGraph 的 runnable，
  所以即使开了 tracing，也只能看到节点级 span，**看不到 prompt、回复、token 用量**——
  那恰好是排查"判定为什么不一致"最需要的三样。
- 项目里没有一行 LangChain 代码，而课程要求技术栈必须落地；强行塞一个无关的 chain 只会减分。
- 没有一条命令能回答"LangSmith 到底能不能用"。

### 2. 改进技术

- 新增 `LangChainChatModel`（`ChatModel` 的第二个实现）：底层换成 `langchain_openai.ChatOpenAI`。
  **换后端只新增一个子类，编排层与节点零改动** —— 这是 DIP 第一次真正兑现。
  附带收益：LangSmith 能看到完整的 LLM span。
- `MODEL_BACKEND=urllib|langchain` 开关（默认 urllib）：
  评测脚本要跑几百次、要盯失败率 → urllib 零依赖、错误直白；
  演示与排查要可观测 → langchain。
- 新增 `src/cli/check_observability.py`：四层自检（网络 `/health` → key 是否配置 →
  官方客户端鉴权 → 追踪环境变量），并对"只开 tracing 仍看不到 urllib 调用"给出明确提示。

### 3. 对应代码位置

- `src/judge/langchain_model.py`：`LangChainChatModel`（消息转换 + 注入式 chat，便于离线测试）
- `src/judge/chat_model.py`：`_backend()`、`_make()`，工厂支持后端切换
- `src/cli/check_observability.py`：`_health()` / `_key()` / `_auth()` / `_trace_env()`
- `tests/judge/test_langchain_model.py`（新增，4 个用例）

### 4. 验证流程

```bash
python -m tests.judge.test_langchain_model
python -m src.cli.serve.check_observability
```

实测结果：

- `test_langchain_model` 4/4：system/human 角色正确转换、未知角色回落 human、返回字符串内容、
  `model` 属性可用于记录仪器名。
- `check_observability`：`/health` 返回 `200 {"ok":true}`；未配置 key → 输出获取途径与三行配置，exit 0。
- 全量离线用例：judge 22 + graph 19 = **41/41 通过**；三个 CLI 入口 import 正常。
- 待办：拿到 key 后打开 `LANGSMITH_TRACING=true`，跑一次 `run_graph` 核对 LangSmith 上是否出现
  节点与 LLM 两层 span。

---

## v0.4.1 · 2026-10-27 · 真 HITL：interrupt + 恢复

### 1. 原有缺陷

- `human` 节点只是"打标记 → END"，**没有真中断**：图不会停，人也没有机会看现场。
  README 里宣称的 HITL 一直是张空头支票。
- 即使中断了，人工裁决的三种结果（放行 / 手改 / 放弃）没有协议，也没留痕，
  "人工放行"无法计入漏杀统计。

### 2. 改进技术

- `human` 节点改用 `langgraph.types.interrupt()` 挂起整图，payload 抛给 CLI：
  草稿 + 分数 + 违规证据清单。
- 三种回传协议：`accept`（强制通过）/ `edit:<文本>`（采用人工改写）/ `abandon`（放弃），
  由调用方用 `Command(resume=...)` 送回图继续执行。
- **每种决定都留痕**：`accepted_by_human` / `edited_by_human` / `abandoned` 写进 trace 与
  `needs_human` 字段。人工放行等于"系统本该拦却让过"，是漏杀统计的一部分，不能当通过。
- `build_graph` 总是配 `MemorySaver`：没有 checkpointer 就没有地方存现场，interrupt 无法恢复。
- CLI（`run_graph`）打印裁决材料并读 `[a]/[e]/[r]`，恢复执行后统一输出结果。

### 3. 对应代码位置

- `src/graph/builder.py`：`human_node()`（interrupt + 三种协议）、`build_graph(checkpointer=...)`、
  常量 `ACCEPT` / `ABANDON` / `EDIT_PREFIX`
- `src/cli/run_graph.py`：`_ask_human()`、`Command(resume=...)` 恢复分支
- `tests/graph/test_builder.py`：扩到 5 个用例，全部走真实 interrupt / resume

### 4. 验证流程

```bash
python -m tests.graph.test_builder
python -m src.cli.serve.run_graph
```

实测结果：

- `test_builder` **5/5 通过**，其中三个是真实中断用例：
  - 持续 drift → 挂起，`__interrupt__` 里带草稿与违规证据，且挂起前已写满 3 稿；
  - `resume=accept` → `final == 草稿`，trace 记 `accepted_by_human`；
  - `resume=edit:<文本>` → `final == 人工改稿`，trace 记 `edited_by_human`；
  - `resume=abandon` → `final == ""`，trace 记 `abandoned`。
- 全量离线用例：judge 18 + graph 19 = **37/37 通过**；两个 CLI 入口 import 正常。

---

## v0.4.0 · 2026-10-27 · LangGraph 状态图闭环 + 判定并发

### 1. 原有缺陷

- **没有状态图**：闭环只有手写 `while`，LangGraph 未接入，`interrupt` / Checkpointer 无从谈起。
- **`final` 是空字符串**（第一次真实运行暴露）：`pass` 分支直接连 `END`，而条件边不能写数据，
  没有任何节点负责把 `draft` 封成 `final`，CLI 拿到的最终文本为空。
- **判定串行，慢到无法迭代**：8 条 trait 顺序调用，单轮 verify 155s；一次三稿冒烟要 8 分钟。
- **`.env` 编码崩**：用 PowerShell `Set-Content` 改写后文件变成 GBK，`EnvLoader` 硬编码
  `utf-8` 直接抛 `UnicodeDecodeError`，报错位置看起来与"读配置"无关。
- **模型构造散落在 CLI**：`smoke_loop` 自己拼 `LLM_*` / `JUDGE_*`，再写一个入口就得复制一遍。

### 2. 改进技术

- `src/graph/builder.py`：5 节点图 `generate → verify → {finalize | rewrite → generate | human}`，
  条件边只调 `routing.decide()`，图本身不含任何判断逻辑。
- 新增 `finalize` 节点：把最后一稿封成 `final`。**边只决定去哪，不能写数据** —— 这是 LangGraph
  逼你想清楚数据流的地方，也是这次踩坑的根源。
- 判定并发：`ThreadPoolExecutor(MAX_JUDGE_WORKERS=4)`，8 条 trait 本质独立，串行是纯浪费。
  实测单轮 verify 155s → **58s**（首轮）/ **30s**（次轮）。
- `trace` 记录每节点 `ms`：数据表明生成仅 3–4s，判定占 95%，此前的"生成慢"判断是错的。
- `EnvLoader._read()` 按 `utf-8-sig → utf-8 → gbk` 回退，Windows 工具改写 `.env` 不再崩。
- 模型工厂收口到 `chat_model.build_generator_model()` / `build_judge_model()`，CLI 不再拼 env。
- `langgraph` 经 pip 镜像装入 `E:\Anaconda_download\envs\py312_env`（conda 源 `repo.anaconda.com` 不通）。

### 3. 对应代码位置

- `src/graph/builder.py`：`build_graph()`、`rewrite_node()`、`finalize_node()`、`human_node()`
- `src/cli/run_graph.py`：状态图入口（新增）
- `src/judge/evaluator.py`：`judge_case()` 分批 + `_run_batch()` 并发
- `src/judge/chat_model.py`：`build_generator_model()` / `build_judge_model()`
- `src/judge/env_loader.py`：`_read()` 编码回退
- `src/judge/constants.py`：`MAX_JUDGE_WORKERS`
- `src/graph/state.py`：新增 `needs_human`
- `tests/graph/test_builder.py`（新增，3 个用例，含"持续 drift 三轮后转人工"）

### 4. 验证流程

```bash
python -m tests.graph.test_builder
python -m src.cli.serve.run_graph
```

实测结果：

- 离线用例：judge 18 + graph 16 = **37/37 通过**。
- 真实闭环（生成 deepseek-chat / 判定 qwen3.8-flash）：
  ```
  generate a1 4072ms → verify a1 score=1 hits=1 58377ms → rewrite
  generate a2 3320ms → verify a2 score=2 hits=0 30755ms → finalize
  ```
  **首次出现"打回一次再通过"的完整闭环**，两稿总耗时约 97s。

---

## v0.3.2 · 2026-10-27 · 闭环跑通（手写串联）

### 1. 原有缺陷

- 生成与校验两个节点虽有，但没有任何东西把它们连起来，也没有"打回后往哪走"的判断。
- 路由规则只存在于对话里，没有落到代码：score=1 是否打回、未完成怎么办，全靠记忆。

### 2. 改进技术

- 新增 `src/graph/routing.py`：`decide()` 纯函数，把三条产品决定固化为代码——
  `2→出口`、`0/1→打回`、`打回满 3 次→人工`、`verify_incomplete→立刻人工不重试`。
  `explain()` 输出人类可读理由，避免路由变黑盒。
- 新增 `src/cli/smoke_loop.py`：不依赖 langgraph 的手写闭环，先跑通再看框架。
  生成侧读 `LLM_*`、判定侧读 `JUDGE_*`，两种模型可分开配置。
- `constants.py` 补 `MAX_REWRITE_ATTEMPTS` 与 `INCOMPLETE_SCORE`（原先只在 `.env` 里，代码读不到）。

### 3. 对应代码位置

- `src/graph/routing.py`：`decide()` / `explain()`
- `src/cli/smoke_loop.py`：`main()` 主循环、`_build_generator()` / `_build_judge()`
- `src/judge/constants.py`：`MAX_REWRITE_ATTEMPTS`、`INCOMPLETE_SCORE`
- `tests/graph/test_routing.py`（新增，7 个用例）

### 4. 验证流程

```bash
python -m tests.graph.test_routing
python -m src.cli.serve.smoke_loop
```

实测结果：

- 离线用例：routing 7/7，合计 **34/34** 通过。
- 真实闭环：1 稿通过（`score=2`、证据 0 条），trace 两条（generate 1598 字符 / verify）。
- **单轮耗时 213.7 秒**：生成 1 次（deepseek-chat）+ 判定 8 次（qwen3.8-max-0902，约 25s/次）。
  这说明判定侧用 MAX 时，一次冒烟要 3.5 分钟、三稿要 10 分钟 —— 迭代速度不可接受，
  正式结论：判定器换 `qwen3.8-flash`。

---

## v0.3.1 · 2026-10-27 · 校验节点接入闭环

### 1. 原有缺陷

- 图里只有生成、没有校验：草稿无人审，`score` 字段永远是初始值 -1，闭环不存在。
- 校验若直接调 `TraitEvaluator` 而不处理失败，会把"缺一条规则算出的 2 分"当成通过 —— 假通过。

### 2. 改进技术

- `VerifyNode`：读 `draft` → 全轴判定 → 写 `verdicts` / `score` / `violated` / `verify_incomplete`。
- **永远 fanout**：不提供"只判某一条"的开关。D04-b 的教训是违规可能落在被标注之外的另一条轴。
- **未完成不许当通过**：任一 trait 调用失败 → `score = -1` + `verify_incomplete = True`，交给路由层送人工。
- 复用 `TraitEvaluator` 而非重写判定逻辑，避免两份会各自漂移的真相。

### 3. 对应代码位置

- `src/graph/nodes/verify.py`：`VerifyNode.__call__()`，`INCOMPLETE_SCORE`
- `src/graph/state.py`：新增 `verify_incomplete` 字段（含 `new_state()` 初始化）
- `tests/graph/test_verify.py`（新增，5 个用例）

### 4. 验证流程

```bash
python -m tests.graph.test_verify
python -m tests.graph.test_generate
python -m tests.judge.test_aggregator; python -m tests.judge.test_quote_validator; python -m tests.judge.test_evaluator
```

实测结果：`test_verify` 5/5、`test_generate` 4/4，判定域 18 个用例无回归，**合计 27/27 通过**。
行数：`verify.py` 66 行、`state.py` 49 行、`generate.py` 58 行，均远低于 300 行上限。

---

## v0.3.0 · 2026-10-27 · 闭环起步：状态契约 + 生成节点

### 1. 原有缺陷

- 项目只有"判定"没有"生成"：`src/` 里没有任何节点，评测对象是静态候选文本，
  不存在"被打回后重写"的活系统。这是结业项目缺的那一半。
- 判定器与生成器共用一套 `.env` 变量，未来生成侧换模型会连带影响判定侧。

### 2. 改进技术

- 新增 `GraphState`：把节点间的通信字段集中定义（user_input / draft / attempt /
  rewrite_notes / verdicts / score / violated / trace），节点不互相调用，只读写 State。
- 新增 `GenerateNode`：读 `persona` + `voice.forbidden_en` + 上一轮 `rewrite_notes`，
  产出 `draft`，写回 `attempt` 并清空已消费的违规清单。
- **刻意的取舍**：生成节点**不读** 8 条完整 anti_pattern。全塞进去会逼模型"背规则"，
  写出来的福尔摩斯扁而无味；判定交给校验节点。
- 节点契约与 LangGraph 解耦：`__call__` 只做"State 进、部分字段出"，因此可离线单测，
  不需要安装 langgraph。

### 3. 对应代码位置

- `src/graph/state.py`：`GraphState`、`new_state()`、`summarize_hits()`、`trace_entry()`
- `src/graph/nodes/generate.py`：`GenerateNode.__call__()` / `_build_messages()`
- `tests/graph/test_generate.py`（新增，4 个用例：状态写入 / 提示词组装 / 回灌与清空 / 违规清单展平）

### 4. 验证流程

```bash
python -m tests.graph.test_generate
python -m tests.judge.test_aggregator; python -m tests.judge.test_quote_validator; python -m tests.judge.test_evaluator
```

实测结果：

- `test_generate` 4/4 通过；判定域 18 个用例无回归，**合计 22/22**。
- 行数：`state.py` 49 行、`generate.py` 58 行，均远低于 300 行上限。
- 冒烟：`python -m src.cli.eval.run_judge --cases data/golden/golden_holdout_f.json --limit 1`
  在新模型 `qwen3.8-max-0902` 上连通正常、判定 1/1。

---

## v0.2.4 · 2026-10-27 · F 集成绩归档并退役

### 1. 原有缺陷

- **F 集跑完但无人归档**：17/17 完整，16/17 = 94.1%，若不写进口径文档，下次一定会被当成"又涨了"。
- **规格书内部自相矛盾**（F07-b 暴露）：`watson_rapport` rule(2) 允许"调侃观察力与判断力"，
  而 anti_pattern(2) 禁止"不信任华生能力、否定判断力"——"否定判断力"落在两者之间没有划界。
- **规则缺口**：`Fetch my coat.` 这类"当差使唤"没有任何 anti_pattern 覆盖。
- **文档里的命令不可用**：README / docs/08 用了 bash 的 `\` 续行，Windows cmd 直接报错。
- **模型额度风险**：qwen3.8-27b 仅剩 5.53%，一轮全量约 20 万 tokens，连一轮都跑不完。

### 2. 改进技术

- F 集成绩按"模型 / 集合 / 样本量 / 是否复跑"四项口径归档，随即**退役**（不再用于报数）。
- F07-b 的矛盾与缺口**作为待办记录**，按留出集纪律**不在 F 上调规则**，等 G 集验证。
- README / docs/08 命令统一改为 **Windows 单行**写法。
- docs/08 新增「换后端」小节：`ChatModel` 抽象让云端/本地只差 `.env` 三行，并给出成本口径
  （136 次调用 ≈ 20 万 tokens），建议开发期走本地 Ollama、定稿再用云端跑留出集。

### 3. 对应代码位置

- `docs/07-A03泄漏审计.md`：新增第八节「F 集成绩与退役」，含报数口径模板与集合身份表
- `docs/08-判定器模块结构.md`：命令改单行；新增「五·补、换后端（成本控制）」
- `README.md`：命令改单行
- 本文件：版本对照表 + 本节

### 4. 验证流程

```bash
python -m src.cli.eval.run_judge --fanout --cases data/golden/golden_holdout_f.json --json-out reports/holdout_F_run_01.json
```

实测结果（qwen3.8-27b，2026-10-27，单次）：

- 有效样本 **17/17**（无 incomplete）
- 全量一致率 **16/17 = 94.1%**
- 0 档（漏杀探针）**5/5 = 100%**
- 2 档（误杀探针）**8/8 = 100%**
- 1 档（边界）**3/4 = 75%**
- 被拒引文 **0 条** / ambiguity 30 条
- 唯一分歧 F07-b（gold 1 / sys 2），归因于规格自相矛盾，非判定器抖动

---

## v0.2.3 · 2026-10-27 · 留出集退役 + F 集封存 + 推功酸味规则

### 1. 原有缺陷

- **留出集已被自污染**：`holdout_run_04` 的 16/17 = 94.1%，但其中至少两处规则修正
  （`evidence_first` rule(6) 复述豁免、聚合去重改「同句」）是**照着 E01–E08 的失败写的**。
  这批样本已经不是留出集，拿它报泛化能力就是自证。
- **`no_glory_seeking` 缺一档**：E05-b 连续三轮稳定判 2、人工判 1，分歧在「总算轮到我」式的酸味，
  规则里没有对应条目。
- **新增规则时引入新泄漏**：为修 E05-b 写的 `example_bad` 与 F05-b 候选共用 40+ 字符片段，
  等于提前把答案塞给了判定器（已换句）。

### 2. 改进技术

- **E01–E08 降级为回归集**：改完规则必须跑，防倒退，不再用于报数。
- **新写 F01–F08 作为留出集**：17 条判定样本（leak 5 / false_alarm 8 / boundary 4），
  同轴不同皮、gold 先写死、每条附 `canon_note`；覆盖两个结构弱点（跨句双轴、复述豁免是否泛化）。
- **泄漏复检**：对 judge.yaml 做 40 字符窗口重叠检测，两批留出集均为 **0 条**。
- `no_glory_seeking` 补第 3 条 soft：「以『一如既往/果然如此/每次都这样/总算轮到我』暗示对功劳归属的怨气或得意」。

### 3. 对应代码位置

- `data/golden/golden_holdout_f.json`（新增，留出集）
- `data/characters/sherlock.yaml`：`no_glory_seeking.anti_patterns` 新增 soft 条目
- `docs/07-A03泄漏审计.md`：新增第七节「留出集的退役规则」
- `data/characters/sherlock.judge.yaml`：重建（10811 字符）

### 4. 验证流程

```bash
python -c "import json;json.load(open('data/golden/golden_holdout_f.json',encoding='utf-8'))"   # 结构
python -m src.cli.tools.build_judge_yaml
python -m tests.scripts.audit_leakage data/characters/sherlock.judge.yaml
python -m tests.judge.test_aggregator && python -m tests.judge.test_quote_validator && python -m tests.judge.test_evaluator
```

实测结果：

- F 集结构：8 输入 / 17 判定样本；gold 分布 `0:5 1:4 2:8`；probe `leak 5 / false_alarm 8 / boundary 4`。
- 40 字符重叠检测：`golden_holdout_f.json` 0 条、`golden_holdout.json` 0 条。
- 离线用例：18/18 通过。
- **F 集尚未跑过**，这是它作为留出集的唯一价值。

---

## v0.2.2 · 2026-10-27 · 超时放宽 + 失败补跑 + 空档告警

### 1. 原有缺陷

- **超时过短**：`timeout=20s` 对 qwen3.8-27b 偏紧（单次常在 15–30s）。`holdout_run_03` 中
  7/17 条候选因单条 trait 读超时整条作废。
- **指标失效被掩盖**：作废的 7 条里**包含全部 4 条漏杀探针**，于是汇总出现
  `0 档 0/0 = n/a`，而"全量 90.0%"的分母只剩 10 条、不含任何该抓类型 —— 这个数没有意义，
  但原先没有任何提示。
- **8 连发易触发限流**：一条候选连续 8 次调用无间隔，失败后又立刻重试，容易撞在同一个限流窗口上。
- 失败只记账不补跑：瞬时失败直接让整条候选作废。

### 2. 改进技术

- 超时 20s → **60s**；重试 2 次；退避基数 1.5 → **3s**（3/6/12，给限流窗口合上的时间）。
- 每次调用之间加 **0.6s 间隔**（`CALL_GAP`），避免 8 连发。
- 新增**失败补跑**：只重试失败的那几条 trait，最多 `--missing-retries` 轮（默认 2），
  已成功的不重跑 —— 一次抖动不再让整条候选作废。
- 汇总对**空档**显式告警：某档有效样本为 0 时打印"该档结论不成立"，不再安静显示 n/a。

### 3. 对应代码位置

- `src/judge/constants.py`：`DEFAULT_TIMEOUT`、`DEFAULT_RETRIES`、`BACKOFF_BASE`、`CALL_GAP`、`MISSING_RETRIES`
- `src/judge/evaluator.py`：`TraitEvaluator.judge_case()` 的补跑循环（`pending` / `failures`）
- `src/cli/run_judge.py`：`--missing-retries`、`_print_summary()` 空档告警
- `tests/judge/test_evaluator.py`（新增，3 个用例：瞬时失败可救回 / 补跑用尽报失败 / 连续失败熔断）
- `docs/08-判定器模块结构.md`：运行时保护第 5 条

### 4. 验证流程

```bash
python -m tests.judge.test_aggregator        # 7 个用例
python -m tests.judge.test_quote_validator   # 8 个用例
python -m tests.judge.test_evaluator         # 3 个用例
python -m src.cli.eval.run_judge --fanout --cases data/golden/golden_holdout.json --json-out reports/holdout_run_04.json
```

实测结果：

- 三组离线用例 **18/18 通过**（7 + 8 + 3），exit 0。
- 补跑用例证明：脚本化瞬时失败 1 次后只补跑失败的那条，`calls == 2`，最终 `failed` 为空。
- 熔断用例证明：连续失败达阈值抛 `JudgeAborted`。
- 修正了一条测试自身的缺陷：`MAX_CONSECUTIVE_FAILURES` 被前一个用例改动后泄漏到后续用例，
  已改为在用例内 try/finally 恢复。

---

## v0.2.1 · 2026-10-27 · 判定器模块化重构 + 运行时保护

### 1. 原有缺陷

- **结构违规**：`src/judge.py` 单文件 600+ 行，违反"单文件 ≤ 300 行"；一个文件同时承担
  .env 读取、规格载入、提示词拼接、HTTP 调用、JSON 解析、引文校验、分数聚合、CLI 八件事，
  违反 SRP；没有 ABC，编排层直接 import `urllib`，违反 DIP；`tests/` 下裸文件 4 个、无子目录、
  无 `__init__.py`，违反模块化规则。
- **观测性缺陷（实际事故）**：整条候选的 8 次调用全部完成后才打印第一行。
  网络异常时屏幕上一个字都没有，用户等了近一小时以为还在跑。实测复现：136 次调用串行、
  无进度、无熔断，最坏可空耗数小时。
- **无连通性探测、无失败熔断**：网络不可用时按 20s×4 次重试逐条白等，不做任何提前退出。

### 2. 改进技术

- 按职责拆为 10 个模块：`constants` / `env_loader` / `spec_loader` / `prompt_builder` /
  `chat_model` / `hit_parser` / `quote_validator` / `aggregator` / `evaluator` / `cli.run_judge`。
  依赖单向向下：入口层 → 编排层 → 能力层 → 常量。
- 定义 `ChatModel`(ABC) 与 `OpenAICompatChatModel`(实现)：编排层只依赖抽象，换服务商只加子类（OCP/DIP）。
- 常量（路径、档位、超时、重试、熔断阈值）全部收敛到 `constants.py`。
- 运行时三重保护：起跑前 `preflight()` 连通性探测；每完成一次调用打一行 `· <trait> ok/FAIL`；
  连续 8 次失败抛 `JudgeAborted` 立即中止。
- 测试迁到 `tests/judge/test_<被测模块>.py`，15 条离线断言，无需 pytest。

### 3. 对应代码位置

- `src/judge/chat_model.py`：`ChatModel`(ABC)、`preflight()`、`OpenAICompatChatModel.complete()`
- `src/judge/evaluator.py`：`TraitEvaluator.judge_case()` 内的连续失败计数与 `JudgeAborted`
- `src/cli/run_judge.py`：`_progress()` 逐次进度、`main()` 中的 preflight 与中止分支
- `src/judge/{constants,env_loader,spec_loader,prompt_builder,hit_parser,quote_validator,aggregator}.py`
- `tests/judge/test_aggregator.py`、`tests/judge/test_quote_validator.py`（新增）
- `docs/08-判定器模块结构.md`（新增：分层、数据流、设计取舍、约束对照）
- 删除 `src/judge.py`（被上述模块替代）

### 4. 验证流程

```bash
python -m tests.judge.test_aggregator        # 期望：7 个用例通过
python -m tests.judge.test_quote_validator   # 期望：8 个用例通过
python -m src.cli.eval.run_judge --cases data/golden/golden_holdout.json --limit 1 --dry   # 只打提示词
python -m src.cli.eval.run_judge --fanout --cases data/golden/golden_holdout.json --json-out reports/holdout_run_03.json
```

实测结果：

- `test_aggregator`：7/7 通过，exit 0。
- `test_quote_validator`：8/8 通过，exit 0（修正了一条自身写错的用例：带引号的整句本就不是子串）。
- `--dry`：正常输出 system 582 字符 + user 提示词。
- preflight：起跑即打印"连通正常，开始评测"，随后逐条打印 `[i/N] <候选>` 与 `· <trait> ok`。
- 文件行数：最大 178 行（`cli/run_judge.py`），其余 19–92 行，全部 < 300。

---

## v0.2.0 · 2026-10-26 · 判定器跨 trait 评测 + 首次留出集盲跑

### 1. 原有缺陷

- **判定输入与规格脱节（最严重）**：`data/characters/sherlock.judge.yaml` 停留在 10:34 的旧版，
  而 `sherlock.yaml` 在 20:43 之后又改过三条规则（直觉需下结论、豁免只适用于方向正确、讽刺须对外部目标）。
  判定器读的是 judge 版，于是 2026-10-26 的 run_02（80.6%）实际评的是**旧规格**——改规格等于没改。
- **跨 trait 去重按字符串相等**：两个 trait 引用同一句、但截断长度不同时被判为不同片段，
  单处漂移被双计成 2 条 soft 直接判 0（D09-c：`Oh, how dreadful for poor Lestrade!` vs 整句）。
- **两条 anti_pattern 过宽**：「把无关细节/职业特征当作罪证」不要求"据此定案"，把仅是怀疑的句子判 0（D05-c / E08-a）；「给出结论但完全不回溯证据」不限定"案情结论"，把"这案子归我"判 0（D04-d）。
- **无留出集**：全部数字都在 dev 上产生，无法回答"规则是否泛化"。
- **判定器不能指向其他测试集**：只能读死 `data/golden/golden_cases.json`。
- **GBK 控制台下崩溃**：打印 ✅ 抛 `UnicodeEncodeError`，跑到一半中断且已消耗模型调用。

### 2. 改进技术

- 规格改动后强制重建判定输入（`src/cli/tools/build_judge_yaml.py`），并以 mtime 校验 judge 版晚于人读版。
- 跨 trait 去重改为**区间重叠判定**：`_span_of()` 把引文映射回候选文本的字符区间，`_overlaps()` 判重叠；支持省略号拼接的多段引文。
- 两条 anti_pattern 收窄：加「并据此宣称其为罪犯/定案」「仅限**案情**结论」限定，并注明"只表达可疑 + 提议核查"走 soft。
- 新增 `--cases` 参数；新增留出集 `data/golden/golden_holdout.json`（E01–E08 / 17 条判定样本），
  按"同轴不同皮、先定 gold 再跑、每条附 `canon_note`"三条纪律编写，且由未参与调规则的一方写。
- 启动时把 stdout/stderr 钉为 UTF-8（`_force_utf8_stdout`），GBK 控制台不再崩溃。

### 3. 对应代码位置

- `src/judge.py`
  - `_force_utf8_stdout()`（L34–L46），`__main__` 处调用（L516）
  - `_span_of()` / `_overlaps()` / `aggregate(results, candidate)`（L253–L303）
  - `--cases` 参数定义与 `golden_path` 读取（CLI 段）
  - `selftest()`：新增"跨 trait 同句不同截断只计 1 条"断言
- `data/characters/sherlock.yaml`：`evidence_first.anti_patterns` 两条 pattern 收窄（L105、L112）
- `data/characters/sherlock.judge.yaml`：重建（296 行 / 10481 字符）
- `data/golden/golden_holdout.json`：新增

### 4. 验证流程

```bash
python -m src.cli.tools.build_judge_yaml
python src/judge.py --selftest
python -m tests.scripts.audit_leakage data/characters/sherlock.judge.yaml
python src/judge.py --fanout --cases data/golden/golden_holdout.json --json-out reports/holdout_run_01.json
```

实测结果：

- `build_judge_yaml`：写出 10481 字符，exit 0；judge 版 mtime 22:23 > 人读版 22:18。
- `--selftest`：解析 / 引文校验 / 聚合 / 区间去重 全部通过，exit 0。
- 泄漏审计（针对 judge.yaml）：L1 = 0（无探针编号与 gold）；L2 = 6/31（`example_bad` 即候选原文，属数据层污染，需换样本，不在本次范围）。
- **留出集首次盲跑：13/17 = 76.5%**（0 档 3/4、2 档 8/9、1 档 2/4），被拒引文 0 条、ambiguity 56 条。
  这是本项目第一个"未见过的样本"上的数字，也是目前唯一可对外的数字。
- 四条分歧（gold 未改动，留待裁决）：E05-b（gold 1 / sys 2）、E06-a（gold 0 / sys 1）、E06-b（gold 1 / sys 2）、E08-a（gold 2 / sys 0）。
  其中 E08-a 是确定性误杀：判定器把"复述输入案情"当成"无依据指认"。
