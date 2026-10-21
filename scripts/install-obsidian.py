#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install-obsidian.py -- 检测 / 静默安装 Obsidian（Windows 优先，D 盘优先）。

设计原则：
  1) 只从 Obsidian 官方 GitHub Releases 下载，下载后做 Authenticode 验签。
  2) 优先装到 D:\\Obsidian；只有一个分区或 D 不可写时回退默认盘。
  3) 新版 Obsidian 是 NSIS 安装器，优先 /S /currentuser /D=<目标>；
     若安装器忽略 /D，则把默认安装目录移动到 D 盘并在原位置建 junction。
  4) 不做全局提权；per-user 安装，失败时保留默认安装并明确告警。
  5) 状态写入 ~/.project-journal/obsidian.json，供 journal.py / setup.py 复用。

用法：
  python install-obsidian.py --check
  python install-obsidian.py --dry-run --version 1.14.4
  python install-obsidian.py --yes
  python install-obsidian.py --yes --install-dir "D:\\Obsidian"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

SCRIPT_VERSION = "1.0.0"
MIN_VERSION = "1.8.0"
REPO = "obsidianmd/obsidian-releases"
STATE_DIR = os.path.join(os.path.expanduser("~"), ".project-journal")
STATE_PATH = os.environ.get("PJ_OBSIDIAN_STATE") or os.path.join(STATE_DIR, "obsidian.json")
JSON_MODE = False


def log(msg=""):
    print(msg, file=sys.stderr if JSON_MODE else sys.stdout)


def emit(obj):
    if JSON_MODE:
        print(json.dumps(obj, ensure_ascii=False, indent=2))


def is_windows():
    return os.name == "nt"


def norm(p):
    return os.path.normcase(os.path.abspath(os.path.expanduser(p))) if p else ""


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _run(cmd, timeout=60, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="ignore",
                              timeout=timeout, **kw)
    except Exception as exc:
        class R:
            returncode = -1
            stdout = ""
            stderr = str(exc)
        return R()


def _file_version(path):
    if is_windows():
        q = path.replace("'", "''")
        r = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                  "(Get-Item -LiteralPath '%s').VersionInfo.FileVersion" % q], timeout=15)
        m = re.search(r"\d+\.\d+\.\d+", r.stdout or "")
        return m.group(0) if m else (r.stdout or "").strip()
    if sys.platform == "darwin":
        r = _run(["defaults", "read", path, "CFBundleShortVersionString"], timeout=10)
        return (r.stdout or "").strip()
    return ""


def _reg_value(key, name):
    try:
        import winreg
        v, _ = winreg.QueryValueEx(key, name)
        return v
    except Exception:
        return ""


def registry_entries():
    """从 HKCU/HKLM 卸载项与旧版 HKCU\\SOFTWARE\\obsidian 找安装位置。"""
    if not is_windows():
        return []
    import winreg
    out = []
    views = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, base in views:
        try:
            root = winreg.OpenKey(hive, base)
        except OSError:
            continue
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(root, i)
            except OSError:
                break
            i += 1
            try:
                k = winreg.OpenKey(root, sub)
                name = str(_reg_value(k, "DisplayName") or "")
                if "obsidian" not in name.lower():
                    continue
                loc = str(_reg_value(k, "InstallLocation") or "").strip().strip('"')
                ver = str(_reg_value(k, "DisplayVersion") or "").strip()
                un = str(_reg_value(k, "UninstallString") or "").strip()
                if not loc and un:
                    m = re.match(r'^"([^"]+)"', un)
                    if m:
                        un = m.group(1)
                    else:
                        un = un.split(" /")[0].strip().strip('"')
                    loc = os.path.dirname(un)
                if loc.lower().endswith(".exe"):
                    loc = os.path.dirname(loc)
                if loc:
                    out.append({"path": os.path.join(loc, "Obsidian.exe"),
                                "install_dir": loc, "version": ver,
                                "source": "registry:%s" % name})
            except OSError:
                pass
    # 旧版 Squirrel
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            k = winreg.OpenKey(hive, r"SOFTWARE\obsidian")
            loc = str(_reg_value(k, "InstallLocation") or "").strip()
            ver = str(_reg_value(k, "DisplayVersion") or "").strip()
            if loc:
                out.append({"path": os.path.join(loc, "Obsidian.exe"),
                            "install_dir": loc, "version": ver,
                            "source": "registry:SOFTWARE\\obsidian"})
        except OSError:
            pass
    return out


