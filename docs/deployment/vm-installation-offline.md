# VM-Installation OFFLINE / Air-Gapped — MPP (Flask + React, Produktion)

Schritt-für-Schritt-Anleitung, um das **Marketplace Portal (MPP)** — Flask 3.1
Backend + React-19/Vite-SPA — auf einer **Rocky/AlmaLinux 9**-VM **ohne
Internetzugang** produktionsnah zu installieren. Alle Quellen (System-RPMs,
Python-Wheels, App-Code, **prebuilt SPA**) werden auf einem verbundenen
**Staging-Host** eingesammelt, als Bundle auf die **Ziel-VM** transportiert und
dort offline installiert.

> **Online-Variante:** Hat die VM Internetzugang, nutze stattdessen
> [`vm-installation.md`](vm-installation.md). Diese Offline-Anleitung teilt deren
> Zielarchitektur — sie ersetzt nur die *Beschaffung* (Repos/PyPI → lokales
> Bundle) und **TLS** (Let's Encrypt → internes/self-signed Zertifikat, da ACME
> ohne Internet nicht funktioniert).

```
Internet ──TLS──▶ nginx (80/443) ──────────────────────────────────────────┐
                     │                                                       │
                     ├─ /            → React-SPA (statisch, frontend-dist)   │
                     └─ /api/        → gunicorn (127.0.0.1:8001) ──▶ Flask (create_app, WSGI)
                                                                          │
                                                                          ▼
                                                                    PostgreSQL 16
```

> **Kein Redis/Celery** — Flask hat keine Background-Jobs. Die React-SPA wird
> **auf dem Staging-Host gebaut** (Node) und **prebuilt** ausgeliefert; die
> Ziel-VM braucht **kein Node.js**.

