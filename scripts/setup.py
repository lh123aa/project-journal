#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup.py -- project-journal 一键安装：技能注册 + Obsidian + 起始 vault + 全局配置。

一条命令完成：
  python scripts/setup.py --yes

做什么：
  1) 把 project-journal 注册为全局技能（复用 install-global.py）
  2) 未安装 Obsidian 时，从官方 GitHub 下载并静默安装（D 盘优先）
  3) 创建起始 vault（D:\\ProjectJournal-Vault，D 不可用时回退 Documents）
  4) 写 ~/.project-journal/config.json，并把所有路径/版本/状态记下来
  5) 打印“装完即可用”的下一步；可选 --open 直接打开 Obsidian

可选：
  --project <项目根>   同时接入一个真实项目（默认原地 <项目根>/project-journal）
  --vault <目录>       指定 vault（与 --project 同用时为集中式 vault）
  --no-obsidian        跳过 Obsidian（仍安装技能与 vault）
  --check              只体检，不写任何文件
  --yes                明确授权下载并静默安装 Obsidian
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
JOURNAL = os.path.join(HERE, "journal.py")
INSTALL_GLOBAL = os.path.join(HERE, "install-global.py")
INSTALL_OBSIDIAN = os.path.join(HERE, "install-obsidian.py")
SKILL_NAME = "project-journal"
JSON_MODE = False


def say(msg=""):
    try:
        f = sys.stderr if JSON_MODE else sys.stdout
        f.write(str(msg) + "\n")
        f.flush()
    except Exception:
        pass


def warn(msg):
    say("[WARN] " + str(msg))


def fail(msg):
    say("[FAIL] " + str(msg))


def read_text(p):
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def write_text(p, s):
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)
    os.replace(tmp, p)


def norm(p):
    return os.path.normcase(os.path.abspath(os.path.expanduser(p))) if p else ""


def load_journal():
    spec = importlib.util.spec_from_file_location("pj_journal_setup", JOURNAL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def skill_version():
    try:
        m = json.loads(read_text(os.path.join(SKILL_DIR, "manifest.json")))
        return str(m.get("version") or "0.0.0")
    except Exception:
        return "0.0.0"


def env_for(home):
    env = os.environ.copy()
    env["PJ_OBSIDIAN_STATE"] = os.path.join(home, ".project-journal", "obsidian.json")
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run_stream(cmd, home):
    env = env_for(home)
    try:
        if JSON_MODE:
            r = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding="utf-8", errors="replace")
            if r.stdout:
                sys.stderr.write(r.stdout)
            if r.stderr:
                sys.stderr.write(r.stderr)
            return r.returncode
        return subprocess.run(cmd, env=env).returncode
    except Exception as exc:
        fail("执行失败：%s（%s）" % (" ".join(cmd), exc))
        return 1


def detect_obsidian(home):
    cmd = [sys.executable, INSTALL_OBSIDIAN, "--check", "--json"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env_for(home), timeout=60)
        data = json.loads((r.stdout or "").strip() or "{}")
        return data.get("installed") or {"installed": False}
    except Exception:
        return {"installed": False, "path": "", "version": "", "source": "error"}


def install_obsidian(home, args):
    cmd = [sys.executable, INSTALL_OBSIDIAN, "--yes"]
    if args.obsidian_dir:
        cmd += ["--install-dir", args.obsidian_dir]
    if args.no_relocate:
        cmd.append("--no-relocate")
    say("[2/4] 安装 Obsidian（官方下载 + 验签 + 静默安装，可能需要几分钟）...")
    rc = run_stream(cmd, home)
    got = detect_obsidian(home)
    if rc != 0 or not got.get("installed"):
        warn("Obsidian 未完成安装；技能本身仍可用，稍后可重跑本脚本")
    return got


