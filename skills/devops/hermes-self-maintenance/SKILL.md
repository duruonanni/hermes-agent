---
name: hermes-self-maintenance
description: Hermes 源码与运行时分离规范：目录架构、安全更新上游、提交本地修改、禁碰路径清单。在 ~/src/hermes-agent/ 和 ~/.hermes/
  分离后使用此 skill 维护开发工作流。
category: devops
triggers:
- 源码管理
- git pull upstream
- git push
- 目录分离
- 提交修改
- 安全操作
- 维护
- 清理
- 删除
- rm
- 迁移
- 目录结构
- cron
- 脚本丢失
- 脚本修改
- 编辑脚本
- 脚本新增
- 网络错误
- network error
- gnutls
- TLS
- 代理
- proxy
- 禁碰
- pip install
- venv
- 磁盘空间
- 释放空间
---

# Hermes Self-Maintenance

## 架构规范：源码与运行时分离

自 2026-06-05 起，`~/.hermes/` 已完成目录分离。严格区分两个角色的职责。

### 目录结构

```
~/src/hermes-agent/         ← 源码 + Git（开发层）
├── hermes_cli/ tools/ agent/ gateway/ plugins/ skills/ ...
├── pyproject.toml
├── .git/                    ← 版本控制（454M，已 gc --aggressive）
├── remotes:
│   ├── origin  → https://github.com/duruonanni/hermes-agent.git
│   ├── upstream → https://github.com/NousResearch/hermes-agent.git
│   └── pjt222   → https://github.com/pjt222/hermes-agent.git
└── 本地修改                → 10 files (skills + tools + scripts)

~/.hermes/                  ← 运行时数据（不可 Git 化）
├── venv/                   ← Python 虚拟环境（402M）
├── node/                   ← Node.js 运行时（661M）
├── skills/                 ← 运行时技能副本（52M，来自同步）
├── logs/ sessions/ cron/   ← 状态数据
├── config.yaml             ← 用户配置
├── .env                    ← API keys
├── state.db                ← 会话数据库（不可碰）
└── scripts/                ← cron no_agent 脚本目录
```

### 连接方式

```
pip install -e ~/src/hermes-agent    # 可编辑安装
systemd: WorkingDirectory=~/.hermes/  # 不可改
         HERMES_HOME=~/.hermes/      # 不可改
```

Python import 从 `~/.hermes/` CWD 启动，经由可编辑安装解析到 `~/src/hermes-agent/`。

---

## 安全操作指南

### 1. 安全 git pull upstream

```bash
cd ~/src/hermes-agent

# 1. 检查本地修改是否会冲突
git stash push -m "pre-upstream-$(date +%Y%m%d_%H%M)"

# 2. 拉取上游
git fetch upstream
git merge upstream/main --no-edit

# 3. 如果有本地修改，恢复并测试
git stash pop
```

**冲突处理：** 如果 merge 冲突，不要硬解。先中止：
```bash
git merge --abort
git stash pop
```
然后逐一文件手动合并（本地修改集中在 skills/ 和 tools/，通常无冲突）。

### 2. 提交本地修改

```bash
cd ~/src/hermes-agent

# 检查修改范围（应只包含 skills/ tools/ scripts/）
git diff --stat

# 提交
git add -A
git commit -m "feat: description of changes"

# 推送
git push origin main
```

### 3. 推送前检查清单

- [ ] 只修改了 skills/ tools/ scripts/，未动核心源码
- [ ] 没有意外包含 config.yaml / .env / state.db
- [ ] commit message 符合 Conventional Commits
- [ ] 已 `pip install -e .` 并验证 gateway 正常

---

## 禁碰路径清单

以下路径在 `~/.hermes/` 下，**绝对不要删除或移动**：

| 路径 | 原因 | 大小 |
|------|------|------|
| `venv/` | Python 环境，gateway ExecStart 指向这里 | 402M |
| `node/` | Node.js 运行时，claude-code 等依赖 | 661M |
| `state.db` | 会话数据库，丢则丢失所有对话历史 | 149M |
| `logs/` | 运行日志 | 14M |
| `sessions/` | 会话状态数据 | 5M |
| `skills/` | 运行时技能（同步自源码） | 52M |
| `config.yaml` | 用户配置 | 10K |
| `.env` | API 密钥（含 token） | 1K |

