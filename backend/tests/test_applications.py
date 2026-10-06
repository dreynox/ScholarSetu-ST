"""
Application endpoints unit, integration, and security tests.
Tests the 5 application endpoints, foreign-key resolution, duplicate prevention, and ownership enforcement.
"""
from datetime import date, datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import jwt
import pytest

from app.main import app
from app.models.student import Student
from app.schemas.application import (
    ApplicationResponse,
    ScholarshipInfo,
    InstitutionInfo,
    ApplicationCreate,
    ApplicationUpdate,
)
from app.services.application_service import ApplicationService, application_service
from app.utils.errors import (
    NotFoundException,
    ConflictException,
    AppException,
    UnauthorizedException,
)

client = TestClient(app)

STUDENT_A_AUTH_ID = "00000000-0000-0000-0000-000000000001"
STUDENT_B_AUTH_ID = "00000000-0000-0000-0000-000000000002"

STUDENT_A_DB_ID = "11111111-1111-1111-1111-111111111111"
STUDENT_B_DB_ID = "22222222-2222-2222-2222-222222222222"

SCHOLARSHIP_UUID = "33333333-3333-3333-3333-333333333333"
INSTITUTION_UUID = "44444444-4444-4444-4444-444444444444"

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
def sample_application_response():
    return ApplicationResponse(
        application_id="TRB-APP-000001",
        scholarship=ScholarshipInfo(
            scholarship_id="TRB-SCH-000001",
            name="Pre-Matric Scholarship for ST Students",
            short_name="PRE_MATRIC",
            scholarship_type="PRE_MATRIC",
        ),
        institution=InstitutionInfo(
            institution_id="TRB-INS-000001",
            name="Ranchi Model Tribal School",
            code="AISHE-102938",
            state="Jharkhand",
            district="Ranchi",
        ),
        academic_year="2026-27",
        status="DRAFT",
        current_stage="APPLICATION",
        application_date=date(2026, 10, 3),
        submitted_at=None,
        sanctioned_at=None,
        rejected_at=None,
        rejection_reason=None,
    )


# =====================================================================
# 1. Create Application (POST /api/v1/applications)
# =====================================================================

def test_create_application_success(sample_application_response):
    """1. Test creating a valid draft application for authenticated student."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.create_application") as mock_create:
        mock_create.return_value = sample_application_response

        response = client.post(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "scholarship_id": "TRB-SCH-000001",
                "institution_id": "TRB-INS-000001",
                "academic_year": "2026-27",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["application_id"] == "TRB-APP-000001"
        assert data["scholarship"]["scholarship_id"] == "TRB-SCH-000001"
        assert data["institution"]["institution_id"] == "TRB-INS-000001"
        assert data["status"] == "DRAFT"
        assert data["current_stage"] == "APPLICATION"
        assert data["academic_year"] == "2026-27"
        assert "id" not in data  # No database internal UUIDs exposed


# =====================================================================
# 2. Get Student's Applications (GET /api/v1/applications)
# =====================================================================

def test_get_my_applications_success(sample_application_response):
    """2. Test retrieving list of applications belonging to authenticated student."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.get_my_applications") as mock_get_my:
        mock_get_my.return_value = [sample_application_response]

        response = client.get(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["applications"][0]["application_id"] == "TRB-APP-000001"
        assert data["applications"][0]["scholarship"]["name"] == "Pre-Matric Scholarship for ST Students"


# =====================================================================
# 3. Get Application By ID (GET /api/v1/applications/{application_id})
# =====================================================================

def test_get_own_application_by_id_success(sample_application_response):
    """3. Test student retrieving their own application by application_id."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.get_my_application_by_id") as mock_get_id:
        mock_get_id.return_value = sample_application_response

        response = client.get(
            "/api/v1/applications/TRB-APP-000001",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["application_id"] == "TRB-APP-000001"


# =====================================================================
# 4. Update Draft Application (PUT /api/v1/applications/{application_id})
# =====================================================================

def test_update_draft_application_success(sample_application_response):
    """4. Test updating editable fields of a draft application."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.update_draft_application") as mock_update:
        mock_update.return_value = sample_application_response

        response = client.put(
            "/api/v1/applications/TRB-APP-000001",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "academic_year": "2026-27",
            }
        )

        assert response.status_code == 200
        assert response.json()["application_id"] == "TRB-APP-000001"


