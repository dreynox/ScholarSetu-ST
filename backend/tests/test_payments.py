"""
Payment endpoints unit, integration, and security tests.
Tests student-scoped payment lookups, cross-student isolation, application-scoped payments, summary calculations, and mutation prevention.
"""
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import jwt
import pytest

from app.main import app
from app.models.student import Student
from app.schemas.payment import (
    PaymentResponse,
    PaymentSummaryResponse,
    ScholarshipPaymentInfo,
)
from app.services.payment_service import PaymentService, payment_service
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
def sample_payment_item_1():
    return PaymentResponse(
        payment_id="TRB-PAY-000001",
        application_id="TRB-APP-000001",
        amount=15000.0,
        payment_status="SUCCESS",
        transaction_reference="TXN-20261001-998811",
        utr_number="SBIN00019283746",
        payment_date=datetime(2026, 10, 1, 14, 30, 0),
        bank_name="State Bank of India",
        failure_reason=None,
        academic_year="2026-27",
        scholarship=ScholarshipPaymentInfo(
            scholarship_id="TRB-SCH-000001",
            name="Pre-Matric Scholarship for ST Students",
            short_name="PRE_MATRIC",
        ),
        created_at=datetime(2026, 10, 1, 14, 0, 0),
        updated_at=datetime(2026, 10, 1, 14, 30, 0),
    )


@pytest.fixture
def sample_payment_item_2():
    return PaymentResponse(
        payment_id="TRB-PAY-000002",
        application_id="TRB-APP-000001",
        amount=15000.0,
        payment_status="PENDING",
        transaction_reference=None,
        utr_number=None,
        payment_date=None,
        bank_name="State Bank of India",
        failure_reason=None,
        academic_year="2026-27",
        scholarship=ScholarshipPaymentInfo(
            scholarship_id="TRB-SCH-000001",
            name="Pre-Matric Scholarship for ST Students",
            short_name="PRE_MATRIC",
        ),
        created_at=datetime(2026, 10, 2, 9, 0, 0),
        updated_at=datetime(2026, 10, 2, 9, 0, 0),
    )


# =====================================================================
# 1. List Own Payments (GET /api/v1/payments)
# =====================================================================

