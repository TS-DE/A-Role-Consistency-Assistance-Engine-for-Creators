# data/golden —— 黄金测试集（数据，不是代码）

三个文件，三种身份。**别把它们混用**，这是整套评测可信度的根基（详见 `docs/07`）。

| 文件 | 集合 | 身份 | 允许做什么 |
|---|---|---|---|
| `golden_cases.json` | D01–D12（31 条判定样本） | **dev** | 随便跑、随便调规则 |
| `golden_holdout.json` | E01–E08（17 条） | **回归集**（已退役的留出集） | 每次改完规则必须跑，防倒退 |
| `golden_holdout_f.json` | F01–F08（17 条） | **留出集**（已用尽，成绩 94.1%，qwen3.8-27b） | **已跑过一次，不再跑** |
| `golden_holdout_g.json` | G01–G08（19 条） | **留出集**（已用尽：2026-10-28 一次跑毕，14/19 = 73.7%，qwen3.8-flash） | **已跑过一次，不再跑**；分歧记录见 docs/07 §十一 |

## 为什么数据从 `tests/` 搬到这里

按《通用约束提示词》第二节，父目录下不得出现裸文件；`tests/` 根曾同时躺着 3 个脚本和
3 个 JSON。**数据与代码分开**还有一个额外好处：换数据集不需要动测试目录结构。

## 相关命令

```bash
python -m tests.scripts.validate_golden     # 结构校验
python -m tests.scripts.compare_rounds      # 多方一致率与 κ
python -m tests.scripts.audit_leakage data/characters/sherlock.judge.yaml
python -m src.cli.eval.run_judge --fanout --cases data/golden/golden_holdout.json
```

## 修改纪律

1. 改 `golden_cases.json`（dev）随时可以。
2. 改 `golden_holdout*.json` 等于**换仪器**：已经报过的数字不能再用，需重跑并注明。
3. 新增留出集按 `docs/07` 第七节的四条规则：同轴不同皮、先定 gold 再跑、只跑一次、写的人不调规则。
