#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# install.sh — MPP (Flask + React) OFFLINE-Installer für AlmaLinux/Rocky 9
#
# Installiert das Marketplace Portal aus diesem Release-Bundle OHNE Internet:
# venv + Wheels (--no-index), PostgreSQL-DB-Anlage, env, alembic-Migrationen,
# systemd (gunicorn), nginx + TLS (liefert die prebuilt React-SPA statisch aus
# und proxyt /api). Spiegelt docs/vm-installation-offline.md (single source of
# truth). Es gibt KEIN Redis/Celery — Flask hat keine Background-Jobs.
#
# Aufruf auf der Ziel-VM (im entpackten Bundle-Ordner), als root:
#     sudo ./deploy/install.sh
#
# Voraussetzungen auf der VM (siehe START-HIER.txt / Doku §7–§8):
#   - AlmaLinux/Rocky 9, x86_64
#   - python3.12, postgresql16-server, nginx installiert & gestartet
#     (Online: dnf install …; Offline: aus rpms/ — siehe Doku §2/§7)
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ROOT="/opt/mpp"
SRC_DIR="$APP_ROOT/src"          # app/, migrations/, alembic.ini, stubs/, scripts/
SPA_DIR="$APP_ROOT/frontend"     # statische React-SPA (von nginx ausgeliefert)
VENV="$APP_ROOT/venv"
ENV_FILE="/etc/mpp/mpp.env"
SVC_USER="mpp"
PY="python3.12"

C_OK=$'\e[0;32m'; C_INFO=$'\e[0;36m'; C_WARN=$'\e[1;33m'; C_ERR=$'\e[0;31m'; C_NC=$'\e[0m'
ok()   { echo "${C_OK}  ✓${C_NC} $1"; }
info() { echo "${C_INFO}  →${C_NC} $1"; }
warn() { echo "${C_WARN}  ⚠${C_NC} $1"; }
die()  { echo "${C_ERR}  ✗${C_NC} $1" >&2; exit 1; }
hdr()  { echo; echo "${C_INFO}═══ $1 ═══${C_NC}"; }

[ "$(id -u)" -eq 0 ] || die "Bitte als root ausführen:  sudo ./deploy/install.sh"

# ── 0. Preflight ──────────────────────────────────────────────────────────────
hdr "0/8  Preflight"
[ -d "$BUNDLE_DIR/app" ]            || die "app/ fehlt im Bundle (falsches Verzeichnis?)"
[ -d "$BUNDLE_DIR/wheels" ]         || die "wheels/ fehlt im Bundle"
[ -d "$BUNDLE_DIR/frontend-dist" ]  || die "frontend-dist/ fehlt im Bundle (SPA nicht gebaut?)"
[ -f "$BUNDLE_DIR/requirements.txt" ] || die "requirements.txt fehlt"
[ -f "$BUNDLE_DIR/alembic.ini" ]    || die "alembic.ini fehlt"
command -v "$PY" >/dev/null   || die "$PY nicht gefunden — zuerst python3.12 installieren (Doku §7)"
"$PY" -c 'import sys; assert sys.version_info[:2]==(3,12)' 2>/dev/null \
  || warn "$PY ist nicht 3.12 — Wheels sind für 3.12 gebaut, Mismatch möglich"
command -v psql >/dev/null    || warn "psql nicht gefunden — ist PostgreSQL installiert? (Doku §8)"
ok "Bundle vollständig, $PY vorhanden"

# ── 1. Eingaben ───────────────────────────────────────────────────────────────
hdr "1/8  Konfiguration"
read -rp "  FQDN der VM (z.B. mpp.internal.example.com): " FQDN
[ -n "$FQDN" ] || die "FQDN ist Pflicht"
read -rsp "  Passwort für DB-User 'mpp' (leer = zufällig): " DBPW; echo
[ -n "$DBPW" ] || { DBPW="$("$PY" -c 'import secrets;print(secrets.token_urlsafe(24))')"; info "DB-Passwort generiert"; }
JWT_SECRET="$("$PY" -c 'import secrets;print(secrets.token_urlsafe(64))')"
ok "Konfiguration erfasst (JWT_SECRET generiert)"

