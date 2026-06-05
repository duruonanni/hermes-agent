# SearXNG 自建指南

在 Hermes Agent 中使用 SearXNG 作为 web 搜索后端。SearXNG 是一个开源、隐私友好的元搜索引擎，自建后**无 API 调用次数限制**。

---

## 前置条件

- Docker + Docker Compose 已安装
- 可通过 `docker compose` 命令运行

## 部署步骤

### 1. 创建项目目录

```bash
mkdir -p ~/searxng && cd ~/searxng
```

### 2. 编写 docker-compose.yml

```yaml
services:
  redis:
    image: redis:alpine
    restart: always
    networks:
      - searxng
    volumes:
      - ./redis-data:/data
    command: redis-server --save 60 1 --loglevel warning

  searxng:
    image: searxng/searxng:latest
    restart: always
    ports:
      - "8888:8080"
    networks:
      - searxng
    volumes:
      - ./searxng-data:/etc/searxng:rw
    environment:
      - SEARXNG_BASE_URL=http://localhost:8888
      - SEARXNG_SECRET_KEY=<用 openssl rand -hex 32 生成的密钥>
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    logging:
      driver: "json-file"
      options:
        max-size: "1m"
        max-file: "1"

networks:
  searxng:
    external: false
```

> ⚠️ **注意：** 新版 Docker Compose 会警告 `version` 字段已废弃，删掉即可。

### 3. 准备数据目录并修复权限

```bash
mkdir -p ~/searxng/searxng-data
chmod 777 ~/searxng/searxng-data
```

> **⚠️ 为什么需要 chmod 777？** SearXNG 容器内部以 UID 977（`searxng` 用户）运行，而宿主机目录默认由当前用户（通常 UID 1000）所有。不设置 777，容器将因 `Permission denied` 无法创建 `/etc/searxng/settings.yml` 而崩溃。如果你熟悉 Docker 用户命名空间映射，可以用更精确的方式；否则 `chmod 777` 是最简单的修复。

### 4. 生成密钥并启动

```bash
openssl rand -hex 32     # 生成密钥
# 填入 docker-compose.yml 后：
docker compose up -d
```

> **⚠️ 镜像较大（~56MB+6MB），下载可能需要几分钟。** 如果 `up -d` 因超时而中断（exit 124），先 `docker pull searxng/searxng:latest && docker pull redis:alpine` 分别下载，再 `docker compose up -d`。

### 5. 启用 JSON API（必须，否则 Hermes 无法使用）

SearXNG 默认只允许 HTML 格式输出，而 Hermes 的 `web_search` 工具调用 JSON API。需要修改配置：

```bash
nano ~/searxng/searxng-data/settings.yml
```

找到 `formats:` 部分（约第 85 行），在 `html` 后追加 `json`：

```yaml
  formats:
    - html
    - json           # ← 添加这一行
```

重启生效：

```bash
docker compose restart searxng
```

### 6. 验证

```bash
# 验证容器运行
docker compose ps

# 验证 JSON API 是否正常
curl -s "http://localhost:8888/search?q=test&format=json" | head -5
# 应返回 JSON 格式的搜索结果，而非 403 Forbidden
```

### 7. 集成到 Hermes Agent

#### 步骤 A：设置环境变量

在 `~/.hermes/.env` 中添加：

```bash
SEARXNG_URL=http://localhost:8888
```

**注意：** URL 不要加 `/search` 后缀，直接是根路径。

#### 步骤 B：激活 SearXNG 后端（关键，容易漏）

仅设 `.env` 不够——Hermes 的 `web_search` 工具需要通过 `web.backend` 配置才知道用哪个后端。两种方式：

**方式 1（推荐，显式配置）：**
```bash
hermes config set web.backend searxng
```

**方式 2（自动检测，不保证所有上下文都能生效）：**
不设 `web.backend` 时，`_get_backend()` 会扫描环境变量自动兜底（`SEARXNG_URL` 存在 → 返回 `"searxng"`）。但在 **cron job 子进程、delegate_task 子 agent** 等上下文中，plugin discovery 可能无法正常加载 searxng provider 到 registry，导致工具返回 `"No web search provider configured"`。遇到这种情况，用方式 1 显式配置 + 重启 gateway 即可。

#### 验证

重启 gateway 使配置生效：

