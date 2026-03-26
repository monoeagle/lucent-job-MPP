import uuid
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.order_repository import OrderRepository


@pytest.fixture
def repo():
    engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    yield OrderRepository(session)
    session.close()
    Base.metadata.drop_all(engine)


class TestCreateAndGet:
    def test_create_order_returns_model_with_id_and_number(self, repo):
        order = repo.create_order(
            requester_id="user-1",
            title="My First Order",
            business_reason="Testing",
            desired_date="2026-04-01",
        )
        assert order.id is not None
        assert order.order_number.startswith("ORD-2026-")
        assert order.requester_id == "user-1"
        assert order.title == "My First Order"
        assert order.business_reason == "Testing"
        assert order.desired_date == "2026-04-01"
        assert order.status == "draft"

    def test_create_order_minimal(self, repo):
        order = repo.create_order(requester_id="user-1", title="Minimal")
        assert order.business_reason is None
        assert order.desired_date is None

    def test_get_by_id_returns_order_with_items(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order With Items")
        repo.add_item(
            order_id=order.id,
            template_slug="vm-linux",
            template_version="1.0.0",
            display_name="Linux VM",
            parameters={"cpu": 4},
        )
        loaded = repo.get_by_id(order.id)
        assert loaded is not None
        assert loaded.title == "Order With Items"
        assert len(loaded.items) == 1
        assert loaded.items[0].template_slug == "vm-linux"

    def test_get_by_id_not_found(self, repo):
        assert repo.get_by_id("nonexistent") is None


class TestListOrders:
    def test_list_all_admin(self, repo):
        repo.create_order(requester_id="user-1", title="Order A")
        repo.create_order(requester_id="user-2", title="Order B")
        result = repo.list_orders()
        assert result["total"] == 2
        assert len(result["items"]) == 2

    def test_list_filtered_by_requester(self, repo):
        repo.create_order(requester_id="user-1", title="Order A")
        repo.create_order(requester_id="user-2", title="Order B")
        result = repo.list_orders(requester_id="user-1")
        assert result["total"] == 1
        assert result["items"][0].requester_id == "user-1"

    def test_list_filtered_by_status(self, repo):
        o1 = repo.create_order(requester_id="user-1", title="Draft")
        o2 = repo.create_order(requester_id="user-1", title="Validated")
        repo.update_order_status(o2.id, "validated")
        result = repo.list_orders(status_filter="draft")
        assert result["total"] == 1
        assert result["items"][0].title == "Draft"

    def test_list_pagination(self, repo):
        for i in range(5):
            repo.create_order(requester_id="user-1", title=f"Order {i}")
        result = repo.list_orders(limit=2, offset=0)
        assert len(result["items"]) == 2
        assert result["total"] == 5
        assert result["limit"] == 2
        assert result["offset"] == 0

        result2 = repo.list_orders(limit=2, offset=2)
        assert len(result2["items"]) == 2
        assert result2["offset"] == 2


class TestUpdateOrder:
    def test_update_title(self, repo):
        order = repo.create_order(requester_id="user-1", title="Old Title")
        updated = repo.update_order(order.id, title="New Title")
        assert updated.title == "New Title"

    def test_update_business_reason(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        updated = repo.update_order(order.id, business_reason="New Reason")
        assert updated.business_reason == "New Reason"

    def test_update_desired_date(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        updated = repo.update_order(order.id, desired_date="2026-06-01")
        assert updated.desired_date == "2026-06-01"

    def test_update_nonexistent_raises(self, repo):
        with pytest.raises(OrderRepository.OrderNotFoundError):
            repo.update_order("nonexistent", title="X")


class TestDeleteOrder:
    def test_delete_order_cascades_items(self, repo):
        order = repo.create_order(requester_id="user-1", title="To Delete")
        repo.add_item(order.id, "vm-linux", "1.0.0", "VM", {"cpu": 2})
        repo.delete_order(order.id)
        assert repo.get_by_id(order.id) is None

    def test_delete_nonexistent_raises(self, repo):
        with pytest.raises(OrderRepository.OrderNotFoundError):
            repo.delete_order("nonexistent")


class TestItems:
    def test_add_item_auto_position(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        item1 = repo.add_item(order.id, "vm-linux", "1.0.0", "VM 1", {"cpu": 2})
        item2 = repo.add_item(order.id, "db-postgres", "1.0.0", "DB", {"size": 10})
        assert item1.position == 1
        assert item2.position == 2

    def test_update_item_parameters_resets_validation(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        item = repo.add_item(order.id, "vm-linux", "1.0.0", "VM", {"cpu": 2})
        repo.update_item_validation(item.id, "valid", [])
        updated = repo.update_item_parameters(item.id, {"cpu": 8})
        assert updated.parameters == {"cpu": 8}
        assert updated.validation_state == "unchecked"

    def test_remove_item(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        item = repo.add_item(order.id, "vm-linux", "1.0.0", "VM", {"cpu": 2})
        repo.remove_item(item.id)
        assert repo.get_item_by_id(item.id) is None

    def test_remove_nonexistent_raises(self, repo):
        with pytest.raises(OrderRepository.ItemNotFoundError):
            repo.remove_item("nonexistent")

    def test_get_item_by_id(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        item = repo.add_item(order.id, "vm-linux", "1.0.0", "VM", {"cpu": 2})
        loaded = repo.get_item_by_id(item.id)
        assert loaded is not None
        assert loaded.display_name == "VM"

    def test_get_item_by_id_not_found(self, repo):
        assert repo.get_item_by_id("nonexistent") is None


class TestStatusTransition:
    def test_update_status(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        updated = repo.update_order_status(order.id, "validated")
        assert updated.status == "validated"

    def test_update_status_submitted_sets_submitted_at(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        repo.update_order_status(order.id, "validated")
        updated = repo.update_order_status(order.id, "submitted")
        assert updated.status == "submitted"
        assert updated.submitted_at is not None

    def test_update_status_nonexistent_raises(self, repo):
        with pytest.raises(OrderRepository.OrderNotFoundError):
            repo.update_order_status("nonexistent", "validated")


class TestItemValidation:
    def test_update_item_validation(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        item = repo.add_item(order.id, "vm-linux", "1.0.0", "VM", {"cpu": 2})
        updated = repo.update_item_validation(item.id, "invalid", ["cpu must be >= 1"])
        assert updated.validation_state == "invalid"
        assert updated.validation_errors == ["cpu must be >= 1"]

    def test_update_validation_nonexistent_raises(self, repo):
        with pytest.raises(OrderRepository.ItemNotFoundError):
            repo.update_item_validation("nonexistent", "valid", [])


class TestReorderItems:
    def test_reorder_items(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        item1 = repo.add_item(order.id, "vm-linux", "1.0.0", "VM", {})
        item2 = repo.add_item(order.id, "db-postgres", "1.0.0", "DB", {})
        item3 = repo.add_item(order.id, "s3-bucket", "1.0.0", "S3", {})

        repo.reorder_items(order.id, [
            {"item_id": item3.id, "position": 1},
            {"item_id": item1.id, "position": 2},
            {"item_id": item2.id, "position": 3},
        ])

        loaded = repo.get_by_id(order.id)
        positions = {item.id: item.position for item in loaded.items}
        assert positions[item3.id] == 1
        assert positions[item1.id] == 2
        assert positions[item2.id] == 3


class TestOrderNumber:
    def test_sequential_order_numbers(self, repo):
        o1 = repo.create_order(requester_id="user-1", title="First")
        o2 = repo.create_order(requester_id="user-1", title="Second")
        # Parse sequence numbers
        seq1 = int(o1.order_number.split("-")[-1])
        seq2 = int(o2.order_number.split("-")[-1])
        assert seq2 == seq1 + 1

    def test_get_next_order_number_starts_at_one(self, repo):
        number = repo.get_next_order_number()
        assert number == "ORD-2026-00001"
