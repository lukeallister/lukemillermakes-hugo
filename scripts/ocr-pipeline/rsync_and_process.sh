#!/bin/bash
# rsync_and_process.sh — pulls new PDFs from the Synology NAS, then runs the
# pipeline on anything new in /inbox.
#
# Two URL styles are supported via the SCAN_NAS_URL env var:
#
#   rsync://user@host/module/path/    — daemon-style rsync
#                                          auth via --password-file
#                                          (uses /etc/rsyncd.password)
#
#   user@host:/path/                  — SSH-style rsync
#                                          auth via SSH_ASKPASS reading
#                                          /etc/rsyncd.password (same file
#                                          carries the SSH password)
#
# Password file location is /etc/rsyncd.password by default (overridable via
# SCAN_RSYNC_PASSWORD_FILE).

set -uo pipefail

# ---- 1. rsync pull from Synology ------------------------------------------
NAS_URL="${SCAN_NAS_URL:-autobot@192.168.0.160:/volume1/NAS/blog-scans/}"
RSYNC_PASSWORD_FILE="${SCAN_RSYNC_PASSWORD_FILE:-/etc/rsyncd.password}"

if [[ ! -f "$RSYNC_PASSWORD_FILE" ]]; then
    echo "[rsync_and_process] ERROR: password file $RSYNC_PASSWORD_FILE missing" >&2
    exit 1
fi

run_rsync() {
    if [[ "$NAS_URL" =~ ^rsync:// ]]; then
        # Daemon-style: --password-file feeds rsync directly.
        echo "[rsync_and_process] rsync daemon pull from $NAS_URL"
        rsync -avz --include='*/' --include='*.pdf' --exclude='*' \
            --password-file="$RSYNC_PASSWORD_FILE" \
            "$NAS_URL" /inbox/
    else
        # SSH-style: use SSH_ASKPASS to feed the autobot password from the
        # bind-mounted password file. ssh + rsync are both in the blog-scan
        # image; see blog-scan/Containerfile.
        echo "[rsync_and_process] SSH pull from $NAS_URL"
        # shellcheck disable=SC2086
        SSH_ASKPASS=/usr/local/bin/scan_askpass.sh \
        DISPLAY=:0 \
        setsid -w \
        rsync -avz --include='*/' --include='*.pdf' --exclude='*' \
            -e "ssh -o BatchMode=no -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null" \
            "$NAS_URL" /inbox/
    fi
}

echo "[rsync_and_process] pulling from $NAS_URL"
if run_rsync; then
    echo "[rsync_and_process] rsync ok"
else
    rc=$?
    echo "[rsync_and_process] rsync failed (exit $rc); skipping pipeline run"
    exit "$rc"
fi

# ---- 2. process any new PDFs ----------------------------------------------
exec /usr/local/bin/scan_to_post.py \
    --inbox      /inbox \
    --processed  /processed \
    --failed     /failed \
    --content    /site/content \
    --state      /var/lib/scan/.processed.json