```bash
systemctl --user restart hermes-gateway
```

然后测试 web_search 是否可用。

**注意：** SearXNG **只支持 `web_search`，不支持 `web_extract`**。如果你需要提取页面内容，需要额外配一个 extract 后端（如 Firecrawl、Tavily）。`web.backend: searxng` 仅对搜索生效，extract 会 fallback 到其他已配置的后端。

## 配置优化

编辑 `~/searxng/searxng-data/settings.yml` 可以调整搜索引擎。具体优化方向请根据你的网络环境决定：

- **中国服务器** → 参见下文「(中国网络)搜索引擎超时问题」章节，禁用海外超时引擎
- **海外/有代理服务器** → 可根据需要启用 Google、Wikipedia 等引擎

改完后重启：`docker compose restart searxng`

## 公网访问（可选）

强烈建议使用 Caddy 自动 HTTPS 反代：

```Caddyfile
your-domain.com {
    reverse_proxy localhost:8888
}
```

## （中国网络）搜索引擎超时问题

在部署于中国的服务器上，Google、DuckDuckGo、Brave、Startpage、Wikipedia 等海外搜索引擎会**全部超时或 HTTP 连接错误**。

> ⚠️ **重要：** 默认的 `settings.yml` 中这些海外引擎**没有 `disabled: true` 标记**，因此 SearXNG 默认会同时查询它们。每次搜索需要等所有引擎超时（通常 15-30 秒）后才返回结果，导致搜索极慢。

### 故障现象

```
web_search 返回空或超时，但 SearXNG 首页能打开
→ 用 curl 测试 JSON API 耗时 20+ 秒
→ 返回结果中的 "unresponsive_engines" 列表包含：
  [[\"brave\", \"HTTP connection error\"], 
   [\"duckduckgo\", \"timeout\"],
   [\"google\", \"timeout\"],
   [\"startpage\", \"timeout\"],
   [\"wikipedia\", \"timeout\"]]
→ 但实际上 Bing 和 360search 的搜索结果正常返回
```

### 修复方案：禁用超时的引擎

SearXNG 默认会查询所有未标记 `disabled` 的引擎。在中国网络环境下，需要**显式禁用**以下引擎（及其子引擎）：

```
✕ brave          ✕ brave.images   ✕ brave.videos   ✕ brave.news
✕ duckduckgo     ✕ duckduckgo images
✕ google         ✕ google images  ✕ google news
✕ startpage      ✕ startpage news  ✕ startpage images
✕ wikipedia
```

对每个引擎，在 `settings.yml` 中其名称后的醒目位置添加 `disabled: true`：

```yaml
  - name: brave
    engine: brave
    shortcut: br
    ...
    disabled: true    # ← 添加这行
```

也可以在 `settings.yml` 中找到这些引擎，通过搜索 `name: brave`、`name: duckduckgo`、`name: google`、`name: startpage`、`name: wikipedia` 快速定位。

### 国内可用引擎（保留）

禁用上述引擎后，以下引擎在中国工作正常：

| 引擎 | 引擎名 (name) | 速度 | 备注 |
|------|--------------|------|------|
| ✅ Bing | bing | ~0.3s | 主力搜索引擎 |
| ✅ Bing 图片 | bing images | 快 | |
| ✅ Bing 新闻 | bing news | 快 | |
| ✅ Bing 视频 | bing videos | 快 | |
| ✅ 360 搜索 | 360search | 快 | 中文搜索 |
| ✅ Arch Wiki | arch linux wiki | 快 | IT 技术 |
| ✅ Bilibili | bilibili | 快 | 视频搜索 |
| ✅ 知乎 | zhihu | 快 | 问答 |
| ✅ StackOverflow | stackoverflow | 快 | 编程 |
| ✅ Arxiv | arxiv | 快 | 论文 |
| ✅ Wikipedia | wikipedia | 有时可用 | 可保留但可能超时 |

Bing 是默认的主力引擎，无需额外配置。

### 验证修复

改完重启后测试：

```bash
docker compose restart searxng
# 不指定引擎，看整体速度
time curl -s --max-time 10 "http://localhost:8888/search?q=test&format=json" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
results = data.get('results', [])
unresp = data.get('unresponsive_engines', [])
print(f'结果数: {len(results)}')
for e, reason in unresp:
    print(f'⚠️  超时: {e} ({reason})')
if not unresp:
    print('✅ 没有超时的引擎')
"
```

