# China-Accessible Web Resources

Known reliable CDNs and services accessible from mainland China (no VPN/proxy needed).
Use this when the agent needs to fetch web resources but Google/Wikipedia/etc. are blocked.

## ✅ Works from China

| Resource | URL Pattern | Use Case |
|----------|-------------|----------|
| **jsDelivr CDN** | `https://cdn.jsdelivr.net/npm/{package}@{version}/{file}` | npm packages, simple-icons SVGs, pure Python libs |
| **simple-icons** | `https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{name}.svg` | 2000+ brand logos as SVG (OpenAI, DeepSeek, Anthropic, Microsoft, etc.) |
| **Alibaba Cloud** | `https://tongyi.aliyun.com` | Qwen, Chinese AI services |
| **ByteDance** | `https://www.doubao.com`, `https://www.douyin.com` | Doubao, TikTok/Douyin |
| **Moonshot** | `https://kimi.moonshot.cn`, `https://statics.moonshot.cn` | Kimi AI, statically hosted assets |
| **Baidu** | `https://www.baidu.com`, `https://baike.baidu.com` | Chinese web search, Baidu Baike |
| **Kuaishou** | `https://klingai.com`, `https://www.kuaishou.com` | Kling AI video, Kuaishou |

## ❌ Blocked from China (no proxy)

- **Google** — all services (google.com, googleusercontent.com)
- **Wikimedia** — upload.wikimedia.org, wikipedia.org
- **DuckDuckGo** — icons.duckduckgo.com (favicon service)
- **ChatGPT** — chatgpt.com, openai.com
- **Claude** — claude.ai, anthropic.com (API may work on some ISPs)
- **Midjourney** — midjourney.com
- **xAI** — x.ai (Grok)
- **Runway** — runwayml.com
- **Leonardo AI** — leonardo.ai
- **elevenlabs.io** — blocked on some ISPs
- **notion.so** — blocked

## Fallback Strategy When web_extract Fails

SearXNG cannot extract URL content. When `web_extract` returns `"SearXNG is a search-only backend"`, fall back to:

1. **curl in terminal** — `curl -sL --connect-timeout 10 -A "Mozilla/5.0..." URL` 
2. **headless Chrome** — use `headless-chrome-screenshot` skill for JS-rendered pages
3. **Python requests** — for API endpoints that return JSON

## SVG to PNG Conversion

Pure Python, no sudo needed:

```bash
pip install cairosvg pillow
```

```python
import cairosvg
from PIL import Image

# SVG bytes → PNG file
with open("icon.svg", "rb") as f:
    png_data = cairosvg.svg2png(
        bytestring=f.read(),
        output_width=256,
        output_height=256,
        background_color="white"  # needed for minimal/white SVGs
    )
with open("icon.png", "wb") as f:
    f.write(png_data)

# ICO → PNG (for favicons)
img = Image.open("favicon.ico")
img = img.convert("RGB")  # Remove alpha
img.resize((256, 256), Image.LANCZOS).save("icon.png", "PNG")

# Create ZIP
import zipfile
with zipfile.ZipFile("icons.zip", "w", zipfile.ZIP_DEFLATED) as zf:
    for fname in ["icon1.png", "icon2.png"]:
        zf.write(fname)
```
