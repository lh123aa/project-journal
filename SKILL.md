---
name: project-journal
description: 项目全过程跟踪与经验资产化引擎。对任何项目调用一次即装上"飞行记录仪"：建立独立记录文件夹、注入会话锚点、建立记录协议；此后每次会话自动续记——有价值的讨论与判断、每日执行、遇到的困难与解法、关键决策与取舍、真实数字（时间/成本/转化/收入）、风险与依赖——直到变现成功或失败，最后沉淀为给人看、给 AI 读、可对外销售的 Markdown 数字资产（案例研究/打法手册/经验教训）。触发词：项目跟踪、过程记录、项目日志、每日记录、决策记录、复盘、经验教训、变现追踪、项目复盘、记录这个项目、跟踪这个项目、build in public、project journal、decision log、lessons learned、case study、retrospective。内置自我迭代机制：运行中发现的 bug／逻辑问题会记录进 skill 自身台账（evolve），修复后自动跑回归自测、升版本、写 CHANGELOG 并迁移已有项目。触发词补充：skill 自我迭代、改进 skill、skill 有 bug、记录这个问题下次别再犯。最短口令：跟踪项目、记一下、项目状态、复盘、结项、出资产。
---

# project-journal — 项目全过程跟踪与经验资产化

## 0. 一句话

给项目装一个**飞行记录仪**：调用一次就把"独立文件夹 + 会话锚点 + 记录协议"建好，此后每次会话自动续记，项目结束时自动产出**经验教训**与**可销售的数字化案例资产**。

> 记录的目标不是"记流水账"，而是让**三个月后的自己、一个新来的 AI、一个付费读者**都能：
> 看懂当时为什么这么选 → 复现关键动作 → 避开踩过的坑。

---

## 0.1 口令表（用户只需记这几个词）

**词组即命令**。用户说出口令时直接按对应动作执行，不需要他复述完整句子。

| 口令 | 语义 | 底层动作 |
|---|---|---|
| **跟踪项目**（或 `跟踪 <项目名>`） | 建立跟踪；已存在则继续 | 首次 `init`，之后 `resume` |
| **记一下**（或 `记录一下`） | 把刚才的增量落盘 | `add` / `metric` / `ledger` |
| **项目状态** | 一行体检：阶段 / 停滞 / 未闭环 / 数字 | `status` |
| **复盘** | 周或月复盘骨架 | `review --period weekly|monthly` |
| **结项** | 终局与成败判定 | `closeout --outcome ...` |
| **出资产** | 生成脱敏可销售资产包 | `publish` |

补充约定：

- 口令只是**入口**；用户不说口令、只是自然提到"把这个项目记一下""我们复盘下"，同样触发。
- 更口语的说法都按上表映射："帮我跟踪这个项目""记一下今天的""这个项目怎么样了""做完了总结下""能卖了吗"。
- 首次执行 **跟踪项目** 时必须问清**成功线与止损线**（见 §4.1 第 1 步），不能跳过。
- 被叫口令但当前没有跟踪中的项目时，先问"跟踪哪个项目"，不要猜。

---

## 1. 何时使用 / 不使用

**使用**
- 用户要开始一个可能持续数天～数月的项目/产品/变现尝试（"我要做 X""帮我推这个项目"）
- 用户要求跟踪、记录、复盘某个项目的**过程**
- 项目到了关键节点：定方向、卡住、上线、拿到第一笔钱、决定放弃
- 用户想要 build in public 素材、案例研究、经验资产

**不使用**
- 一次性问答、单文件小改动、没有过程价值的任务
- 用户明确说"不用记录"

**边界**：本 skill 只管"记录与沉淀"，不替代项目管理工具。任务排期仍写在 `NEXT-ACTIONS.md`，足够。

---

## 2. 持续性从哪来（"调用一次"就够的原理）

Skill 不会自己运行。**持续跟踪 = 四个装置的组合**，`init` 会把前三个一次建好：

| 装置 | 作用 | 维护方式 |
|---|---|---|
| ① **会话锚点** | 在项目根 `AGENTS.md` 注入托管块，让**未来任何一次会话**（换工具、换 Agent、三天后）开工就自动发现跟踪协议并续记 | `journal.py init` 自动注入，幂等可重入 |
| ② **磁盘状态** | `STATE.md` + `tracker.json` 让新会话 30 秒恢复上下文，**不依赖聊天历史** | 脚本自动生成，永远最新 |
| ③ **收尾捕获规则** | 每次工作结束前必须把本次增量写进当日日记："未记录 = 对后人而言没发生过" | 写进 `PROTOCOL.md` 与 `AGENTS.md` 锚点 |
| ④ **可选心跳** | 宿主支持定时任务时（DSH `schedule_create`／cron／CI），每日提醒补记 | 可选，非必需 |

