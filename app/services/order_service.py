# app/services/order_service.py
from app.domain.order import OrderStatus, ItemValidationState
from app.domain.catalog import DependencyRule


class OrderService:
    def __init__(self, order_repo, template_repo, catalog_service,
                 context_service=None):
        self.order_repo = order_repo
        self.template_repo = template_repo
        self.catalog_service = catalog_service
        self.context_service = context_service

    # ── helpers ──────────────────────────────────────────────────

    def _get_order_for_requester(self, order_id: str, requester_id: str):
        order = self.order_repo.get_by_id(order_id)
        if order is None:
            raise ValueError(f"Order '{order_id}' not found.")
        if order.requester_id != requester_id:
            raise PermissionError("No permission to access this order.")
        return order

    @staticmethod
    def _assert_editable(order, allow_validated=False):
        allowed = {OrderStatus.DRAFT}
        if allow_validated:
            allowed.add(OrderStatus.VALIDATED)
        if order.status not in allowed:
            raise ValueError("Order must be in draft status to perform this action.")

    # ── public API ───────────────────────────────────────────────

    def create_order(self, requester_id: str, title: str,
                     business_reason: str | None = None,
                     desired_date: str | None = None,
                     context: dict | None = None) -> dict:
        stripped = title.strip() if title else ""
        if len(stripped) < 3 or len(stripped) > 100:
            raise ValueError("Order title must be between 3 and 100 characters.")

        if context and self.context_service:
            from app.services.context_service import ContextService
            try:
                self.context_service.resolve_context(
                    location_id=context.get("location_id", ""),
                    tenant_id=context.get("tenant_id", ""),
                    security_zone_id=context.get("security_zone_id", ""),
                    network_id=context.get("network_id"),
                    user_id=requester_id,
                )
            except ContextService.ContextValidationError:
                raise
            except ContextService.CmdbUnavailableError:
                raise

        kwargs = {}
        if context is not None:
            kwargs["context"] = context
        order = self.order_repo.create_order(
            requester_id, title, business_reason, desired_date, **kwargs,
        )
        return {"order": order}

    def add_item(self, order_id: str, requester_id: str,
                 template_slug: str, template_version: str,
                 parameters: dict, quantity: int = 1,
                 instance_parameters: list | None = None) -> dict:
        order = self._get_order_for_requester(order_id, requester_id)
        self._assert_editable(order)

        template = self.template_repo.get_by_slug_and_version(template_slug, template_version)
        if template is None:
            raise ValueError(f"Service template '{template_slug}@{template_version}' not found.")
        if template.status == "disabled":
            raise ValueError(f"Template '{template_slug}' is disabled and cannot be ordered.")

        warning = None
        if template.status == "deprecated":
            warning = f"Template '{template_slug}' is deprecated. Consider using a newer version."

        item = self.order_repo.add_item(
            order_id, template_slug, template_version, template.display_name, parameters,
            quantity=quantity, instance_parameters=instance_parameters or [],
        )
        return {"item": item, "warning": warning}

    def update_item(self, order_id: str, item_id: str,
                    requester_id: str, parameters: dict) -> dict:
        order = self._get_order_for_requester(order_id, requester_id)
        self._assert_editable(order, allow_validated=True)

        item = self.order_repo.update_item_parameters(item_id, parameters)

        if order.status == OrderStatus.VALIDATED:
            self.order_repo.update_order_status(order_id, OrderStatus.DRAFT)

        return {"item": item}

    def remove_item(self, order_id: str, item_id: str, requester_id: str) -> None:
        order = self._get_order_for_requester(order_id, requester_id)
        self._assert_editable(order)
        self.order_repo.remove_item(item_id)

    def validate_order(self, order_id: str, requester_id: str) -> dict:
        order = self._get_order_for_requester(order_id, requester_id)
        self._assert_editable(order, allow_validated=True)

        if not order.items:
            raise ValueError("Order must have at least one items to validate.")

        all_valid = True
        item_results = []

        for item in order.items:
            template = self.template_repo.get_by_slug_and_version(
                item.template_slug, item.template_version,
            )

            # Validate shared parameters
            shared_params = [p for p in template.parameters
                            if not p.get("per_instance")]
            violations = self.catalog_service.validate_parameters(
                shared_params, item.parameters, template.cross_parameter_rules,
            )

            # For quantity > 1, validate per-instance parameters for each instance
            quantity = getattr(item, "quantity", 1) or 1
            instance_params_list = getattr(item, "instance_parameters", []) or []
            per_instance_defs = [p for p in template.parameters
                                if p.get("per_instance") is True]

            if quantity > 1 and per_instance_defs:
                for inst_params in instance_params_list:
                    inst_violations = self.catalog_service.validate_parameters(
                        per_instance_defs, inst_params, [],
                    )
                    violations.extend(inst_violations)

            if violations:
                state = ItemValidationState.INVALID
                all_valid = False
            else:
                state = ItemValidationState.VALID

            self.order_repo.update_item_validation(item.id, state, violations)
            item_results.append({
                "item_id": item.id,
                "validation_state": state,
                "violations": violations,
            })

        if all_valid:
            self.order_repo.update_order_status(order_id, OrderStatus.VALIDATED)

        return {
            "status": OrderStatus.VALIDATED if all_valid else OrderStatus.DRAFT,
            "items": item_results,
        }

    def submit_order(self, order_id: str, requester_id: str) -> dict:
        order = self._get_order_for_requester(order_id, requester_id)
        if order.status != OrderStatus.VALIDATED:
            raise ValueError("Order must be validated before submission.")
        if not order.business_reason or not order.business_reason.strip():
            raise ValueError("A business_reason is required to submit an order.")

        updated = self.order_repo.update_order_status(order_id, OrderStatus.SUBMITTED)
        return {"order": updated}

    def export_tofu(self, order_id: str, requester_id: str) -> dict:
        order = self._get_order_for_requester(order_id, requester_id)
        if order.status == OrderStatus.DRAFT:
            raise ValueError("Cannot export a draft order.")

        exported_items = []
        for item in order.items:
            template = self.template_repo.get_by_slug_and_version(
                item.template_slug, item.template_version,
            )

            # Build shared variables (non per-instance params)
            shared_variables = {}
            per_instance_defs = []
            for p in template.parameters:
                if p.get("per_instance"):
                    per_instance_defs.append(p)
                    continue

                depends_on = p.get("depends_on", [])
                if depends_on:
                    dep_state = self.catalog_service.resolve_dependency_state(
                        depends_on, item.parameters,
                    )
                    if not dep_state["is_visible"]:
                        continue

                key = p["key"]
                if key in item.parameters:
                    shared_variables[p["tofu_variable_name"]] = item.parameters[key]

            quantity = getattr(item, "quantity", 1) or 1
            instance_params_list = getattr(item, "instance_parameters", []) or []

            if quantity > 1 and instance_params_list:
                for inst_params in instance_params_list:
                    variables = dict(shared_variables)
                    for p in per_instance_defs:
                        key = p["key"]
                        if key in inst_params:
                            variables[p["tofu_variable_name"]] = inst_params[key]
                    exported_items.append({
                        "template_slug": item.template_slug,
                        "template_version": item.template_version,
                        "module_source": template.tofu_module_source,
                        "variables": variables,
                    })
            else:
                exported_items.append({
                    "template_slug": item.template_slug,
                    "template_version": item.template_version,
                    "module_source": template.tofu_module_source,
                    "variables": shared_variables,
                })

        return {"order_id": order_id, "items": exported_items}

    # ── Group management ──────────────────────────────────────────

    def create_group(self, order_id: str, requester_id: str,
                     name: str, description: str | None = None) -> dict:
        order = self._get_order_for_requester(order_id, requester_id)
        self._assert_editable(order)
        group = self.order_repo.create_group(order_id, name, description)
        return {"group": group}

    def update_group(self, order_id: str, group_id: str,
                     requester_id: str, **fields) -> dict:
        order = self._get_order_for_requester(order_id, requester_id)
        self._assert_editable(order)
        group = self.order_repo.update_group(group_id, **fields)
        return {"group": group}

    def delete_group(self, order_id: str, group_id: str,
                     requester_id: str) -> None:
        order = self._get_order_for_requester(order_id, requester_id)
        self._assert_editable(order)
        self.order_repo.delete_group(group_id)

    def assign_item_to_group(self, order_id: str, item_id: str,
                             requester_id: str, group_id: str | None) -> None:
        order = self._get_order_for_requester(order_id, requester_id)
        self._assert_editable(order)

        item = self.order_repo.get_item_by_id(item_id)
        if item is None:
            raise ValueError(f"Item '{item_id}' not found.")

        if group_id is not None:
            group = self.order_repo.get_group(group_id)
            if group is None:
                raise ValueError(f"Group '{group_id}' not found.")
            if group.order_id != order_id:
                raise ValueError("Group does not belong to the same order.")

        self.order_repo.assign_item_to_group(item_id, group_id)
