# 使用方法（USAGE）

> 面向"我要用它管一个真实项目"的完整操作手册。5 分钟读完即可上手。

## 0. 它是怎么工作的（先理解这一句）

**调用一次 = 给项目装上飞行记录仪**：建好记录目录 → 在项目根 `AGENTS.md` 注入锚点 → 之后**每次会话自动续记**。
你不需要每天记得"要记录"——锚点会在每次开工时把记录协议推到 Agent 面前。

## 0.1 六个口令（记这个就够）

**词组即命令**。不需要背"使用 project-journal skill 跟踪这个项目"这种长句。

```
| 你说 | 它做什么 |
|---|---|
| **跟踪项目** | 建立跟踪（首次）／继续跟踪（已有） |
| **记一下** | 把刚才的增量落盘（决策 / 问题 / 解法 / 认知 / 数字） |
| **项目状态** | 一行体检：阶段 / 停滞 / 未闭环 / 数字 |
| **复盘** | 生成周或月复盘骨架 |
| **结项** | 终局判定：成功 / 失败 / 转向 / 暂停 |
| **出资产** | 生成脱敏可销售资产包 |
```

口语变体同样触发（"帮我跟踪这个项目" / "记一下今天的" / "这个项目怎么样了" / "做完了总结下" / "能卖了吗"）；
英文：`track this project` / `journal this`。

> 首次执行 **跟踪项目** 时，它会要求你写下**成功线与止损线**——这是最后判定"变现成功还是失败"的唯一标尺，别跳过。

---

## 1. 安装

### 方式 A：全局注册（推荐，所有 Agent 工具可用）

```bash
git clone https://github.com/lh123aa/project-journal.git ~/.agents/skills/project-journal
python ~/.agents/skills/project-journal/scripts/install-global.py
```

它会（幂等，可重复跑）：

| 工具 | 注册方式 |
|---|---|
| Claude Code | `~/.claude/skills/project-journal`（junction 链接） |
| opencode | `~/.config/opencode/skills/project-journal` |
| Cursor | `~/.cursor/skills/project-journal` |
| Codex CLI / Gemini CLI / Windsurf / 其它 | 在各自全局指令文件里注入托管块 |
| **DSH** | 原生发现 `~/.agents/skills/*/SKILL.md`，无需额外注册 |

先看它要做什么：`--check`；强制复制而不链接：`--copy`；自定义家目录：`--home <目录>`。

### 方式 B：只给某一个项目用

把仓库放进项目里（例如 `<项目>/tools/project-journal`），在项目 `AGENTS.md` 里写一行"跟踪项目时读 tools/project-journal/SKILL.md"即可。

### 真源放在哪里（以及移动真源时怎么做）

技能真源（这个 git 仓库）**可以放在任意位置**，只要各工具的发现路径指向它即可。当前一种典型布局：

`@
真源      E:\程序\github\我的项目\project-journal        ← git 仓库，随时 git pull
发现路径  %USERPROFILE%\.agents\skills\project-journal  ← junction 指回真源（ASCII 短路径，DSH 等按此发现）
工具链接  %USERPROFILE%\.claude\skills\project-journal  ← junction 指回真源
`@

为什么保留 `~/.agents/skills/project-journal` 这个 junction：DSH 等宿主按该路径发现技能，
而且已经写进各项目 `AGENTS.md` 锚点里的绝对命令也依赖它。保留它，**就不需要改动任何已有项目**。

移动真源后按三步走：

`@bash
# 1) 在原位置建 junction 指回新位置
cmd /c mklink /J "%USERPROFILE%\.agents\skills\project-journal" "E:\程序\github\我的项目\project-journal"
# 2) 到新位置重跑注册（重建各工具链接与托管块）
python "E:\程序\github\我的项目\project-journal\scripts\install-global.py"
# 3) 已有项目无需改动；如契约版本落后再跑一次
python "E:\程序\github\我的项目\project-journal\scripts\journal.py" upgrade --root "<项目根>\project-journal"
`@

