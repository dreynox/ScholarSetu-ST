"""
Payment endpoints for student scholarship disbursements and payment summary.
Protected user-scoped endpoints (Phase 4).
"""
from fastapi import APIRouter, Depends, status
from app.schemas.payment import (
    PaymentResponse,
    PaymentListResponse,
    PaymentSummaryResponse,
)
from app.services.payment_service import payment_service
from app.core.dependencies import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get(
    "",
    response_model=PaymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List student's payments",
    description="Retrieves all scholarship disbursements and payments belonging strictly to the currently authenticated student.",
)
async def get_my_payments(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns list of payments for the authenticated student.
    """
    results = payment_service.get_my_payments(current_user.id)
    return PaymentListResponse(
        payments=results,
        count=len(results)
    )


@router.get(
    "/summary",
    response_model=PaymentSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get student payment summary",
    description="Calculates summary counts and monetary totals for the authenticated student's scholarship disbursements.",
)
async def get_payment_summary(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns student-level payment summary metrics.
    """
    return payment_service.get_payment_summary(current_user.id)


@router.get(
    "/application/{application_id}",
    response_model=PaymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get payments for an application",
    description="Retrieves all disbursement records for a specific application owned by the authenticated student. Returns 404 if application not found or owned by another user.",
)
async def get_payments_by_application(
    application_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns payments linked to a specific student application.
    """
    results = payment_service.get_payments_by_application_id(
        auth_user_id=current_user.id,
        application_id=application_id,
    )
    return PaymentListResponse(
        payments=results,
        count=len(results)
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get payment details by payment ID",
    description="Retrieves detailed payment record by payment business ID or UUID. Enforces strict ownership check; returns 404 if not found or belongs to another user.",
)
async def get_payment_by_id(
    payment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns payment details if owned by current student.
    """
    return payment_service.get_payment_by_id(
        auth_user_id=current_user.id,
        payment_id=payment_id,
    )
