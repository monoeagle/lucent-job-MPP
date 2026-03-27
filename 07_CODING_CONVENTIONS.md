# Coding Conventions — Marketplace Portal (MPP)

---

## Python (Backend)

### Stil
- **Naming:** `snake_case` fuer Variablen, Funktionen, Module; `PascalCase` fuer Klassen
- **Formatting:** Black-kompatibel (Zeilenlaenge 100)
- **Type Hints:** Durchgaengig verwendet (`def login(self, username: str, password: str | None) -> dict:`)
- **Imports:** Standard-Bibliothek, Drittanbieter, eigene Module — jeweils durch Leerzeile getrennt

### Architektur-Muster
- **Repository-Pattern:** Datenbankzugriff nur ueber Repositories (`data/repositories/`)
- **Service-Layer:** Business-Logik in Services (`services/`)
- **Domain-Modelle:** Reine Datenklassen ohne Framework-Abhaengigkeiten (`domain/`)
- **Flask-Blueprints:** Ein Blueprint pro Feature-Modul (`api/v1/`)
- **Fehlerklassen:** Innere Klassen in Services (z.B. `AuthService.InvalidCredentialsError`)

### Error-Handling
- Eigene Error-Klassen in `app/core/errors.py` (ValidationError, NotFoundError, ForbiddenError, etc.)
- Globale Error-Handler wandeln Exceptions in JSON-Responses um
- Request-ID wird automatisch generiert und an Responses angehaengt

### Datei-Groesse
- Ziel: < 200 Zeilen pro Datei
- Bei Ueberschreitung: Aufteilen in logische Module

---

## TypeScript (Frontend)

### Stil
- **Naming:** `camelCase` fuer Variablen und Funktionen; `PascalCase` fuer Komponenten und Typen
- **Strict Mode:** Aktiviert (`"strict": true` in tsconfig.json)
- **Funktionale Komponenten:** Ausschliesslich React Function Components
- **Imports:** Keine Barrel-Pattern (direkte Imports)

### State Management
- **Server-State:** tanstack-query fuer alle API-Daten
- **Client-State:** zustand fuer Auth-Daten (minimaler lokaler State)
- **Keine Props-Drilling:** Hooks fuer Datenzugriff

### Komponenten-Struktur
- Eine Komponente pro Datei
- Hooks in eigene Dateien (`hooks/`)
- API-Aufrufe in API-Module (`api/`)
- Typen in `types/`

---

## Tests

### Backend (pytest)
- **Struktur:** `tests/unit/`, `tests/integration/`, `tests/e2e/`
- **Fixtures:** Gemeinsame Fixtures in `tests/conftest.py`
- **Namenskonvention:** `test_<feature>_<scenario>.py`
- **Datenbank:** Separate Test-Datenbank (`mpp_test`)
- **Isolation:** Jeder Test verwendet eine eigene Session mit Rollback
- **Aktueller Stand:** 594 Tests

### Frontend (vitest)
- **Struktur:** `frontend/tests/` mit Unterverzeichnissen analog zu `src/`
- **Testing Library:** `@testing-library/react` fuer Komponenten-Tests
- **Mocking:** API-Module werden gemockt (kein Backend-Zugriff)
- **Aktueller Stand:** 47 Tests

### TDD-Workflow
1. Test schreiben (red)
2. Minimale Implementierung (green)
3. Refactoring (refactor)
4. Commit

---

## Git

### Commit-Nachrichten
Conventional Commits Format:

```
<type>(<scope>): <beschreibung>
```

**Typen:**
- `feat` — Neues Feature
- `fix` — Bugfix
- `test` — Test-Aenderungen
- `chore` — Tooling, Config, Cleanup
- `refactor` — Code-Umstrukturierung
- `docs` — Dokumentation

**Scopes (optional):**
- `frontend` — Frontend-Aenderungen
- `(kein Scope)` — Backend-Aenderungen

### Branch-Strategie
- Feature-Branches: `feat/<feature-name>`
- Einzelentwickler-Workflow: Direktes Arbeiten auf Hauptbranch erlaubt

---

## Clean Architecture Dependency-Regeln

### Backend
```
app/api/v1/     →  app/services/     →  app/domain/     ←  app/data/
(Presentation)     (Use Cases)          (Entities)          (Repositories)
```

**Erlaubt:**
- `api/` → `services/`, `core/`
- `services/` → `domain/`, `data/repositories/`
- `data/` → `domain/`
- `core/` → ueberall

**Verboten:**
- `api/` → `data/` (nur ueber Services)
- `domain/` → `data/`, `services/`, `api/`
- `services/` → `api/`

### Frontend
```
pages/     →  hooks/     →  api/     ←  types/
(Views)       (Logic)       (Data)      (Domain)
```

---

## Allgemeine Regeln

- Keine Magic Numbers — Konstanten verwenden
- Keine `print()`-Statements — `logging` verwenden
- Keine `# TODO`-Kommentare ohne Ticket-Referenz
- Deutsche Fehlermeldungen fuer Endbenutzer, englische fuer technische Logs
- JSONB-Felder immer mit Default (`default=dict` oder `default=list`)
