# Phase 8: Deployment runbook

**Target**: openSUSE MicroOS VM at `192.168.1.126`
**Runtime user on VM**: `lukemillermakes`
**Container runtime**: rootless podman (MicroOS default)
**Site image**: `localhost/lukemillermakes:latest` — multi-stage `klakegg/hugo:0.148.1-onbuild` → `nginx:1.27-alpine` (see `Dockerfile`, ~50 MB final image)
**Service port**: `8080` (mapped to container's `80`)

This runbook consolidates the deployment path. The full procedure, including the Dockerfile's design rationale and nginx config, lives in:

- `05-deployment-prep.md` — Dockerfile + nginx.conf + initial deploy sketch
- `/opt/data/plans/2026-06-23-0945-wp-to-hugo-docker.md` Tasks 9–13 — task-by-task build, transfer, deploy, verify

Read those first if anything in here is unclear. This file is the **operational quick-path**.

## 8.1 Why port 8080 (rootless caveat)

Rootless podman **cannot bind to ports < 1024** without extra work. Options:

| Option | Cost | Verdict |
|---|---|---|
| Run on 8080 + front with a reverse proxy (Caddy / nginx host) | One extra container | **Recommended for v1** |
| Lower `net.ipv4.ip_unprivileged_port_start=80` | Requires `sudo transactional-update` on MicroOS, survives reboots | Avoid until you need it |

This runbook sticks to port 8080. Put a Caddy reverse proxy in front of it for HTTPS once DNS is pointed at the VM (see `05-deployment-prep.md` §5.4.4).

## 8.2 Build the image on the VM (one-shot)

We **build on the VM directly** rather than transferring a built image. The VM has 78 GB free; the build context is small; and a built image transfer (`podman save | ssh | podman load`) is just more moving parts.

```bash
# From the migration host:
rsync -avz --delete \
  --exclude='.git' --exclude='public' --exclude='resources' \
  --exclude='public_v2' \
  -e ssh \
  /opt/data/lukemillermakes-hugo/ \
  lukemillermakes@192.168.1.126:~/site/
```

Then on the VM:

```bash
ssh lukemillermakes@192.168.1.126
cd ~/site
podman build -t lukemillermakes:latest .
# expect: STEP ... nginx:1.27-alpine → DONE (≈50 MB image)
podman images | grep lukemillermakes
```

If you prefer to build the image locally and transfer it (faster rebuilds on a beefy host), use the `podman save | ssh ... podman load` pattern from `05-deployment-prep.md` §5.4.2.

## 8.3 Run the container (manual, for first-boot smoke test)

```bash
ssh lukemillermakes@192.168.1.126
podman run -d --name lukemillermakes \
  -p 8080:80 \
  --restart=always \
  localhost/lukemillermakes:latest

# verify:
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/about/
# expect: 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/nonexistent
# expect: 404
podman logs lukemillermakes | tail -20
# expect: nginx access lines, no errors
```

If all three pass, stop the manual container and switch to the systemd unit:

```bash
podman stop lukemillermakes
podman rm   lukemillermakes
```

## 8.4 Systemd quadlet (auto-start at boot)

MicroOS uses systemd, and podman integrates via **quadlet** — a unit file that describes a container and gets transpiled into a systemd service at `daemon-reload` time.

Create the quadlet on the VM:

```bash
ssh lukemillermakes@192.168.1.126

mkdir -p ~/.config/containers/systemd

cat > ~/.config/containers/systemd/lukemillermakes.container <<'EOF'
[Unit]
Description=Luke Miller Makes static site (Hugo → nginx)
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
systemctl --user start lukemillermakes.service
```

### 8.4.1 Enable linger (critical)

Without linger, the user service only runs while `lukemillermakes` is logged in. **Linger keeps user services alive across reboots even with no active session.**

```bash
# Check whether linger is already on:
loginctl show-user lukemillermakes | grep Linger
# expect: Linger=yes

# If not:
sudo loginctl enable-linger lukemillermakes
```

Then enable the service to start at boot:

```bash
systemctl --user enable lukemillermakes.service
systemctl --user status lukemillermakes.service
# expect: Active: active (running)
```

> **Why not `podman generate systemd`?** The plan (Task 12) suggests `podman generate systemd --files --new`. That works, but the generated unit is verbose and ties you to the container name. A hand-written quadlet is six lines and portable.

## 8.5 Verify the live site

After the quadlet is enabled and started:

```bash
# From the VM:
curl -s -o /dev/null -w "Homepage: %{http_code}\n" http://127.0.0.1:8080/
curl -s -o /dev/null -w "About:    %{http_code}\n" http://127.0.0.1:8080/about/
curl -s -o /dev/null -w "Post:     %{http_code}\n" \
  http://127.0.0.1:8080/post/2024/08/15/2024-08-15-i-didnt-need-all-those-keys-anyway/
curl -s -o /dev/null -w "404:      %{http_code}\n" http://127.0.0.1:8080/nope

# From your workstation (LAN):
curl -s -o /dev/null -w "%{http_code}\n" http://192.168.1.126:8080/
```

Expected: `200`, `200`, `200`, `404`. If the post URL 404s, your permalink pattern in `hugo.yaml` (`/post/:year/:month/:day/:slug/`) doesn't match the URL you tested — fix the test URL, not the config.

## 8.6 Updating the site (publish workflow)

For each new post (see `how-to-write-a-new-post.md`):

```bash
# 1. edit content on the migration host
cd /opt/data/lukemillermakes-hugo
# write new content/post/YYYY-MM-DD-slug/index.md (+ images/)

# 2. preview locally (optional)
/opt/data/bin/hugo server -D
# browse http://localhost:1313

# 3. sync to VM and rebuild
rsync -avz --delete \
  --exclude='.git' --exclude='public' --exclude='resources' \
  -e ssh /opt/data/lukemillermakes-hugo/ \
  lukemillermakes@192.168.1.126:~/site/

ssh lukemillermakes@192.168.1.126 '
  cd ~/site &&
  podman build -t lukemillermakes:latest . &&
  systemctl --user restart lukemillermakes.service
'

# 4. verify
curl -s -o /dev/null -w "%{http_code}\n" http://192.168.1.126:8080/post/.../
```

Future: once the project lives in git, replace steps 3–4 with a CI pipeline that pushes the new image to the VM (see Long-term notes in `00-SUMMARY.md`).

## 8.7 Quick troubleshoot

### Container won't start

```bash
podman ps -a                  # see exit code + status
podman logs lukemillermakes   # last 50 lines
journalctl --user -u lukemillermakes.service
```

Common causes:

| Symptom | Cause | Fix |
|---|---|---|
| `Error: image not found` | Image not built on VM yet | `podman build -t lukemillermakes:latest .` |
| `Error: port already in use` | Another container (or the manual run from §8.3) is still bound | `podman ps -a` → `podman rm -f <name>` |
| `permission denied` on port 8080 | Some other process owns it | `ss -tlnp 'sport = :8080'` |

### Port 8080 already in use

```bash
ss -tlnp 'sport = :8080'           # find the PID
podman ps -a                       # or check if it's a stray container
podman rm -f lukemillermakes       # remove duplicate container
```

If you need to move the port, change `PublishPort=8080:80` in the `.container` quadlet and reload:

```bash
systemctl --user daemon-reload
systemctl --user restart lukemillermakes.service
```

### Linger not enabled (service dies on logout/reboot)

```bash
loginctl show-user lukemillermakes | grep Linger
# if Linger=no:
sudo loginctl enable-linger lukemillermakes
# verify:
loginctl show-user lukemillermakes | grep Linger
# expect: Linger=yes
systemctl --user restart lukemillermakes.service
```

### Quadlet reload doesn't pick up changes

```bash
# After editing the .container file:
systemctl --user daemon-reload
systemctl --user restart lukemillermakes.service
systemctl --user status lukemillermakes.service
```

### Image is stale (changes don't appear)

```bash
# On the VM:
podman images | grep lukemillermakes
# If the timestamp is older than your last build:
podman build -t lukemillermakes:latest . --no-cache
systemctl --user restart lukemillermakes.service
```

### Reclaim disk (caches + dangling images)

```bash
podman image prune -f
podman build cache prune    # klakegg/hugo layers accumulate
```

## 8.8 DNS + HTTPS (post-deploy, not blocking)

The container is reachable at `http://192.168.1.126:8080/` immediately. To make it the public site:

1. **DNS** — point `lukemillermakes.com` (and `www`) at `192.168.1.126` (A record). Lower TTL 24–48 hrs before cutover.
2. **HTTPS** — run a Caddy container on the host that listens on 80/443 and reverse-proxies to 127.0.0.1:8080. See `05-deployment-prep.md` §5.4.4 for the Caddyfile + `podman run` invocation. Caddy auto-issues Let's Encrypt certs once DNS resolves.
3. **Cutover** — flip DNS; wait for TTL; verify `curl -I https://lukemillermakes.com/about/` returns 200; keep the old WP site around for 30 days as a fallback.

## 8.9 Rollback

| Layer | Rollback action |
|---|---|
| New post broke the build | `git revert <commit>` (or just delete the file), `podman build`, `systemctl --user restart` |
| Container is misbehaving | `systemctl --user stop lukemillermakes.service` (site goes offline, DNS still resolves) |
| Whole VM unreachable | DNS still points to old WP if you keep it running on a separate port; flip the A record back |
| Need a known-good image | Re-tag the previous build: `podman tag <sha> localhost/lukemillermakes:latest` |