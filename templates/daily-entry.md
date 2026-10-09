# 日记条目写法

日记文件：`journal/YYYY-MM-DD.md`，append-only。
条目头由脚本生成（`### HH:MM [类型] 标题`），正文你写。

## 最简可用（任务）
```markdown
### 14:20 [T] 跑通支付回调
- 做了什么：接 Stripe webhook，本地用 ngrok 转发
- 结果：沙箱支付成功回调，订单状态正确流转
- 阻塞：无
```

## 决策（同时生成 ADR 档案时，正文可只写摘要 + 指路）
```markdown
### 15:05 [D] 放弃 WhatsApp 渠道  `ADR-0003`
- 摘要：主体资格不符，等认证要 2-4 周，改用 Telegram 先验证
- 详见：records/decisions/ADR-0003-abandon-whatsapp.md
```

## 认知更新
```markdown
### 18:40 [I] 瓶颈不是流量而是定价页
- 原以为：流量不够
- 现在认为：定价页说服力不足（同一批流量，换页后转化 0% -> 4.3%）
- 依据：10/3-10/8 vs 10/9-10/14，metrics.csv
- 动作：暂停加投，先改定价页
```

## 指标 / 收支（脚本会自动写）
```bash
journal.py metric --name 落地页转化率 --value 4.3 --unit "%" --source GA4 --confidence high
journal.py ledger --kind income --amount 99 --currency USD --channel Gumroad --note "第一单"
```

## 更正已有条目
不要改写历史，新增一条：
```markdown
### 09:10 [U] 更正 ADR-0003
- 原记录：以为 WhatsApp 认证要 4 周
- 更正为：实际官方 SLA 是 2 周（来源：后台公告 10/10 更新）
```
