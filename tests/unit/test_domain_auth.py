from app.domain.auth import User, Role


class TestRole:
    def test_role_values(self):
        assert Role.REQUESTER == "requester"
        assert Role.APPROVER == "approver"
        assert Role.ADMIN == "admin"


class TestUser:
    def test_create_user(self):
        user = User(
            username="test-requester",
            display_name="Test Requester",
            email="requester@test.local",
            roles=[Role.REQUESTER],
        )
        assert user.username == "test-requester"
        assert user.roles == ["requester"]

    def test_user_has_role(self):
        user = User(
            username="test-multi",
            display_name="Test Multi",
            email="multi@test.local",
            roles=[Role.REQUESTER, Role.APPROVER],
        )
        assert user.has_role(Role.REQUESTER) is True
        assert user.has_role(Role.ADMIN) is False

    def test_user_is_admin(self):
        admin = User(
            username="test-admin",
            display_name="Test Admin",
            email="admin@test.local",
            roles=[Role.ADMIN],
        )
        assert admin.is_admin is True

    def test_user_to_jwt_claims(self):
        user = User(
            username="test-requester",
            display_name="Test Requester",
            email="requester@test.local",
            roles=[Role.REQUESTER],
        )
        claims = user.to_jwt_claims()
        assert claims["sub"] == "test-requester"
        assert claims["roles"] == ["requester"]
        assert claims["email"] == "requester@test.local"
        assert claims["display_name"] == "Test Requester"
