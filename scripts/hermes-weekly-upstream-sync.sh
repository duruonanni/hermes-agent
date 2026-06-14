#!/usr/bin/env bash
# hermes-weekly-upstream-sync.sh — 每周从 upstream 拉取、合并、重启
# 用途：no_agent cron，从 NousResearch 官方仓库同步代码
# Silent on Success：无更新时静默退出，有更新时输出变更
set -Eeuo pipefail

REPO_DIR="$HOME/src/hermes-agent"
BRANCH="main"
UPSTREAM="upstream"
REMOTE_REF="$UPSTREAM/$BRANCH"
LOCK_FILE="/tmp/hermes-weekly-upstream-sync.lock"
LOG_DIR="$HOME/.hermes/logs"
LOG_FILE="$LOG_DIR/hermes-weekly-upstream-sync.log"

mkdir -p "$LOG_DIR"

# 日志：同时写入文件 + stdout（cron 投递用）
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== [$(date -Iseconds)] Weekly upstream sync started ==="

# ── flock 防并发 ──
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "Another sync is already running (PID $(cat "$LOCK_FILE" 2>/dev/null || echo '?'))"
    exit 0
fi
echo $$ > "$LOCK_FILE"

# ── 环境 ──
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
export ALL_PROXY="${ALL_PROXY:-http://127.0.0.1:7890}"
export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:7890}"
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:7890}"

# Git 配置：HTTP/1.1 绕过 GnuTLS + 代理的 HTTP/2 TLS 握手问题
GIT=(git -c http.version=HTTP/1.1)

cd "$REPO_DIR"

# ── 前置检查 ──
if ! "${GIT[@]}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: not a git repository: $REPO_DIR"
    exit 1
fi

if ! "${GIT[@]}" remote get-url "$UPSTREAM" >/dev/null 2>&1; then
    echo "ERROR: upstream remote not configured"
    echo "  Run: git remote add upstream https://github.com/NousResearch/hermes-agent.git"
    exit 1
fi

# ── 暂存本地修改 ──
STASHED=false
START_BRANCH=$("${GIT[@]}" branch --show-current 2>/dev/null || echo "")

if ! "${GIT[@]}" diff --quiet || ! "${GIT[@]}" diff --cached --quiet; then
    echo "Local changes found, stashing..."
    "${GIT[@]}" stash push -u -m "hermes-weekly-sync-$(date +%s)"
    STASHED=true
fi

# ── EXIT 时恢复 stash ──
cleanup() {
    local code=$?
    if [ "$STASHED" = true ]; then
        echo "Restoring stashed local changes..."
        if ! "${GIT[@]}" stash pop; then
            echo "ERROR: stash restore failed — manual resolution required"
            echo "  git stash list"
            echo "  git stash pop"
            exit 3
        fi
    fi
    exit "$code"
}
trap cleanup EXIT

# ── 切换到 main ──
if [ "$START_BRANCH" != "$BRANCH" ]; then
    echo "Switching from '$START_BRANCH' to '$BRANCH'..."
    "${GIT[@]}" checkout "$BRANCH"
fi

# ── Fetch upstream（3 次重试，递增间隔）──
fetch_with_retry() {
    local attempt
    for attempt in 1 2 3; do
        echo "Fetch upstream (attempt $attempt/3)..."
        if "${GIT[@]}" fetch --prune "$UPSTREAM"; then
            echo "Fetch succeeded."
            return 0
        fi
        if [ $attempt -lt 3 ]; then
            local delay=$((attempt * 15))
            echo "Fetch failed, retrying in ${delay}s..."
            sleep "$delay"
        fi
    done
    return 1
}

if ! fetch_with_retry; then
    echo "ERROR: fetch failed after 3 attempts — proxy/TLS issue"
    exit 1
fi

# ── 检查差异 ──
BEHIND=$("${GIT[@]}" rev-list --count "HEAD..$REMOTE_REF" 2>/dev/null || echo "0")
AHEAD=$("${GIT[@]}" rev-list --count "$REMOTE_REF..HEAD" 2>/dev/null || echo "0")

echo "Behind upstream: $BEHIND  Ahead of upstream: $AHEAD"

# ── 无落后 → 已是最新 ──
if [ "$BEHIND" = "0" ]; then
    echo "Already up to date."
    exit 0
fi

