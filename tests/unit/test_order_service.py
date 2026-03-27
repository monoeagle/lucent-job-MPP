# tests/unit/test_order_service.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.order_service import OrderService
from app.domain.order import OrderStatus, ItemValidationState


def _make_order(order_id="ord-1", requester_id="user-1", status="draft",
                title="My Order", business_reason=None, items=None):
    order = MagicMock()
    order.id = order_id
    order.requester_id = requester_id
    order.status = status
    order.title = title
    order.business_reason = business_reason
    order.items = items or []
    return order


def _make_item(item_id="item-1", order_id="ord-1", template_slug="vm-basic",
               template_version="1.0.0", parameters=None, validation_state="unchecked",
               quantity=1, instance_parameters=None):
    item = MagicMock()
    item.id = item_id
    item.order_id = order_id
    item.template_slug = template_slug
    item.template_version = template_version
    item.parameters = parameters or {"cpu": 4}
    item.validation_state = validation_state
    item.validation_errors = []
    item.quantity = quantity
    item.instance_parameters = instance_parameters or []
    return item


def _make_template(slug="vm-basic", version="1.0.0", status="active",
                   display_name="Basic VM", parameters=None,
                   cross_parameter_rules=None, tofu_module_source="registry/vm-basic"):
    tpl = MagicMock()
    tpl.slug = slug
    tpl.version = version
    tpl.status = status
    tpl.display_name = display_name
    tpl.parameters = parameters or [
        {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
         "tofu_variable_name": "vm_cpu_count", "display_order": 1,
         "constraints": {"min": 1, "max": 64}, "depends_on": []},
    ]
    tpl.cross_parameter_rules = cross_parameter_rules or []
    tpl.tofu_module_source = tofu_module_source
    return tpl


class TestCreateOrder:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_create_order_success(self):
        expected = _make_order()
        self.order_repo.create_order.return_value = expected

        result = self.service.create_order("user-1", "My Order")
        assert result["order"] == expected
        self.order_repo.create_order.assert_called_once_with(
            "user-1", "My Order", None, None,
        )

    def test_create_order_with_optional_fields(self):
        expected = _make_order(business_reason="Need VMs")
        self.order_repo.create_order.return_value = expected

        result = self.service.create_order(
            "user-1", "My Order", business_reason="Need VMs", desired_date="2026-04-01",
        )
        self.order_repo.create_order.assert_called_once_with(
            "user-1", "My Order", "Need VMs", "2026-04-01",
        )

    def test_create_order_title_too_short(self):
        with pytest.raises(ValueError, match="title"):
            self.service.create_order("user-1", "ab")

    def test_create_order_title_too_long(self):
        with pytest.raises(ValueError, match="title"):
            self.service.create_order("user-1", "x" * 101)

    def test_create_order_title_whitespace_only(self):
        with pytest.raises(ValueError, match="title"):
            self.service.create_order("user-1", "   ")


class TestAddItem:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_add_item_success(self):
        order = _make_order()
        self.order_repo.get_by_id.return_value = order
        template = _make_template()
        self.template_repo.get_by_slug_and_version.return_value = template
        expected_item = _make_item()
        self.order_repo.add_item.return_value = expected_item

        result = self.service.add_item("ord-1", "user-1", "vm-basic", "1.0.0", {"cpu": 4})
        assert result["item"] == expected_item
        assert result.get("warning") is None
        self.order_repo.add_item.assert_called_once_with(
            "ord-1", "vm-basic", "1.0.0", "Basic VM", {"cpu": 4},
            quantity=1, instance_parameters=[],
        )

    def test_add_item_order_not_found(self):
        self.order_repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="not found"):
            self.service.add_item("ord-1", "user-1", "vm-basic", "1.0.0", {})

    def test_add_item_wrong_requester(self):
        order = _make_order(requester_id="other-user")
        self.order_repo.get_by_id.return_value = order
        with pytest.raises(PermissionError, match="permission"):
            self.service.add_item("ord-1", "user-1", "vm-basic", "1.0.0", {})

    def test_add_item_order_not_draft(self):
        order = _make_order(status="submitted")
        self.order_repo.get_by_id.return_value = order
        with pytest.raises(ValueError, match="draft"):
            self.service.add_item("ord-1", "user-1", "vm-basic", "1.0.0", {})

    def test_add_item_template_not_found(self):
        order = _make_order()
        self.order_repo.get_by_id.return_value = order
        self.template_repo.get_by_slug_and_version.return_value = None
        with pytest.raises(ValueError, match="template"):
            self.service.add_item("ord-1", "user-1", "vm-basic", "1.0.0", {})

    def test_add_item_template_disabled(self):
        order = _make_order()
        self.order_repo.get_by_id.return_value = order
        template = _make_template(status="disabled")
        self.template_repo.get_by_slug_and_version.return_value = template
        with pytest.raises(ValueError, match="disabled"):
            self.service.add_item("ord-1", "user-1", "vm-basic", "1.0.0", {})

    def test_add_item_template_deprecated_returns_warning(self):
        order = _make_order()
        self.order_repo.get_by_id.return_value = order
        template = _make_template(status="deprecated")
        self.template_repo.get_by_slug_and_version.return_value = template
        expected_item = _make_item()
        self.order_repo.add_item.return_value = expected_item

        result = self.service.add_item("ord-1", "user-1", "vm-basic", "1.0.0", {"cpu": 4})
        assert result["item"] == expected_item
        assert "deprecated" in result["warning"].lower()


