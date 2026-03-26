import os
import logging

logger = logging.getLogger(__name__)

VALID_AUTH_MODES = ("stub", "ldap")


class Config:
    def __init__(self):
        self.AUTH_MODE = os.environ.get("AUTH_MODE", "ldap")
        self.ENV = os.environ.get("ENV", "development")
        self.JWT_SECRET = os.environ.get("JWT_SECRET", "")
        self.STUB_TOKEN_TTL_SECONDS = int(
            os.environ.get("STUB_TOKEN_TTL_SECONDS", "86400")
        )
        self.DATABASE_URL = os.environ.get(
            "DATABASE_URL", "postgresql://mpp:mpp@localhost:5432/mpp_dev"
        )
        self.TEST_DATABASE_URL = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql://mpp:mpp@localhost:5432/mpp_test",
        )

        self._validate()

    def _validate(self):
        if self.AUTH_MODE not in VALID_AUTH_MODES:
            raise ValueError(
                f"Unknown AUTH_MODE value: {self.AUTH_MODE}. "
                f"Allowed: {', '.join(VALID_AUTH_MODES)}"
            )

        if self.AUTH_MODE == "stub" and self.ENV == "production":
            raise RuntimeError(
                "FATAL: AUTH_MODE=stub must not be used in production environment. "
                "Aborting."
            )

        if self.AUTH_MODE == "stub" and not self.JWT_SECRET:
            self.JWT_SECRET = "stub-jwt-secret-dev-only"
            logger.warning(
                "JWT_SECRET not set in stub mode. Using fallback secret. "
                "Never use this in production."
            )


def get_config() -> Config:
    return Config()
