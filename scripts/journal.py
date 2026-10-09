#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
journal.py -- project-journal 项目全过程跟踪与经验资产化引擎

仅使用 Python 标准库，无第三方依赖。
所有子命令以 --root <记录根目录> 为基准。

设计原则：
  1) 脚本管"结构与索引"（确定性的机械工作），人/Agent 管"内容与判断"。
  2) 日记 append-only，永不改写；档案一主题一文件；指标/收支机器可算。
  3) 所有写盘使用 UTF-8；--body-file 传正文，避免命令行中文转义问题。
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import traceback

SCHEMA = 1
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)

TYPE_CODE = {
    "task": "T", "decision": "D", "problem": "P", "solution": "S",
    "insight": "I", "experiment": "X", "metric": "M", "risk": "R",
    "lesson": "L", "revenue": "$", "cost": "C", "milestone": "MS",
    "question": "Q",
}
TYPE_CN = {
    "task": "任务", "decision": "决策", "problem": "问题", "solution": "解法",
    "insight": "认知", "experiment": "实验", "metric": "指标", "risk": "风险",
    "lesson": "教训", "revenue": "收入", "cost": "成本", "milestone": "里程碑",
    "question": "开放问题",
}
RECORD_TYPES = ["decision", "problem", "solution", "experiment",
                "insight", "lesson", "risk", "milestone"]
ID_PREFIX = {"decision": "ADR", "problem": "PB", "solution": "SL",
             "experiment": "EX", "insight": "IN", "lesson": "LS",
             "risk": "RK", "milestone": "MS"}
RECORD_DIR = {"decision": "decisions", "problem": "problems",
              "solution": "solutions", "experiment": "experiments",
              "insight": "insights", "lesson": "lessons",
              "risk": "risks", "milestone": "milestones"}

STAGES = ["S0", "S1", "S2", "S3", "S4", "S5", "S6"]
STAGE_NAME = {"S0": "想法", "S1": "验证", "S2": "构建", "S3": "上线",
              "S4": "获客", "S5": "付费", "S6": "规模化"}
OUTCOMES = ["success", "failure", "pivot", "paused", "zombie"]

METRICS_HEADER = ["date", "metric", "value", "unit", "source", "confidence", "note"]
LEDGER_HEADER = ["date", "kind", "amount", "currency", "channel", "note"]
EXP_HEADER = ["id", "title", "status", "start", "end", "result", "link"]

ANCHOR_BEGIN = "<!-- project-journal:begin -->"
ANCHOR_END = "<!-- project-journal:end -->"

SECRET_PATTERNS = [
    (r"sk-[A-Za-z0-9_\-]{16,}", "OpenAI风格密钥"),
    (r"AKIA[0-9A-Z]{16}", "AWS AccessKey"),
    (r"gh[pousr]_[A-Za-z0-9]{20,}", "GitHub令牌"),
    (r"AIza[0-9A-Za-z_\-]{30,}", "Google APIKey"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "私钥"),
    (r"(?i)\b(api[_-]?key|apikey|secret|password|passwd|pwd|access[_-]?token|auth[_-]?token)\b\s*[:=]\s*[\"']?([A-Za-z0-9_\-/+=]{8,})", "疑似凭证赋值"),
    (r"\b1[3-9]\d{9}\b", "疑似手机号"),
    (r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}", "邮箱"),
]

# ---- 自我迭代（skill 自身的 bug / 逻辑问题台账）----
EVOLUTION_SCHEMA = 1
CRASH_EXIT = 3
EVOLVE_CATEGORIES = ["bug", "logic", "schema", "docs", "usability", "performance", "feature"]
EVOLVE_SEVERITIES = ["critical", "high", "medium", "low"]
EVOLVE_STATUSES = ["open", "proposed", "in-progress", "applied", "rejected", "wontfix"]


def say(msg=""):
    try:
        sys.stdout.write(str(msg) + "\n")
    except Exception:
        sys.stdout.write(str(msg).encode("utf-8", "replace").decode("utf-8", "replace") + "\n")


def die(msg, code=2):
    say("[ERROR] " + str(msg))
    sys.exit(code)


def today_str():
    return dt.date.today().isoformat()


def now_hm():
    return dt.datetime.now().strftime("%H:%M")


def now_iso():
    return dt.datetime.now().replace(microsecond=0).isoformat()


def parse_date(s):
    if not s:
        return dt.date.today()
    return dt.datetime.strptime(s.strip(), "%Y-%m-%d").date()


def read_text(path, limit=None):
    try:
        with open(path, "rb") as f:
            raw = f.read() if limit is None else f.read(limit)
    except OSError:
        return ""
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def write_text(path, text):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def rel(root, path):
    try:
        return os.path.relpath(path, root).replace(os.sep, "/")
    except ValueError:
        return path.replace(os.sep, "/")


def slugify(text, fallback="record", maxlen=48):
    s = re.sub(r"[^A-Za-z0-9]+", "-", (text or "").lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    if len(s) < 2:
        s = fallback
    return s[:maxlen].strip("-")


def first_heading(body):
    for line in (body or "").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def parse_front_matter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, text[m.end():]


def fm_block(d):
    order = ["id", "type", "project", "title", "date", "status", "tags", "links", "confidence"]
    lines = ["---"]
    for k in order:
        if k in d:
            lines.append("%s: %s" % (k, d[k]))
    lines.append("---")
    return "\n".join(lines) + "\n"


def text_hash(s):
    import hashlib
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()


def skill_manifest():
    try:
        return json.loads(read_text(os.path.join(SKILL_DIR, "manifest.json"))) or {}
    except Exception:
        return {}


def skill_version():
    return os.environ.get("PJ_SKILL_VERSION") or skill_manifest().get("version") or "0.0.0"


def bump_version(ver, part="patch"):
    try:
        a, b, c = [int(x) for x in (ver or "0.0.0").split(".")[:3]]
    except Exception:
        a, b, c = 0, 0, 0
    if part == "major":
        return "%d.0.0" % (a + 1)
    if part == "minor":
        return "%d.%d.0" % (a, b + 1)
    return "%d.%d.%d" % (a, b, c + 1)


def ledger_dir(explicit=None):
    d = explicit or os.environ.get("PJ_LEDGER_DIR") or os.path.join(SKILL_DIR, "evolution")
    try:
        os.makedirs(d, exist_ok=True)
        probe = os.path.join(d, ".write-test")
        write_text(probe, "ok")
        os.remove(probe)
        return d
    except OSError:
        d2 = os.path.join(os.path.expanduser("~"), ".project-journal", "evolution")
        os.makedirs(d2, exist_ok=True)
        say("[WARN] skill 目录不可写，迭代台账改用：%s" % d2)
        return d2


def load_ledger(explicit=None):
    d = ledger_dir(explicit)
    p = os.path.join(d, "ledger.json")
    if os.path.isfile(p):
        try:
            led = json.loads(read_text(p))
            if isinstance(led, dict) and isinstance(led.get("entries"), list):
                led.setdefault("schema", EVOLUTION_SCHEMA)
                return led
        except Exception as e:
            say("[WARN] ledger.json 解析失败，已备份并重建：%s" % e)
            try:
                os.replace(p, p + ".broken")
            except OSError:
                pass
    return {"schema": EVOLUTION_SCHEMA, "skill": "project-journal", "version": skill_version(), "entries": []}


def ledger_md(led):
    L = ["# 自我迭代台账 . project-journal", "",
         "> 由 journal.py 自动生成（%s），请勿手工编辑；改 ledger.json 后重跑任意 evolve 命令即可重建本视图。" % now_iso(),
         "> 用途：记录本 skill 自身在运行中暴露的 bug / 逻辑问题 / 易用性问题及修订历史。",
         "> 闭环流程与治理规则见 references/08-self-evolution.md。", ""]
    ents = led.get("entries", [])
    st = {}
    for e in ents:
        st[e.get("status", "open")] = st.get(e.get("status", "open"), 0) + 1
    L.append("- 当前版本：v%s . 条目 %d 条 %s" % (skill_version(), len(ents),
             ("(" + " . ".join("%s %d" % (k, v) for k, v in st.items()) + ")") if st else ""))
    L.append("")
    L.append("| ID | 日期 | 类别 | 严重度 | 状态 | 标题 | 修复版本 |")
    L.append("|---|---|---|---|---|---|---|")
    for e in ents:
        L.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            e.get("id"), e.get("date"), e.get("category"), e.get("severity"), e.get("status"),
            (e.get("title") or "").replace("|", "/"), e.get("version") or "-"))
    L.append("")
    for e in ents:
        L += ["## %s %s" % (e.get("id"), e.get("title")), "",
              "- 日期：%s . 类别：%s . 严重度：%s . 状态：%s . 发现于：v%s" % (
                  e.get("date"), e.get("category"), e.get("severity"), e.get("status"),
                  e.get("skill_version") or "-"),
              "- 相关项目：%s" % (e.get("project") or "-")]
        if e.get("repro"):
            L.append("- 复现命令：%s" % e["repro"])
        if e.get("evidence"):
            L.append("- 证据：%s" % e["evidence"])
        if e.get("symptom"):
            L += ["", "**症状 / 期望**", "", "```", (e["symptom"] or "").strip(), "```"]
        if e.get("fix"):
            L += ["", "**修复**", "", (e["fix"] or "").strip()]
        if e.get("version"):
            L += ["", "- 修复版本：v%s（%s）" % (e["version"], e.get("resolution_date") or "")]
        L.append("")
    return "\n".join(L)


def save_ledger(led, explicit=None):
    d = ledger_dir(explicit)
    led["skill"] = "project-journal"
    led["version"] = skill_version()
    write_text(os.path.join(d, "ledger.json"), json.dumps(led, ensure_ascii=False, indent=2) + "\n")
    write_text(os.path.join(d, "LEDGER.md"), ledger_md(led))
    return d


def fingerprint(category, title):
    import hashlib
    key = "%s|%s" % (category, re.sub(r"\s+", "", (title or "").lower()))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def next_ev_id(led):
    top = 0
    for e in led.get("entries", []):
        m = re.match(r"EV-(\d+)$", e.get("id", ""))
        if m:
            top = max(top, int(m.group(1)))
    return "EV-%04d" % (top + 1)


def record_evolve(category, severity, title, symptom="", evidence="", repro="",
                  project="", status="open", explicit_ledger=None, fix="", force=False):
    led = load_ledger(explicit_ledger)
    fp = fingerprint(category, title)
    if not force:
        for e in led.get("entries", []):
            if e.get("fingerprint") == fp and e.get("status") not in ("applied", "rejected", "wontfix"):
                return {"id": e["id"], "title": e["title"], "duplicate": True, "status": e.get("status")}
    ent = {"id": next_ev_id(led), "date": today_str(), "category": category, "severity": severity,
           "status": status, "title": title, "symptom": symptom, "evidence": evidence, "repro": repro,
           "project": (project or "").replace(os.sep, "/"), "fix": fix,
           "skill_version": skill_version(), "fingerprint": fp, "version": "", "resolution_date": ""}
    led["entries"].append(ent)
    save_ledger(led, explicit_ledger)
    return ent


def require_root(args):
    if not args.root:
        die("必须指定 --root <记录根目录>")
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        die("记录根目录不存在：%s\n（首次使用请先跑 init）" % root)
    return root


def tracker_path(root):
    return os.path.join(root, "tracker.json")


def load_tracker(root):
    p = tracker_path(root)
    if not os.path.isfile(p):
        die("不是有效的记录目录（缺少 tracker.json）：%s" % root)
    try:
        return json.loads(read_text(p))
    except Exception as e:
        die("tracker.json 解析失败：%s" % e)


