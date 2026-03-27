import uuid
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.data.db.models.order import OrderModel, OrderItemModel
from app.data.db.models.order_group import OrderItemGroupModel


class DuplicateGroupError(Exception):
    pass


class GroupNotEmptyError(Exception):
    pass


class OrderRepository:
    class OrderNotFoundError(Exception):
        pass

    class ItemNotFoundError(Exception):
        pass

    def __init__(self, session: Session):
        self.session = session

    def get_next_order_number(self) -> str:
        year = datetime.now(timezone.utc).year
        max_number = (
            self.session.query(func.max(OrderModel.order_number))
            .filter(OrderModel.order_number.like(f"ORD-{year}-%"))
            .scalar()
        )
        if max_number:
            seq = int(max_number.split("-")[-1]) + 1
        else:
            seq = 1
        return f"ORD-{year}-{seq:05d}"

    def create_order(self, requester_id: str, title: str,
                     business_reason: str | None = None,
                     desired_date: str | None = None,
                     context: dict | None = None) -> OrderModel:
        order = OrderModel(
            id=str(uuid.uuid4()),
            order_number=self.get_next_order_number(),
            requester_id=requester_id,
            status="draft",
            title=title,
            business_reason=business_reason,
            desired_date=desired_date,
            context=context,
        )
        self.session.add(order)
        self.session.commit()
        return order

    def get_by_id(self, order_id: str) -> OrderModel | None:
        return self.session.query(OrderModel).filter_by(id=order_id).first()

    def list_orders(self, requester_id: str | None = None,
                    status_filter: str | None = None,
                    limit: int = 20, offset: int = 0) -> dict:
        q = self.session.query(OrderModel)
        if requester_id:
            q = q.filter_by(requester_id=requester_id)
        if status_filter:
            q = q.filter_by(status=status_filter)
        total = q.count()
        items = q.order_by(OrderModel.created_at.desc()).offset(offset).limit(limit).all()
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def update_order(self, order_id: str, **fields) -> OrderModel:
        order = self.get_by_id(order_id)
        if order is None:
            raise self.OrderNotFoundError(f"Order '{order_id}' not found.")
        for key in ("title", "business_reason", "desired_date"):
            if key in fields:
                setattr(order, key, fields[key])
        self.session.commit()
        return order

    def delete_order(self, order_id: str) -> None:
        order = self.get_by_id(order_id)
        if order is None:
            raise self.OrderNotFoundError(f"Order '{order_id}' not found.")
        self.session.delete(order)
        self.session.commit()

    def add_item(self, order_id: str, template_slug: str, template_version: str,
                 display_name: str, parameters: dict,
                 quantity: int = 1,
                 instance_parameters: list | None = None) -> OrderItemModel:
        max_pos = (
            self.session.query(func.max(OrderItemModel.position))
            .filter_by(order_id=order_id)
            .scalar()
        )
        position = (max_pos or 0) + 1
        item = OrderItemModel(
            id=str(uuid.uuid4()),
            order_id=order_id,
            template_slug=template_slug,
            template_version=template_version,
            display_name=display_name,
            parameters=parameters,
            position=position,
            validation_state="unchecked",
            validation_errors=[],
            quantity=quantity,
            instance_parameters=instance_parameters or [],
        )
        self.session.add(item)
        self.session.commit()
        return item

    def update_item_parameters(self, item_id: str, parameters: dict) -> OrderItemModel:
        item = self.get_item_by_id(item_id)
        if item is None:
            raise self.ItemNotFoundError(f"Item '{item_id}' not found.")
        item.parameters = parameters
        item.validation_state = "unchecked"
        self.session.commit()
        return item

    def remove_item(self, item_id: str) -> None:
        item = self.get_item_by_id(item_id)
        if item is None:
            raise self.ItemNotFoundError(f"Item '{item_id}' not found.")
        self.session.delete(item)
        self.session.commit()

    def get_item_by_id(self, item_id: str) -> OrderItemModel | None:
        return self.session.query(OrderItemModel).filter_by(id=item_id).first()

    def update_order_status(self, order_id: str, new_status: str) -> OrderModel:
        order = self.get_by_id(order_id)
        if order is None:
            raise self.OrderNotFoundError(f"Order '{order_id}' not found.")
        order.status = new_status
        if new_status == "submitted":
            order.submitted_at = datetime.now(timezone.utc)
        self.session.commit()
        return order

    def update_item_validation(self, item_id: str, state: str, errors: list) -> OrderItemModel:
        item = self.get_item_by_id(item_id)
        if item is None:
            raise self.ItemNotFoundError(f"Item '{item_id}' not found.")
        item.validation_state = state
        item.validation_errors = errors
        self.session.commit()
        return item

    def reorder_items(self, order_id: str, positions: list[dict]) -> None:
        for entry in positions:
            item = self.get_item_by_id(entry["item_id"])
            if item:
                item.position = entry["position"]
        self.session.commit()

    # ── Group methods ─────────────────────────────────────────────

    def create_group(self, order_id: str, name: str,
                     description: str | None = None) -> OrderItemGroupModel:
        count = (
            self.session.query(func.count(OrderItemGroupModel.id))
            .filter_by(order_id=order_id)
            .scalar()
        )
        if count >= 20:
            raise ValueError("Maximum of 20 groups per order reached.")

        max_pos = (
            self.session.query(func.max(OrderItemGroupModel.position))
            .filter_by(order_id=order_id)
            .scalar()
        )
        position = (max_pos or 0) + 1

        group = OrderItemGroupModel(
            id=str(uuid.uuid4()),
            order_id=order_id,
            name=name,
            description=description,
            position=position,
        )
        self.session.add(group)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateGroupError(f"Group '{name}' already exists in this order.")
        return group

    def list_groups(self, order_id: str) -> list[OrderItemGroupModel]:
        return (
            self.session.query(OrderItemGroupModel)
            .filter_by(order_id=order_id)
            .order_by(OrderItemGroupModel.position)
            .all()
        )

    def get_group(self, group_id: str) -> OrderItemGroupModel | None:
        return self.session.query(OrderItemGroupModel).filter_by(id=group_id).first()

    def update_group(self, group_id: str, **fields) -> OrderItemGroupModel:
        group = self.get_group(group_id)
        if group is None:
            raise ValueError(f"Group '{group_id}' not found.")
        for key in ("name", "description"):
            if key in fields:
                setattr(group, key, fields[key])
        self.session.commit()
        return group

    def delete_group(self, group_id: str) -> None:
        group = self.get_group(group_id)
        if group is None:
            raise ValueError(f"Group '{group_id}' not found.")
        if group.items:
            raise GroupNotEmptyError("Cannot delete group with assigned items.")
        self.session.delete(group)
        self.session.commit()

    def reorder_groups(self, order_id: str, positions: list[dict]) -> None:
        for entry in positions:
            group = self.get_group(entry["group_id"])
            if group:
                group.position = entry["position"]
        self.session.commit()

    def assign_item_to_group(self, item_id: str, group_id: str | None) -> None:
        item = self.get_item_by_id(item_id)
        if item is None:
            raise self.ItemNotFoundError(f"Item '{item_id}' not found.")
        item.group_id = group_id
        self.session.commit()
