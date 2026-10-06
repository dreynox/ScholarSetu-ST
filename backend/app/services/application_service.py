"""
Application service managing operations on `tribe_applications` table.
"""
import re
import uuid
from datetime import date, datetime
from typing import List, Optional, Dict, Any

from app.db.supabase import get_supabase_service_client
from app.models.student import Student
from app.models.application import Application
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ScholarshipInfo,
    InstitutionInfo,
)
from app.utils.errors import (
    NotFoundException,
    ConflictException,
    AppException,
    ValidationException,
)


class ApplicationService:
    """Service for managing scholarship applications in tribe_applications."""

    APPLICATIONS_TABLE = "tribe_applications"
    STUDENTS_TABLE = "tribe_students"
    SCHOLARSHIPS_TABLE = "tribe_scholarships"
    INSTITUTIONS_TABLE = "tribe_institutions"

    @classmethod
    def _resolve_student(cls, auth_user_id: str) -> Student:
        """
        Derives the student profile from the authenticated user's token UUID.
        Never trusts client-supplied student identifiers.
        """
        supabase = get_supabase_service_client()
        try:
            response = supabase.table(cls.STUDENTS_TABLE)\
                .select("*")\
                .eq("auth_user_id", auth_user_id)\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message="Student profile not found. Please create your student profile before applying for scholarships.",
                    code="STUDENT_NOT_FOUND"
                )

            return Student.model_validate(response.data[0])
        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to resolve student profile: {str(e)}"
            )

    @classmethod
    def _resolve_scholarship(cls, scholarship_ident: str) -> Dict[str, Any]:
        """
        Resolves scholarship business ID or UUID to database record.
        Ensures scheme is active.
        """
        clean_id = scholarship_ident.strip()
        supabase = get_supabase_service_client()
        try:
            response = supabase.table(cls.SCHOLARSHIPS_TABLE)\
                .select("*")\
                .or_(f"scholarship_id.eq.{clean_id},id.eq.{clean_id}")\
                .eq("is_active", True)\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message=f"Active scholarship scheme '{clean_id}' not found.",
                    code="SCHOLARSHIP_NOT_FOUND"
                )

            return response.data[0]
        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to resolve scholarship: {str(e)}"
            )

    @classmethod
    def _resolve_institution(cls, institution_ident: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Resolves institution business ID or UUID to database record.
        """
        if not institution_ident or not institution_ident.strip():
            return None

        clean_id = institution_ident.strip()
        supabase = get_supabase_service_client()
        try:
            response = supabase.table(cls.INSTITUTIONS_TABLE)\
                .select("*")\
                .or_(f"institution_id.eq.{clean_id},id.eq.{clean_id}")\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message=f"Institution '{clean_id}' not found.",
                    code="INSTITUTION_NOT_FOUND"
                )

            return response.data[0]
        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to resolve institution: {str(e)}"
            )

    @classmethod
    def _generate_application_id(cls) -> str:
        """
        Generates unique business application ID (e.g. TRB-APP-000001).
        Uses a collision-resilient sequential + check strategy.
        """
        supabase = get_supabase_service_client()
        try:
            # Query the recent application IDs to find the current sequence number
            response = supabase.table(cls.APPLICATIONS_TABLE)\
                .select("application_id")\
                .order("created_at", desc=True)\
                .limit(100)\
                .execute()

            max_num = 0
            if response.data:
                for row in response.data:
                    app_id_str = row.get("application_id", "")
                    match = re.search(r"TRB-APP-(\d+)", app_id_str)
                    if match:
                        num = int(match.group(1))
                        if num > max_num:
                            max_num = num

            # Try generating the next sequential ID with verification
            for attempt in range(1, 10):
                candidate_num = max_num + attempt
                candidate_id = f"TRB-APP-{candidate_num:06d}"
                
                # Check uniqueness
                check = supabase.table(cls.APPLICATIONS_TABLE)\
                    .select("id")\
                    .eq("application_id", candidate_id)\
                    .execute()

                if not check.data or len(check.data) == 0:
                    return candidate_id

            # Fallback to random hex suffix if sequence range is congested
            random_suffix = uuid.uuid4().hex[:6].upper()
            return f"TRB-APP-{random_suffix}"
        except Exception:
            # Safe fallback on any error
            random_suffix = uuid.uuid4().hex[:6].upper()
            return f"TRB-APP-{random_suffix}"

    @classmethod
    def _build_application_response(
        cls,
        app_record: Dict[str, Any],
        scholarship_record: Optional[Dict[str, Any]] = None,
        institution_record: Optional[Dict[str, Any]] = None,
    ) -> ApplicationResponse:
        """
        Formats internal database application record into clean public response schema.
        Never leaks internal database UUIDs.
        """
        supabase = get_supabase_service_client()

        # Fetch scholarship if not already supplied
        if not scholarship_record and app_record.get("scholarship_id"):
            try:
                s_res = supabase.table(cls.SCHOLARSHIPS_TABLE)\
                    .select("scholarship_id, name, short_name, scholarship_type")\
                    .eq("id", app_record["scholarship_id"])\
                    .execute()
                if s_res.data and len(s_res.data) > 0:
                    scholarship_record = s_res.data[0]
            except Exception:
                pass

        # Fetch institution if not already supplied
        if not institution_record and app_record.get("institution_id"):
            try:
                i_res = supabase.table(cls.INSTITUTIONS_TABLE)\
                    .select("institution_id, name, code, state, district")\
                    .eq("id", app_record["institution_id"])\
                    .execute()
                if i_res.data and len(i_res.data) > 0:
                    institution_record = i_res.data[0]
            except Exception:
                pass

        scholarship_info = ScholarshipInfo(
            scholarship_id=scholarship_record.get("scholarship_id", "UNKNOWN") if scholarship_record else "UNKNOWN",
            name=scholarship_record.get("name", "Unknown Scholarship") if scholarship_record else "Unknown Scholarship",
            short_name=scholarship_record.get("short_name") if scholarship_record else None,
            scholarship_type=scholarship_record.get("scholarship_type") if scholarship_record else None,
        )

        institution_info = None
        if institution_record:
            institution_info = InstitutionInfo(
                institution_id=institution_record.get("institution_id"),
                name=institution_record.get("name"),
                code=institution_record.get("code"),
                state=institution_record.get("state"),
                district=institution_record.get("district"),
            )

        app_date = app_record.get("application_date")
        if isinstance(app_date, str):
            try:
                app_date = date.fromisoformat(app_date)
            except ValueError:
                app_date = None

        created_at_dt = None
        if app_record.get("created_at"):
            try:
                created_at_dt = datetime.fromisoformat(app_record["created_at"].replace("Z", "+00:00"))
            except Exception:
                created_at_dt = None

        updated_at_dt = None
        if app_record.get("updated_at"):
            try:
                updated_at_dt = datetime.fromisoformat(app_record["updated_at"].replace("Z", "+00:00"))
            except Exception:
                updated_at_dt = None

        submitted_at_dt = None
        if app_record.get("submitted_at"):
            try:
                submitted_at_dt = datetime.fromisoformat(app_record["submitted_at"].replace("Z", "+00:00"))
            except Exception:
                submitted_at_dt = None

        sanctioned_at_dt = None
        if app_record.get("sanctioned_at"):
            try:
                sanctioned_at_dt = datetime.fromisoformat(app_record["sanctioned_at"].replace("Z", "+00:00"))
            except Exception:
                sanctioned_at_dt = None

        rejected_at_dt = None
        if app_record.get("rejected_at"):
            try:
                rejected_at_dt = datetime.fromisoformat(app_record["rejected_at"].replace("Z", "+00:00"))
            except Exception:
                rejected_at_dt = None

        return ApplicationResponse(
            application_id=app_record["application_id"],
            scholarship=scholarship_info,
            institution=institution_info,
            academic_year=app_record["academic_year"],
            status=app_record.get("status", "DRAFT"),
            current_stage=app_record.get("current_stage", "APPLICATION"),
            application_date=app_date,
            submitted_at=submitted_at_dt,
            sanctioned_at=sanctioned_at_dt,
            rejected_at=rejected_at_dt,
            rejection_reason=app_record.get("rejection_reason"),
            created_at=created_at_dt,
            updated_at=updated_at_dt,
        )

    @classmethod
    def create_application(cls, auth_user_id: str, payload: ApplicationCreate) -> ApplicationResponse:
        """
        Creates a new draft scholarship application for the authenticated student.
        Validates scholarship existence, institution existence, academic year format, and duplicate protection.
        """
        # 1. Resolve student identity strictly from token
        student = cls._resolve_student(auth_user_id)

        # 2. Resolve scholarship business ID to database record
        scholarship = cls._resolve_scholarship(payload.scholarship_id)

        # 3. Resolve institution business ID if provided
        institution = cls._resolve_institution(payload.institution_id)

        supabase = get_supabase_service_client()

        # 4. Duplicate Application Protection
        try:
            existing = supabase.table(cls.APPLICATIONS_TABLE)\
                .select("id, application_id")\
                .eq("student_id", student.id)\
                .eq("scholarship_id", scholarship["id"])\
                .eq("academic_year", payload.academic_year)\
                .execute()

            if existing.data and len(existing.data) > 0:
                raise ConflictException(
                    message="You already have an application for this scholarship and academic year.",
                    code="DUPLICATE_APPLICATION"
                )
        except ConflictException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to check duplicate application: {str(e)}"
            )

        # 5. Generate unique business Application ID
        app_id = cls._generate_application_id()

        # 6. Insert new application record with defaults
        data_to_insert = {
            "application_id": app_id,
            "student_id": student.id,
            "scholarship_id": scholarship["id"],
            "institution_id": institution["id"] if institution else None,
            "academic_year": payload.academic_year,
            "application_date": date.today().isoformat(),
            "status": "DRAFT",
            "current_stage": "APPLICATION",
            "submitted_at": None,
            "sanctioned_at": None,
            "rejected_at": None,
            "rejection_reason": None,
        }

        try:
            insert_resp = supabase.table(cls.APPLICATIONS_TABLE).insert(data_to_insert).execute()
            if not insert_resp.data or len(insert_resp.data) == 0:
                raise AppException(
                    status_code=500,
                    code="INSERT_FAILED",
                    message="Failed to insert application record."
                )

            created_record = insert_resp.data[0]
            return cls._build_application_response(
                app_record=created_record,
                scholarship_record=scholarship,
                institution_record=institution,
            )
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Database application creation failed: {str(e)}"
            )

    @classmethod
    def get_my_applications(cls, auth_user_id: str) -> List[ApplicationResponse]:
        """
        Retrieves all scholarship applications belonging exclusively to the authenticated student.
        """
        student = cls._resolve_student(auth_user_id)
        supabase = get_supabase_service_client()

        try:
            response = supabase.table(cls.APPLICATIONS_TABLE)\
                .select("*")\
                .eq("student_id", student.id)\
                .order("created_at", desc=True)\
                .execute()

            records = response.data or []
            return [cls._build_application_response(rec) for rec in records]
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch student applications: {str(e)}"
            )

    @classmethod
    def get_my_application_by_id(cls, auth_user_id: str, application_id: str) -> ApplicationResponse:
        """
        Retrieves a specific application by business ID or UUID.
        Enforces strict ownership: returns 404 NOT FOUND if not owned by authenticated student.
        """
        student = cls._resolve_student(auth_user_id)
        clean_id = application_id.strip()
        supabase = get_supabase_service_client()

        try:
            response = supabase.table(cls.APPLICATIONS_TABLE)\
                .select("*")\
                .or_(f"application_id.eq.{clean_id},id.eq.{clean_id}")\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message="Application not found.",
                    code="APPLICATION_NOT_FOUND"
                )

            rec = response.data[0]

            # Enforce strict ownership: Return 404 to avoid leaking existence of other student's records
            if rec.get("student_id") != student.id:
                raise NotFoundException(
                    message="Application not found.",
                    code="APPLICATION_NOT_FOUND"
                )

            return cls._build_application_response(rec)
        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch application: {str(e)}"
            )

    @classmethod
    def update_draft_application(
        cls, auth_user_id: str, application_id: str, payload: ApplicationUpdate
    ) -> ApplicationResponse:
        """
        Updates allowable fields for a draft application owned by authenticated student.
        Only DRAFT status applications can be updated.
        """
        student = cls._resolve_student(auth_user_id)
        clean_id = application_id.strip()
        supabase = get_supabase_service_client()

        # 1. Fetch existing application record
        try:
            response = supabase.table(cls.APPLICATIONS_TABLE)\
                .select("*")\
                .or_(f"application_id.eq.{clean_id},id.eq.{clean_id}")\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message="Application not found.",
                    code="APPLICATION_NOT_FOUND"
                )

            rec = response.data[0]

            # Ownership verification
            if rec.get("student_id") != student.id:
                raise NotFoundException(
                    message="Application not found.",
                    code="APPLICATION_NOT_FOUND"
                )

            # Draft status restriction
            if rec.get("status") != "DRAFT":
                raise AppException(
                    status_code=400,
                    code="APPLICATION_NOT_EDITABLE",
                    message="Only draft applications can be modified."
                )

        except (NotFoundException, AppException):
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to verify application for update: {str(e)}"
            )

        # 2. Determine updated values
        target_scholarship_id = rec.get("scholarship_id")
        scholarship_record = None
        if payload.scholarship_id:
            scholarship_record = cls._resolve_scholarship(payload.scholarship_id)
            target_scholarship_id = scholarship_record["id"]

        target_academic_year = payload.academic_year if payload.academic_year else rec.get("academic_year")

        target_institution_id = rec.get("institution_id")
        institution_record = None
        if payload.institution_id is not None:
            if payload.institution_id.strip() == "":
                target_institution_id = None
            else:
                institution_record = cls._resolve_institution(payload.institution_id)
                target_institution_id = institution_record["id"] if institution_record else None

        # 3. Duplicate check if scholarship or academic_year is modified
        if (target_scholarship_id != rec.get("scholarship_id")) or (target_academic_year != rec.get("academic_year")):
            try:
                dup_check = supabase.table(cls.APPLICATIONS_TABLE)\
                    .select("id")\
                    .eq("student_id", student.id)\
                    .eq("scholarship_id", target_scholarship_id)\
                    .eq("academic_year", target_academic_year)\
                    .neq("id", rec["id"])\
                    .execute()

                if dup_check.data and len(dup_check.data) > 0:
                    raise ConflictException(
                        message="You already have an application for this scholarship and academic year.",
                        code="DUPLICATE_APPLICATION"
                    )
            except ConflictException:
                raise
            except Exception as e:
                raise AppException(
                    status_code=500,
                    code="DATABASE_ERROR",
                    message=f"Failed to check duplicate during update: {str(e)}"
                )

        # 4. Perform database update
        update_data: Dict[str, Any] = {}
        if payload.scholarship_id:
            update_data["scholarship_id"] = target_scholarship_id
        if payload.academic_year:
            update_data["academic_year"] = target_academic_year
        if payload.institution_id is not None:
            update_data["institution_id"] = target_institution_id

        if not update_data:
            return cls._build_application_response(rec)

        try:
            update_resp = supabase.table(cls.APPLICATIONS_TABLE)\
                .update(update_data)\
                .eq("id", rec["id"])\
                .eq("student_id", student.id)\
                .execute()

            if not update_resp.data or len(update_resp.data) == 0:
                raise AppException(
                    status_code=500,
                    code="UPDATE_FAILED",
                    message="Failed to update application."
                )

            updated_record = update_resp.data[0]
            return cls._build_application_response(
                app_record=updated_record,
                scholarship_record=scholarship_record,
                institution_record=institution_record,
            )
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Database application update failed: {str(e)}"
            )

    @classmethod
    def delete_draft_application(cls, auth_user_id: str, application_id: str) -> str:
        """
        Safely deletes a draft application owned by the authenticated student.
        Non-draft applications cannot be deleted.
        """
        student = cls._resolve_student(auth_user_id)
        clean_id = application_id.strip()
        supabase = get_supabase_service_client()

        # 1. Fetch existing application record
        try:
            response = supabase.table(cls.APPLICATIONS_TABLE)\
                .select("*")\
                .or_(f"application_id.eq.{clean_id},id.eq.{clean_id}")\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message="Application not found.",
                    code="APPLICATION_NOT_FOUND"
                )

            rec = response.data[0]

            # Ownership verification
            if rec.get("student_id") != student.id:
                raise NotFoundException(
                    message="Application not found.",
                    code="APPLICATION_NOT_FOUND"
                )

            # Draft status restriction
            if rec.get("status") != "DRAFT":
                raise AppException(
                    status_code=400,
                    code="APPLICATION_NOT_DELETABLE",
                    message="Only draft applications can be deleted."
                )

        except (NotFoundException, AppException):
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to verify application for deletion: {str(e)}"
            )

        # 2. Perform safe deletion
        try:
            del_resp = supabase.table(cls.APPLICATIONS_TABLE)\
                .delete()\
                .eq("id", rec["id"])\
                .eq("student_id", student.id)\
                .eq("status", "DRAFT")\
                .execute()

            return rec["application_id"]
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to delete draft application: {str(e)}"
            )


application_service = ApplicationService()
