# Installation

## Voraussetzungen

| Software    | Version | Beschreibung                    |
|-------------|---------|----------------------------------|
| Python      | 3.12+   | Backend-Runtime                  |
| Node.js     | 20+     | Frontend-Build                   |
| PostgreSQL  | 15+     | Datenbank                        |
| Git         | 2.x     | Versionsverwaltung               |

---

## Repository klonen

```bash
git clone <repository-url> lucent-app-mpp-TDD
cd lucent-app-mpp-TDD
```

---

## Backend einrichten

### 1. Virtual Environment erstellen

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Abhaengigkeiten installieren

```bash
pip install -r requirements.txt
```

### 3. Environment-Variablen

Erstelle eine `.env`-Datei im Projektroot (oder setze die Variablen direkt):

```bash
AUTH_MODE=stub
ENV=development
DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
CMDB_MODE=stub
```

Alle verfuegbaren Variablen sind unter [Credentials](../entwicklung/credentials.md) dokumentiert.

---

## Datenbank einrichten

### 1. PostgreSQL-Benutzer und Datenbanken erstellen

```bash
sudo -u postgres createuser -P mpp          # Passwort: mpp
sudo -u postgres createdb -O mpp mpp_dev
sudo -u postgres createdb -O mpp mpp_test
```

### 2. Migrationen ausfuehren

```bash
alembic upgrade head
```

### 3. Demo-Daten laden (optional)

```bash
python3 scripts/seed.py
```

---

## Frontend einrichten

### 1. Node.js (falls nvm verwendet wird)

```bash
nvm use 20
```

### 2. Abhaengigkeiten installieren

```bash
cd frontend
npm install
```

---

## Dev-Launcher

Der einfachste Weg, alles zu starten:

```bash
./scripts/mpp.sh
```

Das interaktive Menue bietet:

1. Nur Backend starten (Port 5000)
2. Nur Frontend starten (Port 3000)
3. Beides starten
4. Tests ausfuehren
5. Demo-Daten laden

---

## Docker / Offline-Installation

MPP kann auch komplett Docker-basiert betrieben werden — ideal fuer Offline-Umgebungen oder schnelles Setup.

### Voraussetzungen

- Docker 24+
- Docker Compose 2.x

### Starten

```bash
docker compose up -d
```

Das startet Backend, Frontend, PostgreSQL und den GitLab-Mock in separaten Containern.

### Bundle Builder (Offline)

Fuer Air-Gapped-Umgebungen kann ein vollstaendiges Bundle erstellt werden:

```bash
bash scripts/bundle-builder.sh
```

Das erzeugt ein tar-Archiv mit allen Docker-Images, Konfigurationen und Seed-Daten. Das Bundle kann auf dem Zielsystem mit `docker compose load` importiert werden.

### Dateien

- `Dockerfile` — Multi-Stage-Build (Backend + Frontend)
- `docker-compose.yml` — Orchestrierung aller Dienste
- `scripts/bundle-builder.sh` — Offline-Bundle-Erstellung

---

## Verifikation

Nach dem Start:

- Backend-Health: [http://localhost:5000/api/v1/health](http://localhost:5000/api/v1/health)
- Frontend: [http://localhost:3000](http://localhost:3000)
- Login mit `test-requester` (kein Passwort noetig im Stub-Modus)