# ── 2. Service-User + App-Code ────────────────────────────────────────────────
hdr "2/8  Service-User + App-Code"
id "$SVC_USER" &>/dev/null || useradd --system --create-home --home-dir "$APP_ROOT" --shell /usr/sbin/nologin "$SVC_USER"
mkdir -p "$SRC_DIR" "$SPA_DIR" /etc/mpp
cp -a "$BUNDLE_DIR/app"            "$SRC_DIR/"
cp -a "$BUNDLE_DIR/migrations"     "$SRC_DIR/"
cp -a "$BUNDLE_DIR/stubs"          "$SRC_DIR/"
cp -a "$BUNDLE_DIR/scripts"        "$SRC_DIR/" 2>/dev/null || true
cp -a "$BUNDLE_DIR/alembic.ini"    "$SRC_DIR/"
cp -a "$BUNDLE_DIR/requirements.txt" "$SRC_DIR/"
cp -a "$BUNDLE_DIR/wheels"         "$APP_ROOT/"
cp -a "$BUNDLE_DIR/frontend-dist/." "$SPA_DIR/"
chown -R "$SVC_USER:$SVC_USER" "$APP_ROOT"
ok "App nach $SRC_DIR, SPA nach $SPA_DIR kopiert"

# ── 3. venv + Wheels offline ──────────────────────────────────────────────────
hdr "3/8  venv + Wheels (offline, --no-index)"
sudo -u "$SVC_USER" "$PY" -m venv "$VENV"
sudo -u "$SVC_USER" "$VENV/bin/pip" install --no-index --find-links="$APP_ROOT/wheels" --upgrade pip setuptools wheel
sudo -u "$SVC_USER" "$VENV/bin/pip" install --no-index --find-links="$APP_ROOT/wheels" -r "$SRC_DIR/requirements.txt"
sudo -u "$SVC_USER" "$VENV/bin/python" -c "import flask,gunicorn,sqlalchemy,alembic,psycopg2; print('Imports OK')"
ok "Abhängigkeiten offline installiert"

# ── 4. Datenbank ──────────────────────────────────────────────────────────────
hdr "4/8  PostgreSQL-Datenbank"
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='mpp'" 2>/dev/null | grep -q 1; then
  sudo -u postgres psql -c "ALTER ROLE mpp WITH PASSWORD '${DBPW}';" >/dev/null
  info "Rolle 'mpp' existierte — Passwort aktualisiert"
else
  sudo -u postgres psql >/dev/null <<SQL
CREATE ROLE mpp WITH LOGIN PASSWORD '${DBPW}';
CREATE DATABASE mpp_prod OWNER mpp ENCODING 'UTF8' TEMPLATE template0;
GRANT ALL PRIVILEGES ON DATABASE mpp_prod TO mpp;
SQL
  ok "DB 'mpp_prod' + Rolle 'mpp' angelegt"
fi

# ── 5. Umgebungsdatei ─────────────────────────────────────────────────────────
hdr "5/8  Umgebungsdatei $ENV_FILE"
cat > "$ENV_FILE" <<ENV
ENV=production
# ⚠ AUTH_MODE=ldap ist die korrekte Produktions-Einstellung, ABER der LDAP-Login
#   wirft aktuell NotImplementedError (siehe docs/vm-installation.md). Bis LDAP
#   implementiert ist, kann sich niemand einloggen. Für eine reine DEMO ohne
#   echten Produktiv-Anspruch: ENV=development + AUTH_MODE=stub setzen.
AUTH_MODE=ldap
JWT_SECRET=${JWT_SECRET}
DATABASE_URL=postgresql://mpp:${DBPW}@127.0.0.1:5432/mpp_prod
CMDB_MODE=stub
CMDB_STUB_DATA_PATH=./stubs/cmdb/
ENV
chown root:"$SVC_USER" "$ENV_FILE"; chmod 640 "$ENV_FILE"
ok "$ENV_FILE geschrieben (DB-Passwort + JWT_SECRET enthalten)"

# ── 6. Migrationen (alembic) ──────────────────────────────────────────────────
hdr "6/8  alembic-Migrationen"
sudo -u "$SVC_USER" env $(grep -v '^#' "$ENV_FILE" | xargs) \
  "$VENV/bin/alembic" -c "$SRC_DIR/alembic.ini" upgrade head \
  || die "alembic upgrade head fehlgeschlagen — DB erreichbar? (Doku §8)"