**推论**：Bootstrap 之后，即使用户再也不提"记录"二字，锚点也会在下次会话把记录协议推到 Agent 面前。

---

## 3. 数据结构：三层 + 一产出

```
<项目根>/project-journal/          ← 就放在项目根目录的子文件夹里，随 git 走
├── PROTOCOL.md          记录契约（init 时从 skill 复制，新会话先读这个）
├── CHARTER.md           立项宪章：目标 / 变现假设 / 成功线 / 止损线（预先写死，防事后合理化）
├── STATE.md             【自动生成】一页驾驶舱：阶段、数字、未决问题、最近动作
├── INDEX.md             【自动生成】全部条目与档案的目录
├── NEXT-ACTIONS.md      未完成事项（人/Agent 手写，带 checkbox）
├── tracker.json         【自动生成】机器可读状态
├── journal/             原始层：YYYY-MM-DD.md，按时间 append-only，永不改写
├── records/             档案层：一主题一文件，可检索可引用
│   ├── decisions/       ADR-0001-*.md     决策与取舍（含被否决的选项）
│   ├── problems/        PB-0001-*.md      问题（含症状/根因/代价）
│   ├── solutions/       SL-0001-*.md      解法/打法（可复用步骤）
│   ├── experiments/     EX-0001-*.md      实验（假设/做法/结果/结论）
│   ├── insights/        IN-0001-*.md      有价值的讨论与认知更新
│   ├── lessons/         LS-0001-*.md      教训（一句话可复述）
│   ├── risks/           RK-0001-*.md      风险与依赖
│   └── milestones/      MS-0001-*.md      里程碑
├── metrics/             数据层
│   ├── metrics.csv      date,metric,value,unit,source,confidence,note
│   ├── ledger.csv       date,kind,amount,currency,channel,note
│   └── experiments.csv  实验台账
├── reviews/             weekly-2026-W41.md / monthly-2026-10.md / closeout-YYYY-MM-DD.md
├── assets/              截图、导出、证据（原样存放）
└── publish/<日期>/      【产出】脱敏后的可销售资产
```

**为什么分三层**：日记是**事实**（不可篡改），档案是**知识**（可被检索和引用），CSV 是**数字**（可算可画图）。三者互不污染，也就能各自被复用。

---

## 4. 运行逻辑

### 4.1 首次调用 = BOOTSTRAP（7 步）

1. **定位或询问**：项目名、slug、一句话目标、变现假设、**成功线**、**止损线**、基准货币、起始阶段。
   - 能从当前对话/仓库推断的就推断；推断不出的用 `ask_user_question` 问，**绝不编造**。
   - 成功线/止损线是"变现是否成功"的判定标尺，必须**在开始时就写死**（例："连续 3 个月净收入 ≥ $500 且非我时间线性投入"）。
2. **建骨架**：
   ```bash
   python "<SKILL>/scripts/journal.py" init --root "<项目根>/project-journal" --project "<名称>" --slug <slug> --stage S0 --currency USD --hypothesis "<变现假设>" --success "<成功线>" --stop-loss "<止损线>"
   ```
   **约定：记录目录 = 项目根目录下的 `project-journal/` 子文件夹**，随项目一起提交 git；这也让会话锚点能自动落到正确的位置。
   - 省事写法：在项目根目录下直接跑 `journal.py init --project "<名称>"`（默认就是 `./project-journal`）
   - 想用别的文件夹名：`--root "<项目根>/<文件夹>" --project-root "<项目根>"`
   - 集中式知识库：`--root "<vault>/<slug>" --project-root "<项目根>"`
3. **写 CHARTER.md**：把第 1 步的答案写成正式宪章（模板已生成，补全 `待填` 处）。
4. **注入锚点到 `AGENTS.md`**：`init` 已自动完成；确认锚点里的相对路径正确。
5. **把本次对话已有的信息落盘**：现场讨论出的方向、约束、备选方案，用 `add` 写成第一批条目（**不要留到"以后补"**）。
6. **`lint`** 一遍，确保结构完好。
7. **向用户汇报**（见 §12 模板）。

