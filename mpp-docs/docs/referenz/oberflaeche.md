# Oberflächen

Galerie der wichtigsten Screens des Marketplace Portals — Klick auf ein Bild
öffnet die Lightbox-Ansicht (Zoom, Vor/Zurück-Navigation, ESC zum Schließen).

Die Oberfläche ist rollenbasiert: **Requester** bestellen Services, **Approver**
genehmigen, **Admin/Superadmin** verwalten Katalog, Regeln und Audit. Linke
Navigation und sichtbare Bereiche richten sich nach der Rolle des angemeldeten
Benutzers. Die Screenshots zeigen den Stand v1.1.0 (AUTH_MODE=stub) und werden
mit `scripts/run_screenshots.sh` (Playwright) reproduzierbar erzeugt.

---

## Anmeldung

<img src="../../images/screenshots/Screenshot_01_mpp.png"
     alt="Login-Seite des MPP: Anmeldeformular mit Benutzername-/Passwort-Feldern und Anmelden-Button auf der Lucent-Oberfläche.">

Anmeldung über das Backend (`AUTH_MODE`). Im Entwicklungs-/Demo-Betrieb stehen
Stub-Benutzer (`test-requester`, `test-approver`, `test-admin`, `test-multi`,
`test-superadmin`) zur Verfügung; produktiver LDAP-Login ist noch nicht
implementiert.

---

## Dashboard

<img src="../../images/screenshots/Screenshot_02_mpp.png"
     alt="Dashboard: KPI-Kacheln (Offene Orders, Ausstehende Genehmigungen, Aktive Services, Templates), Karte Benachrichtigungen, Tabelle der letzten Bestellungen mit Status-Badges, Donut 'Orders nach Status', Liste beliebter Services und ein Liniendiagramm 'Orders über Zeit'.">

Die Startseite nach dem Login. Oben vier KPI-Kacheln, darunter die letzten
Bestellungen mit Status-Badges, ein Donut „Orders nach Status", die beliebtesten
Services und der Bestell-Verlauf über die Zeit. Die Diagramme nutzen lokal
gebündeltes Chart.js (keine CDN-Abhängigkeit).

---

## Service-Katalog (Shop)

<img src="../../images/screenshots/Screenshot_03_mpp.png"
     alt="Service-Katalog: Suchfeld und Kategorie-Filter oben, darunter Service-Karten (Linux VM, Windows VM) mit Kategorie-Badge 'compute', Kurzbeschreibung, Parameter-Anzahl und Details-/Bestellen-Button.">

Der Katalog listet alle bestellbaren Services als Karten. Suchfeld und
Kategorie-Filter grenzen die Auswahl live ein. Jede Karte zeigt Kategorie,
Kurzbeschreibung, Parameter-Anzahl und Version.

---

## Bestellformular (leer / ausgefüllt)

<div class="adb-shot-compare">
  <figure>
    <img src="../../images/screenshots/Screenshot_04_mpp.png"
         alt="Leeres Bestellformular einer Linux-VM: alle Pflichtfelder auf 'Bitte wählen…', rechts die Zusammenfassung mit Hinweis 'Pflichtfelder noch nicht vollständig'.">
    <figcaption>Leeres Formular</figcaption>
  </figure>
  <figure>
    <img src="../../images/screenshots/Screenshot_05_mpp.png"
         alt="Ausgefülltes Bestellformular einer Linux-VM mit gewählten Parametern und Live-Zusammenfassung der Werte inkl. geschätzter Kosten.">
    <figcaption>Ausgefüllt mit Zusammenfassung</figcaption>
  </figure>
</div>

Das Formular wird dynamisch aus den Template-Parametern erzeugt. **Links** das
leere Formular mit markierten Pflichtfeldern, **rechts** dasselbe Formular
ausgefüllt — die Zusammenfassung rechts aktualisiert live die gewählten Werte und
die geschätzten Kosten vor dem Absenden.

---

## Bestellungen (Workspace)

<img src="../../images/screenshots/Screenshot_06_mpp.png"
     alt="Bestellübersicht (Workspace) mit Tab 'Alle Bestellungen', Tabelle mit Bestellnummer, Service, Status-Badge und Datum.">

Übersicht aller Bestellungen mit Status-Verlauf (pending_approval → validated →
provisioning → done) und Detailansicht je Bestellung.

---

## Eigene Bestellungen

<img src="../../images/screenshots/Screenshot_07_mpp.png"
     alt="Workspace im Tab 'Eigene': auf den angemeldeten Benutzer gefilterte Bestellungen.">

Der Tab „Eigene" filtert die Übersicht auf die Bestellungen des angemeldeten
Benutzers.

---

## Benachrichtigungen

<img src="../../images/screenshots/Screenshot_08_mpp.png"
     alt="Benachrichtigungs-Center mit gelesenen/ungelesenen Einträgen und Markieren-als-gelesen-Aktion.">

Das Benachrichtigungs-Center bündelt Status-Updates zu Bestellungen und
Genehmigungen.

---

## Review Requests (Genehmigungen)

<img src="../../images/screenshots/Screenshot_09_mpp.png"
     alt="Review-Requests-Ansicht: aufklappbare Liste offener Genehmigungen mit Bestelldetails, Deadline sowie Genehmigen-/Ablehnen-Aktion.">

Für **Approver/Admin** sichtbar: offene Genehmigungen mit Bestelldetails und
Deadline sowie Genehmigen-/Ablehnen-Aktion.

---

## Admin — Dashboard

<img src="../../images/screenshots/Screenshot_10_mpp.png"
     alt="Admin-Dashboard mit administrativen Kennzahlen und Verwaltungs-Einstiegen (Konfiguration, Rules, Audit-Log).">

Der administrative Einstieg (Admin/Superadmin) mit Kennzahlen und Verknüpfungen
zu Konfiguration, Regeln und Audit-Log.

---

## Admin — Regeln (Rules)

<img src="../../images/screenshots/Screenshot_11_mpp.png"
     alt="Regel-Verwaltung: Liste der Kontext-/Verfügbarkeitsregeln mit Best-Practice-Seed-Daten und Bearbeiten-Aktionen.">

Verwaltung der Kontext- und Verfügbarkeitsregeln (Best-Practice-Seed-Daten),
die steuern, welche Services in welchem Kontext bestellbar sind.

---

## Admin — Audit-Log

<img src="../../images/screenshots/Screenshot_12_mpp.png"
     alt="Audit-Log-Tabelle mit Zeitstempel, Akteur, Aktion und betroffener Ressource.">

Revisionssicheres Audit-Log aller sicherheitsrelevanten Aktionen (Admin/
Superadmin).