def candidate_paths():
    out = []
    if is_windows():
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            out += [os.path.join(local, "Programs", "Obsidian", "Obsidian.exe"),
                    os.path.join(local, "Obsidian", "Obsidian.exe")]
        for pf in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if pf:
                out.append(os.path.join(pf, "Obsidian", "Obsidian.exe"))
        out += [r"D:\Obsidian\Obsidian.exe", r"D:\Programs\Obsidian\Obsidian.exe",
                r"D:\Program Files\Obsidian\Obsidian.exe",
                r"D:\Program Files (x86)\Obsidian\Obsidian.exe"]
    elif sys.platform == "darwin":
        out += ["/Applications/Obsidian.app/Contents/MacOS/Obsidian",
                os.path.expanduser("~/Applications/Obsidian.app/Contents/MacOS/Obsidian")]
    else:
        w = shutil.which("obsidian")
        if w:
            out.append(w)
        out += ["/usr/bin/obsidian", "/opt/Obsidian/obsidian",
                "/snap/bin/obsidian"]
    return out


def _as_install(path):
    if not path:
        return None
    p = os.path.expanduser(path)
    if sys.platform == "darwin" and p.endswith(".app"):
        exe = os.path.join(p, "Contents", "MacOS", "Obsidian")
        root = p
    elif p.lower().endswith(".exe") or (os.path.isfile(p) and
                                        os.path.basename(p).lower() == "obsidian"):
        exe = p
        root = os.path.dirname(p)
    else:
        exe = os.path.join(p, "Obsidian.exe") if is_windows() else os.path.join(p, "obsidian")
        root = p
    if os.path.isfile(exe):
        return {"path": exe, "install_dir": root, "version": _file_version(exe)}
    return None


def detect():
    """返回 {installed, path, install_dir, version, source}。"""
    seen = set()
    # 1) 上次安装状态
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            st = json.load(f)
        for key in ("path", "install_dir"):
            p = st.get(key)
            got = _as_install(p)
            if got and norm(got["path"]) not in seen:
                got.update(version=st.get("version") or got.get("version") or "",
                           source="state")
                return {"installed": True, **got}
    except Exception:
        pass
    # 2) 注册表
    for ent in registry_entries():
        got = _as_install(ent.get("install_dir") or ent.get("path"))
        if got and norm(got["path"]) not in seen:
            seen.add(norm(got["path"]))
            got["version"] = ent.get("version") or got.get("version") or ""
            got["source"] = ent.get("source") or "registry"
            return {"installed": True, **got}
    # 3) 常见路径
    for p in candidate_paths():
        got = _as_install(p)
        if got and norm(got["path"]) not in seen:
            got["source"] = "path"
            return {"installed": True, **got}
    return {"installed": False, "path": "", "install_dir": "", "version": "", "source": ""}


def _drive_type(path):
    if not is_windows():
        return 0
    try:
        import ctypes
        root = os.path.splitdrive(os.path.abspath(path))[0] + "\\"
        return int(ctypes.windll.kernel32.GetDriveTypeW(root))
    except Exception:
        return 0


def _writable(path):
    try:
        os.makedirs(path, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".pj-write-", dir=path)
        os.close(fd)
        os.unlink(tmp)
        return True
    except Exception:
        return False


def choose_install_dir(requested=None):
    """返回 (目标目录, 原因)。Windows 优先 D:\\Obsidian。"""
    if requested:
        p = os.path.abspath(os.path.expanduser(requested))
        if p.lower().endswith(".exe"):
            p = os.path.dirname(p)
        return p, "用户指定"
    if is_windows():
        d = "D:\\Obsidian"
        try:
            free = shutil.disk_usage("D:\\").free
        except Exception:
            free = 0
        if _drive_type("D:\\") == 3 and free > 2 * 1024 ** 3 and _writable("D:\\"):
            return d, "D 盘为固定磁盘，可用 %.1f GB" % (free / 1024 ** 3)
        local = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(local, "Programs", "Obsidian"), \
            "D 盘不可用/空间不足，回退默认盘"
    if sys.platform == "darwin":
        return os.path.expanduser("~/Applications/Obsidian.app"), "macOS 默认目录"
    return "", "非 Windows 系统不自动安装"


