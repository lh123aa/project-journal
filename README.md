# project-journal

> **给任何项目装一个"飞行记录仪"**：调用一次就持续跟踪记录项目全过程 —— 有价值的讨论、每天的推进、做过的取舍、踩过的坑与解法、真实数字（时间/成本/转化/收入）—— 直到变现成功或失败，并沉淀成可复用的经验与**可销售的数字化资产**；同时它还能**记录并修订自己**。

[English](#english) ｜ 中文

```
一次调用  ->  记录目录 + 会话锚点 + 记录契约  ->  此后每次会话自动续记  ->  项目结束产出案例资产
```

---

## 为什么需要它

项目过程中真正值钱的东西 —— **当时为什么这么选、卡在哪里、怎么绕过去的、真实数字是多少** —— 如果不落盘，三天后只剩模糊印象，三个月后连自己都答不上来。而这个项目结束后，这些正是最值钱的资产。

本 skill 解决三件事：

1. **不靠自觉**：在项目根 `AGENTS.md` 注入会话锚点，未来任何一次会话（换工具、换 Agent、三天后）开工就自动读取契约并续记。
2. **不写流水账**：MUST-RECORD 触发器 + 质量三问（换人可懂吗 / 有证据吗 / 可复用吗），只记有判断、有结论、有数字的东西。
3. **能收口**：立项时先写死**成功线**与**止损线**，项目结束时用它客观判定"变现成功还是失败"，而不是凭感觉；随后脱敏成可销售的案例资产。

## 核心机制

### 持续跟踪的四个装置（"调用一次"就够的原理）

| 装置 | 作用 |
|---|---|
| ① 会话锚点 | 向项目根 `AGENTS.md` 注入托管块（幂等），未来任何会话开工自动续记 |
| ② 磁盘状态 | `STATE.md` + `tracker.json` 让新会话 30 秒恢复上下文，不依赖聊天历史 |
| ③ 收尾捕获 | "未记录 = 对后人而言没发生过"，每次会话结束前落盘 |
| ④ 可选心跳 | 宿主定时任务每日提醒补记 |

### 三层数据 + 一产出

```
原始层  journal/YYYY-MM-DD.md      append-only，永不改写
档案层  records/{decisions,problems,solutions,experiments,insights,lessons,risks,milestones}/
数据层  metrics.csv · ledger.csv · experiments.csv
状态层  STATE.md · tracker.json（自动生成，永远最新）
产出    publish/<日期>/            脱敏后可直接销售或分享的资产包
```

### 自我迭代（这个 skill 自己坏了怎么办）

```
DETECT 发现 -> LOG 记录(evolve) -> TRIAGE 分级 -> FIX 修改
    -> VERIFY 回归自测(门禁) -> RELEASE 升版本+CHANGELOG -> PROPAGATE upgrade 迁移已有项目
```

- 命令崩溃自动记录（退出码 3）；`lint` 自动检测结构性问题（`--auto-evolve` 直接落台账）
- `evolve-apply` 会**先跑回归自测**，不通过就中止，不改版本号、不标记 applied
- 台账 `evolution/LEDGER.md` 跨项目共享、自动去重；`upgrade` 迁移已有项目时**不动任何日记与档案**
- 治理红线：先记录再修 / 每次必须过自测并补用例 / 必须升版本 + 写 CHANGELOG / 拿不准就标 `proposed` 问人

## 安装

把仓库放进 skills 目录即可（DSH / Claude Code 等 agentskills 兼容宿主）：

```bash
git clone https://github.com/lh123aa/project-journal.git ~/.agents/skills/project-journal
# Windows: %USERPROFILE%\.agents\skills\project-journal
```

依赖：**Python 3.8+，仅标准库**，无需 pip 安装任何东西。

## 快速开始

在项目根目录下：

```bash
S=~/.agents/skills/project-journal/scripts/journal.py

# 1) 立项（约定：记录目录 = 项目根的子文件夹 project-journal/）
python $S init --project "我的项目" --stage S0 --currency USD \
  --hypothesis "谁 + 什么痛点 + 愿意付多少 + 凭什么判断" \
  --success   "连续 3 个月净收入 >= 500 USD 且每日投入 < 1 小时" \
  --stop-loss "累计 200 小时且收入 < 100 USD"

# 2) 每次开工先读
python $S resume --root project-journal

# 3) 干活中随时落盘（正文用 --body-file，避免命令行转义）
python $S add --root project-journal --type decision --title "放弃 WhatsApp 渠道" --body-file d.md
python $S metric --root project-journal --name MRR --value 120 --unit USD --source Stripe
python $S ledger --root project-journal --kind income --amount 99 --channel Gumroad
python $S stage  --root project-journal --set S5 --why "拿到首单"

# 4) 收尾
python $S index --root project-journal && python $S lint --root project-journal

# 5) 定期复盘 / 项目终止 / 资产化
python $S review   --root project-journal --period weekly
python $S closeout --root project-journal --outcome success
python $S publish  --root project-journal        # 脱敏 -> 8 个可销售资产文件
```

## 命令一览

| 命令 | 用途 |
|---|---|
| `init` | 建立记录目录（幂等）+ 注入会话锚点 |
| `anchor` | 重新注入/刷新锚点 |
| `status` / `resume` | 一行体检 / 生成"补液包"（新会话开工先跑） |
| `add` / `update` | 追加记录 / 更新档案状态（如问题已解决） |
| `metric` / `ledger` | 指标 / 收入成本 |
| `stage` | 推进阶段 S0→S6 |
| `index` / `lint` | 重建索引 / 体检（结构、ID、密钥泄露、停滞、自我迭代信号） |
| `review` / `closeout` | 周月复盘骨架 / 终局档案与成败判定 |
| `publish` / `vault-index` | 脱敏资产包 / 跨项目总览 |
| `upgrade` / `doctor` | 迁移已有项目到当前版本 / skill 安装自检 |
| `evolve` / `evolve-list` / `evolve-apply` | 记录 skill 自身问题 / 查看台账 / 走完修复闭环 |

记录类型：`task` `decision` `problem` `solution` `insight` `experiment` `metric` `risk` `lesson` `revenue` `cost` `milestone` `question`

## 目录结构

```
SKILL.md                      入口：运行逻辑、触发器、铁律、自我迭代
manifest.json                 版本与元信息（版本号唯一来源）
CHANGELOG.md                  语义化版本变更日志
references/                   00 契约 / 01 分类法 / 02 写作指南 / 03 节奏 /
                              04 变现追踪 / 05 终止复盘 / 06 资产化 / 07 排障 / 08 自我迭代
scripts/journal.py            引擎（stdlib only，约 90KB）
scripts/selftest.py           回归自测（26 项，发布门禁）
templates/                    CHARTER / NEXT-ACTIONS / 各类记录蓝图 / 日记条目
evolution/                    自我迭代台账（ledger.json + LEDGER.md）
```

## 设计原则

- **脚本管结构，Agent 管判断**：脚本只做确定性机械工作（建目录、编号、索引、配对、脱敏、体检），内容由人/Agent 写
- **append-only**：日记与档案不改写；更正走新增条目并标注 `[更正 <ID>]`，历史是用来学习的
- **区分事实与判断**：主观判断必须显式标注，数字必须带单位/时间/来源/置信度
- **不编造**：没确认就写"待确认"，宁可留空
- **防泄露**：`lint` 扫描密钥与隐私，`publish` 强制脱敏并输出审计报告
- **成败以预先写死的线为准**：只有 CHARTER 里的成功线/止损线能判定项目成败

## 自测

```bash
python scripts/selftest.py      # 26/26
python scripts/journal.py doctor
```

> `scripts/selftest.py` 里包含用于验证脱敏的**假密钥与假邮箱**（如 `sk-abcdefghijklmnopqrstuvwx`），是测试夹具，不是真实凭据。

## 版本

当前 `v1.1.3`。修复历史见 `evolution/LEDGER.md` 与 `CHANGELOG.md` —— 项目从 v1.0.0 起累计记录并修复 8 个真实缺陷（含"案例研究缺少认知车道"、"upgrade 无法刷新旧项目"、"lint 正则误报"等），每条都有复现与回归用例。

## License

MIT
