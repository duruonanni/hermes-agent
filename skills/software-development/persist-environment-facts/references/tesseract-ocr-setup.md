# Tesseract OCR Setup (Headless, No-Sudo Variant)

## Context

The original `sudo apt-get install tesseract-ocr` approach failed because:
1. **sudo requires interactive authentication** — not available in non-interactive terminal
2. **Binary `/usr/bin/tesseract` was removed** between sessions (possibly by apt auto-clean)
3. **pytesseract Python library** requires the binary; without it, calls fail with `FileNotFoundError`

## Working setup: tesserocr (Cython wrapper) + manual tessdata

### Install the Python package

```bash
pip install tesserocr
```

This installs `tesserocr` — a Cython wrapper that links directly to libtesseract's C++ API. It does **not** depend on the `tesseract` binary being present.

### Download language data (traineddata)

The `tesserocr` package does not bundle language files. Download them from the official tessdata repo:

```bash
mkdir -p ~/.hermes/tessdata

# English (~23MB)
curl -sL "https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata" \
  -o ~/.hermes/tessdata/eng.traineddata

# Chinese simplified (~43MB)
curl -sL "https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata" \
  -o ~/.hermes/tessdata/chi_sim.traineddata
```

**Pitfall:** `chi_sim.traineddata` is large (43MB) and GitHub raw downloads can be slow from China. Use a mirror if needed:
```bash
curl -sL "https://mirror.ghproxy.com/https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata" \
  -o ~/.hermes/tessdata/chi_sim.traineddata
```

### Set TESSDATA_PREFIX

The `tesserocr` library reads `TESSDATA_PREFIX` environment variable to find `.traineddata` files:

```bash
export TESSDATA_PREFIX=~/.hermes/tessdata
```

This must be set in every terminal session where `tesserocr` is called.

### Usage

```python
import tesserocr
from PIL import Image

text = tesserocr.image_to_text(
    Image.open("screenshot.png"),
    lang="chi_sim+eng"
)
print(text)
```

From shell (one-liner):

```bash
TESSDATA_PREFIX=~/.hermes/tessdata python3 -c "
import tesserocr
from PIL import Image
print(tesserocr.image_to_text(Image.open('screenshot.png'), lang='chi_sim+eng'))
"
```

### Verification

```bash
TESSDATA_PREFIX=~/.hermes/tessdata python3 -c "
import tesserocr
img = __import__('PIL').Image.new('RGB', (100, 30), color='white')
text = tesserocr.image_to_text(img, lang='eng')
print(f'tesserocr OK, version: {tesserocr.__version__}')
print(f'Test OCR result: \"{text.strip()}\"')
"
```

Expected: `tesserocr OK, version: 2.10.0`

### File locations

| Item | Path |
|------|------|
| Python package | pip-installed (`tesserocr`) |
| Language files | `~/.hermes/tessdata/{eng,chi_sim}.traineddata` |
| Env variable | `TESSDATA_PREFIX=~/.hermes/tessdata` |

### Cost

Free — runs locally, no API calls.

### User routing rule

From user preference (June 2026):
- If user says **"截图读文本"** or **"读取文字"** → use tesserocr via terminal
- All other images (charts, UI, handwriting, general vision) → use MiMo vision_analyze
