# OCR scan-to-blog-post workflow: research and recommendations

**Date**: 2026-06-23
**Site**: `/opt/data/lukemillermakes-hugo/` (Hugo + xmin, multi-stage Docker, MicroOS VM, git-tracked)
**Goal**: Typewritten or handwritten page scan → published Hugo post (page image + OCR text)

## 1. OCR tool evaluation

**Recommendation: start with Tesseract (via `ocrmypdf` or `pytesseract`).** Local, free, accurate on typewritten text, no API keys — matches the rest of the site's "minimal, reproducible" ethos. Other tools only matter if handwriting accuracy becomes a blocker.

| Tool | Local? | Cost | Typed | Handwritten | Notes |
|---|---|---|---|---|---|
| **Tesseract OCR** | yes | free | 95–99% | 30–60% | Standard for printed text. 100+ languages. |
| **OCRmyPDF** | yes | free | 95–99% | inherits Tesseract | Tesseract wrapper with deskew / denoise / binarization. `--sidecar` dumps text next to PDF. Best CLI for scan-in / text-out. |
| **pytesseract** | yes | free | same | same | Python wrapper; convenient for scripted pipelines. |
| **marker-pdf** | yes (GPU) | free | high | medium | ML PDF→MD. Heavy on CPU; ~25 p/s on H100. Overkill here. |
| **Ollama + llava / llama3.2-vision** | yes (GPU) | free | medium | medium | No confidence values → silent hallucinations. Slow on CPU. Useful for handwriting fallback only. |
| **Google Cloud Vision** | cloud | $1.50/1k imgs | 95–99% | 85–95% | Best handwriting model. `DOCUMENT_TEXT_DETECTION` flag. Needs GCP billing. |
| **Azure Document Intelligence** | cloud | ~$1.50/1k pgs | high | high | Same tier as Google. |
| **AWS Textract** | cloud | ~$1.50/1k pgs | high | medium-high | Slightly weaker on handwriting than Google/Azure. |
| **Apple Live Text / iOS scan** | mobile | free | 90–95% | 70–85% | Zero-friction iPhone capture. Good ad-hoc, bad for batch. |
| **NAPS2** / **gscan2pdf** | desktop | free | inherits Tesseract | inherits Tesseract | GUI scanner frontends (NAPS2: Win/Mac/Linux; gscan2pdf: GTK Linux). Scanner + OCR + PDF in one. |

### Current accuracy (2025)

- **Tesseract 5.x LSTM**: 95–99% on printed text, 30–60% on handwriting
- **Google Vision handwriting**: 85–95% on cursive, ~98% on print handwriting
- **Ollama vision models**: no published confidence; users consistently report hallucinated OCR output

## 2. Proposed workflow architectures

### Option A — Manual (simplest)

```
scan → save JPG → ocrmypdf --sidecar → write index.md → git commit → push → deploy
```

OCR runs locally. ~5–10 min/post (mostly editing OCR mistakes). Prereqs: `tesseract-ocr` + `ocrmypdf`. Zero new infra; user sees text before publishing (good for exec-function: no surprises). Cons: manual repetition per post.

### Option B — Semi-automated (script-assisted)

```
scan → ~/Scans/Inbox/ → inotifywait triggers scripts/scan-to-post.sh:
   1. ocrmypdf → sidecar .txt
   2. generate slug from filename / first line
   3. copy image to content/post/$DATE-$slug/images/scan-01.jpg
   4. write index.md with image + OCR text in a <details> block
  → user edits front matter → git commit → push
```

OCR runs locally, watcher-triggered. ~1–2 min/post if script works. Prereqs: `inotify-tools`, `ocrmypdf`, ~50 lines of bash or Python. Removes copy/paste friction; still gives a final edit pass. Cons: script needs maintenance; needs sane scan-filename convention.

### Option C — Fully automated (CI/CD)

```
scan → push image to git under incoming/ → CI (Actions/Drone/Woodpecker):
   1. ocrmypdf on image
   2. generate post bundle, commit to content/post/
   3. rebuild Hugo site image
   4. redeploy (ssh + podman load + quadlet restart)
```

OCR runs in CI runner. ~0 user-time; ~3–5 min wall-clock. Prereqs: hosted repo + CI runner + deploy key + rebuild hook on VM. Closest to "upload a scan, get a post"; ideal end-state. Cons: most moving parts; bad OCR hits prod directly; overkill until cadence justifies.

## 3. Hugo integration specifics

### Post structure (page bundle, matches existing site convention)

```
content/post/2026-06-23-my-typewritten-post/
├── index.md
└── images/
    ├── scan-01.jpg
    ├── scan-02.jpg      # only if multi-page
    └── ...
```

### `index.md` template

```markdown
---
title: "My typewritten post"
date: 2026-06-23T14:00:00.000Z
draft: false
categories: ["writing"]
tags: ["typewriter", "scan"]
---

![Page 1](images/scan-01.jpg)

<details>
<summary>Click to read the text extract</summary>

<OCR text goes here, one paragraph per visual paragraph.>

</details>
```

The `<details>/<summary>` block keeps the OCR text accessible (assistive tech, low-bandwidth, no-JS) but tucked away so the scan dominates the page — matching the "show the original; text is the fallback" intent.

### Optional shortcode for consistent styling

Once you have >5 scan-posts, add `layouts/shortcodes/scan.html`:

