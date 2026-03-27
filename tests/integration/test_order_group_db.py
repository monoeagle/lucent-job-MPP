# tests/integration/test_order_group_db.py
import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models.order import OrderModel, OrderItemModel
from app.data.db.models.order_group import OrderItemGroupModel


class TestOrderItemGroupModel:
    def setup_method(self):
        self.engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)

    def teardown_method(self):
        Base.metadata.drop_all(self.engine)

    def _make_order(self, **kwargs):
        defaults = dict(
            id=str(uuid.uuid4()),
            order_number=f"ORD-{uuid.uuid4().hex[:8]}",
            requester_id=str(uuid.uuid4()),
            status="draft",
            title="Test Order",
        )
        defaults.update(kwargs)
        return OrderModel(**defaults)

    def test_create_group_verify_fields(self):
        session = self.Session()
        order = self._make_order()
        group = OrderItemGroupModel(
            id=str(uuid.uuid4()),
            order_id=order.id,
            name="Network Resources",
            description="All network-related items",
            position=1,
        )
        session.add(order)
        session.add(group)
        session.commit()

        loaded = session.query(OrderItemGroupModel).filter_by(id=group.id).first()
        assert loaded is not None
        assert loaded.name == "Network Resources"
        assert loaded.description == "All network-related items"
        assert loaded.position == 1
        assert loaded.order_id == order.id
        assert loaded.created_at is not None
        assert loaded.updated_at is not None
        session.close()

    def test_create_group_with_items(self):
        session = self.Session()
        order = self._make_order()
        group = OrderItemGroupModel(
            id=str(uuid.uuid4()),
            order_id=order.id,
            name="Compute",
            position=1,
        )
        item = OrderItemModel(
            id=str(uuid.uuid4()),
            order_id=order.id,
            template_slug="vm-linux",
            template_version="1.0.0",
            display_name="Linux VM",
            parameters={"cpu_cores": 4},
            position=1,
            group_id=group.id,
        )
        session.add(order)
        session.add(group)
        session.add(item)
        session.commit()

        loaded = session.query(OrderItemGroupModel).filter_by(id=group.id).first()
        assert len(loaded.items) == 1
        assert loaded.items[0].display_name == "Linux VM"
        session.close()

    def test_unique_constraint_order_name(self):
        session = self.Session()
        order = self._make_order()
        g1 = OrderItemGroupModel(
            id=str(uuid.uuid4()), order_id=order.id, name="Same Name", position=1,
        )
        g2 = OrderItemGroupModel(
            id=str(uuid.uuid4()), order_id=order.id, name="Same Name", position=2,
        )
        session.add(order)
        session.add(g1)
        session.commit()
        session.add(g2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.close()

    def test_order_item_with_group_quantity_instance_parameters(self):
        session = self.Session()
        order = self._make_order()
        group = OrderItemGroupModel(
            id=str(uuid.uuid4()), order_id=order.id, name="Storage", position=1,
        )
        params = [{"disk": "100GB"}, {"disk": "200GB"}, {"disk": "300GB"}]
        item = OrderItemModel(
            id=str(uuid.uuid4()),
            order_id=order.id,
            template_slug="storage-block",
            template_version="2.0.0",
            display_name="Block Storage",
            parameters={"type": "ssd"},
            position=1,
            group_id=group.id,
            quantity=3,
            instance_parameters=params,
        )
        session.add(order)
        session.add(group)
        session.add(item)
        session.commit()

        loaded = session.query(OrderItemModel).filter_by(id=item.id).first()
        assert loaded.quantity == 3
        assert loaded.instance_parameters == params
        assert loaded.group_id == group.id
        session.close()

    def test_delete_group_sets_items_group_id_null(self):
        session = self.Session()
        order = self._make_order()
        group = OrderItemGroupModel(
            id=str(uuid.uuid4()), order_id=order.id, name="Temp Group", position=1,
        )
        item = OrderItemModel(
            id=str(uuid.uuid4()),
            order_id=order.id,
            template_slug="vm-linux",
            template_version="1.0.0",
            display_name="Linux VM",
            parameters={},
            position=1,
            group_id=group.id,
        )
        session.add(order)
        session.add(group)
        session.add(item)
        session.commit()

        session.delete(group)
        session.commit()

        loaded_item = session.query(OrderItemModel).filter_by(id=item.id).first()
        assert loaded_item is not None
        assert loaded_item.group_id is None
        session.close()

    def test_order_item_defaults_quantity_and_instance_parameters(self):
        session = self.Session()
        order = self._make_order()
        item = OrderItemModel(
            id=str(uuid.uuid4()),
            order_id=order.id,
            template_slug="vm-linux",
            template_version="1.0.0",
            display_name="Linux VM",
            parameters={"cpu_cores": 2},
            position=1,
        )
        session.add(order)
        session.add(item)
        session.commit()

        loaded = session.query(OrderItemModel).filter_by(id=item.id).first()
        assert loaded.quantity == 1
        assert loaded.instance_parameters == []
        assert loaded.group_id is None
        session.close()

    def test_delete_order_cascades_to_groups(self):
        session = self.Session()
        order = self._make_order()
        group = OrderItemGroupModel(
            id=str(uuid.uuid4()), order_id=order.id, name="Will Be Deleted", position=1,
        )
        session.add(order)
        session.add(group)
        session.commit()

        session.delete(order)
        session.commit()

        assert session.query(OrderItemGroupModel).filter_by(id=group.id).first() is None
        session.close()
