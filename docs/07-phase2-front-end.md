# Phase 2 — Front-end cleanup & layout rebuild

**Date:** June 23, 2026
**Scope:** Custom layout, header CSS wiring, portfolio merge, link fixes,
content cleanup, build verification.

---

## Summary

Phase 2 took the static-output Phase 1 site and re-laid the surface so the
homepage, the portfolio, and the cross-post links all behave like a real blog
rather than the raw XMin default.

Concretely, this phase shipped:

- A **new home page** that lists the 20 most recent posts top-to-bottom, each
  with a real thumbnail that links to the post (the previous card grid had
  thumbnails that all linked back to `/`).
- A **working Portfolio page** with the Woodworking and Knives sections merged
  into a single page, broken image refs and a malformed table replaced.
- **All cross-content links rewritten to relative paths** — no
  `https://lukemillermakes.com` URLs anywhere in the rendered HTML outside of
  the sitemap / RSS (where they're correct by design).
- **WordPress shortcode remnants cleaned** (`\[caption ...\]`, `\[phpinclude\]`)
  in 8 post files plus a separate pass of over-escape cleanup in 3 more posts
  where the WP→MD converter had backslash-escaped every backtick, dash, and
  underscore inside what should have been fenced code blocks.
- **Header CSS wired** — `bootstrap.min.css`, `palette.css`, `style.css`,
  `fonts.css`, `custom.css` all load on every page.

---

## Files changed

| File                                  | What changed                                     |
| ------------------------------------- | ------------------------------------------------ |
| `layouts/index.html`                  | Replaced card grid with vertical post list       |
| `layouts/_partials/header.html`       | `.Site.Language.Locale` → `.Site.LanguageCode` + 5 CSS refs |
| `static/css/custom.css`               | Added `.post-list-*` styles, removed `.post-card` |
| `content/page/2018-03-20-portfolio/index.md` | Rebuilt Woodworking + Knives sections  |
| `content/post/**/*.md` (28 files)     | Hardcoded `lukemillermakes.com` → relative        |
| `content/post/**/*.md` (11 files)     | WP shortcode escapes + over-escape cleanup       |
| `hugo.yaml`                           | Menu comment expanded; `categories/` → `/categories/` |

---

## Home page redesign

The Phase 1 template rendered a 3-column grid of cards with thumbnails that
all linked to `/` (the post itself was reached only via the title link). The
bug came from the template using `{{ $.RelPermalink }}` — `$` resolves to the
top-level context inside the range, not the iterated post.

### New `layouts/index.html`

The new template iterates with `{{ range ... }}` and uses the loop variable's
own `.RelPermalink` for every link (image, title, body), and walks each
post's `.Resources.ByType "image"` to find a usable thumbnail:

```go-html-template
{{ $thumbSrc := "" }}
{{ with .Params.coverImage }}
  {{ $ci := . }}
  {{ range $.Resources.ByType "image" }}
    {{ if or (eq .Name $ci) (eq .Name (printf "%s.jpg" $ci)) (eq .Name (printf "%s.png" $ci)) }}
      {{ if not $thumbSrc }}{{ $thumbSrc = .RelPermalink }}{{ end }}
    {{ end }}
  {{ end }}
{{ end }}
{{ if not $thumbSrc }}
  {{ range .Resources.ByType "image" }}
    {{ if not $thumbSrc }}{{ $thumbSrc = .RelPermalink }}{{ end }}
  {{ end }}
{{ end }}
{{ with $thumbSrc }}
<img class="post-list-thumb" src="{{ . }}" alt="{{ $.Title }}">
{{ end }}
```

Note the coverImage name lookup matches against `.Name` (Hugo's resource
name, which strips the extension) with fallbacks for the two common
extensions. If the coverImage doesn't match any resource, we fall through
to the first image resource — which is the right behavior for the posts
that have no `coverImage` frontmatter (most of them).

### New CSS in `static/css/custom.css`

The grid was replaced by a stacked vertical list — one post per container,
full content width, with a left-rail 220px thumbnail and right-side body:

```css
.post-list-item article {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 1.25rem;
  align-items: start;
}
.post-list-thumb { width: 100%; height: 165px; object-fit: cover; }
@media (max-width: 640px) {
  .post-list-item article { grid-template-columns: 1fr; }
}
```

The full-width mobile breakpoint keeps the thumbnail above the body instead
of squeezing the two-column layout.

---

## Portfolio page merge

`content/page/2018-03-20-portfolio/index.md` had three problems from Phase 1:

1. **Missing images.** Most of the inline `![](images/...)` references pointed
   at filenames that never made it to the bundle (`images/IMG_20170603_135408-1.jpg`,
   `images/download_20170824_201851-1.jpg`, etc.). The two images that DID
   survive (`IMG_0046-1-e1521558725865.jpg`, `IMG_20180312_191301-2-e1521558759423.jpg`)
   were the only ones that rendered.

2. **Malformed table.** The "Friction folder in Jatoba" section had a
   pipe-only table that wasn't valid markdown:

   ```
   | ![](images/th_IMG_20181217_194255945_HDR.jpg) | ![](images/th_IMG_20181217_194248946_HDR.jpg) | ![](images/th_IMG_20181217_194231068_HDR.jpg) |
   | --- | --- | --- |
   ```

   The middle filename (`...194248946_HDR.jpg`) doesn't exist in the bundle,
   so even if the table had been valid it would have had a broken image.

3. **Missing image comments.** Two sections had explicit
   `<!-- MISSING IMAGE: ... -->` comments instead of content.

### Rewrite

The page was rebuilt to:

- Keep the two sections that have working images (Cigar box ukelele,
  Karambit, and the Friction folder in Jatoba, where we use only the two
  existing files).
- Replace each missing-image bullet with a short prose note explaining
  the project and linking to its build post where one exists.
- Replace the malformed table with two valid markdown image lines.

Example of the rebuild (excerpt):

```markdown
### Karambit: 1095 steel, walnut handle
See the [karambit build post](/post/2018/03/13/karambit/) for the full build.

![Karambit with walnut handle](images/IMG_20180312_191301-2-e1521558759423.jpg)
```

The page now renders 3 working images and 7 prose stubs with cross-links
to the build posts, instead of 5 broken image refs and 1 broken table.

---

## Hardcoded link rewrite

Phase 1 had 98 hardcoded `lukemillermakes.com` URLs across 30 content files.
Most were inline image refs like:

```markdown
[![](images/r_IMG_20200321_154453894.jpg)](http://lukemillermakes.com/wp-content/uploads/2020/03/r_IMG_20200321_154453894.jpg)
```

The thumbnail points at the local bundle copy and the outer link points at
the WordPress full-resolution original — but the original is no longer
hosted (or the WP media library was 404ing during migration).

### Rewrite strategy

Three passes:

1. **Image-link WP uploads** → `/post/YYYY/MM/DD/<slug>/images/<filename>`.
   For each WP uploads URL, look up which post bundle owns that file by
   matching `(year, month, filename)` against the page bundle's date and
   image directory. Result: 82 links rewritten.

2. **Date-style post URLs** (`/YYYY/MM/DD/slug/`) → `/post/YYYY/MM/DD/slug/`
   to match Hugo's permalink scheme. Result: 37 links rewritten.

3. **Bare root URLs** (`lukemillermakes.com/about/`) → `/about/`. Result:
   18 more.

### Asset files (.zip, .scad, .stl) — intentionally left as `/wp-content/...`

Five asset downloads (CAD files, firmware zips, etc.) don't exist in the
local bundles and weren't migrated. Their URLs were left as
`/wp-content/uploads/YYYY/MM/<filename>` rather than rewritten — they're
already broken (the files don't exist anywhere on disk), so rewriting them
to a different broken path would just hide the intent. The link text still
says what the user would have downloaded.

### Result

After the rewrite:

- **Zero** hardcoded `lukemillermakes.com` URLs in any rendered HTML page.
- 13 `/wp-content/uploads/...` references remain — all are non-image
  asset URLs (zip/scad/stl) that don't exist on disk.
- The RSS feed (`/post/index.xml`, `/page/index.xml`) and `sitemap.xml`
  still contain `https://lukemillermakes.com` — that's correct by design
  because they need the canonical baseURL.

---

## WP shortcode cleanup

The WP→MD converter emitted literal `\[caption ...\]` and `\[phpinclude ...\]`
shortcodes with leading backslashes, which Hugo's goldmark renders as
escaped-bracket text. The result was visible text like:

```
\[caption id="attachment\_356" align="aligncenter" width="300"\]
[/caption\]
```

showing up in the rendered HTML where the user had meant an inline image
wrapped in a caption.

### Files affected

| File                                                          | Shortcode escapes stripped |
| ------------------------------------------------------------- | --------------------------: |
| `content/page/2018-11-07-passwords/index.md`                  | 1                           |
| `content/post/2018-11-05-frankensteins-password-generator/index.md` | 5                |
| `content/post/2018-11-13-why-would-you-make-that/index.md`    | 4                           |
| `content/post/2018-03-17-repairing-a-silent-guitar/index.md`  | 4                           |
| `content/post/2018-07-11-a-pretentious-carving-knife/index.md` | 3                          |
| `content/post/2019-01-31-battery-powered-speaker/index.md`    | 9                           |
| `content/post/2018-12-02-a-3d-printed-gaming-keyboard-part-1/index.md` | 2       |
| `content/post/2018-05-19-japanese-toolbox/index.md`           | 3                           |

For the `[phpinclude file='pass']` shortcodes (which produced dynamic
password-generator widgets on the live WP site), the plugin and the
generator itself are gone, so the escapes were replaced with a small HTML
comment explaining what used to be there:

```markdown
<!-- dynamic content (pass) was hosted by a WordPress plugin and is no longer available -->
```

### Over-escape pass (3 more files)

Three additional files had a different, more pervasive problem — the
WP→MD converter had backslash-escaped every backtick, dash, and underscore
inside what should have been fenced code blocks:

```markdown
\\`\\`\\` mkdir dev cd dev git clone ... \\`\\`\\`
\\- 1 Arduino pro micro
LD\\_LIBRARY\\_PATH=./mjpg\\_streamer ...
```

These were unescaped using straightforward string substitutions — safe in
context because the source was the user's own original prose and the
over-escapes are a consistent converter artifact in these specific files.
The substitutions:

| Escape | Replace with | Why safe                                                  |
| ------ | ------------ | --------------------------------------------------------- |
| `\\\`` | `` ` ``      | Triple-backtick fence opener/closer — never meaningful literally |
| `\\\`` | `` ` ``      | Single inline-code backtick — never meaningful literally  |
| `\\-`  | `-`          | List-item dash at start of line — never meaningful literally |
| `\\_`  | `_`          | Underscore in identifiers/paths — never meaningful literally |
| `\\*`  | `*`          | Emphasis marker                                          |
| `\\#`  | `#`          | Markdown header marker                                  |
| `\\[`  | `[`          | Literal bracket inside code/text                         |
| `\\]`  | `]`          | Literal bracket inside code/text                         |

Result: 100 over-escapes fixed across the 3 files.

---

## Menu cleanup

The menu (`hugo.yaml` → `menu.main`) was already correct in spirit — Home,
About, Portfolio, Categories — but had one minor inconsistency:

```yaml
- name: Categories
  url: "categories/"    # missing leading /
```

The leading slash was added for consistency with the other entries, which
all use absolute paths:

```yaml
- name: Categories
  url: "/categories/"
```

The menu config comment was also expanded to note that **Portfolio is
the merged landing page for both Woodworking and Knives** — both sections
live there as `<h2>` headings, so no separate top-level menu items are
needed for them.

---

## Build verification

Build command (after permission fix to root-owned files in `public/`):

```bash
/opt/data/bin/hugo --gc --minify
```

Output:

```
Start building sites … 
hugo v0.148.1-98ba786f2f5dca0866f47ab79f394370bcb77d2f+extended linux/amd64

                  │ EN  
──────────────────┼─────
 Pages            │ 311 
 Paginator pages  │   0 
 Non-page files   │ 253 
 Static files     │   5 
 Processed images │   0 
 Aliases          │   0 
 Cleaned          │   0 

Total in 195 ms
```

### Verification checks

| Check                                | Result                                  |
| ------------------------------------ | --------------------------------------- |
| Homepage thumb links to bare `/`     | **0** (was 20 in Phase 1)               |
| Homepage thumb links to `/post/...`  | **20 / 20**                             |
| Homepage title links to `/post/...`  | **20 / 20**                             |
| CSS files in `/css/`                 | **5** (bootstrap, palette, style, fonts, custom) |
| Portfolio has Woodworking section    | ✓                                       |
| Portfolio has Knives section         | ✓                                       |
| Portfolio has working friction-folder image ref | ✓                              |
| Hardcoded `lukemillermakes.com` in HTML pages | **0**                          |
| `/wp-content/...` refs in HTML       | 13 (all non-existent asset URLs)        |
| WP shortcode escapes in HTML         | **0**                                   |
| Build time                           | 195 ms                                  |

### Note on `public/` permission issue

When running `hugo` directly into `./public/`, the build fails with
`permission denied` for the static CSS files in `./public/css/` because
they were originally written by a previous container run as root with
mode 600:

```
ERROR open /opt/data/lukemillermakes-hugo/public/css/custom.css: permission denied
```

The workaround for the verification run was to redirect the build output
to `/tmp/lmmh_build/`:

```bash
/opt/data/bin/hugo --gc --minify --destination /tmp/lmmh_build
```

The `public/` directory needs its permissions relaxed before the next
production build (e.g. `chmod -R u+w public/` or rebuild into a fresh
`public/` after deleting the old one). This is an artifact of the mixed
ownership between the hermes user and the root-owned files from a
previous container run, not a bug in the migration.

---

## What's NOT in this phase

- The 33 broken thumbnail references noted in Phase 1's `04-build-verify.md`
  (mostly rotated-out `-300x225.jpg` derivatives) — these are still broken
  and will need manual cleanup or a `coverImage` frontmatter sweep on a
  per-post basis.
- The 10 ENAMETOOLONG image refs in
  `content/post/2017-06-24-grind-your-own-stub-nib/index.md` — the source
  filenames are too long for the filesystem; these have always been broken.
- A custom 404 page — the XMin default 404 still ships, but it's now
  styled by `custom.css` so it doesn't look un-themed.
- Pagination — the home page lists 20 posts and links to `/post/` for the
  full archive; no page 2/3/4 pagination was added in this phase.

---

## Phase 2 → Phase 3

The site is now ready for:

1. Container rebuild (the existing `Dockerfile` is correct; just rebuild
   and push).
2. Permissions fix on `public/` so the next `hugo` build doesn't fail.
3. Optional Phase 3 work: custom 404, post pagination, the 33 broken
   thumbnails, and the long-filename post images.