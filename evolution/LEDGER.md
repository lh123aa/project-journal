# 自我迭代台账 . project-journal

> 由 journal.py 自动生成（2026-10-09T11:29:04），请勿手工编辑；改 ledger.json 后重跑任意 evolve 命令即可重建本视图。
> 用途：记录本 skill 自身在运行中暴露的 bug / 逻辑问题 / 易用性问题及修订历史。
> 闭环流程与治理规则见 references/08-self-evolution.md。

- 当前版本：v1.2.0 . 条目 9 条 (applied 9)

| ID | 日期 | 类别 | 严重度 | 状态 | 标题 | 修复版本 |
|---|---|---|---|---|---|---|
| EV-0001 | 2026-10-09 | bug | high | applied | 案例研究缺少「关键认知与讨论」车道，insight 正文进不了资产包 | 1.0.1 |
| EV-0002 | 2026-10-09 | logic | medium | applied | 问题与解法配对只看 problem 侧 links，解法常被漏配 | 1.0.1 |
| EV-0003 | 2026-10-09 | usability | low | applied | 重复 init 仍提示「补全 CHARTER」，对已有项目是误导 | 1.0.1 |
| EV-0004 | 2026-10-09 | usability | low | applied | NEXT-ACTIONS 模板留空 checkbox，STATE 出现空条目 | 1.0.1 |
| EV-0005 | 2026-10-09 | feature | high | applied | 缺少自我迭代能力：运行中发现的 bug 无处记录，修复无自测门禁与版本追溯 | 1.1.0 |
| EV-0006 | 2026-10-09 | logic | medium | applied | upgrade 无法刷新无 hash 记录的旧项目，PROTOCOL 落后提示永久存在 | 1.1.1 |
| EV-0007 | 2026-10-09 | logic | medium | applied | 记录目录应固定在项目根的子文件夹；且向上找 .git 会把锚点注入到上级仓库 | 1.1.2 |
| EV-0008 | 2026-10-09 | bug | medium | applied | 误报：合规的日记文件名被判为不合规 | 1.1.3 |
| EV-0009 | 2026-10-09 | feature | high | applied | 缺少跨工具全局注册：所有 Agent 工具都能发现并调用本 skill | 1.2.0 |

## EV-0001 案例研究缺少「关键认知与讨论」车道，insight 正文进不了资产包

- 日期：2026-10-09 . 类别：bug . 严重度：high . 状态：applied . 发现于：v1.0.0
- 相关项目：-
- 复现命令：journal.py publish --root 含 insight 档案的项目
- 证据：scripts/journal.py cmd_publish 的 cs 组装未遍历 by_type['insight']

**症状 / 期望**

```
期望：讨论中形成的认知更新（insight）作为「有价值的讨论」进入 CASE-STUDY。
实际：CASE-STUDY 只输出 decision/problem/solution/lesson，insight 仅在 LESSONS.md 附录被压成一行。
```

**修复**

CASE-STUDY 新增「## 3. 关键认知与讨论」并重排后续小节编号；自测补 check「publish 含关键认知车道」。

- 修复版本：v1.0.1（2026-10-09）

## EV-0002 问题与解法配对只看 problem 侧 links，解法常被漏配

- 日期：2026-10-09 . 类别：logic . 严重度：medium . 状态：applied . 发现于：v1.0.0
- 相关项目：-
- 复现命令：journal.py add --type solution --link PB-0001 后再 publish
- 证据：cmd_publish 中 s['id'] in tags 仅取 problem 侧字段

**症状 / 期望**

```
期望：solution 用 --link PB-0001 关联问题后，案例研究里问题下方紧跟该解法。
实际：配对只检查 problem 的 tags/links，导致解法掉到后面的独立小节，叙事断裂。
```

**修复**

改为双向匹配（两侧任一含对方 ID 即配对），并用 paired 集合避免重复输出；自测补 check「publish 按 links 配对问题与解法」。

- 修复版本：v1.0.1（2026-10-09）

## EV-0003 重复 init 仍提示「补全 CHARTER」，对已有项目是误导

- 日期：2026-10-09 . 类别：usability . 严重度：low . 状态：applied . 发现于：v1.0.0
- 相关项目：-
- 复现命令：journal.py init --root 已存在目录
- 证据：cmd_init 结尾的 say 分支未区分 existed

**症状 / 期望**

```
期望：对已存在的记录目录，init 应提示开工流程（resume）。
实际：无论新旧都打印下一步补全 CHARTER.md 的成功线/止损线。
```

**修复**

按 existed 分支输出：已有目录提示 resume 与收工流程；新建目录才提示补全 CHARTER。

- 修复版本：v1.0.1（2026-10-09）

## EV-0004 NEXT-ACTIONS 模板留空 checkbox，STATE 出现空条目

- 日期：2026-10-09 . 类别：usability . 严重度：low . 状态：applied . 发现于：v1.0.0
- 相关项目：-
- 复现命令：journal.py init 后查看 STATE.md 的下一步段
- 证据：templates/NEXT-ACTIONS.md 的空分区各留了一个空 checkbox

**症状 / 期望**

