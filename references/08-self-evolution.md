# 自我迭代：记录并修订这个 skill 自身

> **原则**：skill 也是一个产品。运行中暴露的问题如果不被记下来，它就会一直坏下去，
> 而且每一次被绕过都会消耗使用者的信任。本机制让 skill 在使用中自己变好。

## 1. 闭环六步

```
DETECT 发现  ->  LOG 记录(evolve)  ->  TRIAGE 分级分流  ->  FIX 修改
      ->  VERIFY 回归自测  ->  RELEASE 升版本+CHANGELOG  ->  PROPAGATE upgrade 迁移已有项目
```

没有 LOG 就没有 FIX；没有 VERIFY 就不许 RELEASE。这两条是这个闭环能长期跑下去的原因。

## 2. DETECT：什么必须记（不许只在对话里抱怨一句）

**人工发现（Agent/人）**
1. 命令报错、退出码非 0、崩溃（崩溃由脚本自动记录，退出码 3）
2. 参数、模板、文档三者不一致（文档说有这个参数，实际没有；模板字段填不进去）
3. 流程缺步骤或走不通，**你不得不绕过 skill 才能完成任务**
4. 自动行为结果不对：ID 重复、索引缺项、问题与解法没配上、脱敏没生效、STATE 过期
5. 语义不适用：某个分类/字段/阶段定义在真实项目里根本用不上，或缺少必需分类
6. 体验摩擦：命令太长、参数反直觉、输出看不懂——**记录成本高于收益时，记录行为本身就会消失**

**自动发现**
- `lint` 会检测结构性问题并打印 `[EVOLVE]` 行（schema 漂移、档案缺 front matter、
  CSV 表头不一致、日记文件名不合规、skill 版本落后、PROTOCOL 契约版本落后）
- `lint --auto-evolve` 把这些自动写入台账
- 命令抛异常时，入口会捕获堆栈与命令行，自动记一条 `bug/high`

## 3. LOG：记录格式

```bash
journal.py evolve --category bug --severity high \
  --title "一句话说清现象" \
  --body-file symptom.md \
  --evidence "scripts/journal.py:412 / 命令输出片段" \
  --repro "journal.py publish --root X" \
  --project <项目 slug>
```

字段要求：
- `title`：可检索、可去重。写现象，不写猜测（"publish 在无实验记录时表格为空"，而不是"publish 有点问题"）
- `symptom`（--body-file）：**期望 vs 实际**，加上最小复现条件
- `evidence`：文件:行、命令输出、数据样例——让修复者不必重新调查
- `repro`：一条能复现的命令
- `category`：`bug`（实现错） / `logic`（运行逻辑设计错） / `schema`（记录格式/版本/迁移） /
  `docs`（文档与实现不一致） / `usability`（能用但难用） / `performance`（太慢） / `feature`（缺能力）
- `severity`：`critical` / `high` / `medium` / `low`

台账位置：`<skill>/evolution/ledger.json`（机器可读）+ `LEDGER.md`（人看，自动生成）。
**跨项目共享**——同一个 skill 服务所有项目，问题只该修一次。相同类别+标题会自动去重。

## 4. TRIAGE：分级与分流

| 严重度 | 判据 | 处置时限 |
|---|---|---|
| critical | 数据丢失或写错、密钥泄露、记录整体不可用 | 立即 |
| high | 命令崩溃、关键功能不可用、产出物错误 | 当天 |
| medium | 结果不正确但有绕法、文档误导、流程缺步骤 | 排期 |
| low | 措辞、体验、锦上添花 | 批量处理 |

**分流规则（决定要不要自动改）**
- 修复明确、影响面局部（文案、模板、校验、小 bug）→ 直接改，跑自测，`evolve-apply --bump patch`
- 涉及记录格式/字段/目录结构 → `--bump minor`，同时写迁移逻辑，并对已有项目跑 `upgrade`
- 语义或方向性变化、可能破坏已有记录、需要用户拍板 → 只记 `--status proposed`，
  **把选择权交给用户，不要自动改**；用户同意后再走 FIX 流程

