"""
Verification endpoints for student verification status lookups.
Protected user-scoped endpoints (Section 8).
"""
from fastapi import APIRouter, Depends, status
from app.schemas.verification import (
    VerificationResponse,
    VerificationListResponse,
    VerificationDetailResponse,
)
from app.services.verification_service import verification_service
from app.core.dependencies import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/verifications", tags=["Verifications"])


@router.get(
    "",
    response_model=VerificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all verifications for authenticated student",
    description="Retrieves verification records across all documents and applications owned by the authenticated student.",
)
async def get_my_verifications(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns all verification records for current student.
    """
    results = verification_service.get_my_verifications(current_user.id)
    return VerificationListResponse(
        verifications=results,
        count=len(results),
    )


@router.get(
    "/document/{document_id}",
    response_model=VerificationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get verification details for a document",
    description="Retrieves verification record for a specific document. Verifies ownership; returns 404 if not owned by current student.",
)
async def get_verification_by_document(
    document_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns verification record for a specific document.
    """
    return verification_service.get_verification_by_document(
        auth_user_id=current_user.id,
        document_id=document_id,
    )


@router.get(
    "/{verification_id}",
    response_model=VerificationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get verification record by ID",
    description="Retrieves specific verification record. Enforces student ownership; returns 404 if not owned by current student.",
)
async def get_my_verification_by_id(
    verification_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns verification record if owned by current student.
    """
    return verification_service.get_my_verification_by_id(
        auth_user_id=current_user.id,
        verification_id=verification_id,
    )
