class ProvisioningStatus:
    NOT_STARTED = "not_started"
    PENDING = "pending"
    PROVISIONING = "provisioning"
    DONE = "done"
    FAILED = "failed"

    _TRANSITIONS = {
        "not_started": {"pending"},
        "pending": {"provisioning", "failed"},
        "provisioning": {"done", "failed"},
        "done": set(),
        "failed": set(),
    }

    @classmethod
    def can_transition(cls, from_s: str, to_s: str) -> bool:
        return to_s in cls._TRANSITIONS.get(from_s, set())
