---
name: hermes-web-setup
description: >
  "Configure web search and browser automation tools in Hermes Agent — includes the critical insight that 'toolset enabled' ≠ 'tool available'."
version: 1.1.0
compatibility: Hermes Agent
metadata:
  hermes:
    tags: [hermes, setup, search, web, backend]
    related_skills: [hermes-agent, headless-chrome-screenshot]
    trigger: manual
---

# Hermes Web & Browser Setup

Hermes has `web` and `browser` toolsets. Enabling them via `hermes tools enable web` is necessary but NOT sufficient — the actual tools (web_search, web_extract, browser_navigate, browser_click, etc.) only register when their required environment variables are present.

**Core insight:** A tool that shows as "enabled" in `hermes tools list` may produce zero visible tools in the agent's tool list because its `check_fn` (in the tool's Python file) returns False.

## Diagnosing the Gap

```bash
# Step 1 — verify the toolset is enabled
hermes tools list

# Step 2 — check which env vars unlock which tool
hermes config check

# Look for lines like:
#   ○ TAVILY_API_KEY → web_search, web_extract
#   ○ BROWSERBASE_API_KEY → browser_navigate, browser_click
#   ○ BRAVE_SEARCH_API_KEY → web_search
#   ○ FIRECRAWL_API_KEY → web_search, web_extract
#   ○ SEARXNG_URL → web_search
```

If the toolset shows `✓ enabled` but the agent never calls web_search/browser_navigate, the most likely cause is a missing env var. The toolset toggle is a platform-level permission; the env var is a runtime capability check.

## Quick Config

Set the env var in `~/.hermes/.env`, then start a **new** session (`/reset` or exit+relaunch). Tool changes never apply mid-conversation.

### Web Search (pick one)

| Service | Env Var | Cost | Notes |
|---------|---------|------|-------|
| SearXNG | `SEARXNG_URL` | Free, self-hosted | No API key needed. 自建指南见 `references/searxng-setup.md` |
| Tavily | `TAVILY_API_KEY` | Free tier | Quickest to start |
| Brave Search | `BRAVE_SEARCH_API_KEY` | Free tier | 2k queries/mo free |
| Firecrawl | `FIRECRAWL_API_KEY` | Free tier | Also does scraping |
| Exa | `EXA_API_KEY` | Paid | |

> **💡 SearXNG 自建：** 免费的元搜索引擎，无需 API Key，没有调用次数限制。通过 Docker Compose 一键部署，完整步骤详见 `references/searxng-setup.md`。

### Browser Automation (pick one)

| Service | Env Vars | Cost |
|---------|----------|------|
| Browserbase | `BROWSERBASE_API_KEY` + `BROWSERBASE_PROJECT_ID` | Free tier |
| Camofox | `CAMOFOX_URL` | Paid |
| Browser Use | `BROWSER_USE_API_KEY` | Paid |

Example `.env` addition:
```
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx
```

## Tool Manifest

After adding the env var and restarting, the following tools appear:

**web_search** — search the web by query string  
**web_extract** — scrape/read a specific URL  
**browser_navigate** — open a page in a headless browser (JS rendering)  
**browser_click** — click elements on a browser page  
**browser_snapshot** — take a screenshot or get page text

## Pitfalls

- **`hermes tools enable web` alone does NOT make web tools appear.** You must also set at least one search API key or SearXNG URL.
- **Changes require `/reset` (CLI) or `/restart` (gateway).** Mid-session toggling of either toolsets or env vars is invisible to the running agent.
- **No env var = no tool, no error.** There is no warning message when a tool's `check_fn` returns False — the tool simply doesn't appear in the tool list. If you expected web tools and don't see them, `hermes config check` is your debug path.
- **`delegate_task` subagents inherit the parent's env.** So if the parent has TAVILY_API_KEY set, subagents with the `web` toolset will also have web_search. If the parent does NOT have it set, subagents won't have it either, even with `toolsets=["web"]`.
- **There's also a `search` toolset** (a subset of `web` that only provides search, not scrape). Enable it: `hermes tools enable search`.
- **Baidu/Google/Bing/DuckDuckGo block plain curl requests** from headless environments (cookie walls, JS challenges, captchas). Web search tools use dedicated APIs (Tavily, Brave, Firecrawl, SearXNG) to bypass this — do NOT try to scrape search engines with `curl`; it will not work from Hermes.

### 搜索范围：全球而非仅中文互联网

