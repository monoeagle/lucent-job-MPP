# Insight — Doku-App-Look-Migration + TDD-Gate (2026-06-18)

Nicht-offensichtliche Erkenntnisse und Sackgassen dieser Session. Code-Struktur steht im Repo;
hier nur, was in einer frischen Session **überraschen** würde.

## 1. „Pattern anwenden" hieß: ein bestehendes `mpp-docs/` an einen *neueren* Pattern-Stand angleichen
`mpp-docs/` existierte schon (zensical.toml), war aber auf altem Stand: `extra.css` 9-Zeilen-
Platzhalter, kein `docs/javascripts/`, kein `tools/`, alte `build_docs.py`. Der „App-Look" (§17:
Icon-Rail + Heatmap + Hero) kam erst 2026-06 dazu. **Lehre:** bei „Doku anpassen" zuerst den
Ist-Stand gegen den *aktuellen* Pattern diffen, nicht von Null bauen.

## 2. Startseite ist NUR das Home-Layout — Hero = AP-Übersicht, kein Fließtext
Erster Versuch hatte H1 + „Was kann MPP"/Tech-Stack/Kennzahlen auf der Startseite + ein
Architektur-Diagramm als Hero. **Falsch.** Lebende Referenzen (libreDrive, snoocount): `index.md`
enthält *ausschließlich* `.adb-home-layout` (Hero = `…-arbeitspakete-1.svg`, Heatmap, Insights),
**kein H1, kein Inhalt darunter**. Beschreibung gehört auf eine eigene Seite. Der Gantt ist NICHT
auf der Startseite, sondern im **Header-Button** (`roadmapSvgUrl` → `…-arbeitspakete-2.svg`).

## 3. Hero/Gantt-SVGs entstehen aus zwei ```mermaid-Blöcken einer *anderen* Seite
`index.md` referenziert nur das fertige SVG. Quelle: zwei Mermaid-Blöcke in
`entwicklung/arbeitspakete.md` → Build extrahiert nach `mermaid-sources/` → rendert
`entwicklung-arbeitspakete-1.svg` (Flowchart) + `-2.svg` (Gantt). `extract` ist **destruktiv**
(```mermaid → `<img>`). mmdc/Chromium war vorhanden → SVGs real gerendert. Gantt-Fallstrick
beachtet: keine `:` in Task-Titeln, volle Daten + Tagesdauern.

## 4. Das TDD-Gate hat sofort einen echten Fehler gefangen
`verify_docs.sh` (11 Regeln) lief zuerst **rot**: `R-NO-PLACEHOLDER` → die `// ADAPT:`-Marker-
Kommentare standen noch in `icon-rail.js` (lebende Referenzen strippen sie). rot→fix→grün. Das ist
der Wert des Gates: meine vorherige „fertig"-Behauptung war es *nicht*. **Lehre:** „Build lief
durch" ≠ fertig; nur ein grüner, reproduzierbarer Gate zählt.

## 5. Globaler `AppImages/`-Sammelordner wird vom run.sh NICHT automatisch bedient
Es gibt `<projects-root>/AppImages/` (zentral, neben allen Lucent-Apps). `run.sh docs-appimage`
kopierte nur nach `release/` → die globale Kopie hing einen ganzen App-Look-Build hinterher.
Jetzt in `cmd_docs_appimage` automatisiert (atomar per `mv`, busy-fest).

## 6. „busy"/ETXTBSY beim Überschreiben der globalen AppImage
Die alte AppImage lief (FUSE-gemountet) → `cp` scheiterte mit „Das Programm kann nicht … (busy)".
**Lösung:** nicht in-place überschreiben, sondern **atomar per rename** (`cp …/.x.new` + `mv -f`)
— der laufende Prozess behält seinen Inode, die Datei ist für den nächsten Start frisch.

## 7. Doku-Browser-Problem war KEIN Portproblem, sondern `xdg-open`
Die AppRun öffnete via `xdg-open` den **Default-Browser** (Firefox) und hängte sich in dessen
Session. **Fix:** isolierte Chromium-Instanz mit eigenem Temp-Profil (`--user-data-dir=$(mktemp -d)
--app=URL`). Zusätzlich Standalone-Port auf **ephemeral/random** (`bind(127.0.0.1,0)`) — fix nur
im Hub-Modus (`--port=`), weil der Hub den Port zum Tab-Öffnen kennen muss.

## 8. run.sh-Build umgeht den `pip`-Bug des run-Scripts
`run_mpp_docs.sh --build` scheitert auf diesem System an `externally-managed-environment` (will
Zensical neu installieren). `cmd_docs_appimage` Stufe-1 ruft daher **direkt** `.venv-docs/bin/
python3 build_docs.py` (Zensical 0.0.31 ist im venv) mit Fallback aufs run-Script.

## Zurückgeführt ins Pattern
`docs-release-sync.pattern`: §B.3 (globaler Spiegel + busy-Replace), §C (cmp-Check), §G (TDD-Gate
als Pflicht, 11 Regeln, rot→grün), §H (Standalone-AppImage: Random-Port + isolierte Chromium-
Instanz). Damit gelten alle Erkenntnisse ökosystemweit, nicht nur für MPP.
