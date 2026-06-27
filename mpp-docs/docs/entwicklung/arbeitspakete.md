# Arbeitspakete & Roadmap

Die Arbeitspakete (APs) wurden **retrospektiv aus der Git-Historie** rekonstruiert
(feat-Commits + Changelog-Phasen, vgl. `CHANGELOG.md`). Backend und Frontend folgen
jeweils sieben Phasen, danach Integration und Auslieferung.

## AP-Überblick

<div class="adb-home-arch-wide">

<img src="../images/mermaid/entwicklung-arbeitspakete-1.svg" alt="Diagramm 1 aus entwicklung/arbeitspakete.md">

</div>

Pfeil-Semantik: `-->` Reihenfolge · `==>` Schlüsselkante · `-.->` lose/optionale Abhängigkeit.
Status: <span style="color:#2ecc71">■</span> erledigt · <span style="color:#f1c40f">■</span> in Arbeit · <span style="color:#7c83ff">■</span> geplant.

## Roadmap (Gantt)

Zeitachse aus den echten Commit-Datumsbereichen (Bulk-Entwicklung 26.–28.03.2026,
Integration und Packaging bis April, Doku-App-Look im Juni).

<img src="../images/mermaid/entwicklung-arbeitspakete-2.svg" alt="Diagramm 2 aus entwicklung/arbeitspakete.md">

## Kürzlich erledigt (v1.1.0 · 2026-06-27)

- **Offline-Release-Bundle + Produktions-Installer** — `./run.sh release` +
  `tools/build_release.py` erzeugen ein versioniertes Offline-ZIP (prebuilt SPA +
  Wheels); `deploy/install.sh` installiert auf AlmaLinux 9 (gunicorn, nginx-SPA,
  self-signed TLS, systemd; kein Celery/Redis). Doku: `vm-installation-offline.md`.
  (war zuvor „Offline-Demo-Installscript" in der Offen-Liste.)
- **Doku-Parität v1.1.0** — Oberflächen-Galerie, gh-pages-Deploy, Architektur-Badge
  (`index-1.svg`), Heatmap-Klick-Toggle.

## Offene Arbeitspakete

Quelle: `todos.md` (Repo-Root).

- **Prereqs im Dev-Launcher** — Prerequisites sammeln und einen Prereqs-Eintrag in
  den Dev-Launcher (`scripts/mpp.sh`) aufnehmen.
