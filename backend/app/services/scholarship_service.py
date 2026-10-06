"""
Scholarship service managing operations on `tribe_scholarships` table.
"""
from typing import List, Optional
from app.db.supabase import get_supabase_service_client
from app.models.scholarship import Scholarship
from app.schemas.scholarship import ScholarshipResponse, ScholarshipSummaryResponse
from app.utils.errors import NotFoundException, ValidationException, AppException


class ScholarshipService:
    """Service for querying scholarship schemes in tribe_scholarships."""

    TABLE_NAME = "tribe_scholarships"

    @classmethod
    def get_all_active_scholarships(cls) -> List[ScholarshipResponse]:
        """
        Retrieves all active scholarship schemes from `tribe_scholarships`.
        """
        supabase = get_supabase_service_client()
        try:
            response = supabase.table(cls.TABLE_NAME)\
                .select("*")\
                .eq("is_active", True)\
                .order("scholarship_id")\
                .execute()

            records = response.data or []
            return [
                ScholarshipResponse(
                    scholarship_id=rec["scholarship_id"],
                    name=rec["name"],
                    short_name=rec["short_name"],
                    description=rec.get("description"),
                    scholarship_type=rec.get("scholarship_type"),
                    provider=rec.get("provider", "Ministry of Tribal Affairs"),
                    is_active=rec.get("is_active", True),
                )
                for rec in records
            ]
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch scholarships: {str(e)}"
            )

    @classmethod
    def get_scholarship_by_business_id(cls, scholarship_id: str) -> ScholarshipResponse:
        """
        Retrieves a scholarship by its business ID (e.g. TRB-SCH-000001) or UUID.
        """
        clean_id = scholarship_id.strip()
        supabase = get_supabase_service_client()
        try:
            response = supabase.table(cls.TABLE_NAME)\
                .select("*")\
                .or_(f"scholarship_id.eq.{clean_id},id.eq.{clean_id}")\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message=f"Scholarship '{clean_id}' not found.",
                    code="SCHOLARSHIP_NOT_FOUND"
                )

            rec = response.data[0]
            return ScholarshipResponse(
                scholarship_id=rec["scholarship_id"],
                name=rec["name"],
                short_name=rec["short_name"],
                description=rec.get("description"),
                scholarship_type=rec.get("scholarship_type"),
                provider=rec.get("provider", "Ministry of Tribal Affairs"),
                is_active=rec.get("is_active", True),
            )
        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch scholarship: {str(e)}"
            )

    @classmethod
    def get_scholarship_by_short_name(cls, short_name: str) -> ScholarshipResponse:
        """
        Retrieves an active scholarship by its short_name code (e.g. PRE_MATRIC, POST_MATRIC).
        """
        clean_code = short_name.strip()
        supabase = get_supabase_service_client()
        try:
            response = supabase.table(cls.TABLE_NAME)\
                .select("*")\
                .ilike("short_name", clean_code)\
                .eq("is_active", True)\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message=f"Scholarship with code '{clean_code}' not found.",
                    code="SCHOLARSHIP_NOT_FOUND"
                )

            rec = response.data[0]
            return ScholarshipResponse(
                scholarship_id=rec["scholarship_id"],
                name=rec["name"],
                short_name=rec["short_name"],
                description=rec.get("description"),
                scholarship_type=rec.get("scholarship_type"),
                provider=rec.get("provider", "Ministry of Tribal Affairs"),
                is_active=rec.get("is_active", True),
            )
        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch scholarship by code: {str(e)}"
            )

    @classmethod
    def search_scholarships(cls, query: str) -> List[ScholarshipResponse]:
        """
        Searches active scholarships matching the query in name, short_name, description, or type.
        """
        if not query or not query.strip():
            raise ValidationException(
                message="Search query cannot be empty.",
                code="INVALID_QUERY"
            )

        q_clean = query.strip()
        if len(q_clean) > 100:
            raise ValidationException(
                message="Search query is too long. Maximum allowed length is 100 characters.",
                code="INVALID_QUERY"
            )

        # Sanitize commas and backslashes that could corrupt PostgREST filter string
        sanitized_q = q_clean.replace(",", " ").replace("\\", "")

        supabase = get_supabase_service_client()
        try:
            response = supabase.table(cls.TABLE_NAME)\
                .select("*")\
                .or_(f"name.ilike.%{sanitized_q}%,short_name.ilike.%{sanitized_q}%,description.ilike.%{sanitized_q}%,scholarship_type.ilike.%{sanitized_q}%")\
                .eq("is_active", True)\
                .order("scholarship_id")\
                .execute()

            records = response.data or []
            return [
                ScholarshipResponse(
                    scholarship_id=rec["scholarship_id"],
                    name=rec["name"],
                    short_name=rec["short_name"],
                    description=rec.get("description"),
                    scholarship_type=rec.get("scholarship_type"),
                    provider=rec.get("provider", "Ministry of Tribal Affairs"),
                    is_active=rec.get("is_active", True),
                )
                for rec in records
            ]
        except ValidationException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to search scholarships: {str(e)}"
            )

    @classmethod
    def get_scholarship_summary(cls) -> ScholarshipSummaryResponse:
        """
        Provides summary count of all and active scholarship schemes.
        """
        supabase = get_supabase_service_client()
        try:
            total_resp = supabase.table(cls.TABLE_NAME).select("id, is_active").execute()
            records = total_resp.data or []
            total_count = len(records)
            active_count = sum(1 for r in records if r.get("is_active") is True)

            return ScholarshipSummaryResponse(
                total_scholarships=total_count,
                active_scholarships=active_count,
            )
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to calculate scholarship summary: {str(e)}"
            )


scholarship_service = ScholarshipService()
