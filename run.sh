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
GLOBAL_DIR="$(dirname "$PROJECT_DIR")/AppImages"   # zentraler Sammelordner neben allen Lucent-Apps
DOCS_DIR="$PROJECT_DIR/mpp-docs"
DOCS_PORT=5083
APP_VERSION="1.1.0"
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

_bundle_python_standalone() {
  local appdir="$1"
  local venv_dir="$2"

  local py_ver
  py_ver=$("$venv_dir/bin/python3" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  local real_py
  real_py="$(readlink -f "$venv_dir/bin/python3")"
  local py_base
  py_base=$("$venv_dir/bin/python3" -c 'import sys; print(sys.base_prefix)')

  info "Python ${py_ver} standalone buendeln..."

  mkdir -p "$appdir/python/bin"
  mkdir -p "$appdir/python/lib/python${py_ver}"

  cp "$real_py" "$appdir/python/bin/python3"
  chmod +x "$appdir/python/bin/python3"
  ln -sf python3 "$appdir/python/bin/python"

  info "Python stdlib kopieren..."
  cp -r "${py_base}/lib/python${py_ver}/"* "$appdir/python/lib/python${py_ver}/" 2>/dev/null || true

  info "Site-packages kopieren..."
  if [ -d "$venv_dir/lib/python${py_ver}/site-packages" ]; then
    cp -r "$venv_dir/lib/python${py_ver}/site-packages" "$appdir/python/lib/python${py_ver}/"
  fi

  for pattern in \
    "/usr/lib/x86_64-linux-gnu/libpython${py_ver}"*.so* \
    "/usr/lib/libpython${py_ver}"*.so* \
    "${py_base}/lib/libpython${py_ver}"*.so*; do
    for lib in $pattern; do
      [ -f "$lib" ] && cp -L "$lib" "$appdir/python/lib/" 2>/dev/null
    done
  done

  info "System-Bibliotheken buendeln..."
  for libname in libssl libcrypto libffi libz libsqlite3 libncurses libtinfo libreadline libbz2 liblzma libexpat libmpdec; do
    for f in /usr/lib/x86_64-linux-gnu/${libname}*.so*; do
      [ -f "$f" ] && cp -L "$f" "$appdir/python/lib/" 2>/dev/null
    done
  done


  # ALL shared library dependencies (automatic ldd scan)
  info "Shared-Library-Abhaengigkeiten scannen (ldd)..."
  local _deplist
  _deplist=$(find "$appdir/python" -name "*.so*" -type f -exec ldd {} 2>/dev/null \; | grep "=> /" | awk '{print $3}' | sort -u)
  local _copied=0
  for dep in $_deplist; do
    [ -f "$dep" ] || continue
    local _bn
    _bn=$(basename "$dep")
    # System-kritische Libs NICHT buendeln
    case "$_bn" in
      libc.so*|libm.so*|libdl.so*|librt.so*|libpthread.so*) continue ;;
      ld-linux*|libgcc_s.so*|libstdc++.so*) continue ;;
      libnss_*|libresolv.so*|libnsl.so*|libutil.so*) continue ;;
      linux-vdso.so*) continue ;;
    esac
    if [ ! -f "$appdir/python/lib/$_bn" ]; then
      cp -L "$dep" "$appdir/python/lib/" 2>/dev/null && _copied=$((_copied + 1))
    fi
  done
  # Bereits faelschlich kopierte System-Libs entfernen
  for _syslib in libc.so* libm.so* libdl.so* librt.so* libpthread.so* ld-linux* libgcc_s.so* libstdc++.so* libnss_* libresolv.so* libnsl.so* libutil.so*; do
    rm -f "$appdir/python/lib/"$_syslib 2>/dev/null
  done
  info "$_copied zusaetzliche Shared Libraries gebundelt"
  ok "Python ${py_ver} standalone gebundelt"
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
  # Seed-Script mitbuendeln
  [ -f "$PROJECT_DIR/scripts/seed.py" ] && cp "$PROJECT_DIR/scripts/seed.py" "$appdir/app/"

  _bundle_python_standalone "$appdir" "$VENV_DIR"

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

  # SPA-Server mit API-Proxy als Python-Script ins AppDir schreiben
  cat > "$appdir/spa_server.py" << 'PYEOF'
