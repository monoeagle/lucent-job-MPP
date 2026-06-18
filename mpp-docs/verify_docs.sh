#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# verify_docs.sh — TDD-Gate für die MPP-Dokumentation
#
# Setzt `docs-release-sync.pattern` §G um: die Doku gilt NUR als fertig, wenn
# JEDE Regel grün ist. Eine rote Regel ⇒ exit 1 (Doku NICHT fertig).
#
# Läuft gegen das real gebaute Artefakt site/ (nach dem zweistufigen Build).
# Reihenfolge:  bash run_mpp_docs.sh --build   →   bash verify_docs.sh
# ══════════════════════════════════════════════════════════════════════════════
set -uo pipefail

DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$DOCS_DIR")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"
SITE="$DOCS_DIR/site"
JS="$DOCS_DIR/docs/javascripts"
GLOBAL_DIR="$ROOT_DIR/AppImages"

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
FAILS=0
pass() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; FAILS=$((FAILS+1)); }
# check <label> <cmd...>  → grün wenn cmd Exit 0
check() { local label="$1"; shift; if "$@" >/dev/null 2>&1; then pass "$label"; else fail "$label"; fi; }

echo -e "${CYAN}═══ MPP Doku — TDD-Gate (docs-release-sync §G) ═══${NC}"

VERSION="$(grep -E '^version:' "$PROJECT_DIR/lucent-hub.yml" | head -1 | tr -d ' "' | cut -d: -f2)"
APPIMAGE="Lucent-MPP-TDD-Docs-${VERSION}-x86_64.AppImage"
echo -e "  ${CYAN}Version aus lucent-hub.yml: ${VERSION}${NC}"

# ── R-PFLICHT ────────────────────────────────────────────────────────────────
echo "── R-PFLICHT (Pflichtdateien)"
for f in zensical.toml build_docs.py run_mpp_docs.sh \
         tools/extract_mermaid_blocks.py tools/render_mermaid.sh tools/generate_project_activity.py \
         docs/javascripts/mermaid.min.js docs/javascripts/mermaid-init.js docs/javascripts/palette-init.js \
         docs/javascripts/lightbox.js docs/javascripts/activity-heatmap.js docs/javascripts/icon-rail.js \
         docs/javascripts/hub-stop.js docs/stylesheets/extra.css; do
  check "$f" test -f "$DOCS_DIR/$f"
done
EXTRA_CSS_LINES=$(wc -l < "$DOCS_DIR/docs/stylesheets/extra.css")
[ "$EXTRA_CSS_LINES" -gt 1000 ] && pass "extra.css Vollversion ($EXTRA_CSS_LINES Z. > 1000)" \
                                || fail "extra.css zu klein ($EXTRA_CSS_LINES Z.) — Platzhalter?"