## 5. FIX：改哪里

| 现象 | 通常改 |
|---|---|
| 命令行为错、崩溃 | `scripts/journal.py` |
| 缺校验/缺自动检测 | `journal.py` 的 `cmd_lint` / `cmd_doctor` |
| 文档与实现不一致 | `SKILL.md` 与对应 `references/0X-*.md`（**两边都要改**） |
| 模板字段不适用 | `templates/*.md` + `journal.py` 生成逻辑 |
| 契约变化（新字段/新规则） | `references/00-protocol.md`（会随 `upgrade` 分发到各项目） |

**改完自问**：老项目还能跑吗？需要迁移吗？`SKILL.md` 与 references 是否同步？

## 6. VERIFY：回归自测是门禁

```bash
python scripts/selftest.py
```

- 任何修复**必须**在 `scripts/selftest.py` 里补一条覆盖该问题的用例——否则下次改动会让它复发
- 修复后必须全绿；`evolve-apply` 会在升版本前自动跑一次，不通过就中止
- 新增能力优先"加"而不是"改"，减少对既有测试的冲击

## 7. RELEASE：版本与变更日志

语义化版本：
- `patch`：修 bug、改文案、加校验（不改变记录格式）
- `minor`：新增命令/字段/车道；记录格式向后兼容地扩展
- `major`：破坏兼容（旧记录必须迁移才能用）

```bash
journal.py evolve-apply --id EV-0005 --bump minor --summary "改了什么、为什么"
```
它会依次：跑自测 → 升 `manifest.json` 版本 → 在 `CHANGELOG.md` 顶部插入条目 →
把台账条目标记 `applied` 并记录修复版本。**任一步失败都不产生半成品状态。**

## 8. PROPAGATE：已有项目跟上

```bash
journal.py lint --root <记录目录>        # 提示 skill/契约版本落后
journal.py upgrade --root <记录目录>     # 迁移：tracker 字段、PROTOCOL 契约、AGENTS 锚点
```

- `tracker.json` 记录 `skill_version`；`PROTOCOL.md` 头部记录 `契约版本`
- `upgrade` **不动任何日记与档案**（历史不可变），只更新基础设施
- PROTOCOL.md 是工具生成文件：升级时先备份为 `PROTOCOL.md.bak-v<旧版本>` 再刷新，避免静默丢内容；
  确实手工维护过该文件的用 `--keep-protocol`，新版写 `PROTOCOL.md.new` 由人合并
- `doctor` 检查安装完整性：文件齐全、版本一致、脚本语法、台账可读

## 9. 治理红线

1. **先记录再修**：没有 EV 编号的改动不允许
2. **每次修复必须过自测**，并补用例
3. **必须升版本 + 写 CHANGELOG**
4. **台账 append-only**：判断变化用 status 表达；`rejected` / `wontfix` 也是有效结论（要写理由）
5. **台账里不写项目隐私**：只写引用路径、命令、错误输出；不复制业务内容
6. **拿不准就问**：`proposed` 状态 + 征询用户，禁止擅自改语义
7. **不许为了过测试而改测试**：测试是安全网，不是装饰

## 10. 反模式

| 反模式 | 后果 |
|---|---|
| 在对话里抱怨但不记录 | 问题随会话蒸发，下次照旧 |
| 直接改代码不记录 | 无法追溯为什么改，无法迁移 |
| 改了不跑自测 | 修一个坏两个 |
| 版本号不动 / CHANGELOG 不写 | 无法判断项目用的是哪版 skill |
| 改语义却当 patch 发 | 老项目静默失效 |
| 台账写成项目日志 | 隐私泄露风险 + 跨项目噪音 |
| 只修症状不修根因 | 复发 |
