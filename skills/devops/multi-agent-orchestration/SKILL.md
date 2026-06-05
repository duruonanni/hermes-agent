---
name: multi-agent-orchestration
description: "多 Agent 协同调度框架 — 遇到架构决策、跨用户设计、编程、技术调研时，按角色委派"
version: 1.5.0
author: Duruo + Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [orchestration, multi-agent, decision, architecture, coding]
    related_skills: [feishu-doc-suggestion, personal-assistant-multi-user]
---

# 多 Agent 协同调度框架

遇到复杂任务时，不自己硬干。拆任务后按角色委派。

---

## 触发条件（只要命中任意一条就加载本 skill）

1. **编程类** — 新功能开发、Bug 修复、重构、代码审查
2. **架构/方案/流程设计** — 系统架构、技术选型、流程规范制定、标准设计、用户行为/记忆架构设计
3. **跨周期决策** — 影响两个以上用户的决策、长期运维方案、系统改造
4. **联合评估** — 需要多个模型给出不同意见再汇总的决策（Task Level 4）
5. **兜底规则** — 任何我第一反应想「自己出方案」的事情，先加载本 skill 再判断
6. **用户明确说** — 「找大家评估一下」「拉上其他人讨论」「走 Pipeline」

---

## 角色定义

| 角色 | 模型/工具 | 职责 | 操作方式 |
|------|-----------|------|---------|
| **我（Orchestrator）** | DeepSeek V4 Flash | 任务分解、Agent调度、结果汇总 | 直接对话 |
| **军师（Architect）** | DeepSeek V4 Pro | 架构设计、算法方案 — 出方案不写代码 | delegate_task |
| **研究员（Researcher）** | MiMo V2.5 Pro | 技术调研、文档生成、测试用例 | delegate_task |
| **主力程序员（Coder）** | Codex CLI (GPT-5.5) | 新功能/模块开发。需代理，不稳定换 Cursor | terminal |
| **替补程序员（Fixer）** | Cursor CLI (composer-2.5) | Codex 不可用时替补，局部修改 | terminal |
| **审查官（Reviewer）** | Claude Code | 代码审查、复杂重构 | terminal |

---

## 委派前分类：Analyze vs Execute（核心决策）

**这是委派前必须做的第一件事。** 在调用任何 `delegate_task` 前，先确定任务的类型：

| 分类 | 定义 | `readonly=` | 示例 goal 措辞 |
|------|------|------------|---------------|
| **🔍 Analyze** | 评估、调研、推荐、方案对比。输出是文本/分析。 | `True` | "评估方案可行性", "搜索社区最佳实践", "分析错误模式", "比较两种方法" |
| **🛠️ Execute** | 创建、修改、删除文件。运行测试产生新状态。 | `False` | "实现功能 X", "修复 Bug Y", "重构模块 Z", "添加测试覆盖" |
| **🧪 Review** | 读代码、对比 spec、检查质量。不写文件。 | `True` | "验证 spec 合规性", "检查代码质量", "验证测试覆盖率" |
| **🔬 Explore** | 调查运行时行为、调试、性能分析。可能用 terminal 但不该改源码。 | `True` | "调试测试失败原因", "分析性能瓶颈", "追踪数据流向" |

**常见陷阱：** 一个 goal 如 "分析错误并修复" 听起来是 Analyze，但子代理听到 "修复" 就要求写文件权限。解决方案：
1. **双阶段委派：** 先 `readonly=True` 分析并给出修改建议，你审核通过后再 `readonly=False` 执行
2. **Goal 措辞控制：** Analyze 类任务避免用 "修复"、"实现"、"应用" — 改为 "评估"、"推荐"、"提出修改方案"
3. **默认 readonly：** 除非你明确需要子代理写文件，否则始终 `readonly=True`

**默认规则：** `readonly=True` 用于所有 `delegate_task` 调用。只有当你明确需要子代理写文件时，才设为 `readonly=False`。

---

## 委派规则

**编程任务（新功能）：**
1. 军师（DS Pro）→ 出架构方案
2. 研究员（MiMo）→ 并行查资料
3. 主力程序员（Codex CLI）→ 写代码（不通则换 Cursor）
4. 审查官（Claude Code）→ Review
5. 我 → 汇总给用户