当用户要求检索社区方案、查找技术文档或评估工具时，**不要局限于中文互联网**。默认搜索策略：
1. **英文优先** — Google/Bing 全局搜索优先于百度/360 等中文引擎
2. **直接搜英文关键词** — 不要先搜中文再翻译。Hermes 社区、arXiv 论文、GitHub Issues 大多数是英文
3. **多源交叉** — 同时搜索 Hermes GitHub Issues（英文）、arXiv（英文）、Google（英文）+ 中文社区（知乎、CSDN）
4. **不预设结果语言** — 不假设"中文用户的问题只能用中文资料解决"。技术方案往往英文资料更全面、更新

**避免的情况：**
- ❌ 只搜百度/360 → 错失大量英文社区讨论
- ❌ 把中文关键词翻译成英文再搜 → 翻译可能改变原意
- ❌ 优先中文搜索结果 → 英文方案通常更详细、更前沿

**正确做法：** 先用英文关键词搜 Google 和 GitHub，再用中文补充搜索特定国内社区的内容。使用 SearXNG 时配 Google 引擎（见 `references/searxng-google-enable.md`）。

### 不可搜索的平台（JS 渲染限制）

SearXNG **没有 Playwright/headless browser 能力**（仅 5 种 HTTP-based 处理器），无法直接搜索小红书、抖音等 JS 重度平台。详见 `references/searxng-setup.md`「不可搜索的平台」章节。

### web_extract 在 SearXNG 下不可用

SearXNG 只支持 web_search，不支持 web_extract（URL 内容提取）。如果 web_extract 返回 `"SearXNG is a search-only backend"`，说明当前配置了 SearXNG 而非 Firecrawl/Tavily/Exa 等提取后端。此时需要用终端 curl 或 headless Chrome 来获取页面内容。详见 `references/china-accessible-cdns.md`「Fallback Strategy」。

### 搜索优先查官方渠道

当被问到"XX 功能/版本/产品是否存在"时，不要依赖本地安装状态或第三方文章判断。优先：
1. **GitHub 官方仓库** — 直接看根目录结构、`apps/`、`README.md`，比任何第三方描述都准确
2. **官方文档站点** — `docs.xxx.com` 等
3. **GitHub API** — releases、pulls、issues 可查实际发布情况
4. 最后才是本地安装包内容和第三方搜索结果

**⚠️ pip install 不包含完整仓库。** `pip install hermes-agent` 只安装 Python 模块，不会包含 `apps/` 目录下的 desktop 应用等。**不要因为本地 pip 安装包里没有就断言功能不存在**——必须先查 GitHub 仓库目录结构。经典案例：`apps/desktop/` 是官方桌面版，但 pip 安装的本地并没有，直接看 GitHub 根目录就能发现。

- **SearXNG Pitfalls**

- **Docker 运行 + env 变量 ≠ 工具可用。** `SEARXNG_URL` 设了且容器跑着，但 `web_search` 仍可能报 `"No web search provider configured"`——因为你漏了 `hermes config set web.backend searxng`。自动检测在 cron job/delegate_task 子进程上下文中可能失败，显式配置是最保险的方式。
- **设置 `web.backend: searxng` 后必须重启 gateway**（`systemctl --user restart hermes-gateway`）才能生效。重启后验证：`web_search` 可用，`web_extract` 不可用（正常，SearXNG 不支持提取）。

