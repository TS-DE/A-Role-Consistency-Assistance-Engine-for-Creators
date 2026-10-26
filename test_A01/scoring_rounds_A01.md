# 黄金测试集 · 隔离自打评分记录

## 使用说明

- 评分依据只有两样：`docs/01-一致性规格书.md` 和校验 prompt。**禁止**打开 `tests/golden_cases.json` 对照，打分期间把它当不存在。
- 候选文本见根目录 `golden_cases_masked.json`（gold / probe / 泄题 note 已遮掉）。
- 每轮一张表，打完**另起一张新表**记下一轮，不许覆盖旧记录。
- 评分口径：0 = OOC（出戏）/ 1 = drift（有偏差但角色还成立）/ 2 = pass（符合人设）。
- 打不准、拿不准的条目照常打分，但**必须在备注里写"拿不准"以及拿不准的原因**——这些正是规格书的洞。

---

## 第一轮 · 2026-10-25

| 候选ID | trait | 评分（0/1/2） | 依据规则（规格书哪一条） | 备注 |
| ------ | --------------------- | ------------- | ------------------------ | ---- |
| D01-a | emotional_restraint | 0 | emotional_restraint（hard）："Let it all out / I am here for you" 为抒情式安慰，情绪外露；违反反向清单第 1 条"关心可以，抒情不行" | |
| D01-b | emotional_restraint | 2 | emotional_restraint：以实用口吻把注意力拉回案件，无 anti_pattern | 符合反向清单"冷淡但真实不是 OOC" |
| D02-a | evidence_first | 0 | evidence_first rule 3（hard）：零证据直接指认具体人物，命中 anti_pattern"无依据直接指认" | |
| D02-b | evidence_first | 2 | evidence_first rule 1/2：复述可观测细节（窗开、无脚印、无尘土），明示"I have no data yet"，主动索要线索 | |
| D03-a | no_glory_seeking | 0 | no_glory_seeking（hard）：主动索要记者、追求头版报道 | |
| D03-b | no_glory_seeking | 2 | no_glory_seeking：明确表示不为报纸办案，淡然处之 | 语气带倨傲但未命中任何 anti_pattern；为何列入争议项，留待对完 gold 复核 |
| D04-a | emotional_restraint | 0 | emotional_restraint（hard）："I understand your pain / I am here for you" 抒情式安慰 | 与场景（受伤想跟去现场）亦错位，但按候选 trait 判 emotional_restraint 命中 hard |
| D04-b | emotional_restraint | 1 | 四·补 watson_rapport rule(5)(6)：命令式关心方向正确，但"You will not last the night"以对方健康作冷嘲断言 → 命中 1 条 soft | 规格书四·补给出的标准判例：整句判 1，不判 2、不判 0 |
| D04-c | emotional_restraint | 2 | 反向清单第 1 条：命令式关心（去睡、案子我来）合格，无冷嘲夹带 | |
| D04-d | voice_register | 1 | 四·补二 voice_register 新增 soft："I forbid it. The case is mine" 属宣誓式/占有式大男主腔 → 命中 1 条 soft | 规格书标注 D04-d 即该条探针 |
| D05-a | evidence_first | 0 | evidence_first rule 3（hard）：附和华生，以"黑手"直接锁定凶手（黑手是职业痕迹，非罪证） | |
| D05-b | evidence_first | 2 | evidence_first rule 1/2：指出黑手是"trade, not guilt"，索要可衡量的证据 | |
| D05-c | evidence_first | 1 | evidence_first（soft 层）：未锁定指认（不触 hard），但仅凭职业特征生成"suspicious / trouble me"的印象式怀疑，属证据使用松动 → 1 条 soft | **拿不准**：若严格按字面 anti_pattern（未指认、且复述了输入细节）应判 2；判 1 是把"trouble me"归入"以直觉为理由"的弱化形态，规格书没写清这种中间态 |
| D06-a | emotional_restraint | 0 | emotional_restraint（hard）："Let me comfort you" 主动抒情安慰，违反反向清单第 1 条 | |
| D06-b | emotional_restraint | 2 | emotional_restraint：坦承"Comfort is not my trade"+实用指引（去睡、明日再看事实）；符合反向清单第 1、5 条 | 拒绝情感表演≠不礼貌 |
| D07-a | era_consistency | 0 | era_consistency（hard）：提及 DNA 检测，命中时代词表禁词 | |
| D07-b | era_consistency | 2 | era_consistency：明示 DNA 属未来未知之物，转向当时可行的沉淀物检验 | |
| D07-c | era_consistency | 2 | era_consistency：否认存在该检测，转向沉淀物检验 | 与 b 的差异仅在是否点破"未来"，均不触词表 |
| D08-a | era_consistency | 0 | era_consistency（hard）：监控录像/街拍摄像头，命中时代词表禁词 | |
| D08-b | era_consistency | 2 | era_consistency：以警员走访住户、煤气灯时代取证手段替代 | |
| D09-a | voice_register | 1 | voice_register（soft）：反讽方向正确，但"Ha! / What a lark!"语气热络嬉闹，违反反向清单第 3 条"讽刺是冷的，不是热络的" | |
| D09-b | voice_register | 2 | voice_register：冷静、带刺、克制的讽刺，符合语域 | |
| D09-c | voice_register | 1 | voice_register（soft）：假慈悲式客套（"Oh, how dreadful… One does feel for the man"）语域做作，偏离冷嘲 | **拿不准**：反讽本身可享"刻薄讽刺"豁免；扣分点在"做作/热络"的语域漂移是否足以构成 soft，规格书对 voice_register 除大男主腔外未列细则 |
| D10-a | watson_rapport | 2 | watson_rapport：调侃观察力属允许范围（"You saw, but you did not observe"），关系位置正常 | |
| D10-b | watson_rapport | 1 | watson_rapport（soft）："you are quite useless to me"贬低+疏远华生，超出"调侃观察力"边界 → 命中 1 条 soft | **拿不准**：若把人身侮辱式语气同时计入 voice_register，则 soft≥2 → 0；规格书对"疏远/贬低"只有 soft 定性、未写明第二条轴怎么算 |
| D11-a | moral_flexibility | 2 | moral_flexibility：基于动机（为妻复仇）与"法律于事无补"的判断放行，符合原作行为模式 | |
| D11-b | moral_flexibility | 1 | moral_flexibility（soft）："Every killer must hang"绝对法律主义，与道德弹性方向相反 → 命中 1 条 soft | **拿不准**：立场与福尔摩斯相反、直觉上更重，但该 trait 为 soft、无 hard 可依，按聚合规则封顶 1 |
| D11-c | moral_flexibility | 0 | 聚合规则第 2 条（soft ≥2 → 0）：①moral_flexibility 被扭曲为道德虚无（弹性≠"杀人在道德上无关紧要"）；②intellectual_appetite（soft）：不经任何查证、对案件无智性兴趣直接放走 | 规格书聚合规则处明举"杀人于我无关"作为 soft 累计封 OOC 的典型例；第二条 soft 归 intellectual_appetite 还是 voice_register，留待复核 |
| D12-a | intellectual_appetite | 2 | intellectual_appetite：嫌琐碎但接案（"my mind rebels at the triviality"），符合原作常态 | |
| D12-b | intellectual_appetite | 1 | intellectual_appetite（soft）：对丢猫伪装"thrilling / delightful"，智性饥渴被夸张失真 → 命中 1 条 soft | |
| D12-c | intellectual_appetite | 1 | intellectual_appetite（soft）：对委托全然冷漠（"I have no interest"）+ 生硬逐客，与"嫌弃但仍以智性参与"的人设有偏 → 命中 1 条 soft | **拿不准**：原作中确有推掉琐事的先例，"完全拒绝"是 1 还是 2 规格书未写清；反向清单第 5 条豁免的是"无关问题"，正式委托案不属此列 |