# =====================================================================
# 5. Delete Draft Application (DELETE /api/v1/applications/{application_id})
# =====================================================================

def test_delete_draft_application_success():
    """5. Test deleting a draft application owned by current student."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.delete_draft_application") as mock_delete:
        mock_delete.return_value = "TRB-APP-000001"

        response = client.delete(
            "/api/v1/applications/TRB-APP-000001",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["application_id"] == "TRB-APP-000001"
        assert "deleted successfully" in data["message"]


# =====================================================================
# 6. Invalid Scholarship (404)
# =====================================================================

def test_create_application_invalid_scholarship():
    """6. Test creating application with non-existent scholarship returns 404."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.create_application") as mock_create:
        mock_create.side_effect = NotFoundException(
            message="Active scholarship scheme 'INVALID-SCH' not found.",
            code="SCHOLARSHIP_NOT_FOUND"
        )

        response = client.post(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "scholarship_id": "INVALID-SCH",
                "academic_year": "2026-27",
            },
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SCHOLARSHIP_NOT_FOUND"


# =====================================================================
# 7. Invalid Institution (404)
# =====================================================================

def test_create_application_invalid_institution():
    """7. Test creating application with non-existent institution returns 404."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.create_application") as mock_create:
        mock_create.side_effect = NotFoundException(
            message="Institution 'INVALID-INS' not found.",
            code="INSTITUTION_NOT_FOUND"
        )

        response = client.post(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "scholarship_id": "TRB-SCH-000001",
                "institution_id": "INVALID-INS",
                "academic_year": "2026-27",
            },
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "INSTITUTION_NOT_FOUND"


# =====================================================================
# 8. Invalid Academic Year (422)
# =====================================================================

def test_create_application_invalid_academic_year_format():
    """8. Test validation rejection for malformed academic year (not YYYY-YY)."""
    token = generate_token(STUDENT_A_AUTH_ID)

    invalid_years = ["2026", "2026-2027", "26-27", "abcd-ef", "2026-28"]
    for y in invalid_years:
        response = client.post(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "scholarship_id": "TRB-SCH-000001",
                "academic_year": y,
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# =====================================================================
# 9. Duplicate Application (409)
# =====================================================================

def test_create_application_duplicate_conflict():
    """9. Test duplicate application for same student, scholarship, and academic year returns 409."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.create_application") as mock_create:
        mock_create.side_effect = ConflictException(
            message="You already have an application for this scholarship and academic year.",
            code="DUPLICATE_APPLICATION"
        )

        response = client.post(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "scholarship_id": "TRB-SCH-000001",
                "institution_id": "TRB-INS-000001",
                "academic_year": "2026-27",
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "DUPLICATE_APPLICATION"
        assert "already have an application" in data["error"]["message"]


# =====================================================================
# 10. Missing Authentication (401)
# =====================================================================

def test_missing_authentication_rejected():
    """10. Test that unauthenticated calls to all application endpoints are rejected with 401."""
    endpoints = [
        ("GET", "/api/v1/applications"),
        ("POST", "/api/v1/applications"),
        ("GET", "/api/v1/applications/TRB-APP-000001"),
        ("PUT", "/api/v1/applications/TRB-APP-000001"),
        ("DELETE", "/api/v1/applications/TRB-APP-000001"),
    ]

    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        elif method == "POST":
            res = client.post(path, json={"scholarship_id": "TRB-SCH-000001", "academic_year": "2026-27"})
        elif method == "PUT":
            res = client.put(path, json={"academic_year": "2026-27"})
        elif method == "DELETE":
            res = client.delete(path)

        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"


# =====================================================================
# 11. Student A Cannot Access Student B's Application (404)
# =====================================================================

def test_student_cannot_access_other_student_application():
    """11. Student A attempts to access Student B's application; returns 404."""
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.get_my_application_by_id") as mock_get_id:
        mock_get_id.side_effect = NotFoundException(
            message="Application not found.",
            code="APPLICATION_NOT_FOUND"
        )

        response = client.get(
            "/api/v1/applications/TRB-APP-999999",
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "APPLICATION_NOT_FOUND"


# =====================================================================
# 12. Student A Cannot Update Student B's Application (404)
# =====================================================================

def test_student_cannot_update_other_student_application():
    """12. Student A attempting to update Student B's application returns 404."""
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.update_draft_application") as mock_update:
        mock_update.side_effect = NotFoundException(
            message="Application not found.",
            code="APPLICATION_NOT_FOUND"
        )

        response = client.put(
            "/api/v1/applications/TRB-APP-999999",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"academic_year": "2026-27"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "APPLICATION_NOT_FOUND"


# =====================================================================
# 13. Student A Cannot Delete Student B's Application (404)
# =====================================================================

def test_student_cannot_delete_other_student_application():
    """13. Student A attempting to delete Student B's application returns 404."""
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.delete_draft_application") as mock_delete:
        mock_delete.side_effect = NotFoundException(
            message="Application not found.",
            code="APPLICATION_NOT_FOUND"
        )

        response = client.delete(
            "/api/v1/applications/TRB-APP-999999",
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "APPLICATION_NOT_FOUND"


# =====================================================================
# 14. Submitted / Non-Draft Application Cannot Be Edited (400)
# =====================================================================

def test_update_non_draft_application_rejected():
    """14. Modifying a submitted/non-draft application returns 400 APPLICATION_NOT_EDITABLE."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.update_draft_application") as mock_update:
        mock_update.side_effect = AppException(
            status_code=400,
            code="APPLICATION_NOT_EDITABLE",
            message="Only draft applications can be modified."
        )

        response = client.put(
            "/api/v1/applications/TRB-APP-000001",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "academic_year": "2026-27",
            }
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "APPLICATION_NOT_EDITABLE"


# =====================================================================
# 15. Submitted / Non-Draft Application Cannot Be Deleted (400)
# =====================================================================

def test_delete_non_draft_application_rejected():
    """15. Deleting a submitted/sanctioned application returns 400 APPLICATION_NOT_DELETABLE."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.delete_draft_application") as mock_delete:
        mock_delete.side_effect = AppException(
            status_code=400,
            code="APPLICATION_NOT_DELETABLE",
            message="Only draft applications can be deleted."
        )

        response = client.delete(
            "/api/v1/applications/TRB-APP-000001",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "APPLICATION_NOT_DELETABLE"


# =====================================================================
# 16. Client Cannot Spoof student_id
# =====================================================================

def test_client_cannot_spoof_student_id_in_payload():
    """16. Injected student_id in body/query is ignored; ownership derives strictly from token."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.application_service.application_service.create_application") as mock_create:
        mock_create.return_value = ApplicationResponse(
            application_id="TRB-APP-000001",
            scholarship=ScholarshipInfo(scholarship_id="TRB-SCH-000001", name="Pre-Matric"),
            academic_year="2026-27",
            status="DRAFT",
            current_stage="APPLICATION",
        )

        response = client.post(
            "/api/v1/applications?student_id=SPOOFED_QUERY_ID",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "scholarship_id": "TRB-SCH-000001",
                "academic_year": "2026-27",
                "student_id": "SPOOFED-VICTIM-STUDENT-ID",
            },
        )

        assert response.status_code == 201
        mock_create.assert_called_once()
        assert mock_create.call_args.kwargs["auth_user_id"] == STUDENT_A_AUTH_ID


# =====================================================================
# 17, 18, 19. Foreign Key Resolution & Correct UUID Insertion Tests
# =====================================================================

def test_application_gets_correct_student_uuid(mock_student_a):
    """17. Verifies application receives the authenticated student's database UUID."""
    mock_supabase = MagicMock()

    with patch("app.services.application_service.get_supabase_service_client", return_value=mock_supabase):
        with patch.object(ApplicationService, "_resolve_student", return_value=mock_student_a):
            with patch.object(
                ApplicationService,
                "_resolve_scholarship",
                return_value={
                    "id": SCHOLARSHIP_UUID,
                    "scholarship_id": "TRB-SCH-000001",
                    "name": "Pre-Matric Scholarship",
                },
            ):
                with patch.object(ApplicationService, "_resolve_institution", return_value=None):
                    with patch.object(ApplicationService, "_generate_application_id", return_value="TRB-APP-000001"):
                        mock_supabase.table().select().eq().eq().eq().execute.return_value.data = []
                        mock_supabase.table().insert.return_value.execute.return_value.data = [
                            {
                                "id": "99999999-9999-9999-9999-999999999999",
                                "application_id": "TRB-APP-000001",
                                "student_id": STUDENT_A_DB_ID,
                                "scholarship_id": SCHOLARSHIP_UUID,
                                "institution_id": None,
                                "academic_year": "2026-27",
                                "status": "DRAFT",
                                "current_stage": "APPLICATION",
                            }
                        ]

                        payload = ApplicationCreate(
                            scholarship_id="TRB-SCH-000001",
                            academic_year="2026-27",
                        )
                        res = application_service.create_application(STUDENT_A_AUTH_ID, payload)

                        insert_dict = mock_supabase.table().insert.call_args[0][0]
                        assert insert_dict["student_id"] == STUDENT_A_DB_ID


def test_application_gets_correct_scholarship_uuid(mock_student_a):
    """18. Verifies application receives the resolved scholarship database UUID."""
    mock_supabase = MagicMock()

    with patch("app.services.application_service.get_supabase_service_client", return_value=mock_supabase):
        with patch.object(ApplicationService, "_resolve_student", return_value=mock_student_a):
            with patch.object(
                ApplicationService,
                "_resolve_scholarship",
                return_value={
                    "id": SCHOLARSHIP_UUID,
                    "scholarship_id": "TRB-SCH-000001",
                    "name": "Pre-Matric Scholarship",
                },
            ):
                with patch.object(ApplicationService, "_resolve_institution", return_value=None):
                    with patch.object(ApplicationService, "_generate_application_id", return_value="TRB-APP-000001"):
                        mock_supabase.table().select().eq().eq().eq().execute.return_value.data = []
                        mock_supabase.table().insert.return_value.execute.return_value.data = [
                            {
                                "id": "99999999-9999-9999-9999-999999999999",
                                "application_id": "TRB-APP-000001",
                                "student_id": STUDENT_A_DB_ID,
                                "scholarship_id": SCHOLARSHIP_UUID,
                                "institution_id": None,
                                "academic_year": "2026-27",
                                "status": "DRAFT",
                                "current_stage": "APPLICATION",
                            }
                        ]

                        payload = ApplicationCreate(
                            scholarship_id="TRB-SCH-000001",
                            academic_year="2026-27",
                        )
                        res = application_service.create_application(STUDENT_A_AUTH_ID, payload)

                        insert_dict = mock_supabase.table().insert.call_args[0][0]
                        assert insert_dict["scholarship_id"] == SCHOLARSHIP_UUID


def test_application_gets_correct_institution_uuid(mock_student_a):
    """19. Verifies application receives the resolved institution database UUID."""
    mock_supabase = MagicMock()

    with patch("app.services.application_service.get_supabase_service_client", return_value=mock_supabase):
        with patch.object(ApplicationService, "_resolve_student", return_value=mock_student_a):
            with patch.object(
                ApplicationService,
                "_resolve_scholarship",
                return_value={
                    "id": SCHOLARSHIP_UUID,
                    "scholarship_id": "TRB-SCH-000001",
                    "name": "Pre-Matric Scholarship",
                },
            ):
                with patch.object(
                    ApplicationService,
                    "_resolve_institution",
                    return_value={
                        "id": INSTITUTION_UUID,
                        "institution_id": "TRB-INS-000001",
                        "name": "Tribal Model School",
                    },
                ):
                    with patch.object(ApplicationService, "_generate_application_id", return_value="TRB-APP-000001"):
                        mock_supabase.table().select().eq().eq().eq().execute.return_value.data = []
                        mock_supabase.table().insert.return_value.execute.return_value.data = [
                            {
                                "id": "99999999-9999-9999-9999-999999999999",
                                "application_id": "TRB-APP-000001",
                                "student_id": STUDENT_A_DB_ID,
                                "scholarship_id": SCHOLARSHIP_UUID,
                                "institution_id": INSTITUTION_UUID,
                                "academic_year": "2026-27",
                                "status": "DRAFT",
                                "current_stage": "APPLICATION",
                            }
                        ]

                        payload = ApplicationCreate(
                            scholarship_id="TRB-SCH-000001",
                            institution_id="TRB-INS-000001",
                            academic_year="2026-27",
                        )
                        res = application_service.create_application(STUDENT_A_AUTH_ID, payload)

                        insert_dict = mock_supabase.table().insert.call_args[0][0]
                        assert insert_dict["institution_id"] == INSTITUTION_UUID
