# MPP — Marketplace Portal

Das **Marketplace Portal (MPP)** ist ein Self-Service-Portal fuer die automatisierte Bereitstellung von IT-Services. Endanwender (Requester) koennen aus einem Servicekatalog VMs, Datenbanken und Container bestellen. Die Bestellungen durchlaufen einen definierten Lifecycle mit optionaler Genehmigung und werden automatisch via GitLab-Pipelines provisioniert.

---

## Was kann MPP?

- **Services bestellen** — VMs, Datenbanken, Container aus einem konfigurierbaren Servicekatalog
- **Shop Wizard** — Wizard/Formular-Toggle mit T-Shirt-Sizes und wizard_config
- **Order-Lifecycle** — Draft → Validated → Submitted → Provisioning → Done
- **Order Groups + Quantity** — Gruppierte Items mit Mengenangabe und Per-Instance-Parametern
- **Subscriptions** — Lifecycle-Management mit Change/Cancel und Approval-Integration
- **Kontextabhaengig** — Standort, Mandant, Sicherheitsbereich beeinflussen Verfuegbarkeit und Parameter
- **Dependency Matrix** — 15 Cross-Field-Abhaengigkeiten mit ~45.000 validen Kombinationen
- **Approval-Workflow** — Automatische Genehmigungspflicht fuer kostenintensive Bestellungen
- **Automatische Provisionierung** — GitLab-Pipeline-Integration mit OpenTofu
- **Rollenbasiert** — Requester, Approver, Admin, Superadmin mit abgestuften Berechtigungen
- **Dashboard** — Statistiken, Suche und Recharts-Charts
- **Notifications** — Read/Unread-Status, Event-Trigger, E-Mail-Stub
- **DSGVO-Anonymisierung** — Middleware fuer datenschutzkonforme Anonymisierung (Admin-Toggle)
- **Audit-Trail** — Vollstaendige Protokollierung aller Aktionen
- **Einmal-Links** — Sichere Zustellung von Zugangsdaten nach Provisionierung
- **Offline-Installer** — Docker-basierte Installation (Dockerfile, docker-compose, Bundle Builder)
- **Screenshot-Tool** — Playwright-basiert, WebP-Format, rollenspezifisch

## Tech-Stack

| Komponente    | Technologie                              |
|---------------|------------------------------------------|
| Backend       | Python 3.12 + Flask 3.1                  |
| Frontend      | React 19 + TypeScript 5.7 + Vite 6      |
| Datenbank     | PostgreSQL + SQLAlchemy 2.0 + Alembic    |
| State         | tanstack-query 5 + zustand 5             |
| Styling       | TailwindCSS 4                            |
| Tests         | pytest (Backend) + vitest (Frontend)     |
| IaC           | OpenTofu (Export-Format)                 |
| Dokumentation | Zensical (MkDocs-kompatibel)             |

## Kennzahlen

| Metrik              | Wert  |
|---------------------|-------|
| Backend-Tests       | 756   |
| Frontend-Tests      | 106   |
| Tests gesamt        | 862   |
| API-Endpoints       | 96    |
| API-Module          | 17    |
| Datenbanktabellen   | 15    |
| Frontend-Seiten     | 17    |
| Frontend-API-Module | 10    |
| Frontend-Hook-Module| 7     |
| Backend-Services    | 13    |

## Ansatz

MPP wurde vollstaendig mit **Test-Driven Development (TDD)** entwickelt. Jedes Feature entstand im Red-Green-Refactor-Zyklus. Beide Seiten (Backend und Frontend) folgen **Clean Architecture** mit strikter Dependency-Richtung.

## Lucent Hub

MPP laeuft im Lucent Hub Oekosystem. Backend auf Port **5000**, Frontend auf Port **3000**. Start ueber `scripts/mpp.sh` (interaktiver Dev-Launcher).
