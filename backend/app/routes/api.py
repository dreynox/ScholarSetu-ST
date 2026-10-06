"""
Base API Router providing base information for /api/v1.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("", summary="API Root Info")
@router.get("/", summary="API Root Info")
async def get_api_info():
    """
    Returns base API information for MoTA Scholarship API v1.
    """
    return {
        "message": "MoTA Scholarship API",
        "version": "1.0.0"
    }