### 4.2 之后每次调用 = RESUME → CAPTURE → VERIFY（3 步）

**STEP 1 · RESUME（先读后写，绝不凭记忆写）**
```bash
python "<SKILL>/scripts/journal.py" resume --root "<root>"
```
输出"补液包"：STATE + 最近 3 天日记 + 未闭环问题/风险 + 未完成事项 + 最近指标。读完后向用户复述一句现状（阶段 / 卡在哪 / 下一步）。

**STEP 2 · CAPTURE（本次会话的增量）**
按 §5 触发器逐条判断，用 `add` / `metric` / `ledger` / `stage` 落盘。
> 判断标准：**如果一个条目删掉后，读者无法理解后续任何一步为什么发生，那它就必须存在。**

**STEP 3 · VERIFY（收尾，不可跳过）**
1. 更新 `NEXT-ACTIONS.md`（勾掉完成项，补上新开口）
2. `python "<SKILL>/scripts/journal.py" index` 与 `STATE.md` 自动刷新（`add` 已触发；手工编辑过文件后必须再跑一次）
3. `lint`；有 WARN 就修
4. 向用户汇报本次新增了哪几条（给 ID）
5. **若本次发现 skill 自身的问题**（报错、文档不符、流程走不通、`lint` 的 `[EVOLVE]`）→ 立即 `evolve` 记录，见 §8

### 4.3 命令路由表

| 用户意图 / 场景 | 动作 |
|---|---|
| "开始这个项目"/首次 | BOOTSTRAP |
| "继续"、日常开工 | RESUME → CAPTURE → VERIFY |
| "我们定了 X"、"用 A 不用 B" | `add --type decision`（写清被否决选项与代价） |
| "卡住了/报错了/踩坑了" | `add --type problem`，解决后再 `add --type solution` 并回填 problem 的 `status: solved` |
| 讨论出重要认知 | `add --type insight`，必须写"我原来的想法 → 现在的想法 → 证据" |
| 做了个尝试 | `add --type experiment` + `experiments.csv` |
| 出现数字（收入/成本/转化/耗时） | `metric` / `ledger` |
| "上线了/拿到第一笔钱/决定放弃" | `add --type milestone`；阶段变了用 `stage` |
| 一周/一月结束 | `review --period weekly\|monthly`，再补写分析段 |
| 项目终止（成功或失败） | `closeout --outcome success\|failure\|pivot\|paused` → 补写 → `publish` |
| 要拿去卖/分享/给别的 AI 当参考 | `publish` |
| 多项目汇总 | `vault-index --root <vault>` |

---

## 5. MUST-RECORD 触发器（命中即记，当天记，不隔夜）

1. **取舍**：任何"选 A 不选 B"的决定，含**被否决的选项和被否决的理由**
2. **纠偏**：用户说"不要这样/太贵/太慢/不对"——偏好和红线
3. **认知更新**：推翻先前假设的那一刻（"原来 X 才是瓶颈"）
4. **卡点与解法**：任何耗时 > 15 分钟的困难，以及最终怎么绕过去的
5. **数字**：价格、成本、转化率、耗时、用户数、收入、退款
6. **外部承诺**：对客户/合作方的承诺、deadline、合同条款
7. **风险与依赖**：可能让项目死掉的事、单点依赖
8. **可复用动作**：一套以后还会再用的步骤（→ solution）
9. **失败与放弃**：pivot、砍功能、关渠道、决定不做了——**这些最值钱，最容易漏记**

**反向规则（防噪音）**：不要记"我打开了文件""我运行了测试"这类无信息量动作；不要粘贴大段 diff、日志、代码全文——给**结论 + 证据位置**（`assets/` 或路径）即可。

---

## 6. 记录质量法则

一条记录要过"三问测试"：

1. **换人可懂吗**？（README 测试：外人只看这条，懂不懂发生了什么、为什么）
2. **有证据吗**？（数字、链接、截图路径、报错原文；没有证据就标 `confidence: low`）
3. **可复用吗**？（下次遇到同类问题，能不能照着做）

**写法规范**
- 每条记录：**背景 → 选项 → 决定/结论 → 理由 → 代价/风险 → 证据 → 下一步**
- 主观判断必须显式标注为判断（`判断：`），与事实（`事实：`）分开
- 数字必须带**单位、时间、来源**；没有来源就写 `来源：未知`
- **不知道就写"不知道"**，禁止把估计值写成实测值
- 给未来的读者写，不给现在的自己写；少用"这个/那个"，多写具体对象

