#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install-global.py -- 把 project-journal 注册为全局技能，供所有 Agent 工具调用。

唯一真源：<skill 目录>（默认 ~/.agents/skills/project-journal，即 git 仓库本身）
做法：
  1) 向有"目录技能"约定的工具建立链接（软链 -> Windows junction -> 复制兜底）
  2) 向没有技能加载器的工具，在其全局指令文件里注入托管块（幂等）

用法：
  python install-global.py                 # 体检 + 安装（幂等，可反复跑）
  python install-global.py --check         # 只体检，不落盘
  python install-global.py --home <目录>    # 指定家目录（自测用）
  python install-global.py --copy          # 一律复制而不是链接
"""

import argparse
import os
import shutil
import subprocess
import sys

SKILL_NAME = "project-journal"
BEGIN = "<!-- project-journal:global:begin -->"
END = "<!-- project-journal:global:end -->"
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)

# (相对 home 的技能目录, 工具根目录, 说明)
DIR_SKILL_TARGETS = [
    (".claude/skills", ".claude", "Claude Code（个人技能）"),
    (".config/opencode/skills", ".config/opencode", "opencode"),
    (".cursor/skills", ".cursor", "Cursor"),
]

# (相对 home 的指令文件, 工具根目录, 说明)
INSTRUCTION_TARGETS = [
    (".claude/CLAUDE.md", ".claude", "Claude Code（全局指令）"),
    (".codex/AGENTS.md", ".codex", "Codex CLI（全局指令）"),
    (".gemini/GEMINI.md", ".gemini", "Gemini CLI（全局指令）"),
    (".config/opencode/AGENTS.md", ".config/opencode", "opencode（全局指令）"),
    (".codeium/windsurf/memories/global_rules.md", ".codeium/windsurf", "Windsurf（全局规则）"),
]


def say(msg=""):
    try:
        sys.stdout.write(str(msg) + "\n")
    except Exception:
        pass


def read_text(p):
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def write_text(p, s):
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def global_block(skill_dir):
    s = skill_dir.replace(os.sep, "/")
    return "\n".join([
        BEGIN,
        "## 全局技能：project-journal（项目全过程跟踪与经验资产化）",
        "",
        "**用户口令（词组即命令，只需记住这几个）**",
        "",
        "| 用户说 | 你做什么 |",
        "|---|---|",
        "| 跟踪项目 / 跟踪 <项目名> | 首次：init（记录目录 = `<项目根>/project-journal/`）；已存在：resume |",
        "| 记一下 / 记录一下 | 把本次会话的增量落盘（决策 / 问题 / 解法 / 认知 / 数字） |",
        "| 项目状态 | status 一行体检 |",
        "| 复盘 | review 生成周 / 月复盘骨架 |",
        "| 结项 | closeout 终局与成败判定 |",
        "| 出资产 | publish 生成脱敏资产包 |",
        "",
        "**也自动触发**：用户提到 项目跟踪、过程记录、项目日志、每日记录、决策记录、经验教训、",
        "变现追踪、build in public、案例资产、\u201c记录这个项目\u201d 时。",
        "",
        "**怎么执行**",
        "",
        "1. 读取 `%s/SKILL.md` 并遵循它的运行逻辑（这是唯一权威入口，不要凭记忆执行）。" % s,
        "2. 一个项目只 `init` 一次：记录目录固定为 `<项目根>/project-journal/`，",
        "   同时向项目根 `AGENTS.md` 注入会话锚点（此后该项目的每次会话都会自动续记）。",
        "3. 之后每次会话：**开工先** `python %s/scripts/journal.py resume --root \"<项目根>/project-journal\"`；" % s,
        "   **收工前**把决策 / 问题与解法 / 认知更新 / 真实数字落盘；最后 `index` + `lint`。",
        "4. 发现 skill 自身的问题（报错、文档不符、流程走不通）：`journal.py evolve` 记录，",
        "   闭环见 `%s/references/08-self-evolution.md`。" % s,
        "",
        "**铁律**：未记录 = 对后人而言没发生过；日记 append-only 不改写历史；",
        "禁止写入密钥与隐私；不编造数字；区分事实与判断。",
        END,
        "",
    ])


def inject(path, block, apply_changes):
    old = read_text(path)
    if BEGIN in old and END in old:
        import re
        new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), block.strip("\n"), old, flags=re.S)
        action = "更新"
    else:
        sep = "" if (not old or old.endswith("\n")) else "\n"
        new = old + sep + ("" if not old else "\n") + block
        action = "注入" if old else "新建"
    if apply_changes and new != old:
        write_text(path, new)
    return action


def link_dir(src, dst, use_copy, apply_changes):
    if os.path.exists(dst) or os.path.islink(dst):
        return "已存在（跳过）"
    if not apply_changes:
        return "待创建"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not use_copy:
        # 1) 原生符号链接（Windows 需开发者模式/管理员）
        try:
            os.symlink(src, dst, target_is_directory=True)
            return "符号链接"
        except (OSError, NotImplementedError, AttributeError):
            pass
        # 2) Windows junction：PowerShell 方式（免管理员，最可靠）
        if os.name == "nt":
            ps = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "New-Item -ItemType Junction -Path '%s' -Target '%s' | Out-Null" % (dst, src)],
                capture_output=True, text=True)
            if ps.returncode == 0 and os.path.exists(dst):
                return "junction"
            # 3) 退回 cmd 的 mklink（个别环境下 cmd 参数解析会失败，故放在后面并校验结果）
            r = subprocess.run(["cmd", "/c", "mklink", "/J", dst, src],
                               capture_output=True, text=True)
            if r.returncode == 0 and os.path.exists(dst):
                return "junction(cmd)"
    # 4) 兜底：复制。不随 git pull 更新，必须明确告警
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    return "复制 ⚠ 不会自动跟随 git pull，建议删掉后重跑或手工建 junction"


def main(argv=None):
    p = argparse.ArgumentParser(prog="install-global.py",
                                description="把 project-journal 注册为全局技能（所有 Agent 工具可用）")
    p.add_argument("--home", help="用户家目录（默认 ~，自测时可用临时目录）")
    p.add_argument("--check", action="store_true", help="只体检，不写入")
    p.add_argument("--copy", action="store_true", help="一律复制而不是链接")
    args = p.parse_args(argv)

    home = os.path.abspath(args.home) if args.home else os.path.expanduser("~")
    apply_changes = not args.check
    src = SKILL_DIR
    say("技能真源：%s" % src.replace(os.sep, "/"))
    say("目标家目录：%s" % home.replace(os.sep, "/"))
    say("模式：%s" % ("体检（不落盘）" if args.check else "安装"))
    say("")

    say("== 目录技能（有技能加载器的工具）==")
    linked = 0
    for rel, tool_root, desc in DIR_SKILL_TARGETS:
        if not os.path.isdir(os.path.join(home, tool_root)):
            say("  %-34s 跳过（未安装 %s）" % (desc, tool_root))
            continue
        dst = os.path.join(home, rel, SKILL_NAME)
        action = link_dir(src, dst, args.copy, apply_changes)
        if action not in ("已存在（跳过）",):
            linked += 1
        say("  %-34s %-24s %s" % (desc, action, dst.replace(os.sep, "/")))

    say("")
    say("== 全局指令文件（无技能加载器的工具靠它发现）==")
    injected = 0
    for rel, tool_root, desc in INSTRUCTION_TARGETS:
        if not os.path.isdir(os.path.join(home, tool_root)):
            say("  %-34s 跳过（未安装 %s）" % (desc, tool_root))
            continue
        path = os.path.join(home, rel)
        action = inject(path, global_block(src), apply_changes)
        injected += 1
        say("  %-34s %-6s %s" % (desc, action, path.replace(os.sep, "/")))

    say("")
    say("== 说明 ==")
    say("  DSH              原生发现 ~/.agents/skills/*/SKILL.md，无需额外注册（避免重复条目）")
    say("  任何支持 shell 的工具  直接用 python <skill>/scripts/journal.py ... 即可，脚本零依赖")
    say("  升级            在真源目录 git pull；用复制方式安装的需重跑本脚本")
    say("")
    if args.check:
        say("体检完成：将创建 %d 个技能链接、写入 %d 个全局指令文件。去掉 --check 即执行。" % (linked, injected))
    else:
        say("完成：技能链接 %d 处、全局指令文件 %d 处（幂等，可重复执行）。" % (linked, injected))
        say("下一步：在任意 Agent 工具里说 \u201c给这个项目开启过程跟踪\u201d 试试。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
