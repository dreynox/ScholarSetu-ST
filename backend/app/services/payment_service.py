"""
Payment service managing student-scoped operations on `tribe_disbursements` table.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.db.supabase import get_supabase_service_client
from app.models.student import Student
from app.schemas.payment import (
    PaymentResponse,
    PaymentSummaryResponse,
    ScholarshipPaymentInfo,
)
from app.utils.errors import (
    NotFoundException,
    AppException,
)


def _parse_dt(val: Any) -> Optional[datetime]:
    """Safely converts string or datetime object to timezone-aware datetime."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


class PaymentService:
    """Service for querying disbursement and payment records in tribe_disbursements."""

    DISBURSEMENTS_TABLE = "tribe_disbursements"
    APPLICATIONS_TABLE = "tribe_applications"
    STUDENTS_TABLE = "tribe_students"
    SCHOLARSHIPS_TABLE = "tribe_scholarships"

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
    def _hydrate_payment_response(
        cls,
        payment_row: Dict[str, Any],
        apps_map: Dict[str, Any],
        scholarships_map: Dict[str, Any]
    ) -> PaymentResponse:
        """Maps a database row from tribe_disbursements into a safe PaymentResponse envelope."""
        app_id_fk = payment_row.get("application_id")
        app_rec = apps_map.get(app_id_fk, {})
        app_business_id = app_rec.get("application_id") or "UNKNOWN_APP"
        academic_year = app_rec.get("academic_year")

        scholarship_fk = app_rec.get("scholarship_id")
        scholarship_rec = scholarships_map.get(scholarship_fk, {})
        scholarship_info = None
        if scholarship_rec:
            scholarship_info = ScholarshipPaymentInfo(
                scholarship_id=scholarship_rec.get("scholarship_id"),
                name=scholarship_rec.get("name"),
                short_name=scholarship_rec.get("short_name"),
            )

        amount_val = float(payment_row.get("amount") or 0.0)

        return PaymentResponse(
            payment_id=payment_row.get("payment_id") or payment_row.get("id"),
            application_id=app_business_id,
            amount=amount_val,
            payment_status=payment_row.get("payment_status", "PENDING"),
            transaction_reference=payment_row.get("transaction_reference"),
            utr_number=payment_row.get("utr_number"),
            payment_date=_parse_dt(payment_row.get("payment_date")),
            bank_name=payment_row.get("bank_name"),
            failure_reason=payment_row.get("failure_reason"),
            academic_year=academic_year,
            scholarship=scholarship_info,
            created_at=_parse_dt(payment_row.get("created_at")),
            updated_at=_parse_dt(payment_row.get("updated_at")),
        )

    @classmethod
    def get_my_payments(cls, auth_user_id: str) -> List[PaymentResponse]:
        """
        Retrieves all payment/disbursement records belonging strictly to the authenticated student.
        """
        student = cls._resolve_student(auth_user_id)
        supabase = get_supabase_service_client()

        try:
            # 1. Fetch disbursements for this student
            disb_resp = supabase.table(cls.DISBURSEMENTS_TABLE)\
                .select("*")\
                .eq("student_id", student.id)\
                .order("created_at", desc=True)\
                .execute()

            disbursements = disb_resp.data or []
            if not disbursements:
                return []

            # 2. Batch fetch associated applications
            app_ids = list({d["application_id"] for d in disbursements if d.get("application_id")})
            apps_map: Dict[str, Any] = {}
            scholarship_ids = set()

            if app_ids:
                apps_resp = supabase.table(cls.APPLICATIONS_TABLE)\
                    .select("id, application_id, scholarship_id, academic_year, student_id")\
                    .in_("id", app_ids)\
                    .execute()
                for app in (apps_resp.data or []):
                    apps_map[app["id"]] = app
                    if app.get("scholarship_id"):
                        scholarship_ids.add(app["scholarship_id"])

            # 3. Batch fetch associated scholarships
            scholarships_map: Dict[str, Any] = {}
            if scholarship_ids:
                sch_resp = supabase.table(cls.SCHOLARSHIPS_TABLE)\
                    .select("id, scholarship_id, name, short_name")\
                    .in_("id", list(scholarship_ids))\
                    .execute()
                for sch in (sch_resp.data or []):
                    scholarships_map[sch["id"]] = sch

            return [
                cls._hydrate_payment_response(d, apps_map, scholarships_map)
                for d in disbursements
            ]

        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch payments: {str(e)}"
            )

    @classmethod
    def get_payment_by_id(cls, auth_user_id: str, payment_id: str) -> PaymentResponse:
        """
        Retrieves a single payment record by payment_id (business ID or internal UUID).
        Strictly enforces student ownership; returns 404 if not found or owned by another user.
        """
        student = cls._resolve_student(auth_user_id)
        clean_id = payment_id.strip()
        supabase = get_supabase_service_client()

        try:
            # Lookup payment
            disb_resp = supabase.table(cls.DISBURSEMENTS_TABLE)\
                .select("*")\
                .or_(f"payment_id.eq.{clean_id},id.eq.{clean_id}")\
                .execute()

            if not disb_resp.data or len(disb_resp.data) == 0:
                raise NotFoundException(
                    message="Payment not found",
                    code="PAYMENT_NOT_FOUND"
                )

            payment_row = disb_resp.data[0]

            # Ownership check
            if payment_row.get("student_id") != student.id:
                raise NotFoundException(
                    message="Payment not found",
                    code="PAYMENT_NOT_FOUND"
                )

            # Hydrate application and scholarship details
            apps_map: Dict[str, Any] = {}
            scholarships_map: Dict[str, Any] = {}
            app_id = payment_row.get("application_id")

            if app_id:
                app_resp = supabase.table(cls.APPLICATIONS_TABLE)\
                    .select("id, application_id, scholarship_id, academic_year, student_id")\
                    .eq("id", app_id)\
                    .execute()
                if app_resp.data and len(app_resp.data) > 0:
                    app_rec = app_resp.data[0]
                    apps_map[app_rec["id"]] = app_rec
                    if app_rec.get("scholarship_id"):
                        sch_resp = supabase.table(cls.SCHOLARSHIPS_TABLE)\
                            .select("id, scholarship_id, name, short_name")\
                            .eq("id", app_rec["scholarship_id"])\
                            .execute()
                        if sch_resp.data and len(sch_resp.data) > 0:
                            sch_rec = sch_resp.data[0]
                            scholarships_map[sch_rec["id"]] = sch_rec

            return cls._hydrate_payment_response(payment_row, apps_map, scholarships_map)

        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch payment details: {str(e)}"
            )

    @classmethod
    def get_payments_by_application_id(cls, auth_user_id: str, application_id: str) -> List[PaymentResponse]:
        """
        Retrieves all payment records for a specific application.
        First verifies that the application exists and is owned by the authenticated student.
        Returns 404 if the application does not exist or belongs to another user.
        """
        student = cls._resolve_student(auth_user_id)
        clean_app_id = application_id.strip()
        supabase = get_supabase_service_client()

        try:
            # 1. Verify application ownership
            app_resp = supabase.table(cls.APPLICATIONS_TABLE)\
                .select("id, application_id, scholarship_id, academic_year, student_id")\
                .or_(f"application_id.eq.{clean_app_id},id.eq.{clean_app_id}")\
                .execute()

            if not app_resp.data or len(app_resp.data) == 0:
                raise NotFoundException(
                    message="Application not found",
                    code="APPLICATION_NOT_FOUND"
                )

            app_rec = app_resp.data[0]
            if app_rec.get("student_id") != student.id:
                raise NotFoundException(
                    message="Application not found",
                    code="APPLICATION_NOT_FOUND"
                )

            # 2. Fetch payments for this application
            disb_resp = supabase.table(cls.DISBURSEMENTS_TABLE)\
                .select("*")\
                .eq("application_id", app_rec["id"])\
                .eq("student_id", student.id)\
                .order("created_at", desc=True)\
                .execute()

            disbursements = disb_resp.data or []
            if not disbursements:
                return []

            apps_map = {app_rec["id"]: app_rec}
            scholarships_map: Dict[str, Any] = {}

            if app_rec.get("scholarship_id"):
                sch_resp = supabase.table(cls.SCHOLARSHIPS_TABLE)\
                    .select("id, scholarship_id, name, short_name")\
                    .eq("id", app_rec["scholarship_id"])\
                    .execute()
                if sch_resp.data and len(sch_resp.data) > 0:
                    scholarships_map[sch_resp.data[0]["id"]] = sch_resp.data[0]

            return [
                cls._hydrate_payment_response(d, apps_map, scholarships_map)
                for d in disbursements
            ]

        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch application payments: {str(e)}"
            )

    @classmethod
    def get_payment_summary(cls, auth_user_id: str) -> PaymentSummaryResponse:
        """
        Computes student-level payment summary metrics for the authenticated student.
        """
        student = cls._resolve_student(auth_user_id)
        supabase = get_supabase_service_client()

        try:
            disb_resp = supabase.table(cls.DISBURSEMENTS_TABLE)\
                .select("amount, payment_status")\
                .eq("student_id", student.id)\
                .execute()

            disbursements = disb_resp.data or []

            total_payments = len(disbursements)
            pending_payments = 0
            processing_payments = 0
            completed_payments = 0
            failed_payments = 0
            total_amount = 0.0
            disbursed_amount = 0.0

            for d in disbursements:
                status_str = (d.get("payment_status") or "").upper()
                amt = float(d.get("amount") or 0.0)
                total_amount += amt

                if status_str == "PENDING":
                    pending_payments += 1
                elif status_str == "PROCESSING":
                    processing_payments += 1
                elif status_str in ["SUCCESS", "COMPLETED", "DISBURSED", "PAID"]:
                    completed_payments += 1
                    disbursed_amount += amt
                elif status_str in ["FAILED", "REJECTED", "CANCELLED"]:
                    failed_payments += 1

            return PaymentSummaryResponse(
                total_payments=total_payments,
                pending_payments=pending_payments,
                processing_payments=processing_payments,
                completed_payments=completed_payments,
                failed_payments=failed_payments,
                total_amount=round(total_amount, 2),
                disbursed_amount=round(disbursed_amount, 2),
            )

        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to compute payment summary: {str(e)}"
            )


payment_service = PaymentService()
