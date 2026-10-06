"""
Document Pydantic schemas for request validation, updates, and responses.
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """Schema for registering a student document."""
    document_type: str = Field(..., min_length=2, max_length=100, description="Document type (e.g. CASTE_CERTIFICATE, INCOME_CERTIFICATE)")
    document_name: str = Field(..., min_length=2, max_length=255, description="Readable name/title for the document")
    file_url: Optional[str] = Field(default=None, description="Public/storage URL of the document file")
    storage_path: Optional[str] = Field(default=None, description="Storage path identifier")
    file_size: Optional[int] = Field(default=None, ge=0, description="File size in bytes")
    file_type: Optional[str] = Field(default=None, description="MIME type (e.g. application/pdf, image/jpeg)")
    document_number: Optional[str] = Field(default=None, max_length=100, description="Official certificate or document number")
    expiry_date: Optional[date] = Field(default=None, description="Document expiration date")


class DocumentUpdate(BaseModel):
    """Schema for updating an editable draft/pending document."""
    document_type: Optional[str] = Field(default=None, min_length=2, max_length=100)
    document_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    file_url: Optional[str] = None
    storage_path: Optional[str] = None
    file_size: Optional[int] = Field(default=None, ge=0)
    file_type: Optional[str] = None
    document_number: Optional[str] = Field(default=None, max_length=100)
    expiry_date: Optional[date] = None


class DocumentResponse(BaseModel):
    """Public representation of a student document."""
    document_id: str = Field(..., description="Unique Business ID (e.g. TRB-DOC-000001)")
    document_type: str = Field(..., description="Category/Type of document")
    document_name: str = Field(..., description="Name of the document")
    file_url: Optional[str] = Field(default=None, description="File URL")
    storage_path: Optional[str] = Field(default=None, description="Storage bucket path")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    file_type: Optional[str] = Field(default=None, description="File MIME type")
    document_number: Optional[str] = Field(default=None, description="Certificate/Registration number")
    expiry_date: Optional[date] = Field(default=None, description="Expiry date")
    is_active: bool = Field(default=True, description="Active status flag")
    verification_status: Optional[str] = Field(default="PENDING", description="Latest verification status")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    """List response envelope for student documents."""
    documents: List[DocumentResponse] = Field(default_factory=list, description="List of documents")
    count: int = Field(..., description="Count of returned documents")


class DocumentDeleteResponse(BaseModel):
    """Response returned upon successful document deletion."""
    message: str = Field(default="Document deleted successfully")
    document_id: str = Field(..., description="Deleted document ID")


class DocumentVerificationInfo(BaseModel):
    """Document verification details response."""
    document_id: str = Field(..., description="Document business ID")
    document_type: str = Field(..., description="Document type")
    document_name: str = Field(..., description="Document name")
    verification_status: str = Field(..., description="Verification status (PENDING, VERIFIED, REJECTED, FLAGGED)")
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    remarks: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
