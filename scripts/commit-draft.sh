#!/usr/bin/env bash
#
# commit-draft.sh — called by the blog-scan pipeline after a scan produces a
# new post. Commits the new draft bundle onto the `drafts` branch and pushes
# `drafts` to Gitea. Publishing (draft:false -> merge drafts -> master) is a
# MANUAL step done by Luke on his workstation.
#
# IMPORTANT: the repo must be seeded once (see setup notes) by fetching
# `master` from Gitea and branching `drafts` from it. This script then only
# ever stages the specific new post bundle — it deliberately does NOT run
# `git add -A`, because the site contains a git submodule (themes/xmin) and
# build artifacts (public/) that must never be re-added wholesale.
#
# Usage: commit-draft.sh POST_BUNDLE_DIR
#   POST_BUNDLE_DIR  path (relative to repo root) of the new post bundle to
#                    commit, e.g. content/post/2026-08-05-synth-case
#
# Auth: relies on git's repo-local credential helper
#   (store --file /home/hermes/.git-credentials) which must contain a line:
#   https://<token>@192.168.0.3:3000/luke/lukemillermakes-hugo.git
#
set -euo pipefail

REPO="/home/hermes/.local/share/containers/storage/volumes/blog-content/_data"
BRANCH="drafts"
REMOTE="origin"
DRY_RUN="${COMMIT_DRAFT_DRY_RUN:-0}"

if [ "$#" -lt 1 ]; then
  echo "usage: commit-draft.sh POST_BUNDLE_DIR" >&2
  exit 2
fi
BUNDLE="$1"

cd "$REPO"

if [ ! -e "$BUNDLE" ]; then
  echo "commit-draft: bundle not found: $BUNDLE" >&2
  exit 3
fi

# Ensure we are on the drafts branch; create it from current HEAD if missing.
CURRENT="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
if [ "$CURRENT" != "$BRANCH" ]; then
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git checkout -q "$BRANCH"
  else
    git checkout -q -b "$BRANCH"
  fi
fi

# Stage ONLY the new post bundle (plus any sidecar files the scan wrote).
git add -- "$BUNDLE"

# Nothing to commit?
if git diff --cached --quiet; then
  echo "commit-draft: no changes staged for $BUNDLE; nothing to do."
  exit 0
fi

MSG="scan: add draft $(basename "$BUNDLE") ($(date '+%Y-%m-%d %H:%M'))"

if [ "$DRY_RUN" = "1" ]; then
  echo "commit-draft [DRY RUN]: would commit with message: $MSG"
  git diff --cached --stat
  exit 0
fi

git commit -q -m "$MSG" >/dev/null 2>&1

# Push drafts to origin. Set upstream on first push.
git push -u "$REMOTE" "$BRANCH" 2>&1

echo "commit-draft: pushed $BRANCH to $REMOTE ($(date '+%Y-%m-%d %H:%M:%S %Z'))"
