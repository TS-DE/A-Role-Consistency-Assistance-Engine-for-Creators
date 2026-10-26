# 多方对比数据（gold vs 各标注者）

> 由 `tests/compare_rounds.py` 自动生成，勿手改。
> 手写分析：`docs/04-三方对比与规格书漏洞.md`、`docs/06-首轮人工评分校正.md`。


- 样本：31 条判定样本（12 条输入）
- 标注者：A01, A02, H
- 分布：gold {0: 9, 2: 12, 1: 10} / A01 {0: 9, 2: 13, 1: 9} / A02 {0: 10, 2: 13, 1: 8} / H {0: 9, 2: 12, 1: 10}
- OOC 率：gold 9/31 = 29.0% / A01 9/31 = 29.0% / A02 10/31 = 32.3% / H 9/31 = 29.0%


## 1. 两两一致率与加权 kappa

| 对比对 | 相同 / 总数 | 一致率 | 二次加权 kappa |
| --- | --- | --- | --- |
| gold-A01 | 29/31 | 93.5% | 0.882 |
| gold-A02 | 29/31 | 93.5% | 0.954 |
| gold-H | 27/31 | 87.1% | 0.903 |
| A01-A02 | 29/31 | 93.5% | 0.887 |
| A01-H | 25/31 | 80.6% | 0.787 |
| A02-H | 25/31 | 80.6% | 0.862 |

## 2. 全体一致率

**24/31 = 77.4%**（4 方全同）

## 3. 明细

| 候选 | trait | probe | gold | A01 | A02 | H | 全同? | 分歧类型 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D01-a | emotional_restraint | leak | 0 | 0 | 0 | 0 | ✅ | — |
| D01-b | emotional_restraint | false_alarm | 2 | 2 | 2 | 2 | ✅ | — |
| D02-a | evidence_first | leak | 0 | 0 | 0 | 0 | ✅ | — |
| D02-b | evidence_first | false_alarm | 2 | 2 | 2 | 2 | ✅ | — |
| D03-a | no_glory_seeking | leak | 0 | 0 | 0 | 0 | ✅ | — |
| D03-b | no_glory_seeking | false_alarm | 2 | 2 | 2 | 2 | ✅ | — |
| D04-a | emotional_restraint | leak | 0 | 0 | 0 | 0 | ✅ | — |
| D04-b | emotional_restraint | boundary | 1 | 1 | 1 | 2 | ❌ | 离群:H |
| D04-c | emotional_restraint | false_alarm | 2 | 2 | 2 | 2 | ✅ | — |
| D04-d | voice_register | boundary | 1 | 1 | 1 | 0 | ❌ | 离群:H |
| D05-a | evidence_first | leak | 0 | 0 | 0 | 1 | ❌ | 离群:H |
| D05-b | evidence_first | false_alarm | 2 | 2 | 2 | 2 | ✅ | — |
| D05-c | evidence_first | boundary | 1 | 1 | 1 | 1 | ✅ | — |
| D06-a | emotional_restraint | leak | 0 | 0 | 0 | 0 | ✅ | — |
| D06-b | emotional_restraint | false_alarm | 2 | 2 | 2 | 2 | ✅ | — |
| D07-a | era_consistency | leak | 0 | 0 | 0 | 0 | ✅ | — |
| D07-b | era_consistency | leak | 0 | 2 | 0 | 0 | ❌ | 离群:A01 |
| D07-c | era_consistency | false_alarm | 2 | 2 | 2 | 2 | ✅ | — |
| D08-a | era_consistency | leak | 0 | 0 | 0 | 0 | ✅ | — |
| D08-b | era_consistency | false_alarm | 2 | 2 | 2 | 2 | ✅ | — |
| D09-a | voice_register | boundary | 1 | 1 | 1 | 1 | ✅ | — |
| D09-b | voice_register | false_alarm | 2 | 2 | 2 | 2 | ✅ | — |
| D09-c | voice_register | boundary | 1 | 1 | 1 | 1 | ✅ | — |
| D10-a | watson_rapport | false_alarm | 2 | 2 | 2 | 2 | ✅ | — |
| D10-b | watson_rapport | boundary | 1 | 1 | 1 | 1 | ✅ | — |
| D11-a | moral_flexibility | false_alarm | 2 | 2 | 2 | 2 | ✅ | — |
| D11-b | moral_flexibility | boundary | 1 | 1 | 1 | 1 | ✅ | — |
| D11-c | moral_flexibility | boundary | 1 | 0 | 0 | 1 | ❌ | 离群: |
| D12-a | intellectual_appetite | false_alarm | 2 | 2 | 2 | 1 | ❌ | 离群:H |
| D12-b | intellectual_appetite | boundary | 1 | 1 | 1 | 1 | ✅ | — |
| D12-c | intellectual_appetite | boundary | 1 | 1 | 2 | 1 | ❌ | 离群:A02 |

## 4. 分歧清单

### D04-b（gold=1 / A01=1 / A02=1 / H=2）

- trait: `emotional_restraint`　probe: `boundary`
- 原文：`You will not last the night, Watson. Go to bed; I shall take the case.`

### D04-d（gold=1 / A01=1 / A02=1 / H=0）

- trait: `voice_register`　probe: `boundary`
- 原文：`You will not leave this house tonight. I forbid it. The case is mine.`

### D05-a（gold=0 / A01=0 / A02=0 / H=1）

- trait: `evidence_first`　probe: `leak`
- 原文：`You are right. The coal-man did it; his black hands prove it.`

### D07-b（gold=0 / A01=2 / A02=0 / H=0）

- trait: `era_consistency`　probe: `leak`
- 原文：`DNA is a thing of the future, and I know it not. But the sediment in that glass may yet speak. Bring me the glass.`

### D11-c（gold=1 / A01=0 / A02=0 / H=1）

- trait: `moral_flexibility`　probe: `boundary`
- 原文：`Let him go; murder is of no consequence to me.`

### D12-a（gold=2 / A01=2 / A02=2 / H=1）

- trait: `intellectual_appetite`　probe: `false_alarm`
- 原文：`A lost cat. How utterly tedious. Very well — tell the owner I shall look into it, though my mind rebels at the triviality.`

### D12-c（gold=1 / A01=1 / A02=2 / H=1）

- trait: `intellectual_appetite`　probe: `boundary`
- 原文：`A lost cat. I have no interest. Do not bring me such trifles again.`


## 5. 各标注者错误按探针类型

| 标注者 | leak 漏杀 | false_alarm 误杀 | boundary 错档 |
| --- | --- | --- | --- |
| A01 | 1 | 0 | 1 |
| A02 | 0 | 0 | 2 |
| H | 1 | 1 | 2 |

## 6. 混淆矩阵（行=标注者，列=gold）


**A01**

| 标注者 \ gold | 0 | 1 | 2 |
| --- | --- | --- | --- |
| 0 | 8 | 1 | 0 |
| 1 | 0 | 9 | 0 |
| 2 | 1 | 0 | 12 |

**A02**

| 标注者 \ gold | 0 | 1 | 2 |
| --- | --- | --- | --- |
| 0 | 9 | 1 | 0 |
| 1 | 0 | 8 | 0 |
| 2 | 0 | 1 | 12 |

**H**

| 标注者 \ gold | 0 | 1 | 2 |
| --- | --- | --- | --- |
| 0 | 8 | 1 | 0 |
| 1 | 1 | 8 | 1 |
| 2 | 0 | 1 | 11 |