如果返回结果且 `unresponsive_engines` 为空，说明修复成功。

### 备选：指定引擎搜索（临时绕过）

无需修改配置时，可以通过 `&engines=` 参数指定引擎子集避免等待：

```bash
curl "http://localhost:8888/search?q=headscale&format=json&engines=bing,360search"
```

Hermes 的 `web_search` 工具默认不传此参数，首次搜索会用所有可用引擎。

### 当文件权限禁止直接编辑时

如果宿主机无法直接修改容器内的 `settings.yml`（例如文件由 UID 977 所有且目录权限严格），用 `docker cp` 操作：

```bash
# 先在宿主机修改文件，然后复制进容器
sg docker -c "docker cp /tmp/settings.yml searxng-searxng-1:/etc/searxng/settings.yml"
sg docker -c "cd ~/searxng && docker compose restart searxng"
```

> 如果你按照标准流程设置了 `chmod 777 ~/searxng/searxng-data`，则直接在宿主机编辑文件即可，无需 `docker cp`。

## 通过代理访问外网（Clash/SSR/VPN）

当你在中国服务器上配置了 Clash/SSR 代理后，可以**重新启用**被禁用的海外引擎（Google、DuckDuckGo、Brave 等），让 SearXNG 通过代理访问它们。

### 代理配置方法

在 `settings.yml` 的 `outgoing:` 部分添加代理配置：

```yaml
outgoing:
  # 默认超时，单个引擎
  request_timeout: 3.0
  # ...
  proxies:
    all://:
      - http://127.0.0.1:7890      # Clash 默认 HTTP 代理
      # - socks5://127.0.0.1:7891   # SOCKS5 代理（备选）

  # 如果代理本身较慢，可适当增加超时时间
  # extra_proxy_timeout: 5
```

> **端口说明：** Clash/Mihomo 默认 HTTP 代理端口为 `7890`，SOCKS5 为 `7891`。具体端口取决于你的代理配置，如果是 SSR 或其他工具，请按实际情况修改。

### 配置步骤

```yaml
# 第 1 步：确保代理已在宿主机运行
curl -x http://127.0.0.1:7890 --max-time 5 https://www.google.com
# 应能正常返回

# 第 2 步：在 settings.yml 中添加 proxies 配置（如上）

# 第 3 步：重新启用之前被禁用的引擎
# 找到各引擎配置，删除或注释掉 disabled: true 行

# 第 4 步：重启 SearXNG
docker compose restart searxng
```

### 验证代理生效

```bash
# 测试 Google 搜索是否可用
curl -s --max-time 10 "http://localhost:8888/search?q=test&format=json&engines=google" | python3 -c "
import sys, json
data = json.loads(sys.stdin.read())
results = data.get('results', [])
print(f'Google 结果数: {len(results)}')
if results:
    print('✅ 代理生效，Google 搜索正常')
else:
    print('❌ Google 仍不可用')
"
```

### 配代理后的全引擎体验

代理配置成功后，以下海外引擎都会恢复正常：

```
✅ Google         → 全球最好的网页索引
✅ DuckDuckGo     → 隐私搜索
✅ Brave Search   → 独立搜索引擎
✅ Startpage      → Google 结果的隐私代理
✅ Wikipedia      → 百科
```

配合国内已有的 Bing、360search、Bilibili 等，搜索覆盖面和结果质量会大幅提升。

### 容器网络注意事项

- **host 网络模式：** 如果使用 `network_mode: host`，容器直接使用宿主机网络栈，`127.0.0.1:7890` 可直接访问代理。
- **bridge/默认网络：** 在默认 bridge 网络中，容器通过 `host.docker.internal:7890` 或宿主机内网 IP 访问宿主机的代理。更简单的方法是用 `network_mode: host`。
- **Docker for Mac/Linux 差异：** Linux 上 `host.docker.internal` 默认不可用，必须手动在 `docker-compose.yml` 的 `extra_hosts` 中添加：`extra_hosts: ["host.docker.internal:host-gateway"]`

## 不可搜索的平台

以下中国热门平台**无法**通过 SearXNG 直接搜索。

### 根本原因：SearXNG 没有浏览器渲染能力

