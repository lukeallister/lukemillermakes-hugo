# How to write a new post manually

The site lives at `/opt/data/lukemillermakes-hugo/`. Every post is a **page bundle** — a folder holding the markdown file and its images.

## Directory structure

```
content/
├── post/                          # blog posts live here
│   └── YYYY-MM-DD-slug/           # one folder per post
│       ├── index.md               # the post
│       └── images/                # any images for this post
└── page/                          # standalone pages (about, portfolio, …)
```

The folder name `YYYY-MM-DD-slug` becomes the URL: `https://lukemillermakes.com/post/YYYY/MM/DD/slug/`.

## Front matter

Every `index.md` starts with YAML between `---` markers:

```markdown
---
title: "My New Post"
date: 2026-06-23T15:00:00.000Z
draft: true
categories: ["tech"]
tags: ["tech", "diy"]
---

Post body goes here. Markdown works as expected.
```

`title` is quoted plain text. `date` must be **RFC 3339 with timezone** (e.g. `2026-06-23T15:00:00.000Z` — the `.000Z` matters). `draft: true` hides the post; `draft: false` (or delete the line) publishes it. `categories` and `tags` are optional lists; use what's already on the site (peek at a sibling post).

## Images

Drop the file in the post's `images/` subdir, then reference it with a **page-bundle relative path**: `![alt](images/photo.jpg)`. Don't use absolute paths or `/post/.../images/` URLs.

## Preview locally

```bash
cd /opt/data/lukemillermakes-hugo
/opt/data/bin/hugo server --buildDrafts
```

Open http://localhost:1313/ — drafts are included because of `--buildDrafts`. No local Hugo? Use Docker:

```bash
docker run --rm -p 1313:1313 -v "$(pwd)":/src klakegg/hugo:ext-alpine server --bind 0.0.0.0 --buildDrafts
```

## Worked example

```bash
cd /opt/data/lukemillermakes-hugo
mkdir -p content/post/2026-06-23-my-new-post/images

cat > content/post/2026-06-23-my-new-post/index.md <<'EOF'
---
title: "My New Post"
date: 2026-06-23T15:00:00.000Z
draft: true
categories: ["tech"]
tags: ["diy"]
---

This is the body. Write in markdown.

![caption](images/photo.jpg)
EOF

# Preview at http://localhost:1313/post/2026/06/23/my-new-post/
/opt/data/bin/hugo server --buildDrafts

# Publish: flip the draft flag, commit, rebuild, ship
sed -i 's/draft: true/draft: false/' content/post/2026-06-23-my-new-post/index.md
git add content/post/2026-06-23-my-new-post/ && git commit -m "post: my new post" && git push
# then follow 08-deployment-runbook.md §8.6
```
One folder, one file, one image directory — that's the whole pattern.