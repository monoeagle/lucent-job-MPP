# Delivery-/Doku-Parität zum Schwester-Stack: Adaption statt Copy

**Datum:** 2026-06-27
**Kontext:** Das Schwesterprojekt `lucent-job-mpp-TDD-Django` (Django + HTMX) war
bei Delivery und Doku-Site auf v1.1.0 vorausgelaufen (Offline-Release-Workflow,
Produktions-Installer, Oberflächen-Galerie, gh-pages-Deploy, Architektur-Badge,
Heatmap-Toggle). Aufgabe: dieses Flask/React-MPP „im selben Stil" angleichen.

## Erkenntnis

**Zwei Projekte mit identischem Doku-Stack (Zensical + Custom-JS/CSS) lassen sich
beim Doku-Teil 1:1 portieren — beim Delivery-Teil NICHT.** Der Installer und die
Deployment-Doku sind keine kopierbaren Artefakte, sondern Ableitungen der
konkreten Laufzeit-Architektur. Jede Abweichung Django↔Flask erzwang eine
Änderung:

| Django (Quelle) | Flask/React (Ziel) — Adaption |
|---|---|
| `gunicorn config.wsgi:application` | `gunicorn "app:create_app()"` (Factory) |
| `manage.py migrate` + `collectstatic` | `alembic upgrade head`; SPA **prebuilt** via nginx (kein collectstatic) |
| Celery + Redis + `mpp-celery.service` | **entfällt** — Flask hat keine Background-Jobs |
| Node nur indirekt | SPA wird auf dem **Staging-Host** gebaut, VM braucht kein Node |
| Django-Admin/allauth-Login | Auth-Blocker: `AUTH_MODE=ldap` → `NotImplementedError` (ehrlich dokumentiert) |

## Warum das zählt

Ein mechanisch kopierter Installer hätte ein `mpp-celery.service` für einen nicht
existenten Worker angelegt, `collectstatic` auf einem Projekt ohne Django-Static
aufgerufen und einen WSGI-Pfad referenziert, der im Flask-Code nicht existiert —
alles erst auf der Ziel-VM gescheitert. Das ist die Delivery-Variante der
globalen Regel **„Spec/Vorlage gegen den echten Code prüfen, bevor geplant wird"**:
die Django-Dateien sind ein *Zielbild des Stils*, keine Grundwahrheit über den
Flask-Code.

## Wie anwenden

- **Doku-Site-Features** (Galerie, Badges, Heatmap-Toggle, CSS, gh-pages) per
  `diff` exakt portieren — sie sind stack-neutral.
- **Delivery-Artefakte** (Installer, Bundle-Builder, Deployment-Doc) Zeile für
  Zeile gegen den Ziel-Code adaptieren: Entry-Point, Migrations-Tool,
  Dienste-Topologie, Static-/Asset-Strategie, Auth-Realität.
- **Bekannte Lücken ehrlich benennen** statt Funktionsfähigkeit vorzutäuschen:
  der Installer setzt die korrekte Produktions-Haltung (`AUTH_MODE=ldap`) und
  dokumentiert laut, dass der Login bis zur LDAP-Implementierung scheitert.

Siehe auch: [[test-baseline-and-prod-gaps]] (Auth-Blocker), `docs/deployment/vm-installation-offline.md`.