```
期望：无待办时 STATE 的下一步段显示没有未完成事项。
实际：模板里预留的空 checkbox 行被当成待办，STATE 输出空破折号。
```

**修复**

模板改为空分区不留 checkbox（只留标题）；脚本侧解析逻辑不变。

- 修复版本：v1.0.1（2026-10-09）

## EV-0005 缺少自我迭代能力：运行中发现的 bug 无处记录，修复无自测门禁与版本追溯

- 日期：2026-10-09 . 类别：feature . 严重度：high . 状态：applied . 发现于：v1.0.1
- 相关项目：-
- 复现命令：journal.py doctor（v1.0.0 不存在该命令）
- 证据：SKILL.md v1.0.0 无自我迭代章节；无 scripts/selftest.py；无 evolution/；manifest 无版本治理

**症状 / 期望**

```
期望：skill 在使用中暴露的问题能被记录、分级、修复、验证、发布并可迁移到已有项目。
实际：v1.0.0 只有文档，没有台账、没有回归自测、没有版本与迁移机制；问题只能在对话里说一句，随会话蒸发。
```

**修复**

新增自我迭代子系统：evolve/evolve-list/evolve-apply/doctor/upgrade 五个命令、崩溃自动记录、lint 结构性问题检测（--auto-evolve）、22 项回归自测门禁 selftest.py、CHANGELOG 与语义化版本治理、PROTOCOL 契约版本与安全迁移（upgrade 不动历史记录），并补 references/08-self-evolution.md 与 SKILL.md 第 8 节

- 修复版本：v1.1.0（2026-10-09）

## EV-0006 upgrade 无法刷新无 hash 记录的旧项目，PROTOCOL 落后提示永久存在

- 日期：2026-10-09 . 类别：logic . 严重度：medium . 状态：applied . 发现于：v1.1.0
- 相关项目：-
- 复现命令：journal.py upgrade --root <旧版创建且无 protocol_hash 的记录目录>
- 证据：scripts/journal.py cmd_upgrade 的 else 分支：无 protocol_hash 时只写 PROTOCOL.md.new

**症状 / 期望**

```
**期望**：对由旧版 skill 创建、tracker.json 里没有 protocol_hash 的记录目录，upgrade 应把 PROTOCOL.md 刷新到当前契约版本，结束版本落后状态。

**实际**：cmd_upgrade 只在 `当前的 hash == 记录的 hash`（或 --force-protocol）时才覆盖；旧项目没有记录 hash，于是走 else 分支，只写出 PROTOCOL.md.new，原文件不动。

**后果**：lint 的 [EVOLVE] "PROTOCOL.md 契约版本落后" 永远无法消除，每次 lint 都提示，形成长期噪音；用户还要手工合并一个本就由工具生成的文件。

**最小复现**：init 一个记录目录 → 删除 tracker.json 的 protocol_hash 并把 skill_version 改成旧版本 → 跑 upgrade → PROTOCOL.md 未变，lint 仍报落后。

**修复方向**：PROTOCOL.md 是工具生成文件（文件头已声明），升级时应先备份为 PROTOCOL.md.bak-v<旧版本> 再覆盖；只想保留原文件的人用 --keep-protocol 走 .new 分支。
```

**修复**

upgrade 改为先备份再刷新工具生成的 PROTOCOL.md（新增 --keep-protocol 逃生口），消除旧项目永远无法清掉的 [EVOLVE] 提示；补充回归用例（第 23 项）

- 修复版本：v1.1.1（2026-10-09）

## EV-0007 记录目录应固定在项目根的子文件夹；且向上找 .git 会把锚点注入到上级仓库

- 日期：2026-10-09 . 类别：logic . 严重度：medium . 状态：applied . 发现于：v1.1.1
- 相关项目：-
- 复现命令：init --root X/sub/proj/project-journal（X 有 .git，proj 没有）
- 证据：SKILL.md 第3/4.1节与 references/07 的路径写法；scripts/journal.py guess_project_root 的向上探测顺序

**症状 / 期望**

```
**用户约定的存放位置**：项目记录目录就是**当前项目根目录下的一个子文件夹**，即 `<项目根>/project-journal/`，随项目一起提交 git。

**问题 1（docs）**：SKILL.md §3/§4.1 与 references/07 写的是 `<项目>/project-journal/<slug>/`，多了一层冗余 slug —— 记录本来就是一项目一份，且已经在项目内，不需要再按 slug 分层。

**问题 2（logic，更危险）**：guess_project_root 先在 root 起向上 6 层找 .git/AGENTS.md，找不到才用 "project-journal" 路径段回退。
当项目自己**没有 .git**、但上层有（monorepo / 上级仓库 / 上层目录放了 AGENTS.md）时，会返回上层目录，
于是会话锚点被注入到**不属于本项目的 AGENTS.md** 里 —— 相当于让无关项目去跟踪另一个项目的记录。

**最小复现**：构造 `X/.git` 与 `X/sub/proj/project-journal`（proj 无 .git），
执行 init --root X/sub/proj/project-journal → 锚点写到 X/AGENTS.md 而不是 X/sub/proj/AGENTS.md。

**修复方向**：约定优先 —— root 的 basename 是 project-journal 时，项目根直接取上一级；
其余情况才向上有限层（<=3）探测，仍不确定就返回 None 并提示用 --project-root，绝不猜。
```

