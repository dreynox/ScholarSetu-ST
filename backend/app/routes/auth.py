"""
Authentication endpoints for Supabase Auth integration.
"""
from fastapi import APIRouter, Depends, status
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, UserResponse
from app.services.auth_service import auth_service
from app.core.dependencies import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student account",
    description="Registers a new user through Supabase Auth without storing raw passwords in application tables.",
)
async def register(payload: RegisterRequest):
    """
    Registers a new student user via Supabase Auth.
    """
    return auth_service.register(payload)


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Student login",
    description="Authenticates the student with email and password via Supabase Auth, returning access token.",
)
async def login(payload: LoginRequest):
    """
    Authenticates existing student credentials and returns a Bearer access token.
    """
    return auth_service.login(payload)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user info",
    description="Validates Bearer access token and returns authenticated user identity.",
)
async def get_current_user_info(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Retrieves authenticated user details from validated token.
    """
    return UserResponse(
        user_id=current_user.id,
        email=current_user.email,
        user_metadata=current_user.user_metadata,
    )