"""SPA server with API proxy for MPP-TDD AppImage."""
import sys, os, json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError

PORT = int(sys.argv[1])
BACKEND = sys.argv[2]
BUILD_DIR = sys.argv[3]

class SPAProxyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=BUILD_DIR, **kw)

    def do_request(self, method):
        # Proxy /api/* to Flask backend
        if self.path.startswith("/api/"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else None
                headers = {k: v for k, v in self.headers.items()
                           if k.lower() not in ("host", "transfer-encoding")}
                req = Request(f"{BACKEND}{self.path}", data=body, headers=headers, method=method)
                with urlopen(req, timeout=30) as resp:
                    self.send_response(resp.status)
                    for k, v in resp.getheaders():
                        if k.lower() not in ("transfer-encoding",):
                            self.send_header(k, v)
                    self.end_headers()
                    self.wfile.write(resp.read())
            except URLError as e:
                self.send_error(502, f"Backend error: {e}")
            return
        # SPA fallback: serve index.html for non-file paths
        path = self.translate_path(self.path)
        if not os.path.exists(path) and "." not in os.path.basename(self.path):
            self.path = "/index.html"
        super().do_GET()

    def do_GET(self): self.do_request("GET")
    def do_POST(self): self.do_request("POST")
    def do_PUT(self): self.do_request("PUT")
    def do_DELETE(self): self.do_request("DELETE")
    def do_PATCH(self): self.do_request("PATCH")
    def log_message(self, fmt, *args):
        if len(args) >= 2 and args[1] not in ("200", "304"):
            super().log_message(fmt, *args)

HTTPServer(("127.0.0.1", PORT), SPAProxyHandler).serve_forever()
PYEOF

  cat > "$appdir/AppRun" << 'RUNEOF'
#!/usr/bin/env bash
SELF="$(readlink -f "${BASH_SOURCE[0]}")"
HERE="$(dirname "$SELF")"
PORT=""            # Frontend-Port (leer = OS-vergebener Ephemeral-Port)
PORT_FIXED=0
OPEN_BROWSER=1
PREFER=0
for arg in "$@"; do
  case "$arg" in
    --port=*)        PORT="${arg#--port=}"; PORT_FIXED=1; OPEN_BROWSER=0 ;;
    --port-prefer=*) PREFER="${arg#--port-prefer=}" ;;
    --no-browser)    OPEN_BROWSER=0 ;;
  esac
done
export PYTHONHOME="${HERE}/python"
export PATH="${HERE}/python/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/python/lib:${LD_LIBRARY_PATH:-}"
PY_VER=$(ls -1 "${HERE}/python/lib/" | grep "^python3\." | head -1 | sed "s/python//")
export PYTHONPATH="${HERE}/python/lib/python${PY_VER}/site-packages"
export AUTH_MODE=stub
export CMDB_MODE=stub
export FLASK_APP=app
export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
PYBIN="${HERE}/python/bin/python3"

# Beide Ports vom OS vergeben lassen (ephemeral) → beliebig viele Instanzen parallel,
# nie "Address already in use". Das Backend ist intern (nur ueber den SPA-Proxy
# erreichbar) und daher IMMER random. Der Frontend-Port ist random, ausser der Hub
# setzt ihn fix via --port= (er muss ihn zum Tab-Oeffnen kennen). --port-prefer=NNNN
# bevorzugt optional einen Wunsch-Frontend-Port (Fallback random).
read -r FE_PORT BE_PORT < <("$PYBIN" - "$PORT_FIXED" "$PORT" "$PREFER" <<'PY'
import socket, sys
fixed = sys.argv[1] == "1"
fixed_port = int(sys.argv[2]) if sys.argv[2].isdigit() else 0
prefer = int(sys.argv[3]) if sys.argv[3].isdigit() else 0
def grab(p):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", p)); return s
    except OSError:
        s.close(); return None
held = []
if fixed:
    fe = fixed_port
else:
    s = grab(prefer) if prefer else None
    if s is None: s = grab(0)   # 0 → OS waehlt freien Ephemeral-Port
    fe = s.getsockname()[1]; held.append(s)
s = grab(0); be = s.getsockname()[1]; held.append(s)
for s in held: s.close()
print(fe, be)
PY
)
PORT="$FE_PORT"
BACKEND_PORT="$BE_PORT"

