---
name: self-code-management
description: "Fork 源码管理规范：只修改 skills/ 和 tools/，feature branch 工作流，定期从 upstream 同步保持 fork 干净，推送本地修改到 fork。"
category: devops
triggers:
  - "提交修改"
  - "fork 管理"
  - "upstream 同步"
  - "技能开发"
  - "工具开发"
  - "分支清理"
  - "自我管理"
  - "代码管理规范"
---

# Self Code Management

## 核心原则

| 原则 | 说明 |
|------|------|
| **修改范围** | 改 `skills/` `tools/` 和自定义 `scripts/`（见分支规范） |
| **不动核心** | 决不修改 `agent/` `gateway/` `plugins/` `cli.py` `run_agent.py` 等核心源码 |
| **Feature Branch** | 所有本地修改提交到 `local/<name>` 分支，不直接改 `main` |
| **Clean Main** | 本地 `main` 始终从 `upstream/main` 拉取，不在 main 上做任何修改 |
| **定期同步 | 定期从 upstream 拉取最新代码，保持 main 不落后 |
| **Fork 清洁** | fork 上的旧分支及时清理，只保留 main + 活跃 feature 分支 |

### 目录权限说明

| 目录 | 可修改？ | 说明 |
|------|---------|------|
| `skills/` | ✅ | 自定义 skill 修改，任意 feature 分支 |
| `tools/` | ✅ | 自定义 tool 修改，任意 feature 分支 |
| `scripts/` | ⚠️ 仅限自定义 cron 脚本 | 必须是上游不存在的自定义脚本，走 `local/cron-scripts` 分支。上游已有同名脚本（install.sh、release.py 等）**不可改** |
| 其余目录 | ❌ | `agent/` `gateway/` `plugins/` `cli.py` `run_agent.py` 等核心 |

## 📌 重要：~/.hermes/ 不是 Git 仓库

自 2026-06-05 目录分离后，**~/.hermes/ 已不是 Git 仓库**。
所有 Git 操作（pull、push、rebase、reset）只能在 `~/src/hermes-agent/` 下执行。

如果操作 `~/.hermes/` 下的 Git 仓库（历史遗留），会清除所有不在 upstream 中的
自定义 skill 和脚本。详见 `hermes-self-maintenance` 的技能事故记录。

## 仓库结构

```\n~/src/hermes-agent/\n├── .git/                    ← Git 仓库\n├── remotes:\n│   ├── origin  → https://github.com/duruonanni/hermes-agent.git   (fork)\n│   ├── upstream → https://github.com/NousResearch/hermes-agent.git (上游)\n│   └── (其他 remote)\n└── 允许修改的目录:\n    ├── skills/              ← ✅ 可修改（任意 feature 分支）\n    ├── tools/               ← ✅ 可修改（任意 feature 分支）\n    └── scripts/             ← ⚠️ 仅自定义 cron 脚本，走 local/cron-scripts 分支\n```

## 工作流

### 日常开发：feature branch 模式

```bash
# 1. 确保 main 是最新的（在 main 分支上）
cd ~/src/hermes-agent
git checkout main
git fetch upstream main
git rebase upstream/main

# 2. 从干净的 main 创建 feature 分支
git checkout -b local/your-feature-name

# 3. 在允许的目录下做修改
#    - skills/ tools/ → 任意 local/<name> 分支
#    - scripts/（自定义 cron 脚本）→ 必须走 local/cron-scripts 分支
#    - 确认修改范围只在允许的目录内

# 4. 提交修改
git add -A
git diff --cached --stat   # 检查是否混入了不允许的文件
git commit -m "feat: description"

# 5. 推送到 fork
ALL_PROXY=http://127.0.0.1:7890 git push origin local/your-feature-name

# 6. 回到 main 准备下一次开发
git checkout main
```

### 从上游同步（保持 main 干净）

```bash
cd ~/src/hermes-agent
git checkout main
git fetch upstream main
git rebase upstream/main
ALL_PROXY=http://127.0.0.1:7890 git push --force origin main
```

> ⚠️ 同步前确保 feature 分支上的修改已提交并推送，否则本地修改会丢失。

### Fork 分支清理

