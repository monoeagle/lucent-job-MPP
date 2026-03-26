import uuid
from datetime import datetime, timezone

from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models.dispatch_log import DispatchLogModel
from app.data.db.models.order import OrderModel, OrderItemModel


class TestDispatchLogModel:
    def setup_method(self):
        self.engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)

    def teardown_method(self):
        Base.metadata.drop_all(self.engine)

    def _create_order_with_item(self, session):
        order = OrderModel(
            id=str(uuid.uuid4()),
            order_number=f"ORD-{uuid.uuid4().hex[:8]}",
            requester_id="user-1",
            status="submitted",
            title="Test Order",
        )
        item = OrderItemModel(
            id=str(uuid.uuid4()),
            order_id=order.id,
            template_slug="vm-linux",
            template_version="1.0",
            display_name="Linux VM",
            parameters={},
            position=1,
            provisioning_status="not_started",
        )
        session.add(order)
        session.add(item)
        session.commit()
        return order, item

    def test_create_dispatch_log(self):
        session = self.Session()
        order, item = self._create_order_with_item(session)

        log = DispatchLogModel(
            id=str(uuid.uuid4()),
            order_id=order.id,
            order_item_id=item.id,
            job_id="pipeline-42",
            dispatch_method="gitlab",
            dispatched_at=datetime.now(timezone.utc),
            attempt_count=1,
            status="success",
            error_message=None,
        )
        session.add(log)
        session.commit()

        saved = session.query(DispatchLogModel).filter_by(order_id=order.id).first()
        assert saved is not None
        assert saved.job_id == "pipeline-42"
        assert saved.dispatch_method == "gitlab"
        assert saved.status == "success"
        assert saved.attempt_count == 1
        session.close()

    def test_query_by_order_item(self):
        session = self.Session()
        order, item = self._create_order_with_item(session)

        for i in range(3):
            session.add(DispatchLogModel(
                id=str(uuid.uuid4()),
                order_id=order.id,
                order_item_id=item.id,
                job_id=f"pipeline-{i}",
                dispatch_method="gitlab",
                dispatched_at=datetime.now(timezone.utc),
                attempt_count=i + 1,
                status="retrying" if i < 2 else "success",
            ))
        session.commit()

        logs = session.query(DispatchLogModel).filter_by(
            order_item_id=item.id
        ).all()
        assert len(logs) == 3
        session.close()

    def test_order_item_provisioning_status(self):
        session = self.Session()
        order, item = self._create_order_with_item(session)

        assert item.provisioning_status == "not_started"
        assert item.job_id is None

        item.provisioning_status = "pending"
        item.job_id = "pipeline-99"
        session.commit()

        refreshed = session.query(OrderItemModel).filter_by(id=item.id).first()
        assert refreshed.provisioning_status == "pending"
        assert refreshed.job_id == "pipeline-99"
        session.close()
