#!/usr/bin/env bash
# zhanggong skill 一键安装脚本（Linux / macOS / Git Bash）
#
# 用法：
#   curl -fsSL https://raw.githubusercontent.com/YOUR_USER/zhanggong-skill/main/install.sh | bash
#   或本地：bash install.sh
#
# 说明：
#   - 默认装到用户级 skills 目录（跨项目可用）
#   - 加 --project 装到当前项目下（团队共享）
#   - 加 --target <dir> 自定义目标目录

set -euo pipefail

SKILL_NAME="zhanggong"
MODE="user"
CUSTOM_TARGET=""

# 注意：必须用 while + shift 解析参数。
# `for arg in "$@"` 会在开始时固定参数列表，循环体内的 shift 不影响迭代，
# 会导致 --target 的值被当成未知参数。
while [ $# -gt 0 ]; do
  case "$1" in
    --project) MODE="project"; shift ;;
    --target)  MODE="custom"; CUSTOM_TARGET="${2:-}"; shift 2 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0 ;;
    *) echo "未知参数：$1（用 --help 查看用法）" >&2; exit 1 ;;
  esac
done

# ---------- 定位源码目录 ----------
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$SRC_DIR/SKILL.md" ]; then
  echo "✗ 未找到 SKILL.md，请在 skill 仓库目录内运行本脚本" >&2
  exit 1
fi

# ---------- 决定目标目录 ----------
if [ "$MODE" = "custom" ]; then
  TARGET="$CUSTOM_TARGET"
elif [ "$MODE" = "project" ]; then
  TARGET="$(pwd)/.workbuddy/skills/$SKILL_NAME"
else
  # 用户级：优先 WorkBuddy 目录，存在则用；否则退回通用 ~/.claude/skills
  if [ -d "$HOME/.workbuddy/skills" ]; then
    TARGET="$HOME/.workbuddy/skills/$SKILL_NAME"
  elif [ -d "$HOME/.claude/skills" ]; then
    TARGET="$HOME/.claude/skills/$SKILL_NAME"
  else
    TARGET="$HOME/.workbuddy/skills/$SKILL_NAME"
  fi
fi

echo "→ 安装源：$SRC_DIR"
echo "→ 目标目录：$TARGET"

# ---------- 备份已有版本 ----------
if [ -e "$TARGET" ]; then
  BACKUP="${TARGET}.bak.$(date +%Y%m%d_%H%M%S)"
  echo "→ 检测到已安装版本，备份到：$BACKUP"
  mv "$TARGET" "$BACKUP"
fi

mkdir -p "$TARGET"

# ---------- 复制核心文件 ----------
cp "$SRC_DIR/SKILL.md" "$TARGET/"
[ -f "$SRC_DIR/README.md" ] && cp "$SRC_DIR/README.md" "$TARGET/"
[ -f "$SRC_DIR/LICENSE" ] && cp "$SRC_DIR/LICENSE" "$TARGET/"

for d in references scripts assets; do
  if [ -d "$SRC_DIR/$d" ]; then
    mkdir -p "$TARGET/$d"
    cp -r "$SRC_DIR/$d/." "$TARGET/$d/"
    echo "  ✓ $d/"
  fi
done

# 清理 Python 缓存
find "$TARGET" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$TARGET" -name '*.pyc' -delete 2>/dev/null || true

# ---------- 校验 ----------
if [ -f "$TARGET/SKILL.md" ] && head -5 "$TARGET/SKILL.md" | grep -q '^name:'; then
  NAME_OK=$(grep -m1 '^name:' "$TARGET/SKILL.md" | sed 's/name: *//')
  REFS=$(ls "$TARGET/references" 2>/dev/null | wc -l | tr -d ' ')
  echo ""
  echo "✓ 安装完成"
  echo "  skill name : $NAME_OK"
  echo "  references : $REFS 个"
  echo "  路径       : $TARGET"
  echo ""
  echo "使用：贴一道言语题给它，或说「按速记卡方式分析这道题」。"
else
  echo "✗ 安装校验失败：SKILL.md frontmatter 异常" >&2
  exit 1
fi
