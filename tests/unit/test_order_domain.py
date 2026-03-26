from app.domain.order import OrderStatus, ItemValidationState


class TestOrderStatus:
    def test_status_values(self):
        assert OrderStatus.DRAFT == "draft"
        assert OrderStatus.VALIDATED == "validated"
        assert OrderStatus.SUBMITTED == "submitted"
        assert OrderStatus.PROVISIONING == "provisioning"
        assert OrderStatus.DONE == "done"
        assert OrderStatus.FAILED == "failed"

    def test_allowed_transitions(self):
        assert OrderStatus.can_transition("draft", "validated") is True
        assert OrderStatus.can_transition("validated", "submitted") is True
        assert OrderStatus.can_transition("validated", "draft") is True
        assert OrderStatus.can_transition("submitted", "provisioning") is True
        assert OrderStatus.can_transition("submitted", "pending_approval") is True
        assert OrderStatus.can_transition("pending_approval", "approved") is True
        assert OrderStatus.can_transition("pending_approval", "rejected") is True
        assert OrderStatus.can_transition("approved", "provisioning") is True
        assert OrderStatus.can_transition("provisioning", "done") is True
        assert OrderStatus.can_transition("provisioning", "failed") is True

    def test_forbidden_transitions(self):
        assert OrderStatus.can_transition("submitted", "draft") is False
        assert OrderStatus.can_transition("done", "draft") is False
        assert OrderStatus.can_transition("failed", "draft") is False
        assert OrderStatus.can_transition("rejected", "draft") is False
        assert OrderStatus.can_transition("done", "failed") is False

    def test_is_terminal(self):
        assert OrderStatus.is_terminal("done") is True
        assert OrderStatus.is_terminal("failed") is True
        assert OrderStatus.is_terminal("rejected") is True
        assert OrderStatus.is_terminal("draft") is False

    def test_is_editable(self):
        assert OrderStatus.is_editable("draft") is True
        assert OrderStatus.is_editable("validated") is False
        assert OrderStatus.is_editable("submitted") is False


class TestItemValidationState:
    def test_states(self):
        assert ItemValidationState.UNCHECKED == "unchecked"
        assert ItemValidationState.VALID == "valid"
        assert ItemValidationState.INVALID == "invalid"
