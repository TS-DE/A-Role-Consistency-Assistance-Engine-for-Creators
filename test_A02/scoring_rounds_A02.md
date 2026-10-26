# 黄金测试集 · 隔离自打评分记录

## 使用说明

- 评分依据只有两样：`docs/01-一致性规格书.md` 和校验 prompt。**禁止**打开 `tests/golden_cases.json` 对照，打分期间把它当不存在。
- 候选文本见根目录 `golden_cases_masked.json`（gold / probe / 泄题 note 已遮掉）。
- 每轮一张表，打完**另起一张新表**记下一轮，不许覆盖旧记录。
- 评分口径：0 = OOC（出戏）/ 1 = drift（有偏差但角色还成立）/ 2 = pass（符合人设）。
- 打不准、拿不准的条目照常打分，但**必须在备注里写"拿不准"以及拿不准的原因**——这些正是规格书的洞。

---

## 第一轮 · 2026-10-25

| 候选ID | trait                 | 评分（0/1/2） | 依据规则（规格书哪一条） | 备注 |
| ------ | --------------------- | ------------- | ------------------------ | ---- |
| D01-a   | emotional_restraint   |       0       | §三（emotional_restraint 为 hard）；§五第1条（关心应实用而非抒情） | 抒情式安慰与亲密称呼明显偏离实用、克制的关心方式。 |
| D01-b   | emotional_restraint   |       2       | §五第1条；§四 evidence_first 样板（主动索要、测量线索） | 克制情绪，并把注意力转回可观察的鞋印与案件。 |
| D02-a   | evidence_first        |       0       | §二；§四 evidence_first rule 1–3、hard anti-pattern | 没有现场证据便直接指认面包师，命中无依据锁定具体人物。 |
| D02-b   | evidence_first        |       2       | §四 evidence_first rule 1–3、observable_behaviors | 明确表示信息不足，并要求检查窗台和地板。 |
| D03-a   | no_glory_seeking      |       0       | §三（no_glory_seeking 为 hard） | 主动要求头版宣传自己的推理，明显追逐名声。 |
| D03-b   | no_glory_seeking      |       2       | §三（no_glory_seeking 为 hard）；§五第5条的角色表达边界 | 明确表示办案并非为了报纸或名利。 |
| D04-a   | emotional_restraint   |       0       | §三（emotional_restraint 为 hard）；§五第1条 | 用“理解你的痛苦、我在这里安慰你”作抒情安慰，不是实用式关心。 |
| D04-b   | emotional_restraint   |       1       | §四·补 rule (5)(6) 与 soft anti-pattern；§五第1条 | 拿不准：规格书明确将“撑不到明天”式健康/安危冷嘲判为1，但该规则归于 watson_rapport，而本候选标为 emotional_restraint（hard）。按 D04 特例的明示判分记1。 |
| D04-c   | emotional_restraint   |       2       | §五第1条（实用式关心合格） | 只劝华生休息并接手案件，符合规格书明确列出的实用式关心。 |
| D04-d   | voice_register        |       1       | §四·补二（voice_register 的大男主腔 soft anti-pattern） | 以“我不许你去”“案子归我”替对方作决定，命中一条 soft。 |
| D05-a   | evidence_first        |       0       | §四 evidence_first rule 1–3、hard anti-pattern | 把煤工的黑手直接当作有罪证明，作出无依据的罪责判断。 |
| D05-b   | evidence_first        |       2       | §四 evidence_first rule 1–3、observable_behaviors | 指出黑手可能只是职业痕迹，并要求脚印、证人等可核验线索。 |
| D05-c   | evidence_first        |       1       | §二；§四 evidence_first rule 1–3 | 拿不准：候选未直接断言煤工是凶手，但把职业性黑手当成嫌疑依据。规格书未明确“可观察但未必有证明力的细节”是否足够、暂时怀疑是否属于无依据指认；按轻微推断漂移暂记1。 |
| D06-a   | emotional_restraint   |       0       | §三（emotional_restraint 为 hard）；§五第1、2条 | 在没有特殊事件依据时给出浓厚、保证式的情绪安慰，偏离情绪克制。 |
| D06-b   | emotional_restraint   |       2       | §五第1条（实用而非抒情的关心） | 不作情绪性保证，提出休息并明天重新查证事实。 |
| D07-a   | era_consistency       |       0       | §三 era_consistency（hard）；§三“为什么新增 era_consistency” | 直接提出用现代 DNA 检测解决案件，属时代不自洽。 |
| D07-b   | era_consistency       |       0       | §三 era_consistency（hard）；§一语言/词表口径 | 拿不准：回复否定了现代检测的可用性，却仍直接提及年代外的“DNA”；规格书未说明否定式或元话语提及是否豁免。按时代词表匹配从严记0。 |
| D07-c   | era_consistency       |       2       | §三 era_consistency（hard）的时代边界；§四证据导向样板 | 未提及年代外技术，改为检查杯中沉淀，符合时代与物证导向。 |
| D08-a   | era_consistency       |       0       | §三 era_consistency（hard）；§三“为什么新增 era_consistency” | 要求调取街头监控录像，属于规格书列明的时代外技术。 |
| D08-b   | era_consistency       |       2       | §三 era_consistency 的时代背景 | 派警员询问住户目击情况，使用符合时代的调查方式。 |
| D09-a   | voice_register        |       1       | §五第3条（刻薄讽刺可用，但应是冷的而非热络） | 讽刺方向符合角色，但“Ha!”与“What a lark!”显得较热闹；暂按一处语气漂移记1。 |
| D09-b   | voice_register        |       2       | §五第3条（刻薄的讽刺与幽默不属于 OOC） | 针对雷斯垂德的冷面挖苦，语气克制，符合反向清单。 |
| D09-c   | voice_register        |       1       | §五第3条（讽刺应冷而非热络） | 拿不准：这句既可读成冷嘲式反讽，也可读成热络同情；规格书没有可观察标准区分两种语气，暂按轻微语气漂移记1。 |
| D10-a   | watson_rapport        |       2       | §三 watson_rapport 的定义；§五第3条 | 针对“看见/观察”的区别调侃华生，属于允许的观察力调侃，关系未疏远。 |
| D10-b   | watson_rapport        |       1       | §三 watson_rapport 的定义；§四·补 rule (5) | 拿不准：嘲讽仍针对观察力（允许的范围），但“quite useless to me”可能越过正常调侃、表现疏远；规格书未界定刻薄程度的边界，暂记1。 |
| D11-a   | moral_flexibility     |       2       | §三（moral_flexibility 为 soft）；§一三档判分原则 | 拿不准：规格书只列出 moral_flexibility 为 soft，未提供具体 if-then / anti-pattern；此回复考虑了复仇动机且未把执法表态绝对化，暂判2。 |
| D11-b   | moral_flexibility     |       1       | §三（moral_flexibility 为 soft）；§一三档判分原则 | 拿不准：规格书没有给出该 trait 的具体判据；“无论理由如何，所有杀人者都必须被处绞刑”表现绝对化，暂按方向偏差记1。 |
| D11-c   | moral_flexibility     |       0       | §一聚合顺序与“杀人于我无关”的示例；§三（moral_flexibility 为 soft） | 拿不准：规格书把“杀人于我无关”列为应纳入 OOC 的明显出戏回复，但没有逐项列出本句累计命中的两条 soft；据该明示示例暂判0。 |
| D12-a   | intellectual_appetite |       2       | §三（intellectual_appetite 为 soft）；§五第5条（拒绝无关问题并非 OOC） | 拿不准：规格书未提供 intellectual_appetite 的具体 if-then / anti-pattern；对小案感到乏味但仍同意调查，暂判2。 |
| D12-b   | intellectual_appetite |       1       | §三（intellectual_appetite 为 soft）；§一三档判分原则 | 拿不准：规格书未给出 intellectual_appetite 的具体判据；将寻猫小事描述为“thrilling / delightful”显得过度兴奋，暂按轻微漂移记1。 |
| D12-c   | intellectual_appetite |       2       | §五第5条（拒绝无关问题不是 OOC）；§三（intellectual_appetite 为 soft） | 拿不准：规格书的豁免针对“无关问题”，而寻猫是否属于无关委托未明；按对琐事缺乏兴趣的角色方向暂判2。 |

