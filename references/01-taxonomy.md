# 分类法与字段规范

## 1. 记录类型总表

| type | 代码 | ID 前缀 | 落盘位置 | 何时用 | status 取值 |
|---|---|---|---|---|---|
| task | T | - | 当日日记 | 有意义的执行动作（不是流水账） | - |
| decision | D | ADR-#### | records/decisions/ | 做了取舍 | proposed / accepted / rejected / superseded |
| problem | P | PB-#### | records/problems/ | 卡住 > 15 分钟 | open / solved / wontfix |
| solution | S | SL-#### | records/solutions/ | 解决了问题且可复用 | done |
| insight | I | IN-#### | records/insights/ | 认知被更新 | - |
| experiment | X | EX-#### | records/experiments/ | 用一次尝试换一个结论 | open / done / aborted |
| metric | M | - | metrics.csv + 日记 | 出现真实数字 | - |
| risk | R | RK-#### | records/risks/ | 可能让项目死掉 | open / mitigated / accepted / closed |
| lesson | L | LS-#### | records/lessons/ | 沉淀成一句话的教训 | - |
| revenue | $ | - | ledger.csv + 日记 | 收到钱 | - |
| cost | C | - | ledger.csv + 日记 | 花钱 | - |
| milestone | MS | MS-#### | records/milestones/ | 阶段性的"第一次" | done |
| question | Q | - | 当日日记 | 悬而未决、需要外部回答 | open / answered |

**选择困难时**：问"这条记录未来会被谁、以什么理由重新读？"——答案是"帮我做同类决定"就记 decision，"避免再踩"就记 problem/lesson。

## 2. 日记条目格式

```markdown
### HH:MM [D] 标题  <ID>
正文（Markdown，建议用下面这个骨架）
```

正文骨架（decision 为例）：
```markdown
- 背景/触发：
- 选项：A ... / B ...
- 决定：
- 理由：
- 代价与风险：
- 证据：
- 下一步：
```

## 3. 档案 front matter

```yaml
---
id: ADR-0003
type: decision
project: my-project
title: 放弃 WhatsApp 渠道
date: 2026-10-09
status: accepted
tags: [渠道, 获客]
links: [PB-0007]
confidence: medium      # high | medium | low
---
```

- `links`：关联的其他 ID（问题↔解法、决策↔实验）。publish 时用它把问题和解法配对。
- `confidence`：证据强度。没有实证的数字/结论一律 `low`。
- `tags`：逗号分隔，用于跨项目聚合（同一 tag 在多个项目出现 = 可提炼的方法论）。

## 4. ID 与命名

- ID 全局唯一、单调递增，**永不复用**（即使某条被废弃）
- 文件名：`<ID>-<英文或拼音 slug>.md`；中文标题会退化成 `record`，可接受
- 日记文件名固定 `YYYY-MM-DD.md`（本地时区日期）

## 5. 指标与收支字段

metrics.csv：
```
date,metric,value,unit,source,confidence,note
2026-10-09,MRR,120,USD,Stripe后台,high,首月
```
- `metric` 名称保持稳定（`MRR` 就一直叫 `MRR`），否则趋势无法计算
- `source` 必填：没有来源的数字等于没有数字
- `confidence`：实测 high / 估算 low

ledger.csv：
```
date,kind,amount,currency,channel,note
2026-10-09,income,99,USD,Gumroad,第一单
2026-10-09,cost,12,USD,域名,年费
```
- `kind` 只允许 `income` / `cost`（收入与成本必须能分开算净额）
- 币种不同的行分开统计，不要手工折算

## 6. 命名约定（避免检索混乱）

- 一个主题一份档案；同一主题有新变化用 `update --append-file` 追加"更新"段，不要新建 ADR-0004
- 只有当**决定被推翻**时才新建档案，并在 `links` 里指向旧 ID，旧档案 status 改 `superseded`
- 标签优先复用已有标签（先看 `INDEX.md`），避免 `获客` / `引流` / `拉新` 三个同义标签并存
