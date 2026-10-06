"""
Services package
"""
from app.services.auth_service import AuthService, auth_service
from app.services.student_service import StudentService, student_service
from app.services.scholarship_service import ScholarshipService, scholarship_service
from app.services.application_service import ApplicationService, application_service
from app.services.document_service import DocumentService, document_service
from app.services.verification_service import VerificationService, verification_service
from app.services.payment_service import PaymentService, payment_service
from app.services.notification_service import NotificationService, notification_service

__all__ = [
    "AuthService",
    "auth_service",
    "StudentService",
    "student_service",
    "ScholarshipService",
    "scholarship_service",
    "ApplicationService",
    "application_service",
    "DocumentService",
    "document_service",
    "VerificationService",
    "verification_service",
    "PaymentService",
    "payment_service",
    "NotificationService",
    "notification_service",
]


