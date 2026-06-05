# Feishu Document API 调试记录

## 2026-06-03: 记忆幻觉审计报告写入经历

### 问题

向现有长文档（144+ 个顶级块）追加 60+ 个内容块时，暴露了多个 API 限制。

### 遇到的坑

#### 1. 50 块硬限制
`POST /children` 一次最多 50 个块。超出返回 `99992402 field validation failed`。
→ 分批次，每批 ≤ 40 留余量。

#### 2. 混合块类型
同一次 POST 的 children 数组必须全为同一 `block_type`。text(2) + heading3(3) 混在一起返回 `1770001`。
→ 按类型分批，或全部用 type=2 文本块（见 all-text fallback pattern）。

#### 3. 嵌套太深 (1770005)
逐个插入块时，如果用新插入的块的 ID 作为下一个块的 parent，会导致嵌套深度递增。~30 层后 API 拒绝。
→ 始终在同一层级插入（DOC_ID 根层级），用 `index` 定位。

#### 4. 父块类型限制
- DOC_ID 根层级：批量插入只接受 type=2
- type=3 (heading3) 父节点：接受 type=2 和 type=4，不接受 type=3
- type=12 (bullet) 父节点：只接受 type=2
→ 插入前先检查 parent 的 block_type。

#### 5. Markdown 表格渲染为纯文本
`| Col1 | Col2 |` 作为 type=2 文本块写入后，飞书显示为原始管道符，而不是表格。
→ 用缩进 + 箭头格式替代表格。

#### 6. 空内容块被拒
`{"elements": []}` 或 `{"content": ""}` 返回 `1770001`。
→ 每个块至少有一个非空 text_run，否则用 `{"content": " "}` 占位。

#### 7. 测试块污染正式文档
调试 API 时直接往正式文档里插测试块，用户看到垃圾内容。
→ 永远先建一个测试文档：`POST /open-apis/docx/v1/documents {"title": "TEST"}`。

### 教训

1. **先建测试文档调通 API，再操作正式文档。**
2. **不要在生产文档中做混合块类型的实验。**
3. **所有内容先锚定好格式（不用 pipe 表格）。**
4. **批量删除用 `batch_delete` 指定 index 范围。**
5. **写入后验证 raw_content 确认干净。**