def http_json(url, timeout=40):
    req = urllib.request.Request(url, headers={
        "User-Agent": "project-journal-setup/%s" % SCRIPT_VERSION})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r), r.geturl()


def release_info(version=""):
    """返回 {version, url, size, source}。不下载。"""
    version = (version or "").strip().lstrip("v")
    if version:
        url = "https://github.com/%s/releases/download/v%s/Obsidian-%s.exe" % (REPO, version, version)
        return {"version": version, "url": url, "size": 0, "source": "explicit"}
    try:
        data, final = http_json("https://api.github.com/repos/%s/releases/latest" % REPO)
        tag = str(data.get("tag_name") or "").lstrip("v")
        best = None
        for a in data.get("assets", []):
            name = str(a.get("name") or "")
            m = re.fullmatch(r"Obsidian-(\d+\.\d+\.\d+)\.exe", name, re.I)
            if not m:
                continue
            if any(x in name.lower() for x in ("arm64", "allusers", "legacy", "32")):
                continue
            if not best or tuple(map(int, m.group(1).split("."))) > tuple(map(int, best["version"].split("."))):
                best = {"version": m.group(1), "url": a.get("browser_download_url"),
                        "size": int(a.get("size") or 0), "source": "github-api"}
        if best:
            return best
        if tag:
            return {"version": tag,
                    "url": "https://github.com/%s/releases/download/v%s/Obsidian-%s.exe" % (REPO, tag, tag),
                    "size": 0, "source": "github-api-tag"}
    except Exception as exc:
        log("[WARN] GitHub API 不可用：%s" % exc)
    # 回退：跟随 latest 重定向
    try:
        req = urllib.request.Request("https://github.com/%s/releases/latest" % REPO,
                                     method="HEAD", headers={"User-Agent": "project-journal-setup"})
        with urllib.request.urlopen(req, timeout=30) as r:
            final = r.geturl()
        tag = final.rstrip("/").split("/")[-1].lstrip("v")
        if re.fullmatch(r"\d+\.\d+\.\d+", tag):
            return {"version": tag,
                    "url": "https://github.com/%s/releases/download/v%s/Obsidian-%s.exe" % (REPO, tag, tag),
                    "size": 0, "source": "github-redirect"}
    except Exception as exc:
        log("[WARN] 获取最新版本失败：%s" % exc)
    return {"version": "", "url": "", "size": 0, "source": ""}


def download(url, dest, expected_size=0):
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    part = dest + ".part"
    h = hashlib.sha256()
    got = 0
    req = urllib.request.Request(url, headers={"User-Agent": "project-journal-setup"})
    with urllib.request.urlopen(req, timeout=90) as r, open(part, "wb") as f:
        total = int(r.headers.get("Content-Length") or expected_size or 0)
        last_pct = -1
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            got += len(chunk)
            if total:
                pct = int(got * 100 / total)
                if pct >= last_pct + 10:
                    last_pct = pct
                    log("  下载 %3d%%  %.1f / %.1f MB" % (pct, got / 1024 ** 2, total / 1024 ** 2))
    if expected_size and got != expected_size:
        try:
            os.unlink(part)
        except OSError:
            pass
        raise RuntimeError("下载大小不符：%d != %d" % (got, expected_size))
    os.replace(part, dest)
    return {"size": got, "sha256": h.hexdigest()}


def trusted_signer(subject):
    """官方签名主体是 Dynalist Inc（Obsidian 母公司）；兼容含 Obsidian 的证书。"""
    s = (subject or "").lower()
    return "obsidian" in s or "dynalist" in s


def verify_signature(path):
    """Windows Authenticode 验签。返回签名主体。"""
    if not is_windows():
        return ""
    q = path.replace("'", "''")
    ps = (
        "$s = Get-AuthenticodeSignature -LiteralPath '%s'; "
        "if ($s.Status -ne 'Valid') { Write-Output ('INVALID|' + $s.Status); exit 2 }; "
        "Write-Output ('OK|' + $s.SignerCertificate.Subject)" % q
    )
    r = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], timeout=120)
    out = (r.stdout or "").strip()
    if out.startswith("INVALID|"):
        raise RuntimeError("安装包签名无效：%s" % out.split("|", 1)[1])
    if not out.startswith("OK|"):
        raise RuntimeError("无法验证安装包签名：%s" % (out or r.stderr or "unknown"))
    subject = out.split("|", 1)[1].strip()
    if not trusted_signer(subject):
        raise RuntimeError("签名主体不是 Obsidian/Dynalist：%s" % subject)
    return subject


