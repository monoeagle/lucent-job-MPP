import uuid
import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.data.db.session import Base
from app.data.repositories.subscription_repository import SubscriptionRepository
from app.data.repositories.order_repository import OrderRepository


DB_URL = "postgresql://mpp:mpp@localhost:5432/mpp_test"


_CLEANUP_TABLES = [
    "subscriptions", "group_subscriptions", "order_items",
    "order_item_groups", "orders", "service_templates",
]


@pytest.fixture(scope="module")
def engine():
    # Use create_engine directly to avoid the module-level engine cache
    # which is shared across test files and causes drop_all/create_all conflicts.
    eng = create_engine(DB_URL, echo=False)
    # Ensure all tables exist without touching tables other test files created.
    Base.metadata.create_all(eng, checkfirst=True)
    # Pre-clean data from any previous run
    with eng.begin() as conn:
        for tname in _CLEANUP_TABLES:
            conn.execute(Base.metadata.tables[tname].delete())
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.rollback()
    sess.close()
    # Clean all data touched by these tests (FK-safe order)
    with engine.begin() as conn:
        conn.execute(Base.metadata.tables["subscriptions"].delete())
        conn.execute(Base.metadata.tables["group_subscriptions"].delete())
        conn.execute(Base.metadata.tables["order_items"].delete())
        conn.execute(Base.metadata.tables["order_item_groups"].delete())
        conn.execute(Base.metadata.tables["orders"].delete())
        conn.execute(Base.metadata.tables["service_templates"].delete())


@pytest.fixture
def repo(session):
    return SubscriptionRepository(session)


@pytest.fixture
def order_repo(session):
    return OrderRepository(session)


@pytest.fixture
def seeded_item(order_repo):
    """Creates a template + order + item in DB, returns the OrderItemModel."""
    from app.data.db.models.service_template import ServiceTemplateModel
    from app.data.db.session import get_engine, get_session_factory

    # Create a service template (required for realistic slug/version data)
    template = ServiceTemplateModel(
        id=str(uuid.uuid4()),
        slug="vm-linux",
        version="1.0.0",
        type="vm",
        display_name="Linux VM",
        category="compute",
        tofu_module_source="git::https://example.com/modules/vm-linux",
        parameters=[],
    )
    order_repo.session.add(template)
    order_repo.session.commit()

    order = order_repo.create_order(
        requester_id="test-requester",
        title="Test Order for Subscriptions",
    )
    item = order_repo.add_item(
        order_id=order.id,
        template_slug="vm-linux",
        template_version="1.0.0",
        display_name="My Linux VM",
        parameters={"cpu": 4, "ram_gb": 16},
    )
    # Ensure the order relationship is loaded
    order_repo.session.refresh(item)
    return item


class TestCreateFromOrderItem:
    def test_creates_subscription_with_required_fields(self, repo, seeded_item):
        sub = repo.create_from_order_item(seeded_item, monthly_cost_eur=Decimal("49.99"))
        assert sub.id is not None
        assert sub.order_item_id == seeded_item.id
        assert sub.requester_id == "test-requester"
        assert sub.status == "ordered"
        assert sub.display_name == "My Linux VM"
        assert sub.template_slug == "vm-linux"
        assert sub.template_version == "1.0.0"
        assert sub.parameters == {"cpu": 4, "ram_gb": 16}
        assert sub.monthly_cost_eur == Decimal("49.99")
        assert sub.activated_at is None
        assert sub.cancelled_at is None

    def test_creates_subscription_without_cost(self, repo, seeded_item):
        sub = repo.create_from_order_item(seeded_item)
        assert sub.monthly_cost_eur is None
        assert sub.status == "ordered"

    def test_order_item_id_is_unique(self, repo, seeded_item):
        repo.create_from_order_item(seeded_item)
        with pytest.raises(Exception):
            # Second subscription for the same order_item_id must fail (unique constraint)
            repo.create_from_order_item(seeded_item)


class TestListSubscriptions:
    def test_list_all(self, repo, seeded_item, order_repo):
        repo.create_from_order_item(seeded_item)
        result = repo.list_subscriptions()
        assert result["total"] == 1
        assert len(result["items"]) == 1

    def test_list_filtered_by_requester(self, repo, seeded_item, order_repo):
        # Create a second order + item with a different requester
        order2 = order_repo.create_order(requester_id="other-user", title="Other Order")
        item2 = order_repo.add_item(
            order_id=order2.id,
            template_slug="vm-linux",
            template_version="1.0.0",
            display_name="Other VM",
            parameters={},
        )
        order_repo.session.refresh(item2)

        repo.create_from_order_item(seeded_item)
        repo.create_from_order_item(item2)

        result = repo.list_subscriptions(requester_id="test-requester")
        assert result["total"] == 1
        assert result["items"][0].requester_id == "test-requester"

    def test_list_filtered_by_status(self, repo, seeded_item, order_repo):
        sub = repo.create_from_order_item(seeded_item)
        repo.update_status(sub.id, "active")

        # Create second item+subscription in pending
        order2 = order_repo.create_order(requester_id="test-requester", title="Order 2")
        item2 = order_repo.add_item(
            order_id=order2.id,
            template_slug="vm-linux",
            template_version="1.0.0",
            display_name="VM 2",
            parameters={},
        )
        order_repo.session.refresh(item2)
        repo.create_from_order_item(item2)

        active_result = repo.list_subscriptions(status="active")
        assert active_result["total"] == 1
        assert active_result["items"][0].id == sub.id

        ordered_result = repo.list_subscriptions(status="ordered")
        assert ordered_result["total"] == 1

    def test_list_pagination(self, repo, order_repo):
        for i in range(5):
            order = order_repo.create_order(requester_id="test-requester", title=f"Order {i}")
            item = order_repo.add_item(
                order_id=order.id,
                template_slug="vm-linux",
                template_version="1.0.0",
                display_name=f"VM {i}",
                parameters={},
            )
            order_repo.session.refresh(item)
            repo.create_from_order_item(item)

        result = repo.list_subscriptions(limit=2, offset=0)
        assert len(result["items"]) == 2
        assert result["total"] == 5
        assert result["limit"] == 2
        assert result["offset"] == 0

        result2 = repo.list_subscriptions(limit=2, offset=2)
        assert len(result2["items"]) == 2
        assert result2["offset"] == 2


