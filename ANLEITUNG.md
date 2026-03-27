# Anleitung — Marketplace Portal (MPP)

Schritt-fuer-Schritt-Anleitung zum Einrichten und Starten des Projekts.

---

## 1. Voraussetzungen

| Software     | Version   | Pruefung                        |
|--------------|-----------|---------------------------------|
| Python       | 3.12+     | `python3 --version`             |
| Node.js      | 22+       | `node --version` (via nvm)      |
| PostgreSQL   | 14+       | `pg_isready`                    |
| pip          | aktuell   | `pip --version`                 |
| npm          | aktuell   | `npm --version`                 |

### Node.js via nvm (empfohlen)

```bash
nvm install 22
nvm use 22
```

### PostgreSQL starten

```bash
sudo systemctl start postgresql
```

---

## 2. Projekt-Setup

### Repository klonen

```bash
cd ~/Dokumente/CLAUDE/lucent-hub-apps/
# Projekt ist bereits unter lucent-app-mpp-TDD/ vorhanden
```

### Python Virtual Environment erstellen

```bash
cd lucent-app-mpp-TDD
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend-Dependencies installieren

```bash
cd frontend
npm install
cd ..
```

---

## 3. Datenbank einrichten

### PostgreSQL-Benutzer und Datenbanken anlegen

```bash
sudo -u postgres createuser -P mpp
# Passwort eingeben: mpp

sudo -u postgres createdb -O mpp mpp_dev
sudo -u postgres createdb -O mpp mpp_test
```

### Schema-Migrationen ausfuehren

```bash
source venv/bin/activate
export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
alembic upgrade head
```

### Demo-Daten laden

```bash
export AUTH_MODE=stub
export CMDB_MODE=stub
python scripts/seed.py
```

Ergebnis: 3 Service-Templates (Linux VM, Windows VM, PostgreSQL DB) + 1 Demo-Bestellung mit 2 Items.

---

## 4. Backend starten

```bash
source venv/bin/activate
export AUTH_MODE=stub
export CMDB_MODE=stub
export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
flask run --port 5000
```

Pruefung: `curl http://localhost:5000/api/v1/health`
Erwartete Antwort: `{"auth_mode":"stub","status":"ok"}`

---

## 5. Frontend starten

In einem neuen Terminal:

```bash
cd frontend
nvm use 22    # falls nvm verwendet wird
npx vite --port 3000
```

Pruefung: Browser oeffnen unter `http://localhost:3000`

---

## 6. Dev-Launcher verwenden (empfohlen)

Der interaktive Launcher startet alles komfortabel:

```bash
bash scripts/mpp.sh
```

Menue-Optionen:
1. Backend starten
2. Frontend starten
3. Beides starten
4. Backend stoppen
5. Frontend stoppen
6. Logs anzeigen
7. Tests ausfuehren
q. Beenden

Der Launcher prueft automatisch Voraussetzungen (PostgreSQL, venv, Node.js) und fuehrt Migrationen und Seed aus.

---

## 7. Tests ausfuehren

### Backend-Tests

```bash
source venv/bin/activate
export DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test
pytest tests/ --tb=short -q
```

Erwartete Ausgabe: 594 Tests bestanden.

### Frontend-Tests

```bash
cd frontend
npx vitest run
```

Erwartete Ausgabe: 47 Tests bestanden.

### Alle Tests (via Launcher)

```bash
bash scripts/mpp.sh
# Option 7 waehlen, dann Option 3 (Alle Tests)
```

---

## 8. Demo-Flow Walkthrough

### 8.1 Anmelden

1. Browser oeffnen: `http://localhost:3000`
2. Anmelden als `test-requester` (kein Passwort noetig)
3. Bestelluebersicht wird angezeigt

### 8.2 Katalog durchsuchen

1. Navigation: **Katalog** in der Sidebar
2. Service-Templates werden angezeigt (Linux VM, Windows VM, PostgreSQL DB)
3. Klick auf ein Template oeffnet den Detail-Drawer

### 8.3 Bestellung erstellen

1. Navigation: **Bestellungen** → **Neue Bestellung**
2. Titel eingeben: "Test Web-Cluster"
3. Service hinzufuegen: "Linux VM" waehlen
4. Parameter konfigurieren: CPU=4, RAM=16 GB, OS=Ubuntu 22.04, Disk=100 GB
5. Weiteren Service hinzufuegen: "PostgreSQL Datenbank"
6. Parameter: Version=16, Speicher=50 GB

### 8.4 Bestellung validieren und einreichen

1. Klick auf **Validieren** — alle Items werden geprueft
2. Status wechselt zu `validated`
3. Klick auf **Einreichen**
4. Falls Approval-Regeln greifen → Status `pending_approval`
5. Falls keine Regeln greifen → direkt `submitted` oder `provisioning`

### 8.5 Als Approver genehmigen (optional)

1. Abmelden
2. Anmelden als `test-approver`
3. Navigation: **Genehmigungen**
4. Offene Anfrage anzeigen und genehmigen

### 8.6 Admin-Funktionen

1. Abmelden
2. Anmelden als `test-admin`
3. Navigation: **Admin** → Dashboard mit Statistiken
4. **Admin** → **Regeln** — Approval-Regeln verwalten
5. **Admin** → **Audit-Log** — alle Aktionen einsehen

---

## Haeufige Probleme

| Problem                          | Loesung                                              |
|----------------------------------|------------------------------------------------------|
| PostgreSQL laeuft nicht          | `sudo systemctl start postgresql`                    |
| Migrations-Fehler                | `alembic downgrade base && alembic upgrade head`     |
| Port 5000 belegt                 | `lsof -i :5000` und Prozess beenden                  |
| Node.js-Version falsch           | `nvm use 22`                                         |
| Frontend baut nicht              | `cd frontend && rm -rf node_modules && npm install`  |
| Datenbank existiert nicht        | Schritt 3 wiederholen                                |
