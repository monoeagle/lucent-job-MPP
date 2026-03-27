# app/data/repositories/dispatch_log_repository.py
import uuid
from sqlalchemy.orm import Session
from app.data.db.models.dispatch_log import DispatchLogModel


class DispatchLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_log(self, order_id: str, order_item_id: str, job_id: str | None,
                   dispatch_method: str, status: str,
                   error_message: str | None = None) -> DispatchLogModel:
        log = DispatchLogModel(
            id=str(uuid.uuid4()),
            order_id=order_id,
            order_item_id=order_item_id,
            job_id=job_id,
            dispatch_method=dispatch_method,
            status=status,
            error_message=error_message,
        )
        self.session.add(log)
        self.session.commit()
        return log

    def get_logs_for_order(self, order_id: str) -> list:
        return (self.session.query(DispatchLogModel)
                .filter_by(order_id=order_id)
                .order_by(DispatchLogModel.dispatched_at.desc())
                .all())

    def get_log_for_item(self, order_item_id: str) -> DispatchLogModel | None:
        return (self.session.query(DispatchLogModel)
                .filter_by(order_item_id=order_item_id)
                .order_by(DispatchLogModel.dispatched_at.desc())
                .first())
