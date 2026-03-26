import uuid

from sqlalchemy.orm import Session

from app.data.db.models.context_rule import AvailabilityRuleModel, ContextRestrictionModel


class ContextRuleRepository:

    def __init__(self, session: Session):
        self.session = session

    # --- Availability Rules ---

    def create_availability_rule(self, name: str, template_slug: str,
                                 rule_type: str, conditions: dict,
                                 priority: int = 0) -> AvailabilityRuleModel:
        rule = AvailabilityRuleModel(
            id=str(uuid.uuid4()),
            name=name,
            template_slug=template_slug,
            rule_type=rule_type,
            conditions=conditions,
            priority=priority,
        )
        self.session.add(rule)
        self.session.commit()
        return rule

    def list_availability_rules(self, template_slug: str | None = None,
                                is_active: bool | None = None) -> list[AvailabilityRuleModel]:
        q = self.session.query(AvailabilityRuleModel)
        if template_slug is not None:
            q = q.filter_by(template_slug=template_slug)
        if is_active is not None:
            q = q.filter_by(is_active=is_active)
        return q.order_by(AvailabilityRuleModel.priority.desc()).all()

    def get_availability_rule(self, rule_id: str) -> AvailabilityRuleModel | None:
        return self.session.query(AvailabilityRuleModel).filter_by(id=rule_id).first()

    def update_availability_rule(self, rule_id: str, **fields) -> AvailabilityRuleModel | None:
        rule = self.get_availability_rule(rule_id)
        if rule is None:
            return None
        for key, value in fields.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        self.session.commit()
        return rule

    def delete_availability_rule(self, rule_id: str) -> bool:
        rule = self.get_availability_rule(rule_id)
        if rule is None:
            return False
        self.session.delete(rule)
        self.session.commit()
        return True

    def check_availability(self, template_slug: str, context: dict) -> dict:
        rules = self.session.query(AvailabilityRuleModel).filter_by(
            template_slug=template_slug, is_active=True,
        ).order_by(AvailabilityRuleModel.priority.desc()).all()

        for rule in rules:
            if self._conditions_match(rule.conditions, context):
                return {
                    "available": rule.rule_type == "allow",
                    "matching_rule": self._rule_to_dict(rule),
                }
        # No matching rule → available by default
        return {"available": True, "matching_rule": None}

    # --- Context Restrictions ---

    def create_restriction(self, name: str, template_slug: str | None,
                           parameter_key: str, restriction_type: str,
                           conditions: dict, effect: dict,
                           priority: int = 0) -> ContextRestrictionModel:
        restriction = ContextRestrictionModel(
            id=str(uuid.uuid4()),
            name=name,
            template_slug=template_slug,
            parameter_key=parameter_key,
            restriction_type=restriction_type,
            conditions=conditions,
            effect=effect,
            priority=priority,
        )
        self.session.add(restriction)
        self.session.commit()
        return restriction

    def list_restrictions(self, template_slug: str | None = None,
                          is_active: bool | None = None) -> list[ContextRestrictionModel]:
        q = self.session.query(ContextRestrictionModel)
        if template_slug is not None:
            q = q.filter_by(template_slug=template_slug)
        if is_active is not None:
            q = q.filter_by(is_active=is_active)
        return q.order_by(ContextRestrictionModel.priority.desc()).all()

    def get_restriction(self, restriction_id: str) -> ContextRestrictionModel | None:
        return self.session.query(ContextRestrictionModel).filter_by(id=restriction_id).first()

    def update_restriction(self, restriction_id: str, **fields) -> ContextRestrictionModel | None:
        restriction = self.get_restriction(restriction_id)
        if restriction is None:
            return None
        for key, value in fields.items():
            if hasattr(restriction, key):
                setattr(restriction, key, value)
        self.session.commit()
        return restriction

    def delete_restriction(self, restriction_id: str) -> bool:
        restriction = self.get_restriction(restriction_id)
        if restriction is None:
            return False
        self.session.delete(restriction)
        self.session.commit()
        return True

    def get_restrictions_for_context(self, template_slug: str,
                                     parameter_key: str,
                                     context: dict) -> list[ContextRestrictionModel]:
        # Match restrictions for the specific template or global (null template_slug)
        from sqlalchemy import or_
        restrictions = self.session.query(ContextRestrictionModel).filter(
            or_(
                ContextRestrictionModel.template_slug == template_slug,
                ContextRestrictionModel.template_slug.is_(None),
            ),
            ContextRestrictionModel.parameter_key == parameter_key,
            ContextRestrictionModel.is_active == True,
        ).order_by(ContextRestrictionModel.priority.desc()).all()

        return [r for r in restrictions if self._conditions_match(r.conditions, context)]

    # --- Helpers ---

    @staticmethod
    def _conditions_match(conditions: dict, context: dict) -> bool:
        for key, value in conditions.items():
            if context.get(key) != value:
                return False
        return True

    @staticmethod
    def _rule_to_dict(rule: AvailabilityRuleModel) -> dict:
        return {
            "id": rule.id,
            "name": rule.name,
            "template_slug": rule.template_slug,
            "rule_type": rule.rule_type,
            "conditions": rule.conditions,
            "priority": rule.priority,
            "is_active": rule.is_active,
        }

    @staticmethod
    def _restriction_to_dict(restriction: ContextRestrictionModel) -> dict:
        return {
            "id": restriction.id,
            "name": restriction.name,
            "template_slug": restriction.template_slug,
            "parameter_key": restriction.parameter_key,
            "restriction_type": restriction.restriction_type,
            "conditions": restriction.conditions,
            "effect": restriction.effect,
            "priority": restriction.priority,
            "is_active": restriction.is_active,
        }
