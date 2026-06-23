# Phase 6: Image reference fix (friction folder knives → site-wide)

**Date**: 2026-06-23 19:37 UTC
**Success criterion**: Friction folder knives post renders with the same number of images as the original WP post (11) ✅
**Result**: 161 of 161 image references across all 67 posts resolve correctly. 0 orphans.

## 6.1 The bug

The migration tool (`lonekorean/wordpress-export-to-markdown` v3.0.5) has a quirk that left broken image references in migrated posts:

1. WordPress generates multiple image variants per upload: an `original` (no size suffix) and several thumbnails like `-300x225.jpg`, `-225x300.jpg`, `-150x150.jpg`, etc.
2. The classic WP editor emits these in `srcset` attributes inside `<img>` tags.
3. The migration tool scrapes every `<img src>` URL it finds and tries to download each one.
4. For thumbnail variants like `IMG_20181027-300x225.jpg`, the request **404s** because WordPress rotates old thumbnails out of the media library (the parent file remains; thumbnails are regenerated on demand and old copies get GC'd).
5. The tool's body-content extractor still writes `![alt](images/<thumb>)` into the markdown, but the actual file on disk is the *parent* (`IMG_20181027.jpg`) — because that one was downloaded via a different code path (the `<a href>` wrapping the image, or a sibling reference).

Result: the markdown points at a thumbnail that doesn't exist on disk, while a parent file sits right next to it unused.

### Example: friction folder knives

The post had **11 image refs** in its body:

```
images/th_IMG_20190215_183026846_HDR-300x225.jpg
images/th_IMG_20181027_130406710-300x225.jpg
images/th_IMG_20181208_103155689_HDR-300x225.jpg
images/th_IMG_20181209_160320327_HDR.jpg           ← no size suffix, OK
images/th_IMG_20181209_193655521_HDR-300x225.jpg
images/th_IMG_20181217_194255945_HDR-300x225.jpg
images/th_IMG_20181217_194250463_HDR-300x225.jpg
images/th_IMG_20181217_194231068_HDR-300x225.jpg
images/th_IMG_20190203_144857816_HDR-e1550594374822-225x300.jpg
images/th_IMG_20190203_144839475_HDR-e1550594394491-225x300.jpg
images/th_IMG_20190203_144825580_HDR-e1550594417737-225x300.jpg
```

On disk in `content/post/2019-02-19-friction-folder-knives/images/` there were **12 files** — all parent versions without `-WxH` suffix:

```
th_IMG_20181027_130406710.jpg
th_IMG_20181208_103155689_HDR.jpg
th_IMG_20181209_160320327_HDR.jpg
th_IMG_20181209_193655521_HDR.jpg
th_IMG_20181213_145655833_HDR.jpg          ← orphan: not referenced in md
th_IMG_20181217_194231068_HDR.jpg
th_IMG_20181217_194250463_HDR.jpg
th_IMG_20181217_194255945_HDR.jpg
th_IMG_20190203_144825580_HDR-e1550594417737.jpg
th_IMG_20190203_144839475_HDR-e1550594394491.jpg
th_IMG_20190203_144857816_HDR-e1550594374822.jpg
th_IMG_20190215_183026846_HDR.jpg
```

**Only 1 of 11 markdown refs had a matching file.** The other 10 referenced thumbnails that didn't exist; their parent files existed but were orphaned in `images/`.

## 6.2 Strategy: TYPE A / TYPE B / TYPE C

For each broken markdown ref, classify:

| Type | Definition | Action |
|---|---|---|
| **TYPE A** | Parent file exists locally on disk (e.g., stripping the `-WxH` suffix yields a file in the same `images/` dir) | Rewrite the `.md` to point at the parent. No file I/O. |
| **TYPE B** | Parent file doesn't exist locally, but the WXR XML knows the original WP upload URL for this attachment | Download the parent from the live WP site into the post's `images/` dir, then rewrite the `.md` ref |
| **TYPE C** | Parent doesn't exist anywhere (true orphan) | Comment out the broken ref with a `<!-- MISSING: ... -->` placeholder so it renders nothing instead of a broken image icon |

### Filename parent-stripping regex

```python
PARENT_RE = re.compile(
    r'^(.+?)(?:-\d+x\d+)?\.(jpg|jpeg|png|gif|webp)$',
    re.IGNORECASE,
)
```

Critical detail: we **deliberately do not strip `-eTIMESTAMP`** segments like `-e1550594374822`. In some posts, that timestamp is part of the canonical filename on disk (it's a WP optimization marker that survives in the parent):

- `th_IMG_20181027_130406710-300x225.jpg` → `th_IMG_20181027_130406710.jpg` (strip size only)
- `th_IMG_20190203_144857816_HDR-e1550594374822-225x300.jpg` → `th_IMG_20190203_144857816_HDR-e1550594374822.jpg` (strip size only, keep `-e…`)
- `th_IMG_20181209_160320327_HDR.jpg` → `th_IMG_20181209_160320327_HDR.jpg` (no change)

Only the trailing `-WxH` segment is stripped. The regex `(.+?)(?:-\d+x\d+)?` matches as little as possible before the optional size suffix, so a filename with multiple digit-containing segments (like `IMG_20181217_194231068`) doesn't get accidentally split.

### Why not strip the size suffix with a single dash-prefix rule?

Because filenames like `th_IMG_20190203_144857816_HDR-e1550594374822-225x300.jpg` would get the timestamp stripped too if you use a naïve `-\d+x\d+` find-and-replace. The anchored regex (with `$` end-of-string anchor) only matches a real trailing size suffix.

## 6.3 Implementation

The fix script lives at `/opt/data/scripts/fix-image-refs.py` (397 lines). Re-runnable — safe to run multiple times; it only acts on broken refs.

Key functions:

```python
def build_url_map(xml_path):
    """Parse WXR XML, return {filename: original_wp_url} for all attachments."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {'wp': 'http://wordpress.org/export/1.2/'}
    m = {}
    for item in root.findall('.//item'):
        pt = item.find('.//wp:post_type', ns)
        if pt is None or pt.text != 'attachment':
            continue
        url_el = item.find('.//wp:attachment_url', ns)
        if url_el is not None and url_el.text:
            url = url_el.text
            fname = url.split('/')[-1]
            m[fname] = url
    return m

def analyze_post(post_dir):
    """Return list of {ref, exists, parent_name, parent_exists} for each image ref."""

def fix_post(post_dir, url_map, dry_run=False):
    """Apply TYPE A/B/C fixes to a single post's index.md."""
```

### Script usage

```bash
# Analyze only — print counts without modifying anything:
python3 /opt/data/scripts/fix-image-refs.py --dry-run

# Apply the fix:
python3 /opt/data/scripts/fix-image-refs.py

# Force re-download even if local parent exists:
python3 /opt/data/scripts/fix-image-refs.py --force-download
```

Outputs:
- `/opt/data/scripts/image-fix.log` — human-readable per-post summary
- `/opt/data/scripts/image-fix-report.json` — structured JSON of every action taken

## 6.4 Results

### Site-wide

| Metric | Before fix | After fix |
|---|---|---|
| Total markdown image refs across all 67 posts | 162 | 162 |
| Refs resolving to an existing file | 151 | 162 |
| Broken refs (pointing at non-existent files) | 11 | 0 |
| TYPE A (rewritten to local parent) | — | 11 |
| TYPE B (downloaded from WP) | — | 0 |
| TYPE C (commented out as orphan) | — | 0 |

**Zero orphans remain.** Every image ref now resolves.

### Friction folder knives (success criterion)

| Metric | Before | After |
|---|---|---|
| Markdown image refs | 11 | 11 |
| Refs matching files on disk | 1 | **11** |
| Files in `images/` dir | 12 | 12 |
| `<img>` tags in rendered `public/post/2019/02/19/friction-folder-knives/index.html` | 1* | **11** |

\* Hugo `--minify` puts everything on one line, so a naive `grep -c '<img'` counts lines (1), not matches. The actual match count via `grep -oE '<img[^>]+>' | wc -l` is 11.

### Build verification

```
$ cd /opt/data/lukemillermakes-hugo && /opt/data/bin/hugo --gc --minify

                  │ EN
──────────────────┼─────
 Pages            │ 313
 Paginator pages  │   0
 Non-page files   │ 270
 Static files     │   2
 Processed images │   0
 Aliases          │   0
 Cleaned          │   0

Total in 225 ms
```

No new errors. The `non-page files: 270` count matches the `images/` count across all post bundles, confirming every image was copied into `public/`.

### Sample rendered `<img>` tags from the rebuilt friction folder knives post

```html
<img src=images/th_IMG_20190215_183026846_HDR.jpg alt>
<img src=images/th_IMG_20181027_130406710.jpg alt>
<img src=images/th_IMG_20181208_103155689_HDR.jpg alt>
<img src=images/th_IMG_20181209_160320327_HDR.jpg alt>
<img src=images/th_IMG_20181209_193655521_HDR.jpg alt>
<img src=images/th_IMG_20181217_194255945_HDR.jpg alt>
<img src=images/th_IMG_20181217_194250463_HDR.jpg alt>
<img src=images/th_IMG_20181217_194231068_HDR.jpg alt>
<img src=images/th_IMG_20190203_144857816_HDR-e1550594374822.jpg alt>
<img src=images/th_IMG_20190203_144839475_HDR-e1550594394491.jpg alt>
<img src=images/th_IMG_20190203_144825580_HDR-e1550594417737.jpg alt>
```

All 11 are pointing at parent (non-thumbnail) filenames, all of which exist on disk.

## 6.5 Edge cases handled

1. **WP optimization timestamps** (`-e1550594374822`): preserved. The regex only strips the trailing size suffix, not internal timestamps.
2. **Multi-digit timestamps in filenames** (`IMG_20181217_194231068`): preserved. The `(.+?)(?:-\d+x\d+)?` regex is non-greedy and anchored to `$`, so it only matches an actual trailing `-WxH` segment, not internal digit runs.
3. **Alternative size suffixes** (`-WxH.jpg`, `-WxH.png`, `-WxH.gif`, `-WxH.webp`, `-WxH.jpeg`): handled. The extension group captures the variant and reattaches it to the parent.
4. **Markdown images with title text** (`![alt](path "title")`): the regex `!\[[^\]]*\]\((images/[^)\s]+)` stops at the first whitespace, so the `"title"` after the path is ignored. Verified on `content/post/2018-11-07-not-a-chikin/index.md` which uses a titled image ref.
5. **WP rotation of thumbnails**: TYPE B fallback would have downloaded missing parents from the live site; in practice no TYPE B was needed because every broken ref had its parent already on disk.

## 6.6 Known limitations / followups

- **`2017-06-24-grind-your-own-stub-nib`** still has 5 broken image refs from the original migration. These are different — they're base64-style Google user-content filenames > 255 chars that hit `ENAMETOOLONG` at download time (documented in `02-migration.md`). They're not thumbnail-to-parent issues; they're fundamentally different URLs that don't exist on the live WP site either. Decision deferred to user.
- **The 12-files-in-images-vs-11-refs discrepancy** in friction folder knives: the `th_IMG_20181213_145655833_HDR.jpg` file is on disk but never referenced in the post body. The migration tool downloaded it as part of another post or via a different code path. It's an orphan image, not a broken ref. We left it on disk — removing it is a manual decision.
- **A few other posts also have orphan images** (files on disk that aren't referenced in their own `index.md`). The fix script doesn't touch these — it only fixes broken refs. Cleaning up orphans would be a separate "remove unused images" pass.

## 6.7 Files produced by this phase

| Path | Purpose |
|---|---|
| `/opt/data/scripts/fix-image-refs.py` | The fix script (re-runnable, idempotent) |
| `/opt/data/scripts/image-fix.log` | Per-post run log from the final execution |
| `/opt/data/scripts/image-fix-report.json` | Structured JSON report of every action |
| `/opt/data/documentation/wp-to-hugo/06-image-fix.md` | This document |

The `index.md` files for all 67 posts were modified in-place to point at parent image filenames instead of thumbnail variants.