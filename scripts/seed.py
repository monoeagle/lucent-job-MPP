#!/usr/bin/env python3
"""Seed script: populates the database with demo data."""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models import *  # noqa: F401,F403 — ensure all models registered
from app.data.repositories.template_repository import TemplateRepository
from app.data.repositories.order_repository import OrderRepository


# ---------------------------------------------------------------------------
# Shared parameters (used by both Windows and Linux VM templates)
# ---------------------------------------------------------------------------

WIZARD_STEPS = [
    {"group": "Netzwerk", "label": "Hostnamen- und Netzwerkkonfiguration"},
    {"group": "Platzierung", "label": "Platzierung"},
    {"group": "Betriebssystem", "label": "Betriebssystem"},
    {"group": "VM Sizing", "label": "VM Sizing"},
    {"group": "Datenspeicher", "label": "Datenspeicher"},
    {"group": "Server Informationen", "label": "Server Informationen"},
    {"group": "Softwaremanagement", "label": "Softwaremanagement"},
    {"group": "Backup", "label": "Backup"},
]

# Parameters shared by both templates (Netzwerk through Backup, excluding OS)
SHARED_PARAMS = [
    # ── Netzwerk ─────────────────────────────────────────────
    {
        "key": "system_type", "label": "Systemtyp", "type": "enum", "required": True,
        "tofu_variable_name": "system_type", "display_order": 10, "group": "Netzwerk",
        "constraints": {"options": [
            {"value": "db", "label": "Datenbank (db)", "enabled": True},
            {"value": "dc", "label": "Domain Controller (dc)", "enabled": True},
            {"value": "fp", "label": "Fileserver/Print (fp)", "enabled": True},
            {"value": "app", "label": "Applikationsserver (app)", "enabled": True},
            {"value": "web", "label": "Webserver (web)", "enabled": True},
        ]},
        "depends_on": [], "affects_options_of": ["ad_tier", "network_layer", "ad_assignment", "tshirt_size"],
    },
    {
        "key": "mandant", "label": "Mandant", "type": "enum", "required": True,
        "tofu_variable_name": "mandant", "display_order": 11, "group": "Netzwerk",
        "constraints": {"options": [
            {"value": "a1", "label": "Mandant A1", "enabled": True},
            {"value": "b1", "label": "Mandant B1", "enabled": True},
            {"value": "c1", "label": "Mandant C1", "enabled": True},
        ]},
        "depends_on": [], "affects_options_of": ["org_area", "security_area"],
    },
    {
        "key": "security_area", "label": "Sicherheitsbereich", "type": "enum", "required": True,
        "tofu_variable_name": "security_area", "display_order": 12, "group": "Netzwerk",
        "constraints": {"options": [
            {"value": "sec1", "label": "SecBereich1", "enabled": True,
             "metadata": {"mandants": ["a1", "b1", "c1"]}},
            {"value": "sec2", "label": "SecBereich2", "enabled": True,
             "metadata": {"mandants": ["a1", "b1"]}},
            {"value": "sec3", "label": "SecBereich3", "enabled": True,
             "metadata": {"mandants": ["a1"]}},
        ]},
        "depends_on": [], "affects_options_of": ["network_vlan", "vmware_cluster", "location"],
    },
    {
        "key": "org_area", "label": "Organisationsbereich", "type": "enum", "required": True,
        "tofu_variable_name": "org_area", "display_order": 13, "group": "Netzwerk",
        "constraints": {"options": [
            {"value": "ou1", "label": "OuBereich1", "enabled": True,
             "metadata": {"mandants": ["a1", "b1"]}},
            {"value": "ou2", "label": "OuBereich2", "enabled": True,
             "metadata": {"mandants": ["b1", "c1"]}},
        ]},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "location", "label": "Standort", "type": "enum", "required": True,
        "tofu_variable_name": "location", "display_order": 14, "group": "Netzwerk",
        "constraints": {"options": [
            {"value": "standort1", "label": "Standort1", "enabled": True,
             "metadata": {"security_areas": ["sec1", "sec2", "sec3"]}},
            {"value": "standort2", "label": "Standort2", "enabled": True,
             "metadata": {"security_areas": ["sec1", "sec2"]}},
        ]},
        "depends_on": [], "affects_options_of": ["dns_server"],
    },
    {
        "key": "dns_server", "label": "DNS Server", "type": "string", "required": True,
        "tofu_variable_name": "dns_server", "display_order": 15, "group": "Netzwerk",
        "description": "IP-Adresse des DNS-Servers",
        "constraints": {"pattern": "^[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}$"},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "lb_subnet", "label": "Loadbalancing-Subnetz", "type": "string", "required": False,
        "tofu_variable_name": "lb_subnet", "display_order": 16, "group": "Netzwerk",
        "description": "CIDR-Notation (z.B. 10.0.1.0/24) — nur fuer Web-/Appserver",
        "constraints": {},
        "depends_on": [
            {"parameter_key": "system_type", "operator": "in", "value": ["web", "app"], "effect": "visible"},
        ],
        "affects_options_of": [],
    },
    {
        "key": "ad_tier", "label": "Sicherheitsklasse (AD Tier)", "type": "enum", "required": True,
        "tofu_variable_name": "ad_tier", "display_order": 17, "group": "Netzwerk",
        "description": "Tier 0 nur fuer Domain Controller, Tier 2 nur fuer Web-/Appserver",
        "constraints": {"options": [
            {"value": "tier0", "label": "Tier 0 — Domain Controllers", "enabled": True,
             "metadata": {"allowed_system_types": ["dc"]}},
            {"value": "tier1", "label": "Tier 1 — Server", "enabled": True,
             "metadata": {"allowed_system_types": ["db", "dc", "fp", "app", "web"]}},
            {"value": "tier2", "label": "Tier 2 — Workstations/Web", "enabled": True,
             "metadata": {"allowed_system_types": ["web", "app"]}},
        ]},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "network_layer", "label": "Layer", "type": "enum", "required": True,
        "tofu_variable_name": "network_layer", "display_order": 18, "group": "Netzwerk",
        "constraints": {"options": [
            {"value": "frontend", "label": "Frontend", "enabled": True,
             "metadata": {"allowed_system_types": ["app", "web"]}},
            {"value": "backend", "label": "Backend", "enabled": True,
             "metadata": {"allowed_system_types": ["db", "dc", "fp", "app", "web"]}},
            {"value": "management", "label": "Management", "enabled": True,
             "metadata": {"allowed_system_types": ["db", "dc"]}},
        ]},
        "depends_on": [], "affects_options_of": ["network_vlan"],
    },
    {
        "key": "network_vlan", "label": "Netzwerk (VLAN)", "type": "enum", "required": True,
        "tofu_variable_name": "network_vlan", "display_order": 19, "group": "Netzwerk",
        "description": "Verfuegbare VLANs abhaengig von Sicherheitsbereich und Layer",
        "constraints": {"options": [
            {"value": "vlan100", "label": "VLAN 100 — Produktion (Sec1)", "enabled": True,
             "metadata": {"security_areas": ["sec1"]}},
            {"value": "vlan110", "label": "VLAN 110 — Produktion (Sec2)", "enabled": True,
             "metadata": {"security_areas": ["sec2"]}},
            {"value": "vlan200", "label": "VLAN 200 — Entwicklung (Sec1/Sec2)", "enabled": True,
             "metadata": {"security_areas": ["sec1", "sec2"]}},
            {"value": "vlan300", "label": "VLAN 300 — Management (Sec3)", "enabled": True,
             "metadata": {"security_areas": ["sec3"]}},
            {"value": "vlan400", "label": "VLAN 400 — DMZ (alle)", "enabled": True,
             "metadata": {"security_areas": ["sec1", "sec2", "sec3"]}},
        ]},
        "depends_on": [], "affects_options_of": [],
    },
    # ── Platzierung ──────────────────────────────────────────
    {
        "key": "ad_assignment", "label": "Zuordnung im AD", "type": "enum", "required": True,
        "tofu_variable_name": "ad_assignment", "display_order": 20, "group": "Platzierung",
        "constraints": {"options": [
            {"value": "app", "label": "APP", "enabled": True,
             "metadata": {"allowed_system_types": ["db", "dc", "fp", "app", "web"]}},
            {"value": "debug", "label": "Debug", "enabled": True,
             "metadata": {"allowed_system_types": ["app", "web"]}},
            {"value": "test", "label": "Test", "enabled": True,
             "metadata": {"allowed_system_types": ["db", "dc", "fp", "app", "web"]}},
            {"value": "prod", "label": "Produktion", "enabled": True,
             "metadata": {"allowed_system_types": ["db", "app", "web"]}},
        ]},
        "depends_on": [], "affects_options_of": ["patch_wave", "maintenance_window"],
    },
    {
        "key": "vmware_cluster", "label": "Zuordnung im VMware Cluster", "type": "enum", "required": True,
        "tofu_variable_name": "vmware_cluster", "display_order": 21, "group": "Platzierung",
        "description": "Dual Site nur fuer SecBereich1 und SecBereich2",
        "constraints": {"options": [
            {"value": "single-site", "label": "Single Site Cluster", "enabled": True,
             "metadata": {"security_areas": ["sec1", "sec2", "sec3"]}},
            {"value": "dual-site", "label": "Dual Site Cluster", "enabled": True,
             "metadata": {"security_areas": ["sec1", "sec2"]}},
        ]},
        "depends_on": [], "affects_options_of": [],
    },
    # ── VM Sizing ────────────────────────────────────────────
    {
        "key": "tshirt_size", "label": "T-Shirt Size", "type": "enum", "required": True,
        "tofu_variable_name": "tshirt_size", "display_order": 40, "group": "VM Sizing",
        "description": "Vorkonfigurierte Groesse — setzt CPU, RAM und OS-Disk automatisch",
        "constraints": {"options": [
            {"value": "xs", "label": "XS — 1 CPU, 2 GB RAM, 40 GB Disk", "enabled": True,
             "metadata": {"cpu_cores": 1, "ram_gb": 2, "os_disk_gb": 40,
                          "allowed_system_types": ["fp", "app", "web"]}},
            {"value": "s", "label": "S — 2 CPU, 4 GB RAM, 60 GB Disk", "enabled": True,
             "metadata": {"cpu_cores": 2, "ram_gb": 4, "os_disk_gb": 60,
                          "allowed_system_types": ["db", "fp", "app", "web"]}},
            {"value": "m", "label": "M — 4 CPU, 8 GB RAM, 80 GB Disk", "enabled": True,
             "metadata": {"cpu_cores": 4, "ram_gb": 8, "os_disk_gb": 80,
                          "allowed_system_types": ["db", "dc", "fp", "app", "web"]}},
            {"value": "l", "label": "L — 8 CPU, 16 GB RAM, 120 GB Disk", "enabled": True,
             "metadata": {"cpu_cores": 8, "ram_gb": 16, "os_disk_gb": 120,
                          "allowed_system_types": ["db", "dc", "fp", "app", "web"]}},
            {"value": "xl", "label": "XL — 16 CPU, 32 GB RAM, 200 GB Disk", "enabled": True,
             "metadata": {"cpu_cores": 16, "ram_gb": 32, "os_disk_gb": 200,
                          "allowed_system_types": ["db", "dc", "fp", "app", "web"]}},
        ]},
        "depends_on": [], "affects_options_of": ["cpu_cores", "ram_gb", "os_disk_gb"],
    },
    {
        "key": "cpu_cores", "label": "CPU Cores", "type": "integer", "required": True,
        "tofu_variable_name": "cpu_cores", "display_order": 41, "group": "VM Sizing",
        "description": "Wird durch T-Shirt Size vorbelegt, kann angepasst werden",
        "constraints": {"min": 1, "max": 64, "step": 1, "unit": "Kerne"},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "ram_gb", "label": "RAM", "type": "integer", "required": True,
        "tofu_variable_name": "ram_gb", "display_order": 42, "group": "VM Sizing",
        "constraints": {"min": 2, "max": 256, "step": 2, "unit": "GB"},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "os_disk_gb", "label": "Groesse OS Disk", "type": "integer", "required": True,
        "tofu_variable_name": "os_disk_gb", "display_order": 43, "group": "VM Sizing",
        "constraints": {"min": 40, "max": 500, "step": 10, "unit": "GB"},
        "depends_on": [], "affects_options_of": [],
    },
    # ── Datenspeicher ────────────────────────────────────────
    {
        "key": "extra_disk_1", "label": "Zusaetzliche Festplatte #1", "type": "integer", "required": False,
        "tofu_variable_name": "extra_disk_1", "display_order": 50, "group": "Datenspeicher",
        "description": "Groesse in GB (leer lassen wenn nicht benoetigt)",
        "constraints": {"min": 10, "max": 4000, "step": 10, "unit": "GB"},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "extra_disk_2", "label": "Zusaetzliche Festplatte #2", "type": "integer", "required": False,
        "tofu_variable_name": "extra_disk_2", "display_order": 51, "group": "Datenspeicher",
        "constraints": {"min": 10, "max": 4000, "step": 10, "unit": "GB"},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "extra_disk_3", "label": "Zusaetzliche Festplatte #3", "type": "integer", "required": False,
        "tofu_variable_name": "extra_disk_3", "display_order": 52, "group": "Datenspeicher",
        "constraints": {"min": 10, "max": 4000, "step": 10, "unit": "GB"},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "extra_disk_4", "label": "Zusaetzliche Festplatte #4", "type": "integer", "required": False,
        "tofu_variable_name": "extra_disk_4", "display_order": 53, "group": "Datenspeicher",
        "constraints": {"min": 10, "max": 4000, "step": 10, "unit": "GB"},
        "depends_on": [], "affects_options_of": [],
    },
    # ── Server Informationen ─────────────────────────────────
    {
        "key": "description_text", "label": "Funktionsbeschreibung", "type": "string", "required": True,
        "tofu_variable_name": "description_text", "display_order": 60, "group": "Server Informationen",
        "description": "Kurze Beschreibung des Verwendungszwecks",
        "constraints": {"min_length": 5, "max_length": 500},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "orderer_email", "label": "Systembesteller (E-Mail)", "type": "string", "required": True,
        "tofu_variable_name": "orderer_email", "display_order": 61, "group": "Server Informationen",
        "description": "E-Mail-Adresse des Bestellers",
        "constraints": {"pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "responsible_email", "label": "Systemverantwortlicher (E-Mail)", "type": "string", "required": True,
        "tofu_variable_name": "responsible_email", "display_order": 62, "group": "Server Informationen",
        "description": "E-Mail-Adresse des Systemverantwortlichen",
        "constraints": {"pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "contact_group_email", "label": "Kontaktgruppe (E-Mail)", "type": "string", "required": True,
        "tofu_variable_name": "contact_group_email", "display_order": 63, "group": "Server Informationen",
        "description": "E-Mail-Adresse der Kontaktgruppe",
        "constraints": {"pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "ticket_id", "label": "Ticket-ID", "type": "string", "required": False,
        "tofu_variable_name": "ticket_id", "display_order": 64, "group": "Server Informationen",
        "description": "Referenz-Ticket (z.B. JIRA-12345)",
        "constraints": {"max_length": 50},
        "depends_on": [], "affects_options_of": [],
    },
    # ── Softwaremanagement ───────────────────────────────────
    {
        "key": "maintenance_window", "label": "Wartungszeitfenster", "type": "enum", "required": True,
        "tofu_variable_name": "maintenance_window", "display_order": 70, "group": "Softwaremanagement",
        "description": "Zeitfenster fuer automatische Updates",
        "constraints": {"options": [
            {"value": "wed-02-06", "label": "Mittwoch 02:00-06:00", "enabled": True,
             "metadata": {"ad_assignments": ["app", "debug", "test"]}},
            {"value": "sat-02-06", "label": "Samstag 02:00-06:00", "enabled": True,
             "metadata": {"ad_assignments": ["app", "debug", "test"]}},
            {"value": "sun-02-06", "label": "Sonntag 02:00-06:00", "enabled": True,
             "metadata": {"ad_assignments": ["prod"]}},
        ]},
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "patch_wave", "label": "Patchwelle", "type": "enum", "required": True,
        "tofu_variable_name": "patch_wave", "display_order": 71, "group": "Softwaremanagement",
        "description": "Zuordnung zur Patch-Rollout-Welle",
        "constraints": {"options": [
            {"value": "wave1", "label": "Welle 1 — Test/Dev (frueh)", "enabled": True,
             "metadata": {"ad_assignments": ["debug", "test", "app"]}},
            {"value": "wave2", "label": "Welle 2 — Staging (mittel)", "enabled": True,
             "metadata": {"ad_assignments": ["test", "app"]}},
            {"value": "wave3", "label": "Welle 3 — Produktion (spaet)", "enabled": True,
             "metadata": {"ad_assignments": ["prod"]}},
        ]},
        "depends_on": [], "affects_options_of": [],
    },
    # ── Backup ───────────────────────────────────────────────
    {
        "key": "backup_enabled", "label": "Backupstatus", "type": "boolean", "required": False,
        "tofu_variable_name": "backup_enabled", "display_order": 80, "group": "Backup",
        "description": "Soll die VM regelmaessig gesichert werden?",
        "constraints": {},
        "default_value": False,
        "depends_on": [], "affects_options_of": [],
    },
    {
        "key": "site_replication", "label": "Standortreplikation", "type": "boolean", "required": False,
        "tofu_variable_name": "site_replication", "display_order": 81, "group": "Backup",
        "description": "Backup an zweiten Standort replizieren?",
        "constraints": {},
        "default_value": False,
        "depends_on": [
            {"parameter_key": "backup_enabled", "operator": "eq", "value": True, "effect": "visible"},
        ],
        "affects_options_of": [],
    },
]


# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

def _build_vm_template(slug, display_name, description, os_params, cost):
    """Build a VM template with shared params + OS-specific params."""
    params = copy.deepcopy(SHARED_PARAMS)
    # Insert OS params at position after Platzierung (display_order 30)
    for p in os_params:
        params.append(p)
    # Sort by display_order
    params.sort(key=lambda p: p["display_order"])
    return {
        "slug": slug,
        "version": "1.0.0",
        "type": "vm",
        "display_name": display_name,
        "description": description,
        "category": "Compute",
        "icon_identifier": f"server-{slug.split('-')[1]}",
        "tofu_module_source": f"git::https://gitlab.internal/tofu-modules/{slug}.git?ref=v1.0.0",
        "estimated_cost_eur_per_month": cost,
        "approval_always_required": True,
        "metadata": {
            "preferred_view": "wizard",
            "wizard_config": {"steps": copy.deepcopy(WIZARD_STEPS)},
        },
        "parameters": params,
    }


WINDOWS_VM = _build_vm_template(
    slug="vm-windows",
    display_name="Windows Virtual Machine",
    description="Windows Server VM mit vollstaendiger Netzwerk-, Platzierungs- und Sizing-Konfiguration.",
    cost=150.00,
    os_params=[
        {
            "key": "os_template", "label": "Template", "type": "enum", "required": True,
            "tofu_variable_name": "os_template", "display_order": 30, "group": "Betriebssystem",
            "constraints": {"options": [
                {"value": "win2016", "label": "Windows Server 2016", "enabled": True},
                {"value": "win2019", "label": "Windows Server 2019", "enabled": True},
                {"value": "win2022", "label": "Windows Server 2022", "enabled": True},
            ]},
            "depends_on": [], "affects_options_of": [],
        },
    ],
)

LINUX_VM = _build_vm_template(
    slug="vm-linux",
    display_name="Linux Virtual Machine",
    description="Linux Server VM mit vollstaendiger Netzwerk-, Platzierungs- und Sizing-Konfiguration.",
    cost=85.00,
    os_params=[
        {
            "key": "os_template", "label": "Template", "type": "enum", "required": True,
            "tofu_variable_name": "os_template", "display_order": 30, "group": "Betriebssystem",
            "constraints": {"options": [
                {"value": "ubuntu2204", "label": "Ubuntu 22.04 LTS", "enabled": True},
                {"value": "ubuntu2404", "label": "Ubuntu 24.04 LTS", "enabled": True},
                {"value": "rhel9", "label": "RHEL 9", "enabled": True},
                {"value": "alma10", "label": "AlmaLinux 10", "enabled": True},
                {"value": "debian12", "label": "Debian 12", "enabled": True},
            ]},
            "depends_on": [], "affects_options_of": [],
        },
    ],
)


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed():
    db_url = os.environ.get("DATABASE_URL", "postgresql://mpp:mpp@localhost:5432/mpp_dev")
    engine = get_engine(db_url)

    Base.metadata.create_all(engine)

    Session = get_session_factory(engine)
    session = Session()

    template_repo = TemplateRepository(session)
    order_repo = OrderRepository(session)

    # Check if data already exists
    existing = template_repo.list_templates()
    if existing["total"] > 0:
        print(f"Database already has {existing['total']} templates. Skipping seed.")
        print("To re-seed, drop and recreate the database first.")
        return

    # Create templates
    templates = []
    for tmpl_data in [WINDOWS_VM, LINUX_VM]:
        t = template_repo.create(tmpl_data)
        templates.append(t)
        print(f"Created template: {t.slug} v{t.version} ({len(tmpl_data['parameters'])} params, ID: {t.id})")

    # Create a demo order
    order = order_repo.create_order(
        requester_id="test-requester",
        title="Demo Web-Cluster",
        business_reason="Initiales Setup fuer Q2 Web-Projekt",
    )
    print(f"\nCreated order: {order.order_number} (ID: {order.id})")

    # Add items to order
    item1 = order_repo.add_item(
        order_id=order.id,
        template_slug="vm-linux",
        template_version="1.0.0",
        display_name="Linux Virtual Machine",
        parameters={
            "system_type": "web", "mandant": "a1", "security_area": "sec1",
            "org_area": "ou1", "location": "standort1", "dns_server": "10.1.0.53",
            "ad_tier": "tier1", "network_layer": "frontend", "network_vlan": "vlan100",
            "ad_assignment": "prod", "vmware_cluster": "dual-site",
            "os_template": "ubuntu2404",
            "tshirt_size": "m", "cpu_cores": 4, "ram_gb": 8, "os_disk_gb": 80,
            "description_text": "Webserver fuer Q2 Projekt",
            "orderer_email": "admin@example.com",
            "responsible_email": "ops@example.com",
            "contact_group_email": "team@example.com",
            "maintenance_window": "sun-02-06", "patch_wave": "wave3",
            "backup_enabled": True, "site_replication": False,
        },
    )
    print(f"  Added item: {item1.display_name} (Position {item1.position})")

    session.close()
    print(f"\nSeed complete! {len(templates)} templates + 1 order with 1 item.")
    print("\nYou can now:")
    print("  1. Start backend:  AUTH_MODE=stub CMDB_MODE=stub flask run --port 5000")
    print("  2. Start frontend: cd frontend && npm run dev")
    print("  3. Open http://localhost:3000")
    print('  4. Login as \'test-requester\' (no password needed)')


if __name__ == "__main__":
    seed()
