# memory_tool.py 三项代码改动 (2026-06-03)

> Codex GPT 5.5 subagent applied these changes. All 68 existing tests pass.
> git diff: +187/-15 lines across memory_tool.py (723→895 lines)

## 改动 A: ## 标题自动分段 (PR #33781 本地实现)

**新增方法**: `MemoryStore._split_by_sections(raw)` — 双格式自动检测

- 若文件包含 `§` 分隔符：走旧解析器（向后兼容）
- 否则按 `## 标题` 行分割条目
- 标题前的 preamble 也作为条目保留

**修改方法**: `_read_file()` — 委托给 `_split_by_sections()`

**修改方法**: `_detect_external_drift()` — 双格式 roundtrip 检验

**写入格式**: 保持 § 格式不变（向后兼容），读取时支持双格式

## 改动 B: add() 自动转 replace

**新增方法**: `_extract_heading(content)` — 提取第一条 `## 标题`

**修改方法**: `add()` — 在 duplicate check 后、append 前插入逻辑：

1. 提取新内容的 `## 标题`
2. 在现有 entries 中搜索包含该标题的条目
3. 若找到 → in-place replace（替换整条，返回 "Entry replaced (topic match: ...)"）
4. 若替换后超限 → fall through 到 append 逻辑（返回更精确的错误信息）

## 改动 C: 写入频率约束

**新增类**: `LastWriteTracker` — 类级 Dict[str, float] 追踪每个 ## 标题的最后写入时间

- 默认冷却: 5.0 秒
- 冷却期内同 heading 写入被静默跳过
- 配置方式: `MemoryStore(..., write_cooldown_secs=5.0)`
- config.yaml 建议加 `memory.write_cooldown_secs: 5.0`

**修改**: `MemoryStore.__init__()` — 新增 `write_cooldown_secs` 参数

**修改**: `add()` + `replace()` — 写入前检查 throttle

## 风险说明

- 改动 A 的 `## 标题解析` 如果条目内容中也包含 `## `（如代码文档）会误分割
- 改动 B 的自动 replace 是静默的 — 模型不知道旧条目被替换
- 改动 C 的冷却期在测试/调试场景下可能误拦
- **所有改动需要对 memory_tool.py 有 write 权限的上下文。`hermes config set memory.write_cooldown_secs 0` 可关闭冷却。**

## 测试验证

```bash
cd ~/.hermes && python3 -m pytest tests/tools/test_memory_tool.py -x -q
# 68 passed in 0.52s
```
