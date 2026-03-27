# Shop-Wizard / Service Request Flow — Design Spec

**Ziel:** Zwei umschaltbare Darstellungsvarianten (Wizard und Formular) fuer die Service-Konfiguration bei Bestellungen. Gefuehrter Step-by-Step Flow oder scrollbare Einzelseite, mit Context-Integration, Quantity-Support und Cluster-Unterstuetzung.

---

## Einstiegspunkte

### Schnellbestellung (Template-First)
Shop → Template-Karte → "Bestellen" → `/shop/{slug}/request` → Context + Parameter konfigurieren → Bestaetigung → Order wird erstellt + Item hinzugefuegt → Weiterleitung zu OrderDetail

### Aus bestehender Order (Order-First)
OrderDetail → "Service hinzufuegen" → Template waehlen → selbe Konfigurationsseite als Fullscreen-Drawer oder eigene Seite `/orders/{orderId}/add/{slug}` → Item wird zur Order hinzugefuegt

### Kopie aus bestehendem Item (Cluster-Shortcut)
OrderDetail → Item-Karte → "Aehnlichen Service hinzufuegen" → Konfigurationsseite mit vorausgefuellten Werten → User passt ab, aendert Quantity/Parameter → neues Item wird hinzugefuegt (optional in selbe Gruppe)

---

## Zwei Darstellungsvarianten

### Variante 1: Wizard-Modus (Step-by-Step)

Gefuehrter Flow durch Parameter-Gruppen als einzelne Steps.

**Layout:**
- Titel + Toggle-Button oben rechts ("Formular-Ansicht")
- Step-Leiste unter dem Titel: zeigt alle Steps mit Status (erledigt/aktuell/offen)
- Aktueller Step-Inhalt mit Gruppentitel und Parameter-Feldern
- Navigation unten: [Zurueck] und [Weiter]
- Letzter Step: Zusammenfassung + Quantity + Bestaetigungsbutton

**Step-Verhalten:**
- "Weiter" validiert Pflichtfelder des aktuellen Steps. Bei Fehlern bleiben Felder rot markiert.
- "Zurueck" speichert ausgefuellte Werte (kein Datenverlust)
- Klick auf erledigten Step in der Step-Leiste springt zurueck
- Steps mit 0 sichtbaren Feldern (alle per depends_on ausgeblendet) werden uebersprungen

### Variante 2: Formular-Modus (Scrollbare Seite)

Alle Parameter-Gruppen als Sektionen untereinander auf einer scrollbaren Seite.

**Layout:**
- Titel + Toggle-Button oben rechts ("Wizard-Ansicht")
- Optionale Anchor-Navigation (Sprunglinks zu jeder Sektion)
- Sektionen mit Gruppentitel, Trennlinie, Parameter-Felder
- depends_on Felder werden live ein-/ausgeblendet
- Zusammenfassung am Ende der Seite mit Quantity + Bestaetigungsbutton

---

## Step-Reihenfolge

### Bei vorhandener wizard_config am Template

Die Reihenfolge wird exakt durch `wizard_config.steps` bestimmt. Kontext ist immer Step 1, Zusammenfassung immer letzter Step (beide werden automatisch hinzugefuegt).

Beispiel fuer VM-Template (verbindliche Reihenfolge aus Anforderung):

```json
{
  "wizard_config": {
    "preferred_view": "wizard",
    "steps": [
      { "group": "Typ", "label": "Typ" },
      { "group": "Netzwerk", "label": "Hostnamen- und Netzwerkkonfiguration" },
      { "group": "Platzierung", "label": "Platzierung" },
      { "group": "Betriebssystem", "label": "Betriebssystem" },
      { "group": "VM Sizing", "label": "VM Sizing" },
      { "group": "Datenspeicher", "label": "Datenspeicher" },
      { "group": "Server Informationen", "label": "Server Informationen" },
      { "group": "Softwaremanagement", "label": "Softwaremanagement" },
      { "group": "Backup", "label": "Backup" }
    ]
  }
}
```

Resultierende Step-Folge:
1. Kontext (automatisch)
2. Typ
3. Hostnamen- und Netzwerkkonfiguration
4. Platzierung
5. Betriebssystem
6. VM Sizing
7. Datenspeicher
8. Server Informationen
9. Softwaremanagement
10. Backup
11. Zusammenfassung (automatisch)

### Ohne wizard_config

Fallback: Steps aus Parameter-Gruppen, sortiert nach dem niedrigsten `display_order` innerhalb jeder Gruppe. `preferred_view` Default: `"wizard"`.

### Formular-Modus

Selbe Reihenfolge wie Wizard-Steps, aber als Sektionen statt Steps.

---

## Context als erster Step

Unabhaengig von der Variante ist Context-Auswahl immer der erste Abschnitt:
- Standort (Location)
- Mandant (Tenant)
- Sicherheitszone (Security Zone)
- Netzwerk (optional, abhaengig von Standort + Zone)

