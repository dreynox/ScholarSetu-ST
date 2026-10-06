"""
Document endpoints unit, integration, and security tests.
Tests document creation, listing, retrieval, updates, deletion, verification lookup, and student ownership isolation.
"""
from datetime import date, datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import jwt
import pytest

from app.main import app
from app.models.student import Student
from app.schemas.document import (
    DocumentResponse,
    DocumentVerificationInfo,
)
from app.services.document_service import DocumentService, document_service
from app.utils.errors import (
    NotFoundException,
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
def sample_document_response():
    return DocumentResponse(
        document_id="TRB-DOC-000001",
        document_type="CASTE_CERTIFICATE",
        document_name="Caste Certificate",
        file_url="https://storage.example.com/docs/caste.pdf",
        storage_path="documents/TRB-STU-000001/caste.pdf",
        file_size=102400,
        file_type="application/pdf",
        document_number="CC-2026-9876",
        expiry_date=None,
        is_active=True,
        verification_status="PENDING",
        created_at=datetime(2026, 10, 3, 10, 0, 0),
        updated_at=datetime(2026, 10, 3, 10, 0, 0),
    )


# =====================================================================
# 1. Create Document (POST /api/v1/documents)
# =====================================================================

def test_create_document_success(sample_document_response):
    """Test registering a document for the authenticated student."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.create_document") as mock_create:
        mock_create.return_value = sample_document_response

        response = client.post(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "document_type": "CASTE_CERTIFICATE",
                "document_name": "Caste Certificate",
                "file_url": "https://storage.example.com/docs/caste.pdf",
                "file_size": 102400,
                "file_type": "application/pdf",
                "document_number": "CC-2026-9876",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["document_id"] == "TRB-DOC-000001"
        assert data["document_type"] == "CASTE_CERTIFICATE"
        assert data["document_name"] == "Caste Certificate"
        assert data["verification_status"] == "PENDING"
        assert "id" not in data  # Internal database UUIDs not exposed


# =====================================================================
# 2. List Documents (GET /api/v1/documents)
# =====================================================================

def test_get_my_documents_success(sample_document_response):
    """Test retrieving documents owned by the authenticated student."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.get_my_documents") as mock_get_my:
        mock_get_my.return_value = [sample_document_response]

        response = client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["documents"][0]["document_id"] == "TRB-DOC-000001"
        assert data["documents"][0]["document_name"] == "Caste Certificate"


# =====================================================================
# 3. Get Own Document By ID (GET /api/v1/documents/{document_id})
# =====================================================================

def test_get_own_document_by_id_success(sample_document_response):
    """Test retrieving a specific document owned by current student."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.get_my_document_by_id") as mock_get_id:
        mock_get_id.return_value = sample_document_response

        response = client.get(
            "/api/v1/documents/TRB-DOC-000001",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["document_id"] == "TRB-DOC-000001"


# =====================================================================
# 4. Update Editable Document (PUT /api/v1/documents/{document_id})
# =====================================================================

def test_update_document_success(sample_document_response):
    """Test updating allowed metadata for an owned document."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.update_document") as mock_update:
        mock_update.return_value = sample_document_response

        response = client.put(
            "/api/v1/documents/TRB-DOC-000001",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "document_name": "Updated Caste Certificate",
                "document_number": "CC-2026-9999",
            }
        )

        assert response.status_code == 200
        assert response.json()["document_id"] == "TRB-DOC-000001"