深度规范见 `references/02-writing-guide.md`。

---

## 7. CLI 速查

脚本：`<SKILL>/scripts/journal.py`（Python 3，**仅标准库**，无依赖）
统一参数：`--root <记录根目录>`（必填）；日期类参数 `--date YYYY-MM-DD`（默认本地今天）

```bash
# 立项
init --project "名称" --slug slug --stage S0 --currency USD \
     --hypothesis "..." --success "..." --stop-loss "..." \
     [--root <记录根>] [--project-root <项目根>] [--force]
anchor --root <记录根> --project-root <项目根>        # 重新注入/刷新 AGENTS.md 锚点

# 日常
status --root <根> [--json]                          # 一行体检：阶段/最后记录/停滞天数/未闭环
resume --root <根>                                   # 生成"补液包"（新会话先跑这个）
add --root <根> --type <类型> --title "标题" [--body-file f.md] [--tags a,b] [--link ADR-0001] [--status open] [--date D]
update --root <根> --id <ID> [--status ...] [--body-file f.md | --append-file f.md] [--result ...]   # 更新档案；两文件参数同义
metric --root <根> --name MRR --value 120 --unit USD [--source "Stripe"] [--confidence high]
ledger --root <根> --kind income|cost --amount 99 --currency USD --channel "..." [--note "..."]
stage  --root <根> --set S3 --why "拿到首单"
index  --root <根>                                   # 重建 INDEX.md / STATE.md
lint   --root <根> [--strict]                        # 体检：结构/ID/密钥泄露/停滞

# 阶段收束
review    --root <根> --period weekly|monthly        # 生成复盘骨架（自动填事实，人补分析）
closeout  --root <根> --outcome success|failure|pivot|paused --title "..." 
publish   --root <根> [--outdir <目录>] [--force]    # 脱敏 → 可销售资产包
vault-index --root <vault>                           # 跨项目总览（多项目资产化）

# 自我迭代（记录并修订这个 skill 自身）
evolve --category bug|logic|schema|docs|usability|performance|feature \
       --severity critical|high|medium|low --title "..." [--body-file f] \
       [--evidence "..."] [--repro "..."] [--project <slug>] [--status open|proposed]
evolve-list [--status open] [--json]                 # 查看迭代台账
evolve-apply --id EV-0005 --bump patch|minor|major --summary "改了什么"   # 自测→升版本→CHANGELOG
doctor                                               # skill 安装自检
upgrade --root <记录根> [--keep-protocol]             # 已有项目迁移（不动日记与档案）
lint --root <记录根> --auto-evolve                    # 自动把结构性问题写入台账
python "<SKILL>/scripts/selftest.py"                 # 回归自测（发布门禁）
```

**`--type` 取值**：`task | decision | problem | solution | insight | experiment | metric | risk | lesson | revenue | cost | milestone | question`
其中 `decision/problem/solution/experiment/insight/lesson/risk/milestone` 会自动开一份 `records/` 档案并生成 ID。

**中文正文的处理**：正文用 `--body-file`（先写文件再传路径），或直接用编辑工具写 `records/` 里的 md 文件后跑 `index`。**不要把长中文塞进命令行参数**（转义易出错）。

---

## 8. 自我迭代（这个 skill 自己坏了怎么办）

**原则：skill 也是一个产品。运行中暴露的问题不记下来，它就会一直坏下去；每一次被迫绕过，都在消耗信任。**

### 8.1 闭环

`@
DETECT 发现 -> LOG 记录(evolve) -> TRIAGE 分级分流 -> FIX 修改
    -> VERIFY 回归自测 -> RELEASE 升版本+CHANGELOG -> PROPAGATE upgrade 迁移已有项目
`@

### 8.2 DETECT：命中即记（不许只在对话里抱怨一句）

- 命令报错、退出码非 0、崩溃（崩溃由脚本自动记录，退出码 3）
- 参数、模板、文档三者不一致；模板字段根本填不进去
- 流程缺步骤、走不通，**你不得不绕过 skill 才能完成任务**
- 索引/配对/脱敏/STATE 等自动行为结果不对
- `lint` 打印的 `[EVOLVE]` 结构性问题（schema 漂移、档案缺 front matter、CSV 表头不一致、契约版本落后等）
- 记录成本高到会让人放弃记录（这本身就是最该修的 bug）

### 8.3 LOG：记录

