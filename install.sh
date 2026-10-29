#!/usr/bin/env bash
# zhanggong skill 一键安装脚本（Linux / macOS / Git Bash）
#
# 用法：
#   curl -fsSL https://raw.githubusercontent.com/Yym11345/zhanggong-yanyu-skill/main/install.sh | bash
#   bash install.sh
#
# 说明：
#   - 默认装到用户级 skills 目录（跨项目可用）
#   - 加 --project 装到当前项目下（团队共享）
#   - 加 --target <dir> 自定义目标目录
#
# 兼容两种运行方式：
#   1) 管道执行（curl | bash）：脚本来自 stdin，没有源码目录，
#      自动从 GitHub 下载仓库压缩包作为安装源
#   2) 本地执行（bash install.sh）：直接用脚本所在目录作为安装源

set -euo pipefail

SKILL_NAME="zhanggong"
MODE="user"
CUSTOM_TARGET=""
REPO="Yym11345/zhanggong-yanyu-skill"
TARBALL="https://github.com/$REPO/archive/refs/heads/main.tar.gz"

usage() {
  cat <<'EOF'
用法：
  curl -fsSL https://raw.githubusercontent.com/Yym11345/zhanggong-yanyu-skill/main/install.sh | bash
  bash install.sh

选项：
  --project        装到当前项目 ./.workbuddy/skills/zhanggong
  --target <dir>   装到指定目录
  -h, --help       显示本帮助
EOF
}

# 注意：必须用 while + shift 解析参数。
# `for arg in "$@"` 会在开始时固定参数列表，循环体内的 shift 不影响迭代，
# 会导致 --target 的值被当成未知参数。
while [ $# -gt 0 ]; do
  case "$1" in
    --project) MODE="project"; shift ;;
    --target)  MODE="custom"; CUSTOM_TARGET="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数：$1（用 --help 查看用法）" >&2; exit 1 ;;
  esac
done

# ---------- 定位/获取安装源 ----------
SRC_DIR=""
TMP_DIR=""

cleanup() {
  if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

# 判定当前是「本地执行」还是「管道执行」。
# 管道执行时 BASH_SOURCE 为空（脚本来自 stdin），$0 是 shell 名而非文件。
_self=""
if [ -n "${BASH_SOURCE+x}" ] && [ -n "${BASH_SOURCE[0]:-}" ]; then
  _self="${BASH_SOURCE[0]}"
elif [ -f "${0:-}" ]; then
  _self="$0"
fi

if [ -n "$_self" ]; then
  # 本地执行：安装源就是脚本所在目录
  SRC_DIR="$(cd "$(dirname "$_self")" 2>/dev/null && pwd || echo "")"
  if [ -z "$SRC_DIR" ] || [ ! -f "$SRC_DIR/SKILL.md" ]; then
    echo "✗ 未找到 SKILL.md，请在 skill 仓库目录内运行本脚本" >&2
    exit 1
  fi
else
  # 管道执行：下载仓库压缩包
  echo "→ 管道模式：从 GitHub 下载安装包..."
  TMP_DIR="$(mktemp -d 2>/dev/null || echo "${TMPDIR:-/tmp}/zg_install_$$")"
  mkdir -p "$TMP_DIR"
  if ! curl -fsSL "$TARBALL" -o "$TMP_DIR/pkg.tgz"; then
    echo "✗ 下载失败：$TARBALL" >&2
    echo "  若处于受限网络，请先设置代理再执行，例如：" >&2
    echo "    https_proxy=http://127.0.0.1:7897 bash -c 'curl -fsSL $TARBALL | bash'" >&2
    exit 1
  fi
  # 解压。注意：GNU tar 会把 Windows 绝对路径里的 "C:" 当成远程主机名
  # （报 "Cannot connect to C: resolve failed"），故先 cd 进临时目录再用相对路径。
  ( cd "$TMP_DIR" && tar -xzf "pkg.tgz" )
  # GitHub archive 解压后是 <repo>-main/ 这一层目录
  SRC_DIR="$(find "$TMP_DIR" -mindepth 2 -maxdepth 2 -name 'SKILL.md' | head -1)"
  SRC_DIR="$(dirname "$SRC_DIR")"
  if [ -z "$SRC_DIR" ] || [ ! -f "$SRC_DIR/SKILL.md" ]; then
    echo "✗ 压缩包结构异常，未找到 SKILL.md" >&2
    exit 1
  fi
  echo "  ✓ 已下载：$SRC_DIR"
fi

# ---------- 决定目标目录 ----------
if [ "$MODE" = "custom" ]; then
  # --target 指定的是**skills 根目录**，skill 装在其下的 $SKILL_NAME/ 子目录，
  # 避免把 SKILL.md / references/ 直接铺平到 skills 根目录污染其他 skill。
  TARGET="${CUSTOM_TARGET%/}/$SKILL_NAME"
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
[ -f "$SRC_DIR/INSTALL.md" ] && cp "$SRC_DIR/INSTALL.md" "$TARGET/"

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