# ── 双向分歧（本地也有上游没有的 commit）→ 自动救援 ──
#    将本地多出的 commit 保存到 local/patches 分支，
#    然后硬重置 main 到上游。
#
#    注意：只有 AHEAD > 0 且 BEHIND > 0 才是真正分叉。
#    AHEAD > 0 但 BEHIND == 0 的情况已在上面 exit 0 处理。
if [ "$AHEAD" != "0" ]; then
    echo "main has $AHEAD local commit(s) not in upstream — auto-rescuing..."

    # 获取本地多出的 commit（旧到新）
    LOCAL_SHA=$("${GIT[@]}" rev-list --reverse "$REMOTE_REF..HEAD")

    # 确保 local/patches 引用是最新的
    "${GIT[@]}" fetch origin local/patches 2>&1 || echo "(origin fetch skipped)"


    # 按 sha 遍历，只处理还没在 local/patches 中的 commit
    PATCHES_BRANCH="local/patches"
    NEEDS_PUSH=false
    NEEDS_CHERRY=false
    TO_SAVE=""

    for SHA in $LOCAL_SHA; do
        SHORT=$("${GIT[@]}" log --oneline --no-decorate "$SHA" -1 2>/dev/null)
        if "${GIT[@]}" merge-base --is-ancestor "$SHA" "$PATCHES_BRANCH" 2>/dev/null; then
            echo "  ✓ $SHORT — already in $PATCHES_BRANCH, skipping"
        else
            echo "  → $SHORT — needs preservation"
            TO_SAVE="$TO_SAVE $SHA"
            NEEDS_CHERRY=true
        fi
    done

    # 将需要保存的 commit cherry-pick 到 local/patches
    if [ "$NEEDS_CHERRY" = true ]; then
        # 确保 local/patches 分支存在（以当前 HEAD 为基创建，如果还不存在）
        if ! "${GIT[@]}" rev-parse --verify "$PATCHES_BRANCH" >/dev/null 2>&1; then
            echo "Creating $PATCHES_BRANCH from current HEAD..."
            "${GIT[@]}" branch "$PATCHES_BRANCH" HEAD
        fi

        # 暂存当前工作区，切换到 local/patches
        PATCHES_STASH=false
        if ! "${GIT[@]}" diff --quiet || ! "${GIT[@]}" diff --cached --quiet; then
            "${GIT[@]}" stash push -u -m "hermes-weekly-sync-patches-$(date +%s)"
            PATCHES_STASH=true
        fi

        "${GIT[@]}" checkout "$PATCHES_BRANCH"

        CHERRY_OK=true
        for SHA in $TO_SAVE; do
            SHORT=$("${GIT[@]}" log --oneline --no-decorate "$SHA" -1 2>/dev/null)
            echo "Cherry-picking $SHORT..."
            if "${GIT[@]}" cherry-pick "$SHA" 2>&1; then
                echo "  ✓ $SHORT saved to $PATCHES_BRANCH"
                NEEDS_PUSH=true
            else
                echo "  ✗ cherry-pick $SHORT failed (conflict), aborting..."
                "${GIT[@]}" cherry-pick --abort 2>/dev/null || true
                CHERRY_OK=false
                break
            fi
        done

        # 切回 main，恢复暂存
        "${GIT[@]}" checkout "$BRANCH"
        if [ "$PATCHES_STASH" = true ]; then
            "${GIT[@]}" stash pop 2>/dev/null || true
        fi

        if [ "$CHERRY_OK" = false ]; then
            echo "WARNING: some commits could not be cherry-picked to $PATCHES_BRANCH."
            echo "  The remaining commits are still in git history — run manually:"
            echo "    git cherry-pick <sha>  # onto $PATCHES_BRANCH"
        fi
    fi

    # 推送 local/patches 到 origin
    if [ "$NEEDS_PUSH" = true ]; then
        echo "Pushing $PATCHES_BRANCH to origin..."
        "${GIT[@]}" push origin "$PATCHES_BRANCH" 2>&1 || echo "WARNING: push failed (network issue), commits safe locally"
    fi

    # 硬重置 main 到 upstream/main
    echo "Resetting $BRANCH to $REMOTE_REF..."
    "${GIT[@]}" reset --hard "$REMOTE_REF"
    echo "Divergence resolved. $BRANCH is now at $REMOTE_REF."
fi

# ── 列出新 commits ──
echo "New commits from upstream:"
"${GIT[@]}" log --oneline --no-decorate "HEAD..$REMOTE_REF"

# ── 快进合并 ──
echo "Fast-forwarding $BRANCH to $REMOTE_REF..."
if ! "${GIT[@]}" merge --ff-only "$REMOTE_REF"; then
    echo "ERROR: fast-forward merge failed (unexpected — BEHIND=$BEHIND AHEAD=$AHEAD)"
    exit 2
fi

echo "Merge successful."

# ── 安装依赖 ──
echo "Installing editable package..."
if ! uv pip install -e "$REPO_DIR" 2>&1; then
    echo "ERROR: pip install failed"
    exit 4
fi
echo "Install successful."

# ── 重启 gateway ──
echo "Restarting hermes-gateway..."
if ! systemctl --user restart hermes-gateway 2>&1; then
    echo "ERROR: gateway restart failed"
    exit 5
fi
echo "Gateway restarted successfully."

echo "=== [$(date -Iseconds)] Sync completed ==="
