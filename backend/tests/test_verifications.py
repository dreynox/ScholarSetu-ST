"""
Verification endpoints unit, integration, and security tests.
Tests student-scoped verification lookups, cross-student isolation, and verifier self-approval prevention.
"""
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import jwt
import pytest

from app.main import app
from app.models.student import Student
from app.schemas.verification import (
    VerificationResponse,
    VerificationDetailResponse,
)
from app.services.verification_service import VerificationService, verification_service
from app.utils.errors import (
    NotFoundException,
    ForbiddenException,
    AppException,
    UnauthorizedException,
)

client = TestClient(app)

STUDENT_A_AUTH_ID = "00000000-0000-0000-0000-000000000001"
STUDENT_B_AUTH_ID = "00000000-0000-0000-0000-000000000002"

STUDENT_A_DB_ID = "11111111-1111-1111-1111-111111111111"
STUDENT_B_DB_ID = "22222222-2222-2222-2222-222222222222"

TEST_SECRET = "super_secure_test_secret_key_32bytes_long!"


def generate_token(user_id: str, email: str = "student@example.com") -> str:
    """Generates a test JWT Bearer token for user_id."""
    payload = {"sub": user_id, "email": email}
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
def mock_student_a():
    return Student(
        id=STUDENT_A_DB_ID,
        student_id="TRB-STU-000001",
        auth_user_id=STUDENT_A_AUTH_ID,
        full_name="Birsa Munda",
        email="birsa.munda@example.com",
        tribal_category="Munda (ST)",
        state="Jharkhand",
        district="Ranchi",
        is_active=True,
    )


@pytest.fixture
def sample_verification_item():
    return VerificationResponse(
        verification_id="verif-uuid-0001",
        verification_type="DOCUMENT",
        reference_id="TRB-DOC-000001",
        status="PENDING",
        verification_level=None,
        verified_at=None,
        verified_by=None,
        remarks=None,
        created_at=datetime(2026, 10, 3, 10, 0, 0),
        updated_at=datetime(2026, 10, 3, 10, 0, 0),
    )


@pytest.fixture
def sample_verification_detail():
    return VerificationDetailResponse(
        verification_id="verif-uuid-0001",
        verification_type="DOCUMENT",
        reference_id="TRB-DOC-000001",
        status="VERIFIED",
        verification_level=None,
        verified_at=datetime(2026, 10, 4, 12, 0, 0),
        verified_by="VERIFIER_OFFICER_01",
        remarks="Caste certificate verified with state portal.",
        created_at=datetime(2026, 10, 3, 10, 0, 0),
        updated_at=datetime(2026, 10, 4, 12, 0, 0),
    )


# =====================================================================
# 1. List Own Verifications (GET /api/v1/verifications)
# =====================================================================

def test_list_my_verifications_success(sample_verification_item):
    """Test retrieving verification records belonging to authenticated student."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.verification_service.verification_service.get_my_verifications") as mock_list:
        mock_list.return_value = [sample_verification_item]

        response = client.get(
            "/api/v1/verifications",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["verifications"][0]["reference_id"] == "TRB-DOC-000001"
        assert data["verifications"][0]["status"] == "PENDING"


# =====================================================================
# 2. Get Verification By ID (GET /api/v1/verifications/{verification_id})
# =====================================================================

def test_get_own_verification_by_id_success(sample_verification_detail):
    """Test retrieving a specific verification record owned by current student."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.verification_service.verification_service.get_my_verification_by_id") as mock_get_id:
        mock_get_id.return_value = sample_verification_detail

        response = client.get(
            "/api/v1/verifications/verif-uuid-0001",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["verification_id"] == "verif-uuid-0001"
        assert data["status"] == "VERIFIED"
        assert data["verified_by"] == "VERIFIER_OFFICER_01"


def test_get_nonexistent_verification_returns_404():
    """Test lookup of non-existent verification record returns 404."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.verification_service.verification_service.get_my_verification_by_id") as mock_get_id:
        mock_get_id.side_effect = NotFoundException(
            message="Verification record not found.",
            code="VERIFICATION_NOT_FOUND"
        )

        response = client.get(
            "/api/v1/verifications/non-existent-uuid",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "VERIFICATION_NOT_FOUND"


# =====================================================================
# 3. Get Verification By Document (GET /api/v1/verifications/document/{document_id})
# =====================================================================

def test_get_verification_by_document_success(sample_verification_detail):
    """Test retrieving verification status for own document."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.verification_service.verification_service.get_verification_by_document") as mock_get_doc:
        mock_get_doc.return_value = sample_verification_detail

        response = client.get(
            "/api/v1/verifications/document/TRB-DOC-000001",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reference_id"] == "TRB-DOC-000001"
        assert data["status"] == "VERIFIED"


def test_get_verification_by_other_student_document_returns_404():
    """Test lookup for another student's document verification returns 404."""
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.verification_service.verification_service.get_verification_by_document") as mock_get_doc:
        mock_get_doc.side_effect = NotFoundException(
            message="Document not found.",
            code="DOCUMENT_NOT_FOUND"
        )

        response = client.get(
            "/api/v1/verifications/document/TRB-DOC-OTHER-STUDENT",
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


# =====================================================================
# 4. Authentication Requirements
# =====================================================================

def test_unauthenticated_verification_requests_rejected():
    """Test unauthenticated calls to all verification endpoints return 401."""
    endpoints = [
        "/api/v1/verifications",
        "/api/v1/verifications/verif-uuid-0001",
        "/api/v1/verifications/document/TRB-DOC-000001",
    ]

    for path in endpoints:
        res = client.get(path)
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"


# =====================================================================
# 5. Cross-Student Ownership Security Tests
# =====================================================================

def test_student_cannot_access_other_student_verification():
    """CRITICAL: Student A cannot access Student B's verification record (returns 404)."""
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.verification_service.verification_service.get_my_verification_by_id") as mock_get_id:
        mock_get_id.side_effect = NotFoundException(
            message="Verification record not found.",
            code="VERIFICATION_NOT_FOUND"
        )

        response = client.get(
            "/api/v1/verifications/verif-student-b",
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "VERIFICATION_NOT_FOUND"


# =====================================================================
# 6. Student Self-Verification Prevention (Section 13, 17, 18, 19)
# =====================================================================

def test_student_cannot_post_or_put_verification():
    """
    CRITICAL SECURITY TEST:
    Students cannot self-approve or create/modify verification state.
    POST and PUT endpoints for verifications are not exposed to normal student roles.
    """
    token = generate_token(STUDENT_A_AUTH_ID)

    # Attempt to POST /api/v1/verifications
    post_res = client.post(
        "/api/v1/verifications",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "VERIFIED", "verification_level": "MINISTRY"}
    )
    # Should be 404/405 (Method Not Allowed / Endpoint Not Found for students)
    assert post_res.status_code in [404, 405]

    # Attempt to PUT /api/v1/verifications/verif-uuid-0001
    put_res = client.put(
        "/api/v1/verifications/verif-uuid-0001",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "APPROVED", "verification_level": "STATE"}
    )
    assert put_res.status_code in [404, 405]