`@bash
journal.py evolve --category bug --severity high --title "一句话现象" \
  --body-file symptom.md --evidence "scripts/journal.py:412 / 输出片段" \
  --repro "journal.py publish --root X" --project <slug>
journal.py lint --auto-evolve     # 自动把检测到的结构性问题写入台账
journal.py evolve-list [--status open]
`@

- `category`：`bug` 实现错 / `logic` 运行逻辑错 / `schema` 格式与迁移 / `docs` 文档不符 / `usability` 难用 / `performance` 慢 / `feature` 缺能力
- `severity`：`critical` 数据或密钥事故 / `high` 崩溃与功能不可用 / `medium` 结果错但有绕法 / `low` 体验
- 台账在 skill 目录 `evolution/LEDGER.md`（机器可读 `ledger.json`），**跨项目共享**，相同类别+标题自动去重
- **台账里不写项目业务内容与隐私**：只写引用路径、命令、错误输出

### 8.4 TRIAGE：分流（要不要自动改）

| 情况 | 处置 |
|---|---|
| 修复明确、影响局部（bug/文案/校验） | 直接改 → 自测 → `evolve-apply --bump patch` |
| 涉及记录格式、字段、目录结构 | `--bump minor` + 写迁移 + 对已有项目 `upgrade` |
| 语义或方向性变化、可能破坏已有记录、需用户拍板 | 只记 `--status proposed`，**问用户，不要自动改** |

### 8.5 FIX → VERIFY → RELEASE

1. 改文件：`scripts/journal.py`、`references/`、`templates/`、`SKILL.md`（文档与实现必须同步改）
2. **给这个 bug 补一条自测用例**（否则下次改动会让它复发）
3. 一次调用完成闭环：

`@bash
journal.py evolve-apply --id EV-0005 --bump minor --summary "改了什么、为什么"
`@

它会**先跑** `scripts/selftest.py`：不通过就中止，不改版本号、不标记 applied。
通过后：升 `manifest.json` 版本 → 在 `CHANGELOG.md` 顶部插入条目 → 台账标记 `applied` + 修复版本。

### 8.6 PROPAGATE：已有项目跟上

`@bash
journal.py lint --root <记录根>       # 提示 skill / 契约版本落后
journal.py upgrade --root <记录根>    # 迁移 tracker 字段、PROTOCOL 契约、AGENTS 锚点
journal.py doctor                     # skill 安装自检：文件齐全 / 版本一致 / 语法 / 台账
`@

- `upgrade` **不动任何日记与档案**（历史不可变），只更新基础设施
- 旧版 `PROTOCOL.md` 先备份为 `PROTOCOL.md.bak-v<旧版本>` 再刷新；想保留原文件用 `--keep-protocol`（新版写 `.new`）
- 成功线/止损线、日记、档案一律不受升级影响

### 8.7 治理红线

1. **先记录再修**：没有 EV 编号的改动不允许
2. **每次修复必须过自测**，并补用例
3. **必须升版本 + 写 CHANGELOG**（语义化：patch 修错 / minor 加能力或扩格式 / major 破坏兼容）
4. **台账 append-only**：`rejected` / `wontfix` 也要写理由，不许删条目
5. **拿不准就问**，禁止擅自修改语义
6. **不许为了过测试而改测试**

> 完整方法论（分级判据、迁移机制、反模式）见 `references/08-self-evolution.md`。

## 9. 铁律与护栏

1. **append-only**：日记与档案不删不改；要更正就新增一条并标 `[更正 ADR-0003]`。历史是用来学习的，不是用来美化的。
2. **禁止密钥与隐私**：API Key、密码、token、客户真实姓名/手机号/邮箱、身份证一律不得写入。`lint` 会扫描泄露；`publish` 会强制脱敏。
3. **不编造**：数字、日期、引用、用户的话，没确认就不写；宁可 `待确认`。
4. **不隔夜**：本次会话产生的条目在本次会话结束前落盘。
5. **先读后写**：任何 CAPTURE 之前必须 RESUME（或至少读 `STATE.md` + 当日日记），避免重复建 ID、覆盖别人写的内容。
6. **区分事实与判断**（见 §6）。
7. **不越权**：记录用户明确拒绝记录的内容时，只记"此处有敏感信息，已按用户要求略过"。

---

## 10. 变现追踪与终局

