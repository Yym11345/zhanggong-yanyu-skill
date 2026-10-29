#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从《中心理解_方法速记卡.html》抽取知识库，生成 zhanggong skill 的 references/*.md。

设计要点（第一性原理）：
  卡片是"给人看的纸面版式"，skill 需要的是"给 AI 用的结构化知识"。
  直接复制 HTML 会带来两个问题：
    1. 体积：244KB HTML ≈ 数万 token，一次加载违背渐进式披露；
    2. 噪声：样式标签、页码锚点、导航条对语义无贡献。
  因此本脚本做"语义降噪 + 结构重建"：
    - 表格 -> Markdown 表格（保留表头语义）
    - 列表 -> Markdown 列表
    - 段落/提示框 -> 加粗小标题 + 引用块
    - <span class="pr" data-t="..."> 页码锚点 -> 丢弃（页码会随重排变化）
  输出按"讲题时按题型加载"切分，而非卡片原始顺序。

用法：
    python extract_card.py [--card <html路径>] [--out <references目录>] [--index-only]
"""
import argparse
import io
import os
import re
import sys

DEFAULT_CARD = r"D:\other\gong\xingce\中心理解_方法速记卡.html"

# ---------------------------------------------------------------- 题型归类规则
# 第一性原理：卡片 section 的 h2 标题是稳定的语义标识（序号会随编辑漂移，标题不会）。
# 规则按"窄规则优先"从上到下匹配——先命中专用题型前缀，避免被通用关键词劫持。
# 典型坑：早期版本用 "思维提升②" 做规则，导致「细节判断·思维提升②」被误归入中心理解。
# 每条规则: (输出文件名, 正则)
RULES = [
    # --- 顶层结构 ---
    ("00-考场速查.md",        r"^考场速查"),
    ("17-PPT来源对照.md",      r"^PPT 来源对照表"),
    ("16-附录-基础词.md",      r"^附录"),
    # --- 逻辑填空（例题优先于方法）---
    ("15-逻辑填空-例题库.md",   r"逻辑填空\s*·\s*例题速查"),
    ("14-逻辑填空-方法.md",     r"^六、逻辑填空|^逻辑填空"),
    # --- 其余五题型（用编号前缀锁定，防止被通用规则劫持）---
    ("10-细节判断.md",         r"^二、细节判断"),
    ("11-语句填空.md",         r"^三、语句填空"),
    ("12-接语选择.md",         r"^四、接语选择"),
    ("13-语句排序.md",         r"^五、语句排序|^排序 ·|^语句排序"),
    # --- 中心理解各专题 ---
    ("07-首句与例子.md",       r"^\(三\) 重视首句|^「回扣开头」|^四个坑|^\(四\) 正确理解例子|^回指 vs 结论"),
    ("05-中心理解-对策类.md",   r"^\(五\)"),
    ("06-中心理解-因果与链条.md", r"^\(七\)|^思维提升① ｜ 答案可以是|^理论要点|^链条题例题速查|^本节例题 · 规律|^与卡上已有内容的挂接"),
    ("09-中心理解-晦涩文段.md",  r"^\(八\)"),
    ("08-中心理解-例题库.md",    r"^例题速查|^考点 → 例题反查表|^反例"),
    ("04-中心理解-排除干扰项.md", r"^第三步|^干扰项五型|^类型②"),
    ("03-中心理解-同义替换与主题词.md", r"^第二步|^主题词|^两个例证|^例（残体之美）|^解题方法"),
    ("02-中心理解-关系与功能.md", r"^第一步|^关系 ·|^专题 ｜ 思维提升"),
    ("01-中心理解-总纲与流程.md", r"^总纲|^冲突仲裁表|^全卡目录导航|^一句话口诀|^做题流程|^全课程闭环|^两步对称|^⚠"),
]

# 无 h2 的 section 用锚点 id 兜底（当前卡片仅 section 28「重视首句·省流版」）
ID_FALLBACK = {
    "a-shouju": "07-首句与例子.md",
}


def classify(title: str, anchor: str = "") -> str:
    """返回目标文件名。标题优先，标题缺失时用锚点 id 兜底。"""
    if title:
        for out, pat in RULES:
            if re.search(pat, title):
                return out
    if anchor in ID_FALLBACK:
        return ID_FALLBACK[anchor]
    return "99-其他.md"


# ---------------------------------------------------------------- HTML -> 文本
def strip_page_anchors(html: str) -> str:
    """页码锚点 span -> 保留可解析的引用文本。

    页码会随重排漂移，写进知识库必然失效；但直接丢弃会让 "见第 页" 变成悬空引用
    （实测 84 处）。因此把页码 span 连同其锚点 id 一起抽出，在拼装阶段还原为
    「参见〈锚点对应章节〉」——锚点稳定，且语义比页码更有用。
    """
    html = re.sub(r'<span class="pr"[^>]*>.*?</span>', "", html, flags=re.S)
    html = re.sub(r'<span class="pr"[^>]*/>', "", html)
    return html


def cell_text(html: str) -> str:
    """表格单元格 -> 纯文本，保留加粗语义为 ** **。"""
    html = re.sub(r"<br\s*/?>", " / ", html)
    html = re.sub(r"</?(?:b|strong|u|em|i)>", "**", html)
    html = re.sub(r"<[^>]+>", "", html)
    html = html.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
    html = re.sub(r"\*\*\s*\*\*", "", html)          # 清理空加粗
    html = re.sub(r"[ \t\u00a0]+", " ", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def table_to_md(html: str) -> str:
    """HTML table -> Markdown table。"""
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = [cell_text(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)]
        if any(c for c in cells):
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = []
    out.append("| " + " | ".join(rows[0]) + " |")
    out.append("|" + "|".join(["---"] * width) + "|")
    for r in rows[1:]:
        out.append("| " + " | ".join(c.replace("\n", " ") for c in r) + " |")
    return "\n".join(out)


def block_to_md(html: str, anchor_map=None) -> str:
    """section 内部 -> Markdown 正文。

    anchor_map: {锚点id: 章节名}，用于把 "见第 <span class='pr' data-t='x'>N</span> 页"
    还原成 "参见〈章节名〉"。锚点稳定、页码易漂移，故用锚点更可靠。
    """
    anchor_map = anchor_map or {}

    # 1) 先把页码 span 换成占位符，并记录其锚点
    refsl = []

    def _ref(m):
        tag = m.group(0)
        dt = re.search(r'data-t="([^"]+)"', tag)
        key = dt.group(1) if dt else ""
        refsl.append(key)
        return "\x01REF%d\x01" % (len(refsl) - 1)
    html = re.sub(r'<span class="pr"[^>]*>.*?</span>', _ref, html, flags=re.S)
    html = re.sub(r'<span class="pr"[^>]*/>', _ref, html)

    # 2) 表格优先抽出。占位符必须用不会与正文冲突的标记，且在最终拼装时回填，
    # 否则表格内容会被后续的"剩余标签清洗"步骤连同标记一起清掉（早期版本踩过此坑）。
    tables = []

    def _grab(m):
        tables.append(table_to_md(m.group(0)))
        return "\n\n@@TBL%d@@\n\n" % (len(tables) - 1)
    html = re.sub(r"<table[^>]*>.*?</table>", _grab, html, flags=re.S)

    # 列表
    def _ol(m):
        items = re.findall(r"<li[^>]*>(.*?)</li>", m.group(0), re.S)
        return "\n" + "\n".join(f"- {cell_text(i)}" for i in items) + "\n"
    html = re.sub(r"<ol[^>]*>.*?</ol>", _ol, html, flags=re.S)
    html = re.sub(r"<ul[^>]*>.*?</ul>", _ol, html, flags=re.S)

    # 标题层级
    html = re.sub(r"<h2[^>]*>(.*?)</h2>", lambda m: "\n\n## " + cell_text(m.group(1)) + "\n\n",
                  html, flags=re.S)
    html = re.sub(r"<h3[^>]*>(.*?)</h3>", lambda m: "\n### " + cell_text(m.group(1)) + "\n",
                  html, flags=re.S)
    html = re.sub(r"<h4[^>]*>(.*?)</h4>", lambda m: "\n#### " + cell_text(m.group(1)) + "\n",
                  html, flags=re.S)

    # div.note / div class 含 note 的提示框 -> 引用块
    def _note(m):
        inner = re.sub(r"<[^>]+>", " ", m.group(0))
        inner = cell_text(m.group(0))
        inner = inner.replace("**", "**")
        return "\n\n> " + inner.replace("\n", "\n> ") + "\n\n"
    html = re.sub(r'<div class="note[^"]*"[^>]*>.*?</div>', _note, html, flags=re.S)

    # 剩余标签
    html = re.sub(r"<br\s*/?>", "\n", html)
    html = re.sub(r"<[^>]+>", " ", html)
    html = html.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")

    # 行内加粗修复：<b> 被替换成 ** 时可能与普通文本相邻，需保证闭合
    lines = []
    for ln in html.split("\n"):
        ln = re.sub(r"[ \t\u00a0]+", " ", ln).strip()
        if ln:
            lines.append(ln)
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)

    # 回填表格
    for i, t in enumerate(tables):
        out = out.replace("@@TBL%d@@" % i, t)

    # 回填交叉引用：把 "第 <ref> 页" / "见第 <ref> 页" 改写为 "参见〈章节名〉"
    for i, key in enumerate(refsl):
        ph = "\x01REF%d\x01" % i
        name = anchor_map.get(key)
        if name:
            # 形如 "见第 页" / "第 页" / "  页" -> 参见〈name〉
            out = re.sub(r"见?\s*第?\s*" + re.escape(ph) + r"\s*页?", "参见〈%s〉" % name, out)
            out = out.replace(ph, "〈%s〉" % name)
        else:
            out = re.sub(r"见?\s*第?\s*" + re.escape(ph) + r"\s*页?", "见相应章节", out)
            out = out.replace(ph, "相应章节")
    return out.strip()


def split_sections(src: str):
    """切出 (h2标题, section内部HTML, 锚点id)。"""
    result = []
    for m in re.finditer(r"<section[^>]*>(.*?)</section>", src, re.S):
        body = m.group(1)
        h = re.search(r"<h2[^>]*>(.*?)</h2>", body, re.S)
        title = cell_text(h.group(1)) if h else ""
        aid = re.search(r'<span id="([^"]+)"', body)
        result.append((title, body, aid.group(1) if aid else ""))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", default=DEFAULT_CARD)
    ap.add_argument("--out", default=None)
    ap.add_argument("--index-only", action="store_true",
                    help="只打印分类清单，不写文件")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = args.out or os.path.join(os.path.dirname(here), "references")

    if not os.path.exists(args.card):
        print("找不到卡片：%s" % args.card, file=sys.stderr)
        return 2

    src = io.open(args.card, encoding="utf-8").read()
    secs = split_sections(src)
    print("解析 section 数：%d" % len(secs))

    buckets = {}
    for title, body, aid in secs:
        buckets.setdefault(classify(title, aid), []).append((title, body, aid))

    # 建立 锚点id -> 章节名 映射，用于还原 "见第 N 页" 这类交叉引用
    anchor_map = {}
    for title, body, aid in secs:
        if not aid:
            continue
        ids = [aid] + re.findall(r'<span id="([^"]+)"', body)
        for i in ids:
            if i not in anchor_map:
                anchor_map[i] = title or aid

    if args.index_only:
        for fn in sorted(buckets):
            print("\n== %s ==" % fn)
            for t, _, a in buckets[fn]:
                print("   [%s] %s" % (a or "-", t[:60]))
        return 0

    os.makedirs(out_dir, exist_ok=True)
    written = []
    for fn, items in buckets.items():
        parts = []
        for title, body, aid in items:
            md = block_to_md(body, anchor_map)
            if not md.strip():
                continue
            parts.append(md)
        if not parts:
            continue
        path = os.path.join(out_dir, fn)
        header = ("> 本文件由 `scripts/extract_card.py` 从《中心理解_方法速记卡.html》自动生成。\n"
                  "> 修改卡片后请重跑脚本刷新；勿直接手改本文件。\n\n")
        io.open(path, "w", encoding="utf-8").write(header + "\n\n---\n\n".join(parts))
        written.append((fn, len(parts)))

    print("\n已生成 %d 个知识文件：" % len(written))
    for fn, n in sorted(written):
        size = os.path.getsize(os.path.join(out_dir, fn))
        print("  %-40s %2d 节  %6d 字节" % (fn, n, size))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