### 第一轮小结（打完再填）

- 自评时觉得"规格书没写清、只能凭感觉"的条目：D05-c（把职业痕迹当可疑依据，算不算"以直觉为理由"的弱化形态）；D09-c（voice_register 除大男主腔外无细则，"做作客套"无处落条）；D10-b（"贬低疏远华生"只有 soft 定性，是否计第二条轴不明）；D11-b（与立场完全相反但 trait 是 soft，档位封顶是否合理存疑）；D11-c（第二条 soft 归 intellectual_appetite 还是 voice_register，无依据）；D12-c（"完全拒绝琐碎委托"与"嫌弃但接案"的边界未写）
- 当时犹豫超过 1 分钟的条目：D05-c、D09-c、D10-b、D11-b、D11-c、D12-c

---

## 第二轮 · 日期：____（与第一轮至少隔一天，凭记忆重打，不翻第一轮答案）

| 候选ID | trait | 评分（0/1/2） | 依据规则（规格书哪一条） | 备注 |
| ------ | --------------------- | ------------- | ------------------------ | ---- |
| D01-a | emotional_restraint | | | |
| D01-b | emotional_restraint | | | |
| D02-a | evidence_first | | | |
| D02-b | evidence_first | | | |
| D03-a | no_glory_seeking | | | |
| D03-b | no_glory_seeking | | | |
| D04-a | emotional_restraint | | | |
| D04-b | emotional_restraint | | | |
| D04-c | emotional_restraint | | | |
| D04-d | voice_register | | | |
| D05-a | evidence_first | | | |
| D05-b | evidence_first | | | |
| D05-c | evidence_first | | | |
| D06-a | emotional_restraint | | | |
| D06-b | emotional_restraint | | | |
| D07-a | era_consistency | | | |
| D07-b | era_consistency | | | |
| D07-c | era_consistency | | | |
| D08-a | era_consistency | | | |
| D08-b | era_consistency | | | |
| D09-a | voice_register | | | |
| D09-b | voice_register | | | |
| D09-c | voice_register | | | |
| D10-a | watson_rapport | | | |
| D10-b | watson_rapport | | | |
| D11-a | moral_flexibility | | | |
| D11-b | moral_flexibility | | | |
| D11-c | moral_flexibility | | | |
| D12-a | intellectual_appetite | | | |
| D12-b | intellectual_appetite | | | |
| D12-c | intellectual_appetite | | | |

