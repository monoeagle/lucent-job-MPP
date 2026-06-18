# Session-Kennzahlen — MPP

Eine Zeile pro Session (Schema: `<projects-root>/.pattern/session-handoff-kpi.pattern`).
Ableitbare KPIs: Tokens/Commit, Tokens/MINOR, Tests-Δ je 100k Tokens, Fang-Quote
(Review-Bugs / (Review+Gerät)), Doc-vs-Code-Anteil, Modell-Mix.

| # | Datum | Modell | Tokens ges. (Msg/Tools) | Commits (Merges) | Tests (von→bis, Δ) | Version (von→bis) | Subagenten | Features / APs | Verifiziert | LOC (authored / getrackt) | Dateien | feat/fix | Review-Bugs | Gerät-Bugs | Notiz |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-06-18 | Opus 4.8 (1M) | n/a¹ | 0 (0) | 862→862 (0) | 1.0.0→1.0.0 | 0 | Doku-App-Look (Icon-Rail/Heatmap/Hero), AP-Übersicht+Gantt, TDD-Gate (11 Regeln), Ein-Befehl-Release (`run.sh docs-appimage`), AppRun Random-Port + isolierte Chromium-Instanz | Site gebaut · Docs-AppImage smoke-getestet (HTTP 200, Random-Port 50609) | ~219 / 2283+ −156² | 15 Repo + 3 Pattern + 3 Handoff | 0/0 | 1³ | 0 | Reine Doku/Tooling-Session, kein App-Code; uncommitted an nächste Session übergeben |
| 2 | 2026-06-19 | Opus 4.8 (1M) | n/a¹ | 5 (0) | 862→869 (+7)⁴ | 1.0.0→1.0.0 | 1 (Explore) | App-AppRun Random-Ports (FE+BE ephemeral) + isolierte Chromium; Docs-Nav-Mirror (Insights/Handoffs) + TDD-Regel R-ERKENNTNISSE; `run_mpp_docs.sh` PEP-668-gehärtet; VM-Install-Guide (Flask/React, 19 Abschnitte); 4 Produktionsreife-Fixes (gunicorn, ProxyFix, Readiness `/ready`, alembic-DATABASE_URL) | 9 neue Tests grün · gunicorn-Smoke-Test (`/health`+`/ready` 200) · alembic-Override funktional bewiesen · App-AppImage e2e (Random-Ports, Proxy 200) | ~990 / 9333+ −58⁵ | 9 Repo + 1 Pattern + 2 Handoff | 2/0 | 1⁶ | 0 | App-Code + Doku; 23 pre-existing Backend-Failures entdeckt (per git-stash als nicht-Regression bewiesen) |

**Fußnoten:**
1. Token-Zahlen aus `/context` nicht verfügbar (Tool-/Headless-Modus, kein `/context`-Zugriff) — bei nächster interaktiver Session nachtragen.
2. *authored* = neu geschriebener Text (`verify_docs.sh` ~120, `arbeitspakete.md` ~80, `ueberblick.md` ~55) ohne kopierte/generierte Blobs; *getrackt* = `git diff --shortstat` (enthält kopierte `extra.css` ~1980 Z. + Edits; `mermaid.min.js` 3 MB binär nicht gezählt).
3. TDD-Gate fing `R-NO-PLACEHOLDER` (ADAPT-Marker-Reste in `icon-rail.js`) **vor** „fertig" → rot→fix→grün. Fang-Quote dieser Session = 1/1 = 100 %.
4. +7 Backend-Tests via TDD (`test_app_factory.py` 1, `test_db_url.py` 3, `test_health.py` Readiness +3). **Achtung:** Voller `tests/unit+integration`-Lauf zeigte 23 **pre-existing** Failures (per `git stash` als Nicht-Regression bewiesen) — die „862 grün"-Baseline war bereits vor dieser Session stale.
5. *authored* ≈ VM-Guide 693 + Prod-Fixes ~90 + Mirror/Härtung 134 + AppRun 76; *getrackt* = Summe `git diff --shortstat` der 5 Commits (9333 dominiert vom Vorsession-Carry-Commit `0ed38136` inkl. binär `mermaid.min.js`).
6. TDD-Gate-Regel `R-ERKENNTNISSE` fing einen Pretty-URL-Pfad-Bug im neuen Mirror **vor** „fertig" → rot→fix→grün. Fang-Quote = 1/1 = 100 %.
