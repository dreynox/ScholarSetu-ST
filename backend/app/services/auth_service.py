"""
Authentication service orchestrating Supabase Auth operations.
"""
from typing import Optional, Dict, Any
from app.db.supabase import get_supabase_client
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, UserResponse
from app.utils.errors import UnauthorizedException, ConflictException, AppException


class AuthService:
    """Service handling user registration, authentication, and session retrieval."""

    @staticmethod
    def register(payload: RegisterRequest) -> AuthResponse:
        """
        Registers a new user in Supabase Auth.
        Does NOT store passwords in the database directly.
        """
        supabase = get_supabase_client()
        try:
            response = supabase.auth.sign_up({
                "email": payload.email,
                "password": payload.password,
                "options": {
                    "data": {
                        "full_name": payload.full_name
                    }
                }
            })

            if not response or not response.user:
                raise AppException(
                    status_code=400,
                    code="REGISTRATION_FAILED",
                    message="Failed to register user account."
                )

            user = response.user
            session = response.session

            return AuthResponse(
                access_token=session.access_token if session else None,
                token_type="bearer",
                expires_in=session.expires_in if session else None,
                refresh_token=session.refresh_token if session else None,
                user=UserResponse(
                    user_id=str(user.id),
                    email=str(user.email),
                    user_metadata=user.user_metadata if hasattr(user, "user_metadata") else {"full_name": payload.full_name},
                )
            )
        except AppException:
            raise
        except Exception as e:
            err_msg = str(e)
            if "already registered" in err_msg.lower() or "unique constraint" in err_msg.lower() or "duplicate" in err_msg.lower():
                raise ConflictException(
                    message="An account with this email already exists.",
                    code="EMAIL_ALREADY_EXISTS"
                )
            raise AppException(
                status_code=400,
                code="AUTH_ERROR",
                message=f"Registration error: {err_msg}"
            )

    @staticmethod
    def login(payload: LoginRequest) -> AuthResponse:
        """
        Authenticates user with Supabase Auth using email and password.
        Returns JWT access token.
        """
        supabase = get_supabase_client()
        try:
            response = supabase.auth.sign_in_with_password({
                "email": payload.email,
                "password": payload.password
            })

            if not response or not response.user or not response.session:
                raise UnauthorizedException(
                    message="Invalid email or password.",
                    code="INVALID_CREDENTIALS"
                )

            user = response.user
            session = response.session

            return AuthResponse(
                access_token=session.access_token,
                token_type="bearer",
                expires_in=session.expires_in,
                refresh_token=session.refresh_token,
                user=UserResponse(
                    user_id=str(user.id),
                    email=str(user.email),
                    user_metadata=user.user_metadata if hasattr(user, "user_metadata") else {},
                )
            )
        except UnauthorizedException:
            raise
        except Exception as e:
            err_msg = str(e)
            if "invalid" in err_msg.lower() or "credentials" in err_msg.lower() or "not found" in err_msg.lower():
                raise UnauthorizedException(
                    message="Invalid email or password.",
                    code="INVALID_CREDENTIALS"
                )
            raise AppException(
                status_code=400,
                code="AUTH_ERROR",
                message=f"Login error: {err_msg}"
            )


auth_service = AuthService()