Bei Schnellbestellung: Context wird frisch abgefragt.
Bei Order-First: Wenn die Order bereits einen Context hat, wird er vorausgefuellt und ist aenderbar.

Die bestehende `ContextSelector`-Komponente wird wiederverwendet.

---

## Quantity und Cluster-Support

### Einzelne Konfiguration vervielfachen (Quantity)

Der QuantitySelector erscheint im letzten Step (Zusammenfassung). User gibt Anzahl ein (1-50).

Bei quantity > 1:
- per_instance="auto" Felder (z.B. Hostname): Hinweis "(wird automatisch vergeben)"
- per_instance=true Felder: Eingabefelder pro Instanz im Zusammenfassungs-Step
- Shared-Parameter gelten fuer alle Instanzen

### Cluster mit verschiedenen Konfigurationen

Kein eigener Cluster-Wizard. Stattdessen sequentieller Aufbau ueber bestehende Groups:

1. User konfiguriert ersten Service (z.B. 5x Web-VM), fuegt ihn hinzu
2. Auf OrderDetail: Item-Karte zeigt "Aehnlichen Service hinzufuegen"-Button
3. Klick oeffnet Konfigurationsseite mit **vorausgefuellten Werten** des Quell-Items
4. User aendert was noetig ist (anderes Template, andere Params, andere Quantity)
5. Neues Item wird zur Order hinzugefuegt, optional in dieselbe Gruppe

**Kopier-Flow:**
- Alle Parameter werden uebernommen (soweit kompatibel)
- Template kann gewechselt werden — nicht-kompatible Parameter werden zurueckgesetzt
- Quantity wird zurueckgesetzt auf 1
- instance_parameters werden nicht kopiert
- Group-Zuordnung des Quell-Items wird als Default vorgeschlagen

---

## Toggle-Verhalten

- Toggle-Button oben rechts: "Wizard-Ansicht" / "Formular-Ansicht"
- Wechsel behaelt alle ausgefuellten Werte bei
- Template hat `preferred_view` Feld (`"wizard"` oder `"form"`, Default: `"wizard"`)
- User-Override wird in localStorage persistiert unter Key `mpp-view-{slug}`
- Prioritaet: localStorage > Template-Default

---

## Template preferred_view

Neues optionales Feld am ServiceTemplate:
- Feld: `preferred_view` (String, nullable, Default: null → behandelt als "wizard")
- Gespeichert in der bestehenden JSONB `metadata` Spalte des Templates (kein DB-Schema-Upgrade)
- Admin setzt beim Template-Erstellen oder -Bearbeiten
- Werte: `"wizard"`, `"form"`

---

## Betroffene Dateien

### Frontend — Neu
- `frontend/src/pages/ServiceRequest.tsx` — Hauptseite fuer Konfiguration (beide Varianten)
- `frontend/src/components/orders/WizardView.tsx` — Wizard-Step-Container mit Navigation
- `frontend/src/components/orders/FormView.tsx` — Scrollbare Formular-Ansicht mit Sektionen
- `frontend/src/components/orders/StepIndicator.tsx` — Step-Leiste fuer Wizard
- `frontend/src/components/orders/RequestSummary.tsx` — Zusammenfassungs-Sektion (beide Varianten)

### Frontend — Aendern
- `frontend/src/pages/Catalog.tsx` — "Bestellen"-Button pro Template-Karte
- `frontend/src/App.tsx` — Route `/shop/:slug/request` und `/orders/:orderId/add/:slug`
- `frontend/src/components/orders/OrderItemCard.tsx` — "Aehnlichen Service hinzufuegen"-Button
- `frontend/src/pages/OrderDetail.tsx` — Kopier-Flow Einstieg, Fullscreen-Drawer oder Redirect

### Frontend — Wiederverwenden (nicht aendern)
- `frontend/src/components/ParameterForm/` — Alle Feld-Komponenten
- `frontend/src/components/orders/ContextSelector.tsx` — Context-Auswahl
- `frontend/src/components/orders/QuantitySelector.tsx` — Quantity-Eingabe

### Backend — Nicht aendern
- Keine neuen Endpoints noetig
- preferred_view wird in bestehender Template-Metadata gespeichert
- wizard_config wird in bestehender Template-Metadata gespeichert
- Order/Item/Group-APIs bleiben unveraendert

---

## Abgrenzung (NICHT in Scope)

- Warenkorb (mehrere Items vor Order-Erstellung sammeln)
- Echtzeit-Kostenkalkulation
- Template-Empfehlungen basierend auf Context
- Admin-UI fuer wizard_config (wird manuell in Template-JSON gesetzt)
- Cluster-Templates (vordefinierte Multi-Service-Bundles)
- Drag-and-Drop Reihenfolge der Steps
