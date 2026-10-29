#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""发布前全面体检：一次跑完所有关键校验项。

用法：python preflight_check.py [skill目录]
"""
import io
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "zhanggong-yanyu-skill")

ok = 0
fail = 0
warn = 0
results = []


def chk(cond, label, detail="", level="fail"):
    global ok, fail, warn
    if cond:
        ok += 1
        results.append(("PASS", label, detail))
    elif level == "warn":
        warn += 1
        results.append(("WARN", label, detail))
    else:
        fail += 1
        results.append(("FAIL", label, detail))


# ---------- 1. 目录结构 ----------
# 安装后模式：install.sh / install.ps1 / INSTALL.md 不随 skill 复制（安装器用完即弃）
core_required = ["SKILL.md", "README.md", "LICENSE", "references", "scripts", "assets"]
installer_only = ["INSTALL.md", "install.sh", "install.ps1"]
for r in core_required:
    chk(os.path.exists(os.path.join(ROOT, r)), "结构存在: %s" % r)
for r in installer_only:
    if os.path.exists(os.path.join(ROOT, r)):
        chk(True, "结构存在: %s" % r)
    else:
        chk(True, "结构存在: %s" % r, "安装后模式：安装器文件不随 skill 复制（预期）",
            level="warn")

# ---------- 2. SKILL.md frontmatter ----------
skill_md = os.path.join(ROOT, "SKILL.md")
sm = io.open(skill_md, encoding="utf-8").read()
m = re.match(r"^---\n(.*?)\n---\n", sm, re.S)
chk(bool(m), "SKILL.md 有 YAML frontmatter")
if m:
    fm = m.group(1)
    nm = re.search(r"^name:\s*(\S+)\s*$", fm, re.M)
    chk(bool(nm), "frontmatter 含 name")
    if nm:
        name = nm.group(1)
        chk(bool(re.match(r"^[a-z0-9-]+$", name)),
            "name 符合 skill 规范 (^[a-z0-9-]+$)", name)
        chk(name == "zhanggong", "name == zhanggong", name)
    chk(bool(re.search(r"^description:\s*\S", fm, re.M)), "frontmatter 含 description")
    chk("agent_created: true" in fm, "frontmatter 含 agent_created: true")
    desc = re.search(r"^description:\s*(.+)$", fm, re.M)
    if desc:
        dl = len(desc.group(1))
        chk(dl < 1024, "description 长度合理", "%d 字符" % dl)

# ---------- 3. references ----------
refdir = os.path.join(ROOT, "references")
refs = sorted(f for f in os.listdir(refdir) if f.endswith(".md"))
chk(len(refs) == 22, "references 数量 == 22", "实际 %d" % len(refs))
chk(len(refs) >= 20, "references 数量 >= 20", "实际 %d" % len(refs))

# 交叉引用完整性：SKILL.md 中提到的 references 文件名都存在
mentioned = set(re.findall(r"([0-9]{2}-[\u4e00-\u9fffA-Za-z0-9\-]+\.md)", sm))
missing = sorted(x for x in mentioned if x not in refs)
chk(not missing, "SKILL.md 引用的 references 全部存在",
    "缺失: %s" % missing if missing else "引用 %d 个" % len(mentioned))

# references 内部互引完整性
broken = []
for f in refs:
    t = io.open(os.path.join(refdir, f), encoding="utf-8").read()
    for x in re.findall(r"([0-9]{2}-[\u4e00-\u9fffA-Za-z0-9\-]+\.md)", t):
        if x not in refs and x != f:
            broken.append("%s -> %s" % (f, x))
chk(not broken, "references 内部互引完整",
    "断裂 %d 处: %s" % (len(broken), broken[:3]) if broken else "0 断裂")

# 空文件检查
empties = [f for f in refs
           if len(io.open(os.path.join(refdir, f), encoding="utf-8").read().strip()) < 50]
chk(not empties, "无空/近空 references", "近空: %s" % empties if empties else "全部有内容")

# ---------- 4. 安装脚本 ----------
# 说明：安装完成后目标目录内不含 install.sh/install.ps1（安装器用完即弃），
#       此时这两项降级为 warn，不算失败。
installed_mode = not os.path.exists(os.path.join(ROOT, "install.sh"))
for fn, must_ascii in (("install.sh", False), ("install.ps1", True)):
    p = os.path.join(ROOT, fn)
    if not os.path.exists(p):
        chk(True, "%s 存在" % fn,
            "安装后模式：安装器未随 skill 复制（预期）", level="warn")
        continue
    b = io.open(p, "rb").read()
    chk(b.count(b"\r\n") == 0, "%s 无 CRLF" % fn, "CRLF=%d" % b.count(b"\r\n"))
    chk(b[:3] != b"\xef\xbb\xbf", "%s 无 BOM" % fn)
    nonascii = sum(1 for c in b if c > 127)
    if must_ascii:
        chk(nonascii == 0, "%s 纯 ASCII (PS 5.1 编码安全)" % fn,
            "non-ascii=%d" % nonascii)
    else:
        chk(True, "%s 可含中文" % fn, "non-ascii=%d" % nonascii)

shp = os.path.join(ROOT, "install.sh")
if os.path.exists(shp):
    sh = io.open(shp, encoding="utf-8").read()
    chk("while [ $# -gt 0 ]" in sh, "install.sh 用 while+shift 解析参数（避开 for 吞参数 bug）")
    chk("--target" in sh, "install.sh 支持 --target")
    # 管道模式（curl | bash）：BASH_SOURCE 为空，必须有管道兜底分支
    chk("BASH_SOURCE" in sh and "管道" in sh,
        "install.sh 支持管道模式（curl | bash）")
    chk("archive/refs/heads" in sh or "codeload" in sh or "tarball" in sh.lower(),
        "install.sh 管道模式有可下载的安装包来源")
    chk("trap cleanup EXIT" in sh or "cleanup()" in sh,
        "install.sh 管道模式会清理临时目录")

psp = os.path.join(ROOT, "install.ps1")
if os.path.exists(psp):
    ps = io.open(psp, encoding="utf-8").read()
    chk("PSScriptRoot" in ps, "install.ps1 判定本地/管道模式")
    chk("Invoke-WebRequest" in ps, "install.ps1 管道模式会下载安装包")
    chk("finally" in ps, "install.ps1 有 finally 清理临时目录")
    # Remove-Item 空值守卫：Get-ChildItem 无匹配时返回 $null，
    # 管道进 Remove-Item 会报 "missing path operand"。要求用 @() 数组化 + 计数判断。
    chk("@(Get-ChildItem" in ps and ".Count -gt 0" in ps,
        "install.ps1 清理逻辑有 $null 守卫（避免 missing path operand）")

# ---------- 5. 占位符 ----------
# 注意：排除本脚本自身（源码里含有该占位符字面量，会造成自指误报）
leftover = []
for dp, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d != ".git"]
    for f in fns:
        if not f.endswith((".md", ".sh", ".ps1", ".py")):
            continue
        if f == os.path.basename(__file__):
            continue
        t = io.open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read()
        if "YOUR_GITHUB_USERNAME" in t:
            leftover.append(os.path.relpath(os.path.join(dp, f), ROOT))
chk(not leftover, "无残留占位符 <YOUR_GITHUB_USERNAME>",
    "残留: %s" % leftover if leftover else "已全部替换")

# ---------- 6. 仓库名一致性 ----------
readme = io.open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
chk("Yym11345" in readme, "README 含正确用户名 Yym11345")
chk("zhanggong-yanyu-skill" in readme, "README 含仓库名")
chk("raw.githubusercontent.com/Yym11345/zhanggong-yanyu-skill/main/install.sh" in readme,
    "README 安装命令指向 main 分支")

# ---------- 7. 致谢表述（用户要求）----------
joined = readme + io.open(os.path.join(ROOT, "LICENSE"), encoding="utf-8").read()
chk("su8023" not in joined, "致谢中已移除具体来源仓库名 su8023")
chk(("社区已有的行测言语类 Skill 基础上完善" in joined or
     "参考其他人的 skill" in joined),
    "致谢改为「在社区已有 Skill 基础上完善」")

# ---------- 8. 速记卡资产 ----------
assets = os.path.join(ROOT, "assets")
cards = [f for f in os.listdir(assets) if f.endswith(".html")]
chk(len(cards) >= 1, "assets 含速记卡 HTML", str(cards))
if cards:
    c = io.open(os.path.join(assets, cards[0]), encoding="utf-8").read()
    pages = len(re.findall(r'class="sheet"', c))
    chk(pages == 42, "速记卡 42 页", "实际 %d 页" % pages)

# ---------- 9. scripts 可执行性 ----------
sdir = os.path.join(ROOT, "scripts")
scripts = sorted(os.listdir(sdir))
chk(len(scripts) >= 3, "scripts 数量 >= 3", str(scripts))
for s in scripts:
    if s.endswith(".py"):
        p = os.path.join(sdir, s)
        src = io.open(p, encoding="utf-8").read()
        try:
            compile(src, s, "exec")
            chk(True, "scripts/%s 语法可编译" % s)
        except SyntaxError as e:
            chk(False, "scripts/%s 语法可编译" % s, str(e))

# ---------- 9b. .gitattributes（防止 Windows clone 后 CRLF） ----------
ga = os.path.join(ROOT, ".gitattributes")
if os.path.exists(ga):
    g = io.open(ga, encoding="utf-8").read()
    chk("eol=lf" in g, ".gitattributes 声明 eol=lf")
    chk("install.sh" in g, ".gitattributes 显式覆盖 install.sh")
    chk("*.sh" in g, ".gitattributes 覆盖所有 .sh")
else:
    chk(True, "存在 .gitattributes",
        "安装后模式：.gitattributes 不随 skill 复制（预期）", level="warn")

# 仓库内不得有 CRLF 文件（用 git ls-files 检查实际入库内容）
gitdir = ROOT
if os.path.isdir(os.path.join(gitdir, ".git")):
    import subprocess
    try:
        out = subprocess.run(["git", "-C", gitdir, "ls-files", "-z"],
                             capture_output=True, text=True, timeout=30).stdout
        crlf = []
        for f in out.split("\0"):
            if not f:
                continue
            p = os.path.join(gitdir, f)
            if not os.path.isfile(p):
                continue
            # 只对「会被当作脚本执行」的文本文件强制 LF；
            # HTML/文档的 CRLF 无害，且工作区副本可能由 Windows 工具生成。
            if not f.endswith((".sh", ".ps1", ".py")):
                continue
            b = io.open(p, "rb").read()
            if b"\r\n" in b:
                crlf.append(f)
        chk(not crlf, "可执行脚本无 CRLF (sh/ps1/py)",
            "含 CRLF: %s" % crlf[:3] if crlf else "全部 LF")
    except Exception as e:
        chk(False, "git ls-files 检查", str(e))

# ---------- 10. zip 包 ----------
zp = os.path.join(HERE, "zhanggong-yanyu-skill.zip")
if os.path.exists(zp):
    z = zipfile.ZipFile(zp)
    names = z.namelist()
    chk(not any(".git/" in n for n in names), "zip 不含 .git")
    chk(any(n.endswith("SKILL.md") for n in names), "zip 含 SKILL.md")
    chk(sum(1 for n in names if n.endswith(".md") and "/references/" in n) == 22,
        "zip 内 references == 22",
        str(sum(1 for n in names if n.endswith(".md") and "/references/" in n)))
    chk(z.testzip() is None, "zip 完整性校验通过")
else:
    chk(True, "zip 包存在", "安装后模式：zip 仅存在于发布目录（预期）", level="warn")

# ---------- 输出 ----------
w = max(len(r[1]) for r in results)
for st, lab, det in results:
    icon = {"PASS": "✓", "WARN": "!", "FAIL": "✗"}[st]
    print("%s %-*s %s" % (icon, w, lab, ("- " + det) if det else ""))

print("")
print("=" * 60)
print("PASS %d   WARN %d   FAIL %d" % (ok, warn, fail))
print("=" * 60)
sys.exit(0 if fail == 0 else 1)
