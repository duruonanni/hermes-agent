# Hermes 源码修改工作规范

## 文件分类体系

| 类别 | 定义 | 存放路径 | 进 Git？ | 提交目标 |
|------|------|----------|----------|---------|
| **Private Config** | 环境密钥、用户偏好、本地调试开关 | `.env`, `config.yaml` | **NO** — `.gitignore` | 不提交 |
| **Local Override** | 运行时覆盖上游行为的工具/脚本 | `~/.hermes/tools/*`, `scripts/*` | **YES** | fork 仓库 |
| **Fork Commit** | fork 特有的定制化修改 | `hermes-agent/src/` DIY 改法 | **YES** | fork 仓库，不提 upstream |
| **Upstream PR** | 可回馈上游的 bugfix/feature | `hermes-agent/src/` 符合上游规范 | **YES** | 从 feature branch 提 PR |

## 工作流模板

### Local Override（最常用 — runtime 文件、配置脚本）

```bash
# 1. 确认修改类型是 runtime 文件（~/.hermes/tools/、scripts/）
# 2. 直接编辑文件
patch tools/my_tool.py ...

# 3. 测试：重启 gateway 即可生效，无需 pip install
systemctl --user restart hermes-gateway

# 4. 验证：跑实际场景确认正确

# 5. 可选提交
git add tools/my_tool.py
git commit -m "feat(tools): description"
git push origin main
```

### 源码修改（修改 venv 安装的 hermes-agent 源码）

```bash
# 1. 创建 feature 或 upstream-pr 分支
git checkout -b fix/my-bugfix

# 2. 修改源码
vim hermes-agent/tools/mcp_tool.py

# 3. 重新安装到站点包
cd ~/.hermes/hermes-agent
pip install -e .

# 4. 重启 gateway
systemctl --user restart hermes-gateway

# 5. 验证
git add -A
git commit -m "fix(tools): description"
git push origin fix/my-bugfix
# 如需上游 PR → 告知用户后操作
```

## 验证门禁（修改后必检清单）

- [ ] `systemctl --user restart hermes-gateway` exit 0，日志无 ERROR
- [ ] 跑实际 prompt 确认功能正常
- [ ] 原有功能不受影响（跑一个代表性 prompt）
- [ ] 知道回滚命令：`git revert HEAD`（已提交）或 `git checkout -- <file>`（未提交）

## 回滚方案

| 场景 | 操作 |
|------|------|
| Local Override 改错（未提交） | `git checkout -- tools/bad_file.py` → restart gateway |
| 已提交到 main | `git revert HEAD` → `git push origin main` → restart |
| Hotfix 出问题 | `git revert <hotfix-commit>` → restart |
| Private Config 改错 | 手动恢复（不 git） |

## 常见陷阱

1. **`hermes config set` 存储 args 为字符串** — `hermes config set mcp_servers.xxx.args '["foo"]'` 存成 JSON 字符串，Pydantic 校验失败。应手动编辑 `config.yaml`，用 `args: ["foo"]` (YAML 列表格式)
2. **修改源码必须 pip install -e . 再重启** — 只重启不重装不会生效
3. **GitHub 操作需事先确认用户** — 见 memory 规则8