- **JSON API 默认关闭。** SearXNG 的 `settings.yml` 中 `formats:` 默认只包含 `html`，必须手动添加 `json` 才能让 Hermes 的 `web_search` 工具正常工作（否则 API 返回 403 Forbidden）。
- **容器 UID 权限问题。** SearXNG 容器内以 UID 977（`searxng` 用户）运行。宿主机挂载目录若不由 UID 977 所有，容器将因 `Permission denied` 崩溃。最简单修复：`chmod 777 searxng-data`。若需修改容器内已有文件，可用 `docker cp` 绕过宿主机文件权限限制。
- **大镜像需要耐心。** `searxng/searxng:latest` ~56MB，`redis:alpine` ~6MB。建议先 `docker pull` 再 `docker compose up -d` 以避免超时。
- **中国服务器上的搜索引擎超时。** Google/DuckDuckGo/Brave/Wikipedia 等海外引擎可能全部超时。请使用 Bing（配 `base_url: https://cn.bing.com`）+ 百度 + 360 搜索等国内引擎替代。详细配置见 `references/searxng-setup.md`。
- **公司内网可能完全阻断搜索。** 即使配置了百度/Bing 等国内引擎，在公司防火墙/NAT 环境下，SearXNG 容器可能无法访问任何外网搜索 API，所有引擎都会返回 ConnectTimeout。此时 Docker 容器的网络不通（host 主机可能能访问外网，但容器内的 DNS/路由不同）。

  **诊断步骤：**
  1. 从容器内测试网络：`docker exec searxng-searxng-1 curl -s --max-time 5 https://cn.bing.com`
  2. 从宿主机测试网络：`curl -s --max-time 5 https://cn.bing.com`
  3. 如果宿主机通但容器不通，说明 Docker 网络层的问题

  **修复方案（按推荐顺序）：**
  - **方案 A：`network_mode: host`**（最简单，推荐）。在 `docker-compose.yml` 的 `searxng` 服务下添加 `network_mode: host`，并删除 `ports` 映射（host 模式下端口直接暴露）。此时容器直接使用宿主机网络栈，DNS 和路由与宿主机一致：
    ```yaml
    services:
      searxng:
        image: searxng/searxng:latest
        restart: always
        network_mode: host  # 使用宿主机网络
        # ports:  # 删除 ports，host 模式直接暴露端口
        #   - "8888:8080"
        volumes:
          - ./searxng-data:/etc/searxng:rw
        environment:
          - SEARXNG_BASE_URL=http://localhost:8888
    ```
    注意：host 模式下容器仍可通过 `localhost:8888` 访问，redis 容器也需要同样改为 `network_mode: host` 或用 `127.0.0.1` 地址。
  - **方案 B：自定义 DNS**（更精确）。在 `docker-compose.yml` 中指定容器的 DNS 服务器（如阿里 DNS `223.5.5.5` 或公司内网 DNS）：
    ```yaml
    services:
      searxng:
        dns:
          - 223.5.5.5
          - 114.114.114.114
    ```
  - **方案 C：通过 SSR/VPN 代理**——见下方「通过代理访问外网」一节。
- **通过 Mihomo (Clash Meta) 代理访问外网。** 若 SearXNG 运行在国内服务器上，海外搜索引擎（Google/DuckDuckGo/Brave/Startpage）会超时。NUC 上已通过 mihomo-cli 安装 Clash Meta 内核并配置了两个机场订阅。代理端口 7890，以 systemd user service 形式运行（开机自启）。完整搭建流程见 `references/mihomo-setup.md`。
  
- **Google 引擎在 SearXNG 中默认禁用。** `settings.yml` 里 `name: google`、`name: google images`、`name: google news` 均有 `disabled: true`。需要手动改为 `false`，然后 `docker compose restart searxng` 才能通过 Google 获取英文搜索结果。国内用户配了代理后尤其需要这个步骤。
- **Mihomo 仅按需使用，非全局代理。** NUC 上 mihomo 服务始终运行，但环境变量中未设置 HTTP_PROXY。默认所有请求直连国内。需要走代理时手动加 `-x http://127.0.0.1:7890`（curl）或在 Hermes 的 provider 配置中设置 proxy。SearXNG 作为特例始终走代理（因海外引擎需要）。
- **SearXNG 容器内连通但 Hermes 的 web_search 仍超时。** 如果 `curl localhost:8888/search?q=test&format=json` 只返回空字符串（不报错），通常是因为所有引擎都超时了。SearXNG 内部会等所有引擎完成（包括超时的），导致 JSON 响应被延迟或截断。指定引擎子集测试：`curl "...&format=json&engines=bing,baidu"`。如果限定了引擎仍然空，则网络确实不通。
- **指定引擎可避免等待超时引擎。** 测试时用 `&engines=bing,baidu` 参数指定引擎子集，避免被全部超时引擎拖垮。Hermes 的 `web_search` 默认不传此参数，首次搜索可能较慢。

## Personal Assistant Configuration

For a personal life assistant use case, the recommended setup order is:

1. **Web search first** — pick one free-tier provider (Tavily is easiest)
2. **Browser automation** — if you need to read JS-heavy pages (comic/manga sites, SPA apps)
3. **Configure platform gateway** — Telegram / Feishu / Discord for mobile access

The `web` toolset alone covers most daily needs (news, weather, questions, content lookup). Browser automation is only needed for sites that render dynamically.
