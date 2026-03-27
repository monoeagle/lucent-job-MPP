#!/usr/bin/env python3
"""Seed script: populates the database with demo data."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models import *  # noqa: F401,F403 — ensure all models registered
from app.data.repositories.template_repository import TemplateRepository
from app.data.repositories.order_repository import OrderRepository


# ---------------------------------------------------------------------------
# Template data
# ---------------------------------------------------------------------------

LINUX_VM = {
    "slug": "vm-linux",
    "version": "1.0.0",
    "type": "vm",
    "display_name": "Linux Virtual Machine",
    "description": "Standard-Linux-VM mit konfigurierbaren CPU-, RAM- und Storage-Werten.",
    "category": "Compute",
    "icon_identifier": "server-linux",
    "tofu_module_source": "git::https://gitlab.internal/tofu-modules/vm-linux.git?ref=v1.0.0",
    "estimated_cost_eur_per_month": 85.00,
    "parameters": [
        {
            "key": "cpu_cores", "label": "CPU-Kerne", "type": "integer", "required": True,
            "tofu_variable_name": "cpu_cores", "display_order": 1, "group": "Compute",
            "description": "Anzahl der virtuellen CPU-Kerne",
            "constraints": {"min": 1, "max": 64, "step": 1, "unit": "Kerne"},
            "depends_on": [], "affects_options_of": [],
        },
        {
            "key": "ram_gb", "label": "Arbeitsspeicher", "type": "integer", "required": True,
            "tofu_variable_name": "ram_gb", "display_order": 2, "group": "Compute",
            "description": "RAM in GB",
            "constraints": {"min": 2, "max": 256, "step": 2, "unit": "GB"},
            "depends_on": [], "affects_options_of": [],
        },
        {
            "key": "os_type", "label": "Betriebssystem", "type": "enum", "required": True,
            "tofu_variable_name": "os_type", "display_order": 3, "group": "System",
            "description": None,
            "constraints": {"options": [
                {"value": "ubuntu-22.04", "label": "Ubuntu 22.04 LTS", "enabled": True},
                {"value": "ubuntu-24.04", "label": "Ubuntu 24.04 LTS", "enabled": True},
                {"value": "rhel-9", "label": "Red Hat Enterprise Linux 9", "enabled": True},
                {"value": "debian-12", "label": "Debian 12", "enabled": True},
            ]},
            "depends_on": [], "affects_options_of": ["disk_type"],
        },
        {
            "key": "disk_size_gb", "label": "Festplatte", "type": "integer", "required": True,
            "tofu_variable_name": "disk_size_gb", "display_order": 4, "group": "Storage",
            "description": "Festplattengröße in GB",
            "constraints": {"min": 20, "max": 2000, "step": 10, "unit": "GB"},
            "depends_on": [], "affects_options_of": [],
        },
        {
            "key": "enable_backup", "label": "Backup aktivieren", "type": "boolean", "required": False,
            "tofu_variable_name": "enable_backup", "display_order": 5, "group": "Sicherheit",
            "description": "Tägliches Backup der VM aktivieren",
            "constraints": {},
            "default_value": False,
            "depends_on": [], "affects_options_of": [],
        },
    ],
    "cross_parameter_rules": [
        {
            "rule_id": "cpu-ram-ratio",
            "description": "RAM muss mindestens 2 GB pro CPU-Kern betragen",
            "parameter_keys": ["cpu_cores", "ram_gb"],
            "expression": "ram_gb >= cpu_cores * 2",
            "error_message": "RAM muss mindestens 2 GB pro CPU-Kern betragen.",
        },
    ],
}

WINDOWS_VM = {
    "slug": "vm-windows",
    "version": "1.0.0",
    "type": "vm",
    "display_name": "Windows Virtual Machine",
    "description": "Windows Server VM für Unternehmensanwendungen.",
    "category": "Compute",
    "icon_identifier": "server-windows",
    "tofu_module_source": "git::https://gitlab.internal/tofu-modules/vm-windows.git?ref=v1.0.0",
    "estimated_cost_eur_per_month": 150.00,
    "approval_always_required": True,
    "parameters": [
        {
            "key": "cpu_cores", "label": "CPU-Kerne", "type": "integer", "required": True,
            "tofu_variable_name": "cpu_cores", "display_order": 1, "group": "Compute",
            "constraints": {"min": 2, "max": 32, "step": 2, "unit": "Kerne"},
            "depends_on": [], "affects_options_of": [],
        },
        {
            "key": "ram_gb", "label": "Arbeitsspeicher", "type": "integer", "required": True,
            "tofu_variable_name": "ram_gb", "display_order": 2, "group": "Compute",
            "constraints": {"min": 4, "max": 128, "step": 4, "unit": "GB"},
            "depends_on": [], "affects_options_of": [],
        },
        {
            "key": "os_version", "label": "Windows Version", "type": "enum", "required": True,
            "tofu_variable_name": "os_version", "display_order": 3, "group": "System",
            "constraints": {"options": [
                {"value": "win-server-2022", "label": "Windows Server 2022", "enabled": True},
                {"value": "win-server-2019", "label": "Windows Server 2019", "enabled": True},
            ]},
            "depends_on": [], "affects_options_of": [],
        },
        {
            "key": "disk_size_gb", "label": "Festplatte", "type": "integer", "required": True,
            "tofu_variable_name": "disk_size_gb", "display_order": 4, "group": "Storage",
            "constraints": {"min": 50, "max": 2000, "step": 50, "unit": "GB"},
            "depends_on": [], "affects_options_of": [],
        },
    ],
}

POSTGRES_DB = {
    "slug": "db-postgres",
    "version": "1.0.0",
    "type": "database",
    "display_name": "PostgreSQL Datenbank",
    "description": "Managed PostgreSQL-Instanz mit konfigurierbarer Version und Speicher.",
    "category": "Database",
    "icon_identifier": "database",
    "tofu_module_source": "git::https://gitlab.internal/tofu-modules/db-postgres.git?ref=v1.0.0",
    "estimated_cost_eur_per_month": 45.00,
    "parameters": [
        {
            "key": "pg_version", "label": "PostgreSQL Version", "type": "enum", "required": True,
            "tofu_variable_name": "pg_version", "display_order": 1, "group": "Datenbank",
            "constraints": {"options": [
                {"value": "14", "label": "PostgreSQL 14", "enabled": True},
                {"value": "15", "label": "PostgreSQL 15", "enabled": True},
                {"value": "16", "label": "PostgreSQL 16", "enabled": True},
            ]},
            "depends_on": [], "affects_options_of": [],
        },
        {
            "key": "storage_gb", "label": "Speicher", "type": "integer", "required": True,
            "tofu_variable_name": "storage_gb", "display_order": 2, "group": "Datenbank",
            "description": "Datenbankspeicher in GB",
            "constraints": {"min": 10, "max": 1000, "step": 10, "unit": "GB"},
            "depends_on": [], "affects_options_of": [],
        },
        {
            "key": "max_connections", "label": "Max. Verbindungen", "type": "integer", "required": False,
            "tofu_variable_name": "max_connections", "display_order": 3, "group": "Datenbank",
            "description": "Maximale Anzahl gleichzeitiger Verbindungen",
            "constraints": {"min": 10, "max": 500, "step": 10},
            "default_value": 100,
            "depends_on": [], "affects_options_of": [],
        },
        {
            "key": "enable_ssl", "label": "SSL aktivieren", "type": "boolean", "required": False,
            "tofu_variable_name": "enable_ssl", "display_order": 4, "group": "Sicherheit",
            "description": "SSL-Verschlüsselung für Verbindungen aktivieren",
            "constraints": {},
            "default_value": True,
            "depends_on": [], "affects_options_of": [],
        },
    ],
}


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
    for tmpl_data in [LINUX_VM, WINDOWS_VM, POSTGRES_DB]:
        t = template_repo.create(tmpl_data)
        templates.append(t)
        print(f"Created template: {t.slug} v{t.version} (ID: {t.id})")

    # Create a demo order
    order = order_repo.create_order(
        requester_id="test-requester",
        title="Demo Web-Cluster",
        business_reason="Initiales Setup für Q2 Web-Projekt",
    )
    print(f"\nCreated order: {order.order_number} (ID: {order.id})")

    # Add items to order
    item1 = order_repo.add_item(
        order_id=order.id,
        template_slug="vm-linux",
        template_version="1.0.0",
        display_name="Linux Virtual Machine",
        parameters={
            "cpu_cores": 4, "ram_gb": 16, "os_type": "ubuntu-22.04",
            "disk_size_gb": 100, "enable_backup": True,
        },
    )
    print(f"  Added item: {item1.display_name} (Position {item1.position})")

    item2 = order_repo.add_item(
        order_id=order.id,
        template_slug="db-postgres",
        template_version="1.0.0",
        display_name="PostgreSQL Datenbank",
        parameters={
            "pg_version": "16", "storage_gb": 50,
            "max_connections": 100, "enable_ssl": True,
        },
    )
    print(f"  Added item: {item2.display_name} (Position {item2.position})")

    session.close()
    print(f"\nSeed complete! {len(templates)} templates + 1 order with 2 items.")
    print("\nYou can now:")
    print("  1. Start backend:  AUTH_MODE=stub CMDB_MODE=stub flask run --port 5000")
    print("  2. Start frontend: cd frontend && npm run dev")
    print("  3. Open http://localhost:3000")
    print('  4. Login as \'test-requester\' (no password needed)')


if __name__ == "__main__":
    seed()