cd "${HERE}/app"

# Beim ersten Start: DB-Migrationen + Seed-Daten
STAMP="${HOME}/.lucent-mpp-tdd-seeded"
if [ ! -f "$STAMP" ]; then
  echo "[MPP-TDD] Erststart: Datenbank initialisieren..."

  # DB erstellen falls nicht vorhanden (ignoriert Fehler wenn sie existiert)
  PGPASSWORD=mpp createdb -h localhost -U mpp mpp_dev 2>/dev/null || true

  # Alembic-Migrationen ausfuehren
  echo "[MPP-TDD] Migrationen ausfuehren..."
  "$PYBIN" -m alembic upgrade head 2>&1 | tail -5

  # Seed-Daten einspielen
  if [ -f "${HERE}/app/seed.py" ]; then
    echo "[MPP-TDD] Seed-Daten einspielen..."
    "$PYBIN" "${HERE}/app/seed.py" 2>&1 | tail -5
  fi

  touch "$STAMP"
  echo "[MPP-TDD] Datenbank bereit."
fi

# Flask Backend starten (interner Ephemeral-Port)
"$PYBIN" -m flask run --port "$BACKEND_PORT" &
BACKEND_PID=$!

# SPA-Server mit API-Proxy starten (leitet /api an das Backend weiter)
"$PYBIN" "${HERE}/spa_server.py" "$PORT" "http://127.0.0.1:${BACKEND_PORT}" "${HERE}/app/frontend_dist" &
SERVER_PID=$!

TMPPROFILE=""
cleanup() {
  kill "$SERVER_PID" "$BACKEND_PID" 2>/dev/null
  [ -n "$TMPPROFILE" ] && rm -rf "$TMPPROFILE"
  exit 0
}
trap cleanup SIGTERM SIGINT

# Warten bis Backend bereit
sleep 2

URL="http://127.0.0.1:${PORT}"
echo "[MPP-TDD] Frontend: $URL"
echo "[MPP-TDD] Backend:  http://127.0.0.1:${BACKEND_PORT}"

if [ "$OPEN_BROWSER" -eq 1 ]; then
  sleep 0.5
  CHROME=""
  for c in chromium chromium-browser google-chrome google-chrome-stable chrome brave-browser; do
    if command -v "$c" &>/dev/null; then CHROME="$c"; break; fi
  done
  if [ -n "$CHROME" ]; then
    # Eigenes Temp-Profil → frische, ISOLIERTE Instanz (unabhaengig von Firefox und
    # jedem schon laufenden Chrome/Chromium); --app = randloses App-Fenster.
    TMPPROFILE="$(mktemp -d /tmp/mpp-app-chrome.XXXXXX)"
    "$CHROME" --user-data-dir="$TMPPROFILE" --no-first-run --no-default-browser-check \
              --new-window --app="$URL" >/dev/null 2>&1 &
  else
    echo "[MPP-TDD] Kein Chromium/Chrome gefunden — bitte manuell oeffnen: $URL"
    xdg-open "$URL" >/dev/null 2>&1 || true
  fi
fi

