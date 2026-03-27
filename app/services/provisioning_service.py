# app/services/provisioning_service.py
from app.domain.provisioning import ProvisioningStatus
from app.domain.order import OrderStatus

# GitLab pipeline status → internal provisioning status
_GITLAB_STATUS_MAP = {
    "pending": ProvisioningStatus.PENDING,
    "running": ProvisioningStatus.PROVISIONING,
    "success": ProvisioningStatus.DONE,
    "failed": ProvisioningStatus.FAILED,
}


class ProvisioningService:
    def __init__(self, order_repo, dispatch_log_repo, gitlab_client):
        self.order_repo = order_repo
        self.dispatch_log_repo = dispatch_log_repo
        self.gitlab_client = gitlab_client

    def dispatch_order(self, order_id: str):
        order = self.order_repo.get_by_id(order_id)
        for item in order.items:
            if item.provisioning_status == ProvisioningStatus.NOT_STARTED:
                self._dispatch_single_item(order_id, item)

    def dispatch_item(self, order_id: str, item_id: str):
        item = self.order_repo.get_item_by_id(item_id)
        if item.provisioning_status != ProvisioningStatus.NOT_STARTED:
            return
        self._dispatch_single_item(order_id, item)

    def _dispatch_single_item(self, order_id: str, item):
        variables = {f"TF_VAR_{k}": str(v) for k, v in item.parameters.items()}

        try:
            result = self.gitlab_client.trigger_pipeline(ref="main", variables=variables)
            pipeline_id = str(result["id"])

            item.job_id = pipeline_id
            item.provisioning_status = ProvisioningStatus.PENDING

            order = self.order_repo.get_by_id(order_id)
            if order.status != OrderStatus.PROVISIONING:
                self.order_repo.update_order_status(order_id, OrderStatus.PROVISIONING)

            self.dispatch_log_repo.create_log(
                order_id=order_id,
                order_item_id=item.id,
                job_id=pipeline_id,
                dispatch_method="gitlab_pipeline",
                status="success",
            )
        except Exception as e:
            self.dispatch_log_repo.create_log(
                order_id=order_id,
                order_item_id=item.id,
                job_id=None,
                dispatch_method="gitlab_pipeline",
                status="failed",
                error_message=str(e),
            )

    def sync_item_status(self, item_id: str):
        item = self.order_repo.get_item_by_id(item_id)
        result = self.gitlab_client.get_pipeline_status(int(item.job_id))
        new_status = _GITLAB_STATUS_MAP.get(result["status"], item.provisioning_status)
        item.provisioning_status = new_status
        self.update_order_aggregate_status(item.order_id)

    def handle_webhook(self, pipeline_id: int, status: str):
        item = self.order_repo.find_item_by_job_id(str(pipeline_id))
        new_status = _GITLAB_STATUS_MAP.get(status, item.provisioning_status)
        item.provisioning_status = new_status
        self.update_order_aggregate_status(item.order_id)

    def update_order_aggregate_status(self, order_id: str):
        order = self.order_repo.get_by_id(order_id)
        statuses = {item.provisioning_status for item in order.items}

        if statuses == {ProvisioningStatus.DONE}:
            self.order_repo.update_order_status(order_id, OrderStatus.DONE)
        elif ProvisioningStatus.FAILED in statuses:
            self.order_repo.update_order_status(order_id, OrderStatus.FAILED)
        # Mixed in-progress: no change
