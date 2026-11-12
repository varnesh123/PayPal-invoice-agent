"""Pydantic schemas for PayPal-related request/response bodies."""

from typing import List, Optional
from pydantic import BaseModel, Field


class PayPalConnectResponse(BaseModel):
    connected: bool
    sandbox_business_email: Optional[str] = None
    message: str


class InvoiceSummary(BaseModel):
    paypal_invoice_id: str
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    amount: float
    currency: str = "USD"
    status: str
    due_date: Optional[str] = None
    balance_due: float = 0.0


class InvoiceDetail(BaseModel):
    paypal_invoice_id: str
    status: str
    amount: float
    currency: str
    due_date: Optional[str] = None
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    balance_due: float = 0.0
    invoice_number: Optional[str] = None


class RemindRequest(BaseModel):
    invoice_id: str
    send_to_recipient: bool = True
    send_to_invoicer: bool = False


class RemindResponse(BaseModel):
    accepted: bool
    message: str


class InvoicesListResponse(BaseModel):
    invoices: List[InvoiceSummary]
    total: Optional[int] = None