wait "$SERVER_PID"
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
  header "MPP TDD — Docs Release (Site → AppImage → Global → TDD-Gate)"

  # ── Stufe 1: Site rendern (Mermaid→SVG, Activity-JSON, zensical build) ──────
  # Bevorzugt das venv-Python direkt (umgeht den pip-Reinstall des run-Scripts auf
  # externally-managed Systemen); Fallback auf run_mpp_docs.sh, das das venv anlegt.
  info "Stufe 1 — Site rendern ..."
  if [ -x "$DOCS_DIR/.venv-docs/bin/python3" ] && "$DOCS_DIR/.venv-docs/bin/python3" -c "import zensical" 2>/dev/null; then
    ( cd "$DOCS_DIR" && rm -rf site && .venv-docs/bin/python3 build_docs.py )
  else
    ( cd "$DOCS_DIR" && bash run_mpp_docs.sh --build )
  fi

  if [ ! -d "$DOCS_DIR/site" ]; then
    fail "Site-Build fehlgeschlagen — site/ fehlt"
  fi
  ok "Site gebaut: ${BOLD}$DOCS_DIR/site${NC}"

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
DEFAULT_PORT="${DOCS_PORT:-5083}"
PORT="$DEFAULT_PORT"
PORT_FIXED=0
OPEN_BROWSER=1
for arg in "$@"; do
  case "$arg" in
    --port=*)     PORT="${arg#--port=}"; PORT_FIXED=1; OPEN_BROWSER=0 ;;
    --no-browser) OPEN_BROWSER=0 ;;
  esac
done
if ! command -v python3 &>/dev/null; then
  echo "[ERROR] python3 nicht gefunden."
  exit 1
fi

# Standalone: IMMER einen zufaellig freien Port nehmen (OS-vergeben, ephemeral) —
# es koennen beliebig viele Instanzen parallel laufen, nie "Address already in use".
# Der Browser wird unten mit genau diesem Port geoeffnet, Fixwert ist unnoetig.
# Hub-Modus (--port=) bleibt exakt, weil der Hub den Port zum Tab-Oeffnen kennen muss.
# Mit --port-prefer=NNNN laesst sich optional ein Wunschport bevorzugen (Fallback random).
PREFER=0
for arg in "$@"; do case "$arg" in --port-prefer=*) PREFER="${arg#--port-prefer=}";; esac; done
if [ "$PORT_FIXED" -eq 0 ]; then
  PORT="$(python3 - "$PREFER" <<'PY'
import socket, sys
prefer = int(sys.argv[1]) if sys.argv[1].isdigit() else 0
def grab(p):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", p)); return s.getsockname()[1], s
    except OSError:
        s.close(); return None, None
port = None
if prefer:
    port, s = grab(prefer)
if port is None:
    port, s = grab(0)          # 0 → OS waehlt freien Ephemeral-Port
s.close()
print(port)
PY
)"
fi

TMPPROFILE=""
cleanup() {
  kill "$SERVER_PID" 2>/dev/null
  [ -n "$TMPPROFILE" ] && rm -rf "$TMPPROFILE"
  exit 0
}
trap cleanup SIGTERM SIGINT
cd "${HERE}/site"
python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
SERVER_PID=$!
URL="http://127.0.0.1:${PORT}"
echo "[Docs] $URL"