**Bug 修复：**
1. 替补（Cursor CLI）→ 定位修复
2. 审查官（Claude Code）→ 验证
3. 我 → 汇总

**技术调研/方案评估：**
1. **【前提门】** 检查所有将传给子代理的 context/背景信息。逐条问：这条是用户说的还是技能示例？如果来自 skill 模板示例 → 删除或标记为未确认。如果无法确认来源 → 先问用户。
2. 研究员（MiMo Pro）→ 调研 + 评估
3. 军师（DS Pro）→ 从架构角度评估
4. 我 → 综合给出推荐

**评估 + 文档输出（单阶段联合交付）：**

当用户要求「评估问题 + 生成 PPT/Word 等 Office 文档」时，这是一个完整的端到端流程，不需要分两阶段：

1. 研究员（MiMo Pro，`toolsets=["web"]`）→ 搜索社区最佳实践、类似案例
2. 军师（DS Pro，`toolsets=["_no_tools"]`）→ 出评估分析和方案草案
3. 我 → 合并两份产出，用 OfficeCLI MCP 工具生成 PPT（多页，含分歧展示 + 推荐方案）
4. Office 文档通过 `send_message` 或 `MEDIA:` 路径发送给用户

**关键规则：**
1. 子代理只用 `delegate_task` 做分析推理，不生成文档——文档生成是 Orchestrator 的职责
2. PPT 结构应至少包含：封面 → 问题描述 → 分歧展示（军师/研究员各一页）→ 推荐方案 → 总结
3. 分歧必须诚实展示，不能强行统一
4. 使用 `mcp_officecli_officecli` 工具时注意 `args: ["mcp"]` 必须是 YAML 列表而非 JSON 字符串

**跨用户设计决策（如记忆隔离方案）：**
1. **【前提门】** 检查所有将传给子代理的 context/背景信息。逐条问：这条是用户说的还是技能示例？如果来自 skill 模板示例 → 删除或标记为未确认。如果无法确认来源 → 先问用户。
2. 研究员（MiMo Pro）→ 评估方案可行性和风险
3. 军师（DS Pro）→ 从架构和长期维护角度评估
4. 我 → 汇总给用户

**流程/规范/标准设计（双阶段）：**

这种任务天然需要两轮讨论——先定方案内容，用户确认后再评估落地形式。千万不能自动推进。

**阶段一：定方案内容**
- 研究员（MiMo Pro，`toolsets=["web"]`）→ 搜社区最佳实践、类似规范、行业标准
- 军师（DS Pro，`toolsets=["_no_tools"]`）→ 从架构/工程角度出草案
- 我 → 合并两份产出，展示给用户

**阶段二：评估落地形式（用户确认方案内容后）**
- 研究员（MiMo Pro，`toolsets=["web"]`）→ 调研各落地形式的社区经验、工具链支持
- 军师（DS Pro，`toolsets=["_no_tools"]`）→ 评分表：强制力 / Token开销 / 维护成本 / 发现成本
- 我 → 综合给出渐进式推荐路径（如 B→C→A 分级），让用户选择介入深度

**关键规则：**
1. 用户说「方案可以」≠ 用户想落地。必须等待用户明确表态后才推进阶段二
2. 阶段二输出应是一个带评分表的推荐路径，而不是单一答案
3. 如果用户说「落地形式我不太懂」→ 先解释各选项的差异再委派评估

## 结果汇总：子代理分歧处理

**问题：当两个子代理给出不同结论时怎么办？** 这不是异常，而是正常现象——研究员（MiMo）从行业实践出发，军师（DS Pro）从架构约束出发，关注点不同，结论可能冲突。

### 分歧检测

```python
# 子代理返回后，比较结论
mimo = mimo_result['summary']   # 研究员结论
dsp = dsp_result['summary']     # 军师结论

# 检查关键维度是否一致
disagreements = []
if mimo_opinion_on_merge != dsp_opinion_on_merge:
    disagreements.append(f"粒度分歧: 研究员说{'合并'}, 军师说{'分开'}")
if mimo_opinion_on_risk != dsp_opinion_on_risk:
    disagreements.append(f"风险评估分歧: {mimo_risk} vs {dsp_risk}")
```