# ── R-VERSION ────────────────────────────────────────────────────────────────
echo "── R-VERSION (Konsistenz)"
ZEN_VER=$(grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' "$DOCS_DIR/zensical.toml" | head -1 | tr -d v)
RAIL_VER=$(grep -oE "APP_VERSION[^']*'[0-9.]+'" "$JS/icon-rail.js" | grep -oE "[0-9]+\.[0-9]+\.[0-9]+")
[ "$ZEN_VER" = "$VERSION" ] && pass "zensical.toml = $ZEN_VER" || fail "zensical.toml ($ZEN_VER) ≠ hub ($VERSION)"
[ "$RAIL_VER" = "$VERSION" ] && pass "icon-rail.js = $RAIL_VER" || fail "icon-rail.js ($RAIL_VER) ≠ hub ($VERSION)"

# ── R-APPLOOK ────────────────────────────────────────────────────────────────
echo "── R-APPLOOK (App-Look komplett)"
for j in mermaid.min.js mermaid-init.js palette-init.js lightbox.js activity-heatmap.js icon-rail.js hub-stop.js; do
  check "extra_javascript bindet $j" grep -q "javascripts/$j" "$DOCS_DIR/zensical.toml"
  check "site/javascripts/$j vorhanden" test -f "$SITE/javascripts/$j"
done
if grep -qE '^\s*"navigation\.tabs' "$DOCS_DIR/zensical.toml"; then
  fail "navigation.tabs noch aktiv (Icon-Rail ersetzt Tabs)"
else
  pass "navigation.tabs/.tabs.sticky entfernt"
fi

# ── R-HOME ───────────────────────────────────────────────────────────────────
echo "── R-HOME (Startseite nur Home-Layout)"
check "Heatmap-Container"  grep -q "data-adb-activity-heatmap" "$SITE/index.html"
check "Insights-Container" grep -q "data-adb-activity-stats"   "$SITE/index.html"
check "Hero AP-Übersicht"  grep -q "entwicklung-arbeitspakete-1.svg" "$SITE/index.html"
if grep -qE "Tech-Stack|Was kann MPP" "$SITE/index.html"; then
  fail "Fremdinhalt auf der Startseite (Tech-Stack/Was-kann-MPP)"
else
  pass "kein ausgelagerter Fließtext auf der Startseite"
fi

# ── R-DIAGRAMME ──────────────────────────────────────────────────────────────
echo "── R-DIAGRAMME (Hero + Gantt)"
for svg in entwicklung-arbeitspakete-1 entwicklung-arbeitspakete-2; do
  if head -c 60 "$SITE/images/mermaid/$svg.svg" 2>/dev/null | grep -q "<svg"; then
    pass "$svg.svg valide"
  else
    fail "$svg.svg fehlt/ungültig"
  fi
done
check "Gantt verdrahtet (roadmapSvgUrl)" grep -q "entwicklung-arbeitspakete-2.svg" "$SITE/javascripts/icon-rail.js"
if grep -qE '^\s*addRoadmapBadge\(\);' "$SITE/javascripts/icon-rail.js"; then
  pass "Roadmap-Badge aktiv"
else
  fail "Roadmap-Badge nicht aktiv (auskommentiert?)"
fi

# ── R-NO-PLACEHOLDER ─────────────────────────────────────────────────────────
echo "── R-NO-PLACEHOLDER"
if grep -rEl '__PROJEKT__|__ROADMAP_GANTT__|ADAPT:|= *.0\.0\.0.' "$JS" >/dev/null 2>&1; then
  fail "Platzhalter/ADAPT-Reste in docs/javascripts/"
else
  pass "keine Platzhalter/ADAPT-Reste"
fi

# ── R-NO-CDN ─────────────────────────────────────────────────────────────────
echo "── R-NO-CDN"
if grep -rEoh '<(script|link)[^>]+(src|href)="https?://[^"]+\.(js|css)"' "$SITE" 2>/dev/null | grep -q .; then
  fail "CDN-Referenz in site/ gefunden"
else
  pass "keine CDN-Referenzen (alles lokal)"
fi

# ── R-APPIMAGE ───────────────────────────────────────────────────────────────
echo "── R-APPIMAGE (frisch + 3 Ziele byte-gleich)"
check "release/$APPIMAGE existiert" test -f "$PROJECT_DIR/release/$APPIMAGE"
check "build/  == release/" cmp -s "$PROJECT_DIR/build/$APPIMAGE" "$PROJECT_DIR/release/$APPIMAGE"
check "release == global ($GLOBAL_DIR)" cmp -s "$PROJECT_DIR/release/$APPIMAGE" "$GLOBAL_DIR/$APPIMAGE"

# ── R-AP-SYNC ────────────────────────────────────────────────────────────────
echo "── R-AP-SYNC (Arbeitspakete)"
check "arbeitspakete.md vorhanden" test -f "$DOCS_DIR/docs/entwicklung/arbeitspakete.md"
check "Flowchart + Gantt referenziert" bash -c \
  "grep -q arbeitspakete-1.svg '$DOCS_DIR/docs/entwicklung/arbeitspakete.md' && grep -q arbeitspakete-2.svg '$DOCS_DIR/docs/entwicklung/arbeitspakete.md'"

# ── Ergebnis ─────────────────────────────────────────────────────────────────
echo ""
if [ "$FAILS" -eq 0 ]; then
  echo -e "${GREEN}═══ ALLE REGELN GRÜN — Doku ist fertig ═══${NC}"
  exit 0
else
  echo -e "${RED}═══ $FAILS REGEL(N) ROT — Doku NICHT fertig ═══${NC}"
  exit 1
fi
