---
description: Git-Konventionen und Ausschluesse fuer MPP
globs: ".gitignore"
---
- Folgende Verzeichnisse/Dateien NIEMALS committen:
  - __pycache__/, *.pyc, .pytest_cache/ (Python-Artefakte)
  - node_modules/ (Node-Dependencies)
  - venv/, **/.venv-docs/ (Python Virtual Environments)
  - frontend/dist/, frontend/tsconfig.tsbuildinfo (Build-Output)
  - **/site/ (generierte Doku-Seiten)
  - logs/, screenshots/ (Laufzeit-Artefakte)
  - _TRANSFER_NON_DOCKER*/ (Transfer-Verzeichnisse)
  - agents_md.zip (generiertes Archiv)
- Virtual Environments unter Unterverzeichnissen brauchen **/-Prefix in .gitignore
- Wenn ein Verzeichnis bereits getrackt ist: `git rm -r --cached <pfad>` (entfernt nur aus Index)