### 第一轮小结（打完再填）

- 自评时觉得"规格书没写清、只能凭感觉"的条目：__
- 当时犹豫超过 1 分钟的条目：__

---

## 第二轮 · 日期：____（与第一轮至少隔一天，凭记忆重打，不翻第一轮答案）

| 候选ID | trait                 | 评分（0/1/2） | 依据规则（规格书哪一条） | 备注 |
| ------ | --------------------- | ------------- | ------------------------ | ---- |
| D01-a  | emotional_restraint   |               |                          |      |
| D01-b  | emotional_restraint   |               |                          |      |
| D02-a  | evidence_first        |               |                          |      |
| D02-b  | evidence_first        |               |                          |      |
| D03-a  | no_glory_seeking      |               |                          |      |
| D03-b  | no_glory_seeking      |               |                          |      |
| D04-a  | emotional_restraint   |               |                          |      |
| D04-b  | emotional_restraint   |               |                          |      |
| D04-c  | emotional_restraint   |               |                          |      |
| D04-d  | voice_register        |               |                          |      |
| D05-a  | evidence_first        |               |                          |      |
| D05-b  | evidence_first        |               |                          |      |
| D05-c  | evidence_first        |               |                          |      |
| D06-a  | emotional_restraint   |               |                          |      |
| D06-b  | emotional_restraint   |               |                          |      |
| D07-a  | era_consistency       |               |                          |      |
| D07-b  | era_consistency       |               |                          |      |
| D07-c  | era_consistency       |               |                          |      |
| D08-a  | era_consistency       |               |                          |      |
| D08-b  | era_consistency       |               |                          |      |
| D09-a  | voice_register        |               |                          |      |
| D09-b  | voice_register        |               |                          |      |
| D09-c  | voice_register        |               |                          |      |
| D10-a  | watson_rapport        |               |                          |      |
| D10-b  | watson_rapport        |               |                          |      |
| D11-a  | moral_flexibility     |               |                          |      |
| D11-b  | moral_flexibility     |               |                          |      |
| D11-c  | moral_flexibility     |               |                          |      |
| D12-a  | intellectual_appetite |               |                          |      |
| D12-b  | intellectual_appetite |               |                          |      |
| D12-c  | intellectual_appetite |               |                          |      |

