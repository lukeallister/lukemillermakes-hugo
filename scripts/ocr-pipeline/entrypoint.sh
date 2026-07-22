#!/bin/bash
# entrypoint.sh — launches two hugo server processes.
#
# PROD (port 8080): published content only. Public-facing via Caddy.
# STAGE (port 8081): includes drafts. LAN-only.
#
# Both watch /site/content via Hugo's --watch (default on hugo server).
# When the scan sidecar writes a new content/post/.../index.md with
# `draft: true`, STAGE rebuilds and renders it; PROD ignores it until
# the user flips draft: false. No `podman build` cycle is ever needed.

set -euo pipefail

# Make Hugo logs distinguishable in `podman logs` output.
export HUGO_BASEURL="https://lukemillermakes.com/"

echo "[entrypoint] starting PROD hugo server on :8080 (published only)"
# IMPORTANT: hugo server's DEFAULT is --buildDrafts=true regardless of
# hugo.yaml's buildDrafts:false. We must pass --buildDrafts=false explicitly
# so prod does not leak drafts to the public site.
hugo server \
  --source /site \
  --port 8080 \
  --bind 0.0.0.0 \
  --watch \
  --buildDrafts=false \
  --renderToMemory \
  --logLevel info \
  &

PROD_PID=$!

echo "[entrypoint] starting STAGE hugo server on :8081 (drafts enabled)"
hugo server \
  --source /site \
  --port 8081 \
  --bind 0.0.0.0 \
  --watch \
  --buildDrafts \
  --renderToMemory \
  --logLevel info \
  &

STAGE_PID=$!

# Trap signals and forward to both children.
trap 'echo "[entrypoint] shutting down"; kill "$PROD_PID" "$STAGE_PID" 2>/dev/null || true; exit 0' \
  SIGTERM SIGINT

echo "[entrypoint] prod pid=$PROD_PID stage pid=$STAGE_PID; waiting"
wait -n
EXIT=$?

# If one exits, clean up the other.
kill "$PROD_PID" "$STAGE_PID" 2>/dev/null || true
exit "$EXIT"