#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest.py -- project-journal 回归自测

在临时目录里完整跑一遍核心流程，任何一项失败都会让退出码非 0。
它是自我迭代的门禁：evolve-apply 会先跑本测试，不通过就不允许升版本。

用法： python scripts/selftest.py [--keep]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
CLI = os.path.join(HERE, "journal.py")
PY = sys.executable

RESULTS = []


def run(args, cwd=None, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([PY, CLI] + args, cwd=cwd, env=e,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def run_script(args, cwd=None, env=None):
    """运行 skill 目录下的任意脚本（用于 install-global 等）"""
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([PY] + args, cwd=cwd, env=e,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def check(name, cond, detail=""):
    ok = bool(cond)
    RESULTS.append((name, ok))
    print(("[PASS] " if ok else "[FAIL] ") + name + ("" if ok else "   <- " + str(detail)[:500]))


def w(path, text):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def r(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def main():
    keep = "--keep" in sys.argv
    tmp = tempfile.mkdtemp(prefix="pj-selftest-")
    try:
        proj = os.path.join(tmp, "proj")
        os.makedirs(os.path.join(proj, ".git"), exist_ok=True)
        root = os.path.join(proj, "project-journal")
        ledger = os.path.join(tmp, "ledger")
        env = {"PJ_LEDGER_DIR": ledger}
        bodies = os.path.join(tmp, "bodies")
        w(os.path.join(bodies, "d.md"), "- 背景：测试\n- 决定：用 A\n- 理由：便宜\n")
        w(os.path.join(bodies, "p.md"), "- 症状：测试失败\n- 根因：待查\n")
        w(os.path.join(bodies, "s.md"), "- 适用场景：同类问题\n- 步骤：\n  1. 先抓包\n")
        w(os.path.join(bodies, "secret.md"), "- 背景：临时密钥 sk-abcdefghijklmnopqrstuvwx\n- 联系：buyer@example.com\n")

        rc, out = run(["--version"])
        check("--version 输出版本号", rc == 0 and re.search(r"v[0-9]+\.[0-9]+\.[0-9]+", out), out)

        rc, out = run(["init", "--root", root, "--project", "Demo", "--stage", "S0",
                       "--hypothesis", "假设", "--success", "成功线", "--stop-loss", "止损线"])
        need = ["PROTOCOL.md", "CHARTER.md", "STATE.md", "INDEX.md", "NEXT-ACTIONS.md", "tracker.json",
                "metrics/metrics.csv", "metrics/ledger.csv", "metrics/experiments.csv", "sanitize.txt"]
        missing = [f for f in need if not os.path.isfile(os.path.join(root, f))]
        check("init 生成全部骨架文件", rc == 0 and not missing, missing or out[-400:])

        agents = os.path.join(proj, "AGENTS.md")
        check("init 注入会话锚点", "<!-- project-journal:begin -->" in r(agents), r(agents)[:200])
        t0 = json.loads(r(os.path.join(root, "tracker.json")))
        check("tracker 记录 skill_version", bool(t0.get("skill_version")), t0)

        run(["init", "--root", root, "--project", "Demo"])
        t1 = json.loads(r(os.path.join(root, "tracker.json")))
        check("重复 init 幂等（锚点不重复、created 不变）",
              r(agents).count("<!-- project-journal:begin -->") == 1 and t1.get("created") == t0.get("created"),
              r(agents).count("<!-- project-journal:begin -->"))

        # 约定：记录目录 = 项目根的子文件夹；锚点必须落在项目根，不能被上层仓库劫持
        hij = os.path.join(tmp, "hijack")
        os.makedirs(os.path.join(hij, ".git"), exist_ok=True)
        deep = os.path.join(hij, "sub", "proj")
        os.makedirs(deep, exist_ok=True)
        rc, out = run(["init", "--root", os.path.join(deep, "project-journal"), "--project", "Deep"])
        check("锚点落在项目根，不被上层仓库劫持（EV-0007）",
              os.path.isfile(os.path.join(deep, "AGENTS.md")) and not os.path.isfile(os.path.join(hij, "AGENTS.md")),
              out[-300:])

        cwdproj = os.path.join(tmp, "cwdproj")
        os.makedirs(cwdproj, exist_ok=True)
        rc, out = run(["init", "--project", "CwdDemo"], cwd=cwdproj)
        check("默认在项目根建 project-journal 子文件夹（EV-0007）",
              rc == 0 and os.path.isfile(os.path.join(cwdproj, "project-journal", "tracker.json")), out[-300:])

        rc, out = run(["add", "--root", root, "--type", "decision", "--title", "测试决策",
                       "--body-file", os.path.join(bodies, "d.md")])
        rec = os.path.join(root, "records", "decisions", "ADR-0001-record.md")
        check("add decision 生成档案与 ID", rc == 0 and os.path.isfile(rec) and "ADR-0001" in r(os.path.join(root, "journal"))[:0] + r(os.path.join(root, "journal")) or "ADR-0001" in "".join(r(os.path.join(root, "journal", f)) for f in os.listdir(os.path.join(root, "journal"))), out[-300:])

        run(["add", "--root", root, "--type", "problem", "--title", "测试问题",
             "--body-file", os.path.join(bodies, "p.md")])
        run(["add", "--root", root, "--type", "solution", "--title", "测试解法",
             "--body-file", os.path.join(bodies, "s.md"), "--link", "PB-0001"])
        rc, out = run(["update", "--root", root, "--id", "PB-0001", "--status", "solved",
                       "--append-file", os.path.join(bodies, "s.md")])
        pb = r(os.path.join(root, "records", "problems", "PB-0001-record.md"))
        check("update 修改档案状态并追加", rc == 0 and "status: solved" in pb and "## 更新" in pb, out[-300:])

        run(["metric", "--root", root, "--name", "MRR", "--value", "120", "--unit", "USD", "--source", "Stripe"])
        run(["ledger", "--root", root, "--kind", "income", "--amount", "99", "--channel", "Gumroad"])
        st = r(os.path.join(root, "STATE.md"))
        check("指标/收支进入 STATE 与 CSV",
              "MRR" in st and "净额 99.00" in st and "income" in r(os.path.join(root, "metrics", "ledger.csv")), st[:300])

        run(["stage", "--root", root, "--set", "S5", "--why", "拿到首单"])
        t2 = json.loads(r(os.path.join(root, "tracker.json")))
        check("stage 记录阶段轨迹", t2.get("stage") == "S5" and len(t2.get("stage_history", [])) == 2, t2.get("stage_history"))

        rc, out = run(["resume", "--root", root])
        check("resume 输出补液包", rc == 0 and "RESUME PACK" in out and "S5" in out, out[:300])

        rc, out = run(["lint", "--root", root])
        check("干净项目 lint 通过", rc == 0, out[-400:])
        check("干净项目 lint 不产生误报 [EVOLVE]（EV-0008）",
              "[EVOLVE]" not in out, out[-400:])

        run(["add", "--root", root, "--type", "decision", "--title", "含密钥的决策",
             "--body-file", os.path.join(bodies, "secret.md")])
        rc, out = run(["lint", "--root", root])
        check("lint 检出密钥/隐私并返回 1", rc == 1 and "疑似敏感信息" in out, out[-400:])

        rc, out = run(["publish", "--root", root])
        pub = os.path.join(root, "publish")
        day = sorted(os.listdir(pub))[-1] if os.path.isdir(pub) else ""
        pubdir = os.path.join(pub, day)
        files = ["INDEX.md", "PRODUCT-SHEET.md", "CASE-STUDY.md", "LESSONS.md", "PLAYBOOK.md",
                 "METRICS.csv", "LEDGER-SUMMARY.md", "_redaction-report.md"]
        missingf = [f for f in files if not os.path.isfile(os.path.join(pubdir, f))]
        cs = r(os.path.join(pubdir, "CASE-STUDY.md"))
        check("publish 生成 8 个资产文件", rc == 0 and not missingf, missingf or out[-300:])
        check("publish 脱敏（原文不泄露）",
              "sk-abcdefghij" not in cs and "buyer@example.com" not in cs and "[已脱敏" in cs,
              cs[-300:])
        check("publish 按 links 配对问题与解法", "对应解法 SL-0001" in cs, "配对失败")
        check("publish 含关键认知车道", "关键认知与讨论" in cs, cs[:200])

        rc, out = run(["closeout", "--root", root, "--outcome", "success", "--note", "测试"])
        t3 = json.loads(r(os.path.join(root, "tracker.json")))
        check("closeout 写入终局", rc == 0 and t3.get("outcome") == "success", t3.get("outcome"))

        rc, out = run(["evolve", "--category", "logic", "--severity", "medium",
                       "--title", "自测用的假问题", "--ledger-dir", ledger], env=env)
        rc2, out2 = run(["evolve", "--category", "logic", "--severity", "medium",
                         "--title", "自测用的假问题", "--ledger-dir", ledger], env=env)
        rc3, out3 = run(["evolve-list", "--ledger-dir", ledger, "--json"], env=env)
        try:
            ents = json.loads(out3)
        except Exception:
            ents = []
        check("evolve 记录并去重",
              rc == 0 and "EV-0001" in out and "跳过" in out2 and len(ents) == 1, out + out2)

        rc, out = run(["upgrade", "--root", root])
        check("upgrade 可重复执行", rc == 0, out[-400:])

        legacy = os.path.join(tmp, "legacy", "project-journal")
        run(["init", "--root", legacy, "--project", "Old"])
        tp = os.path.join(legacy, "tracker.json")
        tj = json.loads(r(tp))
        tj.pop("protocol_hash", None)
        tj["skill_version"] = "0.0.1"
        w(tp, json.dumps(tj, ensure_ascii=False, indent=2))
        pp = os.path.join(legacy, "PROTOCOL.md")
        w(pp, re.sub(r"契约版本：v[0-9.]+", "契约版本：v0.0.1", r(pp)))
        rc, out = run(["upgrade", "--root", legacy])
        rc2, out2 = run(["lint", "--root", legacy])
        check("upgrade 刷新旧版 PROTOCOL 并消除 EVOLVE 提示（EV-0006）",
              rc == 0 and "契约版本：v" in r(pp) and "v0.0.1" not in r(pp)
              and "[EVOLVE]" not in out2 and os.path.isfile(pp + ".bak-v0.0.1"),
              out[-200:] + " || " + out2[-300:])

        fh = os.path.join(tmp, "fakehome")
        os.makedirs(os.path.join(fh, ".claude"), exist_ok=True)
        os.makedirs(os.path.join(fh, ".codex"), exist_ok=True)
        ins = os.path.join(SKILL_DIR, "scripts", "install-global.py")
        rc, out = run_script([ins, "--home", fh])
        rc2, out2 = run_script([ins, "--home", fh])
        blk = r(os.path.join(fh, ".codex", "AGENTS.md")).count("project-journal:global:begin")
        linked = os.path.isfile(os.path.join(fh, ".claude", "skills", "project-journal", "SKILL.md"))
        check("install-global 注册到各工具且幂等（EV-0009）",
              rc == 0 and rc2 == 0 and blk == 1 and linked, out[-200:] + " || " + out2[-200:])
        codex_md = r(os.path.join(fh, ".codex", "AGENTS.md"))
        skill_md = r(os.path.join(SKILL_DIR, "SKILL.md"))
        lic_txt = r(os.path.join(SKILL_DIR, "LICENSE"))
        mf = json.loads(r(os.path.join(SKILL_DIR, "manifest.json")))
        spdx_md = r(os.path.join(SKILL_DIR, "README.md"))
        check("授权为非商用：SPDX 文本 + manifest + README 标识一致（EV-0012/0013）",
              "NonCommercial" in lic_txt and "MIT License" not in lic_txt
              and "Creative Commons Attribution-NonCommercial 4.0 International" in lic_txt
              and str(mf.get("license", "")).startswith("CC-BY-NC")
              and "SPDX-License-Identifier: CC-BY-NC-4.0" in spdx_md,
              "license=%s len=%d" % (mf.get("license"), len(lic_txt)))
        check("全局托管块无未转换占位符 @@（EV-0011）",
              "@@" not in codex_md, [l for l in codex_md.splitlines() if "@@" in l][:2])
        check("最短口令表同时进入全局块与 SKILL.md（EV-0010）",
              all(k in codex_md for k in ("跟踪项目", "记一下", "项目状态", "复盘", "结项", "出资产"))
              and "0.1 口令表" in skill_md,
              "缺失口令；codex_md 尾部=" + codex_md[-160:])

        broken = os.path.join(tmp, "broken", "project-journal")
        run(["init", "--root", broken, "--project", "Broken"])
        csvp = os.path.join(broken, "metrics", "metrics.csv")
        os.remove(csvp)
        os.makedirs(csvp, exist_ok=True)
        rc, out = run(["metric", "--root", broken, "--name", "x", "--value", "1"], env=env)
        led = json.loads(r(os.path.join(ledger, "ledger.json"))) if os.path.isfile(os.path.join(ledger, "ledger.json")) else {"entries": []}
        crash_logged = any("崩溃" in (e.get("title") or "") for e in led.get("entries", []))
        check("命令崩溃时自动记录到迭代台账（exit=3）", rc == 3 and crash_logged, "rc=%s logged=%s" % (rc, crash_logged))

        rc, out = run(["doctor"], env=env)
        check("doctor 自检通过", rc == 0, out[-400:])

        m = json.loads(r(os.path.join(SKILL_DIR, "manifest.json")))
        ch = r(os.path.join(SKILL_DIR, "CHANGELOG.md"))
        mtop = re.search(r"^##\s*\[([0-9]+\.[0-9]+\.[0-9]+)\]", ch, re.M)
        check("manifest 与 CHANGELOG 版本一致",
              bool(mtop) and mtop.group(1) == m.get("version"),
              "manifest=%s changelog=%s" % (m.get("version"), mtop.group(1) if mtop else None))
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print("保留临时目录：" + tmp)

    failed = [n for n, ok in RESULTS if not ok]
    print("")
    print("自测结果：%d/%d 通过" % (len(RESULTS) - len(failed), len(RESULTS)))
    if failed:
        print("失败项：")
        for n in failed:
            print("  - " + n)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