---

## 回滚指南

如果架构迁移导致问题：

```bash
# 方法 1：从备份分支恢复 ~/.hermes/.git
cd ~/.hermes
git init
git remote add origin ~/src/hermes-agent/.git
git fetch origin backup/2026-06-05-pre-migration
git checkout -b main backup/2026-06-05-pre-migration

# 方法 2：从备份 patch 恢复本地修改
cd ~/src/hermes-agent
git checkout .
git apply /tmp/pre-migration-local-changes.patch
```

---

---

## Cron 脚本管理

### 存放位置（重要：注意分辨率）

Hermes cron 系统对 no_agent 脚本的路径分辨率：**相对路径 → `~/.hermes/scripts/`**（而非 `~/.hermes/cron/scripts/`）。

因此**自定义 no_agent 脚本必须放在 `~/.hermes/scripts/`** 才能被 cron 调度器找到：

```
~/.hermes/scripts/         ← ✅ cron no_agent 脚本查找目录
├── weekly_update.sh
├── mihomo_watchdog.sh
├── cron_delivery_watchdog.py
├── daily_api_summary.py
├── memory_review.py
├── run_memory_sync.sh
└── sync_memory_to_feishu.py

~/.hermes/cron/            ← cron 配置管理目录（hermes cron 管理）
├── jobs.json              ← 作业配置
├── output/                ← 执行输出
└── scheduler.py           ← 核心调度器
```

> ⚠️ 历史教训：2026-06-05 发现 `daily_api_summary.py` 被放在了 `~/.hermes/` 根目录而非 `~/.hermes/scripts/`，导致 cron 找不到脚本。**创建 no_agent 脚本时必须放入 `~/.hermes/scripts/`**，然后 `hermes cron list` 确认路径有效。运行时可编辑安装的 `~/src/hermes-agent/` 才是源码 git 树，`~/.hermes/scripts/` 是运行时目录，不会被 git 操作清空。

### 防止脚本丢失

- 自定义脚本必须在 `~/src/hermes-agent` 的 git 仓库中跟踪
- 推送到 `local/cron-scripts` 分支
- `hermes cron list` 定期检查所有 job 的脚本路径是否有效

### 防止自定义 Skill 丢失（2026-06-05 补充）

自定义 skill（不在 upstream skills/ 或 optional-skills/ 中的）存储在 `~/.hermes/skills/`，**不受 git 保护**。自 2026-06-05 审计发现 26+ 个自定义 skill 从未进过 git。

**规范：**
1. 需要纳入 git 跟踪的自定义 skill 归入 `local/custom-skills` 分支
2. 评估标准：✅ 必须跟踪（丢失后运维降级）/ ⚠️ 建议跟踪（可重建但耗时）/ ❌ 可放生
3. 分类优先级：配置类（含本 skill 本身）> 开发调试类 > 工具封装类
4. 创建新自定义 skill 后，同步到 `~/src/hermes-agent/skills/` 下对应分类目录
5. `hermes skills sync` 后确认 manifest 无脏数据

### 修改/新增 cron 脚本的工作流

> ⚠️ 开始之前：**必须先加载此 skill**（`skill_view('hermes-self-maintenance')`），确认规范后再动手。凭记忆操作已经踩过坑。

```mermaid
flowchart LR
    A[加载 skill 确认规范] --> B[编辑 ~/.hermes/scripts/]
    B --> C[手动验证: 直接执行脚本 exit 0]
    C --> D[同步到 ~/src/hermes-agent/scripts/]
    D --> E[git add/commit<br/>到 local/cron-scripts]
    E --> F[git push origin<br/>local/cron-scripts]
    F --> G[hermes cron list<br/>确认路径有效]
```

**步骤详解：**

1. **加载 skill**：`skill_view('hermes-self-maintenance')`，确认规范的当前版本
2. **编辑运行时副本**：`~/.hermes/scripts/<name>.sh`（cron 调度器实际调用位置）
3. **手动验证**：直接在 shell 执行脚本，确认 exit 0 且输出正确
4. **同步到 git 路径**：`cp ~/.hermes/scripts/<name> ~/src/hermes-agent/scripts/`
5. **git 跟踪**：
   ```bash
   cd ~/src/hermes-agent
   git checkout local/cron-scripts 2>/dev/null || git checkout -b local/cron-scripts
   git add scripts/<name>
   git commit -m "chore(scripts): <描述>"
   ALL_PROXY=http://127.0.0.1:7890 git push origin local/cron-scripts
   ```
