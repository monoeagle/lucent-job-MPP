# Session-Kennzahlen — MPP

Eine Zeile pro Session (Schema: `<projects-root>/.pattern/session-handoff-kpi.pattern`).
Ableitbare KPIs: Tokens/Commit, Tokens/MINOR, Tests-Δ je 100k Tokens, Fang-Quote
(Review-Bugs / (Review+Gerät)), Doc-vs-Code-Anteil, Modell-Mix.

| # | Datum | Modell | Tokens ges. (Msg/Tools) | Commits (Merges) | Tests (von→bis, Δ) | Version (von→bis) | Subagenten | Features / APs | Verifiziert | LOC (authored / getrackt) | Dateien | feat/fix | Review-Bugs | Gerät-Bugs | Notiz |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-06-18 | Opus 4.8 (1M) | n/a¹ | 0 (0) | 862→862 (0) | 1.0.0→1.0.0 | 0 | Doku-App-Look (Icon-Rail/Heatmap/Hero), AP-Übersicht+Gantt, TDD-Gate (11 Regeln), Ein-Befehl-Release (`run.sh docs-appimage`), AppRun Random-Port + isolierte Chromium-Instanz | Site gebaut · Docs-AppImage smoke-getestet (HTTP 200, Random-Port 50609) | ~219 / 2283+ −156² | 15 Repo + 3 Pattern + 3 Handoff | 0/0 | 1³ | 0 | Reine Doku/Tooling-Session, kein App-Code; uncommitted an nächste Session übergeben |

**Fußnoten:**
1. Token-Zahlen aus `/context` nicht verfügbar (Tool-/Headless-Modus, kein `/context`-Zugriff) — bei nächster interaktiver Session nachtragen.
2. *authored* = neu geschriebener Text (`verify_docs.sh` ~120, `arbeitspakete.md` ~80, `ueberblick.md` ~55) ohne kopierte/generierte Blobs; *getrackt* = `git diff --shortstat` (enthält kopierte `extra.css` ~1980 Z. + Edits; `mermaid.min.js` 3 MB binär nicht gezählt).
3. TDD-Gate fing `R-NO-PLACEHOLDER` (ADAPT-Marker-Reste in `icon-rail.js`) **vor** „fertig" → rot→fix→grün. Fang-Quote dieser Session = 1/1 = 100 %.
