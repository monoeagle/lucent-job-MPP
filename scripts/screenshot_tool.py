#!/usr/bin/env python3
"""
screenshot_tool.py — MPP UI Screenshot-Tool
Erzeugt Screenshots aller Seiten als WebP.

Verwendet Playwright (headless Firefox/Chromium).
Loggt sich automatisch als test-multi (alle Rollen) ein.

Verwendung:
    python3 scripts/screenshot_tool.py                     # Desktop, alle Seiten
    python3 scripts/screenshot_tool.py --quick             # Nur Hauptseiten
    python3 scripts/screenshot_tool.py --browser chromium  # Chromium statt Firefox
    python3 scripts/screenshot_tool.py --port 3000         # Anderer Port
    python3 scripts/screenshot_tool.py --mobile            # Auch Mobile-Viewport

Voraussetzung:
    pip install playwright pillow
    playwright install firefox
    Frontend muss auf dem angegebenen Port laufen!
"""

import os
import sys
import time
import json
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VIEWPORTS = {
    'desktop': {'width': 1920, 'height': 1080},
    'mobile':  {'width': 390,  'height': 844},
}

# Alle MPP-Seiten die screenshotted werden
MPP_PAGES = [
    ('01_login',             '/login',                     False),
    ('02_dashboard',         '/dashboard',                 True),
    ('03_shop',              '/shop',                      True),
    ('04_bestellungen',      '/workspace',                 True),
    ('05_bestellungen_meine','/workspace?tab=mine',        True),
    ('06_notifications',     '/notifications',             True),
    ('07_reviews',           '/reviews',                   True),
    ('08_admin_dashboard',   '/admin',                     True),
    ('09_admin_rules',       '/admin/rules',               True),
    ('10_admin_audit',       '/admin/audit-log',           True),
]

# Quick-Modus: nur Hauptseiten
MPP_PAGES_QUICK = [
    ('01_login',             '/login',                     False),
    ('02_dashboard',         '/dashboard',                 True),
    ('03_shop',              '/shop',                      True),
    ('04_bestellungen',      '/workspace',                 True),
]

# Zusaetzliche Seiten die Interaktion brauchen
MPP_INTERACTIVE = [
    # (name, path, needs_auth, action_description)
    ('20_shop_windows_bestellen', '/shop/vm-windows/request', True),
    ('21_shop_linux_bestellen',   '/shop/vm-linux/request',   True),
]


def _shot(page, output_dir, name, full_page=True, delay=500, webp=True):
    """Screenshot als WebP speichern."""
    try:
        page.wait_for_timeout(delay)
        ext = 'webp' if webp else 'png'
        filepath = os.path.join(output_dir, f'{name}.{ext}')

        if webp:
            try:
                from PIL import Image
                import io as _io
                buf = page.screenshot(full_page=full_page)
                img = Image.open(_io.BytesIO(buf))
                img.save(filepath, 'WEBP', quality=85)
            except ImportError:
                # Fallback: PNG wenn Pillow fehlt
                filepath = os.path.join(output_dir, f'{name}.png')
                page.screenshot(path=filepath, full_page=full_page)
        else:
            page.screenshot(path=filepath, full_page=full_page)

        return filepath
    except Exception as e:
        print(f"    x {name}: {e}")
        return None


def _login(page, base_url, username='test-multi'):
    """Login ueber die API und Token im localStorage setzen."""
    try:
        import urllib.request
        import json as _json

        # Login via API
        req = urllib.request.Request(
            f'{base_url}/api/v1/auth/login',
            data=_json.dumps({'username': username}).encode(),
            headers={'Content-Type': 'application/json'},
        )
        resp = urllib.request.urlopen(req, timeout=5)
        data = _json.loads(resp.read())
        token = data['token']
        user = data['user']

        # Token + User in localStorage setzen (wie zustand persist)
        page.goto(f'{base_url}/login', wait_until='networkidle', timeout=10000)
        page.wait_for_timeout(500)

        # zustand auth store schreibt in localStorage
        page.evaluate(f"""
            const state = {{
                state: {{
                    token: '{token}',
                    user: {_json.dumps(user)},
                    isAuthenticated: true
                }},
                version: 0
            }};
            localStorage.setItem('auth-storage', JSON.stringify(state));
        """)
        page.wait_for_timeout(200)
        return True
    except Exception as e:
        print(f"    x Login fehlgeschlagen: {e}")
        return False


