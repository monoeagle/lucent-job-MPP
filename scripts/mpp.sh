#!/bin/bash
# Marketplace Portal — Dev Launcher
# Unified menu for starting backend, frontend, docs, or all.

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PID=""
FRONTEND_PID=""
DOCS_PID=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping services...${NC}"
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && echo "  Backend stopped."
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && echo "  Frontend stopped."
    [ -n "$DOCS_PID" ] && kill "$DOCS_PID" 2>/dev/null && echo "  Docs stopped."
    BACKEND_PID=""
    FRONTEND_PID=""
    DOCS_PID=""
}

trap cleanup EXIT

wait_for_enter() {
    echo ""
    echo -e "${YELLOW}Drücke ENTER um zum Menü zurückzukehren...${NC}"
    read -r
}

# ── Prereq Checks ──────────────────────────────────────────

check_postgres() {
    if pg_isready -q 2>/dev/null; then
        echo -e "  PostgreSQL:  ${GREEN}running${NC}"
        return 0
    else
        echo -e "  PostgreSQL:  ${RED}not running${NC}"
        return 1
    fi
}

check_node() {
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    if nvm use 22 >/dev/null 2>&1; then
        echo -e "  Node.js:     ${GREEN}$(node --version)${NC}"
        return 0
    else
        echo -e "  Node.js 22:  ${RED}not available${NC} (run: nvm install 22)"
        return 1
    fi
}

check_venv() {
    if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
        echo -e "  Python venv: ${GREEN}found${NC}"
        return 0
    else
        echo -e "  Python venv: ${RED}not found${NC}"
        echo -e "  ${YELLOW}Erstelle venv...${NC}"
        python3 -m venv "$PROJECT_DIR/venv" && \
            source "$PROJECT_DIR/venv/bin/activate" && \
            pip install -r "$PROJECT_DIR/requirements.txt" -q
        if [ $? -eq 0 ]; then
            echo -e "  Python venv: ${GREEN}erstellt${NC}"
            return 0
        else
            echo -e "  Python venv: ${RED}Installation fehlgeschlagen${NC}"
            return 1
        fi
    fi
}

check_docs_venv() {
    local DOCS_VENV="$PROJECT_DIR/mpp-docs/.venv-docs"
    if [ -f "$DOCS_VENV/bin/activate" ]; then
        echo -e "  Docs venv:   ${GREEN}found${NC}"
        return 0
    else
        echo -e "  Docs venv:   ${YELLOW}not found — erstelle...${NC}"
        python3 -m venv "$DOCS_VENV" && \
            source "$DOCS_VENV/bin/activate" && \
            pip install zensical -q 2>&1
        if [ $? -eq 0 ]; then
            echo -e "  Docs venv:   ${GREEN}erstellt + zensical installiert${NC}"
            deactivate 2>/dev/null
            return 0
        else
            echo -e "  Docs venv:   ${RED}Installation fehlgeschlagen${NC}"
            return 1
        fi
    fi
}

check_frontend_deps() {
    if [ -d "$PROJECT_DIR/frontend/node_modules" ]; then
        echo -e "  node_modules:${GREEN} found${NC}"
        return 0
    else
        echo -e "  node_modules:${YELLOW} not found — installiere...${NC}"
        cd "$PROJECT_DIR/frontend" && npm install -q 2>&1
        if [ $? -eq 0 ]; then
            echo -e "  node_modules:${GREEN} installiert${NC}"
            return 0
        else
            echo -e "  node_modules:${RED} Installation fehlgeschlagen${NC}"
            return 1
        fi
    fi
}

# ── Status ──────────────────────────────────────────────────