这是通过阅读 SearXNG 源码（`searx/search/processors/__init__.py`）验证的事实：

**SearXNG 只有 5 种引擎处理器类型：**
- `online` — 标准 HTTP 请求（类似 curl/httpx）
- `offline` — 离线引擎
- `online_dictionary` — 字典引擎
- `online_currency` — 货币汇率
- `online_url_search` — URL 搜索

**没有 Playwright、没有 Selenium、没有 headless browser。** SearXNG 的所有搜索引擎都只做纯 HTTP 请求，无法渲染 JavaScript。

因此，以下平台**技术上无法被 SearXNG 直接搜索**：

| 平台 | 原因 | 替代方案 |
|------|------|---------|
| ❌ 小红书 | 重度 JS 渲染 SPA，搜索 API 需要登录 Cookie 和签名认证 | 见下文「小红书搜索详细方案」 |
| ❌ 微信公众号 | 搜狗微信搜索 API 限制 | 通过 Bing/Google 搜 `site:mp.weixin.qq.com` |
| ❌ 抖音 | 无公开搜索 API，前端加密 | 通过 Bing/Google 搜 `site:douyin.com` |
| ❌ 微博(热搜/内容) | 公开 API 返回内容有限 | 通过 Bing/Google 搜 `site:weibo.com` |
| ❌ 知乎搜索 | 知乎引擎可能被限速 | 通过 Bing/Google 搜 `site:zhihu.com` |

通用替代方案：通过 **Bing/Google 的 `site:` 搜索**间接获取这些平台的内容。

### 小红书搜索详细方案

#### 方案 A：`site:xiaohongshu.com` 过搜索引擎（推荐，零配置）

通过通用搜索引擎收录小红书内容的索引来搜索：

- **Bing**: 现在就能用，无需任何配置。直接用 `site:xiaohongshu.com <关键词>` 搜索
- **Google**: 配好 Clash 代理后可用，索引质量可能更好
- **Bing 已在 SearXNG 中作为国内可用引擎启用**，直接配到 settings.yml 的引擎列表中也可用

**优点：** 零配置零维护，无需 Cookie，没有过期问题
**缺点：** 时效性有滞后（搜索引擎索引更新可能延迟数小时到数天）

#### 方案 B：独立 Playwright 脚本 + NUC 本地 Cookie 持久化

在 NUC 上写一个 Python 脚本，用 Playwright 自动化搜索小红书：

1. **首次登录**：用户在 NUC 上跑脚本，扫二维码登录小红书
2. **Cookie 持久化**：Cookie 存入 `~/.hermes/scripts/xhs_cookies.json`（保存在用户 NUC 上）
3. **常规搜索**：每次搜索先读取 Cookie 文件，请求小红书搜索 API
4. **Cookie 过期**：脚本检测到过期后报错，用户回家重新扫码即可

Cookie 存储在用户的 NUC（家里的服务器）上，不是传递给 Hermes Agent，安全性没有问题。

**何时需要方案 B：** 当 Bing/Google 的索引不够新鲜，需要实时搜索小红书内容时。

#### 方案 C：配好 Clash 后 Google 收录质量更好

等 Clash 配置好后，Google 对 `site:xiaohongshu.com` 的索引通常比 Bing 更全面和及时。配合 SearXNG 的 `outgoing.proxies` 配置，让 Google 引擎走代理出墙，结果质量会更好。

### 优先级建议

1. 先用方案 A（`site:xiaohongshu.com` 过 Bing），今天就能用
2. 配好 Clash 后，方案 A 自动升级（Google 加入）
3. 如果发现索引不够新鲜，再上方案 B（Playwright 脚本 + Cookie 持久化）

## ⚠️ Docker 权限常见问题

如果你遇到 `permission denied while trying to connect to the Docker daemon socket`：

```bash
# 1. 将当前用户加入 docker 组
sudo usermod -aG docker $USER

# 2. 在当前 shell 中使用 sg 临时切换到 docker 组（无需退出登录）
sg docker -c "docker compose up -d"

# 3. 如果要长期生效，请退出终端重新登录，或执行 newgrp docker
```

## 常用管理命令

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f searxng

# 停止全部
docker compose down

# 启动全部
docker compose up -d

# 仅重启 SearXNG（不改 Redis）
docker compose restart searxng
```
