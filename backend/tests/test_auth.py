"""
Authentication endpoint unit and integration tests.
"""
from unittest.mock import patch
from fastapi.testclient import TestClient
import jwt
from app.main import app
from app.schemas.auth import AuthResponse, UserResponse
from app.utils.errors import ConflictException, UnauthorizedException

client = TestClient(app)

# 32-byte secure test secret for JWT signing in unit tests
TEST_SECRET = "super_secure_test_secret_key_32bytes_long!"


def create_mock_jwt(user_id: str = "00000000-0000-0000-0000-000000000001", email: str = "test.student@example.com"):
    """Generates a test JWT payload."""
    payload = {
        "sub": user_id,
        "email": email,
        "user_metadata": {"full_name": "Test Tribal Scholar"},
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


# =====================================================================
# Registration Tests
# =====================================================================

def test_register_success():
    """Test successful user registration."""
    with patch("app.services.auth_service.auth_service.register") as mock_register:
        mock_register.return_value = AuthResponse(
            access_token="mock-jwt-token",
            token_type="bearer",
            expires_in=3600,
            refresh_token="mock-refresh-token",
            user=UserResponse(
                user_id="00000000-0000-0000-0000-000000000001",
                email="scholar@example.com",
                user_metadata={"full_name": "Tribal Scholar"}
            )
        )

        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "scholar@example.com",
                "password": "StrongPassword123!",
                "full_name": "Tribal Scholar"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "scholar@example.com"
        assert data["user"]["user_id"] == "00000000-0000-0000-0000-000000000001"
        assert data["access_token"] == "mock-jwt-token"


def test_register_duplicate_email():
    """Test registration failure on duplicate email."""
    with patch("app.services.auth_service.auth_service.register") as mock_register:
        mock_register.side_effect = ConflictException(
            message="An account with this email already exists.",
            code="EMAIL_ALREADY_EXISTS"
        )

        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "existing@example.com",
                "password": "StrongPassword123!",
                "full_name": "Existing User"
            }
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_register_invalid_payload():
    """Test validation failure on short password or missing email."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalid-email-format",
            "password": "123",  # Too short (min 6 required)
            "full_name": ""
        }
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# =====================================================================
# Login Tests
# =====================================================================

def test_login_success():
    """Test successful login."""
    with patch("app.services.auth_service.auth_service.login") as mock_login:
        mock_login.return_value = AuthResponse(
            access_token="mock-jwt-token-login",
            token_type="bearer",
            expires_in=3600,
            refresh_token="mock-refresh-token",
            user=UserResponse(
                user_id="00000000-0000-0000-0000-000000000001",
                email="scholar@example.com"
            )
        )

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "scholar@example.com",
                "password": "StrongPassword123!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "mock-jwt-token-login"
        assert data["user"]["email"] == "scholar@example.com"
        # Ensure passwords or internal keys are never returned
        assert "password" not in data
        assert "service_role" not in data


def test_login_invalid_credentials():
    """Test login failure with incorrect credentials."""
    with patch("app.services.auth_service.auth_service.login") as mock_login:
        mock_login.side_effect = UnauthorizedException(
            message="Invalid email or password.",
            code="INVALID_CREDENTIALS"
        )

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "scholar@example.com",
                "password": "WrongPassword"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "INVALID_CREDENTIALS"


# =====================================================================
# Current User (/auth/me) Tests
# =====================================================================

def test_auth_me_missing_token():
    """Test GET /api/v1/auth/me without authorization header."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_auth_me_invalid_header_format():
    """Test GET /api/v1/auth/me with malformed Authorization header."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "InvalidFormatToken123"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_AUTH_HEADER"


def test_auth_me_valid_token():
    """Test GET /api/v1/auth/me with valid Bearer token."""
    test_token = create_mock_jwt("user-uuid-1234", "test.user@example.com")
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user-uuid-1234"
    assert data["email"] == "test.user@example.com"
