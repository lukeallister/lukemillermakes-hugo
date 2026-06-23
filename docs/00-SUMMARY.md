# WordPress → Hugo migration: capstone summary

**Source site**: https://lukemillermakes.com (WordPress 6.6.1, theme "XtremelySocial")
**Source XML**: `/opt/data/dev/lukemillermakes.WordPress.2026-06-23.xml` (2.71 MB WXR, 444 items)
**Output site**: `/opt/data/lukemillermakes-hugo/` (Hugo project)
**Migration tool**: `lonekorean/wordpress-export-to-markdown` v3.0.5 (via `npx --yes`)
**Migration date**: 2026-06-23
**Target deployment**: openSUSE MicroOS VM at 192.168.1.126 (not deployed yet)

## What got migrated

| Item | Count |
|---|---|
| Source `<item>` entries in XML | 444 |
| Published posts migrated | **62** |
| Published pages migrated | **5** (about, knives, portfolio, woodworking, passwords) |
| Draft posts migrated | **2** (in `content/post/_drafts/`, one with empty body) |
| Draft pages migrated | **2** (newsletter, refund_returns) |
| Total `.md` files written | **71** |
| Images successfully downloaded | **276** of 319 attempted |
| Images failed | **43** (10 × ENAMETOOLONG, 33 × 404) |
| Categories | 21 |
| Tags | 98 |
| Rendered HTML pages in `public/` | **313** |
| Final `public/` size | **43 MB** |
| Hugo build time | ~178 ms |

## Stack

