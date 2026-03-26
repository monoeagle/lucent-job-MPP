# tests/integration/test_order_db_model.py
import uuid
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models.order import OrderModel, OrderItemModel


class TestOrderModel:
    def setup_method(self):
        self.engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)

    def teardown_method(self):
        Base.metadata.drop_all(self.engine)

    def test_create_order_with_items(self):
        session = self.Session()
        order = OrderModel(
            id=str(uuid.uuid4()),
            order_number="ORD-2026-00001",
            requester_id=str(uuid.uuid4()),
            status="draft",
            title="Test Order",
            business_reason="Testing",
        )
        item = OrderItemModel(
            id=str(uuid.uuid4()),
            order_id=order.id,
            template_slug="vm-linux",
            template_version="1.0.0",
            display_name="Linux VM",
            parameters={"cpu_cores": 4},
            position=1,
            validation_state="unchecked",
            validation_errors=[],
        )
        session.add(order)
        session.add(item)
        session.commit()

        loaded = session.query(OrderModel).filter_by(id=order.id).first()
        assert loaded is not None
        assert loaded.title == "Test Order"
        assert len(loaded.items) == 1
        assert loaded.items[0].template_slug == "vm-linux"
        session.close()

    def test_order_number_unique(self):
        session = self.Session()
        o1 = OrderModel(id=str(uuid.uuid4()), order_number="ORD-2026-00001",
                        requester_id=str(uuid.uuid4()), status="draft", title="Order 1")
        o2 = OrderModel(id=str(uuid.uuid4()), order_number="ORD-2026-00001",
                        requester_id=str(uuid.uuid4()), status="draft", title="Order 2")
        session.add(o1)
        session.commit()
        session.add(o2)
        import pytest
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            session.commit()
        session.close()