**修复**

记录目录约定改为项目根下的子文件夹 <项目根>/project-journal（去掉冗余 slug 层），SKILL.md/references 同步；guess_project_root 改为约定优先，不再向上越过项目去命中上级 .git，避免把会话锚点注入到无关仓库；新增 2 项回归用例（锚点不被劫持、cwd 默认位置）

- 修复版本：v1.1.2（2026-10-09）

## EV-0008 误报：合规的日记文件名被判为不合规

- 日期：2026-10-09 . 类别：bug . 严重度：medium . 状态：applied . 发现于：v1.1.2
- 相关项目：haiwai-bianxian
- 复现命令：journal.py lint --root 任意正常项目
- 证据：scripts/journal.py:1183 原为 fullmatch(r d{4}-d{2}-d{2}.md )，反斜杠丢失；实机输出 journal/2026-10-09.md 被报不合规

**症状 / 期望**

```
**现象**：在真实项目（海外变现）里跑 lint 时，它把完全合规的日记文件名报成结构性问题：

    [EVOLVE] (bug/medium) 日记文件名不符合 YYYY-MM-DD.md：2026-10-09.md

**根因**：scripts/journal.py 第 1183 行的正则被写成了 `r"d{4}-d{2}-d{2}.md"`，
反斜杠在编辑过程中丢失（原文应为 `\d{4}-\d{2}-\d{2}\.md`）。
于是该正则几乎匹配任何东西，`not fullmatch(...)` 恒为真 → 每个正常日记文件都被误报。

**影响**：lint 的 [EVOLVE] 提示是自我迭代的输入源，误报会稀释信噪比，
让人开始忽略提示 —— 这比不报更糟。

**同类风险**：同一次编辑可能还有别的正则丢了反斜杠。已全量审计 scripts/journal.py 中
所有 re.* 字面量，仅第 1171 行的 `([0-9]+.[0-9]+.[0-9]+)` 点号未转义（功能等价，一并规范）。

**修复方向**：修正两处正则；并在 selftest.py 增加断言"干净项目的 lint 输出不得包含 [EVOLVE]"，
把"误报"变成会被测试拦住的回归项。
```

**修复**

修正 lint 中丢失反斜杠的日记文件名正则（把合规文件误报为结构性问题），并规范一处未转义的点号；selftest 新增断言：干净项目的 lint 输出不得包含 [EVOLVE]（含误报即失败）

- 修复版本：v1.1.3（2026-10-09）

## EV-0009 缺少跨工具全局注册：所有 Agent 工具都能发现并调用本 skill

- 日期：2026-10-09 . 类别：feature . 严重度：high . 状态：applied . 发现于：v1.1.3
- 相关项目：-
- 复现命令：安装后在其他 Agent 工具中提问：如何跟踪这个项目
- 证据：已检测本机安装：.claude/.codex/.gemini/.config/opencode/.cursor/.codeium-windsurf 均存在，但 skill 只存在于 .agents/skills

**症状 / 期望**

```
**需求**：把 skill 注册为**全局技能**，让所有 Agent 工具（Claude Code / Codex CLI / Gemini CLI / opencode / Cursor / Windsurf / DSH 等）都能发现并调用它，而不是只在装了它的某一个工具里可用。

**现状缺口**：安装只落在 @@~/.agents/skills/project-journal@@ 一处。
- 有技能加载器的工具（Claude Code）需要各自的技能目录
- 没有技能加载器的工具（Codex / Gemini / Windsurf）只能靠全局指令文件发现
- 用户每换一个工具就要手工配置一遍，而且不知道配没配对

**要做**：
1. 新增 @@scripts/install-global.py@@：以 @@~/.agents/skills/project-journal@@ 为唯一真源，
   向各工具目录建立链接（Windows 优先 junction，免管理员权限；失败则复制），
   并向各工具的全局指令文件注入**托管块**（幂等，可重复执行）
2. 支持 @@--home@@ 以便在临时目录里自测（不碰真实用户目录）
3. 支持 @@--check@@ 只体检不落盘
4. 输出"哪个工具怎么被发现"的对照表

**边界**：DSH 已原生发现 @@~/.agents/skills@@，不额外注册，避免目录里出现重复条目。
```

**修复**

新增 scripts/install-global.py：以 ~/.agents/skills/project-journal 为唯一真源，一键把 skill 注册为全局技能——Claude Code/opencode/Cursor 建 junction 链接（PowerShell 优先，cmd mklink 兜底且校验结果），Codex/Gemini/Windsurf 注入幂等托管块，DSH 原生发现不重复注册；链接指向 git 仓库，git pull 即可全工具升级。修复 cmd.exe 参数解析偶发失败导致静默退化为复制的问题（现明确告警）。新增 USAGE.md 完整手册与第 27 项回归用例

- 修复版本：v1.2.0（2026-10-09）
