# Phase 9: Scanned typewritten post → Hugo draft pipeline

**Date**: 2026-06-24 (revised)
**Goal**: Synology NAS → automatic draft post → live on stage (LAN-only, with drafts) → user un-drafts → visible on production (public).

## 9.0 Stack & architecture decisions

| Decision | Choice | Reason |
|---|---|---|
| Tool installation | **Containers only.** No `apt install` / `zypper` / `transactional-update` on MicroOS host. | MicroOS root is read-only; any system-pkg install requires reboot. Skill confirms `transactional-update` is the only mechanism — we avoid it entirely. |
| Hugo image | **`hugomods/hugo:exts`** with two `hugo server` processes (watch + drafts). Replaces the old `klakegg/hugo → nginx:alpine` static-build model for this deployment. | Watch-mode lets drafts appear instantly on stage without rebuilding images. Static nginx-build is overkill for low-traffic personal blog + complicates draft publishing. |
| Serving model | **Two Hugo server processes in ONE container**, two ports, same content. | Same container = one Dockerfile, one quadlet, one volume mount. Two processes = one with `--buildDrafts` (stage), one without (prod). Hugo picks up file changes via `--watch` (default). |
| Cron mechanism | **supercronic** (single static binary) inside the scan sidecar. | MicroOS read-only root rules out `/etc/cron.d`. supercronic reads a config file — declarative, versionable in the image. |
| Transfer | **rsync pull from inside the scan container.** Container cron runs `rsync -avz rsync://NAS/blog-scans/ /inbox/` then invokes `scan_to_post.py`. | No host-side mount gymnastics, no SMB/NFS inside containers (Docker seccomp). |
| Pod user | **hermes** on microos_vm1 (per skill). | Confirmed live; `loginctl show-user hermes | grep Linger` → `Linger=yes`. |
| Firewall | None needed. | `command -v firewall-cmd iptables-legacy iptables-nft nft` → empty on microos_vm1. Per skill pitfall, skip firewall config entirely. |
| Reverse proxy | **Caddy** in front of prod port for HTTPS (per Phase 8 §8.8). | Stage port (LAN-only) is not proxied — direct binding. |

## 9.1 Architecture diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  MicroOS VM 192.168.1.126 — user: hermes (linger=yes)                │
│                                                                      │
│  ┌─────────────────────────────────┐  ┌────────────────────────────┐  │
│  │ blog-hugo:latest                │  │ blog-scan:latest           │  │
│  │ (sibling in pod: blog)          │  │                            │  │
│  │                                 │  │ supercronic                │  │
│  │ process 1: PROD                 │  │   ├─ */30 * * * *          │  │
│  │   hugo server --port 8080       │  │   │  rsync -avz            │  │
│  │   --bind 0.0.0.0                │  │   │    rsync://NAS/        │  │
│  │   (no --buildDrafts)            │  │   │      blog-scans/       │  │
│  │                                 │  │   │    /inbox/             │  │
│  │ process 2: STAGE                │  │   │  && scan_to_post.py    │  │
│  │   hugo server --port 8081       │  │   │     /inbox/            │  │
│  │   --bind 0.0.0.0                │  │   │     /processed/        │  │
│  │   --buildDrafts                 │  │   │     /failed/           │  │
│  │                                 │  │   │     /site/content/     │  │
│  │ reads /site/content ◄────────────┼──┤ writes /site/content/    │  │
│  │                                 │  │   post/YYYY-MM-DD-slug/   │  │
│  │ binds:                          │  │                            │  │
│  │   8080 → prod (public via Caddy) │  │ mounts:                    │  │
│  │   8081 → stage (LAN-only)       │  │   /inbox (bind from host)  │  │
│  └─────────────────────────────────┘  │   /processed (bind)        │  │
│                                       │   /failed (bind)           │  │
│                                       │   /site/content (shared    │  │
│                                       │     pod volume)            │  │
│                                       └────────────────────────────┘  │
│                                                                      │
│  Pod: blog                                                           │
│    containers: blog-hugo, blog-scan                                  │
│    volume: blog-content:/site/content                                │
│                                                                      │
│  Host bind-mounts (in container):                                    │
│    ~/.local/share/blog-scans/{inbox,processed,failed} → respective  │
│                                                                      │
│  Separate reverse proxy (Caddy):                                     │
│    :443 → 127.0.0.1:8080 (prod, HTTPS, public DNS)                   │
└──────────────────────────────────────────────────────────────────────┘
```

## 9.2 Two-tier serving model

The single Hugo container runs **two `hugo server` processes**, distinguished by port and the `--buildDrafts` flag:

| Process | Port | Flag | Audience | URL |
|---|---|---|---|---|
| PROD | 8080 | (none) | Public (via Caddy → HTTPS) | `https://lukemillermakes.com/` |
| STAGE | 8081 | `--buildDrafts` | LAN (local network only) | `http://192.168.1.126:8081/` |

