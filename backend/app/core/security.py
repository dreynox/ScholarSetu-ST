"""
Security and JWT token verification helpers.
"""
from typing import Optional, Dict, Any
import jwt
from app.core.config import settings
from app.utils.errors import UnauthorizedException


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT token using configured secret or Supabase JWT secret.
    If JWT_SECRET is configured, performs cryptographic signature verification.
    """
    try:
        if settings.JWT_SECRET:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_aud": False}
            )
            return payload
        else:
            # Fallback decode without verification for metadata inspection when Supabase handles verification
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_aud": False}
            )
            return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(message="Token has expired", code="TOKEN_EXPIRED")
    except jwt.InvalidTokenError as e:
        raise UnauthorizedException(message=f"Invalid token: {str(e)}", code="INVALID_TOKEN")
