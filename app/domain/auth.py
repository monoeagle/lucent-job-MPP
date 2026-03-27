from dataclasses import dataclass, field


class Role:
    REQUESTER = "requester"
    APPROVER = "approver"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


@dataclass(frozen=True)
class User:
    username: str
    display_name: str
    email: str
    roles: list[str] = field(default_factory=list)

    def has_role(self, role: str) -> bool:
        return role in self.roles

    @property
    def is_admin(self) -> bool:
        return self.has_role(Role.ADMIN) or self.has_role(Role.SUPERADMIN)

    @property
    def is_superadmin(self) -> bool:
        return self.has_role(Role.SUPERADMIN)

    def to_jwt_claims(self) -> dict:
        return {
            "sub": self.username,
            "roles": self.roles,
            "email": self.email,
            "display_name": self.display_name,
        }
