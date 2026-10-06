"""
Scholarship Pydantic schemas for request validation and structured API responses.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ScholarshipResponse(BaseModel):
    """Public representation of a scholarship scheme. Excludes internal database UUIDs."""
    scholarship_id: str = Field(..., description="Business ID (e.g. TRB-SCH-000001)")
    name: str = Field(..., description="Full scholarship name")
    short_name: str = Field(..., description="Code name (e.g. PRE_MATRIC, POST_MATRIC)")
    description: Optional[str] = Field(default=None, description="Scheme overview and benefits")
    scholarship_type: Optional[str] = Field(default=None, description="Category type")
    provider: Optional[str] = Field(default="Ministry of Tribal Affairs", description="Scheme provider")
    is_active: bool = Field(default=True, description="Scheme active status")


class ScholarshipListResponse(BaseModel):
    """List response envelope for scholarships."""
    scholarships: List[ScholarshipResponse] = Field(default_factory=list, description="List of scholarship schemes")
    count: int = Field(..., description="Total count of schemes returned")


class ScholarshipSummaryResponse(BaseModel):
    """Summary overview of scholarship schemes in the system."""
    total_scholarships: int = Field(..., description="Total scholarship schemes in the system")
    active_scholarships: int = Field(..., description="Currently active scholarship schemes")