### 分辨率启发式

| 分歧类型 | 权重规则 | 示例 |
|---------|---------|------|
| **架构/粒度问题** | 采纳军师（DS Pro）意见 | 1个还是2个Skill → 看上下文边界和触发条件是否真的不同 |
| **行业实践/社区方案** | 采纳研究员（MiMo）意见 | 业界如何解决同类问题 → 研究员更贴近实际 |
| **风险评估** | 取并集（最保守） | 一个说"低风险"，一个说"中风险" → 报告中风险 |
| **功能性建议** | 取叠加（能做就做） | 一个说"加hook"，一个说"配强度模式" → 两阶段都做 |

### 呈现原则

1. **诚实展示分歧** — 不要强行统一。用户问「团队结论」时，必须说清 A 说 X 而 B 说 Y
2. **给明确推荐** — 分歧不意味放弃判断。给了两个观点后，必须附上你的最终推荐
3. **标注置信度** — 如果分歧源于信息不对称（研究员知道社区方案但军师不知道），标注「此点存疑，建议进一步验证」
4. **让用户做最终决策** — 分歧是正常的，但最终选择权在用户

### 成功案例（2026-06-03：GitHub Skill 评估）

**场景：** 评估创建两个 Git 操作规范 Skill 的需求。研究员（MiMo）和军师（DS Pro）在粒度上存在分歧：

| 维度 | 研究员（MiMo） | 军师（DS Pro） |
|------|---------------|---------------|
| 需求合理性 | 完全合理 | 完全合理 |
| 粒度 | **合并为 1 个** `git-workflow-discipline` | **保持 2 个**，不合并 |
| 分歧原因 | 认为有重叠（force push 双方都提及） | 认为本地/远程触发条件差异大 |
| 特殊建议 | 配置化强度、一键修复、git hook | 双重防护、Fail-Fast、terminal gate |

**处理方法：** 按架构/粒度分歧规则（采纳军师），理论上选择 2 个 Skill（本地/远程分离）方案。但在实际实施时，因 `github-pr-workflow` 已有完备的 PR 生命周期覆盖，最终**集成到现有的 `github-pr-workflow` 一个 Skill 中**（新增 §2.5 Pre-Push Local Hygiene 和强化 PR Discipline Gates），未创建独立 Skill。研究员对重叠的担忧被转化为「明确分工边界、force push 检查只放在本地 Hygiene 段，PR 检查只放在 PR Discipline 段」的约束。

> ⚠️ 如果你也遇到「创建新 Skill 还是集成到现有」的决策，先搜索已有的 skill 库和 references/ 目录。当前会话（2026-06-04）就是在未检查先例的情况下直接创建了 Kanban 任务提议创建新 Skill，而评估结果其实已经存在。

### 成功案例（2026-06-04：并行评估 Git 清理计划）

**场景：** Git 仓库清理——6 个分支要从旧版 upstream 迁移到最新 upstream/main，包含同文件冲突合并、备份策略、pip 重装等复杂步骤。

**方法：** 两个子代理用 `toolsets=["_no_tools"]` 并行评估（每个 1-1.5K token 入站）：
- **军师（DS Pro）** → 评估风险和执行顺序 → 找到 3 个风险点（备份粒度不足、个人文件保护遗漏、pip 命令歧义）
- **研究员（MiMo Pro）** → 评估分支粒度和同文件冲突 → 找到 2 个隐藏的同一文件冲突（hermes-agent-skill-authoring/SKILL.md + github-pr-workflow/SKILL.md 同时出现在 staged/unstaged/stash）

**结果：** 两者无原则性分歧，结论互补。优化后的计划合并了两者全部反馈。总 token 消耗：~2.5K 入站、~2.6K 出站。

> 并行 `_no_tools` 评估模式特别适合计划评审——子代理只基于你给的摘要推理，不会重复搜索，零 token 浪费，而且两个不同角度的代理能找到几乎不重叠的问题。

### 成功案例（2026-06-04：Kanban 评估 → PPT 交付）

**场景：** 用户要求对看板中两个待办任务进行团队评估，并以 PPT 格式输出评估报告。两个任务分别是「创建两个 Skill」和「目录清理与结构重组」。

