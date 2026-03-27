# Troubleshooting

Haeufige Probleme und deren Loesungen.

---

## Port bereits belegt

**Symptom:** `Address already in use` beim Starten von Backend oder Frontend.

**Loesung:**

```bash
# Prozess auf Port 5000 finden und beenden
lsof -i :5000
kill <PID>

# Oder fuer Frontend (Port 3000)
lsof -i :3000
kill <PID>
```

---

## PostgreSQL laeuft nicht

**Symptom:** `Connection refused` oder `could not connect to server` beim Backend-Start.

**Loesung:**

```bash
# Status pruefen
sudo systemctl status postgresql

# Starten
sudo systemctl start postgresql

# Pruefen, ob die Datenbank existiert
psql -U mpp -d mpp_dev -c "SELECT 1"
```

Falls die Datenbank nicht existiert:

```bash
sudo -u postgres createuser -P mpp          # Passwort: mpp
sudo -u postgres createdb -O mpp mpp_dev
sudo -u postgres createdb -O mpp mpp_test
```

---

## Node.js-Version zu alt

**Symptom:** Fehler beim `npm install` oder Frontend-Build. Vite 6 und React 19 benoetigen Node.js 20+.

**Loesung:**

```bash
# Version pruefen
node --version

# Mit nvm aktualisieren
nvm install 20
nvm use 20
```

---

## Alembic-Migrationen fehlgeschlagen

**Symptom:** `alembic upgrade head` schlaegt fehl.

**Moegliche Ursachen:**

1. **Datenbank nicht erreichbar:** Siehe "PostgreSQL laeuft nicht"
2. **Inkonsistenter Zustand:** Migration-Version in DB stimmt nicht mit Dateien ueberein

**Loesung (Reset fuer Entwicklung):**

```bash
# Datenbank zuruecksetzen
sudo -u postgres dropdb mpp_dev
sudo -u postgres createdb -O mpp mpp_dev
alembic upgrade head
python3 scripts/seed.py
```

---

## CMDB nicht verfuegbar

**Symptom:** Fehler bei Kontext-Aufloesung oder leere Dropdown-Listen im Frontend.

**Loesung:** Sicherstellen, dass der CMDB-Stub aktiv ist:

```bash
# In .env oder als Environment-Variable
CMDB_MODE=stub
CMDB_STUB_DATA_PATH=./stubs/cmdb/
```

Pruefen, ob die YAML-Dateien vorhanden sind:

```bash
ls stubs/cmdb/
# Erwartet: locations.yaml  networks.yaml  security_zones.yaml  tenants.yaml
```

---

## GitLab-Mock reagiert nicht

**Symptom:** Provisioning bleibt im Status `dispatched` haengen.

**Loesung:**

```bash
# Pruefen, ob der Mock laeuft
curl http://localhost:8088/api/v4/projects/1

# Falls nicht: Starten
python3 stubs/gitlab_mock.py
```

---

## JWT-Token abgelaufen

**Symptom:** `401 Unauthorized` bei API-Aufrufen, obwohl der Benutzer eingeloggt ist.

**Loesung:**

- Im Frontend: Seite neu laden (Session wird wiederhergestellt)
- Token-TTL erhoehen: `STUB_TOKEN_TTL_SECONDS=172800` (48 Stunden)
- Erneut einloggen

---

## Frontend zeigt keine Daten

**Symptom:** Seiten laden, aber Tabellen und Listen sind leer.

**Checkliste:**

1. Backend laeuft? → `curl http://localhost:5000/api/v1/health`
2. CORS-Fehler in der Browser-Konsole?
3. Demo-Daten geladen? → `python3 scripts/seed.py`
4. Auth-Token gueltig? → Erneut einloggen

---

## Tests schlagen fehl

**Symptom:** `pytest` meldet Fehler.

**Haeufige Ursachen:**

```bash
# Test-Datenbank existiert nicht
sudo -u postgres createdb -O mpp mpp_test

# Migrationen nicht aktuell
DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test alembic upgrade head

# Abhaengigkeiten veraltet
pip install -r requirements.txt
```

---

## Allgemeine Diagnose

```bash
# Backend-Health
curl -s http://localhost:5000/api/v1/health | python3 -m json.tool

# Stub-Benutzer auflisten
curl -s http://localhost:5000/api/v1/dev/auth/stub-users | python3 -m json.tool

# CMDB-Health
curl -s -H "Authorization: Bearer <token>" http://localhost:5000/api/v1/cmdb/health

# Logs pruefen
tail -f logs/*.log
```
