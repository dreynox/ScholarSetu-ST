"""
FastAPI Main Application Entry Point
MoTA Unified Scholarship Platform (Ministry of Tribal Affairs - SIH26238)
"""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.routes.api import router as base_api_router
from app.routes.auth import router as auth_router
from app.routes.students import router as students_router
from app.routes.scholarships import router as scholarships_router
from app.routes.applications import router as applications_router
from app.routes.documents import router as documents_router
from app.routes.verifications import router as verifications_router
from app.routes.payments import router as payments_router
from app.routes.notifications import router as notifications_router
from app.utils.errors import AppException



# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Unified Scholarship Mobile Application Backend for Tribal Students - Ministry of Tribal Affairs (SIH26238)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.ENVIRONMENT == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# Global Exception Handlers for Unified Error JSON Schema (Section 13)
# =====================================================================

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handles custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles Pydantic validation errors."""
    errors = []
    for err in exc.errors():
        field_path = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        errors.append({
            "field": field_path,
            "message": err.get("msg"),
            "type": err.get("type"),
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request body failed schema validation.",
                "details": errors,
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handles standard Starlette / FastAPI HTTPExceptions."""
    # If detail is already a dict, extract structure
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
            headers=exc.headers,
        )

    code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "UNAUTHORIZED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = "FORBIDDEN"
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "NOT_FOUND"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc.detail),
                "details": None,
            }
        },
        headers=exc.headers,
    )


# =====================================================================
# Root Foundation Endpoints (Section 6)
# =====================================================================

@app.get("/health", tags=["Health"], summary="System Health Check")
async def health_check():
    """
    Health check endpoint returning service operational status.
    """
    return {
        "status": "healthy",
        "service": "mota-scholarship-backend"
    }


# Include API v1 Base Route
app.include_router(base_api_router, prefix=settings.API_V1_STR, tags=["API v1"])

# Include Authentication Routes
app.include_router(auth_router, prefix=settings.API_V1_STR)

# Include Student Routes
app.include_router(students_router, prefix=settings.API_V1_STR)

# Include Scholarship Routes
app.include_router(scholarships_router, prefix=settings.API_V1_STR)

# Include Application Routes
app.include_router(applications_router, prefix=settings.API_V1_STR)

# Include Document Routes
app.include_router(documents_router, prefix=settings.API_V1_STR)

# Include Verification Routes
app.include_router(verifications_router, prefix=settings.API_V1_STR)

# Include Payment Routes
app.include_router(payments_router, prefix=settings.API_V1_STR)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