### Why this works

- **Hugo `--buildDrafts` is a render-time flag**, not a per-request toggle — so genuinely separate processes are required to serve "drafts visible" vs "drafts hidden."
- **Both processes watch `/site/content/`**. When the scan sidecar writes a new `content/post/YYYY-MM-DD-slug/index.md` with `draft: true`, the STAGE process picks it up on next rebuild tick and renders it; the PROD process ignores it because its flag is off.
- **When the user un-drafts** (changes `draft: true` → `draft: false` in front matter and saves), both processes pick up the change on next tick; the post appears on prod, stays on stage.
- **`hugo server` rebuild latency** is sub-second for a single page; both processes converge quickly.

### Stage port security (LAN-only)

Per live VM verification, **no firewall exists** on microos_vm1. Without a firewall, port 8081 is bound to `0.0.0.0` and is technically reachable from anything that can route to the VM's IP. Three mitigations, in order of preference:

1. **High non-standard port** (default 8081): security through obscurity. Fine for a private LAN where attackers aren't scanning. **Recommended for v1.**
2. **firewalld added later**: `sudo firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=192.168.1.0/24 port port=8081 protocol=tcp accept' && sudo firewall-cmd --reload`. Would require a `transactional-update` install of `firewalld` and reboot.
3. **Caddy with IP allow-list**: route stage through a second Caddy vhost that checks `remote_ip` against the LAN CIDR. More moving parts.

The doc tracks option 1 as the v1 default; we'll revisit if the LAN exposure becomes a concern.

## 9.3 File transfer: rsync pull inside the scan container

The scan sidecar runs the rsync pull itself — no host-side mount of the Synology share is needed.

```bash
# Inside the blog-scan container, every 30 minutes:
rsync -avz --include='*/' --include='*.pdf' --exclude='*' \
  rsync://SYNOLOGY_HOST/blog-scans/ /inbox/
```

Requirements on the Synology DSM:
1. Control Panel → File Services → rsync → enable
2. Create a shared module named `blog-scans` mapped to `/volume1/blog-scans/` (or wherever)
3. Service account with read-only access to that module

Credentials: store in `~/.config/blog-scan/rsyncd.password` on the host (mode 0600), bind-mounted into the container at `/etc/rsyncd.password`.

## 9.4 Directory layout (host-side + container-side)

**Host (MicroOS, user hermes):**

```
~/.local/share/blog-scans/
├── inbox/                  # New PDFs land here after rsync pull
├── processed/              # Originals moved here after successful draft creation
└── failed/                 # Files that failed processing (manual review)

~/.local/share/containers/
└── blog/
    └── content/            # Mount point for blog-content pod volume
```

**Container (blog-scan):**

```
/inbox/                     # bind from host inbox
/processed/                 # bind from host processed
/failed/                    # bind from host failed
/site/content/              # pod volume (shared with blog-hugo)
/usr/local/bin/
├── supercronic             # static binary
├── scan_to_post.py         # the pipeline script
└── rsync_and_process.sh    # wrapper: rsync + scan_to_post.py
```

**Container (blog-hugo):**

```
/site/content/              # pod volume (read-only mount would be ideal, but Hugo writes .hugo_cache)
/src/                       # (legacy: where the Dockerfile expects content; we override with /site/content)
```

## 9.5 Pipeline script (`scan_to_post.py`)

For each new PDF in `/inbox/` not yet in `.processed.json`:

### Step 1: Parse filename `YYYYMMDD_slug.pdf`
- `date_str` → `YYYY-MM-DD` (RFC 3339 with noon UTC)
- `slug` → URL slug + title (slug → title-case with stopword handling)

### Step 2: Convert PDF pages to JPG (200 DPI)
```python
import subprocess
prefix = "/tmp/page"
subprocess.run(["pdftoppm", "-jpeg", "-r", "200", str(pdf), prefix], check=True)
# Rename to zero-padded: page-01.jpg, page-02.jpg, ...
```

### Step 3: OCR via `ocrmypdf --sidecar`
```python
subprocess.run(["ocrmypdf", "--sidecar", "/tmp/ocr.txt", str(pdf), "/dev/null"], check=True)
ocr_text = Path("/tmp/ocr.txt").read_text()
pages = ocr_text.split("\x0c")  # form-feed split
```

