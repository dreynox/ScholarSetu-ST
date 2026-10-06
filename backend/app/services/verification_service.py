"""
Verification service managing lookups across `tribe_document_verifications` and `tribe_verifications` tables.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.db.supabase import get_supabase_service_client
from app.models.student import Student
from app.schemas.verification import (
    VerificationResponse,
    VerificationDetailResponse,
)
from app.utils.errors import (
    NotFoundException,
    ForbiddenException,
    AppException,
)


class VerificationService:
    """Service for querying verification statuses for student applications and documents."""

    STUDENTS_TABLE = "tribe_students"
    APPLICATIONS_TABLE = "tribe_applications"
    DOCUMENTS_TABLE = "tribe_documents"
    APP_VERIFICATIONS_TABLE = "tribe_verifications"
    DOC_VERIFICATIONS_TABLE = "tribe_document_verifications"

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
                    message="Student profile not found. Please create your profile first.",
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
    def get_my_verifications(cls, auth_user_id: str) -> List[VerificationResponse]:
        """
        Retrieves all verification records belonging to the authenticated student
        (both document verifications and application verifications).
        """
        student = cls._resolve_student(auth_user_id)
        supabase = get_supabase_service_client()
        results: List[VerificationResponse] = []

        # 1. Fetch student's documents
        try:
            docs_resp = supabase.table(cls.DOCUMENTS_TABLE)\
                .select("id, document_id, document_type, document_name")\
                .eq("student_id", student.id)\
                .eq("is_active", True)\
                .execute()

            docs_map = {doc["id"]: doc for doc in (docs_resp.data or [])}

            if docs_map:
                doc_ids = list(docs_map.keys())
                doc_verif_resp = supabase.table(cls.DOC_VERIFICATIONS_TABLE)\
                    .select("*")\
                    .in_("document_id", doc_ids)\
                    .order("created_at", desc=True)\
                    .execute()

                for dv in (doc_verif_resp.data or []):
                    doc_meta = docs_map.get(dv.get("document_id"), {})
                    ref_id = doc_meta.get("document_id", "UNKNOWN_DOC")

                    verified_at_dt = None
                    if dv.get("verified_at"):
                        try:
                            verified_at_dt = datetime.fromisoformat(dv["verified_at"].replace("Z", "+00:00"))
                        except Exception:
                            verified_at_dt = None

                    created_at_dt = None
                    if dv.get("created_at"):
                        try:
                            created_at_dt = datetime.fromisoformat(dv["created_at"].replace("Z", "+00:00"))
                        except Exception:
                            created_at_dt = None

                    updated_at_dt = None
                    if dv.get("updated_at"):
                        try:
                            updated_at_dt = datetime.fromisoformat(dv["updated_at"].replace("Z", "+00:00"))
                        except Exception:
                            updated_at_dt = None

                    results.append(
                        VerificationResponse(
                            verification_id=dv.get("id") or ref_id,
                            verification_type="DOCUMENT",
                            reference_id=ref_id,
                            status=dv.get("verification_status", "PENDING"),
                            verification_level=None,
                            verified_at=verified_at_dt,
                            verified_by=dv.get("verified_by"),
                            remarks=dv.get("remarks"),
                            created_at=created_at_dt,
                            updated_at=updated_at_dt,
                        )
                    )
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch document verifications: {str(e)}"
            )

        # 2. Fetch student's applications
        try:
            apps_resp = supabase.table(cls.APPLICATIONS_TABLE)\
                .select("id, application_id")\
                .eq("student_id", student.id)\
                .execute()

            apps_map = {app["id"]: app for app in (apps_resp.data or [])}

            if apps_map:
                app_ids = list(apps_map.keys())
                app_verif_resp = supabase.table(cls.APP_VERIFICATIONS_TABLE)\
                    .select("*")\
                    .in_("application_id", app_ids)\
                    .order("created_at", desc=True)\
                    .execute()

                for av in (app_verif_resp.data or []):
                    app_meta = apps_map.get(av.get("application_id"), {})
                    ref_id = app_meta.get("application_id", "UNKNOWN_APP")

                    created_at_dt = None
                    if av.get("created_at"):
                        try:
                            created_at_dt = datetime.fromisoformat(av["created_at"].replace("Z", "+00:00"))
                        except Exception:
                            created_at_dt = None

                    updated_at_dt = None
                    if av.get("updated_at"):
                        try:
                            updated_at_dt = datetime.fromisoformat(av["updated_at"].replace("Z", "+00:00"))
                        except Exception:
                            updated_at_dt = None

                    results.append(
                        VerificationResponse(
                            verification_id=av.get("id") or ref_id,
                            verification_type="APPLICATION",
                            reference_id=ref_id,
                            status=av.get("status", "PENDING"),
                            verification_level=av.get("verification_level"),
                            verified_at=None,
                            verified_by=av.get("verified_by"),
                            remarks=av.get("remarks"),
                            created_at=created_at_dt,
                            updated_at=updated_at_dt,
                        )
                    )
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch application verifications: {str(e)}"
            )

        return results

    @classmethod
    def get_my_verification_by_id(cls, auth_user_id: str, verification_id: str) -> VerificationDetailResponse:
        """
        Retrieves a specific verification record ensuring student ownership.
        Returns 404 if not found or if the entity belongs to another student.
        """
        student = cls._resolve_student(auth_user_id)
        clean_id = verification_id.strip()
        supabase = get_supabase_service_client()

        # 1. Check in document verifications table
        try:
            doc_verif_resp = supabase.table(cls.DOC_VERIFICATIONS_TABLE)\
                .select("*")\
                .eq("id", clean_id)\
                .execute()

            if doc_verif_resp.data and len(doc_verif_resp.data) > 0:
                rec = doc_verif_resp.data[0]
                # Verify document belongs to current student
                doc_check = supabase.table(cls.DOCUMENTS_TABLE)\
                    .select("id, document_id, student_id")\
                    .eq("id", rec["document_id"])\
                    .execute()

                if doc_check.data and len(doc_check.data) > 0:
                    doc_rec = doc_check.data[0]
                    if doc_rec.get("student_id") == student.id:
                        verified_at_dt = None
                        if rec.get("verified_at"):
                            try:
                                verified_at_dt = datetime.fromisoformat(rec["verified_at"].replace("Z", "+00:00"))
                            except Exception:
                                verified_at_dt = None

                        created_at_dt = None
                        if rec.get("created_at"):
                            try:
                                created_at_dt = datetime.fromisoformat(rec["created_at"].replace("Z", "+00:00"))
                            except Exception:
                                created_at_dt = None

                        updated_at_dt = None
                        if rec.get("updated_at"):
                            try:
                                updated_at_dt = datetime.fromisoformat(rec["updated_at"].replace("Z", "+00:00"))
                            except Exception:
                                updated_at_dt = None

                        return VerificationDetailResponse(
                            verification_id=rec["id"],
                            verification_type="DOCUMENT",
                            reference_id=doc_rec.get("document_id", "UNKNOWN_DOC"),
                            status=rec.get("verification_status", "PENDING"),
                            verification_level=None,
                            verified_at=verified_at_dt,
                            verified_by=rec.get("verified_by"),
                            remarks=rec.get("remarks"),
                            created_at=created_at_dt,
                            updated_at=updated_at_dt,
                        )
        except Exception:
            pass

        # 2. Check in application verifications table
        try:
            app_verif_resp = supabase.table(cls.APP_VERIFICATIONS_TABLE)\
                .select("*")\
                .eq("id", clean_id)\
                .execute()

            if app_verif_resp.data and len(app_verif_resp.data) > 0:
                rec = app_verif_resp.data[0]
                # Verify application belongs to current student
                app_check = supabase.table(cls.APPLICATIONS_TABLE)\
                    .select("id, application_id, student_id")\
                    .eq("id", rec["application_id"])\
                    .execute()

                if app_check.data and len(app_check.data) > 0:
                    app_rec = app_check.data[0]
                    if app_rec.get("student_id") == student.id:
                        created_at_dt = None
                        if rec.get("created_at"):
                            try:
                                created_at_dt = datetime.fromisoformat(rec["created_at"].replace("Z", "+00:00"))
                            except Exception:
                                created_at_dt = None

                        updated_at_dt = None
                        if rec.get("updated_at"):
                            try:
                                updated_at_dt = datetime.fromisoformat(rec["updated_at"].replace("Z", "+00:00"))
                            except Exception:
                                updated_at_dt = None

                        return VerificationDetailResponse(
                            verification_id=rec["id"],
                            verification_type="APPLICATION",
                            reference_id=app_rec.get("application_id", "UNKNOWN_APP"),
                            status=rec.get("status", "PENDING"),
                            verification_level=rec.get("verification_level"),
                            verified_at=None,
                            verified_by=rec.get("verified_by"),
                            remarks=rec.get("remarks"),
                            created_at=created_at_dt,
                            updated_at=updated_at_dt,
                        )
        except Exception:
            pass

        # If not found or belongs to another student, return 404
        raise NotFoundException(
            message="Verification record not found.",
            code="VERIFICATION_NOT_FOUND"
        )

    @classmethod
    def get_verification_by_document(cls, auth_user_id: str, document_id: str) -> VerificationDetailResponse:
        """
        Retrieves verification record for a specific document owned by the student.
        """
        student = cls._resolve_student(auth_user_id)
        clean_id = document_id.strip()
        supabase = get_supabase_service_client()

        # 1. Fetch document and verify ownership
        try:
            doc_resp = supabase.table(cls.DOCUMENTS_TABLE)\
                .select("*")\
                .or_(f"document_id.eq.{clean_id},id.eq.{clean_id}")\
                .eq("is_active", True)\
                .execute()

            if not doc_resp.data or len(doc_resp.data) == 0:
                raise NotFoundException(
                    message="Document not found.",
                    code="DOCUMENT_NOT_FOUND"
                )

            doc_rec = doc_resp.data[0]
            if doc_rec.get("student_id") != student.id:
                raise NotFoundException(
                    message="Document not found.",
                    code="DOCUMENT_NOT_FOUND"
                )

        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to verify document: {str(e)}"
            )

        # 2. Fetch verification record
        try:
            verif_resp = supabase.table(cls.DOC_VERIFICATIONS_TABLE)\
                .select("*")\
                .eq("document_id", doc_rec["id"])\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()

            if verif_resp.data and len(verif_resp.data) > 0:
                rec = verif_resp.data[0]
                verified_at_dt = None
                if rec.get("verified_at"):
                    try:
                        verified_at_dt = datetime.fromisoformat(rec["verified_at"].replace("Z", "+00:00"))
                    except Exception:
                        verified_at_dt = None

                created_at_dt = None
                if rec.get("created_at"):
                    try:
                        created_at_dt = datetime.fromisoformat(rec["created_at"].replace("Z", "+00:00"))
                    except Exception:
                        created_at_dt = None

                updated_at_dt = None
                if rec.get("updated_at"):
                    try:
                        updated_at_dt = datetime.fromisoformat(rec["updated_at"].replace("Z", "+00:00"))
                    except Exception:
                        updated_at_dt = None

                return VerificationDetailResponse(
                    verification_id=rec.get("id") or doc_rec["document_id"],
                    verification_type="DOCUMENT",
                    reference_id=doc_rec["document_id"],
                    status=rec.get("verification_status", "PENDING"),
                    verification_level=None,
                    verified_at=verified_at_dt,
                    verified_by=rec.get("verified_by"),
                    remarks=rec.get("remarks"),
                    created_at=created_at_dt,
                    updated_at=updated_at_dt,
                )

            # Default if no row exists yet
            return VerificationDetailResponse(
                verification_id=doc_rec["document_id"],
                verification_type="DOCUMENT",
                reference_id=doc_rec["document_id"],
                status="PENDING",
                verification_level=None,
                verified_at=None,
                verified_by=None,
                remarks=None,
                created_at=None,
                updated_at=None,
            )
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch document verification details: {str(e)}"
            )


verification_service = VerificationService()