def take_screenshots(port=3000, viewports_list=None, version='1.0.0',
                     browser_name='firefox', quick=False, webp=True):

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright fehlt: pip install playwright && playwright install firefox")
        return {}

    if not viewports_list:
        viewports_list = ['desktop']

    base_url = f'http://127.0.0.1:{port}'
    results = {}

    pages = MPP_PAGES_QUICK if quick else MPP_PAGES
    out_base = os.path.join(BASE_DIR, 'screenshots', f'v{version}')

    print(f"\n=== MPP Screenshot-Tool v{version} ===")
    print(f"   Server:    {base_url}")
    print(f"   Viewports: {', '.join(viewports_list)}")
    print(f"   Format:    {'WebP' if webp else 'PNG'}")
    print(f"   Quick:     {'ja' if quick else 'nein'}")
    print(f"   Seiten:    {len(pages)}")
    print()

    with sync_playwright() as p:
        browser_type = getattr(p, browser_name, p.firefox)
        browser = browser_type.launch(headless=True)

        for vp_name in viewports_list:
            vp = VIEWPORTS.get(vp_name, VIEWPORTS['desktop'])
            is_mob = (vp_name == 'mobile')

            out = os.path.join(out_base, vp_name)
            os.makedirs(out, exist_ok=True)

            ctx = browser.new_context(
                viewport=vp,
                device_scale_factor=2 if is_mob else 1,
            )
            pg = ctx.new_page()

            print(f"  -- {vp_name} ({vp['width']}x{vp['height']}) --")

            # Login-Seite zuerst (ohne Auth)
            login_page = pages[0]
            pg.goto(f'{base_url}{login_page[1]}', wait_until='networkidle', timeout=15000)
            pg.wait_for_timeout(500)
            r = _shot(pg, out, login_page[0], full_page=False, webp=webp)
            if r:
                results[os.path.basename(r)] = r
                print(f"    + {login_page[0]}")

            # Login
            if not _login(pg, base_url):
                print("    x Abbruch: Login fehlgeschlagen")
                ctx.close()
                continue
            print("    + Login erfolgreich (test-multi)")

            # Alle Seiten mit Auth
            for name, path, needs_auth in pages[1:]:
                if not needs_auth:
                    continue
                try:
                    pg.goto(f'{base_url}{path}', wait_until='networkidle', timeout=15000)
                    pg.wait_for_timeout(800)
                    r = _shot(pg, out, name, full_page=True, webp=webp)
                    if r:
                        results[os.path.basename(r)] = r
                        print(f"    + {name}")
                except Exception as e:
                    print(f"    x {name}: {e}")

            # Interaktive Seiten (nicht im Quick-Modus)
            if not quick:
                print("    -- Interaktiv --")
                for name, path, needs_auth in MPP_INTERACTIVE:
                    try:
                        pg.goto(f'{base_url}{path}', wait_until='networkidle', timeout=15000)
                        pg.wait_for_timeout(1000)
                        r = _shot(pg, out, name, full_page=True, webp=webp)
                        if r:
                            results[os.path.basename(r)] = r
                            print(f"    + {name}")
                    except Exception as e:
                        print(f"    x {name}: {e}")

            ctx.close()
            print()

        browser.close()

    # Manifest
    manifest = {
        'version':     version,
        'timestamp':   time.strftime('%Y-%m-%d %H:%M:%S'),
        'screenshots': len(results),
        'viewports':   viewports_list,
        'browser':     browser_name,
        'format':      'webp' if webp else 'png',
        'files':       sorted(results.keys()),
    }
    os.makedirs(out_base, exist_ok=True)
    with open(os.path.join(out_base, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n=== {len(results)} Screenshots -> screenshots/v{version}/ ===")
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MPP Screenshot-Tool')
    parser.add_argument('--port',     type=int, default=3000)
    parser.add_argument('--browser',  choices=['firefox', 'chromium', 'webkit'], default='firefox')
    parser.add_argument('--mobile',   action='store_true', help='Auch Mobile-Viewport')
    parser.add_argument('--quick',    action='store_true', help='Nur Hauptseiten')
    parser.add_argument('--png',      action='store_true', help='PNG statt WebP')
    parser.add_argument('--version',  type=str, default='1.0.0')
    args = parser.parse_args()

    viewports = ['desktop']
    if args.mobile:
        viewports.append('mobile')

    take_screenshots(
        port=args.port,
        viewports_list=viewports,
        version=args.version,
        browser_name=args.browser,
        quick=args.quick,
        webp=not args.png,
    )