### Step 4: Generate `index.md` with front matter `draft: true`
```yaml
---
title: "..."
date: 2026-06-24T12:00:00.000Z
draft: true
categories: ["typosphere"]
tags: ["scan"]
---
```

Body: image refs `![Page 1](images/page-01.jpg)` followed by `<details>`-wrapped OCR text.

### Step 5: Move original → `/processed/` (or `/failed/`)

### Idempotency: `.processed.json` state file
```json
{
  "20260624_test-post.pdf": {
    "processed_at": "2026-06-24T15:30:00Z",
    "pages": 2,
    "bundle": "content/post/2026-06-24-test-post/"
  }
}
```

### Step 6: Signal Hugo to rebuild (optional optimization)
After writing the bundle, touch `/site/content/.hugo_rebuild_trigger` (a no-op file). Hugo's watcher already picks up changes; this is only for forcing rebuilds if needed. Likely unnecessary — drop unless observed issues.

## 9.6 Tool installation — Dockerfile for `blog-scan`

```dockerfile
# syntax=docker/dockerfile:1
FROM debian:13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    ocrmypdf \
    poppler-utils \
    ghostscript \
    python3 \
    python3-pip \
    rsync \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# supercronic — single static binary
ARG SUPERCRONIC_VERSION=v0.2.33
ARG SUPERCRONIC_SHA1SUM=71b0d58cc53f6bd72cf2f293e09e294b79c666d8
RUN curl -fsSL "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64" \
      -o /usr/local/bin/supercronic \
    && echo "${SUPERCRONIC_SHA1SUM}  /usr/local/bin/supercronic" | sha1sum -c - \
    && chmod +x /usr/local/bin/supercronic

# Python deps (none currently — script uses stdlib only)
# Add requirements.txt install here if/when needed.

COPY scripts/scan_to_post.py /usr/local/bin/scan_to_post.py
COPY scripts/rsync_and_process.sh /usr/local/bin/rsync_and_process.sh
COPY crontab.txt /etc/crontab

RUN chmod +x /usr/local/bin/scan_to_post.py /usr/local/bin/rsync_and_process.sh

CMD ["supercronic", "/etc/crontab"]
```

### `crontab.txt`

```
*/30 * * * * /usr/local/bin/rsync_and_process.sh >> /var/log/scan.log 2>&1
```

### `rsync_and_process.sh`

```bash
#!/bin/bash
set -euo pipefail

# 1. Pull new PDFs from NAS
rsync -avz --include='*/' --include='*.pdf' --exclude='*' \
  --password-file=/etc/rsyncd.password \
  rsync://SYNOLOGY_HOST/blog-scans/ /inbox/

# 2. Process anything new
/usr/local/bin/scan_to_post.py \
  --inbox /inbox \
  --processed /processed \
  --failed /failed \
  --content /site/content \
  --state /var/lib/scan/.processed.json
```

## 9.7 Tool installation — Dockerfile for `blog-hugo`

```dockerfile
# syntax=docker/dockerfile:1
FROM hugomods/hugo:exts

# Two-process entrypoint: prod on 8080 (no drafts), stage on 8081 (drafts)
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8080 8081
CMD ["/usr/local/bin/entrypoint.sh"]
```

### `entrypoint.sh`

```bash
#!/bin/bash
set -euo pipefail

# PROD: published only
hugo server \
  --port 8080 \
  --bind 0.0.0.0 \
  --source /site \
  --watch \
  &

# STAGE: drafts visible
hugo server \
  --port 8081 \
  --bind 0.0.0.0 \
  --source /site \
  --watch \
  --buildDrafts \
  &

wait -n
```

The `--source /site` flag overrides Hugo's default working directory so we can mount the shared pod volume at `/site` (instead of relying on the Dockerfile's baked-in `/src`).

## 9.8 Pod quadlets on microos_vm1

All three quadlets live at `~/.config/containers/systemd/` on hermes.

### `blog.pod`

```ini
[Unit]
Description=Blog pod (Hugo + scan sidecar)

[Pod]
PodName=blog

[Install]
WantedBy=default.target
```

### `blog-content.volume`

```ini
[Unit]
Description=Shared content volume for blog pod

[Volume]
VolumeName=blog-content
```

### `blog-hugo.container`

```ini
[Unit]
Description=Hugo server (prod + stage)

[Container]
Image=localhost/blog-hugo:latest
ContainerName=blog-hugo
Pod=blog.pod
PublishPort=8080:8080
PublishPort=8081:8081
Volume=blog-content:/site

[Service]
Restart=always

[Install]
WantedBy=default.target
```