class TestUpdateItem:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_update_item_success(self):
        item = _make_item()
        order = _make_order(items=[item])
        self.order_repo.get_by_id.return_value = order
        self.order_repo.get_item_by_id.return_value = item
        updated_item = _make_item(parameters={"cpu": 8})
        self.order_repo.update_item_parameters.return_value = updated_item

        result = self.service.update_item("ord-1", "item-1", "user-1", {"cpu": 8})
        assert result["item"] == updated_item

    def test_update_item_resets_validated_order_to_draft(self):
        item = _make_item()
        order = _make_order(status="validated", items=[item])
        self.order_repo.get_by_id.return_value = order
        self.order_repo.get_item_by_id.return_value = item
        self.order_repo.update_item_parameters.return_value = item

        self.service.update_item("ord-1", "item-1", "user-1", {"cpu": 8})
        self.order_repo.update_order_status.assert_called_once_with("ord-1", OrderStatus.DRAFT)

    def test_update_item_order_not_draft_or_validated(self):
        order = _make_order(status="submitted")
        self.order_repo.get_by_id.return_value = order
        with pytest.raises(ValueError, match="draft"):
            self.service.update_item("ord-1", "item-1", "user-1", {"cpu": 8})


class TestRemoveItem:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_remove_item_success(self):
        item = _make_item()
        order = _make_order(items=[item])
        self.order_repo.get_by_id.return_value = order
        self.order_repo.get_item_by_id.return_value = item

        self.service.remove_item("ord-1", "item-1", "user-1")
        self.order_repo.remove_item.assert_called_once_with("item-1")

    def test_remove_item_order_not_draft(self):
        order = _make_order(status="submitted")
        self.order_repo.get_by_id.return_value = order
        with pytest.raises(ValueError, match="draft"):
            self.service.remove_item("ord-1", "item-1", "user-1")


class TestValidateOrder:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_validate_all_valid(self):
        item = _make_item()
        order = _make_order(items=[item])
        self.order_repo.get_by_id.return_value = order
        template = _make_template()
        self.template_repo.get_by_slug_and_version.return_value = template
        self.catalog_service.validate_parameters.return_value = []

        result = self.service.validate_order("ord-1", "user-1")
        assert result["status"] == OrderStatus.VALIDATED
        assert result["items"][0]["validation_state"] == ItemValidationState.VALID
        self.order_repo.update_order_status.assert_called_once_with("ord-1", OrderStatus.VALIDATED)

    def test_validate_with_violations_stays_draft(self):
        item = _make_item()
        order = _make_order(items=[item])
        self.order_repo.get_by_id.return_value = order
        template = _make_template()
        self.template_repo.get_by_slug_and_version.return_value = template
        self.catalog_service.validate_parameters.return_value = [
            {"parameter_key": "cpu", "rule": "required", "message": "CPU required"}
        ]

        result = self.service.validate_order("ord-1", "user-1")
        assert result["status"] == OrderStatus.DRAFT
        assert result["items"][0]["validation_state"] == ItemValidationState.INVALID
        self.order_repo.update_order_status.assert_not_called()

    def test_validate_no_items(self):
        order = _make_order(items=[])
        self.order_repo.get_by_id.return_value = order
        with pytest.raises(ValueError, match="items"):
            self.service.validate_order("ord-1", "user-1")

    def test_validate_order_already_validated(self):
        item = _make_item()
        order = _make_order(status="validated", items=[item])
        self.order_repo.get_by_id.return_value = order
        template = _make_template()
        self.template_repo.get_by_slug_and_version.return_value = template
        self.catalog_service.validate_parameters.return_value = []

        result = self.service.validate_order("ord-1", "user-1")
        assert result["status"] == OrderStatus.VALIDATED

    def test_validate_order_not_draft_or_validated(self):
        order = _make_order(status="submitted")
        self.order_repo.get_by_id.return_value = order
        with pytest.raises(ValueError, match="draft"):
            self.service.validate_order("ord-1", "user-1")


