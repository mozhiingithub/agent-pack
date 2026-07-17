#!/usr/bin/env bash
# bootstrap.sh — 老仓库一次性接入脚手架（参考骨架，Git Bash 兼容，无 jq 依赖）
# 用法: bootstrap.sh [--force] <项目仓库根目录> [agent-pack 目录]
#   幂等：已存在的文件默认跳过，绝不覆盖；--force 才覆盖（用于模板升级）。
set -euo pipefail

FORCE=0
[ "${1:-}" = "--force" ] && { FORCE=1; shift; }
REPO="${1:?用法: bootstrap.sh [--force] <仓库根目录> [agent-pack目录]}"
PACK="${2:-$(cd "$(dirname "$0")/.." && pwd)}"
log() { printf '[bootstrap] %s\n' "$*"; }
die() { echo "[bootstrap] ERROR: $*" >&2; exit 1; }

# ================= 固定区 1：环境检查 =================
[ -d "$REPO/.git" ] || die "不是 git 仓库: $REPO"
for cmd in git tar awk grep sort timeout sha256sum mktemp; do
  command -v "$cmd" >/dev/null || die "缺少命令: $cmd（Git Bash 应自带，请检查环境）"
done
[ -d "$PACK/templates" ] || die "找不到 agent-pack/templates: $PACK"

copy() { # 幂等拷贝：存在即跳过
  local src="$1" dst="$2"
  if [ -e "$dst" ] && [ "$FORCE" -eq 0 ]; then log "跳过（已存在）: $dst"; return; fi
  mkdir -p "$(dirname "$dst")"; cp "$src" "$dst"; chmod +x "$dst" 2>/dev/null || true
  log "已写入: $dst"
}

cd "$REPO"

# ================= 固定区 2：落地文件 =================
copy "$PACK/AGENTS.md"                    AGENTS.md
copy "$PACK/templates/export_package.sh"  tools/export_package.sh
copy "$PACK/templates/safe-git.sh"        tools/safe-git.sh
copy "$PACK/templates/import.sh"          tools/templates/import.sh
copy "$PACK/templates/githooks/pre-push"  .githooks/pre-push

if [ -d .agents/skills ] && [ "$FORCE" -eq 0 ]; then
  log "跳过（已存在）: .agents/skills"
else
  mkdir -p .agents/skills
  cp -r "$PACK/skills/." .agents/skills/
  log "已写入: .agents/skills/"
fi

# ================= 固定区 3：git 配置与忽略规则 =================
git config core.hooksPath .githooks
log "已设置 core.hooksPath=.githooks"

touch .gitignore
grep -qxF '.sync-state/' .gitignore || echo '.sync-state/' >> .gitignore
grep -qxF 'outbox/' .gitignore || echo 'outbox/' >> .gitignore
log "已更新 .gitignore（.sync-state/、outbox/ 不入库）"

# ================= 固定区 4：spec 模板检查（只警告，不改动）===========
if ! grep -rq "部署影响" docs/exec-plans 2>/dev/null; then
  log "警告：docs/exec-plans 未发现「部署影响」一节，请补入 exec-plan 模板（export 脚本硬性检查项）"
fi

# ================= 固定区 5：收尾提示 =================
cat <<'EOF'
[bootstrap] 完成。后续手工步骤：
  1. 填可变区：tools/export_package.sh 与 tools/templates/import.sh 中的项目路径、部署触发命令；
  2. 若仓库已有 AGENTS.md，请手工合并（本脚本未覆盖）；
  3. 提交本次变更，建议 message：chore: 接入 AI 双工协作工具链；
  4. 拿一个小 bug 全流程试跑：建 fix 分支 → 出包 → 内网执行 import.sh → 合并 → close 包。
EOF
