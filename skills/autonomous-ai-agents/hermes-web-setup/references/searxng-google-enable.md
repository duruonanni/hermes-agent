# SearXNG Google 引擎启用

SearXNG 默认配置中 Google 搜索系列引擎是禁用的。

## 启用步骤

1. 编辑 `~/searxng/searxng-data/settings.yml`
2. 找到以下引擎，将 `disabled: true` 改为 `disabled: false`：
   - `name: google`
   - `name: google images`
   - `name: google news`
3. 重启容器：`docker compose restart searxng`

## 验证

```bash
curl "http://localhost:8888/search?q=test&format=json&engines=google" | python3 -m json.tool
```

正常返回应有 `results` 数组不为空。返回空数组说明网络不通（检查代理或 DNS）。

## 前提条件

- SearXNG 已配好 `outgoing.proxies`（指向 mihomo/Clash HTTP 代理）
- mihomo 服务正在运行
- 代理节点能访问 google.com

## Chinese vs English 搜索结果

启用 Google 后，`web_search` 对英文关键词返回的结果质量明显提升。但 SearXNG 的多引擎混合排序可能导致中文结果仍优先展示。要纯英文结果可手动指定 `&engines=google` 参数。