> ## ⚠ Produktiv-Auth ist noch nicht implementiert (Code-Stand 2026-06-27)
> `AUTH_MODE=ldap` wirft beim Login `NotImplementedError`; `AUTH_MODE=stub` ist
> bei `ENV=production` per Guard verboten. Mit diesem Stand kann sich in echter
> Produktion **niemand einloggen**. Health/Ready laufen, die Infrastruktur steht.
> Details + Demo-Override: [`vm-installation.md`](vm-installation.md#18-produktionsreife--offene-punkte).

```
┌─ Staging-Host (mit Internet, Rocky 9 / x86_64) ─┐        ┌─ Ziel-VM (air-gapped) ─┐
│  RPMs (dnf download)                            │  scp/  │  lokales RPM-Repo      │
│  Python-Wheels (pip download)        ──Bundle──▶│  USB   │  pip --no-index        │
│  App-Source + prebuilt SPA (npm build)          │        │  systemd + nginx + TLS │
└─────────────────────────────────────────────────┘        └────────────────────────┘
```

---

## 🚀 Schnellstart mit dem Release-Bundle (empfohlen, „idiotensicher")

Es gibt ein fertiges Offline-Release, das **alle Python-Pakete als Wheels** und
die **fertig gebaute React-SPA** mitbringt — du musst dann KEINEN Staging-Host
aufsetzen und nichts per `pip download`/`npm build` selbst beschaffen. Bauen (auf
einem Linux-Host mit Python 3.12 + Node + Internet, einmalig):

```bash
./run.sh release
# baut frontend/dist, lädt die Wheels (manylinux/cp312) und packt:
# → release/Lucent-MPP-TDD-<version>-almalinux9-offline.zip
```

Auf der **Ziel-VM** (AlmaLinux/Rocky 9) — drei Schritte:

```bash
# 1. System-Prerequisites (einmalig; online ODER aus dem RPM-Bundle, Teil A/C)
sudo dnf install -y python3.12 postgresql16-server postgresql16 nginx openssl
sudo /usr/pgsql-16/bin/postgresql-16-setup initdb
sudo systemctl enable --now postgresql-16

# 2. Bundle entpacken
unzip Lucent-MPP-TDD-<version>-almalinux9-offline.zip
cd Lucent-MPP-TDD-<version>-almalinux9-offline

# 3. Installer ausführen — fragt nur FQDN + DB-Passwort, macht den Rest
sudo ./deploy/install.sh
```

`install.sh` erledigt offline: venv + Wheels (`--no-index`), DB-Anlage, `.env`,
alembic-Migrationen, optional Seed, systemd (gunicorn), nginx + self-signed TLS
(liefert die SPA statisch aus, proxyt `/api`), firewalld/SELinux. Danach:
`https://<FQDN>/`.

> **Voll air-gapped** (die Ziel-VM hat *gar kein* Internet, auch nicht für die
> System-RPMs in Schritt 1): dann zusätzlich die RPMs im Bundle mitliefern —
> dafür ist die ausführliche Anleitung unten (**Teil A–C**) da. Der `install.sh`
> deckt den Python-/App-/Dienste-Teil ab; die RPM-Beschaffung bleibt Teil A.

---

## Inhalt

- **Teil A — Staging-Host (Artefakte einsammeln)**
  1. [Voraussetzungen Staging](#1-voraussetzungen-staging-host)
  2. [System-RPMs herunterladen](#2-system-rpms-herunterladen)
  3. [Python-Wheels herunterladen](#3-python-wheels-herunterladen)
  4. [React-SPA bauen + App-Source paketieren](#4-react-spa-bauen--app-source-paketieren)
  5. [Bundle schnüren + Prüfsummen](#5-bundle-schnüren--prüfsummen)
- **Teil B — Transport**
  6. [Bundle auf die VM bringen + verifizieren](#6-bundle-auf-die-vm-bringen--verifizieren)
- **Teil C — Ziel-VM (offline installieren)**
  7. [System-Pakete aus lokalem Bundle](#7-system-pakete-aus-lokalem-bundle)
  8. [PostgreSQL 16 / Service-User](#8-postgresql-16--service-user)
  9. [Code + venv + Wheels offline](#9-code--venv--wheels-offline)
  10. [.env, alembic-Migrationen, SPA](#10-env-alembic-migrationen-spa)
  11. [systemd-Unit (gunicorn)](#11-systemd-unit-gunicorn)
  12. [nginx + internes TLS (ohne Let's Encrypt)](#12-nginx--internes-tls-ohne-lets-encrypt)
  13. [SELinux & firewalld](#13-selinux--firewalld)
  14. [Verifikation](#14-verifikation)
  15. [Offline-Updates](#15-offline-updates-re-deploy)
  16. [Troubleshooting + Sicherheits-Checkliste](#16-troubleshooting--sicherheits-checkliste)

---

## ⚠️ Grundregel: Staging-Host == Ziel-VM

Binärartefakte (RPMs, kompilierte Wheels wie `psycopg2-binary`) sind an OS,
Architektur und Python-Version gebunden. Der Staging-Host **muss** matchen:

| Merkmal | Wert (dieses Projekt) |
|---|---|
| OS | Rocky Linux 9 / AlmaLinux 9 |
| Architektur | x86_64 |
| Python | 3.12 |
| Node (nur Staging, für `npm build`) | ≥ 20 |

> Ideal ist ein Staging-Host mit *identischem* OS-Minor-Release. Notfalls eine
> Wegwerf-VM/Container mit Rocky 9 + Internet aufsetzen, Bundle bauen, verwerfen.
> Node wird **nur** auf dem Staging-Host gebraucht — die SPA wird prebuilt
> ausgeliefert.

---

# Teil A — Staging-Host (Artefakte einsammeln)

## 1. Voraussetzungen Staging-Host

```bash
# Arbeitsverzeichnis fürs Bundle
mkdir -p ~/mpp-bundle/{rpms,wheelhouse,src}
cd ~/mpp-bundle

# Download-Plugins + PGDG-Repo (liefert PostgreSQL 16)
sudo dnf -y install dnf-plugins-core
sudo dnf -y install https://download.postgresql.org/pub/repos/yum/reporpms/EL-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo dnf -qy module disable postgresql

# EPEL (für evtl. Zusatzpakete)
sudo dnf -y install epel-release
```

## 2. System-RPMs herunterladen

`--resolve --alldeps` zieht **alle** Abhängigkeiten mit, auch solche, die auf dem
Staging-Host schon installiert sind (sonst fehlen sie auf der frischen Ziel-VM):

```bash
cd ~/mpp-bundle
sudo dnf download --resolve --alldeps --destdir ./rpms \
  python3.12 python3.12-devel python3.12-pip \
  gcc make libpq-devel \
  postgresql16-server postgresql16 \
  nginx \
  openssl \
  policycoreutils-python-utils \
  firewalld chrony

echo "Anzahl RPMs:"; ls ./rpms/*.rpm | wc -l
```

> **Hinweis:** Eine *minimal* installierte Rocky-9-VM hat die meisten Basis-Libs
> bereits. Sind beim Offline-Install dennoch Pakete „missing", auf dem Staging
> die fehlenden Namen ergänzen und Schritt 2 wiederholen. **Kein Redis** — Flask
> braucht keinen Broker.

## 3. Python-Wheels herunterladen

Wheels passend zu **Python 3.12 / x86_64**. Am robustesten direkt aus dem Repo
mit dem im Projekt hinterlegten Plattform-Set:

```bash
cd /pfad/zum/repo
python3.12 -m pip download -r requirements.txt --dest ~/mpp-bundle/wheelhouse \
  --only-binary=:all: --python-version 312 --implementation cp --abi cp312 \
  --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux_2_28_x86_64
python3.12 -m pip download pip setuptools wheel --dest ~/mpp-bundle/wheelhouse --only-binary=:all:

echo "Wheels:"; ls ~/mpp-bundle/wheelhouse | wc -l
```

> Erwartet werden u.a. `flask`, `werkzeug`, `sqlalchemy`, `alembic`,
> `psycopg2_binary` (manylinux-Wheel), `gunicorn`, `pyjwt`, `python_dotenv`,
> `pyyaml`, `requests`. Tauchen `.tar.gz`-sdists statt `.whl` auf, fehlen
> Build-Tools — `--only-binary=:all:` erzwingt Wheels und zeigt, welches Paket
> kein Wheel hat.

## 4. React-SPA bauen + App-Source paketieren

Die SPA wird **auf dem Staging-Host** gebaut (dort ist Node), damit die Ziel-VM
kein Node braucht:

```bash
cd /pfad/zum/repo/frontend
npm ci          # oder: npm install
npm run build   # -> frontend/dist/
```

App-Source reproduzierbar aus dem Git-Stand (ohne `.git`-Historie → klein),
**inklusive** der gebauten SPA:

```bash
cd /pfad/zum/repo
git archive --format=tar.gz --prefix=app/ -o ~/mpp-bundle/src/mpp-app.tar.gz HEAD
# die prebuilt SPA separat dazulegen (git archive enthält frontend/dist nicht):
tar -czf ~/mpp-bundle/src/mpp-spa.tar.gz -C frontend/dist .
git rev-parse HEAD > ~/mpp-bundle/src/COMMIT.txt
```

> Einfacher als die manuelle Paketierung ist `./run.sh release` (Schnellstart
> oben) — es baut SPA + Wheels und schnürt das fertige ZIP inkl. `deploy/install.sh`.

## 5. Bundle schnüren + Prüfsummen

```bash
cd ~
( cd mpp-bundle && find . -type f -exec sha256sum {} \; > SHA256SUMS )
tar -czf mpp-offline-bundle.tar.gz -C mpp-bundle .
sha256sum mpp-offline-bundle.tar.gz > mpp-offline-bundle.tar.gz.sha256
ls -lh mpp-offline-bundle.tar.gz*
```

---

# Teil B — Transport

## 6. Bundle auf die VM bringen + verifizieren

Per `scp` (falls SSH erlaubt) oder USB-Medium:

```bash
scp mpp-offline-bundle.tar.gz* admin@mpp-vm:/var/tmp/
```

Auf der **Ziel-VM** Integrität prüfen und entpacken:

```bash
cd /var/tmp
sha256sum -c mpp-offline-bundle.tar.gz.sha256      # -> OK
sudo mkdir -p /opt/mpp-offline
sudo tar -xzf mpp-offline-bundle.tar.gz -C /opt/mpp-offline
cd /opt/mpp-offline
sha256sum -c SHA256SUMS | grep -v ': OK$' || echo "Alle Artefakte OK"
```

---

# Teil C — Ziel-VM (offline installieren)

> Ab hier ist die VM **air-gapped**. Kein `dnf`/`pip`/`npm` greift aufs Internet.

## 7. System-Pakete aus lokalem Bundle

```bash
sudo dnf install -y --disablerepo='*' /opt/mpp-offline/rpms/*.rpm

sudo hostnamectl set-hostname mpp.internal.example.com
sudo timedatectl set-timezone Europe/Berlin
sudo systemctl enable --now chronyd
python3.12 --version    # erwartet 3.12.x
```

> **Reusable-Repo-Alternative:** Ist `createrepo_c` im Bundle:
> `createrepo_c /opt/mpp-offline/rpms` und eine `.repo`-Datei mit
> `baseurl=file:///opt/mpp-offline/rpms` unter `/etc/yum.repos.d/`.

## 8. PostgreSQL 16 / Service-User

```bash
sudo /usr/pgsql-16/bin/postgresql-16-setup initdb
sudo systemctl enable --now postgresql-16

sudo -u postgres psql <<'SQL'
CREATE ROLE mpp WITH LOGIN PASSWORD '<DB-PASSWORT>';
CREATE DATABASE mpp_prod OWNER mpp ENCODING 'UTF8' TEMPLATE template0;
GRANT ALL PRIVILEGES ON DATABASE mpp_prod TO mpp;
SQL

# scram-sha-256 für localhost erzwingen, dann neu starten
sudo sed -i 's/^host\s\+all\s\+all\s\+127.0.0.1\/32\s\+ident/host    all             all             127.0.0.1\/32            scram-sha-256/' \
  /var/lib/pgsql/16/data/pg_hba.conf
sudo systemctl restart postgresql-16

sudo useradd --system --create-home --home-dir /opt/mpp --shell /usr/sbin/nologin mpp
sudo mkdir -p /etc/mpp
```

Details zur DB-Härtung siehe [Online-Anleitung §4](vm-installation.md#4-postgresql-16).

## 9. Code + venv + Wheels offline

```bash
sudo -iu mpp bash

# App-Source + prebuilt SPA entpacken
mkdir -p /opt/mpp/src /opt/mpp/frontend
tar -xzf /opt/mpp-offline/src/mpp-app.tar.gz -C /opt/mpp/src --strip-components=1
tar -xzf /opt/mpp-offline/src/mpp-spa.tar.gz -C /opt/mpp/frontend
cat /opt/mpp-offline/src/COMMIT.txt   # deployter Commit

# venv mit Python 3.12 + Wheels OHNE Internet
python3.12 -m venv /opt/mpp/venv
/opt/mpp/venv/bin/pip install --no-index --find-links=/opt/mpp-offline/wheelhouse --upgrade pip setuptools wheel
/opt/mpp/venv/bin/pip install --no-index --find-links=/opt/mpp-offline/wheelhouse -r /opt/mpp/src/requirements.txt
/opt/mpp/venv/bin/python -c "import flask, gunicorn, sqlalchemy, alembic, psycopg2; print('Imports OK')"
exit
```

> `--no-index` schaltet PyPI komplett ab; `--find-links` zeigt auf das lokale
> Wheelhouse. „No matching distribution" → ein (transitives) Wheel fehlt im
> Bundle → auf dem Staging-Host nachziehen.

## 10. .env, alembic-Migrationen, SPA

```bash
# JWT_SECRET erzeugen (lokal, kein Internet nötig)
/opt/mpp/venv/bin/python -c "import secrets; print(secrets.token_urlsafe(64))"

sudo tee /etc/mpp/mpp.env >/dev/null <<'ENV'
ENV=production
AUTH_MODE=ldap
JWT_SECRET=<oben-erzeugt>
DATABASE_URL=postgresql://mpp:<DB-PASSWORT>@127.0.0.1:5432/mpp_prod
CMDB_MODE=stub
CMDB_STUB_DATA_PATH=./stubs/cmdb/
ENV
sudo chown root:mpp /etc/mpp/mpp.env && sudo chmod 640 /etc/mpp/mpp.env

# alembic-Migrationen
sudo -iu mpp bash
cd /opt/mpp/src
set -a; source /etc/mpp/mpp.env; set +a
/opt/mpp/venv/bin/alembic -c alembic.ini upgrade head
# optional: Stub-Katalogdaten
/opt/mpp/venv/bin/python scripts/seed.py
exit
```

> `migrations/env.py` liest `DATABASE_URL` aus der Umgebung (Vorrang vor der
> hartkodierten `sqlalchemy.url`). Die prebuilt SPA liegt unter
> `/opt/mpp/frontend/` und wird in §12 von nginx ausgeliefert — **kein**
> `collectstatic`, **kein** Node auf der VM.
>
> ⚠ `AUTH_MODE=ldap` ist die korrekte Produktions-Einstellung, der Login wirft
> aber aktuell `NotImplementedError`. Für eine reine **Demo** ohne echten
> Produktiv-Anspruch: `ENV=development` + `AUTH_MODE=stub`.

## 11. systemd-Unit (gunicorn)

`/etc/systemd/system/mpp-web.service` — **kein** Celery, **kein** Redis:

```ini
[Unit]
Description=MPP (Flask, gunicorn)
After=network.target postgresql-16.service
Requires=postgresql-16.service

[Service]
User=mpp
Group=mpp
WorkingDirectory=/opt/mpp/src
EnvironmentFile=/etc/mpp/mpp.env
RuntimeDirectory=mpp
ExecStart=/opt/mpp/venv/bin/gunicorn "app:create_app()" \
    --bind 127.0.0.1:8001 --workers 3 --timeout 60 \
    --access-logfile - --error-logfile -
Restart=on-failure
RestartSec=5
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

## 12. nginx + internes TLS (ohne Let's Encrypt)

**Wichtigster Unterschied zur Online-Anleitung:** ACME/Let's Encrypt scheidet
air-gapped aus. Stattdessen ein **internes CA-** oder **self-signed Zertifikat**.

### Variante A — Zertifikat von der internen Unternehmens-CA
`mpp.crt` (inkl. Zwischen-CA-Kette) + `mpp.key` von der internen PKI ausstellen
lassen und nach `/etc/pki/mpp/` legen. Clients vertrauen der internen Root-CA
bereits → keine Browser-Warnung. **Empfohlen.**

### Variante B — Self-signed (Test/kleine Umgebung)

```bash
sudo mkdir -p /etc/pki/mpp
sudo openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
  -keyout /etc/pki/mpp/mpp.key -out /etc/pki/mpp/mpp.crt \
  -subj "/CN=mpp.internal.example.com" \
  -addext "subjectAltName=DNS:mpp.internal.example.com"
sudo chmod 600 /etc/pki/mpp/mpp.key
```

> Die `mpp.crt` muss in den **Trust-Store der Clients** importiert werden, sonst
> Zertifikatswarnung.

`/etc/nginx/conf.d/mpp.conf`:

```nginx
server {
    listen 80;
    server_name mpp.internal.example.com;
    return 301 https://$host$request_uri;   # HTTP -> HTTPS
}

server {
    listen 443 ssl;
    http2 on;
    server_name mpp.internal.example.com;

    ssl_certificate     /etc/pki/mpp/mpp.crt;
    ssl_certificate_key /etc/pki/mpp/mpp.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    client_max_body_size 25m;

    root /opt/mpp/frontend;

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # React-SPA (statisch) + Client-Side-Routing-Fallback
    location / {
        try_files $uri $uri/ /index.html;
        access_log off;
        expires 1h;
    }
}
```

```bash
sudo nginx -t
sudo systemctl enable --now nginx
```

## 13. SELinux & firewalld

```bash
sudo setsebool -P httpd_can_network_connect on
sudo semanage fcontext -a -t httpd_sys_content_t "/opt/mpp/frontend(/.*)?"
sudo restorecon -Rv /opt/mpp/frontend

sudo firewall-cmd --permanent --add-service=http --add-service=https
sudo firewall-cmd --reload
```

## 14. Verifikation

```bash
systemctl is-active mpp-web nginx postgresql-16

# HTTPS lokal testen (-k akzeptiert self-signed)
curl -kI https://mpp.internal.example.com
curl -ks  https://mpp.internal.example.com/api/v1/health   # {"status":"ok"}
curl -ks  https://mpp.internal.example.com/api/v1/ready     # DB-Check
```

Optional die App-Tests im Ziel-venv (PostgreSQL muss erreichbar sein):

```bash
sudo -iu mpp bash
cd /opt/mpp/src
/opt/mpp/venv/bin/python -m pytest -q
exit
```

## 15. Offline-Updates (Re-Deploy)

Pro Update auf dem Staging-Host ein **neues Bundle** bauen (`./run.sh release`
oder Teil A). Auf der VM:

```bash
sudo -iu mpp bash
tar -xzf /opt/mpp-offline/src/mpp-app.tar.gz -C /opt/mpp/src --strip-components=1
tar -xzf /opt/mpp-offline/src/mpp-spa.tar.gz -C /opt/mpp/frontend
/opt/mpp/venv/bin/pip install --no-index --find-links=/opt/mpp-offline/wheelhouse \
  -r /opt/mpp/src/requirements.txt --upgrade
cd /opt/mpp/src
set -a; source /etc/mpp/mpp.env; set +a
/opt/mpp/venv/bin/alembic -c alembic.ini upgrade head
exit
sudo systemctl restart mpp-web
sudo restorecon -Rv /opt/mpp/frontend   # neue SPA-Dateien
```

## 16. Troubleshooting + Sicherheits-Checkliste

| Symptom | Ursache / Lösung |
|---|---|
| `dnf … No match for argument` | RPM (oder Dep) fehlt im Bundle → Staging Schritt 2 mit `--alldeps` ergänzen |
| `pip … No matching distribution` | Wheel fehlt/falsche Plattform → Staging-Host muss Rocky 9 + Py 3.12 sein; Schritt 3 wiederholen |
| `psycopg2`-Importfehler | `psycopg2-binary`-Wheel fehlt oder Architektur-Mismatch (nicht x86_64) |
| Leere Seite / 404 auf `/` | SPA nicht unter `/opt/mpp/frontend/` entpackt, oder `try_files`-Fallback fehlt |
| `/api/…` 502 | gunicorn (`mpp-web`) läuft nicht → `systemctl status mpp-web`, Logs prüfen |
| Login wirft 501/Fehler | erwartet — `AUTH_MODE=ldap` ist `NotImplemented`; siehe Auth-Box oben |
| Zertifikatswarnung im Browser | interne CA-/self-signed `mpp.crt` nicht im Client-Trust-Store |
| `sha256sum -c` schlägt fehl | Bundle-Transport korrupt → erneut übertragen |
| Zeit/Token-Fehler beim Login | NTP/`chronyd` ohne Zeitserver → internen NTP-Server konfigurieren |

**Sicherheits-Checkliste** (zusätzlich zur
[Online-Liste](vm-installation.md#19-sicherheits-checkliste)):

- [ ] Bundle-Prüfsummen (`SHA256SUMS`) auf der VM verifiziert
- [ ] Staging-Host == Ziel-VM (OS/Arch/Python) bestätigt
- [ ] `pip install --no-index` lief ohne Internet-Fallback durch
- [ ] SPA prebuilt ausgeliefert (kein Node auf der VM)
- [ ] TLS-Zertifikat von interner CA **oder** self-signed in Client-Trust importiert
- [ ] interner NTP-Server konfiguriert (Zeit für Sessions/TLS)
- [ ] deployter Commit (`COMMIT.txt`) dokumentiert
- [ ] Auth-Blocker bekannt: kein Produktiv-Login bis LDAP implementiert

---

*Stand: 2026-06-27 · air-gapped · Stack: Flask 3.1 · Python 3.12 · React 19/Vite (prebuilt) · PostgreSQL 16 · Rocky/AlmaLinux 9 · kein Redis/Celery*
