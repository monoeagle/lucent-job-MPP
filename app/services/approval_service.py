from datetime import datetime, timezone, timedelta


class ApprovalService:
    class ConflictError(Exception):
        pass

    class SelfApprovalError(Exception):
        pass

    def __init__(self, approval_repo, order_repo, template_repo=None,
                 allow_self_approval=False, default_deadline_hours=48):
        self.approval_repo = approval_repo
        self.order_repo = order_repo
        self.template_repo = template_repo
        self.allow_self_approval = allow_self_approval
        self.default_deadline_hours = default_deadline_hours

    def evaluate_rules(self, order) -> list[str]:
        """Returns list of matching rule IDs. Empty = no approval needed."""
        rules = self.approval_repo.list_rules(is_active=True)
        matched = []

        # Resolve templates for all items
        templates = []
        for item in order.items:
            tpl = self.template_repo.get_by_slug(item.template_slug)
            if tpl:
                templates.append((item, tpl))

        total_cost = sum(
            float(tpl.estimated_cost_eur_per_month or 0)
            for _, tpl in templates
        )

        for rule in rules:
            if rule.rule_type == "always":
                matched.append(rule.id)
            elif rule.rule_type == "cost_threshold":
                if total_cost > float(rule.threshold_eur):
                    matched.append(rule.id)
            elif rule.rule_type == "service_type":
                slug = rule.service_type_slug
                for item, _tpl in templates:
                    if item.template_slug == slug or item.template_slug.startswith(slug + "/"):
                        matched.append(rule.id)
                        break

        # Check template-level approval_always_required flag
        for _item, tpl in templates:
            if tpl.approval_always_required:
                if "template_flag" not in matched:
                    matched.append("template_flag")
                break

        return matched

    def create_approval_request(self, order_id, rule_ids):
        """Creates ApprovalRequest with deadline."""
        deadline = datetime.now(timezone.utc) + timedelta(hours=self.default_deadline_hours)
        return self.approval_repo.create_request(order_id, rule_ids, deadline)

    def approve(self, request_id, approver_id, reason=None):
        """Approves request. Checks self-approval. Returns updated request."""
        request = self.approval_repo.get_request(request_id)
        order = self.order_repo.get_by_id(request.order_id)

        if not self.allow_self_approval and approver_id == order.requester_id:
            raise self.SelfApprovalError("Cannot approve your own order.")

        success = self.approval_repo.decide_request(request_id, "approved", approver_id, reason)
        if not success:
            raise self.ConflictError("Request has already been decided.")

        return self.approval_repo.get_request(request_id)

    def reject(self, request_id, approver_id, reason):
        """Rejects request. Reason is required. Returns updated request."""
        if not reason:
            raise ValueError("A reason is required to reject an approval request.")

        request = self.approval_repo.get_request(request_id)
        order = self.order_repo.get_by_id(request.order_id)

        success = self.approval_repo.decide_request(request_id, "rejected", approver_id, reason)
        if not success:
            raise self.ConflictError("Request has already been decided.")

        return self.approval_repo.get_request(request_id)

    def process_timeouts(self):
        """Finds expired pending requests, rejects them with system message."""
        now = datetime.now(timezone.utc)
        expired = self.approval_repo.list_expired_requests(now)
        for req in expired:
            self.approval_repo.decide_request(
                req.id, "rejected", "system",
                "Automatically rejected: approval deadline exceeded.",
            )
