#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
速记卡校验器：例题答案表抽取 + 页数一致性 + 可疑答案扫描。

存在理由（历史教训）：
  卡片逻辑填空例题速查表曾出现 3 处答案误录（例3 B→A、例14 C→B、例28 B→D），
  且例28 属"联想型误录"——判定理由看似自洽，实则错误，靠通读很难发现。
  因此需要一个**机械化**的核对工具：把所有例题的「题号 + 答案 + 判定」抽成清单，
  便于批量交叉核验；并对疑似问题做机械标记。

用法：
    python verify_card.py                 # 全量检查
    python verify_card.py --answers       # 只导出答案清单
    python verify_card.py --check-pages   # 只查 HTML/PDF 页数一致性

退出码：0 = 通过；1 = 发现问题；2 = 输入错误
"""
import argparse
import io
import os
import re
import subprocess
import sys
import glob
import tempfile

DEFAULT_CARD = r"D:\other\gong\xingce\中心理解_方法速记卡.html"

# 答案单元格特征：<td class="k">D</td> / <td class="k">B†推断</td> / <td class="k">C†待核</td>
ANS_CELL = re.compile(r'<td class="k">\s*([A-D])([^<]*)</td>')

# 判定栏里出现的可疑标记
# 注意："?"／"？" 若来自**引用的原文问句**（如"也会对大脑造成危害吗？"）属正常，
# 只有出现在标记位（答案单元格后缀）才算存疑。故问号只查 mark，不查 judge。
SUSPECT_MARKS = ["待核", "疑似", "不确定", "存疑"]
SUSPECT_MARKS_JUDGE = ["待核", "疑似", "不确定", "存疑"]
# 仅在标记位检索的问号（答案单元格后缀里的裸问号）
QUESTION_IN_MARK = re.compile(r"[?？]")


def strip_tags(h: str) -> str:
    h = re.sub(r"<br\s*/?>", " / ", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = h.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
    return re.sub(r"\s+", " ", h).strip()


def find_browser():
    pat = os.path.expanduser(
        r'~\AppData\Local\ms-playwright\chromium_headless_shell-*\chrome-headless-shell-win64\chrome-headless-shell.exe')
    hits = sorted(glob.glob(pat))
    if hits:
        return hits[-1], False
    return r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', True


def pdf_page_count(card: str) -> int:
    """渲染 PDF 并数页数。"""
    browser, is_edge = find_browser()
    tmp = tempfile.mkdtemp(prefix="cardverify_")
    pdf = os.path.join(tmp, "card.pdf")
    base = [browser, "--no-sandbox", "--disable-gpu"]
    if is_edge:
        base.insert(1, "--headless")
    try:
        subprocess.run(
            base + ["--no-pdf-header-footer", "--print-to-pdf=" + pdf,
                    "file:///" + card.replace("\\", "/")],
            capture_output=True, timeout=180)
    except subprocess.TimeoutExpired:
        return -1
    if not os.path.exists(pdf):
        return -1
    data = open(pdf, "rb").read()
    counts = [int(x) for x in re.findall(rb"/Count\s+(\d+)", data)]
    return max(counts) if counts else -1


def html_sheet_count(src: str) -> int:
    """数 HTML 中的 .sheet 容器数（repaginate 生成的每页一个）。"""
    return len(re.findall(r'<div class="sheet"', src))


def collect_answers(src: str):
    """抽取所有例题表的「题号/出处 + 答案」。"""
    rows = []
    for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", src, re.S):
        tr = m.group(1)
        cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(cells) < 2:
            continue
        k = strip_tags(cells[0])
        a = strip_tags(cells[1])
        # 答案列形如 "A" / "B†推断" / "C†待核"
        am = re.match(r"^([A-D])(\s*[†*]?\s*.*)?$", a)
        if not am:
            continue
        if not re.search(r"例?\d|国考|省|深圳|江苏|北京|上海|天津|广西|青海|内蒙古|宁夏|四川|浙江|黑龙江|甘肃|贵州|福建|山西|湖南|湖北|山东|江苏|重庆|陕西|新疆|西藏|吉林|辽宁|河南|河北|安徽|江西|行政", k):
            continue
        judge = strip_tags(cells[2]) if len(cells) > 2 else ""
        rows.append((k, am.group(1), (am.group(2) or "").strip(), judge))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", default=DEFAULT_CARD)
    ap.add_argument("--answers", action="store_true", help="只导出答案清单")
    ap.add_argument("--check-pages", action="store_true", help="只查页数一致性")
    args = ap.parse_args()

    if not os.path.exists(args.card):
        print("找不到卡片：%s" % args.card, file=sys.stderr)
        return 2

    src = io.open(args.card, encoding="utf-8").read()
    problems = []

    # ---------- A. 页数一致性 ----------
    if not args.answers:
        html_pages = html_sheet_count(src)
        pdf_pages = pdf_page_count(args.card)
        print("=== 页数一致性 ===")
        print("  HTML .sheet 数：%d" % html_pages)
        print("  PDF 实测页数 ：%d" % pdf_pages)
        if pdf_pages > 0 and html_pages != pdf_pages:
            problems.append("页数不一致：HTML %d vs PDF %d" % (html_pages, pdf_pages))
            print("  ✗ 不一致！")
        else:
            print("  ✓ 一致")

        # 结构标签配平
        print("\n=== 标签配平 ===")
        for tag in ("div", "section", "table", "tr", "td"):
            a = len(re.findall(r"<" + tag + r"\b", src))
            b = len(re.findall(r"</" + tag + r">", src))
            ok = a == b
            if not ok:
                problems.append("标签 <%s> 不配平：%d/%d" % (tag, a, b))
            print("  %-8s %d/%d %s" % (tag, a, b, "✓" if ok else "✗"))

    # ---------- B. 答案表 ----------
    rows = collect_answers(src)
    print("\n=== 例题答案清单（%d 条）===" % len(rows))
    if args.answers:
        for k, a, mark, _ in rows:
            print("%-40s %s %s" % (k.replace("\n", " "), a, mark))
        return 0

    suspect = []
    noconfirm = []
    for k, a, mark, judge in rows:
        tag = ""
        if mark:
            tag = mark
        # 标记位（含裸问号）→ 存疑
        if QUESTION_IN_MARK.search(mark or ""):
            suspect.append((k, a, tag, judge))
        elif any(s in (mark + judge) for s in SUSPECT_MARKS_JUDGE):
            suspect.append((k, a, tag, judge))
        if "原误记" in judge or "更正为" in judge:
            noconfirm.append((k, a, judge))
        print("  %-38s %s%s" % (k.replace("\n", " ")[:38], a, (" " + tag) if tag else ""))

    if noconfirm:
        print("\n=== 曾修正答案的题（需保持标记）===")
        for k, a, judge in noconfirm:
            print("  %-38s 现答案 %s ｜ %s" % (k.replace("\n", " ")[:38], a, judge[:80]))

    if suspect:
        print("\n=== ⚠ 疑似待核（判定或标记含存疑词）===")
        for k, a, tag, judge in suspect:
            print("  %-38s %s ｜ %s" % (k.replace("\n", " ")[:38], a, judge[:100]))
        problems.append("%d 条例题判定含存疑标记" % len(suspect))

    # ---------- C. 结论 ----------
    print("\n=== 结论 ===")
    if problems:
        for p in problems:
            print("  ✗ " + p)
        return 1
    print("  ✓ 未发现结构性问题（答案正确性仍需人工交叉核验）")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