ok "DB-Schema migriert (alembic upgrade head)"
read -rp "  Stub-Katalogdaten seeden? [j/N] " SEED
if [[ "${SEED,,}" == "j" ]]; then
  sudo -u "$SVC_USER" env $(grep -v '^#' "$ENV_FILE" | xargs) \
    "$VENV/bin/python" "$SRC_DIR/scripts/seed.py" && ok "Seed-Daten eingespielt" \
    || warn "seed.py fehlgeschlagen — später nachholbar"
fi

# ── 7. systemd-Unit (gunicorn) ────────────────────────────────────────────────
hdr "7/8  systemd (gunicorn)"
cat > /etc/systemd/system/mpp-web.service <<UNIT
[Unit]
Description=MPP (Flask, gunicorn)
After=network.target postgresql-16.service
[Service]
User=$SVC_USER
Group=$SVC_USER
WorkingDirectory=$SRC_DIR
EnvironmentFile=$ENV_FILE
RuntimeDirectory=mpp
ExecStart=$VENV/bin/gunicorn "app:create_app()" --bind 127.0.0.1:8001 --workers 3 --timeout 60 --access-logfile - --error-logfile -
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now mpp-web
ok "mpp-web (gunicorn :8001) aktiv"

# ── 8. nginx + TLS + firewalld/SELinux ────────────────────────────────────────
hdr "8/8  nginx + TLS"
if [ ! -f /etc/pki/mpp/mpp.crt ]; then
  mkdir -p /etc/pki/mpp
  openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
    -keyout /etc/pki/mpp/mpp.key -out /etc/pki/mpp/mpp.crt \
    -subj "/CN=${FQDN}" -addext "subjectAltName=DNS:${FQDN}" 2>/dev/null
  chmod 600 /etc/pki/mpp/mpp.key
  warn "Self-signed Zertifikat erzeugt — für Produktion internes CA-Zertifikat einspielen"
fi
cat > /etc/nginx/conf.d/mpp.conf <<NGINX
server { listen 80; server_name ${FQDN}; return 301 https://\$host\$request_uri; }
server {
    listen 443 ssl; http2 on; server_name ${FQDN};
    ssl_certificate /etc/pki/mpp/mpp.crt; ssl_certificate_key /etc/pki/mpp/mpp.key;
    ssl_protocols TLSv1.2 TLSv1.3; client_max_body_size 25m;
    root $SPA_DIR;

    # API → gunicorn
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host \$host; proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme; proxy_redirect off;
    }
    # React-SPA (statisch) + Client-Side-Routing-Fallback
    location / {
        try_files \$uri \$uri/ /index.html;
        access_log off; expires 1h;
    }
}
NGINX
nginx -t && systemctl enable --now nginx && systemctl reload nginx
if command -v setsebool >/dev/null; then
  setsebool -P httpd_can_network_connect on || true
  semanage fcontext -a -t httpd_sys_content_t "$SPA_DIR(/.*)?" 2>/dev/null || true
  restorecon -Rv "$SPA_DIR" >/dev/null 2>&1 || true
fi
if command -v firewall-cmd >/dev/null; then
  firewall-cmd --permanent --add-service=http --add-service=https >/dev/null 2>&1 || true
  firewall-cmd --reload >/dev/null 2>&1 || true
fi
ok "nginx + TLS + firewalld/SELinux konfiguriert"

hdr "FERTIG"
echo "  Portal:   ${C_OK}https://${FQDN}/${C_NC}"
echo "  Health:   https://${FQDN}/api/v1/health"
echo "  Ready:    https://${FQDN}/api/v1/ready"
echo "  Status:   systemctl status mpp-web nginx --no-pager"
echo "  Test:     curl -kI https://${FQDN}"
echo "  ${C_WARN}DB-Passwort + JWT_SECRET stehen in $ENV_FILE (chmod 640).${C_NC}"
echo "  ${C_WARN}⚠ Login funktioniert erst nach LDAP-Implementierung (AUTH_MODE=ldap).${C_NC}"
