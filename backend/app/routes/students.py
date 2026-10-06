"""
Student endpoints managing profiles in `tribe_students` table.
"""
from fastapi import APIRouter, Depends, status
from app.schemas.student import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    StudentStatusResponse,
)
from app.services.student_service import student_service
from app.core.dependencies import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/students", tags=["Students"])


@router.get(
    "/me",
    response_model=StudentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current student profile",
    description="Retrieves the profile of the currently authenticated student from `tribe_students` using token identity.",
)
async def get_my_profile(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Returns current student profile.
    """
    return student_service.get_student_by_auth_user_id(current_user.id)


@router.post(
    "/me",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create current student profile",
    description="Initializes a student profile in `tribe_students` associated with the authenticated user ID.",
)
async def create_my_profile(
    payload: StudentCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Creates a new student profile for the authenticated user.
    """
    return student_service.create_student_profile(
        auth_user_id=current_user.id,
        default_email=current_user.email,
        payload=payload,
    )


@router.put(
    "/me",
    response_model=StudentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current student profile",
    description="Updates non-protected profile fields for the authenticated student.",
)
async def update_my_profile(
    payload: StudentUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Updates the profile for the authenticated student.
    """
    return student_service.update_student_profile(
        auth_user_id=current_user.id,
        payload=payload,
    )


@router.get(
    "/me/status",
    response_model=StudentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check current student profile existence and completeness",
    description="Returns whether profile exists and whether all essential fields are complete.",
)
async def get_my_profile_status(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Checks if profile exists and assesses completeness.
    """
    return student_service.get_profile_status(current_user.id)


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get student by ID (protected ownership check)",
    description="Protected profile lookup. Ensures a student can only view their own profile.",
)
async def get_student_by_id(
    student_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Retrieves student profile by business student_id or UUID, enforcing ownership verification.
    """
    return student_service.get_student_by_student_id(
        auth_user_id=current_user.id,
        target_student_id=student_id,
    )
