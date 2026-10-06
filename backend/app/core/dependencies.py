"""
FastAPI dependencies for authentication, authorization, and Supabase client injection.
"""
from typing import Optional, Dict, Any
from fastapi import Header, Depends
from pydantic import BaseModel
from app.db.supabase import get_supabase_client
from app.core.security import decode_jwt_token
from app.utils.errors import UnauthorizedException, AppException


class AuthenticatedUser(BaseModel):
    """Authenticated user representation extracted from validated token."""
    id: str
    email: str
    token: str
    user_metadata: Optional[Dict[str, Any]] = None


async def get_current_user(
    authorization: Optional[str] = Header(None, description="Bearer token")
) -> AuthenticatedUser:
    """
    Extracts and validates the Supabase Auth token from the Authorization header.
    Never trusts client-supplied user identifiers for identity or ownership.
    """
    if not authorization:
        raise UnauthorizedException(
            message="Authorization header is required",
            code="UNAUTHORIZED"
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException(
            message="Invalid Authorization header format. Expected 'Bearer <token>'",
            code="INVALID_AUTH_HEADER"
        )

    token = parts[1].strip()
    if not token:
        raise UnauthorizedException(
            message="Bearer token is empty",
            code="UNAUTHORIZED"
        )

    # 1. Attempt verification via Supabase Auth API
    try:
        supabase = get_supabase_client()
        user_response = supabase.auth.get_user(token)
        if user_response and user_response.user:
            user = user_response.user
            return AuthenticatedUser(
                id=str(user.id),
                email=str(user.email or ""),
                token=token,
                user_metadata=user.user_metadata if hasattr(user, "user_metadata") else {},
            )
    except Exception:
        # Fall through to standalone JWT decoding (useful in test environments or direct JWT verification)
        pass

    # 2. Standalone JWT decode fallback (useful in test environments or direct JWT verification)
    try:
        payload = decode_jwt_token(token)
        user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
        email = payload.get("email") or payload.get("user_metadata", {}).get("email", "")

        if not user_id:
            raise UnauthorizedException(
                message="Invalid token payload: missing subject identifier",
                code="INVALID_TOKEN_PAYLOAD"
            )

        return AuthenticatedUser(
            id=str(user_id),
            email=str(email),
            token=token,
            user_metadata=payload.get("user_metadata", {}),
        )
    except UnauthorizedException:
        raise
    except Exception as e:
        raise UnauthorizedException(
            message=f"Could not validate credentials: {str(e)}",
            code="UNAUTHORIZED"
        )
