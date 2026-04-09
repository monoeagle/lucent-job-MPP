#!/bin/bash
# PORT=3000
# HEALTHCHECK=/api/v1/health
# COLOR=#2196F3

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

# ── AppImage-Variablen ────────────────────────────────────────────────────────
APPIMAGE_DIR="$PROJECT_DIR/build/appimage"
RELEASE_DIR="$PROJECT_DIR/release"
DOCS_DIR="$PROJECT_DIR/mpp-docs"
DOCS_PORT=5083
APP_VERSION="1.0.0"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
APPIMAGETOOL="$PROJECT_DIR/.tools/appimagetool"

# ── Farben ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()     { echo -e "  ${GREEN}✓${NC} $1"; }
warn()   { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail()   { echo -e "  ${RED}✗${NC} $1"; exit 1; }
info()   { echo -e "  ${CYAN}→${NC} $1"; }
header() { echo -e "\n${BOLD}═══ $1 ═══${NC}\n"; }

_ensure_appimagetool() {
  if [ -x "$APPIMAGETOOL" ]; then return 0; fi
  info "appimagetool wird heruntergeladen..."
  mkdir -p "$(dirname "$APPIMAGETOOL")"
  curl -fsSL "$APPIMAGETOOL_URL" -o "$APPIMAGETOOL"
  chmod +x "$APPIMAGETOOL"
  ok "appimagetool installiert unter .tools/"
}

cmd_serve() {
  BACKEND_PID=""
  FRONTEND_PID=""

  cleanup() {
      [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
      [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
      wait 2>/dev/null
  }
  trap cleanup EXIT INT TERM

  if [ -f "$VENV_DIR/bin/activate" ]; then
      source "$VENV_DIR/bin/activate"
  else
      echo "ERROR: venv not found at $VENV_DIR" >&2
      exit 1
  fi

  export AUTH_MODE=stub
  export CMDB_MODE=stub
  export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
  export FLASK_APP=app

  cd "$PROJECT_DIR"
  flask run --port 5000 &
  BACKEND_PID=$!

  set +e
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  nvm use 22 >/dev/null 2>&1
  set -e

  cd "$PROJECT_DIR/frontend"
  [ -d node_modules ] || npm install -q 2>&1
  npx vite --port 3000 &
  FRONTEND_PID=$!

  wait -n 2>/dev/null || wait
}

cmd_appimage() {
  header "MPP TDD — AppImage Build"

  if [ ! -d "$VENV_DIR" ]; then
    fail "venv nicht vorhanden"
  fi
  if [ ! -d "$PROJECT_DIR/frontend/dist" ]; then
    fail "frontend/dist nicht vorhanden — bitte zuerst: cd frontend && npm run build"
  fi

  _ensure_appimagetool

  local appdir="$APPIMAGE_DIR/LucentMPPTDD.AppDir"

  info "AppDir vorbereiten..."
  rm -rf "$appdir"
  mkdir -p "$appdir/usr/share/icons/hicolor/256x256/apps"
  mkdir -p "$appdir/usr/share/applications"
  mkdir -p "$appdir/app"

  info "App-Sourcen kopieren..."
  cp -r "$PROJECT_DIR/app" "$appdir/app/app"
  cp -r "$PROJECT_DIR/frontend/dist" "$appdir/app/frontend_dist"
  cp -r "$PROJECT_DIR/migrations" "$appdir/app/migrations"
  [ -f "$PROJECT_DIR/alembic.ini" ] && cp "$PROJECT_DIR/alembic.ini" "$appdir/app/"
  [ -f "$PROJECT_DIR/requirements.txt" ] && cp "$PROJECT_DIR/requirements.txt" "$appdir/app/"

  info "Python venv kopieren (kann dauern)..."
  cp -r "$VENV_DIR" "$appdir/venv"

  cat > "$appdir/usr/share/icons/hicolor/256x256/apps/lucent-mpp-tdd.svg" << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <rect width="256" height="256" rx="40" fill="#0A0E1A"/>
  <rect x="58" y="58" width="140" height="100" rx="10" fill="none" stroke="#2196F3" stroke-width="4"/>
  <text x="128" y="118" text-anchor="middle" font-family="sans-serif" font-size="28" font-weight="bold" fill="#2196F3">MPP</text>
  <rect x="78" y="172" width="100" height="24" rx="6" fill="none" stroke="#1565C0" stroke-width="3"/>
  <text x="128" y="190" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#1E88E5">Flask+React</text>
</svg>
SVGEOF
  cp "$appdir/usr/share/icons/hicolor/256x256/apps/lucent-mpp-tdd.svg" \
     "$appdir/lucent-mpp-tdd.svg"

  cat > "$appdir/lucent-mpp-tdd.desktop" << DEOF
[Desktop Entry]
Type=Application
Name=Lucent MPP TDD
Comment=Marketplace Portal — Flask + React
Exec=AppRun
Icon=lucent-mpp-tdd
Categories=Development;Office;
Terminal=false
DEOF
  cp "$appdir/lucent-mpp-tdd.desktop" "$appdir/usr/share/applications/"

  cat > "$appdir/AppRun" << 'RUNEOF'
#!/usr/bin/env bash
SELF="$(readlink -f "${BASH_SOURCE[0]}")"
HERE="$(dirname "$SELF")"
PORT=3000
BACKEND_PORT=5000
for arg in "$@"; do
  case "$arg" in --port=*) PORT="${arg#--port=}";; esac
done
source "${HERE}/venv/bin/activate"
export AUTH_MODE=stub
export CMDB_MODE=stub
export FLASK_APP=app
cd "${HERE}/app"
flask run --port "$BACKEND_PORT" &
BACKEND_PID=$!
cleanup() { kill "$BACKEND_PID" 2>/dev/null; exit 0; }
trap cleanup SIGTERM SIGINT
cd "${HERE}/app/frontend_dist"
exec python3 -m http.server "$PORT" --bind 127.0.0.1
RUNEOF
  chmod +x "$appdir/AppRun"

  local output="$PROJECT_DIR/build/Lucent-MPP-TDD-${APP_VERSION}-x86_64.AppImage"
  info "AppImage erzeugen..."
  ARCH=x86_64 "$APPIMAGETOOL" "$appdir" "$output" 2>&1 | tail -3
  ok "AppImage erstellt: ${BOLD}${output}${NC}"

  mkdir -p "$RELEASE_DIR"
  cp "$output" "$RELEASE_DIR/"
  ok "Kopiert nach ${BOLD}${RELEASE_DIR}/$(basename "$output")${NC}"
}

cmd_docs_appimage() {
  header "MPP TDD — Docs AppImage Build"

  if [ ! -d "$DOCS_DIR/site" ]; then
    fail "Dokumentation nicht gebaut — bitte zuerst Docs bauen"
  fi

  _ensure_appimagetool

  local appdir="$APPIMAGE_DIR/LucentMPPTDDDocs.AppDir"

  info "Docs AppDir vorbereiten..."
  rm -rf "$appdir"
  mkdir -p "$appdir/usr/share/icons/hicolor/256x256/apps"
  mkdir -p "$appdir/usr/share/applications"

  cp -r "$DOCS_DIR/site" "$appdir/site"

  cat > "$appdir/usr/share/icons/hicolor/256x256/apps/lucent-mpp-tdd-docs.svg" << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <rect width="256" height="256" rx="40" fill="#0A0E1A"/>
  <rect x="68" y="58" width="120" height="140" rx="8" fill="none" stroke="#2196F3" stroke-width="4"/>
  <line x1="92" y1="98" x2="164" y2="98" stroke="#1565C0" stroke-width="3"/>
  <line x1="92" y1="122" x2="164" y2="122" stroke="#1565C0" stroke-width="3"/>
  <line x1="92" y1="146" x2="140" y2="146" stroke="#1565C0" stroke-width="3"/>
</svg>
SVGEOF
  cp "$appdir/usr/share/icons/hicolor/256x256/apps/lucent-mpp-tdd-docs.svg" \
     "$appdir/lucent-mpp-tdd-docs.svg"

  cat > "$appdir/lucent-mpp-tdd-docs.desktop" << DEOF
[Desktop Entry]
Type=Application
Name=Lucent MPP TDD Docs
Comment=Dokumentation fuer MPP TDD
Exec=AppRun
Icon=lucent-mpp-tdd-docs
Categories=Documentation;
Terminal=false
DEOF
  cp "$appdir/lucent-mpp-tdd-docs.desktop" "$appdir/usr/share/applications/"

  cat > "$appdir/AppRun" << 'RUNEOF'
#!/usr/bin/env bash
SELF="$(readlink -f "${BASH_SOURCE[0]}")"
HERE="$(dirname "$SELF")"
PORT="${DOCS_PORT:-5083}"
for arg in "$@"; do
  case "$arg" in --port=*) PORT="${arg#--port=}";; esac
done
if ! command -v python3 &>/dev/null; then
  echo "[ERROR] python3 nicht gefunden."
  exit 1
fi
cleanup() { kill "$SERVER_PID" 2>/dev/null; exit 0; }
trap cleanup SIGTERM SIGINT
cd "${HERE}/site"
python3 -m http.server "$PORT" --bind 127.0.0.1 &
SERVER_PID=$!
echo "[Docs] http://127.0.0.1:${PORT}"
if [[ "$*" != *"--port="* ]]; then
  sleep 0.5
  xdg-open "http://127.0.0.1:${PORT}" 2>/dev/null || true
fi
wait "$SERVER_PID"
RUNEOF
  chmod +x "$appdir/AppRun"

  local output="$PROJECT_DIR/build/Lucent-MPP-TDD-Docs-${APP_VERSION}-x86_64.AppImage"
  info "Docs AppImage erzeugen..."
  ARCH=x86_64 "$APPIMAGETOOL" "$appdir" "$output" 2>&1 | tail -3
  ok "Docs AppImage erstellt: ${BOLD}${output}${NC}"

  mkdir -p "$RELEASE_DIR"
  cp "$output" "$RELEASE_DIR/"
  ok "Kopiert nach ${BOLD}${RELEASE_DIR}/$(basename "$output")${NC}"
}

# ══════════════════════════════════════════════════════════════════════════════
# CLI Dispatch
# ══════════════════════════════════════════════════════════════════════════════
case "${1:-serve}" in
  serve)           cmd_serve ;;
  appimage-build)  cmd_appimage ;;
  docs-appimage)   cmd_docs_appimage ;;
  *)
    echo "Usage: $0 [serve|appimage-build|docs-appimage]"
    exit 1
    ;;
esac
