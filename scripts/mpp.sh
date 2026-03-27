#!/bin/bash
# Marketplace Portal — Dev Launcher
# Unified menu for starting backend, frontend, or both.

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

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
    BACKEND_PID=""
    FRONTEND_PID=""
}

trap cleanup EXIT

wait_for_enter() {
    echo ""
    echo -e "${YELLOW}Drücke ENTER um zum Menü zurückzukehren...${NC}"
    read -r
}

check_postgres() {
    if pg_isready -q 2>/dev/null; then
        echo -e "  PostgreSQL: ${GREEN}running${NC}"
        return 0
    else
        echo -e "  PostgreSQL: ${RED}not running${NC}"
        return 1
    fi
}

check_node() {
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    if nvm use 22 >/dev/null 2>&1; then
        echo -e "  Node.js:    ${GREEN}$(node --version)${NC}"
        return 0
    else
        echo -e "  Node.js 22: ${RED}not available${NC} (run: nvm install 22)"
        return 1
    fi
}

check_venv() {
    if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
        echo -e "  Python venv:${GREEN} found${NC}"
        return 0
    else
        echo -e "  Python venv:${RED} not found${NC} (run: python3 -m venv venv && pip install -r requirements.txt)"
        return 1
    fi
}

status_line() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "  Backend:    ${GREEN}running${NC} (PID $BACKEND_PID) → http://localhost:5000/api/v1/health"
    else
        BACKEND_PID=""
        echo -e "  Backend:    ${RED}stopped${NC}"
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "  Frontend:   ${GREEN}running${NC} (PID $FRONTEND_PID) → http://localhost:3000"
    else
        FRONTEND_PID=""
        echo -e "  Frontend:   ${RED}stopped${NC}"
    fi
}

start_backend() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "${YELLOW}Backend läuft bereits (PID $BACKEND_PID).${NC}"
        wait_for_enter
        return
    fi

    echo -e "${CYAN}Backend starten...${NC}"
    cd "$PROJECT_DIR"

    if ! check_venv; then
        wait_for_enter
        return
    fi

    if ! check_postgres; then
        echo -e "${RED}PostgreSQL muss laufen. Bitte starten: sudo systemctl start postgresql${NC}"
        wait_for_enter
        return
    fi

    source venv/bin/activate
    export AUTH_MODE=stub
    export CMDB_MODE=stub
    export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
    export FLASK_APP=app

    echo "  Datenbank-Migrationen..."
    if ! alembic upgrade head 2>&1; then
        echo -e "${RED}Migration fehlgeschlagen!${NC}"
        wait_for_enter
        return
    fi

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

start_frontend() {
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "${YELLOW}Frontend läuft bereits (PID $FRONTEND_PID).${NC}"
        wait_for_enter
        return
    fi

    echo -e "${CYAN}Frontend starten...${NC}"
    cd "$PROJECT_DIR"

    if ! check_node; then
        wait_for_enter
        return
    fi

    cd frontend

    if [ ! -d "node_modules" ]; then
        echo "  Dependencies installieren..."
        if ! npm install 2>&1; then
            echo -e "${RED}npm install fehlgeschlagen!${NC}"
            wait_for_enter
            return
        fi
    fi

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

start_both() {
    echo -e "${CYAN}Backend + Frontend starten...${NC}"

    # Backend
    if [ -z "$BACKEND_PID" ] || ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        cd "$PROJECT_DIR"
        if check_venv && check_postgres; then
            source venv/bin/activate
            export AUTH_MODE=stub
            export CMDB_MODE=stub
            export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
            export FLASK_APP=app
            alembic upgrade head > /dev/null 2>&1
            python scripts/seed.py 2>/dev/null
            flask run --port 5000 > "$PROJECT_DIR/logs/backend.log" 2>&1 &
            BACKEND_PID=$!
            sleep 1
            if kill -0 "$BACKEND_PID" 2>/dev/null; then
                echo -e "  Backend:  ${GREEN}gestartet${NC} (PID $BACKEND_PID)"
            else
                echo -e "  Backend:  ${RED}fehlgeschlagen${NC}"
                BACKEND_PID=""
            fi
        fi
    else
        echo -e "  Backend:  ${GREEN}läuft bereits${NC}"
    fi

    # Frontend
    if [ -z "$FRONTEND_PID" ] || ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        cd "$PROJECT_DIR"
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
        nvm use 22 >/dev/null 2>&1
        cd frontend
        [ ! -d "node_modules" ] && npm install > /dev/null 2>&1
        npx vite --port 3000 > "$PROJECT_DIR/logs/frontend.log" 2>&1 &
        FRONTEND_PID=$!
        sleep 2
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            echo -e "  Frontend: ${GREEN}gestartet${NC} (PID $FRONTEND_PID)"
        else
            echo -e "  Frontend: ${RED}fehlgeschlagen${NC}"
            FRONTEND_PID=""
        fi
    else
        echo -e "  Frontend: ${GREEN}läuft bereits${NC}"
    fi

    echo ""
    echo -e "${BOLD}Portal: http://localhost:3000${NC}"
    echo -e "Login:  test-requester (kein Passwort)"
    wait_for_enter
}

show_logs() {
    echo -e "${CYAN}=== Backend Log (letzte 20 Zeilen) ===${NC}"
    tail -20 "$PROJECT_DIR/logs/backend.log" 2>/dev/null || echo "  (kein Log vorhanden)"
    echo ""
    echo -e "${CYAN}=== Frontend Log (letzte 20 Zeilen) ===${NC}"
    tail -20 "$PROJECT_DIR/logs/frontend.log" 2>/dev/null || echo "  (kein Log vorhanden)"
    wait_for_enter
}

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

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Main menu loop
while true; do
    clear
    echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║   Marketplace Portal — Dev Launcher      ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Status:${NC}"
    status_line
    echo ""
    echo -e "${CYAN}Aktionen:${NC}"
    echo "  [1] Backend starten"
    echo "  [2] Frontend starten"
    echo "  [3] Beides starten"
    echo "  [4] Backend stoppen"
    echo "  [5] Frontend stoppen"
    echo "  [6] Logs anzeigen"
    echo "  [7] Tests ausführen"
    echo ""
    echo "  [q] Beenden"
    echo ""
    read -rp "Wahl: " choice

    case $choice in
        1) start_backend ;;
        2) start_frontend ;;
        3) start_both ;;
        4) stop_backend ;;
        5) stop_frontend ;;
        6) show_logs ;;
        7) run_tests ;;
        q|Q) echo -e "${YELLOW}Bye!${NC}"; exit 0 ;;
        *) echo -e "${RED}Ungültige Eingabe.${NC}"; sleep 1 ;;
    esac
done
