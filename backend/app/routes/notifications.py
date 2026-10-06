"""
Notification endpoints for student scholarship alerts, verifications, and general updates.
Protected user-scoped endpoints (Phase 5).
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    NotificationSummaryResponse,
    NotificationMarkReadResponse,
    NotificationMarkAllReadResponse,
)
from app.services.notification_service import notification_service
from app.core.dependencies import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List student's notifications",
    description="Retrieves notifications belonging strictly to the currently authenticated student. Supports filtering by read status and notification type with pagination.",
)
async def get_my_notifications(
    unread_only: bool = Query(default=False, description="Filter for unread notifications only"),
    notification_type: Optional[str] = Query(default=None, description="Filter by notification type (APPLICATION, DOCUMENT, PAYMENT, etc.)"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of notifications to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns paginated notifications list for the authenticated student.
    """
    notifications, count, unread_count = notification_service.get_my_notifications(
        auth_user_id=current_user.id,
        unread_only=unread_only,
        notification_type=notification_type,
        limit=limit,
        offset=offset,
    )
    return NotificationListResponse(
        notifications=notifications,
        count=count,
        unread_count=unread_count
    )


@router.get(
    "/summary",
    response_model=NotificationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get notification summary",
    description="Calculates summary counts (total, unread, read) for the authenticated student's notifications.",
)
async def get_notification_summary(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns student-level notification summary metrics.
    """
    return notification_service.get_notification_summary(current_user.id)


@router.put(
    "/read-all",
    response_model=NotificationMarkAllReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
    description="Marks all unread notifications of the currently authenticated student as read.",
)
async def mark_all_notifications_as_read(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Marks all notifications for authenticated student as read.
    """
    return notification_service.mark_all_notifications_as_read(current_user.id)


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get notification by ID",
    description="Retrieves a specific notification record. Enforces student ownership; returns 404 if not found or owned by another user.",
)
async def get_notification_by_id(
    notification_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns notification details if owned by current student.
    """
    return notification_service.get_notification_by_id(
        auth_user_id=current_user.id,
        notification_id=notification_id,
    )


@router.put(
    "/{notification_id}/read",
    response_model=NotificationMarkReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a notification as read",
    description="Updates the read state of a specific notification belonging to the authenticated student.",
)
async def mark_notification_as_read(
    notification_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Marks specific notification as read.
    """
    return notification_service.mark_notification_as_read(
        auth_user_id=current_user.id,
        notification_id=notification_id,
    )
