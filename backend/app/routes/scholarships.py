"""
Scholarship endpoints for discovering and retrieving scholarship schemes.
Public read-only endpoints (Section 5).
"""
from typing import Optional
from fastapi import APIRouter, Query, status
from app.schemas.scholarship import (
    ScholarshipResponse,
    ScholarshipListResponse,
    ScholarshipSummaryResponse,
)
from app.services.scholarship_service import scholarship_service

router = APIRouter(prefix="/scholarships", tags=["Scholarships"])


@router.get(
    "",
    response_model=ScholarshipListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all active scholarships",
    description="Returns a list of all currently active MoTA scholarship schemes available for students to apply.",
)
async def get_all_scholarships():
    """
    Returns list of active scholarship schemes.
    """
    results = scholarship_service.get_all_active_scholarships()
    return ScholarshipListResponse(
        scholarships=results,
        count=len(results)
    )


@router.get(
    "/summary",
    response_model=ScholarshipSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get scholarship overview summary",
    description="Returns aggregate counts of total and active scholarship schemes in the system.",
)
async def get_scholarship_summary():
    """
    Returns basic database summary of scholarship schemes.
    """
    return scholarship_service.get_scholarship_summary()


@router.get(
    "/search",
    response_model=ScholarshipListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search scholarships",
    description="Searches active scholarships matching name, code, description, or type using safe ILIKE filtering.",
)
async def search_scholarships(
    q: str = Query(..., min_length=1, max_length=100, description="Search query string")
):
    """
    Searches active scholarships by term.
    """
    results = scholarship_service.search_scholarships(q)
    return ScholarshipListResponse(
        scholarships=results,
        count=len(results)
    )


@router.get(
    "/code/{short_name}",
    response_model=ScholarshipResponse,
    status_code=status.HTTP_200_OK,
    summary="Get scholarship by short name code",
    description="Retrieves active scholarship scheme matching the short code (e.g. PRE_MATRIC, POST_MATRIC, TOP_CLASS).",
)
async def get_scholarship_by_code(short_name: str):
    """
    Returns scholarship matching short_name code.
    """
    return scholarship_service.get_scholarship_by_short_name(short_name)


@router.get(
    "/{scholarship_id}",
    response_model=ScholarshipResponse,
    status_code=status.HTTP_200_OK,
    summary="Get scholarship by ID",
    description="Retrieves details for a specific scholarship using its business identifier (e.g. TRB-SCH-000001).",
)
async def get_scholarship_by_id(scholarship_id: str):
    """
    Returns scholarship details by business ID.
    """
    return scholarship_service.get_scholarship_by_business_id(scholarship_id)