```html
<figure class="scan">
  {{ $img := .Page.Resources.GetMatch (printf "images/%s" (.Get "src")) }}
  {{ if $img }}{{ $resized := $img.Resize "1200x" }}
    <img src="{{ $resized.RelPermalink }}" alt="{{ .Get "alt" | default "scanned page" }}" loading="lazy">
  {{ end }}
  {{ with .Get "caption" }}<figcaption>{{ . }}</figcaption>{{ end }}
</figure>
<details class="scan-text">
  <summary>Read the text extract</summary>
  {{ .Inner | markdownify }}
</details>
```

Used as `{{< scan src="scan-01.jpg" alt="First page" >}}The OCR text{{< /scan >}}`. Gives Hugo-Pipes responsive images (1200px max, lazy) without hand-editing `<img>` tags.

## 4. Handwriting vs typewritten

| | Typewritten | Handwritten |
|---|---|---|
| Tesseract accuracy | 95–99% | 30–60% |
| Google Vision accuracy | 98%+ | 85–95% |
| Preprocessing needed | minimal (300+ DPI, grayscale) | heavy (deskew, denoise, contrast) |
| Human review | light (typo spot-check) | required (often full re-type) |

**Typewritten scans**: Tesseract + OCRmyPDF is enough. 30-second read-through before publishing.
**Handwritten scans**: Tesseract first as a free baseline. If output is unreadable, escalate to Google Cloud Vision ($1.50/1k images — essentially free for a personal blog) or manual transcription.
**Always include a human-review step** regardless of tool. Catches `rn`→`m`, `l`→`1`, `O`→`0`, dropped periods at line ends, wrong line breaks from typewriter carriage returns.

## 5. Recommended starting point

**Start with Option A.** Move to B after 3–5 scan-posts, C after ~20 or if you want mobile capture.

### Why A first

- Lowest startup cost — install `tesseract-ocr` and `ocrmypdf`, done
- No scripts to debug; fewer moving parts match your exec-function profile
- Manually creating 3–5 scan-posts teaches the data model (slug conventions, image naming, front-matter fields) before automating
- Failure-resilient: bad OCR is visible at edit time, not in production

### Concrete first-post sequence

```bash
# one-time
sudo zypper install tesseract-ocr ocrmypdf

# per post
ocrmypdf --sidecar scan.txt scan.jpg scan.pdf           # scan.txt = OCR text
mkdir content/post/$(date -I)-first-scan-post/images
mv scan.jpg content/post/$(date -I)-first-scan-post/images/scan-01.jpg
mv scan.txt content/post/$(date -I)-first-scan-post/     # keep as reference
# write index.md from the template in §3 (image + OCR text + front matter)
git add content/post/$(date -I)-first-scan-post/ && git commit -m "post: ..."
podman build -t lukemillermakes:latest . && \
  podman save lukemillermakes:latest | ssh lukemillermakes@192.168.1.126 podman load && \
  ssh lukemillermakes@192.168.1.126 systemctl --user restart lukemillermakes.service
```

### Upgrade triggers

| After | Move to | Why |
|---|---|---|
| ~5 posts | Option B | Copy-OCR-write cycle is visibly repetitive; 50-line script is a net win |
| ~20 posts OR mobile capture wanted | Option C | Scan→laptop→commit→deploy friction justifies a CI pipeline |

B is the sweet spot for most personal blogs. C is only worth it at multiple-posts/week cadence.

## 6. Open questions to resolve before implementing

| Question | Why it matters |
|---|---|
| **Scan resolution / format** | 300 DPI min for OCR (600 for archival). JPG fine for web; PDF-embedded overkill for static. |
| **Single-page vs multi-page** | Multi-page needs per-page OCR + consistent image-naming (`scan-01.jpg`, `scan-02.jpg`, …). |
| **Handwriting vs typewritten ratio** | If 80%+ handwritten, skip to cloud API or plan for manual transcription. The pipeline changes entirely. |
| **Editable OCR text vs image-only** | Image-only (OCR for accessibility/search): 70% Tesseract accuracy is fine. OCR-as-primary-reading: accuracy matters much more. |
| **Where the scan happens** | Phone (lower quality, always-available), flatbed (high quality, dedicated), or both? Phone → NAPS2 mobile / Live Text can clean up raw camera JPGs. |
| **Slug source** | Auto from filename? First line of OCR? Always manual? Wrong default → bad URLs → renaming later. |
| **Draft vs publish workflow** | Script generates `draft: true` and you flip it (safe) vs commits direct to `main` (fast). |
| **RSS rendering of OCR text** | xmin's RSS likely emits plain text. OCR text with markdown formatting needs either clean OCR preprocessing or manual cleanup. |
| **Backup of original scans** | Bundles store compressed JPGs. Want uncompressed TIFF originals in a separate `originals/` branch or storage path? |

## See also

- `/opt/data/documentation/wp-to-hugo/03-hugo-setup.md` — page-bundle convention, `hugo.yaml`, xmin theme
- `/opt/data/documentation/wp-to-hugo/05-deployment-prep.md` — Dockerfile, deploy workflow scan-posts reuse
- `/opt/data/lukemillermakes-hugo/content/post/2018-09-14-small-walnut-coffee-scoop/` — example image-heavy page bundle
- [OCRmyPDF docs](https://ocrmypdf.readthedocs.io/) · [Tesseract LSTM engine](https://github.com/tesseract-ocr/tesseract) — `--oem 1`, `--psm` modes, language packs