> 移动只影响"工具从哪里找到技能"，**不影响任何项目的记录数据**。`journal.py upgrade` 只动 tracker/契约/锚点，不改写日记与档案。

### 依赖

**Python 3.8+，零第三方依赖**。任何能执行 shell 的 Agent 工具都能跑。

## 2. 五分钟上手

在**项目根目录**下执行一次：

```bash
S=~/.agents/skills/project-journal/scripts/journal.py     # Windows: %USERPROFILE%\.agents\skills\project-journal\scripts\journal.py

python $S init --project "我的项目" --stage S0 --currency USD \
  --hypothesis "谁 + 什么痛点 + 愿意付多少 + 凭什么这么判断" \
  --success    "连续 3 个月净收入 >= 500 USD 且每日投入 < 1 小时" \
  --stop-loss  "累计投入 200 小时且收入 < 100 USD"
```

产出：项目根出现 `project-journal/` 子文件夹（记录目录）+ `AGENTS.md` 注入锚点。

> **成功线与止损线必须在这里写死。** 它们是项目结束时判定"变现成功还是失败"的唯一客观标尺；没有它们，复盘只能凭感觉。

然后打开 `project-journal/CHARTER.md` 补全目标与假设。

## 3. 日常循环（每次会话）

```bash
S=~/.agents/skills/project-journal/scripts/journal.py
R="project-journal"

# ① 开工：先读（必做，别凭记忆）
python $S resume --root $R

# ② 干活中：随时落盘
python $S add --root $R --type decision --title "放弃 WhatsApp 渠道" --body-file d.md
python $S add --root $R --type problem  --title "OAuth 回调丢 session" --body-file p.md
python $S update --root $R --id PB-0001 --status solved --append-file fix.md   # 问题解决后回填
python $S add --root $R --type insight  --title "瓶颈是定价页不是流量" --body-file i.md
python $S add --root $R --type lesson   --title "先收 10 个邮箱再写代码" --body-file l.md
python $S metric --root $R --name MRR --value 120 --unit USD --source Stripe
python $S ledger --root $R --kind income --amount 99 --channel Gumroad
python $S stage  --root $R --set S5 --why "拿到首单"

# ③ 收工：更新待办 → 重建索引 → 体检
#    手工编辑 project-journal/NEXT-ACTIONS.md
python $S index --root $R
python $S lint  --root $R
```

## 4. 记什么（MUST-RECORD 触发器）

命中即记，**当天记**：

1. 任何取舍（选 A 不选 B），含**被否决的选项与理由**
2. 用户的偏好与红线（"不要这样/太贵/太慢"）
3. 认知更新（原以为 X，其实是 Y，证据是 Z）
4. 耗时 > 15 分钟的卡点，以及最终怎么绕过去的
5. 任何数字：价格、成本、转化率、耗时、用户数、收入、退款
6. 对外承诺、deadline、合同条款
7. 可能让项目死掉的风险与单点依赖
8. 可复用的步骤（打完就忘 = 白干）
9. **失败与放弃**：pivot、砍功能、关渠道、不做了 —— 最值钱，最容易漏

**不要记**："打开了文件""运行了测试"这类无信息量动作；不要粘贴大段代码/日志（存 `assets/`，正文只写结论 + 指路）。

## 5. 命令速查

| 场景 | 命令 |
|---|---|
| 立项 | `init --project "名称" --success ... --stop-loss ...` |
| 开工 | `resume --root <R>` |
| 记录 | `add --root <R> --type <类型> --title "..." [--body-file f] [--link ADR-0001]` |
| 闭环问题 | `update --root <R> --id PB-0003 --status solved --append-file fix.md` |
| 数字 | `metric` / `ledger` |
| 阶段 | `stage --root <R> --set S3 --why "..."` |
| 收尾 | `index` + `lint --root <R>` |
| 周月复盘 | `review --root <R> --period weekly` → 补写分析段 |
| 项目终止 | `closeout --root <R> --outcome success\|failure\|pivot\|paused` |
| 资产化 | `publish --root <R>`（脱敏 → 8 个可销售文件） |
| 多项目总览 | `vault-index --root <vault>` |
| 其它项目接入 | `upgrade --root <R>` |
| 报告 skill 问题 | `evolve` / `evolve-list` / `evolve-apply` / `doctor` |