### `blog-scan.container`

```ini
[Unit]
Description=Scan pipeline sidecar (rsync + OCR + post creation)

[Container]
Image=localhost/blog-scan:latest
ContainerName=blog-scan
Pod=blog.pod
Volume=blog-content:/site/content
Volume=~/.local/share/blog-scans/inbox:/inbox:rw
Volume=~/.local/share/blog-scans/processed:/processed:rw
Volume=~/.local/share/blog-scans/failed:/failed:rw
Volume=~/.config/blog-scan/rsyncd.password:/etc/rsyncd.password:ro

[Service]
Restart=always

[Install]
WantedBy=default.target
```

### Activation

```bash
ssh -i ~/.ssh/id_rsa -o UserKnownHostsFile=~/.ssh/known_hosts hermes@192.168.1.126 '
  cd ~/.config/containers/systemd &&
  systemctl --user daemon-reload &&
  systemctl --user start blog.pod &&
  systemctl --user enable blog-hugo.service blog-scan.service &&
  loginctl show-user hermes | grep Linger
'

# Verify
ssh hermes@192.168.1.126 'podman pod ps && podman ps --pod'
# expect: blog pod with blog-hugo + blog-scan both running

# Verify both hugo processes responding
curl -s -o /dev/null -w "prod 8080: %{http_code}\n" http://192.168.1.126:8080/
curl -s -o /dev/null -w "stage 8081: %{http_code}\n" http://192.168.1.126:8081/
```

## 9.9 Deploy order

1. **Build `blog-hugo` image locally** (or on microos_vm1) from the updated `Dockerfile`.
2. **Build `blog-scan` image** from `Dockerfile.scan` once `scan_to_post.py` is implemented.
3. **Create directories** on microos_vm1:
   - `~/.local/share/blog-scans/{inbox,processed,failed}`
   - `~/.config/blog-scan/` (contains `rsyncd.password` with mode 0600)
4. **Transfer quadlet files** to `~/.config/containers/systemd/`.
5. **`systemctl --user daemon-reload && start blog.pod && enable the two services`**.
6. **Verify both ports respond**, then point Caddy at `127.0.0.1:8080` for prod.

## 9.10 Publish workflow (after a draft lands)

```bash
# Option 1: edit the front matter directly on the VM
ssh hermes@192.168.1.126 \
  'sed -i "s/^draft: true/draft: false/" ~/.local/share/containers/blog/content/post/YYYY-MM-DD-slug/index.md'

# Option 2: edit locally, sync, rebuild (no rebuild needed in watch-mode, just wait 1s)
# 1. edit draft: true → draft: false
# 2. rsync the change to the VM
# 3. both Hugo processes pick it up automatically; prod now shows it
```

In watch-mode no rebuild is needed — Hugo re-renders on the next save tick (sub-second).

## 9.11 Resolved open questions

| # | Question | Resolution |
|---|---|---|
| 1 | Synology share folder | `/volume1/blog-scans/` exposed as rsync module `blog-scans` |
| 2 | SMB vs rsync | **rsync only**, pulled from inside the scan container |
| 3 | Container restart for mounts? | No — bind mounts declared in quadlet, no runtime mount needed |
| 4 | Auto-deploy after scan? | **Yes — as draft** (`draft: true`); user manually un-drafts to publish |
| 5 | PDF page resolution | 200 DPI (good balance) |
| 6 | Image format | JPG |
| 7 | Handwriting support | Tesseract only (30-60% accuracy); user primarily typewritten |
| 8 | Post-scan cleanup | Move original to `/processed/` |
| 9 | Which user on MicroOS | **hermes** (confirmed live) |
| 10 | Firewall | None on host; stage port is bound to high non-standard port; security through obscurity |
| 11 | Two serving tiers | **Yes** — same container, two ports, two Hugo processes |
| 12 | Drafts visible to public | **No** — stage port is LAN-only, prod port has no `--buildDrafts` |

## 9.12 Future work (out of scope for v1)

- Move rsync creds into a Docker secret / quadlet Secret directive
- Add `firewalld` with rich rules to restrict 8081 to LAN CIDR (requires `transactional-update` install + reboot)
- Add `watchdog` config to auto-unstage failed Hugo processes
- Migrate publish workflow to a tiny CLI: `blog publish <slug>` that flips `draft: true → false`
- Add a Telegram/Discord notification on successful draft creation
- Replace rsync pull with rsync daemon mode + NAS-side push (push is faster on small files)

