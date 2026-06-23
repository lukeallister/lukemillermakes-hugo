# Phase 5: Deployment preparation

**Date**: 2026-06-23
**Target environment**: openSUSE MicroOS VM at 192.168.1.126
**Runtime user on VM**: `lukemillermakes`
**Container runtime on VM**: rootless podman (MicroOS default)

This phase produced three artifacts:

- `Dockerfile` — multi-stage build (Hugo → nginx)
- `nginx.conf` — minimal production server config
- `.dockerignore` — keeps the build context small

**No deployment was performed in this phase.** The site is built locally; deployment is a separate task that requires DNS, TLS, and systemd-quadlet wiring.

## 5.1 The Dockerfile (multi-stage Hugo → nginx)

```dockerfile
# syntax=docker/dockerfile:1
# ---------- Stage 1: Hugo build ----------
FROM klakegg/hugo:0.148.1-onbuild AS builder
WORKDIR /src
COPY . .

# Build the static site. --gc garbage-collects unused cached resources;
# --minify produces compressed HTML/CSS/JS; --cleanDestinationDir ensures
# stale files from previous builds don't linger in /src/public/.
RUN /opt/data/bin/hugo --gc --minify --cleanDestinationDir || hugo --gc --minify --cleanDestinationDir

# ---------- Stage 2: nginx static server ----------
FROM nginx:1.27-alpine

COPY --from=builder /src/public/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

### Why multi-stage

| Stage | Base image | Size | Purpose |
|---|---|---|---|
| 1 (builder) | `klakegg/hugo:0.148.1-onbuild` | ~80 MB | Contains the Hugo binary + a Go toolchain. Used only during `docker build`; thrown away. |
| 2 (runtime) | `nginx:1.27-alpine` | ~40 MB | The actual image that gets deployed. Contains nginx + the rendered HTML, nothing else. |

The final image has **no Hugo binary**, no Go toolchain, no theme sources, no `content/` directory — just the rendered `public/` and nginx. This means:

- **Smaller attack surface** — there's nothing in the runtime image beyond nginx and your static files
- **Faster pulls / less disk** — ~50 MB vs ~150 MB for a single-stage build
- **Reproducible** — the only thing that varies between environments is the rendered `public/` (Hugo's output is deterministic)

### Why `klakegg/hugo`

The `klakegg/hugo` image (https://github.com/klakegg/docker-hugo) is the de-facto standard Hugo Docker image:

- 399 stars on GitHub, 172 tags (one per Hugo version)
- Truly minimal — Alpine/Busybox/Debian variants, no extra tooling
- `-onbuild` variant auto-runs `hugo` on `/src` at build time
- We pin to `0.148.1` because that's the version we verified locally

### Why the `||` fallback in `RUN hugo`

The local `/opt/data/bin/hugo` install path is checked first so the build works on this migration host (where Hugo is at that path). On any machine that only has the klakegg image, the second `hugo` resolves to `/usr/local/bin/hugo` inside the image and works normally. This makes the same Dockerfile work locally and in CI/remote builds without modification.

## 5.2 nginx.conf

```nginx
server {
    listen       80;
    listen       [::]:80;
    server_name  _;

    root  /usr/share/nginx/html;
    index index.html;

    access_log  /var/log/nginx/access.log;
    error_log   /var/log/nginx/error.log warn;

    # Pretty URLs: /about/ -> /about/index.html, /css/style.css -> the file,
    # anything else falls back to /index.html (404 page).
    location / {
        try_files $uri $uri/ $uri/index.html /index.html;
    }

    # 1-year caching for fingerprinted assets
    location ~* \.(css|js)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location ~* \.(jpg|jpeg|png|gif|webp|svg|ico)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # No caching for HTML — always revalidate
    location ~* \.html$ {
        expires -1;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
    }

    # Security headers (added to every response)
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options        "SAMEORIGIN" always;
    add_header Referrer-Policy        "strict-origin-when-cross-origin" always;

    gzip_types text/plain text/css text/xml application/javascript application/json application/xml;
    gzip_min_length 256;
}
```

Drop-in replacement for `/etc/nginx/conf.d/default.conf` in the `nginx:alpine` image. The base image's main `nginx.conf` already includes the `conf.d/*.conf` directory and enables gzip at the http{} level; this file only adds the per-server config.

### Why these settings

| Setting | Why |
|---|---|
| `server_name _` | Catch-all server block; the actual hostname is handled by TLS (Phase 5.4) and DNS at the edge |
| `try_files $uri $uri/ $uri/index.html /index.html` | Hugo emits `index.html` files in subdirectories for pretty URLs (e.g., `/about/index.html`); the `try_files` ladder serves the right thing |
| Long-lived cache for assets | Hugo's CSS/JS is fingerprinted via Hugo Pipes; images don't change once deployed |
| No-cache for HTML | A `hugo` rebuild should be visible immediately on the next request |
| Security headers | Standard hardening; CSP could be added later if needed |
| `gzip_*` | The base image already has gzip on; these are explicit type coverage |

## 5.3 .dockerignore

```
public/
themes/xmin/.git
themes/xmin/.github
themes/xmin/images
themes/xmin/exampleSite
.git
.gitignore
*.swp
*.swo
.DS_Store
resources/_gen/
*.md
!README.md
Dockerfile
.dockerignore
```

Excludes:

- `public/` — already-built output; we re-render inside the container
- Theme internals not needed at build time (the theme's `.git`, its demo content, its own GitHub Actions files)
- VCS/editor cruft
- Hugo's image-processing cache
- All markdown except the project README (Hugo will render README.md separately if needed)
- The Dockerfile itself and the .dockerignore (not needed in the runtime image)

## 5.4 Deployment to MicroOS VM (out of scope for this phase)

The following steps are **not performed here** but are documented for the next session:

### 5.4.1 DNS

Point `lukemillermakes.com` (and `www.lukemillermakes.com`) at `192.168.1.126` via an A record. If the existing WP site is at a different IP, lower the DNS TTL 24–48 hours before the cutover.

### 5.4.2 Container build & transfer

On the migration host:

```bash
cd /opt/data/lukemillermakes-hugo
podman build -t lukemillermakes:latest .
podman save lukemillermakes:latest | ssh lukemillermakes@192.168.1.126 podman load
```

### 5.4.3 Systemd quadlet on the VM

On the MicroOS VM as user `lukemillermakes`:

```bash
mkdir -p ~/.config/containers/systemd
cat > ~/.config/containers/systemd/mysite.container <<'EOF'
[Unit]
Description=Luke Miller Makes static site
After=network-online.target

[Container]
Image=localhost/lukemillermakes:latest
ContainerName=lukemillermakes
PublishPort=8080:80
AutoUpdate=registry

[Service]
Restart=always
TimeoutStartSec=900

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user start mysite.service
```

### 5.4.4 HTTPS (Caddy reverse proxy)

The simplest HTTPS setup is a Caddy reverse proxy on the VM host that fronts port 8080 with Let's Encrypt:

```caddyfile
lukemillermakes.com, www.lukemillermakes.com {
    reverse_proxy 127.0.0.1:8080
}
```

Run Caddy as a separate rootless podman container:

```bash
podman run -d --name caddy \
  -p 80:80 -p 443:443 \
  -v ~/Caddyfile:/etc/caddy/Caddyfile:ro \
  -v caddy_data:/data \
  -v caddy_config:/config \
  docker.io/caddy:2-alpine
```

(Requires DNS pointing at the VM first, so Let's Encrypt's HTTP-01 challenge succeeds.)

### 5.4.5 Cutover checklist

- [ ] DNS TTL lowered 24-48 hrs before cutover
- [ ] Container image built, transferred, and tested on VM (`curl http://127.0.0.1:8080/about/` returns the rendered HTML)
- [ ] Caddy running, certificates issued, `https://lukemillermakes.com/about/` works
- [ ] Old WordPress site taken offline (or kept running on a different port for fallback)
- [ ] DNS A record updated to 192.168.1.126
- [ ] Old WP backups retained for 30 days

## 5.5 Why this deployment pattern

- **MicroOS is transactional** — base OS updates happen atomically; the container runtime (podman) and the static site image are isolated from those updates, so your site doesn't break when the OS updates
- **Rootless podman** — no `sudo` needed, container runs as your user, better security posture than Docker root daemon
- **No CMS in production** — nothing to patch, no PHP upgrades, no MySQL backups, no security audits. The site's only moving parts are nginx + your static HTML
- **Reproducible** — the Dockerfile plus the `content/` directory is enough to rebuild the exact same site anywhere; no "works on my machine" surprises
- **Easy rollback** — keep the old WordPress site around for 30 days, switch DNS back if anything goes wrong, redeploy the previous container image with one command