"""
Routes package
"""
from app.routes.api import router as api_router
from app.routes.auth import router as auth_router
from app.routes.students import router as students_router
from app.routes.scholarships import router as scholarships_router
from app.routes.applications import router as applications_router
from app.routes.documents import router as documents_router
from app.routes.verifications import router as verifications_router
from app.routes.payments import router as payments_router
from app.routes.notifications import router as notifications_router

__all__ = [
    "api_router",
    "auth_router",
    "students_router",
    "scholarships_router",
    "applications_router",
    "documents_router",
    "verifications_router",
    "payments_router",
    "notifications_router",
]