### 第二轮小结（打完再填）

- 自评时觉得"规格书没写清、只能凭感觉"的条目：__
- 与第一轮回忆不一致、需要翻回第一轮核对的条目：__

---

## 两轮一致率对照（两轮都打完后再填，先别看 gold）

| 候选ID | 第一轮 | 第二轮 | 两轮一致？ | 若不一致：当时我各按哪条规则判的 | 备注 |
| ------ | ------ | ------ | ---------- | -------------------------------- | ---- |
| D01-a  |        |        |            |                                  |      |
| D01-b  |        |        |            |                                  |      |
| D02-a  |        |        |            |                                  |      |
| D02-b  |        |        |            |                                  |      |
| D03-a  |        |        |            |                                  |      |
| D03-b  |        |        |            |                                  |      |
| D04-a  |        |        |            |                                  |      |
| D04-b  |        |        |            |                                  |      |
| D04-c  |        |        |            |                                  |      |
| D04-d  |        |        |            |                                  |      |
| D05-a  |        |        |            |                                  |      |
| D05-b  |        |        |            |                                  |      |
| D05-c  |        |        |            |                                  |      |
| D06-a  |        |        |            |                                  |      |
| D06-b  |        |        |            |                                  |      |
| D07-a  |        |        |            |                                  |      |
| D07-b  |        |        |            |                                  |      |
| D07-c  |        |        |            |                                  |      |
| D08-a  |        |        |            |                                  |      |
| D08-b  |        |        |            |                                  |      |
| D09-a  |        |        |            |                                  |      |
| D09-b  |        |        |            |                                  |      |
| D09-c  |        |        |            |                                  |      |
| D10-a  |        |        |            |                                  |      |
| D10-b  |        |        |            |                                  |      |
| D11-a  |        |        |            |                                  |      |
| D11-b  |        |        |            |                                  |      |
| D11-c  |        |        |            |                                  |      |
| D12-a  |        |        |            |                                  |      |
| D12-b  |        |        |            |                                  |      |
| D12-c  |        |        |            |                                  |      |

**两轮一致率 = 两轮评分相同的条数 ÷ 31。目标 ≥ 90%（即至多 3 条不一致）。**

---

## 争议项复核（两轮打完、对完 gold 之后再做）

逐条回答：按规格书现有文字，能否推导出唯一答案？不能 → 规格书有洞 → **改规则，不改 gold**。

| 候选ID | 我的最终评分 | gold | 一致？ | 按规格书能否推出唯一答案？ | 结论（改哪条规则 / 只是理解偏差） | 备注 |
| ------ | ------------ | ---- | ------ | -------------------------- | --------------------------------- | ---- |
| D03-b  |              |      |        |                            |                                   |      |
| D04-b  |              |      |        |                            |                                   |      |
| D04-d  |              |      |        |                            |                                   |      |
| D09-c  |              |      |        |                            |                                   |      |
| D11-c  |              |      |        |                            |                                   |      |

### 总结（全部完成后填）

- 两轮一致率：__ / 31 = __%
- 与 gold 的一致率：__ / 31 = __%
- 发现并修补的规格书漏洞（列条 + 改了哪条规则）：__
