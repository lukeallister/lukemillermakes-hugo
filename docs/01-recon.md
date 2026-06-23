# Phase 1: Reconnaissance

**Date**: 2026-06-23 (Tuesday)
**Task**: WordPress-to-Hugo migration of `lukemillermakes.com`
**Source**: `/opt/data/dev/lukemillermakes.WordPress.2026-06-23.xml` (2.71 MB)

## 1.1 Tool inventory

The Linux sandbox (Debian GNU/Linux 13 "trixie") was checked for the tools needed across all phases.

| Tool | Available? | Version | Notes |
|---|---|---|---|
| `node` | ✅ | v22.22.3 | `/usr/local/bin/node` |
| `npm` | ✅ | 10.9.8 | `/usr/local/bin/npm` |
| `npx` | ✅ | 10.9.8 | `/usr/local/bin/npx` — primary migration tool will use this |
| `git` | ✅ | 2.47.3 | `/usr/bin/git` |
| `docker` | ✅ | present | `/usr/bin/docker` — used only for the prep Dockerfile, no pulls |
| `python3` | ✅ | 3.13.5 | `/usr/bin/python3` |
| `uv` | ✅ | 0.11.6 | `/usr/local/bin/uv` |
| `hugo` | ❌ → ✅ (installed) | n/a → v0.124.1+extended | **installed**: see §1.2 |
| `podman` | ❌ | n/a | not needed for this task (deployment is out of scope) |
| `go` | ❌ | n/a | not needed; fallback tool `wp2hugo` was not required |

### 1.2 Hugo install

`hugo` was not present. The sandbox is a Debian system but `/usr/local/bin` is not writable as the `hermes` user, so a user-local install was performed:

```bash
# download official extended tarball
curl -fsSL -o /tmp/hugo.tar.gz \
  https://github.com/gohugoio/hugo/releases/download/v0.124.1/hugo_extended_0.124.1_Linux-64bit.tar.gz

# extract
tar -xzf /tmp/hugo.tar.gz  # produces /tmp/hugo (binary)

# install to a writable location
mkdir -p /opt/data/bin
cp /tmp/hugo /opt/data/bin/hugo
chmod +x /opt/data/bin/hugo

# verify
PATH="/opt/data/bin:$PATH" hugo version
# hugo v0.124.1-db083b05f16c945fec04f745f0ca8640560cf1ec+extended linux/amd64
# BuildDate=2024-03-20T11:40:10Z VendorInfo=gohugoio
```

The extended build (with SASS) was chosen so any theme using Sass compiles without issue.

**Path note**: All subsequent commands in this migration that need `hugo` either invoke `/opt/data/bin/hugo` directly or use a shell with `PATH="/opt/data/bin:$PATH"` prepended.

## 1.3 WXR XML inspection

The XML was parsed with Python's `xml.etree.ElementTree` to handle namespaces and CDATA correctly (the file uses `<![CDATA[…]]>` blocks per WordPress convention).

### File metadata

- **Generator**: `WordPress/6.6.1`
- **WXR version**: `1.2`
- **Channel title**: `Luke Miller Makes`
- **Base site URL**: `https://lukemillermakes.com`
- **Base blog URL**: `https://lukemillermakes.com`

### `<item>` breakdown (444 total)

| `wp:post_type` | Count | Notes |
|---|---|---|
| `attachment` | 367 | 351 images + 16 other (pdfs, etc.) |
| `post` | 64 | Blog posts, dates 2017-06-24 → 2024-08-27 |
| `page` | 7 | about, portfolio, knives, woodworking, newsletter, passwords, refund_returns |
| `nav_menu_item` | 3 | Navigation links (not displayed content) |
| `custom_css` | 1 | Customizer CSS (not used directly in Hugo) |
| `wp_navigation` | 1 | Block-based nav (Hugo handles nav separately) |
| `wp_global_styles` | 1 | Theme globals (not used directly in Hugo) |

### Status breakdown

| `wp:status` | Count |
|---|---|
| `inherit` | 367 (attachments) |
| `publish` | 73 (posts + pages + a few extras) |
| `draft` | 4 (skipped from migration by default) |

### Authors

Single author: `lukeallister` <luke@lmak.es>

### Categories (21 total)

```
3d printing, business, carving, comic, Culture, Data Science, fountain pen,
how-to, knife, linux, Literature, making, metalworking, server, story, tech,
Uncategorized, woodworking, writing, devops, flash fiction
```

### Tags (98 total)

First 30:

```
3d printing, amp, analysis, announcement, arduino, audio, bandsaw, bass,
bench, blacksmith, blogging, carving, cedar, chair, cherry, coffe,
coffeescoop, comic, conda, cryptography, culture, customization, cyborg,
data, data science, design, devops, diy, dovetails, drawing, ... (68 more)
```

### Pages (7)

| Slug | Title |
|---|---|
| `about` | About |
| `portfolio` | Portfolio |
| `knives` | Knives |
| `woodworking` | Woodworking |
| `newsletter` | Newsletter |
| `passwords` | Passwords |
| `refund_returns` | Refund and Returns Policy |

### Posts (64)

A range of blog posts spanning 2017–2024 across topics like:

- **Making**: karambit, carving knives, mechanical keyboards, dovetail bench, ash coffee table, cedar chair, walnut coffee scoop, kayak paddle, etc.
- **Tech**: NixOS anyware install, split Planck keyboard, Tailscale VPN, font replacement, NumLock on Raspberry Pi, mamba conda, password generator
- **Writing/poetry**: A Blessing, Greetings from Kepler-1229b, Double or Nothing, Habit and reconsideration

### Attachments (367)

- **351 images** (`.jpg`, `.png`, `.gif`, `.webp`, `.svg`)
- **16 other files** (likely PDFs and the like)

The attachment URLs all live under `/wp-content/uploads/YYYY/MM/...` on the live site, so the migration tool should be able to download them as-is.

## 1.4 Migration plan adjustments

- The 4 **draft** posts will be skipped by the migration tool by default (most CLI tools only convert `publish` status). This is fine — they can be migrated manually if needed.
- The `custom_css` / `wp_navigation` / `wp_global_styles` items are theme artifacts and have no equivalent in Hugo — they'll be dropped.
- The 367 attachments will all be downloaded if the tool supports `--save-images=all`; this will be the longest phase in real time.

The recon confirms the migration tool (`lonekorean/wordpress-export-to-markdown`) will have plenty of content to work with and a clean structure to import into a minimal Hugo theme.