6. **确认生效**：`hermes cron list` 确认 job 的 script 路径有效

**处理顺序**：运行时 `~/.hermes/scripts/` → git 跟踪 `~/src/hermes-agent/scripts/`。两个方向都行，但 git 跟踪步骤不可跳过。

> 审计参考：`references/custom-cron-scripts-audit.md` 记录了全部 8 个自定义脚本的跟踪状态和操作命令。

### Silent on Success 原则

所有 no_agent 脚本遵循：
- **正常**：无输出，exit 0
- **异常**：输出错误信息，exit 非 0
- cron 只投递有输出的运行结果到飞书

### 网络/TLS 排错：GnuTLS -110

**症状**：`hermes update` 或 `git fetch origin` 通过 mihomo 代理到 GitHub 时报：

```
fatal: unable to access 'https://github.com/...':
GnuTLS recv error (-110): The TLS connection was non-properly terminated.
```

**根因**：Ubuntu 上 git 默认链接的是 `libcurl3t64-gnutls`（GnuTLS 版），通过 HTTP 代理（mihomo:7890）连接 GitHub 时，TLS 握手会间歇性地被代理提前中断。

**修复**：系统同时装有 `libcurl4t64`（OpenSSL 版），可以通过环境变量切换：

```bash
export GIT_SSL_BACKEND=openssl
```

这会让 git 使用 OpenSSL 做 TLS，完全跳过 GnuTLS 代码路径，-110 不再出现。在脚本中与其他代理变量一起设置：

```bash
export ALL_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export GIT_SSL_BACKEND=openssl    # ← 加上这行
```

注意：`git config http.sslBackend openssl` **不生效**（该 git 构建只支持 gnutls），必须用环境变量方式。

**不推荐的重试方案**：单纯加 `git fetch` 重试可能连续 3 次都遇 -110（此错误会集群出现）。先切 OpenSSL 后端再重试才是正确顺序。

---

---

## 自定义 Skill 版本管理

> **此协议在以下场景自动激活：** 创建新 Skill、修改已有自定义 Skill、删除自定义 Skill。Agent 读取此章节后必须自我执行。

### 分支与路径

- **源码仓库：** `~/src/hermes-agent`
- **分支：** `local/custom-skills`
- **目标路径：** `skills/<分类>/<skill名>/SKILL.md`（镜像运行时 `~/.hermes/skills/<分类>/<skill名>/`）
- **运行时路径：** `~/.hermes/skills/`（Skill 实际存放位置，非 git 仓库）

### 工作流

修改或新增自定义 Skill 后，按以下步骤操作：

```bash
# 1. 确认在 local/custom-skills 分支
cd ~/src/hermes-agent
git fetch origin main
git checkout local/custom-skills 2>/dev/null || git checkout -b local/custom-skills origin/main

# 2. 从运行时同步到源码
RUNTIME=~/.hermes/skills
REPO=~/src/hermes-agent/skills
cp -r $RUNTIME/<分类>/<skill名>/ $REPO/<分类>/<skill名>/

# 3. git add + commit
git add skills/<分类>/<skill名>/
git commit -m "feat(skills): <add|update|delete> <skill名>"

# 4. 推送
ALL_PROXY=http://127.0.0.1:7890 git push origin local/custom-skills
```

### 提交规范

| 操作 | Commit 格式 | 示例 |
|------|------------|------|
| 新增 Skill | `feat(skills): add <skill名>` | `feat(skills): add skill-lint` |
| 修改 Skill | `feat(skills): update <skill名>` | `feat(skills): update skill-lint` |
| 删除 Skill | `feat(skills): remove <skill名>` | `feat(skills): remove skill-lint` |

### 合规检查

每次涉及 `~/.hermes/skills/` 操作的会话结束时，执行：

```bash
cd ~/src/hermes-agent && git status -- skills/
```

如果有未跟踪或已修改的 skill 文件，执行上述工作流后再结束会话。

