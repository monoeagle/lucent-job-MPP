import pytest
import uuid
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models.order import OrderModel, OrderItemModel
from app.data.db.models.subscription import SubscriptionModel, GroupSubscriptionModel

@pytest.fixture
def db_session(app):
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

def _make_order_item(session):
    """Create and persist a minimal order + order_item for FK purposes."""
    order = OrderModel(
        id=str(uuid.uuid4()),
        order_number=f"ORD-{uuid.uuid4().hex[:8]}",
        requester_id="test-requester",
        status="submitted",
        title="Test Order",
    )
    item = OrderItemModel(
        id=str(uuid.uuid4()),
        order_id=order.id,
        template_slug="vm-linux",
        template_version="1.0.0",
        display_name="Linux VM",
        parameters={"cpu_cores": 4},
        position=1,
    )
    session.add(order)
    session.add(item)
    session.flush()
    return item

class TestSubscriptionModel:
    def test_create_subscription(self, db_session):
        order_item = _make_order_item(db_session)
        sub = SubscriptionModel(
            id=str(uuid.uuid4()), order_item_id=order_item.id,
            requester_id="test-requester", status="ordered",
            display_name="Linux VM", template_slug="vm-linux",
            template_version="1.0.0", parameters={"cpu_cores": 4},
        )
        db_session.add(sub)
        db_session.commit()
        found = db_session.query(SubscriptionModel).filter_by(id=sub.id).first()
        assert found is not None
        assert found.status == "ordered"
        assert found.parameters == {"cpu_cores": 4}
        assert found.activated_at is None
        assert found.pending_changes is None

    def test_create_group_subscription(self, db_session):
        group = GroupSubscriptionModel(
            id=str(uuid.uuid4()), name="Web-Cluster", requester_id="test-requester",
        )
        db_session.add(group)
        db_session.commit()
        found = db_session.query(GroupSubscriptionModel).filter_by(id=group.id).first()
        assert found is not None
        assert found.name == "Web-Cluster"