**阶段机**：`S0 想法 → S1 验证 → S2 构建 → S3 上线 → S4 获客 → S5 付费 → S6 稳定收入 / 规模化`
**终局状态**：`success`（达成 CHARTER 里的成功线）、`failure`（触发止损线，止损退出）、`pivot`（转向）、`paused`（暂停）、`zombie`（既没死也没长）

只有 CHARTER 里**预先写下的标尺**能判定成败——这是本 skill 最重要的一条设计。详见 `references/04-monetization.md`。

`closeout` 会生成终局档案骨架并自动填入：历时、阶段轨迹、总收入/总成本、关键数字、条目统计；需要人/Agent 补写：**关键转折点、成败归因、可复用打法、会重来的做法、不会再做的做法、给下个项目的检查清单**。

---

## 11. 资产化（可销售的数字化资产）

原始日记**不是**商品；商品是**提炼后的结构**。`publish` 产出：

| 文件 | 用途 |
|---|---|
| `CASE-STUDY.md` | 完整案例研究：背景→阶段→决策→卡点→解法→结果（可单独售卖/引流） |
| `PLAYBOOK.md` | 打法手册：从 solution 档案提炼的可复用步骤 |
| `LESSONS.md` | 经验教训清单：每条一句话 + 代价 + 适用边界 |
| `METRICS.csv` | 脱敏后的真实数字（可信度就是卖点） |
| `LEDGER-SUMMARY.md` | 收支与单位经济模型 |
| `PRODUCT-SHEET.md` | 商品化外壳：受众、目录、卖点、定价位、授权条款 |
| `INDEX.md` + `_redaction-report.md` | 阅读指南 + 脱敏审计（证明无隐私泄露） |

**卖点检验**（四条都过才值得上架）：① 有真实数字 ② 有可复用的决策/打法 ③ 有坦白的失败 ④ 完全脱敏。
进阶：多个项目完成后用 `vault-index` 做跨项目汇总，形成**行业数据库/榜单**型资产（单价更高）。详见 `references/06-digital-asset.md`。

---

## 12. 每次调用后向用户汇报什么

**BOOTSTRAP 后**
```
✅ 已为「<项目>」建立跟踪：<root 路径>
- 阶段：S0 想法 ｜ 成功线：<...> ｜ 止损线：<...>
- 已注入会话锚点：<项目根>/AGENTS.md（此后每次会话自动续记）
- 已落盘：<N> 条（D/P/I ...）
- 下次会话开始请说"继续 <项目>"，或直接开工（锚点会提醒 Agent 续记）
```

**日常 CAPTURE 后**（短）
```
📝 本次记录 <N> 条：ADR-0003 放弃 WhatsApp 渠道 ｜ PB-0007 登录态失效（已解决 → SL-0002）
📊 指标：MRR 120 USD ｜ 状态：S3 上线，停滞 0 天，未闭环 2 项
```

**发现 skill 自身问题时**
```
🔧 已记录 skill 问题 EV-0005（logic/high）：<一句话现象>
   处置：<直接修 / 已提 proposed 待你拍板>；修复后会跑自测、升版本并迁移已有项目（见 §8）
```

**CLOSEOUT 后**
```
🏁 项目「<项目>」结束：<outcome>（历时 <N> 天，收入 <X>，成本 <Y>）
- 资产包：<root>/publish/<日期>/（7 个文件，已脱敏）
- 最值钱的 3 条教训：...
```

---

## 13. references 索引

| 文件 | 何时读 |
|---|---|
| `references/00-protocol.md` | 需要引用/复制记录契约原文时（每项目 `PROTOCOL.md` 的源） |
| `references/01-taxonomy.md` | 不确定该用哪种类型/ID/字段时 |
| `references/02-writing-guide.md` | 写决策、问题、教训等长档案时（含范例对照） |
| `references/03-cadence.md` | 日/周/月节律、会话收尾清单 |
| `references/04-monetization.md` | 变现假设、阶段机、实验设计、单位经济、成败判定 |
| `references/05-closeout.md` | 项目终止：成败归因与复盘方法 |
| `references/06-digital-asset.md` | 资产打包、脱敏、定价、授权 |
| `references/07-troubleshooting.md` | 多项目并存、路径/锚点问题、恢复、性能 |
| `references/08-self-evolution.md` | 发现 skill 自身的 bug／逻辑问题，要记录或修订它时 |

模板：`templates/`（CHARTER / NEXT-ACTIONS / 各类型记录蓝图 records.md / 日记条目 daily-entry.md）。
`STATE.md` 与 `INDEX.md` 由脚本自动生成，没有手写模板。
