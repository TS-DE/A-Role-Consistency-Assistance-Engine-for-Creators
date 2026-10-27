# CHANGELOG

> 版本号遵循语义化版本；每节按「原有缺陷 → 改进技术 → 对应代码位置 → 验证流程」四段记录。

## 版本对照表

| 版本 | 日期 | 主题 | 关键产物 |
| --- | --- | --- | --- |
| v0.2.3 | 2026-10-27 | 留出集退役 + F 集封存 + 推功酸味规则 | E 集转回归集、F01–F08、`no_glory_seeking` 第 3 条 soft、泄漏复检 |
| v0.2.2 | 2026-10-27 | 超时放宽 + 失败补跑 + 空档告警 | 超时 60s、调用间隔 0.6s、`--missing-retries` 补跑、空档显式告警、`test_evaluator` |
| v0.2.1 | 2026-10-27 | 判定器模块化重构 + 运行时保护 | 10 个模块分层、`ChatModel` ABC、preflight、逐 trait 进度、失败熔断、离线单测 |
| v0.2.0 | 2026-10-26 | 判定器跨 trait 评测 + 首次留出集盲跑 | `--fanout`、区间去重聚合、`--cases`、留出集 E01–E08、GBK 崩栈修复 |
| v0.1.0 | 2026-10-26 | 初始项目导入与版本化 | 一致性规格书、黄金测试集、人设卡、评测脚本与对比报告 |

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

- `tests/golden_holdout_f.json`（新增，留出集）
- `data/characters/sherlock.yaml`：`no_glory_seeking.anti_patterns` 新增 soft 条目
- `docs/07-A03泄漏审计.md`：新增第七节「留出集的退役规则」
- `data/characters/sherlock.judge.yaml`：重建（10811 字符）

### 4. 验证流程

```bash
python -c "import json;json.load(open('tests/golden_holdout_f.json',encoding='utf-8'))"   # 结构
python tools/build_judge_yaml.py
python tests/audit_leakage.py data/characters/sherlock.judge.yaml
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
python -m src.cli.run_judge --fanout --cases tests/golden_holdout.json --json-out reports/holdout_run_04.json
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
python -m src.cli.run_judge --cases tests/golden_holdout.json --limit 1 --dry   # 只打提示词
python -m src.cli.run_judge --fanout --cases tests/golden_holdout.json --json-out reports/holdout_run_03.json
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
- **判定器不能指向其他测试集**：只能读死 `tests/golden_cases.json`。
- **GBK 控制台下崩溃**：打印 ✅ 抛 `UnicodeEncodeError`，跑到一半中断且已消耗模型调用。

### 2. 改进技术

- 规格改动后强制重建判定输入（`tools/build_judge_yaml.py`），并以 mtime 校验 judge 版晚于人读版。
- 跨 trait 去重改为**区间重叠判定**：`_span_of()` 把引文映射回候选文本的字符区间，`_overlaps()` 判重叠；支持省略号拼接的多段引文。
- 两条 anti_pattern 收窄：加「并据此宣称其为罪犯/定案」「仅限**案情**结论」限定，并注明"只表达可疑 + 提议核查"走 soft。
- 新增 `--cases` 参数；新增留出集 `tests/golden_holdout.json`（E01–E08 / 17 条判定样本），
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
- `tests/golden_holdout.json`：新增

### 4. 验证流程

```bash
python tools/build_judge_yaml.py
python src/judge.py --selftest
python tests/audit_leakage.py data/characters/sherlock.judge.yaml
python src/judge.py --fanout --cases tests/golden_holdout.json --json-out reports/holdout_run_01.json
```

实测结果：

- `build_judge_yaml`：写出 10481 字符，exit 0；judge 版 mtime 22:23 > 人读版 22:18。
- `--selftest`：解析 / 引文校验 / 聚合 / 区间去重 全部通过，exit 0。
- 泄漏审计（针对 judge.yaml）：L1 = 0（无探针编号与 gold）；L2 = 6/31（`example_bad` 即候选原文，属数据层污染，需换样本，不在本次范围）。
- **留出集首次盲跑：13/17 = 76.5%**（0 档 3/4、2 档 8/9、1 档 2/4），被拒引文 0 条、ambiguity 56 条。
  这是本项目第一个"未见过的样本"上的数字，也是目前唯一可对外的数字。
- 四条分歧（gold 未改动，留待裁决）：E05-b（gold 1 / sys 2）、E06-a（gold 0 / sys 1）、E06-b（gold 1 / sys 2）、E08-a（gold 2 / sys 0）。
  其中 E08-a 是确定性误杀：判定器把"复述输入案情"当成"无依据指认"。