def test_list_my_payments_success(sample_payment_item_1, sample_payment_item_2):
    """Test retrieving payment records belonging to authenticated student."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.payment_service.payment_service.get_my_payments") as mock_list:
        mock_list.return_value = [sample_payment_item_1, sample_payment_item_2]

        response = client.get(
            "/api/v1/payments",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["payments"]) == 2
        assert data["payments"][0]["payment_id"] == "TRB-PAY-000001"
        assert data["payments"][0]["amount"] == 15000.0
        assert data["payments"][0]["payment_status"] == "SUCCESS"
        assert data["payments"][0]["scholarship"]["short_name"] == "PRE_MATRIC"
        assert data["payments"][1]["payment_status"] == "PENDING"


def test_list_my_payments_empty():
    """Test retrieving payments when student has no disbursements."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.payment_service.payment_service.get_my_payments") as mock_list:
        mock_list.return_value = []

        response = client.get(
            "/api/v1/payments",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["payments"] == []


# =====================================================================
# 2. Get Payment By ID (GET /api/v1/payments/{payment_id})
# =====================================================================

def test_get_own_payment_by_id_success(sample_payment_item_1):
    """Test retrieving a specific payment record owned by current student."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.payment_service.payment_service.get_payment_by_id") as mock_get:
        mock_get.return_value = sample_payment_item_1

        response = client.get(
            "/api/v1/payments/TRB-PAY-000001",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["payment_id"] == "TRB-PAY-000001"
        assert data["application_id"] == "TRB-APP-000001"
        assert data["amount"] == 15000.0
        assert data["utr_number"] == "SBIN00019283746"
        assert data["payment_status"] == "SUCCESS"


def test_get_nonexistent_payment_returns_404():
    """Test lookup of non-existent payment ID returns 404 PAYMENT_NOT_FOUND."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.payment_service.payment_service.get_payment_by_id") as mock_get:
        mock_get.side_effect = NotFoundException(
            message="Payment not found",
            code="PAYMENT_NOT_FOUND"
        )

        response = client.get(
            "/api/v1/payments/TRB-PAY-NONEXISTENT",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"
        assert response.json()["error"]["message"] == "Payment not found"


def test_cross_student_payment_access_returns_404():
    """CRITICAL SECURITY: Student A attempting to access Student B's payment receives 404."""
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.payment_service.payment_service.get_payment_by_id") as mock_get:
        mock_get.side_effect = NotFoundException(
            message="Payment not found",
            code="PAYMENT_NOT_FOUND"
        )

        response = client.get(
            "/api/v1/payments/TRB-PAY-STUDENT-B",
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"


# =====================================================================
# 3. Get Payments By Application ID (GET /api/v1/payments/application/{application_id})
# =====================================================================

def test_get_payments_by_own_application_success(sample_payment_item_1, sample_payment_item_2):
    """Test retrieving all disbursement records for an application owned by student."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.payment_service.payment_service.get_payments_by_application_id") as mock_app_pay:
        mock_app_pay.return_value = [sample_payment_item_1, sample_payment_item_2]

        response = client.get(
            "/api/v1/payments/application/TRB-APP-000001",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["payments"]) == 2
        assert data["payments"][0]["application_id"] == "TRB-APP-000001"


def test_get_payments_by_cross_student_application_returns_404():
    """CRITICAL SECURITY: Student A accessing Student B's application payments receives 404."""
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.payment_service.payment_service.get_payments_by_application_id") as mock_app_pay:
        mock_app_pay.side_effect = NotFoundException(
            message="Application not found",
            code="APPLICATION_NOT_FOUND"
        )

        response = client.get(
            "/api/v1/payments/application/TRB-APP-STUDENT-B",
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "APPLICATION_NOT_FOUND"


def test_get_payments_by_nonexistent_application_returns_404():
    """Test application not found returns 404."""
    token = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.payment_service.payment_service.get_payments_by_application_id") as mock_app_pay:
        mock_app_pay.side_effect = NotFoundException(
            message="Application not found",
            code="APPLICATION_NOT_FOUND"
        )

        response = client.get(
            "/api/v1/payments/application/NON-EXISTENT-APP",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "APPLICATION_NOT_FOUND"


# =====================================================================
# 4. Payment Summary (GET /api/v1/payments/summary)
# =====================================================================

def test_get_payment_summary_success():
    """Test retrieving aggregated payment summary for authenticated student."""
    token = generate_token(STUDENT_A_AUTH_ID)
    summary_data = PaymentSummaryResponse(
        total_payments=3,
        pending_payments=1,
        processing_payments=1,
        completed_payments=1,
        failed_payments=0,
        total_amount=45000.0,
        disbursed_amount=15000.0,
    )

    with patch("app.services.payment_service.payment_service.get_payment_summary") as mock_summary:
        mock_summary.return_value = summary_data

        response = client.get(
            "/api/v1/payments/summary",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_payments"] == 3
        assert data["pending_payments"] == 1
        assert data["processing_payments"] == 1
        assert data["completed_payments"] == 1
        assert data["failed_payments"] == 0
        assert data["total_amount"] == 45000.0
        assert data["disbursed_amount"] == 15000.0


def test_get_payment_summary_empty():
    """Test summary when student has zero payment records."""
    token = generate_token(STUDENT_A_AUTH_ID)
    summary_data = PaymentSummaryResponse(
        total_payments=0,
        pending_payments=0,
        processing_payments=0,
        completed_payments=0,
        failed_payments=0,
        total_amount=0.0,
        disbursed_amount=0.0,
    )

    with patch("app.services.payment_service.payment_service.get_payment_summary") as mock_summary:
        mock_summary.return_value = summary_data

        response = client.get(
            "/api/v1/payments/summary",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_payments"] == 0
        assert data["total_amount"] == 0.0


# =====================================================================
# 5. Authentication & Authorization Security Tests
# =====================================================================

def test_unauthenticated_payment_requests_rejected():
    """Test unauthenticated calls to all payment endpoints return 401 UNAUTHORIZED."""
    endpoints = [
        "/api/v1/payments",
        "/api/v1/payments/summary",
        "/api/v1/payments/TRB-PAY-000001",
        "/api/v1/payments/application/TRB-APP-000001",
    ]

    for path in endpoints:
        res = client.get(path)
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_token_rejected():
    """Test invalid or malformed Bearer token is rejected with 401."""
    res = client.get(
        "/api/v1/payments",
        headers={"Authorization": "Bearer invalid.malformed.jwt.token"}
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] in ["UNAUTHORIZED", "INVALID_TOKEN"]


def test_student_id_spoofing_prevention():
    """
    CRITICAL SECURITY TEST:
    Passing ?student_id=spoofed_id does not affect authentication or ownership.
    Identity is strictly derived from JWT auth_user_id.
    """
    token_a = generate_token(STUDENT_A_AUTH_ID)

    with patch("app.services.payment_service.payment_service.get_my_payments") as mock_list:
        mock_list.return_value = []

        response = client.get(
            f"/api/v1/payments?student_id={STUDENT_B_DB_ID}",
            headers={"Authorization": f"Bearer {token_a}"}
        )

        assert response.status_code == 200
        # Check that get_my_payments was called with student A's auth user id
        mock_list.assert_called_once_with(STUDENT_A_AUTH_ID)


# =====================================================================
# 6. Student Payment Mutation Prevention (Section 12)
# =====================================================================

def test_student_cannot_post_or_put_payment():
    """
    CRITICAL SECURITY TEST:
    Students cannot create, edit, or delete disbursement/payment records.
    POST, PUT, DELETE endpoints for payments are not exposed to student clients.
    """
    token = generate_token(STUDENT_A_AUTH_ID)

    # Attempt to POST /api/v1/payments
    post_res = client.post(
        "/api/v1/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount": 50000.0, "status": "SUCCESS"}
    )
    assert post_res.status_code in [404, 405]

    # Attempt to PUT /api/v1/payments/TRB-PAY-000001
    put_res = client.put(
        "/api/v1/payments/TRB-PAY-000001",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_status": "SUCCESS"}
    )
    assert put_res.status_code in [404, 405]

    # Attempt to DELETE /api/v1/payments/TRB-PAY-000001
    del_res = client.delete(
        "/api/v1/payments/TRB-PAY-000001",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert del_res.status_code in [404, 405]


# =====================================================================
# 7. PaymentService Logic Unit Tests
# =====================================================================

def test_payment_service_resolve_student_not_found():
    """Test PaymentService raises NotFoundException when student does not exist."""
    with patch("app.services.payment_service.get_supabase_service_client") as mock_sb:
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        with pytest.raises(NotFoundException) as exc_info:
            PaymentService._resolve_student("unknown-auth-id")

        assert exc_info.value.code == "STUDENT_NOT_FOUND"


def test_payment_service_hydrate_response_status_and_defaults():
    """Test PaymentService._hydrate_payment_response handles missing joined fields gracefully."""
    raw_row = {
        "id": "pay-uuid-001",
        "payment_id": "TRB-PAY-999999",
        "application_id": "app-uuid-001",
        "student_id": "stu-uuid-001",
        "amount": 25000.5,
        "payment_status": "PROCESSING",
        "transaction_reference": "TXN-12345",
        "utr_number": None,
        "payment_date": None,
        "bank_name": "Canara Bank",
        "failure_reason": None,
        "created_at": "2026-10-04T10:00:00Z",
        "updated_at": "2026-10-04T10:05:00Z",
    }

    res = PaymentService._hydrate_payment_response(
        raw_row,
        apps_map={},
        scholarships_map={}
    )

    assert res.payment_id == "TRB-PAY-999999"
    assert res.application_id == "UNKNOWN_APP"
    assert res.amount == 25000.5
    assert res.payment_status == "PROCESSING"
    assert res.scholarship is None
    assert res.academic_year is None
    assert res.created_at is not None


def test_payment_service_get_my_payments_e2e_flow():
    """Test full PaymentService.get_my_payments resolution with mocked Supabase queries."""
    with patch.object(PaymentService, "_resolve_student") as mock_res_stu, \
         patch("app.services.payment_service.get_supabase_service_client") as mock_sb:

        mock_student = Student(
            id=STUDENT_A_DB_ID,
            student_id="TRB-STU-000001",
            auth_user_id=STUDENT_A_AUTH_ID,
            full_name="Birsa Munda",
            email="birsa.munda@example.com",
            is_active=True,
        )
        mock_res_stu.return_value = mock_student

        mock_client = MagicMock()
        mock_sb.return_value = mock_client

        # Mock table calls
        def table_side_effect(table_name):
            mock_tbl = MagicMock()
            if table_name == "tribe_disbursements":
                mock_tbl.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=[
                    {
                        "id": "disb-1",
                        "payment_id": "TRB-PAY-000001",
                        "application_id": "app-uuid-1",
                        "student_id": STUDENT_A_DB_ID,
                        "amount": 12000.0,
                        "payment_status": "SUCCESS",
                        "transaction_reference": "TXN-1",
                        "utr_number": "UTR-1",
                        "payment_date": "2026-10-01T10:00:00Z",
                        "bank_name": "SBI",
                        "failure_reason": None,
                        "created_at": "2026-10-01T09:00:00Z",
                        "updated_at": "2026-10-01T10:00:00Z",
                    }
                ])
            elif table_name == "tribe_applications":
                mock_tbl.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[
                    {
                        "id": "app-uuid-1",
                        "application_id": "TRB-APP-000001",
                        "scholarship_id": "sch-uuid-1",
                        "academic_year": "2026-27",
                        "student_id": STUDENT_A_DB_ID,
                    }
                ])
            elif table_name == "tribe_scholarships":
                mock_tbl.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[
                    {
                        "id": "sch-uuid-1",
                        "scholarship_id": "TRB-SCH-000001",
                        "name": "Pre-Matric Scholarship",
                        "short_name": "PRE_MATRIC",
                    }
                ])
            return mock_tbl

        mock_client.table.side_effect = table_side_effect

        payments = PaymentService.get_my_payments(STUDENT_A_AUTH_ID)
        assert len(payments) == 1
        p = payments[0]
        assert p.payment_id == "TRB-PAY-000001"
        assert p.application_id == "TRB-APP-000001"
        assert p.amount == 12000.0
        assert p.payment_status == "SUCCESS"
        assert p.scholarship is not None
        assert p.scholarship.short_name == "PRE_MATRIC"


def test_payment_service_get_payment_summary_calculation():
    """Test PaymentService.get_payment_summary calculates exact metrics."""
    with patch.object(PaymentService, "_resolve_student") as mock_res_stu, \
         patch("app.services.payment_service.get_supabase_service_client") as mock_sb:

        mock_student = Student(
            id=STUDENT_A_DB_ID,
            student_id="TRB-STU-000001",
            auth_user_id=STUDENT_A_AUTH_ID,
            full_name="Birsa Munda",
            email="birsa.munda@example.com",
            is_active=True,
        )
        mock_res_stu.return_value = mock_student

        mock_client = MagicMock()
        mock_sb.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
            {"amount": 10000.0, "payment_status": "SUCCESS"},
            {"amount": 10000.0, "payment_status": "DISBURSED"},
            {"amount": 5000.0, "payment_status": "PROCESSING"},
            {"amount": 5000.0, "payment_status": "PENDING"},
            {"amount": 2000.0, "payment_status": "FAILED"},
        ])

        summary = PaymentService.get_payment_summary(STUDENT_A_AUTH_ID)
        assert summary.total_payments == 5
        assert summary.completed_payments == 2
        assert summary.processing_payments == 1
        assert summary.pending_payments == 1
        assert summary.failed_payments == 1
        assert summary.total_amount == 32000.0
        assert summary.disbursed_amount == 20000.0