### 批量提交（首次）

首次将现有自定义 Skill 纳入 git 跟踪时，用单次 commit 提交所有 Skill：

```bash
cd ~/src/hermes-agent
git fetch origin main
git checkout -b local/custom-skills origin/main
# 复制所有需要跟踪的 skill 目录到 skills/ 下
# git add 所有新 skill 目录
git commit -m "feat(skills): add N custom skills"
ALL_PROXY=http://127.0.0.1:7890 git push -u origin local/custom-skills
```

### 触发条件

`hermes-self-maintenance` Skill 的触发条件已包含以下场景（见 frontmatter triggers）：
- skill 文件创建或修改
- 涉及 `~/.hermes/skills/` 的操作
- 会话结束时的合规检查

---

## 2026-06-05 事故教训

### 事故：venv 自我删除

Hermes 在执行"~/.hermes/ 目录清理"时删除了 `hermes-agent/venv/`，
导致 certifi TLS 证书丢失，所有 HTTPS 通信瘫痪 12 分钟。

**根因**：清理边界不明确，把运行时依赖当作可清理文件。

**教训**：
1. 任何删除操作前，先 `ls -la <target>` 确认内容
2. 禁碰路径清单（见上表）必须严格遵守
3. 清理只针对明确的白名单，不对整个目录做批量删除
4. 如果命令涉及 `rm -rf`，必须先获得用户确认

### 事故：cron 脚本丢失

源码迁移时 `~/.hermes/scripts/` 被清空，5 个未 git 跟踪的自定义 cron 脚本丢失。

### 事故：自定义 Skill 在 Git Cleanup 中被清除

2026-06-04，`~/.hermes/` Git 仓库被重置到 upstream/main，所有自定义 skill
（`skill-lint`, `skill-maintenance-audit`, `verify-system-state` 等）被清除，
因为它们在 upstream 中不存在。

**根因**：`~/.hermes/` 在目录分离前是一个 Git 仓库（远程指向 upstream），
重置操作使所有不在 upstream 中的自定义文件被清除。

**教训与后续措施**：
1. `~/.hermes/` 在 2026-06-05 后已不再是 Git 仓库 — 此事故不会再发生
2. 自定义 skill 应优先写成 SKILL.md 引用支持文件（references/ templates/ scripts/），
   而非作为独立技能文件存在，减少被误删的范围
3. 创建自定义 skill 后，考虑将脚本文件备份到 `~/src/hermes-agent/scripts/`

**教训**：
1. no_agent 脚本放 `~/.hermes/scripts/`（cron 调度器的查找目录），同时 git 跟踪到 `~/src/hermes-agent/scripts/`
2. 所有自定义脚本必须 git 跟踪
3. 迁移前 `hermes cron list` 检查所有脚本路径
4. 创建新 no_agent 脚本后手动执行一次验证，再确认 cron 下次调度能找到文件

---

## 参考

- 迁移日期：2026-06-05
- 备份分支：`backup/2026-06-05-pre-migration`
- 备份 patch：`/tmp/pre-migration-local-changes.patch`（755 行，418+/118-）
- 释放空间：~/.hermes/ 从 2.6G → 1.5G（清理 .git 1.1G + 源码 ~70M + cleanup-backup + hermes-dev）

---

## Cron Script Not Found 排错参考

### 典型症状
watchdog 或 cron 日志报 `Script not found: /home/duruo/.hermes/scripts/<name>.py`

### 排查步骤
1. `ls -la ~/.hermes/scripts/<name>.py` 确认文件在不在正确位置
2. 如果不在：`find ~/ -name "<name>.py" 2>/dev/null` 找实际位置
3. 常见错位：放在 `~/.hermes/` 根目录（本例原因）、`~/.hermes/cron/scripts/`（旧 skill 错误指导）
4. 修：复制到 `~/.hermes/scripts/` 并 chmod +x

### 验证
```bash
cd ~/.hermes/scripts && python3 <name>.py    # 手动执行
ls -la ~/.hermes/scripts/<name>.py            # 确认 watchdog 能发现
```

### 路径分辨率规则
| Cron 类型 | 脚本查找目录 |
|-----------|-------------|
| no_agent（script=相对路径） | `~/.hermes/scripts/` + script 名 |
| 有 prompt 的 agent 任务 | 不查脚本，走 LLM 推理 |