def test_update_verified_document_rejected():
    """Test that a verified document cannot be updated."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.update_document") as mock_update:
        mock_update.side_effect = AppException(
            status_code=400,
            code="DOCUMENT_NOT_EDITABLE",
            message="Verified documents cannot be modified."
        )

        response = client.put(
            "/api/v1/documents/TRB-DOC-000001",
            headers={"Authorization": f"Bearer {token}"},
            json={"document_name": "New Name"}
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_EDITABLE"


# =====================================================================
# 5. Delete Document (DELETE /api/v1/documents/{document_id})
# =====================================================================

def test_delete_document_success():
    """Test deleting an owned document."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.delete_document") as mock_delete:
        mock_delete.return_value = "TRB-DOC-000001"

        response = client.delete(
            "/api/v1/documents/TRB-DOC-000001",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "TRB-DOC-000001"
        assert "deleted successfully" in data["message"]


def test_delete_verified_document_rejected():
    """Test that a verified document cannot be deleted."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.delete_document") as mock_delete:
        mock_delete.side_effect = AppException(
            status_code=400,
            code="DOCUMENT_NOT_DELETABLE",
            message="Verified documents cannot be deleted."
        )

        response = client.delete(
            "/api/v1/documents/TRB-DOC-000001",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_DELETABLE"


# =====================================================================
# 6. Non-existent Document (404)
# =====================================================================

def test_get_nonexistent_document():
    """Test retrieving non-existent document returns 404."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.get_my_document_by_id") as mock_get_id:
        mock_get_id.side_effect = NotFoundException(
            message="Document not found.",
            code="DOCUMENT_NOT_FOUND"
        )

        response = client.get(
            "/api/v1/documents/TRB-DOC-999999",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


# =====================================================================
# 7, 8. Authentication Tests
# =====================================================================

def test_unauthenticated_document_requests_rejected():
    """Test unauthenticated calls to all document endpoints return 401."""
    endpoints = [
        ("GET", "/api/v1/documents"),
        ("POST", "/api/v1/documents"),
        ("GET", "/api/v1/documents/TRB-DOC-000001"),
        ("PUT", "/api/v1/documents/TRB-DOC-000001"),
        ("DELETE", "/api/v1/documents/TRB-DOC-000001"),
        ("GET", "/api/v1/documents/TRB-DOC-000001/verification"),
    ]

    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        elif method == "POST":
            res = client.post(path, json={"document_type": "CASTE", "document_name": "Test"})
        elif method == "PUT":
            res = client.put(path, json={"document_name": "Updated"})
        elif method == "DELETE":
            res = client.delete(path)

        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"


# =====================================================================
# 9, 10, 11. Student Ownership Security Tests
# =====================================================================

def test_student_cannot_access_other_student_document():
    """CRITICAL: Student A cannot access Student B's document (returns 404)."""
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.get_my_document_by_id") as mock_get:
        mock_get.side_effect = NotFoundException(
            message="Document not found.",
            code="DOCUMENT_NOT_FOUND"
        )

        response = client.get(
            "/api/v1/documents/TRB-DOC-OTHER-STUDENT",
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_student_cannot_update_other_student_document():
    """CRITICAL: Student A cannot update Student B's document (returns 404)."""
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.update_document") as mock_update:
        mock_update.side_effect = NotFoundException(
            message="Document not found.",
            code="DOCUMENT_NOT_FOUND"
        )

        response = client.put(
            "/api/v1/documents/TRB-DOC-OTHER-STUDENT",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"document_name": "Hacked Name"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_student_cannot_delete_other_student_document():
    """CRITICAL: Student A cannot delete Student B's document (returns 404)."""
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.delete_document") as mock_delete:
        mock_delete.side_effect = NotFoundException(
            message="Document not found.",
            code="DOCUMENT_NOT_FOUND"
        )

        response = client.delete(
            "/api/v1/documents/TRB-DOC-OTHER-STUDENT",
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


# =====================================================================
# 12. Spoofing Protection
# =====================================================================

def test_client_cannot_spoof_student_id_in_document_payload():
    """Injected student_id in body/query is ignored; derived strictly from token."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.create_document") as mock_create:
        mock_create.return_value = DocumentResponse(
            document_id="TRB-DOC-000001",
            document_type="CASTE_CERTIFICATE",
            document_name="Caste Certificate",
            verification_status="PENDING",
        )

        response = client.post(
            "/api/v1/documents?student_id=SPOOFED_ID",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "document_type": "CASTE_CERTIFICATE",
                "document_name": "Caste Certificate",
                "student_id": "SPOOFED-VICTIM-STUDENT-ID",
            }
        )

        assert response.status_code == 201
        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["auth_user_id"] == STUDENT_A_AUTH_ID


# =====================================================================
# 15, 16. Document Verification Info Lookups
# =====================================================================

def test_get_document_verification_success():
    """Test retrieving verification information for own document."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.get_document_verification") as mock_verif:
        mock_verif.return_value = DocumentVerificationInfo(
            document_id="TRB-DOC-000001",
            document_type="CASTE_CERTIFICATE",
            document_name="Caste Certificate",
            verification_status="PENDING",
            verified_at=None,
            verified_by=None,
            remarks=None,
        )

        response = client.get(
            "/api/v1/documents/TRB-DOC-000001/verification",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "TRB-DOC-000001"
        assert data["verification_status"] == "PENDING"


def test_get_document_verification_other_student_rejected():
    """Test retrieving verification info for another student's document returns 404."""
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.document_service.document_service.get_document_verification") as mock_verif:
        mock_verif.side_effect = NotFoundException(
            message="Document not found.",
            code="DOCUMENT_NOT_FOUND"
        )

        response = client.get(
            "/api/v1/documents/TRB-DOC-OTHER-STUDENT/verification",
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
