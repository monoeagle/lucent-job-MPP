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

| Benutzer         | Rolle(n)              |
|------------------|-----------------------|
| test-requester   | requester             |
| test-approver    | approver              |
| test-admin       | admin                 |
| test-multi       | requester + approver  |

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

## 5. Naechste Schritte

- **Approval testen:** Als `test-approver` einloggen und offene Genehmigungen bearbeiten
- **Admin-Dashboard:** Als `test-admin` einloggen fuer Statistiken und Audit-Log
- **API erkunden:** [API-Referenz](../referenz/api-referenz.md) fuer alle 76 Endpoints
