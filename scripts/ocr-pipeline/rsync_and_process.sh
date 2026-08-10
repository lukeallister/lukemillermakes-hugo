#!/bin/bash
# rsync_and_process.sh — pulls new PDFs from the Synology NAS, then runs the
# pipeline on anything new in /inbox. After a successful scan, it enqueues the
# newly-created draft bundle path into /site/.scan-commit-queue so the host
# systemd timer (scan-commit-drain) commits + pushes it to Gitea `drafts`.
#
# The rsync URL is configurable via the SCAN_NAS_URL env var. The password file
# is bind-mounted at /etc/rsyncd.password.

set -uo pipefail

REPO="/site"
QUEUE="$REPO/.scan-commit-queue"

# ---- 1. rsync pull from Synology ------------------------------------------
NAS_URL="${SCAN_NAS_URL:-rsync://SYNOLOGY_HOST/blog-scans/}"
RSYNC_PASSWORD_FILE="${SCAN_RSYNC_PASSWORD_FILE:-/etc/rsyncd.password}"

if [[ -f "$RSYNC_PASSWORD_FILE" ]]; then
    RSYNC_PASSWORD_ARG="--password-file=$RSYNC_PASSWORD_FILE"
else
    RSYNC_PASSWORD_ARG=""
    echo "[rsync_and_process] WARNING: no password file at $RSYNC_PASSWORD_FILE; trying anonymous"
fi

echo "[rsync_and_process] pulling from $NAS_URL"
if rsync -avz --include='*/' --include='*.pdf' --exclude='*' \
        $RSYNC_PASSWORD_ARG \
        "$NAS_URL" /inbox/ 2>&1; then
    echo "[rsync_and_process] rsync ok"
else
    echo "[rsync_and_process] rsync failed (exit $?); skipping pipeline run"
    exit 1
fi

# ---- 2. process any new PDFs ---------------------------------------------
# Run the scan. NOTE: run (do not `exec`) so we can enqueue the result after.
/usr/local/bin/scan_to_post.py \
    --inbox      /inbox \
    --processed  /processed \
    --failed     /failed \
    --content    /site/content \
    --state      /var/lib/scan/.processed.json
SCAN_RC=$?

if [ "$SCAN_RC" -ne 0 ]; then
    echo "[rsync_and_process] scan_to_post.py exited $SCAN_RC; not enqueuing"
    exit "$SCAN_RC"
fi

# ---- 3. enqueue the newest draft bundle for the drain timer --------------
# Find the most-recently-modified post bundle created by this scan and queue it.
# (scan_to_post.py writes bundles to /site/content/post/<slug>/.)
NEW_BUNDLE="$(find /site/content/post -maxdepth 1 -mindepth 1 -type d \
    -newermt '-15 minutes' 2>/dev/null | sort | tail -1)"

if [ -z "$NEW_BUNDLE" ]; then
    echo "[rsync_and_process] no new bundle detected; nothing to enqueue"
    exit 0
fi

# Make the queue path relative to the repo root, matching commit-draft.sh usage.
REL="${NEW_BUNDLE#/site/}"
# De-duplicate: only append if not already in the queue.
if [ -f "$QUEUE" ] && grep -qxF "$REL" "$QUEUE" 2>/dev/null; then
    echo "[rsync_and_process] $REL already queued; skipping"
else
    echo "$REL" >> "$QUEUE"
    echo "[rsync_and_process] enqueued $REL for commit-draft (drain timer will push to Gitea drafts)"
fi
