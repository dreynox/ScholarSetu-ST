"""
Document service managing operations on `tribe_documents` and `tribe_document_verifications` tables.
"""
import re
import uuid
from datetime import date, datetime
from typing import List, Optional, Dict, Any

from app.db.supabase import get_supabase_service_client
from app.models.student import Student
from app.models.document import Document
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentVerificationInfo,
)
from app.utils.errors import (
    NotFoundException,
    ConflictException,
    AppException,
    ForbiddenException,
)


class DocumentService:
    """Service for managing student documents in tribe_documents."""

    DOCUMENTS_TABLE = "tribe_documents"
    STUDENTS_TABLE = "tribe_students"
    DOCUMENT_VERIFICATIONS_TABLE = "tribe_document_verifications"

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
                    message="Student profile not found. Please create your student profile before uploading documents.",
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
    def _generate_document_id(cls) -> str:
        """
        Generates unique business document ID (e.g. TRB-DOC-000001).
        Uses a collision-resilient sequential + check strategy.
        """
        supabase = get_supabase_service_client()
        try:
            response = supabase.table(cls.DOCUMENTS_TABLE)\
                .select("document_id")\
                .order("created_at", desc=True)\
                .limit(100)\
                .execute()

            max_num = 0
            if response.data:
                for row in response.data:
                    doc_id_str = row.get("document_id", "")
                    match = re.search(r"TRB-DOC-(\d+)", doc_id_str)
                    if match:
                        num = int(match.group(1))
                        if num > max_num:
                            max_num = num

            for attempt in range(1, 10):
                candidate_num = max_num + attempt
                candidate_id = f"TRB-DOC-{candidate_num:06d}"
                check = supabase.table(cls.DOCUMENTS_TABLE)\
                    .select("id")\
                    .eq("document_id", candidate_id)\
                    .execute()

                if not check.data or len(check.data) == 0:
                    return candidate_id

            random_suffix = uuid.uuid4().hex[:6].upper()
            return f"TRB-DOC-{random_suffix}"
        except Exception:
            random_suffix = uuid.uuid4().hex[:6].upper()
            return f"TRB-DOC-{random_suffix}"

    @classmethod
    def _get_document_verification_status(cls, document_db_id: str) -> str:
        """
        Fetches latest verification status for a document from tribe_document_verifications.
        """
        supabase = get_supabase_service_client()
        try:
            resp = supabase.table(cls.DOCUMENT_VERIFICATIONS_TABLE)\
                .select("verification_status")\
                .eq("document_id", document_db_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()

            if resp.data and len(resp.data) > 0:
                return resp.data[0].get("verification_status", "PENDING")
            return "PENDING"
        except Exception:
            return "PENDING"

    @classmethod
    def _build_document_response(
        cls,
        doc_record: Dict[str, Any],
        verification_status: Optional[str] = None
    ) -> DocumentResponse:
        """
        Formats internal document record into public response schema.
        Never exposes database UUIDs.
        """
        if verification_status is None and doc_record.get("id"):
            verification_status = cls._get_document_verification_status(doc_record["id"])

        expiry = doc_record.get("expiry_date")
        if isinstance(expiry, str):
            try:
                expiry = date.fromisoformat(expiry)
            except ValueError:
                expiry = None

        created_at_dt = None
        if doc_record.get("created_at"):
            try:
                created_at_dt = datetime.fromisoformat(doc_record["created_at"].replace("Z", "+00:00"))
            except Exception:
                created_at_dt = None

        updated_at_dt = None
        if doc_record.get("updated_at"):
            try:
                updated_at_dt = datetime.fromisoformat(doc_record["updated_at"].replace("Z", "+00:00"))
            except Exception:
                updated_at_dt = None

        return DocumentResponse(
            document_id=doc_record["document_id"],
            document_type=doc_record["document_type"],
            document_name=doc_record["document_name"],
            file_url=doc_record.get("file_url"),
            storage_path=doc_record.get("storage_path"),
            file_size=doc_record.get("file_size"),
            file_type=doc_record.get("file_type"),
            document_number=doc_record.get("document_number"),
            expiry_date=expiry,
            is_active=doc_record.get("is_active", True),
            verification_status=verification_status or "PENDING",
            created_at=created_at_dt,
            updated_at=updated_at_dt,
        )

    @classmethod
    def create_document(cls, auth_user_id: str, payload: DocumentCreate) -> DocumentResponse:
        """
        Registers a new document for the authenticated student.
        Initializes document verification status to PENDING.
        """
        student = cls._resolve_student(auth_user_id)
        supabase = get_supabase_service_client()

        doc_id = cls._generate_document_id()

        data_to_insert = {
            "document_id": doc_id,
            "student_id": student.id,
            "document_type": payload.document_type.upper().strip(),
            "document_name": payload.document_name.strip(),
            "file_url": payload.file_url,
            "storage_path": payload.storage_path,
            "file_size": payload.file_size,
            "file_type": payload.file_type,
            "document_number": payload.document_number,
            "expiry_date": payload.expiry_date.isoformat() if payload.expiry_date else None,
            "is_active": True,
        }

        try:
            insert_resp = supabase.table(cls.DOCUMENTS_TABLE).insert(data_to_insert).execute()
            if not insert_resp.data or len(insert_resp.data) == 0:
                raise AppException(
                    status_code=500,
                    code="INSERT_FAILED",
                    message="Failed to create document record."
                )

            created_doc = insert_resp.data[0]

            # Initialize verification entry in tribe_document_verifications
            try:
                supabase.table(cls.DOCUMENT_VERIFICATIONS_TABLE).insert({
                    "document_id": created_doc["id"],
                    "verification_status": "PENDING",
                    "verified_at": None,
                    "verified_by": None,
                    "remarks": None,
                }).execute()
            except Exception:
                # If non-critical verification init fails, continue
                pass

            return cls._build_document_response(created_doc, verification_status="PENDING")
        except AppException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Database document creation failed: {str(e)}"
            )

    @classmethod
    def get_my_documents(cls, auth_user_id: str) -> List[DocumentResponse]:
        """
        Retrieves all documents belonging strictly to the authenticated student.
        """
        student = cls._resolve_student(auth_user_id)
        supabase = get_supabase_service_client()

        try:
            response = supabase.table(cls.DOCUMENTS_TABLE)\
                .select("*")\
                .eq("student_id", student.id)\
                .eq("is_active", True)\
                .order("created_at", desc=True)\
                .execute()

            records = response.data or []
            return [cls._build_document_response(rec) for rec in records]
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch student documents: {str(e)}"
            )

    @classmethod
    def get_my_document_by_id(cls, auth_user_id: str, document_id: str) -> DocumentResponse:
        """
        Retrieves a specific document. Returns 404 if not owned by authenticated student.
        """
        student = cls._resolve_student(auth_user_id)
        clean_id = document_id.strip()
        supabase = get_supabase_service_client()

        try:
            response = supabase.table(cls.DOCUMENTS_TABLE)\
                .select("*")\
                .or_(f"document_id.eq.{clean_id},id.eq.{clean_id}")\
                .eq("is_active", True)\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message="Document not found.",
                    code="DOCUMENT_NOT_FOUND"
                )

            rec = response.data[0]

            # Ownership security check
            if rec.get("student_id") != student.id:
                raise NotFoundException(
                    message="Document not found.",
                    code="DOCUMENT_NOT_FOUND"
                )

            return cls._build_document_response(rec)
        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch document: {str(e)}"
            )

    @classmethod
    def update_document(
        cls, auth_user_id: str, document_id: str, payload: DocumentUpdate
    ) -> DocumentResponse:
        """
        Updates editable metadata for an owned document.
        Verified documents cannot be updated.
        """
        student = cls._resolve_student(auth_user_id)
        clean_id = document_id.strip()
        supabase = get_supabase_service_client()

        # 1. Fetch document and verify ownership
        try:
            response = supabase.table(cls.DOCUMENTS_TABLE)\
                .select("*")\
                .or_(f"document_id.eq.{clean_id},id.eq.{clean_id}")\
                .eq("is_active", True)\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message="Document not found.",
                    code="DOCUMENT_NOT_FOUND"
                )

            rec = response.data[0]

            if rec.get("student_id") != student.id:
                raise NotFoundException(
                    message="Document not found.",
                    code="DOCUMENT_NOT_FOUND"
                )

            # 2. Check verification status
            status = cls._get_document_verification_status(rec["id"])
            if status == "VERIFIED":
                raise AppException(
                    status_code=400,
                    code="DOCUMENT_NOT_EDITABLE",
                    message="Verified documents cannot be modified."
                )

        except (NotFoundException, AppException):
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to verify document for update: {str(e)}"
            )

        # 3. Prepare update payload
        update_data: Dict[str, Any] = {}
        if payload.document_type is not None:
            update_data["document_type"] = payload.document_type.upper().strip()
        if payload.document_name is not None:
            update_data["document_name"] = payload.document_name.strip()
        if payload.file_url is not None:
            update_data["file_url"] = payload.file_url
        if payload.storage_path is not None:
            update_data["storage_path"] = payload.storage_path
        if payload.file_size is not None:
            update_data["file_size"] = payload.file_size
        if payload.file_type is not None:
            update_data["file_type"] = payload.file_type
        if payload.document_number is not None:
            update_data["document_number"] = payload.document_number
        if payload.expiry_date is not None:
            update_data["expiry_date"] = payload.expiry_date.isoformat()

        if not update_data:
            return cls._build_document_response(rec, status)

        try:
            update_resp = supabase.table(cls.DOCUMENTS_TABLE)\
                .update(update_data)\
                .eq("id", rec["id"])\
                .eq("student_id", student.id)\
                .execute()

            if not update_resp.data or len(update_resp.data) == 0:
                raise AppException(
                    status_code=500,
                    code="UPDATE_FAILED",
                    message="Failed to update document."
                )

            return cls._build_document_response(update_resp.data[0], status)
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Database document update failed: {str(e)}"
            )

    @classmethod
    def delete_document(cls, auth_user_id: str, document_id: str) -> str:
        """
        Safely deletes a document owned by the authenticated student.
        Verified documents cannot be deleted.
        """
        student = cls._resolve_student(auth_user_id)
        clean_id = document_id.strip()
        supabase = get_supabase_service_client()

        # 1. Fetch document and verify ownership
        try:
            response = supabase.table(cls.DOCUMENTS_TABLE)\
                .select("*")\
                .or_(f"document_id.eq.{clean_id},id.eq.{clean_id}")\
                .eq("is_active", True)\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message="Document not found.",
                    code="DOCUMENT_NOT_FOUND"
                )

            rec = response.data[0]

            if rec.get("student_id") != student.id:
                raise NotFoundException(
                    message="Document not found.",
                    code="DOCUMENT_NOT_FOUND"
                )

            # 2. Check verification status
            status = cls._get_document_verification_status(rec["id"])
            if status == "VERIFIED":
                raise AppException(
                    status_code=400,
                    code="DOCUMENT_NOT_DELETABLE",
                    message="Verified documents cannot be deleted."
                )

        except (NotFoundException, AppException):
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to verify document for deletion: {str(e)}"
            )

        # 3. Perform safe deletion
        try:
            # Delete verification record first
            supabase.table(cls.DOCUMENT_VERIFICATIONS_TABLE)\
                .delete()\
                .eq("document_id", rec["id"])\
                .execute()

            # Delete document record
            supabase.table(cls.DOCUMENTS_TABLE)\
                .delete()\
                .eq("id", rec["id"])\
                .eq("student_id", student.id)\
                .execute()

            return rec["document_id"]
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to delete document: {str(e)}"
            )

    @classmethod
    def get_document_verification(cls, auth_user_id: str, document_id: str) -> DocumentVerificationInfo:
        """
        Retrieves verification information for an owned document.
        """
        student = cls._resolve_student(auth_user_id)
        clean_id = document_id.strip()
        supabase = get_supabase_service_client()

        # 1. Verify document ownership
        try:
            response = supabase.table(cls.DOCUMENTS_TABLE)\
                .select("*")\
                .or_(f"document_id.eq.{clean_id},id.eq.{clean_id}")\
                .eq("is_active", True)\
                .execute()

            if not response.data or len(response.data) == 0:
                raise NotFoundException(
                    message="Document not found.",
                    code="DOCUMENT_NOT_FOUND"
                )

            doc_rec = response.data[0]

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
            verif_resp = supabase.table(cls.DOCUMENT_VERIFICATIONS_TABLE)\
                .select("*")\
                .eq("document_id", doc_rec["id"])\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()

            verif_rec = verif_resp.data[0] if verif_resp.data and len(verif_resp.data) > 0 else {}

            verified_at_dt = None
            if verif_rec.get("verified_at"):
                try:
                    verified_at_dt = datetime.fromisoformat(verif_rec["verified_at"].replace("Z", "+00:00"))
                except Exception:
                    verified_at_dt = None

            created_at_dt = None
            if verif_rec.get("created_at"):
                try:
                    created_at_dt = datetime.fromisoformat(verif_rec["created_at"].replace("Z", "+00:00"))
                except Exception:
                    created_at_dt = None

            updated_at_dt = None
            if verif_rec.get("updated_at"):
                try:
                    updated_at_dt = datetime.fromisoformat(verif_rec["updated_at"].replace("Z", "+00:00"))
                except Exception:
                    updated_at_dt = None

            return DocumentVerificationInfo(
                document_id=doc_rec["document_id"],
                document_type=doc_rec["document_type"],
                document_name=doc_rec["document_name"],
                verification_status=verif_rec.get("verification_status", "PENDING"),
                verified_at=verified_at_dt,
                verified_by=verif_rec.get("verified_by"),
                remarks=verif_rec.get("remarks"),
                created_at=created_at_dt,
                updated_at=updated_at_dt,
            )
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch document verification: {str(e)}"
            )


document_service = DocumentService()
