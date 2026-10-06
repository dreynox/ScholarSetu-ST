"""
Verification Pydantic schemas for student-scoped verification lookups and response envelopes.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class VerificationResponse(BaseModel):
    """Generic verification response representing either document or application verification."""
    verification_id: str = Field(..., description="Verification identifier")
    verification_type: str = Field(..., description="Entity type being verified ('DOCUMENT' or 'APPLICATION')")
    reference_id: str = Field(..., description="Target entity ID (e.g. TRB-DOC-000001 or TRB-APP-000001)")
    status: str = Field(..., description="Current verification status (PENDING, VERIFIED, APPROVED, REJECTED, FLAGGED)")
    verification_level: Optional[str] = Field(default=None, description="Review level (e.g. INSTITUTION, STATE, MINISTRY)")
    verified_at: Optional[datetime] = Field(default=None, description="Timestamp when verification occurred")
    verified_by: Optional[str] = Field(default=None, description="Verifier or Officer identifier")
    remarks: Optional[str] = Field(default=None, description="Feedback or reason provided by verifier")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VerificationListResponse(BaseModel):
    """List response envelope for student verification records."""
    verifications: List[VerificationResponse] = Field(default_factory=list, description="List of verifications")
    count: int = Field(..., description="Count of verification records")


class VerificationDetailResponse(BaseModel):
    """Detailed verification record response."""
    verification_id: str = Field(..., description="Verification identifier")
    verification_type: str = Field(..., description="Entity type being verified")
    reference_id: str = Field(..., description="Business ID of verified item")
    status: str = Field(..., description="Verification status")
    verification_level: Optional[str] = Field(default=None, description="Review level")
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
