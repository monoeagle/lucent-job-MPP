# tests/unit/test_order_groups_service.py
import pytest
from unittest.mock import MagicMock
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
               template_version="1.0.0", parameters=None, quantity=1,
               instance_parameters=None, validation_state="unchecked"):
    item = MagicMock()
    item.id = item_id
    item.order_id = order_id
    item.template_slug = template_slug
    item.template_version = template_version
    item.parameters = parameters or {"cpu": 4}
    item.quantity = quantity
    item.instance_parameters = instance_parameters or []
    item.validation_state = validation_state
    item.validation_errors = []
    return item


def _make_group(group_id="grp-1", order_id="ord-1", name="Compute"):
    group = MagicMock()
    group.id = group_id
    group.order_id = order_id
    group.name = name
    group.items = []
    return group


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
         "constraints": {"min": 1, "max": 64}, "depends_on": [],
         "per_instance": False},
    ]
    tpl.cross_parameter_rules = cross_parameter_rules or []
    tpl.tofu_module_source = tofu_module_source
    return tpl


class TestCreateGroup:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_create_group_success(self):
        order = _make_order()
        self.order_repo.get_by_id.return_value = order
        expected_group = _make_group()
        self.order_repo.create_group.return_value = expected_group

        result = self.service.create_group("ord-1", "user-1", "Compute")
        assert result["group"] == expected_group
        self.order_repo.create_group.assert_called_once_with("ord-1", "Compute", None)

    def test_create_group_non_draft_raises(self):
        order = _make_order(status="submitted")
        self.order_repo.get_by_id.return_value = order
        with pytest.raises(ValueError, match="draft"):
            self.service.create_group("ord-1", "user-1", "Compute")


class TestDeleteGroup:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_delete_group_with_items_raises(self):
        order = _make_order()
        self.order_repo.get_by_id.return_value = order
        from app.data.repositories.order_repository import GroupNotEmptyError
        self.order_repo.delete_group.side_effect = GroupNotEmptyError("Group has items")
        with pytest.raises(GroupNotEmptyError):
            self.service.delete_group("ord-1", "grp-1", "user-1")


class TestAssignItemToGroup:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_assign_item_to_group_success(self):
        order = _make_order()
        self.order_repo.get_by_id.return_value = order
        item = _make_item(order_id="ord-1")
        self.order_repo.get_item_by_id.return_value = item
        group = _make_group(order_id="ord-1")
        self.order_repo.get_group.return_value = group

        self.service.assign_item_to_group("ord-1", "item-1", "user-1", "grp-1")
        self.order_repo.assign_item_to_group.assert_called_once_with("item-1", "grp-1")

    def test_assign_item_to_group_different_order_raises(self):
        order = _make_order()
        self.order_repo.get_by_id.return_value = order
        item = _make_item(order_id="ord-1")
        self.order_repo.get_item_by_id.return_value = item
        group = _make_group(group_id="grp-1", order_id="ord-OTHER")
        self.order_repo.get_group.return_value = group

        with pytest.raises(ValueError, match="order"):
            self.service.assign_item_to_group("ord-1", "item-1", "user-1", "grp-1")


class TestAddItemWithQuantity:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_add_item_with_quantity(self):
        order = _make_order()
        self.order_repo.get_by_id.return_value = order
        template = _make_template()
        self.template_repo.get_by_slug_and_version.return_value = template
        expected_item = _make_item(quantity=3)
        self.order_repo.add_item.return_value = expected_item

        result = self.service.add_item(
            "ord-1", "user-1", "vm-basic", "1.0.0", {"cpu": 4},
            quantity=3, instance_parameters=[{"tag": "a"}, {"tag": "b"}, {"tag": "c"}],
        )
        assert result["item"] == expected_item
        self.order_repo.add_item.assert_called_once_with(
            "ord-1", "vm-basic", "1.0.0", "Basic VM", {"cpu": 4},
            quantity=3, instance_parameters=[{"tag": "a"}, {"tag": "b"}, {"tag": "c"}],
        )


class TestValidateWithQuantity:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_validate_quantity_gt1_validates_all_instances(self):
        item = _make_item(
            quantity=2,
            instance_parameters=[{"hostname": "srv01"}, {"hostname": "srv02"}],
        )
        order = _make_order(items=[item])
        self.order_repo.get_by_id.return_value = order
        template = _make_template(parameters=[
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "vm_cpu_count", "display_order": 1,
             "constraints": {}, "depends_on": [], "per_instance": False},
            {"key": "hostname", "label": "Hostname", "type": "string", "required": True,
             "tofu_variable_name": "vm_hostname", "display_order": 2,
             "constraints": {}, "depends_on": [], "per_instance": True},
        ])
        self.template_repo.get_by_slug_and_version.return_value = template
        self.catalog_service.validate_parameters.return_value = []

        result = self.service.validate_order("ord-1", "user-1")
        assert result["status"] == OrderStatus.VALIDATED
        # Shared params validated once, plus per-instance params validated per instance
        assert self.catalog_service.validate_parameters.call_count >= 1


class TestExportWithQuantity:
    def setup_method(self):
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.catalog_service = MagicMock()
        self.service = OrderService(self.order_repo, self.template_repo, self.catalog_service)

    def test_export_quantity_3_produces_3_blocks(self):
        item = _make_item(
            parameters={"cpu": 4},
            quantity=3,
            instance_parameters=[{"hostname": "srv01"}, {"hostname": "srv02"}, {"hostname": "srv03"}],
        )
        order = _make_order(status="validated", items=[item])
        self.order_repo.get_by_id.return_value = order
        template = _make_template(parameters=[
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "vm_cpu_count", "display_order": 1,
             "constraints": {}, "depends_on": [], "per_instance": False},
            {"key": "hostname", "label": "Hostname", "type": "string", "required": True,
             "tofu_variable_name": "vm_hostname", "display_order": 2,
             "constraints": {}, "depends_on": [], "per_instance": True},
        ])
        self.template_repo.get_by_slug_and_version.return_value = template

        result = self.service.export_tofu("ord-1", "user-1")
        assert len(result["items"]) == 3
        # Each block should have shared + instance-specific variables
        assert result["items"][0]["variables"]["vm_hostname"] == "srv01"
        assert result["items"][1]["variables"]["vm_hostname"] == "srv02"
        assert result["items"][2]["variables"]["vm_hostname"] == "srv03"
        # Shared params present in all blocks
        for block in result["items"]:
            assert block["variables"]["vm_cpu_count"] == 4
