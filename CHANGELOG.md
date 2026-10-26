# CHANGELOG

> 版本号遵循语义化版本；每节按「原有缺陷 → 改进技术 → 对应代码位置 → 验证流程」四段记录。

## 版本对照表

| 版本 | 日期 | 主题 | 关键产物 |
| --- | --- | --- | --- |
| v0.1.0 | 2026-10-26 | 初始项目导入与版本化 | 一致性规格书、黄金测试集、人设卡、评测脚本与对比报告 |

---

## v0.1.0 · 2026-10-26 · 初始项目导入

### 1. 原有缺陷

- 项目资料仅存在于本地目录，未纳入版本控制，无法追溯、协作与回滚。
- 远端 GitHub 仓库为空白，README 所述「第 0 步」产物（一致性规格书、黄金测试集、人设卡、评分记录）均未发布。
- 已入库的 `reports/` 对比数据与最新人工评分不一致：`scoring_rounds.md` 第一轮中 `D11-a=2`，而旧报告仍按 `0` 统计，导致人工一致率被低估（83.9% vs 实际 87.1%）。

### 2. 改进技术

- 以 `main` 为主干初始化 Git 仓库并关联 GitHub 远端，采用 `feature/0.1.0-initial-project-import` 分支开发、`--no-ff` 合并回主干，保留可审计的提交历史。
- 按 docs / data / tests / reports 四个职责域拆分小步提交，每个提交对应一个可验证单元。
- 使用项目自带的 `tests/validate_golden.py` 与 `tests/compare_rounds.py` 重跑自测，并以脚本生成结果同步 `reports/`，消除陈旧产物，保证报告与评分记录自洽。

### 3. 对应代码位置

- 文档：`docs/01-一致性规格书.md` ~ `docs/06-首轮人工评分校正.md`
- 人设卡：`data/characters/sherlock.yaml`
- 语料说明：`data/corpus/README.md`（`raw/` 依 `.gitignore` 不入库）
- 测试集与脚本：`tests/golden_cases.json`、`tests/validate_golden.py`、`tests/compare_rounds.py`
- 评分留档：`scoring_rounds.md`、`test_A01/`、`test_A02/`、`golden_cases_masked.json`
- 对比报告：`reports/compare_data.md`、`reports/compare_data.json`

### 4. 验证流程

```bash
python tests/validate_golden.py   # 黄金测试集结构校验，期望退出码 0
python tests/compare_rounds.py    # 多方一致率与 OOC 统计，期望退出码 0
```

实测结果：

- 结构校验：输入 12 条 / 判定样本 31 条；gold 分布 `0:9 1:10 2:12`；输出「结构校验通过」，退出码 0。
- 多方对比：`gold-A01 93.5%（QWK 0.882）`、`gold-A02 93.5%（QWK 0.954）`、`gold-H 87.1%（QWK 0.903）`，全体一致 `24/31 = 77.4%`，退出码 0。