class TestUpdateStatus:
    def test_update_to_active_sets_activated_at(self, repo, seeded_item):
        sub = repo.create_from_order_item(seeded_item)
        updated = repo.update_status(sub.id, "active")
        assert updated.status == "active"
        assert updated.activated_at is not None
        assert updated.cancelled_at is None

    def test_update_to_cancelled_sets_cancelled_at(self, repo, seeded_item):
        sub = repo.create_from_order_item(seeded_item)
        updated = repo.update_status(sub.id, "cancelled")
        assert updated.status == "cancelled"
        assert updated.cancelled_at is not None
        assert updated.activated_at is None

    def test_update_to_other_status_sets_no_timestamps(self, repo, seeded_item):
        sub = repo.create_from_order_item(seeded_item)
        updated = repo.update_status(sub.id, "suspended")
        assert updated.status == "suspended"
        assert updated.activated_at is None
        assert updated.cancelled_at is None

    def test_update_nonexistent_raises(self, repo):
        with pytest.raises(SubscriptionRepository.SubscriptionNotFoundError):
            repo.update_status(str(uuid.uuid4()), "active")


class TestSetPendingChanges:
    def test_set_pending_changes_stores_jsonb(self, repo, seeded_item):
        sub = repo.create_from_order_item(seeded_item)
        changes = {"cpu": 8, "ram_gb": 32}
        updated = repo.set_pending_changes(sub.id, changes)
        assert updated.pending_changes == changes

    def test_set_pending_changes_nonexistent_raises(self, repo):
        with pytest.raises(SubscriptionRepository.SubscriptionNotFoundError):
            repo.set_pending_changes(str(uuid.uuid4()), {"cpu": 8})


class TestApplyPendingChanges:
    def test_apply_merges_into_parameters_and_clears(self, repo, seeded_item):
        sub = repo.create_from_order_item(seeded_item)
        repo.set_pending_changes(sub.id, {"cpu": 8, "new_key": "value"})
        updated = repo.apply_pending_changes(sub.id)
        assert updated.parameters == {"cpu": 8, "ram_gb": 16, "new_key": "value"}
        assert updated.pending_changes is None

    def test_apply_with_no_pending_changes_is_noop(self, repo, seeded_item):
        sub = repo.create_from_order_item(seeded_item)
        original_params = dict(sub.parameters)
        updated = repo.apply_pending_changes(sub.id)
        assert updated.parameters == original_params
        assert updated.pending_changes is None

    def test_apply_nonexistent_raises(self, repo):
        with pytest.raises(SubscriptionRepository.SubscriptionNotFoundError):
            repo.apply_pending_changes(str(uuid.uuid4()))


class TestCreateGroup:
    def test_create_group_with_name_and_requester(self, repo):
        group = repo.create_group(name="Production VMs", requester_id="test-requester")
        assert group.id is not None
        assert group.name == "Production VMs"
        assert group.requester_id == "test-requester"
        assert group.created_at is not None

    def test_create_group_returns_persisted_model(self, repo):
        group = repo.create_group(name="Dev Group", requester_id="dev-user")
        loaded = repo.get_group_by_id(group.id)
        assert loaded is not None
        assert loaded.name == "Dev Group"


class TestAssignToGroup:
    def test_assign_subscription_to_group(self, repo, seeded_item):
        sub = repo.create_from_order_item(seeded_item)
        group = repo.create_group(name="My Group", requester_id="test-requester")
        updated = repo.assign_to_group(sub.id, group.id)
        assert updated.group_subscription_id == group.id

    def test_assign_to_nonexistent_group_raises(self, repo, seeded_item):
        sub = repo.create_from_order_item(seeded_item)
        with pytest.raises(SubscriptionRepository.GroupNotFoundError):
            repo.assign_to_group(sub.id, str(uuid.uuid4()))

    def test_assign_nonexistent_subscription_raises(self, repo):
        group = repo.create_group(name="Some Group", requester_id="user-1")
        with pytest.raises(SubscriptionRepository.SubscriptionNotFoundError):
            repo.assign_to_group(str(uuid.uuid4()), group.id)

    def test_group_subscriptions_relationship(self, repo, seeded_item):
        sub = repo.create_from_order_item(seeded_item)
        group = repo.create_group(name="Group With Subs", requester_id="test-requester")
        repo.assign_to_group(sub.id, group.id)

        loaded_group = repo.get_group_by_id(group.id)
        repo.session.refresh(loaded_group)
        assert len(loaded_group.subscriptions) == 1
        assert loaded_group.subscriptions[0].id == sub.id