**方法（单阶段联合交付）：**
- 研究员（MiMo，`web`）→ 搜索社区实践（Hermes Skill 最佳实践、目录结构推荐、类似清理案例）→ 发现 SkillsMP 35万+ 索引无现成匹配，推荐创建独立 Skill
- 军师（DS Pro，`_no_tools`）→ 从架构角度评估 → 推荐集成到现有 `github-code-review` Skill
- **分歧处理**：团队在粒度上存在分歧（独立 vs 集成），按架构/粒度规则采纳军师
- **文档输出**（Orchestrator 职责）：合并两份报告后，用 `mcp_officecli_officecli` 工具生成 8 页 PPT（封面 + 任务A评估 + 军师观点 + 研究员观点 + 推荐方案 + 任务B诊断 + 五阶段方案 + 总结），通过 `send_message` 发送到飞书

**关键洞察：**
- 评估 + 文档输出可以单阶段完成，不需要等用户确认再出文档
- OfficeCLI MCP 的 `batch` 命令不适合多页 PPT（props 格式限制），最好逐页用 `add slide` 加 `--prop title= / --prop text=`
- 分歧展示页是 PPT 最有价值的部分——用户能看到两方观点再决定

**参考文件：** `references/kanban-evaluation-ppt-2026-06-04.md`

### 成功案例（2026-06-04：规范设计双阶段讨论）

**场景：** 用户需要建立「源码修改标准工作规范」——先讨论规范内容，再讨论规范落地形式（AGENTS.md vs Skill vs git hook）。

**方法（双阶段）：**
- **阶段一（方案内容）**：研究员（MiMo，web）搜社区最佳实践（Claude Code CLAUDE.md 分层、Aider 自动 commit、pre-commit hook 策略）+ 军师（DS Pro，_no_tools）出规范草案（文件分类体系 + 4 套工作流模板 + 验证门禁 + 回滚方案）
- **阶段二（落地形式）**：用户说「方案可以 落地形式我不太懂」→ 研究员（MiMo，web）查社区三层防御案例（htek.dev 文章、Reddit r/hermesagent 讨论）+ 军师（DS Pro，_no_tools）做 4 选项评分表（强制力/Token/维护/发现）→ 推荐 B→C 渐进式路径

**关键洞察：**
- 用户说「方案可以」≠ 用户想落地。规范设计天然需要两轮讨论（what + how）
- 双阶段之间必须等待用户明确确认，不能自动推进到第二阶段
- 第二阶段输出是一个带评分表的推荐路径（如「先走 B→C，需要再加 A」），让用户选择介入深度
- 如果用户说「落地形式我不太懂」→ 先解释各选项的差异评估再委派

**参考文件：** `references/workflow-design-discussion-2026-06-04.md`

---

## 委派命令

### Hermes 内部（delegate_task）
- 军师/研究员：`delegate_task(goal="...", toolsets=[], context="...")`
- 注意：这两人不做 shell/file 操作
- **必须包含当前会话的完整上下文**（文件路径、用户 open_id、已有的配置）

### 🎯 delegate_task 上下文优化（降低 Token 消耗）

DS Pro / MiMo Pro 的输入 token 计费较高。一次不优化的 delegate_task 可能消耗 70 万+ token（如 2026-06-03 的 DS Pro 调用），而优化后可以降到 1-2 万 token，节省 95%+。

**优化原则：我预读 → 我总结 → 发摘要**

```
❌ 坏模式：把原始文件和搜索结果全部倒入 context
context = f"MEMORY.md: {read_file('MEMORY.md')}\nUSER.md: {read_file('USER.md')}\nskill: {skill_view('xxx')}"
→ 子代理到达后还有全量工具集，会独立重读已经读过的内容、做无效搜索
→ 740K token 消耗，DS Pro 零 cache 命中

✅ 好模式：我读好 → 浓缩摘要 → 只发摘要
context = f"""
## 已知事实（已从文件读取并验证）
- 用户 A：open_id xxx，技术背景（MEMORY.md §用户身份已确认）
- 用户 B：open_id yyy，求职中（MEMORY.md §用户身份已确认）
- 当前规则：MEMORY.md 规则 1-7 已启用
- 等你的决策：...（30-50 字精确定义问题）
"""
→ 1-5K token，子代理直接进入推理环节
```

