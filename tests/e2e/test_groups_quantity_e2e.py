# tests/e2e/test_groups_quantity_e2e.py
"""
E2E test: Full flow for groups + quantity + per-instance parameters.

1. Register template with per_instance params (hostname=auto, custom_tag=true, cpu=false)
2. Register DB template (no per_instance)
3. Create order
4. Create group "Web-Cluster"
5. Add item to group with quantity=3, instance_parameters for custom_tag
6. Add standalone DB item (no group, quantity=1)
7. Validate → all valid
8. Submit → order submitted
9. Export → 4 tofu blocks (3 VMs + 1 DB), each VM has unique instance params
10. Verify group structure in GET order response
"""
import pytest
from tests.e2e.conftest import auth


CLUSTER_VM = {
    "slug": "vm-cluster",
    "version": "1.0.0",
    "type": "vm",
    "display_name": "Cluster VM",
    "category": "Compute",
    "tofu_module_source": "git::https://gitlab.internal/tofu/vm-cluster.git",
    "parameters": [
        {
            "key": "cpu_cores", "label": "CPU", "type": "integer",
            "required": True, "tofu_variable_name": "cpu_cores",
            "display_order": 1, "constraints": {"min": 1, "max": 64},
        },
        {
            "key": "hostname", "label": "Hostname", "type": "string",
            "required": True, "tofu_variable_name": "hostname",
            "display_order": 2, "per_instance": "auto",
        },
        {
            "key": "custom_tag", "label": "Tag", "type": "string",
            "required": True, "tofu_variable_name": "custom_tag",
            "display_order": 3, "per_instance": True,
        },
    ],
}

SIMPLE_DB = {
    "slug": "db-simple",
    "version": "1.0.0",
    "type": "database",
    "display_name": "Simple DB",
    "category": "Database",
    "tofu_module_source": "git::https://gitlab.internal/tofu/db-simple.git",
    "parameters": [
        {
            "key": "storage_gb", "label": "Storage", "type": "integer",
            "required": True, "tofu_variable_name": "storage_gb",
            "display_order": 1, "constraints": {"min": 10, "max": 1000},
        },
    ],
}


class TestGroupsQuantityE2E:
    def test_full_groups_quantity_per_instance_flow(
        self, client, admin_token, requester_token,
    ):
        h_admin = auth(admin_token)
        h_req = auth(requester_token)

        # ── 1. Register templates ────────────────────────────────
        resp = client.post("/api/v1/admin/catalog/templates", json=CLUSTER_VM, headers=h_admin)
        assert resp.status_code == 201, f"Register cluster VM failed: {resp.get_json()}"

        resp = client.post("/api/v1/admin/catalog/templates", json=SIMPLE_DB, headers=h_admin)
        assert resp.status_code == 201, f"Register simple DB failed: {resp.get_json()}"

        # ── 2. Create order ──────────────────────────────────────
        resp = client.post("/api/v1/orders", headers=h_req, json={
            "title": "Web-Stack Bestellung",
            "business_reason": "Neues Web-Projekt",
        })
        assert resp.status_code == 201
        order_id = resp.get_json()["id"]

        # ── 3. Create group "Web-Cluster" ────────────────────────
        resp = client.post(f"/api/v1/orders/{order_id}/groups", headers=h_req, json={
            "name": "Web-Cluster",
            "description": "Frontend VMs",
        })
        assert resp.status_code == 201
        group_id = resp.get_json()["group"]["id"]

        # ── 4. Add VM item with quantity=3 + instance_parameters ─
        resp = client.post(f"/api/v1/orders/{order_id}/items", headers=h_req, json={
            "template_slug": "vm-cluster",
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 8},
            "quantity": 3,
            "instance_parameters": [
                {"custom_tag": "web-01"},
                {"custom_tag": "web-02"},
                {"custom_tag": "web-03"},
            ],
        })
        assert resp.status_code == 201
        vm_item_id = resp.get_json()["item"]["id"]

        # Assign VM item to group
        resp = client.patch(f"/api/v1/orders/{order_id}/items/{vm_item_id}", headers=h_req, json={
            "group_id": group_id,
        })
        assert resp.status_code == 200
        assert resp.get_json()["item"]["group_id"] == group_id

        # ── 5. Add standalone DB item (no group, quantity=1) ─────
        resp = client.post(f"/api/v1/orders/{order_id}/items", headers=h_req, json={
            "template_slug": "db-simple",
            "template_version": "1.0.0",
            "parameters": {"storage_gb": 100},
        })
        assert resp.status_code == 201
        db_item_id = resp.get_json()["item"]["id"]

        # ── 6. Validate → all valid ─────────────────────────────
        resp = client.post(f"/api/v1/orders/{order_id}/validate", headers=h_req)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["all_valid"] is True, f"Validation failed: {data}"

        # ── 7. Submit → order submitted ──────────────────────────
        resp = client.post(f"/api/v1/orders/{order_id}/submit", headers=h_req)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "submitted"

        # ── 8. Export → 4 tofu blocks ────────────────────────────
        resp = client.get(f"/api/v1/orders/{order_id}/export/tofu", headers=h_req)
        assert resp.status_code == 200
        export = resp.get_json()
        assert len(export["items"]) == 4, (
            f"Expected 4 export blocks (3 VMs + 1 DB), got {len(export['items'])}"
        )

        # 3 VM blocks with unique custom_tags
        vm_blocks = [i for i in export["items"] if i["template_slug"] == "vm-cluster"]
        assert len(vm_blocks) == 3
        tags = sorted([b["variables"]["custom_tag"] for b in vm_blocks])
        assert tags == ["web-01", "web-02", "web-03"]
        for b in vm_blocks:
            assert b["variables"]["cpu_cores"] == 8
            assert b["module_source"] == "git::https://gitlab.internal/tofu/vm-cluster.git"

        # 1 DB block
        db_blocks = [i for i in export["items"] if i["template_slug"] == "db-simple"]
        assert len(db_blocks) == 1
        assert db_blocks[0]["variables"]["storage_gb"] == 100

        # ── 9. Verify group structure in GET order ───────────────
        resp = client.get(f"/api/v1/orders/{order_id}", headers=h_req)
        assert resp.status_code == 200
        order_data = resp.get_json()

        # Groups
        assert len(order_data["groups"]) == 1
        group = order_data["groups"][0]
        assert group["name"] == "Web-Cluster"
        assert len(group["items"]) == 1
        assert group["items"][0]["id"] == vm_item_id
        assert group["items"][0]["quantity"] == 3

        # Ungrouped items
        assert len(order_data["ungrouped_items"]) == 1
        assert order_data["ungrouped_items"][0]["id"] == db_item_id
