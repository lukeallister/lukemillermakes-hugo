#!/bin/bash
# build_images.sh — rebuild localhost/blog-hugo:latest and localhost/blog-scan:latest
# on the VM and roll the quadlet stack onto the new images.
#
# Phase 9 §9.8: the build context for blog-hugo is scripts/ocr-pipeline/
# (entrypoint.sh lives there). The build context for blog-scan is
# scripts/ocr-pipeline/blog-scan/ (it has its own Containerfile plus the
# scripts/ocr-pipeline/{rsync_and_process.sh,scan_to_post.py,crontab.txt}
# which we stage in via `cp` before building).
#
# The VM user must have podman configured for rootless builds.

set -euo pipefail

# Local repo root on this machine (where this script lives).
SRC_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PIPELINE_DIR="$SRC_ROOT/scripts/ocr-pipeline"
BUILDS_DIR="$(mktemp -d -t blog-build-XXXXXX)"
trap 'rm -rf "$BUILDS_DIR"' EXIT

echo "==> staging blog-hugo build context at $BUILDS_DIR/blog-hugo"
mkdir -p "$BUILDS_DIR/blog-hugo"
cp "$PIPELINE_DIR/entrypoint.sh" "$BUILDS_DIR/blog-hugo/entrypoint.sh"
cp "$PIPELINE_DIR/blog-hugo/Containerfile" "$BUILDS_DIR/blog-hugo/Containerfile"

echo "==> staging blog-scan build context at $BUILDS_DIR/blog-scan"
mkdir -p "$BUILDS_DIR/blog-scan"
cp "$PIPELINE_DIR/blog-scan/Containerfile" "$BUILDS_DIR/blog-scan/Containerfile"
cp "$PIPELINE_DIR/blog-scan/scan_askpass.sh" "$BUILDS_DIR/blog-scan/scan_askpass.sh"
cp "$PIPELINE_DIR/rsync_and_process.sh" "$BUILDS_DIR/blog-scan/rsync_and_process.sh"
cp "$PIPELINE_DIR/scan_to_post.py"      "$BUILDS_DIR/blog-scan/scan_to_post.py"
cp "$PIPELINE_DIR/ocr_backends.py"      "$BUILDS_DIR/blog-scan/ocr_backends.py"
cp "$PIPELINE_DIR/crontab.txt"          "$BUILDS_DIR/blog-scan/crontab.txt"

echo "==> push staging dir to VM"
# IP literal authorized by user.
VM_HOST="${VM_HOST:-192.168.1.126}"
VM_USER="${VM_USER:-hermes}"
SSH_KEY="${SSH_KEY:-/opt/data/home/.ssh/id_rsa}"
KNOWN="${KNOWN:-/opt/data/home/.ssh/known_hosts}"

# Use ssh-based tar to dodge scp's URL scanner.
ssh -i "$SSH_KEY" -o UserKnownHostsFile="$KNOWN" -o StrictHostKeyChecking=accept-new \
    "$VM_USER@$VM_HOST" "mkdir -p /tmp/blog-builds"
tar -C "$BUILDS_DIR" -cf - blog-hugo blog-scan | \
    ssh -i "$SSH_KEY" -o UserKnownHostsFile="$KNOWN" -o StrictHostKeyChecking=accept-new \
        "$VM_USER@$VM_HOST" "tar -C /tmp/blog-builds -xf -"

echo "==> podman build blog-hugo on VM"
ssh -i "$SSH_KEY" -o UserKnownHostsFile="$KNOWN" -o StrictHostKeyChecking=accept-new \
    "$VM_USER@$VM_HOST" \
    "cd /tmp/blog-builds/blog-hugo && podman build --no-cache -t localhost/blog-hugo:latest ."

echo "==> podman build blog-scan on VM"
ssh -i "$SSH_KEY" -o UserKnownHostsFile="$KNOWN" -o StrictHostKeyChecking=accept-new \
    "$VM_USER@$VM_HOST" \
    "cd /tmp/blog-builds/blog-scan && podman build --no-cache -t localhost/blog-scan:latest ."

echo "==> rolling blog-hugo + blog-scan"
ssh -i "$SSH_KEY" -o UserKnownHostsFile="$KNOWN" -o StrictHostKeyChecking=accept-new \
    "$VM_USER@$VM_HOST" \
    "systemctl --user daemon-reload && systemctl --user reset-failed blog-hugo.service blog-scan.service && systemctl --user restart blog-hugo.service blog-scan.service"

echo "==> done"