#!/bin/bash
# rsync_and_process.sh — pulls new PDFs from the Synology NAS, then runs the
# pipeline on anything new in /inbox.
#
# The rsync URL is configurable via the SCAN_NAS_URL env var. The password file
# is bind-mounted at /etc/rsyncd.password.

set -uo pipefail

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

# ---- 2. process any new PDFs ----------------------------------------------
exec /usr/local/bin/scan_to_post.py \
    --inbox      /inbox \
    --processed  /processed \
    --failed     /failed \
    --content    /site/content \
    --state      /var/lib/scan/.processed.json