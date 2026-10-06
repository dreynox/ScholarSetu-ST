"""
Payment Pydantic schemas for student-scoped payment lookups and response envelopes.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ScholarshipPaymentInfo(BaseModel):
    """Associated scholarship information for payment response."""
    model_config = ConfigDict(from_attributes=True)

    scholarship_id: Optional[str] = Field(default=None, description="Scholarship Business ID (e.g. TRB-SCH-000001)")
    name: Optional[str] = Field(default=None, description="Scholarship Name")
    short_name: Optional[str] = Field(default=None, description="Scholarship Short Name / Code")


class PaymentResponse(BaseModel):
    """
    Standard response schema for payment / disbursement records.
    Hides internal database UUIDs and exposes clean business identifiers.
    """
    model_config = ConfigDict(from_attributes=True)

    payment_id: str = Field(..., description="Unique Business Identifier (e.g. TRB-PAY-000001)")
    application_id: str = Field(..., description="Associated Application Business Identifier (e.g. TRB-APP-000001)")
    amount: float = Field(..., description="Disbursement amount in INR")
    payment_status: str = Field(..., description="Current status (PENDING, PROCESSING, SUCCESS, FAILED)")
    transaction_reference: Optional[str] = Field(default=None, description="Bank transaction reference number")
    utr_number: Optional[str] = Field(default=None, description="Unique Transaction Reference (UTR)")
    payment_date: Optional[datetime] = Field(default=None, description="Timestamp of disbursement")
    bank_name: Optional[str] = Field(default=None, description="Beneficiary / Disbursing bank name")
    failure_reason: Optional[str] = Field(default=None, description="Failure reason if transaction was unsuccessful")
    academic_year: Optional[str] = Field(default=None, description="Academic year of the associated application")
    scholarship: Optional[ScholarshipPaymentInfo] = Field(default=None, description="Associated scholarship details")
    created_at: Optional[datetime] = Field(default=None, description="Disbursement record creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Disbursement record update timestamp")


class PaymentListResponse(BaseModel):
    """List response envelope for student disbursement records."""
    payments: List[PaymentResponse] = Field(default_factory=list, description="List of payment records")
    count: int = Field(..., description="Total count of payment records")


class PaymentSummaryResponse(BaseModel):
    """
    Student-level payment summary metrics.
    Derived strictly from authenticated student's own payment records.
    """
    total_payments: int = Field(default=0, description="Total number of disbursement records")
    pending_payments: int = Field(default=0, description="Count of disbursements in PENDING status")
    processing_payments: int = Field(default=0, description="Count of disbursements in PROCESSING status")
    completed_payments: int = Field(default=0, description="Count of disbursements in SUCCESS/COMPLETED/DISBURSED/PAID status")
    failed_payments: int = Field(default=0, description="Count of disbursements in FAILED/REJECTED/CANCELLED status")
    total_amount: float = Field(default=0.0, description="Total monetary sum of all disbursements")
    disbursed_amount: float = Field(default=0.0, description="Total monetary sum of successfully disbursed payments")
