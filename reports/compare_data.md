# 多方对比数据（gold vs 各标注者）

> 由 `tests/scripts/compare_rounds.py` 自动生成，勿手改。
> 手写分析：`docs/04`（三方）、`docs/06`（首轮人工）、`docs/07`（A03 泄漏审计）。


- 样本：31 条判定样本（12 条输入）
- 覆盖率：A01 31/31，A02 31/31，A03 31/31，H 31/31，H2 8/31


## 1. 两两一致率

| 对比对 | 相同 / 可比 | 一致率 | 二次加权 κ |
| --- | --- | --- | --- |
| gold-A01 | 29/31 | 93.5% | 0.882 |
| gold-A02 | 29/31 | 93.5% | 0.954 |
| gold-A03 | 31/31 | 100.0% | 1.0 |
| gold-H | 27/31 | 87.1% | 0.903 |
| gold-H2 | 8/8 | 100.0% | 1.0 |
| A01-A02 | 29/31 | 93.5% | 0.887 |
| A01-A03 | 29/31 | 93.5% | 0.882 |
| A01-H | 25/31 | 80.6% | 0.787 |
| A01-H2 | 6/8 | 75.0% | 0.444 |
| A02-A03 | 29/31 | 93.5% | 0.954 |
| A02-H | 25/31 | 80.6% | 0.862 |
| A02-H2 | 6/8 | 75.0% | 0.8 |
| A03-H | 27/31 | 87.1% | 0.903 |
| A03-H2 | 8/8 | 100.0% | 1.0 |
| H-H2 | 4/8 | 50.0% | 0.5 |

**5 方（gold+A01+A02+A03+H）在全量 31 条上，全同：24/31 = 77.4%**

> 覆盖率不足的轮次（H2）不计入全同率，只看它自己的两两对比。

## 2. 明细

| 候选 | trait | probe | gold | A01 | A02 | A03 | H | H2 | 全同? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D01-a | emotional_restraint | leak | 0 | 0 | 0 | 0 | 0 | — | ✅ |
| D01-b | emotional_restraint | false_alarm | 2 | 2 | 2 | 2 | 2 | — | ✅ |
| D02-a | evidence_first | leak | 0 | 0 | 0 | 0 | 0 | — | ✅ |
| D02-b | evidence_first | false_alarm | 2 | 2 | 2 | 2 | 2 | — | ✅ |
| D03-a | no_glory_seeking | leak | 0 | 0 | 0 | 0 | 0 | — | ✅ |
| D03-b | no_glory_seeking | false_alarm | 2 | 2 | 2 | 2 | 2 | — | ✅ |
| D04-a | emotional_restraint | leak | 0 | 0 | 0 | 0 | 0 | — | ✅ |
| D04-b | watson_rapport | boundary | 1 | 1 | 1 | 1 | 2 | 1 | ❌ |
| D04-c | emotional_restraint | false_alarm | 2 | 2 | 2 | 2 | 2 | — | ✅ |
| D04-d | voice_register | boundary | 1 | 1 | 1 | 1 | 0 | 1 | ❌ |
| D05-a | evidence_first | leak | 0 | 0 | 0 | 0 | 1 | 0 | ❌ |
| D05-b | evidence_first | false_alarm | 2 | 2 | 2 | 2 | 2 | — | ✅ |
| D05-c | evidence_first | boundary | 1 | 1 | 1 | 1 | 1 | — | ✅ |
| D06-a | emotional_restraint | leak | 0 | 0 | 0 | 0 | 0 | — | ✅ |
| D06-b | emotional_restraint | false_alarm | 2 | 2 | 2 | 2 | 2 | — | ✅ |
| D07-a | era_consistency | leak | 0 | 0 | 0 | 0 | 0 | — | ✅ |
| D07-b | era_consistency | leak | 0 | 2 | 0 | 0 | 0 | 0 | ❌ |
| D07-c | era_consistency | false_alarm | 2 | 2 | 2 | 2 | 2 | — | ✅ |
| D08-a | era_consistency | leak | 0 | 0 | 0 | 0 | 0 | — | ✅ |
| D08-b | era_consistency | false_alarm | 2 | 2 | 2 | 2 | 2 | — | ✅ |
| D09-a | voice_register | boundary | 1 | 1 | 1 | 1 | 1 | — | ✅ |
| D09-b | voice_register | false_alarm | 2 | 2 | 2 | 2 | 2 | — | ✅ |
| D09-c | voice_register | boundary | 1 | 1 | 1 | 1 | 1 | — | ✅ |
| D10-a | watson_rapport | false_alarm | 2 | 2 | 2 | 2 | 2 | — | ✅ |
| D10-b | watson_rapport | boundary | 1 | 1 | 1 | 1 | 1 | — | ✅ |
| D11-a | moral_flexibility | false_alarm | 2 | 2 | 2 | 2 | 2 | 2 | ✅ |
| D11-b | moral_flexibility | boundary | 1 | 1 | 1 | 1 | 1 | — | ✅ |
| D11-c | moral_flexibility | boundary | 1 | 0 | 0 | 1 | 1 | 1 | ❌ |
| D12-a | intellectual_appetite | false_alarm | 2 | 2 | 2 | 2 | 1 | 2 | ❌ |
| D12-b | intellectual_appetite | boundary | 1 | 1 | 1 | 1 | 1 | — | ✅ |
| D12-c | intellectual_appetite | boundary | 1 | 1 | 2 | 1 | 1 | 1 | ❌ |

## 3. 分歧清单

- `D04-b`（gold=1 / A01=1 / A02=1 / A03=1 / H=2 / H2=1）　离群:H
- `D04-d`（gold=1 / A01=1 / A02=1 / A03=1 / H=0 / H2=1）　离群:H
- `D05-a`（gold=0 / A01=0 / A02=0 / A03=0 / H=1 / H2=0）　离群:H
- `D07-b`（gold=0 / A01=2 / A02=0 / A03=0 / H=0 / H2=0）　离群:A01
- `D11-c`（gold=1 / A01=0 / A02=0 / A03=1 / H=1 / H2=1）　离群:
- `D12-a`（gold=2 / A01=2 / A02=2 / A03=2 / H=1 / H2=2）　离群:H
- `D12-c`（gold=1 / A01=1 / A02=2 / A03=1 / H=1 / H2=1）　离群:A02

## 4. 各标注者对 gold 的错误方向

| 标注者 | leak 漏杀(gold=0 判高) | false_alarm 误杀(gold=2 判低) | boundary 错档 |
| --- | --- | --- | --- |
| A01 | 1 | 0 | 1 |
| A02 | 0 | 0 | 2 |
| A03 | 0 | 0 | 0 |
| H | 1 | 1 | 2 |
| H2 | 0 | 0 | 0 |
