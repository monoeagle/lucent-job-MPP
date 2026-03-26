import pytest
import jwt
from app.services.auth_service import AuthService


class TestAuthServiceStub:
    def setup_method(self):
        self.service = AuthService(
            auth_mode="stub",
            jwt_secret="test-secret",
            token_ttl_seconds=3600,
        )

    def test_login_valid_user(self):
        result = self.service.login("test-requester", "stub-password")
        assert result["user"]["username"] == "test-requester"
        assert result["user"]["roles"] == ["requester"]
        assert "token" in result
        assert "expires_at" in result

    def test_login_without_password(self):
        result = self.service.login("test-requester", "")
        assert result["user"]["username"] == "test-requester"

    def test_login_with_none_password(self):
        result = self.service.login("test-requester", None)
        assert result["user"]["username"] == "test-requester"

    def test_login_unknown_user(self):
        with pytest.raises(AuthService.InvalidCredentialsError):
            self.service.login("unknown-user", "stub-password")

    def test_login_multi_role_user(self):
        result = self.service.login("test-multi", "stub-password")
        assert set(result["user"]["roles"]) == {"requester", "approver"}

    def test_token_contains_correct_claims(self):
        result = self.service.login("test-admin", "stub-password")
        decoded = jwt.decode(
            result["token"], "test-secret", algorithms=["HS256"]
        )
        assert decoded["sub"] == "test-admin"
        assert decoded["roles"] == ["admin"]
        assert decoded["email"] == "admin@test.local"
        assert decoded["display_name"] == "Test Admin"
        assert "iat" in decoded
        assert "exp" in decoded

    def test_verify_token_valid(self):
        result = self.service.login("test-requester", "stub-password")
        user = self.service.verify_token(result["token"])
        assert user.username == "test-requester"

    def test_verify_token_expired(self):
        service = AuthService(
            auth_mode="stub", jwt_secret="test-secret", token_ttl_seconds=-1
        )
        result = service.login("test-requester", "stub-password")
        with pytest.raises(AuthService.TokenExpiredError):
            service.verify_token(result["token"])

    def test_verify_token_invalid_signature(self):
        result = self.service.login("test-requester", "stub-password")
        with pytest.raises(AuthService.InvalidTokenError):
            wrong_secret_service = AuthService(
                auth_mode="stub", jwt_secret="wrong-secret", token_ttl_seconds=3600
            )
            wrong_secret_service.verify_token(result["token"])

    def test_get_stub_users(self):
        users = self.service.get_stub_users()
        assert len(users) == 4
        usernames = [u["username"] for u in users]
        assert "test-requester" in usernames
        assert "test-approver" in usernames
        assert "test-admin" in usernames
        assert "test-multi" in usernames
