#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
速记卡自动重排 —— skill 侧包装器。

设计决策（第一性原理）：
  repaginate.py 是本项目唯一的分页实现，逻辑涉及测量/装箱/回写/验页数四个环节，
  复制一份到 skill 里必然产生"两份实现分叉"的维护负担，且极易出现一处修复另一处未修。
  因此这里不复制代码，而是**参数化包装**项目的权威实现：
    - 通过环境变量 ZHANGCONG_CARD 允许指定卡片路径
    - 通过环境变量 ZHANGCONG_REPAGINATE 允许指定实现脚本路径
    - 未设置时回落到项目默认位置

用法：
    python repaginate.py                # 用项目默认卡片
    ZHANGCONG_CARD="D:\\path\\card.html" python repaginate.py   # 指定卡片

依赖：Chromium 无头渲染（优先 Playwright chrome-headless-shell，须 --no-sandbox；回退 Edge）。
"""
import os
import subprocess
import sys

DEFAULT_IMPL = r"D:\other\gong\xingce\.workbuddy\tools\repaginate.py"
DEFAULT_CARD = r"D:\other\gong\xingce\中心理解_方法速记卡.html"

# 项目实现用 `ROOT = dirname(dirname(dirname(abspath(__file__))))` 推导卡片路径，
# 因此把实现复制到别处会指错卡片。这里通过环境变量做最小侵入式覆盖：
# 实现里 CARD 是模块级常量，可用 ZHANGCONG_CARD 直接替换其值。
_IMPL_ENV_OVERRIDE = r'''
import os as _os
_card = _os.environ.get("ZHANGCONG_CARD")
if _card:
    CARD = _card
'''


def main() -> int:
    impl = os.environ.get("ZHANGCONG_REPAGINATE", DEFAULT_IMPL)
    card = os.environ.get("ZHANGCONG_CARD", DEFAULT_CARD)

    if not os.path.exists(impl):
        print("找不到重排实现：%s" % impl, file=sys.stderr)
        return 2
    if not os.path.exists(card):
        print("找不到卡片：%s" % card, file=sys.stderr)
        return 2

    env = dict(os.environ)
    env["ZHANGCONG_CARD"] = card

    # 以 -c 方式先注入覆盖再 exec 实现，避免复制文件
    src = open(impl, encoding="utf-8").read()
    runner = _IMPL_ENV_OVERRIDE + "\n" + src

    print("重排卡片：%s" % card)
    print("调用实现：%s" % impl)
    proc = subprocess.run(
        [sys.executable, "-c", runner],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out)
    # 实现以 print 报告一致性，不以退出码表达；这里按关键校验行判断
    if "✗" in out:
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
