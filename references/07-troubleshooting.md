# 排障与边界情况

## 1. 记录目录放哪

| 布局 | 命令 | 适用 |
|---|---|---|
| **项目根的子文件夹（默认约定）** | `init --root <项目根>/project-journal` | 一个项目一份，随 git 走；锚点自动落在项目根 |
| 更省事 | 在项目根下直接 `init --project "<名称>"` | 等价于 `--root ./project-journal` |
| 自定义文件夹名 | `init --root <项目根>/<文件夹> --project-root <项目根>` | 想用中文名等 |
| 集中式 vault | `init --root <vault>/<slug> --project-root <项目根>` | 多项目统一管理、便于资产化 |
| 老项目补建 | 同上，然后手工补记关键历史节点 | 已有项目 |

**集中式 vault 必须显式给 `--project-root`**，否则脚本无法推断锚点写到哪里（会打印 WARN 并跳过注入）。

## 2. 锚点相关问题

- **没注入锚点**：`journal.py anchor --root <root> --project-root <proj>` 手动补
- **路径变了**（移动了目录/换了机器）：重跑 `anchor`，托管块会被原地更新
- **项目根没有 AGENTS.md**：脚本会创建；若已有 `CLAUDE.md` 且无 `AGENTS.md`，会写进 CLAUDE.md
- **不要手工编辑托管块**：下次注入会被覆盖；要改协议就改 skill 里的模板或 PROTOCOL.md

## 3. 多项目并存

- 一个项目一个记录根目录，**不要共用**
- `status`/`resume` 都要显式 `--root`；根目录搞错会得到"不是有效的记录目录"
- 跨项目汇总：`journal.py vault-index --root <vault>` → 生成 `VAULT-INDEX.md`

## 4. 中文与编码

- 全部写盘为 UTF-8；命令行里**不要塞长中文正文**，用 `--body-file` 或直接写档案文件
- Windows 终端显示乱码不影响文件内容，用编辑器或 `read` 工具确认
- 从 Excel/网页复制的文本可能含不换行空格，Lint 不检查这类问题，人工留意

## 5. resume 输出太长

- 用 `--max-chars 4000` 限制
- 或者只看 `STATE.md`；需要细节时按 `INDEX.md` 定位到具体日期/档案

## 6. lint 报"疑似敏感信息"

- 邮箱/手机号命中很常见（尤其记录用户访谈时）
- 处理：把真实信息换成代号写进日记，真实对应关系存在**项目外的私密位置**（不要放 assets/，那里会一起 publish）
- 确实需要保留原文时，在 `sanitize.txt` 里加规则，让 publish 阶段自动替换

## 7. 误改/误删

- 没有内置版本控制：**强烈建议把记录目录纳入 git**（`git add project-journal`），或定期备份
- 被覆盖的自动生成文件（STATE/INDEX/tracker）直接重跑 `index` 即可重建
- 日记被误删：从 git 恢复；没有 git 就只能靠备份

## 8. 两个 Agent 同时写

- 追加写基本安全（都在文件末尾），但可能覆盖彼此的 STATE/INDEX 刷新
- 约定：写完各自的档案后，最后一个人跑 `index` 与 `lint`
- 高频并发场景（多 Agent 并行开发）建议每个 Agent 写不同 `--type` 或不重叠的主题

## 9. 迁移已有项目（补记历史）

1. `init` 建立目录
2. 用已知信息补写 `CHARTER.md`（目标/假设/成功线）
3. 按时间顺序补记关键节点：`add --date 2026-09-01 --type decision ...`（脚本支持指定日期，会自动写进对应日期的日记）
4. 阶段用 `stage --set` 补推，`why` 里写清当时的依据
5. 无法确认的历史细节写"待确认"，**不要凭记忆编造**
6. 补完后 `lint` + `index`

## 10. 与其它 skill 协作

- 记录的是**过程**，不替代交付类 skill（如开发、设计、写作 skill）
- 交付物本身放项目的正常位置；记录目录只放"决策/问题/数据/教训"和证据快照
- 项目结束后若要把过程做成对外文章/网页，先 `publish` 脱敏，再交给排版类 skill

## 11. 命令返回码

- `0` 成功
- `1` lint 失败（有 error，或 `--strict` 下有 warn）
- `2` 参数/路径错误（如未指定 `--root`、目录不存在）
