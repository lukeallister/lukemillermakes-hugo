# Phase 3: Hugo project setup

**Date**: 2026-06-23
**Hugo project root**: `/opt/data/lukemillermakes-hugo/`

## 3.1 Theme choice: [xmin](https://github.com/yihui/hugo-xmin)

We picked **XMin** (eXtremely Minimal Hugo theme) by Yihui Xie. The author's own README documents the theme's size:

```
find . -not -path '*/exampleSite/*' \( -name '*.html' -o -name '*.css' \) | xargs wc -l
       12 ./layouts/single.html
       20 ./layouts/list.html
       13 ./layouts/terms.html
        5 ./layouts/404.html
        0 ./layouts/_partials/foot_custom.html
        0 ./layouts/_partials/head_custom.html
        9 ./layouts/_partials/footer.html
       20 ./layouts/_partials/header.html
       51 ./static/css/style.css
        7 ./static/css/fonts.css
      137 total
```

That matches "minimal theme" as requested. No JavaScript, no built-in search, no comments, no analytics hooks — just a `<nav>`, `<main>`, `<footer>` and a tiny CSS file.

The theme was cloned directly (not as a submodule) into `themes/xmin/`:

```bash
git clone https://github.com/yihui/hugo-xugo-xmin.git themes/xmin   # (run inside the project)
```

We considered `hugo-paper`, `hugo-papermod`, and `hugo-minimalist`; xmin wins on raw line count and lack of optional widgets.

## 3.2 Hugo version

`hugo new site` initialized the project with **Hugo 0.124.1+extended** (the version installed in `/opt/data/bin/hugo` at the start). The xmin theme's `theme.toml` declares:

```toml
min_version = "0.146.0"
```

A first build attempt produced:

```
WARN  Module "xmin" is not compatible with this Hugo version: Min 0.146.0; run "hugo mod graph" for more information.
```

So we upgraded:

```bash
curl -fsSL -o /tmp/hugo-new.tar.gz \
  https://github.com/gohugoio/hugo/releases/download/v0.148.1/hugo_extended_0.148.1_Linux-64bit.tar.gz
tar -xzf /tmp/hugo-new.tar.gz -C /tmp/
cp /tmp/hugo /opt/data/bin/hugo
/opt/data/bin/hugo version
# hugo v0.148.1-98ba786f2f5dca0866f47ab79f394370bcb77d2f+extended linux/amd64 ...
```

## 3.3 Theme fix: `.Site.Language.Locale` → `.Site.LanguageCode`

Hugo 0.148 removed the `.Language.Locale` field from the Site language object. The xmin theme's `layouts/_partials/header.html` line 2 references it:

```html
<html lang="{{ .Site.Language.Locale }}">
```

That breaks with a runtime error:

```
can't evaluate field Locale in type *langs.Language
```