status_line() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "  Backend:     ${GREEN}running${NC} (PID $BACKEND_PID) → http://localhost:5000/api/v1/health"
    else
        BACKEND_PID=""
        echo -e "  Backend:     ${RED}stopped${NC}"
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "  Frontend:    ${GREEN}running${NC} (PID $FRONTEND_PID) → http://localhost:3000"
    else
        FRONTEND_PID=""
        echo -e "  Frontend:    ${RED}stopped${NC}"
    fi
    if [ -n "$DOCS_PID" ] && kill -0 "$DOCS_PID" 2>/dev/null; then
        echo -e "  Docs:        ${GREEN}running${NC} (PID $DOCS_PID) → http://localhost:5078"
    else
        DOCS_PID=""
        echo -e "  Docs:        ${RED}stopped${NC}"
    fi
}

# ── Backend ─────────────────────────────────────────────────

start_backend() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "${YELLOW}Backend läuft bereits (PID $BACKEND_PID).${NC}"
        wait_for_enter
        return
    fi

    echo -e "${CYAN}Backend starten...${NC}"
    cd "$PROJECT_DIR"

    if ! check_venv; then wait_for_enter; return; fi
    if ! check_postgres; then
        echo -e "${RED}PostgreSQL muss laufen. Bitte starten: sudo systemctl start postgresql${NC}"
        wait_for_enter; return
    fi

    source venv/bin/activate
    export AUTH_MODE=stub
    export CMDB_MODE=stub
    export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
    export FLASK_APP=app

    echo "  Datenbank-Schema pruefen..."
    python -c "
from app.data.db.session import get_engine, Base
from app.data.db.models import *
engine = get_engine('$DATABASE_URL')
Base.metadata.create_all(engine)
" 2>&1 || {
        echo -e "${RED}Schema-Erstellung fehlgeschlagen!${NC}"
        wait_for_enter; return
    }

    echo "  Demo-Daten laden..."
    python scripts/seed.py 2>&1

    echo "  Flask starten auf Port 5000..."
    flask run --port 5000 > "$PROJECT_DIR/logs/backend.log" 2>&1 &
    BACKEND_PID=$!
    sleep 1

    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "${GREEN}Backend gestartet (PID $BACKEND_PID)${NC}"
        echo -e "  Health: ${BOLD}http://localhost:5000/api/v1/health${NC}"
        echo -e "  Log:    tail -f logs/backend.log"
    else
        echo -e "${RED}Backend konnte nicht gestartet werden!${NC}"
        echo "  Log-Ausgabe:"
        cat "$PROJECT_DIR/logs/backend.log" 2>/dev/null
        BACKEND_PID=""
    fi
    wait_for_enter
}

stop_backend() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null
        echo -e "${YELLOW}Backend gestoppt.${NC}"
        BACKEND_PID=""
    else
        echo -e "${YELLOW}Backend läuft nicht.${NC}"
    fi
    wait_for_enter
}

# ── Frontend ────────────────────────────────────────────────

start_frontend() {
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "${YELLOW}Frontend läuft bereits (PID $FRONTEND_PID).${NC}"
        wait_for_enter
        return
    fi

    echo -e "${CYAN}Frontend starten...${NC}"
    cd "$PROJECT_DIR"

    if ! check_node; then wait_for_enter; return; fi
    if ! check_frontend_deps; then wait_for_enter; return; fi

    cd frontend
    echo "  Vite starten auf Port 3000..."
    npx vite --port 3000 > "$PROJECT_DIR/logs/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    sleep 2

    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "${GREEN}Frontend gestartet (PID $FRONTEND_PID)${NC}"
        echo -e "  URL:    ${BOLD}http://localhost:3000${NC}"
        echo -e "  Login:  test-requester (kein Passwort)"
        echo -e "  Log:    tail -f logs/frontend.log"
    else
        echo -e "${RED}Frontend konnte nicht gestartet werden!${NC}"
        echo "  Log-Ausgabe:"
        cat "$PROJECT_DIR/logs/frontend.log" 2>/dev/null
        FRONTEND_PID=""
    fi
    wait_for_enter
}

