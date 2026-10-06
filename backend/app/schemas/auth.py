"""
Authentication Pydantic schemas for request validation and response formatting.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Registration request payload."""
    email: EmailStr = Field(..., description="Student email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    full_name: str = Field(..., min_length=1, max_length=200, description="Full name of student")


class LoginRequest(BaseModel):
    """Login request payload."""
    email: EmailStr = Field(..., description="Registered student email")
    password: str = Field(..., min_length=1, description="Account password")


class UserResponse(BaseModel):
    """Authenticated user info."""
    user_id: str = Field(..., description="Supabase auth UUID")
    email: EmailStr = Field(..., description="User email")
    user_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadata from auth provider")


class AuthResponse(BaseModel):
    """Authentication response payload containing tokens and user profile."""
    access_token: Optional[str] = Field(default=None, description="JWT Bearer access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: Optional[int] = Field(default=None, description="Token validity duration in seconds")
    refresh_token: Optional[str] = Field(default=None, description="Refresh token")
    user: UserResponse = Field(..., description="User identity details")
