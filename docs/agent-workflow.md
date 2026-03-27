# Agent Workflow — MPP Projekt

## Agenten-Uebersicht

| Agent | Wann | Haeufigkeit | Modell |
|-------|------|-------------|--------|
| **produkt-owner** | Feature-Definition | 1x pro Feature | opus |
| **backend-architect** | System-Design | 1x pro Phase | opus |
| **clean-architect** | Architektur-Review | 1x pro Phase-Audit | opus |
| **python-flask-dev** | Backend-Implementierung | N pro Phase (1 pro Task) | sonnet/haiku |
| **qa-test-writer** | Unabhaengige Tests | 1x nach Implementierung | sonnet |
| **senior-debugger** | Bug-Analyse | Ad hoc bei Fehlern | opus |
| **security-engineer** | Security-Review | 1x pro Phase-Audit | opus |
| **auditor** | Production-Readiness | 1x pro Release | opus |
| **devops-engineer** | CI/CD, Docker | 1x bei Setup, dann ad hoc | sonnet |

---

## Workflow: Feature-Entwicklung

```
┌─────────────────────────────────────────────┐
│ Phase 1: Feature-Definition                  │
│                                              │
│   Product Owner Agent                        │
│   → User Stories, Acceptance Criteria        │
│   → Scope-Abgrenzung                        │
│                                              │
│   Ergebnis: Spec-Dokument                   │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ Phase 2: Design                              │
│                                              │
│   Backend Architect Agent                    │
│   → API-Design, Datenmodell, Datenfluss     │
│                                              │
│   Clean Architect Agent (optional)           │
│   → Review des Designs auf Architektur-Regeln│
│                                              │
│   Ergebnis: Implementation Plan              │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ Phase 3: Implementierung (pro Task)          │
│                                              │
│   Python Flask Dev / Frontend Dev            │
│   → TDD: Test → Implement → Verify          │
│                                              │
│   Spec-Review (nach jedem Task)              │
│   → Stimmt Code mit Spec ueberein?           │
│                                              │
│   Quality-Review (nach jedem Task)           │
│   → Code-Qualitaet, Patterns, Naming        │
│                                              │
│   Ergebnis: Committed Code + Tests           │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ Phase 4: Phase-Audit (alle 3-5 Features)     │
│                                              │
│   ┌─────────────────┐                       │
│   │ Security Eng.   │ ──┐                   │
│   └─────────────────┘   │                   │
│   ┌─────────────────┐   ├→ Konsolidierung   │
│   │ Clean Architect │ ──┤   der Findings    │
│   └─────────────────┘   │                   │
│   ┌─────────────────┐   │                   │
│   │ Auditor         │ ──┘                   │
│   └─────────────────┘                       │
│                                              │
│   3 unabhaengige Reviews → Vergleich         │
│   → Priorisierte Finding-Liste               │
│   → Fixes durch Implementer                  │
│                                              │
│   Ergebnis: Audit-Report + Fixes             │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ Phase 5: Deployment (bei Release)            │
│                                              │
│   DevOps Engineer Agent                      │
│   → CI/CD Check, Docker, Deployment          │
│                                              │
│   Ergebnis: Deployment-Ready                 │
└─────────────────────────────────────────────┘
```

---

## Workflow: Bug-Fix

```
Bug gemeldet
     │
     ├──→ Senior Debugger Agent
     │    → Root-Cause-Analyse
     │    → Minimaler Fix-Vorschlag
     │
     ├──→ Security Engineer Agent (parallel)
     │    → Ist es ein Security-Issue?
     │    → Gibt es aehnliche Stellen?
     │
     ▼
Ergebnisse kombinieren
     │
     ▼
Python Flask Dev Agent
     → Fix implementieren (TDD)
     → Tests fuer Regression
```

---

## Workflow: 3-fach Parallel-Audit

### Wann einsetzen?
- Nach Abschluss einer Phase (3-5 Features)
- Vor einem Release
- Nach groesseren Refactorings
- Bei Security-Concerns

### Ablauf

```
Code-Stand festlegen (git SHA)
          │
          ├──→ Security Engineer (parallel)
          │    Fokus: OWASP, Auth, Input, Secrets
          │    Ergebnis: Security-Findings
          │
          ├──→ Clean Architect (parallel)
          │    Fokus: Layering, Dependencies, File Size
          │    Ergebnis: Architektur-Findings
          │
          └──→ Auditor (parallel)
               Fokus: Test Coverage, Code Quality, Production Readiness
               Ergebnis: Quality-Findings

          ▼ (alle 3 fertig)

Konsolidierung:
  1. Findings nach Severity sortieren
  2. Duplikate zusammenfuehren (3 Agenten finden oft dasselbe)
  3. Uebereinstimmung = hohes Vertrauen
  4. Nur 1 Agent findet es = nochmal pruefen
  5. Priorisierte Fix-Liste erstellen

          ▼

Fixes durch Implementer:
  → CRITICAL + HIGH zuerst
  → Re-Review durch betroffenen Agent
```

### Warum 3 unabhaengige Reviews?

| Vorteil | Erklaerung |
|---------|-----------|
| **Verschiedene Perspektiven** | Security sieht Angriffsvektoren, Architect sieht Strukturprobleme, Auditor sieht Luecken |
| **Unabhaengigkeit** | Kein Agent beeinflusst den anderen → weniger Groupthink |
| **Uebereinstimmung = Vertrauen** | Wenn 3/3 dasselbe finden → definitiv fixen. Wenn 1/3 → diskutieren |
| **Vollstaendigkeit** | Verschiedene Checklisten fangen verschiedene Fehlerklassen |

### Wann NICHT 3-fach?

- Kleine Bug-Fixes → nur Senior Debugger
- Triviale UI-Aenderungen → nur 1 Quality Review
- Config-Aenderungen → nur DevOps Review

---

## Agent-Einsatz pro Projekt-Phase

| Projekt-Phase | Agenten | Anzahl Einsaetze |
|---------------|---------|-------------------|
| Feature-Spec | Product Owner | 1 |
| Design | Backend Architect + Clean Architect | 2 |
| Implementierung (10 Tasks) | Flask Dev (10) + Spec Review (10) + Quality Review (10) | 30 |
| Phase-Audit | Security + Clean Arch + Auditor | 3 (parallel) |
| Bug-Fix | Senior Debugger + Security (optional) | 1-2 |
| Release | Auditor + DevOps | 2 |
| **Gesamt pro Phase** | | **~38-40** |