stop_frontend() {
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null
        echo -e "${YELLOW}Frontend gestoppt.${NC}"
        FRONTEND_PID=""
    else
        echo -e "${YELLOW}Frontend läuft nicht.${NC}"
    fi
    wait_for_enter
}

# ── Docs ────────────────────────────────────────────────────

start_docs() {
    if [ -n "$DOCS_PID" ] && kill -0 "$DOCS_PID" 2>/dev/null; then
        echo -e "${YELLOW}Docs läuft bereits (PID $DOCS_PID).${NC}"
        wait_for_enter
        return
    fi

    echo -e "${CYAN}Dokumentation starten...${NC}"
    cd "$PROJECT_DIR"

    if ! check_docs_venv; then wait_for_enter; return; fi

    cd mpp-docs
    source .venv-docs/bin/activate

    echo "  Zensical starten auf Port 5078..."
    python -m zensical serve --dev-addr 0.0.0.0:5078 > "$PROJECT_DIR/logs/docs.log" 2>&1 &
    DOCS_PID=$!
    sleep 2

    if kill -0 "$DOCS_PID" 2>/dev/null; then
        echo -e "${GREEN}Docs gestartet (PID $DOCS_PID)${NC}"
        echo -e "  URL:    ${BOLD}http://localhost:5078${NC}"
        echo -e "  Log:    tail -f logs/docs.log"
    else
        echo -e "${RED}Docs konnten nicht gestartet werden!${NC}"
        echo "  Log-Ausgabe:"
        cat "$PROJECT_DIR/logs/docs.log" 2>/dev/null
        DOCS_PID=""
    fi
    deactivate 2>/dev/null
    wait_for_enter
}

stop_docs() {
    if [ -n "$DOCS_PID" ] && kill -0 "$DOCS_PID" 2>/dev/null; then
        kill "$DOCS_PID" 2>/dev/null
        echo -e "${YELLOW}Docs gestoppt.${NC}"
        DOCS_PID=""
    else
        echo -e "${YELLOW}Docs läuft nicht.${NC}"
    fi
    wait_for_enter
}

# ── Alles starten ───────────────────────────────────────────

start_all() {
    echo -e "${CYAN}Backend + Frontend + Docs starten...${NC}"
    echo ""

    # Backend
    if [ -z "$BACKEND_PID" ] || ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        cd "$PROJECT_DIR"
        if check_venv && check_postgres; then
            source venv/bin/activate
            export AUTH_MODE=stub CMDB_MODE=stub FLASK_APP=app
            export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
            python -c "
from app.data.db.session import get_engine, Base
from app.data.db.models import *
engine = get_engine('$DATABASE_URL')
Base.metadata.create_all(engine)
" > /dev/null 2>&1
            python scripts/seed.py 2>/dev/null
            flask run --port 5000 > "$PROJECT_DIR/logs/backend.log" 2>&1 &
            BACKEND_PID=$!; sleep 1
            if kill -0 "$BACKEND_PID" 2>/dev/null; then
                echo -e "  Backend:  ${GREEN}gestartet${NC} (PID $BACKEND_PID)"
            else
                echo -e "  Backend:  ${RED}fehlgeschlagen${NC} — siehe logs/backend.log"
                BACKEND_PID=""
            fi
        fi
    else echo -e "  Backend:  ${GREEN}läuft bereits${NC}"; fi

    # Frontend
    if [ -z "$FRONTEND_PID" ] || ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        cd "$PROJECT_DIR"
        if check_node; then
            check_frontend_deps > /dev/null 2>&1
            cd frontend
            npx vite --port 3000 > "$PROJECT_DIR/logs/frontend.log" 2>&1 &
            FRONTEND_PID=$!; sleep 2
            if kill -0 "$FRONTEND_PID" 2>/dev/null; then
                echo -e "  Frontend: ${GREEN}gestartet${NC} (PID $FRONTEND_PID)"
            else
                echo -e "  Frontend: ${RED}fehlgeschlagen${NC} — siehe logs/frontend.log"
                FRONTEND_PID=""
            fi
        fi
    else echo -e "  Frontend: ${GREEN}läuft bereits${NC}"; fi

    # Docs
    if [ -z "$DOCS_PID" ] || ! kill -0 "$DOCS_PID" 2>/dev/null; then
        cd "$PROJECT_DIR"
        if check_docs_venv > /dev/null 2>&1; then
            cd mpp-docs && source .venv-docs/bin/activate
            python -m zensical serve --dev-addr 0.0.0.0:5078 > "$PROJECT_DIR/logs/docs.log" 2>&1 &
            DOCS_PID=$!; sleep 2
            deactivate 2>/dev/null
            if kill -0 "$DOCS_PID" 2>/dev/null; then
                echo -e "  Docs:     ${GREEN}gestartet${NC} (PID $DOCS_PID)"
            else
                echo -e "  Docs:     ${RED}fehlgeschlagen${NC} — siehe logs/docs.log"
                DOCS_PID=""
            fi
        fi
    else echo -e "  Docs:     ${GREEN}läuft bereits${NC}"; fi

    echo ""
    echo -e "${BOLD}Portal:    http://localhost:3000${NC}  (Login: test-requester)"
    echo -e "${BOLD}API:       http://localhost:5000/api/v1/health${NC}"
    echo -e "${BOLD}Docs:      http://localhost:5078${NC}"
    wait_for_enter
}

