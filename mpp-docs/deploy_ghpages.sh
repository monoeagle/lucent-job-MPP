#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# deploy_ghpages.sh — MPP (Flask + React) Doku → GitHub Pages (gh-pages-Branch)
#
# Baut die statische Doku (site/) und pusht sie in den gh-pages-Branch (classic
# Pages, build_type=legacy, source: gh-pages /). main bleibt unberührt — der
# Deploy läuft in einem temporären git-worktree.
#
#   ./deploy_ghpages.sh             # voller Build + Deploy
#   ./deploy_ghpages.sh --no-build  # vorhandenes site/ deployen
#
# Voraussetzung: git-Remote 'origin' = GitHub-Repo, Push-Recht.
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(git -C "$DOCS_DIR" rev-parse --show-toplevel)"
SITE="$DOCS_DIR/site"
BRANCH="gh-pages"
PY="$DOCS_DIR/.venv-docs/bin/python3"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "  ${CYAN}→${NC} $1"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; exit 1; }

# ── 1. Build ──────────────────────────────────────────────────────────────────
if [ "${1:-}" != "--no-build" ]; then
  info "Doku bauen (build_docs.py)…"
  "$PY" "$DOCS_DIR/build_docs.py" --no-mermaid --no-activity >/dev/null
fi
[ -f "$SITE/index.html" ] || fail "site/index.html fehlt — zuerst bauen."
touch "$SITE/.nojekyll"          # verhindert Jekyll-Verarbeitung (Ordner mit _)
ok "site/ bereit ($(find "$SITE" -type f | wc -l) Dateien)"

# ── 2. Worktree für gh-pages ──────────────────────────────────────────────────
WT="$(mktemp -d)"
cleanup() { git -C "$REPO_DIR" worktree remove --force "$WT" 2>/dev/null || true; rm -rf "$WT"; }
trap cleanup EXIT

cd "$REPO_DIR"
git fetch origin "$BRANCH" >/dev/null 2>&1 || true
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  info "vorhandenen $BRANCH-Branch aktualisieren…"
  git worktree add -B "$BRANCH" "$WT" "origin/$BRANCH" >/dev/null
else
  info "$BRANCH-Branch (orphan) neu anlegen…"
  git worktree add --detach "$WT" HEAD >/dev/null
  git -C "$WT" checkout --orphan "$BRANCH" >/dev/null
  git -C "$WT" rm -rf . >/dev/null 2>&1 || true
fi

# ── 3. site/ in den Branch spiegeln ───────────────────────────────────────────
find "$WT" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
cp -a "$SITE/." "$WT/"
touch "$WT/.nojekyll"

# ── 4. Commit + Push ──────────────────────────────────────────────────────────
SHA="$(git -C "$REPO_DIR" rev-parse --short HEAD)"
cd "$WT"
git add -A
if git diff --cached --quiet; then
  ok "keine Änderungen — gh-pages bereits aktuell."
else
  git commit -q -m "docs: Site-Deploy (main @ ${SHA})"
  git push -q -u origin "$BRANCH"
  ok "nach origin/$BRANCH gepusht."
fi
