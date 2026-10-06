"""
Notification Pydantic schemas for student-scoped notifications and response envelopes.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    """
    Standard response schema for an individual notification.
    Hides internal database foreign key UUIDs and exposes clean identifiers.
    """
    model_config = ConfigDict(from_attributes=True)

    notification_id: str = Field(..., description="Unique Notification Identifier (UUID)")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message body")
    notification_type: str = Field(..., description="Notification type (e.g. APPLICATION, DOCUMENT, VERIFICATION, PAYMENT, GENERAL)")
    is_read: bool = Field(..., description="True if marked as read by student")
    application_id: Optional[str] = Field(default=None, description="Linked application business ID (e.g. TRB-APP-000001) if applicable")
    sent_at: Optional[datetime] = Field(default=None, description="Timestamp when notification was sent")
    created_at: Optional[datetime] = Field(default=None, description="Record creation timestamp")


class NotificationListResponse(BaseModel):
    """List response envelope for student notifications."""
    notifications: List[NotificationResponse] = Field(default_factory=list, description="List of notifications")
    count: int = Field(..., description="Total count of notifications returned")
    unread_count: int = Field(..., description="Total count of unread notifications for student")


class NotificationSummaryResponse(BaseModel):
    """
    Student-level notification summary metrics.
    Derived strictly from authenticated student's own notification records.
    """
    total_notifications: int = Field(default=0, description="Total number of notifications")
    unread_notifications: int = Field(default=0, description="Count of unread notifications")
    read_notifications: int = Field(default=0, description="Count of read notifications")


class NotificationMarkReadResponse(BaseModel):
    """Response envelope after marking a single notification as read."""
    message: str = Field(default="Notification marked as read", description="Status message")
    notification_id: str = Field(..., description="ID of updated notification")
    is_read: bool = Field(default=True, description="Updated read state")


class NotificationMarkAllReadResponse(BaseModel):
    """Response envelope after marking all student notifications as read."""
    message: str = Field(default="All notifications marked as read", description="Status message")
    updated_count: int = Field(..., description="Number of notifications marked as read")
