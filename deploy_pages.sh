#!/usr/bin/env bash
# Publish web/ to the gh-pages branch.
#
# Eric runs this by hand — it is not wired into CI and Claude does not
# execute it. Deploying a public site is a one-way door (the branch's history
# becomes GitHub Pages' serving history) and belongs to a human decision, not
# a build step.
#
# What it does: builds web/ fresh from the current exports/srd/ (so a stale
# checkout can't get published), then makes gh-pages' tree identical to web/
# via a separate git worktree — no history rewriting, no force-push, one
# ordinary commit per deploy.
#
# Usage:
#   ./deploy_pages.sh              # build + publish
#   ./deploy_pages.sh --no-build   # publish the web/ tree as it stands
#   ./deploy_pages.sh --push       # also push gh-pages to origin

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

DO_BUILD=1
DO_PUSH=0
for arg in "$@"; do
  case "$arg" in
    --no-build) DO_BUILD=0 ;;
    --push) DO_PUSH=1 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

if [ "$DO_BUILD" = "1" ]; then
  echo "== building web/ from exports/srd/ =="
  python3 src/build_web.py
fi

if [ ! -d web ] || [ -z "$(ls -A web 2>/dev/null)" ]; then
  echo "web/ is missing or empty — nothing to publish" >&2
  exit 1
fi

WORKTREE_DIR="$(mktemp -d)"
trap 'git worktree remove --force "$WORKTREE_DIR" >/dev/null 2>&1 || true; rm -rf "$WORKTREE_DIR"' EXIT

if git show-ref --verify --quiet refs/heads/gh-pages; then
  echo "== attaching worktree to existing gh-pages =="
  git worktree add "$WORKTREE_DIR" gh-pages
else
  echo "== creating orphan gh-pages branch =="
  git worktree add --detach "$WORKTREE_DIR"
  git -C "$WORKTREE_DIR" checkout --orphan gh-pages
  git -C "$WORKTREE_DIR" rm -rf --quiet . 2>/dev/null || true
fi

# Make the worktree's tree identical to web/, without touching .git.
find "$WORKTREE_DIR" -mindepth 1 -maxdepth 1 -not -name ".git" -exec rm -rf {} +
cp -R web/. "$WORKTREE_DIR/"
touch "$WORKTREE_DIR/.nojekyll"  # serve files starting with '_' as-is, no Jekyll pass

cd "$WORKTREE_DIR"
git add -A
if git diff --cached --quiet; then
  echo "== gh-pages already matches web/ — nothing to commit =="
else
  git commit -m "Deploy SRD reference site ($(cd "$ROOT" && git rev-parse --short HEAD))"
  echo "== committed on gh-pages =="
fi

if [ "$DO_PUSH" = "1" ]; then
  git push origin gh-pages
  echo "== pushed gh-pages to origin =="
else
  echo "== not pushed (pass --push to publish to origin) =="
fi