## 9.13 Modular three-tier OCR fallback

The scan pipeline no longer depends on the former `ocrmypdf --sidecar` pass. After
`pdftoppm` renders the PDF at 200 DPI, `scan_to_post.py` passes each JPG to the
provider chain in `scripts/ocr-pipeline/ocr_backends.py`. Each page is processed
independently, so a failure does not shift later transcripts out of alignment
with their source images. The provider used for every page is included in the
pipeline log and result detail.

### Provider order

The default `SCAN_OCR_PROVIDERS=ollama,hermes,tesseract` chain is:

1. **`OllamaDirectOCR`** — calls the local Ollama native `/api/chat` endpoint
   directly with a base64 image. This is the preferred low-latency path and
   does not depend on the Hermes API service.
2. **`HermesVisionOCR`** — calls a Hermes Agent OpenAI-compatible
   `/v1/chat/completions` endpoint with an inline image. It provides a hosted
   vision-model fallback when local inference is unavailable.
3. **`TesseractOCR`** — invokes the `tesseract` binary installed in the
   `blog-scan` image. It is deliberately always available as the deterministic
   last resort, so outages or model crashes in both AI tiers do not stop draft
   creation.

`FallbackOCR` returns the first non-empty transcript and logs provider errors
before trying the next tier. If all providers fail for a page,
`recognize_pages()` preserves its position with an empty string and the
provider marker `failed`.

### Configuration

| Variable | Purpose | Default / requirement |
|---|---|---|
| `SCAN_OCR_PROVIDERS` | Comma-separated provider names and priority | `ollama,hermes,tesseract` |
| `OLLAMA_OCR_URL` | Ollama base URL | `http://192.168.0.8:11434` |
| `OLLAMA_OCR_MODEL` | Local vision/OCR model | `glm-ocr` |
| `OLLAMA_OCR_TIMEOUT` | Ollama request timeout in seconds | `120` |
| `OLLAMA_OCR_PROMPT` | Verbatim-transcription prompt override | Built-in exact-transcription prompt |
| `HERMES_OCR_URL` | OpenAI-compatible base URL ending in `/v1` | Required to enable Hermes |
| `HERMES_OCR_API_KEY` | Hermes bearer token | Required to enable Hermes |
| `HERMES_OCR_MODEL` | Model name advertised by the Hermes API | `hermes-ocr` |
| `HERMES_OCR_TIMEOUT` | Hermes request timeout in seconds | `120` |
| `HERMES_OCR_PROMPT` | Hermes transcription prompt override | Built-in exact-transcription prompt |
| `TESSERACT_LANGUAGE` | Installed Tesseract language pack | `eng` |

Providers can be reordered or disabled without code changes. An Ollama tier
with a blank URL/model or a Hermes tier without its URL/key is skipped with a
warning; Tesseract remains usable by default.

### Model status and fallback rationale

Research selected **`glm-ocr`** as the primary local OCR model because it is
purpose-built for document transcription and fits the available hardware.
However, it currently crashes on this box. Tested `qwen2.5vl` variants also
fail during inference with HTTP 500 `unexpected EOF`. These are handled as
normal provider failures: the chain tries Hermes next and reliably reaches
Tesseract when both model-backed tiers are unavailable. Tesseract therefore
remains installed in the scan image rather than being treated as an optional
external service.

### Manual reprocessing and tests

`scripts/ocr-pipeline/reprocess_draft.py` re-runs the same chain against JPGs
already present in a Hugo draft bundle, without repeating rsync or PDF
rendering:

```bash
python3 scripts/ocr-pipeline/reprocess_draft.py \
  content/post/_drafts/id-1048 \
  --out-json /tmp/id-1048-ocr.json
```

Run it where `tesseract` is installed (normally inside `blog-scan`) if tier 3
must be exercised. It prints the configured chain and the provider, status,
character count, and preview for each page.

`tests/test_ocr_backends.py` contains **14 unit tests** covering fallback
priority, empty/error handling, per-page alignment, Ollama and Hermes request
formats and response validation, Tesseract invocation, and environment-driven
chain construction:

```bash
python3 -m unittest tests/test_ocr_backends.py
```

### Rootless Podman and SELinux note

On the MicroOS host, SELinux labeling prevented the required `podman exec`
workflow against the scan container. The Quadlet workaround is
`SecurityLabelDisable=true` in `blog-scan.container`. The operational rationale
and host-specific notes are documented under `/opt/data/documentation/homelab/`,
including `scan-ocr-model-recommendations.md`.
