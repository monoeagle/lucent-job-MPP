# Schnellstart

Diese Anleitung fuehrt in 5 Minuten durch den kompletten Bestell-Flow.

---

## 1. Starten

```bash
./scripts/mpp.sh
```

Waehle Option **[3] Beides starten** — Backend (Port 5000) und Frontend (Port 3000) werden gleichzeitig gestartet.

---

## 2. Browser oeffnen

Navigiere zu [http://localhost:3000](http://localhost:3000).

---

## 3. Login

Waehle den Benutzer **test-requester** aus der Liste. Im Stub-Modus ist kein Passwort erforderlich.

Verfuegbare Benutzer:

| Benutzer         | Rolle(n)              | Passwort          |
|------------------|-----------------------|-------------------|
| test-requester   | requester             | (keins / beliebig)|
| test-approver    | approver              | (keins / beliebig)|
| test-admin       | admin                 | (keins / beliebig)|
| test-multi       | requester + approver  | (keins / beliebig)|
| test-superadmin  | superadmin            | (keins / beliebig)|

---

## 4. Demo-Flow

### Schritt 1: Servicekatalog ansehen

Navigiere zu **Catalog** in der Sidebar. Hier sind alle verfuegbaren Service-Templates aufgelistet — VMs, Datenbanken, Container.

### Schritt 2: Neue Bestellung erstellen

1. Klicke auf **Orders** → **Neue Bestellung**
2. Gib einen Titel und eine geschaeftliche Begruendung ein
3. Waehle den Kontext (Standort, Tenant, Sicherheitszone)

### Schritt 3: Services hinzufuegen

1. Klicke **Service hinzufuegen**
2. Waehle ein Template aus dem Katalog (z.B. "Linux VM")
3. Konfiguriere die Parameter (CPU, RAM, Disk, etc.)
4. Wiederhole fuer weitere Services

### Schritt 4: Validieren

Klicke **Validieren** — das System prueft alle Parameter gegen die Template-Constraints und Cross-Parameter-Rules.

### Schritt 5: Einreichen

Klicke **Einreichen** — die Bestellung wechselt in den Status `submitted`. Je nach Kosten und Regeln wird entweder:

- Direkt provisioniert (Status → `provisioning`)
- Zur Genehmigung vorgelegt (Status → `pending_approval`)

---

## 5. Datenbank zuruecksetzen

Falls die Datenbank in einen inkonsistenten Zustand geraet:

```bash
# Datenbank komplett neu aufsetzen
alembic downgrade base
alembic upgrade head
python3 scripts/seed.py
```

---

## 6. Screenshot-Tool

Automatische Screenshots aller Seiten (rollenspezifisch) mit Playwright:

```bash
python3 scripts/screenshot.py
```

Screenshots werden im WebP-Format erzeugt und nach Benutzerrolle gruppiert.

---

## 7. Naechste Schritte

- **Approval testen:** Als `test-approver` einloggen und offene Genehmigungen bearbeiten
- **Admin-Dashboard:** Als `test-admin` einloggen fuer Statistiken und Audit-Log
- **Superadmin testen:** Als `test-superadmin` einloggen fuer DSGVO-Anonymisierung
- **API erkunden:** [API-Referenz](../referenz/api-referenz.md) fuer alle 96 Endpoints