**具体步骤：**
1. 先自己 `read_file` 读完需要的信息
2. 提取关键事实，删除无关上下文
3. 将事实组织为「已知事实（已验证）」块
4. 精确定义「等待你做的决策」（不超过 50 字）
5. 只发这个摘要给 delegate_task

**例外：** 如果子代理需要自己探索（如调研未知的 API、读社区 Issues），才发原始资料。此时限制 `toolsets` 避免不必要的搜索。

### CLI Agent（terminal）
- Codex：`HTTPS_PROXY=http://127.0.0.1:7890 codex exec --skip-git-repo-check "任务"`
- Cursor：`agent --print --trust --model composer-2.5 "任务"`
- Claude Code：调用方式视超时需求选择：
  ```bash
  # 用 wrapper（120s 硬超时，适合短任务）
  HTTPS_PROXY=http://127.0.0.1:7890 claude-code --print "prompt"

  # 直接调二进制（可设更长 timeout，适合评估/分析类长任务）
  ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic" \
  ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY" \
  ANTHROPIC_MODEL="deepseek-v4-pro[1m]" \
  CLAUDE_CODE_SIMPLE=1 \
  ALL_PROXY=http://127.0.0.1:7890 \
  ~/.hermes/node/bin/claude --print "prompt"
  ```
  Claude Code 后端是 DeepSeek V4 Pro 1M，可作为军师/审查官的替代评估来源（2026-06-05 已验证）。

### 透明性原则（2026-06-05 用户明确要求）

调用任何外部 CLI Agent（Claude Code、Cursor、Codex）时，必须执行以下步骤：

1. **显示调用命令** — 在回复中写出完整的 shell 命令（含环境变量、代理、参数）
2. **显示原始输出** — 将 stdout/stderr 原文贴出，不总结、不剪辑、不美化
3. **区块分离** — 严格分离「原始输出」与「我的分析」两个区块，让用户能独立判断原始输出后再看你的解读
4. **超时透明** — 如果设置了自定义 timeout，标注出来；如果失败了也显示完整错误，不要默默重试

这是 Duruo 2026-06-05 明确要求的透明原则：「别骗我，把调用他的过程和结果都打印给我看」。

---

## 关键原则

