import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.data.db.models.approval import ApprovalRuleModel, ApprovalRequestModel


class ApprovalRepository:
    class RuleInUseError(Exception):
        pass

    def __init__(self, session: Session):
        self.session = session

    # ── Rules ─────────────────────────────────────────────────────

    def create_rule(self, name: str, rule_type: str,
                    threshold_eur=None, service_type_slug=None,
                    is_active: bool = True) -> ApprovalRuleModel:
        rule = ApprovalRuleModel(
            id=str(uuid.uuid4()),
            name=name,
            rule_type=rule_type,
            threshold_eur=threshold_eur,
            service_type_slug=service_type_slug,
            is_active=is_active,
        )
        self.session.add(rule)
        self.session.commit()
        return rule

    def list_rules(self, is_active=None) -> list[ApprovalRuleModel]:
        q = self.session.query(ApprovalRuleModel)
        if is_active is not None:
            q = q.filter_by(is_active=is_active)
        return q.all()

    def get_rule(self, rule_id: str) -> ApprovalRuleModel | None:
        return self.session.query(ApprovalRuleModel).filter_by(id=rule_id).first()

    def update_rule(self, rule_id: str, **fields) -> ApprovalRuleModel:
        rule = self.get_rule(rule_id)
        for key in ("name", "rule_type", "threshold_eur", "service_type_slug", "is_active"):
            if key in fields:
                setattr(rule, key, fields[key])
        self.session.commit()
        return rule

    def delete_rule(self, rule_id: str) -> None:
        pending = (
            self.session.query(ApprovalRequestModel)
            .filter(ApprovalRequestModel.status == "pending")
            .all()
        )
        for req in pending:
            if rule_id in (req.approval_rule_ids or []):
                raise self.RuleInUseError(
                    f"Cannot delete rule '{rule_id}': referenced by pending request '{req.id}'."
                )
        rule = self.get_rule(rule_id)
        if rule:
            self.session.delete(rule)
            self.session.commit()

    # ── Requests ──────────────────────────────────────────────────

    def create_request(self, order_id: str, approval_rule_ids: list[str],
                       deadline_at) -> ApprovalRequestModel:
        now = datetime.now(timezone.utc)
        request = ApprovalRequestModel(
            id=str(uuid.uuid4()),
            order_id=order_id,
            status="pending",
            approval_rule_ids=approval_rule_ids,
            requested_at=now,
            deadline_at=deadline_at,
        )
        self.session.add(request)
        self.session.commit()
        return request

    def get_request(self, request_id: str) -> ApprovalRequestModel | None:
        return self.session.query(ApprovalRequestModel).filter_by(id=request_id).first()

    def get_request_for_order(self, order_id: str) -> ApprovalRequestModel | None:
        return (
            self.session.query(ApprovalRequestModel)
            .filter_by(order_id=order_id)
            .first()
        )

    def list_pending_requests(self) -> list[ApprovalRequestModel]:
        return (
            self.session.query(ApprovalRequestModel)
            .filter_by(status="pending")
            .all()
        )

    def list_expired_requests(self, now) -> list[ApprovalRequestModel]:
        return (
            self.session.query(ApprovalRequestModel)
            .filter(
                ApprovalRequestModel.status == "pending",
                ApprovalRequestModel.deadline_at < now,
            )
            .all()
        )

    def decide_request(self, request_id: str, status: str,
                       decided_by: str, decision_reason: str) -> bool:
        """Atomic decision: UPDATE WHERE status='pending'. Returns False if already decided."""
        count = (
            self.session.query(ApprovalRequestModel)
            .filter(
                ApprovalRequestModel.id == request_id,
                ApprovalRequestModel.status == "pending",
            )
            .update({
                "status": status,
                "decided_by": decided_by,
                "decided_at": datetime.now(timezone.utc),
                "decision_reason": decision_reason,
            })
        )
        self.session.commit()
        return count > 0
