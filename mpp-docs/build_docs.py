#!/usr/bin/env python3
"""
build_docs.py – MPP Dokumentation generieren

Verwendet Zensical (MkDocs Material Wrapper).

Verwendung:
  python3 build_docs.py              # HTML bauen
  python3 build_docs.py --serve      # Live-Server
  python3 build_docs.py --serve --port 5078
  python3 build_docs.py --check      # Nur prüfen
  python3 build_docs.py --ci         # CI-Modus (strict)
"""

import subprocess
import sys
import argparse
import shutil
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent
DOCS_DIR    = BASE_DIR / "docs"
SITE_DIR    = BASE_DIR / "site"
CONFIG_FILE = BASE_DIR / "zensical.toml"


# ──────────────────────────────────────────────────────────────────────────────

def run(cmd, cwd=BASE_DIR):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nFehler (exit {e.returncode})")
        sys.exit(e.returncode)


def check_zensical(auto_install=False):
    try:
        subprocess.run(["zensical", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Zensical nicht gefunden.")
        if auto_install:
            print("Installiere Zensical ...")
            run([sys.executable, "-m", "pip", "install", "zensical"])
        else:
            print("Installieren mit:  pip install zensical")
            sys.exit(1)


def check_structure(strict=False):
    print("\nPruefe Dokumentations-Struktur ...")
    errors = 0

    if not DOCS_DIR.is_dir():
        print("  docs/ Verzeichnis fehlt!")
        errors += 1

    if not CONFIG_FILE.exists():
        print("  zensical.toml fehlt!")
        errors += 1

    md_files = list(DOCS_DIR.rglob("*.md")) if DOCS_DIR.exists() else []
    print(f"  {len(md_files)} Markdown-Dateien gefunden")

    if not any(f.name == "index.md" for f in md_files):
        print("  Kein index.md gefunden")
        if strict:
            errors += 1

    if errors > 0:
        print(f"\n{errors} Fehler gefunden")
        if strict:
            sys.exit(1)
    else:
        print("  Struktur OK")


def build():
    print("\nBaue Dokumentation mit Zensical ...")
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    run(["zensical", "build", "--clean"])
    index = SITE_DIR / "index.html"
    if index.exists():
        print(f"\nFertig! Ausgabe: {SITE_DIR}")
        print(f"   Oeffnen: file://{index}")
    else:
        print("Build fehlgeschlagen")
        sys.exit(1)


def serve(port: int = 5078):
    print(f"\nStarte Live-Server auf Port {port} ...")
    print(f"   Oeffnen: http://127.0.0.1:{port}")
    print("   Beenden: Ctrl+C\n")
    try:
        subprocess.run(
            ["zensical", "serve", "--dev-addr", f"127.0.0.1:{port}"],
            cwd=BASE_DIR
        )
    except KeyboardInterrupt:
        print("\nServer beendet.")


# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MPP Docs Builder")
    parser.add_argument("--serve",   action="store_true", help="Live-Server starten")
    parser.add_argument("--port",    type=int, default=5078, help="Port fuer Live-Server")
    parser.add_argument("--check",   action="store_true", help="Nur Struktur pruefen")
    parser.add_argument("--ci",      action="store_true", help="CI-Modus (strict)")
    parser.add_argument("--install", action="store_true", help="Zensical automatisch installieren")
    args = parser.parse_args()

    check_zensical(auto_install=args.install)
    strict = args.ci

    if args.check:
        check_structure(strict=strict)
    elif args.serve:
        check_structure(strict=strict)
        serve(port=args.port)
    else:
        check_structure(strict=strict)
        build()


if __name__ == "__main__":
    main()