# ── Logs ────────────────────────────────────────────────────

show_logs() {
    echo -e "${CYAN}=== Backend Log (letzte 20 Zeilen) ===${NC}"
    tail -20 "$PROJECT_DIR/logs/backend.log" 2>/dev/null || echo "  (kein Log)"
    echo ""
    echo -e "${CYAN}=== Frontend Log (letzte 20 Zeilen) ===${NC}"
    tail -20 "$PROJECT_DIR/logs/frontend.log" 2>/dev/null || echo "  (kein Log)"
    echo ""
    echo -e "${CYAN}=== Docs Log (letzte 20 Zeilen) ===${NC}"
    tail -20 "$PROJECT_DIR/logs/docs.log" 2>/dev/null || echo "  (kein Log)"
    wait_for_enter
}

# ── Tests ───────────────────────────────────────────────────

run_tests() {
    echo -e "${CYAN}Tests ausführen...${NC}"
    echo ""
    echo "  [1] Backend-Tests (pytest)"
    echo "  [2] Frontend-Tests (vitest)"
    echo "  [3] Alle Tests"
    echo "  [0] Zurück"
    echo ""
    read -rp "Wahl: " test_choice

    cd "$PROJECT_DIR"
    case $test_choice in
        1)
            source venv/bin/activate
            export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test
            pytest tests/ --tb=short -q 2>&1
            ;;
        2)
            export NVM_DIR="$HOME/.nvm"
            [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
            nvm use 22 >/dev/null 2>&1
            cd frontend && npx vitest run 2>&1
            ;;
        3)
            source venv/bin/activate
            export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test
            echo -e "${CYAN}--- Backend ---${NC}"
            pytest tests/ --tb=short -q 2>&1
            echo ""
            echo -e "${CYAN}--- Frontend ---${NC}"
            export NVM_DIR="$HOME/.nvm"
            [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
            nvm use 22 >/dev/null 2>&1
            cd "$PROJECT_DIR/frontend" && npx vitest run 2>&1
            ;;
        0) return ;;
    esac
    wait_for_enter
}

# ── DB Reset ───────────────────────────────────────────────