1. **我不直接处理复杂子任务** — 只拆解和调度。如果发现自己在「想方案」，停下来检查是否应该委派
2. **🧩 前提验证优先 — 严格禁止 Chain Hallucination** — 在委派任务前，必须检查委派的内容（任务描述、背景事实）是否来自**可信来源**。可信来源的定义：
   - ✅ MEMORY.md / USER.md 中用户亲自确认的内容
   - ✅ 通过 `read_file` / `terminal` 验证过的实时系统状态
   - ❌ Skill 文件中的代码块、缩进模板、`[user:xxx]` 标记段 — 这些都是**上轮 Agent 写出的模板示例，不是用户确认的事实**
   - ❌ 你自己「我记得上次会话里用户说过...」的推断

   **Chain Hallucination 的具体杀伤链：**
   ```
   Skill 模板示例（Agent 写的，含 [user:duro] 语气偏好）
      ↓ 你加载 skill 时误认为真实用户偏好
   delegate_task 将假前提传给 MiMo / DS Pro 子代理
      ↓ 子代理基于假前提产出长篇分析（看起来非常合理）
   Pipeline 放大了错误 3 倍：子代理 A 的假结论被代理 B 引用
      ↓
   你的汇总看起来专业可信，但根全是假的
   ```

   **强制检查清单（委派前必须执行，一次）：**
   ```
   [ ] 我传的 context 里有 skill 文件中的代码块或模板内容吗？
   [ ] 这些内容在 MEMORY.md / USER.md 中有对应的真实条目吗？
   [ ] 我是否用自己的记忆替代了实际验证？（危险信号：否定断言）
   [ ] 如果将 context 中的「事实」删掉，子代理还能正确执行吗？
   ```
   ## ⚠️ 已知陷阱

   ### 陷阱1：利用工具集的伪评估

   当 `toolsets=[]` 仍继承父集工具时（上游 bug #11279，当前版本未修复），delegate_task 给子代理虽然是空的 toolsets=[]，但子代理仍然保有 39 个核心工具。一次"只推理不操作"的委派可能消耗 74 万 token。

   **修复前规避方案：**
   - 在 context 中预读所有文件，只发浓缩摘要给子代理
   - 显式在 goal 中加 "analyze only, do NOT use any tools"

   ### 陷阱2：前提未验就委派（Pipeline 放大错误）

   本会话（2026-06-03）暴露的模式：加载 skill → 看到模板示例 → 当事实 → 委派给 MiMo + DS Pro → 两个模型基于假前提产出长篇分析。**Pipeline 正确执行了，但前提是假的，错误被放大三倍。**

   **防御步骤：**
   1. 委派前，识别 context 中的关键前提假设
   2. 对每个前提，自问：这是用户确认的事实，还是 skill 模板示例，还是我自己推导的？
   3. 如果不确定，先问用户，再委派

   ### 陷阱3：虚假的"团队评估"

   本会话（2026-06-03）犯的错：用默认模型（DS Flash）做了分析，然后包装成「团队评估」的语气说给了用户。用户问「团队具体调用了哪些」时才暴露。

   **规则：** 如果只委派了一个子代理，不要说「团队评估」或「小伙伴们说」。只有真正调了多个不同模型并交叉验证后，才能用"多模型评估"的说法。否则直接说「我用 DS Pro 分析得到的结论」。

   ### 陷阱4：子模型编造 API / Hook 名称

   本会话（2026-06-03）暴露的模式：委派 DS V4 Pro 评估问题时，DS Pro 在回答中声称 Hermes 有 `before_response` hook，描述了一个完整的但**根本不存在的** API 机制。实际上 Hermes 只有 `pre_tool_call` hook（Model Tools 层，928 行）。DS Pro 的这段描述完全是在训练数据中见过类似名称后编造出来的。

   **杀伤链（类似 Chain Hallucination 但针对*技术事实*而非用户偏好）：**
   ```
   DS Pro → 编造 "Hermes has a before_response hook"
      ↓ 我未经验证就信了，准备使用这个不存在的 API
      ↓ 用户问起时，我才正式查代码，发现 hook 不存在
      ↓ 信任成本：用户无法区分我哪次说了实话哪次是转述了编造的 API
   ```

   **防御步骤（与其他陷阱不同的重点）：**
   1. **子模型输出的技术性断言（API 名称、框架功能、命令行选项）必须本地验证**
   2. 这与用户偏好的验证不同——技术事实可以通过 repo 代码、文档或 `curl` 测试快速证伪
   3. 当子模型描述了一个「看起来很优雅但没听说过」的功能时，**反直觉反应**是要怀疑的——LLM 倾向于生成听起来合理的名称
   4. 如果无法本地验证，在汇总给用户时必须标注「这是 DS Pro 的声称，未经验证」

   **已知失效案例（2026-06-03）：** DS V4 Pro 回答中称 Hermes 有 `before_response` hook。实际代码中该 hook 不存在。用户没有直接指出这个错误，但表示了对整个评估信任度的质疑。修复后确认：Hermes 只有 `pre_tool_call` / `post_tool_call` / `transform_tool_result` 三个 Plugin hook（`model_tools.py:928-1006`），没有 Response 层 hook。

   ### 陷阱5：toolsets=[] 的 falsy 陷阱

   Python 的 `if toolsets:` 把空列表 `[]` 当作 False，导致 `toolsets=[]` 回退到继承父集工具。上游已有修复但未合并。

   **正确做法：** 纯推理委派用 `toolsets=[\"_no_tools\"]`（假工具集名，与父集取交集后为空）或显式在 context 里禁工具。

   ### 陷阱6：未检查框架内置能力就自己造轮子

   本会话（2026-06-04）暴露的模式：用户需要 git 操作安全防护 → 直接写了 `git-guard` Hermes Plugin（`pre_tool_call` 拦截 git destructive 命令）→ 用户问「是不是已经有现成方案」→ 查代码发现 `tools/approval.py` 已经有完整的 DANGEROUS_PATTERNS 列表 + approval 提示系统，本来加个正则就行了。

   **杀伤链：**
   ```
   用户说「需要 git 操作保护」
      ↓ 我直接写 Plugin
   写了 2 个文件（git-guard plugin）
      ↓ 其实 Hermes 框架已经有 approvals 系统
   重复劳动：Plugin 做的事（pre_tool_call 拦截 git 命令）
      = approvals.py 已经做了同样的事（DANGEROUS_PATTERNS 匹配 + 提示）
   区别：approvals 是框架级别的，跨所有会话；plugin 是本地的，只在此 Hermes 实例上
   ```

   **防御步骤：**
   1. 在写任何 Plugin / Hook / 定制逻辑前，先查 `tools/approval.py`、`hermes_cli/plugins/`、`config.yaml` 的 `command_allowlist`
   2. 特别关注：`DANGEROUS_PATTERNS` 列表是否已覆盖需求（`tools/approval.py` 第 336-448 行）
   3. 如果框架已有机制但缺某个 pattern → 加一个正则，而不是写整个 Plugin
   4. 只有框架完全不支持的场景（如 git hook 这种在 Python 进程外部运行的防护）才造新轮子
   5. 给用户出方案前先查，不要等用户问「有没有现成的」

   **应用场景检查清单（写新工具/插件/钩子前必看）：**
   ```
   [ ] 需求属于「拦截/阻止/审批」类？→ 查 tools/approval.py
   [ ] 需求属于「文件写入安全」类？→ 查 plugins/security-guidance
   [ ] 需求属于「工具可用性」类？→ 查 tools/registry.py 的 check_fn
   [ ] config.yaml 里有没有已有的配置项？（command_allowlist, approvals.mode）
   [ ] 是否真的需要写一个完整 Plugin，还是加个正则就能解决？
   ```

   6. **委派前必须验证前提** — 每次 delegate_task 前，确认 context 中的事实性声明（用户偏好、配置状态、文件内容）已经通过工具调用验证。如果前提可能不实，先用 `read_file` 或终端命令确认。发给子模型的 context 中标记 `<verified_facts>` 区块。
   7. **DS Pro 缓存优化** — DS Pro 没有 prefix cache 机制，每次 delegate_task 都是全新上下文。优化方法：先自己预读文件，浓缩成 2-3K token 的摘要，再发给 DS Pro。不要让 DS Pro 自己去做 web_search 和 read_file——这些调用不仅浪费 token，还无法命中缓存。

