# VM-Installation — MPP (Flask + React, Produktion)

Schritt-für-Schritt-Anleitung, um das **Marketplace Portal (MPP)** — Flask 3.1
Backend + React-19/Vite-SPA — auf einer frischen **Rocky Linux 9 / AlmaLinux 9**-VM
in einer **produktionsnahen** Konfiguration zu installieren:

```
Internet ──TLS──▶ nginx (80/443) ──────────────────────────────────────────┐
                     │                                                       │
                     ├─ /            → React-SPA (statisch, frontend/dist)   │
                     └─ /api/        → gunicorn (127.0.0.1:8001) ──▶ Flask (create_app, WSGI)
                                                                          │
                                                                          ▼
                                                                    PostgreSQL 16
```

> **Zielbild:** dedizierter Service-User, env-basierte Konfiguration
> (`app/core/config.py`), gunicorn als systemd-Unit, nginx als TLS-terminierender
> Reverse-Proxy (liefert die SPA statisch aus und proxyt `/api`), SELinux *enforcing*,
> firewalld aktiv. Es gibt **kein** Redis/Celery — Background-Jobs existieren nicht.

> ## ⚠ Vor dem Start lesen — Produktionsreife (Code-Stand 2026-06-19)
>
> Die Anleitung beschreibt das **Zielbild** und markiert jede offene Stelle mit einer
> **„⚠ Lücke"-Box**.
>
> **In diesem Stand bereits behoben:** gunicorn ist Projekt-Dependency (`requirements.txt`),
> `ProxyFix` ist in `create_app` aktiv, `migrations/env.py` liest `DATABASE_URL`, und es gibt
> einen Readiness-Endpoint `GET /api/v1/ready` mit DB-Check.
>
> **Noch offen (echte Feature-Lücken):**
>
> 1. **Kein lauffähiger Produktiv-Auth.** `AUTH_MODE=ldap` wirft beim Login
>    `NotImplementedError`; `AUTH_MODE=stub` ist bei `ENV=production` per Guard
>    **verboten**. → Mit dem aktuellen Code kann sich in „echter" Produktion
>    **niemand einloggen** (Schritt 9). LDAP muss erst implementiert werden.
> 2. **`CMDB_MODE=live` ist nicht implementiert**, es gibt keinen Live-CMDB-Client.
> 3. **Keine User-Verwaltung** — nur hartkodierte Stub-User, keine User-Tabelle.
> 4. **Kein CORS** im Backend — funktioniert nur same-origin hinter nginx.
>
> Die konsolidierte Liste steht in [Abschnitt 18](#18-produktionsreife--offene-punkte).

---

## Inhalt

1. [Voraussetzungen](#1-voraussetzungen)
2. [VM-Grundkonfiguration](#2-vm-grundkonfiguration)
3. [System-Pakete (Python 3.12, Node.js 22, nginx)](#3-system-pakete-python-312-nodejs-22-nginx)
4. [PostgreSQL 16](#4-postgresql-16)
5. [Service-User & Verzeichnisse](#5-service-user--verzeichnisse)
6. [Backend: Code, venv & Abhängigkeiten](#6-backend-code-venv--abhängigkeiten)
7. [Frontend: React-SPA bauen](#7-frontend-react-spa-bauen)
8. [Datenbank: Migrationen & Seed](#8-datenbank-migrationen--seed)
9. [Umgebungsdatei (Secrets)](#9-umgebungsdatei-secrets)
10. [gunicorn als systemd-Service](#10-gunicorn-als-systemd-service)
11. [nginx Reverse-Proxy](#11-nginx-reverse-proxy)
12. [SELinux & firewalld](#12-selinux--firewalld)
13. [TLS mit Let's Encrypt](#13-tls-mit-lets-encrypt)
14. [Verifikation (Smoke-Test)](#14-verifikation-smoke-test)
15. [Updates & Re-Deploy](#15-updates--re-deploy)
16. [Betrieb: Logs, Backups, Health](#16-betrieb-logs-backups-health)
17. [Troubleshooting](#17-troubleshooting)
18. [Produktionsreife — offene Punkte](#18-produktionsreife--offene-punkte)
19. [Sicherheits-Checkliste](#19-sicherheits-checkliste)

---

## 1. Voraussetzungen

| Komponente | Version / Wert |
|---|---|
| OS | Rocky Linux 9 oder AlmaLinux 9 (x86_64), frisch installiert |
| RAM | min. 2 GB (4 GB empfohlen — der Frontend-Build braucht Speicher) |
| Python | **3.12** (Backend-Stack ist auf 3.12 festgelegt) |
| Node.js | **22** (für den Vite-Build des Frontends) |
| PostgreSQL | 16 (PGDG-Repo) |
| Zugang | sudo-fähiger User, SSH |
| DNS | A-Record `mpp.example.com` → öffentliche IP der VM (für TLS) |

In dieser Anleitung verwendete Platzhalter — überall konsequent ersetzen:

| Platzhalter | Beispiel |
|---|---|
| `mpp.example.com` | euer FQDN |
| `/opt/mpp` | Installationswurzel |
| DB-Name / -User / -Passwort | `mpp_prod` / `mpp` / `<DB-PASSWORT>` |
| `<JWT-SECRET>` | per `secrets.token_urlsafe(64)` erzeugt |

> **Konvention:** Befehle mit `sudo` laufen als Admin. Befehle nach `sudo -iu mpp`
> laufen als **Service-User** `mpp` (siehe Schritt 5).

---

## 2. VM-Grundkonfiguration

```bash
# System aktuell halten
sudo dnf -y upgrade --refresh

# Basis-Werkzeuge
sudo dnf -y install vim git curl policycoreutils-python-utils

# Hostname & Zeitzone
sudo hostnamectl set-hostname mpp.example.com
sudo timedatectl set-timezone Europe/Berlin

# Zeitsynchronisation
sudo systemctl enable --now chronyd
```

---

## 3. System-Pakete (Python 3.12, Node.js 22, nginx)

Rocky/Alma 9 liefert standardmäßig Python 3.9. MPP benötigt **3.12** aus dem
AppStream, dazu Node.js 22 für den Frontend-Build:

```bash
# Python 3.12 + venv/pip + dev-Header (für psycopg2-Wheels harmlos vorzuhalten)
sudo dnf -y install python3.12 python3.12-devel python3.12-pip

# Compiler & libpq (nur falls psycopg2 aus Quelle baut — Default sind Binär-Wheels)
sudo dnf -y install gcc make libpq-devel

# Node.js 22 (AppStream-Modul)
sudo dnf -y module reset nodejs
sudo dnf -y module enable nodejs:22
sudo dnf -y install nodejs

# nginx
sudo dnf -y install nginx

# Prüfen
python3.12 --version   # erwartet: Python 3.12.x
node --version         # erwartet: v22.x
```

> Node.js wird **nur zum Bauen** der SPA gebraucht. Im Betrieb läuft kein
> Node-Prozess — nginx liefert die fertigen Dateien aus `frontend/dist` aus.

---

## 4. PostgreSQL 16

Das offizielle **PGDG**-Repo liefert PostgreSQL 16:

```bash
# PGDG-Repo + AppStream-Modul deaktivieren (sonst Paketkonflikt)
sudo dnf -y install https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo dnf -qy module disable postgresql

# Server + Client
sudo dnf -y install postgresql16-server postgresql16

# Datencluster initialisieren und Dienst starten
sudo /usr/pgsql-16/bin/postgresql-16-setup initdb
sudo systemctl enable --now postgresql-16
```

Datenbank und Rolle anlegen (Namen passend zum späteren `DATABASE_URL`):

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE mpp WITH LOGIN PASSWORD '<DB-PASSWORT>';
CREATE DATABASE mpp_prod OWNER mpp ENCODING 'UTF8' LC_COLLATE 'de_DE.UTF-8' LC_CTYPE 'de_DE.UTF-8' TEMPLATE template0;
GRANT ALL PRIVILEGES ON DATABASE mpp_prod TO mpp;
SQL
```

Lokale Passwort-Authentifizierung (`scram-sha-256`) freischalten:

```bash
sudo sed -i 's/^host\s\+all\s\+all\s\+127.0.0.1\/32\s\+ident/host    all             all             127.0.0.1\/32            scram-sha-256/' \
  /var/lib/pgsql/16/data/pg_hba.conf
sudo systemctl restart postgresql-16

# Verbindung testen (Passwort aus obigem CREATE ROLE)
psql "postgresql://mpp:<DB-PASSWORT>@127.0.0.1:5432/mpp_prod" -c '\conninfo'
```

> Liegt PostgreSQL auf einem separaten Server, dort `listen_addresses` und
> `pg_hba.conf` für das App-Netz öffnen und in `DATABASE_URL` den Host eintragen.

---

## 5. Service-User & Verzeichnisse

Die App läuft als **unprivilegierter** System-User ohne Login-Shell:

```bash
# Dedizierter Service-User
sudo useradd --system --create-home --home-dir /opt/mpp --shell /usr/sbin/nologin mpp

# Verzeichnis für die Umgebungsdatei (Secrets)
sudo mkdir -p /etc/mpp

# Laufzeitverzeichnis (Socket/PID) — zusätzlich per systemd RuntimeDirectory gepflegt
sudo install -d -o mpp -g mpp /run/mpp
```

---

## 6. Backend: Code, venv & Abhängigkeiten

```bash
# Als Service-User arbeiten
sudo -iu mpp

# Repository holen (oder per CI-Artefakt/rsync ausrollen)
git clone <REPO-URL> /opt/mpp/app
cd /opt/mpp/app

# venv mit Python 3.12
python3.12 -m venv /opt/mpp/venv
/opt/mpp/venv/bin/python -m pip install --upgrade pip

# Projekt-Abhängigkeiten (inkl. gunicorn als WSGI-Server)
/opt/mpp/venv/bin/pip install -r requirements.txt

# zurück zum Admin
exit
```

> `gunicorn==23.0.0` ist Teil von `requirements.txt` — der WSGI-Server wird also
> direkt mitinstalliert, kein manueller Extra-Schritt nötig.

Verzeichnis-Layout danach:

```
/opt/mpp/
├── app/                  # Git-Checkout (Repo-Wurzel)
│   ├── app/             # Flask-Package (create_app-Factory in app/__init__.py)
│   ├── frontend/        # React/Vite-Quelle  → Build-Output frontend/dist
│   ├── migrations/      # Alembic-Revisions
│   ├── scripts/seed.py  # Demo-Daten-Seed
│   ├── stubs/           # CMDB-/GitLab-Stubs
│   ├── alembic.ini
│   └── requirements.txt
└── venv/                 # virtualenv (Python 3.12) + gunicorn
/etc/mpp/mpp.env          # Secrets (Schritt 9)
```

---

## 7. Frontend: React-SPA bauen

Das Frontend ist eine eigenständige Vite-SPA, die zu statischem HTML/JS/CSS
kompiliert. Build einmalig (und bei jedem Update) ausführen:

```bash
sudo -iu mpp bash
cd /opt/mpp/app/frontend

# Reproduzierbarer Install aus dem Lockfile
npm ci

# Production-Build  (package.json: "build": "tsc -b && vite build")
npm run build          # erzeugt /opt/mpp/app/frontend/dist

exit
```

> **Same-Origin ist Pflicht.** Das Frontend spricht das Backend über **relative
> Pfade** `/api/v1/...` an (`frontend/src/api/client.ts`). Es gibt **keine**
> `VITE_API_URL`/`.env`-Konfiguration — SPA und API **müssen** hinter demselben
> Origin liegen. Genau das leistet der nginx-Proxy in Schritt 11.

> Der `dist/`-Ordner wird von nginx direkt ausgeliefert (Schritt 11/12 setzen den
> SELinux-Kontext und den `root`-Pfad). Node wird zur Laufzeit nicht benötigt.

---

## 8. Datenbank: Migrationen & Seed

Das Schema wird per **Alembic** angelegt (nicht Flask-Migrate):

```bash
sudo -iu mpp bash
cd /opt/mpp/app
PY=/opt/mpp/venv/bin/python

# Umgebung laden (DATABASE_URL) und Schema auf den aktuellen Stand bringen
set -a; source /etc/mpp/mpp.env; set +a    # Umgebungsdatei aus Schritt 9
$PY -m alembic upgrade head
```

> `migrations/env.py` bevorzugt die Umgebungsvariable **`DATABASE_URL`** vor der
> `sqlalchemy.url` aus `alembic.ini` (siehe `app/core/db_url.py`). Solange
> `DATABASE_URL` auf `mpp_prod` zeigt (Schritt 9), trifft `alembic upgrade head`
> automatisch die richtige DB — die hartkodierte ini-URL (`mpp_dev`) muss **nicht**
> mehr editiert werden.

Optionaler **Demo-Seed** (`scripts/seed.py` liest `DATABASE_URL` aus der Umgebung):

```bash
# nur für Demo/Eval — legt 2 Templates, 9 Beispiel-Orders, Regeln etc. an
set -a; source /etc/mpp/mpp.env; set +a    # Umgebungsdatei aus Schritt 9
$PY scripts/seed.py
exit
```

> ### ⚠ Lücke: keine echten User/Admins
> `seed.py` legt **Demo-Daten**, aber **keine Benutzer** an. Es gibt keine
> User-Tabelle und kein Admin-Anlage-Kommando — die einzigen „Accounts" sind
> hartkodierte **Stub-User** (`test-requester`, `test-approver`, `test-admin`,
> `test-multi`, `test-superadmin`) in `app/services/auth_service.py`, nutzbar nur
> mit `AUTH_MODE=stub`. Für echten Mehrbenutzerbetrieb muss zuerst eine
> Auth-/User-Verwaltung implementiert werden (siehe Schritt 9 + Abschnitt 18).
> In sauberer Produktion **ohne** Demo-Daten den Seed einfach **weglassen** — das
> Schema steht bereits durch `alembic upgrade head`.

---

## 9. Umgebungsdatei (Secrets)

Die App liest ihre Konfiguration in `app/core/config.py` ausschließlich aus
**Umgebungsvariablen**. Vorlage ist `.env.example` im Repo.

> ### ⚠ Lücke: die App lädt selbst KEINE `.env`
> `python-dotenv` ist zwar installiert, wird im Code aber **nie aufgerufen**
> (kein `load_dotenv`). Die Variablen müssen also vom Prozess-Environment kommen —
> hier über die systemd-Direktive `EnvironmentFile=` (Schritt 10), **nicht** über
> eine `.env` im Projektordner.

JWT-Secret erzeugen und Umgebungsdatei anlegen:

```bash
# starkes JWT-Secret erzeugen
/opt/mpp/venv/bin/python -c "import secrets; print(secrets.token_urlsafe(64))"

sudo cp /opt/mpp/app/.env.example /etc/mpp/mpp.env
sudo vim /etc/mpp/mpp.env
```

Alle von der App gelesenen Variablen (`app/core/config.py`) mit ihren Defaults:

| Variable | Default | Bedeutung |
|---|---|---|
| `AUTH_MODE` | `ldap` | `stub` \| `ldap` — `ldap` ist **nicht implementiert** |
| `ENV` | `development` | `production` aktiviert den Stub-Auth-Guard |
| `JWT_SECRET` | _(leer)_ | Signaturschlüssel für Tokens — **zwingend setzen** |
| `STUB_TOKEN_TTL_SECONDS` | `86400` | Token-Lebensdauer im Stub-Modus |
| `DATABASE_URL` | `postgresql://mpp:mpp@localhost:5432/mpp_dev` | App-DB |
| `CMDB_MODE` | `stub` | `stub` \| `live` — `live` ist **nicht implementiert** |
| `CMDB_STUB_DATA_PATH` | `./stubs/cmdb/` | Pfad zu den CMDB-Stub-YAMLs |
| `GITLAB_URL` | _(leer)_ | GitLab-API-Basis (nur wenn Provisioning genutzt) |
| `GITLAB_TOKEN` | _(leer)_ | GitLab-API-Token |
| `GITLAB_PROJECT_ID` | `1` | GitLab-Projekt-ID |
| `GITLAB_WEBHOOK_SECRET` | _(leer)_ | Webhook-Signaturschlüssel |
| `APPROVAL_DEFAULT_DEADLINE_HOURS` | `48` | Default-Genehmigungsfrist |
| `APPROVAL_ALLOW_SELF_APPROVAL` | `false` | Selbst-Genehmigung erlauben |

Empfohlene Produktions-`/etc/mpp/mpp.env`:

```ini
ENV=production
AUTH_MODE=ldap
JWT_SECRET=<JWT-SECRET>
DATABASE_URL=postgresql://mpp:<DB-PASSWORT>@127.0.0.1:5432/mpp_prod
CMDB_MODE=stub
CMDB_STUB_DATA_PATH=/opt/mpp/app/stubs/cmdb/
APPROVAL_ALLOW_SELF_APPROVAL=false
# GITLAB_URL=https://gitlab.example.com
# GITLAB_TOKEN=<token>
# GITLAB_WEBHOOK_SECRET=<secret>
```

Rechte restriktiv setzen (nur root liest/schreibt, Gruppe `mpp` liest):

```bash
sudo chown root:mpp /etc/mpp/mpp.env
sudo chmod 640 /etc/mpp/mpp.env
```

> ### ⚠ Lücke (BLOCKER): kein lauffähiger Produktiv-Login
> `config.py` erzwingt bei `ENV=production` **`AUTH_MODE != stub`** (sonst
> `RuntimeError` beim Start). Der einzige Nicht-Stub-Modus `ldap` wirft beim Login
> aber `NotImplementedError` (`app/services/auth_service.py`). **Ergebnis:** Mit dem
> aktuellen Code kann sich in der `production`-Konfiguration **niemand einloggen**.
>
> Optionen, bis LDAP implementiert ist:
> - **Auth implementieren** (LDAP/OIDC) — der saubere Weg für echten Betrieb.
> - **Geschützter Eval-Betrieb** mit `ENV=development` + `AUTH_MODE=stub` hinter
>   restriktivem nginx/Firewall-Zugang (kein öffentlicher Internet-Zugang). Dann
>   funktionieren die Stub-User — aber **nicht** als „produktionssicher" deklarieren.

---

## 10. gunicorn als systemd-Service

Die Flask-App nutzt die **App-Factory** `create_app` (kein Modul-Level-`app`),
daher startet gunicorn sie als Aufruf `app:create_app()`.

`/etc/systemd/system/mpp-web.service`:

```ini
[Unit]
Description=MPP (Flask/gunicorn)
After=network.target postgresql-16.service
Requires=postgresql-16.service

[Service]
User=mpp
Group=mpp
WorkingDirectory=/opt/mpp/app
EnvironmentFile=/etc/mpp/mpp.env
RuntimeDirectory=mpp
ExecStart=/opt/mpp/venv/bin/gunicorn "app:create_app()" \
    --bind 127.0.0.1:8001 \
    --workers 3 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
Restart=on-failure
RestartSec=5

# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mpp-web
sudo systemctl status mpp-web --no-pager
```

> **Worker-Faustregel:** `(2 × CPU-Kerne) + 1`. Bei 1 Kern also 3.

> **`ProxyFix` ist aktiv:** `create_app` wrappt `app.wsgi_app` mit
> `ProxyFix(..., x_for=1, x_proto=1, x_host=1)`, sodass die von nginx gesetzten
> `X-Forwarded-For/-Proto/-Host`-Header korrekt ausgewertet werden (richtige
> Client-IP + `https`-Erkennung). Wichtig: nginx muss diese Header setzen (Schritt 11).

---

## 11. nginx Reverse-Proxy

nginx liefert die statische SPA aus **und** proxyt `/api` an gunicorn. Zunächst
HTTP (Port 80); TLS kommt in Schritt 13 dazu. `/etc/nginx/conf.d/mpp.conf`:

```nginx
server {
    listen 80;
    server_name mpp.example.com;

    client_max_body_size 25m;

    # React-SPA (statisch gebaut in Schritt 7)
    root /opt/mpp/app/frontend/dist;
    index index.html;

    # API → gunicorn/Flask
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_redirect off;
    }

    # Statische Assets mit Cache-Header
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # SPA-Fallback: alle übrigen Pfade → index.html (Client-Side-Routing)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
sudo nginx -t                 # Konfiguration prüfen
sudo systemctl enable --now nginx
```

> Die Proxy-Pfade und der SPA-Fallback entsprechen exakt der mitgelieferten
> `nginx.conf` des Repos (dort `proxy_pass http://backend:5000` für den
> Docker-Compose-Betrieb) — hier auf den lokalen gunicorn-Port `8001` angepasst.

---

## 12. SELinux & firewalld

Rocky/Alma laufen SELinux *enforcing*. Ohne die folgenden Schritte blockiert
SELinux den Proxy-Zugriff und nginx kann die SPA-Dateien nicht lesen.

```bash
# nginx darf zu gunicorn (TCP 8001) verbinden
sudo setsebool -P httpd_can_network_connect on

# Korrekten SELinux-Kontext für das SPA-Verzeichnis setzen
sudo semanage fcontext -a -t httpd_sys_content_t "/opt/mpp/app/frontend/dist(/.*)?"
sudo restorecon -Rv /opt/mpp/app/frontend/dist

# Firewall: HTTP + HTTPS öffnen
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

> Liefert nginx weiter `403`, prüfe mit `sudo ausearch -m avc -ts recent` die
> SELinux-Denials und passe den Kontext an. Häufige Ursache: `dist/` liegt unter
> `/opt/mpp` (Home des Service-Users) — der `httpd_sys_content_t`-Kontext oben löst das.

---

## 13. TLS mit Let's Encrypt

```bash
# certbot aus EPEL
sudo dnf -y install epel-release
sudo dnf -y install certbot python3-certbot-nginx

# Zertifikat holen und nginx automatisch konfigurieren
sudo certbot --nginx -d mpp.example.com --redirect --agree-tos -m admin@example.com

# Automatische Erneuerung (certbot bringt einen systemd-Timer mit)
sudo systemctl enable --now certbot-renew.timer
sudo certbot renew --dry-run
```

certbot ergänzt den `listen 443 ssl`-Block und einen 80→443-Redirect in
`mpp.conf`.

> ### ⚠ Lücke: HTTPS-Erzwingung kommt nur von nginx
> Anders als beim Django-Pendant gibt es **keine** App-seitige
> `SECURE_SSL_REDIRECT`/HSTS-Logik. HTTPS-Redirect + HSTS müssen vollständig in
> nginx konfiguriert werden (certbot setzt den Redirect; HSTS ggf. per
> `add_header Strict-Transport-Security ...` ergänzen).

---

## 14. Verifikation (Smoke-Test)

```bash
# Dienste laufen?
systemctl is-active mpp-web nginx postgresql-16

# Liveness (lokal, direkt am gunicorn) — immer 200, solange der Prozess lebt
curl -s http://127.0.0.1:8001/api/v1/health      # -> {"status":"ok","auth_mode":"..."}

# Readiness inkl. DB-Check — 200 nur, wenn die Datenbank antwortet (sonst 503)
curl -s http://127.0.0.1:8001/api/v1/ready        # -> {"status":"ready","database":"ok"}

# Über nginx + TLS
curl -I  http://mpp.example.com                   # -> 301/302 nach https
curl -sI https://mpp.example.com/ | head -n1      # -> 200 (SPA index.html)
curl -s  https://mpp.example.com/api/v1/ready     # -> {"status":"ready","database":"ok"}
```

Erwartung: `http://` leitet nach `https://` um, `/` liefert die SPA,
`/api/v1/ready` antwortet mit `{"status":"ready","database":"ok"}`.

> **Liveness vs. Readiness:** `/api/v1/health` ist die reine Liveness-Sonde (immer
> `200`, kein DB-Check) — geeignet für „Prozess lebt?". `/api/v1/ready` führt ein
> `SELECT 1` gegen die DB aus und liefert `503`, wenn die Datenbank nicht erreichbar
> ist — das ist die Sonde für Load-Balancer/Monitoring.

---

## 15. Updates & Re-Deploy

Neue Version ausrollen:

```bash
sudo -iu mpp bash
cd /opt/mpp/app
git pull --ff-only

# Backend-Deps (inkl. gunicorn)
/opt/mpp/venv/bin/pip install -r requirements.txt

# Frontend neu bauen
cd /opt/mpp/app/frontend && npm ci && npm run build

# Schema migrieren (alembic.ini ggf. erneut auf mpp_prod prüfen — Schritt 8)
cd /opt/mpp/app
/opt/mpp/venv/bin/python -m alembic upgrade head
exit

# Dienste neu starten / Assets-Kontext erneuern
sudo restorecon -Rv /opt/mpp/app/frontend/dist
sudo systemctl restart mpp-web
sudo systemctl reload nginx
```

> Nach jedem Frontend-Build neue Dateien in `dist/` → `restorecon` erneut laufen
> lassen, sonst blockiert SELinux die frisch erzeugten Assets.

---

## 16. Betrieb: Logs, Backups, Health

**Logs** (gunicorn loggt nach journald):

```bash
sudo journalctl -u mpp-web -f
sudo tail -f /var/log/nginx/{access,error}.log
```

**Datenbank-Backup** (z. B. täglich per cron/systemd-Timer):

```bash
sudo -u postgres pg_dump -Fc mpp_prod > /var/backups/mpp_prod_$(date +%F).dump
```

**Health-Indikatoren:**

| Prüfung | Befehl |
|---|---|
| Web aktiv | `systemctl is-active mpp-web` |
| App-Liveness | `curl -s http://127.0.0.1:8001/api/v1/health` |
| App-Readiness (inkl. DB) | `curl -s http://127.0.0.1:8001/api/v1/ready` |
| DB erreichbar | `psql "$DATABASE_URL" -c 'SELECT 1'` |
| Migrationen aktuell | `/opt/mpp/venv/bin/python -m alembic current` |
| nginx aktiv | `systemctl is-active nginx` |

---

## 17. Troubleshooting

| Symptom | Ursache / Lösung |
|---|---|
| `502 Bad Gateway` | gunicorn down (`systemctl status mpp-web`) oder SELinux blockiert TCP → `setsebool -P httpd_can_network_connect on` |
| `403` auf `/` oder Assets | falscher SELinux-Kontext auf `frontend/dist` → `restorecon -Rv .../dist`; Build (`npm run build`) gelaufen? |
| `RuntimeError` beim Start | `ENV=production` **und** `AUTH_MODE=stub` gesetzt → in Produktion verboten (Schritt 9) |
| `ValueError: invalid AUTH_MODE/CMDB_MODE` | nur `stub`/`ldap` bzw. `stub`/`live` erlaubt |
| Login → `NotImplementedError` | `AUTH_MODE=ldap` ist nicht implementiert (Abschnitt 18); für Eval `AUTH_MODE=stub` + `ENV=development` |
| gunicorn startet nicht | `app:create_app()` braucht `WorkingDirectory=/opt/mpp/app`, damit das Package `app` gefunden wird |
| Migration trifft falsche DB | `alembic.ini`-`sqlalchemy.url` zeigt noch auf `mpp_dev` (Schritt 8) |
| `psycopg2 OperationalError` | DB-Passwort/`pg_hba.conf` falsch; `DATABASE_URL` prüfen |
| 404 auf Client-Routen (Reload) | SPA-Fallback `try_files ... /index.html` fehlt im nginx-Block (Schritt 11) |
| `/api`-Calls schlagen fehl (CORS) | SPA nicht same-origin ausgeliefert; SPA + API müssen über **denselben** nginx-Host laufen |

---

## 18. Produktionsreife — offene Punkte

Konsolidierte Liste der Stellen, die vor echtem Produktivbetrieb geschlossen
werden sollten (Code-Stand 2026-06-19).

**Bereits behoben (in diesem Stand):**

- [x] **WSGI-Server**: `gunicorn==23.0.0` in `requirements.txt`; Start als `app:create_app()`.
- [x] **Alembic**: `migrations/env.py` bevorzugt `DATABASE_URL` (`app/core/db_url.py`).
- [x] **ProxyFix**: in `create_app` aktiv (`x_for/x_proto/x_host`).
- [x] **Readiness**: `GET /api/v1/ready` mit DB-`SELECT 1`-Check (503 bei DB-Ausfall).

**Noch offen:**

- [ ] **Auth**: `AUTH_MODE=ldap` implementieren (`auth_service.py` → `NotImplementedError`) oder OIDC ergänzen. Ohne das ist in `ENV=production` kein Login möglich. **(Blocker für echten Betrieb.)**
- [ ] **User-Verwaltung**: Es gibt keine User-Tabelle und kein Admin-Anlage-Kommando — nur hartkodierte Stub-User. Für Mehrbenutzerbetrieb nötig.
- [ ] **CMDB**: `CMDB_MODE=live` implementieren (aktuell wird nur bei `stub` ein Client erzeugt).
- [ ] **HSTS/SSL-Redirect**: rein nginx-seitig — bewusst konfigurieren (keine App-seitige Logik).
- [ ] **DSGVO-Anonymisierung**: `config["DSGVO_ANONYMIZE"]` wird in der Middleware ausgewertet, aber nirgends gesetzt — falls gewünscht, in der Config verdrahten.

---

## 19. Sicherheits-Checkliste

- [ ] `JWT_SECRET` stark zufällig erzeugt (`secrets.token_urlsafe(64)`), nicht der `stub-jwt-secret-dev-only`-Default
- [ ] `/etc/mpp/mpp.env` mit `chmod 640`, Eigentümer `root:mpp`
- [ ] `ENV=production` gesetzt — und der Auth-Blocker aus Abschnitt 18 bewusst adressiert
- [ ] `AUTH_MODE` **nicht** `stub` bei öffentlichem Zugang
- [ ] TLS aktiv, HTTP → HTTPS-Redirect, HSTS-Header vorhanden
- [ ] SELinux *enforcing* (`getenforce` → `Enforcing`)
- [ ] firewalld aktiv, nur 80/443 (+SSH) offen
- [ ] PostgreSQL nur auf `127.0.0.1` erreichbar (oder Firewall fürs App-Netz)
- [ ] `frontend/dist` mit `httpd_sys_content_t`-Kontext, kein Schreibzugriff für nginx
- [ ] DB-Backups eingerichtet und Wiederherstellung getestet
- [ ] GitLab-Token/Webhook-Secret (falls Provisioning genutzt) nur in `mpp.env`, nie im Repo

---

*Stand: 2026-06-19 · Stack: Flask 3.1 · React 19 / Vite 6 · Python 3.12 · PostgreSQL 16 · Rocky/AlmaLinux 9 · ohne Redis/Celery*
