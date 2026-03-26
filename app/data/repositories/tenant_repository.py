import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.data.db.models.context_rule import UserTenantAssignmentModel


class TenantRepository:

    class DuplicateAssignmentError(Exception):
        pass

    def __init__(self, session: Session):
        self.session = session

    def assign_tenant(self, user_id: str, tenant_id: str) -> UserTenantAssignmentModel:
        assignment = UserTenantAssignmentModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
        )
        self.session.add(assignment)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise self.DuplicateAssignmentError(
                f"User '{user_id}' is already assigned to tenant '{tenant_id}'."
            )
        return assignment

    def list_assignments(self, user_id: str | None = None) -> list[UserTenantAssignmentModel]:
        q = self.session.query(UserTenantAssignmentModel)
        if user_id is not None:
            q = q.filter_by(user_id=user_id)
        return q.all()

    def get_assignment(self, assignment_id: str) -> UserTenantAssignmentModel | None:
        return self.session.query(UserTenantAssignmentModel).filter_by(id=assignment_id).first()

    def delete_assignment(self, assignment_id: str) -> bool:
        assignment = self.get_assignment(assignment_id)
        if assignment is None:
            return False
        self.session.delete(assignment)
        self.session.commit()
        return True

    def get_user_tenant_ids(self, user_id: str) -> list[str]:
        assignments = self.session.query(UserTenantAssignmentModel).filter_by(
            user_id=user_id
        ).all()
        return [a.tenant_id for a in assignments]

    def get_allowed_tenant_ids(self, user_id: str) -> list[str] | None:
        """Returns list of allowed tenant IDs, or None if no assignments (= all allowed)."""
        try:
            ids = self.get_user_tenant_ids(user_id)
        except Exception:
            self.session.rollback()
            return None
        return ids if ids else None
