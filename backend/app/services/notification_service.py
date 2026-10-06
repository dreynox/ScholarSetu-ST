"""
Notification service managing student-scoped operations on `tribe_notifications` table.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from app.db.supabase import get_supabase_service_client
from app.models.student import Student
from app.schemas.notification import (
    NotificationResponse,
    NotificationSummaryResponse,
    NotificationMarkReadResponse,
    NotificationMarkAllReadResponse,
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


class NotificationService:
    """Service for querying and managing notifications in tribe_notifications."""

    NOTIFICATIONS_TABLE = "tribe_notifications"
    APPLICATIONS_TABLE = "tribe_applications"
    STUDENTS_TABLE = "tribe_students"

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
    def _hydrate_notification_response(
        cls,
        row: Dict[str, Any],
        apps_map: Dict[str, Any]
    ) -> NotificationResponse:
        """Maps a database row from tribe_notifications into a clean NotificationResponse envelope."""
        app_id_fk = row.get("application_id")
        app_business_id = None
        if app_id_fk and app_id_fk in apps_map:
            app_business_id = apps_map[app_id_fk].get("application_id")

        return NotificationResponse(
            notification_id=str(row.get("id")),
            title=row.get("title", ""),
            message=row.get("message", ""),
            notification_type=row.get("notification_type", "GENERAL"),
            is_read=bool(row.get("is_read", False)),
            application_id=app_business_id,
            sent_at=_parse_dt(row.get("sent_at")),
            created_at=_parse_dt(row.get("created_at")),
        )

    @classmethod
    def get_my_notifications(
        cls,
        auth_user_id: str,
        unread_only: bool = False,
        notification_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[NotificationResponse], int, int]:
        """
        Retrieves paginated notifications belonging strictly to the authenticated student.
        Returns (notifications_list, total_filtered_count, total_unread_count).
        """
        student = cls._resolve_student(auth_user_id)
        supabase = get_supabase_service_client()

        try:
            # 1. Calculate unread count for student
            unread_resp = supabase.table(cls.NOTIFICATIONS_TABLE)\
                .select("id")\
                .eq("student_id", student.id)\
                .eq("is_read", False)\
                .execute()
            unread_count = len(unread_resp.data or [])

            # 2. Build filtered query for notifications
            query = supabase.table(cls.NOTIFICATIONS_TABLE)\
                .select("*")\
                .eq("student_id", student.id)

            if unread_only:
                query = query.eq("is_read", False)

            if notification_type and notification_type.strip():
                query = query.eq("notification_type", notification_type.strip().upper())

            # Order by created_at desc
            query = query.order("created_at", desc=True)

            # Apply pagination limit and offset
            safe_limit = min(max(limit, 1), 100)
            safe_offset = max(offset, 0)
            query = query.range(safe_offset, safe_offset + safe_limit - 1)

            notif_resp = query.execute()
            rows = notif_resp.data or []

            # 3. Batch resolve linked applications
            app_ids = list({r["application_id"] for r in rows if r.get("application_id")})
            apps_map: Dict[str, Any] = {}
            if app_ids:
                apps_resp = supabase.table(cls.APPLICATIONS_TABLE)\
                    .select("id, application_id")\
                    .in_("id", app_ids)\
                    .execute()
                for app in (apps_resp.data or []):
                    apps_map[app["id"]] = app

            results = [
                cls._hydrate_notification_response(r, apps_map)
                for r in rows
            ]

            return results, len(results), unread_count

        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch notifications: {str(e)}"
            )

    @classmethod
    def get_notification_by_id(cls, auth_user_id: str, notification_id: str) -> NotificationResponse:
        """
        Retrieves a single notification by its ID.
        Strictly enforces student ownership; returns 404 if not found or belongs to another user.
        """
        student = cls._resolve_student(auth_user_id)
        clean_id = notification_id.strip()
        supabase = get_supabase_service_client()

        try:
            notif_resp = supabase.table(cls.NOTIFICATIONS_TABLE)\
                .select("*")\
                .eq("id", clean_id)\
                .execute()

            if not notif_resp.data or len(notif_resp.data) == 0:
                raise NotFoundException(
                    message="Notification not found",
                    code="NOTIFICATION_NOT_FOUND"
                )

            row = notif_resp.data[0]

            # Ownership check
            if row.get("student_id") != student.id:
                raise NotFoundException(
                    message="Notification not found",
                    code="NOTIFICATION_NOT_FOUND"
                )

            apps_map: Dict[str, Any] = {}
            if row.get("application_id"):
                app_resp = supabase.table(cls.APPLICATIONS_TABLE)\
                    .select("id, application_id")\
                    .eq("id", row["application_id"])\
                    .execute()
                if app_resp.data and len(app_resp.data) > 0:
                    apps_map[app_resp.data[0]["id"]] = app_resp.data[0]

            return cls._hydrate_notification_response(row, apps_map)

        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to fetch notification: {str(e)}"
            )

    @classmethod
    def mark_notification_as_read(cls, auth_user_id: str, notification_id: str) -> NotificationMarkReadResponse:
        """
        Marks a specific notification owned by the authenticated student as read.
        Returns 404 if not found or if notification belongs to another user.
        """
        student = cls._resolve_student(auth_user_id)
        clean_id = notification_id.strip()
        supabase = get_supabase_service_client()

        try:
            # 1. Verify existence and ownership
            notif_resp = supabase.table(cls.NOTIFICATIONS_TABLE)\
                .select("*")\
                .eq("id", clean_id)\
                .execute()

            if not notif_resp.data or len(notif_resp.data) == 0:
                raise NotFoundException(
                    message="Notification not found",
                    code="NOTIFICATION_NOT_FOUND"
                )

            row = notif_resp.data[0]
            if row.get("student_id") != student.id:
                raise NotFoundException(
                    message="Notification not found",
                    code="NOTIFICATION_NOT_FOUND"
                )

            # 2. Update to read state
            supabase.table(cls.NOTIFICATIONS_TABLE)\
                .update({"is_read": True})\
                .eq("id", clean_id)\
                .eq("student_id", student.id)\
                .execute()

            return NotificationMarkReadResponse(
                message="Notification marked as read",
                notification_id=clean_id,
                is_read=True
            )

        except NotFoundException:
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to mark notification as read: {str(e)}"
            )

    @classmethod
    def mark_all_notifications_as_read(cls, auth_user_id: str) -> NotificationMarkAllReadResponse:
        """
        Marks all unread notifications of the authenticated student as read.
        Never touches notifications belonging to any other student.
        """
        student = cls._resolve_student(auth_user_id)
        supabase = get_supabase_service_client()

        try:
            # 1. Check unread count
            unread_resp = supabase.table(cls.NOTIFICATIONS_TABLE)\
                .select("id")\
                .eq("student_id", student.id)\
                .eq("is_read", False)\
                .execute()

            unread_rows = unread_resp.data or []
            updated_count = len(unread_rows)

            if updated_count > 0:
                supabase.table(cls.NOTIFICATIONS_TABLE)\
                    .update({"is_read": True})\
                    .eq("student_id", student.id)\
                    .eq("is_read", False)\
                    .execute()

            return NotificationMarkAllReadResponse(
                message="All notifications marked as read",
                updated_count=updated_count
            )

        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to mark all notifications as read: {str(e)}"
            )

    @classmethod
    def get_notification_summary(cls, auth_user_id: str) -> NotificationSummaryResponse:
        """
        Calculates student-level notification summary metrics.
        """
        student = cls._resolve_student(auth_user_id)
        supabase = get_supabase_service_client()

        try:
            notif_resp = supabase.table(cls.NOTIFICATIONS_TABLE)\
                .select("is_read")\
                .eq("student_id", student.id)\
                .execute()

            rows = notif_resp.data or []
            total_count = len(rows)
            unread_count = sum(1 for r in rows if not r.get("is_read", False))
            read_count = total_count - unread_count

            return NotificationSummaryResponse(
                total_notifications=total_count,
                unread_notifications=unread_count,
                read_notifications=read_count
            )

        except Exception as e:
            raise AppException(
                status_code=500,
                code="DATABASE_ERROR",
                message=f"Failed to compute notification summary: {str(e)}"
            )


notification_service = NotificationService()