def installer_kind(path):
    """粗判 NSIS / Squirrel，用于选择静默参数。"""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            head = f.read(4 * 1024 * 1024)
            f.seek(max(0, size - 4 * 1024 * 1024))
            tail = f.read(4 * 1024 * 1024)
        low = (head + tail).lower()
        if b"nullsoft" in low or b"nsis" in low:
            return "nsis"
        if b"squirrel" in low:
            return "squirrel"
    except Exception:
        pass
    return "unknown"


def _exists_install(path):
    if not path:
        return False
    exe = os.path.join(path, "Obsidian.exe") if is_windows() else path
    try:
        return os.path.isfile(exe) and os.path.getsize(exe) > 1024 * 1024
    except OSError:
        return False


def wait_for_install(target="", timeout=300):
    """轮询安装结果；返回 (安装目录, 是否落在目标目录)。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if target and _exists_install(target):
            return target, True
        got = detect()
        if got.get("installed"):
            return got.get("install_dir") or os.path.dirname(got.get("path", "")), \
                bool(target and norm(got.get("install_dir", "")) == norm(target))
        time.sleep(1.5)
    return "", False


def _rmtree(path):
    def onerr(func, p, exc):
        try:
            os.chmod(p, 0o700)
            func(p)
        except Exception:
            pass
    shutil.rmtree(path, onerror=onerr)


def _obsidian_running():
    if not is_windows():
        return False
    r = _run(["tasklist", "/FI", "IMAGENAME eq Obsidian.exe"], timeout=15)
    return "obsidian.exe" in (r.stdout or "").lower()


def relocate(src, dst):
    """把默认安装目录移动到 dst，并在 src 建 junction。"""
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    if norm(src) == norm(dst):
        return {"method": "direct", "install_dir": dst}
    if os.path.isdir(src) and (os.path.islink(src) or
                               getattr(os.path, "isjunction", lambda p: False)(src)):
        if norm(os.path.realpath(src)) == norm(os.path.realpath(dst)):
            return {"method": "junction", "install_dir": dst}
    if not _exists_install(src):
        raise RuntimeError("找不到默认安装目录：%s" % src)
    if _obsidian_running():
        raise RuntimeError("Obsidian 正在运行，请退出后重试")
    if os.path.exists(dst):
        if _exists_install(dst):
            return {"method": "direct", "install_dir": dst}
        if os.listdir(dst):
            raise RuntimeError("目标目录非空且不像 Obsidian：%s" % dst)
        os.rmdir(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    need = 0
    for base, _dirs, files in os.walk(src):
        for fn in files:
            try:
                need += os.path.getsize(os.path.join(base, fn))
            except OSError:
                pass
    if shutil.disk_usage(os.path.dirname(dst) or dst).free < need * 1.15:
        raise RuntimeError("目标盘空间不足：需要 %.1f MB" % (need / 1024 ** 2))
    log("  移动 %s -> %s（约 %.1f MB）" % (src, dst, need / 1024 ** 2))
    copied = False
    try:
        shutil.copytree(src, dst)
        copied = True
        if not _exists_install(dst):
            raise RuntimeError("复制后校验失败")
        _rmtree(src)
    except Exception:
        # 复制/校验失败时清掉半成品，避免下次误判“目标目录非空”
        try:
            if os.path.isdir(dst) and (not copied or not _exists_install(dst)):
                _rmtree(dst)
        except Exception:
            pass
        raise
    r = _run(["cmd", "/c", "mklink", "/J", src, dst], timeout=30)
    if r.returncode != 0 or not _exists_install(src):
        # 回滚
        try:
            if os.path.isdir(src):
                _rmtree(src)
            if os.path.isdir(dst):
                shutil.move(dst, src)
        except Exception:
            pass
        raise RuntimeError("创建 junction 失败：%s" % (r.stderr or r.stdout or "").strip())
    return {"method": "junction", "install_dir": dst}


def write_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, STATE_PATH)


def build_plan(args):
    got = detect()
    target, reason = choose_install_dir(args.install_dir)
    rel = release_info(args.version) if (args.version or not got.get("installed")) else {}
    return {"installed": got, "target": target, "target_reason": reason, "release": rel}


def install(args):
    got = detect()
    if got.get("installed") and not args.force:
        log("[OK] Obsidian 已安装：%s（%s）" % (got.get("path"), got.get("version") or "版本未知"))
        return {"ok": True, "already": True, "install": got}
    if not is_windows():
        raise RuntimeError("自动安装目前仅支持 Windows；请从 https://obsidian.md 手动安装")
    target, reason = choose_install_dir(args.install_dir)
    log("[INFO] 目标目录：%s（%s）" % (target, reason))
    rel = release_info(args.version)
    if not rel.get("url"):
        raise RuntimeError("无法确定 Obsidian 下载地址")
    log("[INFO] 版本：%s" % (rel.get("version") or "latest"))
    log("[INFO] 来源：%s" % rel["url"])
    if args.dry_run:
        log("[DRY-RUN] 不会下载、不会安装。")
        return {"ok": True, "dry_run": True, "target": target,
                "target_reason": reason, "release": rel, "install": got}
    if not args.yes:
        log("")
        log("需要确认：将下载并静默安装 Obsidian 到 %s" % target)
        log("重跑并加 --yes：python \"%s\" --yes" % os.path.abspath(__file__))
        return {"ok": False, "need_confirm": True, "target": target,
                "target_reason": reason, "release": rel, "install": got}
    tmpdir = tempfile.mkdtemp(prefix="pj-obsidian-")
    installer = os.path.join(tmpdir, "Obsidian-%s.exe" % (rel.get("version") or "setup"))
    try:
        log("[1/4] 下载安装包 ...")
        dl = download(rel["url"], installer, int(rel.get("size") or 0))
        log("      %.1f MB  sha256=%s" % (dl["size"] / 1024 ** 2, dl["sha256"][:16]))
        subject = ""
        if args.no_verify:
            log("[WARN] 已跳过签名校验（--no-verify）")
        else:
            log("[2/4] 校验 Authenticode 签名 ...")
            subject = verify_signature(installer)
            log("      签名主体：%s" % subject)
        kind = installer_kind(installer)
        log("[3/4] 静默安装（%s）..." % kind)
        cmdline = None
        if kind == "squirrel":
            cmd = [installer, "--silent"]
            r = _run(cmd, timeout=args.timeout)
        else:
            # NSIS：/D 必须最后且不加引号；用原始命令行避免 Python 自动加引号
            if " " in target:
                log("[WARN] 目标路径含空格，NSIS /D 可能失效，将走移动+junction 回退")
                cmdline = '"%s" /S /currentuser' % installer
            else:
                cmdline = '"%s" /S /currentuser /D=%s' % (installer, target)
            try:
                r = subprocess.run(cmdline, capture_output=True, text=True,
                                   errors="ignore", timeout=args.timeout)
            except Exception as exc:
                class R:
                    returncode = -1
                    stdout = ""
                    stderr = str(exc)
                r = R()
        log("      安装器退出码：%s" % getattr(r, "returncode", "?"))
        if getattr(r, "stderr", ""):
            log("      stderr：%s" % str(r.stderr).strip()[:300])
        log("[4/4] 等待安装完成 ...")
        found, on_target = wait_for_install(target, timeout=min(args.timeout, 300))
        if not found:
            # 再给注册表/默认路径一点时间
            time.sleep(3)
            got2 = detect()
            if got2.get("installed"):
                found = got2.get("install_dir") or os.path.dirname(got2.get("path", ""))
                on_target = bool(target and norm(found) == norm(target))
        if not found:
            raise RuntimeError("安装器已退出，但未检测到 Obsidian。请查看安装器日志或手动安装")
        method = "direct"
        installed_dir = found
        if target and not on_target:
            if args.no_relocate:
                log("[WARN] 已安装到默认盘 %s（--no-relocate，未移动到 %s）" % (found, target))
                method = "default"
            else:
                log("[INFO] 安装器未使用 /D，回退：移动到 %s + junction" % target)
                try:
                    mv = relocate(found, target)
                    installed_dir = mv["install_dir"]
                    method = mv["method"]
                except Exception as exc:
                    log("[WARN] 移动到 D 盘失败：%s" % exc)
                    log("[WARN] 保留默认安装：%s" % found)
                    method = "default"
        got = detect()
        if not got.get("installed"):
            got = _as_install(installed_dir) or {}
            got = {"installed": True, **got}
        state = {
            "schema": 1,
            "name": "Obsidian",
            "version": got.get("version") or rel.get("version") or "",
            "path": got.get("path") or os.path.join(installed_dir, "Obsidian.exe"),
            "install_dir": installed_dir,
            "method": method,
            "requested_dir": target,
            "relocated": method == "junction",
            "source": rel.get("url"),
            "sha256": dl["sha256"],
            "size": dl["size"],
            "signature": subject,
            "installed_at": now_iso(),
            "installer": kind,
            "fallback_reason": "" if (method == "direct" or not target) else
                               ("安装器忽略 /D" if method == "junction" else "移动失败，保留默认盘"),
        }
        write_state(state)
        log("")
        log("[OK] Obsidian 安装完成")
        log("     路径：%s" % state["path"])
        log("     版本：%s" % (state["version"] or "未知"))
        log("     方式：%s" % {"direct": "直接安装到目标盘",
                              "junction": "默认盘安装 + 移动到目标盘 + junction",
                              "default": "默认盘（未能移动到目标盘）"}.get(method, method))
        if method == "default" and target:
            log("     [WARN] 未能装到 %s，当前仍在默认盘；不影响使用" % target)
        return {"ok": True, "install": state}
    finally:
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass


def main(argv=None):
    global JSON_MODE
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    p = argparse.ArgumentParser(description="检测/静默安装 Obsidian（D 盘优先）")
    p.add_argument("--check", action="store_true", help="只检测，不安装")
    p.add_argument("--dry-run", action="store_true", help="只打印计划，不下载不安装")
    p.add_argument("--yes", action="store_true", help="确认下载并静默安装")
    p.add_argument("--version", default="", help="指定 Obsidian 版本（默认最新）")
    p.add_argument("--install-dir", dest="install_dir", default="", help="指定安装目录")
    p.add_argument("--no-relocate", dest="no_relocate", action="store_true",
                   help="安装器忽略 /D 时，不移动到目标盘")
    p.add_argument("--no-verify", dest="no_verify", action="store_true",
                   help="跳过 Authenticode 校验（不推荐）")
    p.add_argument("--force", action="store_true", help="已安装也重新安装")
    p.add_argument("--timeout", type=int, default=900, help="安装器超时秒数（默认 900）")
    p.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    p.add_argument("--script-version", action="version", version=SCRIPT_VERSION)
    args = p.parse_args(argv)
    JSON_MODE = args.json
    try:
        if args.check and not args.dry_run:
            got = detect()
            if got.get("installed") and got.get("version"):
                try:
                    if tuple(map(int, str(got["version"]).split(".")[:3])) < tuple(
                            map(int, MIN_VERSION.split(".")[:3])):
                        log("[WARN] 当前版本 %s 低于建议的 %s；不影响 Markdown 视图"
                            % (got["version"], MIN_VERSION))
                except Exception:
                    pass
            if args.json:
                emit({"ok": True, "installed": got})
            else:
                if got.get("installed"):
                    log("[OK] Obsidian 已安装：%s（%s）" % (got["path"], got.get("version") or "版本未知"))
                else:
                    log("[MISS] 未检测到 Obsidian")
            return 0 if got.get("installed") else 1
        if args.dry_run:
            plan = build_plan(args)
            if args.json:
                emit({"ok": True, "dry_run": True, **plan})
            else:
                log("[PLAN] 已安装：%s" % ("是" if plan["installed"].get("installed") else "否"))
                if not plan["installed"].get("installed"):
                    log("[PLAN] 目标目录：%s（%s）" % (plan["target"], plan["target_reason"]))
                    log("[PLAN] 版本：%s" % (plan["release"].get("version") or "latest"))
                    log("[PLAN] 下载：%s" % (plan["release"].get("url") or "无法确定"))
                log("[DRY-RUN] 不会下载、不会安装。")
            return 0
        res = install(args)
        if args.json:
            emit(res)
        return 0 if res.get("ok") else 2
    except KeyboardInterrupt:
        log("[ABORT] 已取消")
        return 130
    except Exception as exc:
        if args.json:
            emit({"ok": False, "error": str(exc)})
        log("[FAIL] %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