reset_database() {
    echo -e "${RED}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ACHTUNG: Datenbank wird komplett gelöscht!  ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Dies löscht ALLE Daten (Orders, Templates, Subscriptions, etc.)"
    echo "  und spielt die Demo-Daten neu ein."
    echo ""
    read -rp "  Wirklich fortfahren? (j/N) " -n 1
    echo ""

    if [[ ! $REPLY =~ ^[jJyY]$ ]]; then
        echo "  Abgebrochen."
        wait_for_enter
        return
    fi

    # Stop backend if running
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "  ${YELLOW}Backend wird gestoppt...${NC}"
        kill "$BACKEND_PID" 2>/dev/null
        BACKEND_PID=""
        sleep 1
    fi

    cd "$PROJECT_DIR"
    if ! check_venv > /dev/null 2>&1; then
        echo -e "${RED}Python venv nicht gefunden.${NC}"
        wait_for_enter; return
    fi
    if ! check_postgres > /dev/null 2>&1; then
        echo -e "${RED}PostgreSQL muss laufen.${NC}"
        wait_for_enter; return
    fi

    source venv/bin/activate
    export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev

    echo ""
    echo -e "  ${YELLOW}Lösche Datenbank...${NC}"
    psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>&1 || {
        echo -e "  ${RED}DB-Drop fehlgeschlagen. Versuche dropdb/createdb...${NC}"
        dropdb mpp_dev 2>/dev/null
        createdb -O mpp mpp_dev 2>/dev/null
    }

    echo -e "  ${YELLOW}Schema erstellen...${NC}"
    python -c "
from app.data.db.session import get_engine, Base
from app.data.db.models import *
engine = get_engine('$DATABASE_URL')
Base.metadata.create_all(engine)
print('  Schema erstellt.')
" 2>&1

    echo -e "  ${YELLOW}Demo-Daten laden...${NC}"
    python scripts/seed.py 2>&1

    echo ""
    echo -e "  ${GREEN}✓ Datenbank zurückgesetzt und neu befüllt!${NC}"
    echo -e "  ${GREEN}  Alle Templates mit aktuellen Parametern geladen.${NC}"
    wait_for_enter
}

# ── Main ────────────────────────────────────────────────────

mkdir -p "$PROJECT_DIR/logs"

while true; do
    clear
    echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║   Marketplace Portal — Dev Launcher           ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Status:${NC}"
    status_line
    echo ""
    echo -e "${CYAN}Starten:${NC}"
    echo "  [1] Backend       (Flask :5000)"
    echo "  [2] Frontend      (Vite :3000)"
    echo "  [3] Dokumentation (Zensical :5078)"
    echo "  [4] Alles starten"
    echo ""
    echo -e "${CYAN}Stoppen:${NC}"
    echo "  [5] Backend stoppen"
    echo "  [6] Frontend stoppen"
    echo "  [7] Docs stoppen"
    echo ""
    echo -e "${CYAN}Tools:${NC}"
    echo "  [8] Logs anzeigen"
    echo "  [9] Tests ausführen"
    echo -e "  [r] ${RED}DB Reset + Neu-Seed${NC}"
    echo ""
    echo -e "${CYAN}Demo-Zugaenge:${NC}"
    echo -e "  test-requester   ${YELLOW}Besteller${NC}"
    echo -e "  test-approver    ${YELLOW}Genehmiger${NC}"
    echo -e "  test-admin       ${YELLOW}Administrator${NC}"
    echo -e "  test-multi       ${YELLOW}Alle Rollen${NC}"
    echo -e "  test-superadmin  ${YELLOW}Super Admin${NC}"
    echo -e "  ${BOLD}Passwort: stub-password${NC}"
    echo ""
    echo "  [q] Beenden"
    echo ""
    read -rp "Wahl: " choice

    case $choice in
        1) start_backend ;;
        2) start_frontend ;;
        3) start_docs ;;
        4) start_all ;;
        5) stop_backend ;;
        6) stop_frontend ;;
        7) stop_docs ;;
        8) show_logs ;;
        9) run_tests ;;
        r|R) reset_database ;;
        q|Q) echo -e "${YELLOW}Bye!${NC}"; exit 0 ;;
        *) echo -e "${RED}Ungültige Eingabe.${NC}"; sleep 1 ;;
    esac
done
