from app.domain.provisioning import ProvisioningStatus


class TestProvisioningStatus:
    def test_values(self):
        assert ProvisioningStatus.NOT_STARTED == "not_started"
        assert ProvisioningStatus.PENDING == "pending"
        assert ProvisioningStatus.PROVISIONING == "provisioning"
        assert ProvisioningStatus.DONE == "done"
        assert ProvisioningStatus.FAILED == "failed"

    def test_transitions(self):
        assert ProvisioningStatus.can_transition("not_started", "pending") is True
        assert ProvisioningStatus.can_transition("pending", "provisioning") is True
        assert ProvisioningStatus.can_transition("provisioning", "done") is True
        assert ProvisioningStatus.can_transition("provisioning", "failed") is True
        assert ProvisioningStatus.can_transition("done", "failed") is False