| Layer | Choice |
|---|---|
| Static site generator | Hugo **v0.148.1+extended** (installed at `/opt/data/bin/hugo`) |
| Theme | **[xmin](https://github.com/yihui/hugo-xmin)** by Yihui Xie — eXtremely Minimal Hugo theme, ~137 lines of code total |
| Migration tool | `lonekorean/wordpress-export-to-markdown` v3.0.5 (run via `npx --yes`) |
| Runtime container | `nginx:1.27-alpine` (planned, Dockerfile written) |
| Builder container | `klakegg/hugo:0.148.1-onbuild` (planned, Dockerfile written) |
| Comments | **None** (as requested) |

### Why xmin

The user asked for a minimal theme, and xmin is genuinely minimal — its own README documents ~137 lines of HTML+CSS total. No JavaScript, no search widget, no analytics hooks, no comment system, no menu widget, no social-media cards. Just a `<nav>`, `<main>`, `<footer>` and a 51-line CSS file.

We considered `hugo-paper`, `hugo-papermod`, and `hugo-minimalist`. Picked xmin because it's the smallest by raw line count.

## Directory layout

### Hugo project (`/opt/data/lukemillermakes-hugo/`)

```
lukemillermakes-hugo/
├── .dockerignore
├── .hugo_build.lock
├── Dockerfile             # multi-stage: klakegg/hugo → nginx:alpine
├── README.md              # quick-reference for the project
├── archetypes/            # (empty, default)
├── assets/                # (empty, default)
├── content/
│   ├── page/              # 5 published pages + 1 _drafts/
│   │   ├── 2017-07-06-about/
│   │   ├── 2018-03-20-knives/
│   │   ├── 2018-03-20-portfolio/
│   │   ├── 2018-03-20-woodworking/
│   │   ├── 2018-11-07-passwords/
│   │   └── _drafts/
│   │       ├── 2018-04-21-newsletter/
│   │       └── refund_returns/
│   └── post/              # 62 published post bundles + 1 _drafts/
│       ├── 2017-06-24-grind-your-own-stub-nib/
│       │   ├── index.md
│       │   └── images/    # (empty — ENAMETOOLONG failures)
│       ├── 2017-07-12-the-5-books-most-likely-to-hide-a-gun/
│       │   ├── index.md
│       │   └── images/
│       └── … (61 more)
├── data/                  # (empty, default)
├── hugo.yaml              # site config (menu, permalinks, params)
├── i18n/                  # (empty, default)
├── layouts/
│   ├── _partials/
│   │   └── header.html    # .Site.LanguageCode override
│   └── index.html         # custom home page (date-sorted, posts-only)
├── nginx.conf             # production nginx config
├── public/                # rendered output (build artifact, 43 MB)
├── resources/             # Hugo image cache (regenerated)
├── static/                # (empty, default)
└── themes/
    └── xmin/              # vendored theme (~137 lines)
```

### Documentation (`/opt/data/documentation/wp-to-hugo/`)

```
documentation/wp-to-hugo/
├── 00-SUMMARY.md          # ← this file
├── 01-recon.md            # XML analysis + tool inventory
├── 02-migration.md        # lonekorean tool run, output counts, sample frontmatter
├── 03-hugo-setup.md       # theme choice, hugo.yaml, layout overrides
├── 04-build-verify.md     # build command, output samples, verification
└── 05-deployment-prep.md  # Dockerfile, nginx.conf, MicroOS deploy plan
```

## Sample migrated content

### Post frontmatter (from `content/post/2024-08-15-i-didnt-need-all-those-keys-anyway/index.md`)

```markdown
---
title: "I didn't need all those keys anyway"
date: 2024-08-15T16:46:24.000Z
categories:
  - "tech"
tags:
  - "tech"
  - "keyboard"
  - "making"
---

I've posted a few keyboard builds here over the years. Each one was me looking
for some kind of efficiency, or just wanting to try something different. This
time, I wanted to solve 3 problems:
```

### Page frontmatter (from `content/page/2017-07-06-about/index.md`)

```markdown
---
title: "About"
date: 2017-07-06T00:45:24.000Z
---

A blog. By Luke Miller.

Conversations about art, culture, DIY, and the occasional short story.
```

### Draft frontmatter (from `content/post/_drafts/id-1048/index.md`)

```markdown
---
title: "Running nixos-anywhere on a weird desktop"
coverImage: "small_PXL_20240825_0347080302.jpg"
draft: true
---
```

## Issues encountered & resolutions

### 1. Hugo version compatibility
**Problem**: xmin theme's `theme.toml` declares `min_version = "0.146.0"`; we initially had Hugo 0.124.1.
**Resolution**: Upgraded to Hugo 0.148.1+extended by downloading the official tarball.

### 2. `.Site.Language.Locale` removed in Hugo 0.148
**Problem**: xmin's `header.html` references `.Site.Language.Locale`, which no longer exists in Hugo 0.148+. The build failed at render time with "can't evaluate field Locale".
**Resolution**: Overrode `layouts/_partials/header.html` at the project level, switching to `.Site.LanguageCode` (which still exists).

### 3. Menu URLs needed leading slash
**Problem**: Initial menu config used `url: "page/about/"`. Hugo renders `content/page/about/index.md` to `/about/index.html` (page sections don't appear in URLs), so the link 404'd.
**Resolution**: Changed all menu URLs to absolute-path form: `url: "/about/"`, etc.

### 4. Default home page rendered alphabetically
**Problem**: xmin's `list.html` (used as the home template) sorts pages alphabetically rather than by date.
**Resolution**: Wrote a custom `layouts/index.html` that filters to section=post, sorts by date reversed, and caps at 20 entries.

### 5. 10 broken image refs in oldest post
**Problem**: The first post (`2017-06-24-grind-your-own-stub-nib`) references 5 images hosted on `lh3.googleusercontent.com` with base64-style filenames > 255 chars. The migration tool's filesystem write threw `ENAMETOOLONG`.
**Resolution**: Documented in `02-migration.md`; the post body still references the (non-existent) files, so they'll render as broken images until manually fixed or removed.

### 6. 33 missing thumbnails
**Problem**: 33 small thumbnail files (mostly `-300x225.jpg` derivatives) returned 404 from the live WP media library.
**Resolution**: Documented; ignored because parent full-resolution images are present.

### 7. Empty draft body
**Problem**: `content/post/_drafts/id-970/index.md` (the Ergofan keyboard post) has frontmatter but no body content.
**Resolution**: Left as-is. The WordPress export's source row had empty `post_content`, so there was nothing to migrate.

### 8. Subagent timeouts (2 × 600s)
**Problem**: The original subagent and the follow-up subagent both hit the 10-minute timeout. The first got through recon+migration+Hugo init; the second got through deployment artifacts but not the docs.
**Resolution**: I (the parent agent) wrote the missing docs (03, 04, 05, 00) directly. The Hugo build still passes (313 pages, 178 ms) after all changes.

## What's next

### Immediate (you, the user, should do)

1. **Review migrated content** — open a few posts in `/opt/data/lukemillermakes-hugo/content/post/` and verify they read well. Look at:
   - `2018-03-13-karambit/` (image-heavy post, 16 images downloaded)
   - `2018-04-25-diy-mechanical-keyboard/` (16 images)
   - `2018-05-19-japanese-toolbox/` (16 images)
   - A recent post like `2024-08-15-i-didnt-need-all-those-keys-anyway/`

2. **Preview locally** — see what the rendered site looks like:
   ```bash
   cd /opt/data/lukemillermakes-hugo
   /opt/data/bin/hugo server -D
   ```
   Open http://localhost:1313/ in a browser.

3. **Decide on the ENAMETOOLONG post** — `content/post/2017-06-24-grind-your-own-stub-nib/index.md` has 5 broken image references from 2017. Options:
   - Remove the broken `![...](images/<long-name>)` lines
   - Re-host the images and update the URLs
   - Leave as broken (they're in the oldest post; not high-traffic)

4. **Decide on drafts** — there are 4 draft items left in `content/post/_drafts/` and `content/page/_drafts/`:
   - `content/post/_drafts/id-970/` — Ergofan keyboard (empty body)
   - `content/post/_drafts/id-1048/` — NixOS-anywhere on a weird desktop (cover image but empty body? worth checking)
   - `content/page/_drafts/2018-04-21-newsletter/` — newsletter signup page
   - `content/page/_drafts/refund_returns/` — refund policy (the "Refund and Returns Policy" sample)
   
   These are not rendered in production builds (no `-D` flag). If you want any of them published, move them up one directory level and set `draft: false` (or delete the line).

5. **Consider removing the empty draft body for Ergofan** — if it's really empty, `rm -rf content/post/_drafts/id-970/` cleans it up.

6. **Update `hugo.yaml` `baseURL`** — currently `https://lukemillermakes.com/`. If you decide on a different domain or want to preview at a different URL temporarily, change this before building.

### Near-term (deploy to MicroOS VM)

7. **DNS cutover** — point `lukemillermakes.com` (and `www`) at `192.168.1.126` via an A record. Lower TTL 24-48 hrs before cutover.

8. **Build and transfer the container image**:
   ```bash
   cd /opt/data/lukemillermakes-hugo
   podman build -t lukemillermakes:latest .
   podman save lukemillermakes:latest | ssh lukemillermakes@192.168.1.126 podman load
   ```

9. **Set up the systemd quadlet on the VM** — see `05-deployment-prep.md` §5.4.3 for the full unit file.

10. **Set up HTTPS** — the simplest path is a Caddy reverse proxy on the VM host that fronts port 8080 with Let's Encrypt. See `05-deployment-prep.md` §5.4.4.

11. **Test on the VM** — `curl http://127.0.0.1:8080/about/` should return the rendered HTML. Then `curl https://lukemillermakes.com/about/` should work once DNS and Caddy are in place.

12. **Take down the old WP site** — keep it offline for 30 days as a fallback. Then archive the database and tear it down.

### Long-term (optional)

13. **Add a content search** — xmin doesn't ship search; if you want one, Pagefind (https://pagefind.app/) integrates cleanly with Hugo. It's a static index that runs over the built output, no server needed.

14. **Add an RSS feed** — Hugo auto-generates `/index.xml` already; it's in the build output. Check that it validates against https://validator.w3.org/feed/.

15. **Consider web analytics** — nothing is set up right now (we removed the disqusShortname / googleAnalytics from xmin's example config). Plausible or Umami are privacy-friendly self-hostable options if you want to know who's reading.

16. **Set up a deploy script** — right now the workflow is: edit content, `hugo` to rebuild, `podman build`, `podman save`, ssh, `podman load`, restart the quadlet. A short `deploy.sh` script (or a GitHub Actions workflow if you push the source to a repo) would tighten that up.

## File inventory

### Hugo project files (created/modified during this migration)

- `/opt/data/lukemillermakes-hugo/hugo.yaml` — site config
- `/opt/data/lukemillermakes-hugo/layouts/_partials/header.html` — xmin header override (LanguageCode fix)
- `/opt/data/lukemillermakes-hugo/layouts/index.html` — custom home page (date-sorted, posts-only)
- `/opt/data/lukemillermakes-hugo/Dockerfile` — multi-stage Hugo → nginx
- `/opt/data/lukemillermakes-hugo/nginx.conf` — production nginx config
- `/opt/data/lukemillermakes-hugo/.dockerignore` — build context exclusions
- `/opt/data/lukemillermakes-hugo/README.md` — quick-reference
- `/opt/data/lukemillermakes-hugo/content/post/` — 63 post bundles (62 published + 1 drafts subfolder)
- `/opt/data/lukemillermakes-hugo/content/page/` — 5 published pages + 1 drafts subfolder
- `/opt/data/lukemillermakes-hugo/themes/xmin/` — vendored theme (unchanged)
- `/opt/data/lukemillermakes-hugo/public/` — rendered output (43 MB, 313 HTML + 270 images)

### Documentation files

- `/opt/data/documentation/wp-to-hugo/01-recon.md`
- `/opt/data/documentation/wp-to-hugo/02-migration.md`
- `/opt/data/documentation/wp-to-hugo/03-hugo-setup.md`
- `/opt/data/documentation/wp-to-hugo/04-build-verify.md`
- `/opt/data/documentation/wp-to-hugo/05-deployment-prep.md`
- `/opt/data/documentation/wp-to-hugo/00-SUMMARY.md` (this file)

### Migration tool output (kept for reference)

- `/opt/data/hugo-import/posts/` — original output (now in `content/post/`)
- `/opt/data/hugo-import/pages/` — original output (now in `content/page/`)
- `/opt/data/hugo-import/migration.log` — full tool run log (34 KB, 454 lines)

### Tools installed during migration

- Hugo v0.148.1+extended at `/opt/data/bin/hugo` (was not present; installed from official tarball)

Node.js, npx, and Git were already present.