```bash
cd ~/src/hermes-agent
# 列出 fork 上的所有远程分支
ALL_PROXY=http://127.0.0.1:7890 git ls-remote --heads origin

# 删除旧分支（只保留 main + 活跃 feature 分支）
ALL_PROXY=http://127.0.0.1:7890 git push origin --delete old-branch-name

# 清理本地过期 remote-tracking refs
git remote prune origin
```

### 推送安全：使用代理

从中国网络访问 GitHub 需要通过代理：

```bash
# 方法一：单次命令
ALL_PROXY=http://127.0.0.1:7890 git push origin <branch>

# 方法二：git 本地配置
git config --local http.proxy http://127.0.0.1:7890
git config --local https.proxy http://127.0.0.1:7890
```

## 修改范围检查清单

提交前逐项确认：

- [ ] 只修改了 `skills/` `tools/` 下的文件，或 `scripts/` 下的自定义 cron 脚本
- [ ] 如果修改 `scripts/`，确认脚本是自定义 cron 脚本且不在上游已有（上游已有的 install.sh、release.py 等不可改）
- [ ] 如果修改 `scripts/`，确认所在分支是 `local/cron-scripts`
- [ ] 未修改 `agent/` `gateway/` `plugins/` `cli.py` `run_agent.py` 等核心
- [ ] 未混入 `config.yaml` `.env` `state.db` 等运行时文件
- [ ] Commit message 符合 Conventional Commits 格式
- [ ] 已切到 feature branch，而非 main

## 分支命名规范

| 模式 | 用途 | 示例 |
|------|------|------|
| `local/<name>` | 本地自定义修改（skills/tools） | `local/custom-skills-tools` |
| `local/cron-scripts` | 自定义 cron 脚本（scripts/） | `local/cron-scripts` ⭐ 固定分支名 |
| `feat/<name>` | 上游 PR 准备（很少用） | `feat/new-skill-category` |
| `fix/<name>` | Bug 修复（很少用） | `fix/tool-timeout` |

> ⚠️ `local/cron-scripts` 是**固定分支名**，所有自定义 cron 脚本的修改都提交到这个分支，不要创建多个 cron 相关分支。

## Git 身份验证与 GitHub 邮箱绑定

### 提交者身份

git commit 使用 `user.name` 和 `user.email` 标识作者。推送到 GitHub 后，commit 会按 email 关联到对应的 GitHub 账号：

```bash
# 查看当前生效的身份
git config user.name
git config user.email

# 设置（建议与 GitHub 绑定的邮箱一致）
git config --global user.name "Your Name"
git config --global user.email "your-github-bound-email@example.com"
```

### 验证 GitHub 账号绑定的邮箱

通过已认证的 API 查询：

```bash
source ~/.hermes/.env
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user |
  python3 -c "import sys,json; print(json.load(sys.stdin).get('email', 'none'))"
```

注意：
- `repo, workflow` scope 的 token 也能通过 `/user` 端点返回主邮箱（已验证可行）
- 如果 `user.email` 与 GitHub 绑定邮箱不一致，commit 推上去后不会显示绿色头像和链接

### 常见场景：fork 中未关联的 commit

```bash
# 查看 fork 上最近 commit 的作者邮箱
curl -s "https://api.github.com/repos/your-username/hermes-agent/commits?per_page=5" |
  python3 -c "import sys,json; [print(c['commit']['author']['email']) for c in json.load(sys.stdin)]"

# 筛选特定作者的 commit
curl -s "https://api.github.com/repos/your-username/hermes-agent/commits?per_page=20" |
  python3 -c "
import sys,json
for c in json.load(sys.stdin):
    a=c['commit']['author']
    print(f\"{c['sha'][:12]}  {a['name']} <{a['email']}>  {a['message'][:60]}\")"
```

如果本地 commit 使用的邮箱未被 GitHub 识别（如 `duruo@nuc.local`），推送到 fork 后不会有 GitHub 用户头像关联。

## 禁止操作

- ❌ 直接在 main 上 commit
- ❌ git push --force 到 main（除非从上游同步的场景）
- ❌ 修改核心源码（agent/ gateway/ plugins/ cli.py 等）
- ❌ 将 config.yaml/.env 包含在 commit 中
