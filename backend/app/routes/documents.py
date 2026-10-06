"""
Document endpoints for managing student scholarship documents.
Protected user-scoped endpoints (Section 7).
"""
from fastapi import APIRouter, Depends, status
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
    DocumentDeleteResponse,
    DocumentVerificationInfo,
)
from app.services.document_service import document_service
from app.core.dependencies import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new document",
    description="Uploads/registers a new document record linked to the authenticated student.",
)
async def create_document(
    payload: DocumentCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Creates a new document record for the authenticated student.
    """
    return document_service.create_document(
        auth_user_id=current_user.id,
        payload=payload,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all documents of authenticated student",
    description="Retrieves all documents belonging strictly to the currently authenticated student.",
)
async def get_my_documents(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns list of documents for authenticated student.
    """
    results = document_service.get_my_documents(current_user.id)
    return DocumentListResponse(
        documents=results,
        count=len(results),
    )


@router.get(
    "/{document_id}/verification",
    response_model=DocumentVerificationInfo,
    status_code=status.HTTP_200_OK,
    summary="Get document verification information",
    description="Retrieves verification status and remarks for an owned document. Returns 404 if document belongs to another student.",
)
async def get_document_verification(
    document_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns verification information for a specific document.
    """
    return document_service.get_document_verification(
        auth_user_id=current_user.id,
        document_id=document_id,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document by ID",
    description="Retrieves a specific document. Enforces ownership check; returns 404 if document does not belong to the user.",
)
async def get_my_document_by_id(
    document_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Returns document details if owned by current student.
    """
    return document_service.get_my_document_by_id(
        auth_user_id=current_user.id,
        document_id=document_id,
    )


@router.put(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update editable document metadata",
    description="Updates allowable metadata fields for an owned document. Verified documents cannot be updated.",
)
async def update_my_document(
    document_id: str,
    payload: DocumentUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Updates document metadata.
    """
    return document_service.update_document(
        auth_user_id=current_user.id,
        document_id=document_id,
        payload=payload,
    )


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete document",
    description="Deletes a document owned by current student. Verified documents cannot be deleted.",
)
async def delete_my_document(
    document_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Deletes document.
    """
    deleted_id = document_service.delete_document(
        auth_user_id=current_user.id,
        document_id=document_id,
    )
    return DocumentDeleteResponse(
        message="Document deleted successfully",
        document_id=deleted_id,
    )
