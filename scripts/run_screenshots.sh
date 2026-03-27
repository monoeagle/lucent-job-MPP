#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# run_screenshots.sh — MPP Screenshot-Tool
#
# Installiert Playwright + Browser und erzeugt Screenshots aller Seiten als WebP.
#
# Verwendung:
#   ./scripts/run_screenshots.sh                        → Desktop, alle Seiten
#   ./scripts/run_screenshots.sh --quick                → Nur Hauptseiten
#   ./scripts/run_screenshots.sh --mobile               → Desktop + Mobile
#   ./scripts/run_screenshots.sh --browser chromium     → Chromium statt Firefox
#   ./scripts/run_screenshots.sh --port 3000            → Anderer Port
#
# Voraussetzung: Frontend muss laufen!
# ══════════════════════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="python3"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${CYAN}  ▸ $*${NC}"; }
success() { echo -e "${GREEN}  ✓ $*${NC}"; }
error()   { echo -e "${RED}  ✗ $*${NC}"; exit 1; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   MPP — Screenshot-Tool                  ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# Parse --browser argument
BROWSER="firefox"
for arg in "$@"; do
    if [[ "$prev" == "--browser" ]]; then BROWSER="$arg"; fi
    prev="$arg"
done

# Python pruefen
if ! command -v "$PYTHON" &>/dev/null; then
    error "python3 nicht gefunden."
fi
info "Python: $($PYTHON --version 2>&1)"

# Playwright + Pillow installieren
if ! $PYTHON -c "import playwright" &>/dev/null 2>&1; then
    info "Installiere Playwright..."
    $PYTHON -m pip install playwright pillow --break-system-packages --quiet
    success "Playwright + Pillow installiert."
else
    success "Playwright vorhanden."
fi

# Browser pruefen/installieren
info "Prüfe $BROWSER..."
BROWSER_OK=$($PYTHON -c "
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        bt = getattr(p, '$BROWSER', p.firefox)
        b = bt.launch(headless=True)
        b.close()
    print('ok')
except Exception:
    print('missing')
" 2>&1)

if [[ "$BROWSER_OK" == "ok" ]]; then
    success "$BROWSER vorhanden."
else
    info "Installiere $BROWSER (kann 1-2 Min dauern)..."
    $PYTHON -m playwright install "$BROWSER"
    $PYTHON -m playwright install-deps "$BROWSER" 2>/dev/null || true
    success "$BROWSER installiert."
fi

# Frontend pruefen
PORT=3000
for arg in "$@"; do
    if [[ "$prev" == "--port" ]]; then PORT="$arg"; fi
    prev="$arg"
done

info "Prüfe Frontend auf Port $PORT..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "304" ]]; then
    success "Frontend erreichbar (HTTP $HTTP_CODE)."
else
    error "Frontend nicht erreichbar auf Port $PORT!\n   Bitte zuerst starten: bash scripts/mpp.sh → [2] oder [4]"
fi

# Screenshots erzeugen
echo ""
info "Starte Screenshots..."
echo ""

cd "$PROJECT_DIR"
$PYTHON scripts/screenshot_tool.py "$@"

echo ""
echo -e "${GREEN}  Screenshots liegen in: ${CYAN}$PROJECT_DIR/screenshots/${NC}"
echo ""