类型：`decision` `problem` `solution` `experiment` `insight` `lesson` `risk` `milestone` `task` `metric` `revenue` `cost` `question`

> 中文正文一律用 `--body-file`（先写文件再传路径），不要把长中文塞进命令行。

## 6. 复盘、终止、变现判定

- **每周**：`review --period weekly` → 骨架会自动填事实，你只写"分析"。硬性要求：本期最有价值的 3 条 / 卡点与解法 / 认知更新 / **数字涨跌的原因** / 下期只做一件事。
- **每月**：`review --period monthly` → 检查变现假设是否仍成立、成本是否在累积、有没有自嗨。
- **终止**：触达止损线就立刻 `closeout`，不要拖。五种终局：`success` / `failure` / `pivot` / `paused` / `zombie`。
- **资产化**：`publish` 生成 `CASE-STUDY / PLAYBOOK / LESSONS / METRICS.csv / LEDGER-SUMMARY / PRODUCT-SHEET / INDEX / _redaction-report`。脱敏规则写在 `project-journal/sanitize.txt`（`原文 => 替换`，正则用 `re:模式 => 替换`）。

**卖点检验**（四条全过才值得上架）：有真实数字 / 有可复用决策打法 / 有坦白的失败 / 完全脱敏。

## 7. 多项目与集中管理

- 一个项目一个记录目录，**都在各自项目根下**，随项目 git 走
- 想集中资产化：把多个 `<项目根>/project-journal` 汇总到一个 vault 目录，跑 `vault-index --root <vault>` 得到跨项目总览（L2/L3 资产：方法论、数据库）
- 一个项目多人/多 Agent 协作：各自跑 `add`，最后一个人跑 `index` + `lint`

## 8. 它会自己变好（自我迭代）

运行中遇到这些情况，**立刻记录**（不要只在对话里抱怨）：

- 命令报错、退出码非 0、崩溃（脚本会自动记录，退出码 3）
- 文档与实现不符、模板字段填不进去、流程走不通、你不得不绕过它
- `lint` 打印的 `[EVOLVE]` 提示

```bash
python $S evolve --category bug --severity high --title "一句话现象" \
  --body-file symptom.md --evidence "文件:行 / 输出片段" --repro "复现命令" --project <slug>
python $S evolve-list
python $S evolve-apply --id EV-0009 --bump minor --summary "改了什么、为什么"   # 先跑自测，再升版本
python $S doctor
```

闭环：**发现 → 记录 → 分级 → 修 → 回归自测（26 项门禁）→ 升版本 + CHANGELOG → upgrade 迁移已有项目**。
已有项目升级：`python $S upgrade --root <R>`（只动 tracker/契约/锚点，**不改写任何日记与档案**）。

## 9. FAQ

**Q：没记录会怎样？**
A：对三个月后的你和下一个 AI 而言，那次会话没有发生过。`lint` 会在停滞 7 天后警告。

**Q：会不会记录成本太高，最后放弃？**
A：正常一天 3-8 行；只有发生取舍/卡点/数字变化时才写。如果觉得成本高到想放弃，这本身就是该 `evolve` 上报的 bug。

**Q：和 Notion / Jira 冲突吗？**
A：不冲突。它们管任务，本 skill 管**判断与教训**；而且记录随项目走、是纯 Markdown、可直接当 AI 语料与商品。

**Q：能记录密钥吗？**
A：不能。`lint` 会扫描并在 `publish` 强制脱敏；台账里也只写引用路径。

**Q：记录目录能改位置吗？**
A：约定是 `<项目根>/project-journal/`（锚点靠它自动定位）。要用别的名字：`--root "<项目根>/<文件夹>" --project-root "<项目根>"`。

**Q：怎么升级？**
A：在 skill 真源目录 `git pull`。用 junction 安装的工具会自动跟随；用 `--copy` 安装的需要重跑 `install-global.py`。
