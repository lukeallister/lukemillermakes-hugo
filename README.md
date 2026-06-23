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