We overrode the partial locally at `/opt/data/lukemillermakes-hugo/layouts/_partials/header.html` (Hugo's lookup order picks the project's copy over the theme's). The replacement uses `.Site.LanguageCode`, which still exists and matches the value we set in `hugo.yaml`:

```html
<!DOCTYPE html>
<html lang="{{ .Site.LanguageCode }}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ .Title }} | {{ .Site.Title }}</title>
    <link rel="stylesheet" href="{{ "css/style.css" | relURL }}" />
    <link rel="stylesheet" href="{{ "css/fonts.css" | relURL }}" />
  </head>

  <body>
    <nav>
    <ul class="menu">
      {{ range .Site.Menus.main }}
      <li><a href="{{ .URL | relURL }}">{{ .Name }}</a></li>
      {{ end }}
    </ul>
    <hr/>
    </nav>
```

We also dropped the `{{ partial "head_custom.html" . }}` line at the end of `<head>` since both xmin's `head_custom.html` and `foot_custom.html` are empty files (zero-byte hooks for user overrides) and aren't needed.

## 3.4 `hugo.yaml` configuration

```yaml
baseURL: "https://lukemillermakes.com/"
languageCode: en-us
title: "Luke Miller Makes"
theme: "xmin"

# Page sections: posts live in /post/, pages live in /page/.
# XMin uses .Section for layout selection; we map WP's "post" to "post" and WP's
# "page" to "page". (Hugo treats content/<dir>/index.md as belonging to that section.)
pagination:
  pagerSize: 20

# Permalinks: preserve WP's /YYYY/MM/DD/slug/ structure
permalinks:
  post: "/post/:year/:month/:day/:slug/"
  page: "/:slug/"
  drafts: "/drafts/:year/:month/:day/:slug/"

# Main nav mirrors the live WP site's "Primary Menu"
menu:
  main:
    - name: Home
      url: ""
      weight: 1
    - name: About
      url: "/about/"
      weight: 2
    - name: Portfolio
      url: "/portfolio/"
      weight: 3
    - name: Knives
      url: "/knives/"
      weight: 4
    - name: Woodworking
      url: "/woodworking/"
      weight: 5
    - name: Categories
      url: "categories/"
      weight: 6
    - name: Archives
      url: "archives/"
      weight: 7

params:
  description: "A blog. By Luke Miller. Conversations about art, culture, DIY, and the occasional short story."
  footer: "&copy; Luke Miller {Year} | Built with [Hugo](https://gohugo.io/) and the [XMin theme](https://github.com/yihui/hugo-xmin) | Migrated from WordPress June 2026"
  showPoweredBy: false

# Don't render drafts in production builds; use --buildDrafts locally.
buildDrafts: false
buildFuture: false

# Enable GitHub-flavored markdown + raw HTML passthrough (for any embedded HTML the
# WP→MD converter emitted)
markup:
  goldmark:
    renderer:
      unsafe: true
    extensions:
      passthrough:
        enable: true
        delimiters:
          block:
          - - \[ 
            - \]
          - - $$
            - $$
          inline:
          - - \(
            - \)
```

### Why these choices

| Setting | Why |
|---|---|
| `baseURL` | Placeholder; will become the real lukemillermakes.com URL when DNS is pointed at 192.168.1.126 |
| `languageCode: en-us` | Required by xmin's `header.html` override; was `.Site.Language.Locale` originally |
| `theme: xmin` | The chosen minimal theme |
| `pagination.pagerSize: 20` | Reasonable archive-page size; xmin's `list.html` uses `.Pages` so this only applies if we add paginated lists later |
| `permalinks.post` | The WP URLs are `/YYYY/MM/DD/slug/`; preserving them keeps external links intact |
| `permalinks.page` | WP pages were `/about/`, `/portfolio/`, etc. — flat URLs map cleanly |
| `permalinks.drafts` | Drafts get `/drafts/...` prefix so they're unambiguous |
| `menu.main` | Mirrors WP's Primary Menu (Home/About/Portfolio); plus Knives/Woodworking (sub-pages of Portfolio), plus taxonomy pages |
| `params.description` | Used in the `<meta>` description and feeds |
| `params.footer` | Custom footer text with markdown support |
| `markup.goldmark.renderer.unsafe` | The WP→MD converter emits raw `<img>`, `<iframe>`, etc. for embeds; without `unsafe: true` Hugo would strip them |
| `markup.goldmark.extensions.passthrough` | Allows MathJax-style `\[...\]` and `$$...$$` blocks if you ever add math posts |

## 3.5 Content organization

The migration tool output (`/opt/data/hugo-import/`) was:

```
hugo-import/
├── posts/         # 63 dirs: 62 published + 1 _drafts/ subfolder
│   ├── 2017-06-24-grind-your-own-stub-nib/
│   │   ├── index.md
│   │   └── images/    # (empty — ENAMETOOLONG failures)
│   ├── 2017-07-12-the-5-books-most-likely-to-hide-a-gun/
│   │   ├── index.md
│   │   └── images/
│   └── ...
└── pages/         # 5 published + 1 _drafts/
    ├── 2017-07-06-about/index.md
    ├── 2018-03-20-portfolio/index.md
    └── ...
```

Hugo's content convention requires section names to be at the top level of `content/`, so we renamed:

```bash
mkdir -p /opt/data/lukemillermakes-hugo/content/post
mkdir -p /opt/data/lukemillermakes-hugo/content/page
mv /opt/data/hugo-import/posts/*   /opt/data/lukemillermakes-hugo/content/post/
mv /opt/data/hugo-import/pages/*   /opt/data/lukemillermakes-hugo/content/page/
```

Resulting structure:

```
content/
├── post/
│   ├── 2017-06-24-grind-your-own-stub-nib/
│   │   ├── index.md
│   │   └── images/            # 276 of 319 attempted images made it across
│   ├── 2017-07-12-the-5-books-most-likely-to-hide-a-gun/
│   │   ├── index.md
│   │   └── images/
│   └── ... (61 more published posts)
│   └── _drafts/               # 2 draft posts (1 with empty body)
└── page/
    ├── 2017-07-06-about/
    ├── 2018-03-20-knives/
    ├── 2018-03-20-portfolio/
    ├── 2018-03-20-woodworking/
    ├── 2018-11-07-passwords/
    └── _drafts/
        ├── 2018-04-21-newsletter/
        └── refund_returns/
```

We did **not** rename folders to remove the `YYYY-MM-DD-` prefix. The xmin theme doesn't care about folder names (it uses `.RelPermalink`), and keeping the date prefix gives us stable URLs that match WP's `/YYYY/MM/DD/slug/` permalinks. The 63 post bundles include the image directories alongside each `index.md`, which is Hugo's recommended page-bundle layout for posts that have inline images.

## 3.6 Custom `layouts/index.html`

The default xmin `list.html` works fine for section pages (categories, tags, post archive), but the home page (`/`) inherits it too and ends up listing every post in **alphabetical** order rather than by date. We overrode `layouts/index.html` to:

```html
{{ partial "header.html" . }}
<main>
  {{ .Content }}
  <ul class="posts">
    {{ range first 20 (where .Site.RegularPages "Section" "post").ByDate.Reverse }}
    <li>
      <span class="date">{{ .Date.Format "2006/01/02" }}</span>
      <a href="{{ .RelPermalink }}">{{ .Title | markdownify }}</a>
    </li>
    {{ end }}
  </ul>
</main>
{{ partial "footer.html" . }}
```

Key differences from xmin's `list.html`:

1. **Sort by date** — `ByDate.Reverse` puts the most recent post at the top
2. **Filter to posts only** — `where ... "Section" "post"` excludes pages from the home list
3. **Cap at 20** — `first 20` keeps the home page fast (no pagination yet; can add `template` + `.Paginator` later)
4. **Use `.RegularPages`** — Hugo's "regular pages" excludes taxonomy list pages, so the home list stays clean

The `<main>` wrapper gives us a place to drop a `site.content.md` or `.Content` block in the future (e.g., an introduction paragraph).

## 3.7 What didn't change

- `themes/xmin/` is vendored unchanged except for the `_partials/header.html` override we placed at the project level (Hugo uses project `layouts/` first, so the theme copy stays pristine).
- `static/`, `archetypes/`, `assets/`, `data/`, `i18n/` are all empty defaults from `hugo new site`. We don't need any of them for this site.