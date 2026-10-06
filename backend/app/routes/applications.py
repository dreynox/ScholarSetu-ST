"""
Application endpoints for managing student scholarship applications.
Protected user-scoped endpoints (Section 6).
"""
from fastapi import APIRouter, Depends, status
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationListResponse,
    ApplicationDeleteResponse,
)
from app.services.application_service import application_service
from app.core.dependencies import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new scholarship application",
    description="Initiates a new draft application linked to the authenticated student for a given scholarship scheme and academic year.",
)
async def create_application(
    payload: ApplicationCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Creates a new draft application.
    """
    return application_service.create_application(
        auth_user_id=current_user.id,
        payload=payload,
    )


@router.get(
    "",
    response_model=ApplicationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated student's applications",
    description="Retrieves all scholarship applications belonging strictly to the currently authenticated student.",
)
async def get_my_applications(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns list of applications for the authenticated student.
    """
    results = application_service.get_my_applications(current_user.id)
    return ApplicationListResponse(
        applications=results,
        count=len(results)
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application by ID",
    description="Retrieves a specific application. Enforces ownership check; returns 404 if application does not belong to the user.",
)
async def get_my_application_by_id(
    application_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns application details if owned by current student.
    """
    return application_service.get_my_application_by_id(
        auth_user_id=current_user.id,
        application_id=application_id,
    )


@router.put(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update draft application",
    description="Updates editable parameters of a draft application owned by current student. Only applications with DRAFT status can be modified.",
)
async def update_my_application(
    application_id: str,
    payload: ApplicationUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Updates draft application details.
    """
    return application_service.update_draft_application(
        auth_user_id=current_user.id,
        application_id=application_id,
        payload=payload,
    )


@router.delete(
    "/{application_id}",
    response_model=ApplicationDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete draft application",
    description="Deletes a draft application owned by current student. Non-draft applications (submitted, verified, sanctioned) cannot be deleted.",
)
async def delete_my_application(
    application_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Deletes draft application.
    """
    deleted_id = application_service.delete_draft_application(
        auth_user_id=current_user.id,
        application_id=application_id,
    )
    return ApplicationDeleteResponse(
        message="Draft application deleted successfully",
        application_id=deleted_id,
    )
