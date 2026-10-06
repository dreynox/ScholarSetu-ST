"""
Student endpoints unit and security tests.
"""
from datetime import date
from unittest.mock import patch
from fastapi.testclient import TestClient
import jwt
from app.main import app
from app.models.student import Student
from app.schemas.student import StudentStatusResponse
from app.utils.errors import NotFoundException, ConflictException, ForbiddenException

client = TestClient(app)

STUDENT_A_AUTH_ID = "00000000-0000-0000-0000-000000000001"
STUDENT_B_AUTH_ID = "00000000-0000-0000-0000-000000000002"
TEST_SECRET = "super_secure_test_secret_key_32bytes_long!"


def generate_token(user_id: str, email: str = "student@example.com") -> str:
    """Generates a test JWT Bearer token for user_id."""
    payload = {"sub": user_id, "email": email}
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


# =====================================================================
# 1. Create Profile (POST /api/v1/students/me)
# =====================================================================

def test_create_profile_success():
    """Test creating student profile for authenticated user."""
    token = generate_token(STUDENT_A_AUTH_ID, "birsa.munda@example.com")

    with patch("app.services.student_service.student_service.create_student_profile") as mock_create:
        mock_create.return_value = Student(
            id="11111111-1111-1111-1111-111111111111",
            student_id="TRB-STU-100001",
            auth_user_id=STUDENT_A_AUTH_ID,
            otr_id="OTR-2026-0001",
            full_name="Birsa Munda",
            date_of_birth=date(2004, 11, 15),
            gender="Male",
            mobile_number="9876543210",
            email="birsa.munda@example.com",
            tribal_category="Munda (ST)",
            state="Jharkhand",
            district="Ranchi",
            is_active=True,
        )

        response = client.post(
            "/api/v1/students/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "full_name": "Birsa Munda",
                "date_of_birth": "2004-11-15",
                "gender": "Male",
                "mobile_number": "9876543210",
                "tribal_category": "Munda (ST)",
                "state": "Jharkhand",
                "district": "Ranchi",
                "otr_id": "OTR-2026-0001"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["student_id"] == "TRB-STU-100001"
        assert data["auth_user_id"] == STUDENT_A_AUTH_ID
        assert data["full_name"] == "Birsa Munda"


def test_create_profile_duplicate_conflict():
    """Test creating profile when one already exists for this account."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.student_service.student_service.create_student_profile") as mock_create:
        mock_create.side_effect = ConflictException(
            message="Student profile already exists for this account.",
            code="PROFILE_ALREADY_EXISTS"
        )

        response = client.post(
            "/api/v1/students/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "full_name": "Birsa Munda",
            }
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PROFILE_ALREADY_EXISTS"


# =====================================================================
# 2. Get Profile (GET /api/v1/students/me)
# =====================================================================

def test_get_my_profile_success():
    """Test retrieving authenticated student's profile."""
    token = generate_token(STUDENT_A_AUTH_ID, "birsa.munda@example.com")

    with patch("app.services.student_service.student_service.get_student_by_auth_user_id") as mock_get:
        mock_get.return_value = Student(
            id="11111111-1111-1111-1111-111111111111",
            student_id="TRB-STU-100001",
            auth_user_id=STUDENT_A_AUTH_ID,
            full_name="Birsa Munda",
            email="birsa.munda@example.com",
            tribal_category="Munda (ST)",
            state="Jharkhand",
            district="Ranchi",
            is_active=True,
        )

        response = client.get(
            "/api/v1/students/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["student_id"] == "TRB-STU-100001"
        assert data["auth_user_id"] == STUDENT_A_AUTH_ID


def test_get_my_profile_not_found():
    """Test retrieving profile when user has not yet created one."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.student_service.student_service.get_student_by_auth_user_id") as mock_get:
        mock_get.side_effect = NotFoundException(
            message="Student profile not found",
            code="STUDENT_NOT_FOUND"
        )

        response = client.get(
            "/api/v1/students/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "STUDENT_NOT_FOUND"


# =====================================================================
# 3. Update Profile (PUT /api/v1/students/me)
# =====================================================================

def test_update_my_profile_success():
    """Test updating student profile fields."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.student_service.student_service.update_student_profile") as mock_update:
        mock_update.return_value = Student(
            id="11111111-1111-1111-1111-111111111111",
            student_id="TRB-STU-100001",
            auth_user_id=STUDENT_A_AUTH_ID,
            full_name="Birsa Munda Updated",
            email="birsa.updated@example.com",
            mobile_number="9998887776",
            tribal_category="Munda (ST)",
            state="Jharkhand",
            district="Khunti",
            is_active=True,
        )

        response = client.put(
            "/api/v1/students/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "full_name": "Birsa Munda Updated",
                "mobile_number": "9998887776",
                "district": "Khunti"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Birsa Munda Updated"
        assert data["district"] == "Khunti"


# =====================================================================
# 4. Profile Status (GET /api/v1/students/me/status)
# =====================================================================

def test_profile_status_complete():
    """Test profile completeness check when complete."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.student_service.student_service.get_profile_status") as mock_status:
        mock_status.return_value = StudentStatusResponse(
            profile_exists=True,
            student_id="TRB-STU-100001",
            profile_complete=True,
            missing_fields=[]
        )

        response = client.get(
            "/api/v1/students/me/status",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["profile_exists"] is True
        assert data["profile_complete"] is True
        assert len(data["missing_fields"]) == 0


def test_profile_status_nonexistent():
    """Test profile status when profile has not been created."""
    token = generate_token("new-user-no-profile")

    with patch("app.services.student_service.student_service.get_profile_status") as mock_status:
        mock_status.return_value = StudentStatusResponse(
            profile_exists=False,
            student_id=None,
            profile_complete=False,
            missing_fields=["full_name", "date_of_birth", "gender", "tribal_category", "state", "district", "mobile_number"]
        )

        response = client.get(
            "/api/v1/students/me/status",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["profile_exists"] is False
        assert data["profile_complete"] is False


# =====================================================================
# 5. Security & Ownership Protection Tests (Section 11 & 12)
# =====================================================================

def test_student_cannot_access_other_student_profile():
    """
    CRITICAL SECURITY TEST:
    Student A (STUDENT_A_AUTH_ID) attempts to access Student B's profile.
    Must return 403 Forbidden.
    """
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.student_service.student_service.get_student_by_student_id") as mock_lookup:
        # Mock service enforcing ownership check
        mock_lookup.side_effect = ForbiddenException(
            message="Access denied: You are not authorized to view this profile.",
            code="FORBIDDEN"
        )

        response = client.get(
            "/api/v1/students/TRB-STU-999999",  # Student B's ID
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_student_can_access_own_profile_by_id():
    """Test that a student CAN access their own profile by their student_id."""
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.student_service.student_service.get_student_by_student_id") as mock_lookup:
        mock_lookup.return_value = Student(
            id="11111111-1111-1111-1111-111111111111",
            student_id="TRB-STU-100001",
            auth_user_id=STUDENT_A_AUTH_ID,
            full_name="Birsa Munda",
            email="birsa.munda@example.com",
            is_active=True,
        )

        response = client.get(
            "/api/v1/students/TRB-STU-100001",
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 200
        assert response.json()["student_id"] == "TRB-STU-100001"


def test_query_param_spoofing_prevented():
    """
    Test that sending `?student_id=spoofed_id` or `?auth_user_id=spoofed`
    on /students/me does NOT override the authenticated user's token identity.
    """
    token_a = generate_token(STUDENT_A_AUTH_ID, "birsa.munda@example.com")

    with patch("app.services.student_service.student_service.get_student_by_auth_user_id") as mock_get:
        mock_get.return_value = Student(
            id="11111111-1111-1111-1111-111111111111",
            student_id="TRB-STU-100001",
            auth_user_id=STUDENT_A_AUTH_ID,
            full_name="Birsa Munda",
            email="birsa.munda@example.com",
            is_active=True,
        )

        # Attempt to inject student_id or auth_user_id query param
        response = client.get(
            "/api/v1/students/me?student_id=TRB-STU-VICTIM&auth_user_id=other-uuid",
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 200
        # Verified that mock was called with Student A's authenticated auth_user_id only
        mock_get.assert_called_once_with(STUDENT_A_AUTH_ID)
        assert response.json()["auth_user_id"] == STUDENT_A_AUTH_ID


def test_unauthorized_student_access_without_token():
    """Test that all student endpoints reject unauthenticated requests."""
    endpoints = [
        ("GET", "/api/v1/students/me"),
        ("POST", "/api/v1/students/me"),
        ("PUT", "/api/v1/students/me"),
        ("GET", "/api/v1/students/me/status"),
        ("GET", "/api/v1/students/TRB-STU-000001"),
    ]

    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        elif method == "POST":
            res = client.post(path, json={"full_name": "Test"})
        elif method == "PUT":
            res = client.put(path, json={"full_name": "Test"})

        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"
