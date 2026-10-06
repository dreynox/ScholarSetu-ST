"""
Student Pydantic schemas for request validation, updates, and responses.
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator


class StudentCreate(BaseModel):
    """Schema for creating a student profile."""
    full_name: str = Field(..., min_length=2, max_length=200, description="Full name of the student")
    date_of_birth: Optional[date] = Field(default=None, description="Date of birth (YYYY-MM-DD)")
    gender: Optional[str] = Field(default=None, description="Gender (e.g. Male, Female, Other)")
    mobile_number: Optional[str] = Field(default=None, max_length=20, description="Contact mobile number")
    email: Optional[EmailStr] = Field(default=None, description="Email address (defaults to auth email if omitted)")
    tribal_category: Optional[str] = Field(default=None, description="Tribal category or PVTG name")
    state: Optional[str] = Field(default=None, description="State of domicile")
    district: Optional[str] = Field(default=None, description="District of domicile")
    otr_id: Optional[str] = Field(default=None, description="One-Time Registration ID if available")

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_cleaned = v.strip().replace(" ", "").replace("-", "")
            # Ensure not excessively long or containing invalid characters
            if len(v_cleaned) < 5 or len(v_cleaned) > 15:
                raise ValueError("Mobile number must be between 5 and 15 digits")
            return v_cleaned
        return v


class StudentUpdate(BaseModel):
    """Schema for updating current student profile. Protected fields are omitted."""
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    mobile_number: Optional[str] = None
    email: Optional[EmailStr] = None
    tribal_category: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    otr_id: Optional[str] = None

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_cleaned = v.strip().replace(" ", "").replace("-", "")
            if len(v_cleaned) < 5 or len(v_cleaned) > 15:
                raise ValueError("Mobile number must be between 5 and 15 digits")
            return v_cleaned
        return v


class StudentResponse(BaseModel):
    """Full representation of student profile."""
    id: Optional[str] = None
    student_id: Optional[str] = None
    auth_user_id: str
    otr_id: Optional[str] = None
    full_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    mobile_number: Optional[str] = None
    email: str
    tribal_category: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class StudentStatusResponse(BaseModel):
    """Profile existence and completeness status representation."""
    profile_exists: bool = Field(..., description="Whether a student profile has been created")
    student_id: Optional[str] = Field(default=None, description="Business Student ID if profile exists")
    profile_complete: bool = Field(..., description="Whether all essential profile fields are filled")
    missing_fields: List[str] = Field(default_factory=list, description="List of required fields missing completion")
