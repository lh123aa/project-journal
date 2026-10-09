# CHANGELOG . project-journal

> 版本号遵循语义化：`patch` 修错 / `minor` 加能力或扩展格式（向后兼容）/ `major` 破坏兼容。
> 每一项修复都对应 `evolution/LEDGER.md` 里的一个 EV 编号；任何修复都必须通过 `scripts/selftest.py` 才能发布。

<!-- CHANGELOG:INSERT -->

## [1.3.2] - 2026-10-09
- 修复 README 两处文档缺陷：SPDX 标识改为规范围栏代码块；版本段不再硬编码版本号与缺陷统计（改为指向 manifest/CHANGELOG/LEDGER 单一来源），并新增回归断言禁止 README 再出现硬编码版本号（第 31 项）（EV-0015）
- 类别 / 严重度：docs / low
- 台账：evolution/LEDGER.md 的 EV-0015

## [1.3.1] - 2026-10-09
- LICENSE 换为 SPDX 规范全文并写明 SPDX-License-Identifier: CC-BY-NC-4.0；README 诚实说明 GitHub 徽章不支持 CC BY-NC（模板库 404，任何文本都识别不了，非配置问题），授权以 LICENSE 全文为准；回归断言升级为 SPDX 标题 + manifest + README 标识三者一致（EV-0013）
- 类别 / 严重度：usability / medium
- 台账：evolution/LEDGER.md 的 EV-0013

## [1.3.0] - 2026-10-09
- 授权从 MIT 改为 CC BY-NC 4.0（禁止商用）：LICENSE 换为官方 legalcode 全文，README 顶部与授权段写明允许/禁止清单与商用需另行授权并声明历史版本（<=v1.2.2）仍为 MIT、授权不可撤回；manifest 增加 license 字段；新增回归用例（第 30 项）断言授权为非商用且 LICENSE 与 manifest 一致（EV-0012）
- 类别 / 严重度：docs / high
- 台账：evolution/LEDGER.md 的 EV-0012

## [1.2.2] - 2026-10-09
- 修复全局托管块泄漏 @@ 占位符：install-global.py 的占位符转换函数此前被写坏成恒等操作，导致运行期 @@ 转反引号失效；删除该恒等转换、表格行改用真实反引号，并新增回归断言（注入结果不得出现 @@，第 29 项）（EV-0011）
- 类别 / 严重度：bug / medium
- 台账：evolution/LEDGER.md 的 EV-0011

## [1.2.1] - 2026-10-09
- 新增最短口令表：跟踪项目 / 记一下 / 项目状态 / 复盘 / 结项 / 出资产（词组即命令，覆盖全生命周期），并同步写入 SKILL.md（含 frontmatter 触发词）、references/00-protocol.md（随 upgrade 分发到各项目）与 install-global.py 的全局托管块（所有工具全局指令首屏即为口令表）；补第 28 项回归用例防止口令表丢失（EV-0010）
- 类别 / 严重度：usability / medium
- 台账：evolution/LEDGER.md 的 EV-0010

## [1.2.0] - 2026-10-09
- 新增 scripts/install-global.py：以 ~/.agents/skills/project-journal 为唯一真源，一键把 skill 注册为全局技能——Claude Code/opencode/Cursor 建 junction 链接（PowerShell 优先，cmd mklink 兜底且校验结果），Codex/Gemini/Windsurf 注入幂等托管块，DSH 原生发现不重复注册；链接指向 git 仓库，git pull 即可全工具升级。修复 cmd.exe 参数解析偶发失败导致静默退化为复制的问题（现明确告警）。新增 USAGE.md 完整手册与第 27 项回归用例（EV-0009）
- 类别 / 严重度：feature / high
- 台账：evolution/LEDGER.md 的 EV-0009

## [1.1.3] - 2026-10-09
- 修正 lint 中丢失反斜杠的日记文件名正则（把合规文件误报为结构性问题），并规范一处未转义的点号；selftest 新增断言：干净项目的 lint 输出不得包含 [EVOLVE]（含误报即失败）（EV-0008）
- 类别 / 严重度：bug / medium
- 台账：evolution/LEDGER.md 的 EV-0008

## [1.1.2] - 2026-10-09
- 记录目录约定改为项目根下的子文件夹 <项目根>/project-journal（去掉冗余 slug 层），SKILL.md/references 同步；guess_project_root 改为约定优先，不再向上越过项目去命中上级 .git，避免把会话锚点注入到无关仓库；新增 2 项回归用例（锚点不被劫持、cwd 默认位置）（EV-0007）
- 类别 / 严重度：logic / medium
- 台账：evolution/LEDGER.md 的 EV-0007

## [1.1.1] - 2026-10-09
- upgrade 改为先备份再刷新工具生成的 PROTOCOL.md（新增 --keep-protocol 逃生口），消除旧项目永远无法清掉的 [EVOLVE] 提示；补充回归用例（第 23 项）（EV-0006）
- 类别 / 严重度：logic / medium
- 台账：evolution/LEDGER.md 的 EV-0006

## [1.1.0] - 2026-10-09
- 新增自我迭代子系统：evolve/evolve-list/evolve-apply/doctor/upgrade 五个命令、崩溃自动记录、lint 结构性问题检测（--auto-evolve）、22 项回归自测门禁 selftest.py、CHANGELOG 与语义化版本治理、PROTOCOL 契约版本与安全迁移（upgrade 不动历史记录），并补 references/08-self-evolution.md 与 SKILL.md 第 8 节（EV-0005）
- 类别 / 严重度：feature / high
- 台账：evolution/LEDGER.md 的 EV-0005

## [1.0.1] - 2026-10-09
- 案例研究新增「关键认知与讨论」车道，有价值讨论（insight）正文进入资产包（EV-0001）
- 问题↔解法改为按 links 双向配对，解法不再漏进案例研究（EV-0002）
- 重复 init 不再误报「补全 CHARTER」，改为提示已有目录的开工程序（EV-0003）
- NEXT-ACTIONS 模板去掉空 checkbox，STATE 不再出现空条目（EV-0004）

## [1.0.0] - 2026-10-09
- 首个版本：init / anchor / status / resume / add / update / metric / ledger / stage / index /
  lint / review / closeout / publish / vault-index
- 三层结构（append-only 日记 / 主题档案 / 数据表）+ 会话锚点 + 项目契约 PROTOCOL.md
- MUST-RECORD 触发器、成功线与止损线预置、阶段机、脱敏可销售资产包
