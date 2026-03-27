# MPP — Marketplace Portal

Das **Marketplace Portal (MPP)** ist ein Self-Service-Portal fuer die automatisierte Bereitstellung von IT-Services. Endanwender (Requester) koennen aus einem Servicekatalog VMs, Datenbanken und Container bestellen. Die Bestellungen durchlaufen einen definierten Lifecycle mit optionaler Genehmigung und werden automatisch via GitLab-Pipelines provisioniert.

---

## Was kann MPP?

- **Services bestellen** — VMs, Datenbanken, Container aus einem konfigurierbaren Servicekatalog
- **Order-Lifecycle** — Draft → Validated → Submitted → Provisioning → Done
- **Kontextabhaengig** — Standort, Mandant, Sicherheitsbereich beeinflussen Verfuegbarkeit und Parameter
- **Approval-Workflow** — Automatische Genehmigungspflicht fuer kostenintensive Bestellungen
- **Automatische Provisionierung** — GitLab-Pipeline-Integration mit OpenTofu
- **Rollenbasiert** — Requester, Approver, Admin mit abgestuften Berechtigungen
- **Audit-Trail** — Vollstaendige Protokollierung aller Aktionen
- **Einmal-Links** — Sichere Zustellung von Zugangsdaten nach Provisionierung

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
| Backend-Tests       | 594   |
| Frontend-Tests      | 47    |
| Tests gesamt        | 641   |
| API-Endpoints       | 76    |
| Datenbanktabellen   | 12    |
| Alembic-Migrationen | 9     |
| Frontend-Seiten     | 11    |
| Backend-Services    | 10    |
| Commits             | 77    |

## Ansatz

MPP wurde vollstaendig mit **Test-Driven Development (TDD)** entwickelt. Jedes Feature entstand im Red-Green-Refactor-Zyklus. Beide Seiten (Backend und Frontend) folgen **Clean Architecture** mit strikter Dependency-Richtung.

## Lucent Hub

MPP laeuft im Lucent Hub Oekosystem. Backend auf Port **5000**, Frontend auf Port **3000**. Start ueber `scripts/mpp.sh` (interaktiver Dev-Launcher).
