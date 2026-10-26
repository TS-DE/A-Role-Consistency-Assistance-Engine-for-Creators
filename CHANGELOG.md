# CHANGELOG

> 版本号遵循语义化版本；每节按「原有缺陷 → 改进技术 → 对应代码位置 → 验证流程」四段记录。

## 版本对照表

| 版本 | 日期 | 主题 | 关键产物 |
| --- | --- | --- | --- |
| v0.2.0 | 2026-10-26 | 判定器跨 trait 评测 + 首次留出集盲跑 | `--fanout`、区间去重聚合、`--cases`、留出集 E01–E08、GBK 崩栈修复 |
| v0.1.0 | 2026-10-26 | 初始项目导入与版本化 | 一致性规格书、黄金测试集、人设卡、评测脚本与对比报告 |

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
