# Kanban 评估 → PPT 交付（2026-06-04）

## 场景

用户在飞书会话中要求：对看板两个待办任务进行团队评估，生成 PPT 发回来。

两个待办任务：
1. `t_da97ee3e` — 创建两个 Skill（本地代码版本管理规范 + 远程 Issue/PR 规范）
2. `t_da8ff274` — ~/.hermes/ 配置目录清理与结构重组

## Pipeline 流程

### 1. 委派前准备（Orchestrator 预读）

先自己验证了看板状态：
```bash
hermes kanban list
# → 确认两个任务状态为 ready
```

整理浓缩摘要发给子代理：
- 任务背景（两个 kanban 卡片的描述）
- 环境事实（3层 git 架构、已有 skills 列表、目录结构）
- 限定目标：「输出评估分析 + 处理方案」

### 2. 并行委派

| 角色 | 工具集 | 输入 token | 输出 |
|------|--------|-----------|------|
| 军师（DS Pro） | `["_no_tools"]` | ~56K | 结构化分析 + 推荐集成到现有 Skill |
| 研究员（MiMo） | `["web"]` | ~713K | 社区调研 + 推荐创建独立 Skill |

### 3. 分歧处理

**分歧点：** 任务A的粒度问题（集成 vs 独立）

| 维度 | 研究员（MiMo） | 军师（DS Pro） |
|------|---------------|---------------|
| 结论 | 创建两个独立 Skill | 集成到现有 github-code-review |
| 理由 | 社区偏好原子化，触发条件不同 | 已有 Skill 覆盖了审查流程，避免膨胀 |
| 来源 | 社区调研（SkillsMP、anbeime/skill） | 架构约束 |

**按规则采纳军师**（架构/粒度问题采纳军师意见）。

### 4. 文档输出（Orchestrator 职责）

用 OfficeCLI MCP 工具生成 PPT（通过 `mcp_officecli_officecli` 工具）。

**Step 1: 创建空白 PPT**

```
mcp_officecli_officecli(command="create", file="/home/duruo/deck.pptx", props=["force=true"])
```

**Step 2: 添加 slide + 内容**

有两种方式：

**方式 A — 简单 title+text（v1 风格，纯文本）:**

```
mcp_officecli_officecli(command="add", file="...", parent="/", type="slide", props=["title=标题", "text=内容"])
```

**方式 B — 精确定位的多元素布局（v2 风格，pitch-deck 样式）:**

添加一张空白 slide 后，用 batch 命令在一轮 open/save 中创建多个形状：

```
mcp_officecli_officecli(
  command="batch",
  file="/path/to/deck.pptx",
  commands=[
    {"command":"add","parent":"/slide[N]","type":"shape","props":{"text":"Title","x":"1.5cm","y":"1.2cm","width":"30.87cm","height":"2.5cm","font":"Georgia","size":36,"bold":true,"color":"1E2761","fill":"none"}},
    {"command":"add","parent":"/slide[N]","type":"shape","props":{"geometry":"roundRect","fill":"F5F7FA","x":"1.5cm","y":"6.5cm","width":"14.5cm","height":"10cm"}},
    {"command":"add","parent":"/slide[N]","type":"shape","props":{"text":"Card content","x":"2.2cm","y":"7cm","width":"13cm","height":"9cm","font":"Calibri","size":18,"color":"333333","fill":"none"}}
  ]
)
```

**batch 的 props 格式关键**：`"props":{"key":"val"}` 是对象，不是 CLI 用的 `["key=val"]` 数组。这是 MCP 调用和 CLI 调用的核心区别。

**Step 3: 验证**

```
mcp_officecli_officecli(command="view", file="...", mode="outline")
```

**8 页 PPT 结构示例：**
1. 封面（深海军蓝 + 品牌条）
2. 任务A 评估（灰底卡片）
3. 军师观点（双栏卡片）
4. 研究员观点（双栏卡片）
5. 推荐方案（决策框）
6. 任务B 诊断（问题卡片）
7. 五阶段方案（步骤卡片 + 验证栏）
8. 总结（深蓝底双卡片）

### 5. 样式增强（用户要求后）

用户反馈「一点样式都没有」后，v2 采用 pitch-deck 风格：
- 深色封面（1E2761 背景 + B85042 红色品牌条）
- 白色内容页（圆角卡片 + 双栏布局）
- 每页不同主题色（红/紫/橙/绿/灰）
- 决策框使用深色卡片（白色文字 + 浅色子文字）
- 详见 `creative/officecli-ppt/references/pitch-deck-patterns-2026-06-04.md`

### 6. 交付

通过 `send_message(target="feishu", message="MEDIA:/path/to/file.pptx")` 发送（必须用绝对路径）。

## 注意事项

- **OfficeCLI MCP 配置坑**：`args` 必须是 YAML 列表 `["mcp"]`，不是 JSON 字符串 `'["mcp"]'`
- **PPT 创建方式选择**：简单的 title+text 用逐 slide add；需要精确定位的多元素布局用 batch
- **batch props 格式**：必须是对象 `{"key":"val"}`，不是数组 `["key=val"]`
- **分歧展示**：各占一页，不要合并成「有分歧」一句话
- **文件路径**：用绝对路径（如 `/home/duruo/xxx.pptx`）
- **样式参考**：详见 `officecli-ppt` skill
