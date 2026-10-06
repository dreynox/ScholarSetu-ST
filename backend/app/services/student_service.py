"""
Student service managing operations on `tribe_students` table.
"""
import uuid
from typing import Optional, List, Dict, Any
from app.db.supabase import get_supabase_service_client, get_supabase_client
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate, StudentStatusResponse, StudentResponse
from app.utils.errors import NotFoundException, ConflictException, ForbiddenException, AppException


class StudentService:
    """Service for querying, creating, and updating student profiles in tribe_students."""

    TABLE_NAME = "tribe_students"

    @staticmethod
    def _generate_student_id() -> str:
        """Generates a business student identifier (e.g. TRB-STU-4F8A91)."""
        suffix = uuid.uuid4().hex[:6].upper()
        return f"TRB-STU-{suffix}"

    @classmethod
    def get_student_by_auth_user_id(cls, auth_user_id: str) -> Student:
        """
        Retrieves student profile linked to the authenticated user's UUID.
        """
        supabase = get_supabase_service_client()
        try:
            response = supabase.table(cls.TABLE_NAME)\
                .select("*")\
                .eq("auth_user_id", auth_user_id)\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message="Student profile not found",
                    code="STUDENT_NOT_FOUND"
                )

            return Student.model_validate(response.data[0])
        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch student profile: {str(e)}"
            )

    @classmethod
    def create_student_profile(
        cls, auth_user_id: str, default_email: str, payload: StudentCreate
    ) -> Student:
        """
        Creates a new student profile in `tribe_students` associated with the authenticated user.
        Ensures 1-to-1 mapping and generates a unique student_id.
        """
        supabase = get_supabase_service_client()

        # Check if a student profile already exists for this auth_user_id
        try:
            existing = supabase.table(cls.TABLE_NAME)\
                .select("id, student_id")\
                .eq("auth_user_id", auth_user_id)\
                .execute()

            if existing.data and len(existing.data) > 0:
                raise ConflictException(
                    message="Student profile already exists for this account.",
                    code="PROFILE_ALREADY_EXISTS"
                )
        except ConflictException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to verify existing profile: {str(e)}"
            )

        student_id = cls._generate_student_id()
        email_to_use = str(payload.email) if payload.email else default_email

        data_to_insert = {
            "student_id": student_id,
            "auth_user_id": auth_user_id,
            "otr_id": payload.otr_id,
            "full_name": payload.full_name,
            "date_of_birth": payload.date_of_birth.isoformat() if payload.date_of_birth else None,
            "gender": payload.gender,
            "mobile_number": payload.mobile_number,
            "email": email_to_use,
            "tribal_category": payload.tribal_category,
            "state": payload.state,
            "district": payload.district,
            "is_active": True,
        }

        try:
            response = supabase.table(cls.TABLE_NAME).insert(data_to_insert).execute()
            if not response.data or len(response.data) == 0:
                raise AppException(
                    status_code=500,
                    code="INSERT_FAILED",
                    message="Failed to create student profile record."
                )
            return Student.model_validate(response.data[0])
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Database insertion failed: {str(e)}"
            )

    @classmethod
    def update_student_profile(cls, auth_user_id: str, payload: StudentUpdate) -> Student:
        """
        Updates allowable fields for the authenticated student's profile.
        Protected fields cannot be modified.
        """
        # Verify student exists
        current_student = cls.get_student_by_auth_user_id(auth_user_id)

        update_data: Dict[str, Any] = payload.model_dump(exclude_unset=True)

        if "date_of_birth" in update_data and update_data["date_of_birth"] is not None:
            update_data["date_of_birth"] = update_data["date_of_birth"].isoformat()

        if "email" in update_data and update_data["email"] is not None:
            update_data["email"] = str(update_data["email"])

        if not update_data:
            return current_student

        supabase = get_supabase_service_client()
        try:
            response = supabase.table(cls.TABLE_NAME)\
                .update(update_data)\
                .eq("auth_user_id", auth_user_id)\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message="Student profile not found for update.",
                    code="STUDENT_NOT_FOUND"
                )

            return Student.model_validate(response.data[0])
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to update profile: {str(e)}"
            )

    @classmethod
    def get_student_by_student_id(cls, auth_user_id: str, target_student_id: str) -> Student:
        """
        Retrieves student by business student_id or UUID id.
        Enforces strict ownership check: student cannot view another student's profile.
        """
        supabase = get_supabase_service_client()
        try:
            # Query by business student_id OR UUID id
            response = supabase.table(cls.TABLE_NAME)\
                .select("*")\
                .or_(f"student_id.eq.{target_student_id},id.eq.{target_student_id}")\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message="Student profile not found",
                    code="STUDENT_NOT_FOUND"
                )

            record = response.data[0]
            student = Student.model_validate(record)

            # Ownership security check (Section 11 & 12)
            if student.auth_user_id != auth_user_id:
                raise ForbiddenException(
                    message="Access denied: You are not authorized to view this profile.",
                    code="FORBIDDEN"
                )

            return student
        except (NotFoundException, ForbiddenException):
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch student profile: {str(e)}"
            )

    @classmethod
    def get_profile_status(cls, auth_user_id: str) -> StudentStatusResponse:
        """
        Checks if a profile exists and determines profile completeness.
        """
        supabase = get_supabase_service_client()
        try:
            response = supabase.table(cls.TABLE_NAME)\
                .select("*")\
                .eq("auth_user_id", auth_user_id)\
                .execute()

            if not response.data or len(response.data) == 0:
                return StudentStatusResponse(
                    profile_exists=False,
                    student_id=None,
                    profile_complete=False,
                    missing_fields=[
                        "full_name",
                        "date_of_birth",
                        "gender",
                        "tribal_category",
                        "state",
                        "district",
                        "mobile_number"
                    ]
                )

            record = response.data[0]
            essential_fields = [
                "full_name",
                "date_of_birth",
                "gender",
                "tribal_category",
                "state",
                "district",
                "mobile_number"
            ]

            missing = [f for f in essential_fields if not record.get(f)]

            return StudentStatusResponse(
                profile_exists=True,
                student_id=record.get("student_id"),
                profile_complete=len(missing) == 0,
                missing_fields=missing
            )
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to check profile status: {str(e)}"
            )


student_service = StudentService()