def save_tracker(root, t):
    t["last_touch"] = now_iso()
    write_text(tracker_path(root), json.dumps(t, ensure_ascii=False, indent=2) + "\n")


def ensure_dirs(root):
    for d in ["journal", "records", "metrics", "reviews", "assets", "publish"]:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    for d in RECORD_DIR.values():
        os.makedirs(os.path.join(root, "records", d), exist_ok=True)


def ensure_csv(path, header):
    if not os.path.isfile(path):
        write_text(path, ",".join(header) + "\n")


def read_csv(path):
    if not os.path.isfile(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append({(k or ""): (v or "") for k, v in row.items()})
    return rows


def append_csv(path, header, row):
    ensure_csv(path, header)
    with open(path, "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow([row.get(k, "") for k in header])


def day_path(root, date):
    return os.path.join(root, "journal", "%s.md" % date)


def scan_days(root):
    d = os.path.join(root, "journal")
    if not os.path.isdir(d):
        return []
    return sorted([f[:-3] for f in os.listdir(d)
                   if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", f)])


def parse_daily_entries(text):
    out = []
    for line in (text or "").splitlines():
        m = re.match(r"^###\s+(\d{2}:\d{2})\s+\[([^\]]+)\]\s*(.*?)\s*$", line)
        if not m:
            continue
        title = m.group(3)
        rid = ""
        mm = re.search(r"`([A-Z]{2,3}-\d{4})`", title)
        if mm:
            rid = mm.group(1)
            title = title.replace("`%s`" % rid, "").strip()
        out.append({"time": m.group(1), "code": m.group(2).strip(), "title": title, "id": rid})
    return out


def ensure_day_file(root, tracker, date):
    p = day_path(root, date)
    if os.path.isfile(p):
        return p
    content = (
        "# %s . %s\n\n"
        "> 原始日记（append-only）：只追加，不改写历史。更正请新增条目并标注 [更正 <ID>]。\n"
        "> 条目格式：### HH:MM [类型] 标题 ；类型代码：T任务 D决策 P问题 S解法 I认知 X实验 M指标 $收入 C成本 R风险 L教训 MS里程碑 Q开放问题 U更新\n\n"
        "---\n\n"
    ) % (date, tracker.get("project", ""))
    write_text(p, content)
    return p


def append_daily(root, tracker, date, code, title, body="", ref=""):
    p = ensure_day_file(root, tracker, date)
    text = read_text(p)
    if not text.endswith("\n"):
        text += "\n"
    head = "### %s [%s] %s" % (now_hm(), code, title)
    if ref:
        head += "  `%s`" % ref
    block = head + "\n"
    body = (body or "").strip()
    block += (body + "\n") if body else "- （待补充：背景 / 决定 / 理由 / 证据 / 下一步）\n"
    write_text(p, text.rstrip("\n") + "\n\n" + block + "\n")
    return p


def scan_records(root):
    recs = []
    for t, sub in RECORD_DIR.items():
        d = os.path.join(root, "records", sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md"):
                continue
            p = os.path.join(d, fn)
            meta, body = parse_front_matter(read_text(p))
            rid = meta.get("id") or fn.split("-")[0]
            recs.append({
                "id": rid, "type": meta.get("type", t),
                "title": meta.get("title") or first_heading(body) or fn,
                "date": meta.get("date", ""), "status": meta.get("status", ""),
                "tags": meta.get("tags", ""), "links": meta.get("links", ""),
                "confidence": meta.get("confidence", ""),
                "path": rel(root, p), "raw": read_text(p),
            })
    recs.sort(key=lambda r: (r.get("date") or "", r.get("id") or ""))
    return recs


def find_record_path(root, rid):
    for sub in RECORD_DIR.values():
        d = os.path.join(root, "records", sub)
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if fn.startswith(rid + "-") or fn.startswith(rid + "."):
                return os.path.join(d, fn)
    return None


def next_record_id(root, rtype):
    prefix = ID_PREFIX[rtype]
    top = 0
    for r in scan_records(root):
        if r["id"].startswith(prefix + "-"):
            try:
                top = max(top, int(r["id"].split("-")[1]))
            except (IndexError, ValueError):
                pass
    return "%s-%04d" % (prefix, top + 1)


def days_between(a, b):
    try:
        return (parse_date(b) - parse_date(a)).days
    except Exception:
        return 0


def refs_display(s):
    s = (s or "").strip().strip("[]").strip()
    return s.replace(",", " . ") if s else "无"


def body_after_title(raw):
    parts = (raw or "").split("\n")
    for i, line in enumerate(parts):
        if line.startswith("# "):
            return "\n".join(parts[i + 1:]).strip()
    return (raw or "").strip()


def collect_facts(root, tracker):
    recs = scan_records(root)
    days = scan_days(root)
    entry_count = 0
    recent = []
    for d in days:
        es = parse_daily_entries(read_text(day_path(root, d)))
        entry_count += len(es)
        for e in es:
            recent.append((d, e))
    metrics = read_csv(os.path.join(root, "metrics", "metrics.csv"))
    ledger = read_csv(os.path.join(root, "metrics", "ledger.csv"))
    latest = {}
    for row in metrics:
        if row.get("metric"):
            latest[row["metric"]] = row
    totals = {}
    for row in ledger:
        try:
            amt = float(row.get("amount") or 0)
        except ValueError:
            amt = 0.0
        cur = row.get("currency") or "?"
        kind = (row.get("kind") or "").lower()
        t = totals.setdefault(cur, {"income": 0.0, "cost": 0.0})
        if kind.startswith("inc") or kind in ("revenue", "收入"):
            t["income"] += amt
        else:
            t["cost"] += amt
    return {"records": recs, "days": days, "entry_count": entry_count,
            "recent": recent[-12:], "metrics": metrics, "latest": latest,
            "ledger": ledger, "totals": totals}


def regen_state(root, tracker):
    f = collect_facts(root, tracker)
    created = tracker.get("created", "")
    last = tracker.get("last_entry", "")
    stage = tracker.get("stage", "S0")
    hist = tracker.get("stage_history", [])
    today = today_str()
    L = []
    L.append("# STATE . %s" % tracker.get("project", ""))
    L.append("")
    L.append("> 由 journal.py 自动生成（%s），**手工修改会被下次刷新覆盖**。" % now_iso())
    L.append("> 记录根目录：%s" % root.replace(os.sep, "/"))
    L.append("> 契约 PROTOCOL.md . 目录 INDEX.md . 宪章 CHARTER.md . 待办 NEXT-ACTIONS.md")
    L.append("")
    L.append("## 驾驶舱")
    L.append("")
    L.append("| 项目 | 值 |")
    L.append("|---|---|")
    L.append("| 阶段 | **%s %s** |" % (stage, STAGE_NAME.get(stage, "")))
    if hist:
        L.append("| 阶段轨迹 | %s |" % " -> ".join("%s(%s)" % (h.get("to", "?"), h.get("date", "?")) for h in hist))
    else:
        L.append("| 阶段轨迹 | %s(%s) |" % (stage, created))
    L.append("| 起始 | %s（第 %d 天） |" % (created, (days_between(created, today) + 1) if created else 0))
    if last:
        gap = days_between(last, today)
        gap_txt = "今天" if gap == 0 else "%d 天前" % gap
        mark = " **<- 已停滞**" if gap >= 7 and not tracker.get("outcome") else ""
        L.append("| 最后记录 | %s（%s）%s |" % (last, gap_txt, mark))
    else:
        L.append("| 最后记录 | 尚无 |")
    L.append("| 终局 | %s |" % (tracker.get("outcome") or "进行中"))
    L.append("| 条目总量 | 日记 %d 条 . 档案 %d 份 . 指标 %d 行 . 收支 %d 行 |"
             % (f["entry_count"], len(f["records"]), len(f["metrics"]), len(f["ledger"])))
    L.append("")
    L.append("> 成功线 / 止损线见 CHARTER.md -- **成败以此为准，不以感觉为准**。")
    L.append("")
    L.append("## 关键数字（最新）")
    L.append("")
    if f["latest"]:
        L.append("| 指标 | 值 | 单位 | 日期 | 来源 | 置信度 |")
        L.append("|---|---|---|---|---|---|")
        for name, row in f["latest"].items():
            L.append("| %s | %s | %s | %s | %s | %s |" % (
                name, row.get("value", ""), row.get("unit", ""), row.get("date", ""),
                row.get("source", "") or "-", row.get("confidence", "") or "-"))
    else:
        L.append("_尚无指标。出现任何真实数字时用 journal.py metric 记录。_")
    L.append("")
    if f["totals"]:
        for cur, tot in f["totals"].items():
            L.append("- **%s**：收入 %.2f . 成本 %.2f . 净额 %.2f"
                     % (cur, tot["income"], tot["cost"], tot["income"] - tot["cost"]))
    else:
        L.append("- _尚无收支记录。_")
    L.append("")
    opens = [r for r in f["records"] if r["type"] == "problem"
             and (r["status"] or "open") not in ("solved", "closed", "done", "wontfix")]
    L.append("## 未闭环问题（%d）" % len(opens))
    L.append("")
    L += (["- %s %s（%s . %s）" % (r["id"], r["title"], r["date"], r["status"] or "open") for r in opens]
          or ["_无。_"])
    L.append("")
    risks = [r for r in f["records"] if r["type"] == "risk"
             and (r["status"] or "open") not in ("mitigated", "closed", "accepted", "done")]
    if risks:
        L.append("## 开放风险（%d）" % len(risks))
        L.append("")
        for r in risks:
            L.append("- %s %s" % (r["id"], r["title"]))
        L.append("")
    L.append("## 最近条目")
    L.append("")
    if f["recent"]:
        for d, e in f["recent"][::-1][:10]:
            L.append("- %s %s [%s] %s%s" % (d, e["time"], e["code"], e["title"],
                                            ("  %s" % e["id"]) if e["id"] else ""))
    else:
        L.append("_尚无日记条目。_")
    L.append("")
    na = os.path.join(root, "NEXT-ACTIONS.md")
    L.append("## 下一步（来自 NEXT-ACTIONS.md）")
    L.append("")
    if os.path.isfile(na):
        todos = [re.sub(r"^\s*[-*]\s*\[ \]\s*", "", l.strip())
                 for l in read_text(na).splitlines() if re.match(r"^\s*[-*]\s*\[ \]", l)]
        L += (["- " + t for t in todos[:15]] or ["_没有未完成事项。_"])
    else:
        L.append("_缺少 NEXT-ACTIONS.md。_")
    L.append("")
    path = os.path.join(root, "STATE.md")
    write_text(path, "\n".join(L))
    return path


def regen_index(root, tracker):
    f = collect_facts(root, tracker)
    L = []
    L.append("# INDEX . %s" % tracker.get("project", ""))
    L.append("")
    L.append("> 由 journal.py 自动生成（%s）。按类型/时间检索本项目全部记录。" % now_iso())
    L.append("")
    L.append("- 阶段：%s %s . 终局：%s" % (tracker.get("stage", ""),
             STAGE_NAME.get(tracker.get("stage", ""), ""), tracker.get("outcome") or "进行中"))
    L.append("- 日记 %d 条 . 档案 %d 份" % (f["entry_count"], len(f["records"])))
    L.append("")
    L.append("## 档案")
    L.append("")
    by_type = {}
    for r in f["records"]:
        by_type.setdefault(r["type"], []).append(r)
    if not by_type:
        L.append("_尚无档案。用 journal.py add --type decision|problem|... 创建。_")
    for t in RECORD_TYPES:
        rs = by_type.get(t)
        if not rs:
            continue
        L.append("### %s %s（%d）" % (TYPE_CN.get(t, t), t, len(rs)))
        L.append("")
        for r in rs:
            st = (" . " + r["status"]) if r["status"] else ""
            L.append("- **%s** [%s](%s) -- %s%s" % (r["id"], r["title"], r["path"], r["date"], st))
        L.append("")
    L.append("## 日记")
    L.append("")
    if not f["days"]:
        L.append("_尚无日记。_")
    for d in reversed(f["days"]):
        es = parse_daily_entries(read_text(day_path(root, d)))
        codes = {}
        for e in es:
            codes[e["code"]] = codes.get(e["code"], 0) + 1
        summary = " ".join("%s%d" % (k, v) for k, v in codes.items())
        L.append("- [%s](journal/%s.md) -- %d 条：%s" % (d, d, len(es), summary or "-"))
    L.append("")
    path = os.path.join(root, "INDEX.md")
    write_text(path, "\n".join(L))
    return path


def refresh(root, tracker, do_say=False):
    regen_state(root, tracker)
    regen_index(root, tracker)
    if do_say:
        say("已刷新 STATE.md / INDEX.md")


def guess_project_root(root):
    """推断项目根目录（会话锚点注入到哪里）。

    约定优先：记录目录就是项目根下的子文件夹 <项目根>/project-journal，
    因此它的上一级就是项目根。这样即使项目自身没有 .git，也不会因为
    上层存在仓库（monorepo / 上级 git / 上层 AGENTS.md）而把锚点注入错位置。
    不确定时返回 None（提示用户用 --project-root），绝不猜。
    """
    root = os.path.abspath(root)
    if os.path.basename(root).lower() == "project-journal":
        return os.path.dirname(root)
    cur = root
    for _ in range(3):
        if os.path.isdir(os.path.join(cur, ".git")) or os.path.isfile(os.path.join(cur, "AGENTS.md")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None


def anchor_block(root, project_root):
    r = os.path.relpath(root, project_root).replace(os.sep, "/")
    script = os.path.join(HERE, "journal.py").replace(os.sep, "/")
    return "\n".join([
        ANCHOR_BEGIN,
        "## 项目过程跟踪（project-journal . 自动维护块，请勿手工编辑）",
        "",
        "本项目已启用全过程跟踪，记录目录：%s/（相对本文件所在目录）。" % r,
        "",
        "**每次会话必须遵守：**",
        "",
        "1. **开工先读**：python \"%s\" resume --root \"%s\"" % (script, r),
        "2. **收工前写**：把本次增量追加到当日日记 %s/journal/YYYY-MM-DD.md" % r,
        "   （决策 / 问题与解法 / 有价值的讨论 / 认知更新 / 真实数字 / 风险 / 里程碑）",
        "3. **有数字就进表**：journal.py metric ... 、journal.py ledger ...",
        "4. **收尾三件**：更新 %s/NEXT-ACTIONS.md . 跑 journal.py index . 跑 journal.py lint" % r,
        "5. **铁律**：append-only 不改写历史；禁止写入任何密钥与隐私；不编造数字；区分事实与判断",
        "",
        "> 未记录 = 对三个月后的自己、对下一个 AI 而言没有发生过。",
        "> 契约全文：%s/PROTOCOL.md . 当前状态：%s/STATE.md" % (r, r),
        ANCHOR_END,
        "",
    ])


def inject_anchor(root, tracker, project_root=None, explicit_anchor=None):
    pr = project_root or guess_project_root(root)
    if explicit_anchor:
        target = os.path.abspath(explicit_anchor)
        pr = os.path.dirname(target)
    elif pr:
        target = os.path.join(pr, "AGENTS.md")
        if not os.path.isfile(target) and os.path.isfile(os.path.join(pr, "CLAUDE.md")):
            target = os.path.join(pr, "CLAUDE.md")
    else:
        return None, ("未能确定项目根目录（记录目录不在 <项目根>/project-journal 约定位置）。"
                      "请加 --project-root \"<项目根>\" 或 --anchor \"<AGENTS.md 路径>\" 指定锚点位置。")
    block = anchor_block(root, pr)
    old = read_text(target)
    if ANCHOR_BEGIN in old and ANCHOR_END in old:
        new = re.sub(re.escape(ANCHOR_BEGIN) + r".*?" + re.escape(ANCHOR_END),
                     block.strip("\n").replace("\\", "\\\\"), old, flags=re.S)
        action = "更新"
    else:
        sep = "" if (not old or old.endswith("\n")) else "\n"
        new = old + sep + ("" if not old else "\n") + block
        action = "注入"
    write_text(target, new)
    return target, action


def cmd_init(args):
    root = os.path.abspath(args.root) if args.root else os.path.join(os.getcwd(), "project-journal")
    project = args.project or os.path.basename(root)
    slug = args.slug or slugify(project, "project")
    stage = args.stage or "S0"
    if stage not in STAGES:
        die("--stage 必须是 %s 之一" % "/".join(STAGES))
    ensure_dirs(root)
    ensure_csv(os.path.join(root, "metrics", "metrics.csv"), METRICS_HEADER)
    ensure_csv(os.path.join(root, "metrics", "ledger.csv"), LEDGER_HEADER)
    ensure_csv(os.path.join(root, "metrics", "experiments.csv"), EXP_HEADER)
    existed = os.path.isfile(tracker_path(root))
    if existed and not args.force:
        tracker = load_tracker(root)
        say("[跳过] 记录目录已存在，未改动 tracker.json：%s" % root)
    else:
        tracker = {
            "schema": SCHEMA, "project": project, "slug": slug,
            "created": args.date or today_str(), "stage": stage,
            "currency": args.currency or "USD",
            "hypothesis": args.hypothesis or "", "success_line": args.success or "",
            "stop_loss": args.stop_loss or "", "counters": {}, "last_entry": "",
            "last_touch": now_iso(),
            "stage_history": [{"date": args.date or today_str(), "from": "", "to": stage, "why": "立项"}],
            "outcome": None, "skill_version": skill_version(), "upgrades": [],
        }
        save_tracker(root, tracker)
        say("[OK] 已创建记录目录：%s" % root)
    proto_dst = os.path.join(root, "PROTOCOL.md")
    if not os.path.isfile(proto_dst):
        body = read_text(os.path.join(SKILL_DIR, "references", "00-protocol.md"))
        if not body:
            body = "# 记录契约\n\n（未找到 references/00-protocol.md，请手工补全。）\n"
        body = body.replace("{PROJECT}", tracker.get("project", "")).replace("{VERSION}", skill_version())
        write_text(proto_dst, body)
        tracker["protocol_hash"] = text_hash(body)
        tracker["protocol_version"] = skill_version()
        save_tracker(root, tracker)
        say("[OK] PROTOCOL.md（契约 v%s）" % skill_version())
    charter = os.path.join(root, "CHARTER.md")
    if not os.path.isfile(charter):
        tpl = read_text(os.path.join(SKILL_DIR, "templates", "CHARTER.md"))
        if not tpl:
            tpl = "# CHARTER\n\n## 一句话目标\n待填\n\n## 变现假设\n待填\n\n## 成功线\n待填\n\n## 止损线\n待填\n"
        tpl = (tpl.replace("{PROJECT}", tracker.get("project", ""))
                  .replace("{SLUG}", tracker.get("slug", ""))
                  .replace("{DATE}", tracker.get("created", ""))
                  .replace("{CURRENCY}", tracker.get("currency", "USD"))
                  .replace("{HYPOTHESIS}", tracker.get("hypothesis", "") or "待填")
                  .replace("{SUCCESS}", tracker.get("success_line", "") or "待填")
                  .replace("{STOPLOSS}", tracker.get("stop_loss", "") or "待填"))
        write_text(charter, tpl)
        say("[OK] CHARTER.md（请补全成功线/止损线）")
    na = os.path.join(root, "NEXT-ACTIONS.md")
    if not os.path.isfile(na):
        tpl = read_text(os.path.join(SKILL_DIR, "templates", "NEXT-ACTIONS.md")) or "# NEXT-ACTIONS\n\n## 进行中\n- [ ] 待填\n"
        write_text(na, tpl.replace("{DATE}", today_str()))
        say("[OK] NEXT-ACTIONS.md")
    sanitize = os.path.join(root, "sanitize.txt")
    if not os.path.isfile(sanitize):
        write_text(sanitize,
                   "# 脱敏规则（publish 时按顺序执行）\n"
                   "# 写法： 原文 => 替换文字\n"
                   "# 正则： re:模式 => 替换文字\n"
                   "# 示例：ACME 公司 => A 公司\n")
    target, action = inject_anchor(root, tracker, args.project_root, args.anchor)
    if target:
        say("[OK] %s会话锚点：%s" % (action, target))
        say("     位置：项目根目录下的子文件夹（建议随 git 一起提交，它就是这个项目的数字资产）")
    else:
        say("[WARN] %s" % action)
    refresh(root, tracker)
    say("[OK] STATE.md / INDEX.md")
    say("")
    if existed and not args.force:
        say("记录目录已存在（本次未新建）。开工流程：")
        say("  1) python journal.py resume --root \"%s\"" % root.replace(os.sep, "/"))
        say("  2) 收工前 add/metric/ledger 落盘，更新 NEXT-ACTIONS.md，再跑 lint")
    else:
        say("下一步：")
        say("  1) 补全 %s 的成功线/止损线" % rel(root, charter))
        say("  2) 把本次对话已产出的信息用 add 落盘")
        say("  3) 之后每次开工先跑 resume")
    return 0


def cmd_anchor(args):
    root = require_root(args)
    tracker = load_tracker(root)
    target, action = inject_anchor(root, tracker, args.project_root, args.anchor)
    if not target:
        die(action)
    say("[OK] %s锚点：%s" % (action, target))
    return 0


def cmd_status(args):
    root = require_root(args)
    t = load_tracker(root)
    f = collect_facts(root, t)
    last = t.get("last_entry") or ""
    gap = days_between(last, today_str()) if last else None
    opens = [r for r in f["records"] if r["type"] == "problem"
             and (r["status"] or "open") not in ("solved", "closed", "done", "wontfix")]
    data = {
        "root": root, "project": t.get("project"), "slug": t.get("slug"),
        "stage": t.get("stage"), "stage_name": STAGE_NAME.get(t.get("stage", ""), ""),
        "outcome": t.get("outcome"), "created": t.get("created"),
        "days_active": (days_between(t.get("created", ""), today_str()) + 1) if t.get("created") else 0,
        "last_entry": last, "stale_days": gap, "entries": f["entry_count"],
        "records": len(f["records"]), "open_problems": len(opens),
        "currency": t.get("currency"), "totals": f["totals"],
        "latest_metrics": {k: v.get("value") for k, v in f["latest"].items()},
    }
    if args.json:
        say(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    say("%s  [%s %s]%s" % (data["project"], data["stage"], data["stage_name"],
                           ("  终局：" + data["outcome"]) if data["outcome"] else ""))
    say("  第 %d 天 . 最后记录 %s . 日记 %d 条 . 档案 %d 份 . 未闭环问题 %d"
        % (data["days_active"], last or "无", data["entries"], data["records"], data["open_problems"]))
    if gap is not None and gap >= 7 and not data["outcome"]:
        say("  [WARN] 已停滞 %d 天 -- 项目还在跑吗？补记或关闭它。" % gap)
    if data["latest_metrics"]:
        say("  最新指标：" + " . ".join("%s=%s" % (k, v) for k, v in list(data["latest_metrics"].items())[:8]))
    for cur, tot in data["totals"].items():
        say("  %s：收入 %.2f . 成本 %.2f . 净额 %.2f" % (cur, tot["income"], tot["cost"], tot["income"] - tot["cost"]))
    return 0


def cmd_resume(args):
    root = require_root(args)
    t = load_tracker(root)
    f = collect_facts(root, t)
    budget = args.max_chars
    P = []
    P.append("========== RESUME PACK :: %s ==========" % t.get("project"))
    P.append("阶段 %s %s . 第 %d 天 . 最后记录 %s . 日记 %d 条 . 档案 %d 份"
             % (t.get("stage"), STAGE_NAME.get(t.get("stage", ""), ""),
                days_between(t.get("created", ""), today_str()) + 1,
                t.get("last_entry") or "无", f["entry_count"], len(f["records"])))
    if t.get("hypothesis"):
        P.append("变现假设：%s" % t["hypothesis"])
    P.append("")
    P.append("---------- STATE.md ----------")
    P.append(read_text(os.path.join(root, "STATE.md")).strip() or "(缺失，请跑 index)")
    P.append("")
    P.append("---------- 最近日记（最多 3 天） ----------")
    for d in f["days"][-3:]:
        txt = read_text(day_path(root, d)).strip()
        stripped = "\n".join([l for l in txt.splitlines() if not l.startswith("> ")])
        if len(stripped) > budget // 3:
            stripped = stripped[:budget // 3] + "\n...（已截断，完整内容见 journal/%s.md）" % d
        P.append(stripped)
        P.append("")
    if not f["days"]:
        P += ["(尚无日记)", ""]
    opens = [r for r in f["records"] if r["type"] == "problem"
             and (r["status"] or "open") not in ("solved", "closed", "done", "wontfix")]
    P.append("---------- 未闭环问题（%d） ----------" % len(opens))
    for r in opens:
        P.append("- %s %s (%s) -> %s" % (r["id"], r["title"], r["date"], r["path"]))
    P.append("")
    exp = [r for r in f["records"] if r["type"] == "experiment"
           and (r["status"] or "open") not in ("done", "closed", "finished")]
    if exp:
        P.append("---------- 进行中实验（%d） ----------" % len(exp))
        for r in exp:
            P.append("- %s %s (%s)" % (r["id"], r["title"], r["date"]))
        P.append("")
    P.append("---------- NEXT-ACTIONS.md ----------")
    P.append(read_text(os.path.join(root, "NEXT-ACTIONS.md")).strip() or "(缺失)")
    text = "\n".join(P)
    if len(text) > budget:
        text = text[:budget] + "\n...（补液包超长已截断；请直接读 STATE.md 与 journal/ 下相关文件）"
    say(text)
    say("")
    say(">> 现在按 MUST-RECORD 触发器判断本次增量，用 add/metric/ledger/stage 落盘，最后更新 NEXT-ACTIONS.md 并跑 lint。")
    return 0


def cmd_add(args):
    root = require_root(args)
    t = load_tracker(root)
    rtype = args.type
    if rtype not in TYPE_CODE:
        die("--type 必须是 %s 之一" % "|".join(TYPE_CODE.keys()))
    date = args.date or today_str()
    body = ""
    if args.body_file:
        if not os.path.isfile(args.body_file):
            die("--body-file 不存在：%s" % args.body_file)
        body = read_text(args.body_file).strip()
    title = args.title or first_heading(body) or "(无标题)"
    ref = ""
    created_path = ""
    if rtype in RECORD_TYPES:
        rid = args.id or next_record_id(root, rtype)
        path = os.path.join(root, "records", RECORD_DIR[rtype], "%s-%s.md" % (rid, slugify(title, "record", 40)))
        if os.path.exists(path):
            die("档案已存在：%s" % path)
        default_status = "open" if rtype in ("problem", "risk", "experiment", "question") else ("accepted" if rtype == "decision" else "done")
        meta = {"id": rid, "type": rtype, "project": t.get("slug", ""), "title": title,
                "date": date, "status": args.status or default_status,
                "tags": "[%s]" % (args.tags or ""), "links": "[%s]" % (args.link or ""),
                "confidence": args.confidence or "medium"}
        write_text(path, fm_block(meta) + "\n# %s\n\n%s\n" % (
            title, body or "（待补充：背景 / 选项 / 决定 / 理由 / 代价 / 证据 / 下一步）"))
        ref = rid
        created_path = rel(root, path)
        t["counters"][rtype] = int(t["counters"].get(rtype, 0)) + 1
    append_daily(root, t, date, TYPE_CODE[rtype], title, body, ref)
    if rtype == "experiment" and ref:
        append_csv(os.path.join(root, "metrics", "experiments.csv"), EXP_HEADER,
                   {"id": ref, "title": title, "status": "open", "start": date, "end": "",
                    "result": "", "link": created_path})
    t["last_entry"] = date
    save_tracker(root, t)
    refresh(root, t)
    say("[OK] %s %s -> %s" % (TYPE_CODE[rtype], title, ref or ("journal/%s.md" % date)))
    if created_path:
        say("     档案：%s" % created_path)
    return 0


def cmd_update(args):
    root = require_root(args)
    t = load_tracker(root)
    rid = args.id
    path = find_record_path(root, rid)
    if not path:
        die("找不到档案：%s" % rid)
    meta, body = parse_front_matter(read_text(path))
    if args.status:
        meta["status"] = args.status
    new_txt = fm_block(meta) + body.rstrip("\n") + "\n"
    add = ""
    if args.append_file:
        if not os.path.isfile(args.append_file):
            die("--append-file 不存在：%s" % args.append_file)
        add = read_text(args.append_file).strip()
        new_txt += "\n---\n\n## 更新 %s\n\n%s\n" % (now_iso()[:16].replace("T", " "), add)
    write_text(path, new_txt)
    append_daily(root, t, args.date or today_str(), "U",
                 "更新 %s%s" % (rid, (" -> " + args.status) if args.status else ""), add, "")
    if meta.get("type") == "experiment":
        rows = read_csv(os.path.join(root, "metrics", "experiments.csv"))
        done = (args.status or "") in ("done", "closed", "finished")
        for r in rows:
            if r.get("id") == rid:
                r["status"] = args.status or r.get("status", "")
                if done:
                    r["end"] = args.date or today_str()
                if args.result:
                    r["result"] = args.result
        write_text(os.path.join(root, "metrics", "experiments.csv"),
                   ",".join(EXP_HEADER) + "\n" + "\n".join(
                       ",".join(['"%s"' % (r.get(k, "") or "").replace('"', '""') for k in EXP_HEADER])
                       for r in rows) + "\n")
    t["last_entry"] = args.date or today_str()
    save_tracker(root, t)
    refresh(root, t)
    say("[OK] 已更新 %s%s" % (rid, ("（status=%s）" % args.status) if args.status else ""))
    return 0


def cmd_metric(args):
    root = require_root(args)
    t = load_tracker(root)
    date = args.date or today_str()
    append_csv(os.path.join(root, "metrics", "metrics.csv"), METRICS_HEADER,
               {"date": date, "metric": args.name, "value": args.value, "unit": args.unit or "",
                "source": args.source or "", "confidence": args.confidence or "medium",
                "note": args.note or ""})
    append_daily(root, t, date, "M", "%s = %s %s" % (args.name, args.value, args.unit or ""),
                 "- 来源：%s . 置信度：%s%s" % (args.source or "未知", args.confidence or "medium",
                                               (" . 备注：" + args.note) if args.note else ""), "")
    t["last_entry"] = date
    save_tracker(root, t)
    refresh(root, t)
    say("[OK] 指标 %s = %s %s（%s）" % (args.name, args.value, args.unit or "", date))
    return 0


def cmd_ledger(args):
    root = require_root(args)
    t = load_tracker(root)
    date = args.date or today_str()
    kind = "income" if args.kind.lower().startswith("inc") else "cost"
    cur = args.currency or t.get("currency", "USD")
    append_csv(os.path.join(root, "metrics", "ledger.csv"), LEDGER_HEADER,
               {"date": date, "kind": kind, "amount": args.amount, "currency": cur,
                "channel": args.channel or "", "note": args.note or ""})
    append_daily(root, t, date, "$" if kind == "income" else "C",
                 "%s %s %s" % ("收入" if kind == "income" else "成本", args.amount, cur),
                 "- 渠道：%s%s" % (args.channel or "未知", (" . 备注：" + args.note) if args.note else ""), "")
    t["last_entry"] = date
    save_tracker(root, t)
    refresh(root, t)
    say("[OK] %s %s %s（%s . %s）" % (kind, args.amount, cur, args.channel or "-", date))
    return 0


def cmd_stage(args):
    root = require_root(args)
    t = load_tracker(root)
    new = args.set
    if new not in STAGES:
        die("--set 必须是 %s 之一" % "/".join(STAGES))
    old = t.get("stage", "")
    if old == new:
        say("[跳过] 阶段已经是 %s" % new)
        return 0
    date = args.date or today_str()
    t["stage"] = new
    t.setdefault("stage_history", []).append({"date": date, "from": old, "to": new, "why": args.why or ""})
    append_daily(root, t, date, "MS", "阶段推进 %s -> %s %s" % (old, new, STAGE_NAME.get(new, "")),
                 "- 原因：%s" % (args.why or "待补充"), "")
    t["last_entry"] = date
    save_tracker(root, t)
    refresh(root, t)
    say("[OK] 阶段 %s -> %s %s（%s）" % (old, new, STAGE_NAME.get(new, ""), args.why or "-"))
    return 0


def cmd_index(args):
    root = require_root(args)
    refresh(root, load_tracker(root), do_say=True)
    return 0


def cmd_lint(args):
    root = require_root(args)
    errors, warns, infos = [], [], []
    try:
        t = json.loads(read_text(tracker_path(root)))
        if not isinstance(t, dict):
            raise ValueError("不是 JSON 对象")
    except Exception as e:
        errors.append("tracker.json 无法解析：%s" % e)
        t = {}
    for fn in ["PROTOCOL.md", "CHARTER.md", "STATE.md", "INDEX.md", "NEXT-ACTIONS.md"]:
        if not os.path.isfile(os.path.join(root, fn)):
            errors.append("缺少 %s" % fn)
    for fn, header, label in [("metrics/metrics.csv", METRICS_HEADER, "metrics.csv"),
                              ("metrics/ledger.csv", LEDGER_HEADER, "ledger.csv"),
                              ("metrics/experiments.csv", EXP_HEADER, "experiments.csv")]:
        p = os.path.join(root, fn)
        if not os.path.isfile(p):
            warns.append("缺少 %s（可用 init 重建）" % label)
        else:
            first = read_text(p).splitlines()[:1]
            if first and [c.strip() for c in first[0].split(",")] != header:
                warns.append("%s 表头异常：%s" % (label, first[0]))
    recs = scan_records(root)
    seen = {}
    for r in recs:
        if r["id"] in seen:
            errors.append("ID 重复：%s（%s 与 %s）" % (r["id"], seen[r["id"]], r["path"]))
        seen[r["id"]] = r["path"]
        if not r["date"]:
            warns.append("%s 缺 date 字段" % r["id"])
        if r["type"] in ("problem", "risk", "experiment") and not r["status"]:
            warns.append("%s 缺 status 字段" % r["id"])
    ids = set(seen.keys())
    for d in scan_days(root):
        txt = read_text(day_path(root, d))
        for m in re.finditer(r"`([A-Z]{2,3}-\d{4})`", txt):
            if m.group(1) not in ids:
                warns.append("%s 引用了不存在的档案：%s" % (d, m.group(1)))
    last = t.get("last_entry") or ""
    if last and not t.get("outcome"):
        gap = days_between(last, today_str())
        if gap >= 7:
            warns.append("已停滞 %d 天未记录（最后 %s）-- 补记或 closeout" % (gap, last))
    if not scan_days(root):
        infos.append("尚无日记条目")
    leaks = []
    targets = [os.path.join(root, f) for f in
               ("STATE.md", "INDEX.md", "CHARTER.md", "NEXT-ACTIONS.md", "PROTOCOL.md")]
    targets += [day_path(root, d) for d in scan_days(root)]
    targets += [os.path.join(root, r["path"].replace("/", os.sep)) for r in recs]
    rd = os.path.join(root, "reviews")
    if os.path.isdir(rd):
        targets += [os.path.join(rd, f) for f in os.listdir(rd) if f.endswith(".md")]
    for p in targets:
        if not os.path.isfile(p):
            continue
        txt = read_text(p, limit=2 * 1024 * 1024)
        for pat, label in SECRET_PATTERNS:
            for m in re.finditer(pat, txt):
                snip = m.group(0)
                if len(snip) > 24:
                    snip = snip[:24] + "..."
                leaks.append("%s：%s（%s）" % (rel(root, p), label, snip))
    if leaks:
        errors.append("疑似敏感信息 %d 处：\n    - %s" % (len(leaks), "\n    - ".join(leaks[:12])))
    else:
        infos.append("未发现疑似密钥/隐私")
    opens = [r for r in recs if r["type"] == "problem"
             and (r["status"] or "open") not in ("solved", "closed", "done", "wontfix")]
    infos.append("档案 %d 份，未闭环问题 %d 个" % (len(recs), len(opens)))

    # ---- 结构性问题 = skill 自身的缺陷信号（会自动写入迭代台账）----
    hints = []
    if t.get("schema") != SCHEMA:
        hints.append(("schema", "high", "tracker.schema 与脚本不一致（%s != %s）" % (t.get("schema"), SCHEMA),
                      "tracker.json schema=%s" % t.get("schema")))
    if not t.get("skill_version"):
        hints.append(("schema", "low", "tracker.json 缺少 skill_version 字段（旧版创建）", "tracker.json"))
    elif t["skill_version"] != skill_version():
        hints.append(("schema", "low", "记录目录由 v%s 创建，当前 skill 为 v%s，建议 upgrade"
                      % (t["skill_version"], skill_version()), "tracker.json skill_version"))
    proto_p = os.path.join(root, "PROTOCOL.md")
    if os.path.isfile(proto_p):
        mm = re.search(r"契约版本：v([0-9]+\.[0-9]+\.[0-9]+)", read_text(proto_p))
        if not mm:
            hints.append(("docs", "medium", "PROTOCOL.md 缺少版本标记", "PROTOCOL.md"))
        elif mm.group(1) != skill_version():
            hints.append(("docs", "low", "PROTOCOL.md 契约版本 v%s 落后于 skill v%s" % (mm.group(1), skill_version()),
                          "PROTOCOL.md"))
    for r in recs:
        if not parse_front_matter(r["raw"])[0]:
            hints.append(("bug", "high", "档案缺少 front matter：%s" % r["path"], r["path"]))
    jd = os.path.join(root, "journal")
    if os.path.isdir(jd):
        for fn in os.listdir(jd):
            if fn.endswith(".md") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", fn):
                hints.append(("bug", "medium", "日记文件名不符合 YYYY-MM-DD.md：%s" % fn, "journal/" + fn))
    for fn, header, label in [("metrics/metrics.csv", METRICS_HEADER, "metrics.csv"),
                              ("metrics/ledger.csv", LEDGER_HEADER, "ledger.csv"),
                              ("metrics/experiments.csv", EXP_HEADER, "experiments.csv")]:
        p = os.path.join(root, fn)
        if os.path.isfile(p):
            first = read_text(p).splitlines()[:1]
            if first and [c.strip() for c in first[0].split(",")] != header:
                hints.append(("bug", "high", "%s 表头与脚本定义不一致" % label, first[0]))

    for i in infos:
        say("[INFO] %s" % i)
    for w in warns:
        say("[WARN] %s" % w)
    for e in errors:
        say("[ERROR] %s" % e)
    if hints:
        say("")
        say("检测到 %d 项可能属于 skill 自身的问题（[EVOLVE]）：" % len(hints))
        for cat, sev, title, ev in hints:
            say("  [EVOLVE] (%s/%s) %s" % (cat, sev, title))
            say("           证据：%s" % ev)
        say("  记录方式：journal.py evolve --category <类别> --severity <级别> --title \"...\" --evidence \"...\"")
        if args.auto_evolve:
            for cat, sev, title, ev in hints:
                ent = record_evolve(cat, sev, title, evidence=ev,
                                    repro="lint --root %s" % root, project=(t.get("slug") or ""))
                if ent.get("duplicate"):
                    say("  [EVOLVE] 已有同类记录：%s" % ent["id"])
                else:
                    say("  [EVOLVE] 已自动记录：%s %s" % (ent["id"], ent["title"]))

    if errors:
        say("结果：%d error / %d warn" % (len(errors), len(warns)))
        return 1
    if warns and args.strict:
        say("结果：0 error / %d warn（--strict 下视为失败）" % len(warns))
        return 1
    say("结果：通过（%d warn）" % len(warns))
    return 0


def period_range(period, ref):
    if period == "monthly":
        start = ref.replace(day=1)
        nxt = (start + dt.timedelta(days=32)).replace(day=1)
        end = nxt - dt.timedelta(days=1)
        label = "monthly-%04d-%02d" % (start.year, start.month)
    else:
        start = ref - dt.timedelta(days=ref.weekday())
        end = start + dt.timedelta(days=6)
        y, w, _ = start.isocalendar()
        label = "weekly-%04d-W%02d" % (y, w)
    return start, end, label


def cmd_review(args):
    root = require_root(args)
    t = load_tracker(root)
    start, end, label = period_range(args.period, parse_date(args.date))
    f = collect_facts(root, t)
    in_range = lambda d: start.isoformat() <= d <= end.isoformat()
    L = ["## 周期事实（自动生成 %s）" % now_iso(), "",
         "- 区间：%s ~ %s（%s）" % (start.isoformat(), end.isoformat(), label)]
    any_entry = False
    for d in f["days"]:
        if not in_range(d):
            continue
        for e in parse_daily_entries(read_text(day_path(root, d))):
            any_entry = True
            L.append("- %s %s [%s] %s" % (d, e["time"], e["code"], e["title"]))
    if not any_entry:
        L.append("- （本区间没有日记条目）")
    L.append("")
    for kind, title in [("decision", "本期决策"), ("problem", "本期问题"), ("solution", "本期解法"),
                        ("insight", "本期认知"), ("lesson", "本期教训"), ("experiment", "本期实验")]:
        rs = [r for r in f["records"] if r["type"] == kind and in_range(r["date"])]
        if rs:
            L.append("### %s（%d）" % (title, len(rs)))
            L.append("")
            for r in rs:
                L.append("- %s %s（%s）" % (r["id"], r["title"], r["status"] or "-"))
            L.append("")
    mr = [r for r in f["metrics"] if in_range(r.get("date", ""))]
    if mr:
        first, lastv = {}, {}
        for r in mr:
            first.setdefault(r["metric"], r["value"])
            lastv[r["metric"]] = r["value"]
        L += ["### 指标变化", "", "| 指标 | 期初 | 期末 | 单位 |", "|---|---|---|---|"]
        for k in lastv:
            L.append("| %s | %s | %s | %s |" % (k, first.get(k, "-"), lastv[k], mr[0].get("unit", "")))
        L.append("")
    lr = [r for r in f["ledger"] if in_range(r.get("date", ""))]
    if lr:
        inc = sum(float(r.get("amount") or 0) for r in lr if r.get("kind") == "income")
        cost = sum(float(r.get("amount") or 0) for r in lr if r.get("kind") == "cost")
        L += ["### 收支：收入 %.2f / 成本 %.2f / 净额 %.2f %s"
              % (inc, cost, inc - cost, lr[0].get("currency", "")), ""]
    body = ["# %s 复盘 . %s" % ("周" if args.period == "weekly" else "月", label), "",
            "> 项目：%s . 阶段：%s %s" % (t.get("project"), t.get("stage"), STAGE_NAME.get(t.get("stage", ""), "")),
            "", "\n".join(L), "", "---", "",
            "## 分析（待填写，禁止只写流水账）", "",
            "### 1. 本期最有价值的 3 条（为什么有价值）", "- ",
            "### 2. 卡点与解法（可复用吗）", "- ",
            "### 3. 认知更新（原来的想法 -> 现在的想法 -> 依据）", "- ",
            "### 4. 数字解读（涨/跌的原因，不是复述数字）", "- ",
            "### 5. 下期只做一件最重要的事", "- [ ] ",
            "### 6. 需要止损/放弃的东西", "- ", ""]
    path = os.path.join(root, "reviews", "%s.md" % label)
    if os.path.exists(path) and not args.force:
        say("[跳过] 已存在：%s（用 --force 覆盖）" % rel(root, path))
        return 0
    write_text(path, "\n".join(body))
    say("[OK] 复盘骨架：%s" % rel(root, path))
    say("     请补写「分析」段；自动事实已在其中。")
    return 0


def cmd_closeout(args):
    root = require_root(args)
    t = load_tracker(root)
    outcome = args.outcome
    date = args.date or today_str()
    f = collect_facts(root, t)
    days = days_between(t.get("created", ""), date) + 1
    counts = {}
    for r in f["records"]:
        counts[r["type"]] = counts.get(r["type"], 0) + 1
    trail = " -> ".join("%s %s" % (h.get("to"), h.get("date")) for h in t.get("stage_history", []))
    L = ["# 终局档案 . %s" % t.get("project", ""), "",
         "> 结束日期：%s . 历时：%d 天 . 终局：**%s**" % (date, days, outcome),
         "> 阶段轨迹：%s" % (trail or "-"), "",
         "## 1. 自动事实", "",
         "- 变现假设：%s" % (t.get("hypothesis") or "（未填写）"),
         "- 成功线：%s" % (t.get("success_line") or "（未填写）"),
         "- 止损线：%s" % (t.get("stop_loss") or "（未填写）"),
         "- 是否达到成功线：**待判定**（对照 CHARTER.md 逐条写是/否，禁止含糊）",
         "- 日记 %d 条 . 档案 %d 份 %s" % (f["entry_count"], len(f["records"]),
            ("(" + " ".join("%s%d" % (TYPE_CN.get(k, k), v) for k, v in counts.items()) + ")") if counts else ""),
         ""]
    for cur, tot in f["totals"].items():
        L.append("- %s：收入 %.2f . 成本 %.2f . 净额 %.2f" % (cur, tot["income"], tot["cost"], tot["income"] - tot["cost"]))
    L += ["", "### 关键数字", ""]
    if f["latest"]:
        L += ["| 指标 | 值 | 单位 | 日期 | 来源 |", "|---|---|---|---|---|"]
        for k, r in f["latest"].items():
            L.append("| %s | %s | %s | %s | %s |" % (k, r.get("value"), r.get("unit"), r.get("date"), r.get("source") or "-"))
    else:
        L.append("_无指标记录。_")
    L += ["", "---", "",
          "## 2. 关键转折点（3-5 个，含日期与当时的判断依据）", "- ",
          "", "## 3. 成败归因（要具体到动作，不要写「运气/努力」）",
          "### 做对了什么", "- ", "### 做错了什么", "- ", "### 外部不可控因素", "- ",
          "", "## 4. 可复用打法（下个项目直接抄）", "- ",
          "", "## 5. 不会再做的事（黑名单，附代价）", "- ",
          "", "## 6. 如果重来一次，会怎么改", "- ",
          "", "## 7. 给下一个项目的检查清单", "- [ ] ",
          "", "## 8. 资产化清单",
          "- [ ] 已跑 journal.py publish 生成脱敏资产包",
          "- [ ] 已把 lessons 提炼成一句话（见 LESSONS.md）",
          "- [ ] 已确认无隐私/密钥泄露（lint + _redaction-report.md）",
          "- [ ] 已决定资产形态（案例研究 / 打法手册 / 数据库）与定价",
          "", "## 9. 一句话总结（给未来的自己和 AI）", "> ", ""]
    path = os.path.join(root, "reviews", "closeout-%s.md" % date)
    if os.path.exists(path) and not args.force:
        say("[跳过] 已存在：%s（--force 覆盖）" % rel(root, path))
    else:
        write_text(path, "\n".join(L))
        say("[OK] 终局档案：%s" % rel(root, path))
    t["outcome"] = outcome
    t["outcome_date"] = date
    append_daily(root, t, date, "MS", "项目终局：%s" % outcome,
                 "- 历时 %d 天\n- 依据：%s\n- 终局档案：reviews/closeout-%s.md"
                 % (days, args.note or "对照 CHARTER 成功线/止损线", date), "")
    t["last_entry"] = date
    save_tracker(root, t)
    refresh(root, t)
    say("     下一步：补写终局档案的分析段，然后跑 publish 生成资产包。")
    return 0


def load_sanitize_rules(root):
    rules = [(re.compile(p), "[已脱敏:%s]" % label, label) for p, label in SECRET_PATTERNS]
    p = os.path.join(root, "sanitize.txt")
    if os.path.isfile(p):
        for line in read_text(p).splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=>" not in line:
                continue
            a, b = line.split("=>", 1)
            a, b = a.strip(), b.strip()
            try:
                if a.startswith("re:"):
                    rules.append((re.compile(a[3:].strip()), b, "自定义正则:" + a[3:].strip()[:24]))
                else:
                    rules.append((re.compile(re.escape(a)), b, "自定义:" + a[:24]))
            except re.error as e:
                say("[WARN] 脱敏规则无效已跳过：%s（%s）" % (line, e))
    return rules


def redact(text, rules, counter):
    for rx, rep, label in rules:
        text, n = rx.subn(rep, text)
        if n:
            counter[label] = counter.get(label, 0) + n
    return text


def cmd_publish(args):
    root = require_root(args)
    t = load_tracker(root)
    date = args.date or today_str()
    outdir = os.path.abspath(args.outdir) if args.outdir else os.path.join(root, "publish", date)
    os.makedirs(outdir, exist_ok=True)
    f = collect_facts(root, t)
    rules = [] if args.no_redact else load_sanitize_rules(root)
    counter = {}

    def R(x):
        return x if args.no_redact else redact(x, rules, counter)

    recs = f["records"]
    by_type = {}
    for r in recs:
        by_type.setdefault(r["type"], []).append(r)
    proj = t.get("project", "项目")
    outcome = t.get("outcome") or "进行中（本资产包为阶段性快照）"
    body_of = lambda r: R(body_after_title(r["raw"]))

    cs = ["# %s . 案例研究" % proj, "",
          "> 生成日期：%s . 阶段：%s %s . 终局：%s" % (date, t.get("stage"), STAGE_NAME.get(t.get("stage", ""), ""), outcome),
          "> 数据来源：项目过程记录（原始日记 %d 条 / 档案 %d 份）。数字均来自实际记录，未记录的一律标注为未知。" % (f["entry_count"], len(recs)),
          "", "## 0. 摘要", "",
          "- **做什么**：%s" % (t.get("hypothesis") or "（未记录）"),
          "- **周期**：%s 起，共 %d 天" % (t.get("created", "?"), days_between(t.get("created", ""), date) + 1),
          "- **结果**：%s" % outcome,
          "- **成功线**：%s" % (t.get("success_line") or "（未记录）"),
          "- **止损线**：%s" % (t.get("stop_loss") or "（未记录）"), ""]
    for cur, tot in f["totals"].items():
        cs.append("- **%s 收支**：收入 %.2f / 成本 %.2f / 净额 %.2f" % (cur, tot["income"], tot["cost"], tot["income"] - tot["cost"]))
    cs += ["", "## 1. 阶段时间线", ""]
    if t.get("stage_history"):
        for h in t["stage_history"]:
            cs.append("- **%s**（%s）-> %s . %s" % (h.get("to"), h.get("date"), STAGE_NAME.get(h.get("to", ""), ""), h.get("why") or ""))
    else:
        cs.append("- （无阶段推进记录）")
    cs += ["", "### 里程碑", ""]
    cs += (["- **%s** %s（%s）" % (r["date"], r["title"], r["id"]) for r in by_type.get("milestone", [])] or ["- （无）"])
    cs += ["", "## 2. 关键决策", ""]
    if by_type.get("decision"):
        for r in by_type["decision"]:
            cs += ["### %s %s（%s . %s）" % (r["id"], r["title"], r["date"], r["status"]), "", body_of(r), ""]
    else:
        cs.append("- （无决策档案）")
    cs += ["## 3. 关键认知与讨论", ""]
    if by_type.get("insight"):
        for r in by_type["insight"]:
            cs += ["### %s %s（%s）" % (r["id"], r["title"], r["date"]), "", body_of(r), ""]
    else:
        cs.append("- （无认知更新档案。有价值观点的讨论请用 add --type insight 记录。）")
    cs += ["", "## 4. 遇到的困难与解法", ""]
    problems = by_type.get("problem", [])
    solutions = by_type.get("solution", [])
    paired = set()
    if problems or solutions:
        for p in problems:
            cs += ["### 问题 %s %s（%s）" % (p["id"], p["title"], p["status"] or "open"), "", body_of(p), ""]
            for s in solutions:
                if s["id"] in (p.get("tags", "") + p.get("links", "")) or p["id"] in (s.get("tags", "") + s.get("links", "")):
                    paired.add(s["id"])
                    cs += ["**对应解法 %s %s**" % (s["id"], s["title"]), "", body_of(s), ""]
        for s in solutions:
            if s["id"] not in paired:
                cs += ["### 解法 %s %s" % (s["id"], s["title"]), "", body_of(s), ""]
    else:
        cs.append("- （无问题/解法档案）")
    cs += ["## 5. 实验与数据", ""]
    if by_type.get("experiment"):
        cs += ["| ID | 假设/做法 | 状态 | 开始 |", "|---|---|---|---|"]
        for r in by_type["experiment"]:
            cs.append("| %s | %s | %s | %s |" % (r["id"], r["title"], r["status"], r["date"]))
    else:
        cs.append("- （无实验记录）")
    cs += ["", "### 指标", ""]
    if f["latest"]:
        cs += ["| 指标 | 值 | 单位 | 日期 | 来源 | 置信度 |", "|---|---|---|---|---|---|"]
        for k, r in f["latest"].items():
            cs.append("| %s | %s | %s | %s | %s | %s |" % (R(k), r.get("value"), r.get("unit"), r.get("date"),
                                                            R(r.get("source") or "-"), r.get("confidence")))
    else:
        cs.append("- （无指标）")
    cs += ["", "## 6. 结论与教训", ""]
    cs += (["- **%s** %s" % (r["date"], r["title"]) for r in by_type.get("lesson", [])] or ["- （无教训档案 -> 建议在 closeout 前补齐）"])
    cs += ["", "## 7. 附录：完整时间线（逐日）", ""]
    for d in f["days"]:
        es = parse_daily_entries(read_text(day_path(root, d)))
        if not es:
            continue
        cs += ["### %s" % d, ""]
        for e in es:
            cs.append("- %s [%s] %s%s" % (e["time"], e["code"], R(e["title"]), (" %s" % e["id"]) if e["id"] else ""))
        cs.append("")
    write_text(os.path.join(outdir, "CASE-STUDY.md"), R("\n".join(cs)))

    pb = ["# %s . 打法手册（Playbook）" % proj, "",
          "> 从本项目 %d 份解法档案中提炼的可复用步骤。" % len(solutions), ""]
    if solutions:
        for i, s in enumerate(solutions, 1):
            pb += ["## %d. %s" % (i, s["title"]), "", body_of(s), ""]
    else:
        pb.append("_尚无解法档案。建议在项目过程中遇到并解决困难时用 add --type solution 记录。_")
    write_text(os.path.join(outdir, "PLAYBOOK.md"), R("\n".join(pb)))

    lessons = by_type.get("lesson", [])
    ls = ["# %s . 经验教训清单" % proj, "",
          "> 每条教训都应满足：一句话可复述 . 有代价 . 有适用边界。", ""]
    if lessons:
        for i, r in enumerate(lessons, 1):
            ls += ["## %d. %s" % (i, r["title"]), "",
                   "- 日期：%s . 关联：%s" % (r["date"], refs_display(r.get("links"))), "", body_of(r), ""]
    else:
        ls.append("_尚无教训档案。_")
    insights = by_type.get("insight", [])
    if insights:
        ls += ["## 附：认知更新", ""]
        for r in insights:
            ls.append("- **%s**（%s）：%s" % (r["title"], r["date"], body_of(r).replace("\n", " ")[:300]))
        ls.append("")
    write_text(os.path.join(outdir, "LESSONS.md"), R("\n".join(ls)))

    rows = ["date,metric,value,unit,source,confidence,note"]
    for r in f["metrics"]:
        rows.append(",".join(['"%s"' % R(str(r.get(k, ""))).replace('"', '""') for k in METRICS_HEADER]))
    write_text(os.path.join(outdir, "METRICS.csv"), "\n".join(rows) + "\n")

    lg = ["# %s . 收支与单位经济" % proj, ""]
    if f["totals"]:
        lg += ["| 币种 | 收入 | 成本 | 净额 |", "|---|---|---|---|"]
        for cur, tot in f["totals"].items():
            lg.append("| %s | %.2f | %.2f | %.2f |" % (cur, tot["income"], tot["cost"], tot["income"] - tot["cost"]))
        lg += ["", "## 明细", "", "| 日期 | 类型 | 金额 | 币种 | 渠道 | 备注 |", "|---|---|---|---|---|---|"]
        for r in f["ledger"]:
            lg.append("| %s | %s | %s | %s | %s | %s |" % (r.get("date"), r.get("kind"), r.get("amount"),
                                                           r.get("currency"), R(r.get("channel", "")), R(r.get("note", ""))))
    else:
        lg.append("_尚无收支记录。_")
    write_text(os.path.join(outdir, "LEDGER-SUMMARY.md"), R("\n".join(lg)))

    ps = ["# 商品说明书 . %s 全过程案例" % proj, "",
          "## 这是什么",
          "一份基于真实记录的 %s 全过程档案：从 %s 到 %s，历时 %d 天。" % (proj, t.get("created", "?"), outcome, days_between(t.get("created", ""), date) + 1),
          "", "## 谁需要它",
          "- 正在做同类项目、想少走弯路的人",
          "- 需要真实过程数据（而非成功学）做判断的人",
          "- 需要案例素材的 AI / 研究者 / 内容创作者",
          "", "## 目录", "| 文件 | 内容 |", "|---|---|",
          "| CASE-STUDY.md | 完整案例：背景 . 阶段 . 决策 . 卡点 . 解法 . 结果 |",
          "| PLAYBOOK.md | 可复用打法手册 |",
          "| LESSONS.md | 经验教训清单 |",
          "| METRICS.csv | 脱敏真实数字 |",
          "| LEDGER-SUMMARY.md | 收支与单位经济 |",
          "", "## 卖点（凭记录说话）",
          "- 真实数字：%d 行指标 . %d 行收支" % (len(f["metrics"]), len(f["ledger"])),
          "- 真实决策：%d 个（含被否决的选项与代价）" % len(by_type.get("decision", [])),
          "- 真实失败：%d 个问题 . %d 条教训" % (len(problems), len(lessons)),
          "- 完全脱敏：见 _redaction-report.md",
          "", "## 定价与授权",
          "- 建议定价：待定（参考同类案例单价 / 目标受众支付能力）",
          "- 授权条款：待定（建议：个人学习授权，禁止转售与再分发）",
          "- 联系方式：待定",
          "", "## 数据可信度声明",
          "本文档中所有数字均来自项目过程中的实时记录（含来源与置信度标注）。未记录的推断一律未写入。",
          "", "## 免责声明",
          "结果受时间、市场、个人条件影响，不构成收益承诺。", ""]
    write_text(os.path.join(outdir, "PRODUCT-SHEET.md"), R("\n".join(ps)))

    idx = ["# 资产包索引 . %s（%s）" % (proj, date), "",
           "> 由 journal.py publish 生成。原始记录保留在项目记录目录中，本目录是**脱敏后的对外版本**。", "",
           "## 阅读顺序",
           "1. PRODUCT-SHEET.md -- 这是什么、值不值得读",
           "2. CASE-STUDY.md -- 完整过程",
           "3. LESSONS.md -- 只要教训就看这个",
           "4. PLAYBOOK.md -- 要复用打法看这个",
           "5. METRICS.csv / LEDGER-SUMMARY.md -- 要数据看这个", "",
           "## 溯源",
           "- 源记录目录：%s" % root.replace(os.sep, "/"),
           "- 生成时间：%s" % now_iso(),
           "- 脱敏：%s" % ("已跳过（--no-redact）" if args.no_redact else "已执行，见 _redaction-report.md"), ""]
    write_text(os.path.join(outdir, "INDEX.md"), "\n".join(idx))

    rp = ["# 脱敏报告", "", "生成时间：%s" % now_iso(), "", "| 规则 | 替换次数 |", "|---|---|"]
    if counter:
        for k, v in sorted(counter.items(), key=lambda x: -x[1]):
            rp.append("| %s | %d |" % (k, v))
    else:
        rp.append("| （无需替换） | 0 |")
    rp += ["", "> 规则来源：%s/sanitize.txt + 内置密钥/隐私模式。" % root.replace(os.sep, "/"),
           "> 注意：自动脱敏不能替代人工复核。对外发布前请通读 CASE-STUDY.md 一次。", ""]
    write_text(os.path.join(outdir, "_redaction-report.md"), "\n".join(rp))

    say("[OK] 资产包：%s" % outdir)
    for fn in ["INDEX.md", "PRODUCT-SHEET.md", "CASE-STUDY.md", "LESSONS.md", "PLAYBOOK.md",
               "METRICS.csv", "LEDGER-SUMMARY.md", "_redaction-report.md"]:
        p = os.path.join(outdir, fn)
        if os.path.isfile(p):
            say("     %-22s %6d bytes" % (fn, os.path.getsize(p)))
    if counter and not args.no_redact:
        say("     脱敏替换 %d 类 / %d 处" % (len(counter), sum(counter.values())))
        say("     请人工复核 CASE-STUDY.md 后再对外发布。")
    if not recs:
        say("[WARN] 项目还没有任何档案，资产包内容会很薄 -- 建议先补记决策/问题/教训。")
    return 0


def cmd_vault_index(args):
    root = os.path.abspath(args.root) if args.root else os.getcwd()
    if not os.path.isdir(root):
        die("目录不存在：%s" % root)
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath.count(os.sep) - root.count(os.sep) > 3:
            dirnames[:] = []
            continue
        if "tracker.json" in filenames:
            found.append(dirpath)
            dirnames[:] = []
    if not found:
        die("在 %s 下没找到任何 tracker.json（先在各项目里跑 init）" % root)
    L = ["# VAULT INDEX . 跨项目总览", "",
         "> 由 journal.py vault-index 生成（%s）。" % now_iso(), "",
         "| 项目 | 阶段 | 终局 | 天数 | 最后记录 | 日记 | 档案 | 未闭环 | 收入 | 成本 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for d in sorted(found):
        try:
            t = json.loads(read_text(tracker_path(d)))
        except Exception:
            continue
        ff = collect_facts(d, t)
        opens = len([r for r in ff["records"] if r["type"] == "problem"
                     and (r["status"] or "open") not in ("solved", "closed", "done", "wontfix")])
        inc = sum(v["income"] for v in ff["totals"].values())
        cost = sum(v["cost"] for v in ff["totals"].values())
        L.append("| %s | %s | %s | %d | %s | %d | %d | %d | %.2f | %.2f |" % (
            t.get("project", os.path.basename(d)), t.get("stage", ""), t.get("outcome") or "-",
            days_between(t.get("created", ""), today_str()) + 1, t.get("last_entry") or "-",
            ff["entry_count"], len(ff["records"]), opens, inc, cost))
    L += ["", "## 跨项目观察（待填写）", "",
          "### 反复出现的坑（>=2 个项目都踩过）", "- ",
          "### 最有效的获客/变现动作", "- ",
          "### 平均从想法到第一笔收入：__ 天", "",
          "> 这些跨项目规律就是更高单价的资产（行业数据库/榜单/方法论）。", ""]
    out = os.path.join(root, "VAULT-INDEX.md")
    write_text(out, "\n".join(L))
    say("[OK] 跨项目总览：%s（%d 个项目）" % (out, len(found)))
    return 0


def cmd_evolve(args):
    symptom = ""
    if getattr(args, "body_file", None):
        if not os.path.isfile(args.body_file):
            die("--body-file 不存在：%s" % args.body_file)
        symptom = read_text(args.body_file).strip()
    if not symptom and args.symptom:
        symptom = args.symptom
    ent = record_evolve(args.category, args.severity, args.title, symptom=symptom,
                        evidence=args.evidence, repro=args.repro, project=args.project or "",
                        status=args.status, explicit_ledger=args.ledger_dir, force=args.force)
    if ent.get("duplicate"):
        say("[跳过] 同类问题已存在：%s %s（status=%s）；确实要重复记录请加 --force"
            % (ent["id"], ent["title"], ent["status"]))
        return 0
    say("[OK] 已记录 %s（%s/%s）：%s" % (ent["id"], ent["category"], ent["severity"], ent["title"]))
    say("     台账目录：%s" % ledger_dir(args.ledger_dir).replace(os.sep, "/"))
    if ent["severity"] in ("critical", "high"):
        say("     [注意] 高严重度问题应尽快按 references/08-self-evolution.md 修复，并跑 selftest。")
    return 0


def cmd_evolve_list(args):
    led = load_ledger(args.ledger_dir)
    ents = led.get("entries", [])
    if args.status:
        ents = [x for x in ents if x.get("status") == args.status]
    if args.json:
        say(json.dumps(ents, ensure_ascii=False, indent=2))
        return 0
    if not ents:
        say("（无匹配条目）")
        return 0
    say("%-8s %-10s %-9s %-11s %s" % ("ID", "类别", "严重度", "状态", "标题"))
    for x in ents:
        say("%-8s %-10s %-9s %-11s %s" % (x.get("id"), x.get("category"), x.get("severity"),
                                          x.get("status"), x.get("title")))
    say("")
    say("共 %d 条 . 未修复 %d 条 . 当前 skill 版本 v%s"
        % (len(ents), len([x for x in ents if x.get("status") in ("open", "proposed", "in-progress")]),
           skill_version()))
    return 0


def cmd_evolve_apply(args):
    led = load_ledger(args.ledger_dir)
    ent = None
    for x in led.get("entries", []):
        if x.get("id") == args.id:
            ent = x
            break
    if not ent:
        die("台账中找不到 %s（用 journal.py evolve-list 查看）" % args.id)
    if ent.get("status") == "applied" and not args.force:
        say("[跳过] %s 已是 applied（v%s）" % (args.id, ent.get("version")))
        return 0
    if not args.summary:
        die("必须提供 --summary，写清这次改了什么、为什么（会写进 CHANGELOG）")
    if not args.no_selftest:
        st = os.path.join(HERE, "selftest.py")
        if os.path.isfile(st):
            say(">> 回归自测（自测不通过则不改版本号、不标记 applied）...")
            code = subprocess.call([sys.executable, st])
            if code != 0:
                say("[ERROR] 自测失败（exit=%d），已中止。修好再跑一次。" % code)
                return 1
        else:
            say("[WARN] 未找到 scripts/selftest.py，跳过自测（不推荐）")
    cur = skill_version()
    new_ver = bump_version(cur, args.bump)
    m = skill_manifest()
    m["version"] = new_ver
    m["updated"] = today_str()
    write_text(os.path.join(SKILL_DIR, "manifest.json"), json.dumps(m, ensure_ascii=False, indent=2) + "\n")
    entry = ("## [%s] - %s\n"
             "- %s（%s）\n"
             "- 类别 / 严重度：%s / %s\n"
             "- 台账：evolution/LEDGER.md 的 %s\n\n") % (
        new_ver, today_str(), args.summary, args.id, ent.get("category"), ent.get("severity"), args.id)
    chp = os.path.join(SKILL_DIR, "CHANGELOG.md")
    old = read_text(chp)
    if "<!-- CHANGELOG:INSERT -->" in old:
        new = old.replace("<!-- CHANGELOG:INSERT -->", "<!-- CHANGELOG:INSERT -->\n\n" + entry.rstrip("\n"), 1)
    elif old:
        new = old.rstrip("\n") + "\n\n" + entry
    else:
        new = "# CHANGELOG . project-journal\n\n" + entry
    write_text(chp, new)
    ent["status"] = "applied"
    ent["version"] = new_ver
    ent["resolution_date"] = today_str()
    ent["fix"] = args.summary
    save_ledger(led, args.ledger_dir)
    say("[OK] %s -> applied（v%s -> v%s），CHANGELOG 已更新。" % (args.id, cur, new_ver))
    say("     若改动涉及记录格式/字段，请对已有项目跑：journal.py upgrade --root <记录目录>")
    say("     若改动涉及 SKILL.md 的流程，请同步更新 references/ 与本文档说明。")
    return 0


def cmd_doctor(args):
    fails, warns = [], []
    need = ["SKILL.md", "manifest.json", "CHANGELOG.md", "scripts/journal.py", "scripts/selftest.py",
            "references/00-protocol.md", "references/01-taxonomy.md", "references/02-writing-guide.md",
            "references/03-cadence.md", "references/04-monetization.md", "references/05-closeout.md",
            "references/06-digital-asset.md", "references/07-troubleshooting.md",
            "references/08-self-evolution.md",
            "templates/CHARTER.md", "templates/NEXT-ACTIONS.md", "templates/records.md",
            "templates/daily-entry.md"]
    for fn in need:
        if not os.path.isfile(os.path.join(SKILL_DIR, fn)):
            fails.append("缺少文件：" + fn)
    ver = skill_version()
    m = skill_manifest()
    if not m.get("version"):
        fails.append("manifest.json 缺少 version")
    ch = read_text(os.path.join(SKILL_DIR, "CHANGELOG.md"))
    mtop = re.search(r"^##\s*\[([0-9]+\.[0-9]+\.[0-9]+)\]", ch, re.M)
    if not mtop:
        warns.append("CHANGELOG.md 中找不到版本条目")
    elif mtop.group(1) != ver:
        fails.append("版本不一致：manifest=%s / CHANGELOG=%s" % (ver, mtop.group(1)))
    sm = read_text(os.path.join(SKILL_DIR, "SKILL.md"))
    for ref in sorted(set(re.findall(r"references/([0-9A-Za-z_\-]+\.md)", sm))):
        if not os.path.isfile(os.path.join(SKILL_DIR, "references", ref)):
            fails.append("SKILL.md 引用了不存在的文件：references/" + ref)
    import py_compile
    for fn in ["scripts/journal.py", "scripts/selftest.py"]:
        p = os.path.join(SKILL_DIR, fn)
        if os.path.isfile(p):
            try:
                py_compile.compile(p, cfile=os.path.join(tempfile.gettempdir(), "pj_doctor_check.pyc"), doraise=True)
            except Exception as e:
                fails.append("%s 语法错误：%s" % (fn, e))
    led = load_ledger(None)
    ents = led.get("entries", [])
    openn = [x for x in ents if x.get("status") in ("open", "proposed", "in-progress")]
    for f in fails:
        say("[FAIL] %s" % f)
    for w in warns:
        say("[WARN] %s" % w)
    say("[INFO] 版本 v%s . 台账 %d 条（未修复 %d 条）" % (ver, len(ents), len(openn)))
    if openn:
        say("[INFO] 未修复优先级最高的一条：%s %s（%s/%s）" % (
            openn[0].get("id"), openn[0].get("title"), openn[0].get("category"), openn[0].get("severity")))
    say("结果：%s" % (("不通过（%d 项问题）" % len(fails)) if fails else "通过"))
    return 1 if fails else 0


def cmd_upgrade(args):
    root = require_root(args)
    t = load_tracker(root)
    changes = []
    old_ver = t.get("skill_version") or "0.0.0"
    if t.get("schema") != SCHEMA:
        changes.append("schema %s -> %s" % (t.get("schema"), SCHEMA))
        t["schema"] = SCHEMA
    for k, v in [("counters", {}), ("stage_history", []), ("upgrades", [])]:
        if k not in t:
            t[k] = v
            changes.append("补充字段 " + k)
    proto = os.path.join(root, "PROTOCOL.md")
    src = read_text(os.path.join(SKILL_DIR, "references", "00-protocol.md"))
    if src:
        new_body = src.replace("{PROJECT}", t.get("project", "")).replace("{VERSION}", skill_version())
        if not os.path.isfile(proto):
            write_text(proto, new_body)
            t["protocol_hash"] = text_hash(new_body)
            changes.append("重建 PROTOCOL.md")
        else:
            cur = read_text(proto)
            if cur == new_body:
                t["protocol_hash"] = text_hash(new_body)
            elif args.keep_protocol:
                write_text(proto + ".new", new_body)
                changes.append("PROTOCOL.md 保留原文件，新版写入 PROTOCOL.md.new（--keep-protocol）")
                t["protocol_hash"] = text_hash(cur)
            else:
                mv = re.search(r"契约版本：v([0-9]+\.[0-9]+\.[0-9]+)", cur)
                bak = proto + ".bak-v%s" % (mv.group(1) if mv else "old")
                write_text(bak, cur)
                write_text(proto, new_body)
                changes.append("PROTOCOL.md 升级到契约 v%s（旧版已备份为 %s）"
                               % (skill_version(), os.path.basename(bak)))
                t["protocol_hash"] = text_hash(new_body)
        t["protocol_version"] = skill_version()
    t["skill_version"] = skill_version()
    t.setdefault("upgrades", []).append({"date": args.date or today_str(), "from": old_ver,
                                         "to": skill_version(), "changes": changes})
    save_tracker(root, t)
    target, action = inject_anchor(root, t, args.project_root, args.anchor)
    refresh(root, t)
    say("[OK] 记录目录已升级：v%s -> v%s" % (old_ver, skill_version()))
    for c in changes:
        say("     - %s" % c)
    if not changes:
        say("     （无需结构性改动，仅刷新 STATE/INDEX 与锚点）")
    if target:
        say("[OK] %s锚点：%s" % (action, target))
    say("     升级只动 tracker.json / PROTOCOL.md / AGENTS.md 锚点，**不改写任何日记与档案**。")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="journal.py", description="project-journal 项目全过程跟踪引擎")
    p.add_argument("--version", action="version", version="project-journal v%s" % skill_version())
    sub = p.add_subparsers(dest="cmd")

    def add(name, help_text):
        s = sub.add_parser(name, help=help_text)
        s.add_argument("--root", help="记录根目录")
        s.add_argument("--date", help="日期 YYYY-MM-DD（默认今天）")
        return s

    s = add("init", "建立记录目录（幂等，可重复执行）")
    s.add_argument("--project")
    s.add_argument("--slug")
    s.add_argument("--stage", default="S0")
    s.add_argument("--currency", default="USD")
    s.add_argument("--hypothesis", default="")
    s.add_argument("--success", default="")
    s.add_argument("--stop-loss", dest="stop_loss", default="")
    s.add_argument("--project-root", dest="project_root")
    s.add_argument("--anchor")
    s.add_argument("--force", action="store_true")

    s = add("anchor", "重新注入/刷新会话锚点")
    s.add_argument("--project-root", dest="project_root")
    s.add_argument("--anchor")

    s = add("status", "一行体检")
    s.add_argument("--json", action="store_true")

    s = add("resume", "生成补液包（新会话开工先跑）")
    s.add_argument("--max-chars", dest="max_chars", type=int, default=14000)

    s = add("add", "追加一条记录")
    s.add_argument("--type", required=True, help="|".join(TYPE_CODE.keys()))
    s.add_argument("--title", default="")
    s.add_argument("--body-file", dest="body_file")
    s.add_argument("--tags", default="")
    s.add_argument("--link", default="")
    s.add_argument("--status", default="")
    s.add_argument("--confidence", default="medium")
    s.add_argument("--id", default="")

    s = add("update", "更新已有档案（状态/追加内容）")
    s.add_argument("--id", required=True)
    s.add_argument("--status", default="")
    s.add_argument("--append-file", dest="append_file")
    s.add_argument("--result", default="")

    s = add("metric", "记录一个指标")
    s.add_argument("--name", required=True)
    s.add_argument("--value", required=True)
    s.add_argument("--unit", default="")
    s.add_argument("--source", default="")
    s.add_argument("--confidence", default="medium")
    s.add_argument("--note", default="")

    s = add("ledger", "记录一笔收入/成本")
    s.add_argument("--kind", required=True, help="income|cost")
    s.add_argument("--amount", required=True)
    s.add_argument("--currency", default="")
    s.add_argument("--channel", default="")
    s.add_argument("--note", default="")

    s = add("stage", "推进阶段")
    s.add_argument("--set", required=True, help="S0-S6")
    s.add_argument("--why", default="")

    add("index", "重建 STATE.md / INDEX.md")

    s = add("lint", "体检：结构/ID/敏感信息/停滞/自我迭代信号")
    s.add_argument("--strict", action="store_true")
    s.add_argument("--auto-evolve", dest="auto_evolve", action="store_true",
                   help="把检测到的结构性问题自动写入 skill 迭代台账")

    s = add("review", "生成周/月复盘骨架")
    s.add_argument("--period", default="weekly", choices=["weekly", "monthly"])
    s.add_argument("--force", action="store_true")

    s = add("closeout", "终局档案 + 成败判定")
    s.add_argument("--outcome", required=True, choices=OUTCOMES)
    s.add_argument("--title", default="")
    s.add_argument("--note", default="")
    s.add_argument("--force", action="store_true")

    s = add("publish", "生成脱敏资产包")
    s.add_argument("--outdir")
    s.add_argument("--no-redact", dest="no_redact", action="store_true")
    s.add_argument("--force", action="store_true")

    s = add("upgrade", "把已有记录目录迁移到当前 skill 版本（不动日记与档案）")
    s.add_argument("--project-root", dest="project_root")
    s.add_argument("--anchor")
    s.add_argument("--keep-protocol", dest="keep_protocol", action="store_true",
                   help="不覆盖 PROTOCOL.md，把新版写成 PROTOCOL.md.new（默认会备份后刷新）")

    s = add("evolve", "记录 skill 自身的问题/改进（自我迭代台账）")
    s.add_argument("--category", required=True, choices=EVOLVE_CATEGORIES)
    s.add_argument("--severity", required=True, choices=EVOLVE_SEVERITIES)
    s.add_argument("--title", required=True)
    s.add_argument("--body-file", dest="body_file")
    s.add_argument("--symptom", default="")
    s.add_argument("--evidence", default="")
    s.add_argument("--repro", default="")
    s.add_argument("--project", default="")
    s.add_argument("--status", default="open", choices=EVOLVE_STATUSES)
    s.add_argument("--ledger-dir", dest="ledger_dir")
    s.add_argument("--force", action="store_true")

    s = add("evolve-list", "查看迭代台账")
    s.add_argument("--status", default="", choices=[""] + EVOLVE_STATUSES)
    s.add_argument("--json", action="store_true")
    s.add_argument("--ledger-dir", dest="ledger_dir")

    s = add("evolve-apply", "标记已修复：跑自测 -> 升版本 -> 写 CHANGELOG")
    s.add_argument("--id", required=True)
    s.add_argument("--summary", default="")
    s.add_argument("--bump", default="patch", choices=["patch", "minor", "major"])
    s.add_argument("--ledger-dir", dest="ledger_dir")
    s.add_argument("--no-selftest", dest="no_selftest", action="store_true")
    s.add_argument("--force", action="store_true")

    s = add("doctor", "skill 安装自检（文件/版本/语法/台账）")

    s = sub.add_parser("vault-index", help="跨项目总览")
    s.add_argument("--root")
    return p


HANDLERS = {
    "init": cmd_init, "anchor": cmd_anchor, "status": cmd_status, "resume": cmd_resume,
    "add": cmd_add, "update": cmd_update, "metric": cmd_metric, "ledger": cmd_ledger,
    "stage": cmd_stage, "index": cmd_index, "lint": cmd_lint, "review": cmd_review,
    "closeout": cmd_closeout, "publish": cmd_publish, "vault-index": cmd_vault_index,
    "upgrade": cmd_upgrade, "evolve": cmd_evolve, "evolve-list": cmd_evolve_list,
    "evolve-apply": cmd_evolve_apply, "doctor": cmd_doctor,
}


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    p = build_parser()
    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help()
        return 0
    try:
        return HANDLERS[args.cmd](args) or 0
    except SystemExit:
        raise
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        tb = traceback.format_exc()
        say("[CRASH] 命令 %s 执行异常：%s" % (args.cmd, exc))
        say(tb)
        cmdline = "journal.py " + " ".join(sys.argv[1:])
        try:
            ent = record_evolve("bug", "high",
                                "命令 %s 崩溃：%s" % (args.cmd, str(exc).splitlines()[0][:60]),
                                symptom=tb[-4000:], evidence=cmdline, repro=cmdline,
                                project=getattr(args, "root", "") or "",
                                explicit_ledger=getattr(args, "ledger_dir", None))
            if ent.get("duplicate"):
                say("[EVOLVE] 该崩溃已有记录：%s（%s）" % (ent["id"], ent["title"]))
            else:
                say("[EVOLVE] 已自动记录崩溃：%s（%s）" % (ent["id"], ent["title"]))
            say("[EVOLVE] 修复闭环见 references/08-self-evolution.md")
        except Exception as exc2:
            say("[EVOLVE] 自动记录失败（%s），请手工执行 journal.py evolve" % exc2)
        return CRASH_EXIT


if __name__ == "__main__":
    sys.exit(main())
