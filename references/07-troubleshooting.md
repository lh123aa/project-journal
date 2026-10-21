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
- `1` lint 失败（有 error，或 `--strict` 下有 warn）；`obsidian --check` 表示视图过期；`install-obsidian.py --check` 表示未安装；`selftest.py` 表示有用例失败
- `2` 参数/路径错误（如未指定 `--root`、目录不存在）；`setup.py` 也用它表示参数冲突/项目路径无效
- `3` `setup.py --require-obsidian` 但 Obsidian 未安装/安装失败
- `4` `setup.py` 项目初始化失败

## 12. Obsidian 可视化与一键安装

### 12.1 一键安装后先跑自检

```bash
python "<SKILL>/scripts/setup.py" --check
python "<SKILL>/scripts/install-obsidian.py" --check
```

`setup.py --check` 检查：全局配置、vault 的 `HOME.md`、`.obsidian` 配置、项目记录目录、Obsidian 路径/版本。它**不写入**任何文件；`--json` 输出可机器解析（日志走 stderr）。

### 12.2 检测不到已安装的 Obsidian

- 先跑 `python scripts/install-obsidian.py --check --json` 看 `source`：
  - `state`：来自 `~/.project-journal/obsidian.json`
  - `registry:...`：来自 Windows 卸载注册表
  - `candidate:...`：来自常见安装路径
- 常见路径包括 `%LOCALAPPDATA%\Programs\Obsidian`、`Program Files`、`Program Files (x86)`、`D:\Obsidian`、`D:\Program Files (x86)\Obsidian` 等
- 如果装在自定义位置：`python scripts/install-obsidian.py --install-dir "<目录>" --yes`，或手动打开一次 Obsidian 后重跑 `--check`
- 状态文件损坏：删除 `~/.project-journal/obsidian.json` 后重跑 `--check`，会回退到注册表/路径检测

### 12.3 下载或验签失败

- 安装器从 Obsidian 官方 GitHub Release 下载，并用 Windows Authenticode 验签；网络/代理失败时会中止，不会安装未验签文件
- 官方签名主体是 **`CN=Dynalist Inc`**（Obsidian 母公司），安装器同时接受含 `Obsidian` 或 `Dynalist` 的证书；只认 `Obsidian` 会误拒正版（EV-0023）
- 技能本身仍可用（除非 `setup.py --require-obsidian`）；可稍后重跑：
  ```bash
  python scripts/install-obsidian.py --yes
  ```
- 公司网络拦截 GitHub 时，先手动从 [obsidian.md/download](https://obsidian.md/download) 安装，再跑 `setup.py --yes`（会复用已有安装）
- `--no-verify` 只建议在你已手动核对安装包来源/哈希时使用；不要用它绕过公司安全策略

### 12.4 安装到了默认盘，没进 D 盘

- Obsidian NSIS 安装器在目标路径含空格时可能忽略 `/D=`；安装器会尝试把默认安装复制到 `D:\Obsidian` 并在原位置建 junction
- 若复制/junction 失败，会保留默认盘安装并告警；这是有意的安全回退，不会留下半安装状态
- 查看实际位置：`python scripts/install-obsidian.py --check --json`
- 指定目录重试：`python scripts/install-obsidian.py --yes --install-dir "D:\Obsidian"`；不允许搬迁时加 `--no-relocate`
- D 盘空间不足（< 2 GB）或不可写时，`setup.py` 的 vault 会回退到 `~/Documents/ProjectJournal-Vault`

### 12.5 视图打不开 / 链接失效 / 过期

- **必须把记录目录本身作为 vault 打开**，不是它的父目录；`HOME.md` 在记录根，五个视图在 `_views/`
- 重新生成：`journal.py obsidian --root <记录根>`；只检查：`--check`（过期返回 1）
- 不要手改 `HOME.md` / `_views/`，下次生成会覆盖；要改内容改源日记/档案
- 视图用相对 Markdown 链接，中文和空格路径已做转义；GitHub / VS Code 也能读
- 打开后看不到 `.obsidian` 配置：确认记录根下有 `.obsidian/app.json`；没有就重跑 `obsidian`（不会覆盖已有配置，除非 `--force`）

### 12.6 Obsidian 1.8 与 1.9+ 的配置差异

- 最低支持 **1.8.0**；1.8.x 的 `core-plugins.json` 是数组，1.9+ 是对象
- 生成器会按检测到的版本选择格式；已存在的旧格式会自动迁移（对象↔数组），并在输出里标注
- 我们的视图只用原生 Markdown / Mermaid / Properties / Canvas，**不依赖 Bases**；1.8.x 足够
- 版本检测不到时按 1.9+ 对象格式写；如果界面异常，升级 Obsidian 或删掉 `.obsidian/core-plugins.json` 让 Obsidian 重建默认值

### 12.7 已有 Obsidian 会被覆盖吗

- 不会。检测到 1.8+ 直接复用，不下载、不移动、不改安装目录；`setup.py` 只写 `~/.project-journal/obsidian.json` 和 vault 配置
- 只有显式 `install-obsidian.py --force` 才会重装
- 升级 Obsidian 用其自带更新器或官方安装包；本 skill 不主动升级已有安装