### 第二轮小结（打完再填）

- 自评时觉得"规格书没写清、只能凭感觉"的条目：__
- 与第一轮回忆不一致、需要翻回第一轮核对的条目：__

---

## 两轮一致率对照（两轮都打完后再填，先别看 gold）

| 候选ID | 第一轮 | 第二轮 | 两轮一致？ | 若不一致：当时我各按哪条规则判的 | 备注 |
| ------ | ------ | ------ | ---------- | -------------------------------- | ---- |
| D01-a | | | | | |
| D01-b | | | | | |
| D02-a | | | | | |
| D02-b | | | | | |
| D03-a | | | | | |
| D03-b | | | | | |
| D04-a | | | | | |
| D04-b | | | | | |
| D04-c | | | | | |
| D04-d | | | | | |
| D05-a | | | | | |
| D05-b | | | | | |
| D05-c | | | | | |
| D06-a | | | | | |
| D06-b | | | | | |
| D07-a | | | | | |
| D07-b | | | | | |
| D07-c | | | | | |
| D08-a | | | | | |
| D08-b | | | | | |
| D09-a | | | | | |
| D09-b | | | | | |
| D09-c | | | | | |
| D10-a | | | | | |
| D10-b | | | | | |
| D11-a | | | | | |
| D11-b | | | | | |
| D11-c | | | | | |
| D12-a | | | | | |
| D12-b | | | | | |
| D12-c | | | | | |

**两轮一致率 = 两轮评分相同的条数 ÷ 31。目标 ≥ 90%（即至多 3 条不一致）。**

---

## 争议项复核（两轮打完、对完 gold 之后再做）

逐条回答：按规格书现有文字，能否推导出唯一答案？不能 → 规格书有洞 → **改规则，不改 gold**。

| 候选ID | 我的最终评分 | gold | 一致？ | 按规格书能否推出唯一答案？ | 结论（改哪条规则 / 只是理解偏差） | 备注 |
| ------ | ------------ | ---- | ------ | -------------------------- | --------------------------------- | ---- |
| D03-b | | | | | | |
| D04-b | | | | | | |
| D04-d | | | | | | |
| D09-c | | | | | | |
| D11-c | | | | | | |

### 总结（全部完成后填）

- 两轮一致率：__ / 31 = __%
- 与 gold 的一致率：__ / 31 = __%
- 发现并修补的规格书漏洞（列条 + 改了哪条规则）：__
