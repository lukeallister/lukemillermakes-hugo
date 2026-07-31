# 10 — CI/CD deploy runbook (Gitea Actions → microos)

How a published post gets from a git push to the live site, and what to check
when it doesn't. Written 2026-07-30 after the deploy path was fixed (it had
never completed successfully before run #16).

## The pipeline, end to end

1. Scan sidecar OCRs a PDF and writes a **draft** page bundle into the
   `blog-content` podman volume on microos (see `09-scan-to-blog-pipeline.md`).
2. You edit the post, set `draft: false`, commit, push to `master` on Gitea
   (`luke/lukemillermakes-hugo`, http://192.168.0.3:3000).
3. Gitea Actions fires `.gitea/workflows/deploy.yml` on the `act_runner`
   (container `gitea-act-runner` on alma9):
   - **validate** — builds the site with `hugomods/hugo:exts`, drafts excluded.
   - **deploy** — `needs: validate`; rsyncs `content/` + config into the microos
     `blog-content` volume over SSH as `hermes`, using `sudo rsync` remotely.
4. `blog-hugo` (running `hugo server --watch`) notices the change and rebuilds
   in ~25 s. The post is then live.

## Verifying a deploy

```bash
source ~/.config/gitea-api.env
R=$GITEA_URL/api/v1/repos/luke/lukemillermakes-hugo

# 1. did the run happen, and what did it conclude?
curl -s -H "Authorization: token $GITEA_TOKEN" "$R/actions/runs?limit=5"

# 2. which job/step failed?
curl -s -H "Authorization: token $GITEA_TOKEN" "$R/actions/runs/<run_id>/jobs"

# 3. full log for the failing job
curl -s -H "Authorization: token $GITEA_TOKEN" "$R/actions/jobs/<job_id>/logs"
```

Then confirm on the target:

```bash
V=/home/hermes/.local/share/containers/storage/volumes/blog-content/_data
ssh hermes@192.168.1.126 "grep -m1 draft $V/content/post/<slug>/index.md; ls -la $V/content/post/<slug>/"
ssh hermes@192.168.1.126 'curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/post/YYYY/MM/DD/<slug>/'
```

**Permalinks are `/post/YYYY/MM/DD/<slug>/`**, not `/post/<slug>/`. Grab the
real href off the homepage rather than guessing. A curl issued while Hugo is
mid-rebuild returns `000` or 404 — wait ~25 s and retry before assuming failure.

## "I pushed and nothing happened"

Almost always it *did* trigger and the run failed. `deploy` has
`needs: validate`, so a failed build leaves deploy `skipped` and the site
unchanged — externally indistinguishable from "no trigger". **Check the runs API
first**, before touching webhooks or the runner.

## Known failure modes

| Symptom in the job log | Cause | Fix |
|---|---|---|
| `error calling partial: partial "footer.html" not found` (points at `layouts/index.html`) | `themes/xmin` submodule not checked out; the partial lives in the theme | `submodules: true` on the **validate** job |
| `exec: "node": executable file not found in $PATH`, `exitcode '127'` | deploy job image has no Node; `actions/checkout@v4` is a Node action | use an image with node |
| `Input 'submodules' not supported when falling back to download using the GitHub REST API` | image has node but no git (e.g. `node:18-alpine`) | `node:18-bullseye` |
| `[/home/hermes/.ssh] is not a valid volume, will be ignored` → `Permission denied` → `Too many authentication failures` | act_runner's `valid_volumes` allowlist dropped the SSH bind mount | runner `config.yaml` with `container.valid_volumes: ['**']` (below) |
| rsync `Permission denied` writing `content/` | volume tree owned by uid 100999 (`blog-hugo`) | already handled: `--rsync-path="sudo rsync" --chown=hermes:hermes` |

Expect a **chain** — each fix exposes the next never-executed step. The real
sequence was #12 → #13 → #14 → #15 → #16 green.

## Runner configuration (alma9)

The SSH key mount only works if act_runner's `valid_volumes` allowlist permits
it. The `GITEA_RUNNER_DOCKER_VALID_VOLUMES` /
`GITEA_RUNNER_RUNNER_DOCKER_VALID_VOLUMES` **environment variables do not work**
(verified on act_runner 0.6.1) — only a mounted config file does.

`/home/luke/gitea/act-runner-config.yaml`:

```yaml
log:
  level: debug
runner:
  capacity: 1
  timeout: 3h
container:
  valid_volumes:
    - "**"
  network: ""
  privileged: false
```

Wired into the `act-runner` service in `/home/luke/gitea/docker-compose.yml`:

```yaml
    environment:
      - CONFIG_FILE=/config.yaml
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./act-runner-config.yaml:/config.yaml:ro
```

Apply and verify (`--project-directory` is required — `/home/luke` is mode 700,
so you cannot `cd` there as hermes):

```bash
sudo docker compose -f /home/luke/gitea/docker-compose.yml \
     --project-directory /home/luke/gitea up -d act-runner
sudo docker exec gitea-act-runner cat /config.yaml | grep -A3 valid_volumes
```

To re-trigger CI after a runner-side (non-repo) change:
`git commit --allow-empty -m "ci: trigger" && git push`.

## Notes

- act_runner streams step logs to the Gitea server, not its own stdout — even at
  debug level. Always read logs via the API, not `docker logs`.
- No Gitea secrets are used for deployment; alma9's `~/.ssh/id_ed25519` is
  mounted read-only into the job container and authorises `hermes@microos`.
- No root SSH login and no chown of live container data — the remote write is
  done with passwordless `sudo rsync` and `--chown=hermes:hermes`.
- Backups taken during this work: `/home/luke/gitea/docker-compose.yml.bak-20260730`
  (alma9) and `Dockerfile.scan.bak-20260730` (microos).
