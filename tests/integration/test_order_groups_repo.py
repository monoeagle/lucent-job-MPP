# tests/integration/test_order_groups_repo.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.order_repository import (
    OrderRepository, DuplicateGroupError, GroupNotEmptyError,
)


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


class TestCreateAndListGroups:
    def test_create_group_and_list(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        group = repo.create_group(order.id, "Network")
        assert group.name == "Network"
        assert group.order_id == order.id

        groups = repo.list_groups(order.id)
        assert len(groups) == 1
        assert groups[0].id == group.id

    def test_auto_position(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        g1 = repo.create_group(order.id, "First")
        g2 = repo.create_group(order.id, "Second")
        assert g1.position == 1
        assert g2.position == 2

    def test_duplicate_name_raises(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        repo.create_group(order.id, "Same Name")
        with pytest.raises(DuplicateGroupError):
            repo.create_group(order.id, "Same Name")


class TestUpdateGroup:
    def test_update_group_name(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        group = repo.create_group(order.id, "Old Name")
        updated = repo.update_group(group.id, name="New Name")
        assert updated.name == "New Name"


class TestDeleteGroup:
    def test_delete_empty_group(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        group = repo.create_group(order.id, "Empty Group")
        repo.delete_group(group.id)
        assert repo.get_group(group.id) is None

    def test_delete_non_empty_group_raises(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        group = repo.create_group(order.id, "Has Items")
        repo.add_item(order.id, "vm-linux", "1.0.0", "VM", {"cpu": 2})
        item = repo.get_by_id(order.id).items[0]
        repo.assign_item_to_group(item.id, group.id)
        with pytest.raises(GroupNotEmptyError):
            repo.delete_group(group.id)


class TestReorderGroups:
    def test_reorder_groups(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        g1 = repo.create_group(order.id, "First")
        g2 = repo.create_group(order.id, "Second")
        g3 = repo.create_group(order.id, "Third")

        repo.reorder_groups(order.id, [
            {"group_id": g3.id, "position": 1},
            {"group_id": g1.id, "position": 2},
            {"group_id": g2.id, "position": 3},
        ])

        groups = repo.list_groups(order.id)
        assert groups[0].id == g3.id
        assert groups[1].id == g1.id
        assert groups[2].id == g2.id


class TestAssignItemToGroup:
    def test_assign_and_unassign(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        group = repo.create_group(order.id, "Compute")
        item = repo.add_item(order.id, "vm-linux", "1.0.0", "VM", {"cpu": 2})

        repo.assign_item_to_group(item.id, group.id)
        loaded = repo.get_item_by_id(item.id)
        assert loaded.group_id == group.id

        repo.assign_item_to_group(item.id, None)
        loaded = repo.get_item_by_id(item.id)
        assert loaded.group_id is None


class TestMaxGroups:
    def test_max_20_groups(self, repo):
        order = repo.create_order(requester_id="user-1", title="Order")
        for i in range(20):
            repo.create_group(order.id, f"Group {i}")
        with pytest.raises(ValueError, match="20"):
            repo.create_group(order.id, "Group 20")
