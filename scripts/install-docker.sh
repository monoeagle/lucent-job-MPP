#!/bin/bash
# Offline Docker Installer — Detects distro and installs Docker from local packages
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PKG_DIR="$BUNDLE_DIR/docker-packages"

echo -e "${YELLOW}MPP — Offline Docker Installation${NC}"
echo ""

# Detect distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_ID="$ID"
    DISTRO_LIKE="$ID_LIKE"
else
    echo -e "${RED}Kann Betriebssystem nicht erkennen.${NC}"
    exit 1
fi

echo "Erkannt: $PRETTY_NAME"

install_deb() {
    local dir="$PKG_DIR/mint"
    if [ ! -d "$dir" ] || [ -z "$(ls -A "$dir"/*.deb 2>/dev/null)" ]; then
        echo -e "${RED}Keine .deb-Pakete gefunden in $dir${NC}"
        echo -e "Baue das Bundle neu mit: ${YELLOW}bash scripts/build-bundle.sh${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Installiere Docker aus .deb-Paketen...${NC}"
    sudo dpkg -i "$dir"/*.deb || sudo apt-get install -f -y
    echo -e "${GREEN}✓${NC} Docker installiert"
}

install_rpm() {
    local dir="$PKG_DIR/alma"
    if [ ! -d "$dir" ] || [ -z "$(ls -A "$dir"/*.rpm 2>/dev/null)" ]; then
        echo -e "${RED}Keine .rpm-Pakete gefunden in $dir${NC}"
        echo -e "Baue das Bundle neu mit: ${YELLOW}bash scripts/build-bundle.sh${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Installiere Docker aus .rpm-Paketen...${NC}"
    sudo rpm -ivh "$dir"/*.rpm --nodeps 2>/dev/null || sudo dnf localinstall -y "$dir"/*.rpm
    echo -e "${GREEN}✓${NC} Docker installiert"
}

case "$DISTRO_ID" in
    linuxmint|ubuntu|debian)
        install_deb
        ;;
    almalinux|rocky|rhel|centos|fedora)
        install_rpm
        ;;
    *)
        if echo "$DISTRO_LIKE" | grep -q "debian\|ubuntu"; then
            install_deb
        elif echo "$DISTRO_LIKE" | grep -q "rhel\|fedora"; then
            install_rpm
        else
            echo -e "${RED}Nicht unterstuetzte Distribution: $DISTRO_ID${NC}"
            echo "Unterstuetzt: Linux Mint, Ubuntu, Debian, AlmaLinux, Rocky, RHEL"
            exit 1
        fi
        ;;
esac

# Start Docker
echo ""
echo -e "${YELLOW}Starte Docker-Service...${NC}"
sudo systemctl enable docker
sudo systemctl start docker

# Add current user to docker group
if ! groups | grep -q docker; then
    sudo usermod -aG docker "$USER"
    echo -e "${YELLOW}User '$USER' zur docker-Gruppe hinzugefuegt.${NC}"
    echo -e "${YELLOW}Bitte abmelden und neu anmelden, damit die Aenderung wirkt.${NC}"
fi

echo ""
echo -e "${GREEN}✓ Docker ist bereit: $(docker --version)${NC}"
