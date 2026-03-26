class OrderStatus:
    DRAFT = "draft"
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROVISIONING = "provisioning"
    DONE = "done"
    FAILED = "failed"

    _TRANSITIONS = {
        "draft": {"validated"},
        "validated": {"submitted", "draft"},
        "submitted": {"provisioning", "pending_approval"},
        "pending_approval": {"approved", "rejected"},
        "approved": {"provisioning"},
        "provisioning": {"done", "failed"},
        "done": set(),
        "failed": set(),
        "rejected": set(),
    }

    _TERMINAL = {"done", "failed", "rejected"}

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        return to_status in cls._TRANSITIONS.get(from_status, set())

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        return status in cls._TERMINAL

    @classmethod
    def is_editable(cls, status: str) -> bool:
        return status == cls.DRAFT


class ItemValidationState:
    UNCHECKED = "unchecked"
    VALID = "valid"
    INVALID = "invalid"
