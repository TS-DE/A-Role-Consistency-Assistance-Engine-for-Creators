# 黄金测试集 · 隔离自打评分记录

## 使用说明

- 评分依据只有两样：`docs/01-一致性规格书.md` 和校验 prompt。**禁止**打开 `data/golden/golden_cases.json` 对照，打分期间把它当不存在。
- 候选文本见根目录 `golden_cases_masked.json`（gold / probe / 泄题 note 已遮掉）。
- 每轮一张表，打完**另起一张新表**记下一轮，不许覆盖旧记录。
- 评分口径：0 = OOC（出戏）/ 1 = drift（有偏差但角色还成立）/ 2 = pass（符合人设）。
- 打不准、拿不准的条目照常打分，但**必须在备注里写"拿不准"以及拿不准的原因**——这些正是规格书的洞。

---

## 第一轮 · 2026-10-25

| 候选ID | trait                 | 评分（0/1/2） | 依据规则（规格书哪一条）                                                            | 备注                   |
| ------ | --------------------- | ------------- | ----------------------------------------------------------------------------------- | ---------------------- |
| D01-a  | emotional_restraint   | 0             |                                                                                     |                        |
| D01-b  | emotional_restraint   | 2             |                                                                                     |                        |
| D02-a  | evidence_first        | 0             | 上下文证据不够全面                                                                  |                        |
| D02-b  | evidence_first        | 2             |                                                                                     |                        |
| D03-a  | no_glory_seeking      | 0             |                                                                                     |                        |
| D03-b  | no_glory_seeking      | 2             |                                                                                     |                        |
| D04-a  | emotional_restraint   | 0             |                                                                                     |                        |
| D04-b  | emotional_restraint   | 2             | 命中“`用命令句代替安慰（"去睡。案子我来。"）`”，而没有命中anti_patterns中的反例 |                        |
| D04-c  | emotional_restraint   | 2             | 符合rule的其中一条                                                                  |                        |
| D04-d  | voice_register        | 0             |                                                                                     |                        |
| D05-a  | evidence_first        | 1             | 命中soft：`给出结论但完全不回溯任何证据`                                          |                        |
| D05-b  | evidence_first        | 2             |                                                                                     |                        |
| D05-c  | evidence_first        | 1             | 不清楚。`给出结论但但回溯了一定的证据`                                            |                        |
| D06-a  | emotional_restraint   | 0             | 命中：`抒情式共情与自我情绪表露`                                                  |                        |
| D06-b  | emotional_restraint   | 2             |                                                                                     |                        |
| D07-a  | era_consistency       | 0             | 出现DNA                                                                             |                        |
| D07-b  | era_consistency       | 0             | 出现DNA                                                                             |                        |
| D07-c  | era_consistency       | 2             |                                                                                     |                        |
| D08-a  | era_consistency       | 0             |                                                                                     |                        |
| D08-b  | era_consistency       | 2             | 没命中任何一条`anti_patterns`                                                     |                        |
| D09-a  | voice_register        | 1             | 似乎命中了`大段抒情感慨、情绪宣泄`。                                              | 实际我不确定是否有命中 |
| D09-b  | voice_register        | 2             |                                                                                     |                        |
| D09-c  | voice_register        | 1             | `命中了大段抒情感慨、情绪宣泄`                                                    |                        |
| D10-a  | watson_rapport        | 2             |                                                                                     |                        |
| D10-b  | watson_rapport        | 1             | 命中一条sofr<br />`极度刻薄、不信任华生能力，拒绝让他参与办案`                    | 实际我认为因该为0      |
| D11-a  | moral_flexibility     | 2             | 未命中soft，符合rule                                                                |                        |
| D11-b  | moral_flexibility     | 1             | 命中一条soft`僵化死守法条，对被逼复仇的苦主也一定要送进监狱，毫无变通`            |                        |
| D11-c  | moral_flexibility     | 1             | 命中soft:`无视法律，肆意放走蓄意杀人的歹徒`                                       |                        |
| D12-a  | intellectual_appetite | 1             | 命中soft:`对送来门的委托全然冷漠...`                                              |                        |
| D12-b  | intellectual_appetite | 1             | 命中soft:`对平淡的小案子表现出兴致勃勃、满怀热情的状态`                           |                        |
| D12-c  | intellectual_appetite | 1             | 命中soft:`对送来门的委托全然冷漠`...                                              |                        |