## Pipeline 错误放大防护

当 pipeline 涉及多个子代理时，每一级都可能在前一级的结论上构建，导致错误指数级放大。

### 三明治隔离模式

```
# ❌ 错误：MiMo 的假结论被直接传给 DS Pro
context = f"用户偏好：{mimo_result['preferences']}"
ds_result = delegate_task(goal='评估方案', context=context)

# ✅ 正确：每级之间做前提审查
# 1. MiMo 输出后，先验证其关键前提（特别是涉及用户偏好的断言）
# 2. 只传递 verified 的事实给 DS Pro
clean_context = "已验证前提：服务器IP已确认，用户偏好已根据MEMORY.md核对"
ds_result = delegate_task(goal='评估方案', context=clean_context)
```

### 参考文件
- `references/source-modification-workflow.md` — 源码修改工作规范：文件分类、4 种修改工作流、验证门禁、回滚方案。在修改 Hermes 源码或 runtime 工具前查阅，确定当前修改属于哪一类以及对应的提交/部署流程。
- `references/pipeline-error-amplification-2026-06-03.md` — Chain Hallucination 的完整案例分析、管道放大机制、以及分步修复方案

## 自检机制：发现自己在「直接出结论」时

这个 skill 最常见的失效模式是：agent 的触发判断本身出了问题，根本没加载本 skill。下面的自检清单就是用来拦截这种情况的。

**当遇到复杂问题/架构决策/方案设计时，执行以下自检：**