> `~/.hermes/scripts/` 是运行时目录（不是 git 树），而 `~/src/hermes-agent/` 才是源码 git 根。

---

## Custom Skills 保护

### 背景

自定义 skill 存放在 `~/.hermes/skills/`（运行时目录），**没有 git 保护**。
`skill_manage(action='create')` 创建的新 skill 默认只写磁盘，不进 git。
如果在 `~/src/hermes-agent/` 下执行 git reset/clean（例如从 upstream pull 后回退），
这些 skill 会从文件系统上消失——2026-06-04 发生过。

### 风险分级

| 风险级别 | 特征 | 示例 | 建议动作 |
|---------|------|------|---------|
| 高 | 用户自己写的、每周/每天用的运维核心 skill | `hermes-self-maintenance`, `self-code-management`, `skill-maintenance-audit` | 应优先进 git |
| 中 | 一次性配置的、可远程安装的 | `headless-chrome-screenshot`, `webhook-subscriptions` | 酌情跟踪 |
| 低 | API 参考、文件模板，重新获取成本低 | `deepseek-api`, `html-to-pdf` | 丢了再写也不亏 |

### 审计命令

```bash
# 找出从未进过任何 git branch 的 custom skill
cd ~/src/hermes-agent
find ~/.hermes/skills -name "SKILL.md" -maxdepth 3 | while read f; do
  dir=$(dirname "$f")
  rel="${dir#/home/duruo/.hermes/skills/}"
  name=$(basename "$dir")
  cat="${rel%%/$name}"
  found=$(git log --all --oneline -- "skills/$cat/$name/SKILL.md" "skills/$name/SKILL.md" 2>/dev/null | head -1)
  [ -z "$found" ] && echo "❌ NOT IN GIT: $cat/$name"
done
```

### 保护工作流（git 跟踪自定义 skill）

```bash
cd ~/src/hermes-agent
git checkout -b local/custom-skills        # 或 local/core-devops
# 复制 skill 目录到 git 路径
cp -r ~/.hermes/skills/<category>/<name> skills/<category>/
git add skills/<category>/<name>/
git commit -m "chore(skills): track custom skill <name>"
ALL_PROXY=http://127.0.0.1:7890 git push origin local/custom-skills
```

> 完整审计结果：`references/custom-skills-audit.md`

---

## Skills Manifest 调试

### 背景

`~/.hermes/skills/.bundled_manifest` 是同步时从源码 skills/ 目录生成的清单，格式 `skill_name:md5_hash`。
当 bundled source 变更（如目录分离后换 fork 源码、上游更新），manifest 可能残留在旧状态：

- **manifest 条目数 > 源码 skills 数** → manifest 混入了旧同步遗留的技能名
- **manifest 中的 md5 与磁盘文件不匹配** → 用户本地改过，或 manifest 来自不同版本的源码

### 判断自定义技能的正确方法

1. 读 manifest 获取 bundled 技能名
2. 遍历磁盘所有 SKILL.md 获取实际技能名
3. 不在 bundled 中的 = 自定义技能（含上游官方但 fork 没有的）

### 清理脏 manifest

运行 `hermes skills sync`，或等价地：

```bash
cd ~/src/hermes-agent && python3 -c "
from tools.skills_sync import sync_skills
result = sync_skills(quiet=False)
print(f'cleaned: {len(result[\"cleaned\"])} stale entries')
"
```

这会重新同步源码 skills 到运行时目录，并清理不在源码中的 manifest 条目。

### 常见陷阱

- **误判"系统技能已收录自定义内容"**：manifest 脏数据会让人误以为自定义技能已被官方采纳。先用 sync cleanup 再对比。
- **bundled source 解析顺序**：HERMES_BUNDLED_SKILLS env → wheel 包数据目录 → 源码 checkout → ~/.hermes/skills 兜底。editable install 走源码 checkout。
- **md5 不匹配不一定是用户改过**：manifest 来自旧版本源码时 md5 也不同。运行 sync 可重建正确 md5。
- **不要用废弃方法对比**：不用 `~/.hermes/skills/ vs ~/.hermes/hermes-agent/skills/`，改用 `.bundled_manifest`。
