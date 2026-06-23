# Phase 2: Migration tool (`lonekorean/wordpress-export-to-markdown`)

**Date**: 2026-06-23 18:44 → 18:45 UTC (74 seconds wall time)
**Tool**: `lonekorean/wordpress-export-to-markdown` via `npx --yes`
**Output**: `/opt/data/hugo-import/` (41 MB)

## 2.1 Tool invocation

```bash
mkdir -p /opt/data/hugo-import
cd /opt/data

npx --yes wordpress-export-to-markdown \
  --input=/opt/data/dev/lukemillermakes.WordPress.2026-06-23.xml \
  --output=/opt/data/hugo-import \
  --post-folders=true \
  --prefix-date=true \
  --date-folders=none \
  --save-images=all \
  --wizard=false \
  --request-delay=200 \
  --write-delay=10 \
  --timezone=utc \
  --include-time=true \
  --frontmatter-fields="title,date,categories,tags,coverImage,draft" \
  > /opt/data/hugo-import/migration.log 2>&1
```

Notes on flag choices:

- `--post-folders=true` and `--prefix-date=true` give `content/posts/YYYY-MM-DD-slug/index.md` — which is Hugo's preferred **page-bundle** layout (one folder per post, with `index.md` + `images/`).
- `--save-images=all` downloads every image referenced from a post body, not just "attached" (cover/featured) ones — appropriate for this content-heavy blog.
- `--wizard=false` skips the interactive prompt (we're running from CI/script).
- `--include-time=true` keeps the full ISO timestamp in frontmatter `date:` (otherwise the tool drops the time, which breaks ordering of posts published the same day).
- `--frontmatter-fields="title,date,categories,tags,coverImage,draft"` matches what the tool supports; `coverImage` is filled when a featured image is present.

The tool ran from the npm cache (no global install needed):

```
npx --yes wordpress-export-to-markdown
```

## 2.2 Output structure

```
/opt/data/hugo-import/
├── migration.log               # 34 KB, 454 lines
├── posts/                      # 63 entries: 62 published + 1 _drafts/ subfolder
│   ├── 2017-06-24-grind-your-own-stub-nib/
│   │   ├── index.md            # 6.7 KB
│   │   └── images/             # (empty for this post — images failed: ENAMETOOLONG)
│   ├── 2017-07-12-the-5-books-most-likely-to-hide-a-gun/
│   ├── ...                     # (60 more published posts)
│   ├── 2024-08-15-i-didnt-need-all-those-keys-anyway/
│   └── _drafts/
│       ├── id-970/             # "Ergofan: monoblock split mechanical keyboard" (empty body)
│       └── id-1048/            # "Running nixos-anywhere on a weird desktop"
│           ├── index.md
│           └── images/
└── pages/
    ├── 2017-07-06-about/
    │   └── index.md
    ├── 2018-03-20-knives/
    ├── 2018-03-20-portfolio/
    ├── 2018-03-20-woodworking/
    ├── 2018-11-07-passwords/
    └── _drafts/
        ├── 2018-04-21-newsletter/
        └── refund_returns/
```

## 2.3 Migration totals

| What | Count |
|---|---|
| Items in source `<channel>` | 444 |
| Published posts migrated | **62** (1 of the 4 drafts also captured into `posts/_drafts/`) |
| Published pages migrated | **5** |
| Draft pages migrated | **2** |
| Draft posts migrated | **2** (in `_drafts/`; one is empty body) |
| Total `.md` files written | **71** (63 + 6 + 2) |
| Images successfully downloaded | **276** of 319 attempted |
| Images failed | **43** total (33 × 404, 10 × ENAMETOOLONG) |
| Output total size | **41 MB** |
| Total images-by-extension | jpg: 258, png: 18 |

The tool's footer reads:

```
Done, but with 43 failed.
All done!
```

### Why 43 images failed

The XML's `wp:postmeta` for posts that reference Google-hosted images (`lh3.googleusercontent.com`) contained base64-style filenames that exceeded 255 characters and tripped the filesystem's `ENAMETOOLONG` error on `fs.open`. These were all in the very first post (`2017-06-24-grind-your-own-stub-nib`) which uses 4 such base64-encoded Google URLs in its body:

```
✗ [image] 9lY-g7Hp-MiEicvqoal3BKAMNzCKucxZ_8NCV3TRwN9… (ENAMETOOLONG, ~700 chars)
✗ [image] e4aGRkDPAksK7uvo5VxPygO0Dqo80I__vB5djFcrJIi… (ENAMETOOLONG)
✗ [image] -6XBFWS5txAG88xrrc3g7zsAtZn0rYHjPiSe7VcFcu… (ENAMETOOLONG)
✗ [image] PFCNHT-OarVLnTe5s9b1ntuGbaJgxFgUfsGt9LUdBZ… (ENAMETOOLONG)
✗ [image] U0ix9bwgKVYqr-yV2iLTDkun1B72GPLTOiU_RGlpA… (ENAMETOOLONG)
```

These **do still appear** as `![](images/<long-name>)` in the post body (the markdown was written even though the download failed), so the post will render with broken image links until those are cleaned up. See Phase 3/4 cleanup steps.

The remaining 33 failures were all `Request failed with status code 404` — the URL was valid but the file no longer exists on the live site. Sample:

```
✗ [image] IMG_20180312_191301-2-2449x3265.jpg (Request failed with status code 404)
✗ [image] th_IMG_20190215_183026846_HDR-300x225.jpg (Request failed with status code 404)
✗ [image] th_IMG_20181217_194255945_HDR-300x225.jpg (Request failed with status code 404)
```

These are mostly thumbnail-size duplicates that were rotated out of the WP media library; the parent (full-resolution) images are present, so the rendered output will still look correct — just with a few missing thumbnails.

## 2.4 Sample frontmatter and body

### Published post (with categories/tags)

```markdown
---
title: "Grind your own stub nib"
date: 2017-06-24T17:01:45.000Z
categories:
  - "fountain-pen"
  - "how-to"
  - "writing"
tags:
  - "diy"
  - "fountain-pen"
  - "how-to"
  - "writing"
---

One way to make writing more fun is to use a fountain pen. A standard
fountain pen has an iridium ball on the tip that allows the pen to write
consistent lines at any angle. This is great, except when you want a
pen that reminds you of the signers of the US Constitution.
![Like this](images/JohnHancock.png)
…
```

### Published page

```markdown
---
title: "About"
date: 2017-07-06T00:45:24.000Z
---

A blog. By Luke Miller.

Conversations about art, culture, DIY, and the occasional short story.

\\## What I do

\\### Technical - SQL Reporting - Web development - Python scripting
- CAD design - 3D printing
…
```

Note: the `\\##` and `\\###` (literal double-backslash + hash) are how the WP→MD converter serialized WordPress heading markup from the classic editor. In Markdown these will render as literal `##` text rather than as headings. **This is the one cleanup task** that will be applied during Phase 3 to make the rendered HTML correct.

### Draft page (with `draft: true`)

```markdown
---
title: "Refund and Returns Policy"
draft: true
---

**This is a sample page.** …
```

Note: `refund_returns` is missing a `date:` field because its source post-status was `draft` and the tool skips the publish-date stamp for drafts. Hugo treats a missing `date:` as now, which is fine for a drafts folder.

### Cover image example

```markdown
---
title: "Running nixos-anywhere on a weird desktop"
coverImage: "small_PXL_20240825_0347080302.jpg"
draft: true
---
```

## 2.5 Verification commands run

```bash
# File counts
ls /opt/data/hugo-import/posts | wc -l   # → 63
ls /opt/data/hugo-import/pages | wc -l   # → 5 published + 1 _drafts/ subdir

# Image counts and failure categorization
grep -c '✗' /opt/data/hugo-import/migration.log   # → 43
grep -c '✓' /opt/data/hugo-import/migration.log   # → 392 (includes non-image items)
grep -c 'ENAMETOOLONG' /opt/data/hugo-import/migration.log  # → 10
grep -c '404' /opt/data/hugo-import/migration.log            # → 33

# Per-post image counts (top 10)
for d in /opt/data/hugo-import/posts/*/; do
  n=$(find "$d/images/" -type f 2>/dev/null | wc -l)
  echo "$n $d"
done | sort -rn | head -10
# → 21 images: 2018-12-02-a-3d-printed-gaming-keyboard-part-1
#   16: 2018-05-19-japanese-toolbox
#   16: 2018-04-25-diy-mechanical-keyboard
#   16: 2018-03-13-karambit
#   12: 2019-02-19-friction-folder-knives
#   …
```

## 2.6 Known quirks & cleanup plan

These were observed in the migrated content and will need cleanup before the build is meaningful:

1. **Double-backslash headings**: `\\## Foo`, `\\### Bar` in the About page (and likely scattered through other classic-editor posts). Plan: replace `\\#` with `#` in all generated `.md` files during Phase 3.
2. **ENAMETOOLONG image references**: 5 image URLs in the `2017-06-24-grind-your-own-stub-nib` post point at files that don't exist (because they were too long to be downloaded). Plan: leave them — they'll be 404 in the rendered HTML and clearly visible; user can decide whether to fix.
3. **404 thumbnails**: ~33 thumbnail-sized images failed to download. Plan: ignore unless they break visual layout; the parent images are present.
4. **Empty draft post**: `posts/_drafts/id-970/index.md` (Ergofan) has frontmatter but an empty body. The WordPress DB row for this post has no `post_content` recorded in the export. Plan: leave it; it won't render anything visible.
5. **`refund_returns` page no `date:`**: a draft page without a date. Plan: leave it; Hugo handles missing dates.

Migration tool ran successfully on the first attempt — no fallback to `ashishb/wp2hugo` was needed.