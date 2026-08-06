# lukemillermakes-hugo

Hugo project for [lukemillermakes.com](https://lukemillermakes.com), migrated
from WordPress in June 2026.

## Stack

- **Hugo** `0.148.1+extended` (the xmin theme requires ≥ 0.146)
- **Theme**: [xmin](https://github.com/yihui/hugo-xmin) by Yihui Xie (~137 lines total)
- **Content**: 62 published posts + 3 published pages (about, portfolio, passwords)

## Build

```bash
/opt/data/bin/hugo --gc --minify
# or, on a fresh machine with klakegg/hugo:
hugo --gc --minify
```

Output goes to `./public/` (≈43 MB, 313 rendered HTML pages + 270 image files).

## Local preview

```bash
/opt/data/bin/hugo server -D
# then visit http://localhost:1313
```

The `-D` flag includes drafts.

## Container build & run

```bash
podman build -t lukemillermakes:latest .
podman run --rm -p 8080:80 lukemillermakes:latest
# then visit http://localhost:8080
```

See `Dockerfile` (multi-stage: klakegg/hugo builder → nginx:alpine server,
final image ≈50 MB, no Hugo binary in production).

## Directory layout

```
.
├── Dockerfile            # multi-stage: Hugo → nginx
├── nginx.conf            # minimal production config (gzip, cache, security headers)
├── hugo.yaml             # site config (menu, permalinks, params)
├── content/
│   ├── post/             # 63 post bundles (index.md + images/)
│   └── page/             # 5 published pages + 1 _drafts/ subfolder
├── layouts/
│   ├── index.html        # custom home page override
│   └── _partials/
│       └── header.html   # .Site.Language.Locale → .Site.LanguageCode fix
├── themes/xmin/          # vendored theme
└── public/               # rendered output (build artifact)
```

## Migration notes

See `/opt/data/documentation/wp-to-hugo/` for the full phase-by-phase record:

- `01-recon.md` – source XML analysis
- `02-migration.md` – `lonekorean/wordpress-export-to-markdown` run
- `03-hugo-setup.md` – theme + config choices
- `04-build-verify.md` – build output + verification commands
- `05-deployment-prep.md` – Dockerfile, nginx, MicroOS deployment plan
- `00-SUMMARY.md` – capstone summary

## Known issues carried over from migration

- **10 broken image refs** in the very first post (`2017-06-24-grind-your-own-stub-nib`):
  the source URLs were base64-style Google user-content filenames > 255 chars;
  filesystem rejected them with `ENAMETOOLONG`. The post body still references
  them, so they render as broken images. Fix manually if desired.
- **33 missing thumbnails** across various posts (404 from the live WP media
  library, mostly rotated-out `-300x225.jpg` derivatives). Parent full-resolution
  images are present; the post renders fine, just with a few smaller images missing.
## Content workflow: the `drafts` branch

The blog-content volume on the blog host (MicroOS, `192.168.1.126`) is a git
worktree tracking this repo on Gitea (`luke/lukemillermakes-hugo`, HTTP on
`:3000`; Gitea SSH `:2222` is localhost-only on the Gitea host, so pushes go
over HTTP with a token in `~/.git-credentials`).

Two branches:

- **`master`** — the published site. Only touched when you publish. Pushing
  `master` fires Gitea Actions (`.gitea/workflows/deploy.yml`), which builds
  Hugo and rsyncs into the blog-content volume; the Hugo servers then render it
  (`:8080` PROD / `:8081` STAGE with drafts).
- **`drafts`** — where new posts land automatically. Every scanned post is
  committed here as `draft: true`.

### Writing a post by hand

```bash
git checkout drafts
# ... edit or add content/post/YYYY-MM-DD-slug/index.md (draft: true) ...
git add content/post/YYYY-MM-DD-slug
git commit -m "draft: YYYY-MM-DD-slug"
git push origin drafts
```

### Publishing

1. Edit the draft on the `drafts` branch (or locally after `git checkout drafts`).
2. Set `draft: false` in its `index.md`.
3. Merge `drafts` into `master` and push `master`:
   ```bash
   git checkout master
   git merge drafts
   git push origin master
   ```
   Gitea Actions deploys it. The post is then live.

Do **not** edit `master` directly for new drafts; keep `drafts` as the working
branch so the automated scan commits and your manual edits dont collide.

## Content workflow: the `drafts` branch

The blog-content volume on the blog host (MicroOS, `192.168.1.126`) is a git
worktree tracking this repo on Gitea (`luke/lukemillermakes-hugo`, HTTP on
`:3000`; Gitea SSH `:2222` is localhost-only on the Gitea host, so pushes go
over HTTP with a token in `~/.git-credentials`).

Two branches:

- **`master`** — the published site. Only touched when you publish. Pushing
  `master` fires Gitea Actions (`.gitea/workflows/deploy.yml`), which builds
  Hugo and rsyncs into the blog-content volume; the Hugo servers then render it
  (`:8080` PROD / `:8081` STAGE with drafts).
- **`drafts`** — where new posts land automatically. Every scanned post is
  committed here as `draft: true`.

### Writing a post by hand

```bash
git checkout drafts
# ... edit or add content/post/YYYY-MM-DD-slug/index.md (draft: true) ...
git add content/post/YYYY-MM-DD-slug
git commit -m "draft: YYYY-MM-DD-slug"
git push origin drafts
```

### Publishing

1. Edit the draft on the `drafts` branch (or locally after `git checkout drafts`).
2. Set `draft: false` in its `index.md`.
3. Merge `drafts` into `master` and push `master`:

   ```bash
   git checkout master
   git merge drafts
   git push origin master
   ```

   Gitea Actions deploys it. The post is then live.

Do **not** edit `master` directly for new drafts; keep `drafts` as the working
branch so the automated scan commits and your manual edits don't collide.

### The scan pipeline commits for you

The OCR scan pipeline (a separate application, see below) writes each scanned
post into `content/post/` and auto-commits it to the `drafts` branch, then
pushes to Gitea. You don't need to `git add`/`git commit` scanned drafts by
hand; just publish them when ready using the steps above.

## Scan-to-blog pipeline (separate application)

The paper-scan to Hugo-draft pipeline is **not** part of this repo. It lives in
its own repository, `luke/scan-to-blog-pipeline` on Gitea, with its own
`README.md`, `ARCHITECTURE.md`, and `OPS.md`.

In short: a scanned PDF (named `YYYYMMDD_slug.pdf`) is dropped on a NAS share,
pulled into the `blog-scan` container, OCRed, and written as a Hugo page bundle
(`index.md` + `images/`) with `draft: true`. The container then queues the new
bundle; a host-side job commits it to the `drafts` branch of this repo and
pushes. From there the publish flow above takes over.

See `scan-to-blog-pipeline` for the full design, the `commit-draft.sh` and
`scan-commit-drain` mechanics, and operational runbooks.
