"""
Schemas package
"""
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    AuthResponse,
)
from app.schemas.student import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    StudentStatusResponse,
)
from app.schemas.scholarship import (
    ScholarshipResponse,
    ScholarshipListResponse,
    ScholarshipSummaryResponse,
)
from app.schemas.application import (
    ScholarshipInfo,
    InstitutionInfo,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationListResponse,
    ApplicationDeleteResponse,
)
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
    DocumentDeleteResponse,
    DocumentVerificationInfo,
)
from app.schemas.verification import (
    VerificationResponse,
    VerificationListResponse,
    VerificationDetailResponse,
)
from app.schemas.payment import (
    ScholarshipPaymentInfo,
    PaymentResponse,
    PaymentListResponse,
    PaymentSummaryResponse,
)
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    NotificationSummaryResponse,
    NotificationMarkReadResponse,
    NotificationMarkAllReadResponse,
)

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "UserResponse",
    "AuthResponse",
    "StudentCreate",
    "StudentUpdate",
    "StudentResponse",
    "StudentStatusResponse",
    "ScholarshipResponse",
    "ScholarshipListResponse",
    "ScholarshipSummaryResponse",
    "ScholarshipInfo",
    "InstitutionInfo",
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationResponse",
    "ApplicationListResponse",
    "ApplicationDeleteResponse",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "DocumentListResponse",
    "DocumentDeleteResponse",
    "DocumentVerificationInfo",
    "VerificationResponse",
    "VerificationListResponse",
    "VerificationDetailResponse",
    "ScholarshipPaymentInfo",
    "PaymentResponse",
    "PaymentListResponse",
    "PaymentSummaryResponse",
    "NotificationResponse",
    "NotificationListResponse",
    "NotificationSummaryResponse",
    "NotificationMarkReadResponse",
    "NotificationMarkAllReadResponse",
]