class TestSubmitOrder:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_submit_success(self):
        order = _make_order(status="validated", business_reason="We need VMs")
        self.order_repo.get_by_id.return_value = order
        submitted = _make_order(status="submitted")
        self.order_repo.update_order_status.return_value = submitted

        result = self.service.submit_order("ord-1", "user-1")
        assert result["order"] == submitted
        self.order_repo.update_order_status.assert_called_once_with("ord-1", OrderStatus.SUBMITTED)

    def test_submit_not_validated(self):
        order = _make_order(status="draft")
        self.order_repo.get_by_id.return_value = order
        with pytest.raises(ValueError, match="validated"):
            self.service.submit_order("ord-1", "user-1")

    def test_submit_no_business_reason(self):
        order = _make_order(status="validated", business_reason=None)
        self.order_repo.get_by_id.return_value = order
        with pytest.raises(ValueError, match="business_reason"):
            self.service.submit_order("ord-1", "user-1")

    def test_submit_empty_business_reason(self):
        order = _make_order(status="validated", business_reason="   ")
        self.order_repo.get_by_id.return_value = order
        with pytest.raises(ValueError, match="business_reason"):
            self.service.submit_order("ord-1", "user-1")


class TestExportTofu:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_export_basic(self):
        item = _make_item(parameters={"cpu": 4, "ram": 16})
        order = _make_order(status="validated", items=[item])
        self.order_repo.get_by_id.return_value = order
        template = _make_template(parameters=[
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "vm_cpu_count", "display_order": 1,
             "constraints": {}, "depends_on": []},
            {"key": "ram", "label": "RAM", "type": "integer", "required": True,
             "tofu_variable_name": "vm_ram_gb", "display_order": 2,
             "constraints": {}, "depends_on": []},
        ])
        self.template_repo.get_by_slug_and_version.return_value = template

        result = self.service.export_tofu("ord-1", "user-1")
        assert len(result["items"]) == 1
        exported = result["items"][0]
        assert exported["module_source"] == "registry/vm-basic"
        assert exported["variables"]["vm_cpu_count"] == 4
        assert exported["variables"]["vm_ram_gb"] == 16

    def test_export_excludes_inactive_depends_on_params(self):
        item = _make_item(parameters={"os": None, "disk_type": "ssd"})
        order = _make_order(status="validated", items=[item])
        self.order_repo.get_by_id.return_value = order
        template = _make_template(parameters=[
            {"key": "os", "label": "OS", "type": "enum", "required": False,
             "tofu_variable_name": "vm_os", "display_order": 1,
             "constraints": {}, "depends_on": []},
            {"key": "disk_type", "label": "Disk", "type": "enum", "required": False,
             "tofu_variable_name": "vm_disk_type", "display_order": 2,
             "constraints": {},
             "depends_on": [{"parameter_key": "os", "operator": "neq", "value": None, "effect": "visible"}]},
        ])
        self.template_repo.get_by_slug_and_version.return_value = template
        self.catalog_service.resolve_dependency_state.return_value = {
            "is_visible": False, "is_required": False, "is_disabled": False,
        }

        result = self.service.export_tofu("ord-1", "user-1")
        variables = result["items"][0]["variables"]
        assert "vm_disk_type" not in variables

    def test_export_draft_raises(self):
        order = _make_order(status="draft")
        self.order_repo.get_by_id.return_value = order
        with pytest.raises(ValueError, match="draft"):
            self.service.export_tofu("ord-1", "user-1")

    def test_export_correct_types(self):
        item = _make_item(parameters={"cpu": 4, "ha": True, "name": "srv01"})
        order = _make_order(status="submitted", items=[item])
        self.order_repo.get_by_id.return_value = order
        template = _make_template(parameters=[
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "vm_cpu", "display_order": 1,
             "constraints": {}, "depends_on": []},
            {"key": "ha", "label": "HA", "type": "boolean", "required": False,
             "tofu_variable_name": "vm_ha_enabled", "display_order": 2,
             "constraints": {}, "depends_on": []},
            {"key": "name", "label": "Name", "type": "string", "required": True,
             "tofu_variable_name": "vm_name", "display_order": 3,
             "constraints": {}, "depends_on": []},
        ])
        self.template_repo.get_by_slug_and_version.return_value = template

        result = self.service.export_tofu("ord-1", "user-1")
        variables = result["items"][0]["variables"]
        assert variables["vm_cpu"] == 4
        assert variables["vm_ha_enabled"] is True
        assert variables["vm_name"] == "srv01"