def default_vault(home, explicit_home=False):
    if explicit_home:
        return os.path.join(home, "Documents", "ProjectJournal-Vault")
    if os.name == "nt":
        try:
            import ctypes
            free = shutil.disk_usage("D:\\").free
            fixed = int(ctypes.windll.kernel32.GetDriveTypeW("D:\\")) == 3
            if fixed and free > 2 * 1024 ** 3:
                # 写权限探测
                os.makedirs("D:\\", exist_ok=True)
                probe = os.path.join("D:\\", ".pj-vault-probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                os.unlink(probe)
                return "D:\\ProjectJournal-Vault"
        except Exception:
            pass
        return os.path.join(home, "Documents", "ProjectJournal-Vault")
    return os.path.join(home, "Documents", "ProjectJournal-Vault")


def slugify(s):
    s = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", (s or "").strip(), flags=re.UNICODE)
    s = s.strip("-._")[:60]
    return s or "project"


def starter_home(vault, skill_version, obsidian, projects=None):
    obs = "未安装（可选）"
    if obsidian.get("installed"):
        obs = "%s（%s）" % (obsidian.get("path"), obsidian.get("version") or "版本未知")
    lines = [
        "---",
        'title: "ProjectJournal Vault"',
        "generated: true",
        "tags:",
        "  - project-journal",
        "  - home",
        "---",
        "",
        "# ProjectJournal Vault",
        "",
        "> 这是 ProjectJournal 的起始 vault。记录真源仍在各项目的 `project-journal/` 目录；",
        "> 本 vault 只做入口和跨项目总览，不复制、不改写任何日记或档案。",
        "",
        "## 环境",
        "",
        "| 项目 | 值 |",
        "|---|---|",
        "| 技能版本 | %s |" % skill_version,
        "| Obsidian | %s |" % obs.replace("|", "\\|"),
        "| 技能目录 | `%s` |" % SKILL_DIR.replace(os.sep, "/"),
        "| Vault | `%s` |" % vault.replace(os.sep, "/"),
        "",
        "## 从这里开始",
        "",
        "1. 在任意项目里对 Agent 说「跟踪项目」。",
        "2. 或在项目根运行（把 `<项目根>` 换成真实路径）：",
        "",
        "```powershell",
        'python "%s" init --root "<项目根>/project-journal" --project "<项目名>" --project-root "<项目根>"' % JOURNAL.replace(os.sep, "/"),
        'python "%s" obsidian --root "<项目根>/project-journal" --open' % JOURNAL.replace(os.sep, "/"),
        "```",
        "",
        "3. 用 Obsidian「打开文件夹作为仓库」选择本目录，或直接打开项目的 `project-journal/` 目录。",
        "",
        "## 已接入项目",
        "",
    ]
    if projects:
        for name, path in projects:
            rel = os.path.relpath(path, vault).replace(os.sep, "/").replace(" ", "%20")
            lines.append("- [%s](%s/HOME.md)" % (name, rel))
    else:
        lines.append("_尚无。集中式 vault 的项目会出现在这里；"
                     "默认原地记录请直接打开项目的 `project-journal/`。_")
    lines += [
        "",
        "## 文档",
        "",
        "- [本 vault 说明](README.md)",
        "- 技能入口：`%s`" % os.path.join(SKILL_DIR, "SKILL.md").replace(os.sep, "/"),
        "- 命令手册：`%s`" % os.path.join(SKILL_DIR, "USAGE.md").replace(os.sep, "/"),
        "",
        "> 本页由 `setup.py` 生成；可手工修改，重跑 setup 会覆盖。",
        "",
    ]
    return "\n".join(lines)


def starter_readme(vault):
    return "\n".join([
        "# ProjectJournal Vault",
        "",
        "这是 ProjectJournal 的起始 Obsidian vault。",
        "",
        "- 项目记录真源：各项目根目录下的 `project-journal/`。",
        "- 本 vault 默认是入口与总览，不复制数据，避免双真源。",
        "- 项目可以原地记录，也可以集中到本 vault 的子目录（`--project` + `--vault`）。",
        "- 生成/刷新项目视图：",
        "",
        "```powershell",
        'python "%s" obsidian --root "<项目根>/project-journal"' % JOURNAL.replace(os.sep, "/"),
        "```",
        "",
        "- 只读检查视图是否过期：加 `--check` 会返回 1。",
        "- 全部内容都是普通 Markdown；不用 Obsidian 也能用 GitHub / VS Code 打开。",
        "",
    ])


def write_vault_start(vault, version, obsidian, projects=None):
    made = []
    h = os.path.join(vault, "HOME.md")
    content = starter_home(vault, version, obsidian, projects)
    if read_text(h) != content:
        write_text(h, content)
        made.append("HOME.md")
    r = os.path.join(vault, "README.md")
    if not os.path.isfile(r):
        write_text(r, starter_readme(vault))
        made.append("README.md")
    try:
        j = load_journal()
        made_cfg, skipped = j._write_obsidian_config(
            vault, force=False, obsidian_version=(obsidian or {}).get("version") or "")
        made += made_cfg
    except Exception as exc:
        warn("写 Obsidian 配置失败：%s" % exc)
    return made


def project_paths(project, vault_arg):
    """返回 (record_dir, project_root, name, mode, vault_root, warning)"""
    p = os.path.abspath(os.path.expanduser(project))
    if not os.path.isdir(p):
        raise RuntimeError("项目目录不存在：%s" % p)
    name = os.path.basename(p.rstrip("\\/")) or "project"
    # 传入的已经是记录目录
    if os.path.isfile(os.path.join(p, "CHARTER.md")) and os.path.isfile(os.path.join(p, "STATE.md")):
        try:
            t = json.loads(read_text(os.path.join(p, "tracker.json")))
            name = t.get("project") or name
        except Exception:
            pass
        return p, "", name, "record", p, ""
    # 项目根下已有记录目录
    existing = os.path.join(p, "project-journal")
    if os.path.isfile(os.path.join(existing, "CHARTER.md")):
        return existing, p, name, "in-place", existing, ""
    # 集中式 vault
    if vault_arg:
        root = os.path.abspath(os.path.expanduser(vault_arg))
        rec = os.path.join(root, slugify(name))
        return rec, p, name, "central", root, ""
    # 默认原地
    return existing, p, name, "in-place", existing, ""


def init_project(record_dir, project_root, name, home):
    os.makedirs(os.path.dirname(record_dir) or ".", exist_ok=True)
    if not os.path.isfile(os.path.join(record_dir, "CHARTER.md")):
        cmd = [sys.executable, JOURNAL, "init", "--root", record_dir, "--project", name]
        if project_root:
            cmd += ["--project-root", project_root]
        say("     初始化项目记录：%s" % record_dir.replace(os.sep, "/"))
        rc = run_stream(cmd, home)
        if rc != 0:
            raise RuntimeError("journal.py init 失败（退出码 %s）" % rc)
    else:
        say("     项目记录已存在，跳过 init：%s" % record_dir.replace(os.sep, "/"))
    say("     生成 Obsidian 视图 ...")
    rc = run_stream([sys.executable, JOURNAL, "obsidian", "--root", record_dir], home)
    if rc != 0:
        raise RuntimeError("journal.py obsidian 失败（退出码 %s）" % rc)
    return record_dir


def write_global_config(home, vault, vault_mode, record_dir, project_root,
                        obsidian, version, extra=None):
    p = os.path.join(home, ".project-journal", "config.json")
    old = {}
    try:
        old = json.loads(read_text(p)) or {}
    except Exception:
        old = {}
    obs_state = {}
    try:
        obs_state = json.loads(read_text(os.path.join(home, ".project-journal", "obsidian.json"))) or {}
    except Exception:
        obs_state = {}
    cfg = dict(old)
    cfg.update({
        "schema": 1,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "skill": {
            "name": SKILL_NAME,
            "version": version,
            "dir": SKILL_DIR,
            "python": sys.executable,
            "journal": JOURNAL,
        },
        "obsidian": {
            "installed": bool(obsidian.get("installed")),
            "path": obsidian.get("path") or obs_state.get("path") or "",
            "version": obsidian.get("version") or obs_state.get("version") or "",
            "install_dir": obsidian.get("install_dir") or obs_state.get("install_dir") or "",
            "method": obs_state.get("method") or "",
            "state": os.path.join(home, ".project-journal", "obsidian.json"),
        },
        "vault": {
            "path": vault,
            "mode": vault_mode,
            "record_dir": record_dir,
            "project_root": project_root,
        },
    })
    if extra:
        cfg.update(extra)
    write_text(p, json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    return p


def check_all(home, vault, vault_mode, record_dir, args):
    checks = []

    def add(name, ok, detail="", required=True):
        checks.append({"name": name, "ok": bool(ok), "detail": detail, "required": required})

    add("Python >= 3.8", sys.version_info >= (3, 8), sys.version.split()[0])
    for fn in ("SKILL.md", "manifest.json", "scripts/journal.py", "scripts/install-obsidian.py",
               "scripts/install-global.py", "scripts/setup.py"):
        p = os.path.join(SKILL_DIR, fn)
        add("文件 " + fn, os.path.isfile(p), p)
    add("vault 目录", os.path.isdir(vault), vault)
    add("vault HOME.md", os.path.isfile(os.path.join(vault, "HOME.md")),
        os.path.join(vault, "HOME.md"))
    add("vault .obsidian/app.json", os.path.isfile(os.path.join(vault, ".obsidian", "app.json")),
        os.path.join(vault, ".obsidian", "app.json"))
    cfg = os.path.join(home, ".project-journal", "config.json")
    add("全局配置", os.path.isfile(cfg), cfg)
    if record_dir and record_dir != vault:
        add("项目记录目录", os.path.isdir(record_dir), record_dir)
        add("项目 HOME.md", os.path.isfile(os.path.join(record_dir, "HOME.md")),
            os.path.join(record_dir, "HOME.md"))
    if not args.no_obsidian:
        obs = detect_obsidian(home)
        add("Obsidian（可选）", obs.get("installed"), obs.get("path") or "未安装", required=False)
    say("== 体检 ==")
    for c in checks:
        tag = "OK  " if c["ok"] else ("FAIL" if c["required"] else "WARN")
        say("  [%s] %-24s %s" % (tag, c["name"], c["detail"]))
    bad = [c for c in checks if not c["ok"] and c["required"]]
    say("")
    say("结果：%s" % ("通过" if not bad else "不通过（%d 项）" % len(bad)))
    return (0 if not bad else 1), checks


def main(argv=None):
    global JSON_MODE
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    p = argparse.ArgumentParser(prog="setup.py",
                                description="project-journal 一键安装（技能 + Obsidian + vault + 全局配置）")
    p.add_argument("--yes", action="store_true", help="明确授权下载并静默安装 Obsidian")
    p.add_argument("--no-obsidian", dest="no_obsidian", action="store_true", help="跳过 Obsidian")
    p.add_argument("--require-obsidian", dest="require_obsidian", action="store_true",
                   help="Obsidian 未安装则安装失败")
    p.add_argument("--check", action="store_true", help="只体检，不写任何文件")
    p.add_argument("--home", help="用户家目录（默认 ~；自测时可指定临时目录）")
    p.add_argument("--vault", help="vault 目录（默认 D:\\ProjectJournal-Vault，失败回退 Documents）")
    p.add_argument("--project", help="同时接入一个真实项目目录")
    p.add_argument("--obsidian-dir", dest="obsidian_dir", help="Obsidian 安装目录")
    p.add_argument("--no-relocate", dest="no_relocate", action="store_true",
                   help="安装器忽略 /D 时不移动到目标盘")
    p.add_argument("--copy", action="store_true", help="技能注册使用复制而不是链接")
    p.add_argument("--open", action="store_true", help="安装完成后用 Obsidian 打开 vault")
    p.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = p.parse_args(argv)
    JSON_MODE = args.json

    explicit_home = bool(args.home)
    home = os.path.abspath(args.home) if args.home else os.path.expanduser("~")
    version = skill_version()

    if args.no_obsidian and args.require_obsidian:
        fail("--no-obsidian 与 --require-obsidian 不能同时使用")
        return 2

    # 先算路径（--check 也要知道检查哪里）
    vault = os.path.abspath(os.path.expanduser(args.vault)) if args.vault else default_vault(home, explicit_home)
    record_dir, project_root, project_name, mode, vault_root, note = "", "", "", "starter", vault, ""
    if args.project:
        try:
            record_dir, project_root, project_name, mode, vault_root, note = project_paths(args.project, args.vault)
        except Exception as exc:
            fail(str(exc))
            return 2
        if note:
            warn(note)
        if mode in ("record", "in-place"):
            vault = record_dir
            vault_root = record_dir
        else:
            vault = vault_root
    if args.vault and not args.project:
        vault = os.path.abspath(os.path.expanduser(args.vault))
        vault_root = vault
    if mode == "starter":
        record_dir = ""

    if args.check:
        rc, checks = check_all(home, vault, mode, record_dir, args)
        if args.json:
            print(json.dumps({"ok": rc == 0, "vault": vault, "record_dir": record_dir,
                              "checks": checks}, ensure_ascii=False, indent=2))
        return rc

    say("project-journal 一键安装 v%s" % version)
    say("技能真源：%s" % SKILL_DIR.replace(os.sep, "/"))
    say("用户家目录：%s" % home.replace(os.sep, "/"))
    say("")

    # 1) 注册技能
    say("[1/4] 注册全局技能 ...")
    cmd = [sys.executable, INSTALL_GLOBAL, "--home", home]
    if args.copy:
        cmd.append("--copy")
    rc = run_stream(cmd, home)
    if rc != 0:
        warn("技能注册脚本返回 %s；继续完成其余配置" % rc)

    # 2) Obsidian
    obs = detect_obsidian(home)
    if args.no_obsidian:
        say("[2/4] 跳过 Obsidian（--no-obsidian）")
        obs = {"installed": False, "path": "", "version": "", "skipped": True}
    elif obs.get("installed"):
        say("[2/4] Obsidian 已安装：%s（%s）" % (obs.get("path"), obs.get("version") or "版本未知"))
        try:
            if obs.get("version") and tuple(
                    map(int, str(obs["version"]).split(".")[:3])) < (1, 8, 0):
                warn("Obsidian 版本低于 1.8.0；视图可能不完整，建议升级（不影响记录）")
        except Exception:
            pass
    elif args.yes:
        obs = install_obsidian(home, args)
    else:
        say("[2/4] 未检测到 Obsidian")
        cmd_txt = 'python "%s" --yes' % INSTALL_OBSIDIAN.replace(os.sep, "/")
        say("     将下载并静默安装到 D 盘（若可用）。确认请加 --yes，或先运行：")
        say("     " + cmd_txt)
        if sys.stdin.isatty() and not JSON_MODE:
            try:
                ans = input("     现在安装？[y/N] ").strip().lower()
            except EOFError:
                ans = ""
            if ans in ("y", "yes"):
                obs = install_obsidian(home, args)
    if args.require_obsidian and not obs.get("installed"):
        fail("Obsidian 未安装（--require-obsidian）")
        return 3

    # 3) vault / 项目
    say("[3/4] 准备 vault ...")
    projects = []
    if args.project:
        try:
            record_dir = init_project(record_dir, project_root, project_name, home)
        except Exception as exc:
            fail("项目初始化失败：%s" % exc)
            return 4
        if mode == "central":
            projects.append((project_name, record_dir))
            made = write_vault_start(vault, version, obs, projects)
            say("     起始 vault：%s" % vault.replace(os.sep, "/"))
        else:
            made = []
            say("     项目 vault：%s" % record_dir.replace(os.sep, "/"))
        if made:
            say("     写入：%s" % " . ".join(made))
    else:
        made = write_vault_start(vault, version, obs, projects)
        say("     起始 vault：%s" % vault.replace(os.sep, "/"))
        if made:
            say("     写入：%s" % " . ".join(made))

    # 4) 全局配置
    say("[4/4] 写全局配置 ...")
    cfgp = write_global_config(home, vault, mode, record_dir, project_root, obs, version)
    say("     %s" % cfgp.replace(os.sep, "/"))

    say("")
    say("✅ 安装完成，可以开始使用")
    say("   技能：v%s @ %s" % (version, SKILL_DIR.replace(os.sep, "/")))
    if obs.get("installed"):
        say("   Obsidian：%s（%s）" % (obs.get("path"), obs.get("version") or "版本未知"))
    else:
        say("   Obsidian：未安装（可选；不影响技能使用）")
    say("   Vault：%s" % vault.replace(os.sep, "/"))
    if record_dir and record_dir != vault:
        say("   项目记录：%s" % record_dir.replace(os.sep, "/"))
    say("")
    say("下一步：")
    say("  1. 在任意项目里说「跟踪项目」")
    say("  2. 或运行：python \"%s\" init --root \"<项目根>/project-journal\" --project \"<项目名>\" --project-root \"<项目根>\""
        % JOURNAL.replace(os.sep, "/"))
    say("  3. 生成视图：python \"%s\" obsidian --root \"<项目根>/project-journal\" --open"
        % JOURNAL.replace(os.sep, "/"))
    if not obs.get("installed"):
        say("  4. 安装 Obsidian：python \"%s\" --yes" % INSTALL_OBSIDIAN.replace(os.sep, "/"))
        say("     然后重跑本脚本即可自动配置：python \"%s\" --yes" % os.path.abspath(__file__).replace(os.sep, "/"))
    elif args.open:
        exe = obs.get("path") or ""
        if exe:
            try:
                subprocess.Popen([exe, vault])
                say("  已用 Obsidian 打开：%s" % vault.replace(os.sep, "/"))
            except Exception as exc:
                warn("打开 Obsidian 失败：%s" % exc)
    if args.json:
        print(json.dumps({"ok": True, "version": version, "vault": vault,
                          "record_dir": record_dir, "obsidian": obs,
                          "config": cfgp}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