if [ "$OPEN_BROWSER" -eq 1 ]; then
  sleep 0.5
  CHROME=""
  for c in chromium chromium-browser google-chrome google-chrome-stable chrome brave-browser; do
    if command -v "$c" &>/dev/null; then CHROME="$c"; break; fi
  done
  if [ -n "$CHROME" ]; then
    # Eigenes Temp-Profil → frische, ISOLIERTE Instanz (unabhaengig von Firefox
    # und jedem schon laufenden Chrome/Chromium); --app = randloses Doku-Fenster.
    TMPPROFILE="$(mktemp -d /tmp/mpp-docs-chrome.XXXXXX)"
    "$CHROME" --user-data-dir="$TMPPROFILE" --no-first-run --no-default-browser-check \
              --new-window --app="$URL" >/dev/null 2>&1 &
  else
    echo "[Docs] Kein Chromium/Chrome gefunden — bitte manuell oeffnen: $URL"
    xdg-open "$URL" >/dev/null 2>&1 || true
  fi
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

  # ── In den globalen Sammelordner spiegeln (docs-release-sync.pattern §B.3) ──
  # Atomar per rename, falls die alte AppImage gerade läuft (FUSE-Mount → ETXTBSY).
  local base; base="$(basename "$output")"
  mkdir -p "$GLOBAL_DIR"
  cp "$output" "$GLOBAL_DIR/.${base}.new"
  mv -f "$GLOBAL_DIR/.${base}.new" "$GLOBAL_DIR/${base}"
  chmod +x "$GLOBAL_DIR/${base}"
  ok "Global gespiegelt nach ${BOLD}${GLOBAL_DIR}/${base}${NC}"

  # ── TDD-Gate: Doku ist erst fertig, wenn ALLE Regeln grün sind (§G) ─────────
  if [ -x "$DOCS_DIR/verify_docs.sh" ]; then
    header "TDD-Gate — Doku-Abnahme (docs-release-sync §G)"
    if bash "$DOCS_DIR/verify_docs.sh"; then
      ok "TDD-Gate grün — Doku fertig."
    else
      fail "TDD-Gate ROT — Doku NICHT fertig. Rote Regel(n) oben fixen und neu bauen."
    fi
  else
    warn "verify_docs.sh fehlt/nicht ausführbar — TDD-Gate übersprungen!"
  fi
}

# ══════════════════════════════════════════════════════════════════════════════
# Offline-Release-Bundle (AlmaLinux 9) — gebündelte Wheels + prebuilt SPA + Installer
# ══════════════════════════════════════════════════════════════════════════════
cmd_release() {
  header "MPP (Flask + React) — Offline-Release (AlmaLinux 9)"

  # 1. React-SPA bauen (auf dem Dev-Rechner mit Node; die VM braucht kein Node).
  if [ ! -d "$PROJECT_DIR/frontend/dist" ] || [ -n "${REBUILD_SPA:-}" ]; then
    info "React-SPA bauen (frontend/dist)..."
    ( cd "$PROJECT_DIR/frontend" && [ -d node_modules ] || npm install -q )
    ( cd "$PROJECT_DIR/frontend" && npm run build )
    ok "frontend/dist gebaut"
  else
    info "frontend/dist vorhanden — Rebuild via REBUILD_SPA=1 erzwingen"
  fi

  # 2. Offline-Wheelhouse für AlmaLinux 9 / Py3.12 (nur einmalig, wenn leer).
  local wheels_dir="$PROJECT_DIR/wheels"
  mkdir -p "$wheels_dir"
  if [ -z "$(ls "$wheels_dir"/*.whl 2>/dev/null)" ]; then
    info "Wheelhouse leer — Wheels für AlmaLinux 9 / Py3.12 laden..."
    "$VENV_DIR/bin/python3" -m pip download \
      -r "$PROJECT_DIR/requirements.txt" --dest "$wheels_dir" \
      --only-binary=:all: --python-version 312 --implementation cp --abi cp312 \
      --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux_2_28_x86_64
    "$VENV_DIR/bin/python3" -m pip download pip setuptools wheel --dest "$wheels_dir" --only-binary=:all:
    ok "Wheels geladen nach wheels/"
  else
    info "Wheelhouse vorhanden ($(ls "$wheels_dir"/*.whl 2>/dev/null | wc -l) Wheels) — Neuladen: wheels/ leeren"
  fi

  # 3. Bundle assemblieren + zippen.
  "$VENV_DIR/bin/python3" "$PROJECT_DIR/tools/build_release.py"
}

# ══════════════════════════════════════════════════════════════════════════════
# CLI Dispatch
# ══════════════════════════════════════════════════════════════════════════════
case "${1:-serve}" in
  serve)           cmd_serve ;;
  appimage-build)  cmd_appimage ;;
  docs-appimage)   cmd_docs_appimage ;;
  release)         cmd_release ;;
  *)
    echo "Usage: $0 [serve|appimage-build|docs-appimage|release]"
    exit 1
    ;;
esac
