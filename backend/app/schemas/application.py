"""
Application Pydantic schemas for request validation, updates, and structured responses.
"""
import re
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


def validate_academic_year_format(v: Optional[str]) -> Optional[str]:
    """Validates that academic year follows YYYY-YY standard (e.g. 2026-27)."""
    if v is None:
        return v
    v_clean = v.strip()
    if not re.match(r"^\d{4}-\d{2}$", v_clean):
        raise ValueError("Academic year must be in format YYYY-YY (e.g. 2026-27)")
    
    parts = v_clean.split("-")
    start_year = int(parts[0])
    end_year = int(parts[1])
    expected_end = (start_year + 1) % 100
    if end_year != expected_end:
        raise ValueError(f"Invalid academic year '{v_clean}'. Expected next consecutive year ending in '{expected_end:02d}'.")
    return v_clean


class ScholarshipInfo(BaseModel):
    """Embedded public scholarship information in application responses."""
    scholarship_id: str = Field(..., description="Scholarship business ID (e.g. TRB-SCH-000001)")
    name: str = Field(..., description="Scholarship scheme name")
    short_name: Optional[str] = Field(default=None, description="Scholarship short name code")
    scholarship_type: Optional[str] = Field(default=None, description="Scholarship type")


class InstitutionInfo(BaseModel):
    """Embedded public institution information in application responses."""
    institution_id: Optional[str] = Field(default=None, description="Institution business ID (e.g. TRB-INS-000001)")
    name: Optional[str] = Field(default=None, description="Institution name")
    code: Optional[str] = Field(default=None, description="Institution AISHE/DISE code")
    state: Optional[str] = Field(default=None, description="Institution state")
    district: Optional[str] = Field(default=None, description="Institution district")


class ApplicationCreate(BaseModel):
    """Request schema for creating a new scholarship application."""
    scholarship_id: str = Field(..., min_length=1, max_length=100, description="Scholarship Business ID (e.g. TRB-SCH-000001) or UUID")
    institution_id: Optional[str] = Field(default=None, max_length=100, description="Institution Business ID (e.g. TRB-INS-000001) or UUID")
    academic_year: str = Field(..., description="Academic year (e.g. 2026-27)")

    @field_validator("academic_year")
    @classmethod
    def check_academic_year(cls, v: str) -> str:
        res = validate_academic_year_format(v)
        assert res is not None
        return res


class ApplicationUpdate(BaseModel):
    """Request schema for updating a draft application. Protected fields cannot be modified."""
    scholarship_id: Optional[str] = Field(default=None, min_length=1, max_length=100)
    institution_id: Optional[str] = Field(default=None, max_length=100)
    academic_year: Optional[str] = Field(default=None)

    @field_validator("academic_year")
    @classmethod
    def check_academic_year(cls, v: Optional[str]) -> Optional[str]:
        return validate_academic_year_format(v)


class ApplicationResponse(BaseModel):
    """Public representation of an application record."""
    application_id: str = Field(..., description="Unique Business ID (e.g. TRB-APP-000001)")
    scholarship: ScholarshipInfo = Field(..., description="Associated scholarship details")
    institution: Optional[InstitutionInfo] = Field(default=None, description="Associated institution details")
    academic_year: str = Field(..., description="Academic year")
    status: str = Field(..., description="Current status (e.g. DRAFT, SUBMITTED)")
    current_stage: str = Field(..., description="Current workflow stage")
    application_date: Optional[date] = Field(default=None, description="Date application was initiated")
    submitted_at: Optional[datetime] = Field(default=None, description="Submission timestamp")
    sanctioned_at: Optional[datetime] = Field(default=None, description="Sanction timestamp")
    rejected_at: Optional[datetime] = Field(default=None, description="Rejection timestamp")
    rejection_reason: Optional[str] = Field(default=None, description="Rejection rationale")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


class ApplicationListResponse(BaseModel):
    """List response envelope for student applications."""
    applications: List[ApplicationResponse] = Field(default_factory=list, description="List of applications")
    count: int = Field(..., description="Count of applications")


class ApplicationDeleteResponse(BaseModel):
    """Response returned upon successful deletion of a draft application."""
    message: str = Field(default="Draft application deleted successfully")
    application_id: str = Field(..., description="Deleted application ID")