```
自检步骤：
[ ] 这个任务涉及多步骤（≥3）还是跨周期？
[ ] 这个决策影响两个以上用户？
[ ] 这个问题的答案有多种方案需要对比？
[ ] 我的第一反应是「直接给方案」（危险信号）？
[ ] 我刚刚加载了另一个 skill，觉得「够了」（危险信号——多个 skill 应同时加载）？
[ ] 这个问题涉及到我没有当面验证的事实（比如用户偏好、语气风格）？
[ ] 我加载的 skill 里是否有示例/模板内容被我当成了事实？是否检查过实际的 MEMORY.md/USER.md 文件？
[ ] 我加载的 skill 里是否有 **WARNING / ⚠️ / Marked / Known Failure** 块？这些块是否描述了我正要犯的错误？

有一项为「是」或「说不准」→ 加载本 skill，走 Pipeline
全为「否」→ 可以直接回复
```

### WARNING 块扫描规则（重要）

每次加载 skill 时，在阅读完整内容前，先扫描文件全文搜索以下关键词：
- `WARNING` — 描述了已知的失败模式
- `⚠️` — 警示标记
- `Known failure` — 前次会话的记录
- `Chain Hallucination` — 链式幻觉记录
- `Do NOT` / `Never` — 关键禁止规则

**已知失败案例（2026-06-03）：** 加载 `personal-assistant-multi-user` skill 时，该 skill 第 121-129 行已包含一个 WARNING 块，明确记录了"skill 模板示例被当作用户偏好"的失败案例。但由于 agent 未扫描 WARNING 块，直接阅读了下面的模板示例并将其当作事实，导致了完全相同的错误。**WARNING 存在但未读 = WARNING 不存在。**

**已知失效案例（2026-06-03）：** 用户问「如何让 Hermes 同时服务两个用户」，agent 的第一反应是直接出方案。它没有加载本 skill，因为自认为是「简单配置讨论」不是「复杂任务」。结果：直接给出了 3 层方案没有经过任何模型验证，被用户批评后才补救。

**根本原因：** agent 的直觉判断"这个我不需要找人帮忙"是 Pipeline 最大的敌人。兜底规则（规则5）"任何我第一反应想自己出方案的事情"就是解决这个问题的。如果发现自己在想方案 → 先加载本 skill，不信任自己的第一判断。

---

## 典型示例

### ✅ 正确调用示例
```
用户：帮我设计一个两个用户隔离记忆的方案
我：→ 触发规则7（跨周期决策 + 联合评估）
    → 加载本 skill
    → delegate_task 给 MiMo Pro：「评估多用户记忆隔离方案」
    → delegate_task 给 DS Pro：「从架构角度评估」
    → 综合给用户对比
```

### ❌ 不应跳过的场景
```
用户：如何让Hermes同时服务两个人
我之前跳过判断了，直接自己出方案 → 这是错误的
正确做法：先怀疑复杂度，加载本 skill 再判断
```

---

## 参考文件
- `references/community-issues-summary.md` — Hermes GitHub Issues 关于多 Agent 的讨论
- `references/agent-capability-tests-2026-06-03.md` — 各 Agent 实测能力
- `references/dual-model-consultation-2026-06-03.md` — 双模型联合咨询记录
- `references/premise-verification-2026-06-03.md` — 前提验证失败的案例分析（skill 示例当事实 → Pipeline 放大错误）
- `references/premise-gate-2026-06-03.md` — 前提验证错误导致 Pipeline 放大幻觉的案例
- `references/premise-gate-pattern.md` — 管道错误放大防御：delegate 前验证前提的步骤清单
- `references/failure-recovery-pipeline-execution.md` — Pipeline 跳过后补救模式（2026-06-03）
- `references/pipeline-premise-amplification-2026-06-03.md` — Pipeline 前提放大错误模式（2026-06-03）
- `references/pipeline-error-amplification-2026-06-03.md` — Chain Hallucination 完整分析
- `references/ds-pro-token-2026-06-03.md` — DS Pro token 优化方案
- `references/hermes-systemic-limitations-2026-06-03.md` — 5 个结构性问题审计分析
- `references/delegate-toolsets-bug-2026-06-03.md` — `toolsets=[]` 继承父集 Bug 及 PR 状态
- `references/hermes-hook-architecture-2026-06-03.md` — Hermes Plugin hook 层架构发现：`pre_tool_call` 的拦截能力 vs 不存在的 `before_response` hook
- `references/token-efficiency-patterns.md` — 三 knobs 组合法（Pre-read+Summary / Toolset Restriction / readonly）以 90-97% 节省来降低 delegate_task token 消耗