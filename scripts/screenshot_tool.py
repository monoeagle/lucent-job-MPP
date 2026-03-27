#!/usr/bin/env python3
"""
screenshot_tool.py — MPP UI Screenshot-Tool
Erzeugt Screenshots aller Seiten als WebP, pro Benutzerrolle in eigenen Unterordnern.

Ordnerstruktur: screenshots/v{version}/{user}/{viewport}/

Verwendung:
    python3 scripts/screenshot_tool.py                     # Alle User, Desktop
    python3 scripts/screenshot_tool.py --quick             # Nur Hauptseiten
    python3 scripts/screenshot_tool.py --user test-admin   # Nur ein User
    python3 scripts/screenshot_tool.py --mobile            # Desktop + Mobile
    python3 scripts/screenshot_tool.py --browser chromium  # Chromium
    python3 scripts/screenshot_tool.py --png               # PNG statt WebP

Voraussetzung:
    pip install playwright pillow
    playwright install firefox
    Frontend + Backend muessen laufen!
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

# Benutzer mit ihren Rollen und sichtbaren Seiten
# ── Page Actions ──────────────────────────────────────────────
# Aktionen die nach dem Laden einer Seite ausgefuehrt werden,
# bevor der Screenshot gemacht wird.

def _action_fill_windows_form(page):
    """Windows-VM-Formular mit Beispieldaten ausfuellen."""
    _fill_service_form(page, {
        'system_type': 'app',
        'mandant': 'a1',
        'security_area': 'sec1',
        'org_area': 'ou1',
        'location': 'standort1',
        'ad_tier': 'tier1',
        'network_layer': 'backend',
        'network_vlan': 'vlan100',
        'ad_assignment': 'prod',
        'vmware_cluster': 'single-site',
        'os_template': 'win2022',
        'tshirt_size': 'm',
    })
    page.locator('#param-dns_server').fill('10.0.1.53')
    page.wait_for_timeout(500)


def _action_fill_linux_form(page):
    """Linux-VM-Formular mit Beispieldaten ausfuellen."""
    _fill_service_form(page, {
        'system_type': 'db',
        'mandant': 'b1',
        'security_area': 'sec1',
        'org_area': 'ou2',
        'location': 'standort1',
        'ad_tier': 'tier1',
        'network_layer': 'backend',
        'network_vlan': 'vlan100',
        'ad_assignment': 'app',
        'vmware_cluster': 'dual-site',
        'os_template': 'ubuntu2404',
        'tshirt_size': 'l',
    })
    page.locator('#param-dns_server').fill('10.0.2.53')
    page.wait_for_timeout(500)


def _fill_service_form(page, selects):
    """Enum-Felder (select) in der FormView setzen — mit Locator-API fuer korrekte Events."""
    for key, value in selects.items():
        loc = page.locator(f'#param-{key}')
        if loc.count() > 0:
            loc.select_option(value=value)
            page.wait_for_timeout(200)


def _action_expand_reviews(page):
    """Erste 2 Review-Eintraege aufklappen."""
    rows = page.query_selector_all('[aria-expanded]')
    for row in rows[:2]:
        row.click()
        page.wait_for_timeout(300)


# ── Seiten-Definitionen ──────────────────────────────────────
# Tuple: (name, path, needs_auth, action_fn|None)

USERS = {
    'test-requester': {
        'label': 'Besteller',
        'pages': [
            ('01_login',              '/login',              False, None),
            ('02_dashboard',          '/dashboard',          True,  None),
            ('03_shop',               '/shop',               True,  None),
            ('04_bestellungen',       '/workspace',          True,  None),
            ('05_bestellungen_meine', '/workspace?tab=mine', True,  None),
            ('06_notifications',      '/notifications',      True,  None),
            ('10_shop_windows',       '/shop/vm-windows/request?view=form', True, _action_fill_windows_form),
            ('11_shop_linux',         '/shop/vm-linux/request?view=form',   True, _action_fill_linux_form),
        ],
    },
    'test-approver': {
        'label': 'Genehmiger',
        'pages': [
            ('01_login',              '/login',              False, None),
            ('02_dashboard',          '/dashboard',          True,  None),
            ('03_shop',               '/shop',               True,  None),
            ('04_bestellungen',       '/workspace',          True,  None),
            ('06_notifications',      '/notifications',      True,  None),
            ('07_reviews',            '/reviews',            True,  _action_expand_reviews),
        ],
    },
    'test-admin': {
        'label': 'Administrator',
        'pages': [
            ('01_login',              '/login',              False, None),
            ('02_dashboard',          '/dashboard',          True,  None),
            ('03_shop',               '/shop',               True,  None),
            ('04_bestellungen',       '/workspace',          True,  None),
            ('06_notifications',      '/notifications',      True,  None),
            ('07_reviews',            '/reviews',            True,  _action_expand_reviews),
            ('08_admin_dashboard',    '/admin',              True,  None),
        ],
    },
    'test-multi': {
        'label': 'Alle Rollen',
        'pages': [
            ('01_login',              '/login',              False, None),
            ('02_dashboard',          '/dashboard',          True,  None),
            ('03_shop',               '/shop',               True,  None),
            ('04_bestellungen',       '/workspace',          True,  None),
            ('05_bestellungen_meine', '/workspace?tab=mine', True,  None),
            ('06_notifications',      '/notifications',      True,  None),
            ('07_reviews',            '/reviews',            True,  _action_expand_reviews),
            ('08_admin_dashboard',    '/admin',              True,  None),
            ('10_shop_windows',       '/shop/vm-windows/request?view=form', True, _action_fill_windows_form),
            ('11_shop_linux',         '/shop/vm-linux/request?view=form',   True, _action_fill_linux_form),
        ],
    },
    'test-superadmin': {
        'label': 'Super Admin',
        'pages': [
            ('01_login',              '/login',              False, None),
            ('02_dashboard',          '/dashboard',          True,  None),
            ('03_shop',               '/shop',               True,  None),
            ('04_bestellungen',       '/workspace',          True,  None),
            ('06_notifications',      '/notifications',      True,  None),
            ('07_reviews',            '/reviews',            True,  _action_expand_reviews),
            ('08_admin_dashboard',    '/admin',              True,  None),
            ('09_admin_rules',        '/admin/rules',        True,  None),
            ('10_admin_audit',        '/admin/audit-log',    True,  None),
        ],
    },
}

QUICK_PATHS = {'/login', '/dashboard', '/shop', '/workspace'}


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
                filepath = os.path.join(output_dir, f'{name}.png')
                page.screenshot(path=filepath, full_page=full_page)
        else:
            page.screenshot(path=filepath, full_page=full_page)

        return filepath
    except Exception as e:
        print(f"      x {name}: {e}")
        return None


def _check_backend(base_url):
    """Prueft ob das Backend erreichbar ist."""
    try:
        import urllib.request
        req = urllib.request.Request(f'{base_url}/api/v1/health')
        resp = urllib.request.urlopen(req, timeout=3)
        return resp.status == 200
    except Exception:
        return False


def _login(page, base_url, username):
    """Login per API-Call, Token direkt in localStorage setzen (kein UI-Formular)."""
    try:
        import urllib.request
        import json as _json

        # 1) Token vom Backend holen
        req = urllib.request.Request(
            f'http://127.0.0.1:5000/api/v1/auth/login',
            data=_json.dumps({'username': username}).encode(),
            headers={'Content-Type': 'application/json'},
        )
        resp = urllib.request.urlopen(req, timeout=5)
        data = _json.loads(resp.read())
        token = data['token']
        user_obj = data['user']

        # 2) Seite laden damit localStorage auf dem richtigen Origin verfuegbar ist
        page.goto(f'{base_url}/login', wait_until='commit', timeout=15000)

        # 3) Token + User in localStorage setzen (gleiche Keys wie authStore.ts)
        page.evaluate("""([token, userJson]) => {
            localStorage.setItem('auth-token', token);
            localStorage.setItem('auth-user', userJson);
        }""", [token, _json.dumps(user_obj)])

        # 4) Zu Dashboard navigieren — restoreSession() liest localStorage beim App-Mount
        page.goto(f'{base_url}/dashboard', wait_until='networkidle', timeout=15000)
        page.wait_for_timeout(1500)

        if '/login' in page.url:
            print(f"      x Token gesetzt aber Redirect zu /login")
            return False

        return True
    except Exception as e:
        print(f"      x Login als {username} fehlgeschlagen: {e}")
        return False


def take_screenshots(port=3000, viewports_list=None, version='1.0.0',
                     browser_name='firefox', quick=False, webp=True,
                     user_filter=None):

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright fehlt: pip install playwright && playwright install firefox")
        return {}

    if not viewports_list:
        viewports_list = ['desktop']

    base_url = f'http://127.0.0.1:{port}'
    results = {}

    users_to_run = {k: v for k, v in USERS.items()
                    if not user_filter or k == user_filter}

    total_pages = sum(len(u['pages']) for u in users_to_run.values())

    # Backend-Check (Login braucht API)
    backend_url = f'http://127.0.0.1:5000'
    if not _check_backend(backend_url):
        print(f"\n!!! Backend nicht erreichbar auf {backend_url} !!!")
        print(f"    Login wird fehlschlagen. Bitte Backend starten (Flask :5000).")
        print(f"    Abbruch.")
        return {}

    print(f"\n=== MPP Screenshot-Tool v{version} ===")
    print(f"   Frontend:  {base_url}")
    print(f"   Backend:   {backend_url} (OK)")
    print(f"   Benutzer:  {len(users_to_run)} ({', '.join(users_to_run.keys())})")
    print(f"   Viewports: {', '.join(viewports_list)}")
    print(f"   Format:    {'WebP' if webp else 'PNG'}")
    print(f"   Quick:     {'ja' if quick else 'nein'}")
    print(f"   Seiten:    ~{total_pages}")
    print()

    with sync_playwright() as p:
        browser_type = getattr(p, browser_name, p.firefox)
        browser = browser_type.launch(headless=True)

        for username, user_config in users_to_run.items():
            label = user_config['label']
            pages = user_config['pages']

            if quick:
                pages = [(n, path, auth, act) for n, path, auth, act in pages
                         if path.split('?')[0] in QUICK_PATHS]

            print(f"  ── {username} ({label}) ──")

            for vp_name in viewports_list:
                vp = VIEWPORTS.get(vp_name, VIEWPORTS['desktop'])
                is_mob = (vp_name == 'mobile')

                # screenshots/v1.0.0/test-requester/desktop/
                out = os.path.join(BASE_DIR, 'screenshots', f'v{version}',
                                   username, vp_name)
                os.makedirs(out, exist_ok=True)

                ctx = browser.new_context(
                    viewport=vp,
                    device_scale_factor=2 if is_mob else 1,
                )
                pg = ctx.new_page()

                print(f"    {vp_name} ({vp['width']}x{vp['height']})")

                # Login-Seite (ohne Auth)
                pg.goto(f'{base_url}/login', wait_until='networkidle', timeout=15000)
                pg.wait_for_timeout(500)
                r = _shot(pg, out, '01_login', full_page=False, webp=webp)
                if r:
                    results[os.path.basename(r)] = r
                    print(f"      + 01_login")

                # Login als dieser User
                if not _login(pg, base_url, username):
                    print(f"      x Abbruch: Login fehlgeschlagen")
                    ctx.close()
                    continue
                print(f"      + Login OK")

                # Alle Seiten mit Auth
                for name, path, needs_auth, action in pages:
                    if not needs_auth:
                        continue
                    try:
                        pg.goto(f'{base_url}{path}', wait_until='networkidle',
                                timeout=15000)
                        pg.wait_for_timeout(800)

                        # Page-Action ausfuehren (Formulare fuellen, Reviews aufklappen, etc.)
                        if action:
                            try:
                                action(pg)
                                pg.wait_for_timeout(500)
                            except Exception as ae:
                                print(f"      ! {name}: Action-Warnung: {ae}")

                        r = _shot(pg, out, name, full_page=True, webp=webp)
                        if r:
                            results[os.path.basename(r)] = r
                            print(f"      + {name}")
                    except Exception as e:
                        print(f"      x {name}: {e}")

                ctx.close()

            print()

        browser.close()

    # Manifest pro Version
    out_base = os.path.join(BASE_DIR, 'screenshots', f'v{version}')
    manifest = {
        'version':     version,
        'timestamp':   time.strftime('%Y-%m-%d %H:%M:%S'),
        'screenshots': len(results),
        'users':       list(users_to_run.keys()),
        'viewports':   viewports_list,
        'browser':     browser_name,
        'format':      'webp' if webp else 'png',
        'files':       sorted(results.keys()),
    }
    os.makedirs(out_base, exist_ok=True)
    with open(os.path.join(out_base, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"=== {len(results)} Screenshots -> screenshots/v{version}/ ===")
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MPP Screenshot-Tool')
    parser.add_argument('--port',     type=int, default=3000)
    parser.add_argument('--browser',  choices=['firefox', 'chromium', 'webkit'],
                        default='firefox')
    parser.add_argument('--mobile',   action='store_true',
                        help='Auch Mobile-Viewport')
    parser.add_argument('--quick',    action='store_true',
                        help='Nur Hauptseiten')
    parser.add_argument('--png',      action='store_true',
                        help='PNG statt WebP')
    parser.add_argument('--user',     type=str, default=None,
                        choices=list(USERS.keys()),
                        help='Nur ein bestimmter Benutzer')
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
        user_filter=args.user,
    )
