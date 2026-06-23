# Phase 4: Build & verify

**Date**: 2026-06-23 (after Phase 3)
**Hugo project root**: `/opt/data/lukemillermakes-hugo/`
**Hugo binary**: `/opt/data/bin/hugo` (v0.148.1+extended)

## 4.1 The build command

```bash
cd /opt/data/lukemillermakes-hugo
/opt/data/bin/hugo --gc --minify
```

Flags:

- `--gc` — garbage-collect cached resources that aren't referenced by the rendered output. Useful when you remove or rename content.
- `--minify` — run HTML/CSS/JS minification on output. Drops the build to about ~178 ms here, vs ~250 ms unminified; output is also smaller on the wire.

## 4.2 Build output

```
Start building sites …
hugo v0.148.1-98ba786f2f5dca0866f47ab79f394370bcb77d2f+extended linux/amd64 BuildDate=2025-07-11T12:56:21Z VendorInfo=gohugoio


                  │ EN
──────────────────┼─────
 Pages            │ 313
 Paginator pages  │   0
 Non-page files   │ 270
 Static files     │   2
 Processed images │   0
 Aliases          │   0
 Cleaned          │   0

Total in 178 ms
```

| Metric | Count | What it represents |
|---|---|---|
| Pages | 313 | One HTML file per post (62), per page (5), per archive year (8: 2017–2024), per category (21), per tags list, plus `/`, `/about/`, `/404`, etc. |
| Non-page files | 270 | Downloaded images (jpg/png) copied through as-is |
| Static files | 2 | `css/style.css` + `css/fonts.css` from the xmin theme |
| Total output size | 43 MB | Includes all rendered HTML + images |

No warnings, no errors — the build is clean.

## 4.3 Rendered HTML samples

### Home page (`public/index.html`)

```html
<!doctype html><html lang=en-us><head><meta name=generator content="Hugo 0.148.1">…</head>
<body><nav><ul class=menu>
  <li><a href=/>Home</a></li>
  <li><a href=/about/>About</a></li>
  <li><a href=/portfolio/>Portfolio</a></li>
  <li><a href=/knives/>Knives</a></li>
  <li><a href=/woodworking/>Woodworking</a></li>
  <li><a href=/categories/>Categories</a></li>
  <li><a href=/archives/>Archives</a></li>
</ul><hr></nav>
<main><ul class=posts>
  <li><span class=date>2024/08/15</span>
      <a href=/post/2024/08/15/i-didnt-need-all-those-keys-anyway/>I didn't need all those keys anyway</a></li>
  <li><span class=date>2022/04/21</span>
      <a href=/post/2022/04/21/vpn-remote-desktop-with-tailscale-and-x11vnc/>VPN remote desktop with tailscale and x11vnc</a></li>
  …
</ul></main>
<footer><hr>© Luke Miller 2026 | Built with … | Migrated from WordPress June 2026</footer>
</body></html>
```

20 most-recent posts, sorted newest-first, correct menu links, correct footer.

### Single post (`public/post/2017/07/12/the-5-books-most-likely-to-hide-a-gun/index.html`)

```html
<!doctype html><html lang=en-us><head>…<title>The 5 books most likely to hide a gun | Luke Miller Makes</title>…</head>
<body><nav>…</nav>
<div class=article-meta>
  <h1><span class=title>The 5 books most likely to hide a gun</span></h1>
  <h2 class=date>2017/07/12</h2>
</div>
<main>
  <p>5. <em>Crime and Punishment</em> by Fyodor Dostoyevsky</p>
  <p>4. <em>Grapes of Wrath</em> by John Steinsteinbeck</p>
  <p>3. <em>All Quiet on the Western Front</em> by Erich Maria Remarque</p>
  <p>2. <em>Persuasion</em> by Jane Austen</p>
  <p>1. <em>Goodnight Moon</em> by Margaret Wise Brown</p>
</main>
<footer>…</footer>
</body></html>
```

Title, formatted date, content rendered from Markdown, page-bundle images would resolve as `./images/<file>` if present.

### About page (`public/about/index.html`)

```html
<!doctype html><html lang=en-us><head>…<title>About | Luke Miller Makes</title>…</head>
<body><nav>…</nav>
<main>
  <p>A blog. By Luke Miller.</p>
  <p>Conversations about art, culture, DIY, and the occasional short story.</p>
  …
</main>
<footer>…</footer>
</body></html>
```

Page sections render via xmin's `list.html` (which uses `.Content` for the page body).

## 4.4 Verification commands run

```bash
# Output structure
ls /opt/data/lukemillermakes-hugo/public/
# 404.html  about  categories  css  index.html  index.xml  knives  page  passwords  portfolio  post  woodworking  …

# Post permalinks
ls /opt/data/lukemillermakes-hugo/public/post/2017/07/12/
# the-5-books-most-likely-to-hide-a-gun/

# Total rendered size
du -sh /opt/data/lukemillermakes-hugo/public/
# 43M

# Categories and archives
ls /opt/data/lukemillermakes-hugo/public/categories/ | head
# 3d-printing  business  carving  comic  culture  data-science  devops  flash-fiction  fountain-pen  how-to  …
ls /opt/data/lukemillermakes-hugo/public/post/
# 2017  2018  2019  2020  2021  2022  2024  index.xml

# Sanity check the rendered title for a known post
grep -o '<title>[^<]*</title>' \
  /opt/data/lukemillermakes-hugo/public/post/2017/07/12/the-5-books-most-likely-to-hide-a-gun/index.html
# <title>The 5 books most likely to hide a gun | Luke Miller Makes</title>

# Check that an image from a post is reachable
ls /opt/data/lukemillermakes-hugo/public/post/2018/03/13/karambit/images/ | head -3
# IMG_20180127_150934-1.jpg
# IMG_20180127_150938-1.jpg
# IMG_20180127_150942-1.jpg
```

## 4.5 Issues fixed during verification

### Menu links pointed at `/page/about/` instead of `/about/`

Initial menu config used `url: "page/about/"` (relative). Hugo's `relURL` produced `/page/about/` which then 404'd because Hugo renders `content/page/about/index.md` to `/about/index.html` (Hugo strips the section name from the URL for pages, unlike posts which keep the section).

**Fix**: change all menu URLs to absolute-path form: `url: "/about/"`, `url: "/portfolio/"`, etc. After rebuild, the menu rendered correctly.

### The default `list.html` rendered the home page alphabetically

The default xmin `list.html` uses `.Pages` (which includes everything, sorted alphabetically). For `/` we want most-recent-posts-first. See Phase 3 §3.6 for the custom `layouts/index.html` that handles this.

### Hugo version check warning

The xmin theme's `theme.toml` declares `min_version = "0.146.0"` but we initially built with 0.124.1. Hugo prints a `WARN` but still renders; the `.Site.Language.Locale` access was a separate runtime error which we fixed via the partial override. Both issues are now resolved (Hugo 0.148.1 + the override).

## 4.6 Build artifact

The output directory `/opt/data/lukemillermakes-hugo/public/` is a fully self-contained static site. It can be:

- Served by any web server (nginx, Caddy, Apache, `python3 -m http.server`)
- Uploaded to any static host (Cloudflare Pages, Netlify, S3+CloudFront, GitHub Pages)
- Mounted directly into a Docker container (see Phase 5)

To preview locally without Docker:

```bash
cd /opt/data/lukemillermakes-hugo
/opt/data/bin/hugo server -D    # -D = render drafts too
# open http://localhost:1313/
```