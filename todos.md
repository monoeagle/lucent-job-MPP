-- ERLEDIGT (Session 3, 2026-06-27): Offline-Demo-/Produktions-Installation
   → ./run.sh release + tools/build_release.py (versioniertes Offline-ZIP, prebuilt SPA + Wheels)
   → deploy/install.sh (AlmaLinux 9: gunicorn + nginx-SPA + TLS + systemd, kein Celery/Redis)
   → docs/deployment/vm-installation-offline.md (air-gapped)

--
sammel die Prereqs zusammen und füge einen Prereqs Eintrag in den DEv Launcher ein