### 第一轮小结（打完再填）

- 自评时觉得"规格书没写清、只能凭感觉"的条目：__
- 当时犹豫超过 1 分钟的条目：__

---

## 第二轮 · 日期：_2026.10.26__（与第一轮至少隔一天，凭记忆重打，不翻第一轮答案）

| 候选ID | trait                 | 评分（0/1/2） | 依据规则（规格书哪一条）                                                                    | 备注                                                  |
| ------ | --------------------- | ------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| D01-a  | emotional_restraint   |               |                                                                                             |                                                       |
| D01-b  | emotional_restraint   |               |                                                                                             |                                                       |
| D02-a  | evidence_first        |               |                                                                                             |                                                       |
| D02-b  | evidence_first        |               |                                                                                             |                                                       |
| D03-a  | no_glory_seeking      |               |                                                                                             |                                                       |
| D03-b  | no_glory_seeking      |               |                                                                                             |                                                       |
| D04-a  | emotional_restraint   |               |                                                                                             |                                                       |
| D04-b  | emotional_restraint   | 1             | 因该命中的是soft:`连续两轮以上主动关心对方感受`                                           |                                                       |
| D04-c  | emotional_restraint   |               |                                                                                             |                                                       |
| D04-d  | voice_register        | 1             | 命中一次soft:`以"我"为中心替对方做人生决定 / 宣誓式台词（大男主腔）`                      | 但实际上我认为这段话并不符合福尔摩斯原著形象，因该判0 |
| D05-a  | evidence_first        | 0             | 命中hard:<br />`把无关细节、职业特征或外貌当作罪证 —— 形式上有"细节"，实质上没有推断链` |                                                       |
| D05-b  | evidence_first        |               |                                                                                             |                                                       |
| D05-c  | evidence_first        |               |                                                                                             |                                                       |
| D06-a  | emotional_restraint   |               |                                                                                             |                                                       |
| D06-b  | emotional_restraint   |               |                                                                                             |                                                       |
| D07-a  | era_consistency       |               |                                                                                             |                                                       |
| D07-b  | era_consistency       | 0             | 命中hard:`出现现代刑侦词汇`                                                               |                                                       |
| D07-c  | era_consistency       |               |                                                                                             |                                                       |
| D08-a  | era_consistency       |               |                                                                                             |                                                       |
| D08-b  | era_consistency       |               |                                                                                             |                                                       |
| D09-a  | voice_register        |               |                                                                                             |                                                       |
| D09-b  | voice_register        |               |                                                                                             |                                                       |
| D09-c  | voice_register        |               |                                                                                             |                                                       |
| D10-a  | watson_rapport        |               |                                                                                             |                                                       |
| D10-b  | watson_rapport        |               |                                                                                             |                                                       |
| D11-a  | moral_flexibility     | 2             | 符合rule(1)                                                                                 |                                                       |
| D11-b  | moral_flexibility     |               |                                                                                             |                                                       |
| D11-c  | moral_flexibility     | 1             | 命中soft:`无视法律，肆意放走蓄意杀人的歹徒`                                               |                                                       |
| D12-a  | intellectual_appetite | 2             | 属于not_ooc，`嫌琐碎但接案 = 2`                                                           |                                                       |
| D12-b  | intellectual_appetite |               |                                                                                             |                                                       |
| D12-c  | intellectual_appetite | 1             | 属于`直接拒绝/逐客 = 1（D12-c）`                                                          |                                                       |

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
